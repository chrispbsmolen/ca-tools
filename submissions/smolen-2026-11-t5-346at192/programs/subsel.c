// subsel.c: choose k of q columns minimizing the number of listed pairs fully inside. usage: subsel q k pairs.txt moves seed T out.txt
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
static unsigned long long s=88172645463325252ULL; static inline unsigned long long rnd(){s^=s<<13;s^=s>>7;s^=s<<17;return s;}
int main(int c,char**v){int q=atoi(v[1]),k=atoi(v[2]);FILE*f=fopen(v[3],"r");long moves=atol(v[4]);s^=atol(v[5])*0x9E3779B97F4A7C15ULL;for(int i=0;i<9;i++)rnd();double T=atof(v[6]);
 int cap=300000,n=0;int(*P)[5]=malloc(cap*sizeof(int[5]));while(fscanf(f,"%d %d %d %d %d",&P[n][0],&P[n][1],&P[n][2],&P[n][3],&P[n][4])==5)n++;
 int *deg=calloc(q,4);for(int i=0;i<n;i++)for(int j=0;j<5;j++)deg[P[i][j]]++;
 int **L=malloc(q*sizeof(int*));int *ln=calloc(q,4);for(int y=0;y<q;y++)L[y]=malloc(4*deg[y]);
 for(int i=0;i<n;i++)for(int j=0;j<5;j++){int y=P[i][j];L[y][ln[y]++]=i;}
 char*in=calloc(q,1);int*cnt=calloc(n,4);int*S=malloc(q*4),*Nn=malloc(q*4);int ns=0,nn=0;
 // random start
 int*perm=malloc(q*4);for(int i=0;i<q;i++)perm[i]=i;for(int i=q-1;i>0;i--){int j=rnd()%(i+1);int t=perm[i];perm[i]=perm[j];perm[j]=t;}
 for(int i=0;i<q;i++){if(i<k){in[perm[i]]=1;S[ns++]=perm[i];}else Nn[nn++]=perm[i];}
 long cost=0;for(int i=0;i<n;i++){for(int j=0;j<5;j++)cnt[i]+=in[P[i][j]];if(cnt[i]==5)cost++;}
 long best=cost;char*bin=malloc(q);for(int y=0;y<q;y++)bin[y]=in[y];
 fprintf(stderr,"start %ld\n",cost);
 for(long it=0;it<moves;it++){int ia=rnd()%ns,ib=rnd()%nn;int a=S[ia],b=Nn[ib];
  long d=0;
  // remove a
  for(int i=0;i<ln[a];i++){int p=L[a][i];if(cnt[p]==5)d--;}
  // apply removal temporarily
  for(int i=0;i<ln[a];i++)cnt[L[a][i]]--;
  for(int i=0;i<ln[b];i++){int p=L[b][i];if(cnt[p]==4)d++;}
  double u=(rnd()>>11)*(1.0/9007199254740992.0);
  if(d<=0||u<exp(-d/T)){for(int i=0;i<ln[b];i++)cnt[L[b][i]]++;in[a]=0;in[b]=1;S[ia]=b;Nn[ib]=a;cost+=d;if(cost<best){best=cost;for(int y=0;y<q;y++)bin[y]=in[y];}}
  else{for(int i=0;i<ln[a];i++)cnt[L[a][i]]++;}
  if(it%200000==0)fprintf(stderr,"it %ld cost %ld best %ld\n",it,cost,best);}
 FILE*g=fopen(v[7],"w");for(int y=0;y<q;y++)if(bin[y])fprintf(g,"%d\n",y);fclose(g);printf("best %ld\n",best);}
