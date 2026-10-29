/* brute3.c q t s : direct count of uncovered t-sets {0, s, ...} of the nonresidue circulant (no bitsets, no pruning) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static long long pm(long long a,long long e,long long m){long long r=1;a%=m;while(e){if(e&1)r=r*a%m;a=a*a%m;e>>=1;}return r;}
int main(int argc,char**argv){int q=atoi(argv[1]),t=atoi(argv[2]),s=atoi(argv[3]);unsigned char*x=malloc(q);
 for(int i=0;i<q;i++)x[i]=i==0?0:(pm(i,(q-1)/2,q)==1?0:1);
 int m=t-2,*E=malloc(sizeof(int)*q),ne=0;for(int i=1;i<q;i++)if(i!=s)E[ne++]=i;
 int I[10];for(int i=0;i<m;i++)I[i]=i;long long bad=0,tot=0;int P=1<<t;char seen[256];int S[10];S[0]=0;S[1]=s;
 while(1){for(int j=0;j<m;j++)S[2+j]=E[I[j]];memset(seen,0,P);int n=0;
  for(int r=0;r<q&&n<P;r++){int p=0;for(int j=0;j<t;j++)p=2*p+x[((S[j]-r)%q+q)%q];if(!seen[p]){seen[p]=1;n++;}}
  tot++;if(n<P)bad++;int i=m-1;while(i>=0&&I[i]==ne-m+i)i--;if(i<0)break;I[i]++;for(int j=i+1;j<m;j++)I[j]=I[j-1]+1;}
 printf("brute3 q=%d t=%d s=%d sets=%lld uncovered=%lld\n",q,t,s,tot,bad);return 0;}
