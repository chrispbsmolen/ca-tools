/* pal5.c - CA(p-2; 5, k, 2) from the circulant Paley array of prime order p (a CA(p;5,p,2),
 * e.g. CAs::paley_mat(359)) by deleting two rows {0, d} and choosing k columns.
 * Written for ca-tools, 2026-10-27.
 *
 * A row-deleted array fails on a 5-set S exactly when a deleted row's tuple on S is shown by no
 * remaining row. For the circulant Paley array A[r][c] = f(c - r):
 *  - translation (r, c) -> (r + 1, c + 1) maps row 0's bad sets to row d's: B_d = B_0 + d;
 *  - multiplication of the columns by a square a maps row r to row r/a and fixes row 0, so
 *    B_0 is a union of orbits of the squares; every orbit meets the 5-sets containing 1 or a
 *    fixed non-square g, so only those (2 x C(p-1,4)) are scanned.
 * Recorded for row 0: U = sets where row 0 is the only row with its tuple, and P = sets where
 * exactly one other row q has it (then deleting {0, q} breaks S). For D = {0, d} the bad sets
 * are U, U + d, {S in P : q = d}, and {S + d : S in P, q = -d}.
 * Then simulated annealing over k-subsets of columns (swap moves) minimises the number of bad
 * sets inside the subset. On success the array (rows not in D, chosen columns) is written;
 * verify it with ca_verify.
 *
 * If the annealing ends with a few bad sets left (<= 8), each is repaired, if possible, by one
 * cell change: a remaining row at Hamming distance 1 from the missing tuple takes it, when an
 * exact bitset check shows that no 5-set through that cell loses its only copy of a tuple.
 *
 * usage: pal5 paleyfile k d seed maxsec outfile      (d = 0: try every d and take the best)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <time.h>
#define W 6
static int p; static uint8_t *A; static uint64_t B[400][2][W];
static uint64_t rs=88172645463325252ULL;
static inline uint64_t xr(void){ rs^=rs<<13; rs^=rs>>7; rs^=rs<<17; return rs; }
static double now(void){ struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts); return ts.tv_sec+1e-9*ts.tv_nsec; }
typedef struct { uint16_t c[5]; int16_t q; } rec_t;
static rec_t *R; static long nR, capR;
static void addrec(const int *S, int q){ if(nR>=capR){ capR=capR*2+1024; R=realloc(R,sizeof(rec_t)*capR);} for(int i=0;i<5;i++) R[nR].c[i]=S[i]; R[nR].q=q; nR++; }
static int cmp5(const void *a,const void *b){ const rec_t *x=a,*y=b; for(int i=0;i<5;i++) if(x->c[i]!=y->c[i]) return x->c[i]-y->c[i]; return x->q-y->q; }
static void sort5(int *S){ for(int a=1;a<5;a++){ int x=S[a],b=a-1; while(b>=0&&S[b]>x){S[b+1]=S[b];b--;} S[b+1]=x; } }
static int issq[400];
int main(int argc,char**argv){
    if(argc<7){ fprintf(stderr,"usage: pal5 paleyfile k d seed maxsec outfile\n"); return 2; }
    int k=atoi(argv[2]), dfix=atoi(argv[3]); rs^=strtoull(argv[4],0,10)*0x9E3779B97F4A7C15ULL; for(int i=0;i<20;i++) xr(); double maxsec=atof(argv[5]);
    FILE *f=fopen(argv[1],"r"); if(!f){perror(argv[1]);return 2;}
    /* read square matrix */
    int cap=400*400; A=malloc(cap); int n=0,x; while(fscanf(f,"%d",&x)==1){ if(n>=cap){fprintf(stderr,"too big\n");return 2;} A[n++]=x; } fclose(f);
    p=(int)(sqrt((double)n)+0.5); if(p*p!=n||p>=400){ fprintf(stderr,"not square\n"); return 2; }
    for(int r=0;r<p;r++) for(int c=0;c<p;c++) if(A[r*p+c]!=A[(c-r+p)%p]){ fprintf(stderr,"not circulant\n"); return 2; }
    memset(B,0,sizeof B); for(int r=0;r<p;r++) for(int c=0;c<p;c++) B[c][A[r*p+c]][r>>6]|=1ULL<<(r&63);
    for(int a=1;a<p;a++) issq[(long)a*a%p]=1; int g=2; while(issq[g]) g++;
    printf("pal5: p=%d k=%d nonsquare g=%d\n",p,k,g); fflush(stdout);
    double t0=now();
    /* scan 5-sets containing base in {1,g}: S={base,a<b<c<d} */
    long scanned=0;
    for(int bi=0;bi<2;bi++){ int base= bi? g:1;
        uint64_t m0[W]; for(int w=0;w<W;w++) m0[w]=B[base][A[base]][w];
        int L[400], nl=0; for(int c=0;c<p;c++) if(c!=base) L[nl++]=c;
        for(int i1=0;i1<nl;i1++){ uint64_t m1[W]; int z1=0; for(int w=0;w<W;w++){ m1[w]=m0[w]&B[L[i1]][A[L[i1]]][w]; }
          for(int i2=i1+1;i2<nl;i2++){ uint64_t m2[W]; for(int w=0;w<W;w++) m2[w]=m1[w]&B[L[i2]][A[L[i2]]][w];
            for(int i3=i2+1;i3<nl;i3++){ uint64_t m3[W]; int pc3=0; for(int w=0;w<W;w++){ m3[w]=m2[w]&B[L[i3]][A[L[i3]]][w]; pc3+=__builtin_popcountll(m3[w]); }
              if(pc3>2){ /* most cases: need the 5th column to cut it down to <=2 */
                for(int i4=i3+1;i4<nl;i4++){ const uint64_t *b4=B[L[i4]][A[L[i4]]]; int pc=0; for(int w=0;w<W;w++) pc+=__builtin_popcountll(m3[w]&b4[w]);
                  if(pc<=2){ int S[5]={base,L[i1],L[i2],L[i3],L[i4]}; int q=-1; if(pc==2){ for(int w=0;w<W;w++){ uint64_t y=m3[w]&b4[w]&~(w==0?1ULL:0ULL); if(y){ q=w*64+__builtin_ctzll(y); break; } } }
                    sort5(S); addrec(S,q); } }
              } else { for(int i4=i3+1;i4<nl;i4++){ const uint64_t *b4=B[L[i4]][A[L[i4]]]; int pc=0; uint64_t y[W]; for(int w=0;w<W;w++){ y[w]=m3[w]&b4[w]; pc+=__builtin_popcountll(y[w]); }
                  int S[5]={base,L[i1],L[i2],L[i3],L[i4]}; int q=-1; if(pc==2){ for(int w=0;w<W;w++){ uint64_t yy=y[w]&~(w==0?1ULL:0ULL); if(yy){ q=w*64+__builtin_ctzll(yy); break; } } }
                  sort5(S); addrec(S,q); } }
              scanned+=nl-i3-1; } } }
        printf("  base %d scanned, records so far %ld (%.0fs)\n",base,nR,now()-t0); fflush(stdout);
    }
    (void)scanned;
    /* expand by squares and dedupe */
    long n0=nR; for(long i=0;i<n0;i++) for(int a=2;a<p;a++) if(issq[a]){ int S[5]; for(int j=0;j<5;j++) S[j]=(int)((long)a*R[i].c[j]%p); sort5(S); int q=R[i].q<0?-1:(int)((long)a*R[i].q%p); addrec(S,q); }
    qsort(R,nR,sizeof(rec_t),cmp5); long m=0; for(long i=0;i<nR;i++) if(i==0||cmp5(&R[i],&R[i-1])) R[m++]=R[i]; nR=m;
    long nU=0; static long partner[400]; for(long i=0;i<nR;i++){ if(R[i].q<0) nU++; else partner[R[i].q]++; }
    printf("row 0: %ld sets where it is unique, %ld sets with one partner (%.0fs)\n",nU,nR-nU,now()-t0);
    /* choose d */
    int dlist[400], nd=0; if(dfix>0) dlist[nd++]=dfix; else { for(int d=1;d<p;d++) dlist[nd++]=d; }
    int bestd=-1; long bestcnt=-1;
    for(int i=0;i<nd;i++){ int d=dlist[i]; long c=2*nU+partner[d]+partner[(p-d)%p]; if(bestcnt<0||c<bestcnt){bestcnt=c;bestd=d;} }
    printf("chosen d=%d: %ld bad sets (2 x %ld unique + %ld + %ld partner)\n",bestd,bestcnt,nU,partner[bestd],partner[(p-bestd)%p]); fflush(stdout);
    int d=bestd;
    /* build edge list */
    long ne=0, cape=bestcnt+16; uint16_t (*E)[5]=malloc(sizeof(*E)*cape);
    for(long i=0;i<nR;i++){
        if(R[i].q<0){ memcpy(E[ne++],R[i].c,10); int S[5]; for(int j=0;j<5;j++) S[j]=(R[i].c[j]+d)%p; sort5(S); for(int j=0;j<5;j++) E[ne][j]=S[j]; ne++; }
        else { if(R[i].q==d){ memcpy(E[ne++],R[i].c,10); } if(R[i].q==(p-d)%p){ int S[5]; for(int j=0;j<5;j++) S[j]=(R[i].c[j]+d)%p; sort5(S); for(int j=0;j<5;j++) E[ne][j]=S[j]; ne++; } }
    }
    /* incidence */
    long *deg=calloc(p,sizeof(long)); for(long e=0;e<ne;e++) for(int j=0;j<5;j++) deg[E[e][j]]++;
    long **inc=malloc(sizeof(long*)*p); long *fill=calloc(p,sizeof(long)); for(int c=0;c<p;c++) inc[c]=malloc(sizeof(long)*(deg[c]+1));
    for(long e=0;e<ne;e++) for(int j=0;j<5;j++){ int c=E[e][j]; inc[c][fill[c]++]=e; }
    /* SA over k-subsets */
    int *in=calloc(p,sizeof(int)); uint8_t *cnt=calloc(ne,1); int *pos=malloc(sizeof(int)*p), *lst=malloc(sizeof(int)*p);
    for(int c=0;c<p;c++) lst[c]=c; for(int c=p-1;c>0;c--){ int j=xr()%(c+1), y=lst[c]; lst[c]=lst[j]; lst[j]=y; } for(int c=0;c<p;c++) pos[lst[c]]=c;
    /* lst[0..k) chosen; prefer low degree */
    for(int i=0;i<k;i++) in[lst[i]]=1;
    long cost=0; for(long e=0;e<ne;e++){ int s=0; for(int j=0;j<5;j++) s+=in[E[e][j]]; cnt[e]=s; if(s==5) cost++; }
    printf("SA start cost %ld (edges %ld)\n",cost,ne); fflush(stdout);
    double T=2.0; long it=0, best=cost; uint8_t *mark=calloc(ne,1); int *bestin=malloc(sizeof(int)*p); memcpy(bestin,in,sizeof(int)*p);
    while(cost>0 && now()-t0<maxsec){
        it++;
        int iu=xr()%k, iv=k+xr()%(p-k); int u=lst[iu], v=lst[iv];
        long dl=0; for(long a=0;a<deg[u];a++){ long e=inc[u][a]; mark[e]=1; if(cnt[e]==5) dl--; }
        for(long a=0;a<deg[v];a++){ long e=inc[v][a]; if(!mark[e] && cnt[e]==4) dl++; }
        for(long a=0;a<deg[u];a++) mark[inc[u][a]]=0;
        if(dl<=0 || (xr()>>11)*(1.0/9007199254740992.0) < exp(-dl/T)){
            for(long a=0;a<deg[u];a++) cnt[inc[u][a]]--; for(long a=0;a<deg[v];a++) cnt[inc[v][a]]++;
            in[u]=0; in[v]=1; lst[iu]=v; lst[iv]=u; cost+=dl; if(cost<best){ best=cost; memcpy(bestin,in,sizeof(int)*p); }
        }
        if((it&0xfffff)==0){ T*=0.97; if(T<0.05) T=1.0; }
        if((it&0x3ffffff)==0){ printf("  it=%ld T=%.3f cost=%ld best=%ld (%.0fs)\n",it,T,cost,best,now()-t0); fflush(stdout); }
    }
    int ch[400], nc=0; int nfix=0;
    if(cost>0){
        printf("annealing left %ld bad sets (best %ld) (%.0fs)\n",cost,best,now()-t0);
        if(best>8){ printf("FAILED\n"); return 1; }
        memcpy(in,bestin,sizeof(int)*p);
        /* alive rows */
        uint64_t al[W]; memset(al,0,sizeof al); for(int r=0;r<p;r++) if(r!=0&&r!=d) al[r>>6]|=1ULL<<(r&63);
        for(int c=0;c<p;c++) if(in[c]) ch[nc++]=c;
        for(long e=0;e<ne;e++){
            int allin=1; for(int j=0;j<5;j++) if(!in[E[e][j]]) allin=0; if(!allin) continue;
            /* which deleted row's tuple is missing on this set? */
            for(int dr=0;dr<2;dr++){ int r0= dr? d:0; uint64_t mm[W]; for(int w=0;w<W;w++) mm[w]=al[w]; for(int j=0;j<5;j++){ int c=E[e][j]; for(int w=0;w<W;w++) mm[w]&=B[c][A[r0*p+c]][w]; }
                int z=0; for(int w=0;w<W;w++) if(mm[w]) z=1; if(z) continue;
                int fixed=0;
                for(int r=1;r<p && !fixed;r++){ if(r==d) continue; int diff=0, dc=-1; for(int j=0;j<5;j++){ int c=E[e][j]; if(A[r*p+c]!=A[r0*p+c]){ diff++; dc=c; } } if(diff!=1) continue;
                    /* exact check: every 5-set of chosen columns through dc keeps row r's old tuple covered by another alive row */
                    int ok=1; int oth[400], no=0; for(int j=0;j<nc;j++) if(ch[j]!=dc) oth[no++]=ch[j];
                    uint64_t base[W]; for(int w=0;w<W;w++) base[w]=al[w]&B[dc][A[r*p+dc]][w]&~((r>>6)==w? (1ULL<<(r&63)):0ULL);
                    for(int a1=0;a1<no && ok;a1++){ uint64_t m1[W]; int z1=0; for(int w=0;w<W;w++){ m1[w]=base[w]&B[oth[a1]][A[r*p+oth[a1]]][w]; z1|=m1[w]!=0; } if(!z1){ ok=0; break; }
                      for(int a2=a1+1;a2<no && ok;a2++){ uint64_t m2[W]; int z2=0; for(int w=0;w<W;w++){ m2[w]=m1[w]&B[oth[a2]][A[r*p+oth[a2]]][w]; z2|=m2[w]!=0; } if(!z2){ ok=0; break; }
                        for(int a3=a2+1;a3<no && ok;a3++){ uint64_t m3[W]; int z3=0; for(int w=0;w<W;w++){ m3[w]=m2[w]&B[oth[a3]][A[r*p+oth[a3]]][w]; z3|=m3[w]!=0; } if(!z3){ ok=0; break; }
                          for(int a4=a3+1;a4<no;a4++){ const uint64_t *b4=B[oth[a4]][A[r*p+oth[a4]]]; int z4=0; for(int w=0;w<W;w++) if(m3[w]&b4[w]){ z4=1; break; } if(!z4){ ok=0; break; } } } } }
                    if(ok){ /* apply the change */ int v=A[r*p+dc]; B[dc][v][r>>6]&=~(1ULL<<(r&63)); A[r*p+dc]=1-v; B[dc][1-v][r>>6]|=1ULL<<(r&63); fixed=1; nfix++;
                        printf("  repaired bad set {%d,%d,%d,%d,%d} (row %d missing) by changing cell (row %d, column %d) (%.0fs)\n",E[e][0],E[e][1],E[e][2],E[e][3],E[e][4],r0,r,dc,now()-t0); fflush(stdout); }
                }
                if(!fixed){ printf("FAILED: could not repair bad set %ld\n",e); return 1; }
            }
        }
    } else { for(int c=0;c<p;c++) if(in[c]) ch[nc++]=c; }
    FILE *o=fopen(argv[6],"w"); int nr=0;
    for(int r=0;r<p;r++){ if(r==0||r==d) continue; nr++; for(int j=0;j<nc;j++) fprintf(o,j?" %d":"%d",A[r*p+ch[j]]); fputc('\n',o); }
    fclose(o); printf("WROTE %s: %d rows x %d columns, deleted rows 0 and %d, %d cells changed; columns:",argv[6],nr,nc,d,nfix); for(int j=0;j<nc;j++) printf(" %d",ch[j]); printf(" (%.0fs)\n",now()-t0);
    return 0;
}
