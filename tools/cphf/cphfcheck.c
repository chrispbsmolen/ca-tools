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
 * Output: the number of uncovered t-sets checked (0 = CPHF in modes full and cyclic), the first ones,
 * and the affine flag. Exit 0 if none uncovered, 1 if some, 2 usage/format error, 3 symmetry fails.
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

int main(int argc, char **argv) {
    if (argc < 5) { fprintf(stderr, "usage: cphfcheck FILE t q full|cyclic s|sample S seed [threads]\n"); return 2; }
    t = atoi(argv[2]); q = atoi(argv[3]); const char *mode = argv[4];
    if (t < 2 || t > MAXT) { fprintf(stderr, "t must be 2..%d\n", MAXT); return 2; }
    if (!field_setup()) { fprintf(stderr, "q=%d: not a supported prime power (primes, 4, 8, 9, 16, 25, 27, 32)\n", q); return 2; }
    if (!read_file(argv[1])) return 2;
    if (n > 64) { fprintf(stderr, "at most 64 rows\n"); return 2; }
    int threads = 0, s = 1; long long S = 0; unsigned long long seed = 1;
    if (!strcmp(mode, "cyclic")) { if (argc < 6) return 2; s = atoi(argv[5]); if (argc > 6) threads = atoi(argv[6]); }
    else if (!strcmp(mode, "sample")) { if (argc < 7) return 2; S = atoll(argv[5]); seed = strtoull(argv[6], 0, 10); if (argc > 7) threads = atoi(argv[7]); }
    else if (!strcmp(mode, "full")) { if (argc > 5) threads = atoi(argv[5]); }
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
    return total ? 1 : 0;
}
