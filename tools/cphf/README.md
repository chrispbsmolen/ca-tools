# Cyclic covering perfect hash families (source S8, since 2026-10-28)

Eight arrays of the table come from covering perfect hash families (CPHFs)
found here by a search over families with a cyclic symmetry, and checked
here by two separate programs. Credit: Christopher Smolen (search and checks,
2026-10-26 to 2026-10-29). Report: doi:10.5281/zenodo.23751688.

| array | family | certificate | checked by |
|---|---|---|---|
| CA(2663; 5, 121, 3) | CPHF(11; 121, 3, 5) | `../../table/certificates/CPHF_11_121_3_5.txt` | `ca_verify.c` on the array (stored), `repcheck.c` and `gpu/cphfcheck_metal.m` on the family |
| CA(40613; 5, 781, 5) | CPHF(13; 781, 5, 5) | `../../table/certificates/CPHF_13_781_5_5.txt` | `repcheck.c`, `gpu/cphfcheck_metal.m` |
| CA(218479; 5, 2801, 7) | CPHF(13; 2801, 7, 5) | `../../table/certificates/CPHF_13_2801_7_5.txt` | `repcheck.c`, `gpu/cphfcheck_metal.m` |
| CA(10921; 6, 121, 3) | CPHF(15; 121, 3, 6) | `../../table/certificates/CPHF_15_121_3_6.txt` | `repcheck_pp.c`, `gpu/cphfcheck_metal.m` |
| CA(249985; 6, 781, 5) | CPHF(16; 781, 5, 6) | `../../table/certificates/CPHF_16_781_5_6.txt` | `repcheck_pp.c`, `gpu/cphfcheck_metal.m` |
| CA(49985; 5, 1562, 5) | CPHF(16; 1562, 5, 5), two orbits | `../../table/certificates/CPHF_16_1562_5_5.txt` | `repcheck_pp.c`, `gpu/cphfcheck_metal.m` |
| CA(767625; 5, 1210, 9) | CPHF(13; 1210, 9, 5), ten orbits | `../../table/certificates/CPHF_13_1210_9_5.txt` | `repcheck_pp.c`, `gpu/cphfcheck_metal.m` |
| CA(268897; 5, 5602, 7) | CPHF(16; 5602, 7, 5), two orbits | `../../table/certificates/CPHF_16_5602_7_5.txt` | `repcheck_pp.c`, `gpu/cphfcheck_metal.m` |

## What a CPHF is, and how it gives the array

A CPHF(n; k, q, t), q a prime, is an n x k array whose entries are vectors
of GF(q)^t, such that for every set of t columns some row has t linearly
independent vectors in those columns. Sherwood, Martirosyan and Colbourn
(J. Combin. Des. 14 (2006) 202-213, doi:10.1002/jcd.20067) showed that it
gives a covering array CA(n(q^t - 1) + 1; t, k, q): the all-zero run, and for
every row r and every nonzero beta in GF(q)^t the run whose entry in column
c is the inner product of beta with the row's vector in column c.
`cphf_tools.c expand` writes that array in the table's canonical form, and
its SHA-256 is the `array_sha256` of the table row. The CA(40613; 5, 781, 5)
is 63 MB as text and the CA(218479; 5, 2801, 7) about 1.2 GB, so only their
families are stored (49 KB and 196 KB); anyone can rebuild the arrays and
compare the hash (on macOS build with clang and libomp, as for `repcheck`
below; the second form hashes the 1.2 GB array without writing it to disk):

    gcc -O2 -fopenmp -o cphf_tools cphf_tools.c
    ./cphf_tools expand ../../table/certificates/CPHF_13_2801_7_5.txt 5 7 CA_218479_5_2801_7.txt
    sha256sum CA_218479_5_2801_7.txt      # or: shasum -a 256 CA_218479_5_2801_7.txt
    # 432d81f32d1f3ba0637748e35c1c65848abdc0e021052a95d0695f9b48f7e982

    mkfifo ca.fifo; sha256sum < ca.fifo &     # or: shasum -a 256 < ca.fifo &
    ./cphf_tools expand ../../table/certificates/CPHF_13_2801_7_5.txt 5 7 ca.fifo; wait; rm ca.fifo

## The search (symcphf.c)

The columns are indexed by the cyclic group Z_m, here m = k. Row r is given
by a matrix M_r of GL(t, q) whose m-th power is a scalar, and a seed vector
x_r; its entry in column c is M_r^c x_r. Shifting every column by one then
multiplies every vector of the row by M_r (and the vector of the last column
by a nonzero scalar as well), which does not change linear independence. So
a t-set of columns is covered in a row exactly when its shift is, and it is
enough to check the t-sets that contain column 0: C(k - 1, t - 1) of them
instead of C(k, t), 2.56 x 10^12 instead of 1.43 x 10^15 at k = 2801. In all
three families here k = (q^t - 1)/(q - 1) (121, 781 and 2801 for q = 3, 5
and 7, t = 5), and every row's matrix has projective order k (a Singer
cycle of PGL(5, q)); each family's header lists them. The search picks the
first rows by sampling, makes one exact pass over all representatives to
list the uncovered ones, and completes the family greedily on that list.
The commands, seeds and logs are in `RUNS.txt`. Running a command again
gives the same family; the file differs only in its first comment line,
which records the run's wall-clock time, so compare the lines after the
comments rather than the file's hash.

## The check (repcheck.c)

`repcheck.c` was written separately from the search and shares no code with
it. For a stored family it

1. finds, for every row, the matrix A_r with A_r v[c] = v[c + 1] from t
   consecutive independent columns, and checks that relation at every
   column, the wrap A_r v[k - 1] = mu_r v[0] with mu_r nonzero, and that
   A_r is invertible (the symmetry certificate, checked, not assumed);
2. checks every set {0, a, b, c, d} against the rows, exactly: with the
   first four vectors fixed, their 4 x 4 minors give a normal vector n_r,
   and the set is covered in row r exactly when n_r . v_r[d] is nonzero.

It prints the number of uncovered representatives (0 for a CPHF) and the
first ones found. It was tested against `cphf_tools.c check` (a brute force
over all t-sets by determinant): on a 9-row family with k = 121 that is not
a CPHF both report the same failures (875 representatives, 21,175 sets =
875 x 121 / 5), and a family with one changed entry fails the symmetry
certificate.

    gcc -O3 -fopenmp -o repcheck repcheck.c            # macOS: clang with libomp
    ./repcheck ../../table/certificates/CPHF_13_2801_7_5.txt 5 7 14

`repcheck.c` handles t = 5, q prime below 64 and at most 64 rows, and
`cphf_tools.c` rows of at most 70,000 entries; both are used here well
inside those limits, unchanged from the runs recorded (the stamps name
`repcheck.c` by its SHA-256, 1aaaf64c0e47...).

## The general versions (since 2026-10-28)

`symcphf_pp.c`, `repcheck_pp.c` and `cphf_tools_pp.c` extend the three
programs to q a prime power up to 16 (GF(q) by tables from the Conway
polynomial), to t up to 8, and to several column orbits (k = m s, the
shift col -> col + s). For prime q, `symcphf_pp.c` behaves exactly as
`symcphf.c` (it is built from it by
`python3 mk_symcphf_pp.py symcphf.c symcphf_pp.c`, and it reproduces the
rows of the stored CPHF(13; 781, 5, 5), all but the first comment line,
which records the run's time); its exact pass
is incremental and about fifteen times faster. `repcheck_pp.c` is
written separately from the search, like `repcheck.c`, and checks the
symmetry and every representative t-set with exterior products. It was
tested against brute force on families with q = 4, 8, 9 and 16, t = 3
to 6 and s = 1 to 4, with rows dropped and entries changed.

The strength 6 family has rows of type 5 + 1: multiplication by an
element of GF(3^5) of projective order 121 on five coordinates, and by 1
or 2 on the sixth. It was found by

    ./symcphf_pp 6 3 121 1 -light -n0 10 -seed 2 -cand 200 -optmoves 1500 -psample 400000 -threads 1

in 21 s; 116 runs with other seeds and prefixes never gave fewer than 15 rows.

One limit found on the way, for one shape of family only: at t = 5 with
one column orbit (s = 1, k = (q^5 - 1)/(q - 1)), rows that are Singer
cycles leave some sets of columns uncovered for q = 2, 4 and 8,
whatever rows are chosen. Those sets sit inside a subfield (they lift
from the 225 uncovered representatives at q = 2, k = 31) and are
dependent in every such row. The t = 6 searches of the same kind (rows
of type 5 + 1) found similar uncovered sets for q = 2 and q = 9. This
is a limit of that shape, not of covering arrays at those sizes, and it
does not rule out other layouts: several column orbits with different
rows, or a family that adds a few rows of another kind to cover those
sets, are the next things to try.

## The second check (gpu/cphfcheck_metal.m, since 2026-10-29)

`gpu/cphfcheck_metal.m` checks a family on an Apple GPU and shares no code with `repcheck.c`,
`repcheck_pp.c` or the search. It builds GF(q) by polynomial multiplication (`gpu/gfield.h`, checked
against the field axioms), certifies the shift symmetry of every row by solving for A from t
independent columns and testing it at every column and the wrap (`gpu/common.h`), and then checks
every representative t-set (smallest column < s): each GPU thread fixes all but the last column,
computes for every row a normal vector of the first t - 1 vectors by Gaussian elimination, and tests
the last column by one dot product per row. `gpu/gcheck_ref.c` and `gpu/emu_kernel.c` are plain-C
versions of the same method. On nine incomplete test families (t = 4, 5, 6; q = 3, 4, 5, 9; one, two
and three column orbits; `gpu/t/`, made by `gpu/gen.py` and `gpu/genpp.py`) all three give exactly the
counts of uncovered representatives that `repcheck_pp.c` gives (`gpu/expected.txt`), and a family with
one changed entry fails the certificate. `gpu/gpu_cphf_test.sh` repeats these tests on a Mac. Every
stored family passed it; the results are at the end of RUNS.txt.

    clang -O2 -fobjc-arc -framework Metal -framework Foundation -o cphfcheck_metal cphfcheck_metal.m
    ./cphfcheck_metal ../../../table/certificates/CPHF_13_2801_7_5.txt 5 7 1     # FILE t q s

## The general certificate checker (cphfcheck.c, since 2026-11-01)

`cphfcheck.c` checks any CPHF(n; k, q, t) with q a prime or a prime power
up to 32 (4, 8, 9, 16, 25, 27, 32 by Conway polynomials) and t up to 8,
for submitted certificates (`../check_certificates.py`). It was written
independently of `repcheck_pp.c` and decides coverage another way: for a
prefix of t - 1 columns it reduces their vectors by Gaussian elimination
and solves for the normal w of their span; the t-set with last column c
is covered in a row iff w . v[c] != 0. Modes: `full` (every t-set),
`cyclic s` (the symmetry col -> col + s solved for and checked in every
row, then the t-sets with smallest column < s), `sample S seed` (a
screen, never used to enter a row), and `expand OUT [affine]`, which
writes the covering array in the order of `cphf_tools_pp.c expand` (the
same hashes) or, for affine families, the n(q^t - q) + q array of
Sherwood, Martirosyan and Colbourn.

Tests (2026-11-01): on seven cyclic families (q = 4, 5, 7, 8, 9, 16 at
t = 3) it agrees with `repcheck_pp.c` in full and cyclic mode, and its
expansion has the same SHA-256 as `cphf_tools_pp.c expand`; on random
families for q = 2, 3, 4, 5, 7, 8, 9, 16, 17, 19, 23, 25, 27, 32 its
uncovered counts equal those of an independent Python brute force with
its own field arithmetic (`tests/cphfcheck_brute_test.py`); a family
with one entry changed fails the cyclic certificate; an affine expansion
is verified by `ca_verify` and has no repeated run.

    gcc -O3 -fopenmp -o cphfcheck cphfcheck.c
    ./cphfcheck FAMILY t q full 14
    ./cphfcheck FAMILY t q cyclic s 14
    ./cphfcheck FAMILY t q expand CA.txt [affine]

## Progression and fullfast modes (cphfcheck.c, since 2026-11-01)

Two more exact modes, added for families too large for `full` (issue #18):

    cphfcheck FILE t q progression [threads] [P=r1,r2,...]
    cphfcheck FILE t q fullfast [threads]

Exit codes as before (0 none uncovered, 1 some, 2 usage, 3 a row named in `P=` is not a
progression row), plus 4 when an internal completeness count does not match its binomial (a
bug, never a verdict; never seen in testing). With the environment variable `CPHFCHECK_LIST`
set, full, progression and fullfast print every uncovered t-set as `U c1 ... ct` (for testing).
`tests/test_progression.py` builds the checker and the version first published
(`tests/cphfcheck_a5ad0b7.c.ref`) and runs the whole suite below; the old modes give
byte-identical output to that version. The method was reviewed by two independent design
studies before it was written; the one point the submitter's description left out, columns in
the span of the prefix ("WILD"), is handled and tested by mutation.

### Mode progression

1. Row classification, from the data only. A row is dead if its k vectors do not span GF(q)^t
   (it covers nothing, so it is dropped). Otherwise t independent vectors are taken among
   columns 0..k-2, A is solved from A u_sel = u_(sel+1), A must be invertible (rank t), and
   u_c == A u_(c-1) is then checked exactly for every c = 1..k-1. A row passing all of this is a
   progression (P) row and its A is printed; every other row is an other (O) row, with the
   reason printed. `P=...` names rows that must certify.
2. Translation: in a P row u_c = A^c u_0, so a t-set S fails (is dependent) iff S - min(S)
   fails (factor det(A)^min(S), nonzero). Only representatives D with 0 in D are enumerated.
3. Projection hashing. For t >= 3 the representatives are prefix + {x < y}, prefix = {0} plus
   t-3 further columns, x, y after the prefix. Per prefix and P row: if the prefix vectors have
   rank < t-2 the row is a wildcard row (every completion fails) and is skipped. Otherwise h1, h2
   span the annihilator of the prefix span and column c gets the class [h1.u_c : h2.u_c] in
   PG(1,q), or WILD when both are 0. {x, y} fails in the row iff x or y is WILD or the classes
   are equal. The pairs failing in every non-wildcard P row are found by refining row by row: a
   subproblem (A, B) means the pairs inside A plus the pairs between A and B. Classifying by one
   row into A_z, B_z (classes) and A_w, B_w (WILD), the failing pairs split exactly into the
   subproblems (A_z, A_w + B_z + B_w) for each class z and (A_w, B), with no pair twice; the pairs
   with two different non-WILD classes are counted as ruled out. Subproblems with at most 12
   pairs are finished pair by pair with the same rule. t = 2 is handled directly ({0, y}).
4. Every representative is rechecked by rank in every P row, then every shift D + a,
   a = 0..k-1-max(D), is tested by rank in the O rows (stop at the first covering row). A shift
   failing in every O row is an uncovered t-set. With no O rows every shift is uncovered; with no
   P rows every t-set containing 0 is a representative (correct, but slower than full).
5. Output: the classification, then
   `enumeration: prefixes X (expected C(k-1,t-3)), candidate columns Y (expected C(k-1,t-2)), wildcard (prefix,row) ..., WILD classifications ...`,
   `completeness: pairs failing every progression row F + pairs ruled out R = F+R (expected C(k-1,t-1))`,
   `representatives ..., shifts tested in other rows ...`, then the usual lines.
   If any of the three totals differs from its binomial, or a reported set fails the rank
   recheck, the run prints `INTERNAL CHECK FAILED` and exits 4.

Parallelism: OpenMP over the second prefix column (t >= 4); for t = 3 (a single prefix) the
shift tests run in parallel. Thread count is the optional numeric argument.

### Mode fullfast

The same projection hashing over all non-dead rows, with prefixes of any t-2 columns and
completions after the last prefix column. Every reported t-set is rechecked by rank in every row.
Expected totals: prefixes C(k,t-2), candidate columns C(k,t-1), pairs C(k,t). Parallel over the
first prefix column. Output as in full, plus the two count lines.

### Test results (`tests/test_progression.py`, 1056 tests, 0 failed, 421 s on 2 cores, 2026-11-01)

| section | tests | what |
|---|---|---|
| legacy | 63 (53 without the optional inputs in `tests/legacy/`, which are not in the repository) | full, cyclic, sample, expand (also affine), usage errors: stdout, stderr, exit code and expanded file identical to the original build; header and `checked` line of the new modes match what check_certificates.py parses |
| diff | 700 | random families, t = 2..6 (mostly 3..6), q in {3,4,5,7,8,9}, k up to 90 (t=3), 60 (t=4), 55 (t=5), 26 (t=6); 0..4 progression-built rows (generic A, shared A, monomial and conjugated monomial A, affine x -> Mx+b, -I, I, eigenvector start, translations, invariant subspace starts) and 0..3 other rows (random, affine, few repeated vectors, corrupted progression, singular A). 127 cases have k > q^(t-1). Row classes over all cases: 1021 P, 1290 O, 707 dead. Compared with full (1 thread): exit code, uncovered count, first uncovered set, the complete sorted list whenever there are at most 20000, and the row classification against an independent Python classifier (solves all k-1 equations for A). 15% of runs use the build without OpenMP; thread counts 1 to 3. |
| planted | 120 | a set failing in every P row (from the full listing of the P rows) is made dependent in every O row; 20 each of shift a = 0, middle, a = k-1-max(D), each with and without WILD columns or wildcard rows; the set must be in all three lists and the lists identical |
| negative | 146 | corrupted P row at the first, middle and last column, singular A with spanning row, non-spanning row, constant row: `P=` exits 3 naming the row, the class is right ("singular" reported), the good row alone certifies, and results still equal full; bad `P=` exits 2 |
| real | 4 | four families from the canli submission (t=3,4; q=8,9,13): 0 uncovered in all three modes (none of their rows is a progression in the given column order) |
| medium | 1 | t=4, q=7, k=300, n=9: 476 uncovered, identical lists and first set in full, progression, fullfast; full 2.4 s, fullfast 0.28 s, progression 0.02 s |
| mutation | 7 | each mutant built from a patched copy and run on 236 tests; all caught |

Mutations (tests failing out of 236):

- WILD disabled (zero image treated as an ordinary class): 182, in both new modes
- invertibility check of A removed: 34
- shift range off by one (last shift skipped): 184
- shift a = 0 skipped: 183
- extra, WILD-with-WILD subproblem dropped: 180
- extra, B_w left out of the class subproblems: 105
- extra, progression check stops before the last column: 12

### Timing (one thread, q = 23, 6 progression rows + 2 random rows)

Unit cost = time / (number of units): full per t-set, fullfast per C(k,t-1), progression per
C(k-1,t-2).

| mode | t | k | time | ns per unit |
|---|---|---|---|---|
| full | 4 | 240 | 2.16 s | 16 |
| full | 5 | 100 | 3.89 s | 52 |
| fullfast | 4 | 240 | 0.21 s | 92 |
| fullfast | 5 | 200 | 4.83 s | 75 |
| progression | 5 | 1200 | 18.2 s | 64 (includes 1.25 M shift tests) |
| progression | 6 | 240 | 8.4 s | 63 |

Extrapolation to q = 23, k = 10000 (one thread; divide by the thread count):

- progression t = 5: C(9999,3) x 64 ns, about 1.1e4 s (3 hours) for the hashing; the shift
  tests scale like C(k,t) f^nP (f about 1/21 per P row here): about 5e10 tests, 1 to 3 hours with
  6 P rows. Total roughly half a day on one core.
- progression t = 6: C(9999,4) x 63 ns, about 2.6e7 s (300 days), plus about 1.5e13 shift tests
  (about 25 days) with 6 P rows; fewer with more P rows.
- fullfast t = 5: C(10000,4) x 75 ns, about 3e7 s (360 days); t = 6: about 6e10 s (2000 years).
- full t = 5: C(10000,5) x 5 to 50 ns, 4e9 to 4e10 s (over a century); t = 6 is 1660 times more.

The unit costs fall slightly as k grows (fixed per-prefix cost spread over more columns), so
these are upper-side estimates for the hashing; the shift-test term depends on the number of P
rows and how often they fail together.

### Unit costs (the estimate, since 2026-11-02)

`cphfcheck FILE t q estimate` and `../cphf_cert.py` (its function `unit_ns`, which must equal the
function `unit_ns` of `cphfcheck.c`, as `tests/test_certificates.py` checks) price the methods
in nanoseconds on one core per unit, with n the number of rows of the family:

| method | unit | ns per unit |
|---|---|---|
| full, cyclic | t-set (representative t-set for cyclic) | 0.15 n t^2 |
| fullfast | C(k, t-1) | n (11 + 28/q) |
| progression | C(k-1, t-2) | 10.5 (t-3)^2 + 4.6 k/q^2 |
| fastprog | C(k-1, t-2) | 0.8 (t-3)^2 + 1.1 k/q^2 |
| shift test (progression, fastprog) | one shift tested in the other rows | 140 |

The term in k/q^2 is the work on columns that fall on the same line of PG(2, q), which grows with
k and falls fast with q. The plans of `../cphf_cert.py` multiply the estimate by SAFETY = 2.

Measured on the test VM (2 vCPUs of an Intel Xeon at 2.1 GHz, gcc 13.3, `cc -O3
-march=native -fopenmp`), one thread per run with two runs at a time (one per core), wall-clock
time of the whole process, 2026-11-02. The real families are the 52 families of
`submissions/canli-2026-11-cphf-full/families/` and those of `table/certificates/`, every method
whose old estimate was between 0.02 s and 25 s (runs under 0.1 s were left out of the fit).
The synthetic families have generic progression rows and random other rows from the generators of
`tests/test_progression.py`, t = 3 to 6, q = 5 to 23, k = 200 to 4000, 3 to 8 progression rows
and 0 to 4 other rows. The formulas were fitted by non-negative least squares on relative
error. Model time over measured time (shift tests counted with the estimate's own count):

| method | runs | t | q | n | k | model / measured |
|---|---|---|---|---|---|---|
| full | 18 (17 real) | 3 to 5 | 3 to 23 | 4 to 11 | 121 to 1247 | 0.62 to 1.23 |
| fullfast | 37 (33 real) | 3 to 5 | 3 to 25 | 4 to 11 | 121 to 4750 | 0.60 to 1.48 real, 0.39 to 1.02 synthetic |
| progression | 12 (2 real) | 3 to 6 | 3 to 23 | 6 to 15 | 121 to 4000 | 0.58 to 1.52, and 0.06 (see below) |
| fastprog | 15 (3 real) | 3 to 6 | 3 to 23 | 6 to 15 | 121 to 4000 | 0.35 to 1.60, and 0.06 (see below) |

The largest real run was fastprog on CPHF_13_2801_7_5 (t = 5, q = 7, k = 2801): 218 s, model
270 s. The provisional constants used before (52, 92, 64 and 4.4 ns per unit, 200 ns per shift
test) were up to 16 times too low for fastprog at small q (CPHF_13_781_5_5, t = 5, q = 5: 71 ns
per unit) and up to 3.3 times too low for fullfast at small q (q = 4, n = 10: 300 ns per unit),
and too high for full (5 to 21 ns per t-set at t = 3 and 4 against 52). The two cases far below 1
are one synthetic family at t = 3, q = 23 with 4 progression rows, where the estimate's count of
shift tests (the product of the rows' sampled failure rates) is far below the number of shift
tests actually made. That is an error of the count, not of the unit cost, and it is not covered
by the safety factor. Such a family should be planned with fullfast, which the estimate prices
correctly. Families of progression rows also run fullfast up to 2.6 times slower than the
formula (the synthetic rows), which the safety factor covers.

### Limits and doubts

- Sets proven covered by a P row are never rechecked one by one (that is the whole saving); the
  guarantees are the exact certification of every P row, the binomial totals, the rank recheck
  of everything reported, and the tests above.
- With no P rows, progression costs about C(k,t) rank tests, more than full; use full or
  fullfast then. The four real families tried have no progression rows in their column order.
- In mode full with more than one thread, "first uncovered" depends on scheduling (unchanged
  behaviour); the new modes always report the lexicographic minimum.
- The `checked` count is printed exactly (128-bit), also past 2^63.

## Mode fastprog (cphfcheck.c, since 2026-11-02)

The research behind this mode (the ideas tried, their complexity, why each kept step is exact, and
the ones dropped) is in `RESEARCH_fastprog.md` in this folder.

    cphfcheck FILE t q fastprog [threads] [P=r1,r2,...] [shard i m]

The result of `progression` (the same row classification, the same representatives D with
0 in D failing in every progression row, the same counts and binomials, the same rank recheck of
every representative and the same shift tests in the other rows, so the same output lines) by a
faster exact method, 11 to 21 times faster per unit on the benchmark families below. `progression`
stays available as the simpler reference; `auto` uses fastprog whenever there are progression
rows (it is then always cheaper than `progression`). k is at most 65535 (16-bit column indices);
at t = 2 fastprog runs the code of `progression`.

1. Prefixes of t-3 columns. For a prefix P' (0 in P') and a progression row in which P' has rank
   t-3, the quotient of GF(q)^t by span(P') is 3-dimensional; every column maps to zero or a point
   of PG(2,q), computed once per (P', row) (three dot products per column, vectorised). For
   P = P' + {p} and D = P + {x, y}, dim span(D) = (t-3) + dim span(phi(p), phi(x), phi(y)), so
   D fails in the row iff the three images are dependent: x or y is WILD (zero, or the point of
   p), or x and y lie on the same line through phi(p). The class of a column is that line, read
   from a byte table of PG(2,q) (built and verified at start: q+1 lines through every point, q
   further points on each). These are exactly the classes and the rule of `progression`. A row
   in which P' has rank below t-3, or in which phi(p) = 0, is a wildcard row (every completion
   fails) and is skipped, as in `progression`.
2. Hash join. For one p, the columns c > p get a key: their classes in the first one, two or
   three live rows (by the number of columns), radix q+1. Two non-WILD columns fail those rows
   iff their keys are equal (a stamped hash table with chains); a column WILD in some of the rows
   probes the (q+1)^|S| compatible keys; two WILD columns go through the row-by-row rule. Every
   pair is decided exactly once; pairs passing the joined rows continue row by row through the
   other live rows, and a pair passing all of them is a representative. The key pass uses AVX2
   gathers when the build has them (`-march=native`; `-DNO_AVX2` forces the scalar pass, which
   gives the same results).
3. Completeness: prefixes, candidate columns and pairs failing + pairs ruled out must equal the
   binomials of `progression`, and every representative is rechecked by rank in every
   progression row before its shifts are tested; a mismatch exits 4 (a bug, never a verdict).
   During development the recheck caught both bugs found, never a wrong verdict.

Shards: `shard i m` splits the same outer loop as `progression` (the second column of the
representative, t >= 4; one index at t = 2 and 3), deals it the same way, prints the same
`SHARD` lines with `mode=fastprog`, and `../cphf_cert.py` combines the shards with the same
checks (every index in exactly one shard, each shard's counts recomputed from its indices, totals
equal to an unsharded run). The prototype's own `part=i/m` splitting is not part of this build.

Unit cost: measured at 3.8 to 4.4 ns per C(k-1, t-2) unit on the benchmark families below. The
cost that `estimate` uses depends on t, q and k, see "Unit costs" above.

| family (q = 23) | t | k | rows (P + O) | progression | fastprog, 1 thread | ns per unit |
|---|---|---|---|---|---|---|
| b5_1200 | 5 | 1200 | 6 + 2 | 16.9 s | 1.11 s | 3.9 |
| b5_2000 | 5 | 2000 | 6 + 2 | 125 s | 5.85 s | 4.4 |
| p5_4000 | 5 | 4000 | 8 + 0 | 769 s | 47.3 s | 4.4 |
| b6_240 | 6 | 240 | 6 + 2 | 8.90 s | 0.51 s | 3.8 |
| p6_700 | 6 | 700 | 8 + 0 | 624 s | 43.6 s | 4.4 |
| p6_1000 | 6 | 1000 | 10 + 0 | (about 1.3 h) | 200 s | 4.9 |

(Measured 2026-11-01 on the prototype, whose fastprog code is the code of this build; results
identical to `progression` in every run. With few progression rows and other rows, the shift
tests can dominate both modes: b6_700, 4 + 2 rows, 1060 s against 459 s.) Extrapolation at
q = 23, k = 10000: t = 5, C(9999, 3) units, about 12 minutes on one core; t = 6, C(9999, 4) =
4.2e14 units, about 21 core-days, which is more than 20 shards of 5 hours on 4 threads (the
budget of `../cphf_cert.py`), so such a family enters as SCREENED unless the budget or the
runners change.

Tests: `tests/test_fastprog.py` (below, "Tests").

## One command, estimates and shards (cphfcheck.c, since 2026-11-02)

    cphfcheck FILE t q estimate [threads]
    cphfcheck FILE t q auto [threads] [shard i m]
    cphfcheck FILE t q full|fullfast|progression|fastprog [threads] shard i m
    cphfcheck FILE t q cyclic s [threads] shard i m
    cphfcheck FILE t q canon OUT

### Mode estimate and mode auto

`estimate` runs nothing exact. It classifies the rows as `progression` does, looks for a cyclic
shift symmetry (the smallest s, 1 <= s < k, s dividing k, for which `cyclic s` certifies every
row; rows whose columns 0..k-s-1 do not span GF(q)^t are never certified, as before), and prints
for every method that applies its work units and an estimated time on one core:

| method | units | ns per unit (n rows) |
|---|---|---|
| cyclic s | t-sets with smallest column < s | 0.15 n t^2 (the engine of `full`) |
| fastprog (t >= 3, k <= 65535) | C(k-1, t-2), plus 140 ns per shift test | 0.8 (t-3)^2 + 1.1 k/q^2 |
| progression | C(k-1, t-2), plus 140 ns per shift test | 10.5 (t-3)^2 + 4.6 k/q^2 |
| fullfast | C(k, t-1) | n (11 + 28/q) |
| full | C(k, t) | 0.15 n t^2 |

The costs are those of "Unit costs" above. The number of shift tests is C(k, t) times
the product of the failure rates of the progression rows, each measured on 20,000 random t-sets
with a fixed seed (rows are assumed to fail independently; a row with no failure in the sample
counts as 0.5 / 20,000). The costs are the function `unit_ns` in `cphfcheck.c`. They are a
planning aid only, good to within about 1.6 times on the families measured (apart from a poor
count of shift tests, see "Unit costs"). The method changes how long an exact check takes, never
its answer, and every method below is exact. Then `cheapest:`
names the method of smallest estimate (ties go to cyclic, fastprog, progression, fullfast, full,
in that order; fastprog has the units and shift tests of progression at a lower unit cost, so
progression is never chosen when fastprog applies). `auto` prints the estimate, then `auto: method ...`, then runs that method exactly; the
choice depends only on the data, so every shard of an `auto` run makes the same choice.

### Shards

`shard i m` (the last three arguments) runs shard i of m of the outer loop of an exact mode:

| mode | outer index j | weight of j |
|---|---|---|
| full | smallest column of the t-set, 0..k-t | C(k-1-j, t-1) |
| cyclic s | smallest column, 0..s-1 | C(k-1-j, t-1) |
| fullfast (t >= 3) | first prefix column, 0..k-1 | C(k-1-j, t-2) |
| progression, fastprog (t >= 4) | second column of the representative, 1..k-1 | C(k-1-j, t-3) |

fullfast at t = 2 and progression and fastprog at t = 2 and 3 have one outer index, which goes to shard 0. The
indices are sorted by weight, largest first (ties: smaller index first), and each goes to the
shard with the least weight so far (ties: the lower shard): deterministic, and every index is in
exactly one shard whatever m is. A shard prints its indices (`SHARD indices: ...` as ranges), the
counts of its share in a line `SHARD i=.. m=.. mode=.. units=.. ...` (units: t-sets for full and
cyclic, pairs for fullfast, progression and fastprog; also prefixes and candidate columns for the hashing
modes), every uncovered t-set it finds as `U c1 ... ct` (at most `CPHFCHECK_LISTCAP`, default
10,000) and its lexicographically smallest one. The shard checks its own counts against the
binomial sums of its indices (exit 4 if they differ) and never prints `RESULT`.

`../cphf_cert.py` (`combine()`) puts the shards together. It accepts them only if shards
0..m-1 are each there exactly once, ran the same method on the same family (family_sha256, tool
hash, header and row classification), exited 0 or 1, list disjoint sets of indices that together
are the whole outer loop, have the counts their indices stand for (recomputed in Python from the
binomials), and add up exactly to the totals an unsharded run checks: C(k, t) t-sets for full,
the representatives for cyclic s, C(k, t) pairs, C(k, t-2) prefixes and C(k, t-1) candidate
columns for fullfast, C(k-1, t-1) pairs, C(k-1, t-3) prefixes and C(k-1, t-2) candidate columns
for progression and fastprog. Sharding splits the same loop the unsharded run does, so it never changes the
answer; a missing, repeated or relabelled shard, or one from another run, is refused.

### Tests (`tests/test_shards.py`, `tests/test_certificates.py`, `tests/test_fastprog.py`, 2026-11-02)

`tests/test_progression.py --no-timing` on this source: 1031 tests, 0 failed, 359 s on 2 cores
(legacy 53, all seven mutations caught; mode fastprog does not change the old modes, whose output
is also byte-identical to the build published before 2026-11-02 on 2,400 further runs).

`tests/test_shards.py`: 13,162 tests, 0 failed, 70 s on 2 cores: 160 random families (the generators of
`tests/test_progression.py`, t = 2 to 6, q = 3 to 9; a quarter of them with a cyclic symmetry of
one or two column orbits), each in full, fullfast, progression, fastprog and (when certified) cyclic s, with
m = 1, 2, a random m up to 6, and more shards than the outer loop has indices, 1 or 2 threads,
OpenMP and plain builds. The combined count, smallest uncovered t-set and complete list equal those
of the unsharded `full` listing (2,448 tests); a missing, repeated, relabelled, other-m and truncated
shard is refused every time (8,905); the planner's replica of the deal (`cphf_cert.deal()`) gives the
weights cphfcheck prints (1,450); `auto` reaches the verdict of `full` with the cheapest method and
finds the planted symmetry (187); `canon` equals the Python serialization (160); the buffered
`expand` writes the same bytes as the first published version (12, plain and affine).

`tests/test_certificates.py` (45 tests, 0 failed, 15 s) runs `../check_certificates.py` end to end
on a temporary copy of the table: the family_sha256 of every stored family (Python and
`cphfcheck canon`), the local exact check and its entry, duplicates (a family already in the table,
a family named twice), affine claims with and without the mode, the explicit modes cyclic s,
progression and fastprog, plan (auto plans fastprog for a family of progression rows), shards,
results and entry (VERIFIED), a missing, repeated or relabelled shard (never VERIFIED: the family is screened), a
result folder tampered with after the fact (refused at entry), a family that is not a CPHF (found by
the shards, by the screen and by the light check), a family over the budget (SCREENED, then
VERIFIED by a later exact check, then a duplicate), an array above the hash threshold (lowered for
the test: no array_sha256, identified by family_sha256, a RETRACTED row matched by it, and the
same rows rejected under the real threshold), the one-time fill of family_sha256 in the existing
certificate rows (allowed from empty to the listing's value; refused for another value, on a row
not checked through a certificate, and once set; needs git), and the light check of a pull request.

`tests/test_fastprog.py`: 1,565 tests, 0 failed, about 20 minutes on 2 cores. 300 random families
(t = 3 to 6, q up to 13, k up to 70; every progression row kind of `tests/test_progression.py`,
many WILD columns, all-progression and near-CPHF families) and 60 planted ones: fastprog (1 to 3
threads, AVX2 and scalar builds) and progression give the exit code, count, first set and
`checked` total of `full` of the first published build and the complete list of `full`, with
consistent completeness lines and the Python row classification; in a third of the cases (half of
the planted ones) fastprog also runs as m = 1, 2, 3 or 5 shards and as more shards than indices,
combined by `combine()` (1,190 tests: the same count, first set and list as unsharded fastprog and
full; a missing, repeated or relabelled shard refused). Mutations (scalar build, 80 + 10 cases
each): all 14 caught (WILD treated as a class, no probing of WILD partners, WILD-WILD pairs skipped,
chain cut to one partner, probe one class short, candidate range off by one, LINE[P][P] not WILD,
survivors not checked in the remaining rows, non-projective point index, prefix rank below t-3 not
a wildcard row, progression check stopping one column early, last shift skipped, a shard doing
every index, a shard doing an index it does not own); the equivalent mutant "wildcard row kept"
changes nothing, as expected (control).

### Identity of a family (cphf1)

A family is identified by family_sha256, the SHA-256 of its canonical serialization `cphf1`: the
first line `cphf1 n k q t`, then n lines of k decimal codes (each vector of GF(q)^t written in
base q, most significant digit first, the code of the family file), single spaces, a line feed
after every line, no comments, rows and columns in the order given. `cphfcheck FILE t q canon OUT`
writes it; `../cphf_cert.py` computes it independently, and `../check_certificates.py` refuses a
family for which the two differ. The table's rows keep the SHA-256 of the expanded array in
`array_sha256` whenever N times k is at most 10^12 entries; above that a certificate row may leave
`array_sha256` empty and is identified by the `family_sha256` column of `../../table/ca_table.csv`
alone. Every certificate row since 2026-11-02 records family_sha256, below the threshold as well.

### Expansion rules

`../../table/certificates/CERTIFICATES.csv` names the rule that turns each listed family into its
array (column `expansion`):

- `smc-1`: the all-zero run, then for r = 0..n-1 and beta = 1..q^t-1 in increasing base-q code
  (most significant digit first) the run whose entry in column c is beta . v_r[c]: n (q^t - 1) + 1
  runs (Sherwood, Martirosyan and Colbourn 2006). This is `cphfcheck expand` and
  `cphf_tools_pp.c expand`.
- `smc-1-affine`: as `smc-1`, but beta whose coordinates after the first are all zero are skipped,
  and the constant runs b = 1..q-1 are appended at the end: n (q^t - q) + q runs, for a family in
  which every vector has first coordinate 1 (`cphfcheck expand OUT affine`).
- a rule followed by `+fuse a>b`: then symbol a is written as b in every entry (Colbourn, Keri,
  Rivas Soriano and Schlage-Puchta 2010, Lemma 3.1): the same runs, one symbol fewer.
- a rule followed by `+fuse2 a`: then symbol a (the largest, a = q - 1) is removed with two runs
  as `fuse2.c` does: in every column the entry of the first run is exchanged with a, so that run is
  constant a and is deleted; then in every other run an a in column c is replaced by the entry of
  the second run in column c (by 0 where that entry is a), and the second run is deleted. Two runs
  and one symbol fewer (Lemma 3.1 of the same paper, used twice).

The listings of 2026-10-28 to 2026-10-31 are `smc-1`, `smc-1+fuse 4>0` and `smc-1+fuse2 4`.

### Buffered expand

Since 2026-11-02 `expand` builds each run in a buffer (per row, the sum over the first t-1
coordinates once for every q values of the last one) and writes it in blocks instead of one
`fprintf` per entry. The output bytes are unchanged (tested above and by the legacy section of
`tests/test_progression.py`). CA(40613; 5, 781, 5), 3.2e7 entries, now expands to a file in
0.17 s instead of 1.4 s; CA(218479; 5, 2801, 7), 6.1e8 entries, expands and hashes through a pipe
in 4.1 s (2.3 s for the expansion alone), about 4 ns per entry, so an array of 10^12 entries takes
about an hour to hash (`HASH_NS_PER_ENTRY` in `../cphf_cert.py`).

## Credits and bounds

The CPHF method and the CPHF-to-CA construction are those of Sherwood,
Martirosyan and Colbourn (2006). Rows whose columns are consecutive
vectors M^c x of a cyclic matrix (Singer cycles, linear feedback shift
register sequences) are known in the literature on covering arrays, for
example in the work of Raaphorst, Moura and Stevens (2014), of Tzanakis,
Moura, Panario and Stevens (2016), and of Shokri, Moura and Stevens
(arXiv:2510.13122), which this table already cites. What is this
project's here is these three families, the search that found them, its
completion by an exact pass, and the checker. The
existence bound the strength 5 and 6 rows of the table are compared with is
that of Colbourn, Lanus and Sarkar (Des. Codes Cryptogr. 86 (2018) 907-937,
doi:10.1007/s10623-017-0369-x).
