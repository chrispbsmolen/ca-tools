/* gfield.h - GF(q) for q <= 16 by polynomial arithmetic (no logarithm tables), shared by the
   reference C checker and the Metal host. Element code: sum c_i p^i, coordinates in the basis
   1, x, ..., x^(e-1) of GF(p)[x]/(f), f the Conway polynomial (the convention of the CPHF files). */
#include <stdint.h>
static int gq, gp, ge;
static uint8_t GMUL[16][16], GADD[16][16], GNEG[16], GINV[16];
static int gf_poly(int q, int *f) { /* f[0..e-1], monic x^e + ... */
    if (q == 4) { f[0] = 1; f[1] = 1; return 1; }
    if (q == 8) { f[0] = 1; f[1] = 1; f[2] = 0; return 1; }
    if (q == 9) { f[0] = 2; f[1] = 2; return 1; }
    if (q == 16) { f[0] = 1; f[1] = 1; f[2] = 0; f[3] = 0; return 1; }
    return 0;
}
static int gf_init(int q) {
    gq = q; gp = 0; for (int d = 2; d <= q; d++) if (q % d == 0) { gp = d; break; }
    ge = 0; int x = 1; while (x < q) { x *= gp; ge++; }
    if (x != q || q > 16) return 0;
    for (int d = 2; d < gp; d++) if (gp % d == 0) return 0;
    int f[4] = {0};
    if (ge > 1 && !gf_poly(q, f)) return 0;
    int A[4], B[4];
    for (int a = 0; a < q; a++) for (int b = 0; b < q; b++) {
        int t = a, u = b;
        for (int i = 0; i < ge; i++) { A[i] = t % gp; t /= gp; B[i] = u % gp; u /= gp; }
        int s[4], code = 0;
        for (int i = 0; i < ge; i++) s[i] = (A[i] + B[i]) % gp;
        for (int i = ge - 1; i >= 0; i--) code = code * gp + s[i];
        GADD[a][b] = (uint8_t)code;
        int prod[8] = {0};
        for (int i = 0; i < ge; i++) for (int j = 0; j < ge; j++) prod[i + j] = (prod[i + j] + A[i] * B[j]) % gp;
        for (int d = 2 * ge - 2; d >= ge; d--) { int c = prod[d]; if (!c) continue; prod[d] = 0;
            for (int i = 0; i < ge; i++) prod[d - ge + i] = ((prod[d - ge + i] - c * f[i]) % gp + gp) % gp; }
        code = 0; for (int i = ge - 1; i >= 0; i--) code = code * gp + prod[i];
        GMUL[a][b] = (uint8_t)code;
    }
    for (int a = 0; a < q; a++) { for (int b = 0; b < q; b++) if (GADD[a][b] == 0) GNEG[a] = b;
        GINV[a] = 0; for (int b = 1; b < q; b++) if (GMUL[a][b] == 1) GINV[a] = b; }
    /* sanity: field axioms on all pairs/triples */
    for (int a = 1; a < q; a++) if (!GINV[a]) return 0;
    for (int a = 0; a < q; a++) for (int b = 0; b < q; b++) for (int c = 0; c < q; c++) {
        if (GMUL[a][GADD[b][c]] != GADD[GMUL[a][b]][GMUL[a][c]]) return 0;
        if (GMUL[GMUL[a][b]][c] != GMUL[a][GMUL[b][c]]) return 0; }
    return 1;
}
