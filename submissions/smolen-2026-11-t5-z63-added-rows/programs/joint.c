// joint.c K m seed moves T : K shifts of Z63 and m added rows (with complements), annealed together.
// cost = bad 5-sets inside the shift set not repaired by a row (a 16-missing set costs 1000). Reads bad63.txt. Stops on a move count.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#define NB 8000
int S[NB][5],P[NB],typ[NB],nb; int by[63][2000],nby[63]; int inD[63],R[8][63],cnt[NB],K,m;
static unsigned long long s=88172645463325252ULL; static inline unsigned long long rnd(){s^=s<<13;s^=s>>7;s^=s<<17;return s;}
static inline int w(int i){ if(typ[i])return 1000; for(int r=0;r<m;r++){int v=0;for(int j=0;j<5;j++)v|=R[r][S[i][j]]<<j; if(v==P[i]||v==31-P[i])return 0;} return 1;}
int main(int c,char**v){K=atoi(v[1]);m=atoi(v[2]);s^=atol(v[3])*0x9E3779B97F4A7C15ULL;long moves=atol(v[4]);double T=atof(v[5]);for(int i=0;i<9;i++)rnd();
 FILE*f=fopen("bad63.txt","r");char line[512];while(fgets(line,512,f)){int n,off;sscanf(line,"%d %d %d %d %d :%n",&S[nb][0],&S[nb][1],&S[nb][2],&S[nb][3],&S[nb][4],&off);char*p=line+off;int x,k=0,first=-1;while(sscanf(p," %d%n",&x,&n)==1){if(first<0)first=x;k++;p+=n;}P[nb]=first;typ[nb]=k>2;for(int j=0;j<5;j++){int col=S[nb][j];by[col][nby[col]++]=nb;}nb++;}
 int ins[63],outs[63],ni=0,no=0;for(int i=0;i<63;i++)inD[i]=0;while(ni<K){int x=rnd()%63;if(!inD[x]){inD[x]=1;}ni=0;for(int i=0;i<63;i++)ni+=inD[i];}
 ni=no=0;for(int i=0;i<63;i++){if(inD[i])ins[ni++]=i;else outs[no++]=i;}
 for(int r=0;r<m;r++)for(int i=0;i<63;i++)R[r][i]=rnd()&1;
 long cost=0;for(int i=0;i<nb;i++){cnt[i]=0;for(int j=0;j<5;j++)cnt[i]+=inD[S[i][j]];if(cnt[i]==5)cost+=w(i);}
 long best=cost;int bD[63],bR[8][63];
 for(long it=0;it<moves&&cost;it++){
  if(m&&rnd()%3==0){int r=rnd()%m,col=ins[rnd()%ni];long d=0;for(int x=0;x<nby[col];x++){int i=by[col][x];if(cnt[i]==5)d-=w(i);}R[r][col]^=1;for(int x=0;x<nby[col];x++){int i=by[col][x];if(cnt[i]==5)d+=w(i);}
   if(d<=0||(rnd()>>11)*(1.0/9007199254740992.0)<exp(-d/T))cost+=d;else R[r][col]^=1;}
  else{int a=rnd()%ni,b=rnd()%no,o=ins[a],i2=outs[b];long d=0;for(int x=0;x<nby[o];x++){int i=by[o][x];if(cnt[i]==5)d-=w(i);cnt[i]--;}for(int x=0;x<nby[i2];x++){int i=by[i2][x];cnt[i]++;if(cnt[i]==5)d+=w(i);}
   if(d<=0||(rnd()>>11)*(1.0/9007199254740992.0)<exp(-d/T)){cost+=d;ins[a]=i2;outs[b]=o;inD[o]=0;inD[i2]=1;}
   else{for(int x=0;x<nby[i2];x++)cnt[by[i2][x]]--;for(int x=0;x<nby[o];x++)cnt[by[o][x]]++;}}
  if(cost<best){best=cost;memcpy(bD,inD,sizeof inD);memcpy(bR,R,sizeof R);}
 }
 printf("K %d m %d best %ld\n",K,m,best);if(best==0){printf("D");for(int i=0;i<63;i++)if(bD[i])printf(" %d",i);puts("");for(int r=0;r<m;r++){printf("R ");for(int i=0;i<63;i++)printf("%d",bR[r][i]);puts("");}}
 return 0;}
