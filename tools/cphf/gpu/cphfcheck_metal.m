/* cphfcheck_metal.m - exact check of a cyclic-symmetric covering perfect hash family on an Apple GPU.
 *
 * Written 2026-10-29 for ca-tools as a second checker, independent of repcheck.c / repcheck_pp.c:
 * no shared code, another method. Same file format and conventions as repcheck_pp.c (vectors of
 * GF(q)^t written in base q, most significant digit first; q = p^e with the Conway polynomial;
 * columns col = c*s + i, shift col -> col + s).
 *
 * 1. Symmetry certificate (host, common.h): for each row, A is solved from t independent columns
 *    and checked at every column, with the wrap A v[col] = mu v[col+s-k] for one mu != 0, and A
 *    invertible. Then every shift orbit of t-sets has a member whose smallest column is < s.
 * 2. Enumeration (GPU): every t-set c_0 < ... < c_{t-1} with c_0 < s. The host fixes c_0..c_{t-4};
 *    each GPU thread takes one pair c_{t-3} < c_{t-2}, computes for every row a normal vector n_r
 *    of the t-1 prefix vectors by Gaussian elimination over GF(q) (n_r = 0 if they are dependent),
 *    and then tests every last column c_{t-1}: covered iff n_r . v_r[c_{t-1}] != 0 for some row.
 * Field arithmetic is by tables built from polynomial multiplication (gfield.h), checked against
 * the field axioms.
 *
 * build: clang -O2 -fobjc-arc -framework Metal -framework Foundation -o cphfcheck_metal cphfcheck_metal.m
 * usage: cphfcheck_metal FILE t q [s]          (t = 4..8, q <= 16, n <= 32)
 */
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include "gfield.h"
#include "common.h"

static const char *KSRC =
"#include <metal_stdlib>\n"
"using namespace metal;\n"
"struct P { uint N; uint K; uint T; uint nfix; uint fix[8]; uint L; uint m; uint pad0; uint pad1; };\n"
"inline uint unrank2(uint g, thread uint &i) {\n"
"  uint j = (uint)((1.0f + sqrt(1.0f + 8.0f * (float)g)) * 0.5f);\n"
"  while ((ulong)j * (ulong)(j - 1) / 2 > (ulong)g) j--;\n"
"  while ((ulong)(j + 1) * (ulong)j / 2 <= (ulong)g) j++;\n"
"  i = g - j * (j - 1) / 2; return j; }\n"
"kernel void chk(device const uchar *V [[buffer(0)]], constant uchar *TAB [[buffer(1)]],\n"
"                constant P &p [[buffer(2)]], device atomic_uint *cnt [[buffer(3)]],\n"
"                device atomic_uint *rec [[buffer(4)]], uint gid [[thread_position_in_grid]]) {\n"
"  uint npairs = p.m * (p.m - 1) / 2; if (gid >= npairs) return;\n"
"  constant uchar *MUL = TAB; constant uchar *ADD = TAB + 256; constant uchar *NEG = TAB + 512; constant uchar *INV = TAB + 528;\n"
"  uint a; uint b = unrank2(gid, a);\n"
"  uint cols[8]; for (uint i = 0; i < p.nfix; i++) cols[i] = p.fix[i];\n"
"  uint T = p.T, N = p.N, K = p.K, h = p.nfix;\n"
"  cols[h] = p.L + 1 + a; cols[h + 1] = p.L + 1 + b;\n"
"  uint last = cols[h + 1];\n"
"  uchar nv[32 * 8]; uint has = 0;\n"
"  for (uint r = 0; r < N; r++) {\n"
"    uchar M[8 * 8]; uint piv[8];\n"
"    for (uint i = 0; i < T - 1; i++) for (uint j = 0; j < T; j++) M[i * T + j] = V[(cols[i] * N + r) * T + j];\n"
"    uint rk = 0;\n"
"    for (uint c = 0; c < T && rk < T - 1; c++) {\n"
"      int pr = -1; for (uint i = rk; i < T - 1; i++) if (M[i * T + c]) { pr = (int)i; break; }\n"
"      if (pr < 0) continue;\n"
"      for (uint j = 0; j < T; j++) { uchar x = M[rk * T + j]; M[rk * T + j] = M[(uint)pr * T + j]; M[(uint)pr * T + j] = x; }\n"
"      uchar iv = INV[M[rk * T + c]];\n"
"      for (uint j = 0; j < T; j++) M[rk * T + j] = MUL[iv * 16 + M[rk * T + j]];\n"
"      for (uint i = 0; i < T - 1; i++) if (i != rk && M[i * T + c]) { uchar f = NEG[M[i * T + c]];\n"
"        for (uint j = 0; j < T; j++) M[i * T + j] = ADD[M[i * T + j] * 16 + MUL[f * 16 + M[rk * T + j]]]; }\n"
"      piv[rk] = c; rk++;\n"
"    }\n"
"    for (uint j = 0; j < T; j++) nv[r * 8 + j] = 0;\n"
"    if (rk < T - 1) continue;\n"
"    uint isp = 0; for (uint i = 0; i < rk; i++) isp |= 1u << piv[i];\n"
"    uint fc = 0; while ((isp >> fc) & 1u) fc++;\n"
"    nv[r * 8 + fc] = 1;\n"
"    for (uint i = 0; i < rk; i++) nv[r * 8 + piv[i]] = NEG[M[i * T + fc]];\n"
"    has |= 1u << r;\n"
"  }\n"
"  uint bad = 0;\n"
"  for (uint e = last + 1; e < K; e++) {\n"
"    bool cov = false;\n"
"    for (uint r = 0; r < N && !cov; r++) {\n"
"      if (!((has >> r) & 1u)) continue;\n"
"      device const uchar *v = V + (e * N + r) * T; uchar s = 0;\n"
"      for (uint j = 0; j < T; j++) s = ADD[s * 16 + MUL[nv[r * 8 + j] * 16 + v[j]]];\n"
"      if (s) cov = true;\n"
"    }\n"
"    if (!cov) {\n"
"      bad++;\n"
"      uint slot = atomic_fetch_add_explicit(&rec[0], 1u, memory_order_relaxed);\n"
"      if (slot < 8) { for (uint i = 0; i < h + 2; i++) atomic_store_explicit(&rec[1 + slot * 9 + i], cols[i], memory_order_relaxed);\n"
"        atomic_store_explicit(&rec[1 + slot * 9 + h + 2], e, memory_order_relaxed); }\n"
"    }\n"
"  }\n"
"  if (bad) { uint old = atomic_fetch_add_explicit(&cnt[0], bad, memory_order_relaxed);\n"
"    if (old + bad < old) atomic_fetch_add_explicit(&cnt[1], 1u, memory_order_relaxed); }\n"
"}\n";

typedef struct { uint32_t N, K, T, nfix, fix[8], L, m, pad0, pad1; } Params;

int main(int argc, char **argv) {
  @autoreleasepool {
    if (argc < 4) { fprintf(stderr, "usage: cphfcheck_metal FILE t q [s]\n"); return 2; }
    T = atoi(argv[2]); Q = atoi(argv[3]); if (argc > 4) SO = atoi(argv[4]);
    if (T < 4 || T > 8 || !gf_init(Q)) { fprintf(stderr, "need 4 <= t <= 8 and q a prime power <= 16\n"); return 2; }
    if (!read_family(argv[1])) return 2;
    if (N > 32) { fprintf(stderr, "at most 32 rows\n"); return 2; }
    if (K % SO) { fprintf(stderr, "k not a multiple of s\n"); return 2; }
    printf("family %s: n=%d k=%d t=%d q=%d s=%d\n", argv[1], N, K, T, Q, SO);
    if (!certify(1)) { printf("RESULT: symmetry certificate FAILED\n"); return 3; }
    printf("symmetry certificate passed (every row: A from t columns, checked at all %d columns, wrap scalar, det != 0)\n", K);

    id<MTLDevice> dev = MTLCreateSystemDefaultDevice();
    if (!dev) { fprintf(stderr, "no Metal device\n"); return 2; }
    printf("GPU: %s\n", [[dev name] UTF8String]);
    NSError *err = nil;
    id<MTLLibrary> lib = [dev newLibraryWithSource:[NSString stringWithUTF8String:KSRC] options:nil error:&err];
    if (!lib) { fprintf(stderr, "kernel compile failed: %s\n", [[err description] UTF8String]); return 2; }
    id<MTLComputePipelineState> pso = [dev newComputePipelineStateWithFunction:[lib newFunctionWithName:@"chk"] error:&err];
    if (!pso) { fprintf(stderr, "pipeline failed: %s\n", [[err description] UTF8String]); return 2; }
    id<MTLCommandQueue> queue = [dev newCommandQueue];

    id<MTLBuffer> bV = [dev newBufferWithBytes:VV length:(size_t)N * K * T options:MTLResourceStorageModeShared];
    uint8_t tab[544]; memset(tab, 0, sizeof tab);
    for (int a = 0; a < 16; a++) for (int b = 0; b < 16; b++) { tab[a * 16 + b] = GMUL[a][b]; tab[256 + a * 16 + b] = GADD[a][b]; }
    for (int a = 0; a < 16; a++) { tab[512 + a] = GNEG[a]; tab[528 + a] = GINV[a]; }
    id<MTLBuffer> bTab = [dev newBufferWithBytes:tab length:sizeof tab options:MTLResourceStorageModeShared];
    const int BATCH = 512;
    id<MTLBuffer> bCnt = [dev newBufferWithLength:BATCH * 8 options:MTLResourceStorageModeShared];
    id<MTLBuffer> bRec = [dev newBufferWithLength:(1 + 8 * 9) * 4 options:MTLResourceStorageModeShared];
    memset([bRec contents], 0, (1 + 8 * 9) * 4);
    NSUInteger tg = pso.maxTotalThreadsPerThreadgroup; if (tg > 256) tg = 256;

    /* host prefixes: c_0 < s, c_0 < c_1 < ... < c_{h-1}, h = t-3, with at least 2 columns after the last */
    int h = T - 3; int fix[8]; long long total_bad = 0; unsigned long long nsets = 0;
    NSDate *t0 = [NSDate date];
    for (int i = 0; i < h; i++) fix[i] = i;
    int done = 0;
    while (!done) {
      id<MTLCommandBuffer> cb = [queue commandBuffer];
      id<MTLComputeCommandEncoder> enc = [cb computeCommandEncoder];
      [enc setComputePipelineState:pso];
      [enc setBuffer:bV offset:0 atIndex:0];
      [enc setBuffer:bTab offset:0 atIndex:1];
      [enc setBuffer:bRec offset:0 atIndex:4];
      memset([bCnt contents], 0, BATCH * 8);
      int nb = 0;
      unsigned long long batch_sets = 0;
      while (nb < BATCH && !done && batch_sets < 20000000000ULL) {
        if (fix[0] >= SO) { done = 1; break; }
        int L = fix[h - 1]; uint32_t m = (uint32_t)(K - 1 - L);
        if (m >= 2) {
          Params P; memset(&P, 0, sizeof P); P.N = N; P.K = K; P.T = T; P.nfix = h;
          for (int i = 0; i < h; i++) P.fix[i] = fix[i]; P.L = L; P.m = m;
          uint32_t np = m * (m - 1) / 2;
          [enc setBytes:&P length:sizeof P atIndex:2];
          [enc setBuffer:bCnt offset:nb * 8 atIndex:3];
          [enc dispatchThreads:MTLSizeMake(np, 1, 1) threadsPerThreadgroup:MTLSizeMake(tg, 1, 1)];
          nb++;
          /* number of t-sets with this host prefix: C(m, 3) for the pair and the last column */
          nsets += (unsigned long long)m * (m - 1) * (m - 2) / 6; batch_sets += (unsigned long long)m * (m - 1) * (m - 2) / 6;
        }
        /* next host prefix (lexicographic), each element at most K-4+i... keep it simple: advance and let m<2 skip */
        int i = h - 1; while (i >= 0 && fix[i] >= K - 3 - (h - 1 - i)) i--;
        if (i < 0) { done = 1; break; }
        fix[i]++; for (int j = i + 1; j < h; j++) fix[j] = fix[j - 1] + 1;
      }
      [enc endEncoding];
      [cb commit]; [cb waitUntilCompleted];
      if (cb.status != MTLCommandBufferStatusCompleted) { fprintf(stderr, "GPU error: %s\n", [[cb.error description] UTF8String]); return 4; }
      uint32_t *c = (uint32_t *)[bCnt contents];
      for (int i = 0; i < nb; i++) total_bad += (long long)c[2 * i] + ((long long)c[2 * i + 1] << 32);
    }
    uint32_t *rec = (uint32_t *)[bRec contents];
    for (uint32_t i = 0; i < rec[0] && i < 8; i++) { printf("  uncovered:"); for (int j = 0; j < T; j++) printf(" %u", rec[1 + i * 9 + j]); printf("\n"); }
    printf("checked %llu representative t-sets, uncovered %lld, GPU time %.1f s\n", nsets, total_bad, -[t0 timeIntervalSinceNow]);
    printf("RESULT: %s [cphfcheck_metal]\n", total_bad ? "NOT a CPHF" : "CPHF VERIFIED");
    return total_bad ? 1 : 0;
  }
}
