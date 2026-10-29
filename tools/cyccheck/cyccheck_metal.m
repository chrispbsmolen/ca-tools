/* cyccheck_metal.m - GPU (Metal) version of cyccheck.c for strengths 4, 5 and 6.
 *
 * Same array, same symmetry certificate and the same representatives as cyccheck.c: all sets
 * {0, s} + (t-2)-subset of the other q - 2 elements, s = 1 and s = n0 (smallest nonresidue).
 * One threadgroup per (t-4)-subset of fixed further columns (none for t = 4, c for t = 5, c < d
 * for t = 6): it builds the 2^(t-2) row cells of its fixed columns in threadgroup memory; each
 * thread then takes pairs e < f of the later columns and checks that every cell meets all four
 * value combinations of columns e and f.  The count printed per s is the number of uncovered
 * representatives, exactly as cyccheck.c prints it (and checked against it by gpu_test.sh).
 *
 * build: clang -O2 -fobjc-arc -framework Metal -framework Foundation -o cyccheck_metal cyccheck_metal.m
 * usage: cyccheck_metal q t [vectorfile|-]
 */
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

static const char *KSRC =
"#include <metal_stdlib>\n"
"using namespace metal;\n"
"struct Params { uint q; uint W; uint n; uint k; uint s; uint g0; uint lastmask; uint pad; };\n"
"inline uint unrank2(uint g, thread uint &i) {\n"
"  uint j = (uint)((1.0f + sqrt(1.0f + 8.0f * (float)g)) * 0.5f);\n"
"  while ((ulong)j * (ulong)(j - 1) / 2 > (ulong)g) j--;\n"
"  while ((ulong)(j + 1) * (ulong)j / 2 <= (ulong)g) j++;\n"
"  i = g - j * (j - 1) / 2;\n"
"  return j;\n"
"}\n"
"kernel void chk(device const uint *B [[buffer(0)]],\n"
"                device const uint *cand [[buffer(1)]],\n"
"                constant Params &P [[buffer(2)]],\n"
"                device atomic_uint *cnt [[buffer(3)]],\n"
"                device atomic_uint *rec [[buffer(4)]],\n"
"                uint gid [[threadgroup_position_in_grid]],\n"
"                uint tid [[thread_index_in_threadgroup]],\n"
"                uint tgs [[threads_per_threadgroup]]) {\n"
"  threadgroup uint cells[16 * 64];\n"
"  threadgroup uint nonempty[16];\n"
"  uint g = P.g0 + gid;\n"
"  uint cols[4]; cols[0] = 0; cols[1] = P.s;\n"
"  int last = -1;\n"
"  if (P.k == 1) { last = (int)g; cols[2] = cand[g]; }\n"
"  else if (P.k == 2) { uint i; uint j = unrank2(g, i); cols[2] = cand[i]; cols[3] = cand[j]; last = (int)j; }\n"
"  uint L = 2 + P.k, nc = 1u << L, W = P.W;\n"
"  uint m = (uint)((int)P.n - 1 - last);\n"
"  for (uint idx = tid; idx < nc * W; idx += tgs) {\n"
"    uint pc = idx / W, w = idx % W;\n"
"    uint v = (w == W - 1) ? P.lastmask : 0xffffffffu;\n"
"    for (uint j = 0; j < L; j++) { uint b = B[cols[j] * W + w]; v &= ((pc >> j) & 1u) ? b : ~b; }\n"
"    cells[idx] = v;\n"
"  }\n"
"  threadgroup_barrier(mem_flags::mem_threadgroup);\n"
"  if (tid < nc) { uint o = 0; for (uint w = 0; w < W; w++) o |= cells[tid * W + w]; nonempty[tid] = (o != 0) ? 1u : 0u; }\n"
"  threadgroup_barrier(mem_flags::mem_threadgroup);\n"
"  uint npairs = (m >= 2) ? m * (m - 1) / 2 : 0;\n"
"  bool empty = false;\n"
"  for (uint pc = 0; pc < nc; pc++) if (nonempty[pc] == 0) empty = true;\n"
"  if (empty) { if (tid == 0) atomic_fetch_add_explicit(&cnt[gid], npairs, memory_order_relaxed); return; }\n"
"  for (uint rk = tid; rk < npairs; rk += tgs) {\n"
"    uint a; uint l = unrank2(rk, a);\n"
"    uint e = cand[last + 1 + (int)a], f = cand[last + 1 + (int)l];\n"
"    device const uint *Be = B + e * W; device const uint *Bf = B + f * W;\n"
"    bool ok = true;\n"
"    for (uint pc = 0; pc < nc && ok; pc++) {\n"
"      for (uint c4 = 0; c4 < 4 && ok; c4++) {\n"
"        bool found = false;\n"
"        for (uint w = 0; w < W; w++) {\n"
"          uint be = Be[w], bf = Bf[w];\n"
"          uint v = cells[pc * W + w] & ((c4 & 1u) ? be : ~be) & ((c4 & 2u) ? bf : ~bf);\n"
"          if (v != 0) { found = true; break; }\n"
"        }\n"
"        if (!found) ok = false;\n"
"      }\n"
"    }\n"
"    if (!ok) {\n"
"      atomic_fetch_add_explicit(&cnt[gid], 1u, memory_order_relaxed);\n"
"      uint slot = atomic_fetch_add_explicit(&rec[0], 1u, memory_order_relaxed);\n"
"      if (slot < 8) {\n"
"        for (uint j = 0; j < L; j++) atomic_store_explicit(&rec[1 + slot * 8 + j], cols[j], memory_order_relaxed);\n"
"        atomic_store_explicit(&rec[1 + slot * 8 + L], e, memory_order_relaxed);\n"
"        atomic_store_explicit(&rec[1 + slot * 8 + L + 1], f, memory_order_relaxed);\n"
"      }\n"
"    }\n"
"  }\n"
"}\n";

typedef struct { uint32_t q, W, n, k, s, g0, lastmask, pad; } Params;

static long long pm(long long a, long long e, long long m) { long long r = 1; a %= m; while (e) { if (e & 1) r = r * a % m; a = a * a % m; e >>= 1; } return r; }
static int is_prime(int n) { if (n < 2) return 0; for (int d = 2; (long long)d * d <= n; d++) if (n % d == 0) return 0; return 1; }

int main(int argc, char **argv) {
  @autoreleasepool {
    if (argc < 3) { fprintf(stderr, "usage: cyccheck_metal q t [vectorfile|-]\n"); return 2; }
    int q = atoi(argv[1]), t = atoi(argv[2]);
    if (!is_prime(q) || q < 11 || t < 4 || t > 6 || q > 2047) { fprintf(stderr, "need prime 11 <= q <= 2047 and 4 <= t <= 6\n"); return 2; }
    unsigned char *x = malloc(q);
    for (int i = 0; i < q; i++) x[i] = (i == 0) ? 0 : (pm(i, (q - 1) / 2, q) == 1 ? 0 : 1);
    if (argc > 3 && strcmp(argv[3], "-")) {
      FILE *fp = fopen(argv[3], "r"); if (!fp) { perror(argv[3]); return 2; }
      int i = 0, ch; unsigned char *y = malloc(q);
      while (i < q && (ch = fgetc(fp)) != EOF) { if (ch == '0' || ch == '1') y[i++] = ch - '0'; }
      fclose(fp);
      if (i < q) { fprintf(stderr, "vector file too short\n"); return 2; }
      int diff = 0; for (int j = 0; j < q; j++) if (y[j] != x[j]) diff++;
      printf("vector file %s: %d entries differ from the nonresidue indicator\n", argv[3], diff);
      memcpy(x, y, q); free(y);
    }
    /* symmetry certificate, as in cyccheck.c */
    int g = 0;
    for (int c = 2; c < q && !g; c++) { int ok = 1, mm = q - 1; for (int p = 2; p <= mm; p++) if (mm % p == 0) { while (mm % p == 0) mm /= p; if (pm(c, (q - 1) / p, q) == 1) { ok = 0; break; } } if (ok) g = c; }
    int a = (int)((long long)g * g % q);
    int msym = 1; for (int i = 0; i < q; i++) if (x[(long long)a * i % q] != x[i]) { msym = 0; break; }
    int n0 = 0; for (int i = 2; i < q; i++) if (pm(i, (q - 1) / 2, q) != 1) { n0 = i; break; }
    printf("q=%d t=%d primitive root %d, residue multiplier a=%d: x[a i]=x[i] for all i: %s; nonresidue n0=%d\n", q, t, g, a, msym ? "yes" : "NO", n0);
    if (!msym) { printf("RESULT: symmetry certificate failed, reduction not valid\n"); return 1; }

    id<MTLDevice> dev = MTLCreateSystemDefaultDevice();
    if (!dev) { fprintf(stderr, "no Metal device\n"); return 2; }
    printf("GPU: %s\n", [[dev name] UTF8String]);
    NSError *err = nil;
    id<MTLLibrary> lib = [dev newLibraryWithSource:[NSString stringWithUTF8String:KSRC] options:nil error:&err];
    if (!lib) { fprintf(stderr, "kernel compile failed: %s\n", [[err description] UTF8String]); return 2; }
    id<MTLFunction> fn = [lib newFunctionWithName:@"chk"];
    id<MTLComputePipelineState> pso = [dev newComputePipelineStateWithFunction:fn error:&err];
    if (!pso) { fprintf(stderr, "pipeline failed: %s\n", [[err description] UTF8String]); return 2; }
    id<MTLCommandQueue> queue = [dev newCommandQueue];

    uint32_t W = (q + 31) / 32;
    uint32_t lastmask = (q % 32) ? ((1u << (q % 32)) - 1) : 0xffffffffu;
    id<MTLBuffer> bufB = [dev newBufferWithLength:(size_t)q * W * 4 options:MTLResourceStorageModeShared];
    uint32_t *B = (uint32_t *)[bufB contents]; memset(B, 0, (size_t)q * W * 4);
    for (int c = 0; c < q; c++) for (int r = 0; r < q; r++) if (x[((c - r) % q + q) % q]) B[(size_t)c * W + r / 32] |= 1u << (r % 32);

    const uint32_t CHUNK = 8192;  /* threadgroups per command buffer */
    id<MTLBuffer> bufCnt = [dev newBufferWithLength:CHUNK * 4 options:MTLResourceStorageModeShared];
    id<MTLBuffer> bufRec = [dev newBufferWithLength:(1 + 8 * 8) * 4 options:MTLResourceStorageModeShared];
    memset([bufRec contents], 0, (1 + 8 * 8) * 4);
    NSUInteger tgs = 256; if (tgs > pso.maxTotalThreadsPerThreadgroup) tgs = pso.maxTotalThreadsPerThreadgroup;

    long long total_bad = 0;
    int ss[2] = {1, n0};
    NSDate *t0 = [NSDate date];
    for (int si = 0; si < 2; si++) {
      int s = ss[si];
      uint32_t n = q - 2;
      id<MTLBuffer> bufCand = [dev newBufferWithLength:n * 4 options:MTLResourceStorageModeShared];
      uint32_t *cand = (uint32_t *)[bufCand contents]; uint32_t mm = 0;
      for (int i = 1; i < q; i++) if (i != s) cand[mm++] = i;
      uint32_t k = t - 4;
      uint64_t groups = (k == 0) ? 1 : (k == 1) ? n : (uint64_t)n * (n - 1) / 2;
      long long bad = 0;
      for (uint64_t g0 = 0; g0 < groups; g0 += CHUNK) {
        uint32_t G = (uint32_t)((groups - g0 < CHUNK) ? (groups - g0) : CHUNK);
        memset([bufCnt contents], 0, CHUNK * 4);
        Params P = { (uint32_t)q, W, n, k, (uint32_t)s, (uint32_t)g0, lastmask, 0 };
        id<MTLCommandBuffer> cb = [queue commandBuffer];
        id<MTLComputeCommandEncoder> enc = [cb computeCommandEncoder];
        [enc setComputePipelineState:pso];
        [enc setBuffer:bufB offset:0 atIndex:0];
        [enc setBuffer:bufCand offset:0 atIndex:1];
        [enc setBytes:&P length:sizeof(P) atIndex:2];
        [enc setBuffer:bufCnt offset:0 atIndex:3];
        [enc setBuffer:bufRec offset:0 atIndex:4];
        [enc dispatchThreadgroups:MTLSizeMake(G, 1, 1) threadsPerThreadgroup:MTLSizeMake(tgs, 1, 1)];
        [enc endEncoding];
        [cb commit];
        [cb waitUntilCompleted];
        if (cb.status != MTLCommandBufferStatusCompleted) { fprintf(stderr, "GPU command buffer failed: %s\n", [[cb.error description] UTF8String]); return 3; }
        uint32_t *cnt = (uint32_t *)[bufCnt contents];
        for (uint32_t i = 0; i < G; i++) bad += cnt[i];
      }
      printf("  second element %d: uncovered representatives %lld\n", s, bad);
      total_bad += bad;
    }
    uint32_t *rec = (uint32_t *)[bufRec contents];
    for (uint32_t i = 0; i < rec[0] && i < 8; i++) { printf("  uncovered:"); for (int j = 0; j < t; j++) printf(" %u", rec[1 + i * 8 + j]); printf("\n"); }
    printf("GPU time %.1f s\n", -[t0 timeIntervalSinceNow]);
    printf("RESULT q=%d t=%d: %s (uncovered representatives counted: %lld) [GPU]\n", q, t, total_bad ? "NOT covered" : "CA VERIFIED", total_bad);
    return total_bad ? 1 : 0;
  }
}
