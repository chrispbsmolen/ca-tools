/* nck_lite.c - memory-light row elimination for large binary covering arrays (v = 2), for the cases
 * where nck.c's (set, tuple) table does not fit (t = 5, k > 90). Same idea as nck.c, but necessity is
 * recomputed by a full pass over all column t-sets each round (histogram of the rows' tuples per set),
 * and every cell change is checked exactly on the fly with per-column row bitsets before it is applied,
 * so coverage can never break. Our own implementation (2026-10-27).
 * Usage: nck_lite N t k infile outprefix seed maxseconds [kkeep]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#define MAXN 512
#define WN (MAXN/64)
static int N0,N,T,K; static uint8_t *A; static int alive[MAXN]; static int *nec; /* N0 x K */
static uint64_t B[1200][2][WN]; static int NW;
static unsigned long long rs=88172645463325252ULL;
static inline unsigned long long xr(void){ rs^=rs<<7; rs^=rs>>9; return rs; }
static inline int rnd(int n){ return (int)(xr()%(unsigned long long)n); }
static void build_bits(void){ NW=(N0+63)/64; memset(B,0,sizeof(B)); for(int r=0;r<N0;r++) if(alive[r]) for(int c=0;c<K;c++) B[c][A[r*K+c]][r>>6]|=1ULL<<(r&63); }
/* exact: is cell (r,c) flexible now? every t-set through c: r's tuple covered by another row */
static int flexible_now(int r,int c){
    int idx[8]; int m=T-1; for(int i=0;i<m;i++) idx[i]=i;
    while(1){
        int cols[8]; for(int i=0;i<m;i++) cols[i]= idx[i]<c? idx[i] : idx[i]+1;
        uint64_t w[WN]; for(int q=0;q<NW;q++) w[q]=B[c][A[r*K+c]][q];
        for(int i=0;i<m;i++){ int cc=cols[i]; uint8_t s=A[r*K+cc]; for(int q=0;q<NW;q++) w[q]&=B[cc][s][q]; }
        int cnt=0; for(int q=0;q<NW;q++) cnt+=__builtin_popcountll(w[q]); if(cnt<2) return 0;
        int i=m-1; while(i>=0 && idx[i]==K-1-m+i) i--; if(i<0) break; idx[i]++; for(int j=i+1;j<m;j++) idx[j]=idx[j-1]+1;
    }
    return 1;
}
static void set_cell(int r,int c,int val){ B[c][A[r*K+c]][r>>6]&=~(1ULL<<(r&63)); A[r*K+c]=val; B[c][val][r>>6]|=1ULL<<(r&63); }
/* full pass: nec for all cells; collect sets where row r0 is unique (up to maxL) */
static int (*L)[8]; static int nL, maxL=200000;
static long long pass(int r0){
    memset(nec,0,sizeof(int)*N0*K); nL=0; long long unc=0;
    int c[8]; for(int i=0;i<T;i++) c[i]=i; int VT=1<<T;
    static int hist[64]; static int who[64];
    while(1){
        memset(hist,0,sizeof(int)*VT);
        for(int r=0;r<N0;r++) if(alive[r]){ int tup=0; for(int i=0;i<T;i++) tup|=A[r*K+c[i]]<<i; hist[tup]++; who[tup]=r; }
        for(int tup=0;tup<VT;tup++){ if(hist[tup]==1){ int r=who[tup]; for(int i=0;i<T;i++) nec[r*K+c[i]]++; if(r==r0 && nL<maxL){ for(int i=0;i<T;i++) L[nL][i]=c[i]; nL++; } } else if(hist[tup]==0) unc++; }
        int i=T-1; while(i>=0 && c[i]==K-T+i) i--; if(i<0) break; c[i]++; for(int j=i+1;j<T;j++) c[j]=c[j-1]+1;
    }
    return unc;
}
static int necrow(int r){ int s=0; for(int j=0;j<K;j++) if(nec[r*K+j]) s++; return s; }
static void write_out(const char*prefix){ char fn[512]; snprintf(fn,sizeof fn,"%s_%d.txt",prefix,N); FILE*f=fopen(fn,"w"); for(int r=0;r<N0;r++) if(alive[r]){ for(int j=0;j<K;j++) fprintf(f,"%s%d",j?" ":"",A[r*K+j]); fputc('\n',f);} fclose(f); }
int main(int argc,char**argv){
    if(argc<8){ fprintf(stderr,"usage: nck_lite N t k infile outprefix seed maxseconds [kkeep]\n"); return 2; }
    N0=N=atoi(argv[1]); T=atoi(argv[2]); K=atoi(argv[3]); const char*in=argv[4],*prefix=argv[5]; rs^=strtoull(argv[6],0,10)*0x9E3779B97F4A7C15ULL; for(int i=0;i<20;i++) xr();
    double maxsec=atof(argv[7]); int kread=K; if(argc>8) K=atoi(argv[8]);
    if(N0>MAXN||T>6){fprintf(stderr,"too big\n");return 2;}
    A=malloc(N0*K); nec=malloc(sizeof(int)*N0*K); L=malloc(sizeof(int)*8*maxL);
    FILE*f=fopen(in,"r"); for(int r=0;r<N0;r++){ for(int j=0;j<kread;j++){ int x; if(fscanf(f,"%d",&x)!=1){fprintf(stderr,"short\n");return 2;} if(j<K) A[r*K+j]=x; } alive[r]=1; } fclose(f);
    int mn=9; for(int i=0;i<N0*K;i++) if(A[i]<mn) mn=A[i]; if(mn==1) for(int i=0;i<N0*K;i++) A[i]--;
    build_bits();
    time_t start=time(NULL); int r0=-1; int round=0;
    while(difftime(time(NULL),start)<maxsec){
        round++;
        long long unc=pass(r0);
        if(unc){ fprintf(stderr,"BUG: %lld uncovered\n",unc); return 1; }
        int best=K+1, cand[MAXN], nc=0;
        for(int r=0;r<N0;r++) if(alive[r]){ int s=necrow(r); if(s<best){best=s;nc=0;} if(s==best) cand[nc++]=r; }
        fprintf(stderr,"round %d: N=%d min necessary cells=%d (rows with that: %d), r0=%d unique sets=%d, %.0fs\n",round,N,best,nc,r0,nL,difftime(time(NULL),start));
        if(best==0){ int r=cand[rnd(nc)]; alive[r]=0; N--; build_bits(); write_out(prefix); fprintf(stderr,"row %d deleted -> N=%d\n",r,N); r0=-1; continue; }
        if(r0<0 || !alive[r0] || necrow(r0)>best+2){ r0=cand[rnd(nc)]; continue; }
        /* handover round for r0: for each unique set, find another row that can take the tuple */
        int done=0, tried=0;
        for(int q=0;q<nL;q++){
            int *c=L[q]; /* is r0 still unique here? check exactly */
            uint64_t w[WN]; for(int x=0;x<NW;x++) w[x]=~0ULL; for(int i=0;i<T;i++){ int cc=c[i]; for(int x=0;x<NW;x++) w[x]&=B[cc][A[r0*K+cc]][x]; }
            int cnt=0; for(int x=0;x<NW;x++) cnt+=__builtin_popcountll(w[x]); if(cnt>=2) continue;
            tried++;
            int bestr=-1,bestch=99;
            for(int s=0;s<N0;s++){ int r=(s+rnd(N0))%N0; if(!alive[r]||r==r0) continue; int ch=0,ok=1; for(int i=0;i<T;i++){ if(A[r*K+c[i]]!=A[r0*K+c[i]]){ if(nec[r*K+c[i]]){ok=0;break;} ch++; } } if(ok&&ch<bestch){bestch=ch;bestr=r; if(ch<=1) break;} }
            if(bestr<0) continue;
            /* exact check of each cell to change, then apply */
            int ok=1; int chc[8], nch=0; for(int i=0;i<T;i++) if(A[bestr*K+c[i]]!=A[r0*K+c[i]]){ if(!flexible_now(bestr,c[i])){ok=0;break;} chc[nch++]=c[i]; set_cell(bestr,c[i],A[r0*K+c[i]]); nec[bestr*K+c[i]]=1; }
            if(!ok){ /* revert partial */ for(int i=0;i<nch;i++){ set_cell(bestr,chc[i],1-A[bestr*K+chc[i]]); } continue; }
            done++;
            if(difftime(time(NULL),start)>=maxsec) break;
        }
        fprintf(stderr,"  handovers: %d of %d unique sets still unique; done %d\n",tried,nL,done);
        if(done==0){ /* shake: flip a few exactly-flexible cells in random rows */ int fl=0; for(int w2=0;w2<200;w2++){ int r=rnd(N0); if(!alive[r]||r==r0) continue; int j=rnd(K); if(nec[r*K+j]==0 && flexible_now(r,j)){ set_cell(r,j,1-A[r*K+j]); fl++; } } fprintf(stderr,"  shake %d\n",fl); if(fl==0) r0=-1; }
    }
    fprintf(stderr,"done N=%d\n",N); return 0;
}
