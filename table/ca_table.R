## ca_table.R - load and query the provenance-tracked covering array
## table from R. See README.md for the schema and tier definitions.
##
##   source("ca_table.R")
##   tab <- load_ca_table()            # or load("ca_table.rda")
##   best_known(tab, t = 5, v = 3, k = 7)   # 351
##   verified_rows(tab, t = 5, v = 3)       # stamped rows

load_ca_table <- function(path = "ca_table.csv") {
    tab <- utils::read.csv(path, stringsAsFactors = FALSE,
                           colClasses = c(array_sha256 = "character", family_sha256 = "character"))
    tab$N <- as.numeric(tab$N)   ## 844 entries exceed 32-bit integers
    tab
}

## identity of a row: its array_sha256, or for a certificate row whose array
## is not hashed (more than 10^12 entries, since 2026-11-02) "family:" and its
## family_sha256; "" when neither is given. Mirrors identity() in ca_table.py.
row_identity <- function(tab) {
    fam <- if ("family_sha256" %in% names(tab)) tab$family_sha256 else rep("", nrow(tab))
    fam[is.na(fam)] <- ""
    ifelse(!is.na(tab$array_sha256) & tab$array_sha256 != "", tab$array_sha256,
           ifelse(fam != "", paste0("family:", fam), ""))
}

## the rows that count as best known: tier CITED or VERIFIED, less every
## VERIFIED row that a RETRACTED row names (same t, v, k, N, array_sha256
## and family_sha256). Mirrors counted() in ca_table.py, the one definition.
## how a VERIFIED row was checked, from its stamp: "direct",
## "certificate" or "certificate + fusing" (NA for other tiers); mirrors
## check_method() in ca_table.py
check_method <- function(tab) {
    cert <- grepl("^(repcheck(_pp)?|cphfcheck) ", tab$verify_stamp)
    ifelse(tab$tier != "VERIFIED", NA_character_,
           ifelse(cert & grepl("fused", tab$verify_stamp), "certificate + fusing",
                  ifelse(cert, "certificate", "direct")))
}
## methods = NULL counts every VERIFIED row; for example
## methods = "direct" counts only arrays checked directly
counted_rows <- function(tab, methods = NULL) {
    key <- function(x) paste(x$t, x$v, x$k, x$N, x$array_sha256,
                             if ("family_sha256" %in% names(x)) x$family_sha256 else "")
    r <- tab[tab$tier == "RETRACTED", ]
    keep <- tab$tier %in% c("CITED", "VERIFIED") &
        !(tab$tier == "VERIFIED" & key(tab) %in% key(r))
    if (!is.null(methods))
        keep <- keep & !(tab$tier == "VERIFIED" & !(check_method(tab) %in% methods))
    tab[keep, ]
}

## stair-step best known N: smallest N among the counted rows whose k
## reaches at least the requested k
best_known <- function(tab, t, v, k, methods = NULL) {
    s <- counted_rows(tab, methods)
    s <- s[s$t == t & s$v == v & s$k >= k, ]
    if (nrow(s) == 0) return(NA_real_)
    min(s$N)
}

## the same, also over derived.csv (tools/derive_table.py): sizes that follow from
## the counted rows by published constructions; computed sizes, not arrays
load_derived <- function(path = "derived.csv") {
    if (!file.exists(path)) return(NULL)
    utils::read.csv(path, stringsAsFactors = FALSE)
}
best_derived <- function(tab, derived, t, v, k, methods = NULL) {
    b <- best_known(tab, t, v, k, methods)
    if (!is.null(derived)) {
        d <- derived[derived$t == t & derived$v == v & derived$k >= k, ]
        if (nrow(d) > 0) b <- min(c(b, d$N), na.rm = TRUE)
    }
    b
}

verified_rows <- function(tab, t = NULL, v = NULL) {
    s <- tab[tab$tier == "VERIFIED", ]
    if (!is.null(t)) s <- s[s$t == t, ]
    if (!is.null(v)) s <- s[s$v == v, ]
    s
}

## regenerate the .rda mirror after appending rows
make_rda <- function(path = "ca_table.csv", out = "ca_table.rda") {
    ca_table <- load_ca_table(path)
    save(ca_table, file = out, compress = "xz")
    invisible(ca_table)
}
