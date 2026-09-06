## parse_recipes.R - reproducible version of the recipe-string parse
## (originally run inline 2026-08-30). Output: data/recipe_ingredients.csv
## Run from r/livingtable/ (paths adjusted for the repository layout).
suppressMessages(library(CAs))
cats <- list(DPcat = "DPcat", PCAcat = "PCAcat", CYCLOTOMYcat = "CYCLOTOMYcat",
             PALEYcat = "PALEYcat", CKcombis = "ColbournKeriCombis")
extract_calls <- function(e) {
    if (!is.call(e)) return(character(0))
    fn <- as.character(e[[1]])[1]
    kids <- unlist(lapply(as.list(e)[-1], extract_calls))
    c(paste0(fn, "(", paste(sapply(as.list(e)[-1], function(a)
        paste(deparse(a), collapse = "")), collapse = ", "), ")"), kids)
}
rows <- NULL
for (cn in names(cats)) {
    obj <- get(data(list = cats[[cn]], package = "CAs", envir = environment()))
    if (!("code" %in% names(obj))) next
    for (i in seq_len(nrow(obj))) {
        cd <- as.character(obj$code[i])
        if (is.na(cd) || !nzchar(cd)) next
        e <- tryCatch(parse(text = cd)[[1]], error = function(x) NULL)
        if (is.null(e)) next
        calls <- extract_calls(e)
        top_fn <- as.character(e[[1]])[1]
        ings <- if (length(calls) > 1) calls[-1] else character(0)
        ings <- ings[grepl("^[A-Za-z_][A-Za-z0-9_.]*\\(", ings)]
        ings <- ings[!grepl("^(c|rbind|cbind|\\[|list|paste)\\(", ings)]
        rows <- rbind(rows, data.frame(
            catalogue = cn, row = i, construction = top_fn,
            n_ingredients = length(ings),
            ingredients = paste(ings, collapse = " ||| "), code = cd))
    }
}
write.csv(rows, "data/recipe_ingredients.csv", row.names = FALSE)
cat("recipes:", nrow(rows), "\n")
