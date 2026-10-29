/* common.h - file reading, symmetry certificate and nullspace, used by the reference checker and
   the Metal host. Independent of repcheck_pp.c / symcphf_pp.c (written separately, other methods). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int N, K, T, Q, SO = 1;
static uint8_t *VV;   /* VV[(c*N + r)*T + j] : coordinate j (j = 0 most significant digit) */
static int read_family(const char *path) {
    FILE *fp = fopen(path, "r"); if (!fp) { perror(path); return 0; }
    size_t cap = 1 << 20; char *line = malloc(cap); long *vals = NULL; size_t nv = 0, capv = 0; int rows = 0, k = -1;
    while (fgets(line, (int)cap, fp)) {
        size_t L = strlen(line);
        while (L == cap - 1 && line[L - 1] != '\n') { cap *= 2; line = realloc(line, cap); if (!fgets(line + L, (int)(cap - L), fp)) break; L = strlen(line); }
        if (line[0] == '#' || line[0] == '\n' || line[0] == '\r') continue;
        char *pp = line, *e; int cnt = 0;
        for (;;) { long v = strtol(pp, &e, 10); if (e == pp) break; if (nv == capv) { capv = capv ? 2 * capv : 1 << 16; vals = realloc(vals, capv * sizeof(long)); } vals[nv++] = v; cnt++; pp = e; }
        if (!cnt) continue;
        if (k < 0) k = cnt; else if (cnt != k) { fprintf(stderr, "row %d has %d entries, not %d\n", rows, cnt, k); return 0; }
        rows++;
    }
    fclose(fp); free(line);
    N = rows; K = k; long qt = 1; for (int j = 0; j < T; j++) qt *= Q;
    VV = malloc((size_t)N * K * T);
    for (int r = 0; r < N; r++) for (int c = 0; c < K; c++) {
        long v = vals[(size_t)r * K + c]; if (v < 0 || v >= qt) { fprintf(stderr, "entry out of range at row %d col %d\n", r, c); return 0; }
        for (int j = T - 1; j >= 0; j--) { VV[((size_t)c * N + r) * T + j] = (uint8_t)(v % Q); v /= Q; }
    }
    free(vals); return 1;
}
/* rank and solve over GF(q) by Gaussian elimination on a rows x cols matrix (row-major, in place) */
static int gf_rank(uint8_t *M, int rows, int cols, int *pivcol) {
    int rk = 0;
    for (int c = 0; c < cols && rk < rows; c++) {
        int pr = -1; for (int i = rk; i < rows; i++) if (M[i * cols + c]) { pr = i; break; }
        if (pr < 0) continue;
        for (int j = 0; j < cols; j++) { uint8_t tmp = M[rk * cols + j]; M[rk * cols + j] = M[pr * cols + j]; M[pr * cols + j] = tmp; }
        uint8_t inv = GINV[M[rk * cols + c]];
        for (int j = 0; j < cols; j++) M[rk * cols + j] = GMUL[inv][M[rk * cols + j]];
        for (int i = 0; i < rows; i++) if (i != rk && M[i * cols + c]) { uint8_t f = GNEG[M[i * cols + c]];
            for (int j = 0; j < cols; j++) M[i * cols + j] = GADD[M[i * cols + j]][GMUL[f][M[rk * cols + j]]]; }
        if (pivcol) pivcol[rk] = c;
        rk++;
    }
    return rk;
}
/* symmetry certificate: for each row find A with A v[c] = v[c+SO] (c < K-SO) and A v[c] = mu v[c+SO-K]
   (c >= K-SO) for one mu != 0, A invertible. Returns 1 if every row passes. */
static int certify(int verbose) {
    for (int r = 0; r < N; r++) {
        /* choose T columns with independent vectors among 0..K-SO-1, greedily */
        int cols[16], nc = 0; uint8_t X[16 * 16];
        for (int c = 0; c < K - SO && nc < T; c++) {
            uint8_t Mtest[16 * 16];
            for (int i = 0; i < nc; i++) memcpy(Mtest + i * T, X + i * T, T);
            memcpy(Mtest + nc * T, VV + ((size_t)c * N + r) * T, T);
            if (gf_rank(Mtest, nc + 1, T, NULL) == nc + 1) { memcpy(X + nc * T, VV + ((size_t)c * N + r) * T, T); cols[nc++] = c; }
        }
        if (nc < T) { if (verbose) printf("row %d: fewer than %d independent columns\n", r, T); return 0; }
        /* solve A X^T = Y^T, i.e. for each output coordinate i: X a_i = y_i where a_i is row i of A.
           Augmented system [X | Y] reduced: X is T x T (rows = the chosen columns' vectors). */
        uint8_t Aug[16 * 32];
        for (int i = 0; i < T; i++) { memcpy(Aug + i * 2 * T, X + i * T, T); memcpy(Aug + i * 2 * T + T, VV + ((size_t)(cols[i] + SO) * N + r) * T, T); }
        if (gf_rank(Aug, T, 2 * T, NULL) != T) return 0;
        /* now Aug = [I | Z] with Z = X^{-1} Y (rows indexed by chosen columns); A = Z^T: A[i][j] = Z[j][i] */
        uint8_t A[16 * 16];
        for (int i = 0; i < T; i++) for (int j = 0; j < T; j++) A[i * T + j] = Aug[j * 2 * T + T + i];
        uint8_t Acp[16 * 16]; memcpy(Acp, A, T * T);
        if (gf_rank(Acp, T, T, NULL) != T) { if (verbose) printf("row %d: A singular\n", r); return 0; }
        int mu = -1;
        for (int c = 0; c < K; c++) {
            const uint8_t *v = VV + ((size_t)c * N + r) * T; uint8_t w[16];
            for (int i = 0; i < T; i++) { uint8_t s = 0; for (int j = 0; j < T; j++) s = GADD[s][GMUL[A[i * T + j]][v[j]]]; w[i] = s; }
            int c2 = c + SO; const uint8_t *u;
            if (c2 < K) { u = VV + ((size_t)c2 * N + r) * T; if (memcmp(w, u, T)) { if (verbose) printf("row %d: shift fails at column %d\n", r, c); return 0; } }
            else { u = VV + ((size_t)(c2 - K) * N + r) * T;
                /* w must be mu * u with one mu != 0 for the row */
                int j0 = -1; for (int j = 0; j < T; j++) if (u[j]) { j0 = j; break; }
                if (j0 < 0) return 0;
                int m = GMUL[w[j0]][GINV[u[j0]]];
                if (!m) return 0;
                if (mu < 0) mu = m; else if (mu != m) { if (verbose) printf("row %d: wrap scalar differs\n", r); return 0; }
                for (int j = 0; j < T; j++) if (GMUL[m][u[j]] != w[j]) { if (verbose) printf("row %d: wrap fails at column %d\n", r, c); return 0; }
            }
        }
    }
    return 1;
}
/* normal vector of a (T-1) x T matrix of rank T-1: returns 1 and n with M n = 0, n != 0; 0 if rank < T-1 */
static int normal_of(const uint8_t *rowsv, uint8_t *nvec) {
    uint8_t M[16 * 16]; int piv[16]; memcpy(M, rowsv, (T - 1) * T);
    int rk = gf_rank(M, T - 1, T, piv);
    if (rk < T - 1) { memset(nvec, 0, T); return 0; }
    int isp[16] = {0}; for (int i = 0; i < rk; i++) isp[piv[i]] = 1;
    int fcol = -1; for (int c = 0; c < T; c++) if (!isp[c]) { fcol = c; break; }
    memset(nvec, 0, T); nvec[fcol] = 1;
    for (int i = 0; i < rk; i++) nvec[piv[i]] = GNEG[M[i * T + fcol]];
    return 1;
}
