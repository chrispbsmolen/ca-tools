# Integrating the coverage checker into an R package

Prepared for Prof. Ulrike Groemping, 2026-08-10. Two integration paths,
lowest-friction first. Both are built from the same two files; everything
here passes `R CMD check` cleanly (R 4.3.3, status OK, tests included).

## What this is

A native-R port of the `ca_verify` C tool. Compared with the
command-line version you saw, the R version is friendlier in three ways:

- **No files, no system() calls.** The array passes directly from R as
  an integer matrix to a registered `.Call` entry point.
- **`NA` is the wildcard.** R's missing value maps onto the tool's
  "flexible value" semantics: an `NA` entry counts as every symbol.
- **Portable threading.** OpenMP through R's standard
  `SHLIB_OPENMP_CFLAGS` mechanism (works with Rtools on Windows; falls
  back to single-threaded automatically where OpenMP is absent). No raw
  pthreads.

Usage from R:

    ca <- rbind(c(0,0,0), c(0,1,1), c(1,0,1), c(1,1,0))
    ca_verify(ca, t = 2)
    #> VERIFIED: CA(N=4; t=2, k=3, v=2) - all 3 column sets cover all 4 tuples

    ca_verify(ca[-1, ], t = 2)
    #> NOT a covering array at t=2: 3 of 3 column sets have gaps (3 missing tuples)
    #> first missing examples (columns -> value combination):
    #>   (1,2) -> (0,0)   ...

Symbols may be `0..v-1` or `1..v` (auto-detected); `v` is inferred from
the data if not supplied; missing-tuple examples are reported in the
input coding.

## Path A (recommended): drop two files into your package

1. Copy `src/ca_verify.c` into your package's `src/` directory.
   - One change: rename the registration function `R_init_caverify` at
     the bottom to `R_init_<yourpackagename>`. If your package already
     has an init function, instead add the `C_ca_verify` line to your
     existing `R_CallMethodDef` table.
2. Copy `R/ca_verify.R` into your package's `R/` directory (rename the
   exported function if you prefer your own naming conventions).
3. In your `NAMESPACE` (or via roxygen), ensure:
       useDynLib(<yourpackagename>, .registration = TRUE)
       export(ca_verify)
       S3method(print, ca_verify)
4. Optional, for threading: create `src/Makevars` and
   `src/Makevars.win`, each containing:
       PKG_CFLAGS = $(SHLIB_OPENMP_CFLAGS)
       PKG_LIBS = $(SHLIB_OPENMP_CFLAGS)
   (Omitting this is fine - the code compiles and runs single-threaded
   without any Makevars at all.)
5. `R CMD check` as usual. The C file uses only the standard R API
   (R.h, Rinternals.h, R_ext/Rdynload.h) - no external dependencies.

That is the entire procedure; no autoconf, no C++ toolchain, no linking
questions. The `tests/test-ca_verify.R` file from the demonstration
package can be adapted to your test setup - it includes a pure-R
brute-force oracle and a randomized cross-validation loop you may find
useful as a permanent regression test.

## Path B: depend on the demonstration package

If you prefer not to carry C code at all, the enclosed `caverify`
package can be used as an ordinary dependency (`Imports: caverify`) and
called as `caverify::ca_verify(...)`. It is small, has no dependencies
of its own, and checks cleanly, so it could go to CRAN if that route is
useful to you. Path A keeps you self-contained; Path B keeps you C-free.

## Notes for review

- The worker makes no R API calls inside the parallel region (R is not
  thread-safe); all result construction happens after the join.
- Guard rails: t <= 20, v^t <= 2^31 tuples per column set, symbols
  validated before computation, allocation failures raise R errors
  rather than crashing.
- The `.Call` interface passes R's column-major matrix directly; the C
  code indexes accordingly (no transpose copies).
- License: MIT. Attribution appreciated but use it as suits the
  package best.
