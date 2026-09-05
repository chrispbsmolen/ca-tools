## test_count_core.R - validation of the counting core (increment 1)
## Track 1: randomized mixed-level arrays, with and without NAs,
##          exact agreement with the pure-R oracle on all four
##          outputs (tots, ncovered, missing, rowmult).
## Track 2: NA-free arrays, ncovered/tots per projection against
##          CAs::coverage(verbose = 1), which also fixes the
##          column-subset ORDER contract (lexicographic).
## Track 3: invariants. Sum of cell counts equals the number of
##          complete rows (checked via rowmult of duplicated rows),
##          full factorial covers everything, t = 1 sanity.
## Track 4: guards. Out-of-range symbol errors; bad t errors.

dyn.load("count_core.so")
source("oracle_count.R")
count_core <- function(x, t, vs, rowmult = TRUE) {
    storage.mode(x) <- "integer"
    .Call("C_count_core", x, as.integer(t), as.integer(vs),
          as.integer(rowmult))
}

ncase <- 0L; nfail <- 0L
chk <- function(ok, label) {
    ncase <<- ncase + 1L
    if (!isTRUE(ok)) { nfail <<- nfail + 1L
        cat("FAIL:", label, "\n") }
}

set.seed(20260829)

## Track 1: oracle agreement
for (i in 1:400) {
    k <- sample(3:7, 1); t <- sample(1:min(4, k), 1)
    vs <- sample(2:5, k, replace = TRUE)
    N <- sample(3:25, 1)
    x <- sapply(vs, function(v) sample(0:(v - 1), N, replace = TRUE))
    x <- matrix(as.integer(x), N, k)
    if (i %% 3 == 0) x[sample(length(x), sample(1:4, 1))] <- NA
    r <- count_core(x, t, vs)
    o <- oracle_count(x, t, vs)
    chk(identical(r$tots, o$tots) &&
        identical(r$ncovered, o$ncovered) &&
        identical(r$missing, o$missing) &&
        isTRUE(all.equal(r$rowmult, o$rowmult, check.attributes = FALSE)),
        paste0("oracle rand", i))
}

## Track 2: coverage() agreement, including projection order
suppressMessages(library(CAs))
for (i in 1:120) {
    k <- sample(3:6, 1); t <- sample(2:min(3, k), 1)
    vs <- sample(2:4, k, replace = TRUE)
    N <- sample((max(vs)):30, 1)
    ## every column attains all its symbols (CAs's data-derived counts)
    x <- sapply(vs, function(v) c(sample(0:(v - 1)),
                                  sample(0:(v - 1), N - v, replace = TRUE)))
    x <- matrix(as.integer(x), N, k)
    r <- count_core(x, t, vs, rowmult = FALSE)
    cv <- CAs::coverage(x, t, verbose = 1)
    chk(isTRUE(all.equal(r$tots, as.numeric(cv$tots))) &&
        isTRUE(all.equal(r$ncovered, as.numeric(cv$ncovereds))),
        paste0("coverage rand", i, " (order-sensitive)"))
}

## Track 3: invariants
ff <- as.matrix(expand.grid(0:2, 0:1, 0:1))          ## full factorial
r <- count_core(ff, 2, c(3, 2, 2))
chk(all(r$missing == 0), "full factorial covered at t=2")
r3 <- count_core(ff, 3, c(3, 2, 2))
chk(all(r3$rowmult == 1), "full factorial t=3 all multiplicities 1")
dup <- rbind(ff, ff)                                  ## doubled rows
rd <- count_core(dup, 3, c(3, 2, 2))
chk(all(rd$rowmult == 2), "doubled factorial t=3 all multiplicities 2")
r1 <- count_core(ff, 1, c(3, 2, 2))
chk(identical(r1$tots, c(3, 2, 2)) && all(r1$missing == 0), "t=1 sanity")
## NA row contributes nothing anywhere
na1 <- rbind(ff, c(NA, 0L, 0L))
rn <- count_core(na1, 2, c(3, 2, 2))
chk(all(rn$rowmult[nrow(na1), 1:2] == 0), "NA projections give rowmult 0")
chk(rn$rowmult[nrow(na1), 3] > 0, "non-NA projection still counts")

## Track 4: guards
chk(inherits(try(count_core(ff, 2, c(2, 2, 2)), silent = TRUE), "try-error"),
    "out-of-range symbol rejected")
chk(inherits(try(count_core(ff, 0, c(3, 2, 2)), silent = TRUE), "try-error"),
    "t=0 rejected")
chk(inherits(try(count_core(ff, 4, c(3, 2, 2)), silent = TRUE), "try-error"),
    "t>k rejected")

cat(sprintf("cases: %d, failures: %d\n", ncase, nfail))
if (nfail == 0L) cat("COUNT CORE PASS\n") else cat("COUNT CORE FAIL\n")
