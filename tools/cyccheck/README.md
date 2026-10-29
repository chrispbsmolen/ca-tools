# Full checks of binary cyclotomic arrays (2026-10-28)

`cyccheck.c` checks the strength of the p x p circulant of the quadratic nonresidue
indicator (row r, column c holds 1 when c - r is a nonresidue mod p, 0 on the diagonal),
which is `CAs::cyc(p, 2)`. It verifies two symmetries on the array before using them:
shifting rows and columns together, and multiplying row and column indices by a quadratic
residue (checked for a generator of the residues). Every t-set of columns is then
equivalent to one containing columns 0 and s, s = 1 or the smallest nonresidue n0, and
all such sets are checked. It prints, for each s, the number of uncovered sets of that form.

    gcc -O3 -march=native -fopenmp -o cyccheck cyccheck.c      # macOS: clang with libomp
    ./cyccheck 1231 6 - 14          # p, t, vector file or - (built here), threads

`cyccheck_metal.m` is the same check on an Apple GPU (strengths 4 to 6):

    clang -O2 -fobjc-arc -framework Metal -framework Foundation -o cyccheck_metal cyccheck_metal.m
    ./cyccheck_metal 1231 6 -

`brute.c` (all t-sets) and `brute3.c` (all sets {0, s, ...}) use neither symmetry.
`gpu_test.sh` builds the GPU and CPU checkers and compares their counts on cases where
coverage fails (p = 73, 103 at t = 4; 61, 313, 337 at t = 5; 131 at t = 6) and checks that
a vector with two flipped entries is rejected. The CPU counts were also compared with
`brute3.c` (exact agreement, including p = 359 and 379 at t = 5) and the t = 4 verdicts
with `brute.c` for p = 11 to 113.

Results (Apple M4 Max GPU, 2026-10-28, 4 to 12 minutes per prime): `cyc(p, 2)` has
strength 6 with no uncovered set for the 31 primes p = 1231, 1283, ..., 1619, and
`cyc(503, 2)` has strength 5. So `derive(cyc(p, 2))` is a CA((p-1)/2; 5, p-1, 2). See
`../../results/tjcat_cyclotomy_2026-10-29/` for the list of calls with array hashes.
Credit: Christopher Smolen. The construction is Colbourn's (Des. Codes Cryptogr. 55 (2010)
201-219); the Colbourn tables credit these strength 6 entries to Torres-Jimenez.
