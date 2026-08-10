# ca-tools

Small, dependency-light tools for working with covering arrays: a fast
verifier (the certificate check) and a records lookup for the Colbourn
tables catalogue.

Built as a contribution to the covering array community, alongside the
CAs R package by Ulrike Groemping (github.com/ugroempi/CAs), which preserves
the November 2024 status of Charlie Colbourn's covering array tables.

## What is in here

ca_verify.c
:   Fast strength-t coverage checker in portable C (pthreads). Reads a plain
    text array (whitespace or comma separated, symbols 0..v-1 or 1..v,
    wildcard entries '-', '*', 'x', 'NA' or -1 allowed), checks that every
    t-way interaction is covered, reports either VERIFIED or the missing
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

## R integration (r/)

r/ca_verify_r.c and r/ca_verify.R
:   The checker as a native R component: a single C file with a
    registered .Call entry point and one R wrapper. The array passes
    directly from R as an integer matrix, so there are no files and no
    system calls. R's NA is the wildcard. Threading uses R's standard
    OpenMP mechanism (portable to Windows via Rtools, automatic
    single-threaded fallback). Symbols 0..v-1 or 1..v are detected
    automatically.

r/caverify_0.1.0.tar.gz
:   The same two files as a complete self-contained R package that
    passes R CMD check (status OK). Its tests include a randomized
    cross-validation against an independent pure R implementation.
    Usable directly as a dependency for packages that prefer to stay
    free of C code.

r/INTEGRATION.md
:   Step-by-step instructions for either path: copying the two files
    into an existing package, or depending on the demonstration
    package.

## Validation

The verifier was tested against all 77 covering arrays shipped in the CAs
package data (CAEX_CAs and CKRS_CAs): 77 of 77 verify. Negative tests:
deleting a row, flipping a single entry, and over-claiming strength (t=4 on
a strength-3 array) are all detected and reported with example missing
tuples.

Speed on a small 2-core machine: a full scan of 2,118,760 column sets
(t=5, k=50, v=2, N=150) takes 1.7 seconds. Verification of every array in
the CAs package takes well under a second in total.

## Why a fast verifier matters

Trust in a covering array table should not require trusting the submitter:
an array is a certificate that anyone can check. Checking is cheap at small
strength but explodes combinatorially (C(k,t) column sets times v^t tuples);
at strength 5 and 6, where current research activity is, an R-level checker
becomes the bottleneck. This one is fast enough to re-verify entire
repositories routinely, e.g. in CI on every submission.

## Status and license

Early version, offered to the community; suggestions and corrections
welcome. MIT license (change freely if the community prefers otherwise).
