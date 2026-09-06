## engine_depquery.R - the propagation engine's first organ: the
## reverse-dependency query. Given an ingredient (identified by its
## call, or by matching dimensions), list every recipe that uses it,
## i.e. everything an improvement there would force the engine to
## rebuild and re-verify.
## Inputs: data/ca_edges_v2.csv. Run from r/livingtable/. Usage:
##   Rscript engine_depquery.R "SCA_LCDST(5, 3)"       (by call)
##   Rscript engine_depquery.R dims N k                (by dimensions)
## (paths adjusted for the repository layout: data files live in data/)
ed <- read.csv("data/ca_edges_v2.csv", stringsAsFactors = FALSE)
a <- commandArgs(TRUE)
if (length(a) >= 1 && a[1] == "dims") {
    N <- as.integer(a[2]); k <- as.integer(a[3])
    hit <- ed[!is.na(ed$ing_N) & ed$ing_N == N & ed$ing_k == k, ]
    cat("ingredients matching N=", N, " k=", k, ":\n", sep = "")
    print(unique(hit$ingredient_call))
} else {
    target <- a[1]
    hit <- ed[ed$ingredient_call == target, ]
}
if (!nrow(hit)) { cat("no dependents found\n"); quit(save = "no") }
deps <- unique(hit[, c("catalogue", "cat_row", "construction")])
cat("\nDIRECT DEPENDENTS:", nrow(deps), "recipes\n")
print(head(deps, 20), row.names = FALSE)
## first-order dependents only; the transitive closure over
## recipe-to-recipe links is in engine_closure.R and engine_walker.R
cat("\n(first-order dependents only; for the transitive closure see
 engine_walker.R and data/engine_links.csv)\n")
