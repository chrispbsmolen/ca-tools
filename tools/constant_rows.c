/* constant_rows.c - the largest number of rows of a covering array that
   can be made constant by permuting symbols within columns.

   Two rows can both be made constant exactly when they differ in every
   column in which both are non-missing (a missing cell matches nothing).
   A set of rows can all be made constant exactly when they are pairwise
   such, so the answer is the largest clique in that graph, and it is at
   most v. This is the computation of cafast::maxconstant_c (mc_core.c in
   r/cafast), written as a standalone program so that the submission check
   can record the number for every array it verifies, with no R on the
   runner. The two give the same number; tools/constant_rows_check.R
   compares them over table/arrays.

   Input conventions are those of ca_verify.c: entries separated by
   spaces, tabs or commas, blank lines skipped, symbols 0..v-1 or 1..v
   (detected), don't-care entries NA (any case), '-', '*', 'x', 'X', -1.

   Usage: constant_rows FILE v
   Output: one line "constant_rows C of N rows, k columns, v symbols"
   followed by "rows: i1 i2 ..." (1-based indices of one largest set).
   Exit 0 on success, 2 on a read error. A row consisting only of
   don't-care entries is an error, as it is for cafast::maxconstant_c.
   Agreement with cafast assumes the rows are distinct: cafast 0.1.0
   counts a duplicated constant row twice (its nconstant == v shortcut),
   this program never does.

   Build: cc -O2 -o constant_rows constant_rows.c
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <strings.h>

#define NA_CELL (-1)

static int N, K, V;
static int *D;              /* row-major N x K, NA_CELL for don't care */
static int **adj; static int *deg;
static int best_size; static int *best_set; static int *cur; static int cur_size; static int **bufs;

static int disjoint(int i, int j) {
    const int *a = D + (size_t)i * K, *b = D + (size_t)j * K;
    for (int c = 0; c < K; c++)
        if (a[c] != NA_CELL && b[c] != NA_CELL && a[c] == b[c]) return 0;
    return 1;
}

static int adjacent(int u, int w) {
    int lo = 0, hi = deg[u] - 1;
    while (lo <= hi) { int m = (lo + hi) / 2; if (adj[u][m] == w) return 1; if (adj[u][m] < w) lo = m + 1; else hi = m - 1; }
    return 0;
}

static void extend(int *cand, int ncand) {
    if (cur_size > best_size) { best_size = cur_size; memcpy(best_set, cur, sizeof(int) * cur_size); }
    if (cur_size == V) return;
    if (cur_size + ncand <= best_size) return;
    for (int a = 0; a < ncand; a++) {
        int u = cand[a];
        if (cur_size + (ncand - a) <= best_size) return;
        int *nc = bufs[cur_size + 1]; int nn = 0;
        for (int b = a + 1; b < ncand; b++) if (adjacent(u, cand[b])) nc[nn++] = cand[b];
        cur[cur_size++] = u;
        extend(nc, nn);
        cur_size--;
        if (best_size == V) return;
    }
}

static int read_array(const char *path, int v) {
    FILE *f = fopen(path, "r");
    if (!f) { fprintf(stderr, "cannot open %s\n", path); return 0; }
    size_t cap = 1 << 16, n = 0; int *buf = malloc(cap * sizeof(int));
    int cols = -1, col = 0, rows = 0, minv = 1 << 30, maxv = -1;
    char tok[64]; int tl = 0; int c; int any = 0;
    for (;;) {
        c = fgetc(f);
        int sep = (c == ' ' || c == '\t' || c == ',' || c == '\r' || c == '\n' || c == EOF);
        if (!sep) { if (tl >= 63) { fprintf(stderr, "token too long\n"); fclose(f); free(buf); return 0; } tok[tl++] = (char)c; continue; }
        if (tl > 0) {
            tok[tl] = 0; int val;
            if (!strcmp(tok, "-") || !strcmp(tok, "*") || !strcmp(tok, "x") || !strcmp(tok, "X") ||
                !strcmp(tok, "-1") || !strcasecmp(tok, "NA")) val = NA_CELL;
            else { char *e; long x = strtol(tok, &e, 10); if (*e) { fprintf(stderr, "bad token %s\n", tok); fclose(f); free(buf); return 0; }
                   val = (int)x; if (val < minv) minv = val; if (val > maxv) maxv = val; }
            if (n == cap) { cap *= 2; buf = realloc(buf, cap * sizeof(int)); }
            buf[n++] = val; col++; any = 1; tl = 0;
        }
        if (c == '\n' || c == EOF) {
            if (any) { if (cols < 0) cols = col; else if (col != cols) { fprintf(stderr, "line %d has %d entries, expected %d\n", rows + 1, col, cols); fclose(f); free(buf); return 0; }
                       rows++; }
            col = 0; any = 0;
            if (c == EOF) break;
        }
    }
    fclose(f);
    if (rows == 0 || cols <= 0) { fprintf(stderr, "empty array\n"); free(buf); return 0; }
    for (int i = 0; i < rows; i++) { int allna = 1; for (int c2 = 0; c2 < cols; c2++) if (buf[(size_t)i * cols + c2] != NA_CELL) { allna = 0; break; }
        if (allna) { fprintf(stderr, "row %d consists only of don't-care entries\n", i + 1); free(buf); return 0; } }
    int shift = (minv == 1 && maxv == v) ? 1 : 0;   /* symbols 1..v */
    if (maxv - shift > v - 1 || minv - shift < 0) { fprintf(stderr, "symbols outside 0..%d\n", v - 1); free(buf); return 0; }
    N = rows; K = cols; V = v; D = buf;
    if (shift) for (size_t i = 0; i < n; i++) if (D[i] != NA_CELL) D[i] -= 1;
    return 1;
}

int main(int argc, char **argv) {
    if (argc != 3) { fprintf(stderr, "usage: constant_rows FILE v\n"); return 2; }
    int v = atoi(argv[2]);
    if (v < 2 || !read_array(argv[1], v)) return 2;
    /* the disjoint pairs, found once and kept as (i, j) with i < j */
    deg = calloc(N, sizeof(int));
    size_t pcap = 1 << 16, np = 0; int *pairs = malloc(pcap * 2 * sizeof(int));
    for (int i = 0; i < N; i++) for (int j = i + 1; j < N; j++) if (disjoint(i, j)) {
        if (np == pcap) { pcap *= 2; pairs = realloc(pairs, pcap * 2 * sizeof(int));
            if (!pairs) { fprintf(stderr, "constant_rows: out of memory (%zu disjoint pairs)\n", np); return 3; } }
        pairs[2 * np] = i; pairs[2 * np + 1] = j; np++; deg[i]++; deg[j]++; }
    adj = malloc(N * sizeof(int *));
    int *pool = malloc((np > 0 ? 2 * np : 1) * sizeof(int)); long long off = 0;
    for (int i = 0; i < N; i++) { adj[i] = pool + off; off += deg[i]; deg[i] = 0; }
    for (size_t q = 0; q < np; q++) { int i = pairs[2 * q], j = pairs[2 * q + 1]; adj[i][deg[i]++] = j; adj[j][deg[j]++] = i; }
    free(pairs);
    /* pairs come in increasing (i, j) order, so every list is sorted */
    best_set = malloc(V * sizeof(int)); cur = malloc((V + 1) * sizeof(int)); best_size = 0; cur_size = 0;
    bufs = malloc((V + 2) * sizeof(int *)); for (int d = 0; d < V + 2; d++) bufs[d] = malloc((N > 0 ? N : 1) * sizeof(int));
    int *cand = malloc(N * sizeof(int)); for (int j = 0; j < N; j++) cand[j] = j;
    extend(cand, N);
    printf("constant_rows %d of %d rows, %d columns, %d symbols\n", best_size, N, K, V);
    printf("rows:"); for (int i = 0; i < best_size; i++) printf(" %d", best_set[i] + 1); printf("\n");
    return 0;
}
