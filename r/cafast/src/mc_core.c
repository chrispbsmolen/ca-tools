#include <R.h>
#include <Rinternals.h>
#include <stdlib.h>
#include <string.h>

/* rows i, j of D (N x k, column-major, integers) are "disjoint" when they differ in every column.
   A set of pairwise disjoint rows can all be made constant by permuting symbols within columns.
   C_maxclique_disjoint: largest set of pairwise disjoint rows, at most v of them; if `force`
   (1-based row indices) is non-empty, prefer a largest clique containing all of them. */

static int N, K, V;
static const int *D;
static int **adj; static int *deg;

static int disjoint(int i, int j) {
    for (int c = 0; c < K; c++) if (D[i + (size_t)c * N] == D[j + (size_t)c * N]) return 0;
    return 1;
}

static int best_size; static int *best_set; static int *cur; static int cur_size; static int **bufs;

/* candidates: rows adjacent to all of cur; recursion over candidate list */
static void extend(int *cand, int ncand) {
    if (cur_size > best_size) { best_size = cur_size; memcpy(best_set, cur, sizeof(int) * cur_size); }
    if (cur_size == V) return;
    if (cur_size + ncand <= best_size) return;
    for (int a = 0; a < ncand; a++) {
        int u = cand[a];
        if (cur_size + (ncand - a) <= best_size) return;
        /* new candidates: those after a that are adjacent to u */
        int *nc = bufs[cur_size + 1]; int nn = 0;
        for (int b = a + 1; b < ncand; b++) { int w = cand[b];
            /* adjacency test via sorted adj list of u (binary search) */
            int lo = 0, hi = deg[u] - 1, found = 0;
            while (lo <= hi) { int m = (lo + hi) / 2; if (adj[u][m] == w) { found = 1; break; } if (adj[u][m] < w) lo = m + 1; else hi = m - 1; }
            if (found) nc[nn++] = w; }
        cur[cur_size++] = u;
        extend(nc, nn);
        cur_size--;
        if (best_size == V) return;
    }
}

SEXP C_maxclique_disjoint(SEXP Dm, SEXP nrow, SEXP ncol, SEXP nlev, SEXP force) {
    N = INTEGER(nrow)[0]; K = INTEGER(ncol)[0]; V = INTEGER(nlev)[0]; D = INTEGER(Dm);
    int nf = LENGTH(force); const int *F = INTEGER(force);
    /* adjacency lists: for each i, sorted j > i and j < i (full symmetric lists) */
    deg = (int *) R_alloc(N, sizeof(int)); memset(deg, 0, sizeof(int) * N);
    long long total = 0;
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) if (j != i && disjoint(i, j)) { deg[i]++; total++; }
    adj = (int **) R_alloc(N, sizeof(int *));
    int *pool = (int *) R_alloc(total > 0 ? total : 1, sizeof(int)); long long off = 0;
    for (int i = 0; i < N; i++) { adj[i] = pool + off; off += deg[i]; deg[i] = 0; }
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) if (j != i && disjoint(i, j)) adj[i][deg[i]++] = j;
    best_set = (int *) R_alloc(V, sizeof(int)); cur = (int *) R_alloc(V + 1, sizeof(int)); best_size = 0; cur_size = 0;
    bufs = (int **) R_alloc(V + 2, sizeof(int *)); for (int d = 0; d < V + 2; d++) bufs[d] = (int *) R_alloc(N > 0 ? N : 1, sizeof(int));
    /* forced rows first: they must be pairwise disjoint; start the clique with them */
    int ok = 1;
    for (int a = 0; a < nf && ok; a++) for (int b = a + 1; b < nf; b++) if (!disjoint(F[a] - 1, F[b] - 1)) { ok = 0; break; }
    int *cand = (int *) R_alloc(N, sizeof(int)); int ncand = 0;
    if (nf > 0 && ok) {
        for (int a = 0; a < nf; a++) cur[cur_size++] = F[a] - 1;
        for (int j = 0; j < N; j++) { int fine = 1; for (int a = 0; a < nf; a++) if (F[a] - 1 == j || !disjoint(F[a] - 1, j)) { fine = 0; break; } if (fine) cand[ncand++] = j; }
        extend(cand, ncand);
        int forced_best = best_size;
        /* also compute the unconstrained maximum; if larger, prefer it (her semantics: largest clique first) */
        int *save = (int *) R_alloc(V, sizeof(int)); memcpy(save, best_set, sizeof(int) * forced_best);
        cur_size = 0; best_size = 0; ncand = 0; for (int j = 0; j < N; j++) cand[ncand++] = j;
        extend(cand, ncand);
        if (best_size <= forced_best) { best_size = forced_best; memcpy(best_set, save, sizeof(int) * forced_best); }
    } else {
        for (int j = 0; j < N; j++) cand[ncand++] = j;
        extend(cand, ncand);
    }
    SEXP out = PROTECT(allocVector(INTSXP, best_size));
    for (int i = 0; i < best_size; i++) INTEGER(out)[i] = best_set[i] + 1;
    UNPROTECT(1);
    return out;
}
