## Execute every unique ingredient call from the parsed recipe web,
## record its dimensions and level profile. Checkpointed: rows that
## resolved are skipped on rerun, rows that errored are retried.
## Calls are evaluated inside the CAs namespace because many recipes
## use unexported CAs functions (fixed 2026-09-05).
## Input: data/recipe_ingredients.csv. Output: data/ingredient_dims.csv.
## Run from r/livingtable/ (paths adjusted for the repository layout).
suppressMessages(library(CAs))
ri <- read.csv("data/recipe_ingredients.csv")
ings <- unlist(strsplit(ri$ingredients[ri$n_ingredients > 0], " ||| ", fixed = TRUE))
ings <- unique(ings)
## strip subsetting wrappers like X(...)[, 1:4] down to the call itself
## (the dims we want are the call's own; the recipe row records the slice)
resfile <- "data/ingredient_dims.csv"
done <- if (file.exists(resfile)) read.csv(resfile) else NULL
if (!is.null(done)) done <- done[done$status == "ok", ]   ## retry non-ok rows
t0 <- Sys.time()
for (s in ings) {
    if (!is.null(done) && s %in% done$call) next
    if (as.numeric(Sys.time() - t0) > 400) break
    row <- tryCatch({
        setTimeLimit(elapsed = 15, transient = TRUE)
        A <- suppressWarnings(suppressMessages(eval(parse(text = s)[[1]],
                                                    envir = asNamespace("CAs"))))
        setTimeLimit(elapsed = Inf)
        A <- as.matrix(A)
        vs <- apply(A, 2, function(cc) length(unique(cc[!is.na(cc)])))
        data.frame(call = s, N = nrow(A), k = ncol(A),
                   v_min = min(vs), v_max = max(vs),
                   nNA = sum(is.na(A)), status = "ok")
    }, error = function(e) { setTimeLimit(elapsed = Inf)
        data.frame(call = s, N = NA, k = NA, v_min = NA, v_max = NA,
                   nNA = NA, status = paste0("err: ",
                       substr(conditionMessage(e), 1, 50))) })
    done <- rbind(done, row)
    if (nrow(done) %% 50 == 0) write.csv(done, resfile, row.names = FALSE)
}
write.csv(done, resfile, row.names = FALSE)
cat("resolved:", sum(done$status == "ok"), "of", length(ings),
    " (", nrow(done), "attempted )\n")
cat("errors:", sum(done$status != "ok"), "\n")
if (any(done$status != "ok"))
    print(head(done[done$status != "ok", c("call","status")], 5), row.names = FALSE)
