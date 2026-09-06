## mac_powerct_audit.R - blast-radius audit of the powerCT family,
## same design as the cyclotomy audit: full verification where
## cheap, 4-window screens where heavy. Run AFTER the grind (both
## want all cores). From r/livingtable/ (paths adjusted for the
## repository layout):
##   Rscript mac_powerct_audit.R [workers] | tee results/powerct_audit_result.txt
## Checkpoint/output: data/powerct_audit.csv (not shipped: the audit
## was interrupted before completion, see README.md).
suppressMessages({library(CAs); library(caverify); library(parallel)})
set.seed(20260831)
data(powerCTcat)
pc <- powerCTcat
## The CAs author (2026-08-31) diagnosed a DHHF2CA constant-row bug affecting
## the chi>0 rows (catalogue rows 10, 19, 20, 22, 28-37). Screens
## cannot adjudicate this sparse defect class and a code-level
## diagnosis outranks sampling, so those rows are SKIPPED here and
## tiered AUTHOR_DIAGNOSED pending the upstream fix and re-verification
## (done: mac_powerct_refix.R).
aff <- c(10, 19, 20, 22, 28:37)
pc$row_id <- seq_len(nrow(pc))
pc <- pc[-aff, ]
cat(nrow(pc), "powerCTcat rows to audit (14 author-diagnosed rows skipped)\n")
screen4 <- function(A, t, v) {
    k <- ncol(A)
    wins <- list(head = 1:min(50, k), tail = max(1, k - 49):k)
    if (k > 50) { wins$rand1 <- sort(sample(k, 50)); wins$rand2 <- sort(sample(k, 50)) }
    for (w in names(wins)) {
        r <- tryCatch(ca_verify(A[, wins[[w]], drop = FALSE], t, v = v),
                      error = function(e) NULL)
        if (is.null(r) || !isTRUE(r$covered)) return(w)
    }
    "pass"
}
one <- function(i) {
    t <- pc$t[i]; k <- pc$k[i]; v <- pc$v[i]; N <- pc$N[i]
    A <- tryCatch({ setTimeLimit(elapsed = 240, transient = TRUE)
                    suppressWarnings(suppressMessages(powerCA(t, k, v))) },
                  error = function(e) e)
    setTimeLimit(elapsed = Inf)
    if (inherits(A, "error"))
        return(data.frame(t=t,k=k,v=v,N=N,Source=pc$Source[i],
                          mode="none", result=paste0("construct err: ",
                          substr(conditionMessage(A), 1, 40))))
    A <- as.matrix(A); storage.mode(A) <- "integer"
    full_cost <- choose(k, t) * (v ^ t) * as.numeric(nrow(A))
    if (full_cost <= 5e13) {
        r <- tryCatch(ca_verify(A, t, v = v), error = function(e) NULL)
        ok <- !is.null(r) && isTRUE(r$covered)
        data.frame(t=t,k=k,v=v,N=N,Source=pc$Source[i], mode="FULL",
                   result=if (ok) "pass" else
                       sprintf("FAILS gaps=%d", if (!is.null(r)) r$gaps else -1))
    } else {
        w <- screen4(A, t, v)
        data.frame(t=t,k=k,v=v,N=N,Source=pc$Source[i], mode="SCREEN4",
                   result=if (w == "pass") "pass" else paste("FAILS at", w))
    }
}
nc <- as.integer(commandArgs(TRUE)[1])
if (is.na(nc)) nc <- max(1L, detectCores() - 2L)
res <- if (file.exists("data/powerct_audit.csv"))
    read.csv("data/powerct_audit.csv") else NULL
if (!is.null(res)) {
    donekeys <- paste(res$t, res$k, res$v)
    pc <- pc[!(paste(pc$t, pc$k, pc$v) %in% donekeys), ]
    cat(nrow(pc), "rows remain after checkpoint\n")
}
chunks <- split(seq_len(nrow(pc)), ceiling(seq_len(nrow(pc)) / nc))
for (ch in chunks) {
    out <- mclapply(ch, one, mc.cores = nc)
    bad <- sapply(out, function(x) !is.data.frame(x))
    for (j in which(bad)) out[[j]] <- one(ch[j])
    res <- rbind(res, do.call(rbind, out))
    write.csv(res, "data/powerct_audit.csv", row.names = FALSE)
    f <- res[grepl("^FAILS", res$result), ]
    cat("progress:", nrow(res), "of", nrow(pc), " failures:", nrow(f), "\n")
    if (nrow(f)) print(tail(f, 3), row.names = FALSE)
}
cat("\nPOWERCT AUDIT DONE\n")
f <- res[grepl("^FAILS", res$result), ]
cat(nrow(res), "rows;", sum(res$result == "pass"), "pass;", nrow(f), "FAIL\n")
if (nrow(f)) print(f, row.names = FALSE)
