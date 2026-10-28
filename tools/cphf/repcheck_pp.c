/* repcheck_pp.c - exact check of a cyclic-symmetric covering perfect hash family, any t (3..8),
 * q prime or a prime power <= 16, one or several column orbits.
 *
 * Written 2026-10-28 for ca-tools as the prime-power, any-t successor of repcheck.c; it shares no code
 * with symcphf.c / symcphf_pp.c (nor with repcheck.c, whose 4x4-minor scheme is t = 5 specific).
 * Usage:
 *     repcheck_pp FILE t q [threads] [s]
 * FILE: lines starting with '#' are comments; then n lines of k integers, each integer a vector of
 * GF(q)^t written in base q, most significant digit first; a digit is a GF(q) element code: for
 * q = p^e the integer sum c_i p^i of its coordinates in the basis 1, x, ..., x^(e-1) of GF(p)[x]/(f),
 * f the Conway polynomial (q = 4: x^2+x+1, q = 8: x^3+x+1, q = 9: x^2+2x+2, q = 16: x^4+x+1).
 * The field is built here from discrete logarithms (x is a primitive element of GF(p)[x]/(f) for a
 * Conway polynomial; the program checks this).
 *
 * s (default 1): the number of column orbits. Columns are numbered col = c*s + i (c in Z_m, k = m s),
 * and the symmetry is the shift col -> col + s (mod k).
 *
 * Step 1 (symmetry certificate, checked, not assumed). For every row r the program finds a matrix
 * A_r from t independent columns among 0..k-s-1 and the columns s further on, and checks, for every
 * column col,  A_r v_r[col] = v_r[col+s]  (col < k-s)  and  A_r v_r[col] = mu_r v_r[col+s-k]  (col >= k-s)
 * with one mu_r != 0 for the row, and det A_r != 0. Then a t-set S is covered in row r iff S + s is,
 * and every orbit of t-sets under the shift has a member whose smallest column is < s.
 * If any row fails the certificate the program stops (exit code 3).
 *
 * Step 2 (exact enumeration). Every t-set {c_0 < c_1 < ... < c_{t-1}} with c_0 < s is checked against
 * the rows in order with exterior products: for each row the wedge v[c_0] ^ ... ^ v[c_{j-1}] is kept
 * as its C(t, j) Pluecker coordinates (indexed by bit masks) and extended one column at a time; at
 * j = t-1 its coordinates give a normal vector n_r (n_r . u = det[v c_0 .. v c_{t-2} u]), and the
 * t-set is covered in row r iff n_r . v_r[c_{t-1}] != 0.
 * It prints the number of uncovered representative t-sets (0 means the file is a CPHF) and the first ones.
 * Build: gcc -O3 -fopenmp -o repcheck_pp repcheck_pp.c        (macOS: clang with libomp)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <omp.h>

static int n, k, t, q, S = 1;
static uint8_t *V;                  /* V[(r*k + c)*t + j], digit j of the vector, j = 0 most significant */
static int LOG[16], EXP[32], ADD[16][16], NEG[16];
static uint8_t MUL[16][16];
static int INV[16];

static int field_setup(void) {
    int p = 0; for (int d = 2; d <= q; d++) if (q % d == 0) { p = d; break; }
    int e = 0, x = 1; while (x < q) { x *= p; e++; } if (x != q || q > 16) return 0;
    int f[5] = {0};
    if (e == 1) { /* GF(p): find a primitive root, codes are residues */
        for (int g = 1; g < p; g++) { int y = 1, ord = 0; do { y = y * g % p; ord++; } while (y != 1); if (ord == p - 1) { int z = 1; for (int i = 0; i < p - 1; i++) { EXP[i] = z; z = z * g % p; } break; } }
    } else {
        if (q == 4) { f[0] = 1; f[1] = 1; } else if (q == 8) { f[0] = 1; f[1] = 1; f[2] = 0; } else if (q == 9) { f[0] = 2; f[1] = 2; } else if (q == 16) { f[0] = 1; f[1] = 1; f[2] = 0; f[3] = 0; } else return 0;
        /* powers of x: coordinate vectors, multiply by x = shift and reduce with x^e = -(f_0 + ... + f_{e-1} x^{e-1}) */
        int c[4] = {1, 0, 0, 0};
        for (int i = 0; i < q - 1; i++) {
            int code = 0; for (int j = e - 1; j >= 0; j--) code = code * p + c[j]; EXP[i] = code;
            int top = c[e - 1]; for (int j = e - 1; j > 0; j--) c[j] = c[j - 1]; c[0] = 0;
            for (int j = 0; j < e; j++) c[j] = ((c[j] - top * f[j]) % p + p) % p;
        }
    }
    for (int i = 0; i < q; i++) LOG[i] = -1;
    for (int i = 0; i < q - 1; i++) { if (LOG[EXP[i]] >= 0 || EXP[i] == 0) { fprintf(stderr, "generator is not primitive\n"); return 0; } LOG[EXP[i]] = i; EXP[i + q - 1] = EXP[i]; }
    for (int a = 0; a < q; a++) for (int b = 0; b < q; b++) {
        MUL[a][b] = (a && b) ? EXP[LOG[a] + LOG[b]] : 0;
        int s = 0, pw = 1, aa = a, bb = b; for (int j = 0; j < e; j++) { s += ((aa % p + bb % p) % p) * pw; aa /= p; bb /= p; pw *= p; }
        ADD[a][b] = s;
    }
    for (int a = 0; a < q; a++) for (int b = 0; b < q; b++) if (ADD[a][b] == 0) NEG[a] = b;
    for (int a = 1; a < q; a++) INV[a] = EXP[(q - 1 - LOG[a]) % (q - 1)];
    return 1;
}
static inline int fsub(int a, int b) { return ADD[a][NEG[b]]; }

static int read_file(const char *path) {
    FILE *fp = fopen(path, "r"); if (!fp) { perror(path); return 0; }
    size_t cap = 1 << 20; char *line = malloc(cap); int capn = 0; n = 0; k = 0;
    long qt = 1; for (int j = 0; j < t; j++) qt *= q;
    while (fgets(line, (int)cap, fp)) {
        size_t L = strlen(line);
        while (L == cap - 1 && line[L - 1] != '\n') { cap *= 2; line = realloc(line, cap); if (!fgets(line + L, (int)(cap - L), fp)) break; L = strlen(line); }
        if (line[0] == '#' || line[0] == '\n' || line[0] == '\r') continue;
        int cnt = 0; char *pp = line, *e; long *vals = malloc(sizeof(long) * (L / 2 + 2));
        for (;;) { long v = strtol(pp, &e, 10); if (e == pp) break; vals[cnt++] = v; pp = e; }
        if (!k) k = cnt; else if (cnt != k) { fprintf(stderr, "row %d has %d entries, expected %d\n", n, cnt, k); return 0; }
        if (n == capn) { capn = capn ? 2 * capn : 16; V = realloc(V, (size_t)capn * k * t); }
        for (int c = 0; c < k; c++) {
            long v = vals[c]; if (v < 0 || v >= qt) { fprintf(stderr, "entry out of range at row %d col %d\n", n, c); return 0; }
            for (int j = t - 1; j >= 0; j--) { V[((size_t)n * k + c) * t + j] = (uint8_t)(v % q); v /= q; }
        }
        free(vals); n++;
    }
    fclose(fp); free(line); return n > 0;
}

/* Gauss-Jordan on an a x b matrix (row major, b <= 16), returns rank; used for the certificate only */
static int gj(int a, int b, int M[][16]) {
    int rk = 0;
    for (int col = 0; col < b && rk < a; col++) {
        int pv = -1; for (int i = rk; i < a; i++) if (M[i][col]) { pv = i; break; }
        if (pv < 0) continue;
        for (int j = 0; j < b; j++) { int x = M[pv][j]; M[pv][j] = M[rk][j]; M[rk][j] = x; }
        int iv = INV[M[rk][col]]; for (int j = 0; j < b; j++) M[rk][j] = MUL[iv][M[rk][j]];
        for (int i = 0; i < a; i++) if (i != rk && M[i][col]) { int fct = M[i][col]; for (int j = 0; j < b; j++) M[i][j] = fsub(M[i][j], MUL[fct][M[rk][j]]); }
        rk++;
    }
    return rk;
}

static int certify_row(int r) {
    const uint8_t *v = V + (size_t)r * k * t;
    /* choose t independent columns among 0..k-S-1 greedily */
    int chosen[8], nc = 0; int B[8][16];
    for (int c = 0; c + S < k && nc < t; c++) {
        int M[8][16]; for (int i = 0; i < nc; i++) for (int j = 0; j < t; j++) M[i][j] = v[chosen[i] * t + j];
        for (int j = 0; j < t; j++) M[nc][j] = v[c * t + j];
        if (gj(nc + 1, t, M) == nc + 1) chosen[nc++] = c;
    }
    if (nc < t) { fprintf(stderr, "row %d: fewer than t independent columns\n", r); return 0; }
    /* A X = Y with X = [v chosen], Y = [v chosen+S]: transpose, X^T A^T = Y^T; solve by Gauss-Jordan on [X^T | Y^T] */
    for (int i = 0; i < t; i++) for (int j = 0; j < t; j++) { B[i][j] = v[chosen[i] * t + j]; B[i][t + j] = v[(chosen[i] + S) * t + j]; }
    if (gj(t, 2 * t, B) != t) { fprintf(stderr, "row %d: solve failed\n", r); return 0; }
    int A[8][8]; for (int i = 0; i < t; i++) for (int j = 0; j < t; j++) A[i][j] = B[j][t + i]; /* row i of A = column i of A^T */
    { int M[8][16]; for (int i = 0; i < t; i++) for (int j = 0; j < t; j++) M[i][j] = A[i][j]; if (gj(t, t, M) != t) { fprintf(stderr, "row %d: A singular\n", r); return 0; } }
    int mu = -1;
    for (int c = 0; c < k; c++) {
        int w[8]; for (int i = 0; i < t; i++) { int s = 0; for (int j = 0; j < t; j++) s = ADD[s][MUL[A[i][j]][v[c * t + j]]]; w[i] = s; }
        if (c + S < k) { for (int i = 0; i < t; i++) if (w[i] != v[(c + S) * t + i]) { fprintf(stderr, "row %d: A v[%d] != v[%d]\n", r, c, c + S); return 0; } }
        else {
            const uint8_t *z = v + (size_t)(c + S - k) * t; int found = -1;
            for (int cand = 1; cand < q && found < 0; cand++) { int ok = 1; for (int i = 0; i < t; i++) if (w[i] != MUL[cand][z[i]]) { ok = 0; break; } if (ok) found = cand; }
            if (found < 0 || (mu >= 0 && found != mu)) { fprintf(stderr, "row %d: wrap A v[%d] is not mu v[%d] with one nonzero mu\n", r, c, c + S - k); return 0; }
            mu = found;
        }
    }
    return mu;
}

/* masks of {0..t-1} by popcount, and for every mask and element the sign of appending that element last */
static int nmask[9], masks[9][256];

int main(int argc, char **argv) {
    if (argc < 4) { fprintf(stderr, "usage: repcheck_pp FILE t q [threads] [s]\n"); return 2; }
    t = atoi(argv[2]); q = atoi(argv[3]); int th = argc > 4 ? atoi(argv[4]) : omp_get_max_threads(); if (argc > 5) S = atoi(argv[5]);
    if (t < 3 || t > 8) { fprintf(stderr, "t must be 3..8\n"); return 2; }
    if (!field_setup()) { fprintf(stderr, "unsupported q=%d (primes and 4, 8, 9, 16 up to 16)\n", q); return 2; }
    if (!read_file(argv[1])) return 2;
    if (S < 1 || k % S) { fprintf(stderr, "s=%d does not divide k=%d\n", S, k); return 2; }
    if (n > 64) { fprintf(stderr, "at most 64 rows\n"); return 2; }
    fprintf(stderr, "read n=%d rows, k=%d columns, t=%d, q=%d, s=%d orbits\n", n, k, t, q, S);
    for (int r = 0; r < n; r++) { int mu = certify_row(r); if (mu <= 0) { printf("SYMMETRY CERTIFICATE FAILED at row %d\n", r); return 3; } }
    printf("symmetry certificate: every row r has A_r with A_r v[c] = v[c+%d] and A_r v[c] = mu_r v[c+%d-k] at the wrap (mu_r != 0), det A_r != 0\n", S, S);
    fflush(stdout);
    for (int m = 0; m < (1 << t); m++) { int pc = __builtin_popcount(m); masks[pc][nmask[pc]++] = m; }
    const int R = n, K = k, TT = t, full = (1 << t) - 1;
    /* innermost dot product: 0 = q prime (integer sum mod q), 1 = q = 2^e (xor), 2 = tables */
    int MODE = 2; { int pr = 1; for (int d = 2; d * d <= q; d++) if (q % d == 0) pr = 0; if (pr) MODE = 0; else if ((q & (q - 1)) == 0) MODE = 1; }
    if (MODE == 1) for (int a = 0; a < q; a++) for (int b = 0; b < q; b++) if (ADD[a][b] != (a ^ b)) { fprintf(stderr, "internal: char 2 addition is not xor\n"); return 2; }
    /* P[(c*R + r)*t + j]: column-major copy for locality in the innermost loop */
    uint8_t *P = malloc((size_t)R * K * t);
    for (int r = 0; r < R; r++) for (int c = 0; c < K; c++) for (int j = 0; j < t; j++) P[((size_t)c * R + r) * t + j] = V[((size_t)r * K + c) * t + j];
    long long uncovered = 0, checked = 0; int printed = 0;
    double t0 = omp_get_wtime(); int done = 0;
    long ntask = 0; int *ta = malloc(sizeof(int) * (size_t)S * K), *tb = malloc(sizeof(int) * (size_t)S * K);
    for (int a = 0; a < S; a++) for (int b = a + 1; b <= K - (t - 1); b++) { ta[ntask] = a; tb[ntask] = b; ntask++; }
    #pragma omp parallel num_threads(th) reduction(+:uncovered, checked)
    {
        /* W[j][r][mask]: wedge of the first j columns in row r */
        uint8_t (*W)[64][256] = malloc(sizeof(uint8_t) * 9 * 64 * 256);
        int c[8]; uint8_t nr[64][8];
        #pragma omp for schedule(dynamic, 1)
        for (long ti = 0; ti < ntask; ti++) {
            c[0] = ta[ti]; c[1] = tb[ti];
            for (int r = 0; r < R; r++) { memset(W[0][r], 0, 256); W[0][r][0] = 1; }
            /* extend to level j+1 with column c[j] */
            #define EXTEND(j) do { for (int r = 0; r < R; r++) { const uint8_t *x = P + ((size_t)c[j] * R + r) * TT; \
                for (int mi = 0; mi < nmask[(j) + 1]; mi++) { int Sm = masks[(j) + 1][mi]; int acc = 0, sgn = 0; \
                    for (int i = TT - 1; i >= 0; i--) if (Sm >> i & 1) { int term = MUL[W[j][r][Sm & ~(1 << i)]][x[i]]; acc = sgn ? fsub(acc, term) : ADD[acc][term]; sgn ^= 1; } \
                    W[(j) + 1][r][Sm] = (uint8_t)acc; } } } while (0)
            EXTEND(0); EXTEND(1);
            int l = 2; c[2] = c[1];
            while (l >= 2) {
                c[l]++;
                if (c[l] > K - 1 - (TT - 1 - l)) { l--; continue; }
                if (l < TT - 1) {
                    EXTEND(l);
                    if (l + 1 < TT - 1) { l++; c[l] = c[l - 1]; continue; }
                    /* level t-1: normal vectors. det[w1..w_{t-1} u] = sum_i u_i * (-1)^{#(full\i elements > i)} W[full\i] */
                    for (int r = 0; r < R; r++) for (int i = 0; i < TT; i++) { int w = W[TT - 1][r][full & ~(1 << i)]; nr[r][i] = (uint8_t)(((TT - 1 - i) & 1) ? NEG[w] : w); }
                    for (int d = c[TT - 2] + 1; d <= K - 1; d++) {
                        const uint8_t *u = P + (size_t)d * R * TT; int cov = 0;
                        if (MODE == 0) { for (int r = 0; r < R; r++, u += TT) { int s = 0; for (int i = 0; i < TT; i++) s += nr[r][i] * u[i]; if (s % q) { cov = 1; break; } } }
                        else if (MODE == 1) { for (int r = 0; r < R; r++, u += TT) { int s = 0; for (int i = 0; i < TT; i++) s ^= MUL[nr[r][i]][u[i]]; if (s) { cov = 1; break; } } }
                        else { for (int r = 0; r < R; r++, u += TT) { int s = 0; for (int i = 0; i < TT; i++) s = ADD[s][MUL[nr[r][i]][u[i]]]; if (s) { cov = 1; break; } } }
                        checked++;
                        if (!cov) { uncovered++;
                            #pragma omp critical
                            { if (printed < 10) { printf("UNCOVERED {"); for (int i = 0; i < TT - 1; i++) printf("%d,", c[i]); printf("%d}\n", d); printed++; } } }
                    }
                } else { /* t == 3: c[2] is the last column, W[2] holds the normal */
                    for (int r = 0; r < R; r++) for (int i = 0; i < TT; i++) { int w = W[TT - 1][r][full & ~(1 << i)]; nr[r][i] = (uint8_t)(((TT - 1 - i) & 1) ? NEG[w] : w); }
                    const uint8_t *u = P + (size_t)c[2] * R * TT; int cov = 0;
                    for (int r = 0; r < R; r++, u += TT) { int s = 0; for (int i = 0; i < TT; i++) s = ADD[s][MUL[nr[r][i]][u[i]]]; if (s) { cov = 1; break; } }
                    checked++;
                    if (!cov) { uncovered++;
                        #pragma omp critical
                        { if (printed < 10) { printf("UNCOVERED {%d,%d,%d}\n", c[0], c[1], c[2]); printed++; } } }
                }
            }
            #pragma omp atomic
            done++;
            if (done % 20000 == 0) {
                #pragma omp critical
                { fprintf(stderr, "[%.0fs] %d of %ld outer tasks\n", omp_get_wtime() - t0, done, ntask); }
            }
        }
        free(W);
    }
    long double expect = 0; for (int a = 0; a < S; a++) { long double b = 1; for (int i = 0; i < t - 1; i++) b = b * (K - 1 - a - i) / (i + 1); expect += b; }
    printf("checked %lld representative t-sets (sum_{a<s} C(k-1-a, t-1) = %.0Lf), uncovered %lld, time %.0fs\n", checked, expect, uncovered, omp_get_wtime() - t0);
    if (uncovered == 0 && (long double)checked == expect) { printf("RESULT: CPHF VERIFIED (symmetry certificate + all %lld representatives covered)\n", checked); return 0; }
    printf("RESULT: NOT VERIFIED\n"); return 1;
}
