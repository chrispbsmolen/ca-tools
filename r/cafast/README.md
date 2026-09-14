# cafast

Fast engineering companions to the CAs package (Ulrike Groemping) for
covering arrays. Part of ca-tools; separate from caverify, which stays
the small certificate checker. Working name: rename at will.

Everything here re-implements or generalises a routine of CAs and is
tested against the CAs original on a battery that prints a DONE or PASS
line. NOTES.md is the register: what each function does, how it differs
from hers, what was tested and what the limits are.

## Functions

| function | replaces / extends | what it gives |
|---|---|---|
| `maxconstant_c(D, ...)` | `CAs::maxconstant` | same result up to symbol permutation, 60 to 100 times faster on real CAs (C clique search instead of igraph on an R-built graph) |
| `powerCT_any(t, k, v)`, `power_plan`, `power_build` | `CAs::powerCA` | the Colbourn and Torres-Jimenez power construction for any (t, k, v), not only the 132 catalogued settings; homogeneous case |
| `count_core(x, t, vs)` | counting behind `CAs::coverage` | per t-subset tuple multiplicities, with row multiplicities (ca-tools countkernel) |
| `flexpos_c`, `markflex_c` | `CAs::flexpos`, `CAs::markflex` | cell-for-cell reproductions in C |
| `postopNCK_c(D, t, ...)` | `CAs::postopNCK` | the Nayeri-Colbourn-Konjevod post-optimizer, calibrated against hers by distribution of achieved sizes (190x to 4,896x faster); deviations listed in R/nck_driver.R |

## Build, install, test

    R CMD build cafast
    R CMD INSTALL cafast_0.1.0.tar.gz
    cd cafast/inst/tests
    sh run_all.sh 2>&1 | tee run_all_result.txt

Needs R with CAs, caverify and lhs installed. The full run takes about
six minutes, most of it CAs::postopNCK in the driver comparison.

## Provenance

count_core.c, nck_faces.c, nck_faces.R and nck_driver.R are copies of
ca-tools/r/countkernel (the originals stay there with their own tests
and the calibration folder); the only edits are the load lines, since
the package registers its C routines in src/init.c. mc_core.c,
maxconstant_c.R and powerct.R are new for this package.
