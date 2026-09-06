## arith_coverage_republish.R - the coverage accounting
## republished with the ARITHMETIC tier counted separately from the
## verified tiers, never blended. Reads data/engine_coverage.csv (the
## engine's accounting from engine_coverage.R: RESOLVED / BETTER / LEAF /
## UNRESOLVED) and data/arith_tally.csv (the arithmetic tiers over the
## UNRESOLVED set) and writes data/engine_coverage_v2.csv with one class
## per entry, no omissions.
## Run from r/livingtable/ (paths adjusted for the repository layout):
##   Rscript arith_coverage_republish.R | tee results/arith_coverage_republish_result.txt
cv <- read.csv("data/engine_coverage.csv", stringsAsFactors = FALSE)
ta <- read.csv("data/arith_tally.csv", stringsAsFactors = FALSE)
key <- function(d) paste(d$t, d$v, d$k, d$Source)
cv$tier <- cv$engine_class
m <- match(key(cv), key(ta))
cv$tier[!is.na(m)] <- ta$arith_tier[m[!is.na(m)]]
cv$arith_family <- NA; cv$arith_family[!is.na(m)] <- ta$arith_family[m[!is.na(m)]]
stopifnot(sum(!is.na(m)) == nrow(ta))
write.csv(cv[, c("t","v","k","N","Source","status","engine_class","tier","arith_family")], "data/engine_coverage_v2.csv", row.names = FALSE)
n <- nrow(cv)
lab <- c(RESOLVED = "verified by construction, record reproduced",
         BETTER = "verified by construction, record beaten",
         LEAF = "search or external array, rebuilt by CAs, no ingredients",
         ARITHMETIC = "size law reproduces the record from table ingredients (claims)",
         ARITH_INFERRED = "size law exact, reading possibly coincidental or an ingredient outside the table",
         ARITH_ABOVE = "record above its own law: stale-record leads",
         ARITH_BELOW = "record below the law: better ingredient reading exists",
         ARITH_BOUND_ONLY = "postop tags: the law gives a bound only",
         TERMINAL_CLAIMED = "search result or published array, no ingredient, unverified",
         ARITH_OPEN = "attempted, law not recovered (papers pending)",
         NOT_ATTEMPTED = "family not yet attempted (papers pending)")
cat("COVERAGE ACCOUNTING v2,", n, "entries, no omissions:\n\n")
for (c in names(lab)) { k <- sum(cv$tier == c); cat(sprintf("  %-17s %5d  (%5.1f%%)  %s\n", c, k, 100 * k / n, lab[c])) }
cat("\nsanity: classes sum to", sum(cv$tier %in% names(lab)), "of", n, "\n")
ver <- sum(cv$tier %in% c("RESOLVED","BETTER")); leaf <- sum(cv$tier == "LEAF"); ari <- sum(cv$tier == "ARITHMETIC")
cat(sprintf("\nverified by construction: %d (%.1f%%); leaves rebuilt by CAs, no ingredients: %d (%.1f%%); ARITHMETIC claims with a calibrated law: %d (%.1f%%)\n",
    ver, 100 * ver / n, leaf, 100 * leaf / n, ari, 100 * ari / n))
cat(sprintf("entries with no handle yet (open plus not attempted): %d (%.1f%%); terminal claims, never propagable: %d (%.1f%%)\n",
    sum(cv$tier %in% c("ARITH_OPEN","NOT_ATTEMPTED")), 100 * sum(cv$tier %in% c("ARITH_OPEN","NOT_ATTEMPTED")) / n,
    sum(cv$tier == "TERMINAL_CLAIMED"), 100 * sum(cv$tier == "TERMINAL_CLAIMED") / n))
cat("\nby strength, share with a handle (verified, leaf, or ARITHMETIC, each counted apart above):\n")
print(round(tapply(cv$tier %in% c("RESOLVED","BETTER","LEAF","ARITHMETIC"), cv$t, mean), 3))
cat("\nREPUBLISH DONE\n")
