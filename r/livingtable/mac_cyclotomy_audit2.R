## mac_cyclotomy_audit2.R - bounded cyclotomy audit, replaces the
## unbounded first version (which hit multi-hour rows). Strategy:
##   cheap rows  -> FULL verification (certification-grade)
##   heavy rows  -> 50-column SCREEN (defect-finding grade: a screen
##                  failure proves the construction broken; a screen
##                  pass is NOT a full certificate and is marked so)
## Parallel across rows, resumes from its own checkpoint.
## Run from r/livingtable/ (paths adjusted for the repository layout):
##   Rscript mac_cyclotomy_audit2.R | tee results/cyclotomy_audit2_result.txt
## Checkpoint/output: data/cyclotomy_audit2.csv (shipped, with the
## result log in results/).
suppressMessages({library(CAs); library(caverify); library(parallel)})
data(CYCLOTOMYcat)
cc <- CYCLOTOMYcat
FULL_LIMIT <- 5e9        ## colsets x tuple-space budget for full verify
resfile <- "data/cyclotomy_audit2.csv"
prev <- if (file.exists(resfile)) read.csv(resfile) else NULL
one <- function(i) {
    t <- cc$t[i]; k <- cc$k[i]; v <- cc$v[i]; N <- cc$N[i]
    A <- tryCatch({ setTimeLimit(elapsed = 90, transient = TRUE)
                    suppressWarnings(suppressMessages(cyclotomyCA(t, k, v))) },
                  error = function(e) e)
    setTimeLimit(elapsed = Inf)
    if (inherits(A, "error"))
        return(data.frame(t=t,k=k,v=v,N=N,type=cc$type[i],q=cc$q[i],
                          mode="none", ok=NA, note="construct err"))
    A <- as.matrix(A); storage.mode(A) <- "integer"
    full_cost <- choose(k, t) * (v ^ t)
    if (full_cost <= FULL_LIMIT) { mode <- "FULL"; ksub <- k }
    else { mode <- "SCREEN50"; ksub <- min(k, 50) }
    Ax <- A[, seq_len(ksub), drop = FALSE]
    r <- tryCatch(ca_verify(Ax, t, v = v), error = function(e) NULL)
    ok <- !is.null(r) && isTRUE(r$covered)
    data.frame(t=t,k=k,v=v,N=N,type=cc$type[i],q=cc$q[i],
               mode=mode, ok=ok,
               note=if (ok) mode else paste0("FAILS(", mode, ")"))
}
todo <- seq_len(nrow(cc))
if (!is.null(prev))
    todo <- todo[!(paste(cc$t, cc$k, cc$v) %in% paste(prev$t, prev$k, prev$v))]
cat(length(todo), "rows to audit (", nrow(cc) - length(todo), "already done )\n")
nc <- max(1L, detectCores() - 2L)
chunks <- split(todo, ceiling(seq_along(todo) / (nc * 2)))
res <- prev
for (ch in chunks) {
    out <- mclapply(ch, one, mc.cores = nc)
    bad <- sapply(out, function(x) !is.data.frame(x))
    for (j in which(bad)) out[[j]] <- one(ch[j])
    res <- rbind(res, do.call(rbind, out))
    write.csv(res, resfile, row.names = FALSE)
    f <- res[grepl("^FAILS", res$note), ]
    cat("progress:", nrow(res), "of", nrow(cc),
        " failures so far:", nrow(f), "\n")
}
cat("\nDONE.", nrow(res), "rows;",
    sum(res$ok %in% TRUE), "pass;",
    sum(res$ok %in% FALSE), "FAIL;",
    sum(is.na(res$ok)), "construct-err\n")
cat("full certifications:", sum(res$mode == "FULL" & res$ok %in% TRUE),
    "  screens passed:", sum(res$mode == "SCREEN50" & res$ok %in% TRUE), "\n")
f <- res[res$ok %in% FALSE, ]
if (nrow(f)) { cat("ALL FAILING ROWS:\n"); print(f[, 1:8], row.names = FALSE) }
