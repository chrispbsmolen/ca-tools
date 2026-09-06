## mac_powerct_refix.R - post-fix re-audit of the 14 powerCTcat rows
## the CAs author diagnosed (chi > 0: rows 10, 19, 20, 22, 28-37), which the
## original audit skipped as AUTHOR_DIAGNOSED. Requires the CAs GitHub fix
## installed first (commit d1c6570, 2026-09-04; install the GitHub
## version of CAs from https://github.com/ugroempi/CAs).
## Subprocess per row (powerct_one.R), hard 15-min kill, memory guard,
## checkpointed to data/powerct_refix.csv. Run from r/livingtable/
## (paths adjusted for the repository layout):
##   Rscript mac_powerct_refix.R [cap] [workers] | tee -a results/powerct_refix_result.txt
suppressMessages({library(CAs); library(parallel)})
cap <- as.numeric(commandArgs(TRUE)[1]); if (is.na(cap)) cap <- 1e13
nc  <- as.integer(commandArgs(TRUE)[2]); if (is.na(nc)) nc <- 2L
maxcells <- 2e8
## confirm the installed CAs carries the fix: DHHF2CA must not be the
## pre-fix source (the fixed file mentions the constant-row handling)
src <- deparse(CAs:::DHHF2CA)
cat("installed CAs", as.character(packageVersion("CAs")),
    "; DHHF2CA source lines:", length(src), "\n")
rows <- c(10, 19, 20, 22, 28:37)
cat_ <- CAs::powerCTcat[rows, ]
m <- data.frame(t = cat_$t, k = cat_$k, v = cat_$v, N = cat_$N,
                stringsAsFactors = FALSE)
cat(nrow(m), "author-diagnosed powerCT rows to re-audit with the fixed code\n")
print(m, row.names = FALSE)
big <- as.numeric(m$N) * as.numeric(m$k) > maxcells
if (any(big)) cat(sum(big), "rows exceed the memory guard and are skipped:",
                  paste(sprintf("(%d,%d,%d)", m$t[big], m$k[big], m$v[big]), collapse = " "), "\n")
m <- m[!big, ]
outcsv <- "data/powerct_refix.csv"
done <- if (file.exists(outcsv)) read.csv(outcsv, stringsAsFactors = FALSE) else NULL
key <- function(d) paste(d$t, d$k, d$v)
if (!is.null(done)) m <- m[!(key(m) %in% key(done)), ]
m <- m[order(choose(m$k, m$t) * (m$v ^ m$t) * as.numeric(m$N)), ]
cat(nrow(m), "rows remain\n")
dir.create("data/finish_rows", showWarnings = FALSE)
one <- function(i) {
    f <- sprintf("data/finish_rows/postfix_%d_%d_%d.csv", m$t[i], m$k[i], m$v[i])
    if (file.exists(f)) file.remove(f)
    rc <- system2("Rscript", c("powerct_one.R", m$t[i], m$k[i], m$v[i],
                  m$N[i], format(cap, scientific = TRUE), f),
                  stdout = FALSE, stderr = FALSE, timeout = 900)
    if (!file.exists(f))
        write.csv(data.frame(t=m$t[i],k=m$k[i],v=m$v[i],N_snapshot=m$N[i],
            N_built=NA,verified=NA,size_ok=NA,
            note=if (rc == 124) "ERR: TIMEOUT_KILLED" else paste0("ERR: rc=", rc),
            mode="ERR"), f, row.names = FALSE)
    f
}
if (nrow(m)) {
    chunks <- split(seq_len(nrow(m)), ceiling(seq_len(nrow(m)) / nc))
    t0 <- Sys.time(); ndone <- 0
    for (ch in chunks) {
        fs <- unlist(mclapply(ch, one, mc.cores = nc))
        new <- do.call(rbind, lapply(fs, read.csv))
        print(new[, c("t","k","v","N_snapshot","N_built","note","mode")], row.names = FALSE)
        done <- rbind(done, new); write.csv(done, outcsv, row.names = FALSE)
        ndone <- ndone + length(ch)
        el <- as.numeric(Sys.time() - t0, units = "mins")
        cat(sprintf("progress: %d of %d  elapsed %.1f min\n", ndone, nrow(m), el))
    }
}
cat("\nPOWERCT REFIX DONE\n")
cat("full pass:", sum(done$note == "EXECUTED_POSTFIX"),
    " screen pass:", sum(done$note == "SCREEN4_PASS_POSTFIX"),
    " failures:", sum(grepl("GAPS|FAILS", done$note)),
    " errors:", sum(grepl("^ERR", done$note)), "\n")
