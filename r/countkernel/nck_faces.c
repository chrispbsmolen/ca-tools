/* nck_faces.c - locator and marking faces of the counting kernel.
 *
 * C_flexpos(x, t, vs, conv): N x k logical, TRUE = flexible
 *   position, i.e. for every t-subset S through the cell's column,
 *   the row's projection onto S has multiplicity >= 2. Two NA
 *   conventions (design decision D1):
 *     conv = 0 ("flexpos", the CAs convention, the DEFAULT): NA is
 *       an ordinary symbol that matches NA, exactly R duplicated()
 *       on the projected rows. Provably never flags a cell that
 *       conv = 1 would refuse (the more conservative of the two).
 *     conv = 1 ("coverage"): a row whose projection contains an
 *       NA contributes nothing to S and S imposes no constraint
 *       on that row's cells.
 *   Cells that are themselves NA are always TRUE (as in CAs::flexpos).
 *
 * C_markflex_pin(x, t, vs): the greedy first-coverer pass of
 *   markflex on rows in the GIVEN order (caller sorts). For each
 *   t-subset S in lexicographic order, scanning rows top down, a
 *   row with NA in its projection is skipped, and the first row
 *   attaining each tuple gets its t cells pinned (TRUE in the
 *   returned N x k logical). Unpinned cells are the flexible
 *   values; the R wrapper sets them NA.
 *
 * Symbols must be consecutive 0..vs[c]-1 (D2: enforced with an
 * informative error; the R wrapper normalizes 1-based input, D3).
 * Subset order and tuple linearization (leftmost fastest) match
 * count_core.c, CAs fasttab, and markflex's expand.grid.
 */

#include <R.h>
#include <Rinternals.h>
#include <string.h>

static int check_dims(SEXP xR, SEXP tR, SEXP vsR, int *N, int *k)
{
    SEXP dim = Rf_getAttrib(xR, R_DimSymbol);
    if (dim == R_NilValue || Rf_length(dim) != 2)
        Rf_error("x must be an integer matrix");
    *N = INTEGER(dim)[0]; *k = INTEGER(dim)[1];
    const int t = Rf_asInteger(tR);
    if (t < 2 || t > *k) Rf_error("need 2 <= t <= k");
    if (Rf_length(vsR) != *k) Rf_error("vs must have one entry per column");
    return t;
}

SEXP C_flexpos(SEXP xR, SEXP tR, SEXP vsR, SEXP convR)
{
    int N, k;
    const int t = check_dims(xR, tR, vsR, &N, &k);
    const int *x = INTEGER(xR);
    const int *vs = INTEGER(vsR);
    const int conv = Rf_asInteger(convR);   /* 0 = CAs convention, 1 = coverage */
    if (conv != 0 && conv != 1) Rf_error("conv must be 0 or 1");

    /* effective alphabet: the CAs convention counts NA as one extra symbol */
    int *w = (int *) R_alloc(k, sizeof(int));
    for (int c = 0; c < k; c++) {
        if (vs[c] < 1) Rf_error("all symbol counts must be >= 1");
        w[c] = vs[c] + (conv == 0 ? 1 : 0);
    }

    SEXP outR = PROTECT(Rf_allocMatrix(LGLSXP, N, k));
    int *out = LOGICAL(outR);
    for (R_xlen_t i = 0; i < (R_xlen_t) N * k; i++) out[i] = 1;

    /* max tuple space across subsets, from the t largest w */
    int *wsorted = (int *) R_alloc(k, sizeof(int));
    memcpy(wsorted, w, k * sizeof(int));
    for (int i = 1; i < k; i++) {
        int key = wsorted[i], j = i - 1;
        while (j >= 0 && wsorted[j] < key) { wsorted[j+1] = wsorted[j]; j--; }
        wsorted[j + 1] = key;
    }
    double vt_max_d = 1.0;
    for (int i = 0; i < t; i++) vt_max_d *= wsorted[i];
    if (vt_max_d > 2147483647.0)
        Rf_error("tuple space per column set exceeds 2^31; not supported");
    int *counts = (int *) R_alloc((int) vt_max_d, sizeof(int));
    int *ridx = (int *) R_alloc(N, sizeof(int));
    int *S  = (int *) R_alloc(t, sizeof(int));
    int *pd = (int *) R_alloc(t, sizeof(int));
    for (int i = 0; i < t; i++) S[i] = i;

    R_xlen_t ci = 0;
    for (;;) {
        int tot = 1;
        for (int j = 0; j < t; j++) { pd[j] = tot; tot *= w[S[j]]; }
        memset(counts, 0, (size_t) tot * sizeof(int));
        for (int r = 0; r < N; r++) {
            int idx = 0, ok = 1;
            for (int j = 0; j < t; j++) {
                int s = x[r + (R_xlen_t) S[j] * N];
                if (s == NA_INTEGER) {
                    if (conv == 1) { ok = 0; break; }
                    s = vs[S[j]];          /* NA as the extra symbol */
                } else if (s < 0 || s >= vs[S[j]])
                    Rf_error("symbol %d out of range 0..%d in column %d "
                             "(symbols must be consecutive from 0)",
                             s, vs[S[j]] - 1, S[j] + 1);
                idx += s * pd[j];
            }
            if (ok) { counts[idx]++; ridx[r] = idx; } else ridx[r] = -1;
        }
        /* a row unique in this projection pins its S-cells FALSE;
         * under coverage convention an NA projection imposes nothing */
        for (int r = 0; r < N; r++)
            if (ridx[r] >= 0 && counts[ridx[r]] == 1)
                for (int j = 0; j < t; j++)
                    out[r + (R_xlen_t) S[j] * N] = 0;

        ci++;
        int j = t - 1;
        while (j >= 0 && S[j] == k - t + j) j--;
        if (j < 0) break;
        S[j]++;
        for (int l = j + 1; l < t; l++) S[l] = S[l - 1] + 1;
        if ((ci & 255) == 0) R_CheckUserInterrupt();
    }

    /* cells already NA are flexible by definition */
    for (R_xlen_t i = 0; i < (R_xlen_t) N * k; i++)
        if (x[i] == NA_INTEGER) out[i] = 1;

    UNPROTECT(1);
    return outR;
}

SEXP C_markflex_pin(SEXP xR, SEXP tR, SEXP vsR)
{
    int N, k;
    const int t = check_dims(xR, tR, vsR, &N, &k);
    const int *x = INTEGER(xR);
    const int *vs = INTEGER(vsR);
    for (int c = 0; c < k; c++)
        if (vs[c] < 1) Rf_error("all symbol counts must be >= 1");

    SEXP pinR = PROTECT(Rf_allocMatrix(LGLSXP, N, k));
    int *pin = LOGICAL(pinR);
    memset(pin, 0, (size_t) N * k * sizeof(int));

    int *vsorted = (int *) R_alloc(k, sizeof(int));
    memcpy(vsorted, vs, k * sizeof(int));
    for (int i = 1; i < k; i++) {
        int key = vsorted[i], j = i - 1;
        while (j >= 0 && vsorted[j] < key) { vsorted[j+1] = vsorted[j]; j--; }
        vsorted[j + 1] = key;
    }
    double vt_max_d = 1.0;
    for (int i = 0; i < t; i++) vt_max_d *= vsorted[i];
    if (vt_max_d > 2147483647.0)
        Rf_error("tuple space per column set exceeds 2^31; not supported");
    unsigned char *seen = (unsigned char *) R_alloc((int) vt_max_d, 1);
    int *S  = (int *) R_alloc(t, sizeof(int));
    int *pd = (int *) R_alloc(t, sizeof(int));
    for (int i = 0; i < t; i++) S[i] = i;

    R_xlen_t ci = 0;
    for (;;) {
        int tot = 1;
        for (int j = 0; j < t; j++) { pd[j] = tot; tot *= vs[S[j]]; }
        memset(seen, 0, (size_t) tot);
        for (int r = 0; r < N; r++) {
            int idx = 0, ok = 1;
            for (int j = 0; j < t; j++) {
                const int s = x[r + (R_xlen_t) S[j] * N];
                if (s == NA_INTEGER) { ok = 0; break; }   /* NA covers nothing */
                if (s < 0 || s >= vs[S[j]])
                    Rf_error("symbol %d out of range 0..%d in column %d "
                             "(symbols must be consecutive from 0)",
                             s, vs[S[j]] - 1, S[j] + 1);
                idx += s * pd[j];
            }
            if (ok && !seen[idx]) {      /* first coverer pins its cells */
                seen[idx] = 1;
                for (int j = 0; j < t; j++)
                    pin[r + (R_xlen_t) S[j] * N] = 1;
            }
        }
        ci++;
        int j = t - 1;
        while (j >= 0 && S[j] == k - t + j) j--;
        if (j < 0) break;
        S[j]++;
        for (int l = j + 1; l < t; l++) S[l] = S[l - 1] + 1;
        if ((ci & 255) == 0) R_CheckUserInterrupt();
    }
    UNPROTECT(1);
    return pinR;
}
