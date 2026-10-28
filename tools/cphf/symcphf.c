/* symcphf - search for quasi-cyclic covering perfect hash families CPHF(n; k, q, t), q prime, t <= 6.
 *
 * Columns: k = m*s, column index col = c*s + i with c in Z_m (shift coordinate) and i in [0,s) (orbit).
 * Row r: a semisimple M_r in GL(t,q) with M_r^m scalar (projective order dividing m), in rational
 *   canonical form: blocks of degrees d_1..d_b (sum t); block j is multiplication by beta_j = g_j^{a_j}
 *   on GF(q^{d_j}) = GF(q)^{d_j} (polynomial basis, g_j a primitive element).
 *   Seeds x_{r,i} in GF(q)^t, one per orbit, blockwise as exponents e_{ij} (-1 = zero block).
 *   Entry (r, (c,i)) = M_r^c x_{r,i}, i.e. block j = g_j^{a_j c + e_{ij}}.
 * The shift c -> c+1 multiplies all entries of the row by M_r (up to the scalar M_r^m at the wrap),
 * so a t-set is covered in row r iff its shift is; the CPHF condition on all t-sets is equivalent to
 * the condition on the representatives = t-sets containing a column with c = 0 (min column index < s).
 *
 * Exact search: a coverage count per representative (ranked by the combinatorial number system),
 * greedy row addition (best of C random candidates on the uncovered list), simulated annealing on the
 * row parameters with cheap proposals (scored on the uncovered list U and the critical list of the
 * modified row) and exact updates on acceptance; when a CPHF is found it is saved and the row with the
 * fewest critical sets is dropped.
 *
 * Build: gcc -O3 -march=native -fopenmp -o symcphf symcphf.c -lm
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <omp.h>

#define MAXT 6
#define MAXQ 13
#define MAXROWS 64
#define MAXORB 4096

static int T, Q, M, S, K;
static int mul[MAXQ][MAXQ], inv_[MAXQ];
static int NTHREADS = 2;
static double t_start;
static double now(void) { return omp_get_wtime(); }

/* ---------- GF(q^d) ---------- */
typedef struct { int d; long Qd; int poly[MAXT + 1]; uint8_t *pw; } Ext;
static Ext ext[MAXT + 1];
static void mulx_mod(int *cur, int d, const int *poly) {
    int top = cur[d - 1];
    for (int j = d - 1; j > 0; j--) cur[j] = ((cur[j - 1] - top * poly[j]) % Q + Q) % Q;
    cur[0] = ((-top * poly[0]) % Q + Q) % Q;
}
static long order_of_x(int d, const int *poly, long Qd) {
    int cur[MAXT + 1] = {0}; cur[0] = 1;
    for (long e = 1; e <= Qd; e++) { mulx_mod(cur, d, poly); int one = (cur[0] == 1); for (int j = 1; j < d; j++) if (cur[j]) one = 0; if (one) return e; }
    return 0;
}
static void build_ext(int d) {
    Ext *E = &ext[d]; E->d = d; E->Qd = 1; for (int j = 0; j < d; j++) E->Qd *= Q; E->Qd -= 1;
    long npoly = 1; for (int j = 0; j < d; j++) npoly *= Q; int found = 0;
    for (long code = 0; code < npoly && !found; code++) {
        long c = code; for (int j = 0; j < d; j++) { E->poly[j] = c % Q; c /= Q; } E->poly[d] = 1;
        if (E->poly[0] == 0) continue;
        if (order_of_x(d, E->poly, E->Qd) == E->Qd) found = 1;
    }
    if (!found) { fprintf(stderr, "no primitive polynomial of degree %d\n", d); exit(2); }
    E->pw = malloc((size_t)E->Qd * d);
    int cur[MAXT + 1] = {0}; cur[0] = 1;
    for (long e = 0; e < E->Qd; e++) { for (int j = 0; j < d; j++) E->pw[e * d + j] = cur[j]; mulx_mod(cur, d, E->poly); }
}
static int ext_const(int d, long e) { /* g_d^e if it is a nonzero constant, else 0 */
    Ext *E = &ext[d]; e %= E->Qd; if (e < 0) e += E->Qd;
    for (int j = 1; j < d; j++) if (E->pw[e * d + j]) return 0;
    return E->pw[e * d];
}

/* ---------- M-types ---------- */
typedef struct { int nb; int deg[MAXT]; } Part;
static Part parts[64]; static int nparts = 0;
static void gen_parts(int rem, int maxd, Part *cur) {
    if (rem == 0) { parts[nparts++] = *cur; return; }
    for (int d = (rem < maxd ? rem : maxd); d >= 1; d--) { cur->deg[cur->nb++] = d; gen_parts(rem - d, d, cur); cur->nb--; }
}
typedef struct { int part; long a[MAXT]; int order; } MType;
static MType *types = NULL; static int ntypes = 0, cap_types = 0;
static int allow_parts[64];
static int type_order(const MType *ty) {
    const Part *P = &parts[ty->part];
    for (int c = 1; c <= M; c++) {
        if (M % c) continue;
        int lam = -1, ok = 1;
        for (int j = 0; j < P->nb; j++) { int cst = ext_const(P->deg[j], ty->a[j] * c); if (!cst) { ok = 0; break; } if (lam < 0) lam = cst; else if (lam != cst) { ok = 0; break; } }
        if (ok) return c;
    }
    return 0;
}
static void enum_types(int minorder) {
    static long *Alist[MAXT + 1][MAXQ]; static int nA[MAXT + 1][MAXQ];
    for (int d = 1; d <= T; d++) for (int lam = 1; lam < Q; lam++) {
        Alist[d][lam] = malloc(sizeof(long) * ext[d].Qd); nA[d][lam] = 0;
        for (long a = 0; a < ext[d].Qd; a++) if (ext_const(d, a * M) == lam) Alist[d][lam][nA[d][lam]++] = a;
    }
    for (int p = 0; p < nparts; p++) {
        if (!allow_parts[p]) continue;
        const Part *P = &parts[p];
        for (int lam = 1; lam < Q; lam++) {
            long total = 1; for (int j = 0; j < P->nb; j++) total *= nA[P->deg[j]][lam];
            if (total == 0) continue;
            long lim = total > 2000000 ? 2000000 : total;
            if (lim < total) fprintf(stderr, "partition %d lambda %d: %ld tuples, sampling %ld\n", p, lam, total, lim);
            for (long idx = 0; idx < lim; idx++) {
                long code = lim < total ? (long)(drand48() * total) : idx; long a[MAXT] = {0};
                for (int j = 0; j < P->nb; j++) { int n = nA[P->deg[j]][lam]; a[j] = Alist[P->deg[j]][lam][code % n]; code /= n; }
                if (ntypes == cap_types) { cap_types = cap_types ? 2 * cap_types : 1024; types = realloc(types, sizeof(MType) * cap_types); }
                types[ntypes].part = p; memcpy(types[ntypes].a, a, sizeof(a)); types[ntypes].order = type_order(&types[ntypes]);
                if (types[ntypes].order >= minorder) ntypes++;
            }
        }
    }
}

/* ---------- rows ---------- */
typedef struct { int type; long e[MAXORB][MAXT]; uint8_t *vec; } Row;
static Row rows[MAXROWS]; static int nrows = 0;
static void row_fill_orbit(Row *R, int i) {
    const MType *ty = &types[R->type]; const Part *P = &parts[ty->part];
    for (int c = 0; c < M; c++) {
        uint8_t *v = R->vec + (size_t)(c * S + i) * T; int off = 0;
        for (int j = 0; j < P->nb; j++) {
            int d = P->deg[j]; Ext *E = &ext[d];
            if (R->e[i][j] < 0) memset(v + off, 0, d);
            else { long ex = (ty->a[j] * c + R->e[i][j]) % E->Qd; memcpy(v + off, E->pw + ex * d, d); }
            off += d;
        }
    }
}
static void row_fill(Row *R) { for (int i = 0; i < S; i++) row_fill_orbit(R, i); }
static int proportional(const uint8_t *u, const uint8_t *v) {
    int lam = 0;
    for (int j = 0; j < T; j++) {
        if (u[j] == 0) { if (v[j]) return 0; continue; }
        if (v[j] == 0) return 0;
        int l = mul[v[j]][inv_[u[j]]]; if (lam == 0) lam = l; else if (l != lam) return 0;
    }
    return lam != 0;
}
static int orbit_period(const Row *R, int i) {
    for (int c = 1; c < M; c++) if (M % c == 0 && proportional(R->vec + (size_t)i * T, R->vec + (size_t)(c * S + i) * T)) return c;
    return M;
}
static int require_full = 1;
static void random_seed(Row *R, int i) {
    const MType *ty = &types[R->type]; const Part *P = &parts[ty->part]; int nz;
    do { nz = 0; for (int j = 0; j < P->nb; j++) { R->e[i][j] = (drand48() < 0.08) ? -1 : (long)(drand48() * ext[P->deg[j]].Qd); if (R->e[i][j] >= 0) nz = 1; } } while (!nz);
}
static int row_ok(Row *R) { if (!require_full) return 1; for (int i = 0; i < S; i++) if (orbit_period(R, i) != M) return 0; return 1; }
static void random_row(Row *R) {
    for (int tries = 0; tries < 100000; tries++) {
        R->type = (int)(drand48() * ntypes); for (int i = 0; i < S; i++) random_seed(R, i); row_fill(R);
        if (row_ok(R)) return;
    }
    fprintf(stderr, "cannot generate a full-period row\n"); exit(3);
}
static void copy_params(Row *dst, const Row *src) { dst->type = src->type; memcpy(dst->e, src->e, sizeof(long) * MAXORB * MAXT); }

/* ---------- rank test ---------- */
static inline int covered_by(const uint8_t *vec, const uint16_t *cols) {
    uint8_t m[MAXT][MAXT];
    for (int r = 0; r < T; r++) memcpy(m[r], vec + (size_t)cols[r] * T, T);
    for (int col = 0; col < T; col++) {
        int piv = -1; for (int r = col; r < T; r++) if (m[r][col]) { piv = r; break; }
        if (piv < 0) return 0;
        if (piv != col) { uint8_t tmp[MAXT]; memcpy(tmp, m[piv], T); memcpy(m[piv], m[col], T); memcpy(m[col], tmp, T); }
        int iv = inv_[m[col][col]];
        for (int r = col + 1; r < T; r++) {
            int f = m[r][col]; if (!f) continue; f = mul[f][iv];
            for (int j = col; j < T; j++) { int x = m[r][j] - mul[f][m[col][j]]; if (x < 0) x += Q; m[r][j] = x; }
        }
    }
    return 1;
}

/* ---------- representatives: ranking ---------- */
typedef struct { uint16_t c[MAXT]; } Rep;
typedef struct { Rep *a; long n, cap; } List;
static void list_push(List *L, const Rep *r) { if (L->n == L->cap) { L->cap = L->cap ? 2 * L->cap : 1024; L->a = realloc(L->a, sizeof(Rep) * L->cap); } L->a[L->n++] = *r; }
static long *binom; /* binom[n*(T+1)+i] = C(n,i), n <= K */
static long *off;   /* off[j0] = sum_{j<j0} C(K-1-j, T-1) */
static long NREPS;
static inline long C_(int n, int i) { return (n < 0 || i < 0 || i > n) ? 0 : binom[(size_t)n * (T + 1) + i]; }
static inline long rank_rep(const uint16_t *c) { /* c sorted, c[0] < S */
    long r = off[c[0]]; for (int i = 1; i < T; i++) r += C_(c[i] - c[0] - 1, i); return r;
}
static void unrank_rep(long r, uint16_t *c) {
    int j0 = 0; while (j0 + 1 < S && off[j0 + 1] <= r) j0++;
    long rem = r - off[j0]; c[0] = j0;
    for (int i = T - 1; i >= 1; i--) { int b = i - 1; while (C_(b + 1, i) <= rem) b++; rem -= C_(b, i); c[i] = (uint16_t)(b + j0 + 1); }
}
static uint8_t *cnt, *who;  /* coverage count per rep; covering row when cnt == 1 */
static List U; static List crit[MAXROWS]; static long Ucap = 30000000; static long psample = 200000;

/* enumerate all representatives; callback per rep (sorted columns) with its rank */
#define FOR_EACH_REP(...) do { \
    long tasks_ = 0; int *tj0_ = malloc(sizeof(int) * (size_t)K * S), *tj1_ = malloc(sizeof(int) * (size_t)K * S); \
    for (int j0 = 0; j0 < S; j0++) for (int j1 = j0 + 1; j1 < K; j1++) { tj0_[tasks_] = j0; tj1_[tasks_] = j1; tasks_++; } \
    _Pragma("omp parallel num_threads(NTHREADS)") { \
        Rep rep_; uint16_t *c = rep_.c; \
        _Pragma("omp for schedule(dynamic, 1)") \
        for (long ti_ = 0; ti_ < tasks_; ti_++) { \
            c[0] = tj0_[ti_]; c[1] = tj1_[ti_]; int okinit_ = 1; \
            for (int l = 2; l < T; l++) { c[l] = c[l - 1] + 1; if (c[l] >= K) okinit_ = 0; } \
            if (!okinit_) continue; \
            while (1) { \
                long rk = rank_rep(c); { __VA_ARGS__ } \
                if (T <= 2) break; \
                int l = T - 1; while (l >= 2 && c[l] == K - 1 - (T - 1 - l)) l--; \
                if (l < 2) break; \
                c[l]++; for (int j = l + 1; j < T; j++) c[j] = c[j - 1] + 1; \
            } \
        } \
    } \
    free(tj0_); free(tj1_); } while (0)

static void rebuild_lists(void) {
    U.n = 0; for (int r = 0; r < nrows; r++) crit[r].n = 0;
    for (long rk = 0; rk < NREPS; rk++) {
        if (cnt[rk] >= 2) continue;
        Rep rep; unrank_rep(rk, rep.c);
        if (cnt[rk] == 0) list_push(&U, &rep); else list_push(&crit[who[rk]], &rep);
    }
}
static void full_recount(void) {
    FOR_EACH_REP({
        int n = 0, w = 0; for (int r = 0; r < nrows; r++) if (covered_by(rows[r].vec, c)) { n++; w = r; }
        cnt[rk] = n > 255 ? 255 : n; who[rk] = w;
    });
    rebuild_lists();
}
static inline void set_who_other(long rk, const uint16_t *c, int except) {
    for (int r = 0; r < nrows; r++) if (r != except && covered_by(rows[r].vec, c)) { who[rk] = r; return; }
}
static void add_row_counts(int r) { /* row r has been appended (nrows already incremented) */
    FOR_EACH_REP({ if (covered_by(rows[r].vec, c)) { if (cnt[rk] == 0) who[rk] = r; if (cnt[rk] < 255) cnt[rk]++; } });
    rebuild_lists();
}
static void remove_row(int r) {
    FOR_EACH_REP({ if (covered_by(rows[r].vec, c)) { if (cnt[rk] == 2) set_who_other(rk, c, r); cnt[rk]--; } });
    uint8_t *tmpv = rows[r].vec;
    for (int i = r; i < nrows - 1; i++) { copy_params(&rows[i], &rows[i + 1]); rows[i].vec = rows[i + 1].vec; }
    rows[nrows - 1].vec = tmpv; nrows--;
    for (long rk = 0; rk < NREPS; rk++) if (cnt[rk] == 1 && who[rk] > r) who[rk]--;
    rebuild_lists();
}
/* replace row r by newvec (new params already in newp); modified[col] marks changed columns */
static void apply_replace(int r, const Row *newp, const uint8_t *newvec, const uint8_t *modified) {
    const uint8_t *oldvec = rows[r].vec;
    FOR_EACH_REP({
        int touch = 0; for (int j = 0; j < T; j++) if (modified[c[j]]) { touch = 1; break; }
        if (touch) {
            int o = covered_by(oldvec, c), nw = covered_by(newvec, c);
            if (o && !nw) { if (cnt[rk] == 2) set_who_other(rk, c, r); cnt[rk]--; }
            else if (!o && nw) { if (cnt[rk] == 0) who[rk] = r; if (cnt[rk] < 255) cnt[rk]++; }
        }
    });
    copy_params(&rows[r], newp); memcpy(rows[r].vec, newvec, (size_t)K * T);
    rebuild_lists();
}

/* light mode (no count arrays): one enumeration pass collecting the reps uncovered by all rows */
static long light_pass(void) {
    U.n = 0; long tot = 0; int aborted = 0;
    List *Ul = calloc(NTHREADS, sizeof(List));
    FOR_EACH_REP({
        int tid = omp_get_thread_num(); int cov = 0;
        for (int r = 0; r < nrows && !cov; r++) if (covered_by(rows[r].vec, c)) cov = 1;
        if (!cov) { list_push(&Ul[tid], &rep_); if (Ul[tid].n > Ucap) aborted = 1; }
        (void)rk; (void)tot;
    });
    for (int tid = 0; tid < NTHREADS; tid++) { for (long i = 0; i < Ul[tid].n; i++) list_push(&U, &Ul[tid].a[i]); free(Ul[tid].a); }
    free(Ul); return aborted ? -1 : U.n;
}
/* ---------- output ---------- */
static long vec_code(const uint8_t *v) { long x = 0; for (int j = 0; j < T; j++) x = x * Q + v[j]; return x; }
static void save_solution(const char *path, const char *tag) {
    FILE *f = fopen(path, "w"); if (!f) { perror(path); return; }
    fprintf(f, "# CPHF t=%d q=%d n=%d k=%d m=%d s=%d column=(c*s+i) entry=vector code sum v_j q^(t-1-j) %s\n", T, Q, nrows, K, M, S, tag);
    for (int d = 1; d <= T; d++) { fprintf(f, "# GF(%d^%d) primitive polynomial coefficients (x^0..x^%d):", Q, d, d); for (int j = 0; j <= d; j++) fprintf(f, " %d", ext[d].poly[j]); fprintf(f, "\n"); }
    for (int r = 0; r < nrows; r++) {
        const MType *ty = &types[rows[r].type]; const Part *P = &parts[ty->part];
        fprintf(f, "# row %d M-type: blocks", r); for (int j = 0; j < P->nb; j++) fprintf(f, " (deg %d, beta=g^%ld)", P->deg[j], ty->a[j]);
        fprintf(f, " projective order %d; seeds (exponents per block, -1=zero):", ty->order);
        for (int i = 0; i < S; i++) { fprintf(f, " ("); for (int j = 0; j < P->nb; j++) fprintf(f, "%s%ld", j ? "," : "", rows[r].e[i][j]); fprintf(f, ")"); }
        fprintf(f, "\n");
    }
    for (int r = 0; r < nrows; r++) { for (int col = 0; col < K; col++) fprintf(f, "%s%ld", col ? " " : "", vec_code(rows[r].vec + (size_t)col * T)); fprintf(f, "\n"); }
    fclose(f);
}

/* ---------- search ---------- */
static long eval_on(const List *L, const uint8_t *vec, long stop) {
    long miss = 0; for (long i = 0; i < L->n; i++) if (!covered_by(vec, L->a[i].c)) { miss++; if (miss > stop) return miss; } return miss;
}
static Row cand; static uint8_t *modified;
static long optmoves = 3000;
/* hill-climb a candidate row against the list L (minimise the number of reps of L it misses) */
static long optimize_row_on(Row *R, const List *L, long moves) {
    long cur = eval_on(L, R->vec, L->n); Row tmp; tmp.vec = malloc((size_t)K * T);
    List miss = {0};
    for (long mv = 0; mv < moves && cur > 0; mv++) {
        if (mv % 200 == 0) { miss.n = 0; for (long i = 0; i < L->n; i++) if (!covered_by(R->vec, L->a[i].c)) list_push(&miss, &L->a[i]); }
        copy_params(&tmp, R); memcpy(tmp.vec, R->vec, (size_t)K * T);
        const Rep *rp = &miss.a[(long)(drand48() * miss.n)]; int i = rp->c[(int)(drand48() * T)] % S;
        double u = drand48(); if (S == 1) u = 0.95;
        if (u < 0.5) random_seed(&tmp, i);
        else if (u < 0.9) { const Part *P = &parts[types[tmp.type].part]; int j = (int)(drand48() * P->nb); tmp.e[i][j] = (long)(drand48() * ext[P->deg[j]].Qd); }
        else { tmp.type = (int)(drand48() * ntypes); if (parts[types[tmp.type].part].nb != parts[types[R->type].part].nb) for (int ii = 0; ii < S; ii++) random_seed(&tmp, ii); row_fill(&tmp); }
        if (u < 0.9) row_fill_orbit(&tmp, i);
        if (!row_ok(&tmp)) continue;
        long v = eval_on(L, tmp.vec, cur);
        if (v <= cur) { if (v < cur) mv = (mv / 200) * 200; cur = v; copy_params(R, &tmp); memcpy(R->vec, tmp.vec, (size_t)K * T); if (v < cur) { miss.n = 0; } }
    }
    free(tmp.vec); free(miss.a); return cur;
}
static void greedy_add(int ncand, int verbose) {
    long bestmiss = -1; Row best; best.vec = malloc((size_t)K * T);
    List *target = &U;
    for (int cnd = 0; cnd < ncand; cnd++) { random_row(&cand); long miss = eval_on(target, cand.vec, bestmiss < 0 ? target->n : bestmiss); if (bestmiss < 0 || miss < bestmiss) { bestmiss = miss; copy_params(&best, &cand); memcpy(best.vec, cand.vec, (size_t)K * T); } }
    long opt;
    if (target->n > 100000) { /* optimise on a random subsample of U, then report the exact miss count */
        List sub = {0}; for (long i = 0; i < 100000; i++) list_push(&sub, &target->a[(long)(drand48() * target->n)]);
        optimize_row_on(&best, &sub, optmoves / 3); free(sub.a); opt = eval_on(target, best.vec, target->n);
    } else opt = optimize_row_on(&best, target, optmoves);
    copy_params(&rows[nrows], &best); memcpy(rows[nrows].vec, best.vec, (size_t)K * T); nrows++; free(best.vec);
    add_row_counts(nrows - 1);
    if (verbose) fprintf(stderr, "[%.0fs] greedy row (best of %d left %ld, optimised to %ld) -> n=%d |U|=%ld\n", now() - t_start, ncand, bestmiss, opt, nrows, U.n);
}
/* SA: returns 1 when U is empty */
static double ptarget = 0.6, psideways = 0.1;
static int sa_phase(long maxmoves, double T0, double T1, double pseed, int verbose) {
    long accepted = 0, proposals = 0;
    for (long mv = 0; mv < maxmoves; mv++) {
        if (U.n == 0) return 1;
        double temp = T0 * pow(T1 / T0, (double)mv / maxmoves);
        int r = (int)(drand48() * nrows);
        copy_params(&cand, &rows[r]); memcpy(cand.vec, rows[r].vec, (size_t)K * T);
        memset(modified, 0, K);
        double u = drand48(); if (S == 1) u = 1.0;
        if (u < ptarget) { /* targeted: a column of a random uncovered rep */
            const Rep *rp = &U.a[(long)(drand48() * U.n)]; int i = rp->c[(int)(drand48() * T)] % S;
            if (drand48() < 0.5) random_seed(&cand, i); else { const Part *P = &parts[types[cand.type].part]; int j = (int)(drand48() * P->nb); cand.e[i][j] = (long)(drand48() * ext[P->deg[j]].Qd); }
            row_fill_orbit(&cand, i); for (int c = 0; c < M; c++) modified[c * S + i] = 1; }
        else if (u < ptarget + pseed) { int i = (int)(drand48() * S); random_seed(&cand, i); row_fill_orbit(&cand, i); for (int c = 0; c < M; c++) modified[c * S + i] = 1; }
        else if (u < ptarget + pseed + (1 - ptarget - pseed) * 0.6) { int i = (int)(drand48() * S); const Part *P = &parts[types[cand.type].part]; int j = (int)(drand48() * P->nb); cand.e[i][j] = (long)(drand48() * ext[P->deg[j]].Qd); row_fill_orbit(&cand, i); for (int c = 0; c < M; c++) modified[c * S + i] = 1; }
        else { cand.type = (int)(drand48() * ntypes); if (parts[types[cand.type].part].nb != parts[types[rows[r].type].part].nb) for (int i = 0; i < S; i++) random_seed(&cand, i); row_fill(&cand); memset(modified, 1, K); }
        if (!row_ok(&cand)) continue;
        proposals++;
        long gain = U.n - eval_on(&U, cand.vec, U.n);
        long lost = eval_on(&crit[r], cand.vec, crit[r].n);
        long delta = lost - gain;
        if (delta < 0 || (delta == 0 && drand48() < psideways) || (delta > 0 && drand48() < exp(-delta / temp))) {
            Row np; copy_params(&np, &cand);
            apply_replace(r, &np, cand.vec, modified);
            accepted++;
            if (verbose > 1 && accepted % 100 == 0) fprintf(stderr, "  [%.0fs] mv %ld acc %ld |U|=%ld T=%.3f\n", now() - t_start, mv, accepted, U.n, temp);
        }
    }
    if (verbose) fprintf(stderr, "[%.0fs] SA: %ld proposals, %ld accepted, |U|=%ld\n", now() - t_start, proposals, accepted, U.n);
    return U.n == 0;
}

static void usage(void) {
    fprintf(stderr, "usage: symcphf t q m s [-seed S] [-n0 N] [-nmax N] [-moves L] [-rounds R] [-T0 x] [-T1 x] [-threads n]\n"
                    "  [-parts 'd1+d2,...'] [-anyorder] [-nofull] [-out prefix] [-cand C] [-time sec] [-pseed p] [-maxreps N] [-patience P] [-sastart U] [-psample N] [-v]\n");
    exit(1);
}

int main(int argc, char **argv) {
    if (argc < 5) usage();
    T = atoi(argv[1]); Q = atoi(argv[2]); M = atoi(argv[3]); S = atoi(argv[4]); K = M * S;
    if (T > MAXT || Q > MAXQ || S > MAXORB || K > 65000) { fprintf(stderr, "limits: t<=%d q<=%d s<=%d k<65000\n", MAXT, MAXQ, MAXORB); return 1; }
    long seed = 1; int n0 = -1, nmax = MAXROWS - 1; long moves = 20000; int rounds = 50; double T0 = 2.0, T1 = 0.3; int verbose = 1;
    char partspec[256] = ""; int minorder = -1; const char *out = "cphf"; int ncand = 200; double tlimit = 1e9; double pseed = 0.15; long maxreps = 1500000000L; int patience = 3; long sastart = -1; long probe = 0; int probeseeds = 2; int light = 0; int exactcover = 0;
    for (int i = 5; i < argc; i++) {
        if (!strcmp(argv[i], "-seed")) seed = atol(argv[++i]);
        else if (!strcmp(argv[i], "-n0")) n0 = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-nmax")) nmax = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-moves")) moves = atol(argv[++i]);
        else if (!strcmp(argv[i], "-rounds")) rounds = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-T0")) T0 = atof(argv[++i]);
        else if (!strcmp(argv[i], "-T1")) T1 = atof(argv[++i]);
        else if (!strcmp(argv[i], "-threads")) NTHREADS = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-parts")) strncpy(partspec, argv[++i], 255);
        else if (!strcmp(argv[i], "-anyorder")) minorder = 1;
        else if (!strcmp(argv[i], "-nofull")) require_full = 0;
        else if (!strcmp(argv[i], "-out")) out = argv[++i];
        else if (!strcmp(argv[i], "-cand")) ncand = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-time")) tlimit = atof(argv[++i]);
        else if (!strcmp(argv[i], "-pseed")) pseed = atof(argv[++i]);
        else if (!strcmp(argv[i], "-maxreps")) maxreps = atol(argv[++i]);
        else if (!strcmp(argv[i], "-patience")) patience = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-sastart")) sastart = atol(argv[++i]);
        else if (!strcmp(argv[i], "-probe")) probe = atol(argv[++i]);
        else if (!strcmp(argv[i], "-light")) light = 1;
        else if (!strcmp(argv[i], "-exactcover")) exactcover = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-ucap")) Ucap = atol(argv[++i]);
        else if (!strcmp(argv[i], "-probeseeds")) probeseeds = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-ptarget")) ptarget = atof(argv[++i]);
        else if (!strcmp(argv[i], "-psideways")) psideways = atof(argv[++i]);
        else if (!strcmp(argv[i], "-optmoves")) optmoves = atol(argv[++i]);
        else if (!strcmp(argv[i], "-psample")) psample = atol(argv[++i]);
        else if (!strcmp(argv[i], "-v")) verbose = 2;
        else usage();
    }
    if (minorder < 0) minorder = M;
    srand48(seed); t_start = now();
    for (int a = 0; a < Q; a++) for (int b = 0; b < Q; b++) mul[a][b] = (a * b) % Q;
    for (int a = 1; a < Q; a++) for (int b = 1; b < Q; b++) if (mul[a][b] == 1) inv_[a] = b;
    for (int d = 1; d <= T; d++) build_ext(d);
    Part cur = {0}; gen_parts(T, T, &cur);
    for (int p = 0; p < nparts; p++) {
        if (!partspec[0]) { allow_parts[p] = 1; continue; }
        char name[64] = ""; for (int j = 0; j < parts[p].nb; j++) { char b[8]; sprintf(b, "%s%d", j ? "+" : "", parts[p].deg[j]); strcat(name, b); }
        allow_parts[p] = 0; char spec[256]; strcpy(spec, partspec);
        for (char *tok = strtok(spec, ","); tok; tok = strtok(NULL, ",")) if (!strcmp(tok, name)) allow_parts[p] = 1;
    }
    enum_types(minorder);
    binom = calloc((size_t)(K + 1) * (T + 1), sizeof(long));
    for (int n = 0; n <= K; n++) { binom[(size_t)n * (T + 1)] = 1; for (int i = 1; i <= T && i <= n; i++) binom[(size_t)n * (T + 1) + i] = binom[(size_t)(n - 1) * (T + 1) + i - 1] + (i <= n - 1 ? binom[(size_t)(n - 1) * (T + 1) + i] : 0); }
    off = calloc(S + 1, sizeof(long)); for (int j0 = 0; j0 < S; j0++) off[j0 + 1] = off[j0] + C_(K - 1 - j0, T - 1);
    NREPS = off[S];
    fprintf(stderr, "t=%d q=%d m=%d s=%d k=%d  reps=%ld  C(k,t)=%ld  M-types(order>=%d)=%d\n", T, Q, M, S, K, NREPS, C_(K, T), minorder, ntypes);
    for (int p = 0; p < nparts; p++) { int c = 0, maxo = 0; for (int i = 0; i < ntypes; i++) if (types[i].part == p) { c++; if (types[i].order > maxo) maxo = types[i].order; }
        if (c) { fprintf(stderr, "  partition"); for (int j = 0; j < parts[p].nb; j++) fprintf(stderr, "%s%d", j ? "+" : " ", parts[p].deg[j]); fprintf(stderr, ": %d types, max projective order %d\n", c, maxo); } }
    if (ntypes == 0) { printf("NO M-TYPES of projective order %d for t=%d q=%d m=%d\n", minorder, T, Q, M); return 4; }
    if (NREPS > maxreps && probe == 0 && !light && !exactcover) { fprintf(stderr, "reps %ld exceed -maxreps %ld\n", NREPS, maxreps); return 5; }
    if (exactcover > 0) { /* exact minimum cover over distinct row patterns (seeds immaterial: s=1 Singer/affine types) */
        rows[0].vec = malloc((size_t)K * T); cand.vec = malloc((size_t)K * T);
        List sample = {0};
        for (long i = 0; i < 4000; i++) { Rep rp; int ok; do { ok = 1; int j0 = (int)(drand48() * S); rp.c[0] = j0; for (int j = 1; j < T; j++) rp.c[j] = (uint16_t)(j0 + 1 + drand48() * (K - 1 - j0)); for (int a = 0; a < T && ok; a++) for (int b = a + 1; b < T; b++) if (rp.c[a] == rp.c[b]) ok = 0; } while (!ok); list_push(&sample, &rp); }
        int np = 0; uint8_t **pvec = malloc(sizeof(uint8_t*) * ntypes); uint8_t **sig = malloc(sizeof(uint8_t*) * ntypes);
        for (int ty = 0; ty < ntypes; ty++) { Row *R = &rows[0]; R->type = ty; int ok = 0;
            for (int tries = 0; tries < 2000 && !ok; tries++) { for (int i = 0; i < S; i++) random_seed(R, i); row_fill(R); ok = row_ok(R); }
            if (!ok) continue;
            uint8_t *s_ = malloc(4000); for (long i = 0; i < 4000; i++) s_[i] = covered_by(R->vec, sample.a[i].c);
            int dup = 0; for (int p = 0; p < np && !dup; p++) if (!memcmp(sig[p], s_, 4000)) dup = 1;
            if (dup) { free(s_); continue; }
            sig[np] = s_; pvec[np] = malloc((size_t)K * T); memcpy(pvec[np], R->vec, (size_t)K * T); np++; }
        long words = (NREPS + 63) / 64;
        uint64_t **bm = malloc(sizeof(uint64_t*) * np); long *pc = calloc(np, sizeof(long));
        for (int p = 0; p < np; p++) { bm[p] = calloc(words, sizeof(uint64_t)); const uint8_t *pv = pvec[p];
            FOR_EACH_REP({ if (covered_by(pv, c)) { __atomic_or_fetch(&bm[p][rk >> 6], 1ULL << (rk & 63), __ATOMIC_RELAXED); } });
            for (long w = 0; w < words; w++) pc[p] += __builtin_popcountll(bm[p][w]); }
        fprintf(stderr, "[%.0fs] %d distinct patterns, bitmaps over %ld reps built\n", now() - t_start, np, NREPS);
        /* union of all: dead reps */
        uint64_t *all = calloc(words, sizeof(uint64_t)); for (int p = 0; p < np; p++) for (long w = 0; w < words; w++) all[w] |= bm[p][w];
        long dead = NREPS; for (long w = 0; w < words; w++) dead -= __builtin_popcountll(all[w]);
        printf("EXACT t=%d q=%d m=%d s=%d k=%d: %d distinct patterns; reps %ld; dead (uncovered by every pattern) %ld\n", T, Q, M, S, K, np, NREPS, dead);
        if (dead) return 0;
        /* DFS for a cover of size <= N: branch on the first uncovered rep */
        uint64_t **st = malloc(sizeof(uint64_t*) * (exactcover + 1)); for (int d = 0; d <= exactcover; d++) st[d] = calloc(words, sizeof(uint64_t));
        int chosen[64]; long nodes = 0; int found = 0; long maxpc = 0; for (int p = 0; p < np; p++) if (pc[p] > maxpc) maxpc = pc[p];
        /* iterative DFS */
        int depth = 0; int iter[64]; int cand_list[64][512]; int ncl[64];
        /* level 0 candidates: patterns covering the first rep (rep 0) */
        {
            long r0 = 0; ncl[0] = 0; for (int p = 0; p < np; p++) if (bm[p][r0 >> 6] >> (r0 & 63) & 1) cand_list[0][ncl[0]++] = p; iter[0] = 0;
        }
        while (depth >= 0 && !found) {
            if (iter[depth] >= ncl[depth]) { depth--; continue; }
            int p = cand_list[depth][iter[depth]++]; chosen[depth] = p; nodes++;
            for (long w = 0; w < words; w++) st[depth + 1][w] = st[depth][w] | bm[p][w];
            long unc = NREPS; for (long w = 0; w < words; w++) unc -= __builtin_popcountll(st[depth + 1][w]);
            if (unc == 0) { found = 1; depth++; break; }
            int rem = exactcover - (depth + 1);
            if (rem == 0 || (long)rem * maxpc < unc) continue;
            /* first uncovered rep */
            long r0 = -1; for (long w = 0; w < words; w++) if (~st[depth + 1][w]) { uint64_t x = ~st[depth + 1][w]; r0 = w * 64 + __builtin_ctzll(x); if (r0 >= NREPS) r0 = -1; break; }
            depth++; ncl[depth] = 0; for (int q = 0; q < np; q++) { int used = 0; for (int d = 0; d < depth; d++) if (chosen[d] == q) used = 1; if (!used && (bm[q][r0 >> 6] >> (r0 & 63) & 1)) cand_list[depth][ncl[depth]++] = q; } iter[depth] = 0;
        }
        if (found) { printf("EXACT: cover with %d patterns found (nodes %ld): patterns", depth, nodes); for (int d = 0; d < depth; d++) printf(" %d", chosen[d]); printf("\n");
            nrows = depth; for (int d = 0; d < depth; d++) { rows[d].vec = malloc((size_t)K * T); memcpy(rows[d].vec, pvec[chosen[d]], (size_t)K * T); rows[d].type = 0; }
            char path2[512]; sprintf(path2, "%s_exact_t%d_q%d_k%d_m%d_n%d.txt", out, T, Q, K, M, nrows); FILE *f = fopen(path2, "w");
            fprintf(f, "# CPHF t=%d q=%d n=%d k=%d m=%d s=%d exact cover over distinct patterns\n", T, Q, nrows, K, M, S);
            for (int r = 0; r < nrows; r++) { for (int col = 0; col < K; col++) fprintf(f, "%s%ld", col ? " " : "", vec_code(rows[r].vec + (size_t)col * T)); fprintf(f, "\n"); } fclose(f); printf("  saved %s\n", path2); }
        else printf("EXACT: NO cover with <= %d patterns exists (nodes %ld): the minimum for this symmetric family is > %d\n", exactcover, nodes, exactcover);
        return 0;
    }
    if (probe > 0) { /* dead-set probe: all M-types x probeseeds random seeds, on a random sample of reps */
        rows[0].vec = malloc((size_t)K * T); cand.vec = malloc((size_t)K * T);
        List sample = {0};
        for (long i = 0; i < probe; i++) { Rep rp; int ok; do { ok = 1; int j0 = (int)(drand48() * S); rp.c[0] = j0; for (int j = 1; j < T; j++) rp.c[j] = (uint16_t)(j0 + 1 + drand48() * (K - 1 - j0)); for (int a = 0; a < T && ok; a++) for (int b = a + 1; b < T; b++) if (rp.c[a] == rp.c[b]) ok = 0; } while (!ok); list_push(&sample, &rp); }
        uint8_t *covd = calloc(probe, 1); int nrowsp = 0; long bestcov = 0;
        uint8_t **cov = malloc(sizeof(uint8_t*) * (size_t)ntypes * probeseeds); long *sigs = malloc(sizeof(long) * (size_t)ntypes * probeseeds); long ndup = 0;
        for (int ty = 0; ty < ntypes; ty++) for (int sd = 0; sd < probeseeds; sd++) {
            Row *R = &rows[0]; R->type = ty; int ok = 0;
            for (int tries = 0; tries < 2000 && !ok; tries++) { for (int i = 0; i < S; i++) random_seed(R, i); row_fill(R); ok = row_ok(R); }
            if (!ok) continue;
            cov[nrowsp] = malloc(probe); long c0 = 0; long sig = 0;
            for (long i = 0; i < probe && i < 4000; i++) { cov[nrowsp][i] = covered_by(R->vec, sample.a[i].c); sig = sig * 3 + cov[nrowsp][i]; if (i % 20 == 19) sig %= 1000000007L; }
            { int dup = 0; for (int r = 0; r < nrowsp && !dup; r++) if (sigs[r] == sig && !memcmp(cov[r], cov[nrowsp], probe < 4000 ? probe : 4000)) dup = 1; if (dup) { free(cov[nrowsp]); ndup++; continue; } sigs[nrowsp] = sig; }
            for (long i = 0; i < probe; i++) { if (i >= 4000) cov[nrowsp][i] = covered_by(R->vec, sample.a[i].c); if (cov[nrowsp][i]) { c0++; covd[i] = 1; } }
            if (c0 > bestcov) bestcov = c0; nrowsp++;
        }
        long dead = 0; for (long i = 0; i < probe; i++) if (!covd[i]) dead++;
        printf("PROBE t=%d q=%d m=%d s=%d k=%d: %d distinct rows (%d types x %d seeds, %ld duplicates by pattern on 4000 reps), sample %ld reps: uncovered by every row %ld (%.3g of sample); best single row covers %.4f; time %.0fs\n", T, Q, M, S, K, nrowsp, ntypes, probeseeds, ndup, probe, dead, (double)dead / probe, (double)bestcov / probe, now() - t_start);
        if (dead) { int shown = 0; for (long i = 0; i < probe && shown < 5; i++) if (!covd[i]) { shown++; printf("  dead rep:"); for (int j = 0; j < T; j++) printf(" %d", sample.a[i].c[j]); printf("\n"); } }
        /* greedy set cover on the sample */
        uint8_t *unc = malloc(probe); memcpy(unc, covd, probe); for (long i = 0; i < probe; i++) unc[i] = 1; long left = probe - dead; int chosen = 0;
        for (long i = 0; i < probe; i++) if (!covd[i]) unc[i] = 0;
        while (left > 0 && chosen < 60) { int best = -1; long bg = -1; for (int r = 0; r < nrowsp; r++) { long g = 0; for (long i = 0; i < probe; i++) if (unc[i] && cov[r][i]) g++; if (g > bg) { bg = g; best = r; } }
            for (long i = 0; i < probe; i++) if (unc[i] && cov[best][i]) { unc[i] = 0; left--; } chosen++; }
        printf("  greedy set cover of the sample (excluding dead reps) with %d rows\n", chosen);
        return 0;
    }
    if (!light && !exactcover && probe == 0) { cnt = calloc(NREPS, 1); who = calloc(NREPS, 1); } modified = calloc(K, 1);
    for (int r = 0; r < MAXROWS; r++) rows[r].vec = malloc((size_t)K * T);
    cand.vec = malloc((size_t)K * T);
    /* sigma estimate */
    double sigma; { Row tmp; tmp.vec = malloc((size_t)K * T); long miss = 0, tot = 20000; random_row(&tmp);
      for (long i = 0; i < tot; i++) { uint16_t c[MAXT]; int ok; do { ok = 1; for (int j = 0; j < T; j++) c[j] = (uint16_t)(drand48() * K); for (int a = 0; a < T && ok; a++) for (int b = a + 1; b < T; b++) if (c[a] == c[b]) ok = 0; } while (!ok); if (!covered_by(tmp.vec, c)) miss++; }
      sigma = (double)miss / tot; free(tmp.vec); }
    int best_n = -1; char path[512];
    if (n0 < 0) { n0 = (int)ceil(log((double)NREPS / 3e6) / log(1.0 / (sigma > 0.01 ? sigma : 0.01))); if (n0 < 1) n0 = 1; }
    fprintf(stderr, "sigma(random row) ~ %.4f; union-bound rows %.1f; prefix n0=%d\n", sigma, log((double)C_(K, T)) / log(1 / sigma), n0);
    /* prefix rows chosen as best of ncand on a random sample of reps */
    List sample = {0};
    for (long i = 0; i < psample; i++) { Rep rp; int ok; do { ok = 1; int j0 = (int)(drand48() * S); rp.c[0] = j0; for (int j = 1; j < T; j++) rp.c[j] = (uint16_t)(j0 + 1 + drand48() * (K - 1 - j0)); for (int a = 0; a < T && ok; a++) for (int b = a + 1; b < T; b++) if (rp.c[a] == rp.c[b]) ok = 0; } while (!ok); list_push(&sample, &rp); }
    nrows = 0;
    while (nrows < n0) {
        long bestmiss = -1; Row best; best.vec = malloc((size_t)K * T);
        for (int cnd = 0; cnd < (nrows == 0 ? 1 : ncand); cnd++) { random_row(&cand); long miss = eval_on(&sample, cand.vec, bestmiss < 0 ? sample.n : bestmiss); if (bestmiss < 0 || miss < bestmiss) { bestmiss = miss; copy_params(&best, &cand); memcpy(best.vec, cand.vec, (size_t)K * T); } }
        copy_params(&rows[nrows], &best); memcpy(rows[nrows].vec, best.vec, (size_t)K * T); nrows++; free(best.vec);
        List ns = {0}; for (long i = 0; i < sample.n; i++) if (!covered_by(rows[nrows - 1].vec, sample.a[i].c)) list_push(&ns, &sample.a[i]); free(sample.a); sample = ns;
        if (verbose) fprintf(stderr, "prefix row %d: sample uncovered %ld / %ld\n", nrows, sample.n, psample);
    }
    free(sample.a);
    if (light) {
        long u = light_pass();
        while (u < 0) { random_row(&rows[nrows]); nrows++; fprintf(stderr, "[%.0fs] U exceeded cap, added a random row -> n=%d\n", now() - t_start, nrows); u = light_pass(); }
        fprintf(stderr, "[%.0fs] light pass done: n=%d |U|=%ld\n", now() - t_start, nrows, U.n);
        while (U.n > 0 && nrows < nmax) {
            long bestmiss = -1; Row best; best.vec = malloc((size_t)K * T);
            for (int cnd = 0; cnd < ncand; cnd++) { random_row(&cand); long miss = eval_on(&U, cand.vec, bestmiss < 0 ? U.n : bestmiss); if (bestmiss < 0 || miss < bestmiss) { bestmiss = miss; copy_params(&best, &cand); memcpy(best.vec, cand.vec, (size_t)K * T); } }
            long opt;
            if (U.n > 100000) { List sub = {0}; for (long i = 0; i < 100000; i++) list_push(&sub, &U.a[(long)(drand48() * U.n)]); optimize_row_on(&best, &sub, optmoves / 3); free(sub.a); opt = eval_on(&U, best.vec, U.n); }
            else opt = optimize_row_on(&best, &U, optmoves);
            copy_params(&rows[nrows], &best); memcpy(rows[nrows].vec, best.vec, (size_t)K * T); nrows++; free(best.vec);
            List nu = {0}; for (long i = 0; i < U.n; i++) if (!covered_by(rows[nrows - 1].vec, U.a[i].c)) list_push(&nu, &U.a[i]); free(U.a); U = nu;
            fprintf(stderr, "[%.0fs] light greedy row (best of %d left %ld, optimised to %ld) -> n=%d |U|=%ld\n", now() - t_start, ncand, bestmiss, opt, nrows, U.n);
        }
        if (U.n == 0) {
            sprintf(path, "%s_t%d_q%d_k%d_m%d_n%d.txt", out, T, Q, K, M, nrows);
            char tag[128]; sprintf(tag, "seed=%ld time=%.0fs light", seed, now() - t_start); save_solution(path, tag);
            long qt = 1; for (int j = 0; j < T; j++) qt *= Q;
            printf("FOUND CPHF(%d; %d, %d, %d) m=%d s=%d  N=%ld  file=%s  time=%.0fs (light mode: prefix %d rows, exact pass, greedy completion)\n", nrows, K, Q, T, M, S, (long)nrows * (qt - 1) + 1, path, now() - t_start, n0);
        } else printf("light mode: not completed, |U|=%ld with n=%d\n", U.n, nrows);
        printf("BEST n=%d for t=%d q=%d k=%d m=%d s=%d (reps %ld, types %d, sigma %.4f) time=%.0fs\n", U.n == 0 ? nrows : -1, T, Q, K, M, S, NREPS, ntypes, sigma, now() - t_start);
        return 0;
    }
    full_recount();
    if (verbose) fprintf(stderr, "[%.0fs] n=%d after prefix: |U|=%ld\n", now() - t_start, nrows, U.n);
    int fails = 0;
    if (sastart < 0) { sastart = NREPS / 100; if (sastart < 2000) sastart = 2000; if (sastart > 3000000) sastart = 3000000; }
    for (int round = 0; round < rounds; round++) {
        if (now() - t_start > tlimit) { fprintf(stderr, "time limit\n"); break; }
        if (U.n > 0) {
            if (U.n > sastart || nrows < 2) { if (nrows >= nmax) break; greedy_add(ncand, verbose); continue; }
            int ok = sa_phase(moves, T0, T1, pseed, verbose);
            if (verbose) { fprintf(stderr, "[%.0fs] round %d n=%d |U|=%ld crit:", now() - t_start, round, nrows, U.n); for (int r = 0; r < nrows; r++) fprintf(stderr, " %ld", crit[r].n); fprintf(stderr, "\n"); }
            if (!ok) { fails++; if (fails < patience) continue; fails = 0; if (nrows >= nmax) { fprintf(stderr, "nmax reached, |U|=%ld\n", U.n); if (best_n < 0) break; else continue; } greedy_add(ncand, verbose); }
            else fails = 0;
        }
        if (U.n == 0) {
            if (best_n < 0 || nrows < best_n) {
                best_n = nrows; sprintf(path, "%s_t%d_q%d_k%d_m%d_n%d.txt", out, T, Q, K, M, nrows);
                char tag[128]; sprintf(tag, "seed=%ld time=%.0fs", seed, now() - t_start); save_solution(path, tag);
                long qt = 1; for (int j = 0; j < T; j++) qt *= Q;
                printf("FOUND CPHF(%d; %d, %d, %d) m=%d s=%d  N=%ld  file=%s  time=%.0fs\n", nrows, K, Q, T, M, S, (long)nrows * (qt - 1) + 1, path, now() - t_start); fflush(stdout);
            }
            if (nrows <= 1) break;
            int rmin = 0; for (int r = 1; r < nrows; r++) if (crit[r].n < crit[rmin].n) rmin = r;
            if (verbose) fprintf(stderr, "[%.0fs] dropping row %d (crit %ld)\n", now() - t_start, rmin, crit[rmin].n);
            remove_row(rmin);
            if (verbose) fprintf(stderr, "[%.0fs] n=%d |U|=%ld\n", now() - t_start, nrows, U.n);
        }
    }
    printf("BEST n=%d for t=%d q=%d k=%d m=%d s=%d (reps %ld, types %d, sigma %.4f) time=%.0fs\n", best_n, T, Q, K, M, S, NREPS, ntypes, sigma, now() - t_start);
    if (best_n < 0) printf("NOT FOUND within nmax=%d: final |U|=%ld with n=%d\n", nmax, U.n, nrows);
    return 0;
}
