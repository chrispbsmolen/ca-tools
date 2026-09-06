## engine_closure.R - engine organ 2: recipe-to-recipe linkage and
## the transitive dependency closure, plus the node map linking
## every recipe to its (t, k, v, N) entry in the record.
## Inputs:  data/recipe_ingredients.csv
## Outputs: data/engine_nodes.csv  (recipe -> t,k,v,N, canonical code)
##          data/engine_links.csv  (recipe -> recipe edges, canonical)
##          plus a closure demo printed for the record.
## Run from r/livingtable/ (paths adjusted for the repository layout).
suppressMessages(library(CAs))
ri <- read.csv("data/recipe_ingredients.csv", stringsAsFactors = FALSE)

canon <- function(s) {
    e <- tryCatch(parse(text = s)[[1]], error = function(x) NULL)
    if (is.null(e)) return(NA_character_)
    paste(deparse(e), collapse = " ")
}
ri$canon_code <- vapply(ri$code, canon, "")

## node map: each recipe row -> its record entry (t, k, v, N)
get_cat <- function(nm) get(data(list = nm, package = "CAs",
                                 envir = environment()))
cats <- list(DPcat = get_cat("DPcat"), PCAcat = get_cat("PCAcat"),
             CYCLOTOMYcat = get_cat("CYCLOTOMYcat"),
             PALEYcat = get_cat("PALEYcat"),
             CKcombis = get_cat("ColbournKeriCombis"))
nodes <- NULL
for (i in seq_len(nrow(ri))) {
    cc <- cats[[ri$catalogue[i]]]; r <- ri$row[i]
    t <- if ("t" %in% names(cc)) cc$t[r] else 2L   ## DP/PCA products are strength 2
    nodes <- rbind(nodes, data.frame(
        catalogue = ri$catalogue[i], cat_row = r, t = t,
        v = cc$v[r], k = cc$k[r], N = cc$N[r],
        canon_code = ri$canon_code[i]))
}
write.csv(nodes, "data/engine_nodes.csv", row.names = FALSE)

## recipe->recipe links: an ingredient call whose canonical form
## equals another recipe's canonical code is that recipe used as an
## ingredient
code_index <- setNames(paste(nodes$catalogue, nodes$cat_row),
                       nodes$canon_code)
links <- NULL
for (i in seq_len(nrow(ri))) {
    if (ri$n_ingredients[i] == 0) next
    ings <- strsplit(ri$ingredients[i], " ||| ", fixed = TRUE)[[1]]
    for (g in ings) {
        cg <- canon(g)
        hit <- code_index[cg]
        if (!is.na(hit)) links <- rbind(links, data.frame(
            child = paste(ri$catalogue[i], ri$row[i]),
            parent = unname(hit), parent_call = g))
    }
}
write.csv(links, "data/engine_links.csv", row.names = FALSE)
cat("nodes:", nrow(nodes), "  recipe->recipe links:", nrow(links), "\n")

## transitive closure walker (the cascade)
kids_of <- split(links$child, links$parent)
cascade <- function(start) {
    seen <- character(0); frontier <- start
    while (length(frontier)) {
        nxt <- unique(unlist(kids_of[frontier]))
        nxt <- setdiff(nxt, seen)
        seen <- c(seen, nxt); frontier <- nxt
    }
    seen
}
## demo: deepest cascades from base recipes
roots <- setdiff(unique(links$parent), unique(links$child))
sizes <- vapply(unique(links$parent), function(p) length(cascade(p)), 0L)
top <- sort(sizes, decreasing = TRUE)[1:5]
cat("\nlargest cascades (recipe -> count of transitively dependent recipes):\n")
for (nm in names(top)) cat(" ", nm, "->", top[nm], "dependent recipes\n")
## cycle check (a DAG must have none)
has_cycle <- any(vapply(unique(links$parent), function(p) p %in% cascade(p), TRUE))
cat("\ncycle check (must be FALSE for a valid DAG):", has_cycle, "\n")
