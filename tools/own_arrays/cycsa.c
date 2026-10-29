/* cycsa.c - simulated annealing for binary covering arrays CA(N; t, k, 2), plain or
 * with a cyclic group acting on the columns (group construction, Meagher & Stevens 2005;
 * Chateauneuf, Colbourn & Kreher 1999). Written for ca-tools, 2026-10-27. No ingredient
 * array of anyone else is read unless given with -i (an array built here or algebraic).
 *
 * Model: columns 0..m-1 are permuted cyclically by Z_m, columns m..k-1 are fixed points.
 * The array has s "orbit" rows-generators (starters); each starter expands to its m cyclic
 * shifts (row (i,g) has value st_i[(c-g) mod m] in cycle column c and st_i[c] in fixed
 * column c), plus f fixed rows (constant a_j on the cycle columns, free on the fixed
 * columns). N = m*s + f. With m = 1 this is a plain array of s rows (ordinary SA).
 * Coverage is checked on orbit representatives of t-sets only (the row set is invariant).
 *
 * Cost = uncovered (representative t-set, tuple) pairs. Moves: flip one starter bit or
 * fixed-row bit (Metropolis), or a focused move: pick an uncovered pair, try every flip
 * that would cover it (rows at Hamming distance 1 on that t-set), take the best
 * (in the spirit of Nurmela 2004 and of the mixed neighbourhood of Torres-Jimenez &
 * Rodriguez-Tello 2012). Evaluation is incremental (counts per pair).
 *
 * Usage: cycsa t k m s f seed maxsec outprefix [-T T0] [-E Tend] [-C cycles]
 *               [-p focus_prob] [-i initfile] [-d Nmin]
 *   temperature falls geometrically from T0 to Tend over maxsec/cycles seconds, then restarts
 *   (from the current solution); defaults T0=2, Tend=0.05, cycles=1.
 *   -I iters : temperature follows the iteration count instead (cycle length = iters moves),
 *              which makes a run reproducible from its seed; maxsec still stops it.
 *   -S ps    : (m = 1 only) probability of a swap move: two cells of one column with
 *              different symbols exchange values (keeps column balance, TJ-RT 2012 style).
 *   -b       : balanced random start (each column has floor(N/2) or ceil(N/2) ones).
 *   -d Nmin : descent; after each success remove the starter with least unique coverage
 *             and continue, down to N = Nmin (only sensible for m = 1 or small m).
 * On success writes <outprefix>_<N>.txt (0-based, space separated) and continues if -d.
 * Exit 0 if at least one array was written.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <time.h>

static int t, k, m, s, f, nfix, TT;
static uint8_t *cyc2;   /* s x 2m */
static uint8_t *fx;     /* s x nfix */
static uint8_t *fa;     /* f */
static uint8_t *fb;     /* f x nfix */
static int R;           /* number of reps */
static uint8_t *reps;   /* R x t */
static uint8_t *cmask;  /* R: bitmask of cycle positions */
static uint16_t *cnt;   /* R x TT */
static int32_t *unc, *uncpos; static long nunc;
static long cost;
static int32_t *cl_r; static uint8_t *cl_q; static long ncl;   /* (rep,pos) with cycle col */
static int32_t **fl_r; static uint8_t **fl_q; static long *nfl; /* per fixed col */

static uint64_t rs;
static inline uint64_t xr(void){ rs ^= rs<<13; rs ^= rs>>7; rs ^= rs<<17; return rs; }
static inline int rnd(int n){ return (int)(xr() % (uint64_t)n); }
static inline double rndu(void){ return (xr()>>11) * (1.0/9007199254740992.0); }
static double now(void){ struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts); return ts.tv_sec+1e-9*ts.tv_nsec; }

static inline void dec(long key){ if(--cnt[key]==0){ uncpos[key]=nunc; unc[nunc++]=(int32_t)key; cost++; } }
static inline void inc(long key){ if(cnt[key]++==0){ long p=uncpos[key]; int32_t last=unc[--nunc]; unc[p]=last; uncpos[last]=p; uncpos[key]=-1; cost--; } }

static inline int tup_orb(int i,int g,int r){
    const uint8_t *T=reps+(long)r*t; const uint8_t *cy=cyc2+(long)i*2*m+m-g; const uint8_t *fi=fx+(long)i*nfix-m;
    int x=0; for(int q=0;q<t;q++){ int d=T[q]; x|=(d<m?cy[d]:fi[d])<<q; } return x; }
static inline int tup_fix(int j,int r){
    const uint8_t *T=reps+(long)r*t; int x=0; for(int q=0;q<t;q++){ int d=T[q]; x|=(d<m?fa[j]:fb[(long)j*nfix+d-m])<<q; } return x; }

/* variable ids: [0, s*k): starter i bit c (c<m cyclic pos, c>=m fixed col);
   [s*k, s*k+f*(1+nfix)): fixed row j: 0 -> a, 1+e -> fixed col m+e */
static long nvar;
static void flip(long v){
    if(v < (long)s*k){
        int i=v/k, c=v%k;
        if(c<m){
            for(long e=0;e<ncl;e++){ int r=cl_r[e], q=cl_q[e]; int d=reps[(long)r*t+q]; int g=d-c; if(g<0) g+=m;
                int x=tup_orb(i,g,r); long b=(long)r*TT; dec(b+x); inc(b+(x^(1<<q))); }
            cyc2[(long)i*2*m+c]^=1; cyc2[(long)i*2*m+m+c]^=1;
        } else {
            int e0=c-m;
            for(long e=0;e<nfl[e0];e++){ int r=fl_r[e0][e], q=fl_q[e0][e]; long b=(long)r*TT;
                for(int g=0;g<m;g++){ int x=tup_orb(i,g,r); dec(b+x); inc(b+(x^(1<<q))); } }
            fx[(long)i*nfix+e0]^=1;
        }
    } else {
        long w=v-(long)s*k; int j=w/(1+nfix), e0=w%(1+nfix);
        if(e0==0){
            for(int r=0;r<R;r++){ if(!cmask[r]) continue; int x=tup_fix(j,r); long b=(long)r*TT; dec(b+x); inc(b+(x^cmask[r])); }
            fa[j]^=1;
        } else { e0--;
            for(long e=0;e<nfl[e0];e++){ int r=fl_r[e0][e], q=fl_q[e0][e]; int x=tup_fix(j,r); long b=(long)r*TT; dec(b+x); inc(b+(x^(1<<q))); }
            fb[(long)j*nfix+e0]^=1;
        }
    }
}
static void add_all(int sign){ /* add (sign=1) contributions of all rows from scratch */
    for(int r=0;r<R;r++){ long b=(long)r*TT;
        for(int i=0;i<s;i++) for(int g=0;g<m;g++){ int x=tup_orb(i,g,r); if(sign>0) cnt[b+x]++; }
        for(int j=0;j<f;j++){ int x=tup_fix(j,r); if(sign>0) cnt[b+x]++; } }
    nunc=0; cost=0; for(long key=0;key<(long)R*TT;key++){ if(cnt[key]==0){ uncpos[key]=nunc; unc[nunc++]=key; cost++; } else uncpos[key]=-1; }
}
static void remove_starter(int i){
    for(int r=0;r<R;r++){ long b=(long)r*TT; for(int g=0;g<m;g++) dec(b+tup_orb(i,g,r)); }
    int l=s-1; if(i!=l){ memcpy(cyc2+(long)i*2*m,cyc2+(long)l*2*m,2*m); memcpy(fx+(long)i*nfix,fx+(long)l*nfix,nfix); }
    s--; nvar=(long)s*k+(long)f*(1+nfix);
    /* fixed-row variables shift index; nothing stored by index, fine */
}
static long uniq_of(int i){ long u=0; for(int r=0;r<R;r++){ long b=(long)r*TT; for(int g=0;g<m;g++) if(cnt[b+tup_orb(i,g,r)]==1) u++; } return u; }

static void write_out(const char *pre){
    char fn[1024]; int N=m*s+f; snprintf(fn,sizeof fn,"%s_%d.txt",pre,N);
    FILE *o=fopen(fn,"w"); if(!o){ perror(fn); return; }
    for(int i=0;i<s;i++) for(int g=0;g<m;g++){ for(int c=0;c<k;c++){ int v= c<m? cyc2[(long)i*2*m+((c-g+m)%m)] : fx[(long)i*nfix+c-m]; fprintf(o,c?" %d":"%d",v);} fputc('\n',o); }
    for(int j=0;j<f;j++){ for(int c=0;c<k;c++){ int v= c<m? fa[j] : fb[(long)j*nfix+c-m]; fprintf(o,c?" %d":"%d",v);} fputc('\n',o); }
    fclose(o); printf("WROTE %s N=%d\n",fn,N); fflush(stdout);
}

static int canon_is_min(const int *T){ /* T sorted; cycle part shifted by all h; is T lexicographically minimal? */
    int nc=0; while(nc<t && T[nc]<m) nc++;
    if(nc==0 || m==1) return 1;
    int U[16];
    for(int h=1;h<m;h++){
        for(int q=0;q<nc;q++) U[q]=(T[q]+h)%m;
        /* sort U[0..nc) */
        for(int a=1;a<nc;a++){ int x=U[a],b=a-1; while(b>=0&&U[b]>x){U[b+1]=U[b];b--;} U[b+1]=x; }
        for(int q=0;q<nc;q++){ if(U[q]<T[q]) return 0; if(U[q]>T[q]) break; }
    }
    return 1;
}

int main(int argc,char **argv){
    if(argc<9){ fprintf(stderr,"usage: cycsa t k m s f seed maxsec outprefix [-T T0] [-E Tend] [-C cycles] [-p pfocus] [-i init] [-d Nmin]\n"); return 2; }
    t=atoi(argv[1]); k=atoi(argv[2]); m=atoi(argv[3]); s=atoi(argv[4]); f=atoi(argv[5]);
    uint64_t seed=strtoull(argv[6],0,10); double maxsec=atof(argv[7]); const char *pre=argv[8];
    double T0=2.0, Tend=0.05, pf=0.02, ps=0.0; int cycles=1, bal=0; long L=0, IC=0; const char *init=0; int Nmin=-1;
    for(int a=9;a<argc;a++){
        if(!strcmp(argv[a],"-T")) T0=atof(argv[++a]); else if(!strcmp(argv[a],"-E")) Tend=atof(argv[++a]);
        else if(!strcmp(argv[a],"-C")) cycles=atoi(argv[++a]); else if(!strcmp(argv[a],"-p")) pf=atof(argv[++a]);
        else if(!strcmp(argv[a],"-i")) init=argv[++a]; else if(!strcmp(argv[a],"-d")) Nmin=atoi(argv[++a]);
        else if(!strcmp(argv[a],"-I")) IC=atol(argv[++a]); else if(!strcmp(argv[a],"-S")) ps=atof(argv[++a]);
        else if(!strcmp(argv[a],"-b")) bal=1; else { fprintf(stderr,"unknown option %s\n",argv[a]); return 2; } }
    if(t<2||t>7||m<1||m>k||k>255){ fprintf(stderr,"bad params\n"); return 2; }
    nfix=k-m; TT=1<<t;
    rs=seed*0x9E3779B97F4A7C15ULL+0x1234567ULL; if(!rs) rs=1; for(int i=0;i<20;i++) xr();
    /* reps */
    long cap=1024; reps=malloc(cap*t); R=0;
    int T[16]; for(int q=0;q<t;q++) T[q]=q;
    while(1){
        if(canon_is_min(T)){ if(R>=cap){ cap*=2; reps=realloc(reps,cap*t);} for(int q=0;q<t;q++) reps[(long)R*t+q]=T[q]; R++; }
        int q=t-1; while(q>=0 && T[q]==k-t+q) q--; if(q<0) break; T[q]++; for(int b=q+1;b<t;b++) T[b]=T[b-1]+1;
    }
    cmask=malloc(R); ncl=0;
    for(int r=0;r<R;r++){ int mk=0; for(int q=0;q<t;q++) if(reps[(long)r*t+q]<m){ mk|=1<<q; ncl++; } cmask[r]=mk; }
    cl_r=malloc(sizeof(int32_t)*ncl); cl_q=malloc(ncl); { long e=0; for(int r=0;r<R;r++) for(int q=0;q<t;q++) if(reps[(long)r*t+q]<m){ cl_r[e]=r; cl_q[e]=q; e++; } }
    fl_r=malloc(sizeof(void*)*(nfix+1)); fl_q=malloc(sizeof(void*)*(nfix+1)); nfl=calloc(nfix+1,sizeof(long));
    for(int r=0;r<R;r++) for(int q=0;q<t;q++){ int d=reps[(long)r*t+q]; if(d>=m) nfl[d-m]++; }
    for(int e=0;e<nfix;e++){ fl_r[e]=malloc(sizeof(int32_t)*(nfl[e]+1)); fl_q[e]=malloc(nfl[e]+1); nfl[e]=0; }
    for(int r=0;r<R;r++) for(int q=0;q<t;q++){ int d=reps[(long)r*t+q]; if(d>=m){ int e=d-m; fl_r[e][nfl[e]]=r; fl_q[e][nfl[e]]=q; nfl[e]++; } }
    cnt=calloc((long)R*TT,sizeof(uint16_t)); unc=malloc(sizeof(int32_t)*(long)R*TT); uncpos=malloc(sizeof(int32_t)*(long)R*TT);
    cyc2=calloc((long)s*2*m,1); fx=calloc((long)s*nfix+1,1); fa=calloc(f+1,1); fb=calloc((long)f*nfix+1,1);
    if(init){
        if(m!=1||f!=0){ fprintf(stderr,"-i needs m=1 f=0\n"); return 2; }
        FILE *in=fopen(init,"r"); if(!in){ perror(init); return 2; }
        /* read rows; take first k columns of each row and first s rows */
        char line[1<<16]; int i=0;
        while(i<s && fgets(line,sizeof line,in)){ int c=0; char *p=line; while(*p && c<k){ while(*p==' '||*p=='\t'||*p==',') p++; if(*p<'0'||*p>'9') break; int v=strtol(p,&p,10); if(c==0){ cyc2[(long)i*2]=v&1; cyc2[(long)i*2+1]=v&1; } else fx[(long)i*nfix+c-1]=v&1; c++; } if(c==k) i++; }
        fclose(in); for(;i<s;i++) for(int c=0;c<k;c++){ int v=rnd(2); if(c==0){cyc2[(long)i*2]=v;cyc2[(long)i*2+1]=v;} else fx[(long)i*nfix+c-1]=v; }
    } else {
        for(int i=0;i<s;i++){ for(int c=0;c<m;c++){ int v=rnd(2); cyc2[(long)i*2*m+c]=v; cyc2[(long)i*2*m+m+c]=v; } for(int e=0;e<nfix;e++) fx[(long)i*nfix+e]=rnd(2); }
        for(int j=0;j<f;j++){ fa[j]=j&1; for(int e=0;e<nfix;e++) fb[(long)j*nfix+e]=((j>>1)>>e)&1; }
        if(bal && m==1){ int *pm=malloc(sizeof(int)*s); for(int c=0;c<k;c++){ for(int i=0;i<s;i++) pm[i]=i; for(int i=s-1;i>0;i--){ int j=rnd(i+1),x=pm[i]; pm[i]=pm[j]; pm[j]=x; }
            for(int i=0;i<s;i++){ int v=(pm[i] < s/2)?1:0; if(c==0){ cyc2[(long)i*2]=v; cyc2[(long)i*2+1]=v; } else fx[(long)i*nfix+c-1]=v; } } free(pm); }
    }
    nvar=(long)s*k+(long)f*(1+nfix);
    add_all(1);
    printf("cycsa t=%d k=%d m=%d s=%d f=%d N=%d reps=%d pairs=%ld seed=%llu maxsec=%.0f T0=%g Tend=%g cycles=%d pf=%g ps=%g I=%ld bal=%d init_cost=%ld\n",t,k,m,s,f,m*s+f,R,(long)R*TT,(unsigned long long)seed,maxsec,T0,Tend,cycles,pf,ps,IC,bal,cost); fflush(stdout);
    L=1000;
    double Temp = T0;
    double t0=now(), lastp=t0, tc0=t0; long best=cost; long it=0, itc0=0, sinceimp=0; int wrote=0;
    long *cand=malloc(sizeof(long)*(m*s+f)*t+16);
    while(1){
        if(cost==0){
            write_out(pre); wrote=1;
            if(Nmin<0 || m*s+f-m < Nmin || s<=1) break;
            long bu=-1; int bi=0; for(int i=0;i<s;i++){ long u=uniq_of(i); if(bu<0||u<bu){bu=u;bi=i;} }
            remove_starter(bi); best=cost; tc0=now(); itc0=it; printf("  removed starter %d (unique %ld), N=%d cost=%ld\n",bi,bu,m*s+f,cost); fflush(stdout);
        }
        for(long l=0;l<L && cost>0;l++){
            it++;
            long c0=cost;
            if(nunc>0 && rndu()<pf){
                long key=unc[rnd(nunc)]; int r=key/TT, x=key%TT; int nc=0;
                for(int i=0;i<s;i++) for(int g=0;g<m;g++){ int z=tup_orb(i,g,r)^x; if(z && !(z&(z-1))){ int q=__builtin_ctz(z); int d=reps[(long)r*t+q]; cand[nc++]= d<m? (long)i*k+((d-g+m)%m) : (long)i*k+d; } }
                for(int j=0;j<f;j++){ int z=tup_fix(j,r)^x; if(z && !(z&(z-1))){ int q=__builtin_ctz(z); int d=reps[(long)r*t+q]; if(d>=m) cand[nc++]=(long)s*k+(long)j*(1+nfix)+1+(d-m); } if(z && z==cmask[r]) cand[nc++]=(long)s*k+(long)j*(1+nfix); }
                if(nc==0) continue;
                long bd=0, bv=-1; int ties=0;
                for(int c=0;c<nc;c++){ flip(cand[c]); long d=cost-c0; flip(cand[c]); if(bv<0||d<bd){bd=d;bv=cand[c];ties=1;} else if(d==bd && rnd(++ties)==0) bv=cand[c]; }
                if(bd<=0 || rndu()<exp(-bd/Temp)) flip(bv);
            } else if(ps>0 && m==1 && rndu()<ps){
                int c=rnd(k), i1=rnd(s), i2=rnd(s); long v1=(long)i1*k+c, v2=(long)i2*k+c;
                int a1= c==0? cyc2[(long)i1*2] : fx[(long)i1*nfix+c-1], a2= c==0? cyc2[(long)i2*2] : fx[(long)i2*nfix+c-1];
                if(a1==a2) continue;
                flip(v1); flip(v2); long d=cost-c0;
                if(d>0 && rndu()>=exp(-d/Temp)){ flip(v2); flip(v1); }
            } else {
                long v=rnd(nvar); flip(v); long d=cost-c0;
                if(d>0 && rndu()>=exp(-d/Temp)) flip(v);
            }
            if(cost<best){ best=cost; sinceimp=0; } else sinceimp++;
        }
        if(cost==0) continue;
        double tn=now();
        if(IC>0){ double fr=(double)((it-itc0)%IC)/IC; Temp=T0*pow(Tend/T0,fr); }
        else { double per=maxsec/cycles; double fr=fmod(tn-tc0,per)/per; Temp=T0*pow(Tend/T0,fr); }
        if(tn-lastp>30){ printf("  t=%.0fs it=%ld T=%.3f cost=%ld best=%ld N=%d\n",tn-t0,it,Temp,cost,best,m*s+f); fflush(stdout); lastp=tn; }
        if(tn-t0>maxsec) break;
    }
    if(cost>0 && cost<=64){ printf("UNCOVERED:"); for(long u=0;u<nunc;u++){ int r=unc[u]/TT, x=unc[u]%TT; printf(" {"); for(int q=0;q<t;q++) printf(q?",%d":"%d",reps[(long)r*t+q]); printf("}:"); for(int q=0;q<t;q++) printf("%d",(x>>q)&1); } printf("\n"); }
    printf("END it=%ld time=%.1fs final_cost=%ld best=%ld N=%d wrote=%d\n",it,now()-t0,cost,best,m*s+f,wrote);
    return wrote?0:1;
}
