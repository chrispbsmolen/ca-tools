// patch search: q diagonal bits + m free rows of q cells; cover every listed (set,pattern). any t<=6.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#define MAXM 64
int q,m,nt,t;
int *S,*P,*no,*ox,*ob; unsigned char *mis; int *cov;
unsigned char z[1024],R[MAXM][1024];
int *zl[1024],zn[1024],*cl[1024],cn[1024];
int *unc,*pos,nu;
static unsigned long long s=88172645463325252ULL; static inline unsigned long long rnd(){s^=s<<13;s^=s>>7;s^=s<<17;return s;}
static inline void setunc(int tt,int on){if(on){pos[tt]=nu;unc[nu++]=tt;}else{int p=pos[tt];unc[p]=unc[--nu];pos[unc[p]]=p;pos[tt]=-1;}}
int main(int c,char**v){q=atoi(v[1]);m=atoi(v[2]);FILE*f=fopen(v[3],"r");double T=atof(v[4]);double secs=atof(v[5]);s^=atol(v[6])*0x9E3779B97F4A7C15ULL;for(int i=0;i<9;i++)rnd();
 int cap=1<<20;S=malloc(cap*6*4);P=malloc(cap*4);no=calloc(cap,4);ox=malloc(cap*6*4);ob=malloc(cap*6*4);
 char line[512];while(fgets(line,512,f)){if(nt==cap){cap*=2;S=realloc(S,cap*24);P=realloc(P,cap*4);no=realloc(no,cap*4);ox=realloc(ox,cap*24);ob=realloc(ob,cap*24);}
  char*p=line;int n;sscanf(p,"%d%n",&t,&n);p+=n;for(int j=0;j<t;j++){sscanf(p,"%d%n",&S[nt*6+j],&n);p+=n;}sscanf(p,"%d%n",&P[nt],&n);p+=n;int x,b;no[nt]=0;while(sscanf(p," %d:%d%n",&x,&b,&n)==2){ox[nt*6+no[nt]]=x;ob[nt*6+no[nt]]=b;no[nt]++;p+=n;}nt++;}
 for(int i=0;i<nt;i++){for(int j=0;j<no[i];j++)zn[ox[i*6+j]]++;for(int j=0;j<t;j++)cn[S[i*6+j]]++;}
 for(int i=0;i<q;i++){zl[i]=malloc(4*(zn[i]+1));cl[i]=malloc(8*(cn[i]+1));zn[i]=cn[i]=0;}
 for(int i=0;i<nt;i++){for(int j=0;j<no[i];j++){int x=ox[i*6+j];zl[x][zn[x]++]=i*8+j;}for(int j=0;j<t;j++){int y=S[i*6+j];cl[y][cn[y]*2]=i;cl[y][cn[y]*2+1]=P[i]>>j&1;cn[y]++;}}
 mis=malloc((size_t)nt*m+1);cov=calloc(nt,4);unc=malloc(nt*4);pos=malloc(nt*4);
 FILE*g=c>7?fopen(v[7],"r"):0;
 for(int i=0;i<q;i++){z[i]=rnd()&1;for(int r=0;r<m;r++)R[r][i]=rnd()&1;}
 if(g){char w[2048];int r=0;while(fscanf(g,"%s",w)==1){if(w[0]=='z'){fscanf(g,"%s",w);for(int i=0;i<q;i++)z[i]=w[i]-'0';}else if(w[0]=='R'){fscanf(g,"%s",w);if(r<m){for(int i=0;i<q;i++)R[r][i]=w[i]-'0';r++;}}}}
 for(int i=0;i<nt;i++){pos[i]=-1;for(int j=0;j<no[i];j++)cov[i]+=z[ox[i*6+j]]==ob[i*6+j];for(int r=0;r<m;r++){int mm=0;for(int j=0;j<t;j++)mm+=R[r][S[i*6+j]]!=(P[i]>>j&1);mis[(size_t)i*m+r]=mm;cov[i]+=!mm;}if(!cov[i])setunc(i,1);}
 int best=nu;time_t t0=time(0);long it=0;fprintf(stderr,"nt %d start %d\n",nt,nu);
 while(nu){it++;if((it&1023)==0&&(secs<0?(double)it>=-secs:difftime(time(0),t0)>secs))break;
  int r,y; if(rnd()%100<70){int tt=unc[rnd()%nu];r=rnd()%(m+(no[tt]?1:0));if(r==m){y=ox[tt*6+rnd()%no[tt]];}else{int j=rnd()%t,k=0;for(;k<t;k++){int jj=(j+k)%t;if(R[r][S[tt*6+jj]]!=(P[tt]>>jj&1)){j=jj;break;}}y=S[tt*6+j];}}
  else{r=rnd()%(m+1);y=rnd()%q;}
  int d=0;
  if(r==m){int nb=!z[y];for(int i=0;i<zn[y];i++){int tt=zl[y][i]>>3,j=zl[y][i]&7;int was=(ob[tt*6+j]==z[y]),now=(ob[tt*6+j]==nb);int cc=cov[tt]+now-was;d+=(!cc)-(!cov[tt]);}
   if(d<=0||(rnd()>>11)*(1.0/9007199254740992.0)<exp(-d/T)){for(int i=0;i<zn[y];i++){int tt=zl[y][i]>>3,j=zl[y][i]&7;int was=(ob[tt*6+j]==z[y]),now=(ob[tt*6+j]==nb);int cc=cov[tt]+now-was;if(!cc&&cov[tt])setunc(tt,1);else if(cc&&!cov[tt])setunc(tt,0);cov[tt]=cc;}z[y]=nb;}}
  else{int nb=!R[r][y];int*L=cl[y];int n=cn[y];
   for(int i=0;i<n;i++){int tt=L[2*i];unsigned char mm=mis[(size_t)tt*m+r];if(L[2*i+1]==nb){if(mm==1)d-=!cov[tt];}else{if(mm==0)d+=(cov[tt]==1);}}
   if(d<=0||(rnd()>>11)*(1.0/9007199254740992.0)<exp(-d/T)){for(int i=0;i<n;i++){int tt=L[2*i];unsigned char*mp=&mis[(size_t)tt*m+r];if(L[2*i+1]==nb){if(--*mp==0){if(!cov[tt])setunc(tt,0);cov[tt]++;}}else{if((*mp)++==0){if(--cov[tt]==0)setunc(tt,1);}}}R[r][y]=nb;}}
  if(nu<best){best=nu;if(best<50||(it&4095)==0)fprintf(stderr,"it %ld t %.0f best %d\n",it,difftime(time(0),t0),best);}
 }
 printf("final %d best %d moves %ld\n",nu,best,it);printf("z ");for(int i=0;i<q;i++)putchar('0'+z[i]);puts("");for(int r=0;r<m;r++){printf("R ");for(int i=0;i<q;i++)putchar('0'+R[r][i]);puts("");}return 0;}
