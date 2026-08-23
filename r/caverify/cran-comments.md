## Submission

caverify 0.1.3. This is the correction for the installation ERROR reported
against 0.1.2 on r-devel-linux-x86_64-fedora-clang, notified by the CRAN
Team on 2026-08-20 with a deadline of 2026-09-10.

## The problem and the fix

The install log for that flavour shows six errors inside clang's own
omp.h, all at `#pragma omp declare variant` directives, the first being
"expected 'match', 'adjust_args', or 'append_args' clause on 'omp declare
variant' directive".

The cause is include order in `src/ca_verify.c`. Unless `R_NO_REMAP` is
defined, the R headers define `match` as a macro for `Rf_match`. Clang 22
uses a `match` clause on the `declare variant` directives in its omp.h, so
an omp.h included after the R headers had those clauses rewritten by the
macro and no longer parsed. Earlier compilers on the other flavours do not
use the directive, which is why only this one failed.

Two changes in `src/ca_verify.c`, with no change to behaviour, interface
or documentation.

1. `omp.h` is now included before the R headers.
2. The file defines `R_NO_REMAP` and uses the `Rf_` prefixed API
   throughout, so no R macro can reach a system header again.

## Test environments

* local: macOS Tahoe 26.6.1, aarch64-apple-darwin23, R 4.6.1 (2026-06-24),
  checked with `R CMD check --as-cran`, 2026-08-23, on the submitted
  tarball (md5 71b5ed266ed99388b1c4496684ea2a21)
* win-builder R-devel, 2026-08-23, <<FILL RESULT>>

## R CMD check results

0 errors | 0 warnings | 2 notes

The first note is the one described below. The second is local tooling
only and does not arise on CRAN.

      checking HTML version of manual ... NOTE
      Skipping checking HTML validation: 'tidy' doesn't look like recent
      enough HTML Tidy.
      Skipping checking math rendering: package 'V8' unavailable

Compiled code, pragmas, `SHLIB_OPENMP_*FLAGS` use and all 9 tests check
OK on that run.

A "Days since last update" NOTE is expected. 0.1.2 was published on
2026-08-20 and this submission is the correction requested by the CRAN
Team the same day, so the short interval is deliberate.

## Notes for the reviewer

The package uses OpenMP where it is available, guarded by
`SHLIB_OPENMP_CFLAGS` in `src/Makevars` and `src/Makevars.win`, and runs
single-threaded where it is not. Threads default to half the logical cores,
are capped at two when `_R_CHECK_LIMIT_CORES_` is set, and can be
overridden with `options(caverify.threads)`.

## Previous submission record

0.1.2 submitted 2026-08-19, published 2026-08-20.
