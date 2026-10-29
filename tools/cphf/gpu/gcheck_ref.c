/* gcheck_ref.c - reference (CPU, one thread) version of the GPU checker's enumeration, for testing:
   every representative t-set {c0 < ... < c_{t-1}}, c0 < SO; for each row the normal vector of the
   first t-1 vectors (Gaussian elimination), covered iff some row has n . v[c_{t-1}] != 0.
   usage: gcheck_ref FILE t q [s] */
#include "gfield.h"
#include "common.h"
int main(int argc, char **argv) {
    if (argc < 4) { fprintf(stderr, "usage: gcheck_ref FILE t q [s]\n"); return 2; }
    T = atoi(argv[2]); Q = atoi(argv[3]); if (argc > 4) SO = atoi(argv[4]);
    if (T < 4 || T > 8 || !gf_init(Q)) { fprintf(stderr, "bad t or q\n"); return 2; }
    if (!read_family(argv[1])) return 2;
    if (K % SO) { fprintf(stderr, "k not a multiple of s\n"); return 2; }
    printf("family: n=%d k=%d t=%d q=%d s=%d\n", N, K, T, Q, SO);
    if (!certify(1)) { printf("RESULT: symmetry certificate FAILED\n"); return 3; }
    printf("symmetry certificate passed\n");
    long long bad = 0, tot = 0; int S[16]; uint8_t nv[64 * 16], has[64], M[16 * 16];
    /* enumerate prefixes c0<...<c_{t-2} with c0 < SO, then the last column */
    for (int i = 0; i < T - 1; i++) S[i] = i;
    for (;;) {
        if (S[0] >= SO) break;
        for (int r = 0; r < N; r++) { for (int i = 0; i < T - 1; i++) memcpy(M + i * T, VV + ((size_t)S[i] * N + r) * T, T); has[r] = normal_of(M, nv + r * T); }
        for (int c = S[T - 2] + 1; c < K; c++) {
            int cov = 0;
            for (int r = 0; r < N && !cov; r++) if (has[r]) { const uint8_t *v = VV + ((size_t)c * N + r) * T; uint8_t s = 0;
                for (int j = 0; j < T; j++) s = GADD[s][GMUL[nv[r * T + j]][v[j]]]; if (s) cov = 1; }
            tot++; if (!cov) { bad++; if (bad <= 5) { printf("  uncovered:"); for (int i = 0; i < T - 1; i++) printf(" %d", S[i]); printf(" %d\n", c); } }
        }
        int i = T - 2; while (i >= 0 && S[i] == K - 1 - (T - 1 - i)) i--;   /* last prefix element can be at most K-2 */
        if (i < 0) break; S[i]++; for (int j = i + 1; j < T - 1; j++) S[j] = S[j - 1] + 1;
    }
    printf("checked %lld representative t-sets, uncovered %lld\nRESULT: %s\n", tot, bad, bad ? "NOT a CPHF" : "CPHF VERIFIED");
    return bad ? 1 : 0;
}
