// palsub.c BADFILE n s seed moves T : find s columns out of n containing no bad 5-set (swap annealing, stops on a move count).
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>
uint64_t rs=88172645463325252ULL; static inline uint64_t rnd(){rs^=rs<<13;rs^=rs>>7;rs^=rs<<17;return rs;}
int main(int ac,char**av){FILE*f=fopen(av[1],"rb");int n=atoi(av[2]),s=atoi(av[3]);long seed=atol(av[4]),M=atol(av[5]);double T=atof(av[6]);
  fseek(f,0,SEEK_END);long nb=ftell(f)/5;fseek(f,0,SEEK_SET);unsigned char*B=malloc(nb*5);if(fread(B,5,nb,f)!=(size_t)nb)return 1;
  int*deg=calloc(n,4);for(long i=0;i<nb*5;i++)deg[B[i]]++;int**L=malloc(sizeof(int*)*n);for(int c=0;c<n;c++){L[c]=malloc(4*deg[c]);deg[c]=0;}
  for(long i=0;i<nb;i++)for(int j=0;j<5;j++){int c=B[i*5+j];L[c][deg[c]++]=i;}
  rs^=(uint64_t)seed*0x9E3779B97F4A7C15ULL;for(int i=0;i<20;i++)rnd();
  char*in=calloc(n,1);int*S=malloc(4*n),*O=malloc(4*n);int perm[512];for(int i=0;i<n;i++)perm[i]=i;for(int i=n-1;i>0;i--){int j=rnd()%(i+1);int t=perm[i];perm[i]=perm[j];perm[j]=t;}
  for(int i=0;i<s;i++){S[i]=perm[i];in[perm[i]]=1;}for(int i=s;i<n;i++)O[i-s]=perm[i];
  unsigned char*cnt=calloc(nb,1);long cost=0;for(long i=0;i<nb;i++){for(int j=0;j<5;j++)cnt[i]+=in[B[i*5+j]];if(cnt[i]==5)cost++;}
  long best=cost;int*bs=malloc(4*n);memcpy(bs,S,4*s);
  for(long it=0;it<M&&cost>0;it++){int a=rnd()%s,b=rnd()%(n-s);int x=S[a],y=O[b];
    // delta: sets with cnt 5 containing x are freed; sets containing y with cnt==4 and not x become bad
    long d=0;for(int i=0;i<deg[x];i++)if(cnt[L[x][i]]==5)d--;
    for(int i=0;i<deg[y];i++){int id=L[y][i];if(cnt[id]==4){int hx=0;for(int j=0;j<5;j++)if(B[id*5+j]==x)hx=1;if(!hx)d++;}}
    if(d<=0||(double)(rnd()>>11)/9007199254740992.0<exp(-d/T)){for(int i=0;i<deg[x];i++)cnt[L[x][i]]--;for(int i=0;i<deg[y];i++)cnt[L[y][i]]++;in[x]=0;in[y]=1;S[a]=y;O[b]=x;cost+=d;if(cost<best){best=cost;memcpy(bs,S,4*s);}}}
  printf("n=%d s=%d seed=%ld best=%ld :",n,s,seed,best);if(best==0||getenv("SHOW")){for(int i=0;i<s;i++)printf(" %d",bs[i]);}printf("\n");return best!=0;}
