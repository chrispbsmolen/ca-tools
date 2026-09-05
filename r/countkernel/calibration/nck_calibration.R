## As run on 2026-09-05 for the calibration in this directory. Paths
## (living_table/, ca-tools/r/countkernel) refer to the working folder it
## ran from; adjust to run elsewhere. Produces nck_calibration_result.csv/.txt.
## mac_nck_calibration.R - the NCK calibration gate at catalogue scale
## (COUNTING_KERNEL_REGISTRATION.md section 5): her postopNCK versus
## our postopNCK_c on arrays built by her own constructions that carry
## real slack (rows above the best known size), identical parameters,
## many seeds, achieved sizes compared as distributions, every output
## re-verified by caverify after filling flexible cells.
## Pilot-first: her engine is timed on the smallest instance and the
## whole run is projected BEFORE the main loop starts. Checkpointed per
## (instance, engine, seed) in nck_calibration_result.csv; resumable.
## Arrays are built in the parent process (network) before any fork.
## Run from Spectre (alongside the retry pass is fine, it uses no
## network after setup):
##   Rscript living_table/mac_nck_calibration.R [workers] pilot   (projection only)
##   Rscript living_table/mac_nck_calibration.R [workers] | tee -a living_table/nck_calibration_result.txt
suppressMessages({library(CAs); library(caverify); library(parallel)})
args <- commandArgs(TRUE)
smoke <- "smoke" %in% args                 ## sandbox self-test mode
nc <- suppressWarnings(as.integer(args[1])); if (is.na(nc)) nc <- 6L
kdir <- "ca-tools/r/countkernel"
if (!file.exists(file.path(kdir, "nck_faces.so")))
    system(sprintf("cd %s && R CMD SHLIB nck_faces.c", kdir))
oldwd <- setwd(kdir); source("nck_faces.R"); source("nck_driver.R"); setwd(oldwd)
outcsv <- if (smoke) "/tmp/nck_smoke.csv" else "living_table/nck_calibration_result.csv"
pars <- list(outerRetry = 20, innerRetry = 5, innerMaxnochange = 15)
seeds_hers <- 1:5; seeds_ours <- 1:20
if (smoke) { seeds_hers <- 1; seeds_ours <- 1:2; nc <- 2L }

## ---- instance selection: NIST IPOG arrays (fetched by her nistCA) ----
## Survey of 2026-09-04 (sandbox): her catalogue constructions are
## algebraically tight, 0-5% flexible cells, so NCK cannot act on
## them (as the paper predicts for such arrays). NIST's greedy IPOG
## arrays, the paper's own experimental family, carry real slack
## (5 to 88 rows over best known) and 3-17% flexible cells. They are
## the benchmark. Sizes kept where her R engine finishes in minutes.
cands <- rbind(
    expand.grid(t = 2, k = c(10, 15, 20), v = c(3, 4)),
    expand.grid(t = 2, k = 15, v = 5),
    expand.grid(t = 3, k = c(10, 15, 20), v = 2),
    expand.grid(t = 3, k = c(10, 15), v = 3))
inst <- list()
for (i in seq_len(nrow(cands))) {
    t <- cands$t[i]; k <- cands$k[i]; v <- cands$v[i]
    A <- tryCatch(suppressWarnings(suppressMessages(nistCA(t, k, v))),
                  error = function(e) NULL)
    if (is.null(A)) { cat("  (no NIST array fetched for", t, k, v, ")\n"); next }
    A <- as.matrix(A); storage.mode(A) <- "integer"
    if (any(is.na(A))) A[is.na(A)] <- 0L
    best <- tryCatch(eCAN(t, k, v)$CAN[1], error = function(e) NA)
    flex <- mean(is.na(markflex_c(A, t)))
    if (is.na(best) || nrow(A) <= best || flex < 0.02) next
    if (any(apply(A, 2, function(cc) length(unique(cc))) < v)) next
    inst[[length(inst) + 1]] <- list(id = sprintf("nist_t%d_k%d_v%d", t, k, v),
        t = t, k = k, v = v, A = A, N0 = nrow(A), best = best, flex = flex)
}
if (!length(inst)) stop("no instances with slack found")
if (smoke) inst <- inst[seq_len(min(2, length(inst)))]
inst <- inst[order(sapply(inst, function(z) z$N0 * choose(z$k, z$t) * z$v^z$t))]
cat("instances (NIST IPOG array, rows, best known, slack, flexible cell share):\n")
for (z in inst) cat(sprintf("  %-16s N0 = %4d  best = %4d  slack = %3d  flex = %.3f\n",
                            z$id, z$N0, z$best, z$N0 - z$best, z$flex))

valid <- function(A, t, v) {
    B <- as.matrix(A); attributes(B) <- attributes(B)["dim"]
    for (j in seq_len(ncol(B))) { nas <- which(is.na(B[, j]))
        if (length(nas)) B[nas, j] <- min(B[, j], na.rm = TRUE) }
    storage.mode(B) <- "integer"
    r <- tryCatch(ca_verify(B, t, v = v), error = function(e) NULL)
    !is.null(r) && isTRUE(r$covered)
}
run_one <- function(z, engine, s) {
    t0 <- Sys.time()
    if (engine == "hers") {
        r <- NULL
        capture.output(suppressMessages(r <- tryCatch(do.call(postopNCK,
            c(list(z$A, z$t, seed = s), pars)), error = function(e) NULL)))
    } else {
        r <- tryCatch(do.call(postopNCK_c, c(list(z$A, z$t, seed = s), pars)),
                      error = function(e) NULL)
    }
    secs <- as.numeric(Sys.time() - t0, units = "secs")
    data.frame(id = z$id, t = z$t, k = z$k, v = z$v, engine = engine,
        seed = s, N0 = z$N0, best_known = z$best,
        N_final = if (is.null(r)) NA else nrow(r),
        covered = if (is.null(r)) NA else valid(r, z$t, z$v),
        secs = round(secs, 2), stringsAsFactors = FALSE)
}

## ---- pilot: time her engine on the smallest instance, one seed ----
done <- if (file.exists(outcsv)) read.csv(outcsv, stringsAsFactors = FALSE) else NULL
key <- function(d) paste(d$id, d$engine, d$seed)
z1 <- inst[[1]]
cat("\npilot: her postopNCK on", z1$id, "one seed ...\n")
p <- run_one(z1, "hers", 1)
cat(sprintf("  N %d -> %d, covered %s, %.1f s\n", p$N0, p$N_final, p$covered, p$secs))
cost <- sapply(inst, function(z) z$N0 * choose(z$k, z$t) * z$v^z$t)
proj_hers <- p$secs * sum(cost) / cost[1] * length(seeds_hers) / nc
cat(sprintf("projected wall clock for her side (%d seeds x %d instances, %d workers): %.0f min, uncertainty about 3x either way\n",
            length(seeds_hers), length(inst), nc, proj_hers / 60))
cat("our side is expected to be a small fraction of that.\n\n")
if ("pilot" %in% args) { cat("pilot only; rerun without 'pilot' to launch the full run\n"); quit(save = "no") }
if (is.null(done) || !(key(p) %in% key(done))) {
    done <- rbind(done, p); write.csv(done, outcsv, row.names = FALSE) }

## ---- main loop: all (instance, engine, seed) jobs, checkpointed ----
jobs <- do.call(rbind, lapply(inst, function(z) rbind(
    data.frame(id = z$id, engine = "ours", seed = seeds_ours, stringsAsFactors = FALSE),
    data.frame(id = z$id, engine = "hers", seed = seeds_hers, stringsAsFactors = FALSE))))
jobs <- jobs[!(key(jobs) %in% key(done)), ]
cat(nrow(jobs), "jobs remain\n")
byid <- setNames(inst, sapply(inst, function(z) z$id))
chunks <- split(seq_len(nrow(jobs)), ceiling(seq_len(nrow(jobs)) / nc))
t0 <- Sys.time(); ndone <- 0
for (ch in chunks) {
    res <- mclapply(ch, function(i) run_one(byid[[jobs$id[i]]], jobs$engine[i],
                                           jobs$seed[i]), mc.cores = nc)
    res <- do.call(rbind, res)
    done <- rbind(done, res); write.csv(done, outcsv, row.names = FALSE)
    ndone <- ndone + length(ch)
    el <- as.numeric(Sys.time() - t0, units = "mins")
    cat(sprintf("progress: %d of %d jobs  elapsed %.1f min  projected %.0f min\n",
                ndone, nrow(jobs), el, el / ndone * nrow(jobs)))
}

## ---- summary ----
cat("\nCALIBRATION SUMMARY (identical parameters:",
    paste(names(pars), unlist(pars), sep = "=", collapse = ", "), ")\n")
cat(sprintf("%-16s %5s %5s | %-22s | %-22s | %s\n", "instance", "N0", "best",
            "hers mean/min (n)", "ours mean/min (n)", "speed  all-covered"))
allok <- TRUE
for (z in inst) {
    h <- done[done$id == z$id & done$engine == "hers" & !is.na(done$N_final), ]
    o <- done[done$id == z$id & done$engine == "ours" & !is.na(done$N_final), ]
    cov_ok <- all(c(h$covered, o$covered))
    allok <- allok && cov_ok
    cat(sprintf("%-16s %5d %5d | %6.2f / %4d (%2d)      | %6.2f / %4d (%2d)      | %5.0fx  %s\n",
        z$id, z$N0, z$best, mean(h$N_final), min(h$N_final), nrow(h),
        mean(o$N_final), min(o$N_final), nrow(o),
        mean(h$secs) / mean(o$secs), if (cov_ok) "yes" else "NO"))
}
cat(if (allok) "\nevery output of both engines verified covering\n" else
    "\n*** some outputs did NOT cover, inspect the csv ***\n")
cat("CALIBRATION DONE\n")
