## arith_tally.R - the running tally of the ARITHMETIC tier: joins every family csv to the
## 9,007 UNRESOLVED entries of engine_coverage.csv and counts the tiers.
## The Add tags come from arith_formula_addn.csv (all n), which
## supersedes the n = 1 rows of arith_formula_small.csv and the
## "Add a factor" rows of arith_families_probe.csv; fused rows come
## from arith_formula_fuse.csv, which supersedes the probe's TERMINAL
## classification on fused rows that have their unfused base in the
## table (22 Raaphorst-Moura-Stevens, 7 extended OA special, 1
## Cyclotomy, 30 in all); a fused row whose base is outside the table
## (8 Raaphorst-Moura-Stevens) keeps the probe's classification. The
## tail csv (arith_families_tail.R) covers the last 39 rows outside
## the paper-blocked families.
## Run from r/livingtable/ after the family scripts (paths adjusted for
## the repository layout; every csv is read from data/):
##   Rscript arith_tally.R | tee results/arith_tally_result.txt
cv <- read.csv("data/engine_coverage.csv", stringsAsFactors = FALSE)
u <- cv[cv$engine_class == "UNRESOLVED", ]
u$key <- paste(u$t, u$v, u$k, u$Source)
fam <- list(
    power  = { x <- read.csv("data/arith_formula_power.csv", stringsAsFactors = FALSE); data.frame(key = paste(x$t, x$v, x$k, x$Source), tier = x$arith_tier, family = paste("Power", x$fam)) },
    dp     = { x <- read.csv("data/arith_formula_dp_table.csv", stringsAsFactors = FALSE); data.frame(key = paste(x$t, x$v, x$k, x$Source), tier = x$arith_tier, family = "Direct product") },
    small  = { x <- read.csv("data/arith_formula_small.csv", stringsAsFactors = FALSE); x <- x[x$family != "Add n factors", ]; data.frame(key = paste(x$t, x$v, x$k, x$Source), tier = x$tier, family = x$family) },
    addn   = { x <- read.csv("data/arith_formula_addn.csv", stringsAsFactors = FALSE); data.frame(key = paste(x$t, x$v, x$k, x$Source), tier = x$tier, family = ifelse(x$Source == "Add a factor", "Add a factor", "Add n factors")) },
    mc     = { x <- read.csv("data/arith_formula_mc.csv", stringsAsFactors = FALSE); data.frame(key = paste(x$t, x$v, x$k, x$Source), tier = x$tier, family = x$family) },
    fuse   = { x <- read.csv("data/arith_formula_fuse.csv", stringsAsFactors = FALSE); x <- x[x$tier != "INGREDIENT_OUTSIDE_TABLE", ]; data.frame(key = paste(x$t, x$v, x$k, x$Source), tier = x$tier, family = "fuse") },
    cmtw   = { x <- read.csv("data/arith_formula_cmtw.csv", stringsAsFactors = FALSE); data.frame(key = paste(x$t, x$v, x$k, x$Source), tier = x$tier, family = x$family) },
    mtvt   = { x <- read.csv("data/arith_formula_mtvt.csv", stringsAsFactors = FALSE); data.frame(key = paste(x$t, x$v, x$k, x$Source), tier = x$tier, family = x$family) },
    tail   = { x <- read.csv("data/arith_families_tail.csv", stringsAsFactors = FALSE); data.frame(key = paste(x$t, x$v, x$k, x$Source), tier = x$tier, family = x$family) },
    cz     = { x <- read.csv("data/arith_probe_powerCZ.csv", stringsAsFactors = FALSE); data.frame(key = paste(x$t, x$v, x$k, x$Source), tier = "ARITH_OPEN", family = "Power CZ") },
    probe  = { x <- read.csv("data/arith_families_probe.csv", stringsAsFactors = FALSE); x <- x[x$family != "Add a factor", ]; data.frame(key = x$key, tier = x$tier, family = x$family) })
## the fuse family takes precedence over the probe's classification for a fused row whose
## unfused base is in the table, and only there
fam$probe <- fam$probe[!(fam$probe$key %in% fam$fuse$key), ]
all <- do.call(rbind, fam)
stopifnot(!any(duplicated(all$key)))
u$arith_tier <- all$tier[match(u$key, all$key)]
u$arith_family <- all$family[match(u$key, all$key)]
u$arith_tier[is.na(u$arith_tier)] <- "NOT_ATTEMPTED"
cat("unresolved entries:", nrow(u), "\n\n== by tier ==\n"); print(table(u$arith_tier))
cat("\n== by family and tier ==\n"); print(table(u$arith_family, u$arith_tier, useNA = "ifany"))
cat("\nARITHMETIC (formula reproduces the record exactly, ingredients from the table):", sum(u$arith_tier == "ARITHMETIC"),
    "\nARITH_INFERRED (exact, but the reading may be coincidental):", sum(u$arith_tier == "ARITH_INFERRED"),
    "\nARITH_ABOVE (record above the law: stale-record leads):", sum(u$arith_tier == "ARITH_ABOVE"),
    "\nARITH_BOUND_ONLY (postop tags; formula gives a bound):", sum(u$arith_tier == "ARITH_BOUND_ONLY"),
    "\nARITH_BELOW (record below the law: a better ingredient reading exists):", sum(u$arith_tier == "ARITH_BELOW"),
    "\nTERMINAL_CLAIMED (search results or published arrays, no table ingredient; propagation can never reach them):", sum(u$arith_tier == "TERMINAL_CLAIMED"),
    "\nARITH_OPEN (attempted, law not recovered):", sum(u$arith_tier == "ARITH_OPEN"),
    "\nNOT_ATTEMPTED:", sum(u$arith_tier == "NOT_ATTEMPTED"), "\n")
cat("\nlargest families not yet attempted:\n")
na <- u[u$arith_tier == "NOT_ATTEMPTED", ]
print(head(sort(table(sub("^(Colbourn-Martirosyan-TVT-Walker|Martirosyan-TVT|Martirosyan-Colbourn|Cohen-Colbourn-Ling|PCAx2PCA|PCAxPCA|orthogonal array|projection|Augment OA|Add [a-z ]+|Raaphorst-Moura-Stevens|extended OA|Cyclotomy|Torres-Jimenez|Torres|cover starter|Cover|Ji-Li-Yin|Fix|[A-Za-z-]+).*", "\\1", na$Source)), decreasing = TRUE), 20))
write.csv(u[, c("t","v","k","N","Source","arith_family","arith_tier")], "data/arith_tally.csv", row.names = FALSE)
cat("\nTALLY DONE\n")
