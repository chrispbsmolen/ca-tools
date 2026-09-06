## mac_finish3.R - screen-tier pass over the timeout pile from the
## finishing run. Same subprocess-per-row architecture as
## mac_finish2.R (hard 15-min external kill per row), but the cost
## cap defaults LOW (1e13, roughly 10 seconds of full-verify work)
## so the heavy rows drop to finish_one.R's window-screen tier
## instead of attempting full verification they cannot finish in
## 15 minutes. Targets only rows whose latest ledger note is ERR.
## finish_one.R passes maxN = Inf to bestCA, and rows too large to
## build inside 15 min stay ERR, labeled with the reason.
## Writes fresh retry_*.csv files so stale row_*.csv files from the
## timed-out attempts can never be read back by mistake. When a row
## resolves, its old ERR entries are pruned from the full ledger.
## Run from r/livingtable/ (paths adjusted for the repository layout):
##   Rscript mac_finish3.R [cap] [workers] [maxcells] | tee -a results/mac_finish3_result.txt
## Ledgers: data/edge_executed_progress.csv, data/edge_screen_progress.csv.
## Per-row files: data/finish_rows/.
suppressMessages(library(parallel))
cap <- as.numeric(commandArgs(TRUE)[1]); if (is.na(cap)) cap <- 1e13
nc  <- as.integer(commandArgs(TRUE)[2])
if (is.na(nc)) nc <- max(1L, detectCores() - 2L)
led <- read.csv("data/edge_executed_progress.csv", stringsAsFactors = FALSE)
scr <- if (file.exists("data/edge_screen_progress.csv"))
    read.csv("data/edge_screen_progress.csv", stringsAsFactors = FALSE) else NULL
key <- function(d) paste(d$t, d$k, d$v)
donekey <- c(key(led)[led$note %in% c("EXECUTED", "GAPS_FOUND")],
             if (!is.null(scr)) key(scr)[grepl("SCREEN4|FAILS", scr$note)])
## stale ERR rows for keys that already have a real result are noise
led <- led[!(grepl("^ERR", led$note) & key(led) %in% donekey), ]
m <- led[grepl("^ERR", led$note) & !(key(led) %in% donekey),
         c("t", "k", "v", "N_snapshot")]
m <- m[!duplicated(paste(m$t, m$k, m$v)), ]
names(m)[4] <- "N"
## MEMORY GUARD (added 2026-09-04 after the retry pass exhausted the
## workstation's 128 GB and froze it): an array's footprint in R is roughly
## N x k x 4 bytes, and the CAs constructions hold several working copies.
## Any row whose bare array would exceed maxcells cells (default 2e8,
## about 0.8 GB bare, a few GB in practice) is NOT attempted; it is
## written to the ledger as ERR: TOO_LARGE_FOR_THIS_MACHINE, which is
## an honest tier, not a failure of the sweep.
maxcells <- as.numeric(commandArgs(TRUE)[3]); if (is.na(maxcells)) maxcells <- 2e8
big <- as.numeric(m$N) * as.numeric(m$k) > maxcells
if (any(big)) {
    cat(sum(big), "rows exceed the memory guard (", format(maxcells, scientific = TRUE),
        "cells ) and are recorded as TOO_LARGE_FOR_THIS_MACHINE, not attempted\n")
    tl <- data.frame(t = m$t[big], k = m$k[big], v = m$v[big], N_snapshot = m$N[big],
        N_built = NA, verified = NA, size_ok = NA,
        note = "ERR: TOO_LARGE_FOR_THIS_MACHINE", stringsAsFactors = FALSE)
    led <- led[!(grepl("^ERR", led$note) & key(led) %in% key(tl)), ]
    led <- rbind(led, tl[, names(led)])
    write.csv(led, "data/edge_executed_progress.csv", row.names = FALSE)
    m <- m[!big, ]
}
m <- m[order(choose(m$k, m$t) * (m$v ^ m$t) * as.numeric(m$N)), ]
cat(nrow(m), "timeout rows to retry at screen tier; cap",
    format(cap, scientific = TRUE), ";", nc, "subprocesses\n")
dir.create("data/finish_rows", showWarnings = FALSE)
one <- function(i) {
    f <- sprintf("data/finish_rows/retry_%d_%d_%d.csv", m$t[i], m$k[i], m$v[i])
    if (file.exists(f)) file.remove(f)
    rc <- system2("Rscript", c("finish_one.R", m$t[i], m$k[i], m$v[i],
                  m$N[i], format(cap, scientific = TRUE), f),
                  stdout = FALSE, stderr = FALSE, timeout = 900)
    if (!file.exists(f))
        write.csv(data.frame(t=m$t[i],k=m$k[i],v=m$v[i],
            N_snapshot=m$N[i],N_built=NA,verified=NA,size_ok=NA,
            note=if (rc == 124) "ERR: TIMEOUT_KILLED" else
                 paste0("ERR: subprocess rc=", rc), ledger="full"),
            f, row.names = FALSE)
    f
}
chunks <- split(seq_len(nrow(m)), ceiling(seq_len(nrow(m)) / nc))
t0 <- Sys.time(); ndone <- 0
for (ch in chunks) {
    fs <- unlist(mclapply(ch, one, mc.cores = nc))
    new <- do.call(rbind, lapply(fs, read.csv))
    f <- new[grepl("GAPS|FAILS", new$note), ]
    if (nrow(f)) { cat("*** FAILURE:\n"); print(f[,1:7], row.names = FALSE) }
    ## every attempted key's old ERR rows are superseded by this
    ## attempt's row, whatever its outcome (no duplicate ERR rows)
    led <- led[!(grepl("^ERR", led$note) & key(led) %in% key(new)), ]
    led <- rbind(led, new[new$ledger == "full", names(led)])
    if (any(new$ledger == "screen")) {
        add <- new[new$ledger == "screen",
                   c("t","k","v","N_snapshot","N_built","note")]
        scr <- if (is.null(scr)) add else rbind(scr, add)
    }
    write.csv(led, "data/edge_executed_progress.csv", row.names = FALSE)
    if (!is.null(scr)) write.csv(scr, "data/edge_screen_progress.csv", row.names = FALSE)
    ndone <- ndone + length(ch)
    el <- as.numeric(Sys.time() - t0, units = "mins")
    cat(sprintf("progress: %d of %d  elapsed %.1f min  projected %.0f min\n",
        ndone, nrow(m), el, el / ndone * nrow(m)))
}
cat("\nRETRY PASS DONE\n")
cat("certified:", sum(led$note == "EXECUTED"),
    " failures:", sum(led$note == "GAPS_FOUND"),
    " screened:", if (is.null(scr)) 0 else sum(scr$note == "SCREEN4_PASS"),
    " still unresolved:", sum(grepl("^ERR", led$note)), "\n")
