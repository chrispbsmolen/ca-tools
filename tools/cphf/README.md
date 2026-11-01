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
| legacy | 63 | full, cyclic, sample, expand (also affine), usage errors: stdout, stderr, exit code and expanded file identical to the original build; header and `checked` line of the new modes match what check_certificates.py parses |
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

### Limits and doubts

- Sets proven covered by a P row are never rechecked one by one (that is the whole saving); the
  guarantees are the exact certification of every P row, the binomial totals, the rank recheck
  of everything reported, and the tests above.
- With no P rows, progression costs about C(k,t) rank tests, more than full; use full or
  fullfast then. The four real families tried have no progression rows in their column order.
- In mode full with more than one thread, "first uncovered" depends on scheduling (unchanged
  behaviour); the new modes always report the lexicographic minimum.
- The `checked` count is printed exactly (128-bit), also past 2^63.

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
