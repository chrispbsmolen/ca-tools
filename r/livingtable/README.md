# livingtable: a dependency-propagation engine for the covering array tables

## What this is

The Colbourn tables record the smallest known covering array for each
(t, k, v). Their maintainer's site is no longer public, and the R
package CAs (Groemping, GitHub version 0.24) ships a November 2024
snapshot of the tables as the dataset `colbournBigFrame` (13,641 rows
of t, v, k, N, Source), documented in `?colbournBigFrame` and in the
`ColbournTables.md` file of the CAs GitHub repository, together with per-family catalogues whose
rows carry executable recipes (`DPcat`, `PCAcat`, `CYCLOTOMYcat`,
`PALEYcat`, `ColbournKeriCombis`, and others such as `powerCTcat`).
Many entries are produced by constructions from smaller ingredient
entries, so an improvement at one entry changes the entries built on
it, and nothing public currently propagates such a change through the
tables. This directory is a propagation engine built on top of the CAs
catalogues.
Each catalogue recipe is a node, each ingredient call inside a recipe
is an edge, and the engine can find everything downstream of an
ingredient, rebuild those entries with a changed ingredient, verify
each rebuilt array with `caverify::ca_verify`, and cross-check the
incremental result against a full recompute. The directory also
carries the ledgers of the reproduction and verification campaign that
was run against the frozen snapshot, and the coverage accounting that
says which entries the engine can and cannot reach.

## How the engine is organized

All scripts run with `Rscript` from this directory. They read and
write CSV files in `data/`, and the stdout logs of the campaign runs
are kept in `results/`. Nothing is compiled.

The substrate is three files built from the CAs catalogues:

- `data/recipe_ingredients.csv`: one row per catalogue recipe (1,539
  recipes over five catalogues), with the recipe's code string and the
  list of ingredient calls parsed out of it (`parse_recipes.R`).
- `data/ingredient_dims.csv`: every unique ingredient call executed
  once and measured (876 calls, all resolved) (`ingredient_dims.R`).
- `data/ca_edges_v2.csv`: one row per (recipe, ingredient) pair,
  4,324 edges over 1,304 recipes, each with the ingredient's measured
  N, k and level range (`build_edges_v2.R`).

From these, `engine_closure.R` writes the two files the engine walks:

- `data/engine_nodes.csv`: one row per recipe, with its catalogue,
  row number, t, v, k, N and the canonical form of its code
  (1,539 nodes).
- `data/engine_links.csv`: recipe-to-recipe edges, present wherever a
  recipe's ingredient call is itself another recipe's code (412
  links). The closure script checks that this graph is acyclic.

`data/ca_edges.csv` is the earlier, coarser edge seed at the level of
(t, k, v) entries and construction families, produced from the
reproduction sweep. Its schema is described in
`LIVING_TABLE_SCHEMA.md`. The recipe-level files above supersede it
for the catalogues that carry code.

The engine has two modes, and they are required to agree:

- Graph mode (`engine_depquery.R`, `engine_walker.R`,
  `engine_substitute.R`, `mac_engine_demo.R`): start from an
  ingredient call, take its direct dependents from `ca_edges_v2.csv`,
  close transitively over `engine_links.csv`, and rebuild only that
  cascade. A substitution is done by evaluating each recipe in an
  environment layered over the CAs namespace in which the ingredient
  function returns the replacement array when called with exactly the
  target arguments.
- Sweep mode (`engine_sweep.R`, `mac_sweep.R`): re-evaluate every
  recipe in the web, with and without the substitution, and diff the
  sizes. The sweep is the correctness anchor. The set of entries the
  sweep says changed must lie inside the cascade graph mode predicted,
  and a disagreement is a bug in one of them, with the sweep winning
  until it is resolved.

Verification tiers used in the ledgers and logs:

- `EXECUTED`: the array was built and `ca_verify` confirmed full
  coverage at the declared strength (in the demo diff this tier is
  called `FULL`).
- `SCREEN4_PASS`: the array was too costly to verify in full within
  the run's budget, so four column windows (first 50, last 50, two
  random 50-column windows, narrower for high t in the powerCT
  re-audit) were each verified in full. A screen failure proves a
  defect because a subset of a covering array's columns must itself
  cover. A screen pass is not a certificate and is labeled as such.
- `GAPS_FOUND` and `FAILS(screen)`: coverage failed at the full or
  screen tier respectively.
- `ERR: TIMEOUT_KILLED`: the row's subprocess was killed at the
  15-minute limit in the retry pass (`mac_finish3.R`), after the row
  had already ended in an ERR in the earlier finishing pass.
- `ERR: TOO_LARGE_FOR_THIS_MACHINE`: the bare array would exceed the
  memory guard (2e8 cells by default) and was not attempted.
- `EXECUTED_POSTFIX` and `SCREEN4_PASS_POSTFIX`: the same tiers, in
  the re-audit run after the upstream fix of 2026-09-04.

## Coverage accounting

`data/ca_reproduction.csv` is the reproduction sweep over all 13,641
entries of `colbournBigFrame`: for each entry it asks `CAs::Ns(t, k, v)`
whether any implemented route reproduces the recorded N. Its `status`
column reads MATCH 985, BETTER 26, GAP 8,748, NOIMPL 3,834, ERR 48.

`engine_coverage.R` combines that with the recipe nodes and classifies
every entry. `data/engine_coverage.csv` says, over 13,641 entries with
no omissions:

| class | entries | share | meaning |
|---|---|---|---|
| RESOLVED | 987 | 7.2% | an implemented route or web recipe reproduces the recorded N exactly (985 MATCH rows plus 2 BETTER rows for which a recipe node has the recorded N) |
| BETTER | 24 | 0.2% | implemented routes beat the record |
| LEAF | 3,623 | 26.6% | the Source tag names a search, CPHF or annealing origin, so there are no ingredients to propagate from |
| UNRESOLVED | 9,007 | 66.0% | everything else |

The UNRESOLVED count by strength is t=2: 2,920, t=3: 686, t=4: 850,
t=5: 1,670, t=6: 2,881.

`data/better_verified.csv` holds the 17 BETTER entries that were
feasible to build and verify in full. All 17 verified, with margins of
1 to 170 rows over the snapshot (routes TJ, CK_doublingCA, ODbasedCA,
DWYER).

The 9,007 UNRESOLVED entries are the subject of the arithmetic tier
below, which reads size laws off their Source tags and splits the
class further in `data/engine_coverage_v2.csv`.

## The arithmetic tier

The verified engine reaches only entries with an executable recipe.
The 9,007 UNRESOLVED entries carry Source tags that name a
construction and its parameters, or a search result, but no
executable recipe. Where the tag names a recursive construction
(Power CT, Direct product, Add n factors, fuse, and so on) the size
is a function of the recorded sizes of other table entries, and the
arithmetic tier is that function, recovered per family and wired as
an engine organ. Every law is a size
relation over claims. Nothing in this tier is verified, it sits below
EXECUTED and SCREEN4_PASS, it is never blended with them, and a size it
propagates is reported as a claim derived from claims.

The ingredient lookup is `eCAN(t, w, v)`, the smallest N recorded in
the table at any k of at least w, which is what the table's own
entries use. A family's law is admitted only where it is exact. The
calibration gate is that the recorded N of every row of the family in
the frozen table must equal the law applied to the recorded sizes of
its ingredients, using no free parameter beyond what the tag states
(one exception, the Power N-CT hash family row count, is described in
the table). Rows that fail the gate are not admitted and are tiered by
how they fail. The tiers, over the 9,007 UNRESOLVED entries
(`data/arith_tally.csv`, `results/arith_tally_result.txt`):

| tier | entries | meaning |
|---|---|---|
| ARITHMETIC | 4,401 | a calibrated law reproduces the recorded N exactly from ingredient sizes that are themselves table entries; wired into the engine |
| ARITH_INFERRED | 149 | the law is exact but an ingredient is not a table entry (117 Martirosyan-Colbourn rows with v of at least 6) or the reading may be coincidental (32 Direct product generalized rows); not wired |
| ARITH_ABOVE | 10 | the record sits above its own law, so the law claims a smaller array than the record; leads, not claims, until the array is built |
| ARITH_BELOW | 0 | the record sits below the law (a better ingredient reading exists); none remain |
| ARITH_BOUND_ONLY | 13 | postop NCK tags, where the law gives a bound only |
| TERMINAL_CLAIMED | 700 | the tag names a search result or a published array with no table ingredient, so no propagation can ever reach the entry |
| ARITH_OPEN | 2,901 | attempted, law not recovered |
| NOT_ATTEMPTED | 833 | Cohen-Colbourn-Ling 318, PCAx2PCA 294, PCAxPCA 221 |

The families and their laws, each calibrated on every row of the
family in the frozen table (counts from the result logs named in the
inventory; "unresolved admitted" is the family's ARITHMETIC count in
the tally):

| family | law | calibration on the table | unresolved admitted |
|---|---|---|---|
| Power CT | hash family of M rows over the columns of OA(q^e, q+1, q, e), row i a CA(t, w_i, v) with rho_i constant rows, N = chi + sum (N_i - rho_i) (Colbourn and Torres-Jimenez 2010, Theorem 2.3, as in `CAs::DHHF2CA`), M = (e - 1) Turan(t, v) + 1, tag grammar q^e, +p, T, S, Arc, Trin, c read from the record | 469 of 471 exact, 0 wrong, 2 inexpressible | 445 |
| Power N-CT | the same law with M not known from theory and solved from the record as one integer per (t, min(t, v), q, e), 39 keys, every row of a key giving the same integer, M plus or minus 1 fitting 0 of 2,093 rows | 2,033 of 2,093 exact, 0 wrong, 60 inexpressible | 2,033 |
| perfect hash family a,b,w [T r or S s] [,c] | the same law with M = a; the D16 form (na rows at a symbols, nb at b) N = na (eCAN(t, a, v) - 1) + nb (eCAN(t, b, v) - 1) + 1 | 612 of 612, and 8 of 8 for the D16 form | 620 |
| Direct product (plain tag) | N = min over pairs k1 k2 of at least k of eCAN(2, k1, v) + eCAN(2, k2, v) - v (Colbourn, Martirosyan, Mullen, Shasha, Sherwood and Yucas 2006; `CAs::productCA`), 174 of 174 on the executed DPcat recipes | 212 of 545 exact; the generalized tag 32 of 1,573 with the record below the best pair on 1,522 | 206 |
| Derive from strength t+1 | N = floor(eCAN(t+1, k+1, v) / v) | 71 of 71 | 33 |
| Add n factors, Add a factor | b = k - n, N = eCAN(t, b, v) + sum over j = 2 to min(t, n+1) of v^(j-1) (v-1) eCAN(t-j, b-1, v); domain n of at most 2, or v a prime power with n of at most v, or n = 3 at v in 12, 15, 20, 21, 24 | 396 of 579 exact, 6 above inside the domain, 177 outside the domain | 391 |
| Chateauneuf-Kreher doubling | N = eCAN(3, k/2, v) + (v-1) eCAN(2, k/2, v) (Cohen, Colbourn and Ling 2008, Theorem 2) | 111 of 114, the 3 rows at v = 20 above the law | 95 |
| Martirosyan-Colbourn | h = k/2, N = eCAN(t, h, v) + (v-1) eCAN(t-1, h, v) + eCAN(t-2, h, v^2), read off the record (no copy of the paper was available) | 37 of 38 exact where the third ingredient is a table entry (v of at most 5), 1 above; 117 rows at larger v exact with one constant per (t, v), tiered ARITH_INFERRED | 37 |
| fuse (every tag ending in m fuse words) | N = eCAN(t, k, v + m) - 2m at strengths 3 to 6, a regularity read from the record | 1,303 of 1,354 exact, 42 with the base outside the table, 9 below the law | 147 |
| Colbourn-Martirosyan-TVT-Walker, strength 3 | N = eCAN(3, k', v) + (v-1) eCAN(2, k', v) + v^3 - v^2, k' = ceiling(k / v), at prime power v; at v + 1 a prime power, that row minus 2 | 28 of 28 (23 and 5) | 28 |
| Martirosyan-TVT | even k, c = k/2, the size law `CAs::N_upper_MTVTRouxtypeCA` states at strength 5 and its shape one strength up at 6; odd k (the variant tag), the ingredient widths split over ceiling(k/2) and floor(k/2) as the unique full fit | 206 of 206 even, 160 of 160 odd, 6 postop rows bound only | 366 |

The strength-4 rows of Colbourn-Martirosyan-TVT-Walker (582 of the
583), the direct product rows without a law (1,861, of which 1,541
carry the generalized tag and 320 the plain tag), Power CZ (212), the
Add rows
outside their domain (177), 62 power rows with an Arc reduction
followed by a T reduction, and 7 fused extended OA rows are the 2,901
ARITH_OPEN entries.

Identity test (`arith_engine.R identity`,
`results/arith_engine_identity_result.txt`). The law evaluators in
`arith_laws.R` are a second implementation of the calibration scripts,
and the engine requires the frozen record to reproduce itself through
them. Result, 4,401 of 4,401 ARITHMETIC entries reproduce their
recorded N. The run writes `data/arith_edges.csv`, 10,328 distinct
entry-to-lookup edges (14,101 lookups in all), the non-range lookups
answered by 1,902 distinct table rows, and 240 ARITHMETIC entries are themselves
ingredients of other ARITHMETIC entries, which is why propagation has
to iterate.

Propagation (`arith_engine.R demo` and `arith_engine.R propagate
file.csv`). An improvement is a row t, k, v, N, optionally with the
number of constant rows the new array is known to carry (default 1,
the only number any covering array guarantees, so a law that credits
an ingredient with v constant rows credits an improved ingredient only
for what it carries). Improvements are validated (known (t, v),
integer N of at least v^t, k of at least t, N below the current
lookup, k clamped to the table's widest row). Two modes, graph (only
the entries whose recorded lookups the improvement can move, applied
and repeated with the changed entries as the next round's
improvements) and sweep (recompute every ARITHMETIC entry, apply,
repeat), are each iterated to a fixpoint and must agree on the
closure, the sweep winning otherwise.

Demo (`results/arith_engine_demo_result.txt`, `data/arith_cascade.csv`).
The 17 verified improvements of `data/better_verified.csv` were
offered and all 17 accepted. The closure is two entries, both from the
verified CA(3, 12, 14) at 3,381 rows (record 3,458). CAN(3, 24, 14)
goes from 6,279 to 6,202 by Chateauneuf-Kreher doubling, and
CAN(5, 23, 14) goes from 3,070,224 to 3,053,515 through the
Martirosyan-TVT variant law, 16,786 rows in all. Graph mode and sweep
mode both stop after two rounds and agree (the log's verdict line is
`TWO-MODE AGREEMENT ON THE CLOSURE: PASS`). Both new sizes are claims.
The doubling's other ingredient, the table's CAN(2, 12, 14) at 217
rows, carries a terminal tag (Add Factor SO, a search result), so the
doubled array cannot be built here from table ingredients and neither
new size has been verified. The other 16 improvements move no
recorded lookup; graph mode found two candidate entries in its first
round, both fed by CA(3, 12, 14), and none in the second.

The ten ARITH_ABOVE rows are the only places where a law claims more
than the record, and each is a construction that has not been
executed. They are the three Chateauneuf-Kreher doubling rows at
v = 20, k = 36, 38, 40 (recorded 18,677, 18,753, 19,019 against the
law's 18,487, 18,563, 18,639, with the present eCAN(2, 18 to 20, 20)
as ingredient), six Add n factors rows, three at (t, v) = (5, 8) and
three at (5, 13), above the sum by 7, 12 and 24 units of v(v - 1),
each equal to the difference between the answering strength-3 row
and a neighbouring row, and one Martirosyan-Colbourn row, (5, 4, 2374)
recorded 45,549 against 45,534. They are listed in
`results/arith_formula_small_result.txt`,
`results/arith_formula_addn_result.txt` and
`results/arith_formula_mc_result.txt`.

Coverage with the tier counted apart (`arith_coverage_republish.R`,
`data/engine_coverage_v2.csv`, `results/arith_coverage_republish_result.txt`),
over 13,641 entries with no omissions:

| class | entries | share |
|---|---|---|
| RESOLVED | 987 | 7.2% |
| BETTER | 24 | 0.2% |
| LEAF | 3,623 | 26.6% |
| ARITHMETIC | 4,401 | 32.3% |
| ARITH_INFERRED | 149 | 1.1% |
| ARITH_ABOVE | 10 | 0.1% |
| ARITH_BELOW | 0 | 0.0% |
| ARITH_BOUND_ONLY | 13 | 0.1% |
| TERMINAL_CLAIMED | 700 | 5.1% |
| ARITH_OPEN | 2,901 | 21.3% |
| NOT_ATTEMPTED | 833 | 6.1% |

Entries with a handle (verified by construction 1,011, leaves 3,623,
ARITHMETIC 4,401, each counted apart) number 9,035 of 13,641, 66.2
percent. By strength the share with a handle is 16.6 percent at t = 2,
70.1 at t = 3, 64.1 at t = 4, 85.0 at t = 5 and 94.2 at t = 6. Strength
two is low because its 2,376 entries without a handle are exactly the
direct product rows without a law (1,861) and the PCA products (515).
Entries
with no handle (open plus not attempted) are 3,734 in all, 27.4
percent, and 700 are terminal claims that no propagation can reach.

What stays open, and why. Two closed papers and one missing table
hold the constructions behind most of the 3,734 entries. Colbourn,
Martirosyan, Mullen, Shasha, Sherwood and Yucas (2006, J. Combin.
Des. 14) are the tables' authority for the generalized product (the
1,861 open direct product rows, 1,541 of them under the generalized
tag) and, by the tag names, for the PCA products (515 rows); Colbourn
2008 (Discrete Mathematics 308) was read and cites the 2006 theorems
rather than restating them. Colbourn and Zhou (2012, J. Stat. Theory
Pract. 6) are named by the Power CZ tag (212 rows); the Power CT law
reproduces none of its 215 table rows, every residual negative. Neither
paper is open access and neither was read. The third gap is not a
paper but a table. The k-ary Roux theorem of Cohen, Colbourn and Ling
(2008, Theorem 3) and the strength-4 theorems of Colbourn,
Martirosyan, Van Trung and Walker (2006) use difference covering array
numbers (DCAN) and covering ordered design numbers (CODN) that the
covering array table does not hold, so the 318 Cohen-Colbourn-Ling
rows and the 583 strength-4 CMTW rows cannot be calibrated from the
table alone (the pure-CAN strength-4 forms were tested and fit none of
the 583). The CMTW paper was read only through an automated summary
of the authors' open copy, so its theorem numbers are that summary's.
The Add n factors law outside its stated domain (177 rows) and the 62
power rows with an Arc reduction followed by a T reduction were
attempted and not recovered.

## Verification campaign results

The campaign attempted to build and verify every MATCH entry of the
reproduction sweep with `CAs::bestCA` and `caverify::ca_verify` (`mac_grind.R`,
then `mac_finish2.R` with a subprocess and hard timeout per row, then
`mac_finish3.R` for the timeout pile at screen tier with a memory
guard). The two ledgers cover all 985 MATCH entries with no overlap:

`data/edge_executed_progress.csv` (716 rows):

| note | rows |
|---|---|
| EXECUTED | 629 |
| GAPS_FOUND | 2 |
| ERR: TIMEOUT_KILLED | 36 |
| ERR: TOO_LARGE_FOR_THIS_MACHINE | 49 |

`data/edge_screen_progress.csv` (269 rows):

| note | rows |
|---|---|
| SCREEN4_PASS | 267 |
| FAILS(screen) | 2 |

So 629 entries are fully certified, 267 pass a four-window screen,
85 are unresolved with a stated reason, and 4 failed. The final log of
the retry pass is `results/mac_finish3_result.txt` (its last line:
certified 629, failures 2, screened 267, still unresolved 85). Two
details of the ledgers: 16 of the 267 SCREEN4_PASS rows have k between
19 and 37, where a 50-column window is the whole array, so each of
those was in fact verified in full by an earlier version of the worker
that still labeled it a screen (the shipped `finish_one.R` labels such
rows EXECUTED), and three EXECUTED rows built one row smaller than the
snapshot, (2, 1728, 11) 359 to 358, (2, 8000, 19) 1079 to 1078 and
(2, 17576, 25) 1871 to 1870, all Direct product entries built via
recBoseCA_CA and verified at the smaller size.

The four failures are the four defects the campaign found, all in
frozen-table entries whose cited construction, as implemented in CAs
at the time, did not produce a covering array:

| entry | recorded N | how it failed | finding |
|---|---|---|---|
| CAN(3, 128, 6) | 762 | full verification, cyclotomy type 3a at q=127 | `findings/FINDING_CAN_3_128_6.md` |
| CAN(3, 2162, 20) | 43,220 | 50-column screen, cyclotomy type 3a at q=2161 | same finding |
| CAN(3, 2312, 21) | 48,531 | 50-column screen, cyclotomy type 3a at q=2311 | same finding |
| CAN(3, 1584, 2) | 64 | full verification, 123 gapped triples, powerCT with cover starter | `findings/FINDING_POWERCT_3_1584_2.md` |

The cyclotomy family audit (`mac_cyclotomy_audit2.R`,
`results/cyclotomy_audit2_result.txt`) covered all 213 rows of
`CYCLOTOMYcat`: 210 pass (16 full, 194 screen), the 3 above fail. The
follow-up (`results/cyclotomy_followup_result.txt`) ran multi-window
screens on the 194 screen-tier rows with zero new failures, and the
four-window screens pass for the type 3b sibling at the two large q.
The q=127 type 3b array (792 x 128) was fully verified, as recorded in
the finding. The per-row outputs are `data/cyclotomy_audit2.csv` and
`data/cyclotomy_screen4.csv`.

All four were fixed upstream in CAs on 2026-09-04 (GitHub commits
ae81661 for the cyclotomy rows, which now use type 4a at sizes
vq + v, and d1c6570 for the DHHF2CA defect behind the powerCT entry,
both dated 2026-09-04 in the repository history). The CAs `NEWS.md`
entry "September 05 2026, still version 0.24" describes both fixes.
The type 4a arrays were checked here: `results/mac_4a_q127_result.txt`
(768 x 128, full verification, 0 gaps of 341,376 projections) and
`results/mac_4a_result.txt` (43,240 x 2162 and 48,552 x 2312, 48
caverify windows each, all pass). The 14 powerCT rows the CAs author
had diagnosed as affected were re-audited with the fixed code
(`mac_powerct_refix.R`, `data/powerct_refix.csv`,
`results/powerct_refix_result.txt`): 2 full passes including
CAN(3, 1584, 2) at 64 rows, 12 screen passes, 0 failures. The main
ledgers were not re-run after the fix, so they still record the four
rows as failures of the pre-fix code.

## Acceptance evidence

Two-mode agreement (`mac_sweep.R`, `results/mac_sweep_result.txt`,
`data/sweep_agreement.csv`). Both full sweeps of the 1,539 recipes ran
with 0 construct errors. The wall time of the sweeps was not reliably
recorded (the timing line of the shipped log came from a units error
in `mac_sweep.R`, since corrected). The baseline sweep matched the catalogue's
recorded N at 1,531 of 1,539 recipes. The 8 mismatches are all DPcat
products (rows 49, 59, 62, 69, 87, 98, 110, 322) whose rebuilt array
is smaller than the catalogue records, seven by one row and DPcat 322
by two. Under a substitution that serves a one-row-fatter
`SCA_LCDST(5, 3)` everywhere, the sweep found 20 changed entries, the
graph cascade predicted at most 41, 0 changed entries lay outside the
predicted cascade, and 21 cascade members absorbed the change. Verdict
in the log: TWO-MODE AGREEMENT: PASS.

Demo and replay (`mac_engine_demo.R`, `results/engine_demo_result.txt`,
`data/engine_demo_diff.csv`). With the same fatter `SCA_LCDST(5, 3)`
payload: cascade 41 entries (41 direct). Baseline pass 41 entries,
verified 41, errors 0. Replacement pass 41 entries, verified 41,
errors 0. Restore pass 41 entries, verified 41, errors 0. Entries
changed by the replacement: 20 of 41 (absorbed unchanged: 21).
Rebuilt arrays verified covering: 41 of 41, all at tier FULL.
Baseline rebuilt sizes equal the recorded sizes: 41 of 41. After
restore, rebuilt sizes equal the recorded sizes: 41 of 41. Verdicts:
propagation test PASS (change propagated, every output verified),
replay test PASS (record reproduced after rewind and restore).

The shipped `results/engine_demo_result.txt` and
`results/mac_4a_q127_result.txt` were regenerated with the shipped
scripts on 2026-09-05 (2-core sandbox, 2 workers for the demo), after
the scripts' output wording was changed, so that the logs are verbatim
output of the scripts as shipped. The regenerated
`data/engine_demo_diff.csv` was identical to the file produced on the
author's workstation.

## What is not done or untested

- The new-record form of the demo (a genuine improvement propagated
  to dependents and the improved sizes verified) has not been run. As
  of 2026-09-05 none of the verified improvements in
  `data/better_verified.csv` has dependents in the recipe web (they
  are high-strength leaves), so the demo uses a substitution payload
  (`fatter`, the ingredient with one duplicated row) instead. The
  code path is the same and accepts any replacement array from an
  `.rds` file.
- 9,007 of 13,641 entries (66.0%) are UNRESOLVED: no implemented route
  in CAs reproduces them and no recipe node matches them, so the
  engine cannot rebuild them. A further 3,623 are leaves. The
  arithmetic tier gives 4,401 of the 9,007 a calibrated size law, as
  claims only; 3,734 have no handle and 700 are terminal claims.
- Nothing in the arithmetic tier is verified. The two propagated
  sizes of the demo, CAN(3, 24, 14) at 6,202 and CAN(5, 23, 14) at
  3,053,515, are claims from a verified ingredient through the
  record's own tags, and the ten ARITH_ABOVE rows are constructions
  that have not been executed. The propagate mode has been exercised
  here only with the demo's improvement set, and no propagated size
  has yet been built and verified.
- The arithmetic laws for Martirosyan-Colbourn, Martirosyan-TVT at
  strength 6, the odd-k Martirosyan-TVT variant, the fuse loss of two
  rows per symbol at strengths 3 to 6, the Add n factors sum and the
  D16 hash family form were read off the record, not from a paper.
  Each is exact on every row of its stated domain, and each is
  labeled a reading in its script header. The paper of Colbourn,
  Martirosyan, Van Trung and Walker was read only through an
  automated summary of the authors' copy.
- `results/arith_formula_dp_result.txt` was not regenerated in the
  packaging test (the script needs `data/engine_nodes.csv`,
  `data/recipe_ingredients.csv` and `data/ingredient_dims.csv`, which
  were not in the test copy); it is the log of the original run. Every
  other arithmetic-tier log was regenerated by the shipped scripts on
  2026-09-06, and every regenerated csv with an original to compare
  against (15 of 16) was byte-identical to it.
- 85 MATCH entries remain unverified: 49 arrays are too large for the
  memory of one workstation (128 GB) and 36 hit the 15-minute limit
  per row in the retry pass. Screens of 50-column windows are not certificates.
- Several shipped data files predate the cyclotomy fix of 2026-09-04
  and reflect the three type-3a rows (CYCLOTOMYcat 5, 26, 29) at their
  old sizes 762, 43,220 and 48,531: `data/recipe_ingredients.csv` and
  `data/engine_nodes.csv` carry the old `type = "3a"` code,
  `data/sweep_agreement.csv` carries the old sizes in N_book and
  N_base, and `data/ca_reproduction.csv` records those three entries
  as MATCH via the CYCLOTOMY route, which `data/engine_coverage.csv`
  inherits as RESOLVED. With the current CAs, `Ns(3, 128, 6)` reports
  CYCLOTOMY = 768 against the snapshot's 762, so a rerun of the
  reproduction sweep would turn those three rows into GAP (MATCH 985
  would become 982 and RESOLVED 987 would become 984), and a rerun of
  `mac_sweep.R` against the shipped nodes would report 1,528 of 1,539
  baseline matches instead of 1,531. The reproduction sweep script is
  not shipped, so `data/ca_reproduction.csv` cannot be regenerated
  from this directory. Re-running `parse_recipes.R` and
  `engine_closure.R` regenerates the recipe and node files from the
  fixed catalogue (the packaging test confirmed that exactly those
  three rows change). None of the three rows is in the
  `SCA_LCDST(5, 3)` cascade used by the demo and the sweep test.
- The engine covers the five catalogues with executable code strings.
  `powerCTcat` and the other catalogues without code strings are not
  nodes in the web (the cyclotomy family was audited row by row, the
  powerCT family only partly, see the next item).
- The full powerCT family audit (`mac_powerct_audit.R`) was
  interrupted before completion and its partial checkpoint is not
  shipped. The fourteen author-diagnosed rows were re-audited after
  the upstream fix (`mac_powerct_refix.R`, `data/powerct_refix.csv`).
  The three construct errors that the partial run recorded for
  powerCA(6, 1332, 3) and powerCA(6, 1369, 3) ("invalid 'type' (list)
  of argument") remain unexamined and are listed here as an open item.
- The campaign scripts (`mac_grind.R`, `mac_finish2.R`,
  `mac_finish3.R`, the family audits) were run on a workstation with
  many cores and hours of wall time and have not been re-run in the
  packaging test. Their paths were adjusted to this layout in the same
  way as the tested scripts.

## How to run

Requirements: R, the CAs package (GitHub version, 0.24 or later, with
the 2026-09-04 fixes if you want the catalogues to match the findings)
and the caverify package from this repository (`r/caverify`, 0.2.0 or
later). No build step. Run everything from this directory. Network
access is needed for a full rebuild: several catalogue recipes and
`bestCA` routes download arrays from math.nist.gov (this affects
`ingredient_dims.R`, the sweeps and the campaign scripts).

The demo (about 1 to 5 minutes depending on cores, `cap` is the
full-verification cost budget, `workers` the number of parallel
processes):

    Rscript mac_engine_demo.R "SCA_LCDST(5, 3)" fatter 1e13 2 | tee results/engine_demo_result.txt

To propagate a real replacement array, save it with `saveRDS` and pass
the path in place of `fatter`. Output: `data/engine_demo_diff.csv`.

The two-mode sweep (both full sweeps, then the agreement check, uses
all cores but two by default):

    Rscript mac_sweep.R | tee results/mac_sweep_result.txt

The coverage accounting (about one second, rewrites
`data/engine_coverage.csv` from `data/ca_reproduction.csv` and
`data/engine_nodes.csv`):

    Rscript engine_coverage.R

Individual organs:

    Rscript engine_depquery.R "SCA_LCDST(5, 3)"        direct dependents of a call
    Rscript engine_depquery.R dims 11 5                 same, by ingredient dimensions
    Rscript engine_walker.R "PCAcat 1"                  rebuild and verify the cascade below a recipe
    Rscript engine_substitute.R identity "SCA_LCDST(5, 3)" 8
    Rscript engine_substitute.R swap "SCA_LCDST(5, 3)" repl.rds 8
    Rscript engine_sweep.R baseline out.csv [start] [end]
    Rscript engine_sweep.R swap "SCA_LCDST(5, 3)" repl.rds out.csv [start] [end]

Rebuilding the substrate from the installed CAs, in order:
`parse_recipes.R`, `ingredient_dims.R` (checkpointed, retries rows
that errored, rerun until it reports 876 of 876 resolved),
`build_edges_v2.R` (must report 0 unresolved), `engine_closure.R`.

The campaign scripts take optional `[cap] [workers]` arguments and are
documented in their headers. `finish_one.R` and `powerct_one.R` are
per-row workers launched by `mac_finish2.R`, `mac_finish3.R` and
`mac_powerct_refix.R` as subprocesses and are not run directly.

The arithmetic tier, in this order (each script reads the frozen
table inside CAs and, most of them, `data/engine_coverage.csv`, writes
its csv to `data/`, and takes a few seconds apart from
`arith_formula_mtvt.R` at about a minute; the whole sequence ran in
about two minutes in the packaging test):

    Rscript arith_measure.R | tee results/arith_measure_result.txt
    Rscript arith_formula_power.R | tee results/arith_formula_power_result.txt
    Rscript arith_formula_dp.R | tee results/arith_formula_dp_result.txt
    Rscript arith_formula_dp_table.R | tee results/arith_formula_dp_table_result.txt
    Rscript arith_probe_powerCZ.R | tee results/arith_probe_powerCZ_result.txt
    Rscript arith_formula_small.R | tee results/arith_formula_small_result.txt
    Rscript arith_families_probe.R | tee results/arith_families_probe_result.txt
    Rscript arith_formula_addn.R | tee results/arith_formula_addn_result.txt
    Rscript arith_formula_mc.R | tee results/arith_formula_mc_result.txt
    Rscript arith_formula_fuse.R | tee results/arith_formula_fuse_result.txt
    Rscript arith_formula_cmtw.R | tee results/arith_formula_cmtw_result.txt
    Rscript arith_formula_mtvt.R | tee results/arith_formula_mtvt_result.txt
    Rscript arith_families_tail.R | tee results/arith_families_tail_result.txt
    Rscript arith_tally.R | tee results/arith_tally_result.txt
    Rscript arith_engine.R identity | tee results/arith_engine_identity_result.txt
    Rscript arith_engine.R demo | tee results/arith_engine_demo_result.txt
    Rscript arith_coverage_republish.R | tee results/arith_coverage_republish_result.txt

`arith_formula_dp.R` reads the substrate files (`data/engine_nodes.csv`,
`data/recipe_ingredients.csv`, `data/ingredient_dims.csv`) and only
checks the law on the executed recipes; the family scripts do not
depend on it. `arith_formula_fuse.R` reads the probe's csv, `arith_tally.R`
reads every family csv, `arith_engine.R` reads `data/arith_tally.csv`
and `data/arith_power_Mtable.csv` and sources `arith_laws.R`, and the
republish reads the tally. To propagate your own improvements, give a
csv with columns t, k, v, N and optionally nconst (constant rows the
array carries, default 1):

    Rscript arith_engine.R propagate my_improvements.csv

The cascade is written to `data/arith_cascade_my_improvements.csv`.
Every size it contains is a claim.

## File inventory

| file | role |
|---|---|
| `README.md` | this file |
| `PIPELINE.md` | manifest: which script produces which file, in order |
| `LIVING_TABLE_SCHEMA.md` | design note for the edge schema and the two propagation modes |
| `parse_recipes.R` | parse catalogue code strings into ingredient calls |
| `ingredient_dims.R` | execute and measure every unique ingredient call |
| `build_edges_v2.R` | join recipes and ingredient dimensions into the edge file |
| `engine_closure.R` | recipe nodes, recipe-to-recipe links, DAG check |
| `engine_depquery.R` | reverse-dependency query for an ingredient |
| `engine_walker.R` | rebuild and verify the cascade below a recipe |
| `engine_substitute.R` | re-evaluate dependents with a replaced ingredient |
| `engine_sweep.R` | full recompute of every recipe, optional substitution |
| `engine_coverage.R` | coverage accounting of the 13,641 entries |
| `mac_sweep.R` | two-mode agreement run (baseline and swap sweeps versus graph cascade) |
| `mac_engine_demo.R` | live propagation with verification and change-and-restore replay |
| `mac_grind.R` | certification grind over MATCH entries |
| `mac_finish2.R`, `finish_one.R` | subprocess-per-row finishing run and its worker |
| `mac_finish3.R` | screen-tier retry of the timeout pile with memory guard |
| `verify_better.R` | build and verify the BETTER entries |
| `mac_cyclotomy_audit2.R`, `mac_cyclotomy_followup.R` | cyclotomy family audit and follow-up |
| `mac_4a_check.R`, `mac_4a_q127.R` | checks of the type 4a repair |
| `mac_powerct_audit.R` | powerCT family audit |
| `mac_powerct_refix.R`, `powerct_one.R` | post-fix re-audit of the 14 diagnosed powerCT rows and its worker |
| `data/recipe_ingredients.csv` | recipes and their ingredient calls |
| `data/ingredient_dims.csv` | measured dimensions of each ingredient call |
| `data/ca_edges_v2.csv` | recipe-to-ingredient edges |
| `data/ca_edges.csv` | earlier entry-level edge seed |
| `data/engine_nodes.csv` | recipe nodes with t, v, k, N and canonical code |
| `data/engine_links.csv` | recipe-to-recipe links |
| `data/construction_families.csv` | Source tags of `colbournBigFrame` clustered into families |
| `data/ca_reproduction.csv` | reproduction sweep over all 13,641 entries |
| `data/engine_coverage.csv` | coverage class of every entry |
| `data/better_verified.csv` | verified BETTER entries |
| `data/edge_executed_progress.csv` | full-verification ledger of the campaign |
| `data/edge_screen_progress.csv` | screen-tier ledger of the campaign |
| `data/sweep_agreement.csv` | per-recipe sizes from the baseline and swap sweeps |
| `data/engine_demo_diff.csv` | per-entry diff of the demo (recorded, baseline, replacement, restored) |
| `data/powerct_refix.csv` | post-fix powerCT re-audit ledger |
| `data/cyclotomy_audit2.csv` | per-row output of the cyclotomy family audit (213 rows) |
| `data/cyclotomy_screen4.csv` | per-row output of the cyclotomy multi-window follow-up (194 rows) |
| `results/mac_sweep_result.txt` | log of the two-mode agreement run |
| `results/engine_demo_result.txt` | log of the demo and replay |
| `results/mac_finish3_result.txt` | log of the final retry pass of the campaign |
| `results/cyclotomy_audit2_result.txt` | log of the cyclotomy audit |
| `results/cyclotomy_followup_result.txt` | log of the cyclotomy follow-up |
| `results/mac_4a_result.txt` | log of the type 4a window checks at q=2161 and q=2311 |
| `results/mac_4a_q127_result.txt` | log of the type 4a full verification at q=127 |
| `results/powerct_refix_result.txt` | log of the post-fix powerCT re-audit |
| `findings/FINDING_CAN_3_128_6.md` | the cyclotomy finding |
| `findings/FINDING_POWERCT_3_1584_2.md` | the powerCT finding |
| `arith_measure.R` | the ceiling of the arithmetic tier: the UNRESOLVED entries by tag family |
| `arith_formula_power.R` | Power CT and Power N-CT size law, calibrated on every power row |
| `arith_formula_dp.R` | direct product law checked on the executed DPcat recipes |
| `arith_formula_dp_table.R` | direct product law on the frozen table (best pair) |
| `arith_probe_powerCZ.R` | Power CZ probe (grammar and column rule read, size law not recovered) |
| `arith_formula_small.R` | Derive, Add 1 factor, Chateauneuf-Kreher doubling, perfect hash family |
| `arith_families_probe.R` | Add a factor, a recorded blind pattern search (nothing admitted), the terminal families |
| `arith_formula_addn.R` | Add n factors and Add a factor for every n, with the domain |
| `arith_formula_mc.R` | Martirosyan-Colbourn |
| `arith_formula_fuse.R` | the fuse suffix over the whole table |
| `arith_formula_cmtw.R` | Colbourn-Martirosyan-TVT-Walker (strength 3 admitted, strength 4 open) |
| `arith_formula_mtvt.R` | Martirosyan-TVT, even and odd k |
| `arith_families_tail.R` | the last 39 rows outside the paper-blocked families |
| `arith_tally.R` | the tally of every UNRESOLVED entry by arithmetic tier |
| `arith_laws.R` | the law evaluators, one per admitted family (sourced by the engine) |
| `arith_engine.R` | identity test, arithmetic edges, and two-mode propagation to closure |
| `arith_coverage_republish.R` | coverage accounting with the arithmetic tier counted apart |
| `data/arith_formula_power.csv`, `data/arith_power_Mtable.csv` | per-row power calibration and the fitted N-CT hash family table |
| `data/arith_formula_dp_table.csv` | per-row direct product calibration |
| `data/arith_probe_powerCZ.csv` | per-row Power CZ probe |
| `data/arith_formula_small.csv`, `data/arith_families_probe.csv`, `data/arith_families_tail.csv` | per-row calibration of the smaller families, the probe and the tail |
| `data/arith_formula_addn.csv`, `data/arith_formula_mc.csv`, `data/arith_formula_fuse.csv`, `data/arith_formula_cmtw.csv`, `data/arith_formula_mtvt.csv` | per-row calibration of the Add, Martirosyan-Colbourn, fuse, CMTW and Martirosyan-TVT families |
| `data/arith_tally.csv` | every UNRESOLVED entry with its arithmetic tier and family |
| `data/arith_edges.csv` | entry-to-lookup edges of the ARITHMETIC entries with the answering table row |
| `data/arith_cascade.csv` | the demo closure (two entries) |
| `data/engine_coverage_v2.csv` | coverage class of every entry with the arithmetic tier apart |
| `results/arith_*_result.txt` | the log of each arithmetic-tier script above (identity and demo logs for the engine) |
