/* catabu.c - row elimination plus fixed-N tabu search for binary covering arrays
 * CA(N; t, k, 2), t = 3 or 4.  Written for ca-tools, 2026-10-27; no external ingredient.
 *
 * Method (credits): the outer loop is row elimination in the spirit of Nayeri, Colbourn and
 * Konjevod (2013, "Randomized post-optimization of covering arrays", Eur. J. Combin.): delete
 * the row that covers the fewest t-way interactions on its own. The inner loop is the tabu
 * search of Nurmela (2004, "Upper bounds for covering arrays by tabu search", Discrete Appl.
 * Math. 138): pick an uncovered interaction at random, consider every single-cell change that
 * makes some row cover it, take the best change that is not tabu (aspiration when it gives a
 * new best cost).  Our own implementation:
 *   - column bitsets over the rows; the cost of a change is
 *       loss = nec[r][j]  (interactions through column j covered by row r alone, kept
 *                          incrementally, as in our nck.c)
 *       gain = uncovered interactions through column j that row r would cover after the change
 *              (scan of a per-column list of the uncovered interactions);
 *   - applying a change walks the C(k-1, t-1) column sets through j with bitset ANDs only, so
 *     no table of size C(k, t) 2^t is stored (memory O(N k)).
 *
 * Usage:
 *   catabu t k infile N_in target outprefix seed maxsec [tenure] [noise_permille] [colsel]
 *          [attemptsec]
 *   infile  : N_in x (>= k) array, symbols 0/1 or 1/2, one row per line
 *   colsel  : 0 = first k columns; s > 0 = a random k-subset of the columns (seed s), kept in
 *             their original order
 *   Every time the array becomes a covering array with fewer rows than before, it is written to
 *   outprefix_N.txt (0-based, space separated). It stops at target rows or after maxsec
 *   seconds (wall clock). attemptsec (default maxsec): if one level has not reached cost 0
 *   after that long, go back to the last covering array and delete another row.
 * Compile: cc -O3 -march=native -DW=2 -o catabu2 catabu.c   (W = 64-bit words per column:
 *          N <= 64 W)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

#ifndef W
#define W 2
#endif
#define NMAX (64*W)
#define KMAX 4095

typedef struct { uint64_t w[W]; } bs;

static int N, K, T;
static uint8_t *A;           /* NMAX x K */
static bs *col;              /* K */
static bs all;
static int *nec;             /* NMAX x K */
static long long cost = 0;

static unsigned long long rs = 88172645463325252ULL;
static inline unsigned long long xr(void){ rs ^= rs<<13; rs ^= rs>>7; rs ^= rs<<17; return rs; }
static inline int rnd(int n){ return (int)(xr() % (unsigned long long)n); }
static double now(void){ struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts); return ts.tv_sec+1e-9*ts.tv_nsec; }

static inline bs band(bs a, bs b){ bs r; for(int i=0;i<W;i++) r.w[i]=a.w[i]&b.w[i]; return r; }
static inline bs bandn(bs a, bs b){ bs r; for(int i=0;i<W;i++) r.w[i]=a.w[i]&~b.w[i]; return r; }
static inline int bpop(bs a){ int s=0; for(int i=0;i<W;i++) s+=__builtin_popcountll(a.w[i]); return s; }
/* 0, 1 or 2 (= at least two) */
static inline int bpop2(bs a){ int s=0; for(int i=0;i<W;i++){ uint64_t x=a.w[i]; if(x){ if(x&(x-1)) return 2; s++; if(s>1) return 2; } } return s; }
static inline int bfirst(bs a){ for(int i=0;i<W;i++) if(a.w[i]) return 64*i+__builtin_ctzll(a.w[i]); return -1; }
static inline int bget(bs a,int r){ return (a.w[r>>6]>>(r&63))&1; }
static inline bs match(int c,int v){ return v? col[c] : bandn(all,col[c]); }

/* ---------- uncovered interactions: pool + hash + per-column lists ---------- */
typedef struct { uint16_t c[4]; uint8_t tup; int pos[4]; uint64_t key; } Ent;
static Ent *pool; static int poolcap=0, npool=0; static int *freel; static int nfree=0;
static int *hsh; static long long hcap=0, hcount=0;    /* stores entry id or -1 */
static int **clist; static int *clen, *ccap;
static int *ulist; static int ulen=0, ucap=0; static int *upos;  /* global list for random pick */

static inline uint64_t mkkey(const int *c,int tup){ uint64_t k=0; for(int i=0;i<T;i++) k|=((uint64_t)c[i])<<(12*i); return k|((uint64_t)tup<<48); }
static inline uint64_t hfun(uint64_t k){ k^=k>>33; k*=0xff51afd7ed558ccdULL; k^=k>>33; k*=0xc4ceb9fe1a85ec53ULL; k^=k>>33; return k; }
static void hinsert_raw(int id){ uint64_t m=hcap-1; uint64_t h=hfun(pool[id].key)&m; while(hsh[h]>=0) h=(h+1)&m; hsh[h]=id; }
static void hgrow(void){ long long oc=hcap; int *oh=hsh; hcap = oc? oc*2 : 1<<16; hsh=malloc(sizeof(int)*hcap); for(long long i=0;i<hcap;i++) hsh[i]=-1; if(oh){ for(long long i=0;i<oc;i++) if(oh[i]>=0) hinsert_raw(oh[i]); free(oh);} }
static long long hfind(uint64_t key){ uint64_t m=hcap-1; uint64_t h=hfun(key)&m; while(hsh[h]>=0){ if(pool[hsh[h]].key==key) return (long long)h; h=(h+1)&m; } return -1; }
static void hdel(long long h){ uint64_t m=hcap-1; hsh[h]=-1; uint64_t i=(h+1)&m; while(hsh[i]>=0){ int id=hsh[i]; hsh[i]=-1; hinsert_raw(id); i=(i+1)&m; } }

static void unc_add_sorted(const int *c,int tup){
    if(hcount*2+2>hcap) hgrow();
    int id; if(nfree) id=freel[--nfree]; else { if(npool==poolcap){ poolcap=poolcap?poolcap*2:4096; pool=realloc(pool,sizeof(Ent)*poolcap); freel=realloc(freel,sizeof(int)*poolcap); upos=realloc(upos,sizeof(int)*poolcap);} id=npool++; }
    Ent *e=&pool[id]; for(int i=0;i<T;i++) e->c[i]=(uint16_t)c[i]; e->tup=(uint8_t)tup; e->key=mkkey(c,tup);
    hinsert_raw(id); hcount++;
    for(int i=0;i<T;i++){ int cc=c[i]; if(clen[cc]==ccap[cc]){ ccap[cc]=ccap[cc]?ccap[cc]*2:16; clist[cc]=realloc(clist[cc],sizeof(int)*ccap[cc]); } e->pos[i]=clen[cc]; clist[cc][clen[cc]++]=id; }
    if(ulen==ucap){ ucap=ucap?ucap*2:4096; ulist=realloc(ulist,sizeof(int)*ucap);} upos[id]=ulen; ulist[ulen++]=id;
    cost++;
}
static void unc_remove_sorted(const int *c,int tup){
    uint64_t key=mkkey(c,tup); long long h=hfind(key);
    if(h<0){ fprintf(stderr,"BUG: remove of absent entry\n"); exit(3); }
    int id=hsh[h]; hdel(h); hcount--;
    Ent *e=&pool[id];
    for(int i=0;i<T;i++){ int cc=e->c[i]; int p=e->pos[i]; int last=clist[cc][--clen[cc]];
        if(last!=id){ clist[cc][p]=last; Ent *f=&pool[last]; for(int q=0;q<T;q++) if(f->c[q]==cc){ f->pos[q]=p; break; } } }
    { int p=upos[id]; int last=ulist[--ulen]; if(last!=id){ ulist[p]=last; upos[last]=p; } }
    freel[nfree++]=id; cost--;
}
static void unc_clear(void){
    for(int c=0;c<K;c++) clen[c]=0; ulen=0; npool=0; nfree=0; hcount=0; if(hsh) for(long long i=0;i<hcap;i++) hsh[i]=-1; cost=0;
}
/* sort the set {others..., j} with tuple bits; vals[i] = value of row at column cs[i] */
static inline void sort_set(int *cs,int *vals,int n){ for(int i=1;i<n;i++){ int x=cs[i], y=vals[i], p=i-1; while(p>=0 && cs[p]>x){ cs[p+1]=cs[p]; vals[p+1]=vals[p]; p--; } cs[p+1]=x; vals[p+1]=y; } }
static inline int tup_of(const int *vals){ int t=0; for(int i=0;i<T;i++) t|=vals[i]<<i; return t; }

/* ---------- full recomputation ---------- */
static void rebuild(void){
    for(int i=0;i<W;i++) all.w[i]=0; for(int r=0;r<N;r++) all.w[r>>6]|=1ULL<<(r&63);
    for(int c=0;c<K;c++){ for(int i=0;i<W;i++) col[c].w[i]=0; for(int r=0;r<N;r++) if(A[r*K+c]) col[c].w[r>>6]|=1ULL<<(r&63); }
    memset(nec,0,sizeof(int)*NMAX*K); unc_clear();
    if(T==3){
        for(int a=0;a<K;a++) for(int b=a+1;b<K;b++){ bs P[4]; for(int x=0;x<4;x++) P[x]=band(match(a,x&1),match(b,(x>>1)&1));
            for(int c=b+1;c<K;c++){ bs m1=col[c], m0=bandn(all,col[c]);
                for(int x=0;x<8;x++){ bs M=band(P[x&3], (x>>2)? m1:m0); int p=bpop2(M);
                    if(p==0){ int cs[3]={a,b,c}; unc_add_sorted(cs,x); }
                    else if(p==1){ int r=bfirst(M); nec[r*K+a]++; nec[r*K+b]++; nec[r*K+c]++; } } } }
    } else {
        for(int a=0;a<K;a++) for(int b=a+1;b<K;b++){ bs P[4]; for(int x=0;x<4;x++) P[x]=band(match(a,x&1),match(b,(x>>1)&1));
            for(int c=b+1;c<K;c++){ bs Q[8]; bs m1=col[c], m0=bandn(all,col[c]); for(int x=0;x<8;x++) Q[x]=band(P[x&3],(x>>2)?m1:m0);
                for(int d=c+1;d<K;d++){ bs n1=col[d], n0=bandn(all,col[d]);
                    for(int x=0;x<16;x++){ bs M=band(Q[x&7],(x>>3)?n1:n0); int p=bpop2(M);
                        if(p==0){ int cs[4]={a,b,c,d}; unc_add_sorted(cs,x); }
                        else if(p==1){ int r=bfirst(M); nec[r*K+a]++; nec[r*K+b]++; nec[r*K+c]++; nec[r*K+d]++; } } } } }
    }
}

/* ---------- apply a flip of cell (r, j) ---------- */
static bs *Dp;   /* per column: rows != r agreeing with row r */
static void apply_flip(int r,int j){
    bs notr=all; notr.w[r>>6]&=~(1ULL<<(r&63));
    for(int c=0;c<K;c++){ Dp[c]= A[r*K+c]? band(col[c],notr) : band(bandn(all,col[c]),notr); }
    bs Dj=Dp[j]; int vj=A[r*K+j];
    int *nr=&nec[r*K];
    if(T==3){
        for(int a=0;a<K;a++){ if(a==j) continue; for(int b=a+1;b<K;b++){ if(b==j) continue;
            bs M=band(Dp[a],Dp[b]); bs x=band(M,Dj), y=bandn(M,Dj);
            int px=bpop2(x), py=bpop2(y);
            if(px<2){ if(px==0){ int cs[3]={a,b,j}, vs[3]={A[r*K+a],A[r*K+b],vj}; sort_set(cs,vs,3); unc_add_sorted(cs,tup_of(vs)); nr[a]--; nr[b]--; nr[j]--; }
                      else { int q=bfirst(x); int *nq=&nec[q*K]; nq[a]++; nq[b]++; nq[j]++; } }
            if(py<2){ if(py==0){ int cs[3]={a,b,j}, vs[3]={A[r*K+a],A[r*K+b],vj^1}; sort_set(cs,vs,3); unc_remove_sorted(cs,tup_of(vs)); nr[a]++; nr[b]++; nr[j]++; }
                      else { int q=bfirst(y); int *nq=&nec[q*K]; nq[a]--; nq[b]--; nq[j]--; } }
        } }
    } else {
        for(int a=0;a<K;a++){ if(a==j) continue; for(int b=a+1;b<K;b++){ if(b==j) continue; bs E=band(Dp[a],Dp[b]);
            for(int c=b+1;c<K;c++){ if(c==j) continue;
                bs M=band(E,Dp[c]); bs x=band(M,Dj), y=bandn(M,Dj);
                int px=bpop2(x), py=bpop2(y);
                if(px<2){ if(px==0){ int cs[4]={a,b,c,j}, vs[4]={A[r*K+a],A[r*K+b],A[r*K+c],vj}; sort_set(cs,vs,4); unc_add_sorted(cs,tup_of(vs)); nr[a]--; nr[b]--; nr[c]--; nr[j]--; }
                          else { int q=bfirst(x); int *nq=&nec[q*K]; nq[a]++; nq[b]++; nq[c]++; nq[j]++; } }
                if(py<2){ if(py==0){ int cs[4]={a,b,c,j}, vs[4]={A[r*K+a],A[r*K+b],A[r*K+c],vj^1}; sort_set(cs,vs,4); unc_remove_sorted(cs,tup_of(vs)); nr[a]++; nr[b]++; nr[c]++; nr[j]++; }
                          else { int q=bfirst(y); int *nq=&nec[q*K]; nq[a]--; nq[b]--; nq[c]--; nq[j]--; } }
            } } }
    }
    A[r*K+j]^=1; col[j].w[r>>6]^=1ULL<<(r&63);
}

/* gain of flipping (r, j): uncovered interactions through j that row r would then cover */
static inline int gain_of(int r,int j){
    int g=0; const uint8_t *ar=&A[r*K]; int n=clen[j]; const int *L=clist[j];
    for(int i=0;i<n;i++){ const Ent *e=&pool[L[i]]; int ok=1;
        for(int q=0;q<T;q++){ int c=e->c[q]; int want=(e->tup>>q)&1; if(c==j){ if(ar[c]==want){ok=0;break;} } else if(ar[c]!=want){ok=0;break;} }
        g+=ok; }
    return g;
}

static void write_out(const char *prefix){
    char fn[600]; snprintf(fn,sizeof fn,"%s_%d.txt",prefix,N); FILE *f=fopen(fn,"w"); if(!f){perror("write");return;}
    for(int r=0;r<N;r++){ for(int c=0;c<K;c++) fprintf(f,"%s%d",c?" ":"",A[r*K+c]); fputc('\n',f);} fclose(f);
}

int main(int argc,char**argv){
    if(argc<9){ fprintf(stderr,"usage: catabu t k infile N_in target outprefix seed maxsec [tenure] [noise_permille] [colsel] [attemptsec]\n"); return 2; }
    T=atoi(argv[1]); K=atoi(argv[2]); const char *in=argv[3]; int Nin=atoi(argv[4]); int target=atoi(argv[5]); const char *prefix=argv[6];
    unsigned long long seed=strtoull(argv[7],0,10); double maxsec=atof(argv[8]);
    int tenure = argc>9? atoi(argv[9]) : 10; int noise = argc>10? atoi(argv[10]) : 20; unsigned long long colsel = argc>11? strtoull(argv[11],0,10):0;
    double attemptsec = argc>12? atof(argv[12]) : maxsec;
    if(T!=3 && T!=4){ fprintf(stderr,"t must be 3 or 4\n"); return 2; }
    if(Nin>NMAX){ fprintf(stderr,"N_in=%d > NMAX=%d (recompile with larger W)\n",Nin,NMAX); return 2; }
    if(K>KMAX){ fprintf(stderr,"k too large\n"); return 2; }
    rs ^= seed*0x9E3779B97F4A7C15ULL; for(int i=0;i<50;i++) xr();
    /* read */
    FILE *f=fopen(in,"r"); if(!f){perror("in");return 2;}
    int cap=1<<16; int *buf=malloc(sizeof(int)*cap); int n=0, rows=0, kin=-1, cur=0; int ch; int val=-1;
    while(1){ ch=fgetc(f); if(ch>='0'&&ch<='9'){ val=(val<0?0:val*10)+(ch-'0'); continue; }
        if(val>=0){ if(n==cap){cap*=2;buf=realloc(buf,sizeof(int)*cap);} buf[n++]=val; cur++; val=-1; }
        if(ch=='\n'||ch==EOF){ if(cur>0){ if(kin<0) kin=cur; else if(cur!=kin){ fprintf(stderr,"ragged input\n"); return 2;} rows++; } cur=0; if(ch==EOF) break; } }
    fclose(f);
    if(rows!=Nin){ fprintf(stderr,"input has %d rows, expected %d\n",rows,Nin); return 2; }
    if(kin<K){ fprintf(stderr,"input has %d columns < k=%d\n",kin,K); return 2; }
    int mn=99,mx=-1; for(int i=0;i<n;i++){ if(buf[i]<mn) mn=buf[i]; if(buf[i]>mx) mx=buf[i]; }
    if(mx-mn>1){ fprintf(stderr,"not binary\n"); return 2; }
    int *cols=malloc(sizeof(int)*kin); for(int i=0;i<kin;i++) cols[i]=i;
    if(colsel){ unsigned long long save=rs; rs=colsel*0xD1B54A32D192ED03ULL+1; for(int i=0;i<50;i++) xr();
        for(int i=kin-1;i>0;i--){ int p=rnd(i+1); int t=cols[i]; cols[i]=cols[p]; cols[p]=t; }
        /* keep the first K of the shuffle, in increasing order */
        for(int i=1;i<K;i++){ int x=cols[i],p=i-1; while(p>=0&&cols[p]>x){cols[p+1]=cols[p];p--;} cols[p+1]=x; }
        rs=save; }
    N=Nin; A=calloc((size_t)NMAX*K,1); for(int r=0;r<N;r++) for(int c=0;c<K;c++) A[r*K+c]=(uint8_t)(buf[r*kin+cols[c]]-mn);
    fprintf(stderr,"columns used:"); for(int c=0;c<K;c++) fprintf(stderr," %d",cols[c]); fprintf(stderr,"\n");
    col=malloc(sizeof(bs)*K); Dp=malloc(sizeof(bs)*K); nec=malloc(sizeof(int)*NMAX*K);
    clist=calloc(K,sizeof(int*)); clen=calloc(K,sizeof(int)); ccap=calloc(K,sizeof(int));
    uint8_t *saveA=malloc((size_t)NMAX*K); int saveN;
    int *tabu=malloc(sizeof(int)*NMAX*K);
    double t0=now();
    rebuild();
    fprintf(stderr,"N=%d t=%d k=%d: initial uncovered=%lld (%.1fs)\n",N,T,K,cost,now()-t0);
    if(cost==0){ memcpy(saveA,A,(size_t)N*K); saveN=N; } else saveN=-1;
    long long moves=0; double lastrep=now(), attempt_start=now(); long long best=cost; int fails=0;
    typedef struct { int r,j,d; } Cand; Cand *cand=malloc(sizeof(Cand)*NMAX*4);
    while(now()-t0<maxsec){
        if(cost==0){
            if(saveN<0 || N<=saveN){ memcpy(saveA,A,(size_t)N*K); saveN=N; }
            write_out(prefix);
            fprintf(stderr,"COVERING ARRAY N=%d (moves %lld, %.1fs) -> %s_%d.txt\n",N,moves,now()-t0,prefix,N); fflush(stderr);
            if(N<=target) break;
            /* delete the row with fewest uniquely covered interactions (ties random) */
            int br=-1; long long bu=1LL<<60; int nt=0;
            for(int r=0;r<N;r++){ long long u=0; for(int c=0;c<K;c++) u+=nec[r*K+c]; if(u<bu){bu=u;br=r;nt=1;} else if(u==bu){ nt++; if(rnd(nt)==0) br=r; } }
            for(int c=0;c<K;c++) A[br*K+c]=A[(N-1)*K+c]; N--;
            rebuild(); best=cost; attempt_start=now(); fails=0;
            for(int i=0;i<NMAX*K;i++) tabu[i]=0; moves=0;
            fprintf(stderr,"deleted a row (%lld/%d unique interactions) -> N=%d, uncovered=%lld\n",bu/T,1,N,cost); fflush(stderr);
            continue;
        }
        if(now()-attempt_start>attemptsec && saveN>0){
            /* restart this level: back to the last covering array, delete a random low-coverage row */
            memcpy(A,saveA,(size_t)saveN*K); N=saveN; rebuild();
            long long *u=malloc(sizeof(long long)*N); for(int r=0;r<N;r++){ u[r]=0; for(int c=0;c<K;c++) u[r]+=nec[r*K+c]; }
            /* choose among the 8 rows with fewest unique interactions */
            int idx[8]; int m=0; for(int s=0;s<8&&s<N;s++){ int b=-1; for(int r=0;r<N;r++){ int used=0; for(int q=0;q<m;q++) if(idx[q]==r) used=1; if(!used && (b<0||u[r]<u[b])) b=r; } idx[m++]=b; }
            int br=idx[rnd(m)]; long long bu=u[br]; free(u);
            for(int c=0;c<K;c++) A[br*K+c]=A[(N-1)*K+c]; N--;
            rebuild(); best=cost; attempt_start=now(); fails++;
            for(int i=0;i<NMAX*K;i++) tabu[i]=0; moves=0;
            fprintf(stderr,"restart %d of level N=%d: deleted a row with %lld unique interactions, uncovered=%lld (%.0fs)\n",fails,N,bu/T,cost,now()-t0); fflush(stderr);
            continue;
        }
        /* one tabu move */
        int eid=ulist[rnd(ulen)]; Ent *e=&pool[eid]; int nc=0;
        for(int i=0;i<T;i++){ bs M=all; for(int l=0;l<T;l++){ bs m=match(e->c[l],(e->tup>>l)&1); if(l==i){ M=bandn(M,m);} else M=band(M,m);}
            for(int w=0;w<W;w++){ uint64_t x=M.w[w]; while(x){ int b=__builtin_ctzll(x); x&=x-1; int r=64*w+b; cand[nc].r=r; cand[nc].j=e->c[i]; nc++; } } }
        if(nc==0){ /* no row at distance 1: write the tuple into a random row */
            Ent ec=*e; int r=rnd(N); for(int l=0;l<T;l++){ int c=ec.c[l]; if(A[r*K+c]!=((ec.tup>>l)&1)) apply_flip(r,c); } moves++; continue; }
        int pick=-1;
        if(rnd(1000)<noise) pick=rnd(nc);
        else { int bd=1<<30, nt=0;
            for(int i=0;i<nc;i++){ int r=cand[i].r, j=cand[i].j; int d=nec[r*K+j]-gain_of(r,j); cand[i].d=d;
                int allowed = tabu[r*K+j]<=moves || cost+d<best;
                if(!allowed) continue;
                if(d<bd){bd=d;pick=i;nt=1;} else if(d==bd){ nt++; if(rnd(nt)==0) pick=i; } }
            if(pick<0) pick=rnd(nc); }
        { int r=cand[pick].r, j=cand[pick].j; apply_flip(r,j); moves++; tabu[r*K+j]=(int)moves+tenure; }
        if(cost<best) best=cost;
        if(now()-lastrep>30){ fprintf(stderr,"  N=%d cost=%lld best=%lld moves=%lld (%.0f/s) %.0fs\n",N,cost,best,moves,moves/(now()-attempt_start+1e-9),now()-t0); fflush(stderr); lastrep=now(); }
    }
    fprintf(stderr,"done: last covering array N=%d; current N=%d cost=%lld; %.0fs\n",saveN,N,cost,now()-t0);
    return 0;
}
