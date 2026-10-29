## Rebuilds the 32 TJcat entries listed in TJcat_cyclotomy_replacements.csv with CAs
## and compares each array with the one that was checked (same dimensions, same MD5).
## Base R and CAs only. Takes a minute or two.
library(CAs)
d <- read.csv("TJcat_cyclotomy_replacements.csv", stringsAsFactors = FALSE)
for (i in seq_len(nrow(d))) {
  A <- eval(parse(text = d$call[i]))
  f <- tempfile()
  write.table(unname(A), f, row.names = FALSE, col.names = FALSE)
  ok <- nrow(A) == d$N_TJcat[i] && ncol(A) == d$k[i] &&
        unname(tools::md5sum(f)) == d$md5[i]
  cat(sprintf("%-16s %-22s %4d x %4d  %s\n", d$TJcat_name[i], d$call[i],
              nrow(A), ncol(A), if (ok) "same array as checked" else "DIFFERENT"))
  unlink(f)
}
