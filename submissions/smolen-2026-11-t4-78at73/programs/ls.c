#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#define MT 200000
int q,m,nt; int S[MT][4],P[MT]; int no[MT],ox[MT][4],ob[MT][4];
unsigned char z[512],R[16][512]; int cnt[MT];
// incidence lists
int *zl[512],zn[512]; int *cl[512],cn[512];
static unsigned long long s=88172645463325252ULL; static inline unsigned long long rnd(){s^=s<<13;s^=s>>7;s^=s<<17;return s;}
int eval(int t){int c=0;for(int j=0;j<no[t];j++)if(z[ox[t][j]]==ob[t][j])c++;for(int i=0;i<m;i++){int ok=1;for(int j=0;j<4;j++)if(R[i][S[t][j]]!=(P[t]>>j&1)){ok=0;break;}c+=ok;}return c;}
int main(int c,char**v){q=atoi(v[1]);m=atoi(v[2]);FILE*f=fopen(v[3],"r");double T=atof(v[4]);long iters=atol(v[5]);s^=atol(v[6])*0x9E3779B97F4A7C15ULL;
 char line[256];while(fgets(line,256,f)){int n,off;sscanf(line,"%d %d %d %d %d%n",&S[nt][0],&S[nt][1],&S[nt][2],&S[nt][3],&P[nt],&off);char*p=line+off;int x,b;no[nt]=0;while(sscanf(p," %d:%d%n",&x,&b,&n)==2){ox[nt][no[nt]]=x;ob[nt][no[nt]]=b;no[nt]++;p+=n;}nt++;}
 for(int t=0;t<nt;t++){for(int j=0;j<no[t];j++)zn[ox[t][j]]++;for(int j=0;j<4;j++)cn[S[t][j]]++;}
 for(int i=0;i<q;i++){zl[i]=malloc(4*(zn[i]+1));cl[i]=malloc(4*(cn[i]+1));zn[i]=cn[i]=0;}
 for(int t=0;t<nt;t++){for(int j=0;j<no[t];j++)zl[ox[t][j]][zn[ox[t][j]]++]=t;for(int j=0;j<4;j++)cl[S[t][j]][cn[S[t][j]]++]=t;}
 for(int i=0;i<q;i++){z[i]=rnd()&1;for(int r=0;r<m;r++)R[r][i]=rnd()&1;}
 int cost=0;for(int t=0;t<nt;t++){cnt[t]=eval(t);cost+=!cnt[t];}
 int best=cost;static int tmp[MT];
 for(long it=0;it<iters&&cost;it++){int r=rnd()%(m+1),y=rnd()%q;int*L;int n;unsigned char*cell;
  if(r==m){L=zl[y];n=zn[y];cell=&z[y];}else{L=cl[y];n=cn[y];cell=&R[r][y];}
  *cell^=1;int d=0;for(int i=0;i<n;i++){int t=L[i];int e=eval(t);tmp[i]=e;d+=(!e)-(!cnt[t]);}
  if(d<=0||(rnd()>>11)*(1.0/9007199254740992.0)<exp(-d/T)){cost+=d;for(int i=0;i<n;i++)cnt[L[i]]=tmp[i];if(cost<best){best=cost;fprintf(stderr,"it %ld best %d\n",it,best);}}
  else *cell^=1;}
 printf("final %d best %d\n",cost,best);if(!cost){printf("z ");for(int i=0;i<q;i++)putchar('0'+z[i]);puts("");for(int r=0;r<m;r++){printf("R ");for(int i=0;i<q;i++)putchar('0'+R[r][i]);puts("");}}}
