## arith_formula_fuse.R - the "fuse" suffix as a family of its
## own: every Source tag ending in one or more " fuse" words, over the
## WHOLE frozen table (1,354 rows), calibrated on every such row. With
## m the number of fuse words the reading is
##   N = eCAN(t, k, v + m) - 2 m
## that is, the same k at v + m symbols, two rows lost per symbol
## fused. The minus 2 per symbol is a regularity read from the record
## at strengths 3 to 6; Colbourn 2008 (Discrete Mathematics 308, read
## 2026-09-06) states the general fusion as minus 1 and, in its Lemma
## 3.1, minus 2 at strength two,
## and the two strength-2 rows of this family follow the sharper
## q^2 - 3 form, so a strength-2 fuse row is not this law. Exact on
## 1,303 of 1,354 rows, the unfused base row present in every one.
## Of the 51 others, 42 have no table ingredient (v + m > 25:
## orthogonal array 26, Raaphorst-Moura-Stevens 8, SCPHF LFSR 8) and
## are marked INGREDIENT_OUTSIDE_TABLE, not failures; 9 have an
## ingredient and sit BELOW the law (the 2 strength-2 orthogonal array
## rows, and 7 "extended OA (Colbourn) special" rows, a sharper
## fusion not recovered), ARITH_OPEN. Of the 162 UNRESOLVED fuse rows
## 147 are exact and propagable, whatever the base family's own
## status; the ingredient row's own tag is reported so that a fused
## row of a TERMINAL base is seen for what it is, a claim m fusions
## away from a search result. The engine's dependency is the unfused
## base at v + m; an intermediate fused row is itself derived from
## that base. Tags with a postop suffix after the fuse words are not
## in this family.
## Run from r/livingtable/ (paths adjusted for the repository layout):
##   Rscript arith_formula_fuse.R | tee results/arith_formula_fuse_result.txt
suppressMessages(library(CAs)); data(colbournBigFrame); cb <- colbournBigFrame
ec <- function(t, w, v) { r <- tryCatch(eCAN(t, w, v), error = function(e) NULL); if (is.null(r)) NA else as.numeric(r$CAN) }
cv <- read.csv("data/engine_coverage.csv", stringsAsFactors = FALSE)
u <- cv[cv$engine_class == "UNRESOLVED", ]

d <- cb[grepl("( fuse)+$", cb$Source), ]
d$m <- lengths(regmatches(d$Source, gregexpr(" fuse", d$Source)))
d$base_tag <- sub("( fuse)+$", "", d$Source)
d$N_pred <- mapply(function(t, k, v, m) { e <- ec(t, k, v + m); if (is.na(e)) NA else e - 2 * m }, d$t, d$k, d$v, d$m)
d$tier <- ifelse(is.na(d$N_pred), "INGREDIENT_OUTSIDE_TABLE", ifelse(d$N == d$N_pred, "ARITHMETIC", "ARITH_OPEN"))
d$base_shape <- gsub("[0-9]+", "#", d$base_tag)
cat("== fuse rows in the frozen table:", nrow(d), " by m:", paste(names(table(d$m)), table(d$m), collapse = ", "), "==\n")
cat("exact:", sum(d$tier == "ARITHMETIC"), " ingredient outside the table:", sum(d$tier == "INGREDIENT_OUTSIDE_TABLE"), " not exact with an ingredient (open):", sum(d$tier == "ARITH_OPEN"), "\n")
cat("\nnot exact, by base tag shape and tier:\n"); print(table(d$base_shape[d$tier != "ARITHMETIC"], d$tier[d$tier != "ARITHMETIC"]))
cat("rows with an ingredient and not exact, record against law (all below):\n")
print(d[d$tier == "ARITH_OPEN", c("t","v","k","N","Source","N_pred")], row.names = FALSE)
m <- match(paste(u$t, u$v, u$k, u$Source), paste(d$t, d$v, d$k, d$Source))
du <- d[m[!is.na(m)], ]
cat("\nunresolved fuse rows:", nrow(du), "\n"); print(table(base = du$base_shape, tier = du$tier))
cat("\nunresolved fuse rows whose unfused base row is itself a search result or published array (TERMINAL base):\n")
ter <- read.csv("data/arith_families_probe.csv", stringsAsFactors = FALSE); ter <- ter[ter$tier == "TERMINAL_CLAIMED", ]
du$base_key <- paste(du$t, du$v + du$m, du$k, du$base_tag)
cat(sum(du$base_key %in% ter$key), "of", nrow(du), "\n")
d$family <- "fuse"
write.csv(d[, c("family","t","v","k","N","Source","m","base_tag","N_pred","tier")], "data/arith_formula_fuse.csv", row.names = FALSE)
cat("\nFUSE RUN DONE\n")
