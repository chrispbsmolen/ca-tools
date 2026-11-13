/* extv.c - frozen-core extension annealer, any strength t (2..6) and alphabet v (2..16). ca-tools engine, own code.
 * Generalises extt.c (binary) to v symbols. The base CA (N0 x k0) is frozen; r free rows and m free columns are
 * added; only t-sets containing at least one new column are counted (the base covers the rest), plus, when m = 0,
 * nothing (use fillrows.c for rows only).
 * usage: extv t v base N0 k0 r m seed secs T out [-i state]
 * Moves: single free cell to a random symbol, or a repair move that takes a hole (t-set, tuple) and writes one of its
 * symbols into a free cell of a random row. Metropolis at temperature T with reheats. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <stdint.h>
static int t, v, N0, k0, r, m, N, k, P;
static unsigned char **a; static int *sets; static long ns; static int **inc_; static long *ninc;
static uint16_t *cnt; static int32_t *hpos, *hole; static long H;
static uint64_t rs; static inline uint64_t rnd(void) { rs ^= rs << 13; rs ^= rs >> 7; rs ^= rs << 17; return rs; }
static inline double urand(void) { return (rnd() >> 11) * (1.0 / 9007199254740992.0); }
static inline void decc(long id) { if (--cnt[id] == 0) { hpos[id] = H; hole[H++] = id; } }
static inline void incc(long id) { if (cnt[id]++ == 0) { int32_t p = hpos[id]; int32_t l = hole[--H]; hole[p] = l; hpos[l] = p; hpos[id] = -1; } }
static inline int pat(const unsigned char *row, const int *s) { int p = 0; for (int e = 0; e < t; e++) p = p * v + row[s[e]]; return p; }
static int POW[8];
static void setcell(int R, int X, int nv) {
    unsigned char *row = a[R]; long n = ninc[X]; int *L = inc_[X]; int old = row[X];
    for (long i = 0; i < n; i++) { long s = L[i]; const int *S = sets + s * t; int p = pat(row, S); int w = 0;
        for (int e = 0; e < t; e++) if (S[e] == X) w = POW[t - 1 - e];
        decc(s * P + p); incc(s * P + p + (nv - old) * w); }
    row[X] = nv;
}
static long delta(int R, int X, int nv) {   /* change in the number of holes */
    unsigned char *row = a[R]; long n = ninc[X]; int *L = inc_[X]; int old = row[X]; long d = 0;
    for (long i = 0; i < n; i++) { long s = L[i]; const int *S = sets + s * t; int p = pat(row, S); int w = 0;
        for (int e = 0; e < t; e++) if (S[e] == X) w = POW[t - 1 - e];
        long q = p + (nv - old) * w; if (cnt[s * P + p] == 1) d++; if (cnt[s * P + q] == 0) d--; }
    return d;
}
static int isfree(int R, int X) { return R >= N0 || X >= k0; }
static void save(const char *fn) { FILE *f = fopen(fn, "w"); for (int i = 0; i < N; i++) { for (int j = 0; j < k; j++) fprintf(f, j ? " %d" : "%d", a[i][j]); fprintf(f, "\n"); } fclose(f); }
int main(int argc, char **argv) {
    if (argc < 12) { fprintf(stderr, "usage: extv t v base N0 k0 r m seed secs T out [-i state]\n"); return 2; }
    t = atoi(argv[1]); v = atoi(argv[2]); const char *basef = argv[3]; N0 = atoi(argv[4]); k0 = atoi(argv[5]); r = atoi(argv[6]); m = atoi(argv[7]);
    long seed = atol(argv[8]); double secs = atof(argv[9]), T0 = atof(argv[10]); const char *out = argv[11]; const char *init = NULL;
    for (int i = 12; i < argc; i++) if (!strcmp(argv[i], "-i")) init = argv[++i];
    N = N0 + r; k = k0 + m; P = 1; for (int i = 0; i < t; i++) P *= v; POW[0] = 1; for (int i = 1; i < t; i++) POW[i] = POW[i - 1] * v;
    rs = 0x9E3779B97F4A7C15ULL ^ (seed * 0xD1B54A32D192ED03ULL); for (int i = 0; i < 20; i++) rnd();
    a = malloc(N * sizeof *a); for (int i = 0; i < N; i++) { a[i] = malloc(k); for (int j = 0; j < k; j++) a[i][j] = rnd() % v; }
    FILE *f = fopen(basef, "r"); if (!f) { perror("base"); return 2; }
    for (int i = 0; i < N0; i++) for (int j = 0; j < k0; j++) { int x; if (fscanf(f, "%d", &x) != 1) { fprintf(stderr, "base too small\n"); return 2; } a[i][j] = x; }
    fclose(f);
    if (init) { f = fopen(init, "r"); for (int i = 0; i < N; i++) for (int j = 0; j < k; j++) { int x; if (fscanf(f, "%d", &x) == 1) a[i][j] = x; } fclose(f); }
    /* t-sets with at least one new column */
    long cap = 1 << 20; sets = malloc(sizeof(int) * cap * t); ns = 0; int c[8];
    for (int i = 0; i < t; i++) c[i] = i;
    for (;;) { if (c[t - 1] >= k0) { if (ns == cap) { cap *= 2; sets = realloc(sets, sizeof(int) * cap * t); } memcpy(sets + ns * t, c, sizeof(int) * t); ns++; }
        int i = t - 1; while (i >= 0 && c[i] == k - t + i) i--; if (i < 0) break; c[i]++; for (int j = i + 1; j < t; j++) c[j] = c[j - 1] + 1; }
    ninc = calloc(k, sizeof(long)); for (long s = 0; s < ns; s++) for (int e = 0; e < t; e++) ninc[sets[s * t + e]]++;
    inc_ = malloc(sizeof(int *) * k); long *fl = calloc(k, sizeof(long)); for (int j = 0; j < k; j++) inc_[j] = malloc(sizeof(int) * (ninc[j] + 1));
    for (long s = 0; s < ns; s++) for (int e = 0; e < t; e++) { int j = sets[s * t + e]; inc_[j][fl[j]++] = s; }
    cnt = calloc(ns * P, sizeof(uint16_t)); hpos = malloc(sizeof(int32_t) * ns * P); hole = malloc(sizeof(int32_t) * ns * P); H = 0;
    for (long s = 0; s < ns; s++) for (int i = 0; i < N; i++) cnt[s * P + pat(a[i], sets + s * t)]++;
    for (long id = 0; id < ns * P; id++) { hpos[id] = -1; if (!cnt[id]) { hpos[id] = H; hole[H++] = id; } }
    fprintf(stderr, "extv t=%d v=%d: %d x %d frozen, +%d rows, +%d cols: %ld sets, holes %ld\n", t, v, N0, k0, r, m, ns, H);
    clock_t t0 = clock(); double T = T0; long best = H, it = 0;
    while (H > 0) {
        if ((it & 1023) == 0 && (double)(clock() - t0) / CLOCKS_PER_SEC > secs) break;
        int R, X, nv;
        if (rnd() & 1) { long id = hole[rnd() % H]; long s = id / P; int p = id % P; const int *S = sets + s * t;
            R = rnd() % N; int e = rnd() % t; X = S[e]; if (!isfree(R, X)) { /* try a free row instead */ if (!r) continue; R = N0 + rnd() % r; }
            nv = (p / POW[t - 1 - e]) % v;
        } else { R = rnd() % N; X = rnd() % k; if (!isfree(R, X)) continue; nv = rnd() % v; }
        if (a[R][X] == nv) continue;
        long d = delta(R, X, nv);
        if (d <= 0 || urand() < exp(-d / T)) { setcell(R, X, nv); if (H < best) { best = H; } }
        it++; T *= 0.99995; if (T < 0.05) T = T0;
    }
    fprintf(stderr, "end holes %ld best %ld it %ld time %.1f\n", H, best, it, (double)(clock() - t0) / CLOCKS_PER_SEC);
    if (H == 0) { save(out); printf("FOUND %d x %d\n", N, k); return 0; }
    printf("NOT FOUND %ld\n", H); return 1;
}
