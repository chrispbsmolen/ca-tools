// subselw.c: weighted subset selection with optional orbit groups.
// usage: subselw q k pairsw.txt(5 cols + weight) moves seed T out.txt [groups.txt (one group of columns per line, equal sizes)]
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
static unsigned long long s=88172645463325252ULL; static inline unsigned long long rnd(){s^=s<<13;s^=s>>7;s^=s<<17;return s;}
int main(int c,char**v){int q=atoi(v[1]),k=atoi(v[2]);FILE*f=fopen(v[3],"r");long moves=atol(v[4]);s^=atol(v[5])*0x9E3779B97F4A7C15ULL;for(int i=0;i<9;i++)rnd();double T=atof(v[6]);
 int cap=300000,n=0;int(*P)[5]=malloc(cap*sizeof(int[5]));double*W=malloc(cap*8);
 while(fscanf(f,"%d %d %d %d %d %lf",&P[n][0],&P[n][1],&P[n][2],&P[n][3],&P[n][4],&W[n])==6)n++;
 int *deg=calloc(q,4);for(int i=0;i<n;i++)for(int j=0;j<5;j++)deg[P[i][j]]++;
 int **L=malloc(q*sizeof(int*));int *ln=calloc(q,4);for(int y=0;y<q;y++)L[y]=malloc(4*deg[y]+4);
 for(int i=0;i<n;i++)for(int j=0;j<5;j++){int y=P[i][j];L[y][ln[y]++]=i;}
 // groups
 int ng=0,gs=1;int **G=malloc(q*sizeof(int*));int *gsz=calloc(q,4);
 if(c>8){FILE*h=fopen(v[8],"r");char buf[8192];while(fgets(buf,8192,h)){G[ng]=malloc(4*q);int m=0,nn,x;char*p=buf;while(sscanf(p,"%d%n",&x,&nn)==1){G[ng][m++]=x;p+=nn;}gsz[ng]=m;if(m)ng++;}}
 else{for(int y=0;y<q;y++){G[y]=malloc(4);G[y][0]=y;gsz[y]=1;}ng=q;}
 gs=gsz[0]; int kg=k/gs; if(kg*gs!=k){fprintf(stderr,"k not multiple of group size\n");return 1;}
 char*in=calloc(q,1);int*cnt=calloc(n,4);int*Sg=malloc(ng*4),*Ng=malloc(ng*4);int ns=0,nn=0;
 int*perm=malloc(ng*4);for(int i=0;i<ng;i++)perm[i]=i;for(int i=ng-1;i>0;i--){int j=rnd()%(i+1);int t=perm[i];perm[i]=perm[j];perm[j]=t;}
 for(int i=0;i<ng;i++){if(i<kg){for(int j=0;j<gsz[perm[i]];j++)in[G[perm[i]][j]]=1;Sg[ns++]=perm[i];}else Ng[nn++]=perm[i];}
 double cost=0;long raw=0;for(int i=0;i<n;i++){for(int j=0;j<5;j++)cnt[i]+=in[P[i][j]];if(cnt[i]==5){cost+=W[i];raw++;}}
 double best=cost;char*bin=malloc(q);memcpy(bin,in,q);
 fprintf(stderr,"start cost %.3f raw %ld ng %d kg %d\n",cost,raw,ng,kg);
 for(long it=0;it<moves;it++){int ia=rnd()%ns,ib=rnd()%nn;int a=Sg[ia],b=Ng[ib];
  double d=0;
  // remove group a one column at a time, then add group b; record to undo
  for(int j=0;j<gsz[a];j++){int y=G[a][j];for(int i=0;i<ln[y];i++){int p=L[y][i];if(cnt[p]==5)d-=W[p];cnt[p]--;}}
  for(int j=0;j<gsz[b];j++){int y=G[b][j];for(int i=0;i<ln[y];i++){int p=L[y][i];cnt[p]++;if(cnt[p]==5)d+=W[p];}}
  double u=(rnd()>>11)*(1.0/9007199254740992.0);
  if(d<=0||u<exp(-d/T)){for(int j=0;j<gsz[a];j++)in[G[a][j]]=0;for(int j=0;j<gsz[b];j++)in[G[b][j]]=1;Sg[ia]=b;Ng[ib]=a;cost+=d;if(cost<best-1e-9){best=cost;memcpy(bin,in,q);}}
  else{for(int j=0;j<gsz[b];j++){int y=G[b][j];for(int i=0;i<ln[y];i++)cnt[L[y][i]]--;}for(int j=0;j<gsz[a];j++){int y=G[a][j];for(int i=0;i<ln[y];i++)cnt[L[y][i]]++;}}
  if(it%200000==0)fprintf(stderr,"it %ld cost %.3f best %.3f\n",it,cost,best);}
 FILE*g=fopen(v[7],"w");for(int y=0;y<q;y++)if(bin[y])fprintf(g,"%d\n",y);fclose(g);printf("best %.3f\n",best);}
