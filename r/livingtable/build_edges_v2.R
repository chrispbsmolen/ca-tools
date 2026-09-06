## build_edges_v2.R - reproducible version of the edges-v2 build
## (originally run inline 2026-08-31, saved as a file so that the
## analysis is reproducible).
## Inputs:  data/recipe_ingredients.csv (from parse_recipes.R),
##          data/ingredient_dims.csv (from ingredient_dims.R)
## Output:  data/ca_edges_v2.csv, one row per (recipe, ingredient) with
##          the ingredient's measured dimensions.
## Run from r/livingtable/ (paths adjusted for the repository layout).
ri <- read.csv("data/recipe_ingredients.csv", stringsAsFactors = FALSE)
dm <- read.csv("data/ingredient_dims.csv", stringsAsFactors = FALSE)
dim_of <- setNames(split(dm[, c("N","k","v_min","v_max")], seq_len(nrow(dm))), dm$call)
rows <- list()
for (i in seq_len(nrow(ri))) {
    ings <- if (nzchar(ri$ingredients[i]) && ri$n_ingredients[i] > 0)
        strsplit(ri$ingredients[i], " ||| ", fixed = TRUE)[[1]] else character(0)
    for (g in ings) {
        d <- dim_of[[g]]
        ok <- !is.null(d) && !is.na(d$N)
        rows[[length(rows) + 1]] <- data.frame(
            catalogue = ri$catalogue[i], cat_row = ri$row[i],
            construction = ri$construction[i], ingredient_call = g,
            ing_N = if (ok) d$N else NA, ing_k = if (ok) d$k else NA,
            ing_vmin = if (ok) d$v_min else NA, ing_vmax = if (ok) d$v_max else NA,
            confidence = if (ok) "INGREDIENT_MEASURED" else "UNRESOLVED",
            stamp_date = format(Sys.Date()))
    }
}
out <- do.call(rbind, rows)
write.csv(out, "data/ca_edges_v2.csv", row.names = FALSE)
cat("edges:", nrow(out), " unresolved:", sum(out$confidence == "UNRESOLVED"), "\n")
