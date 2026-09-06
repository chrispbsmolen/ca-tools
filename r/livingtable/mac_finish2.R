## mac_finish2.R - finishing run v2. Each row runs in its OWN fresh
## Rscript subprocess with a hard 15-minute external timeout, so a
## hung download kills one row, never the run. Parallelism = several
## subprocesses at once. Resumable; same ledgers.
## Run from r/livingtable/ (paths adjusted for the repository layout):
##   Rscript mac_finish2.R [cap] [workers] | tee -a results/mac_finish_result.txt
## Input: data/ca_reproduction.csv. Ledgers: data/edge_executed_progress.csv,
## data/edge_screen_progress.csv. Per-row files: data/finish_rows/.
suppressMessages(library(parallel))
cap <- as.numeric(commandArgs(TRUE)[1]); if (is.na(cap)) cap <- 1e15
nc  <- as.integer(commandArgs(TRUE)[2])
if (is.na(nc)) nc <- max(1L, detectCores() - 2L)
d <- read.csv("data/ca_reproduction.csv", stringsAsFactors = FALSE)
m <- d[d$status == "MATCH", ]
led <- if (file.exists("data/edge_executed_progress.csv"))
    read.csv("data/edge_executed_progress.csv", stringsAsFactors = FALSE) else NULL
scr <- if (file.exists("data/edge_screen_progress.csv"))
    read.csv("data/edge_screen_progress.csv", stringsAsFactors = FALSE) else NULL
donekey <- c(if (!is.null(led)) paste(led$t, led$k, led$v)[
                 led$note %in% c("EXECUTED", "GAPS_FOUND")],
             if (!is.null(scr)) paste(scr$t, scr$k, scr$v)[
                 grepl("SCREEN4|FAILS", scr$note)])
m <- m[!(paste(m$t, m$k, m$v) %in% donekey), ]
m <- m[order(choose(m$k, m$t) * (m$v ^ m$t) * as.numeric(m$N)), ]
cat(nrow(m), "entries remain; hard 15-min timeout per row,",
    nc, "subprocesses\n")
dir.create("data/finish_rows", showWarnings = FALSE)
one <- function(i) {
    f <- sprintf("data/finish_rows/row_%d_%d_%d.csv", m$t[i], m$k[i], m$v[i])
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
    led <- rbind(led, new[new$ledger == "full", names(led)])
    if (any(new$ledger == "screen"))
        scr <- rbind(scr, new[new$ledger == "screen",
                     c("t","k","v","N_snapshot","N_built","note")])
    write.csv(led, "data/edge_executed_progress.csv", row.names = FALSE)
    if (!is.null(scr)) write.csv(scr, "data/edge_screen_progress.csv", row.names = FALSE)
    ndone <- ndone + length(ch)
    el <- as.numeric(Sys.time() - t0, units = "mins")
    cat(sprintf("progress: %d of %d  elapsed %.1f min  projected %.0f min\n",
        ndone, nrow(m), el, el / ndone * nrow(m)))
}
cat("\nFINISHING RUN DONE\n")
cat("certified:", sum(led$note == "EXECUTED"),
    " failures:", sum(led$note == "GAPS_FOUND"),
    " screened:", if (is.null(scr)) 0 else sum(scr$note == "SCREEN4_PASS"),
    " timeouts/errors to revisit:",
    sum(grepl("^ERR", led$note)), "\n")
