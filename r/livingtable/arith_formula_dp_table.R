## arith_formula_dp_table.R - the direct product family on the
## FROZEN TABLE (2,120 rows, all strength 2; 2,101 unresolved). The
## tags "Direct product" and "Direct product generalized" name no
## ingredients, so the ingredients are inferred: the table builder
## takes the best pair. Size law (Colbourn, Martirosyan, Mullen,
## Shasha, Sherwood, Yucas 2006; CAs::productCA and create_DPcat.R):
##   N = N1 + N2 - c,  k = k1 * k2,  N_i = eCAN(2, k_i, v),
## with c = v for the generalized product (ingredients supplying v
## constant rows between them; calibrated 174 of 174 on the executed
## DPcat recipes in arith_formula_dp.R) and, tested here, c = 1 for
## the plain product. Calibration on the record: the recorded N must
## equal the MINIMUM over all pairs k1 <= k2 with k1 * k2 >= k of
## N1 + N2 - c, using the frozen table's own eCAN values. That is a
## parameter free check (no free choice of pair).
## RESULT: the plain "Direct product" tag (545 rows) is
## exact on 212 under c = v; on the 103 plain rows (and 19 generalized)
## where the record sits ABOVE the best pair, the implied c = v - (N -
## N_best) runs from 2 to v - 1, consistent with c = min(v, c1 + c2)
## of create_DPcat.R and ingredients short of constant rows (the 10
## rows whose best pair is two orthogonal arrays all have c = 2, one
## constant row each), but the per ingredient counts are not in the
## table, so those rows are not reproduced. The
## "generalized" tag (1,573 rows) is exact on 32 only; on 1,522 the
## record is BELOW the best pair even with c = v, so the generalized
## theorem (Colbourn, Martirosyan, Mullen, Shasha, Sherwood, Yucas 2006,
## paywalled; also Colbourn 2008 "existence tables and projection")
## subtracts more than v or uses ingredients the eCAN lookup does not
## see. Not recovered here; those rows stay open. Tiers: 212
## ARITHMETIC (plain, exact at c = v), 32 ARITH_INFERRED (generalized,
## exact at c = v, possibly coincidental), 2 bound only (postop), the
## rest ARITH_OPEN.
## Run from r/livingtable/ (paths adjusted for the repository layout):
##   Rscript arith_formula_dp_table.R | tee results/arith_formula_dp_table_result.txt
suppressMessages(library(CAs)); data(colbournBigFrame); cb <- colbournBigFrame
p <- cb[grepl("^Direct product", cb$Source), ]
p$generalized <- grepl("generalized", p$Source)
p$postop <- grepl("postop", p$Source)
cat("Direct product rows:", nrow(p), " generalized:", sum(p$generalized), " with postop:", sum(p$postop), "\n")
## per v: the table's N as a function of k (smallest N at k' >= k), t = 2
t2 <- cb[cb$t == 2, ]
Nk_of <- function(v) { s <- t2[t2$v == v, ]; s <- s[order(s$k), ]
    kmax <- max(s$k); out <- rep(NA, kmax)
    ## eCAN(2, k, v) = min N over rows with k' >= k = running min from the right
    Nmin <- rev(cummin(rev(s$N)))
    for (i in seq_len(nrow(s))) { lo <- if (i == 1) 1 else s$k[i - 1] + 1; out[lo:s$k[i]] <- Nmin[i] }
    out }
Nk <- lapply(sort(unique(p$v)), Nk_of); names(Nk) <- sort(unique(p$v))
best_pair <- function(k, v, c) { N <- Nk[[as.character(v)]]; kmax <- length(N)
    best <- Inf; arg <- c(NA, NA)
    for (k1 in 2:min(kmax, floor(sqrt(k)) + 1)) { k2 <- ceiling(k / k1); if (k2 > kmax) next
        val <- N[k1] + N[k2] - c
        if (!is.na(val) && val < best) { best <- val; arg <- c(k1, k2) } }
    c(best, arg) }
res <- t(mapply(function(k, v) c(best_pair(k, v, v), best_pair(k, v, 1)[1]), p$k, p$v))
p$N_gen <- res[, 1]; p$k1 <- res[, 2]; p$k2 <- res[, 3]; p$N_plain <- res[, 4]
p$d_gen <- p$N - p$N_gen; p$d_plain <- p$N - p$N_plain
cat("\n== record vs best product, by tag ==\n")
for (g in c(TRUE, FALSE)) { s <- p[p$generalized == g & !p$postop, ]
    cat(sprintf("%-28s rows %4d | c = v: exact %4d, record below %3d, record above %3d | c = 1: exact %4d\n",
        if (g) "Direct product generalized" else "Direct product", nrow(s),
        sum(s$d_gen == 0), sum(s$d_gen < 0), sum(s$d_gen > 0), sum(s$d_plain == 0))) }
cat("\nrecord above the best generalized product (the product would beat the record; investigate):\n")
ab <- p[p$d_gen > 0 & !p$postop, ]; print(head(ab[order(-ab$d_gen), c("t","v","k","N","Source","N_gen","k1","k2","d_gen")], 30), row.names = FALSE)
cat("\nrecord below the best generalized product (another ingredient reading; first 30):\n")
be <- p[p$d_gen < 0 & !p$postop, ]; print(head(be[order(be$d_gen), c("t","v","k","N","Source","N_gen","N_plain","k1","k2","d_gen","d_plain")], 30), row.names = FALSE)
cat("\nby v (generalized tag, c = v): exact / rows\n")
print(aggregate(cbind(exact = d_gen == 0, rows = 1) ~ v, data = p[p$generalized & !p$postop, ], FUN = sum))
## tier
p$arith_tier <- ifelse(p$postop, "ARITH_BOUND_ONLY",
                ifelse(p$d_gen == 0 & !p$generalized, "ARITHMETIC",
                ifelse(p$d_gen == 0 & p$generalized, "ARITH_INFERRED", "ARITH_OPEN")))
cat("\n== TIERS over all", nrow(p), "direct product rows ==\n"); print(table(p$generalized, p$arith_tier))
cv <- read.csv("data/engine_coverage.csv", stringsAsFactors = FALSE)
u <- cv[cv$engine_class == "UNRESOLVED" & grepl("^Direct product", cv$Source), ]
m <- match(paste(u$t, u$v, u$k, u$Source), paste(p$t, p$v, p$k, p$Source))
cat("unresolved direct product entries:", nrow(u), " matched:", sum(!is.na(m)), "\n"); print(table(p$arith_tier[m], useNA = "ifany"))
write.csv(p[, c("t","v","k","N","Source","generalized","postop","k1","k2","N_gen","N_plain","d_gen","d_plain","arith_tier")], "data/arith_formula_dp_table.csv", row.names = FALSE)
cat("\nDIRECT PRODUCT TABLE RUN DONE\n")
