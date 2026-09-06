## arith_engine.R - the ARITHMETIC tier wired as an engine organ. The living table is the frozen record (13,641 rows of
## colbournBigFrame) plus verified improvements; the ARITHMETIC entries
## (data/arith_tally.csv, tier ARITHMETIC) are recomputed from it by the
## laws in arith_laws.R, and every lookup an entry makes is recorded as
## an arithmetic edge (data/arith_edges.csv: child entry -> ingredient
## lookup (t, w, v) and the table row that currently answers it).
## Two propagation modes, contracted to agree on the CLOSURE (each is
## iterated to a fixpoint, since an ARITHMETIC entry can itself be the
## ingredient of another, e.g. the Add-1-factor chains):
##   sweep  recompute every ARITHMETIC entry from the updated table,
##          apply the changes, repeat until nothing moves
##   graph  recompute only the entries whose recorded lookups an
##          improvement can move (same t and v, lookup width <= the
##          improved k, and the improvement below the lookup's answer;
##          a direct product entry is a candidate for any t = 2 change
##          at its v), apply, and repeat with the changed entries as
##          the next round's improvements
## An ARITHMETIC recomputation is a size relation over claims; nothing
## here is verified, and the output tier is ARITHMETIC, below EXECUTED
## and SCREEN4, as the tier's claim rule requires.
## Usage (from r/livingtable/; paths adjusted for the repository layout):
##   Rscript arith_engine.R identity                 the frozen record must reproduce itself
##   Rscript arith_engine.R propagate improvements.csv   columns t,k,v,N (new best sizes)
##   Rscript arith_engine.R demo                     improvements = data/better_verified.csv
## Outputs: data/arith_edges.csv (identity run; one row per distinct
## child -> lookup pair with its multiplicity, range rows for the
## direct product carry no answering row) and the cascade files named
## below.
## Improvements are validated: known (t, v), integer N >= v^t, k >= t,
## N below the current lookup; k beyond the table's widest row is
## clamped (the offered k is kept in the report). An improvement may
## carry an nconst column, the constant rows its array is known to
## have (CAs::maxconstant on the built array); absent, it is credited
## with one, the only number any covering array guarantees. Laws that
## assume v constant rows (c flags, the direct product) credit an
## improved ingredient only for what it carries.
## Result files: results/arith_engine_identity_result.txt (identity),
## results/arith_engine_demo_result.txt and data/arith_cascade.csv (demo),
## and for propagate, data/arith_cascade_<file>.csv (the improvements
## file path is used as given).
suppressMessages(library(CAs)); data(colbournBigFrame); cb <- colbournBigFrame
source("arith_laws.R")
Mtab <- read.csv("data/arith_power_Mtable.csv", stringsAsFactors = FALSE)
tal <- read.csv("data/arith_tally.csv", stringsAsFactors = FALSE)
ar <- tal[tal$arith_tier == "ARITHMETIC", ]
cat("ARITHMETIC entries:", nrow(ar), " by family:", paste(names(table(ar$arith_family)), table(ar$arith_family), collapse = "; "), "\n")

## ---- the living table lookup: ecan(t, w, v) = min N over rows with k >= w ----
LT <- new.env()
build_lookup <- function(tab) {
    LT$kmax <- list(); LT$Nk <- list(); LT$who <- list(); LT$nc <- list()
    for (key in unique(paste(tab$t, tab$v))) {
        tv <- strsplit(key, " ")[[1]]; s <- tab[tab$t == tv[1] & tab$v == tv[2], ]; s <- s[order(s$k), ]
        km <- max(s$k); Nk <- rep(NA_real_, km); who <- rep(NA_real_, km)
        ## running minimum from the right: the smallest N at any k' >= w, and the k' that attains it
        best <- Inf; bk <- NA
        for (i in nrow(s):1) { if (s$N[i] < best) { best <- s$N[i]; bk <- s$k[i] }
            lo <- if (i == 1) 1 else s$k[i - 1] + 1; Nk[lo:s$k[i]] <- best; who[lo:s$k[i]] <- bk }
        LT$kmax[[key]] <- km; LT$Nk[[key]] <- Nk; LT$who[[key]] <- who; LT$nc[[key]] <- rep(NA_real_, km) }
}
ecan <- function(t, w, v) { key <- paste(t, v); Nk <- LT$Nk[[key]]; if (is.null(Nk) || w < 1 || w > length(Nk)) return(NA_real_); Nk[w] }
whok <- function(t, w, v) { key <- paste(t, v); who <- LT$who[[key]]; if (is.null(who) || w < 1 || w > length(who)) return(NA_real_); who[w] }
ncan <- function(t, w, v) { key <- paste(t, v); nc <- LT$nc[[key]]; if (is.null(nc) || w < 1 || w > length(nc)) return(NA_real_); nc[w] }
apply_improvement <- function(t, k, v, N, nconst = 1) {
    key <- paste(t, v); Nk <- LT$Nk[[key]]; if (is.null(Nk)) return(invisible(FALSE))
    kk <- min(k, length(Nk)); idx <- 1:kk; hit <- Nk[idx] > N
    LT$Nk[[key]][idx][hit] <- N; LT$who[[key]][idx][hit] <- k; LT$nc[[key]][idx][hit] <- nconst
    ## a tie in N keeps the larger constant-row credit (order independence within a batch)
    tie <- Nk[idx] == N & !is.na(LT$nc[[key]][idx]) & LT$nc[[key]][idx] < nconst
    LT$nc[[key]][idx][tie] <- nconst; invisible(any(hit))
}
kmax2 <- function() { out <- list(); for (key in names(LT$kmax)) { tv <- strsplit(key, " ")[[1]]; if (tv[1] == "2") out[[tv[2]]] <- LT$kmax[[key]] }; out }
base <- cb[, c("t", "k", "v", "N")]
build_lookup(base); K2 <- kmax2()

recompute <- function(idx) {
    lapply(idx, function(i) eval_law(ar$arith_family[i], ar$t[i], ar$v[i], ar$k[i], ar$Source[i], ecan, ncan, Mtab, K2))
}

mode <- commandArgs(TRUE)[1]; if (is.na(mode)) mode <- "identity"

## ---- identity: the frozen record reproduces itself, and the edges are written ----
t0 <- Sys.time()
res0 <- recompute(seq_len(nrow(ar)))
N0 <- sapply(res0, `[[`, "N")
cat(sprintf("identity: %d of %d ARITHMETIC entries reproduce their recorded N from the frozen record (%.1f s)\n",
            sum(N0 == ar$N, na.rm = TRUE), nrow(ar), as.numeric(Sys.time() - t0, units = "secs")))
bad <- which(is.na(N0) | N0 != ar$N)
if (length(bad)) { cat("IDENTITY FAILURES (engine law disagrees with the calibration script):\n"); print(ar[bad, c("t","v","k","N","Source","arith_family")], row.names = FALSE); print(N0[bad]) }
if (mode == "identity") {
    edges <- do.call(rbind, lapply(seq_len(nrow(ar)), function(i) { d <- res0[[i]]$deps; if (is.null(d)) return(NULL)
        d <- aggregate(list(mult = rep(1, nrow(d))), by = d[, c("t", "w", "v", "range")], FUN = sum)
        data.frame(child_t = ar$t[i], child_v = ar$v[i], child_k = ar$k[i], child_N = ar$N[i], child_Source = ar$Source[i],
                   family = ar$arith_family[i], ing_t = d$t, ing_w = d$w, ing_v = d$v, ing_range = d$range, mult = d$mult,
                   ing_N_now = ifelse(d$range, NA, mapply(ecan, d$t, d$w, d$v)), ing_k_now = ifelse(d$range, NA, mapply(whok, d$t, d$w, d$v)),
                   confidence = "ARITHMETIC", stamp_date = "2026-09-06", stringsAsFactors = FALSE) }))
    write.csv(edges, "data/arith_edges.csv", row.names = FALSE)
    nr <- edges[!edges$ing_range, ]
    cat("data/arith_edges.csv:", nrow(edges), "distinct child->lookup edges (multiplicity in mult, total lookups", sum(edges$mult), ");",
        sum(edges$ing_range), "range edges (direct product, any t = 2 row at that v);",
        length(unique(paste(nr$ing_t, nr$ing_k_now, nr$ing_v))), "distinct table rows answer the non-range lookups\n")
    ## the record's own structure: which ingredient rows feed the most distinct dependents
    top <- sort(table(paste0("(", nr$ing_t, ",", nr$ing_k_now, ",", nr$ing_v, ")")[!duplicated(nr[, c("child_t","child_v","child_k","child_Source","ing_t","ing_k_now","ing_v")])]), decreasing = TRUE)
    cat("ingredient rows feeding the most distinct ARITHMETIC entries (t,k,v): ", paste(names(head(top, 8)), head(top, 8), collapse = "; "), "\n")
    ## how many ARITHMETIC entries are themselves ingredients of others (the reason propagation iterates)
    ck <- paste(ar$t, ar$k, ar$v); ik <- paste(nr$ing_t, nr$ing_k_now, nr$ing_v)
    cat("ARITHMETIC entries that are ingredients of other ARITHMETIC entries:", length(unique(ik[ik %in% ck])), "\n")
    cat("IDENTITY DONE\n"); quit(save = "no")
}

## ---- propagation ----
impfile <- if (mode == "demo") "data/better_verified.csv" else commandArgs(TRUE)[2]
imp <- if (mode == "demo") { b <- read.csv("data/better_verified.csv", stringsAsFactors = FALSE); b <- b[b$verified %in% TRUE, ]
        data.frame(t = b$t, k = b$k, v = b$v, N = b$N_built) } else read.csv(impfile, stringsAsFactors = FALSE)
if (is.null(imp$nconst)) imp$nconst <- 1
imp$nconst[is.na(imp$nconst)] <- 1
imp$k_offered <- imp$k
## validation
ok <- rep(TRUE, nrow(imp)); why <- rep("", nrow(imp))
for (j in seq_len(nrow(imp))) { key <- paste(imp$t[j], imp$v[j])
    if (is.null(LT$Nk[[key]])) { ok[j] <- FALSE; why[j] <- "no (t, v) in the table" }
    else if (imp$N[j] != round(imp$N[j]) || imp$k[j] != round(imp$k[j]) || imp$k[j] < imp$t[j]) { ok[j] <- FALSE; why[j] <- "N and k must be integers with k >= t" }
    else if (imp$N[j] < imp$v[j]^imp$t[j]) { ok[j] <- FALSE; why[j] <- "below the trivial bound v^t" }
    else if (imp$nconst[j] < 1 || imp$nconst[j] > imp$v[j]) { ok[j] <- FALSE; why[j] <- "nconst must be between 1 and v" }
    else { if (imp$k[j] > LT$kmax[[key]]) { why[j] <- sprintf("k clamped to the table's widest row %d", LT$kmax[[key]]); imp$k[j] <- LT$kmax[[key]] }
        if (!(ecan(imp$t[j], imp$k[j], imp$v[j]) > imp$N[j])) { ok[j] <- FALSE; why[j] <- "does not beat the current table" } } }
cat("\nimprovements offered:", nrow(imp), " accepted:", sum(ok), "\n"); print(cbind(imp[, c("t","k_offered","v","N","nconst")], note = why), row.names = FALSE)
imp <- imp[ok, ]
if (!nrow(imp)) { cat("no accepted improvement; nothing to propagate\nPROPAGATION DONE\n"); quit(save = "no") }
## dependency index for graph mode: every recorded lookup with its entry
deps_all <- lapply(res0, `[[`, "deps")
DX <- do.call(rbind, lapply(seq_along(deps_all), function(i) { d <- deps_all[[i]]; if (is.null(d)) NULL else cbind(entry = i, d) }))
candidates <- function(cur) { c0 <- rep(FALSE, nrow(ar))
    for (j in seq_len(nrow(cur))) { h <- DX$t == cur$t[j] & DX$v == cur$v[j] & (DX$range | (DX$w <= cur$k[j] & mapply(ecan, DX$t, DX$w, DX$v) > cur$N[j]))
        c0[unique(DX$entry[h])] <- TRUE }
    c0 }
direct <- candidates(imp)   ## read on the untouched table, for the report
direct_via <- sapply(seq_len(nrow(ar)), function(i) if (!direct[i]) "" else { d <- deps_all[[i]]
    hits <- unlist(lapply(seq_len(nrow(imp)), function(j) if (any(d$t == imp$t[j] & d$v == imp$v[j] & (d$range | d$w <= imp$k[j])))
        sprintf("(%d,%d,%d)->%d", imp$t[j], imp$k_offered[j], imp$v[j], imp$N[j])))
    paste(unique(hits), collapse = " ") })
## graph mode: rounds of candidates from the current improvements, applied, until no entry moves
Ncur_G <- ar$N; round <- 0; cur <- imp
snap <- list(Nk = LT$Nk, who = LT$who, nc = LT$nc)
t1 <- Sys.time()
while (nrow(cur)) { round <- round + 1
    cand <- candidates(cur)
    for (j in seq_len(nrow(cur))) apply_improvement(cur$t[j], cur$k[j], cur$v[j], cur$N[j], cur$nconst[j])
    NG <- sapply(recompute(which(cand)), `[[`, "N"); ch <- which(cand)[!is.na(NG) & NG < Ncur_G[cand]]
    cat(sprintf("graph mode round %d: candidates %d, changed %d\n", round, sum(cand), length(ch)))
    Ncur_G[ch] <- NG[match(ch, which(cand))]
    ## a propagated entry is a claim with no array behind it: it is credited with one constant row
    cur <- if (length(ch)) data.frame(t = ar$t[ch], k = ar$k[ch], v = ar$v[ch], N = Ncur_G[ch], nconst = 1) else cur[0, ] }
cat(sprintf("graph mode: %d entries change in %d rounds (%.1f s)\n", sum(Ncur_G < ar$N), round, as.numeric(Sys.time() - t1, units = "secs")))
## sweep mode from the same starting table: full recompute, apply, repeat
LT$Nk <- snap$Nk; LT$who <- snap$who; LT$nc <- snap$nc
for (j in seq_len(nrow(imp))) apply_improvement(imp$t[j], imp$k[j], imp$v[j], imp$N[j], imp$nconst[j])
Ncur_S <- ar$N; sround <- 0; t2 <- Sys.time()
repeat { sround <- sround + 1
    NS <- sapply(recompute(seq_len(nrow(ar))), `[[`, "N"); ch <- which(!is.na(NS) & NS < Ncur_S)
    cat(sprintf("sweep mode round %d: changed %d\n", sround, length(ch)))
    if (!length(ch)) break
    Ncur_S[ch] <- NS[ch]
    for (i in ch) apply_improvement(ar$t[i], ar$k[i], ar$v[i], Ncur_S[i], 1) }
cat(sprintf("sweep mode: %d entries change, stable after %d rounds (%.1f s)\n", sum(Ncur_S < ar$N), sround, as.numeric(Sys.time() - t2, units = "secs")))
agree <- all(Ncur_G == Ncur_S)
cat("TWO-MODE AGREEMENT ON THE CLOSURE:", if (agree) "PASS" else "FAIL (sweep wins; investigate graph mode)", "\n")
changed <- which(Ncur_S < ar$N)
casc <- ar[changed, c("t","v","k","N","Source","arith_family"), drop = FALSE]
casc$N_new <- Ncur_S[changed]; casc$delta <- casc$N_new - casc$N
casc$via <- if (length(changed)) ifelse(direct_via[changed] != "", direct_via[changed], "via another ARITHMETIC entry") else character(0)
casc$tier <- rep("ARITHMETIC", nrow(casc))
outfile <- if (mode == "demo") "data/arith_cascade.csv" else paste0("data/arith_cascade_", sub("\\.csv$", "", basename(impfile)), ".csv")
write.csv(casc, outfile, row.names = FALSE)
cat("\n== CLOSURE:", nrow(casc), "ARITHMETIC entries improve (claims propagated from the improvements) ==\n")
if (nrow(casc)) print(casc[order(casc$t, casc$v, casc$k), c("t","v","k","N","N_new","delta","Source","via")], row.names = FALSE)
cat("total rows saved across the closure:", -sum(casc$delta), " written:", outfile, "\n")
cat("PROPAGATION DONE\n")
