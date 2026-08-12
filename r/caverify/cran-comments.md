## Test environments

* local: macOS Tahoe 26.6.1, aarch64-apple-darwin23, R 4.6.1 (2026-06-24)
* win-builder: R-devel and R-release

## R CMD check results

Status: 2 NOTEs

* checking CRAN incoming feasibility ... NOTE
  Maintainer: 'Christopher Smolen <chrispbsmolen@gmail.com>'
  New submission

  This is a new submission.

* checking HTML version of manual ... NOTE
  Skipping checking HTML validation: 'tidy' doesn't look like recent
  enough HTML Tidy.
  Skipping checking math rendering: package 'V8' unavailable

  Both are limitations of the local check machine's toolchain rather than
  properties of the package. Neither check could run here. The package
  contains no math rendering in its documentation.

There were no ERRORs and no WARNINGs.

## Parallelism

The package uses OpenMP and by default requests half of the machine's
logical cores. It runs single-threaded for inputs below a size threshold,
and it caps itself at 2 threads when `_R_CHECK_LIMIT_CORES_` is set, so
checks on CRAN's machines will not exceed the two-core limit. The thread
count can also be set explicitly by the caller or by
`options(caverify.threads)`.

## Downstream dependencies

None. This is a new submission.
