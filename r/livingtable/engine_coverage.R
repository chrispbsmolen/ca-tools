## engine_coverage.R - coverage accounting. Every
## entry of the record classified, no silent omissions, fractions
## published. Categories:
##   RESOLVED   an implemented route or web recipe reproduces the
##              recorded N exactly (the engine can rebuild it)
##   BETTER     implemented routes beat the record (verified list)
##   LEAF       search/CPHF/annealing-tagged: no ingredients by
##              nature; needs re-discovery, not propagation
##   UNRESOLVED everything else (the work queue)
## Inputs: data/ca_reproduction.csv, data/engine_nodes.csv.
## Output: data/engine_coverage.csv. Run from r/livingtable/
## (paths adjusted for the repository layout).
d <- read.csv("data/ca_reproduction.csv", stringsAsFactors = FALSE)
nds <- read.csv("data/engine_nodes.csv", stringsAsFactors = FALSE)
leafpat <- "SBSTT|annealing|Annealing|tabu|Tabu|IPO|ordered design|SIPO|Density|two-stage|CPHF|SCPHF"
key_book <- paste(d$t, d$k, d$v)
key_node <- paste(nds$t, nds$k, nds$v)
recipe_exact <- key_book %in% key_node[!is.na(nds$N)] &
    mapply(function(kb, N) any(key_node == kb & nds$N == N), key_book, d$N)
cls <- ifelse(d$status == "MATCH" | recipe_exact, "RESOLVED",
       ifelse(d$status == "BETTER", "BETTER",
       ifelse(grepl(leafpat, d$Source), "LEAF", "UNRESOLVED")))
d$engine_class <- cls
write.csv(d[, c("t","v","k","N","Source","status","engine_class")],
          "data/engine_coverage.csv", row.names = FALSE)
n <- nrow(d)
cat("COVERAGE ACCOUNTING,", n, "entries, no omissions:\n\n")
for (c in c("RESOLVED","BETTER","LEAF","UNRESOLVED")) {
    m <- sum(cls == c)
    cat(sprintf("  %-11s %5d  (%.1f%%)\n", c, m, 100*m/n))
}
cat("\nsanity: classes sum to", sum(table(cls)), "of", n, "\n")
cat("\nUNRESOLVED by strength (the work queue):\n")
print(table(d$t[cls == "UNRESOLVED"]))
