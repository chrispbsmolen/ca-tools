## nck_faces.R - R wrappers for the locator and marking faces.
## Load with: source("nck_faces.R"); needs nck_faces.so beside it,
## built by: R CMD SHLIB nck_faces.c

if (!is.loaded("C_flexpos")) dyn.load("nck_faces.so")

## normalize an integer matrix to 0-based consecutive coding (D2/D3):
## accepts 0-based or 1-based; anything else is rejected informatively.
## PRECONDITION: the input is a covering array (or a marked one), so
## every column contains its lowest level. A 0-based array missing
## level 0 in EVERY column would be read as 1-based (harmless for the
## faces, which are recoding-invariant; wrong for the driver's fills).
## Returns list(x, vs, shift) where shift is 0 or 1 (to restore coding).
.nck_norm <- function(D, vs = NULL) {
    if (is.data.frame(D)) D <- as.matrix(D)
    if (!is.matrix(D)) stop("D must be a matrix or data.frame")
    x <- D; storage.mode(x) <- "integer"
    mins <- suppressWarnings(apply(x, 2, min, na.rm = TRUE))
    if (any(!is.finite(mins))) stop("a column is entirely NA")
    shift <- if (all(mins >= 1)) 1L else 0L
    x <- x - shift
    if (is.null(vs)) {
        vs <- suppressWarnings(apply(x, 2, max, na.rm = TRUE)) + 1L
        vs <- as.integer(vs)
    } else vs <- as.integer(vs)
    ## values must lie in 0..vs-1 after the shift (absent levels are
    ## permitted; the C side range-checks again and never drops bins,
    ## which is the D2 protection against silent corruption)
    for (cc in seq_len(ncol(x))) {
        vals <- x[, cc]; vals <- vals[!is.na(vals)]
        if (any(vals < 0L) || any(vals >= vs[cc]))
            stop(sprintf(
                "column %d has symbols outside 0..%d (or 1..%d): coding must be consecutive from 0 or 1; recode the array first",
                cc, vs[cc] - 1L, vs[cc]))
    }
    list(x = x, vs = vs, shift = shift)
}

## flexpos_c: CAs::flexpos, fast. conv = "flexpos" (default, the CAs
## NA convention, verified to be the more conservative) or "coverage".
flexpos_c <- function(D, t, conv = c("flexpos", "coverage")) {
    conv <- match.arg(conv)
    nz <- .nck_norm(D)
    .Call("C_flexpos", nz$x, as.integer(t), nz$vs,
          if (conv == "flexpos") 0L else 1L)
}

## .markflex0: internal marking on an already-normalized 0-based
## matrix. Sort ascending by flexpos count (CAs convention), stable,
## fixrows prefix frozen (fixrows >= N-1 disables the sort, as in
## CAs::markflex); greedy first-coverer pins cells; unpinned cells NA.
## Returns list(x = marked matrix in sorted order, ord = row order).
.markflex0 <- function(x, t, vs, fixrows = 0) {
    N <- nrow(x)
    if (fixrows < N - 1) {
        fp <- .Call("C_flexpos", x, as.integer(t), vs, 0L)
        cnt <- rowSums(fp)
        if (fixrows > 0) {
            rest <- (fixrows + 1L):N
            ord <- c(seq_len(fixrows), rest[order(cnt[rest])])
        } else ord <- order(cnt)               ## stable (radix)
    } else ord <- seq_len(N)
    xs <- x[ord, , drop = FALSE]
    pin <- .Call("C_markflex_pin", xs, as.integer(t), vs)
    xs[!pin & !is.na(xs)] <- NA
    list(x = xs, ord = ord)
}

## markflex_c: CAs::markflex, fast. Returns the marked matrix in the
## SORTED row order, in the input's own coding, with attributes
## "rowOrder" (original indices) and "flexcount" (per-row NAs).
markflex_c <- function(D, t, fixrows = 0) {
    nz <- .nck_norm(D)
    mk <- .markflex0(nz$x, t, nz$vs, fixrows)
    out <- mk$x + nz$shift
    attr(out, "rowOrder") <- mk$ord
    attr(out, "flexcount") <- rowSums(is.na(out))
    out
}
