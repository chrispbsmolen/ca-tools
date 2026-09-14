suppressMessages({library(CAs); library(caverify)})
suppressMessages(library(cafast))
nconst <- function(B) { # leading constant rows with strictly ascending symbol = the clique placed in front (a chance duplicate behind it does not count)
    cst <- rowSums(B == B[, 1]) == ncol(B); n <- 0L
    for (r in seq_len(nrow(B))) { if (!cst[r] || (r > 1 && B[r, 1] <= B[r - 1, 1])) break; n <- r }
    n }
ntotal <- function(B) sum(rowSums(B == B[, 1]) == ncol(B))
mk <- function(t, k, v) { A <- suppressWarnings(nistCA(t, k, v)); A <- as.matrix(A); A[is.na(A)] <- 0L; storage.mode(A) <- "integer"; A }
specs <- list(c(2,20,4), c(3,30,3), c(2,40,5), c(3,20,4), c(4,15,3), c(3,60,4), c(2,60,6), c(4,30,4), c(5,20,3), c(4,20,5))
cases <- lapply(specs, function(s) mk(s[1], s[2], s[3]))
names(cases) <- sapply(specs, function(s) sprintf("nistCA(%d,%d,%d)", s[1], s[2], s[3]))
set.seed(7)
for (i in 1:40) { N <- sample(10:80, 1); k <- sample(3:12, 1); v <- sample(2:6, 1)
    M <- matrix(sample(0:(v - 1), N * k, TRUE), N, k); M[1:v, ] <- matrix(rep(0:(v - 1), k), v, k); cases[[sprintf("random%d", i)]] <- M[sample(N), ] }
cases[["bush64"]] <- { D <- lhs::createBush(4, 5); storage.mode(D) <- "integer"; D }
cases[["cyc19"]] <- { D <- cyc(19, 2); D <- as.matrix(D); storage.mode(D) <- "integer"; D }
fails <- 0; tot_h <- 0; tot_c <- 0
for (nm in names(cases)) {
    A <- cases[[nm]]; t_use <- if (grepl("nistCA", nm)) as.integer(sub("nistCA\\((\\d).*", "\\1", nm)) else 2L
    th <- system.time(H <- maxconstant(A))[["elapsed"]]
    tc <- system.time(C <- maxconstant_c(A))[["elapsed"]]
    tot_h <- tot_h + th; tot_c <- tot_c + tc
    same_n <- nconst(H) == nconst(C)
    front <- nconst(C) >= 1
    asc <- nconst(C) < 2 || all(diff(C[seq_len(nconst(C)), 1]) > 0)  # holds by definition of nconst; kept as a printed reminder
    equiv <- nrow(C) == nrow(A) && all(sapply(seq_len(ncol(A)), function(j) identical(sort(as.vector(table(A[, j]))), sort(as.vector(table(C[, j]))))))
    cov <- if (grepl("nistCA|bush|cyc", nm)) { r <- ca_verify(C, t_use); isTRUE(r$covered) } else NA
    ok <- same_n && front && asc && equiv && !isFALSE(cov)
    if (!ok) fails <- fails + 1
    cat(sprintf("%-16s %5d x %2d  hers %d front (%d total) %6.2fs   ours %d front (%d total) %6.2fs   asc %s equiv %s covers %s  %s\n",
        nm, nrow(A), ncol(A), nconst(H), ntotal(H), th, nconst(C), ntotal(C), tc, asc, equiv, cov, if (ok) "OK" else "MISMATCH"))
}
for (nm in c("bush64", "cyc19")) { A <- cases[[nm]]; C1 <- maxconstant_c(A, remove = TRUE); C2 <- maxconstant_c(A, one_is_enough = TRUE)
    cat(sprintf("%s: remove=TRUE gives %d rows (was %d); one_is_enough gives %d constant rows\n", nm, nrow(C1), nrow(A), nconst(C2))) }
cat(sprintf("\ncases %d, mismatches %d, total time hers %.1f s, ours %.1f s\n", length(cases), fails, tot_h, tot_c))
cat("MAXCONSTANT TEST DONE\n")
