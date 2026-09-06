## arith_families_probe.R - a pass over the unresolved
## families: (a) "Add a factor" (t = 3, 4) under the Add-1-factor law
## with eCAN(1, ., v) = v at t = 3; (b) a recorded, NOT admitted, blind
## pattern search over the recursive strength 3 and 4 families
## (Colbourn-Martirosyan-TVT-Walker, Cohen-Colbourn-Ling): every row's
## N tested against a N_t(k1) + b N_t(k2) + c N_{t-1}(k1) + d N_{t-1}(k2)
## [+ e N_{t-2}(k1) + f N_{t-2}(k2)] over pairs k1 k2 >= k and small
## coefficient sets in v. A pattern is a LEAD only if one form fits a
## clear majority; a search space this rich fits many rows by chance
## (30 of 60 CCL rows fit something, no form on more than 3), so
## nothing here is admitted without the paper; (c) the TERMINAL families: tags naming a search
## or a published array with no table ingredient (Torres-Jimenez, cover
## starters, Raaphorst-Moura-Stevens, Fix symbols, Add Factor SO,
## Cyclotomy variants, extended OA, Augment OA, Ji-Li-Yin, orthogonal
## array fuse postop, projection postop, Add a symbol). No formula can
## reproduce those and no ingredient change can reach them; they are
## verified only by obtaining the array itself. They are counted apart
## so the "dark" number stops including entries that propagation could
## never touch.
## Pointer: the seven strength-4 "Add a factor"
## rows recorded BELOW the one-factor law here are the n = 2 case of
## the full Add n law in arith_formula_addn.R, exact there;
## arith_tally.R takes "Add a factor" from that file's csv and ignores
## this file's rows for the tag. Section (a) is left as written.
## Second pointer: fused rows whose unfused base is
## in the table (30 Raaphorst-Moura-Stevens, 7 extended OA special, 1
## Cyclotomy) are classified by arith_formula_fuse.R; arith_tally.R
## takes that file's tier for them over section (c) here.
## Run from r/livingtable/ (paths adjusted for the repository layout):
##   Rscript arith_families_probe.R | tee results/arith_families_probe_result.txt
suppressMessages(library(CAs)); data(colbournBigFrame); cb <- colbournBigFrame
ec <- function(t, w, v) { r <- tryCatch(eCAN(t, w, v), error = function(e) NULL); if (is.null(r)) NA else as.numeric(r$CAN) }
cv <- read.csv("data/engine_coverage.csv", stringsAsFactors = FALSE); u <- cv[cv$engine_class == "UNRESOLVED", ]
ukey <- paste(u$t, u$v, u$k, u$Source)

## ---- (a) Add a factor ----
a <- cb[cb$Source == "Add a factor", ]
a$N_pred <- mapply(function(t, k, v) ec(t, k - 1, v) + v * (v - 1) * (if (t - 2 >= 2) ec(t - 2, k - 2, v) else v^(t - 2)), a$t, a$k, a$v)
a$tier <- ifelse(a$N == a$N_pred, "ARITHMETIC", ifelse(a$N < a$N_pred, "ARITH_BELOW", "ARITH_ABOVE"))
cat("== Add a factor:", nrow(a), "rows; exact", sum(a$tier == "ARITHMETIC"), " record below law", sum(a$tier == "ARITH_BELOW"), "(t = 4 only)\n")
print(a[a$tier != "ARITHMETIC", c("t","v","k","N","Source","N_pred")], row.names = FALSE)

## ---- (b) blind pattern search, recorded as leads only ----
Nk <- function(t, v) { s <- cb[cb$t == t & cb$v == v, ]; s <- s[order(s$k), ]; if (!nrow(s)) return(NULL)
    out <- rep(NA, max(s$k)); Nmin <- rev(cummin(rev(s$N)))
    for (i in seq_len(nrow(s))) { lo <- if (i == 1) 1 else s$k[i-1] + 1; out[lo:s$k[i]] <- Nmin[i] }; out }
lab1 <- c("0","1","2","v-2","v-1","v","v+1"); lab2 <- c("0","1","v-1","v","2(v-1)","(v-1)^2","v(v-1)","C(v-1,2)","C(v,2)")
val <- function(l, v) switch(l, "0"=0,"1"=1,"2"=2,"v-2"=v-2,"v-1"=v-1,"v"=v,"v+1"=v+1,"2(v-1)"=2*(v-1),"(v-1)^2"=(v-1)^2,"v(v-1)"=v*(v-1),"C(v-1,2)"=choose(v-1,2),"C(v,2)"=choose(v,2))
blind <- function(fam, tt, maxrows) {
    p <- cb[grepl(fam, cb$Source) & cb$t == tt, ]; set.seed(1); if (nrow(p) > maxrows) p <- p[sample(nrow(p), maxrows), ]
    if (tt >= 4) grid <- expand.grid(a = 0:1, b = 0:1, c = lab1, d = lab1, e = lab2, f = lab2, stringsAsFactors = FALSE)
    else grid <- expand.grid(a = 0:1, b = 0:1, c = c(lab1, lab2[-(1:2)]), d = c(lab1, lab2[-(1:2)]), e = "0", f = "0", stringsAsFactors = FALSE)
    grid <- unique(grid)
    keys <- apply(grid, 1, function(r) sprintf("N%d(k1)*%s + N%d(k2)*%s + N%d(k1)*[%s] + N%d(k2)*[%s]%s", tt, r[1], tt, r[2], tt-1, r[3], tt-1, r[4],
        if (tt >= 4) sprintf(" + N%d(k1)*[%s] + N%d(k2)*[%s]", tt-2, r[5], tt-2, r[6]) else ""))
    hits <- integer(nrow(grid)); rowhit <- rep(FALSE, nrow(p))
    for (i in seq_len(nrow(p))) { v <- p$v[i]; k <- p$k[i]; N <- p$N[i]
        Nt <- Nk(tt, v); Nt1 <- Nk(tt-1, v); Nt2 <- if (tt >= 4) Nk(tt-2, v) else NULL
        G <- cbind(grid$a, grid$b, sapply(grid$c, val, v = v), sapply(grid$d, val, v = v), sapply(grid$e, val, v = v), sapply(grid$f, val, v = v))
        hit_i <- rep(FALSE, nrow(grid))
        for (k1 in 2:min(length(Nt), floor(sqrt(k)) + 1)) { k2 <- ceiling(k / k1); if (k2 < k1 || k2 > length(Nt)) next
            x <- c(Nt[k1], Nt[k2], Nt1[k1], Nt1[k2], if (tt >= 4) c(Nt2[k1], Nt2[k2]) else c(0, 0)); if (any(is.na(x))) next
            hit_i <- hit_i | (as.vector(G %*% x) == N) }
        hits <- hits + hit_i; rowhit[i] <- any(hit_i) }
    cat(sprintf("\n== blind search %s t = %d: %d rows sampled, %d fit some pattern; top forms:\n", fam, tt, nrow(p), sum(rowhit)))
    o <- order(-hits)[1:5]; print(data.frame(pattern = keys[o], rows = hits[o]), row.names = FALSE)
}
blind("^Colbourn-Martirosyan-TVT-Walker$", 3, 28)
blind("^Cohen-Colbourn-Ling$", 3, 60)
blind("^Colbourn-Martirosyan-TVT-Walker$", 4, 40)
cat("\nReading: CMTW t = 3 has one form on 23 of 28 rows, N3(k2) + (v-1)(N2(k1) + N2(k2)) with k = k1 k2,\n",
    "a LEAD to check against the paper; t = 4 and CCL show no dominant form. Nothing admitted.\n")

## ---- (c) terminal families among the unresolved ----
term_pat <- "^(Torres|cover starter|Cover starter|Raaphorst|Fix [0-9]|Add Factor SO|Cyclotomy|extended OA|Augment OA|Ji-Li-Yin|orthogonal array|projection|Add a symbol|Kleitman|Nurmela|Walker|Hartman|Meagher|Sherwood|Kokkala|IPO|Paley|simulated annealing|Tabu|tabu|Cohen SA|SA |CS_)"
term <- u[grepl(term_pat, u$Source), ]
cat("\n== TERMINAL families among the unresolved (search results or published arrays, no table ingredient):", nrow(term), "entries ==\n")
print(sort(table(sub("^([A-Za-z-]+( [a-z]+)?).*", "\\1", term$Source)), decreasing = TRUE))
cat("status of those entries in the sweep:"); print(table(term$status))
out <- rbind(data.frame(key = paste(a$t, a$v, a$k, a$Source), tier = a$tier, family = "Add a factor"),
             data.frame(key = paste(term$t, term$v, term$k, term$Source), tier = "TERMINAL_CLAIMED", family = "terminal (search or published array)"))
out <- out[!duplicated(out$key), ]
write.csv(out, "data/arith_families_probe.csv", row.names = FALSE)
cat("\nFAMILIES PROBE DONE\n")
