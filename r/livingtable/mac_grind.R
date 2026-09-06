## mac_grind.R - certification grind, workstation edition. Builds and FULLY
## verifies every remaining reproducible entry (no screens here,
## this is certification). Bounded: rows whose verification cost
## exceeds the budget are marked DEFER_HEAVY, not attempted.
## Parallel, checkpointed per chunk, resumes cleanly, prints any
## coverage failure immediately.
## Run from r/livingtable/ (paths adjusted for the repository layout):
##   Rscript mac_grind.R [cost_cap] [workers] | tee results/mac_grind_result.txt
## Input: data/ca_reproduction.csv. Ledger: data/edge_executed_progress.csv.
suppressMessages({library(CAs); library(caverify); library(parallel)})
d <- read.csv("data/ca_reproduction.csv")
m <- d[d$status == "MATCH", ]
resfile <- "data/edge_executed_progress.csv"
done <- if (file.exists(resfile)) read.csv(resfile) else NULL
if (!is.null(done)) done <- done[done$note != "DEFER_HEAVY", ]  ## always retry deferrals
if (!is.null(done))
    m <- m[!(paste(m$t, m$k, m$v) %in% paste(done$t, done$k, done$v)), ]
cost <- choose(m$k, m$t) * (m$v ^ m$t) * as.numeric(m$N)
m <- m[order(cost), ]; cost <- sort(cost)
COST_CAP <- as.numeric(commandArgs(TRUE)[1])
if (is.na(COST_CAP)) COST_CAP <- 1e15   ## ~10-15 min single-thread per row
cat(nrow(m), "entries remaining;", sum(cost > COST_CAP), "beyond cost cap (deferred)\n")
one <- function(i) {
    t <- m$t[i]; k <- m$k[i]; v <- m$v[i]; N <- m$N[i]
    if (choose(k, t) * (v ^ t) * as.numeric(N) > COST_CAP)
        return(data.frame(t=t,k=k,v=v,N_snapshot=N,N_built=NA,verified=NA,
                          size_ok=NA, note="DEFER_HEAVY"))
    out <- tryCatch({
        setTimeLimit(elapsed = 300, transient = TRUE)
        A <- suppressWarnings(suppressMessages(bestCA(t, k, v, seed = 20260829)))
        setTimeLimit(elapsed = Inf)
        A <- as.matrix(A); storage.mode(A) <- "integer"
        r <- ca_verify(A, t, v = v)
        data.frame(t=t,k=k,v=v,N_snapshot=N,N_built=nrow(A),
                   verified=isTRUE(r$covered), size_ok=(nrow(A) <= N),
                   note=if (isTRUE(r$covered)) "EXECUTED" else "GAPS_FOUND")
    }, error = function(e) { setTimeLimit(elapsed = Inf)
        data.frame(t=t,k=k,v=v,N_snapshot=N,N_built=NA,verified=NA,size_ok=NA,
                   note=paste0("ERR: ", substr(conditionMessage(e), 1, 60))) })
    out
}
nc <- as.integer(commandArgs(TRUE)[2])
if (is.na(nc)) nc <- max(1L, detectCores() - 2L)
chunks <- split(seq_len(nrow(m)), ceiling(seq_len(nrow(m)) / nc))
for (ch in chunks) {
    out <- mclapply(ch, one, mc.cores = nc)
    bad <- sapply(out, function(x) !is.data.frame(x))
    for (j in which(bad)) out[[j]] <- one(ch[j])
    new <- do.call(rbind, out)
    f <- new[new$note == "GAPS_FOUND", ]
    if (nrow(f)) { cat("*** COVERAGE FAILURE:\n"); print(f, row.names = FALSE) }
    done <- rbind(done, new)
    write.csv(done, resfile, row.names = FALSE)
    cat("progress:", nrow(done), "total;",
        sum(done$verified %in% TRUE), "certified;",
        sum(done$note == "GAPS_FOUND"), "failures;",
        sum(done$note == "DEFER_HEAVY"), "deferred\n")
}
cat("\nGRIND DONE\n")
