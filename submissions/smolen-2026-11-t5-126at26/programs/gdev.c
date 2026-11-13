// gdev.c (eager126, 2026-11-13): group-developed complement-doubled arrays for strength 5.
// Array: rows x in G (abelian, product of cyclic groups) plus optional constant border row; columns d in G; A[x][d]=f(x+d); rows doubled by complement.
// A 5-set of columns is covered iff the four sums c_a^c_b, c_a^c_c, c_a^c_d, c_a^c_e take all 16 values on the rows of A.
// usage: gdev MODULI BORDER MODE SEED ITERS T [FFILE] [K]
//   MODULI like 2,2,2,2,2,2 or 63 or 65 or 5,13 ; BORDER 0/1
//   MODE scan : read f from FFILE (n chars 0/1), print missing events on 5-sets containing 0 and total bad 5-sets, write bad.bin (all bad 5-sets, 5 bytes each)
//   MODE sa   : anneal f (start FFILE or random if FFILE is "-") on a random sample of SAMPLE (env, default 30000) shapes containing 0; prints best f
//   MODE joint: anneal f and a K-subset D of columns, objective = missing events over all 5-subsets of D (start FFILE or random); prints f and D
// env BAL=1 keeps f balanced with swaps (sa/joint); env DFILE=file with K column indices to start joint from.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>
typedef struct{uint64_t a,b;}W;
static uint64_t rs=88172645463325252ULL; static inline uint64_t rnd(){rs^=rs<<13;rs^=rs>>7;rs^=rs<<17;return rs;}
static int n,R,border; static int addt[130][130]; static char f[130]; static W col[130]; static W full;
static void build(){for(int d=0;d<n;d++){W c={0,0};for(int x=0;x<n;x++)if(f[addt[x][d]]){if(x<64)c.a|=1ULL<<x;else c.b|=1ULL<<(x-64);}
  if(border){int x=n;if(x<64)c.a|=1ULL<<x;else c.b|=1ULL<<(x-64);}col[d]=c;}}
static inline int miss5(int a,int b,int c,int d,int e){ // number of missing classes (0..15)
  W g1={col[a].a^col[b].a,col[a].b^col[b].b},g2={col[a].a^col[c].a,col[a].b^col[c].b},g3={col[a].a^col[d].a,col[a].b^col[d].b},g4={col[a].a^col[e].a,col[a].b^col[e].b};
  int m=0; W p[4];
  p[0].a=~g1.a&~g2.a&full.a;p[0].b=~g1.b&~g2.b&full.b;p[1].a=g1.a&~g2.a;p[1].b=g1.b&~g2.b;p[2].a=~g1.a&g2.a&full.a;p[2].b=~g1.b&g2.b&full.b;p[3].a=g1.a&g2.a;p[3].b=g1.b&g2.b;
  for(int i=0;i<4;i++){uint64_t xa=p[i].a,xb=p[i].b;
    if(!((xa&~g3.a&~g4.a)|(xb&~g3.b&~g4.b)))m++; if(!((xa&g3.a&~g4.a)|(xb&g3.b&~g4.b)))m++;
    if(!((xa&~g3.a&g4.a)|(xb&~g3.b&g4.b)))m++; if(!((xa&g3.a&g4.a)|(xb&g3.b&g4.b)))m++;}
  return m;}
int main(int ac,char**av){ if(ac<7){fprintf(stderr,"usage\n");return 2;}
  int mod[8],nm=0;{char*s=strdup(av[1]);for(char*t=strtok(s,",");t;t=strtok(0,","))mod[nm++]=atoi(t);}
  n=1;for(int i=0;i<nm;i++)n*=mod[i]; border=atoi(av[2]); R=n+border; if(R>128){fprintf(stderr,"too many rows\n");return 2;}
  for(int x=0;x<n;x++)for(int y=0;y<n;y++){int r=0,mul=1,xx=x,yy=y;for(int i=0;i<nm;i++){int s=(xx%mod[i]+yy%mod[i])%mod[i];r+=s*mul;mul*=mod[i];xx/=mod[i];yy/=mod[i];}addt[x][y]=r;}
  for(int x=0;x<R;x++){if(x<64)full.a|=1ULL<<x;else full.b|=1ULL<<(x-64);}
  char*mode=av[3];long seed=atol(av[4]),M=atol(av[5]);double T=atof(av[6]);rs^=(uint64_t)(seed+1)*0x9E3779B97F4A7C15ULL;for(int i=0;i<20;i++)rnd();
  int bal=getenv("BAL")?atoi(getenv("BAL")):0; double TE=getenv("TEND")?atof(getenv("TEND")):T; // geometric cooling T -> TEND
  if(ac>7&&strcmp(av[7],"-")&&strcmp(mode,"cls")){FILE*g=fopen(av[7],"r");int i=0,ch;while(i<n&&(ch=fgetc(g))!=EOF)if(ch=='0'||ch=='1')f[i++]=ch-'0';fclose(g);if(i<n){fprintf(stderr,"short f\n");return 2;}}
  else{for(int i=0;i<n;i++)f[i]=i&1;for(int i=n-1;i>0;i--){int j=rnd()%(i+1);char t=f[i];f[i]=f[j];f[j]=t;}if(!bal)for(int i=0;i<n;i++)f[i]=rnd()&1;}
  build();
  if(!strcmp(mode,"scan")){long ev=0,bs=0,tot=0;for(int b=1;b<n;b++)for(int c=b+1;c<n;c++)for(int d=c+1;d<n;d++)for(int e=d+1;e<n;e++){int m=miss5(0,b,c,d,e);tot++;ev+=m;if(m)bs++;}
    printf("n=%d rows=%d shapes0=%ld bad0=%ld (%.4g) missing_events0=%ld\n",n,2*R,tot,bs,(double)bs/tot,ev);
    FILE*g=fopen("bad.bin","wb");long bad=0,all=0;for(int a=0;a<n;a++)for(int b=a+1;b<n;b++)for(int c=b+1;c<n;c++)for(int d=c+1;d<n;d++)for(int e=d+1;e<n;e++){all++;if(miss5(a,b,c,d,e)){bad++;unsigned char o[5]={a,b,c,d,e};fwrite(o,1,5,g);}}
    fclose(g);printf("all 5-sets=%ld bad=%ld (%.4g)\n",all,bad,(double)bad/all);return 0;}
  if(!strcmp(mode,"sa")){int S=getenv("SAMPLE")?atoi(getenv("SAMPLE")):30000;int(*sh)[4]=malloc(sizeof(int[4])*S);
    for(int i=0;i<S;i++){int v[4];for(;;){for(int j=0;j<4;j++)v[j]=1+rnd()%(n-1);if(v[0]!=v[1]&&v[0]!=v[2]&&v[0]!=v[3]&&v[1]!=v[2]&&v[1]!=v[3]&&v[2]!=v[3])break;}memcpy(sh[i],v,sizeof v);}
    long cost=0;for(int i=0;i<S;i++)cost+=miss5(0,sh[i][0],sh[i][1],sh[i][2],sh[i][3]);long best=cost;char bf[130];memcpy(bf,f,n);
    for(long it=0;it<M&&best>0;it++){int i=rnd()%n,j=-1;if(bal){do j=rnd()%n;while(f[j]==f[i]);f[j]^=1;}f[i]^=1;build();
      long c2=0;for(int k=0;k<S;k++)c2+=miss5(0,sh[k][0],sh[k][1],sh[k][2],sh[k][3]);
      if(c2<=cost||(double)(rnd()>>11)/9007199254740992.0<exp(-(c2-cost)/(T*pow(TE/T,(double)it/M)))){cost=c2;if(cost<best){best=cost;memcpy(bf,f,n);}}else{f[i]^=1;if(j>=0)f[j]^=1;}
      if(it%2000==0){fprintf(stderr,"it %ld cost %ld best %ld\n",it,cost,best);}}
    printf("best %ld of %d shapes (missing events) f=",best,S);for(int i=0;i<n;i++)putchar('0'+bf[i]);printf("\n");return 0;}
  if(!strcmp(mode,"joint")){int K=ac>8?atoi(av[8]):26;int D[130],O[130],in[130]={0};int perm[130];for(int i=0;i<n;i++)perm[i]=i;for(int i=n-1;i>0;i--){int j=rnd()%(i+1);int t=perm[i];perm[i]=perm[j];perm[j]=t;}
    if(getenv("DFILE")){FILE*g=fopen(getenv("DFILE"),"r");for(int i=0;i<K;i++){if(fscanf(g,"%d",&D[i])!=1)return 2;in[D[i]]=1;}fclose(g);}else for(int i=0;i<K;i++){D[i]=perm[i];in[perm[i]]=1;}
    int no=0;for(int i=0;i<n;i++)if(!in[i])O[no++]=i;
    #define EVAL(c) {c=0;for(int a=0;a<K;a++)for(int b=a+1;b<K;b++)for(int cc=b+1;cc<K;cc++)for(int d=cc+1;d<K;d++)for(int e=d+1;e<K;e++)c+=miss5(D[a],D[b],D[cc],D[d],D[e]);}
    long cost;EVAL(cost);long best=cost;char bf[130];int bD[130];memcpy(bf,f,n);memcpy(bD,D,sizeof D);double pf=getenv("PF")?atof(getenv("PF")):0.5;
    for(long it=0;it<M&&best>0;it++){int kind=((double)(rnd()>>11)/9007199254740992.0)<pf;int i=0,j=-1,a=0,b=0;
      if(kind){i=rnd()%n;if(bal){do j=rnd()%n;while(f[j]==f[i]);f[j]^=1;}f[i]^=1;build();}else{a=rnd()%K;b=rnd()%no;int t=D[a];D[a]=O[b];O[b]=t;}
      long c2;EVAL(c2);
      if(c2<=cost||(double)(rnd()>>11)/9007199254740992.0<exp(-(c2-cost)/(T*pow(TE/T,(double)it/M)))){cost=c2;if(cost<best){best=cost;memcpy(bf,f,n);memcpy(bD,D,sizeof D);}}
      else{if(kind){f[i]^=1;if(j>=0)f[j]^=1;build();}else{int t=D[a];D[a]=O[b];O[b]=t;}}
      if(it%500==0)fprintf(stderr,"it %ld cost %ld best %ld\n",it,cost,best);}
    printf("best %ld missing class events (real holes = 2x) f=",best);for(int i=0;i<n;i++)putchar('0'+bf[i]);printf(" D=");for(int i=0;i<K;i++)printf(" %d",bD[i]);printf("\n");return 0;}
  if(!strcmp(mode,"cls")){ // av[7]=class file (n ints: class id per element). exhaustive over class assignments if k<=22 (class 0 fixed to 0), else SA by class flips. prints TOP best.
    int cl[130],k=0;{FILE*g=fopen(av[7],"r");for(int i=0;i<n;i++){if(fscanf(g,"%d",&cl[i])!=1)return 2;if(cl[i]+1>k)k=cl[i]+1;}fclose(g);}
    int S=getenv("SAMPLE")?atoi(getenv("SAMPLE")):30000;int(*sh)[4]=malloc(sizeof(int[4])*S);
    for(int i=0;i<S;i++){int v[4];for(;;){for(int j=0;j<4;j++)v[j]=1+rnd()%(n-1);if(v[0]!=v[1]&&v[0]!=v[2]&&v[0]!=v[3]&&v[1]!=v[2]&&v[1]!=v[3]&&v[2]!=v[3])break;}memcpy(sh[i],v,sizeof v);}
    #define CEV(c,m) {for(int i=0;i<n;i++)f[i]=((m)>>cl[i])&1;build();c=0;for(int q=0;q<S;q++)c+=miss5(0,sh[q][0],sh[q][1],sh[q][2],sh[q][3]);}
    int TOP=getenv("TOP")?atoi(getenv("TOP")):10; long bc[64];uint64_t bm[64];int nb=0;
    #define REC(c,m) {int pos=nb;while(pos>0&&bc[pos-1]>c)pos--;if(pos<TOP){int dup=0;for(int z=0;z<nb;z++)if(bm[z]==(m))dup=1;if(!dup){if(nb<TOP)nb++;for(int z=nb-1;z>pos;z--){bc[z]=bc[z-1];bm[z]=bm[z-1];}bc[pos]=c;bm[pos]=(m);}}}
    if(k<=22){for(uint64_t m=0;m<(1ULL<<k);m+=2){long c;CEV(c,m);REC(c,m);}}
    else{uint64_t m=rnd()&((1ULL<<k)-2);long cost;CEV(cost,m);for(long it=0;it<M;it++){uint64_t m2=m^(1ULL<<(1+rnd()%(k-1)));long c2;CEV(c2,m2);
        if(c2<=cost||(double)(rnd()>>11)/9007199254740992.0<exp(-(c2-cost)/(T*pow(TE/T,(double)it/M)))){cost=c2;m=m2;REC(cost,m);}}}
    printf("classes %d sample %d\n",k,S);for(int z=0;z<nb;z++){printf("%ld f=",bc[z]);for(int i=0;i<n;i++)putchar('0'+(int)((bm[z]>>cl[i])&1));printf("\n");}return 0;}
  return 2;}
