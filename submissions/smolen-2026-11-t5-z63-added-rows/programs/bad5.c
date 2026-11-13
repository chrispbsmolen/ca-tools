// bad5.c F : F = 0/1 string of length n<=64. Rows f(x+d) and complements. Lists every 5-set of shifts that misses a pattern:
// "d1 d2 d3 d4 d5 : p p ..." where p is a missing 5-bit row pattern (bit i = entry in column d_{i+1}); patterns come in complement pairs.
#include <stdio.h>
#include <string.h>
typedef unsigned long long u64;
int main(int c,char**v){char*f=v[1];int n=strlen(f);u64 F[64],full=(n==64)?~0ULL:((1ULL<<n)-1);
 for(int d=0;d<n;d++){u64 r=0;for(int x=0;x<n;x++)if(f[(x+d)%n]=='1')r|=1ULL<<x;F[d]=r;}
 long nb=0,tot=0;int S[5];
 for(S[0]=0;S[0]<n;S[0]++)for(S[1]=S[0]+1;S[1]<n;S[1]++)for(S[2]=S[1]+1;S[2]<n;S[2]++)for(S[3]=S[2]+1;S[3]<n;S[3]++)for(S[4]=S[3]+1;S[4]<n;S[4]++){
  tot++;int mp[32],nm=0;
  for(int p=0;p<32;p++){u64 a=full,b=full;for(int i=0;i<5;i++){u64 col=F[S[i]];a&=(p>>i&1)?col:~col;b&=(p>>i&1)?~col:col;}if(!(a|b)&&1)mp[nm++]=p;}
  if(nm){nb++;printf("%d %d %d %d %d :",S[0],S[1],S[2],S[3],S[4]);for(int i=0;i<nm;i++)printf(" %d",mp[i]);puts("");}}
 fprintf(stderr,"n %d sets %ld bad %ld\n",n,tot,nb);}
