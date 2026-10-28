/* cphf_tools_pp - cphf_tools.c for prime-power q (2026-10-28): same commands and file format, with
 * GF(q) arithmetic for q = p^e <= 16. An element of GF(p^e) is coded by the integer sum c_i p^i of its
 * coordinates in the basis 1, x, ..., x^(e-1) of GF(p)[x]/(f), f the Conway polynomial (q = 4: x^2+x+1,
 * q = 8: x^3+x+1, q = 9: x^2+2x+2, q = 16: x^4+x+1), the convention of symcphf_pp.c. The field tables
 * are computed here by schoolbook polynomial multiplication (no code shared with symcphf_pp.c or
 * repcheck_pp.c). For prime q the results are those of cphf_tools.c.
 *
 *
 * File format: lines starting with '#' are comments; then n lines of k integers, each integer
 * encoding a vector of GF(q)^t by base-q digits, most significant first (digitsBase convention).
 *
 *   cphf_tools_pp check FILE t q [s]     brute force: every t-set of columns, every row, determinant
 *                                        by Laplace expansion mod q (independent of symcphf's rank code)
 *   cphf_tools expand FILE t q OUT       write the CA(n(q^t-1)+1; t, k, q): the all-zero row once, then
 *                                        for every CPHF row and every nonzero beta in GF(q)^t the row beta.v_c
 * Build: gcc -O2 -fopenmp -o cphf_tools cphf_tools.c
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

static int n, k, t, q; static int *A; /* A[(r*k + c)*t + j] */
static int FADD[16][16], FMUL[16][16], FNEG[16];
static int field_init(void) {
    static const int conway[17][5] = { [4] = {1, 1, 1}, [8] = {1, 1, 0, 1}, [9] = {2, 2, 1}, [16] = {1, 1, 0, 0, 1} };
    int p = 0; for (int d = 2; d <= q; d++) if (q % d == 0) { p = d; break; }
    int e = 0, x = 1; while (x < q) { x *= p; e++; } if (x != q || q > 16) return 0;
    if (e > 1 && conway[q][e] != 1) return 0;
    for (int a = 0; a < q; a++) for (int b = 0; b < q; b++) {
        int ca[4], cb[4], pr[8] = {0}, s = 0, m = 0, pw = 1;
        for (int i = 0, aa = a, bb = b; i < e; i++) { ca[i] = aa % p; aa /= p; cb[i] = bb % p; bb /= p; }
        for (int i = 0; i < e; i++) { s += ((ca[i] + cb[i]) % p) * pw; pw *= p; }
        for (int i = 0; i < e; i++) for (int j = 0; j < e; j++) pr[i + j] += ca[i] * cb[j];
        for (int i = 2 * e - 2; i >= e; i--) for (int j = 0; j < e; j++) pr[i - e + j] -= pr[i] * conway[q][j];
        pw = 1; for (int i = 0; i < e; i++) { m += (((pr[i] % p) + p) % p) * pw; pw *= p; }
        if (e == 1) m = (a * b) % q;
        FADD[a][b] = s; FMUL[a][b] = m;
    }
    for (int a = 0; a < q; a++) for (int b = 0; b < q; b++) if (FADD[a][b] == 0) FNEG[a] = b;
    return 1;
}

static long det_laplace(long *m, int sz, int *rowsused, int col) {
    /* expand along column `col` over unused rows; m is t x t */
    if (col == t) return 1;
    int det = 0; int sign = 1;
    for (int r = 0; r < t; r++) {
        if (rowsused[r]) continue;
        if (m[r * t + col]) { rowsused[r] = 1; int term = FMUL[m[r * t + col]][det_laplace(m, sz, rowsused, col + 1)]; det = FADD[det][sign > 0 ? term : FNEG[term]]; rowsused[r] = 0; }
        sign = -sign;
    }
    return det;
}

static int read_file(const char *path) {
    FILE *f = fopen(path, "r"); if (!f) { perror(path); return 0; }
    char *line = NULL; size_t cap = 0; n = 0; k = 0; int capn = 0;
    while (getline(&line, &cap, f) > 0) {
        if (line[0] == '#' || line[0] == '\n') continue;
        int cnt = 0; long vals[70000]; char *p = line;
        while (*p) { while (*p == ' ' || *p == '\t') p++; if (*p == '\n' || !*p) break; vals[cnt++] = strtol(p, &p, 10); }
        if (k == 0) k = cnt; else if (cnt != k) { fprintf(stderr, "ragged row\n"); return 0; }
        if (n == capn) { capn = capn ? 2 * capn : 16; A = realloc(A, sizeof(int) * (size_t)capn * k * t); }
        for (int c = 0; c < k; c++) { long v = vals[c]; if (v < 0) { fprintf(stderr, "negative entry\n"); return 0; } for (int j = t - 1; j >= 0; j--) { A[((size_t)n * k + c) * t + j] = v % q; v /= q; } if (v) { fprintf(stderr, "entry out of range\n"); return 0; } }
        n++;
    }
    fclose(f); return 1;
}

int main(int argc, char **argv) {
    if (argc < 5) { fprintf(stderr, "usage: cphf_tools_pp check|expand FILE t q [OUT]\n"); return 2; }
    t = atoi(argv[3]); q = atoi(argv[4]);
    if (!field_init()) { fprintf(stderr, "unsupported q=%d\n", q); return 2; }
    if (!read_file(argv[2])) return 2;
    fprintf(stderr, "read CPHF with n=%d rows, k=%d columns, t=%d, q=%d\n", n, k, t, q);
    if (!strcmp(argv[1], "expand")) {
        FILE *o = fopen(argv[5], "w"); long qt = 1; for (int j = 0; j < t; j++) qt *= q;
        for (int c = 0; c < k; c++) fprintf(o, "%s0", c ? " " : ""); fprintf(o, "\n"); long N = 1;
        for (int r = 0; r < n; r++) for (long b = 1; b < qt; b++) {
            int beta[8]; long bb = b; for (int j = t - 1; j >= 0; j--) { beta[j] = bb % q; bb /= q; }
            for (int c = 0; c < k; c++) { int s = 0; for (int j = 0; j < t; j++) s = FADD[s][FMUL[beta[j]][A[((size_t)r * k + c) * t + j]]]; fprintf(o, "%s%d", c ? " " : "", s); }
            fprintf(o, "\n"); N++;
        }
        fclose(o); printf("wrote CA with N=%ld rows (= n(q^t-1)+1 = %ld), k=%d\n", N, (long)n * (qt - 1) + 1, k); return 0;
    }
    if (!strcmp(argv[1], "sample")) { /* independent check on N random t-sets (not a proof) */
        long N = atol(argv[5]); srand48(argc > 6 ? atol(argv[6]) : 1); long unc = 0;
        for (long i = 0; i < N; i++) {
            int c[8]; int ok; do { ok = 1; for (int j = 0; j < t; j++) c[j] = (int)(drand48() * k); for (int a = 0; a < t && ok; a++) for (int b = a + 1; b < t; b++) if (c[a] == c[b]) ok = 0; } while (!ok);
            int cov = 0;
            for (int r = 0; r < n && !cov; r++) { long m[64]; int used[8] = {0}; for (int a = 0; a < t; a++) for (int j = 0; j < t; j++) m[a * t + j] = A[((size_t)r * k + c[a]) * t + j]; if (det_laplace(m, t, used, 0)) cov = 1; }
            if (!cov) { unc++; if (unc <= 5) { fprintf(stderr, "uncovered:"); for (int j = 0; j < t; j++) fprintf(stderr, " %d", c[j]); fprintf(stderr, "\n"); } }
        }
        printf("%s: %ld random t-sets checked, uncovered %ld\n", argv[2], N, unc); return unc ? 1 : 0;
    }
    /* check */
    long total = 0, uncovered = 0, unc_low = 0; int shown = 0; int S = argc > 5 ? atoi(argv[5]) : 1; /* also count uncovered t-sets with smallest column < S */
    #pragma omp parallel for schedule(dynamic, 1) reduction(+:total, uncovered, unc_low)
    for (int c0 = 0; c0 <= k - t; c0++) {
        int c[8]; c[0] = c0; for (int j = 1; j < t; j++) c[j] = c0 + j;
        while (1) {
            total++;
            int cov = 0;
            for (int r = 0; r < n && !cov; r++) {
                long m[64]; int used[8] = {0};
                for (int a = 0; a < t; a++) for (int j = 0; j < t; j++) m[a * t + j] = A[((size_t)r * k + c[a]) * t + j];
                if (det_laplace(m, t, used, 0)) cov = 1;
            }
            if (!cov) { uncovered++; if (c[0] < S) unc_low++;
                #pragma omp critical
                { if (shown < 5) { shown++; fprintf(stderr, "uncovered t-set:"); for (int j = 0; j < t; j++) fprintf(stderr, " %d", c[j]); fprintf(stderr, "\n"); } } }
            int l = t - 1; while (l >= 1 && c[l] == k - 1 - (t - 1 - l)) l--;
            if (l < 1) break;
            c[l]++; for (int j = l + 1; j < t; j++) c[j] = c[j - 1] + 1;
        }
    }
    printf("%s: t-sets checked %ld, uncovered %ld (of which with smallest column < %d: %ld) -> %s\n", argv[2], total, uncovered, S, unc_low, uncovered ? "NOT a CPHF" : "CPHF verified (all t-sets covered)");
    return uncovered ? 1 : 0;
}
