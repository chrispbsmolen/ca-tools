/* ext2t: frozen-core / free-mask annealer, ternary (v=3) strength 2, with chaining.
   Base (N0 x k0) is frozen except rows listed with -fr and columns listed with -fc. r free rows and m free
   columns are added. ALL pairs are counted exactly (so any free mask is legal). Focus move: pick an uncovered
   (u,w,a,b), try CAND rows that can take it (cells free or already right), apply the best, Metropolis fixed T.
   -chain M: every time holes reach 0 the array is saved and one more random free column is appended (up to M).
   usage: ext2t base N0 k0 r m seed secs T out [-i state] [-c cand] [-chain M] [-fr a,b,..] [-fc a,b,..] [-frl n] (free last n base rows) [-ntry n] (best of n random new columns) [-kick it] (redraw the last column after it moves without success; use only with -chain and no -i holes in old columns)
   state/out: full N x k arrays, symbols 0..2. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <stdint.h>
static int N0,k0,r,m,N,k,KM; static unsigned char **a; static unsigned char *frow,*fcol;
static uint8_t *cnt; static int32_t *hpos,*hole; static long H;
static uint64_t rs; static inline uint64_t rnd(void){rs^=rs<<13;rs^=rs>>7;rs^=rs<<17;return rs;}
static inline double urand(void){return (rnd()>>11)*(1.0/9007199254740992.0);}
static inline long pid(int u,int w){return ((long)u*KM+w)*9;} /* u<w */
static inline void dec(long id){ if(--cnt[id]==0){hpos[id]=H;hole[H++]=id;} }
static inline void inc(long id){ if(cnt[id]++==0){long p=hpos[id];long l=hole[--H];hole[p]=l;hpos[l]=p;hpos[id]=-1;} }
static void setc(int R,int X,int n){ unsigned char*row=a[R]; int o=row[X]; if(o==n)return;
  for(int y=0;y<X;y++){long b=pid(y,X)+row[y]*3; dec(b+o); inc(b+n);}
  for(int y=X+1;y<k;y++){long b=pid(X,y)+row[y]; dec(b+o*3); inc(b+n*3);}
  row[X]=n; }
static inline int isfree(int R,int X){return R>=N0||X>=k0||frow[R]||fcol[X];}
static void save(const char*fn){FILE*f=fopen(fn,"w");for(int i=0;i<N;i++){for(int j=0;j<k;j++)fprintf(f,j?" %d":"%d",a[i][j]);fprintf(f,"\n");}fclose(f);}
static int NTRY=1; static long KICK=0;
static int colholes(unsigned char*c){ int h=0; for(int y=0;y<k;y++){ int m=0; for(int R=0;R<N;R++)m|=1<<(a[R][y]*3+c[R]); h+=9-__builtin_popcount(m);} return h; }
static void addcol(void){ int X=k; unsigned char best[256],cand[256]; int bh=1<<30;
  for(int t=0;t<NTRY;t++){ for(int R=0;R<N;R++)cand[R]=rnd()%3; int h=NTRY>1?colholes(cand):0; if(h<bh){bh=h;memcpy(best,cand,N);} }
  for(int R=0;R<N;R++)a[R][X]=best[R]; k++;
  for(int y=0;y<X;y++){long b=pid(y,X); for(int R=0;R<N;R++)cnt[b+a[R][y]*3+a[R][X]]++; for(int p=0;p<9;p++){ if(cnt[b+p]==0){hpos[b+p]=H;hole[H++]=b+p;} else hpos[b+p]=-1; } } }
static void plist(char*s,unsigned char*f,int n){ char*t=strtok(s,","); while(t){int x=atoi(t); if(x>=0&&x<n)f[x]=1; t=strtok(NULL,",");} }
int main(int argc,char**argv){
  if(argc<10){fprintf(stderr,"usage: ext2t base N0 k0 r m seed secs T out [-i state] [-c cand] [-chain M] [-fr list] [-fc list] [-frl n]\n");return 2;}
  const char*basef=argv[1];N0=atoi(argv[2]);k0=atoi(argv[3]);r=atoi(argv[4]);m=atoi(argv[5]);
  long seed=atol(argv[6]);double secs=atof(argv[7]),T=atof(argv[8]);const char*out=argv[9];const char*init=NULL;int CAND=4,chain=0;
  N=N0+r;k=k0+m; frow=calloc(N+1,1); fcol=calloc(k0+m+1,1);
  for(int i=10;i<argc;i++){if(!strcmp(argv[i],"-i"))init=argv[++i];else if(!strcmp(argv[i],"-c"))CAND=atoi(argv[++i]);else if(!strcmp(argv[i],"-chain"))chain=atoi(argv[++i]);else if(!strcmp(argv[i],"-ntry"))NTRY=atoi(argv[++i]);else if(!strcmp(argv[i],"-kick"))KICK=atol(argv[++i]);
    else if(!strcmp(argv[i],"-fr"))plist(argv[++i],frow,N);else if(!strcmp(argv[i],"-fc"))plist(argv[++i],fcol,k);
    else if(!strcmp(argv[i],"-frl")){int n=atoi(argv[++i]);for(int j=N0-n;j<N0;j++)if(j>=0)frow[j]=1;}}
  KM=k+chain; rs=0x9E3779B97F4A7C15ULL^(seed*0xD1B54A32D192ED03ULL);for(int i=0;i<20;i++)rnd();
  a=malloc(N*sizeof*a);for(int i=0;i<N;i++){a[i]=malloc(KM);for(int j=0;j<KM;j++)a[i][j]=rnd()%3;}
  FILE*f=fopen(basef,"r");if(!f){perror(basef);return 2;}
  for(int i=0;i<N0;i++)for(int j=0;j<k0;j++){int x;if(fscanf(f,"%d",&x)!=1){fprintf(stderr,"short base\n");return 2;}a[i][j]=x;}fclose(f);
  if(init){f=fopen(init,"r");if(!f){perror(init);return 2;}for(int i=0;i<N;i++)for(int j=0;j<k;j++){int x;if(fscanf(f,"%d",&x)!=1){fprintf(stderr,"short init\n");return 2;}if(isfree(i,j))a[i][j]=x;else if(a[i][j]!=x){fprintf(stderr,"init differs from base at %d %d\n",i,j);return 2;}}fclose(f);}
  long total=(long)KM*KM*9; cnt=calloc(total,1);hpos=malloc(total*sizeof*hpos);hole=malloc(total*sizeof*hole);
  H=0; for(int w=1;w<k;w++)for(int u=0;u<w;u++){long b=pid(u,w);for(int R=0;R<N;R++)cnt[b+a[R][u]*3+a[R][w]]++;
    for(int p=0;p<9;p++){ if(cnt[b+p]==0){hpos[b+p]=H;hole[H++]=b+p;} else hpos[b+p]=-1; } }
  long nfree=0; for(int i=0;i<N;i++)for(int j=0;j<k;j++)nfree+=isfree(i,j);
  long best=H;double t0=clock()/(double)CLOCKS_PER_SEC,tl=t0,tk=t0;long it=0;fprintf(stderr,"N=%d k=%d free cells=%ld start holes=%ld T=%g\n",N,k,nfree,H,T);
  int *cr=malloc(N*sizeof*cr); int solvedk=0; long dead=0, itk=0;
  for(;;){
    if(H==0){ char fn[512];snprintf(fn,sizeof fn,"%s_%d_%d.txt",out,N,k);save(fn);solvedk=k;double now=clock()/(double)CLOCKS_PER_SEC;
      printf("FOUND %s t=%.1f (leg %.1f s) it=%ld\n",fn,now-t0,now-tk,it);fflush(stdout);tk=now;itk=it;
      if(k<KM){addcol();best=H;continue;} else break; }
    if((it&255)==0){double now=clock()/(double)CLOCKS_PER_SEC;if(now-t0>=secs)break;if(now-tl>=30){tl=now;fprintf(stderr,"t=%.0f it=%ld k=%d holes=%ld best=%ld\n",now-t0,it,k,H,best);}}
    it++;
    if(KICK&&k>k0&&k-1>=solvedk&&it-itk>KICK){ itk=it; k--; /* drop the stuck last column and draw a fresh one */
      for(int y=0;y<k;y++){long b=pid(y,k); for(int p=0;p<9;p++){ if(cnt[b+p]==0){long ps=hpos[b+p];long l=hole[--H];hole[ps]=l;hpos[l]=ps;} cnt[b+p]=0; hpos[b+p]=-1; } }
      addcol(); best=H; if(H==0)continue; }
    long id=hole[rnd()%H];int pat=id%9;long q=id/9;int u=q/KM,w=q%KM;int col[2]={u,w},val[2]={pat/3,pat%3};
    int nc=0;for(int R=0;R<N;R++){int ok=1;for(int e=0;e<2;e++)if(a[R][col[e]]!=val[e]&&!isfree(R,col[e])){ok=0;break;}if(ok)cr[nc++]=R;}
    if(!nc){dead++;continue;}
    long H0=H,bestH=-1;int bestR=-1;int tries=nc<CAND?nc:CAND;
    for(int c=0;c<tries;c++){int j=c+rnd()%(nc-c);int R=cr[j];cr[j]=cr[c];cr[c]=R;
      int o0=a[R][u],o1=a[R][w]; setc(R,u,val[0]); setc(R,w,val[1]);
      if(bestH<0||H<bestH){bestH=H;bestR=R;}
      setc(R,w,o1); setc(R,u,o0);}
    if(bestH<=H0||urand()<exp((H0-bestH)/T)){setc(bestR,u,val[0]);setc(bestR,w,val[1]);
      if(H<best){best=H;if(best<=30&&best>0){char fn[512];snprintf(fn,sizeof fn,"%s_best.txt",out);save(fn);}}}
  }
  printf("END N=%d k=%d holes=%ld best=%ld solvedk=%d it=%ld dead=%ld secs=%.0f T=%g\n",N,k,H,best,solvedk,it,dead,clock()/(double)CLOCKS_PER_SEC-t0,T);
  return H?1:0;
}
