/* cphfcheck.c - exact check of a covering perfect hash family (CPHF), any field q <= 32, t <= 8.
 *
 * Written 2026-11-01 for ca-tools, independently of repcheck_pp.c (which uses exterior products):
 * here coverage is decided by Gaussian elimination over GF(q).
 *
 * A CPHF(n; k, q, t) is an n x k array whose entries are vectors of GF(q)^t; a set of t columns is
 * covered in a row when the t vectors of that row are linearly independent; the array is a CPHF
 * when every t-set is covered in at least one row. It gives a CA(n (q^t - 1) + 1; t, k, q), and
 * a CA(n (q^t - q) + q; t, k, q) when every vector has first coordinate 1 (affine points,
 * Sherwood, Martirosyan and Colbourn 2006).
 *
 * File: lines starting with '#' are comments; then n lines of k integers. Each integer is a vector
 * written in base q, most significant digit first (digit j = coordinate j); a digit is a field
 * element code: for q = p prime the residue, for q = p^e the integer sum c_i p^i of its coordinates
 * in the basis 1, x, ..., x^(e-1) of GF(p)[x]/(f), f the Conway polynomial below. (The format of
 * repcheck_pp.c; the same files check with both.)
 *
 * Usage:  cphfcheck FILE t q MODE [threads] [args]
 *   MODE full            every t-set of columns
 *   MODE cyclic s        symmetry col -> col + s (mod k) certified first (per row an invertible
 *                        matrix A_r and scalar mu_r with A_r v[c] = v[c+s] for c < k-s and
 *                        A_r v[c] = mu_r v[c+s-k] otherwise, solved and then checked on every
 *                        column), then every t-set whose smallest column is < s
 *   MODE sample S seed   S random t-sets (a screen, not a proof)
 *   MODE expand OUT [affine]   write the covering array in the table's canonical form: the all-zero run,
 *                        then for every row r and every nonzero beta in GF(q)^t (base q, most significant
 *                        digit first, in increasing order) the run beta . v_r[c] (the order of
 *                        cphf_tools_pp.c expand, so the hashes agree). With "affine" (every vector has first
 *                        coordinate 1) the runs with beta = (b, 0, ..., 0), constant in every column, are left
 *                        out of the rows and written once at the end for b = 1..q-1, giving
 *                        n (q^t - q) + q runs (Sherwood, Martirosyan and Colbourn 2006).
 *   MODE progression [threads] [P=r1,r2,...]
 *                        rows are classified from the data: progression rows (an invertible A with
 *                        u_c = A u_{c-1} for every c = 1..k-1, solved and then checked on every
 *                        column), dead rows (vectors do not span GF(q)^t; dropped), other rows. A t-set
 *                        fails in a progression row iff its translate with smallest column 0 does, so
 *                        the representatives D (0 in D) failing in every progression row are found by
 *                        projection hashing, and every shift D + a, a = 0..k-1-max(D), is tested by
 *                        rank in every other row. P= lists rows that must certify (exit 3 if not).
 *   MODE fullfast [threads]
 *                        every t-set, by projection hashing over all rows (prefixes of t-2 columns)
 *   MODE fastprog [threads] [P=r1,r2,...] [shard i m]
 *                        (since 2026-11-02) mode progression's result (same representatives, same counts and
 *                        binomials, same rank recheck and shift tests) by a faster exact method: prefixes of
 *                        t-3 columns, point indices in PG(2,q), a line table for the classes, and a hash join
 *                        over up to three rows at once; see the section "mode fastprog" below and
 *                        tools/cphf/README.md. k at most 65535. Mode progression stays as the simpler reference.
 *   Both new modes print counts that must equal binomials (prefixes, candidate columns, and pairs
 *   failing + pairs ruled out) and recheck every reported set by rank; a mismatch exits 4.
 *   With the environment variable CPHFCHECK_LIST set, modes full, progression and fullfast also print
 *   every uncovered t-set as a line "U c1 ... ct" (a testing aid; order not fixed in the new modes).
 *   In the new modes "first uncovered" is the lexicographically smallest uncovered t-set.
 *   MODE estimate [threads]
 *                        (since 2026-11-02) runs nothing exact: classifies the rows, looks for a cyclic shift
 *                        symmetry (the smallest s dividing k, s < k, that certify_cyclic accepts), and prints
 *                        for every applicable method its work units and estimated time from the unit costs
 *                        measured in tools/cphf/README.md (function unit_ns below), then the cheapest.
 *   MODE auto [threads] [shard i m]
 *                        the estimate, then the cheapest exact method (cyclic s, fastprog, progression, fullfast or full),
 *                        printed as "auto: method ..." before its own output. The choice depends on the data only.
 *   MODE canon OUT       write the family in the canonical serialization "cphf1" (tools/cphf/README.md): first
 *                        line "cphf1 n k q t", then n lines of k decimal codes, single spaces, LF after every line.
 *   "shard i m" (after the thread count, modes full, cyclic, fullfast, progression, fastprog, auto): run only shard i of m
 *                        (0 <= i < m): the outer loop indices are dealt to m shards by weight (largest first, each
 *                        to the least loaded shard, ties to the lower index; deterministic), and this run does the
 *                        indices of shard i. It prints its partial counts in a line "SHARD i=.. m=.. ..." (the
 *                        partial counts are checked against the binomial sums of its own indices, exit 4 if not),
 *                        the lexicographically smallest uncovered t-set of the shard and every uncovered t-set as
 *                        "U c1 ... ct" (at most CPHFCHECK_LISTCAP, default 10000, lines). It never prints RESULT:
 *                        tools/cphf_cert.py combines the m outputs and checks that the partial counts add up to
 *                        the totals an unsharded run checks, which also catches a missing or repeated shard.
 * Output: the number of uncovered t-sets checked (0 = CPHF in modes full and cyclic), the first ones,
 * and the affine flag. Exit 0 if none uncovered, 1 if some, 2 usage/format error, 3 symmetry fails
 * (or a row listed in P= is not a progression row), 4 internal consistency check failed.
 *
 * Method: for a prefix c_0 < ... < c_{t-2}, per row, the t-1 vectors are reduced by elimination; if
 * they are independent their span is a hyperplane, whose normal w (w . v = 0 for the prefix vectors)
 * is found by solving the reduced system; then the t-set with last column c is covered in that row
 * iff w . v[c] != 0. A prefix dependent in a row covers nothing in that row.
 * Build: gcc -O3 -fopenmp -o cphfcheck cphfcheck.c
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#ifdef _OPENMP
#include <omp.h>
#endif
#if defined(__AVX2__) && !defined(NO_AVX2)
#include <immintrin.h>
#endif

#define MAXT 8
static int n, k, t, q, p, e;
static int g_quiet;                /* certify_cyclic: no messages (used when searching for a symmetry) */
static uint8_t *V;                 /* V[(r*k + c)*t + j] */
static uint8_t ADD[32][32], MUL[32][32], NEG[32], INV[32];

/* ---------- field ---------- */
static int field_setup(void) {
    p = 0; for (int d = 2; d <= q; d++) if (q % d == 0) { p = d; break; }
    e = 0; int x = 1; while (x < q) { x *= p; e++; }
    if (x != q || q > 32) return 0;
    int f[6] = {0};                  /* x^e = -(f0 + f1 x + ...) ; Conway polynomials */
    if (e == 2 && p == 2) { f[0] = 1; f[1] = 1; }               /* x^2+x+1 */
    else if (e == 3 && p == 2) { f[0] = 1; f[1] = 1; }          /* x^3+x+1 */
    else if (e == 4 && p == 2) { f[0] = 1; f[1] = 1; }          /* x^4+x+1 */
    else if (e == 5 && p == 2) { f[0] = 1; f[2] = 1; }          /* x^5+x^2+1 */
    else if (e == 2 && p == 3) { f[0] = 2; f[1] = 2; }          /* x^2+2x+2 */
    else if (e == 3 && p == 3) { f[0] = 1; f[1] = 2; }          /* x^3+2x+1 */
    else if (e == 2 && p == 5) { f[0] = 2; f[1] = 4; }          /* x^2+4x+2 */
    else if (e != 1) return 0;
    /* element code -> coordinate vector; add and multiply polynomials mod f */
    for (int a = 0; a < q; a++) for (int b = 0; b < q; b++) {
        int ca[6] = {0}, cb[6] = {0}, s = 0, pw = 1;
        for (int i = 0, u = a, w = b; i < e; i++) { ca[i] = u % p; u /= p; cb[i] = w % p; w /= p; }
        for (int i = 0; i < e; i++) { s += ((ca[i] + cb[i]) % p) * pw; pw *= p; }
        ADD[a][b] = (uint8_t)s;
        int prod[12] = {0};
        for (int i = 0; i < e; i++) for (int j = 0; j < e; j++) prod[i + j] = (prod[i + j] + ca[i] * cb[j]) % p;
        for (int d = 2 * e - 2; d >= e; d--) {            /* reduce x^d = x^(d-e) * x^e */
            int c = prod[d]; prod[d] = 0;
            if (!c) continue;
            for (int i = 0; i < e; i++) prod[d - e + i] = ((prod[d - e + i] - c * f[i]) % p + p) % p;
        }
        s = 0; pw = 1; for (int i = 0; i < e; i++) { s += prod[i] * pw; pw *= p; }
        MUL[a][b] = (uint8_t)s;
    }
    for (int a = 0; a < q; a++) { for (int b = 0; b < q; b++) if (ADD[a][b] == 0) NEG[a] = (uint8_t)b; }
    INV[0] = 0;
    for (int a = 1; a < q; a++) { int found = 0; for (int b = 1; b < q; b++) if (MUL[a][b] == 1) { INV[a] = (uint8_t)b; found = 1; } if (!found) return 0; }
    /* field axioms spot check: associativity, distributivity, f irreducible means no zero divisors */
    for (int a = 1; a < q; a++) for (int b = 1; b < q; b++) if (MUL[a][b] == 0) return 0;
    for (int a = 0; a < q; a++) for (int b = 0; b < q; b++) for (int c = 0; c < q; c++)
        if (MUL[a][ADD[b][c]] != ADD[MUL[a][b]][MUL[a][c]] || MUL[MUL[a][b]][c] != MUL[a][MUL[b][c]]) return 0;
    return 1;
}

/* ---------- linear algebra ---------- */
/* rank of the m vectors (each t coordinates) */
static int rank_of(const uint8_t *const *vs, int m) {
    uint8_t M[MAXT][MAXT];
    for (int i = 0; i < m; i++) memcpy(M[i], vs[i], t);
    int r = 0;
    for (int col = 0; col < t && r < m; col++) {
        int piv = -1; for (int i = r; i < m; i++) if (M[i][col]) { piv = i; break; }
        if (piv < 0) continue;
        if (piv != r) { uint8_t tmp[MAXT]; memcpy(tmp, M[r], t); memcpy(M[r], M[piv], t); memcpy(M[piv], tmp, t); }
        uint8_t iv = INV[M[r][col]];
        for (int j = 0; j < t; j++) M[r][j] = MUL[M[r][j]][iv];
        for (int i = 0; i < m; i++) if (i != r && M[i][col]) {
            uint8_t fct = NEG[M[i][col]];
            for (int j = 0; j < t; j++) M[i][j] = ADD[M[i][j]][MUL[fct][M[r][j]]];
        }
        r++;
    }
    return r;
}

/* normal w of the span of t-1 vectors: returns 0 if they are dependent */
static int normal_of(const uint8_t *const *vs, uint8_t *w) {
    uint8_t M[MAXT][MAXT]; int m = t - 1, pivcol[MAXT], r = 0;
    for (int i = 0; i < m; i++) memcpy(M[i], vs[i], t);
    int isp[MAXT] = {0};
    for (int col = 0; col < t && r < m; col++) {
        int piv = -1; for (int i = r; i < m; i++) if (M[i][col]) { piv = i; break; }
        if (piv < 0) continue;
        if (piv != r) { uint8_t tmp[MAXT]; memcpy(tmp, M[r], t); memcpy(M[r], M[piv], t); memcpy(M[piv], tmp, t); }
        uint8_t iv = INV[M[r][col]];
        for (int j = 0; j < t; j++) M[r][j] = MUL[M[r][j]][iv];
        for (int i = 0; i < m; i++) if (i != r && M[i][col]) {
            uint8_t fct = NEG[M[i][col]];
            for (int j = 0; j < t; j++) M[i][j] = ADD[M[i][j]][MUL[fct][M[r][j]]];
        }
        pivcol[r] = col; isp[col] = 1; r++;
    }
    if (r < m) return 0;
    int fr = -1; for (int c = 0; c < t; c++) if (!isp[c]) { fr = c; break; }
    /* reduced rows: x_{pivcol[i]} + M[i][fr] x_fr = 0 ; set x_fr = 1 */
    memset(w, 0, t); w[fr] = 1;
    for (int i = 0; i < m; i++) w[pivcol[i]] = NEG[M[i][fr]];
    return 1;
}

static inline uint8_t dot(const uint8_t *a, const uint8_t *b) {
    uint8_t s = 0; for (int j = 0; j < t; j++) s = ADD[s][MUL[a[j]][b[j]]]; return s;
}
#define VEC(r, c) (V + ((size_t)(r) * k + (c)) * t)

/* ---------- input ---------- */
static int read_file(const char *path) {
    FILE *f = fopen(path, "r"); if (!f) { perror(path); return 0; }
    size_t cap = 1 << 16; char *line = malloc(cap); int rows = 0; size_t vcap = 0; V = NULL; k = -1;
    while (1) {
        size_t len = 0; int ch;
        while ((ch = fgetc(f)) != EOF && ch != '\n') { if (len + 1 >= cap) { cap *= 2; line = realloc(line, cap); } line[len++] = (char)ch; }
        if (ch == EOF && len == 0) break;
        line[len] = 0;
        if (line[0] == '#') continue;
        char *s = line; int cnt = 0;
        long long maxcode = 1; for (int j = 0; j < t; j++) maxcode *= q;
        while (*s) {
            while (*s == ' ' || *s == '\t' || *s == ',' || *s == '\r') s++;
            if (!*s) break;
            char *end; long long x = strtoll(s, &end, 10);
            if (end == s || x < 0 || x >= maxcode) { fprintf(stderr, "bad entry on data line %d\n", rows + 1); return 0; }
            s = end;
            size_t need = ((size_t)rows * (k > 0 ? k : 1) + cnt + 1) * t;
            if (k < 0 || need > vcap) { vcap = need * 2 + 1024; V = realloc(V, vcap); }
            uint8_t *dst = V + (k < 0 ? (size_t)cnt * t : ((size_t)rows * k + cnt) * t);
            for (int j = t - 1; j >= 0; j--) { dst[j] = (uint8_t)(x % q); x /= q; }
            cnt++;
        }
        if (cnt == 0) { if (ch == EOF) break; continue; }
        if (k < 0) k = cnt;
        else if (cnt != k) { fprintf(stderr, "row %d has %d entries, expected %d\n", rows + 1, cnt, k); return 0; }
        rows++;
        if (ch == EOF) break;
    }
    n = rows; fclose(f); free(line);
    return n > 0 && k >= t;
}

/* ---------- checking ---------- */
static long long check_prefix(const int *pre, int cfrom, int cto, long long *firstbad, int *nbad_out) {
    /* returns the number of last columns c in [cfrom, cto) uncovered by every row */
    uint8_t W[64][MAXT]; int ok[64]; const uint8_t *vs[MAXT];
    for (int r = 0; r < n; r++) {
        for (int i = 0; i < t - 1; i++) vs[i] = VEC(r, pre[i]);
        ok[r] = normal_of(vs, W[r]);
    }
    long long bad = 0;
    for (int c = cfrom; c < cto; c++) {
        int cov = 0;
        for (int r = 0; r < n && !cov; r++) if (ok[r] && dot(W[r], VEC(r, c))) cov = 1;
        if (!cov) { if (bad == 0 && firstbad) *firstbad = c; bad++; }
    }
    (void)nbad_out;
    return bad;
}

static int certify_cyclic(int s) {
    if (k % s) { if (!g_quiet) fprintf(stderr, "s=%d does not divide k=%d\n", s, k); return 0; }
    for (int r = 0; r < n; r++) {
        /* choose t independent columns among 0..k-s-1 */
        int sel[MAXT], m = 0; const uint8_t *vs[MAXT];
        for (int c = 0; c < k - s && m < t; c++) { vs[m] = VEC(r, c); if (rank_of(vs, m + 1) == m + 1) { sel[m] = c; m++; } }
        if (m < t) { if (!g_quiet) fprintf(stderr, "row %d: no %d independent columns, symmetry not certified\n", r, t); return 0; }
        /* solve A X = Y with X = [v[sel]], Y = [v[sel+s]]: A = Y X^{-1}; invert X by elimination on [X^T | I] */
        uint8_t X[MAXT][2 * MAXT];
        for (int i = 0; i < t; i++) { for (int j = 0; j < t; j++) X[i][j] = VEC(r, sel[j])[i]; for (int j = 0; j < t; j++) X[i][t + j] = (i == j); }
        for (int col = 0; col < t; col++) {
            int piv = -1; for (int i = col; i < t; i++) if (X[i][col]) { piv = i; break; }
            if (piv < 0) return 0;
            if (piv != col) for (int j = 0; j < 2 * t; j++) { uint8_t tmp = X[col][j]; X[col][j] = X[piv][j]; X[piv][j] = tmp; }
            uint8_t iv = INV[X[col][col]]; for (int j = 0; j < 2 * t; j++) X[col][j] = MUL[X[col][j]][iv];
            for (int i = 0; i < t; i++) if (i != col && X[i][col]) { uint8_t fct = NEG[X[i][col]]; for (int j = 0; j < 2 * t; j++) X[i][j] = ADD[X[i][j]][MUL[fct][X[col][j]]]; }
        }
        /* Xinv[a][b] = X[a][t+b]; A[i][j] = sum_l Y[i][l] Xinv[l][j], Y[i][l] = v[sel[l]+s][i] */
        uint8_t A[MAXT][MAXT];
        for (int i = 0; i < t; i++) for (int j = 0; j < t; j++) { uint8_t sum = 0; for (int l = 0; l < t; l++) sum = ADD[sum][MUL[VEC(r, sel[l] + s)[i]][X[l][t + j]]]; A[i][j] = sum; }
        const uint8_t *rowsA[MAXT]; for (int i = 0; i < t; i++) rowsA[i] = A[i];
        if (rank_of(rowsA, t) != t) { if (!g_quiet) fprintf(stderr, "row %d: A singular\n", r); return 0; }
        int mu = -1;
        for (int c = 0; c < k; c++) {
            uint8_t img[MAXT]; for (int i = 0; i < t; i++) { uint8_t sum = 0; for (int j = 0; j < t; j++) sum = ADD[sum][MUL[A[i][j]][VEC(r, c)[j]]]; img[i] = sum; }
            const uint8_t *tgt = VEC(r, (c + s) % k);
            if (c < k - s) { if (memcmp(img, tgt, t)) { if (!g_quiet) fprintf(stderr, "row %d col %d: A v != v[c+s]\n", r, c); return 0; } }
            else {
                int jn = -1; for (int j = 0; j < t; j++) if (tgt[j]) { jn = j; break; }
                if (jn < 0 || !img[jn]) { if (!g_quiet) fprintf(stderr, "row %d col %d: wrap fails\n", r, c); return 0; }
                int m2 = MUL[img[jn]][INV[tgt[jn]]];
                if (mu < 0) mu = m2;
                if (m2 != mu) { if (!g_quiet) fprintf(stderr, "row %d: mu not constant\n", r); return 0; }
                for (int j = 0; j < t; j++) if (img[j] != MUL[(uint8_t)mu][tgt[j]]) { if (!g_quiet) fprintf(stderr, "row %d col %d: wrap fails\n", r, c); return 0; }
            }
        }
    }
    return 1;
}

/* ---------- projection hashing: modes progression and fullfast ----------
 * For a prefix of t-2 columns whose vectors are independent in row r, h1, h2 (a basis of the
 * annihilator of their span) map GF(q)^t onto GF(q)^2 with kernel exactly that span. The t-set
 * prefix + {x, y} is dependent in row r iff the images of u_x and u_y are dependent in GF(q)^2,
 * i.e. iff one image is 0 (class WILD) or both lie on the same point of PG(1, q) (equal class).
 * A row in which the prefix itself is dependent is a wildcard row: every completion fails there.
 * split() finds every pair failing in all non-wildcard rows by refining row by row. A problem
 * (A, B) stands for the pairs inside A and the pairs between A and B (never pairs inside B).
 * Classifying by row r into classes A_z, B_z (z in PG(1,q)) and A_w, B_w (WILD), the failing pairs
 * are partitioned exactly into the subproblems (A_z, A_w + B_z + B_w) for every z, and (A_w, B);
 * the pairs ruled out are those with two non-WILD, different classes, counted separately, so that
 * failing + ruled out pairs must add up to C(m, 2) for every prefix (checked as a binomial total). */
typedef unsigned __int128 u128;
#define WILDC (q + 1)              /* class of a column in the span of the prefix: matches every class */
#define NCLS 34                    /* q + 2 <= 34 */
#ifndef SMALLPAIRS
#define SMALLPAIRS 12              /* subproblems with at most this many pairs are finished pair by pair */
#endif
#define REPCAP 65536

static void u128_str(u128 x, char *buf) {
    char tmp[64]; int i = 0;
    do { tmp[i++] = (char)('0' + (int)(x % 10)); x /= 10; } while (x);
    int j = 0; while (i) buf[j++] = tmp[--i]; buf[j] = 0;
}
static u128 binom(int a, int b) {
    if (b < 0 || a < 0 || b > a) return 0;
    u128 r = 1; for (int i = 1; i <= b; i++) r = r * (u128)(a - b + i) / (u128)i;
    return r;
}

/* ---------- shards ----------
 * "shard i m": the outer loop of a mode runs over indices lo..hi-1 (full and cyclic: the smallest column c0;
 * fullfast: the first prefix column; progression, t >= 4: the second column of the representative). Index j
 * has weight binom(k-1-j, d) (the work it stands for, d set by the mode). The indices are sorted by weight,
 * largest first (ties: smaller index first), and each goes to the shard with the least weight so far (ties:
 * the lower shard). Every index belongs to exactly one shard, whatever m is; tools/cphf_cert.py checks the
 * combined counts against the totals of an unsharded run. Modes whose outer loop has a single index (t = 2,
 * and progression at t = 3) give all their work to shard 0. */
static int g_shi = 0, g_shm = 0;       /* this run is shard g_shi of g_shm; g_shm = 0: no sharding */
static unsigned char *g_own;           /* g_own[j - g_lo]: index j is done by this run */
static int g_lo = 0, g_hi = 0, g_nown = 0;
static u128 g_wown = 0, g_wtot = 0;
static u128 *g_wsort;
static int cmp_idx(const void *a, const void *b) {
    int x = *(const int *)a, y = *(const int *)b;
    if (g_wsort[x] != g_wsort[y]) return g_wsort[x] > g_wsort[y] ? -1 : 1;
    return x - y;
}
static int shard_setup(int lo, int hi, int d) {
    g_lo = lo; g_hi = hi; int len = hi > lo ? hi - lo : 0;
    g_own = calloc((size_t)len + 1, 1); g_nown = 0; g_wown = g_wtot = 0;
    u128 *w = calloc((size_t)len + 1, sizeof(u128)); int *idx = malloc(((size_t)len + 1) * sizeof(int));
    if (!g_own || !w || !idx) return 0;
    for (int j = 0; j < len; j++) { w[j] = d < 0 ? 1 : binom(k - 1 - (lo + j), d); idx[j] = j; g_wtot += w[j]; }
    if (!g_shm) { memset(g_own, 1, (size_t)len); g_nown = len; g_wown = g_wtot; free(w); free(idx); return 1; }
    g_wsort = w; qsort(idx, (size_t)len, sizeof(int), cmp_idx);
    u128 *load = calloc((size_t)g_shm, sizeof(u128)); if (!load) return 0;
    for (int a = 0; a < len; a++) {
        int best = 0; for (int s = 1; s < g_shm; s++) if (load[s] < load[best]) best = s;
        load[best] += w[idx[a]];
        if (best == g_shi) { g_own[idx[a]] = 1; g_nown++; g_wown += w[idx[a]]; }
    }
    free(load); free(w); free(idx);
    return 1;
}
static inline int owned(int j) { return j >= g_lo && j < g_hi && g_own[j - g_lo]; }
static long long g_listcap = -1, g_listed = 0;   /* -1: no limit */
static void shard_banner(const char *what) {
    char a[64], b[64]; u128_str(g_wown, a); u128_str(g_wtot, b);
    printf("shard %d of %d: %d of %d outer indices (%s), weight %s of %s\n", g_shi, g_shm, g_nown, g_hi - g_lo, what, a, b);
    /* the indices themselves, as ranges, so that the combiner can check that the shards cover the outer
       loop exactly once (and recompute each shard's counts from its indices) */
    printf("SHARD indices:");
    int first = 1;
    for (int j = g_lo; j < g_hi; j++) if (owned(j)) {
        int e2 = j; while (e2 + 1 < g_hi && owned(e2 + 1)) e2++;
        if (e2 > j) printf("%s%d-%d", first ? " " : ",", j, e2); else printf("%s%d", first ? " " : ",", j);
        first = 0; j = e2;
    }
    printf("%s\n", first ? " none" : "");
}

/* basis of {h : h . v = 0 for the m vectors}: returns the rank of the vectors, writes t - rank vectors to H */
static int annihilator(const uint8_t *const *vs, int m, uint8_t H[MAXT][MAXT]) {
    uint8_t M[MAXT][MAXT]; int pivcol[MAXT], isp[MAXT] = {0}, r = 0;
    for (int i = 0; i < m; i++) memcpy(M[i], vs[i], t);
    for (int col = 0; col < t && r < m; col++) {
        int piv = -1; for (int i = r; i < m; i++) if (M[i][col]) { piv = i; break; }
        if (piv < 0) continue;
        if (piv != r) { uint8_t tmp[MAXT]; memcpy(tmp, M[r], t); memcpy(M[r], M[piv], t); memcpy(M[piv], tmp, t); }
        uint8_t iv = INV[M[r][col]];
        for (int j = 0; j < t; j++) M[r][j] = MUL[M[r][j]][iv];
        for (int i = 0; i < m; i++) if (i != r && M[i][col]) {
            uint8_t fct = NEG[M[i][col]];
            for (int j = 0; j < t; j++) M[i][j] = ADD[M[i][j]][MUL[fct][M[r][j]]];
        }
        pivcol[r] = col; isp[col] = 1; r++;
    }
    int nf = 0;
    for (int fc = 0; fc < t; fc++) if (!isp[fc]) {
        memset(H[nf], 0, t); H[nf][fc] = 1;
        for (int i = 0; i < r; i++) H[nf][pivcol[i]] = NEG[M[i][fc]];
        nf++;
    }
    return r;
}

static inline uint8_t fdot(const uint8_t *a, const uint8_t *b) {   /* = dot(a, b); integer arithmetic for prime q */
    if (e == 1) { int s = 0; for (int j = 0; j < t; j++) s += a[j] * b[j]; return (uint8_t)(s % q); }
    return dot(a, b);
}

static inline int cls_of(const uint8_t H[2][MAXT], const uint8_t *u) {
    uint8_t a = fdot(H[0], u), b = fdot(H[1], u);
    if (!a && !b) return WILDC;
    if (b) return MUL[a][INV[b]];
    return q;
}

static int set_rank(int r, const int *S) {
    const uint8_t *vs[MAXT]; for (int i = 0; i < t; i++) vs[i] = VEC(r, S[i]);
    return rank_of(vs, t);
}

/* row r: 0 dead (its vectors do not span GF(q)^t, it covers nothing), 1 progression (u_c = A u_{c-1}
 * for every c = 1..k-1 with A invertible, A derived from the data and then checked on every column),
 * 2 other. why gets a short reason. */
static int classify_row(int r, uint8_t A[MAXT][MAXT], char *why, size_t wl) {
    const uint8_t *vs[MAXT]; int m = 0;
    for (int c = 0; c < k && m < t; c++) { vs[m] = VEC(r, c); if (rank_of(vs, m + 1) == m + 1) m++; }
    if (m < t) { snprintf(why, wl, "dead (its vectors span a space of dimension %d < t, it covers no t-set)", m); return 0; }
    int sel[MAXT]; m = 0;
    for (int c = 0; c < k - 1 && m < t; c++) { vs[m] = VEC(r, c); if (rank_of(vs, m + 1) == m + 1) { sel[m] = c; m++; } }
    if (m < t) { snprintf(why, wl, "other (columns 0..k-2 do not span GF(q)^t)"); return 2; }
    /* A X = Y, X = [u_sel], Y = [u_{sel+1}] (vectors as columns): A = Y X^{-1}; invert X on [X | I] */
    uint8_t X[MAXT][2 * MAXT];
    for (int i = 0; i < t; i++) { for (int j = 0; j < t; j++) X[i][j] = VEC(r, sel[j])[i]; for (int j = 0; j < t; j++) X[i][t + j] = (i == j); }
    for (int col = 0; col < t; col++) {
        int piv = -1; for (int i = col; i < t; i++) if (X[i][col]) { piv = i; break; }
        if (piv < 0) { snprintf(why, wl, "other (internal: X singular)"); return 2; }
        if (piv != col) for (int j = 0; j < 2 * t; j++) { uint8_t tmp = X[col][j]; X[col][j] = X[piv][j]; X[piv][j] = tmp; }
        uint8_t iv = INV[X[col][col]]; for (int j = 0; j < 2 * t; j++) X[col][j] = MUL[X[col][j]][iv];
        for (int i = 0; i < t; i++) if (i != col && X[i][col]) { uint8_t fct = NEG[X[i][col]]; for (int j = 0; j < 2 * t; j++) X[i][j] = ADD[X[i][j]][MUL[fct][X[col][j]]]; }
    }
    for (int i = 0; i < t; i++) for (int j = 0; j < t; j++) {
        uint8_t sum = 0; for (int l = 0; l < t; l++) sum = ADD[sum][MUL[VEC(r, sel[l] + 1)[i]][X[l][t + j]]];
        A[i][j] = sum;
    }
    const uint8_t *rowsA[MAXT]; for (int i = 0; i < t; i++) rowsA[i] = A[i];
    if (rank_of(rowsA, t) != t) { snprintf(why, wl, "other (the matrix A solved from the data is singular)"); return 2; }
    for (int c = 1; c <= k - 1; c++) {
        uint8_t img[MAXT];
        for (int i = 0; i < t; i++) { uint8_t sum = 0; for (int j = 0; j < t; j++) sum = ADD[sum][MUL[A[i][j]][VEC(r, c - 1)[j]]]; img[i] = sum; }
        if (memcmp(img, VEC(r, c), t)) { snprintf(why, wl, "other (u_%d != A u_%d)", c, c - 1); return 2; }
    }
    snprintf(why, wl, "progression");
    return 1;
}

typedef struct {
    int nlive, live[64]; uint8_t H[64][2][MAXT];   /* non-wildcard rows of the current prefix, their h1, h2 */
    int pre[MAXT], npre;
    int *pool; size_t top, cap;                     /* stack of int arrays for split() */
    long long prefixes, wildrows, wildcls;          /* statistics */
    u128 cand, outpairs, elimpairs;
    u128 reps, shifts, unc; long long bad_recheck;  /* results */
    int have_min, minset[MAXT];
    int *rep; size_t nrep;                          /* representatives waiting for their shifts */
    struct Fp *F;                                   /* mode fastprog */
    char pad[64];
} Ctx;
struct Fp;
typedef struct Fp Fp;

static int g_prog;                    /* 1: mode progression, 0: mode fullfast */
static int g_inner_par;               /* progression t = 3: one prefix, shifts tested in parallel */
static int g_list;                    /* CPHFCHECK_LIST set: print every uncovered t-set ("U c1 ... ct") */
static int Prow[64], nP, Orow[64], nO, Lrow[64], nL;
static Ctx *ctxs;

static int ctx_tid(void) {
#ifdef _OPENMP
    return omp_get_thread_num();
#else
    return 0;
#endif
}

static int *palloc(Ctx *X, size_t m) {
    if (X->top + m > X->cap) { fprintf(stderr, "INTERNAL CHECK FAILED: work stack overflow\n"); printf("INTERNAL CHECK FAILED: work stack overflow\n"); fflush(stdout); exit(4); }
    int *p = X->pool + X->top; X->top += m; return p;
}

static void record_uncovered(Ctx *X, const int *S) {
    X->unc++;
    int less = !X->have_min;
    if (!less) for (int i = 0; i < t; i++) if (S[i] != X->minset[i]) { less = S[i] < X->minset[i]; break; }
    if (less) { X->have_min = 1; memcpy(X->minset, S, t * sizeof(int)); }
    if (g_list) {
        #pragma omp critical(cphf_list)
        { if (g_listcap < 0 || g_listed < g_listcap) { g_listed++; printf("U"); for (int i = 0; i < t; i++) printf(" %d", S[i]); printf("\n"); } }
    }
}

/* representative D (D[0] = 0) fails in every progression row: test every shift D + a in the other rows */
static void test_rep(Ctx *X, const int *D) {
    for (int i = 0; i < nP; i++) if (set_rank(Prow[i], D) == t) { X->bad_recheck++; return; }
    X->reps++;
    for (int a = 0; a <= k - 1 - D[t - 1]; a++) {
        int S[MAXT]; for (int i = 0; i < t; i++) S[i] = D[i] + a;
        X->shifts++;
        int cov = 0;
        for (int i = 0; i < nO && !cov; i++) if (set_rank(Orow[i], S) == t) cov = 1;
        if (!cov) record_uncovered(X, S);
    }
}

static void flush_reps(Ctx *X) {
    if (g_inner_par) {
        long long nr = (long long)X->nrep; const int *R = X->rep;
        #pragma omp parallel for schedule(dynamic, 16)
        for (long long i = 0; i < nr; i++) test_rep(&ctxs[ctx_tid()], R + i * t);
    } else for (size_t i = 0; i < X->nrep; i++) test_rep(X, X->rep + i * t);
    X->nrep = 0;
}

static void emit_pair(Ctx *X, int x, int y) {
    if (x > y) { int tmp = x; x = y; y = tmp; }
    int S[MAXT]; for (int i = 0; i < X->npre; i++) S[i] = X->pre[i];
    S[X->npre] = x; S[X->npre + 1] = y;
    if (g_prog) {
        memcpy(X->rep + X->nrep * t, S, t * sizeof(int));
        if (++X->nrep == REPCAP) flush_reps(X);
    } else {
        for (int r = 0; r < n; r++) if (set_rank(r, S) == t) { X->bad_recheck++; return; }   /* exact recheck */
        record_uncovered(X, S);
    }
}

/* one pair against the non-wildcard rows depth..nlive-1, the same rule: fails iff WILD or equal classes */
static void pair_rest(Ctx *X, int depth, int x, int y) {
    for (int d = depth; d < X->nlive; d++) {
        int r = X->live[d];
        int cx = cls_of(X->H[d], VEC(r, x)), cy = cls_of(X->H[d], VEC(r, y));
        if (cx == WILDC || cy == WILDC) { X->wildcls++; continue; }
        if (cx != cy) { X->elimpairs++; return; }
    }
    X->outpairs++;
    emit_pair(X, x, y);
}

static void split(Ctx *X, int depth, const int *A, int nA, const int *B, int nB) {
    if (nA == 0 || (nA == 1 && nB == 0)) return;
    if (depth == X->nlive) {
        X->outpairs += (u128)nA * (u128)(nA - 1) / 2 + (u128)nA * (u128)nB;
        for (int i = 0; i < nA; i++) {
            for (int j = i + 1; j < nA; j++) emit_pair(X, A[i], A[j]);
            for (int j = 0; j < nB; j++) emit_pair(X, A[i], B[j]);
        }
        return;
    }
    if ((long long)nA * (nA - 1) / 2 + (long long)nA * nB <= SMALLPAIRS) {
        for (int i = 0; i < nA; i++) {
            for (int j = i + 1; j < nA; j++) pair_rest(X, depth, A[i], A[j]);
            for (int j = 0; j < nB; j++) pair_rest(X, depth, A[i], B[j]);
        }
        return;
    }
    size_t mark = X->top;
    const uint8_t (*H)[MAXT] = X->H[depth]; int r = X->live[depth];
    int *cA = palloc(X, nA), *cB = palloc(X, nB), *sA = palloc(X, nA), *sB = palloc(X, nB);
    int cntA[NCLS] = {0}, cntB[NCLS] = {0};
    for (int i = 0; i < nA; i++) { cA[i] = cls_of(H, VEC(r, A[i])); cntA[cA[i]]++; }
    for (int i = 0; i < nB; i++) { cB[i] = cls_of(H, VEC(r, B[i])); cntB[cB[i]]++; }
    X->wildcls += cntA[WILDC] + cntB[WILDC];
    u128 sa = 0, sb = 0, sqa = 0, ab = 0;          /* pairs ruled out: two classes, different */
    for (int z = 0; z <= q; z++) { sa += cntA[z]; sb += cntB[z]; sqa += (u128)cntA[z] * cntA[z]; ab += (u128)cntA[z] * cntB[z]; }
    X->elimpairs += (sa * sa - sqa) / 2 + (sa * sb - ab);
    int offA[NCLS + 1], offB[NCLS + 1], posA[NCLS], posB[NCLS];
    offA[0] = offB[0] = 0;
    for (int z = 0; z <= q + 1; z++) { offA[z + 1] = offA[z] + cntA[z]; offB[z + 1] = offB[z] + cntB[z]; posA[z] = offA[z]; posB[z] = offB[z]; }
    for (int i = 0; i < nA; i++) sA[posA[cA[i]]++] = A[i];
    for (int i = 0; i < nB; i++) sB[posB[cB[i]]++] = B[i];
    const int W = WILDC;
    for (int z = 0; z <= q; z++) {
        if (!cntA[z]) continue;
        size_t m2 = X->top;
        int nb = cntA[W] + cntB[z] + cntB[W], j = 0;
        int *cb = palloc(X, nb);
        for (int i = 0; i < cntA[W]; i++) cb[j++] = sA[offA[W] + i];
        for (int i = 0; i < cntB[z]; i++) cb[j++] = sB[offB[z] + i];
        for (int i = 0; i < cntB[W]; i++) cb[j++] = sB[offB[W] + i];
        split(X, depth + 1, sA + offA[z], cntA[z], cb, nb);
        X->top = m2;
    }
    if (cntA[W]) split(X, depth + 1, sA + offA[W], cntA[W], B, nB);
    X->top = mark;
}

/* prefix pre (npre = t-2 columns): every completion {x < y}, x > last prefix column */
static void process_prefix(Ctx *X, const int *pre, int npre, const int *rowsH, int nrowsH) {
    X->prefixes++;
    int last = npre ? pre[npre - 1] : -1, m = k - 1 - last;
    X->cand += (u128)m;
    memcpy(X->pre, pre, npre * sizeof(int)); X->npre = npre;
    X->nlive = 0;
    for (int i = 0; i < nrowsH; i++) {
        int r = rowsH[i];
        const uint8_t *vs[MAXT]; for (int j = 0; j < npre; j++) vs[j] = VEC(r, pre[j]);
        uint8_t Hb[MAXT][MAXT]; int rk = annihilator(vs, npre, Hb);
        if (rk < npre) { X->wildrows++; continue; }          /* wildcard row: every completion fails */
        memcpy(X->H[X->nlive][0], Hb[0], t); memcpy(X->H[X->nlive][1], Hb[1], t); X->live[X->nlive++] = r;
    }
    if (m < 2) return;
    size_t mark = X->top;
    int *A = palloc(X, m); for (int i = 0; i < m; i++) A[i] = last + 1 + i;
    split(X, 0, A, m, NULL, 0);
    X->top = mark;
}

/* pre[0..fixed-1] given; every way to fill pre[fixed..npre-1] with increasing columns */
static void enum_prefixes(Ctx *X, int *pre, int fixed, int npre, const int *rowsH, int nrowsH) {
    int r = npre - fixed;
    if (r == 0) { process_prefix(X, pre, npre, rowsH, nrowsH); return; }
    int lo = fixed ? pre[fixed - 1] + 1 : 0;
    if (lo + r > k) return;
    for (int i = 0; i < r; i++) pre[fixed + i] = lo + i;
    while (1) {
        process_prefix(X, pre, npre, rowsH, nrowsH);
        int i = r - 1;
        while (i >= 0 && pre[fixed + i] == k - r + i) i--;
        if (i < 0) break;
        pre[fixed + i]++; for (int j = i + 1; j < r; j++) pre[fixed + j] = pre[fixed + j - 1] + 1;
    }
}

/* ---------- mode fastprog: projection hashing through a prefix of t-3 columns, line table, hash join ----------
 * Same representatives D (0 in D, failing in every progression row), the same classes and the same
 * decision rule as mode progression; what changes is how a class is computed and how the pairs with
 * equal classes in every row are found.
 * Classes. For a prefix P' of t-3 columns (0 in P' when t > 3; empty for t = 3) and a progression row
 * r in which the vectors of P' have rank t-3, the quotient GF(q)^t / span(P') is 3-dimensional; the
 * quotient map phi_r (coordinates = three annihilator vectors of span(P')) sends every column c to
 * phi_r(u_c), which is 0 or a point of PG(2,q); pt_r[c] is its index (ZEROP for 0), computed once per
 * (P', row) and reused for every extension P = P' + {p}. For D = P + {x, y}:
 *   dim span(D) = (t-3) + dim span(phi(u_p), phi(u_x), phi(u_y)),
 * so D fails in r iff those three images are dependent. With phi(u_p) != 0 (otherwise P is dependent
 * in r: wildcard row, every completion fails, the row is skipped for this p), column c is WILD iff
 * phi(u_c) = 0 or phi(u_c) is the point phi(u_p) (iff u_c in span(P)), and otherwise its class is the
 * line of PG(2,q) through phi(u_p) and phi(u_c), one of the q+1 lines through phi(u_p), numbered 0..q
 * in the table row LINE[phi(u_p)][.]: two non-WILD columns x, y have the same class iff the three
 * points are collinear iff D fails in r. These are the classes [h1.u : h2.u] of mode progression
 * (the hyperplanes through span(P) are the lines through phi(u_p)), so the rule is the same: {x, y}
 * fails in r iff x or y is WILD or their classes are equal. If the vectors of P' have rank < t-3 in
 * row r, every t-set containing P' fails in r and the row is skipped for the whole P'.
 * Join. For one p the columns c > p are decided together by a hash join over j = 1, 2 or 3 live rows
 * at once (fjoin): see there. Pairs passing the j rows continue row by row, and a pair passing every
 * live row is a representative, rechecked by rank (test_rep) and then shifted over the other rows as
 * in mode progression. The same binomial totals are printed and checked.
 * Cost. Per (P', p, c > p): j table lookups per row and one hash insert, about 10-15 instructions;
 * per (P', row): 3 dot products per column (the point indices). Memory per thread: a few hundred KB.
 */
static int g_fast;                    /* 1: mode fastprog */
static int NPTS, ZEROP;               /* q^2 + q + 1 points of PG(2,q); index used for the zero vector */
static uint16_t *PTIDX;               /* vector code (a q^2 + b q + c) -> point index or ZEROP */
static uint8_t *LINE;                 /* [(NPTS+1)*(NPTS+1)]: LINE[P][Q] = id of line PQ among the lines through P (0..q), WILDC if Q = P or Q = ZEROP */
static uint8_t *VT;                   /* [i][j][c] (i: index in Prow): coordinate j of column c, for the vectorized point computation */
static uint8_t *MODQ;                 /* x mod q for 0 <= x <= t (q-1)^2 (prime q) */
#define LN(P) (LINE + (size_t)(P) * (NPTS + 1))
#ifndef JOIN_J2
#define JOIN_J2 24                    /* more than this many columns after p: join two rows at once */
#endif
#ifndef JOIN_J3
#define JOIN_J3 300                   /* more than this many: three rows at once */
#endif

struct Fp {
    uint16_t *pt;                     /* [d * k + c]: point of column c in the quotient by P', row liveP[d] */
    int nliveP, liveP[64];            /* progression rows in which P' has rank t-3 */
    int pp[MAXT], npp, last, ready;
    int nlive; const uint8_t *Lrow[64]; const uint16_t *ptrow[64];   /* rows live for the current p, in order */
    uint32_t *tab; uint32_t cur_stamp; size_t nkeys;   /* hash join: tab[key] = (stamp << 16) | last index with that key */
    int *nxt, *key;                              /* chain: previous index with the same key, -1 none, -2 WILD; keys */
    int *wlist; uint8_t *wmask, *wz;             /* WILD columns of the join: index, rows (bits), classes */
    int16_t *acc;                                /* [3][k] dot product accumulators (prime q) */
};

static uint8_t cross_norm_idx(const uint8_t *a, const uint8_t *b, int *idx) {
    uint8_t w[3];
    w[0] = ADD[MUL[a[1]][b[2]]][NEG[MUL[a[2]][b[1]]]];
    w[1] = ADD[MUL[a[2]][b[0]]][NEG[MUL[a[0]][b[2]]]];
    w[2] = ADD[MUL[a[0]][b[1]]][NEG[MUL[a[1]][b[0]]]];
    *idx = PTIDX[(w[0] * q + w[1]) * q + w[2]];
    return w[0] | w[1] | w[2];
}

/* PG(2,q): point indices and the line table; every count is verified (q+1 lines through each point, q other points on each) */
static int fp_setup(void) {
    int q3 = q * q * q; NPTS = q * q + q + 1; ZEROP = NPTS;
    PTIDX = malloc((size_t)q3 * sizeof(uint16_t));
    uint8_t (*ptv)[3] = malloc((size_t)NPTS * 3);
    int *idx_of_norm = malloc((size_t)q3 * sizeof(int));
    for (int c = 0; c < q3; c++) idx_of_norm[c] = -1;
    int np = 0;
    for (int code = 0; code < q3; code++) {            /* normalized vectors: first nonzero coordinate 1 */
        int v[3] = {code / (q * q), (code / q) % q, code % q};
        int j = 0; while (j < 3 && !v[j]) j++;
        if (j < 3 && v[j] == 1) { idx_of_norm[code] = np; for (int i = 0; i < 3; i++) ptv[np][i] = (uint8_t)v[i]; np++; }
    }
    if (np != NPTS) return 0;
    for (int code = 0; code < q3; code++) {
        int v[3] = {code / (q * q), (code / q) % q, code % q};
        int j = 0; while (j < 3 && !v[j]) j++;
        if (j == 3) { PTIDX[code] = (uint16_t)ZEROP; continue; }
        uint8_t iv = INV[v[j]]; int w = 0;
        for (int i = 0; i < 3; i++) w = w * q + MUL[iv][v[i]];
        if (idx_of_norm[w] < 0) return 0;
        PTIDX[code] = (uint16_t)idx_of_norm[w];
    }
    size_t L = (size_t)(NPTS + 1) * (NPTS + 1) + 8;        /* slack: the AVX2 gather reads 4 bytes at every id */
    LINE = malloc(L); memset(LINE, WILDC, L);
    int *map = malloc((size_t)NPTS * sizeof(int));
    int *ptsOnLine = calloc((size_t)(q + 1), sizeof(int));
    for (int P = 0; P < NPTS; P++) {
        for (int l = 0; l < NPTS; l++) map[l] = -1;
        for (int z = 0; z <= q; z++) ptsOnLine[z] = 0;
        int cnt = 0;
        for (int Q = 0; Q < NPTS; Q++) {
            if (Q == P) continue;
            int l; if (!cross_norm_idx(ptv[P], ptv[Q], &l)) return 0;   /* distinct points: nonzero cross product */
            if (map[l] < 0) { if (cnt > q) return 0; map[l] = cnt++; }
            LN(P)[Q] = (uint8_t)map[l]; ptsOnLine[map[l]]++;
        }
        if (cnt != q + 1) return 0;
        for (int z = 0; z <= q; z++) if (ptsOnLine[z] != q) return 0;
    }
    free(map); free(ptsOnLine); free(idx_of_norm); free(ptv);
    VT = malloc((size_t)(nP > 0 ? nP : 1) * t * k);
    for (int i = 0; i < nP; i++) for (int c = 0; c < k; c++) for (int j = 0; j < t; j++) VT[((size_t)i * t + j) * k + c] = VEC(Prow[i], c)[j];
    int mx = t * (q - 1) * (q - 1) + 1;
    MODQ = malloc((size_t)mx);
    for (int x = 0; x < mx; x++) MODQ[x] = (uint8_t)(x % q);
    return 1;
}

/* one pair against the live rows depth..nlive-1: fails iff in every row WILD or equal classes */
static void fpair_rest(Ctx *X, int depth, int x, int y) {
    Fp *F = X->F;
    for (int d = depth; d < F->nlive; d++) {
        int cx = F->Lrow[d][F->ptrow[d][x]], cy = F->Lrow[d][F->ptrow[d][y]];
        if (cx == WILDC || cy == WILDC) { X->wildcls++; continue; }
        if (cx != cy) { X->elimpairs++; return; }
    }
    X->outpairs++;
    emit_pair(X, x, y);
}

/* Hash join over the first j live rows for the pairs {x < y} of the columns p < x < y < k (index i = c - p - 1).
 * A column WILD in none of the j rows gets the key (class_1, ..., class_j) in radix q+1; two such
 * columns agree in all j rows iff their keys are equal, so the pairs of two such columns that fail
 * the j rows are exactly the pairs inside a key group (found by chains tab/nxt: from every column, all
 * earlier columns with its key), and the other such pairs are ruled out (counted from the group sizes).
 * A column WILD in a subset S of the j rows (key -1, never inserted) fails with a non-WILD column iff
 * their classes agree outside S: those partners are found by probing the (q+1)^|S| keys compatible
 * with it, and the non-WILD columns not found are ruled out. A pair of two WILD columns goes
 * through the row-by-row rule fpair_rest(0). So every pair is decided exactly once: (non-WILD,
 * non-WILD) by the chains, (WILD, non-WILD) by the probes, (WILD, WILD) pair by pair. A pair passing
 * the j rows continues row by row from row j, or is a failing pair when no live row is left. */
/* survivors of the j rows: the pair (c0 + l, c0 + i) for every l in the chain starting at prev */
static __attribute__((noinline)) void fjoin_chain(Ctx *X, int j, int last, const int *nxt, int prev, int i, int c0, u128 *found) {
    for (int l = prev; l >= 0; l = nxt[l]) {
        (*found)++;
        if (last) { X->outpairs++; emit_pair(X, c0 + l, c0 + i); }
        else fpair_rest(X, j, c0 + l, c0 + i);
    }
}

/* pass A: key of every column, -1 if WILD in one of the j rows */
static inline __attribute__((always_inline)) void fjoin_keys(const int j, const uint16_t *P0, const uint16_t *P1, const uint16_t *P2,
                                                            const uint8_t *L0, const uint8_t *L1, const uint8_t *L2, int m, int R, int *key) {
    const int W = WILDC, R2 = R * R;
    int i = 0;
#if defined(__AVX2__) && !defined(NO_AVX2)
    /* eight columns at a time: the point indices are loaded as 16-bit lanes, the line ids gathered as 32-bit words
     * (only the low byte is the id; LINE has at least 3 bytes of slack after every row because NPTS + 1 >= 8) */
    {
        const __m256i vW = _mm256_set1_epi32(W), vR = _mm256_set1_epi32(R), vR2 = _mm256_set1_epi32(R2), m1 = _mm256_set1_epi32(-1), ff = _mm256_set1_epi32(0xff);
        for (; i + 8 <= m; i += 8) {
            __m256i i0 = _mm256_cvtepu16_epi32(_mm_loadu_si128((const __m128i *)(P0 + i)));
            __m256i z0 = _mm256_and_si256(_mm256_i32gather_epi32((const int *)L0, i0, 1), ff);
            __m256i kk = z0, wl = _mm256_cmpeq_epi32(z0, vW);
            if (j > 1) {
                __m256i i1 = _mm256_cvtepu16_epi32(_mm_loadu_si128((const __m128i *)(P1 + i)));
                __m256i z1 = _mm256_and_si256(_mm256_i32gather_epi32((const int *)L1, i1, 1), ff);
                kk = _mm256_add_epi32(kk, _mm256_mullo_epi32(z1, vR)); wl = _mm256_or_si256(wl, _mm256_cmpeq_epi32(z1, vW));
            }
            if (j > 2) {
                __m256i i2 = _mm256_cvtepu16_epi32(_mm_loadu_si128((const __m128i *)(P2 + i)));
                __m256i z2 = _mm256_and_si256(_mm256_i32gather_epi32((const int *)L2, i2, 1), ff);
                kk = _mm256_add_epi32(kk, _mm256_mullo_epi32(z2, vR2)); wl = _mm256_or_si256(wl, _mm256_cmpeq_epi32(z2, vW));
            }
            _mm256_storeu_si256((__m256i *)(key + i), _mm256_blendv_epi8(kk, m1, wl));
        }
    }
#endif
    for (; i < m; i++) {
        int z0 = L0[P0[i]], z1 = j > 1 ? L1[P1[i]] : 0, z2 = j > 2 ? L2[P2[i]] : 0;
        int kk = z0 + R * z1 + R2 * z2;
        int wl = (z0 == W) | (z1 == W) | (z2 == W);
        key[i] = wl ? -1 : kk;
    }
}

static inline __attribute__((always_inline)) void fjoin_impl(Ctx *X, const int j, int p) {
    Fp *F = X->F;
    int m = k - 1 - p, c0 = p + 1, nw = 0;
    int *nxt = F->nxt, *key = F->key, *wlist = F->wlist; uint8_t *wmask = F->wmask, *wz = F->wz;
    const uint8_t *L0 = F->Lrow[0], *L1 = j > 1 ? F->Lrow[1] : L0, *L2 = j > 2 ? F->Lrow[2] : L0;
    const uint16_t *P0 = F->ptrow[0] + c0, *P1 = (j > 1 ? F->ptrow[1] : F->ptrow[0]) + c0, *P2 = (j > 2 ? F->ptrow[2] : F->ptrow[0]) + c0;
    const int R = q + 1;                     /* key radix: digits are classes 0..q; WILD columns are not inserted */
    fjoin_keys(j, P0, P1, P2, L0, L1, L2, m, R, key);
    uint32_t st = ++F->cur_stamp & 0xffffu;
    if (st == 0) { memset(F->tab, 0, F->nkeys * sizeof(uint32_t)); st = F->cur_stamp = 1; }
    uint32_t *tab = F->tab, sthi = st << 16;
    int last = j >= F->nlive;                 /* no live row after the j rows */
    u128 found = 0;
    /* pass B: chains of equal keys; a pair is found when its later column is inserted; WILD columns are listed */
    for (int i = 0; i < m; i++) {
        int kk = key[i];
        if (kk < 0) {
            int z0 = L0[P0[i]], z1 = j > 1 ? L1[P1[i]] : 0, z2 = j > 2 ? L2[P2[i]] : 0;
            wlist[nw] = i; wmask[nw] = (uint8_t)((z0 == WILDC) | (z1 == WILDC) << 1 | (z2 == WILDC) << 2);
            wz[3 * nw] = (uint8_t)z0; wz[3 * nw + 1] = (uint8_t)z1; wz[3 * nw + 2] = (uint8_t)z2; nw++; nxt[i] = -2;
            continue;
        }
        uint32_t v = tab[kk];
        int prev = (v >> 16) == st ? (int)(v & 0xffffu) : -1;
        nxt[i] = prev;
        tab[kk] = sthi | (uint32_t)i;
        if (prev >= 0) fjoin_chain(X, j, last, nxt, prev, i, c0, &found);
    }
    u128 mnw = (u128)(m - nw);
    X->elimpairs += mnw * (mnw - 1) / 2 - found;
    for (int w = 0; w < nw; w++) {
        int iw = wlist[w], mk = wmask[w];
        int lo[3], hi[3];
        for (int d = 0; d < 3; d++) { if (d < j && (mk >> d & 1)) { lo[d] = 0; hi[d] = q; } else { lo[d] = hi[d] = (d < j) ? wz[3 * w + d] : 0; } }
        X->wildcls += (mk & 1) + (mk >> 1 & 1) + (mk >> 2 & 1);
        u128 fw = 0;
        for (int d2 = lo[2]; d2 <= hi[2]; d2++) for (int d1 = lo[1]; d1 <= hi[1]; d1++) for (int d0 = lo[0]; d0 <= hi[0]; d0++) {
            uint32_t v = tab[d0 + R * d1 + R * R * d2];
            if ((v >> 16) != st) continue;
            fjoin_chain(X, j, last, nxt, (int)(v & 0xffffu), iw, c0, &fw);
        }
        X->elimpairs += mnw - fw;
        for (int w2 = w + 1; w2 < nw; w2++) fpair_rest(X, 0, c0 + iw, c0 + wlist[w2]);
    }
}
static __attribute__((noinline)) void fjoin1(Ctx *X, int p) { fjoin_impl(X, 1, p); }
static __attribute__((noinline)) void fjoin2(Ctx *X, int p) { fjoin_impl(X, 2, p); }
static __attribute__((noinline)) void fjoin3(Ctx *X, int p) { fjoin_impl(X, 3, p); }

/* P' = pp[0..npp-1] (0 in it for npp > 0): point indices of every column after last(P') in every P row */
static void fp_process_prime(Ctx *X, const int *pp, int npp) {
    Fp *F = X->F;
    F->npp = npp; if (npp) memcpy(F->pp, pp, (size_t)npp * sizeof(int)); F->last = npp ? pp[npp - 1] : -1; F->ready = 1;
    F->nliveP = 0;
    int last = F->last;
    for (int i = 0; i < nP; i++) {
        int r = Prow[i];
        const uint8_t *vs[MAXT]; for (int j = 0; j < npp; j++) vs[j] = VEC(r, pp[j]);
        uint8_t Hb[MAXT][MAXT]; int rk = annihilator(vs, npp, Hb);
        if (rk < npp) { X->wildrows += k - 1 - last; continue; }          /* every t-set containing P' fails in r */
        int d = F->nliveP++; F->liveP[d] = r;
        uint16_t *pr = F->pt + (size_t)d * k;
        if (e == 1) {
            /* prime q: integer dot products on the transposed layout (vectorizable), reduction by table */
            int m = k - 1 - last;
            int16_t *a0 = F->acc, *a1 = F->acc + k, *a2 = F->acc + 2 * k;
            memset(a0, 0, (size_t)m * 2); memset(a1, 0, (size_t)m * 2); memset(a2, 0, (size_t)m * 2);
            for (int j = 0; j < t; j++) {
                const uint8_t *vj = VT + ((size_t)i * t + j) * k + last + 1;
                int16_t h0 = Hb[0][j], h1 = Hb[1][j], h2 = Hb[2][j];
                for (int c = 0; c < m; c++) { int16_t v = vj[c]; a0[c] += h0 * v; a1[c] += h1 * v; a2[c] += h2 * v; }
            }
            for (int c = 0; c < m; c++) pr[last + 1 + c] = PTIDX[(MODQ[a0[c]] * q + MODQ[a1[c]]) * q + MODQ[a2[c]]];
        } else for (int c = last + 1; c < k; c++) {
            const uint8_t *u = VEC(r, c);
            int a = fdot(Hb[0], u), b = fdot(Hb[1], u), cc = fdot(Hb[2], u);
            pr[c] = PTIDX[(a * q + b) * q + cc];
        }
    }
}

/* one extension p of P': every pair {x < y} with p < x */
static void fp_process_p(Ctx *X, int p) {
    Fp *F = X->F;
    X->prefixes++;
    int m = k - 1 - p;
    X->cand += (u128)m;
    memcpy(X->pre, F->pp, (size_t)F->npp * sizeof(int)); X->pre[F->npp] = p; X->npre = F->npp + 1;
    F->nlive = 0;
    for (int d = 0; d < F->nliveP; d++) {
        const uint16_t *pr = F->pt + (size_t)d * k;
        if (pr[p] == ZEROP) { X->wildrows++; continue; }                 /* P dependent in this row: wildcard row */
        F->ptrow[F->nlive] = pr; F->Lrow[F->nlive] = LN(pr[p]); F->nlive++;
    }
    if (m < 2) return;
    if (F->nlive == 0) {                                                  /* every pair fails every live row */
        X->outpairs += (u128)m * (u128)(m - 1) / 2;
        for (int x = p + 1; x < k; x++) for (int y = x + 1; y < k; y++) emit_pair(X, x, y);
        return;
    }
    if ((long long)m * (m - 1) / 2 <= SMALLPAIRS) {
        for (int x = p + 1; x < k; x++) for (int y = x + 1; y < k; y++) fpair_rest(X, 0, x, y);
        return;
    }
    int j = m > JOIN_J3 ? 3 : m > JOIN_J2 ? 2 : 1;
    if (j > F->nlive) j = F->nlive;
    if (j == 3) fjoin3(X, p); else if (j == 2) fjoin2(X, p); else fjoin1(X, p);
}

static void fp_alloc(Ctx *X) {
    Fp *F = calloc(1, sizeof(Fp)); X->F = F;
    F->pt = malloc((size_t)(nP > 0 ? nP : 1) * k * sizeof(uint16_t));
    F->nkeys = (size_t)(q + 1) * (q + 1) * (q + 1);
    F->tab = calloc(F->nkeys, sizeof(uint32_t));
    F->nxt = malloc((size_t)(k + 1) * sizeof(int)); F->key = malloc((size_t)(k + 1) * sizeof(int));
    F->wlist = malloc((size_t)(k + 1) * sizeof(int)); F->wmask = malloc((size_t)(k + 1)); F->wz = malloc((size_t)3 * (k + 1));
    F->acc = malloc((size_t)3 * k * sizeof(int16_t));
    if (!F->acc || !F->pt || !F->tab || !F->nxt || !F->key || !F->wlist || !F->wmask || !F->wz) { fprintf(stderr, "out of memory\n"); exit(2); }
}

/* enumerate P' = {0, p1, ...} (t-3 columns) with the given p1, then every extension p */
static void fp_enum_prime(Ctx *X, int *pp, int fixed, int npp) {
    int r = npp - fixed;
    if (r == 0) {
        fp_process_prime(X, pp, npp);
        for (int p = X->F->last + 1; p < k; p++) fp_process_p(X, p);
        return;
    }
    int lo = pp[fixed - 1] + 1;
    if (lo + r > k) return;
    for (int i = 0; i < r; i++) pp[fixed + i] = lo + i;
    while (1) {
        fp_process_prime(X, pp, npp);
        for (int p = X->F->last + 1; p < k; p++) fp_process_p(X, p);
        int i = r - 1;
        while (i >= 0 && pp[fixed + i] == k - r + i) i--;
        if (i < 0) break;
        pp[fixed + i]++; for (int j = i + 1; j < r; j++) pp[fixed + j] = pp[fixed + j - 1] + 1;
    }
}

static int run_hash_mode(int threads, const int *must, int nmust, int affine) {
    (void)threads;
    uint8_t Am[MAXT][MAXT]; char why[160];
    int nd = 0;
    nP = nO = nL = 0;
    for (int r = 0; r < n; r++) {
        int st = classify_row(r, Am, why, sizeof why);
        if (st == 0) { nd++; printf("row %d: %s\n", r, why); continue; }
        Lrow[nL++] = r;
        if (!g_prog) continue;
        if (st == 1) {
            Prow[nP++] = r;
            printf("row %d: progression, A =", r);
            for (int i = 0; i < t; i++) { printf(i ? " ;" : " ["); for (int j = 0; j < t; j++) printf(" %d", Am[i][j]); }
            printf(" ] (rows of A, field element codes; u_c = A u_(c-1) checked for c = 1..%d)\n", k - 1);
        } else { Orow[nO++] = r; printf("row %d: %s\n", r, why); }
    }
    if (g_prog) {
        printf("progression rows %d, other rows %d, dead rows %d\n", nP, nO, nd);
        for (int i = 0; i < nmust; i++) {
            int ok = 0; for (int j = 0; j < nP; j++) if (Prow[j] == must[i]) ok = 1;
            if (!ok) { printf("PROGRESSION NOT CERTIFIED: row %d is not a progression row\n", must[i]); return 3; }
        }
    } else printf("rows used %d, dead rows dropped %d\n", nL, nd);

    int nth = 1;
#ifdef _OPENMP
    nth = omp_get_max_threads();
#endif
    ctxs = calloc((size_t)nth, sizeof(Ctx));
    for (int i = 0; i < nth; i++) {
        ctxs[i].cap = (size_t)(3 * (n + 1) + 2) * (size_t)(k + 1);
        ctxs[i].pool = malloc(ctxs[i].cap * sizeof(int));
        ctxs[i].rep = malloc((size_t)REPCAP * t * sizeof(int));
        if (!ctxs[i].pool || !ctxs[i].rep) { fprintf(stderr, "out of memory\n"); return 2; }
    }
    u128 exp_pre, exp_cand, exp_pairs;
    /* shard domains (see "shards" above): the outer index, and per index the prefixes, candidate columns and
       pairs it stands for, as binomials; unsharded, their sums are the totals below */
    int dlo = 0, dhi = 1, dw = -1, single = 1;
    if (g_prog && t >= 4) { dlo = 1; dhi = k; dw = t - 3; single = 0; }
    if (!g_prog && t >= 3) { dlo = 0; dhi = k; dw = t - 2; single = 0; }
    if (!shard_setup(dlo, dhi, dw)) { fprintf(stderr, "out of memory\n"); return 2; }
    if (g_fast && t >= 3) {
        if (k > 65535) { fprintf(stderr, "fastprog: k must be at most 65535\n"); return 2; }
        if (!fp_setup()) { printf("INTERNAL CHECK FAILED: PG(2,%d) tables\n", q); return 4; }
        for (int i = 0; i < nth; i++) fp_alloc(&ctxs[i]);
        exp_pre = exp_cand = exp_pairs = 0;
        if (t == 3) {
            g_inner_par = 1;
            if (owned(0)) {
            fp_process_prime(&ctxs[0], NULL, 0);
            fp_process_p(&ctxs[0], 0);
            flush_reps(&ctxs[0]);
            }
            exp_pre = 1; exp_cand = (u128)(k - 1); exp_pairs = binom(k - 1, 2);
        } else if (t == 4) {
            g_inner_par = 0;
            int pp0[1] = {0};
            #pragma omp parallel for schedule(dynamic, 64)
            for (int p = 1; p < k; p++) {
                if (!owned(p)) continue;
                Ctx *X = &ctxs[ctx_tid()];
                if (!X->F->ready) fp_process_prime(X, pp0, 1);
                fp_process_p(X, p);
            }
            for (int i = 0; i < nth; i++) flush_reps(&ctxs[i]);
            for (int p = 1; p < k; p++) { exp_pre += 1; exp_cand += (u128)(k - 1 - p); exp_pairs += binom(k - 1 - p, 2); }
        } else {
            g_inner_par = 0;
            #pragma omp parallel for schedule(dynamic, 1)
            for (int p1 = 1; p1 < k; p1++) {
                if (!owned(p1)) continue;
                Ctx *X = &ctxs[ctx_tid()];
                int pp[MAXT]; pp[0] = 0; pp[1] = p1;
                fp_enum_prime(X, pp, 2, t - 3);
                flush_reps(X);
            }
            for (int p1 = 1; p1 < k; p1++) { exp_pre += binom(k - 1 - p1, t - 4); exp_cand += binom(k - 1 - p1, t - 3); exp_pairs += binom(k - 1 - p1, t - 2); }
        }
        /* the sums over all outer indices must be the binomials (a check of the per-index counts that the
           shards use); a shard's own share is computed from its indices below */
        if ((exp_pre != binom(k - 1, t - 3) || exp_cand != binom(k - 1, t - 2) || exp_pairs != binom(k - 1, t - 1))) {
            printf("INTERNAL CHECK FAILED: expected totals\n"); return 4;
        }
    } else if (g_prog) {
        if (t == 2) {
            Ctx *X = &ctxs[0];
            if (owned(0)) {
            X->prefixes = 1; X->cand = (u128)(k - 1);
            for (int y = 1; y < k; y++) {
                int D[2] = {0, y}, fails = 1;
                for (int i = 0; i < nP && fails; i++) if (set_rank(Prow[i], D) == t) fails = 0;
                if (fails) { X->outpairs++; memcpy(X->rep + X->nrep * t, D, sizeof D); if (++X->nrep == REPCAP) flush_reps(X); }
                else X->elimpairs++;
            }
            g_inner_par = 1; flush_reps(X);
            }
            exp_pre = 1; exp_cand = (u128)(k - 1); exp_pairs = (u128)(k - 1);
        } else if (t == 3) {
            int pre[MAXT] = {0};
            g_inner_par = 1;
            if (owned(0)) {
            process_prefix(&ctxs[0], pre, 1, Prow, nP);
            flush_reps(&ctxs[0]);
            }
            exp_pre = binom(k - 1, 0); exp_cand = binom(k - 1, 1); exp_pairs = binom(k - 1, 2);
        } else {
            g_inner_par = 0;
            #pragma omp parallel for schedule(dynamic, 1)
            for (int j = 1; j < k; j++) {
                if (!owned(j)) continue;
                Ctx *X = &ctxs[ctx_tid()];
                int pre[MAXT]; pre[0] = 0; pre[1] = j;
                enum_prefixes(X, pre, 2, t - 2, Prow, nP);
                flush_reps(X);
            }
            exp_pre = binom(k - 1, t - 3); exp_cand = binom(k - 1, t - 2); exp_pairs = binom(k - 1, t - 1);
        }
    } else {
        if (t == 2) {
            int pre[MAXT];
            if (owned(0)) process_prefix(&ctxs[0], pre, 0, Lrow, nL);
        } else {
            #pragma omp parallel for schedule(dynamic, 1)
            for (int i = 0; i < k; i++) {
                if (!owned(i)) continue;
                Ctx *X = &ctxs[ctx_tid()];
                int pre[MAXT]; pre[0] = i;
                enum_prefixes(X, pre, 1, t - 2, Lrow, nL);
            }
        }
        exp_pre = binom(k, t - 2); exp_cand = binom(k, t - 1); exp_pairs = binom(k, t);
    }
    u128 tot_pre = exp_pre, tot_cand = exp_cand, tot_pairs = exp_pairs;
    if (g_shm) {                          /* this shard's share: the binomials of its own indices */
        exp_pre = exp_cand = exp_pairs = 0;
        if (single) { if (owned(0)) { exp_pre = tot_pre; exp_cand = tot_cand; exp_pairs = tot_pairs; } }
        else for (int j = dlo; j < dhi; j++) if (owned(j)) {
            int a = k - 1 - j;
            if (g_prog) { exp_pre += binom(a, t - 4); exp_cand += binom(a, t - 3); exp_pairs += binom(a, t - 2); }
            else { exp_pre += binom(a, t - 3); exp_cand += binom(a, t - 2); exp_pairs += binom(a, t - 1); }
        }
        shard_banner(single ? "a single outer index" : g_prog ? "second column of the representative" : "first prefix column");
    }
    /* totals */
    long long prefixes = 0, wildrows = 0, wildcls = 0, bad = 0;
    u128 cand = 0, outp = 0, elim = 0, reps = 0, shifts = 0, unc = 0; int have = 0, best[MAXT];
    for (int i = 0; i < nth; i++) {
        Ctx *X = &ctxs[i];
        prefixes += X->prefixes; wildrows += X->wildrows; wildcls += X->wildcls; bad += X->bad_recheck;
        cand += X->cand; outp += X->outpairs; elim += X->elimpairs; reps += X->reps; shifts += X->shifts; unc += X->unc;
        if (X->have_min) {
            int less = !have;
            if (!less) for (int j = 0; j < t; j++) if (X->minset[j] != best[j]) { less = X->minset[j] < best[j]; break; }
            if (less) { have = 1; memcpy(best, X->minset, t * sizeof(int)); }
        }
    }
    char b1[64], b2[64], b3[64], b4[64], b5[64], b6[64], b7[64];
    u128_str(cand, b1); u128_str(exp_cand, b2); u128_str(outp, b3); u128_str(elim, b4); u128_str(outp + elim, b5); u128_str(exp_pairs, b6); u128_str(exp_pre, b7);
    printf("enumeration: prefixes %lld (expected %s), candidate columns %s (expected %s), wildcard (prefix,row) %lld, WILD classifications %lld\n",
           prefixes, b7, b1, b2, wildrows, wildcls);
    printf("completeness: pairs failing every %s row %s + pairs ruled out %s = %s (expected %s)\n",
           g_prog ? "progression" : "used", b3, b4, b5, b6);
    int consistent = (u128)prefixes == exp_pre && cand == exp_cand && outp + elim == exp_pairs && bad == 0 && (!g_prog || reps == outp);
    if (g_prog) { u128_str(reps, b1); u128_str(shifts, b2); printf("representatives failing every progression row %s, shifts tested in other rows %s\n", b1, b2); }
    if (!consistent) {
        printf("INTERNAL CHECK FAILED: enumeration counts do not match the binomials, or %lld sets failed the exact recheck\n", bad);
        return 4;
    }
    if (g_shm) {
        u128_str(outp + elim, b1); u128_str(cand, b2); u128_str(unc, b3); u128_str(reps, b4); u128_str(shifts, b5);
        printf("SHARD i=%d m=%d mode=%s units=%s prefixes=%lld candidates=%s uncovered=%s reps=%s shifts=%s listed=%lld\n",
               g_shi, g_shm, g_fast ? "fastprog" : g_prog ? "progression" : "fullfast", b1, prefixes, b2, b3, b4, b5, g_listed);
        u128_str(tot_pairs, b1); u128_str(tot_pre, b2); u128_str(tot_cand, b3);
        printf("SHARD totals of the unsharded run: units=%s prefixes=%s candidates=%s\n", b1, b2, b3);
        if (unc) { printf("first uncovered:"); for (int i = 0; i < t; i++) printf(" %d", best[i]); printf("\n"); }
        return unc ? 1 : 0;
    }
    u128_str(binom(k, t), b1); u128_str(unc, b2);
    printf("checked %s t-sets%s, uncovered %s\n", b1, g_prog ? " (all, by translation from the representatives)" : "", b2);
    if (unc) { printf("first uncovered:"); for (int i = 0; i < t; i++) printf(" %d", best[i]); printf("\n"); }
    else {
        long long Q = 1; for (int i = 0; i < t; i++) Q *= q;
        printf("RESULT: CPHF(%d; %d, %d, %d) - gives CA(%lld; %d, %d, %d)", n, k, q, t, (long long)n * (Q - 1) + 1, t, k, q);
        if (affine) printf(" and, affine, CA(%lld; %d, %d, %d)", (long long)n * (Q - q) + q, t, k, q);
        printf("\n");
    }
    return unc ? 1 : 0;
}

/* ---------- estimate and auto ----------
 * Unit costs in ns on one core, fitted to timed runs of real and synthetic families (tools/cphf/README.md,
 * "Unit costs", 2026-11-02; the same formulas as unit_ns() in tools/cphf_cert.py). They depend on n, q, k and t
 * as the measurements showed. They are a planning aid only: the choice of method changes how long an exact
 * check takes, never its answer. */
static double unit_ns(const char *mode) {
    double tt = t, kq = (double)k / ((double)q * q);
    if (!strcmp(mode, "full") || !strcmp(mode, "cyclic")) return 0.15 * n * tt * tt;   /* per t-set */
    if (!strcmp(mode, "fullfast")) return n * (11.0 + 28.0 / q);                       /* per C(k, t-1) */
    if (!strcmp(mode, "progression")) return 10.5 * (tt - 3) * (tt - 3) + 4.6 * kq;    /* per C(k-1, t-2) */
    if (!strcmp(mode, "fastprog")) return 0.8 * (tt - 3) * (tt - 3) + 1.1 * kq;        /* per C(k-1, t-2) */
    return 140.0;                                         /* "shift": one shift tested in the other rows */
}
#define EST_SAMPLES 20000         /* random t-sets per progression row for its failure rate (fixed seed) */

static double u2d(u128 x) { return (double)x; }

/* smallest s, 1 <= s < k, s | k, for which col -> col + s is a certified symmetry of every row; 0 if none */
static int find_symmetry(void) {
    int found = 0; g_quiet = 1;
    for (int s = 1; s < k && !found; s++) if (k % s == 0 && certify_cyclic(s)) found = s;
    g_quiet = 0;
    return found;
}

static u128 cyclic_reps(int s) {      /* t-sets with smallest column < s */
    u128 r = 0; for (int c0 = 0; c0 < s && c0 < k; c0++) r += binom(k - 1 - c0, t - 1);
    return r;
}

/* prints the estimate; returns the cheapest method in *best ("full", "fullfast", "progression", "fastprog",
 * "cyclic") with *best_s the shift for cyclic. Ties go to the earlier of cyclic, fastprog, progression, fullfast,
 * full. fastprog is listed when there are progression rows, t >= 3 and k <= 65535; it has the units and the shift
 * tests of progression at a lower cost per unit, so auto chooses it over progression whenever it applies. */
static void estimate(int threads, char *best, int *best_s) {
    uint8_t Am[MAXT][MAXT]; char why[160]; int np = 0, no = 0, nd = 0, prow[64];
    for (int r = 0; r < n; r++) {
        int st = classify_row(r, Am, why, sizeof why);
        if (st == 0) nd++; else if (st == 1) prow[np++] = r; else no++;
    }
    printf("rows: progression %d, other %d, dead %d\n", np, no, nd);
    int s = find_symmetry();
    if (s) printf("symmetry: col -> col+%d certified for all %d rows\n", s, n);
    else printf("symmetry: none (no s < k dividing k with col -> col+s certified in every row)\n");
    char b1[64]; double cs, bestcs = -1; strcpy(best, "full"); *best_s = 0;
    if (s) {
        u128 u = cyclic_reps(s); cs = u2d(u) * unit_ns("cyclic") * 1e-9; u128_str(u, b1);
        printf("estimate cyclic %d units=%s unit_ns=%.0f core_seconds=%.4g\n", s, b1, unit_ns("cyclic"), cs);
        bestcs = cs; strcpy(best, "cyclic"); *best_s = s;
    }
    if (np) {
        /* shift tests = t-sets failing in every progression row; their share is estimated as the product of the
           measured failure rates of the rows (independence assumed; a row with no failure in the sample counts
           as 0.5 / EST_SAMPLES) */
        double frac = 1;
        unsigned long long x = 0x9E3779B97F4A7C15ULL;
        for (int i = 0; i < np; i++) {
            long long fails = 0;
            for (int it = 0; it < EST_SAMPLES; it++) {
                int c[MAXT], m = 0;
                while (m < t) { x ^= x << 13; x ^= x >> 7; x ^= x << 17; int y = (int)(x % (unsigned long long)k), dup = 0; for (int j = 0; j < m; j++) if (c[j] == y) dup = 1; if (!dup) c[m++] = y; }
                if (set_rank(prow[i], c) < t) fails++;
            }
            frac *= fails ? (double)fails / EST_SAMPLES : 0.5 / EST_SAMPLES;
        }
        u128 u = binom(k - 1, t - 2); double sh = frac * u2d(binom(k, t));
        u128_str(u, b1);
        if (t >= 3 && k <= 65535) {
            cs = u2d(u) * unit_ns("fastprog") * 1e-9 + sh * unit_ns("shift") * 1e-9;
            printf("estimate fastprog units=%s unit_ns=%.1f shift_tests=%.4g shift_ns=%.0f core_seconds=%.4g\n", b1, unit_ns("fastprog"), sh, unit_ns("shift"), cs);
            if (bestcs < 0 || cs < bestcs) { bestcs = cs; strcpy(best, "fastprog"); }
        } else printf("estimate fastprog not applicable (%s)\n", t < 3 ? "t = 2: mode progression's code" : "k above 65535");
        cs = u2d(u) * unit_ns("progression") * 1e-9 + sh * unit_ns("shift") * 1e-9;
        printf("estimate progression units=%s unit_ns=%.0f shift_tests=%.4g shift_ns=%.0f core_seconds=%.4g\n", b1, unit_ns("progression"), sh, unit_ns("shift"), cs);
        if (bestcs < 0 || cs < bestcs) { bestcs = cs; strcpy(best, "progression"); }
    } else printf("estimate fastprog not applicable (no progression rows)\nestimate progression not applicable (no progression rows)\n");
    {
        u128 u = binom(k, t - 1); cs = u2d(u) * unit_ns("fullfast") * 1e-9; u128_str(u, b1);
        printf("estimate fullfast units=%s unit_ns=%.0f core_seconds=%.4g\n", b1, unit_ns("fullfast"), cs);
        if (bestcs < 0 || cs < bestcs) { bestcs = cs; strcpy(best, "fullfast"); }
    }
    {
        u128 u = binom(k, t); cs = u2d(u) * unit_ns("full") * 1e-9; u128_str(u, b1);
        printf("estimate full units=%s unit_ns=%.0f core_seconds=%.4g\n", b1, unit_ns("full"), cs);
        if (bestcs < 0 || cs < bestcs) { bestcs = cs; strcpy(best, "full"); }
    }
    int th = threads;
#ifdef _OPENMP
    if (th <= 0) th = omp_get_max_threads();
#endif
    if (th <= 0) th = 1;
    if (!strcmp(best, "cyclic")) printf("cheapest: cyclic %d core_seconds=%.4g wall_seconds=%.4g threads=%d\n", *best_s, bestcs, bestcs / th, th);
    else printf("cheapest: %s core_seconds=%.4g wall_seconds=%.4g threads=%d\n", best, bestcs, bestcs / th, th);
}

/* mode full and cyclic in a shard: every uncovered t-set is listed and the smallest kept */
static long long g_fmin[MAXT]; static int g_fhave;
static void record_full(const int *S) {
    #pragma omp critical(cphf_list)
    {
        int less = !g_fhave;
        if (!less) for (int i = 0; i < t; i++) if (S[i] != g_fmin[i]) { less = S[i] < g_fmin[i]; break; }
        if (less) { g_fhave = 1; for (int i = 0; i < t; i++) g_fmin[i] = S[i]; }
        if (g_listcap < 0 || g_listed < g_listcap) { g_listed++; printf("U"); for (int i = 0; i < t; i++) printf(" %d", S[i]); printf("\n"); }
    }
}

/* the covering array, written with a buffer (the bytes of the earlier fprintf version, one per entry) */
static int expand_array(const char *path, int aff) {
    FILE *o = fopen(path, "w"); if (!o) { perror(path); return 2; }
    char num[32][4]; int nlen[32];
    for (int x = 0; x < q; x++) nlen[x] = snprintf(num[x], sizeof num[x], "%d", x);
    size_t cap = (size_t)1 << 20; if (cap < (size_t)4 * k + 16) cap = (size_t)4 * k + 16;
    char *buf = malloc(cap); uint8_t *part = malloc((size_t)k), *last = malloc((size_t)k);
    if (!buf || !part || !last) { fprintf(stderr, "out of memory\n"); return 2; }
    size_t bl = 0;
#define EXP_FLUSH() do { if (bl && fwrite(buf, 1, bl, o) != bl) { perror(path); return 2; } bl = 0; } while (0)
#define EXP_ROOM() do { if (bl + (size_t)4 * k + 2 > cap) EXP_FLUSH(); } while (0)
    long long Q = 1; for (int j = 0; j < t; j++) Q *= q;
    long long N = 1;
    EXP_ROOM();
    for (int c = 0; c < k; c++) { if (c) buf[bl++] = ' '; buf[bl++] = '0'; }
    buf[bl++] = '\n';
    for (int r = 0; r < n; r++) {
        for (int c = 0; c < k; c++) last[c] = VEC(r, c)[t - 1];
        for (long long hi = 0; hi < Q / q; hi++) {
            /* beta = (digits of hi, d), most significant first: part[c] = sum over the first t-1 digits */
            uint8_t beta[MAXT]; long long bb = hi; for (int j = t - 2; j >= 0; j--) { beta[j] = (uint8_t)(bb % q); bb /= q; }
            int rest = 0; for (int j = 1; j < t - 1; j++) rest |= beta[j];
            for (int c = 0; c < k; c++) { const uint8_t *v = VEC(r, c); uint8_t sum = 0; for (int j = 0; j < t - 1; j++) sum = ADD[sum][MUL[beta[j]][v[j]]]; part[c] = sum; }
            for (int d = 0; d < q; d++) {
                if (hi == 0 && d == 0) continue;
                if (aff && !rest && (t == 1 || !d)) continue;      /* beta = (b, 0, ..., 0): constant runs, written at the end */
                EXP_ROOM();
                const uint8_t *md = MUL[d];
                for (int c = 0; c < k; c++) {
                    int x = ADD[part[c]][md[last[c]]];
                    if (c) buf[bl++] = ' ';
                    memcpy(buf + bl, num[x], (size_t)nlen[x]); bl += (size_t)nlen[x];
                }
                buf[bl++] = '\n'; N++;
            }
        }
    }
    if (aff) for (int x = 1; x < q; x++) {
        EXP_ROOM();
        for (int c = 0; c < k; c++) { if (c) buf[bl++] = ' '; memcpy(buf + bl, num[x], (size_t)nlen[x]); bl += (size_t)nlen[x]; }
        buf[bl++] = '\n'; N++;
    }
    EXP_FLUSH();
#undef EXP_FLUSH
#undef EXP_ROOM
    if (fclose(o)) { perror(path); return 2; }
    free(buf); free(part); free(last);
    printf("wrote CA(%lld; %d, %d, %d)%s\n", N, t, k, q, aff ? " (affine)" : "");
    return 0;
}

/* the family in the canonical serialization cphf1 (tools/cphf/README.md) */
static int write_canon(const char *path) {
    FILE *o = fopen(path, "w"); if (!o) { perror(path); return 2; }
    fprintf(o, "cphf1 %d %d %d %d\n", n, k, q, t);
    for (int r = 0; r < n; r++) {
        for (int c = 0; c < k; c++) {
            long long code = 0; const uint8_t *v = VEC(r, c);
            for (int j = 0; j < t; j++) code = code * q + v[j];
            fprintf(o, c ? " %lld" : "%lld", code);
        }
        fputc('\n', o);
    }
    if (fclose(o)) { perror(path); return 2; }
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 5) { fprintf(stderr, "usage: cphfcheck FILE t q full|cyclic s|sample S seed [threads]\n"
                                    "       cphfcheck FILE t q progression [threads] [P=r1,r2,...] | fullfast [threads]\n"); return 2; }
    t = atoi(argv[2]); q = atoi(argv[3]); const char *mode = argv[4];
    if (t < 2 || t > MAXT) { fprintf(stderr, "t must be 2..%d\n", MAXT); return 2; }
    if (!field_setup()) { fprintf(stderr, "q=%d: not a supported prime power (primes, 4, 8, 9, 16, 25, 27, 32)\n", q); return 2; }
    if (!read_file(argv[1])) return 2;
    if (n > 64) { fprintf(stderr, "at most 64 rows\n"); return 2; }
    /* "shard i m" after the other arguments (modes full, cyclic, fullfast, progression, fastprog, auto) */
    if (!strcmp(mode, "full") || !strcmp(mode, "cyclic") || !strcmp(mode, "fullfast") || !strcmp(mode, "progression") || !strcmp(mode, "fastprog") || !strcmp(mode, "auto")) {
        for (int a = 5; a < argc; a++) if (!strcmp(argv[a], "shard")) {
            char *e1, *e2;
            if (a + 3 != argc) { fprintf(stderr, "shard: give \"shard i m\" as the last three arguments\n"); return 2; }
            long i = strtol(argv[a + 1], &e1, 10), m = strtol(argv[a + 2], &e2, 10);
            if (*e1 || *e2 || e1 == argv[a + 1] || e2 == argv[a + 2] || m < 1 || m > 1024 || i < 0 || i >= m) { fprintf(stderr, "shard: need 0 <= i < m <= 1024\n"); return 2; }
            g_shi = (int)i; g_shm = (int)m; argc = a;
            const char *cap = getenv("CPHFCHECK_LISTCAP");
            g_listcap = cap ? atoll(cap) : 10000;
            break;
        }
    }
    int threads = 0, s = 1; long long S = 0; unsigned long long seed = 1;
    int header_done = 0;
    if (!strcmp(mode, "estimate") || !strcmp(mode, "auto")) {
        if (argc > 5) { char *end; long v = strtol(argv[5], &end, 10); if (end == argv[5] || *end || v < 0 || argc > 6) { fprintf(stderr, "bad argument %s\n", argv[5]); return 2; } threads = (int)v; }
#ifdef _OPENMP
        if (threads > 0) omp_set_num_threads(threads);
#endif
        int affine = 1;
        for (int r = 0; r < n && affine; r++) for (int c = 0; c < k; c++) if (VEC(r, c)[0] != 1) { affine = 0; break; }
        printf("CPHF candidate: n=%d k=%d q=%d t=%d mode=%s%s\n", n, k, q, t, mode, affine ? " (affine: first coordinate 1)" : "");
        static char chosen[32]; int cs = 0;
        estimate(threads, chosen, &cs);
        if (!strcmp(mode, "estimate")) return 0;
        header_done = 1;
        if (!strcmp(chosen, "cyclic")) printf("auto: method cyclic %d\n", cs); else printf("auto: method %s\n", chosen);
        mode = chosen; s = cs;
        if (!strcmp(mode, "progression") || !strcmp(mode, "fullfast") || !strcmp(mode, "fastprog")) {
            g_fast = !strcmp(mode, "fastprog");
            g_prog = !strcmp(mode, "progression") || g_fast;
            g_list = getenv("CPHFCHECK_LIST") != NULL || g_shm;
            return run_hash_mode(threads, NULL, 0, affine);
        }
    }
    else if (!strcmp(mode, "cyclic")) { if (argc < 6) return 2; s = atoi(argv[5]); if (argc > 6) threads = atoi(argv[6]); }
    else if (!strcmp(mode, "sample")) { if (argc < 7) return 2; S = atoll(argv[5]); seed = strtoull(argv[6], 0, 10); if (argc > 7) threads = atoi(argv[7]); }
    else if (!strcmp(mode, "full")) { if (argc > 5) threads = atoi(argv[5]); }
    else if (!strcmp(mode, "progression") || !strcmp(mode, "fullfast") || !strcmp(mode, "fastprog")) {
        int must[64], nmust = 0;
        g_fast = !strcmp(mode, "fastprog");
        for (int a = 5; a < argc; a++) {
            if (!strncmp(argv[a], "P=", 2) && (!strcmp(mode, "progression") || g_fast)) {
                char *s2 = argv[a] + 2;
                while (*s2) {
                    char *end; long v = strtol(s2, &end, 10);
                    if (end == s2 || v < 0 || v >= n || nmust >= 64) { fprintf(stderr, "bad row list %s (rows are 0..%d)\n", argv[a], n - 1); return 2; }
                    must[nmust++] = (int)v; s2 = end; if (*s2 == ',') s2++; else if (*s2) { fprintf(stderr, "bad row list %s\n", argv[a]); return 2; }
                }
            } else {
                char *end; long v = strtol(argv[a], &end, 10);
                if (end == argv[a] || *end || v < 0) { fprintf(stderr, "bad argument %s\n", argv[a]); return 2; }
                threads = (int)v;
            }
        }
#ifdef _OPENMP
        if (threads > 0) omp_set_num_threads(threads);
#endif
        g_prog = !strcmp(mode, "progression") || g_fast;
        g_list = getenv("CPHFCHECK_LIST") != NULL || g_shm;
        int affine = 1;
        for (int r = 0; r < n && affine; r++) for (int c = 0; c < k; c++) if (VEC(r, c)[0] != 1) { affine = 0; break; }
        printf("CPHF candidate: n=%d k=%d q=%d t=%d mode=%s%s\n", n, k, q, t, mode, affine ? " (affine: first coordinate 1)" : "");
        return run_hash_mode(threads, must, nmust, affine);
    }
    else if (!strcmp(mode, "expand")) {
        if (argc < 6) return 2;
        int aff = argc > 6 && !strcmp(argv[6], "affine");
        if (aff) for (int r = 0; r < n; r++) for (int c = 0; c < k; c++) if (VEC(r, c)[0] != 1) { fprintf(stderr, "affine: row %d column %d has first coordinate %d\n", r, c, VEC(r, c)[0]); return 2; }
        return expand_array(argv[5], aff);
    }
    else if (!strcmp(mode, "canon")) {
        if (argc < 6) return 2;
        return write_canon(argv[5]);
    }
    else { fprintf(stderr, "unknown mode %s\n", mode); return 2; }
#ifdef _OPENMP
    if (threads > 0) omp_set_num_threads(threads);
#endif
    int affine = 1;
    for (int r = 0; r < n && affine; r++) for (int c = 0; c < k; c++) if (VEC(r, c)[0] != 1) { affine = 0; break; }
    if (!header_done) printf("CPHF candidate: n=%d k=%d q=%d t=%d mode=%s%s\n", n, k, q, t, mode, affine ? " (affine: first coordinate 1)" : "");
    if (!strcmp(mode, "cyclic")) {
        if (!certify_cyclic(s)) { printf("SYMMETRY NOT CERTIFIED\n"); return 3; }
        printf("symmetry col -> col+%d certified for all %d rows\n", s, n);
    }
    long long total = 0, checked = 0;
    if (!strcmp(mode, "sample")) {
        #pragma omp parallel reduction(+:total,checked)
        {
            int tid = 0, nt = 1;
#ifdef _OPENMP
            tid = omp_get_thread_num(); nt = omp_get_num_threads();
#endif
            unsigned long long x = seed * 6364136223846793005ULL + 1442695040888963407ULL * (tid + 1);
            for (long long it = tid; it < S; it += nt) {
                int c[MAXT], m = 0;
                while (m < t) { x ^= x << 13; x ^= x >> 7; x ^= x << 17; int y = (int)(x % (unsigned long long)k), dup = 0; for (int i = 0; i < m; i++) if (c[i] == y) dup = 1; if (!dup) c[m++] = y; }
                for (int i = 1; i < t; i++) for (int j = i; j > 0 && c[j] < c[j - 1]; j--) { int tmp = c[j]; c[j] = c[j - 1]; c[j - 1] = tmp; }
                int pre[MAXT]; for (int i = 0; i < t - 1; i++) pre[i] = c[i];
                long long fb; total += check_prefix(pre, c[t - 1], c[t - 1] + 1, &fb, 0); checked++;
            }
        }
        printf("sampled %lld t-sets, uncovered %lld (a screen, not a proof)\n", checked, total);
        return total ? 1 : 0;
    }
    /* enumerate prefixes c0 < c1 < ... < c_{t-2}; c0 < s in cyclic mode, c0 < k-t+1 otherwise */
    int c0max = !strcmp(mode, "cyclic") ? s : k - t + 1;
    if (!shard_setup(0, c0max, t - 1)) { fprintf(stderr, "out of memory\n"); return 2; }
    long long firstbad_set[MAXT] = {0}; int have_first = 0;
    #pragma omp parallel for schedule(dynamic, 1) reduction(+:total,checked)
    for (int c0 = 0; c0 < c0max; c0++) {
        if (!owned(c0)) continue;
        int pre[MAXT]; pre[0] = c0;
        for (int i = 1; i < t - 1; i++) pre[i] = c0 + i;
        if (t == 2) { long long fb = -1; long long b = check_prefix(pre, c0 + 1, k, &fb, 0); total += b; checked += k - c0 - 1;
            if (b) {
                #pragma omp critical
                { if (!have_first) { have_first = 1; firstbad_set[0] = c0; firstbad_set[1] = fb; } }
                if (g_shm) for (int c = c0 + 1; c < k; c++) { long long f2; if (check_prefix(pre, c, c + 1, &f2, 0)) { int S2[MAXT] = {c0, c}; record_full(S2); } }
            }
            continue; }
        while (1) {
            long long fb = -1;
            long long b = check_prefix(pre, pre[t - 2] + 1, k, &fb, 0);
            total += b; checked += k - pre[t - 2] - 1;
            if (b) {
                #pragma omp critical
                { if (!have_first) { have_first = 1; for (int i = 0; i < t - 1; i++) firstbad_set[i] = pre[i]; firstbad_set[t - 1] = fb; } }
                if (g_shm) for (int c = pre[t - 2] + 1; c < k; c++) {
                    long long f2; if (check_prefix(pre, c, c + 1, &f2, 0)) { int S2[MAXT]; for (int i = 0; i < t - 1; i++) S2[i] = pre[i]; S2[t - 1] = c; record_full(S2); }
                }
            }
            int i = t - 2;
            while (i >= 1 && pre[i] == k - (t - 1 - i) - 1) i--;
            if (i < 1) break;
            pre[i]++; for (int j = i + 1; j < t - 1; j++) pre[j] = pre[j - 1] + 1;
        }
    }
    if (g_shm) {
        u128 want = 0, tot = 0;
        for (int c0 = 0; c0 < c0max; c0++) { u128 w = binom(k - 1 - c0, t - 1); tot += w; if (owned(c0)) want += w; }
        shard_banner("smallest column of the t-set");
        char b1[64], b2[64], b3[64];
        u128_str((u128)checked, b1); u128_str(want, b2); u128_str(tot, b3);
        if ((u128)checked != want) { printf("INTERNAL CHECK FAILED: shard checked %s t-sets, its indices stand for %s\n", b1, b2); return 4; }
        printf("SHARD i=%d m=%d mode=%s units=%s uncovered=%lld listed=%lld\n", g_shi, g_shm, mode, b1, total, g_listed);
        printf("SHARD totals of the unsharded run: units=%s\n", b3);
        if (total) { printf("first uncovered:"); for (int i = 0; i < t; i++) printf(" %lld", g_fmin[i]); printf("\n"); }
        return total ? 1 : 0;
    }
    printf("checked %lld t-sets%s, uncovered %lld\n", checked, !strcmp(mode, "cyclic") ? " (representatives)" : "", total);
    if (total) { printf("first uncovered:"); for (int i = 0; i < t; i++) printf(" %lld", firstbad_set[i]); printf("\n"); }
    else {
        long long Q = 1; for (int i = 0; i < t; i++) Q *= q;
        printf("RESULT: CPHF(%d; %d, %d, %d) - gives CA(%lld; %d, %d, %d)", n, k, q, t, (long long)n * (Q - 1) + 1, t, k, q);
        if (affine) printf(" and, affine, CA(%lld; %d, %d, %d)", (long long)n * (Q - q) + q, t, k, q);
        printf("\n");
    }
    if (!strcmp(mode, "full") && getenv("CPHFCHECK_LIST")) {
        /* testing aid: every uncovered t-set, one per line, by the same engine, one thread */
        int pre[MAXT]; for (int i = 0; i < t - 1; i++) pre[i] = i;
        while (1) {
            for (int c = pre[t - 2] + 1; c < k; c++) {
                long long fb; if (check_prefix(pre, c, c + 1, &fb, 0)) { printf("U"); for (int i = 0; i < t - 1; i++) printf(" %d", pre[i]); printf(" %d\n", c); }
            }
            int i = t - 2;
            while (i >= 0 && pre[i] == (k - 1) - (t - 1 - i)) i--;
            if (i < 0) break;
            pre[i]++; for (int j = i + 1; j < t - 1; j++) pre[j] = pre[j - 1] + 1;
        }
    }
    return total ? 1 : 0;
}
