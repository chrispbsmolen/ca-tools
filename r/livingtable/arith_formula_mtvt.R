## arith_formula_mtvt.R - the "Martirosyan-TVT" family (372
## rows, t = 5 and 6; tags "Martirosyan-TVT" 206, all even k;
## "Martirosyan-TVT variant" 160, all odd k; "Martirosyan-TVT postop
## NCK" 6), calibrated on every row. Read from the base first: the CAs
## package (0.24) implements Martirosyan and Van Trung (2004) Section 4
## in MTVTRouxtypeCA, and its N_upper_MTVTRouxtypeCA(theoretical =
## TRUE) states a size law, which the package attributes to their
## Theorem 4.13 (the paper is not on record here), at strengths 4 and
## 5 with every ingredient at c = ceiling(k / 2) columns:
##   t = 4:  N = eCAN(4, c, v) + (v - 1) eCAN(3, c, v) + eCAN(2, c, v)^2
##   t = 5:  N = eCAN(5, c, v) + (v - 1) eCAN(4, c, v) + 2 eCAN(3, c, v) eCAN(2, c, v)
## The strength-6 form is the same shape one strength up, read off the
## record (the package stops at 5):
##   t = 6:  N = eCAN(6, c, v) + (v - 1) eCAN(5, c, v) + 2 eCAN(4, c, v) eCAN(2, c, v) + eCAN(3, c, v)^2
## Exact on all 206 even-k rows (66 at t = 5 through the package's
## formula, 140 at t = 6 through the extension). The package's own
## source notes that its strength-5 construction "appears to be wrong
## (and uses more runs)"; what is calibrated here is the size law the
## record uses, not the built array.
## "variant", odd k = k1 + k2 with k1 = ceiling(k / 2), k2 = floor(k / 2):
## the width of every ingredient was searched over {k1, k2} per row
## and the one assignment common to every row taken:
##   t = 5:  N = eCAN(5, k1, v) + (v - 1) eCAN(4, k1, v) + eCAN(2, k2, v) [eCAN(3, k1, v) + eCAN(3, k2, v)]
##   t = 6:  N = eCAN(6, k1, v) + (v - 1) eCAN(5, k1, v) + eCAN(2, k2, v) [eCAN(4, k1, v) + eCAN(4, k2, v)] + eCAN(3, k1, v) eCAN(3, k2, v)
## which at k1 = k2 is the even-k law. Exact on all 160. The width
## assignment is read from the fit, not from the paper, and it is the
## unique full fit in the search below; the nearest rival assignment
## misses 2 rows at t = 5 and 6 at t = 6, the width of the strength-5
## top ingredient rests on 2 rows, and the even-k law at
## k1 fits no variant row.
## "postop NCK" (6 rows, t = 6, v = 6, k = 11..16): post-optimized
## arrays; the even-k law at ceiling(k / 2) is a bound only there,
## ARITH_BOUND_ONLY as for the direct product's postop tags.
## Run from r/livingtable/ (paths adjusted for the repository layout):
##   Rscript arith_formula_mtvt.R | tee results/arith_formula_mtvt_result.txt
suppressMessages(library(CAs)); data(colbournBigFrame); cb <- colbournBigFrame
ec <- function(t, w, v) { r <- tryCatch(eCAN(t, w, v), error = function(e) NULL); if (is.null(r)) NA else as.numeric(r$CAN) }
cv <- read.csv("data/engine_coverage.csv", stringsAsFactors = FALSE)
u <- cv[cv$engine_class == "UNRESOLVED", ]

law_even <- function(t, v, c) { e <- sapply(2:t, ec, w = c, v = v); names(e) <- 2:t; if (any(is.na(e))) return(NA)
    if (t == 5) e["5"] + (v - 1) * e["4"] + 2 * e["3"] * e["2"]
    else if (t == 6) e["6"] + (v - 1) * e["5"] + 2 * e["4"] * e["2"] + e["3"]^2
    else NA }
law_odd <- function(t, v, k1, k2) {
    if (t == 5) ec(5, k1, v) + (v - 1) * ec(4, k1, v) + ec(2, k2, v) * (ec(3, k1, v) + ec(3, k2, v))
    else if (t == 6) ec(6, k1, v) + (v - 1) * ec(5, k1, v) + ec(2, k2, v) * (ec(4, k1, v) + ec(4, k2, v)) + ec(3, k1, v) * ec(3, k2, v)
    else NA }

d <- cb[grepl("^Martirosyan-TVT", cb$Source), ]
d$kind <- ifelse(d$Source == "Martirosyan-TVT", "plain", ifelse(grepl("variant", d$Source), "variant", "postop"))
cat("rows:", nrow(d), "\n"); print(table(kind = d$kind, t = d$t)); cat("odd k by kind:\n"); print(table(kind = d$kind, odd = d$k %% 2 == 1))
d$k1 <- ceiling(d$k / 2); d$k2 <- floor(d$k / 2)
d$N_pred <- mapply(function(t, v, k1, k2, kind) if (kind == "variant") law_odd(t, v, k1, k2) else law_even(t, v, k1), d$t, d$v, d$k1, d$k2, d$kind)
d$tier <- ifelse(is.na(d$N_pred), "ARITH_OPEN", ifelse(d$kind == "postop", "ARITH_BOUND_ONLY",
          ifelse(d$N == d$N_pred, "ARITHMETIC", ifelse(d$N > d$N_pred, "ARITH_ABOVE", "ARITH_BELOW"))))
cat("\n== tiers by kind ==\n"); print(table(kind = d$kind, tier = d$tier))
cat("plain rows exact by t:\n"); print(table(t = d$t[d$kind == "plain"], exact = (d$N == d$N_pred)[d$kind == "plain"]))
cat("postop rows (bound only): record against the law\n"); print(d[d$kind == "postop", c("t","v","k","N","N_pred")], row.names = FALSE)

## the width search that found the variant assignment: every ingredient at k1 or k2,
## the assignments that fit each row, intersected over the rows of each t
cat("\n== variant width search (0 = k1, 1 = k2) ==\n")
for (tt in c(5, 6)) {
    vr <- d[d$kind == "variant" & d$t == tt, ]
    nf <- if (tt == 5) 6 else 8
    grid <- as.matrix(expand.grid(rep(list(0:1), nf)))
    common <- NULL
    for (i in seq_len(nrow(vr))) {
        v <- vr$v[i]; N <- vr$N[i]; ks <- c(vr$k1[i], vr$k2[i])
        fits <- apply(grid, 1, function(w) { W <- ks[w + 1]
            p <- if (tt == 5) ec(5, W[1], v) + (v - 1) * ec(4, W[2], v) + ec(3, W[3], v) * ec(2, W[4], v) + ec(2, W[5], v) * ec(3, W[6], v)
                 else ec(6, W[1], v) + (v - 1) * ec(5, W[2], v) + ec(4, W[3], v) * ec(2, W[4], v) + ec(2, W[5], v) * ec(4, W[6], v) + ec(3, W[7], v) * ec(3, W[8], v)
            !is.na(p) && p == N })
        common <- if (is.null(common)) which(fits) else intersect(common, which(fits)) }
    cat("t =", tt, ":", nrow(vr), "rows; assignments common to all rows:", length(common), "\n")
    if (length(common)) print(grid[common, , drop = FALSE])
    cat("  (columns:", if (tt == 5) "e5 e4 e3 e2 | e2 e3" else "e6 e5 e4 e2 | e2 e4 | e3 e3", "; the common assignments are one expression in its orderings)\n")
}

m <- match(paste(u$t, u$v, u$k, u$Source), paste(d$t, d$v, d$k, d$Source))
cat("\nunresolved rows in the family:", sum(!is.na(m)), "\n"); print(table(d$tier[m[!is.na(m)]]))
d$family <- "Martirosyan-TVT"
write.csv(d[, c("family","t","v","k","N","Source","kind","N_pred","tier")], "data/arith_formula_mtvt.csv", row.names = FALSE)
cat("\nMARTIROSYAN-TVT RUN DONE\n")
