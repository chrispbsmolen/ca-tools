// need5s.c: q prime. Paley array chi(x+y), diagonal (x+y=0) cells excluded (free). Enumerate 5-sets {0,b,c,d,e} (translation reps) and print
// each pattern p not covered by CLEAN rows: "b c d e p". Same logic as item143 need5.c, but prints the lines. usage: need5s q
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef unsigned long long u64;
#define W 6
int q;u64 B[2][512][W];
int main(int c,char**v){q=atoi(v[1]);static int chi[512];for(int i=1;i<q;i++)chi[(i*i)%q]=1;
 for(int y=0;y<q;y++)for(int x=0;x<q;x++){int s=(x+y)%q;if(!s)continue;B[chi[s]][y][x>>6]|=1ULL<<(x&63);}
 long need=0,sets=0;
 u64 m2[4][W],m3[8][W],m4[16][W];
 for(int b=1;b<q;b++){for(int p=0;p<4;p++)for(int w=0;w<W;w++)m2[p][w]=B[p&1][0][w]&B[p>>1][b][w];
  for(int cc=b+1;cc<q;cc++){for(int p=0;p<8;p++)for(int w=0;w<W;w++)m3[p][w]=m2[p&3][w]&B[p>>2][cc][w];
   for(int d=cc+1;d<q;d++){for(int p=0;p<16;p++)for(int w=0;w<W;w++)m4[p][w]=m3[p&7][w]&B[p>>3][d][w];
    for(int e=d+1;e<q;e++){for(int p=0;p<32;p++){u64 a=0;for(int w=0;w<W;w++)a|=m4[p&15][w]&B[p>>4][e][w];if(!a){printf("%d %d %d %d %d\n",b,cc,d,e,p);need++;}}
     sets++;}}}
  if(b%20==0){fprintf(stderr,"b %d need %ld\n",b,need);fflush(stderr);}}
 fprintf(stderr,"done q=%d sets=%ld need=%ld\n",q,sets,need);}
