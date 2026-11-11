// orbfree3.c - binary covering arrays of strength 3 from a row permutation: full column orbits plus free columns.
// Exhaustive, no random numbers, no input array. Build WITHOUT OpenMP (cc -O3) so that the order of the search, and
// with it the output file, is the same on every machine.
//
// usage: orbfree3 N m out c1 c2 ...
//   N rows. The row permutation tau has cycles of lengths c1 c2 ... (rows 0..c1-1, then the next c2 rows, and so on).
//   L = lcm of the cycle lengths. A column is a 0/1 vector on the rows, up to complement. Its orbit is its L images
//   under tau. The program keeps every orbit whose L columns form a strength-3 array by themselves, joins orbits
//   whose union is a strength-3 array, lists every set of m such orbits that contains a representative under the
//   normaliser of tau, and for each set lists ALL free columns (columns that keep strength 3 with the m*L orbit
//   columns; found by one subset-sum transform over the 2^N sets of rows) and finds the largest set of free columns
//   that keeps strength 3 together. It writes out_ext_N_k.txt each time the total number of columns k improves.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef _OPENMP
#include <omp.h>
#endif
static double wtime(void){return (double)clock()/CLOCKS_PER_SEC;}
typedef unsigned int u32;
int N,L,perm[40];u32 F;
int gcd(int a,int b){return b?gcd(b,a%b):a;}
u32 (*T)[4][256];
static inline u32 ap(int s,u32 x){return T[s][0][x&255]|T[s][1][(x>>8)&255]|T[s][2][(x>>16)&255]|T[s][3][x>>24];}
static inline int cov3(u32 a,u32 b,u32 c){u32 na=~a&F,nb=~b&F,nc=~c&F;
  return (a&b&c)&&(a&b&nc)&&(a&nb&c)&&(a&nb&nc)&&(na&b&c)&&(na&b&nc)&&(na&nb&c)&&(na&nb&nc);}
u32*R;long nv=0;
static inline int pairok(const u32*A,const u32*B){
  for(int j=1;j<=L/2;j++)for(int k=0;k<L;k++)if(!cov3(A[0],A[j],B[k]))return 0;
  for(int j=1;j<=L/2;j++)for(int k=0;k<L;k++)if(!cov3(B[0],B[j],A[k]))return 0;
  return 1;}
static inline int tripok(const u32*A,const u32*B,const u32*C){for(int j=0;j<L;j++)for(int k=0;k<L;k++)if(!cov3(A[0],B[j],C[k]))return 0;return 1;}
int want;long cntm[16];int bestm=0;char*outp;
void wr(int m,const int*ix){char fn[300];sprintf(fn,"%s_%d_%d.txt",outp,N,m*L);FILE*f=fopen(fn,"w");
  for(int r=0;r<N;r++){int first=1;for(int i=0;i<m;i++)for(int s=0;s<L;s++){fprintf(f,"%s%d",first?"":" ",(int)(R[(size_t)ix[i]*L+s]>>r&1));first=0;}fprintf(f,"\n");}fclose(f);}

int gbesttot=0;
static int extend(const int*cl,int m,int*bestS,u32*outS){ // returns max number of extra free columns
  int k0=m*L;u32 B[256];for(int i=0;i<m;i++)for(int s=0;s<L;s++)B[i*L+s]=R[(size_t)cl[i]*L+s];
  size_t SZ=(size_t)1<<N;short*Z=calloc(SZ,sizeof(short));
  for(int i=0;i<k0;i++)for(int j=i+1;j<k0;j++){u32 a=B[i],b=B[j];Z[a&b]++;Z[a&~b&F]++;Z[~a&b&F]++;Z[~a&~b&F]++;}
  for(int b=0;b<N;b++){size_t st=(size_t)1<<b;for(size_t x=0;x<SZ;x+=2*st){short*lo=Z+x,*hi=Z+x+st;for(size_t y=0;y<st;y++)hi[y]+=lo[y];}}
  u32*E=malloc(4*4096);int ne=0;for(size_t x=0;x<SZ/2&&ne<4096;x++)if(Z[x]+Z[x^F]==0)E[ne++]=x;
  free(Z);
  // pair graph on E
  unsigned char*A=calloc((size_t)ne*ne,1);
  for(int i=0;i<ne;i++)for(int j=i+1;j<ne;j++){int ok=1;for(int b=0;b<k0&&ok;b++)if(!cov3(B[b],E[i],E[j]))ok=0;A[(size_t)i*ne+j]=A[(size_t)j*ne+i]=ok;}
  // max clique with triple checks (simple DFS)
  int best=0;int st[64];int*cands[64];int nc[64];int chosen[64];
  cands[0]=malloc(sizeof(int)*(ne+1));for(int i=0;i<ne;i++)cands[0][i]=i;nc[0]=ne;st[0]=0;int d=0;
  for(int i=1;i<64;i++)cands[i]=malloc(sizeof(int)*(ne+1));
  while(d>=0){
    if(st[d]>=nc[d]||d+ (nc[d]-st[d]) <= best){d--;continue;}
    int w=cands[d][st[d]++];
    int ok=1;for(int a=0;a<d&&ok;a++)for(int b=a+1;b<d&&ok;b++)if(!cov3(E[chosen[a]],E[chosen[b]],E[w]))ok=0;
    if(!ok)continue;
    chosen[d]=w;if(d+1>best){best=d+1;for(int i=0;i<=d;i++)outS[i]=E[chosen[i]];}
    int m2=0;for(int j=st[d];j<nc[d];j++)if(A[(size_t)w*ne+cands[d][j]])cands[d+1][m2++]=cands[d][j];
    if(d<62){d++;nc[d]=m2;st[d]=0;}
  }
  for(int i=0;i<64;i++)free(cands[i]);free(A);free(E);*bestS=ne;return best;}
void dfs(int depth,int*cl,const int*cand,int n,long*lc,int*lbest,int (*lbix)[16]){
  lc[depth]++;if(depth>*lbest){*lbest=depth;memcpy(*lbix,cl,sizeof(int)*depth);}
  if(depth==want){int ne;u32 S[64];int e=extend(cl,depth,&ne,S);
    #pragma omp critical
    {static long done=0;static long hist[64];done++;hist[e]++;
     if(depth*L+e>gbesttot){gbesttot=depth*L+e;char fn[300];sprintf(fn,"%s_ext_%d_%d.txt",outp,N,gbesttot);FILE*f=fopen(fn,"w");
       for(int r=0;r<N;r++){int first=1;for(int i=0;i<depth;i++)for(int q=0;q<L;q++){fprintf(f,"%s%d",first?"":" ",(int)(R[(size_t)cl[i]*L+q]>>r&1));first=0;}for(int i=0;i<e;i++)fprintf(f," %d",(int)(S[i]>>r&1));fprintf(f,"\n");}fclose(f);
       printf("NEW BEST total %d columns = %d orbit columns + %d free (of %d free candidates)\n",gbesttot,depth*L,e,ne);fflush(stdout);}
     if(done%500==0){printf("bases done %ld; extra-column histogram:",done);for(int i=0;i<12;i++)printf(" %d:%ld",i,hist[i]);printf("\n");fflush(stdout);}}
    return;}
  if(depth>=want||!n)return;
  int*nx=malloc(sizeof(int)*n);
  for(int i=0;i<n;i++){int w=cand[i];
    int ok=1;for(int a=0;a<depth&&ok;a++)for(int b=a+1;b<depth&&ok;b++)if(!tripok(R+(size_t)cl[a]*L,R+(size_t)cl[b]*L,R+(size_t)w*L))ok=0;
    if(!ok)continue;
    cl[depth]=w;int m=0;const u32*Rw=R+(size_t)w*L;for(int j=i+1;j<n;j++)if(pairok(Rw,R+(size_t)cand[j]*L))nx[m++]=cand[j];
    dfs(depth+1,cl,nx,m,lc,lbest,lbix);}
  free(nx);}
int main(int ac,char**av){
  N=atoi(av[1]);want=atoi(av[2]);outp=av[3];int pos=0;L=1;int ncyc=ac-4,clen[40],coff[40];
  for(int a=4;a<ac;a++){int c=atoi(av[a]);clen[a-4]=c;coff[a-4]=pos;for(int i=0;i<c;i++)perm[pos+i]=pos+(i+1)%c;pos+=c;L=L/gcd(L,c)*c;}
  if(pos!=N)return 1;F=(1u<<N)-1;double t0=wtime();
  T=malloc(sizeof(u32[4][256])*L);
  {int ps[40];for(int i=0;i<N;i++)ps[i]=i;
   for(int s=0;s<L;s++){for(int b=0;b<4;b++)for(int v=0;v<256;v++){u32 r=0;for(int j=0;j<8;j++)if((v>>j&1)&&b*8+j<N)r|=1u<<ps[b*8+j];T[s][b][v]=r;}
     for(int i=0;i<N;i++)ps[i]=perm[ps[i]];}}
  long cap=1<<20;u32*fs=malloc(4*cap);
  #pragma omp parallel for schedule(dynamic,4096)
  for(u32 f=0;f<(1u<<(N-1));f++){
    int w=__builtin_popcount(f);if(w<4||w>N-4)continue;
    u32 Q[512];Q[0]=f;int ok=1;u32 nf=~f&F;
    for(int s=1;s<=L/2&&ok;s++){u32 g=ap(s,f);Q[s]=g;u32 ng=~g&F;if(!(f&g)||!(f&ng)||!(nf&g)||!(nf&ng))ok=0;}
    if(!ok)continue;
    for(int s=L/2+1;s<L;s++)Q[s]=ap(s,f);
    for(int b=1;b<L&&ok;b++)for(int c=b+1;c<L;c++)if(!cov3(f,Q[b],Q[c])){ok=0;break;}
    for(int s=1;s<L&&ok;s++){u32 g=Q[s];if(g>>(N-1)&1)g=~g&F;if(g<f)ok=0;}
    if(ok){
      #pragma omp critical
      {if(nv==cap){cap*=2;fs=realloc(fs,4*cap);}fs[nv++]=f;}}
  }
  R=malloc((size_t)nv*L*4);for(long i=0;i<nv;i++)for(int s=0;s<L;s++)R[(size_t)i*L+s]=ap(s,fs[i]);
  // normaliser
  long nrot=1;for(int c=0;c<ncyc;c++)nrot*=clen[c];int nu=0,us[512];for(int u=1;u<=L;u++)if(gcd(u,L)==1)us[nu++]=u;
  long nh=nrot*nu;u32 (*HT)[4][256]=malloc(sizeof(u32[4][256])*nh);
  for(long r=0;r<nrot;r++)for(int ui=0;ui<nu;ui++){int ph[40];long x=r;for(int c=0;c<ncyc;c++){int al=x%clen[c];x/=clen[c];for(int i=0;i<clen[c];i++)ph[coff[c]+i]=coff[c]+(int)(((long)us[ui]*i+al)%clen[c]);}
    u32 (*t)[256]=HT[r*nu+ui];for(int bb=0;bb<4;bb++)for(int v=0;v<256;v++){u32 q=0;for(int j=0;j<8;j++)if((v>>j&1)&&bb*8+j<N)q|=1u<<ph[bb*8+j];t[bb][v]=q;}}
  char*isrep=malloc(nv);long nrep=0;
  #pragma omp parallel for schedule(dynamic,256) reduction(+:nrep)
  for(long i=0;i<nv;i++){u32 f=fs[i];int rep=1;for(long h=0;h<nh&&rep;h++){u32 (*t)[256]=HT[h];u32 g=t[0][f&255]|t[1][(f>>8)&255]|t[2][(f>>16)&255]|t[3][f>>24];if(g>>(N-1)&1)g=~g&F;if(g<f)rep=0;}isrep[i]=rep;nrep+=rep;}
  printf("N %d L %d: %ld orbits, normaliser %ld, %ld representatives (%.1f s)\n",N,L,nv,nh,nrep,wtime()-t0);fflush(stdout);
  long totdeg=0;int gbix[16];
  #pragma omp parallel
  { int*cand=malloc(sizeof(int)*nv);long lc[16];memset(lc,0,sizeof lc);int lbest=0;int lbix[16];int cl[16];
    #pragma omp for schedule(dynamic,8) reduction(+:totdeg)
    for(long v=0;v<nv;v++){ if(!isrep[v])continue;const u32*Rv=R+(size_t)v*L;int n=0;
      for(long j=0;j<nv;j++){if(j==v)continue;if(pairok(Rv,R+(size_t)j*L))cand[n++]=j;}
      totdeg+=n;cl[0]=v;dfs(1,cl,cand,n,lc,&lbest,&lbix);}
    #pragma omp critical
    {for(int d=0;d<16;d++)cntm[d]+=lc[d];if(lbest>bestm){bestm=lbest;memcpy(gbix,lbix,sizeof gbix);}}
    free(cand);
  }
  if(bestm>=1)wr(bestm,gbix);
  printf("shape");for(int a=4;a<ac;a++)printf(" %s",av[a]);printf(": avg degree of reps %.1f; cliques through reps by size:",(double)totdeg/(nrep?nrep:1));for(int d=1;d<=want;d++)printf(" %d:%ld",d,cntm[d]);
  printf("; MAX full orbits %d = %d columns (%.1f s)\n",bestm,bestm*L,wtime()-t0);
  return 0;}
