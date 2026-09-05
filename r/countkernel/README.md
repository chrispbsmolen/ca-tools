# countkernel: a fast counting kernel for covering arrays, with an NCK post-optimizer

Part of ca-tools. Companion to the caverify package and to Ulrike
Groemping's CAs package, whose postopNCK algorithm this reimplements
at speed. Status: calibrated against CAs::postopNCK (see below);
awaiting the author's review before being called final.

## What is here

| file | what it is |
|---|---|
| `count_core.c` | the counting core: per t-subset of columns, the multiplicity of every value tuple over the rows (a row with an NA in the projection contributes nothing). Validated against a pure-R oracle on 529 randomized cases and against CAs::coverage. |
| `nck_faces.c` | `C_flexpos` (flexible positions, two NA conventions) and `C_markflex_pin` (the greedy first-coverer marking). Reproduce CAs::flexpos and CAs::markflex cell for cell. |
| `nck_faces.R` | R wrappers `flexpos_c(D, t, conv)` and `markflex_c(D, t, fixrows)`, plus the coding normalizer (0-based or 1-based input, returned in its own coding). |
| `nck_driver.R` | `postopNCK_c(D, t, ...)`: the Nayeri-Colbourn-Konjevod post-optimizer as implemented in CAs::postopNCK, the same core arguments and return shape, with the deviations listed in its header (D3 to D8) and two paper features (`timeBudget`, `restarts`). Interrupting returns the best array found so far. |
| `test_count_core.R` | counting core battery (oracle + CAs::coverage). |
| `test_nck_faces.R` | faces battery: 300 random mixed-level arrays for flexpos (half with NAs, both conventions), 120 for markflex with identical row order, coding tests. |
| `test_nck_driver.R` | driver battery: validity via caverify on every output, an instance whose reduction requires the inner search, timeBudget, restarts, early exit. |
| `oracle_count.R`, `bench_core.R` | the pure-R oracle and a benchmark. |

## Build and run

    R CMD SHLIB count_core.c
    R CMD SHLIB nck_faces.c
    Rscript test_count_core.R
    Rscript test_nck_faces.R
    Rscript test_nck_driver.R      # ~4 min, runs CAs::postopNCK for comparison

Requires R with packages CAs and caverify installed.

    library(CAs); library(caverify)
    source("nck_faces.R"); source("nck_driver.R")
    A <- nistCA(2, 15, 4)                      # a greedy array with slack
    B <- postopNCK_c(A, 2, seed = 1)           # 34 rows -> about 31
    caverify::ca_verify(B, 2, v = 4)           # NAs are flexible cells; fill them and it still covers

## Calibration against CAs::postopNCK (2026-09-05)

Twelve NIST IPOG arrays (the paper's own test family), identical
parameters (outerRetry 20, innerRetry 5, innerMaxnochange 15),
CAs::postopNCK 5 seeds per instance and postopNCK_c 20, six runs at
a time on one machine, every output verified by caverify after
filling flexible cells. Achieved sizes agree within seed noise
(postopNCK ahead on 8 of 12 instances by mean, postopNCK_c on 3,
one tie; average gap 0.09 rows in postopNCK's favour; rank test
p = 0.08). The 300 runs took postopNCK 11.7 hours of compute and
postopNCK_c 107 seconds. Per-instance speed ratios from 190x
(smallest) to 4,896x (largest). The script, table and csv are in
`calibration/`. Neither engine approaches the best known sizes from
greedy starting arrays, consistent with the original paper's
finding that post-optimization improves greedy arrays but not
search results.

Two things learned along the way, both consistent with the paper:
the algebraic constructions in CAs carry almost no flexible cells,
so post-optimization cannot act on them; greedy IPOG arrays carry
5 to 17 percent and are where it acts.

## Deviations from CAs::postopNCK

All deliberate and listed in `nck_driver.R`'s header: fills in the
array's own coding; explicit exhausted-row bookkeeping; own RNG
(seeds reproduce this driver, not postopNCK); silent by default;
`timeBudget` and `restarts` off by default; an unsuccessful inner
pass hands its perturbed array forward; the between-retry reset
freezes exactly the exhausted rows. `flexpos_c` keeps CAs's NA
convention as the default (shown to be the more conservative of
the two) and exposes the coverage convention behind `conv`.

## Argument and return differences from CAs::postopNCK

Arguments: `verbose` sits last instead of fourth, there is no `...`,
and `timeBudget` and `restarts` are added. Return: both give a
matrix of class `c("ca", "matrix", "array")` with flexible cells as
NA and a `seed` attribute; postopNCK_c does not carry postopNCK's
`rowOrder`, `Call`, or flexible-profile attributes, nor the input's
attributes.

## Review history

Three independent adversarial reviews (2026-09-04 and 2026-09-05)
preceded release, each by execution; every finding was fixed or
documented above.
