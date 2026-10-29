/* cyccheck.c - full check of strength t for the binary cyclotomic (Paley-type) circulant of a prime q.
 *
 * The array A (q x q): A[r][c] = x[(c - r) mod q], with x[0] = 0, x[i] = 1 if i is a quadratic
 * nonresidue mod q, 0 if a residue (this is CAs::cyc(q, 2, type = "1")).  Read from a file (one row
 * of q digits, the first row of the array) or built here from the Legendre symbol.
 *
 * Symmetry used (each checked here, not assumed):
 *  - translation: a set S of columns is covered iff S + b is (rows shift with it); the input is a
 *    circulant by construction, and the program checks that row 0 is x;
 *  - multipliers: for a quadratic residue a, x[a i] = x[i] for all i (checked for a = g^2, g a
 *    primitive root, which generates the residues); then S is covered iff a S is.
 * Every t-set S has a translate containing 0 and a second element s; a residue multiplier maps s to
 * 1 or to the fixed nonresidue n0.  So it suffices to check all sets {0, 1} + (t-2)-subset and
 * {0, n0} + (t-2)-subset of the remaining q - 2 elements.
 *
 * Coverage of a set: the rows are split by the columns' bits (bitsets over the q rows); all 2^t
 * cells must be nonempty.  An empty cell for a subset means all its supersets are uncovered too.
 *
 * usage: cyccheck q t [vectorfile|-] [threads]       prints the number of uncovered representatives
 * build: gcc -O3 -march=native -fopenmp -o cyccheck cyccheck.c       (macOS: clang + libomp)
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#ifdef _OPENMP
#include <omp.h>
#endif
typedef uint64_t u64;
static int q, t, W, W2, use_mode;   /* use_mode 0 intersection (default), 1 row lists, 2 bitset split */
static u64 *ROT0, *ROT1;   /* ROT0[r]: bit e set iff x[(e - r) mod q] == 0; ROT1 likewise for 1 */
static u64 *B;          /* B[c*W ...]: bitset over rows r of A[r][c] = x[(c-r) mod q] */
static unsigned char *x, *x2;   /* x2[i] = x[i mod q], 0 <= i < 2q */
static long long powmod(long long a, long long e, long long m){ long long r=1; a%=m; while(e){ if(e&1) r=r*a%m; a=a*a%m; e>>=1;} return r; }
static int is_prime(int n){ if(n<2) return 0; for(int d=2; (long long)d*d<=n; d++) if(n%d==0) return 0; return 1; }

/* recursive split; cells: 2^L bitsets of W words at level L */
static long long check_rest(u64 *cells, int L, int start, int need, int *S, long long *found, int report){
  if(need==0) return 0;
  long long bad=0;
  int nc = 1<<L;
  if(need==1 && use_mode==0){
    /* last column by intersection: for a cell with rows R, the columns e on which it is all 0 are
       the intersection over r in R of {e : x[e - r] = 0} = rotation of Z0 by r (likewise all 1).
       The uncovered completions are the union over cells of these columns, restricted to e >= start,
       e != S[1]. */
    u64 *badset = calloc(W2, sizeof(u64)), *E0 = malloc(sizeof(u64)*W2), *E1 = malloc(sizeof(u64)*W2);
    for(int i=0;i<nc;i++){
      const u64 *cell=cells+(size_t)i*W; int first=1, alive0=1, alive1=1;
      for(int w=0;w<W && (alive0||alive1);w++){ u64 v=cell[w];
        while(v && (alive0||alive1)){ int r=w*64+__builtin_ctzll(v); v&=v-1;
          const u64 *z0=ROT0+(size_t)r*W2, *z1=ROT1+(size_t)r*W2;
          if(first){ memcpy(E0,z0,sizeof(u64)*W2); memcpy(E1,z1,sizeof(u64)*W2); first=0; }
          else { u64 o0=0,o1=0;
            if(alive0){ for(int j=0;j<W2;j++){ E0[j]&=z0[j]; o0|=E0[j]; } if(!o0) alive0=0; }
            if(alive1){ for(int j=0;j<W2;j++){ E1[j]&=z1[j]; o1|=E1[j]; } if(!o1) alive1=0; }
          } } }
      if(alive0) for(int j=0;j<W2;j++) badset[j]|=E0[j];
      if(alive1) for(int j=0;j<W2;j++) badset[j]|=E1[j];
    }
    for(int e=start;e<q;e++) if(e!=S[1] && ((badset[e/64]>>(e%64))&1)){ bad++;
        if(*found<report){
          #pragma omp critical
          { if(*found<report){ printf("  uncovered:"); for(int j=0;j<L;j++) printf(" %d",S[j]); printf(" %d\n", e); } (*found)++; }
        } }
    free(badset); free(E0); free(E1);
    return bad;
  }
  if(need==1 && use_mode==1){
    /* last column: unpack each cell's rows once, then for each candidate e check that both
       values occur in every cell (exit at the first two different values) */
    int *rows = malloc(sizeof(int)*q), *off = malloc(sizeof(int)*(nc+1)); int m=0;
    for(int i=0;i<nc;i++){ off[i]=m; const u64 *cell=cells+(size_t)i*W;
      for(int w=0;w<W;w++){ u64 v=cell[w]; while(v){ int bpos=__builtin_ctzll(v); rows[m++]=w*64+bpos; v&=v-1; } } }
    off[nc]=m;
    for(int e=start;e<q;e++){
      if(e==S[1]) continue;
      const unsigned char *xe = x2 + e + q;   /* xe[-r] = x[(e - r) mod q] */
      int ok=1;
      for(int i=0;i<nc && ok;i++){
        int a0=off[i], a1=off[i+1]; unsigned char first = xe[-rows[a0]]; int j=a0+1;
        while(j<a1 && xe[-rows[j]]==first) j++;
        if(j==a1) ok=0;
      }
      if(!ok){ bad++;
        if(*found<report){
          #pragma omp critical
          { if(*found<report){ printf("  uncovered:"); for(int j=0;j<L;j++) printf(" %d",S[j]); printf(" %d\n", e); } (*found)++; }
        }
      }
    }
    free(rows); free(off);
    return bad;
  }
  u64 *nxt = malloc(sizeof(u64)*(size_t)W*nc*2);
  for(int c=start; c<=q-need; c++){
    if(c==S[1]) continue;
    const u64 *b = B + (size_t)c*W;
    int ok=1;
    for(int i=0;i<nc && ok;i++){
      const u64 *cell = cells + (size_t)i*W;
      u64 *o0 = nxt + (size_t)(2*i)*W, *o1 = nxt + (size_t)(2*i+1)*W;
      u64 n0=0, n1=0;
      for(int w=0;w<W;w++){ u64 a=cell[w]&~b[w], d=cell[w]&b[w]; o0[w]=a; o1[w]=d; n0|=a; n1|=d; }
      if(!n0 || !n1) ok=0;
    }
    S[L]=c;
    if(!ok){
      /* every completion of this partial set is uncovered; count the completions */
      long long cnt=1; int avail=0;
      for(int e=c+1;e<q;e++) if(e!=S[1]) avail++;
      int k=need-1; for(int j=0;j<k;j++) cnt = cnt*(avail-j)/(j+1);
      if(k>avail) cnt=0;
      bad+=cnt;
      if(*found<report)
      #pragma omp critical
      { if(*found<report){ printf("  uncovered (partial set):"); for(int j=0;j<=L;j++) printf(" %d",S[j]); printf(" (+%d more)\n", need-1); } (*found)++; }
      continue;
    }
    bad += check_rest(nxt, L+1, c+1, need-1, S, found, report);
  }
  free(nxt);
  return bad;
}

int main(int argc, char **argv){
  if(argc<3){ fprintf(stderr,"usage: cyccheck q t [vectorfile|-] [threads]\n"); return 2; }
  q=atoi(argv[1]); t=atoi(argv[2]);
  if(!is_prime(q) || q<11 || t<3 || t>8){ fprintf(stderr,"need prime q >= 11, 3 <= t <= 8\n"); return 2; }
  int threads = argc>4 ? atoi(argv[4]) : 0;
#ifdef _OPENMP
  if(threads>0) omp_set_num_threads(threads);
#endif
  x = malloc(q);
  for(int i=0;i<q;i++) x[i] = (i==0) ? 0 : (powmod(i,(q-1)/2,q)==1 ? 0 : 1);
  if(argc>3 && strcmp(argv[3],"-")){
    FILE *f=fopen(argv[3],"r"); if(!f){ perror(argv[3]); return 2; }
    int i=0, ch; unsigned char *y=malloc(q);
    while(i<q && (ch=fgetc(f))!=EOF){ if(ch=='0'||ch=='1') y[i++]=ch-'0'; else if(ch!=' '&&ch!='\t'&&ch!='\r'&&ch!='\n'){ fprintf(stderr,"bad char\n"); return 2; } }
    fclose(f);
    if(i<q){ fprintf(stderr,"vector file has %d < %d entries\n", i, q); return 2; }
    int diff=0; for(int j=0;j<q;j++) if(y[j]!=x[j]) diff++;
    printf("vector file %s: %d entries differ from the nonresidue indicator\n", argv[3], diff);
    memcpy(x,y,q); free(y);
  }
  /* multiplier check */
  int g=0;
  for(int c=2;c<q && !g;c++){ int ok=1; int m=q-1; for(int p=2;p<=m;p++) if(m%p==0){ while(m%p==0) m/=p; if(powmod(c,(q-1)/p,q)==1){ ok=0; break; } } if(ok) g=c; }
  int a = (int)((long long)g*g%q);
  int msym=1; for(int i=0;i<q;i++) if(x[(long long)a*i%q]!=x[i]){ msym=0; break; }
  int n0=0; for(int i=2;i<q;i++) if(powmod(i,(q-1)/2,q)!=1){ n0=i; break; }
  printf("q=%d t=%d primitive root %d, residue multiplier a=%d: x[a i]=x[i] for all i: %s; nonresidue n0=%d\n", q,t,g,a, msym?"yes":"NO", n0);
  if(!msym){ printf("RESULT: symmetry certificate failed, reduction not valid\n"); return 1; }
  W2=(q+63)/64;
  ROT0=calloc((size_t)q*W2,sizeof(u64)); ROT1=calloc((size_t)q*W2,sizeof(u64));
  for(int r=0;r<q;r++) for(int e=0;e<q;e++){ if(x[((e-r)%q+q)%q]) ROT1[(size_t)r*W2+e/64]|=1ULL<<(e%64); else ROT0[(size_t)r*W2+e/64]|=1ULL<<(e%64); }
  x2 = malloc((size_t)2*q); for(int i=0;i<2*q;i++) x2[i]=x[i%q];
  W=(q+63)/64;
  B = calloc((size_t)q*W, sizeof(u64));
  for(int c=0;c<q;c++) for(int r=0;r<q;r++) if(x[((c-r)%q+q)%q]) B[(size_t)c*W + r/64] |= 1ULL<<(r%64);
  long long total_bad=0, found=0;
  use_mode = getenv("CYC_MODE") ? atoi(getenv("CYC_MODE")) : 0;
  if(getenv("CYC_BITSET")) use_mode = 2;
  int cmin = getenv("CYC_CMIN") ? atoi(getenv("CYC_CMIN")) : 1;   /* benchmarking only */
  if(cmin>1) printf("BENCHMARK: third element limited to >= %d, not a full check\n", cmin);
  int cmax = getenv("CYC_CMAX") ? atoi(getenv("CYC_CMAX")) : q;   /* benchmarking only */
  if(cmax<q) printf("BENCHMARK: third element limited to < %d, not a full check\n", cmax);
  int seconds[2]={1,n0};
  for(int si=0;si<2;si++){
    int s=seconds[si];
    /* cells after columns 0 and s */
    u64 *base=calloc((size_t)4*W,sizeof(u64));
    const u64 *b0=B, *bs=B+(size_t)s*W;
    for(int w=0;w<W;w++){
      u64 full = (w==W-1 && q%64) ? ((1ULL<<(q%64))-1) : ~0ULL;
      base[0*W+w]=full&~b0[w]&~bs[w]; base[1*W+w]=full&~b0[w]&bs[w];
      base[2*W+w]=full&b0[w]&~bs[w];  base[3*W+w]=full&b0[w]&bs[w];
    }
    int empty=0; for(int i=0;i<4;i++){ u64 o=0; for(int w=0;w<W;w++) o|=base[i*W+w]; if(!o) empty=1; }
    if(empty){ printf("  pair {0,%d} already uncovered\n", s); total_bad++; free(base); continue; }
    long long bad=0;
    /* parallel over the third element */
    #pragma omp parallel for schedule(dynamic,1) reduction(+:bad)
    for(int c=cmin;c<cmax;c++){
      if(c==s) continue;
      if(q-c < t-2) continue;
      int S[16]; S[0]=0; S[1]=s;
      u64 *cells=malloc(sizeof(u64)*(size_t)W*8);
      const u64 *b=B+(size_t)c*W; int ok=1;
      for(int i=0;i<4;i++){ u64 n0_=0,n1_=0; for(int w=0;w<W;w++){ u64 u=base[i*W+w]&~b[w], d=base[i*W+w]&b[w]; cells[(2*i)*W+w]=u; cells[(2*i+1)*W+w]=d; n0_|=u; n1_|=d; } if(!n0_||!n1_) ok=0; }
      S[2]=c;
      if(!ok){ bad++; 
        #pragma omp critical
        { if(found<10) printf("  uncovered (partial set): 0 %d %d\n", s, c); found++; }
      }
      else if(t>3) bad += check_rest(cells, 3, c+1, t-3, S, &found, 10);
      free(cells);
    }
    printf("  second element %d: uncovered representatives %lld\n", s, bad);
    total_bad += bad; free(base);
  }
  printf("RESULT q=%d t=%d: %s (uncovered representatives counted: %lld)\n", q, t, total_bad? "NOT covered":"CA VERIFIED", total_bad);
  return total_bad?1:0;
}
