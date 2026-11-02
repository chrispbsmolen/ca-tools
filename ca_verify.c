/* ca_verify (version 2, 2026-11-02) - fast exact strength-t coverage checker for covering arrays.
 *
 * Drop-in replacement for the first ca_verify.c, which it replaced in this
 * file on 2026-11-02 (same arguments, same stdout lines, same exit codes,
 * same input conventions, same list of example gaps), typically two to
 * three orders of magnitude faster on large arrays.
 *
 * Verifies that an N x k array over v symbols covers every t-way interaction:
 * for every choice of t columns and every one of the v^t value tuples, some
 * row exhibits that tuple. The verdict is exact; nothing is sampled.
 *
 * Input format: plain text, one row per line, entries separated by spaces,
 * tabs or commas. Symbols may be 0..v-1 or 1..v (auto-shifted). A '-', '*',
 * 'NA' or 'x' entry is a don't-care (flexible value). A row contributes
 * nothing to a projection in which it has a don't-care: coverage must hold
 * on the concrete entries alone (the "promise" rule of caverify 0.2.0).
 *
 * Usage: ca_verify FILE t v [threads] [SHARD/NSHARDS] [--fail-fast]
 *   threads        1..64, default 4 (as ca_verify)
 *   SHARD/NSHARDS  check only the t-sets whose smallest column is congruent
 *                  to SHARD modulo NSHARDS (0 <= SHARD < NSHARDS). The
 *                  NSHARDS runs partition the C(k,t) column sets exactly, so
 *                  their "column sets" counts add up to C(k,t) and the array
 *                  is a covering array iff every shard reports VERIFIED.
 *                  Output lines then carry a "(shard S/M)" marker.
 *   --fail-fast    stop at the first gap found (exit 1); the gap and tuple
 *                  counts printed are then lower bounds and the reported
 *                  gaps are not necessarily the lexicographically first.
 * Exit status: 0 = full coverage verified, 1 = coverage gaps found, 2 = error.
 *
 * Method (see tools/RESEARCH_ca_verify.md): every t-set of columns is written uniquely as a
 * (t-1)-set P (its t-1 smallest columns) plus its largest column d. For a
 * fixed P the rows are partitioned by their value tuple on P into v^(t-1)
 * classes. The t-set P+{d} covers tuple (s,u) iff some row of class s has
 * value u in column d. For each class s we therefore OR together the row
 * bit-planes (row r's plane for value u has bit d set iff A[r][d] == u) of
 * the rows of class s, restricted to columns d > max(P); the AND over u of
 * those ORs has bit d clear exactly where P+{d} misses a tuple. This checks
 * all candidate columns d at once with 64-bit (or 256-bit SIMD) words,
 * which makes the work per (t-1)-set about N*v*(k/64) word operations
 * instead of N*t scalar operations per t-set. Classes are formed
 * incrementally along a depth-first enumeration of the (t-1)-sets using
 * per-(column,value) row bitsets, so each class costs one bitset AND.
 * Binary arrays without don't-cares use a single plane per row with an OR
 * and an AND accumulator (value 1 missing <=> OR bit clear, value 0 missing
 * <=> AND bit set).
 *
 * Work is split over threads (and optional shards) by the smallest column
 * of the t-set, dynamically scheduled. Gap examples are collected with
 * their lexicographic rank so that the ten examples printed are exactly the
 * ones ca_verify prints for the same thread count (ca_verify assigns column
 * set number r to thread r mod threads and prints each thread's first ten
 * in turn).
 *
 * Environment variables (test hooks, never needed in normal use): the
 * kernel is chosen by size heuristics; CA_VERIFY2_REP=planes|onehot forces
 * the general-v representation, CA_VERIFY2_CLASSES=bitset|sort how classes
 * are formed, CA_VERIFY2_ROWS=bits|list how class rows are walked, and
 * CA_VERIFY2_KERNEL=base disables the AVX2 clone. All paths give identical
 * output; the differential tests exercise each of them.
 *
 * Build: cc -O3 -pthread -o ca_verify ca_verify.c
 * On x86-64 the hot kernels are compiled twice (AVX2 and baseline) and the
 * AVX2 version is selected at run time when the CPU supports it; on other
 * architectures (e.g. Apple Silicon, NEON) the compiler's native vector
 * width is used. No -march flag is needed.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <ctype.h>
#include <pthread.h>
#include <time.h>

#define MAX_MISS_REPORT 10
#define WILDCARD -1
#define MAXT 31
#define MAXNT 64
#define CH 4                        /* words per column chunk (256 columns) */
#define PAD CH

static int N, K, T, V;
static long long VT;                /* v^t   */
static long long VT1;               /* v^(t-1) */
static int NT = 4;
static int8_t *A;                   /* N x K array, row-major */
static int W;                       /* 64-bit words per row set (N bits) */
static int Kw;                      /* 64-bit words per K columns */
static int NCH;                     /* column chunks of CH words */
static uint64_t *X;                 /* X[(c*V+u)*W + w]: rows with A[r][c]==u */
static uint64_t *PL;                /* bit planes, chunk-major (see kernels) */
static int binary_fast;             /* v==2 and no don't-cares: one plane/row */
static int bitset_classes;          /* generic kernel: classes from R[T-1] bitsets */
static int list_mode;               /* binary kernel: extract class row lists first */
static int use_onehot;              /* generic kernel: one-hot lanes instead of planes */
static int LB;                      /* one-hot lane width in bits: 8, 16, 32 or 64 */
static int CPU_;                    /* one-hot columns per 32-byte unit = 256/LB */
static int NU;                      /* one-hot units per row */
static uint8_t *OH;                 /* one-hot rows: NU*32 bytes each */
static uint64_t *R0;                /* bitset of all rows */
static uint64_t *dvalid;            /* Kw words, bit d set iff d < K */
static int shard_i = 0, shard_n = 1;
static int fail_fast = 0;
static volatile int g_stop = 0;
static volatile int g_next_unit = 0;
static int n_units;
static int rank_ok = 1;             /* binomials fit in 64 bits */
static unsigned long long *BIN;     /* BIN[n*(T+1)+j] = C(n,j), n<=K, j<=T */
static unsigned long long CKT;      /* C(K,T) */
static const char *kernel_name = "portable";

typedef struct {
    unsigned long long rank;
    long long tuple;
    int cols[MAXT];
} Example;

typedef struct {
    int tid;
    long long combos, gaps, missing;
    Example *ex; int n_ex, cap_ex;
    int res_count[MAXNT];
    int collecting;
    uint64_t *R[MAXT + 1];          /* R[j]: V^j row sets of W words */
    uint64_t *gapmask;              /* Kw words: d with a gap in this prefix */
    uint64_t *dm;                   /* Kw words: valid d > c */
    uint64_t *acc;                  /* V*PAD words (generic kernel) */
    int *rows, *tmp; int8_t *tmpu; long long *off; /* generic kernel class lists */
    uint8_t *cm;                    /* one-hot lane masks: lane d all ones iff c < d < K */
    int *pd; long long *ptuple; int np; /* gaps found in current prefix */
    int cur_cols[MAXT];
} Work;

static unsigned long long binom(int n, int j) {
    if (j < 0 || n < 0 || j > n) return 0;
    return BIN[(size_t)n * (T + 1) + j];
}

static void die(const char *msg) { fprintf(stderr, "%s\n", msg); exit(2); }

static void *xcalloc(size_t n, size_t sz) {
    void *p = calloc(n ? n : 1, sz);
    if (!p) die("alloc fail");
    return p;
}

static void *xaligned(size_t bytes) {
    void *p = NULL;
    bytes = (bytes + 63) & ~(size_t)63;
    if (posix_memalign(&p, 64, bytes ? bytes : 64)) die("alloc fail");
    memset(p, 0, bytes);
    return p;
}

/* ------------------------------------------------------------------ */
/* gap bookkeeping (cold path)                                          */
/* ------------------------------------------------------------------ */

/* record that for the current prefix, columns d in 'newbits' (word wi) first
   miss tuple index (s*V + u) where u is given per bit by umiss[]: umiss[u]
   has bit d set iff value u is missing. */
static void note_new_gaps(Work *w, int wi, uint64_t newbits, long long s,
                          const uint64_t *umiss) {
    while (newbits) {
        int b = __builtin_ctzll(newbits);
        newbits &= newbits - 1;
        int d = wi * 64 + b;
        int u = 0;
        if (umiss) { while (u < V && !((umiss[u] >> b) & 1)) u++; }
        w->pd[w->np] = d;
        w->ptuple[w->np] = s * V + u;
        w->np++;
    }
}

/* finish a prefix: fold the gaps found into counts and examples */
static void finish_prefix(Work *w, const int *cols, int c, int w0) {
    long long g = 0;
    for (int wi = w0; wi < Kw; wi++) g += __builtin_popcountll(w->gapmask[wi]);
    w->gaps += g;
    if (w->np == 0 || !w->collecting) { w->np = 0; return; }
    /* sort gaps of this prefix by d (lexicographic order of the t-sets) */
    for (int i = 1; i < w->np; i++) {
        int d = w->pd[i]; long long tp = w->ptuple[i]; int j = i - 1;
        while (j >= 0 && w->pd[j] > d) { w->pd[j+1] = w->pd[j]; w->ptuple[j+1] = w->ptuple[j]; j--; }
        w->pd[j+1] = d; w->ptuple[j+1] = tp;
    }
    unsigned long long part = 0;
    if (rank_ok) {
        part = CKT - 1;
        for (int j = 0; j <= T - 2; j++) part -= binom(K - 1 - cols[j], T - j);
    }
    for (int i = 0; i < w->np; i++) {
        int d = w->pd[i];
        unsigned long long rank = rank_ok ? part - (unsigned long long)(K - 1 - d) : 0;
        int res = rank_ok ? (int)(rank % NT) : 0;
        if (w->res_count[res] >= MAX_MISS_REPORT) continue;
        w->res_count[res]++;
        if (w->n_ex == w->cap_ex) {
            w->cap_ex = w->cap_ex ? 2 * w->cap_ex : 64;
            w->ex = realloc(w->ex, (size_t)w->cap_ex * sizeof(Example));
            if (!w->ex) die("alloc fail");
        }
        Example *e = &w->ex[w->n_ex++];
        e->rank = rank; e->tuple = w->ptuple[i];
        for (int j = 0; j <= T - 2; j++) e->cols[j] = cols[j];
        e->cols[T - 1] = d;
        (void)c;
    }
    int still = 0;
    for (int r = 0; r < NT; r++) if (w->res_count[r] < MAX_MISS_REPORT) still = 1;
    if (!rank_ok && w->res_count[0] >= MAX_MISS_REPORT) still = 0;
    w->collecting = still;
    w->np = 0;
}

/* an empty class: every value is missing for every candidate d */
static void empty_class(Work *w, long long s, int w0) {
    for (int wi = w0; wi < Kw; wi++) {
        uint64_t unc = w->dm[wi];
        if (!unc) continue;
        w->missing += (long long)V * __builtin_popcountll(unc);
        uint64_t nw = unc & ~w->gapmask[wi];
        w->gapmask[wi] |= unc;
        if (nw && w->collecting) note_new_gaps(w, wi, nw, s, NULL);
    }
}

/* slow path shared by both kernels: umiss[u*PAD + x] for words wb..wb+ch-1 */
static void slow_path(Work *w, long long s, int wb, int ch, const uint64_t *umiss) {
    uint64_t um[128];
    for (int x = 0; x < ch; x++) {
        int wi = wb + x;
        uint64_t any = 0;
        for (int u = 0; u < V; u++) {
            uint64_t mu = umiss[(size_t)u * PAD + x] & w->dm[wi];
            um[u] = mu;
            any |= mu;
            w->missing += __builtin_popcountll(mu);
        }
        if (!any) continue;
        uint64_t nw = any & ~w->gapmask[wi];
        w->gapmask[wi] |= any;
        if (nw && w->collecting) note_new_gaps(w, wi, nw, s, um);
    }
}

/* one-hot slow path: acc holds one lane (LB bits) per column of unit `unit`;
   lane bits are the values seen in column d within class s */
static void onehot_slow(Work *w, long long s, int unit, const uint8_t *acc, int c) {
    uint64_t full = V == 64 ? ~0ULL : (1ULL << V) - 1;
    for (int j = 0; j < CPU_; j++) {
        int d = unit * CPU_ + j;
        if (d <= c || d >= K) continue;
        uint64_t lane;
        switch (LB) {
        case 8:  lane = acc[j]; break;
        case 16: { uint16_t x; memcpy(&x, acc + 2 * j, 2); lane = x; break; }
        case 32: { uint32_t x; memcpy(&x, acc + 4 * j, 4); lane = x; break; }
        default: memcpy(&lane, acc + 8 * j, 8); break;
        }
        uint64_t miss = ~lane & full;
        if (!miss) continue;
        w->missing += __builtin_popcountll(miss);
        uint64_t bit = 1ULL << (d & 63);
        if (!(w->gapmask[d >> 6] & bit)) {
            w->gapmask[d >> 6] |= bit;
            if (w->collecting) {
                w->pd[w->np] = d;
                w->ptuple[w->np] = s * V + __builtin_ctzll(miss);
                w->np++;
            }
        }
    }
}

/* ------------------------------------------------------------------ */
/* hot kernels                                                          */
/* ------------------------------------------------------------------ */

/* The kernels below are instantiated twice on x86-64 (baseline SSE2 and
   AVX2) via KATTR; the AVX2 copy is chosen at run time. They are written
   with GCC/clang vector extensions (4 x 64-bit lanes = 256 bits): one AVX2
   register, two SSE2 or NEON registers.

   Plane layout is chunk-major: the K columns are cut into NCH chunks of 256
   (CH = 4 words) and chunk ci of row r (for value u in the generic case)
   is the 32-byte block PL[((u*NCH + ci)*N + r)*CH .. +CH). So within a
   chunk, consecutive rows are 32 bytes apart: the data a prefix touches
   is compact (N*32 bytes per chunk) and row addresses need no multiply. */

typedef uint64_t v4u __attribute__((vector_size(32)));

#define ldv(p) ({ v4u x_; memcpy(&x_, (p), 32); x_; })
#define stv(p, x) do { v4u y_ = (x); memcpy((p), &y_, 32); } while (0)
#define hor(x) ({ v4u z_ = (x); z_[0] | z_[1] | z_[2] | z_[3]; })

/* Write the row indices of class bitset bs (W words) to L; return the count.
   Each word is unpacked with eight unconditional steps (ctz of 0 is forced to
   63 by setting the top bit, the surplus entries are overwritten), so the
   loop-exit branch mispredicts only for words holding more than eight rows
   of the class. Used when classes are sparse (few rows per bitset word),
   where the plain ctz loop mispredicts once per word. L needs W*8 + N slack. */
static inline int extract_rows(const uint64_t *bs, int *L) {
    int m = 0;
    for (int ww = 0; ww < W; ww++) {
        uint64_t b = bs[ww];
        int n = __builtin_popcountll(b), base = ww * 64;
        for (int j = 0; j < 8; j++) {
            L[m + j] = base + __builtin_ctzll(b | 0x8000000000000000ULL);
            b &= b - 1;
        }
        m += n < 8 ? n : 8;
        if (n > 8) { while (b) { L[m++] = base + __builtin_ctzll(b); b &= b - 1; } }
    }
    return m;
}

/* walk the rows of class bitset bs (W words); the body sees `const uint64_t *p`,
   the address of the row's block in chunk base `pb`. In list mode the rows
   were extracted to w->rows (m entries) beforehand. */
#define FOR_ROWS(bs, pb, ...)                                                   \
    if (list_mode) {                                                            \
        const int *L_ = w->rows;                                                \
        for (int i_ = 0; i_ < m; i_++) {                                        \
            const uint64_t *p = (pb) + (size_t)L_[i_] * CH;                     \
            __VA_ARGS__                                                         \
        }                                                                       \
    } else                                                                      \
    for (int ww_ = 0; ww_ < W; ww_++) {                                         \
        uint64_t b_ = (bs)[ww_];                                                \
        const uint64_t *pw_ = (pb) + (size_t)ww_ * 64 * CH;                     \
        while (b_) {                                                            \
            const uint64_t *p = pw_ + (size_t)__builtin_ctzll(b_) * CH;         \
            b_ &= b_ - 1;                                                       \
            __VA_ARGS__                                                         \
        }                                                                       \
    }

#define BIN_REPORT(ci, a, o)                                                    \
    do {                                                                        \
        uint64_t um_[2 * CH];                                                   \
        stv(um_, (a)); stv(um_ + CH, ~(o));                                     \
        slow_path(w, s, (ci) * CH, Kw - (ci) * CH < CH ? Kw - (ci) * CH : CH, um_); \
    } while (0)

/* One-hot representation (general v <= 64, any k, don't-cares allowed): the
   entry (r, d) is the lane value 1 << A[r][d] (0 for a don't-care) in a lane
   of LB bits; 32 bytes hold CPU_ = 256/LB consecutive columns. The values
   seen in column d within a class are the OR of the rows' lanes, and column
   d is covered iff that OR is the full mask of v bits. Unlike bit planes,
   which need v passes over 256-column chunks, this needs one pass over
   (k - c)/CPU_ units, so it wins when v is large or k is small. */

#define DEFINE_ONEHOT(SUFFIX, KATTR, LT, VT_)                                   \
static KATTR void onehot_class_##SUFFIX##_##LT(Work *w, long long s,            \
        const int *L, int ml, int c, int u0, uint64_t fullbits) {               \
    VT_ full;                                                                   \
    for (unsigned j = 0; j < sizeof(VT_) / sizeof(full[0]); j++)                \
        full[j] = (__typeof__(full[0]))fullbits;                                \
    const uint8_t *O = OH;                                                      \
    const size_t rs = (size_t)NU * 32;                                          \
    const uint8_t *cm = w->cm;                                                  \
    int un = u0;                                                                \
    for (; un + 3 < NU; un += 4) {                                              \
        VT_ a0 = full ^ full, a1 = a0, a2 = a0, a3 = a0;                        \
        const uint8_t *pb = O + (size_t)un * 32;                                \
        for (int i = 0; i < ml; i++) {                                          \
            const uint8_t *p = pb + (size_t)L[i] * rs;                          \
            VT_ x0, x1, x2, x3;                                                 \
            memcpy(&x0, p, 32); memcpy(&x1, p + 32, 32);                        \
            memcpy(&x2, p + 64, 32); memcpy(&x3, p + 96, 32);                   \
            a0 |= x0; a1 |= x1; a2 |= x2; a3 |= x3;                             \
        }                                                                       \
        VT_ m0, m1, m2, m3;                                                     \
        memcpy(&m0, cm + (size_t)un * 32, 32); memcpy(&m1, cm + (size_t)(un + 1) * 32, 32); \
        memcpy(&m2, cm + (size_t)(un + 2) * 32, 32); memcpy(&m3, cm + (size_t)(un + 3) * 32, 32); \
        VT_ bad = ((a0 ^ full) & m0) | ((a1 ^ full) & m1) | ((a2 ^ full) & m2) | ((a3 ^ full) & m3); \
        if (hor((v4u)bad)) {                                                    \
            uint8_t buf[32];                                                    \
            memcpy(buf, &a0, 32); onehot_slow(w, s, un, buf, c);                \
            memcpy(buf, &a1, 32); onehot_slow(w, s, un + 1, buf, c);            \
            memcpy(buf, &a2, 32); onehot_slow(w, s, un + 2, buf, c);            \
            memcpy(buf, &a3, 32); onehot_slow(w, s, un + 3, buf, c);            \
        }                                                                       \
    }                                                                           \
    for (; un < NU; un++) {                                                     \
        VT_ a0 = full ^ full, a1 = a0;                                          \
        const uint8_t *pb = O + (size_t)un * 32;                                \
        int i = 0;                                                              \
        for (; i + 1 < ml; i += 2) {                                            \
            VT_ x0, x1;                                                         \
            memcpy(&x0, pb + (size_t)L[i] * rs, 32);                            \
            memcpy(&x1, pb + (size_t)L[i + 1] * rs, 32);                        \
            a0 |= x0; a1 |= x1;                                                 \
        }                                                                       \
        if (i < ml) { VT_ x0; memcpy(&x0, pb + (size_t)L[i] * rs, 32); a0 |= x0; } \
        a0 |= a1;                                                               \
        VT_ m0; memcpy(&m0, cm + (size_t)un * 32, 32);                          \
        VT_ bad = (a0 ^ full) & m0;                                             \
        if (hor((v4u)bad)) { uint8_t buf[32]; memcpy(buf, &a0, 32); onehot_slow(w, s, un, buf, c); } \
    }                                                                           \
}

typedef uint8_t  v32u8  __attribute__((vector_size(32)));
typedef uint16_t v16u16 __attribute__((vector_size(32)));
typedef uint32_t v8u32  __attribute__((vector_size(32)));

/* run one class through the representation chosen at start-up */
#define CLASS_DISPATCH(SUFFIX, w, s, L, ml, c, c0)                              \
    do {                                                                        \
        if (!use_onehot) generic_class_##SUFFIX(w, s, L, ml, c0);               \
        else {                                                                  \
            int u0_ = (c + 1) / CPU_;                                           \
            uint64_t f_ = LB >= 64 && V == 64 ? ~0ULL : (1ULL << V) - 1;        \
            switch (LB) {                                                       \
            case 8:  onehot_class_##SUFFIX##_v32u8(w, s, L, ml, c, u0_, f_); break; \
            case 16: onehot_class_##SUFFIX##_v16u16(w, s, L, ml, c, u0_, f_); break; \
            case 32: onehot_class_##SUFFIX##_v8u32(w, s, L, ml, c, u0_, f_); break; \
            default: onehot_class_##SUFFIX##_v4u(w, s, L, ml, c, u0_, f_); break; \
            }                                                                   \
        }                                                                       \
    } while (0)

#define DEFINE_KERNELS(SUFFIX, KATTR)                                           \
/* binary, no don't-cares: one plane per row, OR and AND accumulators */        \
static KATTR void kernel_binary_##SUFFIX(Work *w, const int *cols, int c) {     \
    const int c0 = (c + 1) >> 8;                 /* first chunk with d > c */   \
    const uint64_t *Rl = w->R[T - 1];                                           \
    const uint64_t *P = PL;                                                     \
    const uint64_t *dm = w->dm;                                                 \
    const size_t cs = (size_t)N * CH;            /* words per chunk block */    \
    for (long long s = 0; s < VT1; s++) {                                       \
        const uint64_t *bs = Rl + (size_t)s * W;                                \
        uint64_t anyrow = 0;                                                    \
        for (int ww = 0; ww < W; ww++) anyrow |= bs[ww];                        \
        if (!anyrow) { empty_class(w, s, c0 * CH); continue; }                  \
        int m = list_mode ? extract_rows(bs, w->rows) : 0;                      \
        int ci = c0;                                                            \
        for (; ci + 3 < NCH; ci += 4) {          /* four chunks at a time */    \
            v4u o0 = {0, 0, 0, 0}, o1 = o0, o2 = o0, o3 = o0;                   \
            v4u a0 = ~o0, a1 = a0, a2 = a0, a3 = a0;                            \
            const uint64_t *pb = P + (size_t)ci * cs;                           \
            FOR_ROWS(bs, pb, {                                                  \
                v4u x0 = ldv(p), x1 = ldv(p + cs), x2 = ldv(p + 2 * cs), x3 = ldv(p + 3 * cs); \
                o0 |= x0; a0 &= x0; o1 |= x1; a1 &= x1;                         \
                o2 |= x2; a2 &= x2; o3 |= x3; a3 &= x3;                         \
            })                                                                  \
            v4u u0 = (a0 | ~o0) & ldv(dm + ci * CH), u1 = (a1 | ~o1) & ldv(dm + (ci + 1) * CH); \
            v4u u2 = (a2 | ~o2) & ldv(dm + (ci + 2) * CH), u3 = (a3 | ~o3) & ldv(dm + (ci + 3) * CH); \
            if (hor(u0 | u1 | u2 | u3)) {                                       \
                BIN_REPORT(ci, a0, o0); BIN_REPORT(ci + 1, a1, o1);             \
                BIN_REPORT(ci + 2, a2, o2); BIN_REPORT(ci + 3, a3, o3);         \
            }                                                                   \
        }                                                                       \
        for (; ci + 1 < NCH; ci += 2) {          /* two chunks at a time */     \
            v4u o0 = {0, 0, 0, 0}, o1 = o0, a0 = ~o0, a1 = a0;                  \
            const uint64_t *pb = P + (size_t)ci * cs;                           \
            FOR_ROWS(bs, pb, {                                                  \
                v4u x0 = ldv(p), x1 = ldv(p + cs);                              \
                o0 |= x0; a0 &= x0; o1 |= x1; a1 &= x1;                         \
            })                                                                  \
            v4u u0 = (a0 | ~o0) & ldv(dm + ci * CH), u1 = (a1 | ~o1) & ldv(dm + (ci + 1) * CH); \
            if (hor(u0 | u1)) { BIN_REPORT(ci, a0, o0); BIN_REPORT(ci + 1, a1, o1); } \
        }                                                                       \
        if (ci < NCH) {                                                         \
            v4u o0 = {0, 0, 0, 0}, a0 = ~o0;                                    \
            const uint64_t *pb = P + (size_t)ci * cs;                           \
            FOR_ROWS(bs, pb, { v4u x0 = ldv(p); o0 |= x0; a0 &= x0; })          \
            v4u u0 = (a0 | ~o0) & ldv(dm + ci * CH);                            \
            if (hor(u0)) BIN_REPORT(ci, a0, o0);                                \
        }                                                                       \
    }                                                                           \
    (void)cols;                                                                 \
}                                                                               \
/* general v (or binary with don't-cares): v planes per row, OR accumulators.  \
   One class (row list L of length ml) of prefix tuple s. */                    \
static KATTR void generic_class_##SUFFIX(Work *w, long long s, const int *L,    \
                                         int ml, int c0) {                      \
    uint64_t *acc = w->acc;                                                     \
    const uint64_t *P = PL;                                                     \
    const uint64_t *dm = w->dm;                                                 \
    const size_t cs = (size_t)N * CH;                                           \
    for (int ci = c0; ci < NCH; ci++) {                                         \
        v4u cov = {0, 0, 0, 0}; cov = ~cov;                                     \
        for (int u = 0; u < V; u++) {                                           \
            v4u o = {0, 0, 0, 0}, o2 = o;                                       \
            const uint64_t *pb = P + ((size_t)u * NCH + ci) * cs;               \
            int i = 0;                                                          \
            for (; i + 1 < ml; i += 2) {                                        \
                o |= ldv(pb + (size_t)L[i] * CH);                               \
                o2 |= ldv(pb + (size_t)L[i + 1] * CH);                          \
            }                                                                   \
            if (i < ml) o |= ldv(pb + (size_t)L[i] * CH);                       \
            o |= o2;                                                            \
            cov &= o;                                                           \
            stv(acc + (size_t)u * CH, ~o);                                      \
        }                                                                       \
        v4u unc = ~cov & ldv(dm + ci * CH);                                     \
        if (hor(unc)) slow_path(w, s, ci * CH, Kw - ci * CH < CH ? Kw - ci * CH : CH, acc); \
    }                                                                           \
}                                                                               \
/* Class lists come either from the class bitsets R[T-1] (cheap when         \
   v^(t-1) is small) or from a counting sort of each parent class (bitset in \
   R[T-2]) by the value in column c (cheaper when v^(t-1)*W is large). */       \
static KATTR void kernel_generic_##SUFFIX(Work *w, const int *cols, int c) {    \
    const int c0 = (c + 1) >> 8;                                                \
    int *rows = w->rows, *tmp = w->tmp;                                         \
    int8_t *tmpu = w->tmpu;                                                     \
    long long *off = w->off;                                                    \
    if (bitset_classes) {                                                       \
        const uint64_t *Rl = w->R[T - 1];                                       \
        for (long long s = 0; s < VT1; s++) {                                   \
            const uint64_t *bs = Rl + (size_t)s * W;                            \
            int m = extract_rows(bs, rows);                                     \
            if (m == 0) empty_class(w, s, c0 * CH);                             \
            else CLASS_DISPATCH(SUFFIX, w, s, rows, m, c, c0);                  \
        }                                                                       \
        (void)cols; return;                                                     \
    }                                                                           \
    long long nparent = T >= 2 ? VT1 / V : 1;                                   \
    for (long long sp = 0; sp < nparent; sp++) {                                \
        const uint64_t *bs = T >= 2 ? w->R[T - 2] + (size_t)sp * W : R0;        \
        int m = 0;                                                              \
        for (int ww = 0; ww < W; ww++) {                                        \
            uint64_t b = bs[ww];                                                \
            while (b) {                                                         \
                int r = ww * 64 + __builtin_ctzll(b); b &= b - 1;               \
                int8_t u = T >= 2 ? A[(size_t)r * K + c] : 0;                   \
                if (u != WILDCARD) { tmp[m] = r; tmpu[m] = u; m++; }            \
            }                                                                   \
        }                                                                       \
        for (int u = 0; u <= V; u++) off[u] = 0;                                \
        for (int i = 0; i < m; i++) off[tmpu[i] + 1]++;                         \
        for (int u = 0; u < V; u++) off[u + 1] += off[u];                       \
        for (int i = 0; i < m; i++) rows[off[tmpu[i]]++] = tmp[i];              \
        for (int u = V; u > 0; u--) off[u] = off[u - 1];                        \
        off[0] = 0;                                                             \
        for (int uc = 0; uc < (T >= 2 ? V : 1); uc++) {                         \
            long long s = sp * V + uc;                                          \
            int ml = (int)(off[uc + 1] - off[uc]);                              \
            if (ml == 0) empty_class(w, s, c0 * CH);                            \
            else CLASS_DISPATCH(SUFFIX, w, s, rows + off[uc], ml, c, c0);       \
        }                                                                       \
        if (T == 1) break;                                                      \
    }                                                                           \
    (void)cols;                                                                 \
}

DEFINE_ONEHOT(base, , v32u8, v32u8)
DEFINE_ONEHOT(base, , v16u16, v16u16)
DEFINE_ONEHOT(base, , v8u32, v8u32)
DEFINE_ONEHOT(base, , v4u, v4u)
DEFINE_KERNELS(base, )
#if defined(__x86_64__) && (defined(__GNUC__) || defined(__clang__)) && !defined(NO_AVX2_CLONE)
DEFINE_ONEHOT(avx2, __attribute__((target("avx2,bmi,bmi2,popcnt"))), v32u8, v32u8)
DEFINE_ONEHOT(avx2, __attribute__((target("avx2,bmi,bmi2,popcnt"))), v16u16, v16u16)
DEFINE_ONEHOT(avx2, __attribute__((target("avx2,bmi,bmi2,popcnt"))), v8u32, v8u32)
DEFINE_ONEHOT(avx2, __attribute__((target("avx2,bmi,bmi2,popcnt"))), v4u, v4u)
DEFINE_KERNELS(avx2, __attribute__((target("avx2,bmi,bmi2,popcnt"))))
#define HAVE_AVX2_CLONE 1
#endif

typedef void (*kernel_fn)(Work *, const int *, int);
static kernel_fn kernel_binary = kernel_binary_base;
static kernel_fn kernel_generic = kernel_generic_base;

static void select_kernels(void) {
#ifdef HAVE_AVX2_CLONE
    __builtin_cpu_init();
    const char *env = getenv("CA_VERIFY2_KERNEL");   /* test hook: "base" disables AVX2 */
    if (env && !strcmp(env, "base")) return;
    if (__builtin_cpu_supports("avx2") && __builtin_cpu_supports("bmi2")) {
        kernel_binary = kernel_binary_avx2;
        kernel_generic = kernel_generic_avx2;
        kernel_name = "avx2";
    }
#endif
}

/* ------------------------------------------------------------------ */
/* enumeration of (t-1)-prefixes                                        */
/* ------------------------------------------------------------------ */

/* process prefix cols[0..T-2] whose largest column is c (c = -1 when t = 1) */
static void do_prefix(Work *w, const int *cols, int c) {
    if (g_stop) return;
    int w0 = (c + 1) >> 6;
    int wa = ((c + 1) >> 8) * CH;               /* chunk-aligned start */
    for (int wi = wa; wi < NCH * CH; wi++) {
        uint64_t m = wi < w0 ? 0 : dvalid[wi];
        if (wi == w0 && ((c + 1) & 63)) m &= ~0ULL << ((c + 1) & 63);
        w->dm[wi] = m;
        w->gapmask[wi] = 0;
    }
    if (use_onehot) {
        /* lane masks for units from the one holding column c+1 */
        int lb = LB / 8;
        int d0 = (c + 1) / CPU_ * CPU_;
        for (int d = d0; d < NU * CPU_; d++) {
            uint8_t val = (d > c && d < K) ? 0xff : 0;
            memset(w->cm + (size_t)d * lb, val, lb);
        }
    }
    w->combos += K - 1 - c;
    w->np = 0;
    if (binary_fast) kernel_binary(w, cols, c); else kernel_generic(w, cols, c);
    long long before = w->gaps;
    finish_prefix(w, cols, c, w0);
    if (fail_fast && w->gaps > before) g_stop = 1;
}

/* cols[0..j-1] chosen; R[j-1] holds the classes of cols[0..j-2]; build R[j]
   by splitting on cols[j-1], then either run the kernel (j == T-1) or
   extend the prefix. */
static void level(Work *w, int j, int *cols) {
    int c = cols[j - 1];
    long long nprev = 1;
    for (int i = 0; i < j - 1; i++) nprev *= V;
    const uint64_t *Rp = w->R[j - 1];
    uint64_t *Rn = w->R[j];
    if (j == T - 1 && !binary_fast && !bitset_classes) { do_prefix(w, cols, c); return; } /* generic kernel splits on c itself */
    for (long long sp = 0; sp < nprev; sp++) {
        const uint64_t *src = Rp + (size_t)sp * W;
        for (int u = 0; u < V; u++) {
            const uint64_t *xc = X + ((size_t)c * V + u) * W;
            uint64_t *dst = Rn + ((size_t)sp * V + u) * W;
            for (int ww = 0; ww < W; ww++) dst[ww] = src[ww] & xc[ww];
        }
    }
    if (j == T - 1) { do_prefix(w, cols, c); return; }
    for (int cn = c + 1; cn <= K - 1 - (T - 1 - j); cn++) {
        if (g_stop) return;
        cols[j] = cn;
        level(w, j + 1, cols);
    }
}

static void *worker(void *arg) {
    Work *w = (Work *)arg;
    int cols[MAXT];
    for (;;) {
        if (g_stop) break;
        int i = __sync_fetch_and_add(&g_next_unit, 1);
        if (i >= n_units) break;
        if (T == 1) { do_prefix(w, cols, -1); continue; }
        int a = shard_i + i * shard_n;
        cols[0] = a;
        level(w, 1, cols);
    }
    return NULL;
}

static int cmp_example(const void *pa, const void *pb) {
    const Example *a = pa, *b = pb;
    if (a->rank != b->rank) return a->rank < b->rank ? -1 : 1;
    /* ranks are unique unless rank_ok is 0; then keep lexicographic order */
    for (int j = 0; j < T; j++) if (a->cols[j] != b->cols[j]) return a->cols[j] < b->cols[j] ? -1 : 1;
    return 0;
}

/* ------------------------------------------------------------------ */
/* main                                                                 */
/* ------------------------------------------------------------------ */

int main(int argc, char **argv) {
    if (argc < 4) {
        fprintf(stderr, "usage: %s FILE t v [threads] [SHARD/NSHARDS] [--fail-fast]\n", argv[0]);
        return 2;
    }
    const char *path = argv[1];
    T = atoi(argv[2]); V = atoi(argv[3]);
    int saw_threads = 0;
    for (int i = 4; i < argc; i++) {
        if (!strcmp(argv[i], "--fail-fast")) { fail_fast = 1; continue; }
        if (strchr(argv[i], '/')) {
            if (sscanf(argv[i], "%d/%d", &shard_i, &shard_n) != 2 || shard_n < 1 ||
                shard_i < 0 || shard_i >= shard_n) {
                fprintf(stderr, "bad shard spec %s (want SHARD/NSHARDS with 0 <= SHARD < NSHARDS)\n", argv[i]);
                return 2;
            }
            continue;
        }
        if (!saw_threads) { NT = atoi(argv[i]); saw_threads = 1; continue; }
        fprintf(stderr, "unexpected argument %s\n", argv[i]);
        return 2;
    }
    if (T < 1 || T > MAXT || V < 2 || NT < 1 || NT > MAXNT) {
        fprintf(stderr, "bad parameters\n"); return 2;
    }
    VT = 1;
    for (int i = 0; i < T; i++) {
        VT *= V;
        if (VT > (1LL << 40)) { fprintf(stderr, "v^t too large\n"); return 2; }
    }
    VT1 = VT / V;
    if (VT1 > (1LL << 26)) {
        /* the class tables hold v^(t-1) row sets per thread; no array of a size that can be
           stored reaches this, since a covering array has at least v^t rows */
        fprintf(stderr, "v^(t-1) = %lld is above 2^26, out of range for ca_verify "
                "(a covering array of strength t over v symbols has at least v^t = %lld rows)\n",
                VT1, VT);
        return 2;
    }

    /* ---- read the array (same tokenizer as ca_verify) ---- */
    FILE *f = fopen(path, "r");
    if (!f) { fprintf(stderr, "cannot open %s\n", path); return 2; }
    size_t cap = 1 << 20;
    int8_t *buf = malloc(cap);
    if (!buf) die("alloc fail");
    size_t n_entries = 0;
    int cols = -1, cur_cols = 0;
    int minv = 127, maxv = -2;
    char *line = NULL; size_t lcap = 0; ssize_t llen;
    int wild = 0;
    while ((llen = getline(&line, &lcap, f)) != -1) {
        char *p = line;
        cur_cols = 0;
        int any = 0;
        while (*p) {
            while (*p && (*p == ' ' || *p == '\t' || *p == ',' || *p == '\r' || *p == '\n')) p++;
            if (!*p) break;
            long val;
            if (*p == '-' && !isdigit((unsigned char)p[1])) { val = WILDCARD; p++; }
            else if ((*p == '*') || (*p == 'x') || (*p == 'X')) { val = WILDCARD; p++; }
            else if ((p[0] == 'N' || p[0] == 'n') && (p[1] == 'A' || p[1] == 'a')) { val = WILDCARD; p += 2; }
            else if (isdigit((unsigned char)*p) || (*p == '-' && isdigit((unsigned char)p[1]))) {
                val = strtol(p, &p, 10);
            } else { p++; continue; }
            if (val > 127 || val < -128) {
                fprintf(stderr, "symbol %ld out of range for v=%d\n", val, V);
                return 2;
            }
            if (n_entries >= cap) { cap <<= 1; buf = realloc(buf, cap); if (!buf) die("alloc fail"); }
            buf[n_entries++] = (int8_t)val;
            if (val != WILDCARD) { if (val < minv) minv = (int)val; if (val > maxv) maxv = (int)val; }
            else wild = 1;
            cur_cols++; any = 1;
        }
        if (!any) continue;
        if (cols == -1) cols = cur_cols;
        else if (cur_cols != cols) {
            fprintf(stderr, "ragged row (got %d entries, expected %d)\n", cur_cols, cols);
            return 2;
        }
    }
    free(line);
    fclose(f);
    if (cols < T) { fprintf(stderr, "fewer columns than t\n"); return 2; }
    K = cols; N = (int)(n_entries / cols);

    /* auto-shift 1-based symbols */
    int shift = 0;
    if (minv == 1 && maxv == V) shift = 1;
    else if (minv == 0 && maxv == V - 1) shift = 0;
    else if (maxv - shift >= V || minv < WILDCARD) {
        fprintf(stderr, "symbols out of range for v=%d (saw %d..%d)\n", V, minv, maxv);
        return 2;
    }
    A = buf;
    if (shift)
        for (size_t i = 0; i < n_entries; i++)
            if (A[i] != WILDCARD) A[i] -= 1;

    fprintf(stderr, "read %d rows x %d columns over v=%d (t=%d, %d threads)\n",
            N, K, V, T, NT);
    if (shard_n > 1)
        fprintf(stderr, "shard %d of %d: column sets whose smallest column is %d mod %d\n",
                shard_i, shard_n, shard_i, shard_n);

    struct timespec ts0, ts1;
    clock_gettime(CLOCK_MONOTONIC, &ts0);
    select_kernels();

    /* ---- build bitsets and planes ---- */
    W = (N + 63) / 64;
    Kw = (K + 63) / 64;
    NCH = (Kw + CH - 1) / CH;
    binary_fast = (V == 2 && !wild);
    /* class bitsets cost v^(t-1)*W word ANDs per prefix, counting sort about
       8N scalar operations with strided loads; pick the cheaper */
    const char *env;
    bitset_classes = (VT1 * W <= 8LL * N);
    /* binary kernel: walk class bitsets directly when classes are dense
       (about 7 or more rows per word, as for t=4 with N around 200), extract
       row lists first when they are sparse (loop exits mispredict per word) */
    list_mode = ((double)N / ((double)VT1 * W) < 4.0);
    env = getenv("CA_VERIFY2_ROWS");                      /* test hook: bits|list */
    if (env && !strcmp(env, "bits")) list_mode = 0;
    else if (env && !strcmp(env, "list")) list_mode = 1;
    /* representation for the general kernel: bit planes cost about
       v * max(1, (k/t)/256) vector ops per row visit, one-hot lanes about
       (k/t) * LB/256 with LB the lane width; k/t estimates the number of
       candidate columns d > c */
    use_onehot = 0;
    if (!binary_fast && V <= 64) {
        LB = V <= 8 ? 8 : V <= 16 ? 16 : V <= 32 ? 32 : 64;
        double cand = (double)K / T;
        double cost_planes = V * (cand / 256.0 > 1 ? cand / 256.0 : 1);
        double cost_onehot = cand * LB / 256.0;
        if (cost_onehot < cost_planes) use_onehot = 1;
    }
    /* test hooks: force a representation or class-building method */
    env = getenv("CA_VERIFY2_REP");
    if (env && !strcmp(env, "planes")) { use_onehot = 0; binary_fast = 0; }
    else if (env && !strcmp(env, "onehot") && V <= 64) {
        use_onehot = 1; binary_fast = 0;
        LB = V <= 8 ? 8 : V <= 16 ? 16 : V <= 32 ? 32 : 64;
    }
    env = getenv("CA_VERIFY2_CLASSES");
    if (env && !strcmp(env, "bitset")) bitset_classes = 1;
    else if (env && !strcmp(env, "sort")) bitset_classes = 0;
    if (use_onehot) {
        CPU_ = 256 / LB;
        NU = (K + CPU_ - 1) / CPU_;
        OH = xaligned((size_t)N * NU * 32);
    }
    size_t nplanes = binary_fast ? 1 : (size_t)V;
    X = xaligned((size_t)K * V * W * sizeof(uint64_t));
    PL = xaligned(use_onehot ? 64 : nplanes * NCH * (size_t)N * CH * sizeof(uint64_t));
    R0 = xaligned((size_t)W * sizeof(uint64_t));
    dvalid = xaligned((size_t)(NCH * CH) * sizeof(uint64_t));
    for (int r = 0; r < N; r++) {
        const int8_t *row = A + (size_t)r * K;
        R0[r >> 6] |= 1ULL << (r & 63);
        for (int c = 0; c < K; c++) {
            int8_t s = row[c];
            if (s == WILDCARD) continue;
            X[((size_t)c * V + s) * W + (r >> 6)] |= 1ULL << (r & 63);
            size_t ci = (size_t)c >> 8;
            size_t word = ((size_t)c >> 6) & (CH - 1);
            if (use_onehot) {
                uint8_t *lane = OH + (size_t)r * NU * 32 + (size_t)c * (LB / 8);
                switch (LB) {
                case 8:  lane[0] = (uint8_t)(1u << s); break;
                case 16: { uint16_t x = (uint16_t)(1u << s); memcpy(lane, &x, 2); break; }
                case 32: { uint32_t x = 1u << s; memcpy(lane, &x, 4); break; }
                default: { uint64_t x = 1ULL << s; memcpy(lane, &x, 8); break; }
                }
            } else if (binary_fast) {
                if (s) PL[(ci * N + r) * CH + word] |= 1ULL << (c & 63);
            } else {
                PL[(((size_t)s * NCH + ci) * N + r) * CH + word] |= 1ULL << (c & 63);
            }
        }
    }
    for (int d = 0; d < K; d++) dvalid[d >> 6] |= 1ULL << (d & 63);

    /* binomials for ranks (as ca_verify numbers the column sets) */
    BIN = xcalloc((size_t)(K + 1) * (T + 1), sizeof(unsigned long long));
    for (int n = 0; n <= K; n++) {
        BIN[(size_t)n * (T + 1) + 0] = 1;
        for (int j = 1; j <= T && j <= n; j++) {
            unsigned long long a = BIN[(size_t)(n - 1) * (T + 1) + j - 1];
            unsigned long long b = j <= n - 1 ? BIN[(size_t)(n - 1) * (T + 1) + j] : 0;
            unsigned long long s;
            if (__builtin_add_overflow(a, b, &s)) { rank_ok = 0; s = ~0ULL; }
            BIN[(size_t)n * (T + 1) + j] = s;
        }
    }
    CKT = binom(K, T);
    if (!rank_ok) fprintf(stderr, "note: C(k,t) exceeds 64 bits; examples are listed in lexicographic order\n");

    /* ---- work units: smallest column a, 0 <= a <= K-T, in this shard ---- */
    if (T == 1) n_units = (shard_i == 0) ? 1 : 0;
    else {
        n_units = 0;
        for (int a = shard_i; a <= K - T; a += shard_n) n_units++;
    }

    /* ---- threads ---- */
    pthread_t th[MAXNT];
    Work *w = xcalloc(NT, sizeof(Work));
    for (int i = 0; i < NT; i++) {
        w[i].tid = i;
        w[i].collecting = 1;
        long long vj = 1;
        for (int j = 0; j <= T - 1; j++) {
            if (j == T - 1 && j > 0 && !binary_fast && !bitset_classes) break;   /* generic kernel works from R[T-2] */
            w[i].R[j] = xaligned((size_t)vj * W * sizeof(uint64_t));
            vj *= V;
        }
        memcpy(w[i].R[0], R0, (size_t)W * sizeof(uint64_t));
        w[i].gapmask = xcalloc((size_t)NCH * CH, sizeof(uint64_t));
        w[i].dm = xcalloc((size_t)NCH * CH, sizeof(uint64_t));
        w[i].acc = xaligned((size_t)V * PAD * sizeof(uint64_t));
        w[i].rows = xcalloc((size_t)N + 8 * W + 8, sizeof(int));
        w[i].tmp = xcalloc(N + 1, sizeof(int));
        w[i].tmpu = xcalloc(N + 1, sizeof(int8_t));
        w[i].off = xcalloc(V + 2, sizeof(long long));
        if (use_onehot) w[i].cm = xaligned((size_t)NU * 32);
        w[i].pd = xcalloc(K, sizeof(int));
        w[i].ptuple = xcalloc(K, sizeof(long long));
    }
    for (int i = 0; i < NT; i++) pthread_create(&th[i], NULL, worker, &w[i]);
    for (int i = 0; i < NT; i++) pthread_join(th[i], NULL);

    long long combos = 0, gaps = 0, mtup = 0;
    int n_all = 0;
    for (int i = 0; i < NT; i++) {
        combos += w[i].combos; gaps += w[i].gaps; mtup += w[i].missing;
        n_all += w[i].n_ex;
    }
    clock_gettime(CLOCK_MONOTONIC, &ts1);
    double secs = (ts1.tv_sec - ts0.tv_sec) + 1e-9 * (ts1.tv_nsec - ts0.tv_nsec);
    fprintf(stderr, "checked %lld column sets in %.2f s (%s, %s%s)\n", combos, secs,
            kernel_name, binary_fast ? "binary planes" : use_onehot ? "one-hot lanes" : "value planes",
            g_stop ? ", stopped early" : "");

    char shard_tag[64] = "";
    if (shard_n > 1) snprintf(shard_tag, sizeof shard_tag, " (shard %d/%d)", shard_i, shard_n);

    if (gaps == 0) {
        printf("VERIFIED%s: CA(N=%d; t=%d, k=%d, v=%d) - all %lld column sets fully cover all %lld tuples\n",
               shard_tag, N, T, K, V, combos, VT);
        return 0;
    }
    printf("NOT A COVERING ARRAY%s: %lld of %lld column sets have gaps (%lld missing tuples total)\n",
           shard_tag, gaps, combos, mtup);

    /* merge examples: sort by rank, then print residue classes 0..NT-1 in
       turn, at most MAX_MISS_REPORT per class and overall, as ca_verify does */
    Example *all = xcalloc(n_all ? n_all : 1, sizeof(Example));
    int na = 0;
    for (int i = 0; i < NT; i++) for (int j = 0; j < w[i].n_ex; j++) all[na++] = w[i].ex[j];
    qsort(all, na, sizeof(Example), cmp_example);
    int shown = 0;
    for (int res = 0; res < NT && shown < MAX_MISS_REPORT; res++) {
        int in_res = 0;
        for (int i = 0; i < na && shown < MAX_MISS_REPORT && in_res < MAX_MISS_REPORT; i++) {
            int r = rank_ok ? (int)(all[i].rank % NT) : 0;
            if (r != res) continue;
            in_res++; shown++;
            printf("  missing: columns (");
            for (int q = 0; q < T; q++) printf("%d%s", all[i].cols[q], q < T - 1 ? "," : "");
            printf(") tuple (");
            long long idx = all[i].tuple;
            int digs[MAXT];
            for (int q = T - 1; q >= 0; q--) { digs[q] = (int)(idx % V); idx /= V; }
            for (int q = 0; q < T; q++) printf("%d%s", digs[q], q < T - 1 ? "," : "");
            printf(")\n");
        }
    }
    return 1;
}
