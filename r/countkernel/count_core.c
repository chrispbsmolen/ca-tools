/* count_core.c - the counting kernel's core (increment 1)
 *
 * For every t-subset S of columns (lexicographic order, matching
 * CAs nchoosek and R combn), tabulate the multiplicity of every
 * value tuple over the rows of an N x k integer matrix. A row with
 * an NA anywhere in the projection contributes nothing (the
 * coverage/markflex convention; the flexpos NA convention lives in
 * nck_faces.c, C_flexpos with conv = 0).
 *
 * Tuple linearization is leftmost-factor-fastest (strides
 * cumprod(c(1, vs[S]))), matching CAs fasttab and R array indexing.
 *
 * Returns list(tots, ncovered, missing, rowmult) where rowmult is
 * an N x choose(k,t) matrix of per-row projection multiplicities
 * (0 for a row with NA in the projection), or NULL when not
 * requested. From these derive: coverage backend (tots, ncovered,
 * missing), flexpos-style redundancy (rowmult >= 2 over all S
 * through a column), uniquecount (rowmult == 1).
 *
 * Single-threaded correct first; interrupt-checked between batches.
 * Part of ca-tools. Validation: oracle_count.R (pure R, no shared
 * logic) and CAs::coverage cross-checks in test_count_core.R.
 */

#include <R.h>
#include <Rinternals.h>
#include <string.h>

SEXP C_count_core(SEXP xR, SEXP tR, SEXP vsR, SEXP wantRowmultR)
{
    const int t = Rf_asInteger(tR);
    SEXP dim = Rf_getAttrib(xR, R_DimSymbol);
    const int N = INTEGER(dim)[0], k = INTEGER(dim)[1];
    const int *x = INTEGER(xR);
    const int *vs = INTEGER(vsR);
    const int wantRM = Rf_asInteger(wantRowmultR);

    if (t < 1 || t > k) Rf_error("need 1 <= t <= k");
    for (int c = 0; c < k; c++)
        if (vs[c] < 1) Rf_error("all symbol counts must be >= 1");

    /* number of column subsets, exactly */
    double ncomb_d = 1.0;
    for (int i = 0; i < t; i++) ncomb_d = ncomb_d * (k - i) / (i + 1.0);
    R_xlen_t ncomb = (R_xlen_t)(ncomb_d + 0.5);

    /* largest tuple space = product of the t largest vs; guard 2^31 */
    int *vsorted = (int *) R_alloc(k, sizeof(int));
    memcpy(vsorted, vs, k * sizeof(int));
    for (int i = 1; i < k; i++) {          /* insertion sort desc */
        int key = vsorted[i], j = i - 1;
        while (j >= 0 && vsorted[j] < key) { vsorted[j + 1] = vsorted[j]; j--; }
        vsorted[j + 1] = key;
    }
    double vt_max_d = 1.0;
    for (int i = 0; i < t; i++) vt_max_d *= vsorted[i];
    if (vt_max_d > 2147483647.0)
        Rf_error("tuple space per column set exceeds 2^31; not supported");
    const int vt_max = (int) vt_max_d;

    SEXP totsR = PROTECT(Rf_allocVector(REALSXP, ncomb));
    SEXP ncovR = PROTECT(Rf_allocVector(REALSXP, ncomb));
    SEXP missR = PROTECT(Rf_allocVector(REALSXP, ncomb));
    double *tots = REAL(totsR), *ncov = REAL(ncovR), *miss = REAL(missR);
    SEXP rmR = R_NilValue;
    double *rm = NULL;
    int nprot = 3;
    if (wantRM) {
        if ((double) N * (double) ncomb > 2e9)
            Rf_error("rowmult matrix would exceed 2e9 cells; not supported");
        rmR = PROTECT(Rf_allocMatrix(REALSXP, N, (int) ncomb));
        rm = REAL(rmR);
        nprot++;
    }

    int *S  = (int *) R_alloc(t, sizeof(int));
    int *pd = (int *) R_alloc(t, sizeof(int));
    int *counts = (int *) R_alloc(vt_max, sizeof(int));
    int *ridx = (int *) R_alloc(N, sizeof(int));   /* row's cell, -1 = NA */
    for (int i = 0; i < t; i++) S[i] = i;

    R_xlen_t ci = 0;
    for (;;) {
        /* leftmost-fastest strides and total for this subset */
        int tot = 1;
        for (int j = 0; j < t; j++) { pd[j] = tot; tot *= vs[S[j]]; }
        memset(counts, 0, (size_t) tot * sizeof(int));

        for (int r = 0; r < N; r++) {
            int idx = 0, ok = 1;
            for (int j = 0; j < t; j++) {
                const int s = x[r + (R_xlen_t) S[j] * N];
                if (s == NA_INTEGER) { ok = 0; break; }
                if (s < 0 || s >= vs[S[j]])
                    Rf_error("symbol %d out of range 0..%d in column %d",
                             s, vs[S[j]] - 1, S[j] + 1);
                idx += s * pd[j];
            }
            if (ok) { counts[idx]++; ridx[r] = idx; } else ridx[r] = -1;
        }

        int covered = 0;
        for (int c = 0; c < tot; c++) if (counts[c]) covered++;
        tots[ci] = (double) tot;
        ncov[ci] = (double) covered;
        miss[ci] = (double) (tot - covered);
        if (wantRM)
            for (int r = 0; r < N; r++)
                rm[r + ci * N] = (ridx[r] >= 0) ? (double) counts[ridx[r]] : 0.0;

        ci++;
        /* next t-subset in lexicographic order */
        int j = t - 1;
        while (j >= 0 && S[j] == k - t + j) j--;
        if (j < 0) break;
        S[j]++;
        for (int l = j + 1; l < t; l++) S[l] = S[l - 1] + 1;
        if ((ci & 255) == 0) R_CheckUserInterrupt();
    }

    SEXP out = PROTECT(Rf_allocVector(VECSXP, 4)); nprot++;
    SET_VECTOR_ELT(out, 0, totsR);
    SET_VECTOR_ELT(out, 1, ncovR);
    SET_VECTOR_ELT(out, 2, missR);
    SET_VECTOR_ELT(out, 3, rmR);
    SEXP nm = PROTECT(Rf_allocVector(STRSXP, 4)); nprot++;
    SET_STRING_ELT(nm, 0, Rf_mkChar("tots"));
    SET_STRING_ELT(nm, 1, Rf_mkChar("ncovered"));
    SET_STRING_ELT(nm, 2, Rf_mkChar("missing"));
    SET_STRING_ELT(nm, 3, Rf_mkChar("rowmult"));
    Rf_setAttrib(out, R_NamesSymbol, nm);
    UNPROTECT(nprot);
    return out;
}
