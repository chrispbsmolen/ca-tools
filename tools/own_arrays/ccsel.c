/* ccsel.c - binary CAs from doubled Paley matrices by row deletion and column choice.
 * Written for ca-tools, 2026-10-27.
 *
 * Paley (1933): for a prime q = 3 mod 4 let P[r][c] = 1 if c - r is a nonzero square mod q,
 * else 0 (computed here). M = the q rows of P plus an all-ones row (option -n drops it).
 * For a set C of columns the array {m|C, complement(m)|C : m in M'} (M' = M minus deleted rows)
 * is a CA of strength t iff every t-set S of C is "CC-covered": for every x, x or its complement
 * is shown by some m in M' on S. With -x the doubling column of CAs:::Double is added too
 * (rows (0|m) and (1|complement m)); then every (t-1)-set of C must also be covered by M' in the
 * ordinary sense. The bad sets (all t-sets, and (t-1)-sets with -x) are enumerated by brute
 * force; rows are deleted greedily (fewest new bad sets); simulated annealing over k-subsets of
 * the q columns then looks for a subset containing no bad set; leftover bad sets are repaired,
 * if possible, by single cell changes with an exact check. N = 2|M'|.
 *
 * usage: ccsel q t k ndel seed maxsec outfile [-x] [-n]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <time.h>
#define MQ 128
static int q, t, K, nM; static uint8_t Mv[MQ+1][MQ]; static int alive[MQ+1];
static uint64_t rs=88172645463325252ULL;
static inline uint64_t xr(void){ rs^=rs<<13; rs^=rs>>7; rs^=rs<<17; return rs; }
static double now(void){ struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts); return ts.tv_sec+1e-9*ts.tv_nsec; }
typedef struct { uint8_t c[8]; uint8_t sz; } edge_t;
static edge_t *E; static long ne, cape;
static void addedge(const int *S,int sz){ if(ne>=cape){ cape=cape*2+4096; E=realloc(E,sizeof(edge_t)*cape);} for(int i=0;i<sz;i++) E[ne].c[i]=S[i]; E[ne].sz=sz; ne++; }
/* enumerate sets of size s; for each, CC (cc=1) or plain (cc=0) coverage by alive rows; mode 0: collect bad sets; mode 1: count, per row, sets where it is the only coverer of some class */
static long scan(int s,int cc,int mode,long *uniq){
    int S[8]; for(int i=0;i<s;i++) S[i]=i; long nbad=0; int ncls= cc? 1<<(s-1) : 1<<s;
    int cntc[128], who[128];
    while(1){
        memset(cntc,0,sizeof(int)*ncls);
        for(int r=0;r<nM;r++){ if(!alive[r]) continue; int x=0; for(int i=0;i<s;i++) x|=Mv[r][S[i]]<<i; if(cc && (x>>(s-1))&1) x^=(1<<s)-1; cntc[x]++; who[x]=r; }
        int bad=0; for(int x=0;x<ncls;x++){ if(cntc[x]==0) bad=1; else if(cntc[x]==1 && mode==1) uniq[who[x]]++; }
        if(bad){ nbad++; if(mode==0) addedge(S,s); }
        int i=s-1; while(i>=0 && S[i]==K-s+i) i--; if(i<0) break; S[i]++; for(int j=i+1;j<s;j++) S[j]=S[j-1]+1;
    }
    return nbad;
}
int main(int argc,char**argv){
    if(argc<8){ fprintf(stderr,"usage: ccsel q t k ndel seed maxsec outfile [-x] [-n]\n"); return 2; }
    q=atoi(argv[1]); t=atoi(argv[2]); int k=atoi(argv[3]), ndel=atoi(argv[4]); rs^=strtoull(argv[5],0,10)*0x9E3779B97F4A7C15ULL; for(int i=0;i<20;i++) xr(); double maxsec=atof(argv[6]);
    int dbl=0, noones=0; for(int a=8;a<argc;a++){ if(!strcmp(argv[a],"-x")) dbl=1; else if(!strcmp(argv[a],"-n")) noones=1; }
    if(q>MQ||t>7||t<2){ fprintf(stderr,"bad params\n"); return 2; }
    K=q; int sq[MQ]={0}; for(int a=1;a<q;a++) sq[(a*a)%q]=1;
    for(int r=0;r<q;r++) for(int c=0;c<q;c++){ int d=((c-r)%q+q)%q; Mv[r][c]= (d!=0 && sq[d]); }
    nM=q; if(!noones){ for(int c=0;c<q;c++) Mv[q][c]=1; nM=q+1; }
    for(int r=0;r<nM;r++) alive[r]=1;
    double t0=now();
    printf("ccsel q=%d t=%d k=%d (+doubling column: %d) delete %d of %d M-rows, N = %d\n",q,t,k,dbl,ndel,nM,2*(nM-ndel)); fflush(stdout);
    long *uq=calloc(nM,sizeof(long));
    for(int dd=0; dd<ndel; dd++){
        memset(uq,0,sizeof(long)*nM); scan(t,1,1,uq); if(dbl) scan(t-1,0,1,uq);
        int br=-1; for(int r=0;r<nM;r++) if(alive[r] && (br<0 || uq[r]<uq[br])) br=r;
        alive[br]=0; printf("  delete M-row %d (it alone covers a class on %ld sets) (%.0fs)\n",br,uq[br],now()-t0); fflush(stdout);
    }
    ne=0; long b1=scan(t,1,0,0), b2= dbl? scan(t-1,0,0,0) : 0;
    printf("bad sets: %ld of size %d, %ld of size %d (%.0fs)\n",b1,t,b2,t-1,now()-t0); fflush(stdout);
    if(k>K){ fprintf(stderr,"k > q\n"); return 2; }
    /* incidence */
    long *deg=calloc(K,sizeof(long)); for(long e=0;e<ne;e++) for(int j=0;j<E[e].sz;j++) deg[E[e].c[j]]++;
    long **inc=malloc(sizeof(long*)*K); long *fill=calloc(K,sizeof(long)); for(int c=0;c<K;c++) inc[c]=malloc(sizeof(long)*(deg[c]+1));
    for(long e=0;e<ne;e++) for(int j=0;j<E[e].sz;j++){ int c=E[e].c[j]; inc[c][fill[c]++]=e; }
    int *in=calloc(K,sizeof(int)), *lst=malloc(sizeof(int)*K); uint8_t *cnt=calloc(ne+1,1), *mark=calloc(ne+1,1);
    for(int c=0;c<K;c++) lst[c]=c; for(int c=K-1;c>0;c--){ int j=xr()%(c+1), y=lst[c]; lst[c]=lst[j]; lst[j]=y; }
    for(int i=0;i<k;i++) in[lst[i]]=1;
    long cost=0; for(long e=0;e<ne;e++){ int s=0; for(int j=0;j<E[e].sz;j++) s+=in[E[e].c[j]]; cnt[e]=s; if(s==E[e].sz) cost++; }
    long best=cost; int *bestin=malloc(sizeof(int)*K); memcpy(bestin,in,sizeof(int)*K); double T=2.0; long it=0;
    printf("SA start cost %ld\n",cost); fflush(stdout);
    while(cost>0 && now()-t0<maxsec && k<K){
        it++; int iu=xr()%k, iv=k+xr()%(K-k); int u=lst[iu], v=lst[iv];
        long dl=0; for(long a=0;a<deg[u];a++){ long e=inc[u][a]; mark[e]=1; if(cnt[e]==E[e].sz) dl--; }
        for(long a=0;a<deg[v];a++){ long e=inc[v][a]; if(!mark[e] && cnt[e]==E[e].sz-1) dl++; }
        for(long a=0;a<deg[u];a++) mark[inc[u][a]]=0;
        if(dl<=0 || (xr()>>11)*(1.0/9007199254740992.0) < exp(-dl/T)){
            for(long a=0;a<deg[u];a++) cnt[inc[u][a]]--; for(long a=0;a<deg[v];a++) cnt[inc[v][a]]++;
            in[u]=0; in[v]=1; lst[iu]=v; lst[iv]=u; cost+=dl; if(cost<best){ best=cost; memcpy(bestin,in,sizeof(int)*K);} }
        if((it&0xfffff)==0){ T*=0.97; if(T<0.05) T=1.0; }
        if((it&0xffffff)==0){ printf("  it=%ld T=%.3f cost=%ld best=%ld (%.0fs)\n",it,T,cost,best,now()-t0); fflush(stdout); }
    }
    printf("column SA: best %ld bad sets inside (%.0fs)\n",best,now()-t0); fflush(stdout);
    memcpy(in,bestin,sizeof(int)*K);
    /* final array */
    int ch[MQ], nc=0; for(int c=0;c<K;c++) if(in[c]) ch[nc++]=c;
    int kk=nc+dbl; static uint8_t F[2*MQ+4][MQ+1]; int NF=0;
    for(int r=0;r<nM;r++){ if(!alive[r]) continue; int j0=0; if(dbl){ F[NF][0]=0; F[NF+1][0]=1; j0=1; } for(int j=0;j<nc;j++){ F[NF][j0+j]=Mv[r][ch[j]]; F[NF+1][j0+j]=1-Mv[r][ch[j]]; } NF+=2; }
    /* repair loop: find uncovered (set, tuple) of the final array among t-sets (brute force, small k) and fix by single flips */
    int nfix=0;
    for(int round=0; round<200; round++){
        /* find first uncovered */
        int S[8]; for(int i=0;i<t;i++) S[i]=i; int found=0, xs=0;
        while(!found){ static uint8_t seen[256]; memset(seen,0,1<<t); for(int r=0;r<NF;r++){ int x=0; for(int i=0;i<t;i++) x|=F[r][S[i]]<<i; seen[x]=1; }
            for(int x=0;x<(1<<t);x++) if(!seen[x]){ found=1; xs=x; break; } if(found) break;
            int i=t-1; while(i>=0 && S[i]==kk-t+i) i--; if(i<0) break; S[i]++; for(int j=i+1;j<t;j++) S[j]=S[j-1]+1; }
        if(!found) break;
        int fixed=0;
        for(int r=0;r<NF && !fixed;r++){ int diff=0, dj=-1; for(int i=0;i<t;i++) if(F[r][S[i]]!=((xs>>i)&1)){ diff++; dj=S[i]; } if(diff!=1) continue;
            /* exact check: every t-set through dj keeps row r's old tuple covered elsewhere */
            int ok=1; int U[8]; int m=t-1; for(int i=0;i<m;i++) U[i]=i;
            int oth[MQ+1], no=0; for(int j=0;j<kk;j++) if(j!=dj) oth[no++]=j;
            while(ok){ int cs[8]; cs[0]=dj; for(int i=0;i<m;i++) cs[i+1]=oth[U[i]];
                int cov=0; for(int r2=0;r2<NF && !cov;r2++){ if(r2==r) continue; int eq=1; for(int i=0;i<t;i++) if(F[r2][cs[i]]!=F[r][cs[i]]){ eq=0; break; } if(eq) cov=1; }
                if(!cov){ ok=0; break; }
                int i=m-1; while(i>=0 && U[i]==no-m+i) i--; if(i<0) break; U[i]++; for(int j=i+1;j<m;j++) U[j]=U[j-1]+1; }
            if(ok){ F[r][dj]^=1; fixed=1; nfix++; }
        }
        if(!fixed){ printf("FAILED: an uncovered tuple could not be repaired by one cell (%d repairs done) (%.0fs)\n",nfix,now()-t0); return 1; }
    }
    { /* final full check */ int S[8]; for(int i=0;i<t;i++) S[i]=i; long unc=0;
      while(1){ static uint8_t seen[256]; memset(seen,0,1<<t); for(int r=0;r<NF;r++){ int x=0; for(int i=0;i<t;i++) x|=F[r][S[i]]<<i; seen[x]=1; } for(int x=0;x<(1<<t);x++) if(!seen[x]) unc++;
        int i=t-1; while(i>=0 && S[i]==kk-t+i) i--; if(i<0) break; S[i]++; for(int j=i+1;j<t;j++) S[j]=S[j-1]+1; }
      if(unc){ printf("FAILED: %ld uncovered pairs remain\n",unc); return 1; } }
    FILE *o=fopen(argv[7],"w"); for(int r=0;r<NF;r++){ for(int j=0;j<kk;j++) fprintf(o,j?" %d":"%d",F[r][j]); fputc('\n',o);} fclose(o);
    printf("WROTE %s: %d rows x %d columns, %d cells changed; Paley columns:",argv[7],NF,kk,nfix); for(int j=0;j<nc;j++) printf(" %d",ch[j]); printf(" (%.0fs)\n",now()-t0);
    return 0;
}
