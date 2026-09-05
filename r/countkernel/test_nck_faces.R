## test_nck_faces.R - validation battery for the locator/marking
## faces against CAs 0.24.
## Run from this directory:  Rscript test_nck_faces.R
suppressMessages(library(CAs))
source("nck_faces.R")
set.seed(20260904)
fails <- 0
chk <- function(ok, what) {
    if (!ok) { cat("FAIL:", what, "\n"); fails <<- fails + 1 }
}

## ---- 1. flexpos_c vs CAs::flexpos, CAs convention, NA-free ----
## (exact agreement expected under EITHER convention on NA-free)
hilf <- strsplit(c("2222001", "0022222", "1121201", "0120110",
                   "2210202", "2102122", "1200020", "0211121",
                   "1012100", "2001210", "0000001", "1111012",
                   "2222222", "2222011"), "")
plan <- do.call(rbind, lapply(hilf, as.numeric))
chk(identical(unname(flexpos(plan, 2)), unname(flexpos_c(plan, 2))),
    "manual example, CAs convention")
chk(identical(unname(flexpos(plan, 2)),
              unname(flexpos_c(plan, 2, conv = "coverage"))),
    "manual example, coverage convention (must agree when NA-free)")

nrand <- 0
for (rep in 1:300) {
    N <- sample(6:14, 1); k <- sample(4:7, 1)
    vs <- sample(2:4, k, replace = TRUE)
    D <- sapply(vs, function(v) sample(0:(v-1), N, replace = TRUE))
    D[1, ] <- 0
    tt <- sample(2:min(3, k - 1), 1)
    ## with probability 1/2 add NAs (sparing row 1)
    if (runif(1) < 0.5) {
        okk <- setdiff(seq_len(N * k), 1 + (0:(k-1)) * N)
        D[sample(okk, sample(1:5, 1))] <- NA
    }
    a <- suppressMessages(unname(flexpos(D, tt)))
    b <- unname(flexpos_c(D, tt))
    if (!identical(a, b)) chk(FALSE, sprintf("random flexpos rep %d", rep))
    nrand <- nrand + 1
}
cat("flexpos random battery:", nrand, "arrays (mixed levels, half with NAs)\n")

## ---- 2. coverage-convention face vs the independent R model ----
## (the oracle from flexpos_q1_check.R, reimplemented here verbatim)
nchoosek <- CAs:::nchoosek
flexpos_cov_oracle <- function(D, t) {
    N <- nrow(D); k <- ncol(D)
    fpos <- matrix(TRUE, N, k)
    tuples <- nchoosek(k, t)
    for (i in 1:ncol(tuples)) {
        S <- tuples[, i]
        now <- D[, S, drop = FALSE]
        hasNA <- apply(now, 1, function(r) any(is.na(r)))
        keyz <- apply(now, 1, paste, collapse = ",")
        tab <- table(keyz[!hasNA])
        needed <- which(!hasNA & tab[keyz] == 1)
        fpos[needed, S] <- FALSE
    }
    fpos[which(is.na(D))] <- TRUE
    fpos
}
for (rep in 1:100) {
    N <- sample(6:12, 1); k <- sample(4:6, 1); v <- sample(2:3, 1)
    D <- matrix(sample(0:(v-1), N * k, replace = TRUE), N, k)
    D[1, ] <- 0
    okk <- setdiff(seq_len(N * k), 1 + (0:(k-1)) * N)
    D[sample(okk, sample(1:4, 1))] <- NA
    a <- flexpos_cov_oracle(D, 2)
    b <- unname(flexpos_c(D, 2, conv = "coverage"))
    if (!identical(a, b)) chk(FALSE, sprintf("coverage conv rep %d", rep))
}
cat("coverage-convention battery: 100 NA-bearing arrays vs R oracle\n")

## ---- 3. markflex_c vs CAs::markflex ----
## deterministic given the row order; agreement = identical marked
## matrix after aligning row order via the rowOrder attribute.
mm_agree <- function(D, t, fixrows = 0) {
    hers <- suppressMessages(markflex(D, t, fixrows = fixrows))
    ourz <- markflex_c(D, t, fixrows = fixrows)
    ho <- as.integer(attr(hers, "rowOrder")); oo <- as.integer(attr(ourz, "rowOrder"))
    if (!length(ho)) ho <- seq_len(nrow(D))
    a <- as.matrix(hers); attributes(a) <- attributes(a)["dim"]
    storage.mode(a) <- "integer"
    b <- ourz; attributes(b) <- attributes(b)["dim"]
    storage.mode(b) <- "integer"
    if (identical(ho, oo)) return(identical(a, b))
    ## orders differ (tie-break or convention): compare as multisets
    ka <- apply(a, 1, paste, collapse = ",")
    kb <- apply(b, 1, paste, collapse = ",")
    identical(sort(ka), sort(kb))
}
chk(mm_agree(plan, 2), "markflex manual example")
chk(mm_agree(plan, 2, fixrows = 2), "markflex manual example fixrows=2")
A19 <- cyc(19, 2)
chk(mm_agree(A19, 3), "markflex cyc(19,2) t=3")
nsame_order <- 0; ntot <- 0
for (rep in 1:120) {
    N <- sample(8:16, 1); k <- sample(4:7, 1)
    v <- sample(2:3, 1)
    D <- matrix(sample(0:(v-1), N * k, replace = TRUE), N, k)
    D[1:v, ] <- matrix(0:(v-1), v, k)   ## every level present per column
    tt <- sample(2:min(3, k - 1), 1)
    if (!mm_agree(D, tt)) chk(FALSE, sprintf("random markflex rep %d", rep))
    hers <- suppressMessages(markflex(D, tt))
    if (identical(as.integer(attr(hers, "rowOrder")),
                  as.integer(attr(markflex_c(D, tt), "rowOrder"))))
        nsame_order <- nsame_order + 1
    ntot <- ntot + 1
}
cat("markflex random battery:", ntot, "arrays; identical row order in",
    nsame_order, "\n")

## ---- 4. D2 rejection (out-of-range coding) ----
bad <- matrix(c(0, 2, -1, 2, 2, 0, 0, 2), 4, 2)   ## negative symbol
r <- tryCatch(flexpos_c(bad, 2), error = function(e) e)
chk(inherits(r, "error") && grepl("consecutive", conditionMessage(r)),
    "out-of-range coding rejected informatively")
## a 0/2 column (absent middle level) must NOT corrupt: multiplicity
## semantics equal duplicated(), same as CAs::flexpos
gap <- matrix(c(0, 2, 0, 2, 2, 0, 0, 2, 1, 1, 0, 0), 4, 3)
chk(identical(unname(flexpos(gap, 2)), unname(flexpos_c(gap, 2))),
    "absent-level column matches CAs::flexpos")

## ---- 5. D3, 1-based input round-trips in its own coding ----
D1b <- matrix(sample(1:3, 30, replace = TRUE), 10, 3); D1b[1, ] <- 1
m <- markflex_c(D1b, 2)
vals <- m[!is.na(m)]
chk(all(vals >= 1 & vals <= 3), "1-based coding preserved in output")

cat("\n", if (fails == 0) "ALL NCK FACES TESTS PASS" else
    paste(fails, "FAILURES"), "\n", sep = "")
