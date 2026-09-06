## arith_laws.R - the ARITHMETIC tier's law evaluators, one per
## calibrated family, each a function of the entry (t, v, k, Source)
## and a lookup function ecan(t, w, v) over the CURRENT living table
## (frozen record plus verified improvements), plus ncan(t, w, v), the
## constant rows the answering row is known to carry: NA for a frozen
## record row (the tag's assumption stands, that is the calibration),
## a number for an improvement (what it was measured or declared to
## have, default 1). A law credits an improved ingredient only for
## the constant rows it carries: rho_i = min(tag rho, ncan), and the
## direct product's c = min(v, nc1 + nc2) with a frozen partner
## counted as 1 when the other is improved. Every evaluator returns
## list(N = recomputed size, deps = data.frame(t, w, v) of the lookups
## it made), so the engine knows which table entries feed which.
## The laws are the ones calibrated in arith_formula_power.R,
## arith_formula_dp_table.R, arith_formula_small.R,
## arith_families_probe.R, arith_formula_addn.R, arith_formula_mc.R,
## arith_formula_fuse.R, arith_formula_cmtw.R and arith_formula_mtvt.R;
## the identity test in arith_engine.R
## requires this file to reproduce every ARITHMETIC entry's recorded
## N from the frozen record, which pins the two implementations to
## each other. Sourced by arith_engine.R.
Turan <- function(t, v) { if (v >= t) return(t * (t - 1) / 2)
    a <- floor(t / v); b <- a + 1; nb <- t - a * v; na <- v - nb
    t * (t - 1) / 2 - na * a * (a - 1) / 2 - nb * b * (b - 1) / 2 }

## ---- power family (Power CT, Power N-CT) and perfect hash family ----
parse_power_tag <- function(s) {
    fam <- if (grepl("^Power N-CT", s)) "N-CT" else "CT"
    body <- sub("^Power (N-)?CT", "", s)
    q <- as.numeric(sub("\\^.*", "", body)); rest <- sub("^[0-9]+\\^", "", body)
    e <- as.numeric(sub("[^0-9].*$", "", rest)); mods <- sub("^[0-9]+", "", rest)
    plus <- 0; reds <- c(); cfl <- c(); base_c <- FALSE; run <- c()
    if (grepl("Trin", mods)) { r <- as.numeric(strsplit(sub(".*Trin", "", mods), ",")[[1]])
        reds <- c(reds, r); cfl <- c(cfl, rep(FALSE, 3)); mods <- sub("Trin.*$", "", mods) }
    if (grepl("twos", mods)) { x <- as.numeric(sub(".*:([0-9]+) twos.*", "\\1", mods)); y <- as.numeric(sub(".*,([0-9]+) ones.*", "\\1", mods))
        reds <- c(reds, rep(2, x), rep(1, y)); cfl <- c(cfl, rep(FALSE, x + y)); mods <- sub("Arc\\([0-9]+\\):[0-9]+ twos,[0-9]+ ones", "", mods) }
    if (grepl("Arc", mods)) { a <- as.numeric(sub(".*Arc\\(([0-9]+)\\).*", "\\1", mods))
        reds <- c(reds, rep(1, a)); cfl <- c(cfl, rep(FALSE, a)); mods <- sub("Arc\\([0-9]+\\)", "", mods) }
    if (grepl("\\+", mods)) { plus <- as.numeric(sub(".*\\+ ?([0-9]+).*", "\\1", mods)); mods <- sub("\\+ ?[0-9]+", "", mods) }
    toks <- regmatches(mods, gregexpr("T[0-9]+|S[0-9]+|c|,", mods))[[1]]
    for (tk in toks) {
        if (tk == ",") { run <- c(); next }
        if (grepl("^T", tk)) { reds <- c(reds, as.numeric(sub("T", "", tk))); cfl <- c(cfl, FALSE); run <- c(run, length(reds)) }
        else if (grepl("^S", tk)) { s2 <- as.numeric(sub("S", "", tk)); reds <- c(reds, rep(1, s2)); cfl <- c(cfl, rep(FALSE, s2)); run <- c(run, length(reds) - s2 + seq_len(s2)) }
        else if (tk == "c") { if (!length(run)) base_c <- TRUE else cfl[run] <- TRUE } }
    list(fam = fam, q = q, e = e, plus = plus, reds = reds, cfl = cfl, base_c = base_c)
}
hash_law <- function(t, v, M, w0, rho0, ws, rhos, ecan, ncan) {
    ## N = chi + u0 (N0 - rho0) + sum_j (N_j - rho_j), chi = max(0, v - u0 (v - rho0) - sum_j (v - rho_j))
    u0 <- M - length(ws); if (is.na(u0) || u0 < 0) return(list(N = NA, deps = NULL))
    N0 <- ecan(t, w0, v); Nj <- if (length(ws)) sapply(ws, ecan, t = t, v = v) else numeric(0)
    ## constant rows: an improved answering row is credited only for what it carries
    nc0 <- ncan(t, w0, v); if (!is.na(nc0)) rho0 <- min(rho0, nc0)
    if (length(ws)) { ncj <- sapply(ws, ncan, t = t, v = v); rhos <- ifelse(is.na(ncj), rhos, pmin(rhos, ncj)) }
    chi <- max(0, v - u0 * (v - rho0) - sum(v - rhos))
    list(N = chi + u0 * (N0 - rho0) + sum(Nj - rhos), deps = data.frame(t = t, w = c(w0, ws), v = v, range = FALSE))
}
law_power <- function(t, v, k, Source, ecan, ncan, Mtab) {
    pr <- parse_power_tag(Source)
    M <- if (pr$fam == "CT") (pr$e - 1) * Turan(t, v) + 1 else {
        i <- which(Mtab$t == t & Mtab$pcls == min(t, v) & Mtab$q == pr$q & Mtab$e == pr$e); if (length(i) == 1) Mtab$M[i] else NA }
    hash_law(t, v, M, pr$q + pr$plus, if (pr$base_c) v else 1, pr$q - pr$reds, ifelse(pr$cfl, v, 1), ecan, ncan)
}
law_phf <- function(t, v, k, Source, ecan, ncan) {
    if (grepl("^perfect hash familyD", Source)) {   ## D16 form (arith_families_tail.R): na rows at a symbols, nb at b, (N_i - 1) each plus one row; ncan not consulted
        m <- regmatches(Source, regexec("^perfect hash familyD([0-9]+),([0-9]+),([0-9]+)\\^([0-9]+) ([0-9]+)\\^([0-9]+)$", Source))[[1]]
        a <- as.numeric(m[4]); nA <- as.numeric(m[5]); b <- as.numeric(m[6]); nB <- as.numeric(m[7])
        return(list(N = nA * (ecan(t, a, v) - 1) + nB * (ecan(t, b, v) - 1) + 1, deps = data.frame(t = t, w = c(a, b), v = v, range = FALSE))) }
    m <- regmatches(Source, regexec("^perfect hash family([0-9]+),([0-9]+),([0-9]+)(T([0-9]+)|S([0-9]+)|(,c))?$", Source))[[1]]
    a <- as.numeric(m[2]); w <- as.numeric(m[4]); Tr <- suppressWarnings(as.numeric(m[6])); Ss <- suppressWarnings(as.numeric(m[7])); cf <- m[8] == ",c"
    rho <- if (cf) v else 1
    ws <- c(); if (!is.na(Tr)) ws <- w - Tr; if (!is.na(Ss)) ws <- rep(w - 1, Ss)
    hash_law(t, v, a, w, rho, ws, rep(rho, length(ws)), ecan, ncan)
}
## ---- direct product, plain tag: best pair, c = v on the record's own
## pairs (the calibration), c = min(v, nc1 + nc2) when an improved row
## answers, a frozen partner counted as 1 constant row ----
law_dp <- function(t, v, k, Source, ecan, ncan, kmax) {
    best <- Inf; deps <- data.frame(t = 2, w = kmax, v = v, range = TRUE)   ## any (2, w <= kmax, v) can move the minimum
    for (k1 in 2:min(kmax, floor(sqrt(k)) + 1)) { k2 <- ceiling(k / k1); if (k2 > kmax) next
        n1 <- ncan(2, k1, v); n2 <- ncan(2, k2, v)
        cc <- if (is.na(n1) && is.na(n2)) v else min(v, ifelse(is.na(n1), 1, n1) + ifelse(is.na(n2), 1, n2))
        val <- ecan(2, k1, v) + ecan(2, k2, v) - cc
        if (!is.na(val) && val < best) best <- val }
    list(N = best, deps = deps)
}
## ---- derive, add n factors, Martirosyan-Colbourn, CK doubling ----
law_derive <- function(t, v, k, Source, ecan) { f <- as.numeric(sub(".*strength ([0-9]+)", "\\1", Source))
    list(N = floor(ecan(f, k + 1, v) / v), deps = data.frame(t = f, w = k + 1, v = v, range = FALSE)) }
## add n factors (tags "Add n factors" and "Add a factor"; for the latter
## n is the chain length of consecutive "Add a factor" rows in the frozen
## record, which needs cb, colbournBigFrame, in scope as in arith_engine.R):
## N = ecan(t, b, v) + sum_{j=2}^{min(t, n+1)} v^(j-1) (v-1) ecan(t-j, b-1, v),
## b = k - n, ecan(1, ., v) = v, ecan(0, ., v) = 1 (arith_formula_addn.R)
add_chain <- function(t, v, k) { f <- cb$k[cb$Source == "Add a factor" & cb$t == t & cb$v == v]; n <- 1
    while ((k - n) %in% f) n <- n + 1; n }
law_addn <- function(t, v, k, Source, ecan) {
    n <- if (grepl("^Add [0-9]+ factors$", Source)) as.numeric(sub("Add ([0-9]+) factors", "\\1", Source)) else add_chain(t, v, k)
    b <- k - n; N <- ecan(t, b, v); deps <- data.frame(t = t, w = b, v = v, range = FALSE)
    for (j in 2:min(t, n + 1)) { s <- t - j
        e <- if (s >= 2) ecan(s, b - 1, v) else if (s == 1) v else 1
        if (s >= 2) deps <- rbind(deps, data.frame(t = s, w = b - 1, v = v, range = FALSE))
        N <- N + v^(j - 1) * (v - 1) * e }
    list(N = N, deps = deps) }
## Martirosyan-Colbourn (t = 5, 6, k even, h = k/2): N = ecan(t, h, v) +
## (v-1) ecan(t-1, h, v) + ecan(t-2, h, v^2); the third ingredient is a
## table entry only for v <= 5, so only those rows are ARITHMETIC and
## wired (arith_formula_mc.R)
law_mc <- function(t, v, k, Source, ecan) { if (k %% 2 != 0 || v^2 > 25) return(list(N = NA, deps = NULL)); h <- k / 2
    list(N = ecan(t, h, v) + (v - 1) * ecan(t - 1, h, v) + ecan(t - 2, h, v^2),
         deps = data.frame(t = c(t, t - 1, t - 2), w = h, v = c(v, v, v^2), range = FALSE)) }
law_ck <- function(t, v, k, Source, ecan) { if (k %% 2 != 0) return(list(N = NA, deps = NULL))
    list(N = ecan(3, k / 2, v) + (v - 1) * ecan(2, k / 2, v), deps = data.frame(t = c(3, 2), w = k / 2, v = v, range = FALSE)) }

## ---- fuse: the same k at v + m symbols, two rows per symbol fused (arith_formula_fuse.R) ----
law_fuse <- function(t, v, k, Source, ecan) { m <- lengths(regmatches(Source, gregexpr(" fuse", Source)))
    list(N = ecan(t, k, v + m) - 2 * m, deps = data.frame(t = t, w = k, v = v + m, range = FALSE)) }
## ---- Colbourn-Martirosyan-TVT-Walker, strength 3 only (arith_formula_cmtw.R):
## Theorem 3.4 at prime power v, k' = ceiling(k / v); at v + 1 prime power, that row fused ----
is_pp <- function(v) { p <- 2; while (v %% p != 0) p <- p + 1; while (v %% p == 0) v <- v / p; v == 1 }
law_cmtw <- function(t, v, k, Source, ecan) { if (t != 3) return(list(N = NA, deps = NULL))
    if (is_pp(v)) { kk <- ceiling(k / v)
        list(N = ecan(3, kk, v) + (v - 1) * ecan(2, kk, v) + v^3 - v^2, deps = data.frame(t = c(3, 2), w = kk, v = v, range = FALSE)) }
    else if (is_pp(v + 1)) list(N = ecan(3, k, v + 1) - 2, deps = data.frame(t = 3, w = k, v = v + 1, range = FALSE))
    else list(N = NA, deps = NULL) }
## ---- Martirosyan-TVT (arith_formula_mtvt.R): even k, every ingredient at k/2; odd k ("variant"),
## k1 = ceiling(k/2), k2 = floor(k/2) as calibrated; postop rows are bound-only and not wired ----
law_mtvt <- function(t, v, k, Source, ecan) { if (!(t %in% c(5, 6)) || grepl("postop", Source)) return(list(N = NA, deps = NULL))
    k1 <- ceiling(k / 2); k2 <- floor(k / 2)
    N <- if (t == 5) ecan(5, k1, v) + (v - 1) * ecan(4, k1, v) + ecan(2, k2, v) * (ecan(3, k1, v) + ecan(3, k2, v))
         else ecan(6, k1, v) + (v - 1) * ecan(5, k1, v) + ecan(2, k2, v) * (ecan(4, k1, v) + ecan(4, k2, v)) + ecan(3, k1, v) * ecan(3, k2, v)
    deps <- unique(data.frame(t = c(t, t - 1, 2, rep(3:(t - 2), 2)), w = c(k1, k1, k2, rep(c(k1, k2), each = t - 4)), v = v, range = FALSE))
    list(N = N, deps = deps) }

## ---- dispatcher ----
eval_law <- function(family, t, v, k, Source, ecan, ncan, Mtab, kmax2) {
    switch(family,
        "Power CT" = , "Power N-CT" = law_power(t, v, k, Source, ecan, ncan, Mtab),
        "perfect hash family" = law_phf(t, v, k, Source, ecan, ncan),
        "Direct product" = law_dp(t, v, k, Source, ecan, ncan, kmax2[[as.character(v)]]),
        "Derive" = law_derive(t, v, k, Source, ecan),
        "Add n factors" = , "Add a factor" = law_addn(t, v, k, Source, ecan),
        "Martirosyan-Colbourn" = law_mc(t, v, k, Source, ecan),
        "fuse" = law_fuse(t, v, k, Source, ecan),
        "Colbourn-Martirosyan-TVT-Walker" = law_cmtw(t, v, k, Source, ecan),
        "Martirosyan-TVT" = law_mtvt(t, v, k, Source, ecan),
        "Chateauneuf-Kreher doubling" = law_ck(t, v, k, Source, ecan),
        list(N = NA, deps = NULL))
}
