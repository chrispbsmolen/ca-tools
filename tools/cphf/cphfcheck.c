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
 *   Both new modes print counts that must equal binomials (prefixes, candidate columns, and pairs
 *   failing + pairs ruled out) and recheck every reported set by rank; a mismatch exits 4.
 *   With the environment variable CPHFCHECK_LIST set, modes full, progression and fullfast also print
 *   every uncovered t-set as a line "U c1 ... ct" (a testing aid; order not fixed in the new modes).
 *   In the new modes "first uncovered" is the lexicographically smallest uncovered t-set.
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

#define MAXT 8
static int n, k, t, q, p, e;
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
    if (k % s) { fprintf(stderr, "s=%d does not divide k=%d\n", s, k); return 0; }
    for (int r = 0; r < n; r++) {
        /* choose t independent columns among 0..k-s-1 */
        int sel[MAXT], m = 0; const uint8_t *vs[MAXT];
        for (int c = 0; c < k - s && m < t; c++) { vs[m] = VEC(r, c); if (rank_of(vs, m + 1) == m + 1) { sel[m] = c; m++; } }
        if (m < t) { fprintf(stderr, "row %d: no %d independent columns, symmetry not certified\n", r, t); return 0; }
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
        if (rank_of(rowsA, t) != t) { fprintf(stderr, "row %d: A singular\n", r); return 0; }
        int mu = -1;
        for (int c = 0; c < k; c++) {
            uint8_t img[MAXT]; for (int i = 0; i < t; i++) { uint8_t sum = 0; for (int j = 0; j < t; j++) sum = ADD[sum][MUL[A[i][j]][VEC(r, c)[j]]]; img[i] = sum; }
            const uint8_t *tgt = VEC(r, (c + s) % k);
            if (c < k - s) { if (memcmp(img, tgt, t)) { fprintf(stderr, "row %d col %d: A v != v[c+s]\n", r, c); return 0; } }
            else {
                int jn = -1; for (int j = 0; j < t; j++) if (tgt[j]) { jn = j; break; }
                if (jn < 0 || !img[jn]) { fprintf(stderr, "row %d col %d: wrap fails\n", r, c); return 0; }
                int m2 = MUL[img[jn]][INV[tgt[jn]]];
                if (mu < 0) mu = m2;
                if (m2 != mu) { fprintf(stderr, "row %d: mu not constant\n", r); return 0; }
                for (int j = 0; j < t; j++) if (img[j] != MUL[(uint8_t)mu][tgt[j]]) { fprintf(stderr, "row %d col %d: wrap fails\n", r, c); return 0; }
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
    char pad[64];
} Ctx;

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
        { printf("U"); for (int i = 0; i < t; i++) printf(" %d", S[i]); printf("\n"); }
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
    if (g_prog) {
        if (t == 2) {
            Ctx *X = &ctxs[0]; X->prefixes = 1; X->cand = (u128)(k - 1);
            for (int y = 1; y < k; y++) {
                int D[2] = {0, y}, fails = 1;
                for (int i = 0; i < nP && fails; i++) if (set_rank(Prow[i], D) == t) fails = 0;
                if (fails) { X->outpairs++; memcpy(X->rep + X->nrep * t, D, sizeof D); if (++X->nrep == REPCAP) flush_reps(X); }
                else X->elimpairs++;
            }
            g_inner_par = 1; flush_reps(X);
            exp_pre = 1; exp_cand = (u128)(k - 1); exp_pairs = (u128)(k - 1);
        } else if (t == 3) {
            int pre[MAXT] = {0};
            g_inner_par = 1;
            process_prefix(&ctxs[0], pre, 1, Prow, nP);
            flush_reps(&ctxs[0]);
            exp_pre = binom(k - 1, 0); exp_cand = binom(k - 1, 1); exp_pairs = binom(k - 1, 2);
        } else {
            g_inner_par = 0;
            #pragma omp parallel for schedule(dynamic, 1)
            for (int j = 1; j < k; j++) {
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
            process_prefix(&ctxs[0], pre, 0, Lrow, nL);
        } else {
            #pragma omp parallel for schedule(dynamic, 1)
            for (int i = 0; i < k; i++) {
                Ctx *X = &ctxs[ctx_tid()];
                int pre[MAXT]; pre[0] = i;
                enum_prefixes(X, pre, 1, t - 2, Lrow, nL);
            }
        }
        exp_pre = binom(k, t - 2); exp_cand = binom(k, t - 1); exp_pairs = binom(k, t);
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

int main(int argc, char **argv) {
    if (argc < 5) { fprintf(stderr, "usage: cphfcheck FILE t q full|cyclic s|sample S seed [threads]\n"
                                    "       cphfcheck FILE t q progression [threads] [P=r1,r2,...] | fullfast [threads]\n"); return 2; }
    t = atoi(argv[2]); q = atoi(argv[3]); const char *mode = argv[4];
    if (t < 2 || t > MAXT) { fprintf(stderr, "t must be 2..%d\n", MAXT); return 2; }
    if (!field_setup()) { fprintf(stderr, "q=%d: not a supported prime power (primes, 4, 8, 9, 16, 25, 27, 32)\n", q); return 2; }
    if (!read_file(argv[1])) return 2;
    if (n > 64) { fprintf(stderr, "at most 64 rows\n"); return 2; }
    int threads = 0, s = 1; long long S = 0; unsigned long long seed = 1;
    if (!strcmp(mode, "cyclic")) { if (argc < 6) return 2; s = atoi(argv[5]); if (argc > 6) threads = atoi(argv[6]); }
    else if (!strcmp(mode, "sample")) { if (argc < 7) return 2; S = atoll(argv[5]); seed = strtoull(argv[6], 0, 10); if (argc > 7) threads = atoi(argv[7]); }
    else if (!strcmp(mode, "full")) { if (argc > 5) threads = atoi(argv[5]); }
    else if (!strcmp(mode, "progression") || !strcmp(mode, "fullfast")) {
        int must[64], nmust = 0;
        for (int a = 5; a < argc; a++) {
            if (!strncmp(argv[a], "P=", 2) && !strcmp(mode, "progression")) {
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
        g_prog = !strcmp(mode, "progression");
        g_list = getenv("CPHFCHECK_LIST") != NULL;
        int affine = 1;
        for (int r = 0; r < n && affine; r++) for (int c = 0; c < k; c++) if (VEC(r, c)[0] != 1) { affine = 0; break; }
        printf("CPHF candidate: n=%d k=%d q=%d t=%d mode=%s%s\n", n, k, q, t, mode, affine ? " (affine: first coordinate 1)" : "");
        return run_hash_mode(threads, must, nmust, affine);
    }
    else if (!strcmp(mode, "expand")) {
        if (argc < 6) return 2;
        int aff = argc > 6 && !strcmp(argv[6], "affine");
        if (aff) for (int r = 0; r < n; r++) for (int c = 0; c < k; c++) if (VEC(r, c)[0] != 1) { fprintf(stderr, "affine: row %d column %d has first coordinate %d\n", r, c, VEC(r, c)[0]); return 2; }
        FILE *o = fopen(argv[5], "w"); if (!o) { perror(argv[5]); return 2; }
        long long Q = 1; for (int j = 0; j < t; j++) Q *= q;
        long long N = 1;
        for (int c = 0; c < k; c++) fprintf(o, c ? " 0" : "0"); fprintf(o, "\n");
        for (int r = 0; r < n; r++) for (long long b = 1; b < Q; b++) {
            uint8_t beta[MAXT]; long long bb = b; for (int j = t - 1; j >= 0; j--) { beta[j] = (uint8_t)(bb % q); bb /= q; }
            if (aff) { int rest = 0; for (int j = 1; j < t; j++) rest |= beta[j]; if (!rest) continue; }
            for (int c = 0; c < k; c++) fprintf(o, c ? " %d" : "%d", dot(beta, VEC(r, c)));
            fprintf(o, "\n"); N++;
        }
        if (aff) for (int x = 1; x < q; x++) { for (int c = 0; c < k; c++) fprintf(o, c ? " %d" : "%d", x); fprintf(o, "\n"); N++; }
        fclose(o);
        printf("wrote CA(%lld; %d, %d, %d)%s\n", N, t, k, q, aff ? " (affine)" : "");
        return 0;
    }
    else { fprintf(stderr, "unknown mode %s\n", mode); return 2; }
#ifdef _OPENMP
    if (threads > 0) omp_set_num_threads(threads);
#endif
    int affine = 1;
    for (int r = 0; r < n && affine; r++) for (int c = 0; c < k; c++) if (VEC(r, c)[0] != 1) { affine = 0; break; }
    printf("CPHF candidate: n=%d k=%d q=%d t=%d mode=%s%s\n", n, k, q, t, mode, affine ? " (affine: first coordinate 1)" : "");
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
    long long firstbad_set[MAXT] = {0}; int have_first = 0;
    #pragma omp parallel for schedule(dynamic, 1) reduction(+:total,checked)
    for (int c0 = 0; c0 < c0max; c0++) {
        int pre[MAXT]; pre[0] = c0;
        for (int i = 1; i < t - 1; i++) pre[i] = c0 + i;
        if (t == 2) { long long fb = -1; long long b = check_prefix(pre, c0 + 1, k, &fb, 0); total += b; checked += k - c0 - 1;
            if (b) {
                #pragma omp critical
                { if (!have_first) { have_first = 1; firstbad_set[0] = c0; firstbad_set[1] = fb; } }
            }
            continue; }
        while (1) {
            long long fb = -1;
            long long b = check_prefix(pre, pre[t - 2] + 1, k, &fb, 0);
            total += b; checked += k - pre[t - 2] - 1;
            if (b) {
                #pragma omp critical
                { if (!have_first) { have_first = 1; for (int i = 0; i < t - 1; i++) firstbad_set[i] = pre[i]; firstbad_set[t - 1] = fb; } }
            }
            int i = t - 2;
            while (i >= 1 && pre[i] == k - (t - 1 - i) - 1) i--;
            if (i < 1) break;
            pre[i]++; for (int j = i + 1; j < t - 1; j++) pre[j] = pre[j - 1] + 1;
        }
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
