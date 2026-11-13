// holes4w.c q MASKFILE out.txt : Paley q (chi(0) FREE) kept rows K. Lists every (4-set,pattern) not strictly covered by K
// (strict = row matches all 4 cells, diagonal cells never count) as an ls2m line:  4 a b c d P opt:bit ...   (opt = row x whose diagonal cell lies in the set and whose other cells match).
// Prints counts: holes, holes with 0 options (need free rows).
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
typedef struct{uint64_t w[3];}B;
int q;B col[256],Wd[256];
static inline B AND(B a,B b){B r;for(int i=0;i<3;i++)r.w[i]=a.w[i]&b.w[i];return r;}
static inline B OR(B a,B b){B r;for(int i=0;i<3;i++)r.w[i]=a.w[i]|b.w[i];return r;}
static inline B NOT(B a){B r;for(int i=0;i<3;i++)r.w[i]=~a.w[i];return r;}
static inline int nz(B a){return (a.w[0]|a.w[1]|a.w[2])!=0;}
int main(int argc,char**argv){q=atoi(argv[1]);
 int sq[256]={0};for(int i=1;i<q;i++)sq[(i*i)%q]=1;
 B K;memset(&K,0,sizeof K);{FILE*f=fopen(argv[2],"r");char s[400];fscanf(f,"%s",s);for(int x=0;x<q;x++)if(s[x]=='1')K.w[x>>6]|=1ULL<<(x&63);}
 for(int y=0;y<q;y++){memset(&col[y],0,sizeof(B));memset(&Wd[y],0,sizeof(B));for(int x=0;x<q;x++)if(sq[(x+y)%q])col[y].w[x>>6]|=1ULL<<(x&63);int xd=(q-y)%q;Wd[y].w[xd>>6]|=1ULL<<(xd&63);}
 B s1[256],s0[256],w1[256],w0[256];
 for(int y=0;y<q;y++){s1[y]=col[y];s0[y]=AND(NOT(col[y]),NOT(Wd[y]));w1[y]=OR(col[y],Wd[y]);w0[y]=NOT(col[y]);}
 FILE*o=fopen(argv[3],"w");long holes=0,noopt=0;
 for(int a=0;a<q;a++)for(int b=a+1;b<q;b++)for(int c=b+1;c<q;c++)for(int d=c+1;d<q;d++){int Y[4]={a,b,c,d};
  for(int p=0;p<16;p++){B S=K,Wm=K;for(int i=0;i<4;i++){int y=Y[i];if((p>>i)&1){S=AND(S,s1[y]);Wm=AND(Wm,w1[y]);}else{S=AND(S,s0[y]);Wm=AND(Wm,w0[y]);}}
   if(nz(S))continue; holes++;
   fprintf(o,"4 %d %d %d %d %d",a,b,c,d,p);int n=0;
   for(int w=0;w<3;w++){uint64_t m=Wm.w[w];while(m){int x=w*64+__builtin_ctzll(m);m&=m-1;int yd=(q-x)%q;for(int i=0;i<4;i++)if(Y[i]==yd){fprintf(o," %d:%d",x,(p>>i)&1);n++;}}}
   if(!n)noopt++;fprintf(o,"\n");}}
 fclose(o);printf("holes %ld noopt %ld\n",holes,noopt);}
