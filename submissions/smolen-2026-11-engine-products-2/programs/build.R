# smolen-2026-11-engine-products-2: rebuild every array of this submission from programs/recipes.csv.
# Usage (from the submission folder):  Rscript programs/build.R programs/recipes.csv OUTDIR [TABLE_ARRAYS_DIR]
# Ingredients: Bose orthogonal arrays (CAs::SCA_Bose), construction functions of the R package CAs 0.24.4
# (U. Groemping; constructions only, no stored catalogue), and arrays of this table built by C. Smolen (table/arrays).
# Products: CAs::productPCA (PCA product, Colbourn et al. 2006 Theorem 3.2; Colbourn and Torres-Jimenez 2013) and
# CAs::productCA (generalized direct product, Colbourn and Torres-Jimenez 2013 Corollary 4.3). Columns 1..k are kept.
suppressMessages(library(CAs))
a <- commandArgs(TRUE); R <- read.csv(a[1], stringsAsFactors=FALSE); out <- a[2]
tab <- if (length(a) > 2) a[3] else "../../table/arrays"
dir.create(out, showWarnings=FALSE)
topca <- function(D) {
  P <- tryCatch(CA_to_PCA(D, tryhard = nrow(D) <= 130 && ncol(D) <= 60), error=function(e) NULL)
  if (is.null(P)) D else P }
ing <- function(s, v) {
  p <- strsplit(s, ":")[[1]]
  if (p[1] == "SCA_Bose") { D <- SCA_Bose(v); return(D - min(D)) }
  if (p[1] == "table") { D <- as.matrix(read.table(file.path(tab, p[2]))); return(topca(D - min(D))) }
  set.seed(20261112)
  D <- eval(parse(text = CAs:::labelToCode(p[2], 2, as.integer(p[3]), v)))
  topca(D - min(D)) }
for (i in seq_len(nrow(R))) {
  v <- R$v[i]; k <- R$k[i]
  A <- ing(R$A[i], v)
  D <- switch(R$op[i], base = A, PCA = productPCA(A, ing(R$B[i], v)), DP = productCA(A, ing(R$B[i], v)))
  D <- unclass(D); D <- D - min(D); D <- D[, 1:k, drop = FALSE]
  attributes(D) <- list(dim = dim(D))
  stopifnot(nrow(D) == R$N[i])
  write.table(D, file.path(out, sprintf("CA_%d_2_%d_%d.txt", nrow(D), k, v)), row.names=FALSE, col.names=FALSE)
  cat(sprintf("CA(%d; 2, %d, %d) %s\n", nrow(D), k, v, R$op[i]))
}
