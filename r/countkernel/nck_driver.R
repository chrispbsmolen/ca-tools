## nck_driver.R - postopNCK_c, the fast NCK post-optimizer driver.
## The Nayeri/Colbourn/Konjevod algorithm as implemented in
## CAs::postopNCK (read at source, 2026-09-04), with these
## deliberate deviations, agreed with the CAs author in advance:
##   D3 fills in the array's own coding (internally 0-based),
##   D4 corrected exhausted-row bookkeeping (explicit vector,
##      exhausted rows kept at the top, frozen count = their number,
##      instead of the contiguity-assuming index arithmetic),
##   D5 seeds reproduce THIS driver's runs, not postopNCK's,
##   D6 silent by default (verbose >= 1 restores progress lines),
## and two features from the paper, both agreed:
##   timeBudget (seconds): wall-clock stopping rule; on expiry the
##     best array found so far is returned with attr "timeout",
##   restarts: after outerMaxnochange unchanged outer rounds, up to
##     this many full random refill-and-remark restarts from the
##     current best before giving up (0 = postopNCK's stopping behavior).
## Interrupting with ESC returns the best array found so far with
## attr "interrupt".
## Further deviations from CAs::postopNCK, found in review and kept
## deliberately:
##   D7 an inner pass that removes nothing hands its perturbed
##      (shuffled, refilled, remarked) array forward instead of
##      returning the input as postopNCK does; measured slightly better
##      on random CAs (e.g. 13.00 vs 13.47 mean rows, k=7 v=3 t=2).
##   D8 the retry restructure freezes exactly the exhausted rows;
##      postopNCK freezes through the last exhausted index, which
##      in practice freezes every flexible-bearing row too.
##   The pick offset pick + sum(exhausted[1:pick]) in postopNCK_one,
##   which can land on a fixed row when fixrows > 0, is replaced by
##   the explicit vector; sample() is guarded against a length-1 set
##   (R would draw from 1:x), a hazard not observed to fire in
##   postopNCK_one itself.
## So: same algorithm, listed deviations, calibrated against
## CAs::postopNCK by distribution of achieved sizes (see
## calibration/), not by trajectory.
## Load after nck_faces.R:  source("nck_faces.R"); source("nck_driver.R")

## one inner pass; x is 0-based and ALREADY MARKED; ex is the
## exhausted flags aligned with x's rows (fixed prefix included).
## Returns list(x, removed, timeout).
.nck_one0 <- function(x, t, vs, fixrows, innerRetry, innerMaxnochange,
                      deadline, verbose = 0) {
    k <- ncol(x); N <- nrow(x)
    hilf <- rowSums(is.na(x))
    toremove <- which(hilf >= k - (t - 1))
    if (length(toremove))
        return(list(x = x[-toremove, , drop = FALSE],
                    removed = length(toremove), timeout = FALSE))
    ex <- rep(FALSE, N)
    if (fixrows > 0) ex[seq_len(fixrows)] <- TRUE
    for (r in seq_len(innerRetry)) {
        if (Sys.time() >= deadline)
            return(list(x = x, removed = 0, timeout = TRUE))
        if (verbose >= 2) cat("  inner retry:", r, "\n")
        count <- 0
        lastmax <- max(hilf)
        cand <- which(!ex)
        if (!length(cand)) break
        pick <- cand[which.max(hilf[cand])]
        repeat {
            ## reorder: exhausted first (stable), shuffled others, pick last
            others <- setdiff(which(!ex), pick)
            ord <- c(which(ex), if (length(others) > 1) sample(others)
                     else others, pick)
            x <- x[ord, , drop = FALSE]; ex <- ex[ord]
            ## fills: columns where the pick (now last) is concrete get
            ## its value; columns where it is flexible get random draws
            flexlast <- which(is.na(x[N, ]))
            for (j in setdiff(seq_len(k), flexlast)) {
                nas <- which(is.na(x[, j]))
                if (length(nas)) x[nas, j] <- x[N, j]
            }
            for (j in flexlast) {
                nas <- which(is.na(x[, j]))
                x[nas, j] <- sample(0:(vs[j] - 1L), length(nas),
                                    replace = TRUE)
            }
            ## remark with the exhausted block frozen at the top
            mk <- .markflex0(x, t, vs, fixrows = sum(ex))
            x <- mk$x; ex <- ex[mk$ord]
            hilf <- rowSums(is.na(x))
            pick <- N        ## postopNCK's rule: keep targeting the row sorted last
            curmax <- hilf[N]
            if (curmax <= lastmax) count <- count + 1
            else { lastmax <- curmax; count <- 0 }
            toremove <- which(hilf >= k - (t - 1))
            if (length(toremove))
                return(list(x = x[-toremove, , drop = FALSE],
                            removed = length(toremove), timeout = FALSE))
            if (count > innerMaxnochange) break
            if (Sys.time() >= deadline)
                return(list(x = x, removed = 0, timeout = TRUE))
        }
        ## retry restructure (postopNCK's between-retry reset, the paper's
        ## stall escape): the current last row becomes exhausted,
        ## flexible-bearing rows move up (behind the exhausted
        ## block), every remaining NA is refilled at random, remark
        ex[N] <- TRUE
        flexrows <- setdiff(which(hilf > 0), which(ex))
        ord <- c(which(ex), flexrows,
                 setdiff(which(!ex), flexrows))
        x <- x[ord, , drop = FALSE]; ex <- ex[ord]
        for (j in seq_len(k)) {
            nas <- which(is.na(x[, j]))
            if (length(nas)) x[nas, j] <- sample(0:(vs[j] - 1L),
                                                 length(nas), replace = TRUE)
        }
        mk <- .markflex0(x, t, vs, fixrows = sum(ex))
        x <- mk$x; ex <- ex[mk$ord]
        hilf <- rowSums(is.na(x))
    }
    list(x = x, removed = 0, timeout = FALSE)
}

postopNCK_c <- function(D, t, fixrows = 0, outerRetry = 50,
                        outerMaxnochange = 10, innerRetry = 10,
                        innerMaxnochange = 25, seed = NULL,
                        timeBudget = Inf, restarts = 0, verbose = 0) {
    nz <- .nck_norm(D)
    x <- nz$x; vs <- nz$vs; shift <- nz$shift
    N0 <- nrow(x); k <- ncol(x)
    if (t > k) stop("t cannot exceed the number of columns")
    if (!is.numeric(fixrows) || length(fixrows) != 1 || fixrows < 0 ||
        fixrows > N0 || fixrows != floor(fixrows))
        stop("fixrows must be a single integer between 0 and nrow(D)")
    ## the driver's fills draw from 0..vs-1, so every level must be
    ## present in its column (true for any covering array)
    for (j in seq_len(k)) {
        present <- unique(x[, j]); present <- present[!is.na(present)]
        if (length(present) < vs[j])
            stop(sprintf("column %d does not contain every level 0..%d (or 1..%d); postopNCK_c needs a covering array as input",
                         j, vs[j] - 1L, vs[j]))
    }
    bound <- prod(sort(vs, decreasing = TRUE)[seq_len(t)])
    finish <- function(xm, extra = NULL) {
        out <- xm + shift
        class(out) <- c("ca", class(out))
        if (any(is.na(out)))
            attr(out, "flexible") <- list(value = NA)
        attr(out, "seed") <- seed
        for (nmx in names(extra)) attr(out, nmx) <- extra[[nmx]]
        out
    }
    if (N0 == bound) {
        if (verbose >= 1) message("D is already optimal")
        return(D)
    }
    if (is.null(seed)) seed <- sample(32000, 1)
    set.seed(seed)
    deadline <- Sys.time() + timeBudget
    mk <- .markflex0(x, t, vs, fixrows)
    Di <- mk$x
    best <- Di
    ncur <- nrow(Di); count_unchanged <- 0; restarts_left <- restarts
    res <- tryCatch({
        for (i in seq_len(outerRetry)) {
            if (verbose >= 1) cat("outer", i, " rows", nrow(Di), "\n")
            one <- .nck_one0(Di, t, vs, fixrows, innerRetry,
                             innerMaxnochange, deadline, verbose)
            Di <- one$x
            if (nrow(Di) < nrow(best)) best <- Di
            if (one$timeout) return(finish(best, list(timeout = TRUE)))
            if (one$removed == 0) {
                count_unchanged <- count_unchanged + 1
                if (count_unchanged >= outerMaxnochange) {
                    if (restarts_left > 0) {
                        ## paper stall escape at the outer level: full
                        ## random refill of the best, remark, go again
                        restarts_left <- restarts_left - 1
                        count_unchanged <- 0
                        xr <- best
                        for (j in seq_len(k)) {
                            nas <- which(is.na(xr[, j]))
                            if (length(nas))
                                xr[nas, j] <- sample(0:(vs[j] - 1L),
                                    length(nas), replace = TRUE)
                        }
                        Di <- .markflex0(xr, t, vs, fixrows)$x
                        next
                    }
                    break
                }
            } else count_unchanged <- 0
            if (nrow(Di) == bound) break
        }
        finish(best)
    }, interrupt = function(e) {
        if (verbose >= 1)
            message("interrupted; returning best result so far")
        finish(best, list(interrupt = TRUE))
    })
    res
}
