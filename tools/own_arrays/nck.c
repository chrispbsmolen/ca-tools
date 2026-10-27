/* nck.c - post-optimization of a covering array by row elimination, in the spirit of
 * Nayeri, Colbourn and Konjevod (2013), "Randomized post-optimization of covering arrays".
 * Our own implementation (2026-10-27), no external ingredient.
 *
 * Usage: nck N t k v infile outprefix seed maxseconds [kkeep]
 * Reads an N x k array (first kkeep columns used if given), builds the coverage counts of every
 * (column t-set, tuple) with the XOR of the ids of the covering rows, so that a tuple covered once
 * knows its unique row. nec[r][c] = number of tuples uniquely covered by row r through column c.
 * A cell with nec = 0 is flexible: it can be changed without losing coverage. The loop picks the
 * row with fewest necessary cells, tries to hand each of its unique tuples to another row by
 * writing the tuple into flexible cells of that row, and deletes the row when nothing depends on
 * it. Random walks on flexible cells when stuck. Every improvement is written to
 * outprefix_N.txt (canonical form: 0-based symbols, space separated).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

static int N0, N, T, K, V, VT;
static int *A; static int *alive;
static long long nsets;
static uint16_t *cnt, *xr_;
static int *nec;            /* N0 x K */
static long long binomtab[1200][8];
static int pw[8];
static long long uncovered=0;

static unsigned long long rs = 88172645463325252ULL;
static inline unsigned long long xr(void){ rs ^= rs<<7; rs ^= rs>>9; return rs; }
static inline int rnd(int n){ return (int)(xr() % (unsigned long long)n); }

static void init_binom(void){ for(int n=0;n<1200;n++) for(int r=0;r<8;r++){ if(r==0) binomtab[n][r]=1; else if(n==0) binomtab[n][r]=0; else binomtab[n][r]=binomtab[n-1][r-1]+binomtab[n-1][r]; } }
static inline long long rank_of(const int *c){ long long s=0; for(int i=0;i<T;i++) s+=binomtab[c[i]][i+1]; return s; }
static inline int tup_of(int r,const int *c){ int t=0; for(int i=0;i<T;i++) t=t*V+A[r*K+c[i]]; return t; }

/* enumeration of the (T-1)-subsets of the other columns: idx[] are indices into
   {0..K-2}, mapped to columns by skipping col */
static inline void sorted_insert(const int *idx,int col,int *c){ int ii=0, placed=0; for(int i=0;i<T;i++){ int oc = (ii<T-1) ? (idx[ii]<col? idx[ii] : idx[ii]+1) : -1; if(!placed && (ii==T-1 || oc>col)){ c[i]=col; placed=1; } else { c[i]=oc; ii++; } } }
static inline void first_oth(int *idx,int col){ (void)col; for(int i=0;i<T-1;i++) idx[i]=i; }
static inline int next_oth(int *idx,int col){ (void)col; int m=T-1, n=K-1; int i=m-1; while(i>=0 && idx[i]==n-m+i) i--; if(i<0) return 0; idx[i]++; for(int j=i+1;j<m;j++) idx[j]=idx[j-1]+1; return 1; }

static void nec_add(int r,const int *c,int d){ for(int i=0;i<T;i++) nec[r*K+c[i]]+=d; }

/* remove row r's contribution on set c (rank R): */
static inline void remove_from(long long R,int r,const int *c){
    int tup=tup_of(r,c); long long idx=R*VT+tup;
    uint16_t cn=cnt[idx];
    if(cn==1){ nec_add(r,c,-1); uncovered++; }
    cnt[idx]=cn-1; xr_[idx]^=(uint16_t)r;
    if(cn==2){ int r2=xr_[idx]; nec_add(r2,c,+1); }
}
static inline void add_to(long long R,int r,const int *c){
    int tup=tup_of(r,c); long long idx=R*VT+tup;
    uint16_t cn=cnt[idx];
    if(cn==0){ uncovered--; nec_add(r,c,+1); }
    if(cn==1){ int r1=xr_[idx]; nec_add(r1,c,-1); }
    cnt[idx]=cn+1; xr_[idx]^=(uint16_t)r;
}

static void set_cell2(int r,int col,int val){
    int old=A[r*K+col]; if(old==val) return;
    int oth[8], c[8]; first_oth(oth,col);
    int more=1;
    while(more){
        sorted_insert(oth,col,c); long long R=rank_of(c);
        A[r*K+col]=old; remove_from(R,r,c);
        A[r*K+col]=val; add_to(R,r,c);
        more=next_oth(oth,col);
    }
    A[r*K+col]=val;
}
static void delete_row(int r){
    /* iterate over all T-sets */
    int c[8]; for(int i=0;i<T;i++) c[i]=i;
    while(1){
        long long R=rank_of(c); remove_from(R,r,c);
        int i=T-1; while(i>=0 && c[i]==K-T+i) i--; if(i<0) break; c[i]++; for(int j=i+1;j<T;j++) c[j]=c[j-1]+1;
    }
    alive[r]=0; N--;
}
static int necrow(int r){ int s=0; for(int j=0;j<K;j++) if(nec[r*K+j]>0) s++; return s; }

static void write_out(const char *prefix){
    char fn[512]; snprintf(fn,sizeof fn,"%s_%d.txt",prefix,N);
    FILE *f=fopen(fn,"w"); if(!f){perror("open");return;}
    for(int r=0;r<N0;r++) if(alive[r]){ for(int j=0;j<K;j++) fprintf(f,"%s%d",j?" ":"",A[r*K+j]); fputc('\n',f); }
    fclose(f);
}

int main(int argc,char**argv){
    if(argc<9){ fprintf(stderr,"usage: nck N t k v infile outprefix seed maxseconds [kkeep]\n"); return 2; }
    N0=N=atoi(argv[1]); T=atoi(argv[2]); K=atoi(argv[3]); V=atoi(argv[4]);
    const char *infile=argv[5], *prefix=argv[6]; rs^=strtoull(argv[7],0,10)*0x9E3779B97F4A7C15ULL; for(int i=0;i<20;i++) xr();
    double maxsec=atof(argv[8]); int kread=K; if(argc>9){ kread=K; K=atoi(argv[9]); } int shake = getenv("SHAKE")? atoi(getenv("SHAKE")) : 10;
    if(T>7||K>=1200){fprintf(stderr,"too big\n");return 2;}
    init_binom();
    A=malloc(sizeof(int)*N0*K); alive=malloc(sizeof(int)*N0); nec=calloc((size_t)N0*K,sizeof(int));
    FILE *f=fopen(infile,"r"); if(!f){perror("in");return 2;}
    for(int r=0;r<N0;r++){ for(int j=0;j<kread;j++){ int x; if(fscanf(f,"%d",&x)!=1){fprintf(stderr,"short input\n");return 2;} if(j<K) A[r*K+j]=x; } alive[r]=1; }
    fclose(f);
    int mn=V; for(int i=0;i<N0*K;i++) if(A[i]<mn) mn=A[i]; if(mn==1) for(int i=0;i<N0*K;i++) A[i]--;
    nsets=binomtab[K][T]; VT=1; for(int i=0;i<T;i++) VT*=V; pw[T-1]=1; for(int i=T-2;i>=0;i--) pw[i]=pw[i+1]*V;
    size_t tot=(size_t)nsets*VT;
    cnt=calloc(tot,sizeof(uint16_t)); xr_=calloc(tot,sizeof(uint16_t));
    if(!cnt||!xr_){fprintf(stderr,"alloc fail (%zu entries)\n",tot);return 2;}
    uncovered=tot;
    fprintf(stderr,"N=%d t=%d k=%d v=%d sets=%lld entries=%zu\n",N,T,K,V,nsets,tot);
    { int c[8]; for(int i=0;i<T;i++) c[i]=i;
      while(1){ long long R=rank_of(c); for(int r=0;r<N0;r++) add_to(R,r,c);
        int i=T-1; while(i>=0 && c[i]==K-T+i) i--; if(i<0) break; c[i]++; for(int j=i+1;j<T;j++) c[j]=c[j-1]+1; } }
    fprintf(stderr,"uncovered=%lld (must be 0)\n",uncovered);
    if(uncovered){ fprintf(stderr,"input is not a covering array\n"); return 1; }
    /* report flexibility */
    int nflex=0; for(int r=0;r<N0;r++) for(int j=0;j<K;j++) if(nec[r*K+j]==0) nflex++;
    fprintf(stderr,"flexible cells: %d of %d\n",nflex,N0*K);
    clock_t start=clock(); long long iter=0; int target=-1; int stuck=0;
    while((double)(clock()-start)/CLOCKS_PER_SEC < maxsec){
        iter++;
        /* pick target row: fewest necessary cells (random tie-break), re-pick occasionally */
        if(target<0 || !alive[target] || (iter%50==0)){
            int best=K+1; int cand[4096]; int nc=0;
            for(int r=0;r<N0;r++) if(alive[r]){ int s=necrow(r); if(s<best){best=s;nc=0;} if(s==best && nc<4096) cand[nc++]=r; }
            target=cand[rnd(nc)];
        }
        int r0=target;
        if(necrow(r0)==0){ delete_row(r0); write_out(prefix); fprintf(stderr,"row deleted -> N=%d (iter %lld, %.0fs)\n",N,iter,(double)(clock()-start)/CLOCKS_PER_SEC); target=-1; stuck=0; continue; }
        /* try to hand over one uniquely covered tuple of r0 */
        int progressed=0;
        int cols[1200]; int ncl=0; for(int j=0;j<K;j++) if(nec[r0*K+j]>0) cols[ncl++]=j;
        int col=cols[rnd(ncl)];
        int oth[8], c[8]; first_oth(oth,col); int more=1;
        while(more){
            sorted_insert(oth,col,c); long long R=rank_of(c); int tup=tup_of(r0,c);
            if(cnt[R*VT+tup]==1){
                /* find a row that can take this tuple with fewest changes among flexible cells */
                int bestr=-1, bestch=99; int tries=0;
                for(int q=0;q<N0 && tries<N0;q++){ int r=(q+rnd(N0))%N0; if(!alive[r]||r==r0) continue; tries++;
                    int ch=0, ok=1; for(int i=0;i<T;i++){ int want=(tup/pw[i])%V; if(A[r*K+c[i]]!=want){ if(nec[r*K+c[i]]>0){ok=0;break;} ch++; } }
                    if(ok && ch<bestch){ bestch=ch; bestr=r; if(ch<=1) break; }
                }
                if(bestr>=0){ for(int i=0;i<T;i++){ int want=(tup/pw[i])%V; if(A[bestr*K+c[i]]!=want) set_cell2(bestr,c[i],want); } progressed=1; break; }
            }
            more=next_oth(oth,col);
        }
        if(!progressed){
            stuck++;
            /* random walk: flip a random flexible cell in a random row other than r0 */
            for(int w=0;w<3;w++){ int r=rnd(N0); if(!alive[r]||r==r0) continue; int j=rnd(K); if(nec[r*K+j]==0){ int val=rnd(V-1); if(val>=A[r*K+j]) val++; set_cell2(r,j,val); } }
            if(stuck%60==0){ /* shake: randomize a fraction of the flexible cells, in random order */
                int nf=0; for(int r=0;r<N0;r++) if(alive[r]) for(int j=0;j<K;j++) if(nec[r*K+j]==0 && rnd(100)<shake){ int val=rnd(V-1); if(val>=A[r*K+j]) val++; set_cell2(r,j,val); nf++; }
                (void)nf; }
            if(stuck>200){ target=-1; stuck=0; }
        }
    }
    fprintf(stderr,"done: N=%d after %lld iterations\n",N,iter);
    return 0;
}
