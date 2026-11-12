# Rebuild every array of this submission.
# Usage (from the submission folder): Rscript programs/build.R claims.csv OUTDIR
# Needs the R package CAs 0.24.4 (CRAN). Uses CAs's constructions only, never its stored data objects.
suppressMessages(library(CAs))
a <- commandArgs(TRUE); claims <- read.csv(a[1], stringsAsFactors=FALSE); out <- a[2]
dir.create(out, showWarnings=FALSE)
for (i in seq_len(nrow(claims))) {
  r <- claims[i, ]
  if (grepl("all words plus a sum column", r$source_detail)) {
    W <- as.matrix(expand.grid(rep(list(0:(r$v-1)), r$t)))[, r$t:1, drop=FALSE]
    A <- cbind(W, rowSums(W) %% r$v)
  } else {
    m <- sub('.*labelToCode\\("([^"]+)".*', "\\1", r$source_detail)
    set.seed(20261112)
    A <- as.matrix(eval(parse(text=CAs:::labelToCode(m, r$t, r$k, r$v))))
    if (any(is.na(A))) A[is.na(A)] <- sample(0:(r$v-1), sum(is.na(A)), replace=TRUE)
    A <- A[, seq_len(r$k), drop=FALSE]
  }
  write.table(A, file.path(out, r$file), row.names=FALSE, col.names=FALSE, quote=FALSE)
}
cat("rebuilt", nrow(claims), "arrays\n")
