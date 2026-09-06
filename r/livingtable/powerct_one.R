## powerct_one.R - single-row worker for the post-fix powerCT re-audit.
## Builds the array with powerCA(t, k, v) from the INSTALLED CAs (must
## include the 2026-09-04 GitHub fix, commit d1c6570 or later), then either
## verifies in full (cost <= cap) or screens 4 column windows whose
## width shrinks with t so t=6 giants stay within minutes.
## Args: t k v N cap outfile   (called by mac_powerct_refix.R from
## r/livingtable/; outfile is given by the caller)
suppressMessages({library(CAs); library(caverify)})
a <- commandArgs(TRUE)
t <- as.integer(a[1]); k <- as.integer(a[2]); v <- as.integer(a[3])
N <- as.integer(a[4]); cap <- as.numeric(a[5]); outfile <- a[6]
set.seed(20260905)
res <- tryCatch({
    A <- suppressWarnings(suppressMessages(powerCA(t, k, v)))
    A <- as.matrix(A); storage.mode(A) <- "integer"
    if (any(is.na(A))) A[is.na(A)] <- 0L
    heavy <- choose(k, t) * (v ^ t) * as.numeric(nrow(A)) > cap
    if (!heavy) {
        r <- ca_verify(A, t, v = v)
        data.frame(t=t,k=k,v=v,N_snapshot=N,N_built=nrow(A),
            verified=isTRUE(r$covered), size_ok=(nrow(A) <= N),
            note=if (isTRUE(r$covered)) "EXECUTED_POSTFIX" else "GAPS_FOUND_POSTFIX",
            mode="FULL")
    } else {
        w <- c(50, 50, 50, 40, 30, 25)[min(t, 6)]
        w <- min(w, k)
        wins <- list(1:w, (k - w + 1):k, sort(sample(k, w)), sort(sample(k, w)))
        ok <- TRUE; verr <- NULL
        for (win in wins) {
            r <- tryCatch(ca_verify(A[, win, drop = FALSE], t, v = v),
                          error = function(e) e)
            if (inherits(r, "error")) { verr <- r; break }
            if (!isTRUE(r$covered)) { ok <- FALSE; break } }
        if (!is.null(verr)) stop("verify error: ", conditionMessage(verr))
        data.frame(t=t,k=k,v=v,N_snapshot=N,N_built=nrow(A),
            verified=NA, size_ok=(nrow(A) <= N),
            note=if (ok) "SCREEN4_PASS_POSTFIX" else "FAILS(screen)_POSTFIX",
            mode=sprintf("SCREEN4_w%d", w))
    }
}, error = function(e)
    data.frame(t=t,k=k,v=v,N_snapshot=N,N_built=NA,verified=NA,size_ok=NA,
        note=paste0("ERR: ", substr(conditionMessage(e), 1, 60)), mode="ERR"))
write.csv(res, outfile, row.names = FALSE)
