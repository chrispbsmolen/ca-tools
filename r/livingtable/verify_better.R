## verify_better.R - construct and fully verify the feasible BETTER
## entries. Each success upgrades an arithmetic claim to a certified
## one: the CAs implemented route really produces a smaller array than
## the frozen snapshot records, and the array really covers.
## Input: data/ca_reproduction.csv. Output: data/better_verified.csv.
## Run from r/livingtable/ (paths adjusted for the repository layout).
suppressMessages({library(CAs); library(caverify)})
d <- read.csv("data/ca_reproduction.csv")
b <- d[d$status == "BETTER" & d$k <= 400 & d$best_impl <= 10000, ]
b <- b[order(b$k * b$best_impl), ]
resfile <- "data/better_verified.csv"
done <- if (file.exists(resfile)) read.csv(resfile) else NULL
for (i in seq_len(nrow(b))) {
    t <- b$t[i]; k <- b$k[i]; v <- b$v[i]; Nrec <- b$N[i]; Nimp <- b$best_impl[i]
    if (!is.null(done) && any(done$t==t & done$k==k & done$v==v)) next
    ns <- suppressWarnings(suppressMessages(Ns(t, k, v)))
    impl <- ns[setdiff(names(ns), "eCAN")]; impl <- impl[is.finite(impl)]
    route <- names(impl)[which.min(impl)]
    cat(sprintf("[%d/%d] t=%d k=%d v=%d  snapshot %d -> %d via %s ... ",
                i, nrow(b), t, k, v, Nrec, Nimp, route))
    A <- tryCatch(suppressWarnings(suppressMessages(
             bestCA(t, k, v, seed = 20260829))),
         error = function(e) e)
    if (inherits(A, "error")) {
        cat("CONSTRUCT_FAIL:", conditionMessage(A), "\n")
        row <- data.frame(t=t,k=k,v=v,N_snapshot=Nrec,N_impl=Nimp,route=route,
                          N_built=NA, verified=FALSE, note="construct failed")
    } else {
        A <- as.matrix(A); storage.mode(A) <- "integer"
        Nb <- nrow(A)
        r <- tryCatch(ca_verify(A, t, v = v), error = function(e) e)
        ok <- !inherits(r, "error") && isTRUE(r$covered)
        cat("built N=", Nb, if (ok) " VERIFIED" else " NOT covered/err", "\n", sep = "")
        row <- data.frame(t=t,k=k,v=v,N_snapshot=Nrec,N_impl=Nimp,route=route,
                          N_built=Nb, verified=ok,
                          note=if (ok) sprintf("margin %d", Nrec-Nb) else
                               if (inherits(r,"error")) conditionMessage(r) else "gaps")
    }
    done <- rbind(done, row); write.csv(done, resfile, row.names = FALSE)
}
cat("\nsummary:\n"); print(done[, c("t","k","v","N_snapshot","N_built","verified","route")], row.names=FALSE)
cat("verified count:", sum(done$verified, na.rm=TRUE), "of", nrow(done), "\n")
