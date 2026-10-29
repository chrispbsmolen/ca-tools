/* binsa.c - simulated annealing for binary covering arrays CA(N; t, k, 2), t <= 7, k <= 64.
 * Written for ca-tools, 2026-10-27. Method: simulated annealing on single-cell flips with
 * incremental (read-only) evaluation of the change in the number of uncovered
 * (column t-set, tuple) pairs, as in Torres-Jimenez & Rodriguez-Tello, "New bounds for
 * binary covering arrays using simulated annealing", Information Sciences 185 (2012), and
 * Cohen, Colbourn & Ling (2003); plus an optional focused move in the style of Nurmela (2004):
 * pick an uncovered pair, evaluate every single flip that covers it, take the best.
 * No ingredient array unless -i is given (then the first N rows, first k columns of that file).
 *
 * usage: binsa N t k seed maxsec outprefix [options]
 *   -T T0 -E Tend   temperature goes geometrically from T0 to Tend over one cycle (default 2, 2)
 *   -I iters        cycle length in moves (deterministic; default 50e6); cycles repeat
 *   -p pf           probability of a focused move (default 0)
 *   -i file         initial array (rows beyond N ignored, missing rows random)
 *   -d Nmin         descent: after each success delete the row with the fewest uniquely
 *                   covered pairs and continue, down to Nmin
 *   -b              balanced random start
 *   -R moves        with -d: if a deletion is not repaired within this many moves, go back to
 *                   the last covering array and delete the row with the next fewest uniquely
 *                   covered pairs instead (up to 20 rows per level)
 * Writes <outprefix>_<N>.txt (0-based) at each success. Exit 0 if anything was written.
 * Every move is driven by the seed only (no clock in the schedule), so a run is reproducible
 * from its command line, except where maxsec cuts it short.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <time.h>

static int N, t, k, TT; static long nsets;
static uint8_t *A;            /* N x k */
static uint8_t *setc;         /* nsets x t */
#ifndef CNT16
typedef uint8_t cnt_t;         /* counts; a count reaching 255 aborts the run (never seen) */
#define CNTMAX 255
#else
typedef uint16_t cnt_t;
#define CNTMAX 65535
#endif
static cnt_t *cnt;            /* nsets x TT */
typedef struct { uint32_t base; uint8_t q; uint8_t o[7]; } ent_t;   /* o: other columns, then their positions are implied */
static ent_t **cl; static long ncl;   /* per column list of sets containing it */
static uint8_t **clpos;       /* per column per entry: positions of the other columns (t-1 bytes) */
static long cost;
static int32_t *ul; static long nul, ulcap;  /* lazy list of uncovered keys (may hold stale entries) */

static uint64_t rs;
static inline uint64_t xr(void){ rs ^= rs<<13; rs ^= rs>>7; rs ^= rs<<17; return rs; }
static inline long rndl(long n){ return (long)(xr() % (uint64_t)n); }
static inline double rndu(void){ return (xr()>>11) * (1.0/9007199254740992.0); }
static double now(void){ struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts); return ts.tv_sec+1e-9*ts.tv_nsec; }
static long binom(int n,int r){ if(r<0||r>n) return 0; long b=1; for(int i=1;i<=r;i++) b=b*(n-r+i)/i; return b; }

static inline void ul_push(long key){ if(nul>=ulcap){ ulcap=ulcap*2+1024; ul=realloc(ul,sizeof(int32_t)*ulcap); } ul[nul++]=(int32_t)key; }
static void ul_rebuild(void){ nul=0; for(long key=0;key<nsets*TT;key++) if(cnt[key]==0) ul_push(key); }

static inline int tup_e(const uint8_t *row, const ent_t *e, const uint8_t *pos){
    int x=0; for(int j=0;j<t-1;j++) x|=row[e->o[j]]<<pos[j]; return x; }   /* without the flipped column */

static inline long delta(int i,int c){
    const uint8_t *row=A+(long)i*k; int b=row[c]; long d=0; const ent_t *E=cl[c]; const uint8_t *P=clpos[c];
    for(long e=0;e<ncl;e++){ if(e+16<ncl) __builtin_prefetch(cnt+E[e+16].base);
        int x=tup_e(row,E+e,P+e*(t-1)); int q=E[e].q; const cnt_t *C=cnt+E[e].base;
        int xo=x|(b<<q), xn=x|((b^1)<<q); d += (C[xo]==1) - (C[xn]==0); }
    return d; }
static inline void apply(int i,int c){
    uint8_t *row=A+(long)i*k; int b=row[c]; const ent_t *E=cl[c]; const uint8_t *P=clpos[c];
    for(long e=0;e<ncl;e++){ if(e+16<ncl) __builtin_prefetch(cnt+E[e+16].base);
        int x=tup_e(row,E+e,P+e*(t-1)); int q=E[e].q; cnt_t *C=cnt+E[e].base;
        int xo=x|(b<<q), xn=x|((b^1)<<q);
        if(--C[xo]==0){ cost++; ul_push(E[e].base+xo); }
        if(C[xn]==CNTMAX){ fprintf(stderr,"count overflow\n"); exit(3); }
        if(C[xn]++==0) cost--; }
    row[c]=b^1; }
static int tuple_set(int i,long s){ int x=0; for(int q=0;q<t;q++) x|=A[(long)i*k+setc[s*t+q]]<<q; return x; }
static void full_counts(void){ memset(cnt,0,sizeof(cnt_t)*nsets*TT); for(long s=0;s<nsets;s++) for(int i=0;i<N;i++){ cnt_t *p=&cnt[s*TT+tuple_set(i,s)]; if(*p==CNTMAX){ fprintf(stderr,"count overflow\n"); exit(3);} (*p)++; }
    cost=0; for(long key=0;key<nsets*TT;key++) if(!cnt[key]) cost++; ul_rebuild(); }
static long uniq(int i){ long u=0; for(long s=0;s<nsets;s++) if(cnt[s*TT+tuple_set(i,s)]==1) u++; return u; }
static void del_row(int i){ for(long s=0;s<nsets;s++){ long key=s*TT+tuple_set(i,s); if(--cnt[key]==0){ cost++; ul_push(key);} }
    if(i!=N-1) memcpy(A+(long)i*k,A+(long)(N-1)*k,k); N--; }
static void write_out(const char *pre){ char fn[1024]; snprintf(fn,sizeof fn,"%s_%d.txt",pre,N); FILE *o=fopen(fn,"w"); if(!o){perror(fn);return;}
    for(int i=0;i<N;i++){ for(int c=0;c<k;c++) fprintf(o,c?" %d":"%d",A[(long)i*k+c]); fputc('\n',o);} fclose(o); printf("WROTE %s N=%d\n",fn,N); fflush(stdout); }

int main(int argc,char **argv){
    if(argc<7){ fprintf(stderr,"usage: binsa N t k seed maxsec outprefix [-T T0] [-E Tend] [-I iters] [-p pf] [-i init] [-d Nmin] [-b]\n"); return 2; }
    N=atoi(argv[1]); t=atoi(argv[2]); k=atoi(argv[3]); uint64_t seed=strtoull(argv[4],0,10); double maxsec=atof(argv[5]); const char *pre=argv[6];
    double T0=2, Tend=2, pf=0; long IC=50000000; const char *init=0; int Nmin=-1, bal=0; long stall=0;
    for(int a=7;a<argc;a++){
        if(!strcmp(argv[a],"-T")) T0=atof(argv[++a]); else if(!strcmp(argv[a],"-E")) Tend=atof(argv[++a]);
        else if(!strcmp(argv[a],"-I")) IC=atol(argv[++a]); else if(!strcmp(argv[a],"-p")) pf=atof(argv[++a]);
        else if(!strcmp(argv[a],"-i")) init=argv[++a]; else if(!strcmp(argv[a],"-d")) Nmin=atoi(argv[++a]);
        else if(!strcmp(argv[a],"-b")) bal=1; else if(!strcmp(argv[a],"-R")) stall=atol(argv[++a]); else { fprintf(stderr,"unknown option %s\n",argv[a]); return 2; } }
    if(t<2||t>7||k>64||k<=t||N<1){ fprintf(stderr,"bad params\n"); return 2; }
    TT=1<<t; nsets=binom(k,t); ncl=binom(k-1,t-1);
    rs=seed*0x9E3779B97F4A7C15ULL+0x2545F4914F6CDD1DULL; if(!rs) rs=1; for(int i=0;i<20;i++) xr();
    setc=malloc(nsets*t); cnt=malloc(sizeof(cnt_t)*nsets*TT);
    cl=malloc(sizeof(ent_t*)*k); clpos=malloc(sizeof(uint8_t*)*k); long *fill=calloc(k,sizeof(long));
    for(int c=0;c<k;c++){ cl[c]=malloc(sizeof(ent_t)*ncl); clpos[c]=malloc(ncl*(t-1)+1); }
    { int S[8]; for(int q=0;q<t;q++) S[q]=q; long s=0;
      while(1){ for(int q=0;q<t;q++) setc[s*t+q]=S[q];
        for(int q=0;q<t;q++){ int c=S[q]; ent_t *e=&cl[c][fill[c]]; uint8_t *p=clpos[c]+fill[c]*(t-1); e->base=(uint32_t)(s*TT); e->q=q; int j=0; for(int r=0;r<t;r++) if(r!=q){ e->o[j]=S[r]; p[j]=r; j++; } fill[c]++; }
        s++; int q=t-1; while(q>=0 && S[q]==k-t+q) q--; if(q<0) break; S[q]++; for(int r=q+1;r<t;r++) S[r]=S[r-1]+1; } }
    A=malloc((long)N*k); int nread=0;
    if(init){ FILE *in=fopen(init,"r"); if(!in){ perror(init); return 2; } char *line=malloc(1<<20);
        while(nread<N && fgets(line,1<<20,in)){ char *p=line; int c=0; while(c<k){ while(*p==' '||*p=='\t'||*p==',') p++; if(*p<'0'||*p>'9') break; long v=strtol(p,&p,10); A[(long)nread*k+c]=v&1; c++; } if(c==k) nread++; }
        fclose(in); free(line); }
    for(int i=nread;i<N;i++) for(int c=0;c<k;c++) A[(long)i*k+c]=xr()&1;
    if(bal && !init){ int *pm=malloc(sizeof(int)*N); for(int c=0;c<k;c++){ for(int i=0;i<N;i++) pm[i]=i; for(int i=N-1;i>0;i--){ int j=rndl(i+1),x=pm[i]; pm[i]=pm[j]; pm[j]=x; } for(int i=0;i<N;i++) A[(long)i*k+c]=(pm[i]<N/2); } free(pm); }
    full_counts();
    printf("binsa N=%d t=%d k=%d seed=%llu maxsec=%.0f T0=%g Tend=%g I=%ld pf=%g init=%s(%d rows) Nmin=%d bal=%d R=%ld sets=%ld init_cost=%ld mem=%.0fMB\n",
        N,t,k,(unsigned long long)seed,maxsec,T0,Tend,IC,pf,init?init:"-",nread,Nmin,bal,stall,nsets,cost,(nsets*TT*(double)sizeof(cnt_t)+k*ncl*(sizeof(ent_t)+t))/1e6); fflush(stdout);
    double t0=now(), lastp=t0; long it=0, itc0=0, best=cost; int wrote=0; double Temp=T0;
    int *cr=malloc(sizeof(int)*N*2+8), *cc=malloc(sizeof(int)*N*2+8);
    double lT0=log(T0), lr=log(Tend/T0);
    uint8_t *Asave=0; long *uu=0; int *ordl=0, Nsave=0, op=0;
    while(1){
        if(cost==0){ write_out(pre); wrote=1; if(Nmin<0 || N-1<Nmin) break;
            if(!Asave){ Asave=malloc((long)N*k); uu=malloc(sizeof(long)*N); ordl=malloc(sizeof(int)*N); }
            memcpy(Asave,A,(long)N*k); Nsave=N;
            for(int i=0;i<N;i++){ uu[i]=uniq(i); ordl[i]=i; }
            for(int a=1;a<N;a++){ int x=ordl[a],b=a-1; while(b>=0 && uu[ordl[b]]>uu[x]){ ordl[b+1]=ordl[b]; b--; } ordl[b+1]=x; }
            op=0; int bi=ordl[0];
            del_row(bi); best=cost; itc0=it; printf("  deleted row %d (unique %ld) N=%d cost=%ld\n",bi,uu[bi],N,cost); fflush(stdout); }
        if(stall>0 && Asave && cost>0 && it-itc0>stall && op+1<Nsave && op+1<20){
            memcpy(A,Asave,(long)Nsave*k); N=Nsave; full_counts(); op++; int bi=ordl[op];
            del_row(bi); best=cost; itc0=it; printf("  stalled: back to N=%d, deleted row %d instead (unique %ld) cost=%ld\n",Nsave,bi,uu[bi],cost); fflush(stdout); }
        for(int l=0;l<4096 && cost>0;l++){
            it++;
            if(pf>0 && rndu()<pf){
                long key=-1; while(nul>0){ long j=rndl(nul); if(cnt[ul[j]]==0){ key=ul[j]; break; } ul[j]=ul[--nul]; }
                if(key<0){ ul_rebuild(); continue; }
                long s=key/TT; int x=key%TT; int nc=0;
                for(int i=0;i<N;i++){ int z=tuple_set(i,s)^x; if(z && !(z&(z-1))){ cr[nc]=i; cc[nc]=setc[s*t+__builtin_ctz(z)]; nc++; } }
                if(!nc) continue; long bd=0; int bj=-1, ties=0;
                for(int j=0;j<nc;j++){ long d=delta(cr[j],cc[j]); if(bj<0||d<bd){bd=d;bj=j;ties=1;} else if(d==bd && rndl(++ties)==0) bj=j; }
                if(bd<=0 || rndu()<exp(-bd/Temp)) apply(cr[bj],cc[bj]);
            } else {
                int i=rndl(N), c=rndl(k); long d=delta(i,c);
                if(d<=0 || rndu()<exp(-d/Temp)) apply(i,c);
            }
            if(cost<best) best=cost;
        }
        if(nul>8*(cost+1024)) ul_rebuild();
        { double fr=(double)((it-itc0)%IC)/IC; Temp=exp(lT0+lr*fr); }
        double tn=now();
        if(tn-lastp>60){ printf("  t=%.0fs it=%ld T=%.3f cost=%ld best=%ld N=%d\n",tn-t0,it,Temp,cost,best,N); fflush(stdout); lastp=tn; }
        if(tn-t0>maxsec) break;
    }
    { long c1=cost; full_counts(); if(c1!=cost) printf("CHECK MISMATCH incremental %ld full %ld\n",c1,cost); }
    printf("END it=%ld time=%.1fs final_cost=%ld best=%ld N=%d wrote=%d rate=%.0f/s\n",it,now()-t0,cost,best,N,wrote,it/(now()-t0+1e-9));
    return wrote?0:1;
}
