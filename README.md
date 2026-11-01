# ca-tools

The maintained version of this repository is at
https://github.com/chrispbsmolen/ca-tools. Forks and other copies may be
out of date.

Small, dependency-light tools for working with covering arrays: a fast
verifier (the certificate check) and a records lookup for the Colbourn
tables catalogue.

Built as a contribution to the covering array community, alongside the
CAs R package by Ulrike Groemping (github.com/ugroempi/CAs), which preserves
the November 2024 status of Charles J. Colbourn's covering array tables.

## What is in here

ca_verify.c
:   Fast strength-t coverage checker in portable C (pthreads). Reads a plain
    text array (whitespace or comma separated, symbols 0..v-1 or 1..v,
    don't-care entries '-', '*', 'x', 'NA' or -1 allowed and contributing
    nothing to a projection that contains them, the rule of caverify
    0.2.0), checks that every t-way interaction is covered, reports either
    VERIFIED or the missing
    tuples. Exit code 0/1/2 = verified / gaps / error, so it can gate a CI
    pipeline. Build: cc -O3 -pthread -o ca_verify ca_verify.c

ca_verify.py
:   The same checker in pure Python, no compiler needed. Slower; same
    input format, same output, same exit codes.

ca_query.py
:   Lookup and filtering over the Colbourn catalogue snapshot
    (colbourn_catalogue.csv, 13,641 records, from colbournBigFrame in the
    CAs package, November 2024 status). Subcommands: best, steps, sources,
    params. Standard library only.

colbourn_catalogue.csv
:   The catalogue as flat CSV: t, v, k, N, Source. A row means "with N runs,
    up to k columns are achievable at strength t with v levels". Best known
    N for a given k is the smallest N whose row has k at least your k
    (ca_query.py best does this for you).

## Submitting arrays (submissions/, tools/, .github/)

Anyone can add an explicit covering array to the provenance table in
table/ by pull request. A pull request adds one directory
submissions/<slug>/ with a claims.csv and the array files; a GitHub
Actions workflow verifies every array with ca_verify and posts a report
on the pull request; when a passing pull request is merged, the table
workflow on main checks it again against the current table and adds
its rows. The report usually appears within a few minutes. A
maintainer then reviews and merges, usually within a few days.
Every row records the published work its construction builds on, so
the table credits earlier authors and records new methods under the
names of the people who found them. The
format and the rules are in
submissions/README.md. tools/check_submission.py is the check (also
runnable locally), tools/render_table.py builds the table page
docs/index.html, which GitHub Pages serves. Both are standard library
Python. Every claim names its construction, every array on file has
its constant rows counted (tools/constant_rows.c, the computation of
cafast::maxconstant_c), and the table at
table/ca_table.csv (raw URL in table/README.md) is the machine-readable
form of the whole thing, read with the stair-step rule.

## R packages (r/)

r/caverify/
:   The verifier as an R package, caverify 0.2.0, on CRAN
    (`install.packages("caverify")`). A don't-care entry (NA)
    contributes nothing to a projection that contains it, so a verified
    array stays covering however its NA entries are later filled.
    Versions 0.1.x counted an NA as every symbol, a rule Ulrike
    Groemping showed can certify an array that is not covering. Its
    tests include a randomized cross-validation against an independent
    pure R implementation, and r/xval_mixed.R cross-validates it
    against the CAs package on mixed-level arrays.

r/cafast/
:   Fast C versions of routines of the CAs package (maxconstant_c,
    flexpos_c, markflex_c, postopNCK_c, count_core, and the power
    construction for any (t, k, v)), each tested against the CAs
    original. Version 0.1.0 is under review at CRAN; the development
    version here adds the change listed in its NEWS.md.

r/countkernel/
:   The development sources of cafast's counting kernel and of its
    Nayeri-Colbourn-Konjevod post-optimizer, with their calibration
    against CAs::postopNCK.

r/livingtable/
:   A dependency-propagation engine over the CAs catalogues, with the
    ledgers of the reproduction and verification campaign and an
    accounting of all 13,641 catalogue entries in nine classes.
    VERIFIED 987 and VERIFIED_IMPROVED 24 are entries an implemented
    route in CAs reproduces or beats; of these, 629 and 17 were built
    and verified in full, the rest screened, unfinished or failed (these
    are the engine's working labels, not the table's VERIFIED tier;
    three of the 987, the cyclotomy entries CAN(3, 128, 6),
    CAN(3, 2162, 20) and CAN(3, 2312, 21), failed a later check and
    would count 984 on a rerun, see r/livingtable/README.md).
    RECURSIVE 4,425 are sizes a calibrated construction law reproduces
    exactly from table ingredients,
    nothing built, with RECURSIVE_TENTATIVE 531 where the reading may
    be coincidental and RECURSIVE_STALE 10 where the law now gives
    fewer rows than the entry. POST_OPTIMIZED 380 were finished by a
    search after a construction, SEARCH 3,623 are search-tagged with
    no table ingredient, DIRECT_ONLY 339 are published one-off
    constructions with no builder, and OPEN 3,322 wait on ingredients
    the tables never published. The one distinction that matters is
    between an array that exists and has been checked and a size
    that only a construction accounts for. The engine is run by hand
    and is not yet connected to submissions, so the table holds no
    values derived by it. Details, laws and logs in
    r/livingtable/README.md.

## Validation

The verifier was tested against all 77 covering arrays of the CAs
package data sets CAEX_CAs and CKRS_CAs: 77 of 77 verify. Negative tests:
deleting a row, flipping a single entry, and over-claiming strength (t=4 on
a strength-3 array) are all detected and reported with example missing
tuples.

Speed on a small 2-core machine: a full scan of 2,118,760 column sets
(t=5, k=50, v=2, N=150) takes 1.7 seconds. Verification of all 77
of those arrays takes well under a second in total.

## Why a fast verifier matters

Trust in a covering array table should not require trusting the submitter:
an array is a certificate that anyone can check. Checking is cheap at small
strength but explodes combinatorially (C(k,t) column sets times v^t tuples);
at strength 5 and 6, where current research activity is, an R-level checker
becomes the bottleneck. This one is fast enough to re-verify entire
repositories routinely, e.g. in CI on every submission.

## How to cite

Cite the repository, https://github.com/chrispbsmolen/ca-tools, with the
commit you used, and for the arrays from cyclic covering perfect hash
families the report: C. Smolen, Cyclic covering perfect hash families: new
covering arrays of strength five and six with exact certificates, Zenodo,
doi:10.5281/zenodo.23751687 (all versions; the latest version also lists
arrays added after it was first published). Each row of the table names its own source,
and results of other authors should be cited to them.

## Status and license

Early version, offered to the community; suggestions and corrections
welcome, as a GitHub issue or by email to the maintainer, Christopher
Smolen (independent researcher, ORCID 0009-0002-9537-7961),
chrispbsmolen@gmail.com. The code is under the MIT license (LICENSE), except r/cafast
and r/countkernel, which follow code of the CAs package (GPL-3, by Ulrike
Groemping) closely and are under GPL (>= 3), with her agreement to the
"or later" terms. The table data in table/ is not original
to this repository. Each row names its source, the sources are listed
under Attribution in table/README.md, and the data remains subject to
those sources' terms. The arrays and certificates built by this project
(source S8, made by tools/own_arrays and tools/cphf and stored in
table/arrays and table/certificates) are by Christopher Smolen and are
released under the Creative Commons Attribution 4.0 International
license (CC BY 4.0).
