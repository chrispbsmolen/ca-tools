# Faster exact verification of explicit covering arrays

Since 2026-11-02 the program called ca_verify2 here is `ca_verify.c` itself (version 2), and
the program called ca_verify here is the first version, which it replaced. The names below are
those of the time of writing.

Problem. An N x k array A over {0..v-1} is a CA(N; t, k, v) iff for every
t-set of columns every one of the v^t value tuples appears in some row. The
reference tool `ca_verify.c` enumerates the C(k,t) column sets and, for
each, marks the tuple of every row in a v^t-bit bitmap and popcounts it:
about C(k,t) * N * t scalar operations with a strided memory access per row
(each row's t entries are k bytes apart). Measured on this 2-core VM:
608 to 668 ns per column set for N = 216 (one thread, k = 200 and 150),
so CA(216; 4, 1368, 2) with C(1368,4) = 1.455e11 column sets needs about
24 to 27 CPU-hours (the run started by the main session had used 3 CPU-hours
after 3 hours and was far from done).

Everything below is exact. No sampling, no probabilistic shortcut; every
idea is a different way to compute the same predicate, and each section
says why the computed quantity equals the original definition.

Notation: W = ceil(N/64) words per row set, Kw = ceil(k/64) words per
column set, c = largest column of a (t-1)-prefix, so k-1-c candidate last
columns remain.

## Ranking

1. (implemented, the core) t = (t-1) + 1 split with bit-sliced last column
   and per-prefix row classes. Cost per (t-1)-prefix: N row visits, each
   touching ceil((k-1-c)/256) 256-bit words per value. Total about
   C(k,t-1) * N * v * (k/t)/256 vector operations versus C(k,t) * N * t
   scalar operations: an asymptotic factor of order 128 t / v fewer
   operations, and each operation is a 256-bit AND/OR on contiguous data.
   Measured (CPU time, see BENCH.md): 340x to 375x on the four t = 4
   binary arrays (24 to 62 CPU-hours extrapolated for ca_verify against 4
   to 10 CPU-minutes), 61x at t = 5 (900 x 200), 18x at t = 6 (1900 x 100),
   1.7x to 29x at t = 3 with v = 5 to 25 (where ca_verify already takes
   only seconds).
2. (implemented) One-hot lanes for medium v: a column's seen-value set as a
   v-bit lane; one pass per 256 bits regardless of v. Replaces v passes
   of bit planes when v is large or k is small (the planes pay for whole
   256-column chunks). 12x faster than the plane kernel on
   CA(30625; 3, 52, 25).
3. (implemented) Incremental class formation: classes of a prefix are
   intersections of per-(column, value) row bitsets along a depth-first
   enumeration (one bitset AND per class), or a counting sort of the parent
   class by the new column when v^(t-1) * W exceeds about 8N. Negligible
   next to the kernel for binary t = 4; matters for v = 25.
4. (implemented) SIMD everywhere with portable code: GCC/clang vector
   extensions, an AVX2 clone selected at run time on x86-64, the same source
   compiling to NEON pairs on arm64 and to SSE2 pairs as the baseline.
5. (implemented) Popcount-free emptiness: the covering test is one
   `(AND | ~OR) & mask` (binary) or `~(AND over values of OR) & mask` per
   256 columns; popcounts and tuple identification happen only when the
   test fires, which is never for a covering array.
6. (implemented) Deterministic work split by smallest column: dynamic
   thread scheduling, and shards SHARD/NSHARDS (smallest column congruent
   to SHARD mod NSHARDS) whose column-set counts add up to C(k,t) exactly.
   Gap examples carry their lexicographic rank so the printed examples are
   the ones `ca_verify` prints for the same thread count.
7. (implemented, binary only) complement symmetry: without don't-cares the
   value-0 plane is the complement of the value-1 plane, so one plane per
   row with an OR and an AND accumulator (value 1 missing iff OR bit clear,
   value 0 missing iff AND bit set) halves the loads.
8. (evaluated, not adopted) Pair row-set tables, t = 2 + 2. Per 4-set 16
   intersections of two W-word sets. With N <= 256 each is one AVX2 AND and
   one test: 16 to 32 instructions per 4-set, versus about 3 cycles per
   4-set for idea 1 at k = 1368 (see the cost model below). Storing the
   tables for all C(k,2) pairs needs 4 * 32 bytes * C(1368,2) = 120 MB; on
   the fly it is the same work as idea 1 without the amortization.
   A refinement, "class lanes" (rows permuted per (a,b) so the four classes
   of (a,b) occupy 64-bit lanes of one 256-bit register, then 13
   instructions per (c,d) pair with no data-dependent branches), is about
   equal to idea 1 at k = 1368 and up to 3x better at k = 300, but requires
   every class of (a,b) to have at most 64 rows: for N = 242 a class exceeds
   64 rows in most pairs. Worth doing for N <= 200 (future work).
9. (evaluated, not adopted as default) Early exit and rarest-pattern
   ordering. `ca_verify` prints the number of column sets with gaps and the
   total number of missing tuples, and `tools/check_submission.py` keeps
   its first output line; a drop-in replacement must therefore do the
   whole count. Provided as `--fail-fast` (exit 1 at the first gap with
   counts that are then lower bounds). Ordering tuples by rarity does not
   change the work of an exhaustive count.
10. (evaluated, not adopted) Inclusion-exclusion counting. The number of
   covered tuples of a t-set is the size of a union over rows; inclusion-
   exclusion over rows is exponential and sorting the N projections is
   O(N log N) per t-set, no better than marking. Exact but not competitive.
11. (evaluated, kept for simplicity) Cache blocking. Planes are stored
   chunk-major (all rows of one 256-column chunk contiguous, N * 32 bytes)
   so a pass over a class touches a compact block and row addresses are
   shifts. Measured equal to row-major on this machine: the kernel is bound
   by per-row instruction overhead and branch mispredictions of the class
   bit iteration, not by cache misses, at these sizes (planes of
   CA_216_4_1368_2 are 55 KB in either layout).
12. (evaluated, not adopted) Transposed per-d test: for each candidate d
   and class, test X_d AND class in {empty, class} with one `vptest`:
   3 instructions per (d, class), 24 per binary 4-set. Better than idea 1
   only when k-1-c < about 85; a hybrid would gain about 10 percent on
   k = 1368 (future work).
13. (not needed) Packing several binary columns per word is what the planes
   do (256 columns per operation); the one-hot lanes are the general-v
   version of packing.

## Idea 1 in detail (what ca_verify2 does)

Every t-set S of columns is written uniquely as S = P + {d} with P its
t-1 smallest columns and d its largest. For a fixed P, the rows are
partitioned into v^(t-1) classes by their value tuple on P (rows with a
don't-care on P belong to no class, matching the rule that such a row
exhibits nothing on S). Then

    S covers tuple (s, u)  iff  some row of class s has value u in column d.

For each row r and value u let plane_u[r] be the k-bit vector with bit d
set iff A[r][d] = u (a don't-care sets no bit). Then

    covered_s,u = OR over r in class s of plane_u[r]

has bit d set exactly when (s, u) is covered by P + {d}. The AND over u of
covered_s,u, complemented and masked to c < d < k, has bit d set exactly
when P + {d} misses some tuple; popcounts of the complemented covered_s,u
give the number of missing tuples per column set, and the smallest
(s, u) with a clear bit at d gives the lexicographically first missing
tuple of P + {d}, which is what `ca_verify` reports (its tuple index is
the base-v number with the smallest column most significant, i.e. s*v+u).
Restricting to d > c loses nothing: S with d < max(P) is handled by the
prefix made of its own t-1 smallest columns. The number of column sets
checked, summed over prefixes, is sum_P (k-1-max P) = C(k,t).

Classes: along the depth-first enumeration of prefixes, the class bitsets
at depth j are R_j[s'*v+u] = R_{j-1}[s'] AND X[c_j][u] where X[c][u] is the
set of rows with A[r][c] = u. Only the last level costs; its v^(t-1) ANDs
of W words are tiny next to the N row visits of the kernel. When
v^(t-1) * W > 8N the last level instead counting-sorts the rows of each
parent class by A[r][c] (one pass over N rows per prefix).

Binary kernel (v = 2, no don't-cares): one plane per row (value 1). For a
class, OR and AND accumulators over the class's rows: value 1 missing at
d iff OR bit clear, value 0 missing iff AND bit set (all rows have 1).
Candidate columns are processed in 256-column chunks, four, two or one
chunk per pass over the class, accumulators in registers; a pass is one
load and two logic operations per row per chunk.

General kernel: either v planes (one pass per value per chunk) or one-hot
lanes: entry (r, d) is 1 << A[r][d] in a lane of LB = 8, 16, 32 or 64 bits
(the smallest power of two >= v), 256/LB consecutive columns per 32-byte
unit, so one pass over the units from the one containing c+1 gives, per
column, the set of values seen in the class; covered iff equal to the full
mask of v bits. Chosen when (k/t) * LB/256 < v * max(1, (k/t)/256).

Don't-cares: X[c][u] excludes rows with a don't-care at c, so such rows
are in no class of a prefix containing c; a don't-care at d sets no plane
bit and a zero one-hot lane, so it covers nothing at d. Both match the
original's "a row with a don't-care in the projection contributes
nothing".

Examples and thread compatibility: `ca_verify` numbers column sets in
lexicographic order and gives set number r to thread r mod threads; each
thread keeps its first ten gaps and the main program prints thread 0's
list, then thread 1's, up to ten lines. ca_verify2 computes the rank of
each gap column set (rank = C(k,t) - 1 - sum_j C(k-1-c_j, t-j), closed
form from the combinatorial number system), keeps per residue class the
lexicographically first ten, and prints residue classes in order. Within
a prefix the gaps found are sorted by d before ranking; threads own
contiguous ranges of smallest columns in increasing order so their lists
are already in lexicographic order. If C(k,t) overflows 64 bits (far
beyond any feasible run) examples fall back to plain lexicographic order,
announced on stderr.

## Cost model and what limits the binary kernel

Per (t-1)-prefix the binary kernel visits every row once per chunk pass:
tzcnt, blsr, address, load, OR, AND and the loop branch, about 7
instructions, plus one loop-exit misprediction per (class, bitset word)
because class sizes vary (when classes are sparse the rows are first
listed with a nearly branch-free unpacking, see item 3 and "What
remains"). For N = 216, v^(t-1) = 8 classes and W = 4
words that is about 1500 instructions and 32 mispredictions per prefix,
measured at about 430 ns (k = 600) to 600 ns (k = 1368, more chunk passes)
on this 2.1 GHz Xeon, i.e. 1.6 to 1.8 ns per column set on the four large
arrays, 340 to 375 times below the original's 608 to 668 ns. The per-row overhead dominates the useful
256-bit operations, which is why making the planes more compact did not
help and why the alternatives in items 8 and 12 come out roughly even:
all of them spend about 3 to 4 cycles per 4-set at k around 1400.

Scaling: time is proportional to C(k,t-1) * N * (passes), so for the four
t = 4 arrays it grows like k^3 N (see BENCH.md). Threads scale linearly
(dynamic scheduling over smallest columns; the largest unit is
C(k-1,2) prefixes out of C(k,3), 0.2 percent of the work for k = 1368),
and shards partition the same units deterministically.

## What remains

- Class lanes (item 8) for N <= 200: no mispredictions, up to 3x at
  k ~ 300, same at k ~ 1400.
- Hybrid with the transposed test (item 12) for the tail of each
  prefix range: about 10 percent on the t = 4 arrays.
- AVX-512 clone (512 columns per operation) for runners that have it;
  the vector-extension source makes this a third instantiation.
- t = 2 is served but not special-cased (a direct pair pass would be
  cheaper); t = 2 runs are already fast.
- Loop-exit mispredictions of the class walk: for sparse classes (fewer
  than about 4 rows per bitset word, as at t = 5, 6 with N in the
  hundreds or thousands) the rows are now extracted to a list with eight
  unconditional steps per word, which gave 1.4x to 1.5x there; for dense
  classes (t = 4, N about 200) the direct ctz walk is as fast and a
  branch-free variant was estimated at no more than 10 to 20 percent.
