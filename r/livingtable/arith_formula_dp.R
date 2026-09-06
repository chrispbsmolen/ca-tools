## arith_formula_dp.R - the direct product family on the executed recipes:
## recover the size formula EMPIRICALLY from the resolved DPcat recipes
## and calibrate it on the record. Run from r/livingtable/ (paths
## adjusted for the repository layout):
##   Rscript arith_formula_dp.R | tee results/arith_formula_dp_result.txt
n  <- read.csv("data/engine_nodes.csv", stringsAsFactors = FALSE)
ri <- read.csv("data/recipe_ingredients.csv", stringsAsFactors = FALSE)
dm <- read.csv("data/ingredient_dims.csv", stringsAsFactors = FALSE)
r2 <- ri[ri$catalogue == "DPcat" & ri$n_ingredients == 2, ]
rows <- lapply(seq_len(nrow(r2)), function(i) {
    ing <- trimws(strsplit(r2$ingredients[i], "|||", fixed = TRUE)[[1]])
    d1 <- dm[match(ing[1], dm$call), ]; d2 <- dm[match(ing[2], dm$call), ]
    code <- r2$code[i]
    ## each ingredient's column count: its own "[, 1:n]" subset if it
    ## carries one, else the measured dims (the first version of this
    ## script gave the first subset found to ingredient 1 regardless,
    ## which produced 11 spurious "k != k1 * k2 variants"; since fixed)
    args2 <- sub("^productCA\\((.*),\\s*c1\\s*=\\s*[0-9]+\\)$", "\\1", code)
    kk <- function(txt, d) { m <- regmatches(txt, regexpr("\\[,\\s*1:([0-9]+)\\]", txt))
        if (length(m)) as.numeric(sub(".*1:([0-9]+).*", "\\1", m)) else d$k }
    ## split at the top level comma between the two ingredient calls
    depth <- 0; cut <- NA; ch <- strsplit(args2, "")[[1]]
    for (j in seq_along(ch)) { if (ch[j] %in% c("(", "[")) depth <- depth + 1; if (ch[j] %in% c(")", "]")) depth <- depth - 1
        if (ch[j] == "," && depth == 0) { cut <- j; break } }
    k1 <- kk(substr(args2, 1, cut - 1), d1); k2 <- kk(substr(args2, cut + 1, nchar(args2)), d2)
    c1 <- suppressWarnings(as.numeric(sub(".*c1\\s*=\\s*([0-9]+).*", "\\1", code)))
    nd <- n[n$catalogue == "DPcat" & n$cat_row == r2$row[i], ]
    data.frame(row = r2$row[i], t = nd$t, v = nd$v, k = nd$k, N = nd$N,
               N1 = d1$N, N2 = d2$N, k1 = k1, k2 = k2, c1 = c1) })
x <- do.call(rbind, rows)
cat("two-ingredient DPcat recipes:", nrow(x), " strengths:", paste(unique(x$t), collapse = ","), "\n")
cat("column rule  k == k1 * k2      :", sum(x$k == x$k1 * x$k2), "of", nrow(x), "\n")
cat("size rule    N == N1 + N2 - v  :", sum(x$N == x$N1 + x$N2 - x$v), "of", nrow(x), "\n")
cat("rejected     N == N1 + N2 - c1 :", sum(x$N == x$N1 + x$N2 - x$c1, na.rm = TRUE), "of", nrow(x), "\n")
odd <- x[x$k != x$k1 * x$k2, ]
if (nrow(odd)) { cat("recipes where k != k1*k2 (variant to read):\n"); print(odd[, c("row","t","v","k","k1","k2","N")], row.names = FALSE) }
cat(if (all(x$N == x$N1 + x$N2 - x$v)) "\nDIRECT PRODUCT FORMULA CALIBRATED ON THE RECORD: N = N1 + N2 - v\n" else "\nFORMULA NOT UNIVERSAL, investigate\n")
