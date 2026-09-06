## arith_measure.R - the ceiling of the ARITHMETIC tier. Tallies the 9,007 UNRESOLVED entries by construction
## family from their source tags, and counts the modifier tags (fuse,
## postop NCK, Arc, T) that qualify a formula. Run from r/livingtable/ (paths adjusted for
## the repository layout):
##   Rscript arith_measure.R | tee results/arith_measure_result.txt
cv <- read.csv("data/engine_coverage.csv", stringsAsFactors = FALSE)
u <- cv[cv$engine_class == "UNRESOLVED", ]
cat("unresolved:", nrow(u), "\n")
fams <- c("Power N-CT","Power CT","Power CZ","perfect hash family","Restricted SCPHF",
  "Restricted CPHF","SCPHF","CPHF","Augment","orthogonal array","cover starter",
  "Torres-Jimenez","Li-Ji-Yin","simulated annealing","Tabu","tabu","Chateauneuf-Kreher",
  "derive","projection","fuse","Arc","add","Direct product","product","Martirosyan",
  "Colbourn","Cohen","Nurmela","Walker","Hartman","Meagher","Sherwood","Kleitman",
  "Kokkala","IPO","Doubling","Cyclotomy","cyclotomy","Paley","Dwyer","3-stage")
pat <- paste0("^(", paste(fams, collapse = "|"), ")")
u$fam <- sapply(u$Source, function(s) { m <- regmatches(s, regexpr(pat, s))
    if (length(m)) m else sub("^(\\S+).*", "\\1", s) })
tb <- sort(table(u$fam), decreasing = TRUE)
print(head(tb, 25))
cat("\nshare of unresolved in the top 10 families:", round(sum(head(tb, 10)) / nrow(u), 3), "\n")
formula_fams <- c("Direct product","Power N-CT","Power CT","Power CZ","Add","PCAx2PCA",
                  "PCAxPCA","projection","Augment","Chateauneuf-Kreher","Derive")
cat("entries in formula-bearing families (the ceiling):", sum(tb[names(tb) %in% formula_fams]),
    "of", nrow(u), "\n")
cat("modifier tags among unresolved: fuse", sum(grepl("fuse", u$Source)),
    " postop NCK", sum(grepl("postop", u$Source)), " Arc(", sum(grepl("Arc\\(", u$Source)),
    " T-modifiers", sum(grepl("T[0-9]", u$Source)), "\n")
cat("(postop NCK entries can only receive a BOUND from a formula, not an exact size)\n")
