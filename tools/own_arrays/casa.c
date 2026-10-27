/* casa.c - simulated annealing for covering arrays CA(N; t, k, v).
 *
 * Usage: casa N t k v seed maxseconds [T0] [alpha] [outfile] [initfile]
 * Cost = number of uncovered (column t-set, tuple) pairs. Moves: single-cell change, or
 * "repair" move that picks an uncovered tuple and a random row and writes the tuple into
 * that row (TJ-RT style neighbourhood, our own implementation). Metropolis acceptance with
 * geometric cooling and reheating. Prints the array to outfile when cost reaches 0.
 * Written for this project (2026-10-27); no external ingredient.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

static int N, T, K, V;
static int *A;              /* N x K */
static int nsets;           /* C(K,T) */
static int VT;              /* V^T */
static int *cnt;            /* nsets x VT */
static int **colsets;       /* per column: list of set indices containing it */
static int **colpos;        /* per column: position of column within that set */
static int **setcols;       /* per set: its T columns */
static int ncs;             /* C(K-1,T-1) */
static int cost;
static int *unc;            /* list of uncovered (set*VT+tuple) */
static int *uncpos;         /* position in unc or -1 */
static int nunc;
static int pw[16];

static unsigned long long rng_s = 88172645463325252ULL;
static inline unsigned long long xr(void){ rng_s ^= rng_s<<7; rng_s ^= rng_s>>9; return rng_s; }
static inline int rnd(int n){ return (int)(xr() % (unsigned long long)n); }
static inline double rndu(void){ return (xr()>>11) * (1.0/9007199254740992.0); }

static long long binom(int n,int r){ if(r<0||r>n) return 0; long long b=1; for(int i=1;i<=r;i++) b=b*(n-r+i)/i; return b; }

static void unc_add(int key){ if(uncpos[key]<0){ uncpos[key]=nunc; unc[nunc++]=key; } }
static void unc_del(int key){ int p=uncpos[key]; if(p>=0){ int last=unc[--nunc]; unc[p]=last; uncpos[last]=p; uncpos[key]=-1; } }

static int tuple_of(int s,int r){ int *c=setcols[s]; int t=0; for(int i=0;i<T;i++) t=t*V+A[r*K+c[i]]; return t; }

static void build_sets(void){
    nsets=(int)binom(K,T); VT=1; for(int i=0;i<T;i++) VT*=V;
    pw[T-1]=1; for(int i=T-2;i>=0;i--) pw[i]=pw[i+1]*V;
    setcols=malloc(sizeof(int*)*nsets);
    int *c=malloc(sizeof(int)*T); for(int i=0;i<T;i++) c[i]=i;
    ncs=(int)binom(K-1,T-1);
    colsets=malloc(sizeof(int*)*K); colpos=malloc(sizeof(int*)*K);
    int *fill=calloc(K,sizeof(int));
    for(int j=0;j<K;j++){ colsets[j]=malloc(sizeof(int)*ncs); colpos[j]=malloc(sizeof(int)*ncs); }
    int s=0;
    while(1){
        setcols[s]=malloc(sizeof(int)*T);
        for(int i=0;i<T;i++){ setcols[s][i]=c[i]; colsets[c[i]][fill[c[i]]]=s; colpos[c[i]][fill[c[i]]]=i; fill[c[i]]++; }
        s++;
        int i=T-1; while(i>=0 && c[i]==K-T+i) i--; if(i<0) break; c[i]++; for(int j=i+1;j<T;j++) c[j]=c[j-1]+1;
    }
    free(c); free(fill);
}

static void full_count(void){
    memset(cnt,0,sizeof(int)*nsets*VT); nunc=0;
    for(int i=0;i<nsets*VT;i++) uncpos[i]=-1;
    for(int s=0;s<nsets;s++) for(int r=0;r<N;r++) cnt[s*VT+tuple_of(s,r)]++;
    cost=0;
    for(int i=0;i<nsets*VT;i++) if(cnt[i]==0){ cost++; unc_add(i); }
}

/* delta of changing A[r][col] to val, without applying */
static int delta_cell(int r,int col,int val){
    int old=A[r*K+col]; if(old==val) return 0;
    int d=0; int *ss=colsets[col], *pp=colpos[col];
    for(int i=0;i<ncs;i++){
        int s=ss[i]; int tup=tuple_of(s,r); int ntup=tup+(val-old)*pw[pp[i]];
        if(cnt[s*VT+tup]==1) d++;
        if(cnt[s*VT+ntup]==0) d--;
    }
    return d;
}
static void apply_cell(int r,int col,int val){
    int old=A[r*K+col]; if(old==val) return;
    int *ss=colsets[col], *pp=colpos[col];
    for(int i=0;i<ncs;i++){
        int s=ss[i]; int tup=tuple_of(s,r); int ntup=tup+(val-old)*pw[pp[i]];
        if(--cnt[s*VT+tup]==0){ cost++; unc_add(s*VT+tup); }
        if(cnt[s*VT+ntup]++==0){ cost--; unc_del(s*VT+ntup); }
    }
    A[r*K+col]=val;
}

static void write_array(const char *fn){
    FILE *f=fopen(fn,"w"); if(!f){perror("open"); return;}
    for(int r=0;r<N;r++){ for(int j=0;j<K;j++) fprintf(f,"%s%d",j?" ":"",A[r*K+j]); fputc('\n',f); }
    fclose(f);
}

int main(int argc,char**argv){
    if(argc<7){ fprintf(stderr,"usage: casa N t k v seed maxseconds [T0] [alpha] [outfile] [initfile]\n"); return 2; }
    N=atoi(argv[1]); T=atoi(argv[2]); K=atoi(argv[3]); V=atoi(argv[4]);
    unsigned long long seed=strtoull(argv[5],0,10); double maxsec=atof(argv[6]);
    double T0 = argc>7? atof(argv[7]) : 1.0; double alpha = argc>8? atof(argv[8]) : 0.999; double tmin = getenv("TMIN")? atof(getenv("TMIN")) : 0.05;
    const char *outfile = argc>9? argv[9] : "casa_out.txt"; const char *initfile = argc>10? argv[10] : NULL;
    rng_s ^= seed*0x9E3779B97F4A7C15ULL; for(int i=0;i<20;i++) xr();
    A=malloc(sizeof(int)*N*K);
    build_sets();
    cnt=malloc(sizeof(int)*nsets*VT); unc=malloc(sizeof(int)*nsets*VT); uncpos=malloc(sizeof(int)*nsets*VT);
    if(initfile){ FILE*f=fopen(initfile,"r"); if(!f){perror("init");return 2;} for(int i=0;i<N*K;i++) if(fscanf(f,"%d",&A[i])!=1){fprintf(stderr,"short init\n");return 2;} fclose(f); }
    else for(int i=0;i<N*K;i++) A[i]=rnd(V);
    full_count();
    int best=cost; clock_t start=clock(); double temp=T0; long long it=0, lastimp=0;
    long long plateau = 2000LL*N*K; if(plateau<200000) plateau=200000;
    fprintf(stderr,"N=%d t=%d k=%d v=%d sets=%d init cost=%d\n",N,T,K,V,nsets,cost);
    while(cost>0){
        it++;
        if((it&0xfff)==0){
            double el=(double)(clock()-start)/CLOCKS_PER_SEC;
            if(el>maxsec){ fprintf(stderr,"timeout best=%d cost=%d it=%lld\n",best,cost,it); return 1; }
            temp*=alpha; if(temp<tmin) temp=tmin;
            if(it-lastimp>plateau){ temp=T0; lastimp=it; }
        }
        if(nunc>0 && (xr()&3)==0){
            /* repair move: pick uncovered tuple, random row, write tuple */
            int key=unc[rnd(nunc)]; int s=key/VT, tup=key%VT; int r=rnd(N);
            int oldv[16]; int newv[16]; int *c=setcols[s]; int tt=tup;
            for(int i=T-1;i>=0;i--){ newv[i]=tt%V; tt/=V; }
            int d=0; for(int i=0;i<T;i++){ oldv[i]=A[r*K+c[i]]; if(oldv[i]!=newv[i]){ d+=delta_cell(r,c[i],newv[i]); apply_cell(r,c[i],newv[i]); } }
            /* d is the exact delta: cost already updated */
            if(d>0 && rndu()>=exp(-d/temp)){ for(int i=T-1;i>=0;i--) if(oldv[i]!=newv[i]) apply_cell(r,c[i],oldv[i]); }
        } else {
            int r=rnd(N), col=rnd(K), val=rnd(V-1); if(val>=A[r*K+col]) val++;
            int d=delta_cell(r,col,val);
            if(d<=0 || rndu()<exp(-d/temp)) apply_cell(r,col,val);
        }
        if(cost<best){ best=cost; lastimp=it; }
    }
    fprintf(stderr,"found cost 0 at it=%lld, %.1fs\n",it,(double)(clock()-start)/CLOCKS_PER_SEC);
    write_array(outfile);
    return 0;
}
