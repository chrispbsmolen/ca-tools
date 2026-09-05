## oracle_count.R - pure-R oracle for the counting core.
## Deliberately shares NO logic with count_core.c: no stride
## arithmetic, no tabulate. Tuples are compared as pasted strings.
## A row with an NA in the projection contributes nothing.
oracle_count <- function(x, t, vs) {
    k <- ncol(x); N <- nrow(x)
    combs <- utils::combn(k, t)
    nc <- ncol(combs)
    tots <- numeric(nc); ncov <- numeric(nc); miss <- numeric(nc)
    rowmult <- matrix(0, N, nc)
    for (ci in seq_len(nc)) {
        cols <- combs[, ci]
        tots[ci] <- prod(vs[cols])
        sub <- x[, cols, drop = FALSE]
        complete <- !apply(sub, 1, anyNA)
        keys <- apply(sub[complete, , drop = FALSE], 1, paste, collapse = "|")
        tab <- table(keys)
        ncov[ci] <- length(tab)
        miss[ci] <- tots[ci] - ncov[ci]
        if (any(complete))
            rowmult[which(complete), ci] <- as.numeric(tab[keys])
    }
    list(tots = tots, ncovered = ncov, missing = miss, rowmult = rowmult)
}
