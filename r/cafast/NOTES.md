# cafast (working name) - notes and register

Separate package from caverify, by decision 2026-09-13 (reply to Ulrike).
Purpose: fast replacements for the slow parts of the CAs package that the
living table rebuild leans on, plus the countkernel optimizer. caverify
stays small; this package is the "engineering" side.

Every function here is tested against Ulrike's original on a battery of
arrays and the battery prints a DONE line. Semantics are matched, not
just results: where a tie-break can differ from hers, it is written down
here.

## 1. maxconstant_c (replaces CAs::maxconstant)      2026-09-14

What her function does: builds a graph on the rows (edge = the two rows
differ in every column), takes the largest clique with igraph, prefers a
largest clique that contains the existing constant rows, moves the
clique to the front and permutes symbols within each column so those
rows become the constant rows 0, 1, 2, ... in order. A clique can have
at most v rows. The pair loop is quadratic in N in R, which is where the
time goes (nistCA(4,20,5), 2892 rows: 25 s).

What ours does: src/mc_core.c, C_maxclique_disjoint. Same graph, built in
C; a bounded branch-and-bound clique search that stops at size v; the
existing constant rows are tried first as a forced start, then the
unconstrained maximum; a strictly larger unconstrained clique wins,
otherwise the forced one is kept (her preference). R/maxconstant_c.R
reorders rows clique-first and applies the per-column symbol
permutation. Arguments as hers: verbose (0, 1, 2, 12), remove,
one_is_enough, dupcheck. NA cells are refused (fill them before calling).

Tie-break difference: when several largest cliques exist, hers takes
igraph's last one, ours takes the first found in row order. The results
are equivalent (same clique size; the arrays differ by a symbol
permutation and a row order), which is all any caller relies on. On
arrays with many duplicate rows this changes how many rows outside the
clique happen to come out constant too; that number is not a property
either function promises.

Test: tests/test_maxconstant.R (run from tests/, needs CAs, caverify,
lhs; loads ../src/mc_core.so built with `R CMD SHLIB mc_core.c` in src/).
Battery: 10 nistCA cases (t = 2..5, k up to 60, N up to 2892), 40 random
arrays with all levels present in every column (seed 7; includes arrays
with 3 columns, many chance constant rows and many duplicates), Bush
CA(4,5,4) of 64 rows, cyclic CA(2,19,2). Checks per case: same number of
leading constant rows (strictly ascending symbol), rows equivalent to the
input up to per-column symbol permutation and row order, and for the CA
cases full coverage by ca_verify. Also remove = TRUE and one_is_enough on
two cases.

Result 2026-09-14: 52 cases, 0 mismatches; hers 35.5 s total, ours 0.5 s;
nistCA(4,20,5) 25.4 s vs 0.29 s. Two earlier "mismatches" were the test
counting chance constant duplicates, fixed in the metric, not the code.

## 2. powerCT_any (generalises CAs::powerCA)      2026-09-14

Her powerCA builds only the 132 settings in powerCTcat. Ours takes any
(t, k, v): R/powerct.R, functions power_plan, power_build, powerCT_any.
Homogeneous case only (one ingredient, no T-reductions). Shape: Bush
OA(q^e, q+1, q, e) transposed, first M = (e-1)*Turan(t,v) + 1 columns
become the DHF rows (needs q >= M-1); ingredient CA(t, q, v) from
CAs::bestCA, constant rows moved front with maxconstant_c (rho of them);
N = M*(N1 - rho) + chi, chi = max(0, v - M*(v - rho)). Assembly mirrors
DHHF2CA (row r of the DHF uses the ingredient shifted by (r-1)*rho mod v;
chi constant rows added for the tuples nobody covered; duplicates
removed). power_plan enumerates e = 2..emax and, per e, the smallest
admissible prime powers q with q^e >= k (qextra more), builds each
ingredient once and reports N; powerCT_any builds the smallest.

Test: tests/test_powerct.R. Part 1: every homogeneous Bush row of her
catalogue with N <= 3000 (t=3 k=121, t=3 k=1331, t=4 k=1331, t=5 k=2197,
all v=2) rebuilt with her q and e: same N as the catalogue and as her
array; coverage verified in full or by a 10x25 window screen when the
column-set count exceeds 2e6. Part 2: six settings not in the catalogue
(CA(3,200,3) 255 rows, CA(3,500,2) 55, CA(4,300,2) 190, CA(3,100,4) 472,
CA(4,200,3) 1407, CA(5,400,2) 791), all built and verified (full or
screen). failures 0. Larger catalogue rows skipped in the battery;
tests/time_big.R rebuilds CA(6,361,3): 52614 rows on both, hers 9.1 s,
ours 4.6 s, 5x20 screen passes. The gain here is generality, not speed:
her power construction is fast already because it uses one_is_enough on
big ingredients.

Honest limits: the plan only says what the construction gives, which is
usually above the table (e.g. CA(3,200,3): 255 vs known 153); the
catalogue's heterogeneous rows (T-reductions, several ingredients) are
not reproduced yet; non-Bush OAs for the DHF (her miscCA(2,7,12) row)
are not covered.

## 3. Package assembled                              2026-09-14

DESCRIPTION, NAMESPACE (useDynLib with registration, src/init.c),
R/: maxconstant_c.R, powerct.R, count_core.R (new wrapper), nck_faces.R
and nck_driver.R (copies of countkernel, load lines removed, .Call on
registered symbols). inst/tests/: test_count_core.R (with
oracle_count.R), test_nck_faces.R, test_maxconstant.R, test_powerct.R,
test_nck_driver.R, time_big.R, run_all.sh. Built and installed here
(R CMD build / INSTALL, no warnings), run_all.sh: count core 529 cases
0 failures; faces PASS; maxconstant 52 cases 0 mismatches; powerCT 0
failures; driver PASS. Result file inst/tests/run_all_result.txt.
Next: same on the Mac, then ship into ca-tools/r/cafast (his commit).
Waiting on Ulrike's naming answer only for the living-table rename,
not for this package.

Mac run 2026-09-14 (R 4.6, Apple clang, arm64): build and install clean,
run_all.sh all five batteries pass, result file inst/tests/run_all_result.txt
(count core 529/0; faces PASS; maxconstant 52 cases 0 mismatches, hers
15.0 s vs ours 0.2 s; powerCT 0 failures; driver PASS). Package ready to
commit.
