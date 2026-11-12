#include <stdio.h>
#include <stdlib.h>
// list (S,p) not covered by clean rows of the q x q cyclotomic array; for each, print S, p, and diag options (row x, needed z)
int main(int c,char**v){int q=atoi(v[1]);static int chi[512];static unsigned char a[512][512];
 for(int i=1;i<q;i++)chi[(i*i)%q]=1;
 for(int x=0;x<q;x++)for(int y=0;y<q;y++){int s=(x+y)%q;a[x][y]=s?chi[s]:2;}
 int S[4];
 for(S[0]=0;S[0]<q;S[0]++)for(S[1]=S[0]+1;S[1]<q;S[1]++)for(S[2]=S[1]+1;S[2]<q;S[2]++)for(S[3]=S[2]+1;S[3]<q;S[3]++){
  unsigned m=0;for(int x=0;x<q;x++){int pp=0,bad=0;for(int j=0;j<4;j++){int e=a[x][S[j]];if(e==2)bad=1;else pp|=e<<j;}if(!bad)m|=1u<<pp;}
  if(m==0xffff)continue;
  for(int p=0;p<16;p++)if(!(m>>p&1)){printf("%d %d %d %d %d",S[0],S[1],S[2],S[3],p);
   for(int j=0;j<4;j++){int x=(q-S[j])%q;int ok=1;for(int l=0;l<4;l++)if(l!=j&&a[x][S[l]]!=(p>>l&1))ok=0;if(ok)printf(" %d:%d",x,p>>j&1);}
   puts("");}
 }}
