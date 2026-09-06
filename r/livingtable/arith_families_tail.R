## arith_families_tail.R - the last 39 not-attempted rows
## outside the paper-blocked families (Cohen-Colbourn-Ling and the
## PCA products), read one tag at a time:
##   perfect hash familyD16,k,a^na b^nb (8 rows, t = 6): read as a
##     heterogeneous hash family of 16 rows over k columns, na of its
##     rows on a symbols and nb on b symbols (na + nb = 16 on all 8;
##     the D as in the DHHF2CA law already on record), each row
##     composed with the table's CA(6, w, v) at its own w;
##     N = na (eCAN(6, a, v) - 1) + nb (eCAN(6, b, v) - 1) + 1, one row
##     lost per ingredient and one constant row kept. Exact on 8 of 8;
##     ARITHMETIC. The reading of a and b as symbol counts per row is
##     the fit's, not a paper's; k = a b on all three tags supports it.
##     The +1 is one row above what the on-record hash_law gives with
##     rho = 1 on 16 rows (its chi is 0 there), so this is a separate
##     8-row calibration, and the branch never consults the
##     constant-row count of an improved ingredient.
##   Chateauneuf-Kreher doubling postop NCK (5 rows): the doubling law
##     at ceiling(k / 2) is a bound, the record below it on all 5;
##     ARITH_BOUND_ONLY.
##   The rest (26 rows): direct or published constructions with no
##     table ingredient (Brick by Brick, Cyclic, Cyclic derived, Holey
##     and Incomplete Transversal Design, Ji-Yin, Li-Ji-Yin, PGL and
##     its postop rows, Two-stage, Xu-Ji-Dong, double proj postop);
##     TERMINAL_CLAIMED, 25 of them with no table ingredient. The
##     26th, "Cyclic, derived" (5, 503, 2) = 503, has one: its
##     ingredient (6, 504, 2) = 1008 is a table entry and the derive
##     law gives floor(1008 / 2) = 504, one above the record, so the
##     record's derivation is sharper than the law; it is kept
##     TERMINAL here as a published array, with the note that an
##     ingredient at 1005 rows or fewer would reach it.
## Run from r/livingtable/ (paths adjusted for the repository layout):
##   Rscript arith_families_tail.R | tee results/arith_families_tail_result.txt
suppressMessages(library(CAs)); data(colbournBigFrame); cb <- colbournBigFrame
ec <- function(t, w, v) { r <- tryCatch(eCAN(t, w, v), error = function(e) NULL); if (is.null(r)) NA else as.numeric(r$CAN) }
cv <- read.csv("data/engine_coverage.csv", stringsAsFactors = FALSE)
u <- cv[cv$engine_class == "UNRESOLVED", ]
pat <- "^perfect hash familyD|^Chateauneuf-Kreher doubling postop|^Brick by Brick|^Cyclic|^Holey Transversal|^Incomplete Transversal|^Ji-Yin|^Li-Ji-Yin|^PGL|^Two-stage|^Xu-Ji-Dong|^double proj"
na <- u[grepl(pat, u$Source), c("t","v","k","N","Source")]
cat("unresolved rows in the tail tags:", nrow(na), "\n"); stopifnot(nrow(na) == 39)
na$N_pred <- NA; na$tier <- "TERMINAL_CLAIMED"; na$family <- "terminal (search or published array)"

## perfect hash family D16
i <- grepl("^perfect hash familyD", na$Source)
prs <- regmatches(na$Source[i], regexec("^perfect hash familyD([0-9]+),([0-9]+),([0-9]+)\\^([0-9]+) ([0-9]+)\\^([0-9]+)$", na$Source[i]))
ok <- sapply(prs, length) == 7; stopifnot(all(ok))
M <- as.numeric(sapply(prs, `[`, 2)); kk <- as.numeric(sapply(prs, `[`, 3)); a <- as.numeric(sapply(prs, `[`, 4)); nA <- as.numeric(sapply(prs, `[`, 5)); b <- as.numeric(sapply(prs, `[`, 6)); nB <- as.numeric(sapply(prs, `[`, 7))
cat("PHF D rows:", sum(i), "; M = 16 on", sum(M == 16), "; na + nb = M on", sum(nA + nB == M), "; tag k equals row k on", sum(kk == na$k[i]), "\n")
na$N_pred[i] <- mapply(function(t, v, a, nA, b, nB) nA * (ec(t, a, v) - 1) + nB * (ec(t, b, v) - 1) + 1, na$t[i], na$v[i], a, nA, b, nB)
na$tier[i] <- ifelse(na$N[i] == na$N_pred[i], "ARITHMETIC", ifelse(na$N[i] > na$N_pred[i], "ARITH_ABOVE", "ARITH_BELOW"))
na$family[i] <- "perfect hash family"
print(na[i, c("t","v","k","N","Source","N_pred","tier")], row.names = FALSE)

## CK doubling postop
j <- na$Source == "Chateauneuf-Kreher doubling postop NCK"
na$N_pred[j] <- mapply(function(v, k) { h <- ceiling(k / 2); ec(3, h, v) + (v - 1) * ec(2, h, v) }, na$v[j], na$k[j])
na$tier[j] <- "ARITH_BOUND_ONLY"; na$family[j] <- "Chateauneuf-Kreher doubling"
cat("\nCK doubling postop rows:", sum(j), "; record below the doubling bound on", sum(na$N[j] < na$N_pred[j]), "\n")
print(na[j, c("t","v","k","N","Source","N_pred","tier")], row.names = FALSE)

## the derived cyclic row, tested against the derive law
d <- na$Source == "Cyclic, derived (Colbourn-Keri)"
cat("\nCyclic, derived:", na$t[d], na$v[d], na$k[d], "N", na$N[d], "; floor(eCAN(t+1, k+1, v) / v) =", floor(ec(na$t[d] + 1, na$k[d] + 1, na$v[d]) / na$v[d]), "\n")

cat("\nterminal rows by tag:\n"); print(table(sub(" postop.*$", "", na$Source[na$tier == "TERMINAL_CLAIMED"])))
cat("\n== tiers ==\n"); print(table(na$tier))
write.csv(na[, c("family","t","v","k","N","Source","N_pred","tier")], "data/arith_families_tail.csv", row.names = FALSE)
cat("\nTAIL RUN DONE\n")
