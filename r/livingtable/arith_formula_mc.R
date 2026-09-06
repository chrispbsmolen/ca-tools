## arith_formula_mc.R - the "Martirosyan-Colbourn" family
## (155 rows, t = 5 and 6, every k even), calibrated on EVERY row of
## the family in the frozen table. No copy of the Martirosyan and
## Colbourn paper was available; the law below is
## recovered from the record alone. In shape it is the strength-5 and
## 6 form of Theorem 4.7 of Colbourn, Martirosyan, Van Trung and
## Walker (2006), CAN(4, 2k, v) <= CAN(4, k, v) + (v - 1) CAN(3, k, v)
## + CAN(2, k, v^2), as read on 2026-09-06 through an automated summary
## of the authors' open copy, not by eye (see arith_formula_cmtw.R);
## that is a reading of a paper, not a computed fact. With h = k / 2:
##   N = eCAN(t, h, v) + (v - 1) eCAN(t - 1, h, v) + eCAN(t - 2, h, v^2)
## The third ingredient is a table entry only for v <= 5 (v^2 <= 25).
## For v >= 6 the record uses one k-independent number per (t, v),
## seven constants in all, each read from the record and each equal
## to 2 q^(t-2) - 1 - 2 (q - v^2) with q the least prime power >= v^2.
## Observation, not a claim: that reads as a strength-(t-2) array on
## q symbols with 2 q^(t-2) - 1 rows, fused down to v^2 symbols at two
## rows per symbol. At t = 5 the table itself supports it: 2 q^3 - 1 is
## its Raaphorst-Moura-Stevens size at k = q^2 + q + 1, and the (5, 6)
## rows end at h = 1407 = 37^2 + 37 + 1. At t = 6 the table holds no
## strength-4 analogue, so the (6, 6) constant is fitted only. Those
## 117 rows reproduce exactly but their third ingredient is not a
## table entry, so they are ARITH_INFERRED, not ARITHMETIC, and they
## are not wired into the engine; a change to eCAN(t, h, v) or
## eCAN(t - 1, h, v) would still move them by the same sum, noted for
## the engine as a later option.
## Run from r/livingtable/ (paths adjusted for the repository layout):
##   Rscript arith_formula_mc.R | tee results/arith_formula_mc_result.txt
suppressMessages(library(CAs)); data(colbournBigFrame); cb <- colbournBigFrame
ec <- function(t, w, v) { r <- tryCatch(eCAN(t, w, v), error = function(e) NULL); if (is.null(r)) NA else as.numeric(r$CAN) }
is_pp <- function(v) { p <- 2; while (v %% p != 0) p <- p + 1; while (v %% p == 0) v <- v / p; v == 1 }
least_pp_ge <- function(w) { q <- w; while (!is_pp(q)) q <- q + 1; q }
cv <- read.csv("data/engine_coverage.csv", stringsAsFactors = FALSE)
u <- cv[cv$engine_class == "UNRESOLVED", ]

d <- cb[cb$Source == "Martirosyan-Colbourn", ]
cat("Martirosyan-Colbourn rows:", nrow(d), " even k:", sum(d$k %% 2 == 0), " by (t, v):\n"); print(table(d$t, d$v))
d$h <- d$k / 2
d$e_t  <- mapply(ec, d$t, d$h, d$v)
d$e_t1 <- mapply(ec, d$t - 1, d$h, d$v)
d$e_t2sq <- mapply(function(t, h, v) if (v^2 <= 25) ec(t - 2, h, v^2) else NA, d$t, d$h, d$v)
d$resid <- d$N - d$e_t - (d$v - 1) * d$e_t1

## rows with the third ingredient in the table (v <= 5)
d$N_pred <- d$e_t + (d$v - 1) * d$e_t1 + d$e_t2sq
d$tier <- ifelse(is.na(d$N_pred), NA, ifelse(d$N == d$N_pred, "ARITHMETIC", ifelse(d$N > d$N_pred, "ARITH_ABOVE", "ARITH_BELOW")))
cat("\n== v <= 5, third ingredient eCAN(t-2, h, v^2) from the table:", sum(!is.na(d$N_pred)), "rows ==\n"); print(table(d$tier[!is.na(d$N_pred)]))
ab <- d[!is.na(d$tier) & d$tier != "ARITHMETIC", ]
if (nrow(ab)) { ab$diff <- ab$N - ab$N_pred; print(ab[, c("t","v","k","N","N_pred","diff","e_t","e_t1","e_t2sq")], row.names = FALSE) }

## rows with v >= 6: the residual is one constant per (t, v)
big <- d[is.na(d$N_pred), ]
cst <- aggregate(resid ~ t + v, big, function(x) length(unique(x)))
cat("\n== v >= 6:", nrow(big), "rows; distinct residuals per (t, v) (must all be 1 for a constant reading) ==\n")
print(cst, row.names = FALSE)
K <- aggregate(resid ~ t + v, big, unique); names(K)[3] <- "C"
K$q <- sapply(K$v, function(v) least_pp_ge(v^2))
K$closed <- 2 * K$q^(K$t - 2) - 1 - 2 * (K$q - K$v^2)
K$rows <- sapply(seq_len(nrow(K)), function(i) sum(big$t == K$t[i] & big$v == K$v[i]))
K$hmax <- sapply(seq_len(nrow(K)), function(i) max(big$h[big$t == K$t[i] & big$v == K$v[i]]))
cat("\nthe seven constants, each against 2 q^(t-2) - 1 - 2 (q - v^2), q the least prime power >= v^2:\n"); print(K, row.names = FALSE)
cat("constants equal to the closed form:", sum(K$C == K$closed), "of", nrow(K), "\n")
big$C <- K$C[match(paste(big$t, big$v), paste(K$t, K$v))]
big$N_pred <- big$e_t + (big$v - 1) * big$e_t1 + big$C
big$tier <- ifelse(big$N == big$N_pred, "ARITH_INFERRED", ifelse(big$N > big$N_pred, "ARITH_ABOVE", "ARITH_BELOW"))
cat("v >= 6 rows reproduced with the constant:", sum(big$tier == "ARITH_INFERRED"), "of", nrow(big), "\n")
d[is.na(d$tier), c("N_pred", "tier")] <- big[, c("N_pred", "tier")]

cat("\n== all rows by tier ==\n"); print(table(d$tier))
m <- match(paste(u$t, u$v, u$k, u$Source), paste(d$t, d$v, d$k, d$Source))
cat("unresolved entries in the family:", sum(!is.na(m)), "\n"); print(table(d$tier[m[!is.na(m)]]))
d$family <- "Martirosyan-Colbourn"
write.csv(d[, c("family","t","v","k","N","Source","N_pred","tier")], "data/arith_formula_mc.csv", row.names = FALSE)
cat("\nMARTIROSYAN-COLBOURN RUN DONE\n")
