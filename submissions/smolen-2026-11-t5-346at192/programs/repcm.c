// rep.c: t=5 repair of wide binary arrays by bit flips, exact incremental hole/unique lists.
// usage: rep FILE ndel seed secs T out [fixed_del_rows comma list]
// Delete ndel rows (random or given), then repair holes by flipping single entries.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <time.h>
#define MAXW 4
static int N,K,W;
static uint8_t *A; // N x K
typedef struct {int16_t c[5]; uint8_t v[5]; int row;} Ev;
static Ev *ev; static int nev, capev;
static uint64_t rs;
static inline uint64_t rnd(){rs^=rs<<13;rs^=rs>>7;rs^=rs<<17;return rs;}
static inline double ur(){return (rnd()>>11)*(1.0/9007199254740992.0);}
static void addev(int16_t *c,int pat,int row){ // c sorted? pat bit i = value at c[i]
  if(nev==capev){capev=capev?capev*2:1024;ev=realloc(ev,capev*sizeof(Ev));}
  Ev *e=&ev[nev++]; for(int i=0;i<5;i++){e->c[i]=c[i];e->v[i]=(pat>>i)&1;} e->row=row;}
// scan all 5-sets containing column c0 whose other 4 columns are in allowed[0..na)
static void scan(int c0,int *allowed,int na){
  static uint64_t rb[2048][MAXW]; // permuted rows
  int nw=(na+63)/64;
  for(int r=0;r<N;r++){for(int w=0;w<nw;w++)rb[r][w]=0; for(int i=0;i<na;i++) if(A[r*K+allowed[i]]) rb[r][i>>6]|=1ULL<<(i&63);}
  static int L[5][2048]; int m[5];
  // level0: split by c0
  int m0[2]={0,0}; static int cl0[2][2048];
  for(int r=0;r<N;r++){int b=A[r*K+c0];cl0[b][m0[b]++]=r;}
  for(int b=0;b<2;b++){
   for(int i2=0;i2<na;i2++){
    int m2[2]={0,0}; static int l2[2][2048];
    for(int q=0;q<m0[b];q++){int r=cl0[b][q];int x=A[r*K+allowed[i2]];l2[x][m2[x]++]=r;}
    for(int b2=0;b2<2;b2++) for(int i3=i2+1;i3<na;i3++){
      int m3[2]={0,0}; static int l3[2][2048];
      for(int q=0;q<m2[b2];q++){int r=l2[b2][q];int x=A[r*K+allowed[i3]];l3[x][m3[x]++]=r;}
      for(int b3=0;b3<2;b3++) for(int i4=i3+1;i4<na-1;i4++){
        int m4[2]={0,0}; static int l4[2][2048];
        for(int q=0;q<m3[b3];q++){int r=l3[b3][q];int x=A[r*K+allowed[i4]];l4[x][m4[x]++]=r;}
        for(int b4=0;b4<2;b4++){
          int *rows=l4[b4]; int mm=m4[b4];
          uint64_t o1[MAXW]={0},t1[MAXW]={0},o0[MAXW]={0},t0[MAXW]={0};
          for(int q=0;q<mm;q++){uint64_t *w=rb[rows[q]];for(int k=0;k<nw;k++){uint64_t x=w[k];t1[k]|=o1[k]&x;o1[k]|=x;uint64_t y=~x;t0[k]|=o0[k]&y;o0[k]|=y;}}
          int16_t cc[5]={c0,allowed[i2],allowed[i3],allowed[i4],0};
          int base=b|(b2<<1)|(b3<<2)|(b4<<3);
          for(int k=0;k<nw;k++){
            uint64_t hmask=~0ULL; // d index > i4
            for(int bit=0;bit<2;bit++){
              uint64_t once=bit?o1[k]:o0[k], twice=bit?t1[k]:t0[k];
              uint64_t hole=~once, uni=once&~twice;
              // restrict to d idx>i4 and < na
              for(int half=0;half<2;half++){uint64_t msk=half?uni:hole;
                if(!msk)continue;
                while(msk){int bi=__builtin_ctzll(msk);msk&=msk-1;int d=k*64+bi; if(d<=i4||d>=na)continue;
                  cc[4]=allowed[d]; int pat=base|(bit<<4);
                  int row=-1;
                  if(half){for(int q=0;q<mm;q++){int r=rows[q]; if(A[r*K+allowed[d]]==bit){row=rows[q];break;}}}
                  addev(cc,pat,row);}
              }
            }
          }
        }
      }
    }
   }
  }
}
static int hasc(Ev*e,int c){for(int i=0;i<5;i++)if(e->c[i]==c)return i;return -1;}
static void fullscan(){nev=0;int al[2048];for(int c=0;c<K;c++){int na=0;for(int d=c+1;d<K;d++)al[na++]=d; if(na>=4) scan(c,al,na);}}
static void rescan(int c){int j=0;for(int i=0;i<nev;i++) if(hasc(&ev[i],c)<0) ev[j++]=ev[i]; nev=j;
  int al[2048],na=0;for(int d=0;d<K;d++)if(d!=c)al[na++]=d; scan(c,al,na);}
static int nholes(){int h=0;for(int i=0;i<nev;i++)if(ev[i].row<0)h++;return h;}
int main(int argc,char**argv){
  FILE*f=fopen(argv[1],"r"); int ndel=atoi(argv[2]); rs=atoll(argv[3])*2654435761ULL+88172645463325252ULL; double secs=atof(argv[4]); double T=atof(argv[5]); char*out=argv[6];
  int N0=0; static char line[20000]; int cap=0; uint8_t*B=NULL;
  while(fgets(line,sizeof line,f)){int k=0;uint8_t row[2048];for(char*p=line;*p;p++)if(*p=='0'||*p=='1')row[k++]=*p-'0'; if(!k)continue;K=k; if(N0==cap){cap=cap?cap*2:512;B=realloc(B,(size_t)cap*K);} memcpy(B+(size_t)N0*K,row,K);N0++;}
  fclose(f);
  int del[64]={0}; int isdel[4096]={0};
  if(argc>7){char*p=argv[7];for(int i=0;i<ndel;i++){del[i]=strtol(p,&p,10);if(*p==',')p++;}}
  else for(int i=0;i<ndel;i++){int r;do r=rnd()%N0;while(isdel[r]);isdel[r]=1;del[i]=r;}
  for(int i=0;i<ndel;i++)isdel[del[i]]=1;
  N=0;A=malloc((size_t)N0*K);for(int r=0;r<N0;r++)if(!isdel[r]){memcpy(A+(size_t)N*K,B+(size_t)r*K,K);N++;}
  fprintf(stderr,"N=%d K=%d deleted:",N,K);for(int i=0;i<ndel;i++)fprintf(stderr," %d",del[i]);fprintf(stderr,"\n");
  clock_t t0=clock(); fullscan(); int H=nholes();
  fprintf(stderr,"fullscan %.2fs events=%d holes=%d\n",(double)(clock()-t0)/CLOCKS_PER_SEC,nev,H);
  int best=H; long it=0; static int tabu[4096][256]; // iteration until which (r,c) tabu
  int Nmin=getenv("NMIN")?atoi(getenv("NMIN")):N;
 again:
  while(((getenv("MAXIT")?(it<atol(getenv("MAXIT"))):((double)(clock()-t0)/CLOCKS_PER_SEC<secs))) && H>0){
    it++;
    // pick random hole
    int hi=-1,cnt=0;for(int i=0;i<nev;i++)if(ev[i].row<0){cnt++;if(rnd()%cnt==0)hi=i;}
    Ev h=ev[hi];
    int bd=1<<30,br=-1,bj=-1,nb=0;
    for(int r=0;r<N;r++){
      int diff=-1,nd=0;for(int i=0;i<5;i++)if(A[r*K+h.c[i]]!=h.v[i]){nd++;diff=i;if(nd>1)break;}
      if(nd!=1)continue; int c=h.c[diff]; if(tabu[r][c]>it)continue;
      int lost=0,gain=0; int nv=1-A[r*K+c];
      for(int i=0;i<nev;i++){Ev*e=&ev[i];int j=hasc(e,c);if(j<0)continue;
        if(e->row==r)lost++;
        else if(e->row<0){int ok=1;for(int q=0;q<5;q++){int val=(q==j)?nv:A[r*K+e->c[q]];if(val!=e->v[q]){ok=0;break;}} if(ok)gain++;}}
      int d=lost-gain;
      if(d<bd){bd=d;br=r;bj=diff;nb=1;} else if(d==bd){nb++;if(rnd()%nb==0){br=r;bj=diff;}}
    }
    if(br<0)continue;
    if(bd>0 && ur()>exp(-bd/T)) {continue;}
    int c=h.c[bj]; A[br*K+c]^=1; tabu[br][c]=it+50+rnd()%50;
    rescan(c); H=nholes();
    if(H<best){best=H;fprintf(stderr,"it=%ld t=%.1f holes=%d events=%d\n",it,(double)(clock()-t0)/CLOCKS_PER_SEC,H,nev);}
  }
  if(H==0){ char fn[512]; snprintf(fn,sizeof fn,"%s_%d.txt",out,N); FILE*o=fopen(fn,"w");for(int r=0;r<N;r++){for(int c=0;c<K;c++)fprintf(o,"%d%c",A[r*K+c],c==K-1?'\n':' ');}fclose(o);
    fprintf(stderr,"WROTE %s t=%.1f\n",fn,(double)(clock()-t0)/CLOCKS_PER_SEC);
    if(N>Nmin){ int *u=calloc(N,sizeof(int)); for(int i=0;i<nev;i++) if(ev[i].row>=0) u[ev[i].row]++;
      int br=0; for(int r=1;r<N;r++) if(u[r]<u[br]) br=r; fprintf(stderr,"delete row %d (unique %d)\n",br,u[br]); free(u);
      memmove(A+(size_t)br*K,A+(size_t)(br+1)*K,(size_t)(N-1-br)*K); N--; fullscan(); H=nholes(); best=H; memset(tabu,0,sizeof tabu);
      fprintf(stderr,"N=%d holes=%d\n",N,H); goto again; } }
  fprintf(stderr,"end it=%ld holes=%d best=%d\n",it,H,best);
  if(H>0){ char fn[512]; snprintf(fn,sizeof fn,"%s_cur_%d.txt",out,N); FILE*o=fopen(fn,"w");for(int r=0;r<N;r++){for(int c=0;c<K;c++)fprintf(o,"%d%c",A[r*K+c],c==K-1?'\n':' ');}fclose(o); fprintf(stderr,"saved state %s\n",fn); }
  if(H==0){FILE*o=fopen(out,"w");for(int r=0;r<N;r++){for(int c=0;c<K;c++)fprintf(o,"%d%c",A[r*K+c],c==K-1?'\n':' ');}fclose(o);printf("TIE N=%d written %s\n",N,out);}
  return 0;}
