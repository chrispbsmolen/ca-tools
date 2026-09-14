## cafast: powerCT_any against CAs::powerCA on the homogeneous catalogue rows,
## plus settings outside the catalogue verified with caverify. Run from tests/.
suppressMessages({library(CAs); library(caverify)})
suppressMessages(library(cafast))
e <- environment(CAs::powerCA); cat_ <- get("powerCTcat", envir = e)
hom <- cat_[cat_$u2 == 0 & grepl("SCA_Busht", cat_$OAforDHF), ]
hom <- hom[!duplicated(hom[, c("t", "v", "k", "N")]), ]
cat("prime powers to 60:", cafast:::prime_powers(60), "\n")
cat("Turan check:", all(sapply(2:7, function(t) sapply(2:6, function(v) cafast:::Turan_(t, v) == CAs::Turan(t, v)))), "\n\n")
## full verification when the column-set count is small; otherwise a window screen
check <- function(A, t, v, W = 10, w = 25) {
    if (choose(ncol(A), t) <= 2e6) return(list(kind = "full", ok = isTRUE(ca_verify(A, t, v = v)$covered)))
    set.seed(1); ok <- TRUE
    for (j in seq_len(W)) { cols <- sort(sample(ncol(A), min(w, ncol(A)))); if (!isTRUE(ca_verify(A[, cols, drop = FALSE], t, v = v)$covered)) { ok <- FALSE; break } }
    list(kind = sprintf("screen %dx%d", W, w), ok = ok)
}
fails <- 0
cat("== part 1: catalogue rows (same q, e as hers), compare N and verify where feasible\n")
for (i in seq_len(nrow(hom))) {
    t <- hom$t[i]; k <- hom$k[i]; v <- hom$v[i]; q <- hom$w1[i]; ee <- hom$expon[i]
    if (hom$N[i] > 3000) { cat(sprintf("t=%d k=%d v=%d: catalogue N=%d, skipped (too large for this battery)\n", t, k, v, hom$N[i])); next }
    t0 <- Sys.time()
    A <- power_build(t, k, v, q, ee)
    tb <- as.numeric(Sys.time() - t0, units = "secs")
    t0 <- Sys.time(); H <- suppressWarnings(suppressMessages(powerCA(t, k, v))); H <- as.matrix(H); H[is.na(H)] <- 0L; th <- as.numeric(Sys.time() - t0, units = "secs")
    ch <- check(A, t, v); ok <- ch$ok
    same <- nrow(A) == hom$N[i] && nrow(H) == nrow(A)
    if (!(ok && same)) fails <- fails + 1
    cat(sprintf("t=%d k=%d v=%d q=%d e=%d: catalogue N=%d, hers %d rows (%.1f s), ours %d rows (%.1f s), covers %s (%s)  %s\n", t, k, v, q, ee, hom$N[i], nrow(H), th, nrow(A), tb, ok, ch$kind, if (ok && same) "OK" else "MISMATCH"))
}
cat("\n== part 2: settings outside the catalogue\n")
outside <- list(c(3, 200, 3), c(3, 500, 2), c(4, 300, 2), c(3, 100, 4), c(4, 200, 3), c(5, 400, 2))
for (s in outside) {
    t <- s[1]; k <- s[2]; v <- s[3]
    cat(sprintf("CA(%d,%d,%d):\n", t, k, v))
    A <- tryCatch(powerCT_any(t, k, v), error = function(err) { cat("  error:", conditionMessage(err), "\n"); NULL })
    if (is.null(A)) { fails <- fails + 1; next }
    ch <- check(A, t, v); ok <- ch$ok
    cn <- tryCatch(Ns(t, k, v), error = function(err) NA)
    cat(sprintf("  built %d rows (q=%d e=%d), covers %s (%s); table/known N: %s\n", nrow(A), attr(A, "q"), attr(A, "e"), ok, ch$kind, paste(cn, collapse = " ")))
    if (!ok) fails <- fails + 1
}
cat(sprintf("\nfailures %d\n", fails)); cat("POWERCT TEST DONE\n")
