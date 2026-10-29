/* brute.c q t : all t-sets of the q x q nonresidue circulant, direct pattern count per set */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static long long pm(long long a,long long e,long long m){long long r=1;a%=m;while(e){if(e&1)r=r*a%m;a=a*a%m;e>>=1;}return r;}
int main(int argc,char**argv){int q=atoi(argv[1]),t=atoi(argv[2]);unsigned char*x=malloc(q);
 for(int i=0;i<q;i++)x[i]=i==0?0:(pm(i,(q-1)/2,q)==1?0:1);
 int S[10];for(int i=0;i<t;i++)S[i]=i;long long bad=0,tot=0;int P=1<<t;char seen[256];
 while(1){memset(seen,0,P);int n=0;for(int r=0;r<q&&n<P;r++){int p=0;for(int j=0;j<t;j++)p=2*p+x[((S[j]-r)%q+q)%q];if(!seen[p]){seen[p]=1;n++;}}
  tot++;if(n<P)bad++;
  int i=t-1;while(i>=0&&S[i]==q-t+i)i--;if(i<0)break;S[i]++;for(int j=i+1;j<t;j++)S[j]=S[j-1]+1;}
 printf("brute q=%d t=%d sets=%lld uncovered=%lld %s\n",q,t,tot,bad,bad?"NOT covered":"covered");return 0;}
