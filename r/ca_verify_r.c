/* ca_verify.c - fast strength-t coverage checker for covering arrays,
 * R .Call interface.
 *
 * Port of the standalone ca_verify CLI tool (C. Smolen, ca-tools) to a
 * native R entry point: the array arrives as an R integer matrix (no
 * files, no system calls), R's NA_integer_ is the wildcard ("flexible
 * value", counts as every symbol), and results return as an R list.
 *
 * Threading: optional OpenMP (portable through R's SHLIB_OPENMP_CFLAGS
 * mechanism, including Windows/Rtools); falls back to single-threaded
 * cleanly when OpenMP is unavailable. No R API calls occur inside the
 * parallel region (R is not thread-safe); all SEXP construction happens
 * after the join.
 *
 * Symbols are expected as 0..v-1 (the R wrapper auto-shifts 1..v input).
 */
#include <R.h>
#include <Rinternals.h>
#include <R_ext/Rdynload.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

#ifdef _OPENMP
#include <omp.h>
#endif

#define MAX_T 20

typedef struct {
    long long combos;
    long long gaps;
    long long missing;
    int n_ex;
    int max_ex;
    int *ex_cols;          /* max_ex x T, 0-based column indices */
    long long *ex_tuple;   /* max_ex tuple ranks                 */
} Acc;

/* advance combination c[0..t-1] over k columns; return 0 when exhausted */
static int next_comb(int *c, int k, int t) {
    int i = t - 1;
    while (i >= 0 && c[i] == k - t + i) i--;
    if (i < 0) return 0;
    c[i]++;
    for (int j = i + 1; j < t; j++) c[j] = c[j - 1] + 1;
    return 1;
}

/* mark tuples exhibited by row r on columns c[]; NA = wildcard */
static void mark_row(uint64_t *bm, const int *m, int nrow, int r,
                     const int *c, int t, int v, const long long *mult) {
    int wpos[MAX_T], nw = 0;
    long long base = 0;
    for (int j = 0; j < t; j++) {
        int s = m[r + (long long)c[j] * nrow];
        if (s == NA_INTEGER) wpos[nw++] = j;
        else base += (long long)s * mult[j];
    }
    if (nw == 0) {
        bm[base >> 6] |= 1ULL << (base & 63);
        return;
    }
    long long nexp = 1;
    for (int i = 0; i < nw; i++) nexp *= v;
    for (long long e = 0; e < nexp; e++) {
        long long idx = base, ee = e;
        for (int i = 0; i < nw; i++) {
            idx += (ee % v) * mult[wpos[i]];
            ee /= v;
        }
        bm[idx >> 6] |= 1ULL << (idx & 63);
    }
}

SEXP C_ca_verify(SEXP mat, SEXP t_, SEXP v_, SEXP nthreads_, SEXP maxreport_)
{
    if (!isInteger(mat) || !isMatrix(mat))
        error("internal: matrix of integers expected");
    const int *m = INTEGER(mat);
    const int nrow = Rf_nrows(mat), ncol = Rf_ncols(mat);
    const int t = asInteger(t_), v = asInteger(v_);
    int nt = asInteger(nthreads_);
    const int max_ex = asInteger(maxreport_);

    if (t < 1 || t > MAX_T) error("t must be in 1..%d", MAX_T);
    if (v < 2) error("v must be >= 2");
    if (ncol < t) error("array has fewer columns (%d) than t (%d)", ncol, t);
    if (nt < 1) nt = 1;
    if (nt > 64) nt = 64;

    long long vt = 1;
    for (int i = 0; i < t; i++) {
        vt *= v;
        if (vt > (1LL << 31))
            error("v^t too large (limit 2^31 tuples per column set)");
    }
    long long mult[MAX_T], mm = 1;
    for (int j = t - 1; j >= 0; j--) { mult[j] = mm; mm *= v; }

    /* validate symbol range once, outside the parallel region */
    for (long long i = 0; i < (long long)nrow * ncol; i++) {
        int s = m[i];
        if (s != NA_INTEGER && (s < 0 || s >= v))
            error("symbol %d out of range 0..%d (after any auto-shift)", s, v - 1);
    }

#ifndef _OPENMP
    nt = 1;
#endif

    Acc *acc = (Acc *) calloc(nt, sizeof(Acc));
    if (!acc) error("allocation failure");
    int alloc_fail = 0;
    for (int i = 0; i < nt; i++) {
        acc[i].max_ex = max_ex;
        acc[i].ex_cols = (int *) malloc(sizeof(int) * (size_t)(max_ex > 0 ? max_ex : 1) * t);
        acc[i].ex_tuple = (long long *) malloc(sizeof(long long) * (size_t)(max_ex > 0 ? max_ex : 1));
        if (!acc[i].ex_cols || !acc[i].ex_tuple) alloc_fail = 1;
    }
    const long long words = (vt + 63) >> 6;

#ifdef _OPENMP
#pragma omp parallel num_threads(nt)
#endif
    {
#ifdef _OPENMP
        const int tid = omp_get_thread_num();
        const int nthr = omp_get_num_threads();
#else
        const int tid = 0, nthr = 1;
#endif
        if (!alloc_fail) {
            uint64_t *bm = (uint64_t *) malloc(words * sizeof(uint64_t));
            if (!bm) {
                alloc_fail = 1;      /* benign race: any thread may set it */
            } else {
                Acc *w = &acc[tid];
                int c[MAX_T];
                for (int j = 0; j < t; j++) c[j] = j;
                long long rank = 0;
                do {
                    if (rank++ % nthr != tid) continue;
                    memset(bm, 0, words * sizeof(uint64_t));
                    for (int r = 0; r < nrow; r++)
                        mark_row(bm, m, nrow, r, c, t, v, mult);
                    long long covered = 0;
                    for (long long i = 0; i < words; i++)
                        covered += __builtin_popcountll(bm[i]);
                    w->combos++;
                    if (covered != vt) {
                        w->gaps++;
                        w->missing += vt - covered;
                        if (w->n_ex < w->max_ex) {
                            for (long long idx = 0; idx < vt; idx++) {
                                if (!(bm[idx >> 6] & (1ULL << (idx & 63)))) {
                                    memcpy(w->ex_cols + (size_t)w->n_ex * t,
                                           c, t * sizeof(int));
                                    w->ex_tuple[w->n_ex] = idx;
                                    w->n_ex++;
                                    break;
                                }
                            }
                        }
                    }
                } while (next_comb(c, ncol, t));
                free(bm);
            }
        }
    }

    if (alloc_fail) {
        for (int i = 0; i < nt; i++) { free(acc[i].ex_cols); free(acc[i].ex_tuple); }
        free(acc);
        error("allocation failure in worker");
    }

    long long combos = 0, gaps = 0, missing = 0;
    int n_ex = 0;
    for (int i = 0; i < nt; i++) {
        combos += acc[i].combos;
        gaps += acc[i].gaps;
        missing += acc[i].missing;
        n_ex += acc[i].n_ex;
    }
    if (n_ex > max_ex) n_ex = max_ex;

    /* examples: n_ex x (t cols 1-based, then t tuple symbols 0-based) */
    SEXP ex = PROTECT(allocMatrix(INTSXP, n_ex, 2 * t));
    int *e = INTEGER(ex);
    int row = 0;
    for (int i = 0; i < nt && row < n_ex; i++) {
        for (int j = 0; j < acc[i].n_ex && row < n_ex; j++, row++) {
            for (int q = 0; q < t; q++)
                e[row + (long long)q * n_ex] =
                    acc[i].ex_cols[(size_t)j * t + q] + 1;
            long long idx = acc[i].ex_tuple[j];
            int digs[MAX_T];
            for (int q = t - 1; q >= 0; q--) { digs[q] = (int)(idx % v); idx /= v; }
            for (int q = 0; q < t; q++)
                e[row + (long long)(t + q) * n_ex] = digs[q];
        }
    }
    for (int i = 0; i < nt; i++) { free(acc[i].ex_cols); free(acc[i].ex_tuple); }
    free(acc);

    const char *names[] = {"covered", "colsets", "gaps", "missing_tuples",
                           "examples", ""};
    SEXP out = PROTECT(Rf_mkNamed(VECSXP, names));
    SET_VECTOR_ELT(out, 0, ScalarLogical(gaps == 0));
    SET_VECTOR_ELT(out, 1, ScalarReal((double)combos));
    SET_VECTOR_ELT(out, 2, ScalarReal((double)gaps));
    SET_VECTOR_ELT(out, 3, ScalarReal((double)missing));
    SET_VECTOR_ELT(out, 4, ex);
    UNPROTECT(2);
    return out;
}

static const R_CallMethodDef CallEntries[] = {
    {"C_ca_verify", (DL_FUNC) &C_ca_verify, 5},
    {NULL, NULL, 0}
};

void R_init_caverify(DllInfo *dll)
{
    R_registerRoutines(dll, NULL, CallEntries, NULL, NULL);
    R_useDynamicSymbols(dll, FALSE);
}
