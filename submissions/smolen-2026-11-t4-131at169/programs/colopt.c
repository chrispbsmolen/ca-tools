// colopt FILE K N MAXM T moves seed : optimise one new column (N bits) minimizing monochrome triple-pattern row sets (m<=MAXM)
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
typedef struct{uint64_t w[3];}B;
int N,K;B col[256];
static unsigned long long s=88172645463325252ULL; static inline unsigned long long rnd(){s^=s<<13;s^=s>>7;s^=s<<17;return s;}
int main(int argc,char**argv){FILE*f=fopen(argv[1],"r");K=atoi(argv[2]);N=atoi(argv[3]);int MAXM=atoi(argv[4]);double T=atof(argv[5]);long moves=atol(argv[6]);s^=atol(argv[7])*0x9E3779B97F4A7C15ULL;
 for(int r=0;r<N;r++)for(int c=0;c<K;c++){int b;if(fscanf(f,"%d",&b)!=1)return 1;if(b)col[c].w[r>>6]|=1ULL<<(r&63);}
 B ones;memset(&ones,0,sizeof ones);for(int r=0;r<N;r++)ones.w[r>>6]|=1ULL<<(r&63);
 long cap=1<<22,ns=0;B*sets=malloc(cap*sizeof(B));
 for(int a=0;a<K;a++)for(int b=a+1;b<K;b++)for(int c=b+1;c<K;c++)for(int p=0;p<8;p++){B m=ones;int cs[3]={a,b,c};
  for(int i=0;i<3;i++)for(int w=0;w<3;w++)m.w[w]&=((p>>i)&1)?col[cs[i]].w[w]:~col[cs[i]].w[w];
  int n=__builtin_popcountll(m.w[0])+__builtin_popcountll(m.w[1])+__builtin_popcountll(m.w[2]);
  if(n<=MAXM){if(ns==cap){cap*=2;sets=realloc(sets,cap*sizeof(B));}sets[ns++]=m;}}
 fprintf(stderr,"sets %ld\n",ns);
 // incidence
 int *cnt=calloc(N,4);long **inc=malloc(N*sizeof(long*));
 for(long i=0;i<ns;i++)for(int r=0;r<N;r++)if((sets[i].w[r>>6]>>(r&63))&1)cnt[r]++;
 for(int r=0;r<N;r++){inc[r]=malloc(8*(cnt[r]+1));cnt[r]=0;}
 int *sz=malloc(ns*4),*n1=calloc(ns,4);
 unsigned char x[256];for(int r=0;r<N;r++)x[r]=rnd()&1;
 for(long i=0;i<ns;i++){int z=0;for(int r=0;r<N;r++)if((sets[i].w[r>>6]>>(r&63))&1){inc[r][cnt[r]++]=i;z++;if(x[r])n1[i]++;}sz[i]=z;}
 long cost=0;for(long i=0;i<ns;i++)cost+=(n1[i]==0||n1[i]==sz[i]);
 long best=cost;fprintf(stderr,"start %ld\n",cost);
 for(long it=0;it<moves&&cost>0;it++){int r=rnd()%N;long d=0;int nb=!x[r];
  for(int j=0;j<cnt[r];j++){long i=inc[r][j];int o=n1[i],nw=o+(nb?1:-1);d+=((nw==0||nw==sz[i])-(o==0||o==sz[i]));}
  if(d<=0||(rnd()>>11)*(1.0/9007199254740992.0)<exp(-d/T)){for(int j=0;j<cnt[r];j++){long i=inc[r][j];n1[i]+=nb?1:-1;}x[r]=nb;cost+=d;if(cost<best){best=cost;}}
  if(it%20000==0)fprintf(stderr,"it %ld cost %ld best %ld\n",it,cost,best);}
 printf("final %ld best %ld\n",cost,best);for(int r=0;r<N;r++)putchar('0'+x[r]);puts("");}
