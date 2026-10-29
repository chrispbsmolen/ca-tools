/* emu_kernel.c - the host loop and kernel of cphfcheck_metal.m transcribed to plain C (one thread),
   to test the enumeration (host prefixes + colex pairs) in the cloud. usage: emu_kernel FILE t q [s] */
#include <math.h>
#include "gfield.h"
#include "common.h"
static uint32_t unrank2(uint32_t g, uint32_t *i) { uint32_t j = (uint32_t)((1.0f + sqrtf(1.0f + 8.0f * (float)g)) * 0.5f);
  while ((uint64_t)j * (j - 1) / 2 > g) j--; while ((uint64_t)(j + 1) * j / 2 <= g) j++; *i = g - j * (j - 1) / 2; return j; }
static long long kernel(int h, const int *fix, int L, uint32_t m) {
  uint32_t npairs = m * (m - 1) / 2; long long bad = 0;
  for (uint32_t gid = 0; gid < npairs; gid++) {
    uint32_t a, b = unrank2(gid, &a); int cols[8]; for (int i = 0; i < h; i++) cols[i] = fix[i];
    cols[h] = L + 1 + a; cols[h + 1] = L + 1 + b; int last = cols[h + 1];
    uint8_t nv[32 * 8]; uint32_t has = 0;
    for (int r = 0; r < N; r++) { uint8_t M[64]; for (int i = 0; i < T - 1; i++) memcpy(M + i * T, VV + ((size_t)cols[i] * N + r) * T, T);
      if (normal_of(M, nv + r * 8)) has |= 1u << r; }
    for (int e = last + 1; e < K; e++) { int cov = 0;
      for (int r = 0; r < N && !cov; r++) { if (!((has >> r) & 1)) continue; const uint8_t *v = VV + ((size_t)e * N + r) * T; uint8_t s = 0;
        for (int j = 0; j < T; j++) s = GADD[s][GMUL[nv[r * 8 + j]][v[j]]];
        if (s) cov = 1; }
      if (!cov) bad++; }
  }
  return bad;
}
int main(int argc, char **argv) {
  T = atoi(argv[2]); Q = atoi(argv[3]); if (argc > 4) SO = atoi(argv[4]);
  if (!gf_init(Q) || !read_family(argv[1])) return 2;
  if (!certify(1)) { printf("certificate FAILED\n"); return 3; }
  int h = T - 3, fix[8]; long long bad = 0; unsigned long long nsets = 0;
  for (int i = 0; i < h; i++) fix[i] = i;
  for (;;) {
    if (fix[0] >= SO) break;
    int L = fix[h - 1]; uint32_t m = K - 1 - L;
    if (m >= 2) { bad += kernel(h, fix, L, m); nsets += (unsigned long long)m * (m - 1) * (m - 2) / 6; }
    int i = h - 1; while (i >= 0 && fix[i] >= K - 3 - (h - 1 - i)) i--;
    if (i < 0) break; fix[i]++; for (int j = i + 1; j < h; j++) fix[j] = fix[j - 1] + 1;
  }
  printf("checked %llu representative t-sets, uncovered %lld\n", nsets, bad);
  return 0;
}
