# Faster exact CPHF checking: research notes and prototype (mode fastprog)

Scope: CPHF(n; k, q, t) with t = 3..6, q <= 25 (prime powers), k <= 10000, n <= 30; many rows are
progressions u_c = A^c u_0 with A invertible. Everything below is exact: no sampling, no
probabilistic shortcut. Files in this folder:

- `cphfcheck2.c`: a copy of `tools/cphf/cphfcheck.c` with one new mode, `fastprog` (all old modes
  untouched). `gcc -O3 -march=native -fopenmp -o cphfcheck2 cphfcheck2.c`
  (clang on macOS: add libomp as for the other tools; without AVX2 the scalar key pass is used).
- `test_fastprog.py`: differential tests against mode full (imports the generators of the existing
  suite from `ct/tools/cphf/tests/test_progression.py`, read only). `mutate.py`: mutation tests.
- `gen.py`: writes a random family with the suite's generators (used for benchmarks).
- `BENCH.md`: measurements and extrapolation.

## 1. Where the time goes, and what can and cannot be changed

Notation: a representative is a t-set D with 0 in D (translation symmetry of the progression rows);
there are C(k-1, t-1) of them. Projection hashing (modes progression and fullfast) fixes a prefix
P of t-2 columns (0 in P), maps every later column c to a class in PG(1,q) or WILD per row, and
finds the pairs {x, y} whose classes agree in every row. Its work is one unit per (P, c > max P),
i.e. C(k-1, t-2) units (4.16e14 for t = 6, k = 10000; 1.67e11 for t = 5), at 63 ns per unit.

Counting what any method must look at:

| quantity, t = 6, k = 10000, q = 23 | count |
|---|---|
| representatives (sets containing column 0) | C(9999, 5) = 8.3e17 |
| ... failing in one given progression row (about 1/q of them) | 3.6e16 |
| ... failing in two rows | 1.6e15 |
| ... failing in three rows | 6.8e13 |
| ... failing in four rows | 3.0e12 |
| units of projection hashing, (prefix, column) pairs | C(9999, 4) = 4.2e14 |

Any method that enumerates the sets failing in one row, or in two rows, touches more objects than
projection hashing does. The sets failing in three or more rows are fewer, but no method found here
enumerates them without passing through a coarser level: finding the sets that fail in rows 1, 2
and 3 is a three-way "collinear in three planes at once" problem with no equality structure that a
hash can use (see 3.2 to 3.4). The unit count C(k-1, t-2) is therefore kept, and the gains come
from the cost per unit, which went from 63 ns to about 3 to 4 ns on the test machine (15 to 25x,
section 2), plus a clean split into independent parts for many machines (section 4).

Why the split (t-2) + 2 is the right one. For a fixed prefix P the condition "P + {x, y} is
dependent in row r" is an equality: class_r(x) = class_r(y) (or WILD). For a split (t-3) + 3 the
condition on the triple is "collinear in PG(2,q)", for (t-4) + 4 "coplanar in PG(3,q)": not an
equality of per-column keys, so the pairs/triples cannot be joined by hashing, only enumerated,
and the enumeration counts above are larger. A split t/2 + t/2 gives a bilinear condition (the
Laplace expansion of the determinant in the Pluecker coordinates of the two halves): an
"orthogonal vectors" problem, for which no truly subquadratic exact algorithm is known in general.

## 2. Ideas, ranked, with complexity and exactness

Units below: U = C(k-1, t-2), the number of (prefix, column) pairs; nP progression rows.

### 2.1 Reuse across prefixes through a prefix of t-3 columns (implemented, exact, large gain)

For a prefix P' of t-3 columns (0 in P') and a progression row r in which P' has rank t-3, the
quotient GF(q)^t / span(P') is 3-dimensional. Every column c maps to phi_r(u_c): zero or a point of
PG(2,q); this point index is computed once per (P', row, column), i.e. C(k-1, t-3) * k * nP times
(2 to 4 percent of the work at k = 10000), with three dot products. For every extension
P = P' + {p} and column c > p the class of c relative to P is the line of PG(2,q) through phi(u_p)
and phi(u_c), one of the q+1 lines through phi(u_p), read from a byte table LINE[point][point]
(306 KB for q = 23), and c is WILD iff phi(u_c) is zero or equal to the point phi(u_p). Exactness:
dim span(P + {x, y}) = (t-3) + dim span(phi(u_p), phi(u_x), phi(u_y)), so the set is dependent
iff the three images are dependent iff one is zero, two coincide, or the three are collinear;
with phi(u_p) nonzero this is exactly "x or y WILD, or same line through phi(u_p)", the rule of
mode progression. If phi(u_p) = 0 the prefix P is dependent in r and r is a wildcard row (skipped
for this p); if P' has rank < t-3 in r, r is skipped for the whole P'. Cost per unit: one byte
lookup per row used, instead of two dot products of length t and a division in GF(q).

### 2.2 Hash join over several rows at once (implemented, exact, large gain)

Mode progression refines the columns row by row (bucket by class, recurse); with q+1 classes
the subproblems become tiny after two rows and the fixed cost per subproblem dominates (14 million
subproblems for k = 1200). Instead, for one p all columns c > p get one key: the classes in the
first j live rows (j = 1, 2, 3 by the number of columns; radix q+1; WILD columns get no key and
are not inserted), and equal keys are found with a stamped hash table (one 32-bit word per key:
stamp and last index; chains through nxt[]). Two non-WILD columns fail the j rows iff their keys
are equal. A column that is WILD in a subset S of the j rows fails with a non-WILD column iff
their classes agree outside S: its partners are found by probing the (q+1)^|S| compatible keys
(24 probes for |S| = 1, typical). Pairs of two WILD columns go through the row-by-row rule. Every
pair is decided exactly once (non-WILD pairs by the chains, mixed pairs by the probes, WILD pairs
one by one); survivors continue row by row through the remaining live rows and finally reach the
rank recheck. Cost per unit: j table lookups, one hash insert, about 20 instructions in two tight
passes (key pass, insert pass), 3 to 4 ns measured. Survivors of j = 3 rows are 1/(q+1)^3 of the
pairs, WILD partners about 1/q of the columns times 1/(q+1)^2 of the columns; both are small.
The key pass is vectorized with AVX2 gathers where available (10 to 15 percent).

### 2.3 Splitting into independent parts (implemented)

`part=i/m` processes only the prefixes whose second column is congruent to i mod m (for t = 4 the
single extension p; t = 3 has one prefix and needs no split). Each part prints its own counts
and the expected totals of its part (sums of binomials), checks them, and prints the uncovered sets
of the part; the union over all parts is the full result. Parts are balanced by construction
(residues interleave the decreasing work per p1). This maps onto 20 free runners x 4 cores.

### 2.4 Bucketed first row (prototyped, exact, dropped)

With columns bucketed by their PG(2,q) point in the first row, the classes of p are unions of
buckets (the q points on each line through phi(u_p)), so the first row costs nothing per column.
Measured: slower (4x at k = 400) because of the O(q^2) scan per extension and the per-class fixed
costs; at k = 10000 it would save at most 15 percent of the lookups. Not worth the complexity.

### 2.5 Cyclic-code view (analysed, exact, no gain for the check)

In a progression row the failing t-sets are the supports of codewords of weight <= t of the code
with parity check matrix [u_0 ... u_(k-1)] (a shortened cyclic code when A has order >= k; the
minimal polynomial of u_0 under A has degree t when the row spans). Weight enumerators give exact
counts per row (MacWilliams), usable as a checksum of one row's failing sets, but the quantity
needed is the intersection over rows, and the polynomials realising the dependencies differ from
row to row, so there is no joint algebraic structure to exploit. Inclusion-exclusion over rows
needs the number of sets independent in every row of a subset R, as hard as the problem itself.
Dropped as a speedup; the per-row counts could serve as an extra consistency check (not done).

### 2.6 Most selective row first, hyperplane lists (analysed, exact, no gain)

Listing, per row, the columns on each hyperplane (q^t-1)/(q-1) * k/q entries: 5.8 GB per row at
t = 6) would give the classes of the first row as lists, but the sum of the list sizes is k per
prefix, the same as classifying every column; intersecting lists of two rows costs more than
bucketing. Choosing the row order by selectivity changes little: progression rows are all about
1/(q+1) selective. The join uses the first three live rows; the others only see survivors.

### 2.7 Meet in the middle over rows, pair-side keys (analysed, exact, worse)

Keying the pairs {x, y} (their line per row) and looking up the p compatible with them needs
(q+1)^j probes per pair for j rows, C(k,2) pairs per P': 3e10 operations per P' against 1.5e8 for
the prefix side. The asymmetry (one column p against k columns) is what makes the prefix side cheap.

### 2.8 Extra symmetry of fully cyclic families (not implemented, exact, factor <= t)

If all rows are cyclic with the same order and the family is invariant under the multiplier
c -> q c (Frobenius), representatives could be reduced by a further factor up to t. This needs
the invariance to be certified from the data (as the shift is) and holds for few families. A
candidate for later; not a general speedup.

### 2.9 Low-level items (implemented)

16-bit point indices, byte line table, stamped hash table with no clearing, implicit column ids
(index = c - p - 1), the two-pass loop to avoid register spills (this alone gave 1.6x), AVX2
gathers for the key pass, specialised code for j = 1, 2, 3. Field arithmetic is only used in the
setup (point indices), so prime powers cost the same as primes in the main loop.

### 2.10 Not exact, dropped

Sampling of any kind; probabilistic hashing without recheck (the rank recheck of every reported
representative is kept, so even a hash bug cannot produce a false uncovered set, only a missed one,
which the differential and mutation tests guard against); floating point determinants.

## 3. Exactness argument of mode fastprog (summary)

1. Row classification is unchanged (every progression row certified on every column, A invertible).
2. In a progression row, D fails iff D - min D fails; representatives contain 0 (unchanged).
3. For P' and a row of rank t-3 on P', the quotient map and the line table decide "P' + {p, x, y}
   dependent" exactly (section 2.1); rows of lower rank on P', and rows in which phi(u_p) = 0, are
   wildcard rows in which every completion fails, so skipping them is exact.
4. The join decides every pair {x < y} with p < x exactly once (section 2.2); a pair reaching the
   end of the live rows is a representative. The counts (prefixes, candidate columns, failing +
   ruled out pairs) must equal the binomials, otherwise exit 4.
5. Every representative is rechecked by rank in every progression row, and its shifts are tested
   by rank in the other rows, exactly as in mode progression.

## 4. What remains

- Per-unit cost is near the scalar instruction floor (about 20 instructions). A further 1.5 to 2x
  may be available from AVX-512 (16 lanes, scatter-free insert still scalar) and from tuning on
  the target machines; a GPU would change the picture but is excluded here.
- t = 6, k = 10000 stays a large computation: about 4.2e14 units, 15 to 20 CPU-days at 3 to 4 ns;
  feasible on 20 runners (4 cores, 6 h) as 20 to 40 parts, or in about a day on a 14-thread Mac.
  Resumable parts and a combining script are the practical next step.
- The shift tests of representatives in the other rows (test_rep) are unchanged; with few
  progression rows (nP <= 6) they dominate at t = 6 (1e13 rank tests for 6 P rows, see the README);
  a hashed version over the other rows would be the natural extension if such families appear.
- The fully cyclic multiplier symmetry (2.8) and per-row weight-enumerator checksums (2.5) are
  possible additions.

## 5. Usage

    cphfcheck2 FILE t q fastprog [threads] [P=r1,r2,...] [part=i/m]

Same output lines, exit codes, `P=` and `CPHFCHECK_LIST` behaviour as mode progression (row
classification, enumeration and completeness counts with their binomials, representatives, checked
and uncovered counts, first uncovered set, RESULT line). t = 2 falls back to the progression code;
t = 3 runs the single prefix with the shift tests in parallel; t = 4 is parallel over the extension
p; t >= 5 over the second prefix column. `part=i/m` (t >= 4) runs one of m balanced parts and prints
a `PART i/m` line with the part's counts, checked against the part's own binomial sums; combine the
part outputs with `combine_parts.py t k OUT...`. k must be at most 65535 (16-bit column indices).

## 6. Tests (all with the reference build of the original cphfcheck.c as mode full)

- Differential (`test_fastprog.py`): random families t = 3..6, q in {3,4,5,7,8,9,11,13}, k up to 70,
  0..6 progression rows of all the suite's kinds (generic, shared A, monomial and conjugated
  monomial A with many WILD columns, affine, -I, I, eigenvector and invariant-subspace starts) and
  0..3 other rows; all-progression families; near-CPHF families. Compared with full: exit code,
  count, first set, the complete sorted list of uncovered sets (up to 40000), the checked total,
  the completeness line, and the row classification against the suite's independent Python
  classifier; fastprog with 1 to 3 threads, and in 30 percent of the t >= 4 cases also as 2, 3 or 5
  parts whose union must equal the list. Runs during development: 580, 460, 350, 350, 290, 140 and
  a final 700 (600 random + 100 planted) tests, 0 failures after the two bugs found by the built-in
  rank recheck during development (a macro shadowing bug and a WILD-key bug, both caught by exit 4,
  never by a wrong verdict).
- Planted faults: a set failing in every progression row made dependent in every other row; must
  appear in the listing (100 in the final run).
- Prime powers: q = 16, 25, 27, 32 at t = 4 and 5 agree with full (table-based point computation).
- Existing suite (`tests/test_progression.py --quick`, 270 tests) run against cphfcheck2.c: the old
  modes are unchanged (legacy section byte-identical to the first published build).
- Mutations (`mutate.py`, 80 random + 10 planted tests per mutant, scalar build): 12 of 13 caught:
  WILD treated as a class, no probing of WILD partners, WILD-WILD pairs skipped, chain truncated to
  one partner, probe one class short, candidate range off by one, LINE[P][P] not WILD, survivors
  not checked in the remaining rows, non-projective point index, prefix rank < t-3 not a wildcard
  row, progression check stopping one column early, last shift skipped. The 13th (keeping a
  wildcard row with its all-WILD table row) is an equivalent mutant kept as a control; it changes
  nothing, as expected.
- Benchmarks (BENCH.md): identical results to mode progression on nine q = 23 families up to
  k = 4000 (t = 5) and k = 1000 (t = 6), including 3.6 million uncovered sets on one of them.
