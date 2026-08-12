## Test environments

* local: macOS Tahoe 26.6.1, aarch64-apple-darwin23, R 4.6.1 (2026-06-24),
  checked with `R CMD check --as-cran` on the submitted tarball, 2026-08-12
* win-builder: R-devel (2026-08-10 r90389 ucrt) and R-release 4.6.1 ucrt.
  Windows binaries built successfully on both. The service did not return a
  check log for either run, so no win-builder check result is claimed here.

## R CMD check results

0 errors | 0 warnings | 2 notes

* checking CRAN incoming feasibility ... NOTE

      Maintainer: 'Christopher Smolen <chrispbsmolen@gmail.com>'
      New submission

  This is the first submission of caverify to CRAN.

* checking HTML version of manual ... NOTE

      Skipping checking HTML validation: 'tidy' doesn't look like recent
      enough HTML Tidy.
      Skipping checking math rendering: package 'V8' unavailable

  Both checks were skipped because of the local machine's HTML Tidy version
  and a missing optional package. This reflects the check environment rather
  than the package.

## Notes for the reviewer

The package uses OpenMP where it is available, guarded by
`SHLIB_OPENMP_CFLAGS` in `src/Makevars` and `src/Makevars.win`, and runs
single-threaded where it is not. Threads default to half the logical cores,
are capped at two when `_R_CHECK_LIMIT_CORES_` is set, and can be overridden
with `options(caverify.threads)`.
