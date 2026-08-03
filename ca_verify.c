/* ca_verify - fast strength-t coverage checker for covering arrays.
 *
 * Verifies that an N x k array over v symbols covers every t-way interaction:
 * for every choice of t columns and every one of the v^t value tuples, some
 * row exhibits that tuple. This is the certificate check for a covering array.
 *
 * Input format: plain text, one row per line, entries separated by spaces,
 * tabs or commas. Symbols may be 0..v-1 or 1..v (auto-shifted). A '-', '*',
 * 'NA' or 'x' entry is a wildcard (flexible value) and counts as every symbol.
 *
 * Usage: ca_verify FILE t v [threads]
 * Exit status: 0 = full coverage verified, 1 = coverage gaps found, 2 = error.
 *
 * Written to be small, dependency-free and auditable. Multithreaded over
 * column combinations; memory is one v^t bitmap per thread.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <ctype.h>
#include <pthread.h>

#define MAX_MISS_REPORT 10
#define WILDCARD -1

static int N, K, T, V;
static long long VT;              /* v^t tuples per column set */
static int8_t *A;                 /* N x K array, row-major     */
static int NT = 4;

typedef struct {
    int tid;
    long long combos_checked;
    long long gaps;               /* column sets with missing tuples */
    long long missing_tuples;     /* total missing tuples             */
    /* first few missing examples: columns + tuple index */
    int miss_cols[MAX_MISS_REPORT][32];
    long long miss_tuple[MAX_MISS_REPORT];
    int n_miss;
} Work;

/* advance combination c[0..T-1] over K columns; return 0 when exhausted */
static int next_comb(int *c) {
    int i = T - 1;
    while (i >= 0 && c[i] == K - T + i) i--;
    if (i < 0) return 0;
    c[i]++;
    for (int j = i + 1; j < T; j++) c[j] = c[j-1] + 1;
    return 1;
}

/* mark tuples exhibited by row r on columns c[], honoring wildcards */
static void mark_row(uint64_t *bm, const int8_t *row, const int *c) {
    /* iterate over wildcard expansions; non-wildcard digits fixed */
    int wpos[32], nw = 0;
    long long base = 0;
    for (int j = 0; j < T; j++) {
        int8_t s = row[c[j]];
        if (s == WILDCARD) { wpos[nw++] = j; }
    }
    /* compute base index with wildcards as 0 */
    long long mult[32];
    long long m = 1;
    for (int j = T - 1; j >= 0; j--) { mult[j] = m; m *= V; }
    for (int j = 0; j < T; j++) {
        int8_t s = row[c[j]];
        base += (long long)(s == WILDCARD ? 0 : s) * mult[j];
    }
    if (nw == 0) {
        bm[base >> 6] |= 1ULL << (base & 63);
        return;
    }
    /* expand wildcards (rare; nw small) */
    long long nexp = 1;
    for (int i = 0; i < nw; i++) nexp *= V;
    for (long long e = 0; e < nexp; e++) {
        long long idx = base, ee = e;
        for (int i = 0; i < nw; i++) {
            idx += (ee % V) * mult[wpos[i]];
            ee /= V;
        }
        bm[idx >> 6] |= 1ULL << (idx & 63);
    }
}

static void *worker(void *arg) {
    Work *w = (Work *)arg;
    int c[32];
    for (int j = 0; j < T; j++) c[j] = j;
    long long words = (VT + 63) >> 6;
    uint64_t *bm = calloc(words, sizeof(uint64_t));
    if (!bm) { fprintf(stderr, "alloc fail\n"); exit(2); }
    long long rank = 0;
    do {
        if (rank++ % NT != w->tid) continue;
        memset(bm, 0, words * sizeof(uint64_t));
        for (int r = 0; r < N; r++) mark_row(bm, A + (long long)r * K, c);
        /* count coverage */
        long long covered = 0;
        for (long long i = 0; i < words; i++) covered += __builtin_popcountll(bm[i]);
        w->combos_checked++;
        if (covered != VT) {
            w->gaps++;
            w->missing_tuples += VT - covered;
            if (w->n_miss < MAX_MISS_REPORT) {
                /* find first missing tuple */
                for (long long idx = 0; idx < VT; idx++) {
                    if (!(bm[idx >> 6] & (1ULL << (idx & 63)))) {
                        memcpy(w->miss_cols[w->n_miss], c, T * sizeof(int));
                        w->miss_tuple[w->n_miss] = idx;
                        w->n_miss++;
                        break;
                    }
                }
            }
        }
    } while (next_comb(c));
    free(bm);
    return NULL;
}

int main(int argc, char **argv) {
    if (argc < 4) {
        fprintf(stderr, "usage: %s FILE t v [threads]\n", argv[0]);
        return 2;
    }
    const char *path = argv[1];
    T = atoi(argv[2]); V = atoi(argv[3]);
    if (argc > 4) NT = atoi(argv[4]);
    if (T < 1 || T > 31 || V < 2 || NT < 1 || NT > 64) {
        fprintf(stderr, "bad parameters\n"); return 2;
    }
    VT = 1;
    for (int i = 0; i < T; i++) {
        VT *= V;
        if (VT > (1LL << 40)) { fprintf(stderr, "v^t too large\n"); return 2; }
    }

    /* ---- read the array ---- */
    FILE *f = fopen(path, "r");
    if (!f) { fprintf(stderr, "cannot open %s\n", path); return 2; }
    int cap = 1 << 20;
    int8_t *buf = malloc(cap);
    int n_entries = 0, cols = -1, cur_cols = 0;
    int minv = 127, maxv = -2;
    char line[1 << 16];
    while (fgets(line, sizeof line, f)) {
        char *p = line;
        cur_cols = 0;
        int any = 0;
        while (*p) {
            while (*p && (*p == ' ' || *p == '\t' || *p == ',' || *p == '\r' || *p == '\n')) p++;
            if (!*p) break;
            int val;
            if (*p == '-' && !isdigit((unsigned char)p[1])) { val = WILDCARD; p++; }
            else if ((*p == '*') || (*p == 'x') || (*p == 'X')) { val = WILDCARD; p++; }
            else if ((p[0] == 'N' || p[0] == 'n') && (p[1] == 'A' || p[1] == 'a')) { val = WILDCARD; p += 2; }
            else if (isdigit((unsigned char)*p) || (*p == '-' && isdigit((unsigned char)p[1]))) {
                val = (int)strtol(p, &p, 10);
            } else { p++; continue; }
            if (n_entries >= cap) { cap <<= 1; buf = realloc(buf, cap); }
            buf[n_entries++] = (int8_t)val;
            if (val != WILDCARD) { if (val < minv) minv = val; if (val > maxv) maxv = val; }
            cur_cols++; any = 1;
        }
        if (!any) continue;
        if (cols == -1) cols = cur_cols;
        else if (cur_cols != cols) {
            fprintf(stderr, "ragged row (got %d entries, expected %d)\n", cur_cols, cols);
            return 2;
        }
    }
    fclose(f);
    if (cols < T) { fprintf(stderr, "fewer columns than t\n"); return 2; }
    K = cols; N = n_entries / cols;

    /* auto-shift 1-based symbols */
    int shift = 0;
    if (minv == 1 && maxv == V) shift = 1;
    else if (minv == 0 && maxv == V - 1) shift = 0;
    else if (maxv - shift >= V || minv < WILDCARD) {
        fprintf(stderr, "symbols out of range for v=%d (saw %d..%d)\n", V, minv, maxv);
        return 2;
    }
    A = buf;
    if (shift)
        for (int i = 0; i < n_entries; i++)
            if (A[i] != WILDCARD) A[i] -= 1;

    fprintf(stderr, "read %d rows x %d columns over v=%d (t=%d, %d threads)\n",
            N, K, V, T, NT);

    /* ---- verify ---- */
    pthread_t th[64];
    Work w[64];
    memset(w, 0, sizeof w);
    for (int i = 0; i < NT; i++) { w[i].tid = i; pthread_create(&th[i], NULL, worker, &w[i]); }
    long long combos = 0, gaps = 0, mtup = 0;
    int shown = 0;
    for (int i = 0; i < NT; i++) pthread_join(th[i], NULL);
    for (int i = 0; i < NT; i++) {
        combos += w[i].combos_checked;
        gaps += w[i].gaps;
        mtup += w[i].missing_tuples;
    }
    if (gaps == 0) {
        printf("VERIFIED: CA(N=%d; t=%d, k=%d, v=%d) - all %lld column sets fully cover all %lld tuples\n",
               N, T, K, V, combos, VT);
        return 0;
    }
    printf("NOT A COVERING ARRAY: %lld of %lld column sets have gaps (%lld missing tuples total)\n",
           gaps, combos, mtup);
    for (int i = 0; i < NT && shown < MAX_MISS_REPORT; i++) {
        for (int j = 0; j < w[i].n_miss && shown < MAX_MISS_REPORT; j++, shown++) {
            printf("  missing: columns (");
            for (int q = 0; q < T; q++) printf("%d%s", w[i].miss_cols[j][q], q < T-1 ? "," : "");
            printf(") tuple (");
            long long idx = w[i].miss_tuple[j];
            int digs[32];
            for (int q = T - 1; q >= 0; q--) { digs[q] = idx % V; idx /= V; }
            for (int q = 0; q < T; q++) printf("%d%s", digs[q], q < T-1 ? "," : "");
            printf(")\n");
        }
    }
    return 1;
}
