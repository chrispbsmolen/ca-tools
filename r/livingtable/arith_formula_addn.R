## arith_formula_addn.R - the "Add n factors" family in full
## (tags "Add n factors", n >= 1, and "Add a factor"), calibrated on
## EVERY row of both tags in the frozen table. Supersedes the n = 1
## only reading in arith_formula_small.R and the "Add a factor" probe
## in arith_families_probe.R; arith_tally.R takes this file's csv for
## both tags.
## Law, recovered from the record (b = k - n original columns, the
## base entry eCAN(t, b, v); eCAN(1, ., v) = v, eCAN(0, ., v) = 1):
##   N = eCAN(t, b, v) + sum_{j = 2}^{min(t, n + 1)} v^(j-1) (v - 1) eCAN(t - j, b - 1, v)
## The n = 1 case is the Add-1-factor law already on record (j = 2
## only). Each further factor up to the strength adds the next term;
## the sum stops at j = t, so the added terms are the same for every
## n >= t - 1.
## Domain, read off the record and stated descriptively: exact for
## every row with n <= 2; for n >= 3 exact when v is a prime power and
## n <= v, and at n = 3 for v in {12, 15, 20, 21, 24}; not exact
## (record ABOVE the sum) for any other non prime power row with
## n >= 3 nor for any row with n > v. Those rows are ARITH_OPEN (the
## record's route there is not this sum), not stale-record leads. The
## prime power and n <= v part of the domain is a rule; the n = 3 list
## is the observed set, so the coincidence check below is informative
## only for the rule part.
## "Add a factor" (t = 3, 4) counts one factor per entry; when the
## entry at k - 1 is itself an "Add a factor" row, the chain length is
## n and the base is the entry at k - n. The seven strength-4 rows the
## probe had recorded BELOW the one-factor law are the n = 2 case.
## The six prime power rows inside the domain that sit ABOVE the sum
## do so by 7, 12 and 24 units of v(v-1); each gap equals the
## difference between the answering (3, ., v) row and a neighbouring
## row of the table, which is the reading "a strength-3 ingredient
## moved after the entry was made". They are kept ARITH_ABOVE, leads
## to be checked by construction before any claim.
## Run from r/livingtable/ (paths adjusted for the repository layout):
##   Rscript arith_formula_addn.R | tee results/arith_formula_addn_result.txt
suppressMessages(library(CAs)); data(colbournBigFrame); cb <- colbournBigFrame
ec <- function(t, w, v) { if (t <= 0) return(1); if (t == 1) return(v)
    r <- tryCatch(eCAN(t, w, v), error = function(e) NULL); if (is.null(r)) NA else as.numeric(r$CAN) }
is_pp <- function(v) { p <- 2; while (v %% p != 0) p <- p + 1; while (v %% p == 0) v <- v / p; v == 1 }
law_addn <- function(t, v, k, n) { b <- k - n; N <- ec(t, b, v); if (is.na(N)) return(NA)
    for (j in 2:min(t, n + 1)) { e <- ec(t - j, b - 1, v); if (is.na(e)) return(NA); N <- N + v^(j - 1) * (v - 1) * e }
    N }
cv <- read.csv("data/engine_coverage.csv", stringsAsFactors = FALSE)
u <- cv[cv$engine_class == "UNRESOLVED", ]

## ---- Add n factors ----
a <- cb[grepl("^Add [0-9]+ factors$", cb$Source), ]
a$n <- as.numeric(sub("Add ([0-9]+) factors", "\\1", a$Source))

## ---- Add a factor: chain length from the frozen table ----
f <- cb[cb$Source == "Add a factor", ]
f$n <- mapply(function(t, v, k) { n <- 1
    while (any(f$t == t & f$v == v & f$k == k - n)) n <- n + 1; n }, f$t, f$v, f$k)

d <- rbind(a, f)
d$N_pred <- mapply(law_addn, d$t, d$v, d$k, d$n)
d$pp <- sapply(d$v, is_pp)
d$domain <- d$n <= 2 | (d$pp & d$n <= d$v) | (d$n == 3 & d$v %in% c(12, 15, 20, 21, 24))
d$tier <- ifelse(is.na(d$N_pred), "ARITH_OPEN",
          ifelse(d$N == d$N_pred, "ARITHMETIC",
          ifelse(!d$domain, "ARITH_OPEN",
          ifelse(d$N > d$N_pred, "ARITH_ABOVE", "ARITH_BELOW"))))

cat("== Add n factors + Add a factor:", nrow(d), "table rows (", nrow(a), "tagged Add n factors,", nrow(f), "tagged Add a factor ) ==\n")
cat("exact:", sum(d$tier == "ARITHMETIC"), " record above law inside the domain:", sum(d$tier == "ARITH_ABOVE"),
    " record below law:", sum(d$tier == "ARITH_BELOW"), " outside the domain or inexpressible:", sum(d$tier == "ARITH_OPEN"), "\n")
cat("\nexact by n (all rows):\n"); print(table(n = pmin(d$n, 9), exact = d$N == d$N_pred))
cat("\nexact by prime power and n <= v:\n"); print(table(pp = d$pp, n_le_v = d$n <= d$v, exact = d$N == d$N_pred))
cat("\nnon prime power rows with n = 3, exact by v:\n"); s <- d[!d$pp & d$n == 3, ]; print(table(v = s$v, exact = s$N == s$N_pred))
cat("\nrows outside the domain that the sum reproduces anyway (a coincidence check on the rule part; should be none):", sum(!d$domain & d$N == d$N_pred), "\n")
cat("\nrecord above the law inside the domain (kept as leads; difference in units of v(v-1)):\n")
ab <- d[d$tier == "ARITH_ABOVE", ]; ab$diff <- ab$N - ab$N_pred; ab$units <- ab$diff / (ab$v * (ab$v - 1))
print(ab[, c("t","v","k","n","N","Source","N_pred","diff","units")], row.names = FALSE)
cat("\nAdd a factor rows by chain length:\n"); print(table(t = f$t, n = f$n))
cat("\nAdd a factor rows with n = 2 (the rows the probe had BELOW the one-factor law):\n")
print(d[d$Source == "Add a factor" & d$n == 2, c("t","v","k","n","N","N_pred","tier")], row.names = FALSE)

m <- match(paste(u$t, u$v, u$k, u$Source), paste(d$t, d$v, d$k, d$Source))
cat("\nunresolved entries in these tags:", sum(!is.na(m)), "\n"); print(table(d$tier[m[!is.na(m)]]))
cat("unresolved by tag and tier:\n"); print(table(ifelse(grepl("^Add a", d$Source[m[!is.na(m)]]), "Add a factor", "Add n factors"), d$tier[m[!is.na(m)]]))
d$family <- ifelse(d$Source == "Add a factor", "Add a factor", "Add n factors")
write.csv(d[, c("family","t","v","k","N","Source","n","N_pred","domain","tier")], "data/arith_formula_addn.csv", row.names = FALSE)
cat("\nADD N FACTORS RUN DONE\n")
