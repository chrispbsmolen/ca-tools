## finish_one.R - single-row worker for the finishing run. Fresh
## process per row, so downloads cannot deadlock any sibling.
## Args: t k v N cap outfile   (called by mac_finish2.R / mac_finish3.R
## from r/livingtable/; outfile is given by the caller)
suppressMessages({library(CAs); library(caverify)})
a <- commandArgs(TRUE)
t <- as.integer(a[1]); k <- as.integer(a[2]); v <- as.integer(a[3])
N <- as.integer(a[4]); cap <- as.numeric(a[5]); outfile <- a[6]
set.seed(20260901)
heavy <- choose(k, t) * (v ^ t) * as.numeric(N) > cap
res <- tryCatch({
    A <- suppressWarnings(suppressMessages(bestCA(t, k, v, seed = 20260829,
                                                  maxN = Inf)))
    A <- as.matrix(A); storage.mode(A) <- "integer"
    if (!heavy) {
        r <- ca_verify(A, t, v = v)
        data.frame(t=t,k=k,v=v,N_snapshot=N,N_built=nrow(A),
            verified=isTRUE(r$covered), size_ok=(nrow(A) <= N),
            note=if (isTRUE(r$covered)) "EXECUTED" else "GAPS_FOUND",
            ledger="full")
    } else {
        ## k <= 50: the 'window' is the whole array, so this is a
        ## single full verification, labeled as such (clarified 2026-09-04)
        wins <- if (k <= 50) list(1:k) else
            list(1:50, (k - 49):k, sort(sample(k, 50)), sort(sample(k, 50)))
        ok <- TRUE; verr <- NULL
        for (w in wins) {
            r <- tryCatch(ca_verify(A[, w, drop = FALSE], t, v = v),
                          error = function(e) e)
            if (inherits(r, "error")) { verr <- r; break }   ## error != gap
            if (!isTRUE(r$covered)) { ok <- FALSE; break } }
        if (!is.null(verr)) stop("verify error: ", conditionMessage(verr))
        data.frame(t=t,k=k,v=v,N_snapshot=N,N_built=nrow(A),
            verified=if (k <= 50) ok else NA, size_ok=(nrow(A) <= N),
            note=if (k <= 50) (if (ok) "EXECUTED" else "GAPS_FOUND") else
                 (if (ok) "SCREEN4_PASS" else "FAILS(screen)"),
            ledger=if (k <= 50) "full" else "screen")
    }
}, error = function(e)
    data.frame(t=t,k=k,v=v,N_snapshot=N,N_built=NA,verified=NA,size_ok=NA,
        note=paste0("ERR: ", substr(conditionMessage(e), 1, 50)),
        ledger="full"))
write.csv(res, outfile, row.names = FALSE)
