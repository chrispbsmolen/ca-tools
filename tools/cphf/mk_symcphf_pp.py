"""Builds symcphf_pp.c from symcphf.c by exact, asserted string replacements (each must occur once).
Usage: python3 mk_symcphf_pp.py symcphf.c symcphf_pp.c"""
import sys
src = open(sys.argv[1]).read()
def rep(old, new, count=1):
    global src
    n = src.count(old)
    assert n == count, (n, old[:80])
    src = src.replace(old, new)

rep("/* symcphf - search for quasi-cyclic covering perfect hash families CPHF(n; k, q, t), q prime, t <= 6.\n",
    "/* symcphf_pp - search for quasi-cyclic covering perfect hash families CPHF(n; k, q, t), q a prime power <= 16, t <= 8.\n"
    " *\n"
    " * Prime-power version of symcphf.c (2026-10-28). Differences from symcphf.c:\n"
    " *  - GF(q) arithmetic by tables (add, sub, mul, inv) for q = p^e <= 16; an element of GF(p^e) is coded\n"
    " *    by the integer sum c_i p^i of its coordinates in the polynomial basis 1, x, ..., x^(e-1) of\n"
    " *    GF(p)[x]/(f), f the Conway polynomial (q=4: x^2+x+1, q=8: x^3+x+1, q=9: x^2+2x+2, q=16: x^4+x+1).\n"
    " *    For prime q the tables are the integers mod q and the program behaves exactly as symcphf.c.\n"
    " *  - t up to 8 (MAXT 8).\n"
    " *  - light mode uses an incremental exact pass (reduced row echelon bases per prefix of the t-set, a\n"
    " *    normal vector for the last column; same enumeration order and same uncovered list as the\n"
    " *    rank-test pass of symcphf.c, which -slowpass restores).\n"
    " *  - files of non-prime q carry a '# GF(q) ...' comment line naming the polynomial.\n")
rep(" * Build: gcc -O3 -march=native -fopenmp -o symcphf symcphf.c -lm\n",
    " * Build: gcc -O3 -march=native -fopenmp -o symcphf_pp symcphf_pp.c -lm\n")
rep("#define MAXT 6\n#define MAXQ 13\n", "#define MAXT 8\n#define MAXQ 16\n")
rep("static int mul[MAXQ][MAXQ], inv_[MAXQ];\n",
    "static int mul[MAXQ][MAXQ], inv_[MAXQ], add_[MAXQ][MAXQ], sub_[MAXQ][MAXQ];\n"
    "static int QP = 0, QE = 1; static int QPOLY[8]; /* q = QP^QE; QPOLY = Conway polynomial coefficients x^0..x^QE */\n"
    "static int setup_field(int q) {\n"
    "    int p = 0; for (int d = 2; d <= q; d++) if (q % d == 0) { p = d; break; }\n"
    "    int e = 0; long x = 1; while (x < q) { x *= p; e++; } if (x != q) return 0;\n"
    "    QP = p; QE = e; memset(QPOLY, 0, sizeof(QPOLY));\n"
    "    if (e == 1) { QPOLY[0] = 0; QPOLY[1] = 1; }\n"
    "    else if (q == 4) { int f[] = {1, 1, 1}; memcpy(QPOLY, f, sizeof(f)); }\n"
    "    else if (q == 8) { int f[] = {1, 1, 0, 1}; memcpy(QPOLY, f, sizeof(f)); }\n"
    "    else if (q == 9) { int f[] = {2, 2, 1}; memcpy(QPOLY, f, sizeof(f)); }\n"
    "    else if (q == 16) { int f[] = {1, 1, 0, 0, 1}; memcpy(QPOLY, f, sizeof(f)); }\n"
    "    else return 0;\n"
    "    for (int a = 0; a < q; a++) for (int b = 0; b < q; b++) {\n"
    "        int da[8], db[8], s[8], d_[8], pr[16] = {0}; int aa = a, bb = b;\n"
    "        for (int i = 0; i < e; i++) { da[i] = aa % p; aa /= p; db[i] = bb % p; bb /= p; }\n"
    "        for (int i = 0; i < e; i++) { s[i] = (da[i] + db[i]) % p; d_[i] = (da[i] - db[i] + p) % p; }\n"
    "        for (int i = 0; i < e; i++) for (int j = 0; j < e; j++) pr[i + j] = (pr[i + j] + da[i] * db[j]) % p;\n"
    "        for (int i = 2 * e - 2; i >= e; i--) { int c = pr[i]; if (!c) continue; pr[i] = 0;\n"
    "            for (int j = 0; j < e; j++) pr[i - e + j] = ((pr[i - e + j] - c * QPOLY[j]) % p + p) % p; }\n"
    "        int cs = 0, cd = 0, cm = 0; for (int i = e - 1; i >= 0; i--) { cs = cs * p + s[i]; cd = cd * p + d_[i]; cm = cm * p + pr[i]; }\n"
    "        add_[a][b] = cs; sub_[a][b] = cd; mul[a][b] = cm;\n"
    "    }\n"
    "    for (int a = 1; a < q; a++) { inv_[a] = 0; for (int b = 1; b < q; b++) if (mul[a][b] == 1) inv_[a] = b; if (!inv_[a]) return 0; }\n"
    "    return 1;\n"
    "}\n")
# polynomial arithmetic over GF(q) in the extension builder
rep("    for (int j = d - 1; j > 0; j--) cur[j] = ((cur[j - 1] - top * poly[j]) % Q + Q) % Q;\n"
    "    cur[0] = ((-top * poly[0]) % Q + Q) % Q;\n",
    "    for (int j = d - 1; j > 0; j--) cur[j] = sub_[cur[j - 1]][mul[top][poly[j]]];\n"
    "    cur[0] = sub_[0][mul[top][poly[0]]];\n")
rep("            for (int j = col; j < T; j++) { int x = m[r][j] - mul[f][m[col][j]]; if (x < 0) x += Q; m[r][j] = x; }\n",
    "            for (int j = col; j < T; j++) m[r][j] = sub_[m[r][j]][mul[f][m[col][j]]];\n")
# field setup instead of the prime tables
rep("    for (int a = 0; a < Q; a++) for (int b = 0; b < Q; b++) mul[a][b] = (a * b) % Q;\n"
    "    for (int a = 1; a < Q; a++) for (int b = 1; b < Q; b++) if (mul[a][b] == 1) inv_[a] = b;\n",
    "    if (!setup_field(Q)) { fprintf(stderr, \"q=%d is not a supported prime power (primes <= 16, 4, 8, 9, 16)\\n\", Q); return 1; }\n")
rep('    if (T > MAXT || Q > MAXQ || S > MAXORB || K > 65000) { fprintf(stderr, "limits: t<=%d q<=%d s<=%d k<65000\\n", MAXT, MAXQ, MAXORB); return 1; }\n',
    '    if (T > MAXT || Q > MAXQ || S > MAXORB || K > 65000) { fprintf(stderr, "limits: t<=%d q<=%d s<=%d k<65000\\n", MAXT, MAXQ, MAXORB); return 1; }\n'
    '    if (T < 3) { fprintf(stderr, "t >= 3 required\\n"); return 1; }\n')
# header line on the field for non-prime q
rep("    for (int d = 1; d <= T; d++) { fprintf(f, \"# GF(%d^%d) primitive polynomial",
    "    if (QE > 1) { fprintf(f, \"# GF(%d) = GF(%d)[x]/(f), element code sum c_i %d^i (coordinates in the basis 1, x, ...), f coefficients (x^0..x^%d):\", Q, QP, QP, QE); for (int j = 0; j <= QE; j++) fprintf(f, \" %d\", QPOLY[j]); fprintf(f, \"\\n\"); }\n"
    "    for (int d = 1; d <= T; d++) { fprintf(f, \"# GF(%d^%d) primitive polynomial")
# fast pass: insert before the output section
FAST = r'''
/* incremental exact pass (light mode): per row, a reduced row echelon basis of the span of the first l
   columns of the t-set; at l = t-1 a normal vector n of that hyperplane, and the last column u is covered
   in that row iff n . u != 0. Same task list, order and per-thread lists as light_pass(). */
static int slowpass = 0;
typedef struct { uint8_t b[MAXT][MAXT]; uint8_t piv[MAXT]; uint8_t dep; } RState;
static inline void rs_add(const RState *s, RState *o, int l, const uint8_t *v) {
    if (s->dep) { o->dep = 1; return; }
    uint8_t w[MAXT]; memcpy(w, v, T);
    for (int i = 0; i < l; i++) { int f = w[s->piv[i]]; if (f) for (int j = 0; j < T; j++) w[j] = sub_[w[j]][mul[f][s->b[i][j]]]; }
    int p = -1; for (int j = 0; j < T; j++) if (w[j]) { p = j; break; }
    if (p < 0) { o->dep = 1; return; }
    o->dep = 0; int iv = inv_[w[p]]; for (int j = 0; j < T; j++) w[j] = mul[iv][w[j]];
    for (int i = 0; i < l; i++) { o->piv[i] = s->piv[i]; int f = s->b[i][p];
        if (f) for (int j = 0; j < T; j++) o->b[i][j] = sub_[s->b[i][j]][mul[f][w[j]]]; else memcpy(o->b[i], s->b[i], T); }
    memcpy(o->b[l], w, T); o->piv[l] = p;
}
static long light_pass_fast(void) {
    U.n = 0; int aborted = 0;
    List *Ul = calloc(NTHREADS, sizeof(List));
    long tasks = 0; int *tj0 = malloc(sizeof(int) * (size_t)K * S), *tj1 = malloc(sizeof(int) * (size_t)K * S);
    for (int j0 = 0; j0 < S; j0++) for (int j1 = j0 + 1; j1 < K; j1++) { tj0[tasks] = j0; tj1[tasks] = j1; tasks++; }
    const int R = nrows, isprime = (QE == 1);
    #pragma omp parallel num_threads(NTHREADS)
    {
        RState *st = malloc(sizeof(RState) * (size_t)(T + 1) * R); /* st[l*R + r]: state after l columns */
        uint8_t nrm[MAXROWS][MAXT]; int nlive; int live[MAXROWS];
        Rep rep; uint16_t *c = rep.c; int tid = omp_get_thread_num();
        #pragma omp for schedule(dynamic, 1)
        for (long ti = 0; ti < tasks; ti++) {
            c[0] = tj0[ti]; c[1] = tj1[ti]; if (c[1] + (T - 2) > K - 1) continue;
            for (int r = 0; r < R; r++) { RState z; z.dep = 0; rs_add(&z, &st[1 * R + r], 0, rows[r].vec + (size_t)c[0] * T); rs_add(&st[1 * R + r], &st[2 * R + r], 1, rows[r].vec + (size_t)c[1] * T); }
            /* iterative nested loops over c[2..T-1] */
            int l = 2; c[2] = c[1];
            while (l >= 2) {
                c[l]++;
                if (c[l] > K - 1 - (T - 1 - l)) { l--; continue; }
                if (l < T - 1) {
                    for (int r = 0; r < R; r++) rs_add(&st[l * R + r], &st[(l + 1) * R + r], l, rows[r].vec + (size_t)c[l] * T);
                    if (l + 1 == T - 1) { /* normal vectors for the rows still independent */
                        nlive = 0;
                        for (int r = 0; r < R; r++) { const RState *s = &st[(T - 1) * R + r]; if (s->dep) continue;
                            int used[MAXT] = {0}; for (int i = 0; i < T - 1; i++) used[s->piv[i]] = 1; int f = 0; while (used[f]) f++;
                            memset(nrm[nlive], 0, T); nrm[nlive][f] = 1; for (int i = 0; i < T - 1; i++) nrm[nlive][s->piv[i]] = sub_[0][s->b[i][f]];
                            live[nlive++] = r; }
                        /* innermost column */
                        for (int d = c[T - 2] + 1; d <= K - 1; d++) {
                            int cov = 0;
                            for (int a = 0; a < nlive && !cov; a++) { const uint8_t *u = rows[live[a]].vec + (size_t)d * T; const uint8_t *nn = nrm[a];
                                if (isprime) { int s = 0; for (int j = 0; j < T; j++) s += nn[j] * u[j]; cov = (s % Q) != 0; }
                                else { int s = 0; for (int j = 0; j < T; j++) s = add_[s][mul[nn[j]][u[j]]]; cov = s != 0; } }
                            if (!cov) { c[T - 1] = d; list_push(&Ul[tid], &rep); if (Ul[tid].n > Ucap) aborted = 1; }
                        }
                        continue; /* advance c[l] = c[T-2] */
                    }
                    l++; c[l] = c[l - 1];
                } else { /* T == 3: l == T-1 == 2 handled as innermost directly */
                    int cov = 0;
                    for (int r = 0; r < R && !cov; r++) cov = covered_by(rows[r].vec, c);
                    if (!cov) { list_push(&Ul[tid], &rep); if (Ul[tid].n > Ucap) aborted = 1; }
                }
            }
        }
        free(st);
    }
    for (int tid = 0; tid < NTHREADS; tid++) { for (long i = 0; i < Ul[tid].n; i++) list_push(&U, &Ul[tid].a[i]); free(Ul[tid].a); }
    free(Ul); free(tj0); free(tj1); return aborted ? -1 : U.n;
}
/* ---------- output ---------- */
'''
rep("/* ---------- output ---------- */\n", FAST.lstrip("\n"))
rep('        long u = light_pass();\n', '        long u = slowpass ? light_pass() : light_pass_fast();\n')
rep('u = light_pass(); }\n', 'u = slowpass ? light_pass() : light_pass_fast(); }\n')
rep('        else if (!strcmp(argv[i], "-v")) verbose = 2;\n',
    '        else if (!strcmp(argv[i], "-v")) verbose = 2;\n        else if (!strcmp(argv[i], "-slowpass")) slowpass = 1;\n')
open(sys.argv[2], "w").write(src)
print("ok")
