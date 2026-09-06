## arith_formula_cmtw.R - the "Colbourn-Martirosyan-TVT-Walker"
## family (707 rows: 611 plain, 96 with fuse suffixes handled in
## arith_formula_fuse.R), calibrated on every plain row. The paper,
## CMTW 2006, was found open (the authors' copy) on 2026-09-06 and read
## through an automated summary of the pdf, not by eye; the theorem
## numbers and conditions below are that summary's, and the fits do
## not depend on them.
## Strength 3 (28 plain rows), the form the summary calls Theorem 3.4:
##   N = eCAN(3, k', v) + (v - 1) eCAN(2, k', v) + v^3 - v^2,  k' = ceiling(k / v)
## exact on all 23 rows with prime power v (21 with k = v k', 2 at the
## table's k = 10000 cap where k' = ceiling(10000 / v) gives the same
## eCAN values). The 5 rows at v = 10, 18, 22, 24 (v + 1 a prime power)
## equal the v + 1 row of this family at the same k minus 2, the
## fusion reading of arith_formula_fuse.R without the tag; exact on
## all 5 and admitted under that reading.
## Strength 4 (583 plain rows): the pure-CAN strength-4 forms in the
## summary (4.7, a doubling with a CAN(2, k/2, v^2) ingredient; 4.9,
## the prime power doubling with v^2 CAN(2, k/2, v) - v^2) and the
## package's strength-4 Martirosyan-Van Trung form (eCAN(4, c, v) +
## (v - 1) eCAN(3, c, v) + eCAN(2, c, v)^2, c = ceiling(k / 2)) are
## tested below and fit none of the 583 rows; the remaining forms
## carry DCAN (difference covering array) or CODN (covering ordered
## design) numbers the table does not hold. No law admitted, all 583
## ARITH_OPEN. Observation recorded, not admitted: on the 304 rows
## with v | k, the residual N - eCAN(4, k/v, v) - (v - 1) eCAN(3, k/v, v)
## takes few values across k/v at v = 7, 8, 9, 11, 23, 25 (one value on
## all five rows at v = 8, four on 17 rows at v = 7) and varies almost
## row by row at 12 <= v <= 20; a reading of that, as the summary's vk
## form with slowly varying DCAN and CODN values, is a reading only.
## Run from r/livingtable/ (paths adjusted for the repository layout):
##   Rscript arith_formula_cmtw.R | tee results/arith_formula_cmtw_result.txt
suppressMessages(library(CAs)); data(colbournBigFrame); cb <- colbournBigFrame
ec <- function(t, w, v) { r <- tryCatch(eCAN(t, w, v), error = function(e) NULL); if (is.null(r)) NA else as.numeric(r$CAN) }
is_pp <- function(v) { p <- 2; while (v %% p != 0) p <- p + 1; while (v %% p == 0) v <- v / p; v == 1 }
cv <- read.csv("data/engine_coverage.csv", stringsAsFactors = FALSE)
u <- cv[cv$engine_class == "UNRESOLVED", ]

d <- cb[cb$Source == "Colbourn-Martirosyan-TVT-Walker", ]
cat("plain rows:", nrow(d), " by t:", paste(names(table(d$t)), table(d$t), collapse = ", "), "\n")
d$pp <- sapply(d$v, is_pp)
d$route <- NA; d$N_pred <- NA
## strength 3, Theorem 3.4
i3 <- d$t == 3 & d$pp
d$route[i3] <- "3.4"
d$N_pred[i3] <- mapply(function(k, v) { kk <- ceiling(k / v); e3 <- ec(3, kk, v); e2 <- ec(2, kk, v); if (is.na(e3) || is.na(e2)) NA else e3 + (v - 1) * e2 + v^3 - v^2 }, d$k[i3], d$v[i3])
## strength 3, v + 1 prime power: the v + 1 row of the family minus 2
i3f <- d$t == 3 & !d$pp
d$route[i3f] <- "3.4 at v+1, fused"
d$N_pred[i3f] <- mapply(function(k, v) { if (!is_pp(v + 1)) return(NA); e <- ec(3, k, v + 1); if (is.na(e)) NA else e - 2 }, d$k[i3f], d$v[i3f])
d$tier <- ifelse(d$t != 3 | is.na(d$N_pred), "ARITH_OPEN", ifelse(d$N == d$N_pred, "ARITHMETIC", ifelse(d$N > d$N_pred, "ARITH_ABOVE", "ARITH_BELOW")))
cat("\n== strength 3:", sum(d$t == 3), "rows ==\n"); print(table(route = d$route[d$t == 3], tier = d$tier[d$t == 3]))
s3 <- d[d$t == 3, ]; s3$kk <- ceiling(s3$k / s3$v)
print(s3[, c("v","k","N","kk","route","N_pred","tier")], row.names = FALSE)

## strength 4: the pure-CAN forms, tested
s4 <- d[d$t == 4, ]
cat("\n== strength 4:", nrow(s4), "rows, all ARITH_OPEN ==\n")
h <- ceiling(s4$k / 2)
f47 <- mapply(function(k, v, h) if (k %% 2 == 0 && v^2 <= 25) ec(4, h, v) + (v - 1) * ec(3, h, v) + ec(2, h, v^2) else NA, s4$k, s4$v, h)
f49 <- mapply(function(k, v, h) if (k %% 2 == 0 && is_pp(v)) ec(4, h, v) + (v - 1) * ec(3, h, v) + v^2 * ec(2, h, v) - v^2 else NA, s4$k, s4$v, h)
f413 <- mapply(function(v, h) ec(4, h, v) + (v - 1) * ec(3, h, v) + ec(2, h, v)^2, s4$v, h)
cat("pure-CAN forms on the 583 rows: 4.7 evaluable", sum(!is.na(f47)), "exact", sum(s4$N == f47, na.rm = TRUE),
    "; 4.9 evaluable", sum(!is.na(f49)), "exact", sum(s4$N == f49, na.rm = TRUE), "record below it", sum(s4$N < f49, na.rm = TRUE),
    "; package strength-4 form evaluable", sum(!is.na(f413)), "exact", sum(s4$N == f413, na.rm = TRUE), "\n")
cat("k divisible by v:", sum(s4$k %% s4$v == 0), "; k = 10000:", sum(s4$k == 10000), "; prime power v:", sum(s4$pp), "\n")
s4d <- s4[s4$k %% s4$v == 0, ]
s4d$kk <- s4d$k / s4d$v
s4d$resid <- s4d$N - mapply(ec, 4, s4d$kk, s4d$v) - (s4d$v - 1) * mapply(ec, 3, s4d$kk, s4d$v)
pl <- aggregate(resid ~ v, s4d, function(x) length(unique(x)))
rows <- aggregate(resid ~ v, s4d, length)
cat("rows with v | k, per v: rows and distinct residuals N - eCAN(4,k/v,v) - (v-1) eCAN(3,k/v,v):\n")
print(data.frame(v = pl$v, rows = rows$resid, distinct_residuals = pl$resid), row.names = FALSE)
cat("example, v = 7, residual by k/v:\n"); x <- s4d[s4d$v == 7, ]; print(x[order(x$kk), c("kk","N","resid")], row.names = FALSE)

m <- match(paste(u$t, u$v, u$k, u$Source), paste(d$t, d$v, d$k, d$Source))
cat("\nunresolved plain rows:", sum(!is.na(m)), "\n"); print(table(d$tier[m[!is.na(m)]]))
d$family <- "Colbourn-Martirosyan-TVT-Walker"
write.csv(d[, c("family","t","v","k","N","Source","route","N_pred","tier")], "data/arith_formula_cmtw.csv", row.names = FALSE)
cat("\nCMTW RUN DONE\n")
