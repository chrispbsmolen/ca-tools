## ecan_compare.R - checks that table/ca_table.csv can stand in for the
## frozen Colbourn tables behind CAs::eCAN and CAs::eCAK. The baseline rows (CITED, S1)
## must equal CAs::colbournBigFrame row for row, the same stair-step
## lookups over the baseline rows alone must reproduce eCAN and eCAK exactly
## (number and Source text) at every (t, k, v) and (t, N, v) of the
## frozen tables, and the lookups over all CITED and VERIFIED rows together
## must never be worse. Run from the repository root:
##   Rscript tools/ecan_compare.R | tee results/ecan_compare_<date>.txt
suppressMessages(library(CAs))
cat("CAs", as.character(packageVersion("CAs")), "\n")
tab <- read.csv("table/ca_table.csv", stringsAsFactors = FALSE)
tab$N <- as.numeric(tab$N)
source("table/ca_table.R")   ## counted_rows(): the rows that count as best known
cb <- colbournBigFrame
cit <- tab[tab$tier == "CITED" & tab$source_id == "S1", ]
cat("table rows", nrow(tab), " baseline (CITED, S1)", nrow(cit), " colbournBigFrame", nrow(cb), "\n")
same <- nrow(cit) == nrow(cb) && all(cit$t == cb$t & cit$v == cb$v & cit$k == cb$k &
                                     cit$N == cb$N & cit$construction == cb$Source)
cat("baseline rows equal colbournBigFrame row for row (Source = construction):", same, "\n")
best_N <- function(tab, t, k, v) {
    s <- counted_rows(tab); s <- s[s$t == t & s$v == v & s$k >= k, ]
    if (nrow(s) == 0) return(data.frame(CAN = NA, Source = ""))
    i <- which.min(s$N); data.frame(CAN = s$N[i], Source = s$construction[i])
}
best_k <- function(tab, t, N, v) {
    s <- counted_rows(tab); s <- s[s$t == t & s$v == v & s$N <= N, ]
    if (nrow(s) == 0) return(data.frame(CAK = NA, Source = ""))
    i <- which.max(s$k); data.frame(CAK = s$k[i], Source = s$construction[i])
}
kn <- unique(cb[, c("t", "k", "v")]); bad <- 0; lower <- NULL
for (i in seq_len(nrow(kn))) {
    e <- eCAN(kn$t[i], kn$k[i], kn$v[i]); a <- best_N(cit, kn$t[i], kn$k[i], kn$v[i])
    if (!identical(as.numeric(e$CAN), as.numeric(a$CAN)) || !identical(e$Source, a$Source)) bad <- bad + 1
    b <- best_N(tab, kn$t[i], kn$k[i], kn$v[i])
    if (b$CAN != e$CAN) lower <- rbind(lower, data.frame(t = kn$t[i], k = kn$k[i], v = kn$v[i],
                                                         eCAN = e$CAN, table = b$CAN))
}
cat("eCAN: points", nrow(kn), " baseline-only lookup differs", bad,
    " full table differs", NROW(lower), " all smaller:", if (is.null(lower)) NA else all(lower$table < lower$eCAN), "\n")
if (!is.null(lower)) print(lower[order(lower$t, lower$v, lower$k), ], row.names = FALSE)
nk <- unique(cb[, c("t", "N", "v")]); badk <- 0; more <- 0; worse <- 0
for (i in seq_len(nrow(nk))) {
    e <- eCAK(nk$t[i], nk$N[i], nk$v[i]); a <- best_k(cit, nk$t[i], nk$N[i], nk$v[i])
    if (!identical(as.numeric(e$CAK), as.numeric(a$CAK)) || !identical(e$Source, a$Source)) badk <- badk + 1
    b <- best_k(tab, nk$t[i], nk$N[i], nk$v[i])
    if (b$CAK > e$CAK) more <- more + 1
    if (b$CAK < e$CAK) worse <- worse + 1
}
cat("eCAK: points", nrow(nk), " baseline-only lookup differs", badk,
    " full table gives more columns at", more, " fewer at", worse, "\n")
cat("ECAN COMPARE:", if (same && bad == 0 && badk == 0 && worse == 0 &&
                          (is.null(lower) || all(lower$table < lower$eCAN))) "PASS" else "FAIL", "\n")
