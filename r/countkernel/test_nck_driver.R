## test_nck_driver.R - driver validity battery plus a smoke
## calibration vs CAs::postopNCK (the full calibration gate runs on
## a full machine, see calibration/).
## Run from this directory:  Rscript test_nck_driver.R
suppressMessages({library(CAs); library(caverify)})
source("nck_faces.R"); source("nck_driver.R")
set.seed(20260904)
fails <- 0
chk <- function(ok, what) {
    if (!ok) { cat("FAIL:", what, "\n"); fails <<- fails + 1 }
}
## an output is valid iff, with every flexible cell filled
## arbitrarily, the array still covers (promise semantics)
valid_ca <- function(A, t, vs) {
    B <- as.matrix(A); attributes(B) <- attributes(B)["dim"]
    for (j in seq_len(ncol(B))) {
        nas <- which(is.na(B[, j]))
        if (length(nas)) B[nas, j] <- min(B[, j], na.rm = TRUE)
    }
    storage.mode(B) <- "integer"
    r <- tryCatch(ca_verify(B, t, v = max(vs)), error = function(e) NULL)
    !is.null(r) && isTRUE(r$covered)
}

## ---- 1. the manual example: reach 12 rows, every output valid ----
hilf <- strsplit(c("2222001", "0022222", "1121201", "0120110",
                   "2210202", "2102122", "1200020", "0211121",
                   "1012100", "2001210", "0000001", "1111012",
                   "2222222", "2222011"), "")
plan <- do.call(rbind, lapply(hilf, as.numeric))
sizes <- integer(10)
for (s in 1:10) {
    o <- postopNCK_c(plan, 2, seed = s, outerRetry = 3)
    sizes[s] <- nrow(o)
    chk(valid_ca(o, 2, rep(3, 7)), sprintf("manual seed %d output covers", s))
}
cat("manual example: achieved sizes over 10 seeds:",
    paste(sizes, collapse = " "), "(optimum by eCAN is 12)\n")
chk(all(sizes <= 12), "manual example reaches 12 rows on every seed")

## ---- 2. smoke calibration vs CAs::postopNCK, same tiny budget ----
A <- cyc(19, 2)                       ## strength-3 array
A <- rbind(A, A[sample(nrow(A), 4), ])   ## add 4 redundant rows
storage.mode(A) <- "integer"
t_h <- system.time({
    hs <- sapply(1:4, function(s) {
        r <- NULL
        capture.output(suppressMessages(
            r <- postopNCK(A, 3, seed = s, outerRetry = 2,
                           innerRetry = 2, innerMaxnochange = 5)))
        nrow(r)
    })
})[3]
t_o <- system.time({
    os <- sapply(1:8, function(s) {
        o <- postopNCK_c(A, 3, seed = s, outerRetry = 2,
                         innerRetry = 2, innerMaxnochange = 5)
        chk(valid_ca(o, 3, rep(2, ncol(A))),
            sprintf("cyc19 seed %d output covers", s))
        nrow(o)
    })
})[3]
cat("smoke calibration, CA from cyc(19,2)+4 dup rows, t=3, tiny budget:\n")
cat("  CAs: sizes", paste(hs, collapse = " "),
    " in", round(t_h, 1), "s (4 seeds)\n")
cat("  ours: sizes", paste(os, collapse = " "),
    " in", round(t_o, 1), "s (8 seeds)\n")
chk(min(os) <= min(hs), "ours reaches at least CAs best size")
cat("  (note: this instance reduces at the first removal check only;",
    "the inner search is exercised in 2b)\n")

## ---- 2b. inner-loop calibration (added after the 2026-09-04 review) ----
## A random covering array built by adding random rows until covered.
## 'trivial strip' = repeated markflex + first-check removal, which
## needs no shuffle/fill search. Anything below it REQUIRES the inner
## loop. Identical parameters for both engines, outputs re-verified.
set.seed(7)
k <- 7; v <- 3; tt <- 2
R <- matrix(sample(0:(v-1), 6 * k, replace = TRUE), 6, k)
R[1:v, ] <- matrix(0:(v-1), v, k)
repeat {
    if (isTRUE(ca_verify(R, tt, v = v)$covered)) break
    R <- rbind(R, sample(0:(v-1), k, replace = TRUE))
}
storage.mode(R) <- "integer"
triv <- R
repeat {
    m <- markflex_c(triv, tt)
    rm <- which(rowSums(is.na(m)) >= k - tt + 1)
    if (!length(rm)) break
    m <- m[-rm, , drop = FALSE]
    for (j in seq_len(k)) { nas <- which(is.na(m[, j]))
        if (length(nas)) m[nas, j] <- 0L }
    triv <- m; attributes(triv) <- attributes(triv)["dim"]
}
cat("inner-loop instance: k=7 v=3 t=2, N0 =", nrow(R),
    " trivial strip =", nrow(triv), "\n")
pars <- list(outerRetry = 10, innerRetry = 5, innerMaxnochange = 15)
t_h2 <- system.time({
    hs2 <- sapply(1:4, function(s) { r <- NULL
        capture.output(suppressMessages(r <- do.call(postopNCK,
            c(list(R, tt, seed = s), pars)))); nrow(r) })
})[3]
t_o2 <- system.time({
    os2 <- sapply(1:12, function(s) {
        o <- do.call(postopNCK_c, c(list(R, tt, seed = s), pars))
        chk(valid_ca(o, tt, rep(v, k)), sprintf("inner-loop seed %d covers", s))
        nrow(o) })
})[3]
cat("  CAs: sizes", paste(hs2, collapse = " "), " mean", round(mean(hs2), 2),
    " in", round(t_h2, 1), "s (4 seeds)\n")
cat("  ours: sizes", paste(os2, collapse = " "), " mean", round(mean(os2), 2),
    " in", round(t_o2, 1), "s (12 seeds)\n")
chk(mean(os2) < nrow(triv), "inner loop reduces below the trivial strip")
chk(mean(os2) <= mean(hs2) + 1, "ours within one row of CAs mean size")

## ---- 3. wall-clock budget returns a valid best-so-far ----
B <- rbind(A, A[sample(nrow(A), 2), ])
o <- postopNCK_c(B, 3, seed = 1, timeBudget = 0.4, outerRetry = 50)
chk(isTRUE(attr(o, "timeout")) || nrow(o) < nrow(B),
    "timeBudget: timed out or improved")
chk(valid_ca(o, 3, rep(2, ncol(B))), "timeBudget output covers")

## ---- 4. already-optimal early exit ----
FF <- as.matrix(expand.grid(0:1, 0:1)); storage.mode(FF) <- "integer"
o <- postopNCK_c(FF, 2, seed = 1)
chk(identical(dim(o), dim(FF)), "full factorial returned unchanged")

## ---- 5. restarts argument runs and stays valid ----
o <- postopNCK_c(plan, 2, seed = 3, outerRetry = 6,
                 outerMaxnochange = 2, restarts = 2)
chk(valid_ca(o, 2, rep(3, 7)), "restarts output covers")

cat("\n", if (fails == 0) "ALL NCK DRIVER TESTS PASS" else
    paste(fails, "FAILURES"), "\n", sep = "")
