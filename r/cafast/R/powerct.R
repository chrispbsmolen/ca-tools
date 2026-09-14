## Power construction of Colbourn and Torres-Jimenez (2010), homogeneous case,
## for any (t, k, v): not limited to the 132 catalogued settings of CAs::powerCA.
##
## Shape of the construction (as in CAs::powerCA / createDHF / DHHF2CA):
##   an orthogonal array OA(q^e, q+1, q, e) from the Bush construction is
##   transposed and its first M = (e-1)*Turan(t, v) + 1 columns become the M
##   rows of a distributing hash family (DHF) with k = q^e columns and q
##   classes; this needs q + 1 > M - 1, i.e. q >= (e-1)*Turan(t, v).
##   One ingredient CA(t, q, v) with N1 rows, rho of them constant (after
##   maxconstant), is plugged into every DHF row; each row contributes
##   N1 - rho rows, shifted by (row index)*rho mod v so that different rows
##   cover different constant tuples; chi = max(0, v - M*(v - rho)) constant
##   rows are added back for the tuples nobody covered.
##   N = M*(N1 - rho) + chi.
##
## Functions:
##   power_plan(t, k, v, ...)   enumerate admissible (q, e), build each
##                              ingredient, return a data.frame sorted by N
##   power_build(t, k, v, q, e, ingredient)  build the array
##   powerCT_any(t, k, v, ...)  plan, build the best, return the array with
##                              attributes t, N, plan row
## Ingredient by default CAs::bestCA(t, q, v) (her best implemented
## construction); a matrix or a function(t, q, v) can be given instead.

Turan_ <- function(t, v) {
    if (v >= t) return(t * (t - 1) / 2)
    a <- floor(t / v); b <- a + 1; nb <- t - a * v; na <- v - nb
    t * (t - 1) / 2 - na * a * (a - 1) / 2 - nb * b * (b - 1) / 2
}

prime_powers <- function(upto) {
    isprime <- function(n) n >= 2 && (n < 4 || all(n %% 2:floor(sqrt(n)) != 0))
    out <- integer(0)
    for (p in Filter(isprime, 2:upto)) { x <- p; while (x <= upto) { out <- c(out, x); x <- x * p } }
    sort(unique(out))
}

## the DHF: M x q^e, entries 0..q-1
power_dhf <- function(q, e, M) {
    oa <- CAs::SCA_Busht(q, e)
    oa <- as.matrix(oa); storage.mode(oa) <- "integer"
    stopifnot(ncol(oa) >= M)
    P <- t(oa[, seq_len(M), drop = FALSE])
    P - min(P)
}

## assemble: P (M x K, classes 0..q-1), D ingredient with rho leading constant
## rows (ascending symbols 0..rho-1), v levels. Mirrors CAs::DHHF2CA for one ingredient.
power_assemble <- function(P, D, v) {
    M <- nrow(P); K <- ncol(P)
    cst <- rowSums(D == D[, 1]) == ncol(D); rho <- 0L
    for (r in seq_len(nrow(D))) { if (!cst[r] || (r > 1 && D[r, 1] <= D[r - 1, 1])) break; rho <- r }
    constlev <- if (rho > 0) D[seq_len(rho), 1] else integer(0)
    Drem <- D[setdiff(seq_len(nrow(D)), seq_len(rho)), , drop = FALSE]
    n1 <- nrow(Drem)
    chi <- max(0, v - M * (v - rho))
    out <- matrix(NA_integer_, M * n1 + chi, K)
    covered <- integer(0)
    for (r in seq_len(M)) {
        shift <- (r - 1) * rho
        out[(r - 1) * n1 + seq_len(n1), ] <- (Drem[, P[r, ] + 1L, drop = FALSE] + shift) %% v
        covered <- union(covered, setdiff(0:(v - 1), (constlev + shift) %% v))
    }
    if (chi > 0) {
        miss <- setdiff(0:(v - 1), covered)
        if (length(miss) > chi) { out <- rbind(out, matrix(NA_integer_, length(miss) - chi, K)); chi <- length(miss) }
        if (length(miss) < chi) stop("power_assemble: fewer uncovered constant tuples than chi")
        out[M * n1 + seq_len(chi), ] <- matrix(miss, chi, K)
    }
    storage.mode(out) <- "integer"
    unique(out)
}

get_ingredient <- function(ingredient, t, q, v, ...) {
    D <- if (is.function(ingredient)) ingredient(t, q, v, ...) else if (is.matrix(ingredient)) ingredient else CAs::bestCA(t, q, v, ...)
    D <- as.matrix(D); if (any(is.na(D))) D[is.na(D)] <- 0L; storage.mode(D) <- "integer"
    D <- D - min(D)
    if (ncol(D) < q) stop("ingredient has fewer than q columns")
    if (ncol(D) > q) D <- D[, seq_len(q), drop = FALSE]
    maxconstant_c(D)
}

power_plan <- function(t, k, v, emax = 4, qextra = 1, ingredient = NULL, maxq = 400, verbose = TRUE, ...) {
    Tu <- Turan_(t, v)
    rows <- list(); cache <- list()
    for (e in 2:emax) {
        M <- (e - 1) * Tu + 1
        qs <- prime_powers(maxq)
        qs <- qs[qs^e >= k & qs >= M - 1 & qs >= t & qs > e]
        if (length(qs) == 0) next
        qs <- qs[seq_len(min(length(qs), 1 + qextra))]
        for (q in qs) {
            key <- as.character(q)
            if (is.null(cache[[key]])) {
                D <- tryCatch(get_ingredient(ingredient, t, q, v, ...), error = function(err) NULL)
                if (is.null(D)) { if (verbose) cat(sprintf("  q=%d: no ingredient CA(%d,%d,%d)\n", q, t, q, v)); cache[[key]] <- NA; next }
                cache[[key]] <- D
            }
            D <- cache[[key]]; if (!is.matrix(D)) next
            cst <- rowSums(D == D[, 1]) == ncol(D); rho <- 0L
            for (r in seq_len(nrow(D))) { if (!cst[r] || (r > 1 && D[r, 1] <= D[r - 1, 1])) break; rho <- r }
            chi <- max(0, v - M * (v - rho))
            N <- M * (nrow(D) - rho) + chi
            if (verbose) cat(sprintf("  e=%d q=%d: M=%d, ingredient N1=%d rho=%d, chi=%d -> N=%d (k=%d)\n", e, q, M, nrow(D), rho, chi, N, q^e))
            rows[[length(rows) + 1]] <- data.frame(t = t, k = k, v = v, e = e, q = q, M = M, N1 = nrow(D), rho = rho, chi = chi, N = N, kmax = q^e)
        }
    }
    if (length(rows) == 0) return(NULL)
    plan <- do.call(rbind, rows); plan <- plan[order(plan$N, plan$q), ]; rownames(plan) <- NULL
    attr(plan, "ingredients") <- cache
    plan
}

power_build <- function(t, k, v, q, e, ingredient = NULL, ...) {
    M <- (e - 1) * Turan_(t, v) + 1
    D <- get_ingredient(ingredient, t, q, v, ...)   # a matrix passes through maxconstant_c again (idempotent)
    P <- power_dhf(q, e, M)
    A <- power_assemble(P, D, v)[, seq_len(k), drop = FALSE]
    attr(A, "t") <- t; attr(A, "q") <- q; attr(A, "e") <- e; attr(A, "M") <- M; attr(A, "N1") <- nrow(D)
    attr(A, "origin") <- "Power construction of Colbourn and Torres-Jimenez 2010 (cafast::powerCT_any)"
    A
}

powerCT_any <- function(t, k, v, emax = 4, qextra = 1, ingredient = NULL, verbose = TRUE, ...) {
    plan <- power_plan(t, k, v, emax = emax, qextra = qextra, ingredient = ingredient, verbose = verbose, ...)
    if (is.null(plan)) stop("no admissible (q, e) for this setting")
    best <- plan[1, ]
    D <- attr(plan, "ingredients")[[as.character(best$q)]]
    A <- power_build(t, k, v, best$q, best$e, ingredient = D)
    if (nrow(A) != best$N) warning(sprintf("built %d rows, plan said %d", nrow(A), best$N))
    attr(A, "plan") <- plan
    A
}
