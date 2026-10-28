/* repcheck.c - independent exact check of a cyclic-symmetric covering perfect hash family.
 *
 * Written 2026-10-27 for ca-tools, separately from symcphf.c (no code shared). Usage:
 *     repcheck FILE t q [threads]
 * FILE: lines starting with '#' are comments; then n lines of k integers, each integer a vector
 * of GF(q)^t written in base q, most significant digit first. q must be prime.
 *
 * A CPHF(n; k, q, t) needs: for every set S of t columns some row r in which the t vectors
 * v_r[c], c in S, are linearly independent over GF(q).
 *
 * Step 1 (symmetry certificate, checked, not assumed). For every row r the program finds a matrix
 * A_r from t consecutive independent columns and checks, for every column c,
 *     A_r v_r[c] = v_r[c+1]  (c < k-1)   and   A_r v_r[k-1] = mu_r v_r[0]  with mu_r != 0,
 * and det A_r != 0. Then the columns of the shifted set S+1 (mod k) in row r are A_r times the
 * columns of S, one of them multiplied by mu_r, so S is covered in row r iff S+1 is. Every t-set
 * has a cyclic shift that contains column 0, so it suffices to check the sets containing 0.
 * If any row fails the certificate the program stops and says so (exit code 3).
 *
 * Step 2 (exact enumeration). Every set {0, a, b, c, d} (t = 5; general t handled by the same
 * scheme with t-1 nested loops is not needed here, so t = 5 only) with 1 <= a < b < c < d <= k-1
 * is checked against the rows in order: with v0, va, vb, vc fixed, the 4x4 minors of these four
 * vectors give a normal vector n_r, and {0,a,b,c,d} is covered in row r iff n_r . v_r[d] != 0.
 * (When v0, va, vb, vc are dependent n_r = 0 and no d is covered in that row, which is correct.)
 * The program prints the number of uncovered representative sets (0 means the file is a CPHF)
 * and the first few uncovered sets.
 * Build: gcc -O3 -fopenmp -o repcheck repcheck.c        (macOS: clang with libomp)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

static int n, k, t, q;
static int *V;                    /* V[(r*k + c)*t + j], digit j of the vector, j = 0 most significant */
static int inv[64];

static int md(long x) { x %= q; return (int)(x < 0 ? x + q : x); }

static int read_file(const char *path) {
    FILE *f = fopen(path, "r"); if (!f) { perror(path); return 0; }
    size_t cap = 1 << 20; char *line = malloc(cap); int capn = 0; n = 0; k = 0;
    while (fgets(line, (int)cap, f)) {
        size_t L = strlen(line);
        while (L == cap - 1 && line[L - 1] != '\n') { cap *= 2; line = realloc(line, cap); if (!fgets(line + L, (int)(cap - L), f)) break; L = strlen(line); }
        if (line[0] == '#' || line[0] == '\n' || line[0] == '\r') continue;
        int cnt = 0; char *p = line, *e;
        long *vals = malloc(sizeof(long) * (L / 2 + 2));
        for (;;) { long v = strtol(p, &e, 10); if (e == p) break; vals[cnt++] = v; p = e; }
        if (!k) k = cnt; else if (cnt != k) { fprintf(stderr, "row %d has %d entries, expected %d\n", n, cnt, k); return 0; }
        if (n == capn) { capn = capn ? 2 * capn : 16; V = realloc(V, sizeof(int) * (size_t)capn * k * t); }
        for (int c = 0; c < k; c++) {
            long v = vals[c]; long qt = 1; for (int j = 0; j < t; j++) qt *= q;
            if (v < 0 || v >= qt) { fprintf(stderr, "entry out of range at row %d col %d\n", n, c); return 0; }
            for (int j = t - 1; j >= 0; j--) { V[((size_t)n * k + c) * t + j] = (int)(v % q); v /= q; }
        }
        free(vals); n++;
    }
    fclose(f); free(line); return n > 0;
}

/* rank of an rows x t matrix over GF(q) (rows given as int arrays), destroys a copy */
static int rank_of(int m[][8], int rows) {
    int a[8][8]; memcpy(a, m, sizeof(a)); int rk = 0;
    for (int col = 0; col < t && rk < rows; col++) {
        int p = -1; for (int i = rk; i < rows; i++) if (a[i][col]) { p = i; break; }
        if (p < 0) continue;
        for (int j = 0; j < t; j++) { int x = a[p][j]; a[p][j] = a[rk][j]; a[rk][j] = x; }
        int iv = inv[a[rk][col]];
        for (int j = 0; j < t; j++) a[rk][j] = md((long)a[rk][j] * iv);
        for (int i = 0; i < rows; i++) if (i != rk && a[i][col]) { int f = a[i][col]; for (int j = 0; j < t; j++) a[i][j] = md(a[i][j] - (long)f * a[rk][j]); }
        rk++;
    }
    return rk;
}

/* solve: find A (t x t) with A X = Y, X columns x_0..x_{t-1} independent. Returns 0 on failure. */
static int solve_A(int X[8][8], int Y[8][8], int A[8][8]) {
    /* A = Y X^{-1}; compute X^{-1} by Gauss-Jordan on [X | I] (X stored column-wise: X[j][i] = x_i digit j) */
    int M[8][16];
    for (int i = 0; i < t; i++) for (int j = 0; j < t; j++) { M[i][j] = X[i][j]; M[i][t + j] = (i == j); }
    for (int col = 0; col < t; col++) {
        int p = -1; for (int i = col; i < t; i++) if (M[i][col]) { p = i; break; }
        if (p < 0) return 0;
        for (int j = 0; j < 2 * t; j++) { int x = M[p][j]; M[p][j] = M[col][j]; M[col][j] = x; }
        int iv = inv[M[col][col]]; for (int j = 0; j < 2 * t; j++) M[col][j] = md((long)M[col][j] * iv);
        for (int i = 0; i < t; i++) if (i != col && M[i][col]) { int f = M[i][col]; for (int j = 0; j < 2 * t; j++) M[i][j] = md(M[i][j] - (long)f * M[col][j]); }
    }
    for (int i = 0; i < t; i++) for (int j = 0; j < t; j++) { long s = 0; for (int l = 0; l < t; l++) s += (long)Y[i][l] * M[l][t + j]; A[i][j] = md(s); }
    return 1;
}

static int certify_row(int r) {
    const int *v = V + (size_t)r * k * t;
    int start = -1;
    for (int s0 = 0; s0 + t <= k; s0++) {
        int m[8][8] = {{0}}; for (int i = 0; i < t; i++) for (int j = 0; j < t; j++) m[i][j] = v[(s0 + i) * t + j];
        if (rank_of(m, t) == t) { start = s0; break; }
    }
    if (start < 0 || start + t >= k) { fprintf(stderr, "row %d: no t consecutive independent columns\n", r); return 0; }
    int X[8][8], Y[8][8], A[8][8];
    for (int i = 0; i < t; i++) for (int j = 0; j < t; j++) { X[j][i] = v[(start + i) * t + j]; Y[j][i] = v[(start + i + 1) * t + j]; }
    if (!solve_A(X, Y, A)) { fprintf(stderr, "row %d: solve failed\n", r); return 0; }
    { int m[8][8]; for (int i = 0; i < t; i++) for (int j = 0; j < t; j++) m[i][j] = A[i][j]; if (rank_of(m, t) != t) { fprintf(stderr, "row %d: A singular\n", r); return 0; } }
    int mu = -1;
    for (int c = 0; c < k; c++) {
        int w[8]; for (int i = 0; i < t; i++) { long s = 0; for (int j = 0; j < t; j++) s += (long)A[i][j] * v[c * t + j]; w[i] = md(s); }
        if (c < k - 1) { for (int i = 0; i < t; i++) if (w[i] != v[(c + 1) * t + i]) { fprintf(stderr, "row %d: A v[%d] != v[%d]\n", r, c, c + 1); return 0; } }
        else {
            /* w must equal mu * v[0], mu != 0 */
            for (int cand = 1; cand < q; cand++) { int ok = 1; for (int i = 0; i < t; i++) if (w[i] != md((long)cand * v[i])) { ok = 0; break; } if (ok) { mu = cand; break; } }
            if (mu < 0) { fprintf(stderr, "row %d: wrap A v[k-1] is not a nonzero multiple of v[0]\n", r); return 0; }
        }
    }
    return mu;
}

int main(int argc, char **argv) {
    if (argc < 4) { fprintf(stderr, "usage: repcheck FILE t q [threads]\n"); return 2; }
    t = atoi(argv[2]); q = atoi(argv[3]); int th = argc > 4 ? atoi(argv[4]) : omp_get_max_threads();
    if (t != 5) { fprintf(stderr, "this checker handles t = 5 only\n"); return 2; }
    for (int d = 2; d * d <= q; d++) if (q % d == 0) { fprintf(stderr, "q must be prime\n"); return 2; }
    for (int a = 1; a < q; a++) for (int b = 1; b < q; b++) if ((a * b) % q == 1) inv[a] = b;
    if (!read_file(argv[1])) return 2;
    fprintf(stderr, "read n=%d rows, k=%d columns, t=%d, q=%d\n", n, k, t, q);
    for (int r = 0; r < n; r++) { int mu = certify_row(r); if (mu <= 0) { printf("SYMMETRY CERTIFICATE FAILED at row %d\n", r); return 3; } }
    printf("symmetry certificate: every row r has A_r with A_r v[c] = v[c+1] and A_r v[k-1] = mu_r v[0] (mu_r != 0), det A_r != 0\n");
    fflush(stdout);
    /* column vectors per row as small arrays */
    const int K = k, R = n;
    unsigned char *P = malloc((size_t)R * K * 5);
    for (int r = 0; r < R; r++) for (int c = 0; c < K; c++) for (int j = 0; j < 5; j++) P[((size_t)c * R + r) * 5 + j] = (unsigned char)V[((size_t)r * K + c) * 5 + j];
    long long uncovered = 0, checked = 0; int printed = 0;
    double t0 = omp_get_wtime();
    int adone = 0;
    #pragma omp parallel for schedule(dynamic, 1) num_threads(th) reduction(+:uncovered, checked)
    for (int a = 1; a <= K - 4; a++) {
        int nr[64][5];
        for (int b = a + 1; b <= K - 3; b++) {
            /* 3x3 minors of [v0 va vb] per row: m3[r][i][j] = minor with coordinates (all except i and j) -> store for pairs i<j */
            int m3[64][5][5];
            for (int r = 0; r < R; r++) {
                const unsigned char *x = P + ((size_t)0 * R + r) * 5, *y = P + ((size_t)a * R + r) * 5, *z = P + ((size_t)b * R + r) * 5;
                for (int i = 0; i < 5; i++) for (int j = i + 1; j < 5; j++) {
                    int idx[3], c3 = 0; for (int l = 0; l < 5; l++) if (l != i && l != j) idx[c3++] = l;
                    long d = (long)x[idx[0]] * ((long)y[idx[1]] * z[idx[2]] - (long)y[idx[2]] * z[idx[1]])
                           - (long)x[idx[1]] * ((long)y[idx[0]] * z[idx[2]] - (long)y[idx[2]] * z[idx[0]])
                           + (long)x[idx[2]] * ((long)y[idx[0]] * z[idx[1]] - (long)y[idx[1]] * z[idx[0]]);
                    m3[r][i][j] = m3[r][j][i] = md(d);
                }
            }
            for (int c = b + 1; c <= K - 2; c++) {
                /* normal n_i = (-1)^i * det of 4x4 matrix [v0 va vb vc] with coordinate i removed.
                   Expand that 4x4 along the vc column: det = sum over l != i of (-1)^{pos(l)} vc_l * minor3(i,l)
                   where pos(l) is the position of l among the coordinates except i (0..3), column vc is last (index 3). */
                for (int r = 0; r < R; r++) {
                    const unsigned char *w = P + ((size_t)c * R + r) * 5;
                    for (int i = 0; i < 5; i++) {
                        long s = 0; int pos = 0;
                        for (int l = 0; l < 5; l++) { if (l == i) continue; long term = (long)w[l] * m3[r][i][l]; if (((pos + 3) & 1) == 0) s += term; else s -= term; pos++; }
                        nr[r][i] = md((i & 1) ? -s : s);
                    }
                }
                for (int d = c + 1; d <= K - 1; d++) {
                    const unsigned char *u = P + (size_t)d * R * 5;
                    int cov = 0;
                    for (int r = 0; r < R; r++, u += 5) {
                        int s = nr[r][0] * u[0] + nr[r][1] * u[1] + nr[r][2] * u[2] + nr[r][3] * u[3] + nr[r][4] * u[4];
                        if (s % q) { cov = 1; break; }
                    }
                    checked++;
                    if (!cov) {
                        uncovered++;
                        #pragma omp critical
                        { if (printed < 10) { printf("UNCOVERED {0,%d,%d,%d,%d}\n", a, b, c, d); printed++; } }
                    }
                }
            }
        }
        #pragma omp atomic
        adone++;
        if ((a % 50) == 0) {
            #pragma omp critical
            { fprintf(stderr, "[%.0fs] outer index a = %d done (%d of %d outer values finished)\n", omp_get_wtime() - t0, a, adone, K - 4); }
        }
    }
    long double expect = 1; for (int i = 0; i < 4; i++) expect = expect * (K - 1 - i) / (i + 1);
    printf("checked %lld representative sets {0,a,b,c,d} (C(k-1,4) = %.0Lf), uncovered %lld, time %.0fs\n", checked, expect, uncovered, omp_get_wtime() - t0);
    if (uncovered == 0 && (long double)checked == expect) { printf("RESULT: CPHF VERIFIED (symmetry certificate + all %lld representatives covered)\n", checked); return 0; }
    printf("RESULT: NOT VERIFIED\n"); return 1;
}
