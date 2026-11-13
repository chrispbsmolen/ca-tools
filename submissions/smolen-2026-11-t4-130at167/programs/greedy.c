// greedy.c q target : pure row elimination of the Paley q x q array (chi(0)=0), strength 4: repeatedly delete the kept row with fewest uniquely-covered (4-set,pattern); print holes each step.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
typedef struct{uint64_t w[3];}B;
int q;B col[256];
static inline B AND(B a,B b){B r;for(int i=0;i<3;i++)r.w[i]=a.w[i]&b.w[i];return r;}
static inline B ANDN(B a,B b){B r;for(int i=0;i<3;i++)r.w[i]=a.w[i]&~b.w[i];return r;}
int main(int argc,char**argv){q=atoi(argv[1]);int target=atoi(argv[2]);
 int sq[256]={0};for(int i=1;i<q;i++)sq[(i*i)%q]=1;
 for(int y=0;y<q;y++){memset(&col[y],0,sizeof(B));for(int x=0;x<q;x++)if(sq[(x+y)%q])col[y].w[x>>6]|=1ULL<<(x&63);}
 B R;memset(&R,0,sizeof R);for(int x=0;x<q;x++)R.w[x>>6]|=1ULL<<(x&63);
 int n=q;
 while(n>target){
  long nec[256]={0};long holes=0;
  for(int a=0;a<q;a++)for(int b=a+1;b<q;b++){B ab[4];ab[0]=ANDN(ANDN(R,col[a]),col[b]);ab[1]=ANDN(AND(R,col[b]),col[a]);ab[2]=ANDN(AND(R,col[a]),col[b]);ab[3]=AND(AND(R,col[a]),col[b]);
   for(int c=b+1;c<q;c++){B abc[8];for(int i=0;i<4;i++){abc[2*i]=ANDN(ab[i],col[c]);abc[2*i+1]=AND(ab[i],col[c]);}
    for(int d=c+1;d<q;d++){for(int i=0;i<8;i++){B m0=ANDN(abc[i],col[d]),m1=AND(abc[i],col[d]);
      for(int z=0;z<2;z++){B m=z?m1:m0;int pcnt=__builtin_popcountll(m.w[0])+__builtin_popcountll(m.w[1])+__builtin_popcountll(m.w[2]);
        if(pcnt==0)holes++;else if(pcnt==1){int x=m.w[0]?__builtin_ctzll(m.w[0]):(m.w[1]?64+__builtin_ctzll(m.w[1]):128+__builtin_ctzll(m.w[2]));nec[x]++;}}}}}}
  int best=-1;for(int x=0;x<q;x++)if((R.w[x>>6]>>(x&63))&1){if(best<0||nec[x]<nec[best])best=x;}
  printf("rows %d holes %ld delete row %d (unique %ld)\n",n,holes,best,nec[best]);fflush(stdout);
  R.w[best>>6]&=~(1ULL<<(best&63));n--;
 }
 printf("MASK ");for(int x=0;x<q;x++)printf("%d",(int)((R.w[x>>6]>>(x&63))&1));printf("\n");}
