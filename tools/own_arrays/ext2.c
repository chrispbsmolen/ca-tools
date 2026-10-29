/* ext2.c - strength-2 covering array search with column extension, general v (used with v = 3).
 * Written 2026-10-27 for ca-tools (group B, ternary t = 2). No external array is read except the
 * optional start file given on the command line.
 *
 * Methods (credit): the local search is a tabu search in the style of Nurmela (2004, "Upper bounds
 * for covering arrays by tabu search"): pick a random uncovered pair-tuple, consider every one-cell
 * change that covers it, take the best non-tabu one. Column extension (add a column to a covering
 * array, then repair by search) follows the idea of Torres-Jimenez, Acevedo-Juarez and Avila-George
 * (2021, "CA Extender"); this is our own implementation and starts only from arrays we give it.
 *
 * Usage: ext2 N K v seed maxseconds outprefix [initfile|-] [k0]
 *   N, K       rows and final number of columns.
 *   initfile   optional start array (n0 <= N rows, k1 columns, 0- or 1-based); extra rows random.
 *   k0         incremental mode: start with k0 columns (taken from the init file, or random) and add
 *              one column at a time whenever the current array covers; 0 or absent = all K columns at
 *              once (fixed mode).
 * Local search: each step picks a random uncovered (column pair, tuple) and lists the one-cell
 *   changes that would cover it. With SAT = 0 (default) it is the tabu search above: the best
 *   non-tabu change is made (aspiration on a new best). With SAT > 0 it is simulated annealing:
 *   one listed change is drawn at random and made with the Metropolis rule at temperature SAT
 *   (always when it does not raise the number of uncovered tuples, else with prob. exp(-d/SAT)).
 * Environment (all optional; a variable left unset leaves the run as without it):
 *   TENURE       tabu tenure in iterations (default 3; tabu mode)
 *   STAG         iterations without improvement before a perturbation of N/4+1 random cells
 *                (default 200000; tabu mode)
 *   SAT          annealing temperature; > 0 selects simulated annealing (default 0)
 *   SAT1, SAL    cyclic geometric cooling from SAT to SAT1 over SAL iterations, repeated
 *                (default: SAL = 0, constant temperature SAT)
 *   SASTAG       (annealing) after SASTAG iterations without a new best, change SAKICK random
 *                cells (default 0 = off); SAKICK default 3
 *   NEWCOLTRY    in incremental mode, a new column gets the best of NEWCOLTRY random fillings,
 *                each followed by greedy descent on that column (default 1)
 *   COLRESAMPLE  (annealing, incremental mode) when the newest column has not been covered after
 *                COLRESAMPLE iterations, refill it as for a new column (default 0 = off)
 *   RESTART      (annealing, incremental mode) when the newest column has not been covered after
 *                RESTART iterations, go back to the last covering array and refill the new column
 *                (default 0 = off)
 *   FIXC         the first FIXC rows are fixed constant rows (row r all r) and never changed
 *                (default 0)
 *   DROP         comma list of 0-based row numbers of the init file to skip when reading it
 *   SAVEK        comma list of k at which to save a file in incremental mode
 * Output: outprefix_N_k.txt (0-based, space separated) for every success in fixed mode, and in
 *   incremental mode for the largest k reached and each k in SAVEK. Log on stderr.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <math.h>

static int N, K, KM, V, VV;            /* KM = current number of columns */
static uint8_t *A;                    /* N x K row-major */
static uint8_t *cnt;                  /* K x K x VV, both orientations */
static int32_t *pos;                  /* tri(a,b)*VV+tup -> index in ulist or -1 */
static int64_t *ul; static int64_t nu = 0;
static int64_t *tabu; static int FIXC=0;
static unsigned long long rs = 88172645463325252ULL;
static inline unsigned long long xr(void){ rs ^= rs<<7; rs ^= rs>>9; return rs; }
static inline int rnd(int n){ return (int)(xr() % (unsigned long long)n); }
static inline int64_t tri(int a,int b){ return (int64_t)a*(2LL*K-a-1)/2 + (b-a-1); }
static inline void unc_add(int a,int b,int tup){ int64_t e=tri(a,b)*VV+tup; pos[e]=(int32_t)nu; ul[nu++]=((int64_t)a*K+b)*VV+tup; }
static inline void unc_del(int a,int b,int tup){ int64_t e=tri(a,b)*VV+tup; int32_t p=pos[e]; int64_t last=ul[--nu]; ul[p]=last;
    int64_t lt=last%VV, lp=last/VV; int la=(int)(lp/K), lb=(int)(lp%K); pos[tri(la,lb)*VV+lt]=p; pos[e]=-1; }
static double now(void){ struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return t.tv_sec+1e-9*t.tv_nsec; }

static inline int delta(int r,int c,int nv){
    int ov=A[(size_t)r*K+c]; if(ov==nv) return 0;
    const uint8_t *base=cnt+(size_t)c*K*VV; const uint8_t *row=A+(size_t)r*K; int d=0;
    const int o1=ov*V, n1=nv*V;
    for(int j=0;j<KM;j++){ if(j==c) continue; const uint8_t *q=base+(size_t)j*VV; int y=row[j]; d += (q[o1+y]==1) - (q[n1+y]==0); }
    return d;
}
static void apply(int r,int c,int nv){
    int ov=A[(size_t)r*K+c]; if(ov==nv) return;
    uint8_t *base=cnt+(size_t)c*K*VV; const uint8_t *row=A+(size_t)r*K;
    for(int j=0;j<KM;j++){ if(j==c) continue; int y=row[j];
        uint8_t *q=base+(size_t)j*VV, *qt=cnt+((size_t)j*K+c)*VV;
        int a=c<j?c:j, b=c<j?j:c;
        /* remove old */
        q[ov*V+y]--; qt[y*V+ov]--; if(q[ov*V+y]==0) unc_add(a,b, c<j? ov*V+y : y*V+ov);
        if(q[nv*V+y]==0) unc_del(a,b, c<j? nv*V+y : y*V+nv);
        q[nv*V+y]++; qt[y*V+nv]++;
    }
    A[(size_t)r*K+c]=nv;
}
/* add column c=KM with current values in A (already set); update counts */
static void add_column(void){
    int c=KM;
    for(int j=0;j<c;j++){
        uint8_t *q=cnt+((size_t)c*K+j)*VV, *qt=cnt+((size_t)j*K+c)*VV; memset(q,0,VV); memset(qt,0,VV);
        for(int r=0;r<N;r++){ int x=A[(size_t)r*K+c], y=A[(size_t)r*K+j]; q[x*V+y]++; qt[y*V+x]++; }
        for(int t=0;t<VV;t++) if(qt[t]==0) unc_add(j,c,t);
    }
    KM++;
}
/* choose values for column c (already counted): best of ntry random starts + greedy descent */
static void newcol(int c,int ntry,int first_random){
    static uint8_t bestcol[256]; int64_t bestnu=-1;
    for(int tr=0;tr<ntry;tr++){
        if(tr>0 || first_random) for(int r=FIXC;r<N;r++) apply(r,c,rnd(V));
        for(int pass=0;pass<4;pass++){ int ch=0; for(int r=FIXC;r<N;r++){ int bv=A[(size_t)r*K+c], bd=0; for(int v=0;v<V;v++){ int d=delta(r,c,v); if(d<bd){bd=d;bv=v;} } if(bd<0){ apply(r,c,bv); ch=1; } } if(!ch) break; }
        if(bestnu<0 || nu<bestnu){ bestnu=nu; for(int r=0;r<N;r++) bestcol[r]=A[(size_t)r*K+c]; }
    }
    for(int r=FIXC;r<N;r++) apply(r,c,bestcol[r]);
}
static uint8_t *snap=NULL; static int snapk=0;
static void take_snapshot(void){ if(!snap) snap=malloc((size_t)N*K); memcpy(snap,A,(size_t)N*K); snapk=KM; }
/* restore the last covered array (first snapk columns) and recount everything for KMnew columns */
static void restore_snapshot(int KMnew){
    for(int64_t i=0;i<nu;i++){ int64_t e=ul[i]; int64_t tp=e%VV, p=e/VV; int a=(int)(p/K), b=(int)(p%K); pos[tri(a,b)*VV+tp]=-1; }
    nu=0;
    for(int r=0;r<N;r++) memcpy(A+(size_t)r*K, snap+(size_t)r*K, snapk);
    KM=0; for(int c=0;c<KMnew;c++) add_column();
}
static void write_out(const char *prefix, int last){
    char fn[600]; if(last) snprintf(fn,sizeof fn,"%s_%d_last.txt",prefix,N); else snprintf(fn,sizeof fn,"%s_%d_%d.txt",prefix,N,KM);
    FILE *f=fopen(fn,"w"); if(!f){perror("open");return;}
    for(int r=0;r<N;r++){ for(int j=0;j<KM;j++) fprintf(f,"%s%d",j?" ":"",A[(size_t)r*K+j]); fputc('\n',f); }
    fclose(f);
}
int main(int argc,char**argv){
    if(argc<7){ fprintf(stderr,"usage: ext2 N K v seed maxseconds outprefix [initfile|-] [k0]\n"); return 2; }
    N=atoi(argv[1]); K=atoi(argv[2]); V=atoi(argv[3]); VV=V*V; unsigned long long seed=strtoull(argv[4],0,10);
    double maxsec=atof(argv[5]); const char *prefix=argv[6]; const char *init=(argc>7 && strcmp(argv[7],"-"))? argv[7]:NULL;
    int k0=(argc>8)? atoi(argv[8]) : 0; if(k0<=1||k0>K) k0=K;
    double sat=getenv("SAT")?atof(getenv("SAT")):0; double sat0=sat, sat1=getenv("SAT1")?atof(getenv("SAT1")):sat; long long sal=getenv("SAL")?atoll(getenv("SAL")):0;
    long long sastag=getenv("SASTAG")?atoll(getenv("SASTAG")):0; int sakick=getenv("SAKICK")?atoi(getenv("SAKICK")):3;
    int ncoltry=getenv("NEWCOLTRY")?atoi(getenv("NEWCOLTRY")):1;
    FIXC=getenv("FIXC")?atoi(getenv("FIXC")):0;
    int tenure=getenv("TENURE")?atoi(getenv("TENURE")):3; long long stag=getenv("STAG")?atoll(getenv("STAG")):200000;
    int savek[64], nsk=0; if(getenv("SAVEK")){ char *s=strdup(getenv("SAVEK")); for(char *p=strtok(s,",");p&&nsk<64;p=strtok(0,",")) savek[nsk++]=atoi(p); }
    rs ^= seed*0x9E3779B97F4A7C15ULL; for(int i=0;i<50;i++) xr();
    if(N>255){fprintf(stderr,"N too big\n");return 2;}
    A=malloc((size_t)N*K); cnt=calloc((size_t)K*K*VV,1); int64_t np=(int64_t)K*(K-1)/2*VV;
    pos=malloc(sizeof(int32_t)*np); ul=malloc(sizeof(int64_t)*np); tabu=calloc((size_t)N*K,sizeof(int64_t));
    if(!A||!cnt||!pos||!ul||!tabu){fprintf(stderr,"alloc fail\n");return 2;}
    memset(pos,-1,sizeof(int32_t)*np);
    for(size_t i=0;i<(size_t)N*K;i++) A[i]=rnd(V);
    int n0=0,k1=0;
    if(init){ FILE *f=fopen(init,"r"); if(!f){perror("init");return 2;}
        /* count columns of first line */
        char line[1<<16]; int mn=99; int r=0; static int buf[1<<15];
        int drop[256]={0}; if(getenv("DROP")){ char *s2=strdup(getenv("DROP")); for(char *p=strtok(s2,",");p;p=strtok(0,",")) { int d=atoi(p); if(d>=0&&d<256) drop[d]=1; } }
        int lineno=-1;
        while(fgets(line,sizeof line,f) && r<N){ int k=0; char *p=line; while(*p){ while(*p==' '||*p=='\t'||*p==',') p++; if(*p=='\n'||!*p) break; buf[k++]=(int)strtol(p,&p,10); }
            if(!k) continue; lineno++; if(lineno<256 && drop[lineno]) continue; if(!k1) k1=k; for(int j=0;j<k && j<K;j++){ A[(size_t)r*K+j]=(uint8_t)buf[j]; if(buf[j]<mn) mn=buf[j]; } r++; }
        fclose(f); n0=r; if(mn==1){ for(int i=0;i<n0;i++) for(int j=0;j<k1&&j<K;j++) A[(size_t)i*K+j]--; }
        fprintf(stderr,"init %s: %d rows, %d columns\n",init,n0,k1);
    }
    for(int r=0;r<FIXC;r++) for(int j=0;j<K;j++) A[(size_t)r*K+j]=(uint8_t)r;
    /* build counts for the first k0 columns */
    KM=0; for(int c=0;c<k0;c++) add_column();
    fprintf(stderr,"N=%d K=%d v=%d k0=%d seed=%llu tenure=%d stag=%lld start uncovered=%lld\n",N,K,V,k0,seed,tenure,stag,(long long)nu);
    int incr=(k0<K); long long restart=getenv("RESTART")?atoll(getenv("RESTART")):0; long long nrestart=0;
    long long colres=getenv("COLRESAMPLE")?atoll(getenv("COLRESAMPLE")):0; long long kit=0;
    double t0=now(); long long it=0, lastimp=0; int64_t best=nu; int bestk=(nu==0)?KM:0;
    int cr[1024], cc[1024], cv[1024], cd[1024];
    while(1){
        if(nu==0){
            int save=(KM==K); for(int i=0;i<nsk;i++) if(savek[i]==KM) save=1;
            if(KM>bestk){ bestk=KM; fprintf(stderr,"covered k=%d at %.1fs iter %lld\n",KM,now()-t0,it); }
            if(restart>0) take_snapshot();
            if(save || KM==K) write_out(prefix,0);
            if(KM<K) write_out(prefix,1);
            if(KM==K){ fprintf(stderr,"SUCCESS N=%d k=%d %.1fs iter %lld\n",N,KM,now()-t0,it); break; }
            /* add a column: random values if beyond init, then greedy descent on it */
            int c=KM; if(c>=k1) for(int r=0;r<N;r++) A[(size_t)r*K+c]= r<FIXC? r : rnd(V);
            for(int r=n0;r<N;r++) if(c<k1) {} /* extra rows keep random values */
            add_column();
            if(c>=k1) newcol(c,ncoltry,0);
            best=nu; lastimp=it; kit=it; continue;
        }
        if((it&1023)==0 && now()-t0>maxsec) break;
        it++;
        int64_t e=ul[rnd((int)nu)]; int tup=(int)(e%VV); int64_t p=e/VV; int a=(int)(p/K), b=(int)(p%K); int x=tup/V, y=tup%V;
        int nc=0;
        for(int r=FIXC;r<N;r++){ const uint8_t *row=A+(size_t)r*K;
            if(row[b]==y && row[a]!=x){ cr[nc]=r; cc[nc]=a; cv[nc]=x; nc++; }
            else if(row[a]==x && row[b]!=y){ cr[nc]=r; cc[nc]=b; cv[nc]=y; nc++; }
        }
        if(nc==0){ int r=FIXC+rnd(N-FIXC); if(rnd(2)) { cr[0]=r; cc[0]=a; cv[0]=x; } else { cr[0]=r; cc[0]=b; cv[0]=y; } nc=1; }
        if(sat>0){ /* Metropolis on a random covering move; cyclic geometric cooling sat -> sat1 over sal iterations */
            if(sal>0 && (it%1024)==0){ double f=(double)(it%sal)/sal; sat=sat0*pow(sat1/sat0,f); }
            int i=rnd(nc); int d=delta(cr[i],cc[i],cv[i]);
            if(d<=0 || (double)(xr()>>11)*(1.0/9007199254740992.0) < exp(-d/sat)) apply(cr[i],cc[i],cv[i]);
            if(nu<best){ best=nu; lastimp=it; }
            else if(restart>0 && incr && snap && KM==snapk+1 && it-kit>restart){ restore_snapshot(KM); newcol(KM-1,ncoltry,1); kit=it; best=nu; lastimp=it; nrestart++;
                if((nrestart%10)==1) fprintf(stderr,"restart %lld at k=%d it=%lld uncovered=%lld\n",nrestart,KM,it,(long long)nu); }
            else if(colres>0 && incr && KM-1>=k1 && KM>bestk && it-kit>colres){ newcol(KM-1,ncoltry,1); kit=it; best=nu; lastimp=it; }
            else if(sastag>0 && it-lastimp>sastag){ for(int q=0;q<sakick;q++){ int r=FIXC+rnd(N-FIXC), c=rnd(KM); apply(r,c,rnd(V)); } lastimp=it; best=nu; }
            if((it%2000000)==0) fprintf(stderr,"it=%lld k=%d uncovered=%lld best=%lld %.0fs\n",it,KM,(long long)nu,(long long)best,now()-t0);
            continue; }
        int bd=1<<30, nb=0, bi=-1;
        for(int i=0;i<nc;i++){ cd[i]=delta(cr[i],cc[i],cv[i]);
            int tb = tabu[(size_t)cr[i]*K+cc[i]] > it && !(nu+cd[i] < best);
            if(tb) continue;
            if(cd[i]<bd){ bd=cd[i]; nb=1; bi=i; } else if(cd[i]==bd){ nb++; if(rnd(nb)==0) bi=i; }
        }
        if(bi<0) bi=rnd(nc);
        apply(cr[bi],cc[bi],cv[bi]); tabu[(size_t)cr[bi]*K+cc[bi]] = it+tenure;
        if(nu<best){ best=nu; lastimp=it; }
        else if(it-lastimp>stag){ /* perturb: a few random cells */
            for(int q=0;q<N/4+1;q++){ int r=FIXC+rnd(N-FIXC), c=rnd(KM); apply(r,c,rnd(V)); }
            lastimp=it; best=nu; }
        if((it%2000000)==0) fprintf(stderr,"it=%lld k=%d uncovered=%lld best=%lld %.0fs\n",it,KM,(long long)nu,(long long)best,now()-t0);
    }
    if(nu>0) { fprintf(stderr,"STOP N=%d reached k=%d (current k=%d uncovered=%lld) %.1fs iter %lld\n",N,bestk,KM,(long long)nu,now()-t0,it); }
    /* in incremental mode, write the largest covered array: rerun not stored; we saved at success points */
    return nu==0?0:1;
}
