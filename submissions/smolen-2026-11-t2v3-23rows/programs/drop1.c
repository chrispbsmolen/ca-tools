// free23.c: exact list of ALL free columns of a ternary strength-2 array (N <= 24 rows): partitions of the rows into
// three sets that each meet every class of every column. Then the largest set of pairwise compatible free columns
// (greedy + exact small search; here only "is there 1" and "are there 2 compatible" matter).
// drop1 variant: for every column c, drop c and list all free columns of the rest; report when 2 compatible exist.
// usage: drop1 FILE   prints: k, number of free columns, max compatible found (up to 3), and writes FILE.ext if >0
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef unsigned int u32;
int N,k;u32 F;u32 cl[512][3];
static inline int qi(const u32*x,const u32*y){for(int a=0;a<3;a++)for(int b=0;b<3;b++)if(!(x[a]&y[b]))return 0;return 1;}
int main(int ac,char**av){
  FILE*f=fopen(av[1],"r");char line[100000];N=0;k=0;
  while(fgets(line,sizeof line,f)){int c=0;char*p=line;int any=0;while(*p){if(*p>='0'&&*p<='2'){if(N==0)cl[c][0]=cl[c][1]=cl[c][2]=0;cl[c][*p-'0']|=1u<<N;c++;any=1;}p++;}if(any){if(N==0)k=c;N++;}}
  fclose(f);F=(1u<<N)-1;size_t SZ=(size_t)1<<N;short*W=malloc(SZ*sizeof(short));unsigned char*hit=malloc(SZ);
  int cap=200000;u32(*E)[3]=malloc(sizeof(u32[3])*cap);int gbest=0;
  for(int drop=0;drop<k;drop++){
    memset(W,0,SZ*sizeof(short));
    for(int i=0;i<k;i++){if(i==drop)continue;for(int a=0;a<3;a++)W[cl[i][a]]++;}
    for(int b=0;b<N;b++){size_t st=(size_t)1<<b;for(size_t x=0;x<SZ;x+=2*st){short*lo=W+x,*hi=W+x+st;for(size_t y=0;y<st;y++)hi[y]+=lo[y];}}
    for(size_t x=0;x<SZ;x++)hit[x]=(W[F^x]==0);
    long ne=0;
    for(u32 c0=1;c0<F;c0+=2){if(!hit[c0])continue;u32 rest=F&~c0;u32 low=rest&-rest;u32 r2=rest&~low;if(!r2)continue;u32 sub=r2;
      do{sub=(sub-1)&r2;u32 c1=low|sub;if(!hit[c1])continue;u32 c2=r2&~sub;if(!c2||!hit[c2])continue;if(ne<cap){E[ne][0]=c0;E[ne][1]=c1;E[ne][2]=c2;}ne++;}while(sub);}
    long m=ne<cap?ne:cap;int best=ne>0;long bi=0,bj=-1;
    for(long i=0;i<m&&best<2;i++)for(long j=i+1;j<m;j++)if(qi(E[i],E[j])){best=2;bi=i;bj=j;break;}
    if(best>gbest)gbest=best;
    if(best>=2){printf("%s: drop column %d -> %ld free columns, 2 compatible: %d columns total\n",av[1],drop,ne,k+1);
      char fn[600];sprintf(fn,"%s.plus1",av[1]);FILE*o=fopen(fn,"w");
      for(int r=0;r<N;r++){for(int i=0;i<k;i++){if(i==drop)continue;fprintf(o,"%d ",(cl[i][0]>>r&1)?0:((cl[i][1]>>r&1)?1:2));}
        fprintf(o,"%d %d\n",(E[bi][0]>>r&1)?0:((E[bi][1]>>r&1)?1:2),(E[bj][0]>>r&1)?0:((E[bj][1]>>r&1)?1:2));}fclose(o);fflush(stdout);break;}
  }
  printf("%s: N %d k %d drop-one result %d\n",av[1],N,k,gbest);
  return 0;}
