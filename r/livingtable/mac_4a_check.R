## mac_4a_check.R - thorough checks (2026-09-03) of type 4a at the
## two giant faulty-3a field sizes. The CAs author's sample checks
## show no violations; this goes much further: for each of
## q=2161 (v=20) and q=2311 (v=21), build cyc(q, v, type="4a") and
## screen with head/tail 50-column windows, 40 random 50-column
## windows, and 6 random 150-column windows, every window fully
## verified by caverify at t=3. (Full verification at these sizes
## is infeasible anywhere; this is the strongest feasible tier and
## is reported as such.) Expected sizes: vq + v, i.e. 43,240 and
## 48,552. Run from r/livingtable/ (paths adjusted for the repository layout):
##   Rscript mac_4a_check.R | tee results/mac_4a_result.txt
suppressMessages({library(CAs); library(caverify)})
set.seed(20260903)
ns <- asNamespace("CAs")
for (p in list(c(2161, 20), c(2311, 21))) {
    q <- p[1]; v <- p[2]
    cat("== q =", q, " v =", v, " type 4a ==\n")
    t0 <- Sys.time()
    A <- eval(parse(text = sprintf("cyc(%d, %d, type=\"4a\")", q, v)),
              envir = ns)
    A <- as.matrix(A); storage.mode(A) <- "integer"
    cat("built", nrow(A), "x", ncol(A), "(expected", v * q + v, "rows ) in",
        round(as.numeric(Sys.time() - t0, units = "mins"), 1), "min\n")
    k <- ncol(A)
    wins <- c(list(head = 1:50, tail = (k - 49):k),
              setNames(lapply(1:40, function(i) sort(sample(k, 50))),
                       paste0("r50_", 1:40)),
              setNames(lapply(1:6, function(i) sort(sample(k, 150))),
                       paste0("r150_", 1:6)))
    nfail <- 0
    for (i in seq_along(wins)) {
        r <- tryCatch(ca_verify(A[, wins[[i]], drop = FALSE], 3, v = v),
                      error = function(e) NULL)
        ok <- !is.null(r) && isTRUE(r$covered)
        if (!ok) { nfail <- nfail + 1
            cat("*** WINDOW FAILS:", names(wins)[i], "\n") }
        if (i %% 12 == 0) cat("  ...", i, "of", length(wins), "windows\n")
    }
    cat("windows passed:", length(wins) - nfail, "of", length(wins),
        if (nfail == 0) " ALL PASS\n\n" else " FAILURES ABOVE\n\n")
}
cat("4A CHECK DONE\n")
