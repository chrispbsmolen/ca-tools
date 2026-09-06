## mac_4a_q127.R - reproduces the q=127 type-4a full verification
## that was first run in the cloud sandbox on 2026-09-03 (the
## question of that date: does type 4a repair the faulty 3a cases).
## This is the one faulty field size small enough for FULL
## verification. Expected: cyc(127, 6, type="4a") builds 768 x 128
## (the CAs author's predicted vq + v = 768, vs broken 3a at 762 and the 3b
## repair at 792), and ca_verify at t=3 returns covered = TRUE
## with 0 gaps out of choose(128,3) = 341,376 projections.
## Run from r/livingtable/ (paths adjusted for the repository layout):
##   Rscript mac_4a_q127.R | tee results/mac_4a_q127_result.txt
suppressMessages({library(CAs); library(caverify)})
ns <- asNamespace("CAs")
t0 <- Sys.time()
A <- eval(parse(text = "cyc(127, 6, type=\"4a\")"), envir = ns)
A <- as.matrix(A); storage.mode(A) <- "integer"
cat("built", nrow(A), "x", ncol(A),
    "(the CAs author's prediction: 768 x 128; broken 3a was 762; the 3b repair was 792)\n")
r <- ca_verify(A, 3, v = 6)
cat("covered:", r$covered, "\n")
## r$gaps is a scalar count in caverify 0.2.0 (checked 2026-09-04)
ngap <- if (is.null(r$gaps)) 0 else as.numeric(r$gaps)[1]
cat("gaps:", ngap, "of", choose(128, 3), "projections\n")
cat("elapsed:", round(as.numeric(Sys.time() - t0, units = "mins"), 1), "min\n")
cat(if (isTRUE(r$covered)) "Q127 4A FULL VERIFICATION PASS\n" else
    "*** Q127 4A FAILS ***\n")
