// fa_det: fa.c with -I MOVES (stop on a move count, not on the clock: DECISIONS B7). With -I the secs argument is ignored.
// fa: free-cell annealer, binary, any t, k<=64, exact counts on all t-sets (pext). Own code (screening session S).
// fa FILE t T secs seed OUT [-R r new random rows] [-F r1,r2.. free existing rows] [-X r1,.. delete rows] [-D c1,.. drop cols]
//    [-C m new random free cols] [-c c1,.. free existing cols (indices after drop)] [-n cand] [-L lowestU: free the L rows with fewest uniq]
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <time.h>
#if defined(__BMI2__)
#include <immintrin.h>
#else  /* portable fallback (Apple Silicon etc.) */
#include <stdint.h>
static inline uint64_t _pext_u64(uint64_t x,uint64_t m){uint64_t r=0;int i=0;while(m){uint64_t b=m&-m;if(x&b)r|=1ULL<<i;i++;m^=b;}return r;}
static inline uint64_t _pdep_u64(uint64_t x,uint64_t m){uint64_t r=0;int i=0;while(m){uint64_t b=m&-m;if(x>>i&1)r|=b;i++;m^=b;}return r;}
#endif
typedef uint64_t u64;
int N,k,t,P; u64 *row; int nsets; u64 *mask; int **cset; unsigned char **cpos; int ncs;
uint16_t *cnt; int *hpos,*hl; int nh=0;
u64 rs=88172645463325252ULL; static inline u64 rnd(){rs^=rs<<13;rs^=rs>>7;rs^=rs<<17;return rs;}
static inline void addh(int i){hpos[i]=nh;hl[nh++]=i;} static inline void delh(int i){int p=hpos[i];int l=hl[--nh];hl[p]=l;hpos[l]=p;hpos[i]=-1;}
static inline void flip(int r,int c){ u64 x=row[r]; int*cs=cset[c]; unsigned char*cp=cpos[c];
  for(int j=0;j<ncs;j++){int s=cs[j]; int o=(int)_pext_u64(x,mask[s]); int io=(s<<t)|o, in=io^(1<<cp[j]);
    if(--cnt[io]==0)addh(io); if(cnt[in]++==0)delh(in);} row[r]=x^(1ULL<<c); }
static int parse(char*s,int*o){int n=0;char*p=strtok(s,",");while(p){o[n++]=atoi(p);p=strtok(0,",");}return n;}
int main(int ac,char**av){
  FILE*f=fopen(av[1],"r"); t=atoi(av[2]); double T=atof(av[3]); double secs=atof(av[4]); int seed=atoi(av[5]); char*out=av[6];
  long IT=0; int nR=0,Fl[2000],nF=0,Xl[2000],nX=0,Dl[200],nD=0,nC=0,cl[200],ncl=0,cand=1,L=0,ALL=0,K=0,MP=1;
  for(int i=7;i<ac;i++){ if(!strcmp(av[i],"-R"))nR=atoi(av[++i]); else if(!strcmp(av[i],"-F"))nF=parse(av[++i],Fl); else if(!strcmp(av[i],"-X"))nX=parse(av[++i],Xl);
    else if(!strcmp(av[i],"-D"))nD=parse(av[++i],Dl); else if(!strcmp(av[i],"-C"))nC=atoi(av[++i]); else if(!strcmp(av[i],"-c"))ncl=parse(av[++i],cl); else if(!strcmp(av[i],"-n"))cand=atoi(av[++i]); else if(!strcmp(av[i],"-L"))L=atoi(av[++i]); else if(!strcmp(av[i],"-A"))ALL=1; else if(!strcmp(av[i],"-m"))MP=atoi(av[++i]); else if(!strcmp(av[i],"-I"))IT=atol(av[++i]); else if(!strcmp(av[i],"-K"))K=atoi(av[++i]);}
  rs^=(u64)seed*0x9E3779B97F4A7C15ULL; for(int i=0;i<20;i++)rnd();
  static char line[100000]; static u64 R0[5000]; int n0=0,k0=0;
  while(fgets(line,sizeof line,f)){u64 x=0;int c=0;for(char*p=line;*p;p++)if(*p=='0'||*p=='1'){if(*p=='1')x|=1ULL<<c;c++;} if(c){R0[n0++]=x;k0=c;}}
  int keepc[64],nk=0; for(int c=0;c<k0;c++){int d=0;for(int j=0;j<nD;j++)if(Dl[j]==c)d=1;if(!d)keepc[nk++]=c;}
  k=nk+nC; row=malloc(sizeof(u64)*(n0+nR)); char*rfree=calloc(n0+nR,1); N=0;
  for(int r=0;r<n0;r++){int d=0;for(int j=0;j<nX;j++)if(Xl[j]==r)d=1;if(d)continue; u64 x=0;for(int c=0;c<nk;c++)if(R0[r]>>keepc[c]&1)x|=1ULL<<c; for(int c=nk;c<k;c++)if(rnd()&1)x|=1ULL<<c;
    for(int j=0;j<nF;j++)if(Fl[j]==r)rfree[N]=1; row[N++]=x;}
  for(int i=0;i<nR;i++){rfree[N]=1;row[N++]=rnd()&((k==64)?~0ULL:((1ULL<<k)-1));}
  u64 cfree=0; for(int c=nk;c<k;c++)cfree|=1ULL<<c; for(int j=0;j<ncl;j++)cfree|=1ULL<<cl[j];
  // sets
  P=1<<t; long ns=1; for(int i=0;i<t;i++)ns=ns*(k-i)/(i+1); nsets=ns; mask=malloc(8*ns); ncs=(long)ns*t/k;
  cset=malloc(sizeof(int*)*k); cpos=malloc(sizeof(char*)*k); int fill[64]={0}; for(int c=0;c<k;c++){cset[c]=malloc(4*ncs);cpos[c]=malloc(ncs);}
  { int cs[8]; for(int i=0;i<t;i++)cs[i]=i; int s=0; for(;;){ u64 m=0; for(int i=0;i<t;i++)m|=1ULL<<cs[i]; mask[s]=m; for(int i=0;i<t;i++){int c=cs[i];cset[c][fill[c]]=s;cpos[c][fill[c]++]=i;} s++;
      int i=t-1; while(i>=0&&cs[i]==k-t+i)i--; if(i<0)break; cs[i]++; for(int j=i+1;j<t;j++)cs[j]=cs[j-1]+1; } }
  cnt=calloc((size_t)ns*P,2); hpos=malloc(sizeof(int)*(size_t)ns*P); hl=malloc(sizeof(int)*(size_t)ns*P);
  for(int r=0;r<N;r++)for(int s=0;s<nsets;s++)cnt[(s<<t)|_pext_u64(row[r],mask[s])]++;
  for(int j=0;j<K;j++){ long bu=1L<<60;int b=-1; for(int r=0;r<N;r++){ if(rfree[r])continue; long u=0; for(int s=0;s<nsets;s++)if(cnt[(s<<t)|_pext_u64(row[r],mask[s])]==1)u++; if(u<bu){bu=u;b=r;} }
    for(int s=0;s<nsets;s++)cnt[(s<<t)|_pext_u64(row[b],mask[s])]--; row[b]=row[N-1]; char tf=rfree[b]; rfree[b]=rfree[N-1]; rfree[N-1]=tf; N--; fprintf(stderr,"K-delete row uniq=%ld\n",bu); }
  if(ALL)for(int r=0;r<N;r++)rfree[r]=1;
  if(L>0){ // free the L rows with fewest uniquely covered patterns
    long*u=calloc(N,sizeof(long)); for(int r=0;r<N;r++)for(int s=0;s<nsets;s++)if(cnt[(s<<t)|_pext_u64(row[r],mask[s])]==1)u[r]++;
    for(int j=0;j<L;j++){int b=-1;for(int r=0;r<N;r++)if(!rfree[r]&&(b<0||u[r]<u[b]))b=r; rfree[b]=1;} free(u); }
  for(long i=0;i<(long)ns*P;i++){hpos[i]=-1;} for(long i=0;i<(long)ns*P;i++)if(cnt[i]==0)addh(i);
  int *fr=malloc(4*N),nfr=0; for(int r=0;r<N;r++)if(rfree[r])fr[nfr++]=r;
  fprintf(stderr,"N=%d k=%d t=%d sets=%d free rows=%d free cols=%d start holes=%d\n",N,k,t,nsets,nfr,__builtin_popcountll(cfree),nh);
  int best=nh; u64*bestrow=malloc(8*N); memcpy(bestrow,row,8*N); clock_t t0=clock(); long it=0,acc=0; double lastp=0;
  while(nh>0){ if(IT>0&&it>=IT)break; if((it&255)==0){double el=(double)(clock()-t0)/CLOCKS_PER_SEC; if(IT==0&&el>secs)break; if(el-lastp>=10){lastp=el;fprintf(stderr,"  %.0fs it=%ld acc=%ld holes=%d best=%d\n",el,it,acc,nh,best);} }
    it++; int h=hl[rnd()%nh]; int s=h>>t,p=h&(P-1); u64 want=_pdep_u64((u64)p,mask[s]);
    int br=-1,bd=1<<30; u64 bdiff=0;
    for(int cc=0;cc<cand;cc++){ int r=-1; u64 diff=0;
      {int got=0,bp=99; for(int tr=0;tr<30*MP&&got<MP;tr++){ int q=(nfr&&(rnd()&1))?fr[rnd()%nfr]:(int)(rnd()%N); u64 d=(row[q]^want)&mask[s]; if(rfree[q]||(d&~cfree)==0){got++; int pc=__builtin_popcountll(d); if(pc<bp){bp=pc;r=q;diff=d;}} }}
      if(r<0)continue; if(cand==1){br=r;bdiff=diff;break;}
      int h0=nh; u64 d=diff; while(d){int c=__builtin_ctzll(d);d&=d-1;flip(r,c);} int dl=nh-h0; d=diff; while(d){int c=__builtin_ctzll(d);d&=d-1;flip(r,c);}
      if(dl<bd){bd=dl;br=r;bdiff=diff;} }
    if(br<0)continue; int h0=nh; u64 d=bdiff; while(d){int c=__builtin_ctzll(d);d&=d-1;flip(br,c);} int dl=nh-h0;
    if(dl<=0||(double)(rnd()>>11)/9007199254740992.0<exp(-dl/T)){acc++; if(nh<best){best=nh;memcpy(bestrow,row,8*N);} }
    else { d=bdiff; while(d){int c=__builtin_ctzll(d);d&=d-1;flip(br,c);} }
  }
  double el=(double)(clock()-t0)/CLOCKS_PER_SEC; printf("RESULT N=%d k=%d t=%d best=%d it=%ld acc=%ld secs=%.0f %s\n",N,k,t,best,it,acc,el,best==0?"FOUND":"");
  FILE*o=fopen(out,"w"); for(int r=0;r<N;r++){for(int c=0;c<k;c++)fprintf(o,"%d%s",(int)(bestrow[r]>>c&1),c==k-1?"\n":" ");} fclose(o); return 0; }
