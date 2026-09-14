maxconstant_c <- function(D, verbose = 0, remove = FALSE, one_is_enough = FALSE, dupcheck = FALSE, ...) {
    Dnam <- deparse(substitute(D))
    stopifnot(verbose %in% c(0, 1, 2, 12))
    stopifnot(is.matrix(D), is.numeric(D))
    if (dupcheck) D <- D[!duplicated(D), , drop = FALSE]
    N <- nrow(D); k <- ncol(D)
    levs <- sort(unique(as.vector(D)))
    levs <- levs[!is.na(levs)]
    v <- length(levs)
    if (any(is.na(D))) stop("maxconstant_c needs an array without NA cells")
    consts <- rowSums(D == D[, 1]) == k
    nconstant <- sum(consts)
    posconsts <- integer(0)
    if (nconstant > 0) { posconsts <- which(consts); posconsts <- posconsts[order(D[posconsts, 1])] }
    if (nconstant == v) {
        D <- if (remove) D[setdiff(seq_len(N), posconsts), , drop = FALSE] else D[c(posconsts, setdiff(seq_len(N), posconsts)), , drop = FALSE]
        if (verbose %in% c(2, 12)) attr(D, "constant_rows") <- list(design_name = Dnam, row_set_list = posconsts)
        return(D)
    }
    if (one_is_enough) {
        if (nconstant == 0) {
            target <- levs[1]
            for (j in seq_len(k)) { s <- D[1, j]; if (s != target) { col <- D[, j]; D[col == s, j] <- target; D[col == target, j] <- s } }
            nconstant <- 1L; posconsts <- 1L
        }
        clique <- posconsts
    } else {
        code <- matrix(match(D, levs) - 1L, N, k)
        storage.mode(code) <- "integer"
        clique <- .Call(C_maxclique_disjoint, code, as.integer(N), as.integer(k), as.integer(v), as.integer(posconsts))
        clique <- sort(clique)
    }
    nmax <- length(clique)
    if (verbose %in% c(1, 12)) message("used largest clique: ", paste(clique, collapse = ", "))
    if (nmax == nconstant) {
        if (verbose %in% c(1, 12)) message("No additional constant rows found, existing constant rows moved to rows 1:", nconstant)
        D <- if (remove) D[setdiff(seq_len(N), posconsts), , drop = FALSE] else D[c(posconsts, setdiff(seq_len(N), posconsts)), , drop = FALSE]
        if (verbose %in% c(2, 12)) attr(D, "constant_rows") <- list(design_name = Dnam, row_set_list = posconsts)
        return(D)
    }
    if (remove) {
        D <- D[setdiff(seq_len(N), clique), , drop = FALSE]
    } else {
        D <- D[c(clique, setdiff(seq_len(N), clique)), , drop = FALSE]
        for (j in seq_len(k)) {
            col <- D[, j]
            from <- col[seq_len(nmax)]
            to <- levs[seq_len(nmax)]
            perm <- levs
            names(perm) <- levs
            others_from <- setdiff(levs, from); others_to <- setdiff(levs, to)
            perm[as.character(from)] <- to
            perm[as.character(others_from)] <- others_to
            D[, j] <- unname(perm[as.character(col)])
        }
    }
    if (verbose %in% c(2, 12)) attr(D, "constant_rows") <- list(design_name = Dnam, row_set_list = clique)
    D
}
