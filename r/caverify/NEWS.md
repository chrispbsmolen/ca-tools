# caverify 0.2.0

* Mixed-level covering arrays (MCAs): `v` now also accepts an integer
  vector of length `ncol(x)` giving each column its own number of
  symbols, or the string `"auto"` to infer per-column symbol counts
  from each column's own maximum. Tuple counting and indexing in the C
  kernel are mixed-radix; a uniform array is the degenerate case and
  takes the same code path.
* NA wildcard semantics unchanged: an NA entry counts as every symbol
  of its own column.
* Unchanged defaults: `v = NULL` still infers a single uniform value
  from the data range exactly as in 0.1.x, and a scalar `v` behaves as
  before, so existing callers (including package 'CAs') see identical
  behaviour.
* `print` shows mixed-level results with the levels profile in
  exponent notation (e.g. `levels 4^2 3 2^3`).
* Tests: mixed-level brute-force oracle plus randomized mixed-level
  cross-validation added.

# caverify 0.1.3

* Fixed an installation failure on R-devel with clang 22, seen on the
  CRAN flavour r-devel-linux-x86_64-fedora-clang. The R headers remap
  `match` to `Rf_match` unless `R_NO_REMAP` is defined, and clang 22's
  `omp.h` uses `match` as a clause of `#pragma omp declare variant`, so
  an `omp.h` included after the R headers no longer parsed. `omp.h` is
  now included first and the C code compiles with `R_NO_REMAP` and the
  `Rf_` prefixed API. No user-visible change.

# caverify 0.1.2

* Automatic thread selection: by default the checker now uses half the
  machine's logical cores (single-threaded for small jobs, capped to 2
  during CRAN checks). No setup needed; `options(caverify.threads = n)`
  or the `threads` argument still override.

# caverify 0.1.1

* Long verifications are now interruptible (Escape / Ctrl-C) without
  aborting the R session: combinations are processed in batches with an
  interrupt check between batches, and all working memory is R-managed
  so interruption cannot leak.
* `threads` now defaults to `getOption("caverify.threads", 1L)`.
* DESCRIPTION metadata cleanup (URL, BugReports).

# caverify 0.1.0

* First version: registered .Call interface, NA as wildcard ("flexible
  value"), optional OpenMP threading, 0- or 1-based symbol detection,
  tests including randomized cross-validation against a pure R oracle.
