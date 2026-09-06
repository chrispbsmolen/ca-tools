## arith_formula_power.R - the power family (Power CT and
## Power N-CT, 2,564 table rows, 2,540 of them UNRESOLVED): the size
## law recovered from the Source tag and calibrated on every row of the
## frozen table, with the table's own eCAN values as ingredient sizes.
##
## Size law (Colbourn and Torres-Jimenez 2010, Theorem 2.3, as in
## CAs::DHHF2CA): a hash family with M rows over the q^e columns of the
## OA(q^e, q+1, q, e) transposed; row i carries a CA(t, w_i, v) of N_i rows
## with rho_i constant rows; N = chi + sum_i (N_i - rho_i),
## chi = max(0, v - sum_i (v - rho_i)); N_i = eCAN(t, w_i, v).
## Tag grammar, every piece verified on the record below:
##   q^e          base; e = 2, 3 or 4 (nine rows); M rows of w = q
##   +p           p extra columns, base rows use w = q + p
##   T r          one row reduced to w = q - r (Tred, Lemma 3.1)
##   S s          s rows reduced by 1 (mostly e = 3, removed planes through
##                a point; seven N-CT rows have S with e = 2)
##   Arc(a)       a rows reduced by 1 (e = 2; removed lines pairwise meeting)
##   Arc(a):x twos,y ones   x rows reduced by 2 and y by 1 (the number a
##                is not used by the size law or the column rule and its
##                meaning is not known; a != 2x + y on 6 of the 14 rows)
##   Trin a,b,c   three rows reduced by a, b, c
##   c            constant rows used: rho = v for the flagged rows,
##                otherwise rho = 1; a "c" flags the T/S tokens since the
##                last comma, or the base when there are none. The rule
##                is discriminated by the record only at v = 2 (38 rows,
##                38 exact; "previous token only" fails 5, "base only"
##                fails 14). One row, Power CT11^4,cT9c, is ambiguous:
##                its T9 ingredient has w = 2 < t, where eCAN(3, 2, 2) = 8
##                is the table's k >= 2 lookup rather than the 4 row full
##                factorial; the record (68) is reproduced with the lookup
##                and the base flag, and also with the factorial and no
##                base flag, so that row does not decide anything.
##   ingredients  N_i = eCAN(t, w_i, v), the smallest table N at k >= w_i,
##                which is what the table's own entries use (checked
##                against CAs::powerCTcat on "+p": w = q + p)
##   M: Power CT   M = (e-1) * Turan(t, v) + 1  (CAs createPOWERcat.R)
##      Power N-CT M is NOT known from theory (meaning of "N" not known
##                to the CAs author, and not recovered here). It is solved from the record
##                as ONE integer per key (t, min(t,v), q, e): 39 keys, 2 to
##                296 rows and 2 to 8 tag shapes each, and every row of a
##                key gives the same integer. So the N-CT result is "2,033
##                rows reproduced from 39 fitted integers", not a
##                parameter free reproduction. Sensitivity: M - 1 or M + 1
##                fits 0 of 2,093 rows (the smallest ingredient is 24,965
##                rows, so a unit of M moves N by at least that). The fitted
##                M runs 1 to 3 below the CT formula and falls with q
##                (t = 6: 15, 14, 13 at q <= 37, 41..67, >= 73; t = 5: 10 at
##                37, 9 from 41), the signature of a searched hash family
##                table rather than a formula.
## Column rule (checked where derived): plain q^e + p; T rows within e,
## prod(q - r_j) q^(e - nT); Arc(a) on q^2, q^2 - a q + C(a,2); Arc(a)T r,
## (q - r)(q - a) + C(a,2); twos/ones with L = 2x + y lines, q^2 - L q + C(L,2) - x;
## S s on q^3, q^3 - 1 - s(q^2 - 1) + (q-1) C(s,2); T r S s on q^3, (q-r)(q^2 - s q + C(s,2))
## (four rows at q = 31, s = 29 and 30, miss this rule while their N is
## exact; undetermined whether rule or row). No column rule for S on q^2.
## Run from r/livingtable/ (paths adjusted for the repository layout):
##   Rscript arith_formula_power.R | tee results/arith_formula_power_result.txt
suppressMessages(library(CAs)); data(colbournBigFrame); cb <- colbournBigFrame
Turan <- CAs:::Turan
ecan <- function(t, w, v) { r <- tryCatch(eCAN(t, w, v), error = function(e) NULL)
    if (is.null(r)) NA else as.numeric(r$CAN) }
p <- cb[grepl("^Power (N-)?CT", cb$Source), ]
p$fam <- ifelse(grepl("^Power N-CT", p$Source), "N-CT", "CT")
cat("power rows in the table: CT", sum(p$fam == "CT"), " N-CT", sum(p$fam == "N-CT"), "\n")

parse_power <- function(s) {
    body <- sub("^Power (N-)?CT", "", s)
    q <- as.numeric(sub("\\^.*", "", body))
    rest <- sub("^[0-9]+\\^", "", body)
    e <- as.numeric(sub("[^0-9].*$", "", rest))
    mods <- sub("^[0-9]+", "", rest)
    plus <- 0; reds <- c(); cfl <- c(); base_c <- FALSE; run <- c(); Tlist <- c()
    shape <- list(arc = 0, twos = 0, ones = 0, trin = FALSE, S = 0)
    if (grepl("Trin", mods)) { r <- as.numeric(strsplit(sub(".*Trin", "", mods), ",")[[1]])
        reds <- c(reds, r); cfl <- c(cfl, rep(FALSE, 3)); shape$trin <- TRUE
        mods <- sub("Trin.*$", "", mods) }
    if (grepl("twos", mods)) { x <- as.numeric(sub(".*:([0-9]+) twos.*", "\\1", mods))
        y <- as.numeric(sub(".*,([0-9]+) ones.*", "\\1", mods))
        reds <- c(reds, rep(2, x), rep(1, y)); cfl <- c(cfl, rep(FALSE, x + y))
        shape$twos <- x; shape$ones <- y; mods <- sub("Arc\\([0-9]+\\):[0-9]+ twos,[0-9]+ ones", "", mods) }
    if (grepl("Arc", mods)) { a <- as.numeric(sub(".*Arc\\(([0-9]+)\\).*", "\\1", mods))
        reds <- c(reds, rep(1, a)); cfl <- c(cfl, rep(FALSE, a)); shape$arc <- a
        mods <- sub("Arc\\([0-9]+\\)", "", mods) }
    if (grepl("\\+", mods)) { plus <- as.numeric(sub(".*\\+ ?([0-9]+).*", "\\1", mods)); mods <- sub("\\+ ?[0-9]+", "", mods) }
    toks <- regmatches(mods, gregexpr("T[0-9]+|S[0-9]+|c|,", mods))[[1]]
    for (tk in toks) {
        if (tk == ",") { run <- c(); next }
        if (grepl("^T", tk)) { reds <- c(reds, as.numeric(sub("T", "", tk))); cfl <- c(cfl, FALSE); run <- c(run, length(reds))
            Tlist <- c(Tlist, as.numeric(sub("T", "", tk))) }
        else if (grepl("^S", tk)) { s <- as.numeric(sub("S", "", tk)); shape$S <- s
            reds <- c(reds, rep(1, s)); cfl <- c(cfl, rep(FALSE, s)); run <- c(run, length(reds) - s + seq_len(s)) }
        else if (tk == "c") { if (!length(run)) base_c <- TRUE else cfl[run] <- TRUE }
    }
    list(q = q, e = e, plus = plus, reds = reds, cfl = cfl, base_c = base_c, shape = shape,
         nT = length(Tlist), Tlist = Tlist)
}
pars <- lapply(p$Source, parse_power)
p$q <- sapply(pars, `[[`, "q"); p$e <- sapply(pars, `[[`, "e"); p$plus <- sapply(pars, `[[`, "plus")
p$nred <- sapply(pars, function(z) length(z$reds)); p$pcls <- pmin(p$t, p$v)
p$shape <- gsub("[0-9]+", "#", p$Source)

## size law for a given M; also the M that solves the law for the row
size_parts <- function(i) {
    pr <- pars[[i]]; t <- p$t[i]; v <- p$v[i]
    N0 <- ecan(t, pr$q + pr$plus, v); rho0 <- if (pr$base_c) v else 1
    Nj <- if (length(pr$reds)) sapply(pr$q - pr$reds, ecan, t = t, v = v) else numeric(0)
    rhoj <- if (length(pr$reds)) ifelse(pr$cfl, v, 1) else numeric(0)
    list(N0 = N0, rho0 = rho0, Nj = Nj, rhoj = rhoj)
}
N_of_M <- function(sp, M, v, nred) {
    u0 <- M - nred; if (is.na(u0) || u0 < 0) return(NA)
    chi <- max(0, v - u0 * (v - sp$rho0) - sum(v - sp$rhoj))
    chi + u0 * (sp$N0 - sp$rho0) + sum(sp$Nj - sp$rhoj)
}
parts <- lapply(seq_len(nrow(p)), size_parts)
## M solved from the row (chi assumed 0, then confirmed by recomputation)
p$M_solved <- sapply(seq_len(nrow(p)), function(i) { sp <- parts[[i]]
    (p$N[i] - sum(sp$Nj - sp$rhoj)) / (sp$N0 - sp$rho0) + p$nred[i] })
p$M_ct <- (p$e - 1) * mapply(Turan, p$t, p$v) + 1

## ---- Power CT: M by formula ----
ct <- which(p$fam == "CT")
p$M <- NA; p$M[ct] <- p$M_ct[ct]
## ---- Power N-CT: M from the record, keyed by (t, p, q, e) ----
nct <- which(p$fam == "N-CT")
key <- paste(p$t, p$pcls, p$q, p$e)
keys <- unique(key[nct])
Mtab <- do.call(rbind, lapply(keys, function(kk) { ii <- nct[key[nct] == kk]
    ms <- p$M_solved[ii]; ok <- all(!is.na(ms)) && all(ms == round(ms)) && length(unique(ms)) == 1
    data.frame(key = kk, t = p$t[ii[1]], pcls = p$pcls[ii[1]], q = p$q[ii[1]], e = p$e[ii[1]],
               rows = length(ii), shapes = length(unique(p$shape[ii])),
               M = if (ok) ms[1] else NA, M_values = paste(sort(unique(round(ms, 3))), collapse = "/"),
               stringsAsFactors = FALSE) }))
Mtab$status <- ifelse(is.na(Mtab$M), "CONFLICT", ifelse(Mtab$shapes >= 2, "CALIBRATED", "SINGLE_SHAPE"))
cat("\nN-CT hash family table: keys", nrow(Mtab), " calibrated (>= 2 tag shapes agree)", sum(Mtab$status == "CALIBRATED"),
    " single shape", sum(Mtab$status == "SINGLE_SHAPE"), " conflict", sum(Mtab$status == "CONFLICT"), "\n")
print(reshape(Mtab[order(Mtab$t, Mtab$pcls, Mtab$q), c("t","pcls","q","M")], idvar = c("t","pcls"), timevar = "q", direction = "wide"), row.names = FALSE)
if (any(Mtab$status != "CALIBRATED")) { cat("keys not calibrated:\n"); print(Mtab[Mtab$status != "CALIBRATED", c("t","pcls","q","e","rows","shapes","M_values","status")], row.names = FALSE) }
p$M[nct] <- Mtab$M[match(key[nct], Mtab$key)]
p$M_status <- NA; p$M_status[ct] <- "FORMULA"; p$M_status[nct] <- Mtab$status[match(key[nct], Mtab$key)]
write.csv(Mtab, "data/arith_power_Mtable.csv", row.names = FALSE)
## sensitivity of the fitted M: a wrong integer must fail
for (d in c(-1, 1)) { nn <- sapply(nct, function(i) N_of_M(parts[[i]], p$M[i] + d, p$v[i], p$nred[i]))
    cat(sprintf("N-CT rows exact with M %+d instead of the fitted M: %d of %d\n", d, sum(nn == p$N[nct], na.rm = TRUE), length(nct))) }

## ---- predicted N and k ----
p$N_pred <- sapply(seq_len(nrow(p)), function(i) N_of_M(parts[[i]], p$M[i], p$v[i], p$nred[i]))
k_rule <- function(i) { pr <- pars[[i]]; q <- pr$q; e <- pr$e; sh <- pr$shape
    Ts <- pr$Tlist
    if (sh$trin) return(NA)
    if (sh$twos + sh$ones > 0) { L <- 2 * sh$twos + sh$ones; if (pr$nT == 0 && e == 2) return(q^2 - L * q + choose(L, 2) - sh$twos) else return(NA) }
    if (sh$arc > 0) { a <- sh$arc; if (e != 2) return(NA)
        if (pr$nT == 0) return(q^2 - a * q + choose(a, 2) + pr$plus)
        if (pr$nT == 1) return((q - Ts) * (q - a) + choose(a, 2) + pr$plus)
        return(NA) }
    if (sh$S > 0) { s <- sh$S; if (e != 3) return(NA)
        if (pr$nT == 0) return(q^3 - 1 - s * (q^2 - 1) + (q - 1) * choose(s, 2))
        if (pr$nT == 1) return((q - Ts) * (q^2 - s * q + choose(s, 2)))
        return(NA) }
    if (pr$nT <= e) return(prod(q - Ts) * q^(e - pr$nT) + pr$plus)
    NA
}
p$k_pred <- sapply(seq_len(nrow(p)), k_rule)
p$dN <- p$N - p$N_pred; p$dk <- p$k - p$k_pred
p$capped <- p$k == 10000

cat("\n== SIZE LAW ==\n")
for (f in c("CT", "N-CT")) { s <- p[p$fam == f, ]
    cat(sprintf("%-5s rows %4d  with M %4d  N exact %4d  N wrong %d  law inexpressible %d\n", f, nrow(s), sum(!is.na(s$M)),
                sum(s$dN == 0, na.rm = TRUE), sum(!is.na(s$dN) & s$dN != 0), sum(!is.na(s$M) & is.na(s$dN)))) }
cat("\nby tag shape (N-CT):\n")
sh <- p[p$fam == "N-CT" & !is.na(p$M), ]
print(aggregate(cbind(rows = 1, exact = dN == 0) ~ shape, data = sh, FUN = sum))
cat("\nby tag shape (CT):\n")
sh <- p[p$fam == "CT", ]
print(aggregate(cbind(rows = 1, exact = dN == 0) ~ shape, data = sh, FUN = sum))
mis <- p[!is.na(p$M) & !is.na(p$dN) & p$dN != 0, ]
if (nrow(mis)) { cat("\nsize misses:\n"); print(mis[, c("fam","t","v","k","N","Source","M","N_pred","dN")], row.names = FALSE) }
opn <- p[!is.na(p$M) & is.na(p$N_pred), ]
cat("\nrows the law cannot express (Arc(a) with a = M, then T r):", nrow(opn), " shapes:", paste(unique(opn$shape), collapse = ", "), "\n")

cat("\n== COLUMN RULE (where derived) ==\n")
cat("rows with a rule:", sum(!is.na(p$k_pred)), " exact:", sum(p$dk == 0, na.rm = TRUE),
    " capped at k=10000:", sum(!is.na(p$k_pred) & p$dk != 0 & p$capped), " other misses:", sum(!is.na(p$k_pred) & p$dk != 0 & !p$capped), "\n")
km <- p[!is.na(p$k_pred) & p$dk != 0 & !p$capped, ]
if (nrow(km)) print(km[, c("fam","t","v","k","Source","k_pred","dk")], row.names = FALSE)

## ---- tier assignment for the living table ----
## Arc(a) with a = M followed by T r (62 rows): the law above leaves no
## base row (u0 < 0) and no row composition of M rows fits; a brute
## force found a 10 row fit at one (t, v, q) that did not transfer.
## Structure not recovered; these stay open.
p$arith_tier <- ifelse(is.na(p$M) | is.na(p$N_pred), "ARITH_OPEN",
                ifelse(p$dN != 0, "ARITH_MISS",
                ifelse(p$M_status %in% c("FORMULA", "CALIBRATED"), "ARITHMETIC", "ARITH_INFERRED")))
cat("\n== TIERS over all", nrow(p), "power rows ==\n"); print(table(p$fam, p$arith_tier))
cv <- read.csv("data/engine_coverage.csv", stringsAsFactors = FALSE)
u <- cv[cv$engine_class == "UNRESOLVED" & grepl("^Power (N-)?CT", cv$Source), ]
m <- match(paste(u$t, u$v, u$k, u$Source), paste(p$t, p$v, p$k, p$Source))
cat("unresolved power CT/N-CT entries:", nrow(u), " matched to a table row:", sum(!is.na(m)), "\n")
print(table(p$arith_tier[m], useNA = "ifany"))
out <- p[, c("fam","t","v","k","N","Source","q","e","plus","nred","M","M_status","N_pred","dN","k_pred","dk","arith_tier")]
write.csv(out, "data/arith_formula_power.csv", row.names = FALSE)
cat("\nPOWER FAMILY FORMULA RUN DONE\n")
