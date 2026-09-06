## arith_probe_powerCZ.R - probe of the Power CZ family (215
## table rows, 212 unresolved), Colbourn and Zhou (2012), "Improving
## two recursive constructions for covering arrays" (paywalled; not
## read). Tag grammar, read from the rows: "Power CZ e-q.u1-w2.u2-w3.u3..."
## is a hash family on the q^e columns of OA(q^e, q+1, q, e) with u1
## rows of width q and u_i rows of width w_i; M = sum u_i, which equals
## the Power CT row count on 188 rows and is one less on the 27 rows
## at t = 3, v = 3. The column rule of Power CT (Tred on the reduced
## rows, prod(q - r) q^(e - nred)) reproduces k on 104 of the 109 rows
## where nred <= e (2 more at the k = 10000 cap, 3 misses). The Power
## CT size law does NOT reproduce N on any of the 215 rows: every
## residual is negative and varies with q and the reduced widths in a
## way that reads as one row carrying a different, smaller ingredient
## (e.g. t = 3, v = 3, all rows of width q: N - 5 (eCAN - 1) = 29, 32,
## 38, 40 at q = 14, 16, 19, 20). The improvement's rule is NOT
## recovered here; the family stays OPAQUE (ARITH_OPEN) pending the
## paper. Run from r/livingtable/ (paths adjusted for the repository layout):
##   Rscript arith_probe_powerCZ.R | tee results/arith_probe_powerCZ_result.txt
suppressMessages(library(CAs)); data(colbournBigFrame); cb <- colbournBigFrame
ec <- function(t, w, v) tryCatch(eCAN(t, w, v)$CAN, error = function(e) NA)
p <- cb[grepl("^Power CZ", cb$Source), ]
p$e <- as.numeric(sub("Power CZ([0-9]+)-.*", "\\1", p$Source))
p$q <- as.numeric(sub("Power CZ[0-9]+-([0-9]+)\\..*", "\\1", p$Source))
parts <- lapply(seq_len(nrow(p)), function(i) { s <- sub("Power CZ[0-9]+-", "", p$Source[i])
    segs <- strsplit(s, "-")[[1]]
    data.frame(w = as.numeric(sub("\\..*", "", segs)), u = as.numeric(sub(".*\\.", "", segs))) })
p$M <- sapply(parts, function(d) sum(d$u)); p$Mct <- (p$e - 1) * mapply(CAs:::Turan, p$t, p$v) + 1
p$N_ctlaw <- mapply(function(i) { d <- parts[[i]]; sum(d$u * (sapply(d$w, ec, t = p$t[i], v = p$v[i]) - 1)) }, seq_len(nrow(p)))
p$res <- p$N - p$N_ctlaw
p$k_pred <- mapply(function(i) { d <- parts[[i]]; q <- p$q[i]; e <- p$e[i]
    red <- rep(q - d$w[d$w < q], d$u[d$w < q])
    if (length(red) <= e) prod(q - red) * q^(e - length(red)) else NA }, seq_len(nrow(p)))
cat("Power CZ rows:", nrow(p), " by strength:"); print(table(p$t))
cat("M == Power CT row count:", sum(p$M == p$Mct), " M == CT - 1:", sum(p$M == p$Mct - 1), " other:", sum(abs(p$M - p$Mct) > 1), "\n")
cat("column rule (Tred product) exact:", sum(p$k == p$k_pred, na.rm = TRUE), " of", sum(!is.na(p$k_pred)), "with a rule;",
    " capped k=10000:", sum(p$k == 10000 & !is.na(p$k_pred) & p$k != p$k_pred), "\n")
cat("Power CT size law exact:", sum(p$res == 0, na.rm = TRUE), " residual sign: negative", sum(p$res < 0, na.rm = TRUE),
    " zero", sum(p$res == 0, na.rm = TRUE), " positive", sum(p$res > 0, na.rm = TRUE), "\n")
cat("\nresidual by (t, v), range:\n")
print(aggregate(res ~ t + v, data = p, FUN = function(z) paste(range(z), collapse = "..")))
cat("\nrows with every hash family row at width q (the cleanest cases):\n")
allq <- sapply(parts, function(d) nrow(d) == 1)
print(p[allq, c("t","v","k","N","Source","M","N_ctlaw","res")], row.names = FALSE)
write.csv(p[, c("t","v","k","N","Source","e","q","M","Mct","N_ctlaw","res","k_pred")], "data/arith_probe_powerCZ.csv", row.names = FALSE)
cat("\nCZ PROBE DONE: size law not recovered, family stays open\n")
