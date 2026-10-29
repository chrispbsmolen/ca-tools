/* pal6.c - CA(2(p-1); 6, k, 2) from the doubled Paley array CAs:::Double(rbind(1, paley_mat(p)))
 * (a CA(2(p+1); 6, p+1, 2) for p = 359 per CAs's PALEYcat) by deleting two complementary pairs of
 * rows and choosing k of the Paley columns. Written for ca-tools, 2026-10-27.
 *
 * Let M = {P_0..P_{p-1}} plus the all-ones row (index p), P circulant: P_r[c] = f(c - r).
 * Without the doubling column, the doubled array restricted to a column set C has rows m|C and
 * its complement for every m in M; it covers every 6-tuple on S iff for every pattern x some
 * m in M shows x or its complement on S. Deleting M-rows P_0 and P_d (four rows of the doubled
 * array) breaks S iff the class {x, x'} of P_0|S (or of P_d|S) is shown by no remaining M-row.
 * Symmetries as in pal5.c: translation (B_d = B_0 + d; the all-ones row is fixed) and column
 * multiplication by squares (fixes P_0 and the all-ones row, maps P_r to P_{r/a}). Only 6-sets
 * containing 1 or a fixed non-square g are scanned (OpenMP over the first free column).
 * Then SA over k-subsets of the p columns, then single-cell repairs of leftover bad sets in
 * the final 2(p-1)-row array with an exact bitset check (as in pal5.c).
 *
 * usage: pal6 paleyfile k d seed maxsec outfile [-brute]
 *   paleyfile: the p x p circulant paley_mat(p) (0/1); d = 0: choose the d with fewest bad sets
 *   -brute: also count row 0's bad sets by brute force over all 6-sets (test for small p)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <time.h>
#ifdef _OPENMP
#include <omp.h>
#endif
#define MAXP 400
#define WM 7          /* words for M rows (p+1 <= 448) */
#define WF 12         /* words for final array rows (<= 768) */
static int p; static uint8_t *P; static uint64_t BM[MAXP][2][WM];
static uint64_t rs=88172645463325252ULL;
static inline uint64_t xr(void){ rs^=rs<<13; rs^=rs>>7; rs^=rs<<17; return rs; }
static double now(void){ struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts); return ts.tv_sec+1e-9*ts.tv_nsec; }
typedef struct { uint16_t c[6]; int16_t q; } rec_t;
static int cmp6(const void *a,const void *b){ const rec_t *x=a,*y=b; for(int i=0;i<6;i++) if(x->c[i]!=y->c[i]) return x->c[i]-y->c[i]; return x->q-y->q; }
static void sort6(int *S){ for(int a=1;a<6;a++){ int x=S[a],b=a-1; while(b>=0&&S[b]>x){S[b+1]=S[b];b--;} S[b+1]=x; } }
static int issq[MAXP];
static inline int Mval(int r,int c){ return r==p? 1 : P[r*p+c]; }
/* rows of M matching P_0's class on S: count and the partner (other than row 0) */
static inline int classcount(const int *S, int *q){
    uint64_t mx[WM], my[WM]; for(int w=0;w<WM;w++){ mx[w]=~0ULL; my[w]=~0ULL; }
    for(int j=0;j<6;j++){ int c=S[j], v=P[c]; for(int w=0;w<WM;w++){ mx[w]&=BM[c][v][w]; my[w]&=BM[c][1-v][w]; } }
    int pc=0; for(int w=0;w<WM;w++) pc+=__builtin_popcountll(mx[w]|my[w]);
    if(pc==2 && q){ for(int w=0;w<WM;w++){ uint64_t y=(mx[w]|my[w])&~(w==0?1ULL:0ULL); if(y){ *q=w*64+__builtin_ctzll(y); break; } } }
    return pc; }
int main(int argc,char**argv){
    if(argc<7){ fprintf(stderr,"usage: pal6 paleyfile k d seed maxsec outfile [-brute]\n"); return 2; }
    int k=atoi(argv[2]), dfix=atoi(argv[3]); rs^=strtoull(argv[4],0,10)*0x9E3779B97F4A7C15ULL; for(int i=0;i<20;i++) xr(); double maxsec=atof(argv[5]);
    int brute= argc>7 && !strcmp(argv[7],"-brute");
    FILE *f=fopen(argv[1],"r"); if(!f){perror(argv[1]);return 2;}
    int cap=MAXP*MAXP; P=malloc(cap); int n=0,x; while(fscanf(f,"%d",&x)==1){ if(n>=cap){fprintf(stderr,"too big\n");return 2;} P[n++]=x; } fclose(f);
    p=(int)(sqrt((double)n)+0.5); if(p*p!=n||p>=MAXP){ fprintf(stderr,"not square\n"); return 2; }
    { int mn=9; for(int i=0;i<n;i++) if(P[i]<mn) mn=P[i]; if(mn==1) for(int i=0;i<n;i++) P[i]--; }
    for(int r=0;r<p;r++) for(int c=0;c<p;c++) if(P[r*p+c]!=P[(c-r+p)%p]){ fprintf(stderr,"not circulant\n"); return 2; }
    memset(BM,0,sizeof BM); for(int r=0;r<=p;r++) for(int c=0;c<p;c++) BM[c][Mval(r,c)][r>>6]|=1ULL<<(r&63);
    for(int a=1;a<p;a++) issq[(long)a*a%p]=1; int g=2; while(issq[g]) g++;
    printf("pal6: p=%d k=%d nonsquare g=%d\n",p,k,g); fflush(stdout);
    double t0=now();
    rec_t *R=0; long nR=0, capR=0;
    for(int bi=0;bi<2;bi++){ int base= bi? g:1;
        int L[MAXP], nl=0; for(int c=0;c<p;c++) if(c!=base) L[nl++]=c;
        #pragma omp parallel
        { rec_t *loc=0; long nloc=0, caploc=0;
          #pragma omp for schedule(dynamic,1)
          for(int i1=0;i1<nl;i1++){
            if(i1%25==0 || i1<4){ double done=0, tot=0; for(int j=0;j<nl;j++){ double w=(double)(nl-j-1)*(nl-j-2)*(nl-j-3)*(nl-j-4); tot+=w; if(j<i1) done+=w; } printf("    base %d: starting i1=%d, ~%.1f%% of this base's work before it (%.0fs)\n",base,i1,100*done/tot,now()-t0); fflush(stdout); }
            int vb=P[base]; uint64_t x1[WM], y1[WM]; int c1=L[i1], v1=P[c1];
            for(int w=0;w<WM;w++){ x1[w]=BM[base][vb][w]&BM[c1][v1][w]; y1[w]=BM[base][1-vb][w]&BM[c1][1-v1][w]; }
            for(int i2=i1+1;i2<nl;i2++){ int c2=L[i2], v2=P[c2]; uint64_t x2[WM], y2[WM]; for(int w=0;w<WM;w++){ x2[w]=x1[w]&BM[c2][v2][w]; y2[w]=y1[w]&BM[c2][1-v2][w]; }
             for(int i3=i2+1;i3<nl;i3++){ int c3=L[i3], v3=P[c3]; uint64_t x3[WM], y3[WM]; for(int w=0;w<WM;w++){ x3[w]=x2[w]&BM[c3][v3][w]; y3[w]=y2[w]&BM[c3][1-v3][w]; }
              for(int i4=i3+1;i4<nl;i4++){ int c4=L[i4], v4=P[c4]; uint64_t x4[WM], y4[WM]; int pc4=0; for(int w=0;w<WM;w++){ x4[w]=x3[w]&BM[c4][v4][w]; y4[w]=y3[w]&BM[c4][1-v4][w]; pc4+=__builtin_popcountll(x4[w]|y4[w]); }
               if(pc4>2){
                for(int i5=i4+1;i5<nl;i5++){ int c5=L[i5], v5=P[c5]; const uint64_t *bx=BM[c5][v5], *by=BM[c5][1-v5]; int pc=0; for(int w=0;w<WM;w++) pc+=__builtin_popcountll((x4[w]&bx[w])|(y4[w]&by[w]));
                  if(pc<=2){ int S[6]={base,c1,c2,c3,c4,c5}, q=-1; if(pc==2){ for(int w=0;w<WM;w++){ uint64_t yy=((x4[w]&bx[w])|(y4[w]&by[w]))&~(w==0?1ULL:0ULL); if(yy){ q=w*64+__builtin_ctzll(yy); break; } } }
                    sort6(S); if(nloc>=caploc){ caploc=caploc*2+1024; loc=realloc(loc,sizeof(rec_t)*caploc);} for(int j=0;j<6;j++) loc[nloc].c[j]=S[j]; loc[nloc].q=q; nloc++; } }
               } else {
                for(int i5=i4+1;i5<nl;i5++){ int c5=L[i5], v5=P[c5]; const uint64_t *bx=BM[c5][v5], *by=BM[c5][1-v5]; int pc=0, q=-1; for(int w=0;w<WM;w++) pc+=__builtin_popcountll((x4[w]&bx[w])|(y4[w]&by[w]));
                  if(pc==2){ for(int w=0;w<WM;w++){ uint64_t yy=((x4[w]&bx[w])|(y4[w]&by[w]))&~(w==0?1ULL:0ULL); if(yy){ q=w*64+__builtin_ctzll(yy); break; } } }
                  int S[6]={base,c1,c2,c3,c4,c5}; sort6(S); if(nloc>=caploc){ caploc=caploc*2+1024; loc=realloc(loc,sizeof(rec_t)*caploc);} for(int j=0;j<6;j++) loc[nloc].c[j]=S[j]; loc[nloc].q=q; nloc++; }
               } } } } }
          #pragma omp critical
          { if(nR+nloc>capR){ capR=nR+nloc+1024; R=realloc(R,sizeof(rec_t)*capR);} memcpy(R+nR,loc,sizeof(rec_t)*nloc); nR+=nloc; }
          free(loc);
        }
        printf("  base %d scanned, records so far %ld (%.0fs)\n",base,nR,now()-t0); fflush(stdout);
    }
    /* canonical orbit representatives under the squares (memory-light; partner sets have a trivial stabiliser) */
    int nsq=0, *sq=malloc(sizeof(int)*p); for(int a=1;a<p;a++) if(issq[a]) sq[nsq++]=a;
    int *inv=malloc(sizeof(int)*p); for(int a=1;a<p;a++) for(int b=1;b<p;b++) if((long)a*b%p==1){ inv[a]=b; break; }
    #pragma omp parallel for schedule(dynamic,1024)
    for(long i=0;i<nR;i++){ rec_t bestr=R[i];
        for(int s=0;s<nsq;s++){ int a=sq[s]; int S[6]; for(int j=0;j<6;j++) S[j]=(int)((long)a*R[i].c[j]%p); sort6(S);
            rec_t c; for(int j=0;j<6;j++) c.c[j]=S[j]; int q=R[i].q; c.q=(q<0||q==p)? q : (int)((long)a*q%p);
            if(cmp6(&c,&bestr)<0) bestr=c; }
        R[i]=bestr; }
    qsort(R,nR,sizeof(rec_t),cmp6); { long m=0; for(long i=0;i<nR;i++) if(i==0||cmp6(&R[i],&R[i-1])) R[m++]=R[i]; nR=m; }
    /* unique sets: expand fully (few); partner counts per q */
    rec_t *U=0; long nU=0, capU=0; static long partner[MAXP+1]; long npart=0, nones=0;
    for(long i=0;i<nR;i++){
        if(R[i].q<0){ for(int s=0;s<nsq;s++){ int a=sq[s]; int S[6]; for(int j=0;j<6;j++) S[j]=(int)((long)a*R[i].c[j]%p); sort6(S);
                if(nU>=capU){ capU=capU*2+1024; U=realloc(U,sizeof(rec_t)*capU);} for(int j=0;j<6;j++) U[nU].c[j]=S[j]; U[nU].q=-1; nU++; } }
        else if(R[i].q==p){ /* the all-ones partner is fixed by every multiplier: count the orbit exactly */
            rec_t *im=malloc(sizeof(rec_t)*nsq); for(int s=0;s<nsq;s++){ int a=sq[s]; int S[6]; for(int j=0;j<6;j++) S[j]=(int)((long)a*R[i].c[j]%p); sort6(S); for(int j=0;j<6;j++) im[s].c[j]=S[j]; im[s].q=p; }
            qsort(im,nsq,sizeof(rec_t),cmp6); long u=0; for(int s=0;s<nsq;s++) if(s==0||cmp6(&im[s],&im[s-1])) u++; free(im); nones+=u; npart+=u; }
        else { for(int s=0;s<nsq;s++) partner[(long)sq[s]*R[i].q%p]++; npart+=nsq; } }
    qsort(U,nU,sizeof(rec_t),cmp6); { long m=0; for(long i=0;i<nU;i++) if(i==0||cmp6(&U[i],&U[i-1])) U[m++]=U[i]; nU=m; }
    printf("row P_0: %ld 6-sets where its class is unique, %ld with one partner (%ld of them the all-ones row); %ld orbit representatives (%.0fs)\n",nU,npart,nones,nR,now()-t0); fflush(stdout);
    if(brute){ long bu=0, bp=0; int S[6]; for(int a=0;a<6;a++) S[a]=a;
        while(1){ int q=-1; int c=classcount(S,&q); if(c==1) bu++; else if(c==2) bp++;
            int i=5; while(i>=0 && S[i]==p-6+i) i--; if(i<0) break; S[i]++; for(int j=i+1;j<6;j++) S[j]=S[j-1]+1; }
        printf("BRUTE: unique %ld, one partner %ld  (symmetric scan: %ld, %ld) %s\n",bu,bp,nU,npart,(bu==nU&&bp==npart)?"AGREE":"DISAGREE"); return 0; }
    int bestd=-1; long bestcnt=-1;
    for(int d=1;d<p;d++){ if(dfix>0 && d!=dfix) continue; long c=2*nU+partner[d]+partner[(p-d)%p]; if(bestcnt<0||c<bestcnt){bestcnt=c;bestd=d;} }
    int d=bestd; printf("chosen d=%d: %ld bad sets\n",d,bestcnt); fflush(stdout);
    long ne=0; uint16_t (*E)[6]=malloc(sizeof(*E)*(bestcnt+16));
    for(long i=0;i<nU;i++){ int S[6]; memcpy(E[ne++],U[i].c,12); for(int j=0;j<6;j++) S[j]=(U[i].c[j]+d)%p; sort6(S); for(int j=0;j<6;j++) E[ne][j]=S[j]; ne++; }
    for(long i=0;i<nR;i++){ int q=R[i].q; if(q<0||q==p) continue;
        for(int h=0;h<2;h++){ int target= h? (p-d)%p : d; int a=(int)((long)target*inv[q]%p); if(!issq[a]) continue;
            int S[6]; for(int j=0;j<6;j++) S[j]=(int)(((long)a*R[i].c[j]%p + (h? d:0))%p); sort6(S); for(int j=0;j<6;j++) E[ne][j]=S[j]; ne++; } }
    if(ne!=bestcnt) printf("note: %ld edges built, %ld expected\n",ne,bestcnt);
    long *deg=calloc(p,sizeof(long)); for(long e=0;e<ne;e++) for(int j=0;j<6;j++) deg[E[e][j]]++;
    long **inc=malloc(sizeof(long*)*p); long *fill=calloc(p,sizeof(long)); for(int c=0;c<p;c++) inc[c]=malloc(sizeof(long)*(deg[c]+1));
    for(long e=0;e<ne;e++) for(int j=0;j<6;j++){ int c=E[e][j]; inc[c][fill[c]++]=e; }
    int *in=calloc(p,sizeof(int)), *lst=malloc(sizeof(int)*p); uint8_t *cnt=calloc(ne+1,1);
    for(int c=0;c<p;c++) lst[c]=c; for(int c=p-1;c>0;c--){ int j=xr()%(c+1), y=lst[c]; lst[c]=lst[j]; lst[j]=y; }
    for(int i=0;i<k;i++) in[lst[i]]=1;
    long cost=0; for(long e=0;e<ne;e++){ int s=0; for(int j=0;j<6;j++) s+=in[E[e][j]]; cnt[e]=s; if(s==6) cost++; }
    printf("SA start cost %ld (edges %ld)\n",cost,ne); fflush(stdout);
    double T=2.0; long it=0, best=cost; uint8_t *mark=calloc(ne+1,1); int *bestin=malloc(sizeof(int)*p); memcpy(bestin,in,sizeof(int)*p);
    while(cost>0 && now()-t0<maxsec){
        it++; int iu=xr()%k, iv=k+xr()%(p-k); int u=lst[iu], v=lst[iv];
        long dl=0; for(long a=0;a<deg[u];a++){ long e=inc[u][a]; mark[e]=1; if(cnt[e]==6) dl--; }
        for(long a=0;a<deg[v];a++){ long e=inc[v][a]; if(!mark[e] && cnt[e]==5) dl++; }
        for(long a=0;a<deg[u];a++) mark[inc[u][a]]=0;
        if(dl<=0 || (xr()>>11)*(1.0/9007199254740992.0) < exp(-dl/T)){
            for(long a=0;a<deg[u];a++) cnt[inc[u][a]]--; for(long a=0;a<deg[v];a++) cnt[inc[v][a]]++;
            in[u]=0; in[v]=1; lst[iu]=v; lst[iv]=u; cost+=dl; if(cost<best){ best=cost; memcpy(bestin,in,sizeof(int)*p); } }
        if((it&0xfffff)==0){ T*=0.97; if(T<0.05) T=1.0; }
        if((it&0x3ffffff)==0){ printf("  it=%ld T=%.3f cost=%ld best=%ld (%.0fs)\n",it,T,cost,best,now()-t0); fflush(stdout); }
    }
    if(best>12){ printf("FAILED: best %ld bad sets inside\n",best); return 1; }
    memcpy(in,bestin,sizeof(int)*p);
    int ch[MAXP], nc=0; for(int c=0;c<p;c++) if(in[c]) ch[nc++]=c;
    /* final array: rows m and complement(m) for m in M minus {P_0, P_d}, columns ch */
    int NF=0; static uint8_t F[2*MAXP+2][MAXP]; static uint64_t BF[MAXP][2][WF];
    for(int r=0;r<=p;r++){ if(r==0||r==d) continue; for(int j=0;j<nc;j++){ F[NF][j]=Mval(r,ch[j]); F[NF+1][j]=1-Mval(r,ch[j]); } NF+=2; }
    memset(BF,0,sizeof BF); for(int r=0;r<NF;r++) for(int j=0;j<nc;j++) BF[j][F[r][j]][r>>6]|=1ULL<<(r&63);
    int nfix=0;
    printf("annealing best %ld bad sets; final array %d x %d; repairing (%.0fs)\n",best,NF,nc,now()-t0); fflush(stdout);
    for(long e=0;e<ne;e++){
        int pos[6], allin=1; for(int j=0;j<6;j++){ int c=E[e][j]; if(!in[c]){ allin=0; break; } int q=0; while(ch[q]!=c) q++; pos[j]=q; } if(!allin) continue;
        for(int dr=0;dr<2;dr++) for(int cmpl=0;cmpl<2;cmpl++){
            int r0= dr? d:0; int y[6]; for(int j=0;j<6;j++) y[j]=P[r0*p+E[e][j]]^cmpl;
            uint64_t mm[WF]; for(int w=0;w<WF;w++) mm[w]=~0ULL; for(int j=0;j<6;j++) for(int w=0;w<WF;w++) mm[w]&=BF[pos[j]][y[j]][w];
            int z=0; for(int w=0;w<WF;w++) if(mm[w]) z=1; if(z) continue;   /* covered (maybe by an earlier repair) */
            int fixed=0;
            for(int r=0;r<NF && !fixed;r++){ int diff=0, dj=-1; for(int j=0;j<6;j++) if(F[r][pos[j]]!=y[j]){ diff++; dj=pos[j]; } if(diff!=1) continue;
                int ok=1, oth[MAXP], no=0; for(int j=0;j<nc;j++) if(j!=dj) oth[no++]=j;
                uint64_t b0[WF]; for(int w=0;w<WF;w++) b0[w]=BF[dj][F[r][dj]][w]&~((r>>6)==w?(1ULL<<(r&63)):0ULL);
                for(int a1=0;a1<no&&ok;a1++){ uint64_t m1[WF]; int z1=0; for(int w=0;w<WF;w++){ m1[w]=b0[w]&BF[oth[a1]][F[r][oth[a1]]][w]; z1|=m1[w]!=0; } if(!z1){ok=0;break;}
                 for(int a2=a1+1;a2<no&&ok;a2++){ uint64_t m2[WF]; int z2=0; for(int w=0;w<WF;w++){ m2[w]=m1[w]&BF[oth[a2]][F[r][oth[a2]]][w]; z2|=m2[w]!=0; } if(!z2){ok=0;break;}
                  for(int a3=a2+1;a3<no&&ok;a3++){ uint64_t m3[WF]; int z3=0; for(int w=0;w<WF;w++){ m3[w]=m2[w]&BF[oth[a3]][F[r][oth[a3]]][w]; z3|=m3[w]!=0; } if(!z3){ok=0;break;}
                   for(int a4=a3+1;a4<no&&ok;a4++){ uint64_t m4[WF]; int z4=0; for(int w=0;w<WF;w++){ m4[w]=m3[w]&BF[oth[a4]][F[r][oth[a4]]][w]; z4|=m4[w]!=0; } if(!z4){ok=0;break;}
                    for(int a5=a4+1;a5<no;a5++){ const uint64_t *b5=BF[oth[a5]][F[r][oth[a5]]]; int z5=0; for(int w=0;w<WF;w++) if(m4[w]&b5[w]){ z5=1; break; } if(!z5){ ok=0; break; } } } } } }
                if(ok){ int v=F[r][dj]; BF[dj][v][r>>6]&=~(1ULL<<(r&63)); F[r][dj]=1-v; BF[dj][1-v][r>>6]|=1ULL<<(r&63); fixed=1; nfix++;
                    printf("  repaired a missing tuple on {%d,%d,%d,%d,%d,%d} by changing final row %d, column %d (%.0fs)\n",E[e][0],E[e][1],E[e][2],E[e][3],E[e][4],E[e][5],r,ch[dj],now()-t0); fflush(stdout); }
            }
            if(!fixed){ printf("FAILED: could not repair bad set %ld\n",e); return 1; }
        }
    }
    FILE *o=fopen(argv[6],"w"); for(int r=0;r<NF;r++){ for(int j=0;j<nc;j++) fprintf(o,j?" %d":"%d",F[r][j]); fputc('\n',o); } fclose(o);
    printf("WROTE %s: %d rows x %d columns (M-rows P_0 and P_%d deleted with their complements, doubling column not used), %d cells changed; Paley columns:",argv[6],NF,nc,d,nfix);
    for(int j=0;j<nc;j++) printf(" %d",ch[j]); printf(" (%.0fs)\n",now()-t0);
    return 0;
}
