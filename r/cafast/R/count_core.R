## count_core: per t-subset of columns (lexicographic), the multiplicity of
## every value tuple over the rows; a row with an NA in the projection
## contributes nothing. Returns list(tots, ncovered, missing, rowmult).
## vs: number of levels per column (0-based coding expected).
count_core <- function(x, t, vs = apply(x, 2, function(col) max(col, na.rm = TRUE) + 1L), rowmult = TRUE) {
    x <- as.matrix(x); storage.mode(x) <- "integer"
    .Call(C_count_core, x, as.integer(t), as.integer(vs), as.integer(rowmult))
}
