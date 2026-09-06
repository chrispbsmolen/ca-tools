## arith_formula_small.R - four smaller families whose size
## law is a direct function of other table entries (ingredient sizes
## from the frozen table's own eCAN), each calibrated on EVERY row of
## the family in the frozen table. Laws, each recovered from the record:
##   Derive from strength t+1:  N = floor(eCAN(t+1, k+1, v) / v)
##       (fix one column at its least frequent symbol, drop it)
##   Add 1 factors:  N = eCAN(t, k-1, v) + v (v-1) eCAN(t-2, k-2, v)
##       (the (t-2)-ingredient spans the k-2 columns other than the new
##       one and one partner; 133 of 133). "Add n factors" for n >= 2
##       does not repeat this per factor (the later increments are much
##       smaller); NOT recovered, those rows stay open.
##   Chateauneuf-Kreher doubling (t = 3):  N = eCAN(3, k/2, v) + (v-1) eCAN(2, k/2, v)
##       (111 of 114; the three v = 20 rows at k = 36, 38, 40 sit ABOVE
##       the law by 190, 190, 380, multiples of v(v-1)/2, with the present
##       eCAN(2, 18..20, 20) as ingredient, so the law as it stands would
##       improve the record there; kept as ARITH_ABOVE, a stale-record
##       lead to be checked by construction before it is claimed)
##   perfect hash family a,b,w [T r | S s] [,c]:  the DHHF2CA law with M = a
##       rows over k = b columns, ingredient CA(t, w, v), N = sum_i (N_i -
##       rho_i) + chi, rho = 1 (rho = v with ",c"), T r one row at w - r,
##       S s: s rows at w - 1. "fuse" suffixes (18 rows) reduce v and
##       are not attempted here.
## Pointer: the "Add n factors" law for every n,
## with the domain read from the record, is in arith_formula_addn.R;
## arith_tally.R takes the Add tags from that file's csv and ignores
## this file's "Add n factors" rows. The header above is left as
## written.
## Run from r/livingtable/ (paths adjusted for the repository layout):
##   Rscript arith_formula_small.R | tee results/arith_formula_small_result.txt
suppressMessages(library(CAs)); data(colbournBigFrame); cb <- colbournBigFrame
ec <- function(t, w, v) { r <- tryCatch(eCAN(t, w, v), error = function(e) NULL); if (is.null(r)) NA else as.numeric(r$CAN) }
cv <- read.csv("data/engine_coverage.csv", stringsAsFactors = FALSE)
u <- cv[cv$engine_class == "UNRESOLVED", ]
out <- list()
report <- function(name, d) {
    d$tier <- ifelse(is.na(d$N_pred), "ARITH_OPEN", ifelse(d$N == d$N_pred, "ARITHMETIC",
              ifelse(d$N > d$N_pred, "ARITH_ABOVE", "ARITH_BELOW")))
    m <- match(paste(u$t, u$v, u$k, u$Source), paste(d$t, d$v, d$k, d$Source))
    cat(sprintf("\n== %s: %d table rows, exact %d, record above law %d, record below law %d, inexpressible %d; unresolved entries %d ==\n", name, nrow(d),
        sum(d$tier == "ARITHMETIC"), sum(d$tier == "ARITH_ABOVE"), sum(d$tier == "ARITH_BELOW"), sum(d$tier == "ARITH_OPEN"), sum(!is.na(m))))
    if (any(d$tier != "ARITHMETIC")) print(head(d[d$tier != "ARITHMETIC", c("t","v","k","N","Source","N_pred")], 12), row.names = FALSE)
    d$family <- name; out[[name]] <<- d[, c("family","t","v","k","N","Source","N_pred","tier")]
}

## ---- Derive ----
d <- cb[grepl("^Derive from strength [0-9]+$", cb$Source), ]
d$from <- as.numeric(sub(".*strength ([0-9]+)", "\\1", d$Source))
d$N_pred <- mapply(function(t, k, v, f) floor(ec(f, k + 1, v) / v), d$t, d$k, d$v, d$from)
cat("Derive: from == t + 1 on", sum(d$from == d$t + 1), "of", nrow(d), "\n")
report("Derive", d)

## ---- Add n factors ----
a <- cb[grepl("^Add [0-9]+ factors$", cb$Source), ]
a$n <- as.numeric(sub("Add ([0-9]+) factors", "\\1", a$Source))
a$N_pred <- mapply(function(t, k, v, n) if (n == 1) ec(t, k - 1, v) + v * (v - 1) * ec(t - 2, k - 2, v) else NA, a$t, a$k, a$v, a$n)
cat("Add n factors: n = 1 rows", sum(a$n == 1), " n >= 2 rows", sum(a$n >= 2), "(open)\n")
report("Add n factors", a)

## ---- Chateauneuf-Kreher doubling ----
ck <- cb[grepl("^Chateauneuf-Kreher doubling$", cb$Source), ]
ck$N_pred <- mapply(function(k, v) if (k %% 2 == 0) ec(3, k / 2, v) + (v - 1) * ec(2, k / 2, v) else NA, ck$k, ck$v)
report("Chateauneuf-Kreher doubling", ck)

## ---- perfect hash family ----
ph <- cb[grepl("^perfect hash family[0-9]+,[0-9]+,[0-9]+(T[0-9]+|S[0-9]+|,c)?$", cb$Source), ]
prs <- regmatches(ph$Source, regexec("^perfect hash family([0-9]+),([0-9]+),([0-9]+)(T([0-9]+)|S([0-9]+)|(,c))?$", ph$Source))
ph$a <- as.numeric(sapply(prs, `[`, 2)); ph$b <- as.numeric(sapply(prs, `[`, 3)); ph$w <- as.numeric(sapply(prs, `[`, 4))
ph$Tr <- suppressWarnings(as.numeric(sapply(prs, `[`, 6))); ph$Ss <- suppressWarnings(as.numeric(sapply(prs, `[`, 7))); ph$cflag <- sapply(prs, `[`, 8) == ",c"
ph$N_pred <- mapply(function(t, v, a, w, Tr, Ss, cf) {
    rho <- if (cf) v else 1
    ws <- rep(w, a); if (!is.na(Tr)) ws[1] <- w - Tr; if (!is.na(Ss)) { if (Ss > a) return(NA); ws[seq_len(Ss)] <- w - 1 }
    Ns <- sapply(ws, ec, t = t, v = v); chi <- max(0, v - a * (v - rho))
    chi + sum(Ns - rho) }, ph$t, ph$v, ph$a, ph$w, ph$Tr, ph$Ss, ph$cflag)
cat("PHF: k == b on", sum(ph$k == ph$b), "of", nrow(ph), "; shapes:", paste(names(table(gsub("[0-9]+", "#", ph$Source))), table(gsub("[0-9]+", "#", ph$Source)), collapse = ", "), "\n")
report("perfect hash family", ph)
phf_fuse <- sum(grepl("^perfect hash family.*fuse", cb$Source)); cat("PHF rows with fuse (not attempted):", phf_fuse, "\n")

all <- do.call(rbind, out)
cat("\n== TIERS ==\n"); print(table(all$family, all$tier))
m <- match(paste(u$t, u$v, u$k, u$Source), paste(all$t, all$v, all$k, all$Source))
cat("unresolved entries covered by these families:", sum(!is.na(m)), "\n"); print(table(all$tier[m[!is.na(m)]]))
write.csv(all, "data/arith_formula_small.csv", row.names = FALSE)
cat("\nSMALL FAMILIES RUN DONE\n")
