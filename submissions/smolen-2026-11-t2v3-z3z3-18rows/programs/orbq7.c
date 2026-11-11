/* orbq7.c = orbq6.c + logged free-candidate maximum and overflow count (item123 step 8). orbq6.c  exact orbit-graph clique search for ternary strength-2 covering arrays, own code (item123, 2026-11-10).
   Rebuild of the idea of debate 16 agent A's orbq5 (source lost), generalised to any row group.
   Rows 0..N-1. Group G of row permutations given in a spec file. Column orbits of full length |G|.
   Vertex = self-compatible full column orbit (up to symbol relabelling). Edge = every column of one orbit
   is qualitatively independent (QI) of every column of the other. m-clique = N x m|G| covering array.
   For every m-clique (up to the given normaliser) list all free columns QI with all its columns, and the
   largest mutually QI set of them (exact).
   usage: orbq6 SPEC m nfree prefix [mod res] [secs]
   SPEC: line1: N ; then lines "g p0 p1 ... pN-1" (generators of G), lines "h p0 ... pN-1" (normaliser generators).
   env V=3 fixed. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
typedef unsigned int u32; typedef unsigned long long u64;
#define MAXG 128
#define MAXH 64
static int N,G,NH,M,NFREE;
typedef struct{int p[32];u32 t[4][256];}Perm;
static Perm ge[MAXG],hh[MAXH];
static void mk(Perm*P){memset(P->t,0,sizeof P->t);for(int r=0;r<N;r++){int s=P->p[r];for(int v=0;v<256;v++)if(v>>(s&7)&1)P->t[s>>3][v]|=1u<<r;}}
static inline u32 app(const Perm*P,u32 m){return P->t[0][m&255]|P->t[1][(m>>8)&255]|P->t[2][(m>>16)&255]|P->t[3][m>>24];}
static inline int qi(const u32*a,const u32*b){return (a[0]&b[0])&&(a[0]&b[1])&&(a[0]&b[2])&&(a[1]&b[0])&&(a[1]&b[1])&&(a[1]&b[2])&&(a[2]&b[0])&&(a[2]&b[1])&&(a[2]&b[2]);}
static inline u64 key(const u32*m){u32 a=m[0],b=m[1],c=m[2],t;
  if(__builtin_ctz(b)<__builtin_ctz(a)){t=a;a=b;b=t;} if(__builtin_ctz(c)<__builtin_ctz(a)){t=a;a=c;c=t;}
  if(__builtin_ctz(c)<__builtin_ctz(b)){t=b;b=c;c=t;} return ((u64)a<<32)|b;}
static u32 *sm; static long V=0,cap=0; /* sm[(v*G+e)*3+a] */
static u64 nstart=0;
static void leaf(u32 m0,u32 m1,u32 m2){
  nstart++;
  if(__builtin_popcount(m0)<3||__builtin_popcount(m1)<3||__builtin_popcount(m2)<3)return;
  u32 x[3]={m0,m1,m2}; u64 kx=key(x); u32 s[MAXG][3];
  for(int e=1;e<G;e++){s[e][0]=app(&ge[e],m0);s[e][1]=app(&ge[e],m1);s[e][2]=app(&ge[e],m2);
    if(key(s[e])<=kx)return; if(!qi(x,s[e]))return;}
  if(V==cap){cap=cap?cap*2:1<<16;sm=realloc(sm,(size_t)cap*G*3*sizeof(u32));if(!sm){fprintf(stderr,"oom\n");exit(1);}}
  u32*d=sm+(size_t)V*G*3; d[0]=m0;d[1]=m1;d[2]=m2; for(int e=1;e<G;e++){d[e*3]=s[e][0];d[e*3+1]=s[e][1];d[e*3+2]=s[e][2];}
  V++;
}
static void rec(int r,u32 m0,u32 m1,u32 m2,int mx){
  if(r==N){leaf(m0,m1,m2);return;}
  /* count pruning */
  int need=(3-__builtin_popcount(m0)>0?3-__builtin_popcount(m0):0)+(3-__builtin_popcount(m1)>0?3-__builtin_popcount(m1):0)+(3-__builtin_popcount(m2)>0?3-__builtin_popcount(m2):0);
  if(need>N-r)return;
  rec(r+1,m0|1u<<r,m1,m2,mx);
  if(mx>=1)rec(r+1,m0,m1|1u<<r,m2,mx<2?2:mx);
  if(mx>=2)rec(r+1,m0,m1,m2|1u<<r,mx);
}
/* hash */
static u64*hk; static int*hv; static u64 hmask;
static void hput(u64 k,int v){u64 i=(k*0x9E3779B97F4A7C15ull)>>20&hmask;while(hv[i]>=0)i=(i+1)&hmask;hk[i]=k;hv[i]=v;}
static int hget(u64 k){u64 i=(k*0x9E3779B97F4A7C15ull)>>20&hmask;while(hv[i]>=0){if(hk[i]==k)return hv[i];i=(i+1)&hmask;}return -1;}
static int*uf; static int fnd(int x){while(uf[x]!=x){uf[x]=uf[uf[x]];x=uf[x];}return x;}
static inline const u32* S(int v,int e){return sm+((size_t)v*G+e)*3;}
static inline int adj(int u,int w){const u32*a=S(u,0);const u32*b=S(w,0);for(int e=0;e<G;e++)if(!qi(a,b+e*3))return 0;return 1;}
/* free columns */
static u32 C[1024][3]; static int nC;
static int lst[32][3][512],nl[32][3]; /* sets (c*3+a) whose k-th from last row is r */
static u32 cand[4096][3]; static int ncand; static long candtotal,maxcand=0,ncapped=0;
static void frec(int r,u32 y0,u32 y1,u32 y2,int mx){
  if(r>0){int q=r-1;u32 y[3]={y0,y1,y2};
    for(int i=0;i<nl[q][0];i++){int id=lst[q][0][i];u32 s=C[id/3][id%3];if(!(s&y0)||!(s&y1)||!(s&y2))return;}
    for(int i=0;i<nl[q][1];i++){int id=lst[q][1][i];u32 s=C[id/3][id%3];if(!(s&y0)+!(s&y1)+!(s&y2)>1)return;}
    for(int i=0;i<nl[q][2];i++){int id=lst[q][2][i];u32 s=C[id/3][id%3];if(!(s&y0)+!(s&y1)+!(s&y2)>2)return;}
    (void)y;}
  if(r==N){candtotal++;if(ncand<4096){cand[ncand][0]=y0;cand[ncand][1]=y1;cand[ncand][2]=y2;ncand++;}return;}
  frec(r+1,y0|1u<<r,y1,y2,mx);
  if(mx>=1)frec(r+1,y0,y1|1u<<r,y2,mx<2?2:mx);
  if(mx>=2)frec(r+1,y0,y1,y2|1u<<r,mx);
}
static int fbest,fcur[64],fsel[64]; static unsigned char fa[4096][4096/8];
static void fcl(int d,int*cd,int n){ if(d>fbest){fbest=d;memcpy(fsel,fcur,sizeof(int)*d);} if(d+n<=fbest||fbest>=NFREE)return;
  for(int i=0;i<n;i++){ if(d+n-i<=fbest)return; int u=cd[i]; fcur[d]=u; int nc[n],k=0; for(int j=i+1;j<n;j++)if(fa[u][cd[j]>>3]>>(cd[j]&7)&1)nc[k++]=cd[j]; fcl(d+1,nc,k); if(fbest>=NFREE)return;}}
static int best=0; static long ncl=0,hist[65]; static char*prefix; static int clq[64];
static void dump(int nf){char fn[512];snprintf(fn,512,"%s_dump_%d_%d.txt",prefix,N,nC+nf);FILE*f=fopen(fn,"w");
  for(int r=0;r<N;r++){for(int c=0;c<nC;c++)fprintf(f,"%d ",(C[c][1]>>r&1)+2*(C[c][2]>>r&1));
    for(int i=0;i<nf;i++){u32*y=cand[fsel[i]];fprintf(f,"%d ",(y[1]>>r&1)+2*(y[2]>>r&1));}fprintf(f,"\n");}fclose(f);
  printf("DUMP %s  (%d orbit columns + %d free)\n",fn,nC,nf);fflush(stdout);}
static void handle(void){
  ncl++; nC=0; for(int i=0;i<M;i++)for(int e=0;e<G;e++){memcpy(C[nC],S(clq[i],e),12);nC++;}
  int nf=0;
  if(NFREE>0){
    memset(nl,0,sizeof nl);
    for(int c=0;c<nC;c++)for(int a=0;a<3;a++){u32 s=C[c][a];for(int k=0;k<3;k++){int r=31-__builtin_clz(s);lst[r][k][nl[r][k]++]=c*3+a;s&=~(1u<<r);if(!s)break;}}
    ncand=0; candtotal=0; frec(1,1,0,0,1); if(candtotal>maxcand)maxcand=candtotal; if(candtotal>4095)ncapped++;
    if(ncand){ if(ncand>4095)ncand=4095; for(int i=0;i<ncand;i++)memset(fa[i],0,(ncand+7)/8);
      for(int i=0;i<ncand;i++)for(int j=i+1;j<ncand;j++)if(qi(cand[i],cand[j])){fa[i][j>>3]|=1<<(j&7);fa[j][i>>3]|=1<<(i&7);}
      int cd[4096];for(int i=0;i<ncand;i++)cd[i]=i; fbest=0; fcl(0,cd,ncand); nf=fbest; }
    hist[nf>64?64:nf]++;
  }
  if(nC+nf>best){best=nC+nf;printf("clique #%ld: %d orbit columns, %d free candidates, %d mutually QI -> %d columns\n",ncl,nC,ncand,nf,best);dump(nf);}
}
static int maxdepth=0; static int **cbuf; static double tlimit; static clock_t t0; static int timedout=0;
static void ext(int d,int*cd,int n){
  if(d>maxdepth){maxdepth=d;}
  if(d==M){handle();return;}
  if(d+n<M)return;
  for(int i=0;i<n;i++){ if(d+1+(n-i-1)<M)return; int u=cd[i]; clq[d]=u;
    if(d+1==M){handle();continue;}
    int*nc=cbuf[d+1];int k=0; for(int j=i+1;j<n;j++)if(adj(u,cd[j]))nc[k++]=cd[j];
    if(d+1+k>=M) ext(d+1,nc,k); else if(d+1>maxdepth)maxdepth=d+1;
    if((i&63)==0&&(double)(clock()-t0)/CLOCKS_PER_SEC>tlimit){timedout=1;return;}
    if(timedout)return; }
}
/* bitset clique search with greedy colouring bound inside a second-level neighbourhood */
static u64*bm; static int bw,n2; static int*n2v; static u64**Pb; static int**ordb,**colb; static long bcap=0;
static void bext(int d,u64*P){
  if(d>maxdepth)maxdepth=d;
  if(d==M){handle();return;}
  int cnt=0;for(int w=0;w<bw;w++)cnt+=__builtin_popcountll(P[w]); if(d+cnt<M)return;
  int*ord=ordb[d],*col=colb[d]; u64*U=Pb[d]+bw,*Q=Pb[d]+2*bw,*NP=Pb[d+1]; memcpy(U,P,bw*8); int idx=0,k=0,left=cnt;
  while(left){k++;memcpy(Q,U,bw*8);
    for(int w=0;w<bw;w++){while(Q[w]){int b=__builtin_ctzll(Q[w]);int v=w*64+b;Q[w]&=~(1ull<<b);U[w]&=~(1ull<<b);
      u64*a=bm+(size_t)v*bw;for(int x=w;x<bw;x++)Q[x]&=~a[x];ord[idx]=v;col[idx]=k;idx++;left--;}}}
  for(int i=cnt-1;i>=0;i--){ if(d+col[i]<M)return; int v=ord[i]; clq[d]=n2v[v];
    u64*a=bm+(size_t)v*bw; for(int w=0;w<bw;w++)NP[w]=P[w]&a[w];
    bext(d+1,NP); P[v>>6]&=~(1ull<<(v&63)); if(timedout)return; }
}
static u64*BM; static long BMcap=0; static int*posb; static int*vidb;
static void level2(int*c1,int k){
  int bwk=(k+63)/64; if((long)k*bwk>BMcap){BMcap=(long)k*bwk;free(BM);BM=malloc((size_t)BMcap*8);if(!BM){fprintf(stderr,"oom BM k=%d\n",k);exit(1);}}
  memset(BM,0,(size_t)k*bwk*8);
  for(int a=0;a<k;a++){const int ua=c1[a];u64*ra=BM+(size_t)a*bwk;for(int b=a+1;b<k;b++)if(adj(ua,c1[b])){ra[b>>6]|=1ull<<(b&63);BM[(size_t)b*bwk+(a>>6)]|=1ull<<(a&63);}}
  if(!posb){posb=malloc(sizeof(int)*V);vidb=malloc(sizeof(int)*V);}
  for(int i=0;i<k&&!timedout;i++){ if(1+(k-i)<M)return; clq[1]=c1[i]; int m2=0; u64*ri=BM+(size_t)i*bwk;
    for(int w=i>>6;w<bwk;w++){u64 x=ri[w];while(x){int bb=__builtin_ctzll(x);x&=x-1;int j=w*64+bb;if(j>i){posb[m2]=j;vidb[m2]=c1[j];m2++;}}}
    if(maxdepth<2)maxdepth=2;
    if(2+m2<M)continue;
    n2=m2;n2v=vidb;bw=(m2+63)/64; if((long)m2*bw>bcap){bcap=(long)m2*bw;bm=realloc(bm,bcap*8);}
    memset(bm,0,(size_t)m2*bw*8);
    for(int a=0;a<m2;a++){u64*ra=BM+(size_t)posb[a]*bwk;u64*da=bm+(size_t)a*bw;for(int b=a+1;b<m2;b++){int j=posb[b];if(ra[j>>6]>>(j&63)&1){da[b>>6]|=1ull<<(b&63);bm[(size_t)b*bw+(a>>6)]|=1ull<<(a&63);}}}
    for(int d=0;d<=M+1;d++){Pb[d]=realloc(Pb[d],(size_t)bw*3*8);ordb[d]=realloc(ordb[d],sizeof(int)*(m2+1));colb[d]=realloc(colb[d],sizeof(int)*(m2+1));}
    u64*P=Pb[2];memset(P,0,bw*8);for(int a2=0;a2<m2;a2++)P[a2>>6]|=1ull<<(a2&63);
    if(M==2)handle(); else bext(2,P);
    if((i&255)==0&&(double)(clock()-t0)/CLOCKS_PER_SEC>tlimit)timedout=1; }
}
int main(int argc,char**argv){
  if(argc<5){fprintf(stderr,"usage: orbq6 SPEC m nfree prefix [mod res] [secs]\n");return 1;}
  FILE*f=fopen(argv[1],"r"); M=atoi(argv[2]); NFREE=atoi(argv[3]); prefix=argv[4];
  int mod=argc>6?atoi(argv[5]):1,res=argc>6?atoi(argv[6]):0; tlimit=argc>7?atof(argv[7]):1e18; t0=clock();
  if(fscanf(f,"%d",&N)!=1)return 1; Perm gens[16];int ng=0; NH=0; char tag[8];
  while(fscanf(f,"%7s",tag)==1){Perm*P=tag[0]=='g'?&gens[ng++]:&hh[NH++];for(int r=0;r<N;r++)if(fscanf(f,"%d",&P->p[r])!=1)return 1;mk(P);}
  /* closure */
  G=1;for(int r=0;r<N;r++)ge[0].p[r]=r; mk(&ge[0]);
  for(int i=0;i<G;i++)for(int g=0;g<ng;g++){Perm q;for(int r=0;r<N;r++)q.p[r]=ge[i].p[gens[g].p[r]];int fnd_=0;for(int j=0;j<G;j++)if(!memcmp(q.p,ge[j].p,sizeof(int)*N)){fnd_=1;break;}
    if(!fnd_){if(G>=MAXG){fprintf(stderr,"group too big\n");return 1;}ge[G]=q;mk(&ge[G]);G++;}}
  printf("N=%d |G|=%d normaliser gens=%d target m=%d nfree=%d\n",N,G,NH,M,NFREE);fflush(stdout);
  rec(1,1,0,0,1);
  printf("starters %llu, vertices %ld  (%.1f s)\n",nstart,V,(double)(clock()-t0)/CLOCKS_PER_SEC);fflush(stdout);
  if(!V){printf("EXACT MAX 0\n");return 0;}
  int hb=1;while((1L<<hb)<V*2)hb++; hmask=(1ull<<hb)-1; hk=malloc(sizeof(u64)<<hb);hv=malloc(sizeof(int)<<hb);for(u64 i=0;i<=hmask;i++)hv[i]=-1;
  for(long v=0;v<V;v++)hput(key(S(v,0)),v);
  uf=malloc(sizeof(int)*V);for(long v=0;v<V;v++)uf[v]=v;
  for(int h=0;h<NH;h++)for(long v=0;v<V;v++){u32 y[3];const u32*x=S(v,0);y[0]=app(&hh[h],x[0]);y[1]=app(&hh[h],x[1]);y[2]=app(&hh[h],x[2]);
    u64 kb=~0ull;for(int e=0;e<G;e++){u32 z[3]={app(&ge[e],y[0]),app(&ge[e],y[1]),app(&ge[e],y[2])};u64 k=key(z);if(k<kb)kb=k;}
    int u=hget(kb);if(u<0){fprintf(stderr,"normaliser generator %d does not preserve the vertex set\n",h);return 1;}
    int a=fnd(v),b=fnd(u);if(a!=b){if(a<b)uf[b]=a;else uf[a]=b;}}
  int*rank=malloc(sizeof(int)*V);int*rep=malloc(sizeof(int)*V);int nr=0;
  for(long v=0;v<V;v++)if(fnd(v)==v){rank[v]=nr;rep[nr++]=v;} for(long v=0;v<V;v++)rank[v]=rank[fnd(v)];
  printf("normaliser orbits (representatives) %d\n",nr);fflush(stdout);
  if(!getenv("NOORDER")){ /* order representatives by sampled degree, ascending (hubs last, when few vertices are left) */
    int ns=V<20000?V:20000; long step=V/ns; int*dg=malloc(sizeof(int)*nr); int*ordr=malloc(sizeof(int)*nr);
    for(int i=0;i<nr;i++){int c=0;for(int j=0;j<ns;j++){long u=j*step;if(u!=rep[i]&&adj(rep[i],u))c++;}dg[i]=c;ordr[i]=i;}
    /* simple sort */
    for(int gap=nr/2;gap>0;gap/=2)for(int i=gap;i<nr;i++){int t=ordr[i],j=i;while(j>=gap&&dg[ordr[j-gap]]>dg[t]){ordr[j]=ordr[j-gap];j-=gap;}ordr[j]=t;}
    int*newrank=malloc(sizeof(int)*nr);int*newrep=malloc(sizeof(int)*nr);
    for(int i=0;i<nr;i++){newrank[ordr[i]]=i;newrep[i]=rep[ordr[i]];}
    for(long v=0;v<V;v++)rank[v]=newrank[rank[v]]; memcpy(rep,newrep,sizeof(int)*nr);
    printf("ordered by sampled degree (%.0f s)\n",(double)(clock()-t0)/CLOCKS_PER_SEC);fflush(stdout);
  }
  Pb=calloc(M+3,sizeof(u64*));ordb=calloc(M+3,sizeof(int*));colb=calloc(M+3,sizeof(int*));
  cbuf=malloc(sizeof(int*)*(M+2));for(int d=0;d<=M+1;d++)cbuf[d]=malloc(sizeof(int)*V);
  int done=0;
  for(int i=0;i<nr&&!timedout;i++){ if(i%mod!=res)continue; int v=rep[i]; clq[0]=v; int*c1=cbuf[1];int k=0;
    for(long u=0;u<V;u++)if(rank[u]>=i&&u!=v&&adj(v,u))c1[k++]=u;
    if(k>20000){printf("rep %d deg %d ... %.0f s\n",i,k,(double)(clock()-t0)/CLOCKS_PER_SEC);fflush(stdout);}
    if(M==1)handle(); else if(M==2){if(1+k>=M)ext(1,c1,k);} else if(1+k>=M)level2(c1,k);
    done++;
    if(done%20==0||k>20000){printf("rep %d/%d deg %d cliques %ld best %d maxdepth %d  %.0f s\n",i,nr,k,ncl,best,maxdepth,(double)(clock()-t0)/CLOCKS_PER_SEC);fflush(stdout);}
    if((double)(clock()-t0)/CLOCKS_PER_SEC>tlimit)timedout=1; }
  printf("%s: m-cliques (up to normaliser, as enumerated) %ld, largest clique seen %d, best columns %d\n",timedout?"PARTIAL (time limit)":"EXACT COMPLETE",ncl,maxdepth,best);
  if(NFREE>0){printf("largest free-candidate list %ld (cap 4095), cliques over the cap %ld\n",maxcand,ncapped);printf("free-column histogram:");for(int i=0;i<=64;i++)if(hist[i])printf(" %d:%ld",i,hist[i]);printf("\n");}
  return 0;
}
