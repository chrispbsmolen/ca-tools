## ca_table.R - load and query the provenance-tracked covering array
## table from R. See README.md for the schema and tier definitions.
##
##   source("ca_table.R")
##   tab <- load_ca_table()            # or load("ca_table.rda")
##   best_known(tab, t = 5, v = 3, k = 7)   # 351
##   verified_rows(tab, t = 5, v = 3)       # stamped rows

load_ca_table <- function(path = "ca_table.csv") {
    tab <- utils::read.csv(path, stringsAsFactors = FALSE)
    tab$N <- as.numeric(tab$N)   ## 844 entries exceed 32-bit integers
    tab
}

## the rows that count as best known: tier CITED or VERIFIED, less every
## VERIFIED row that a RETRACTED row names (same t, v, k, N and
## array_sha256). Mirrors counted() in ca_table.py, the one definition.
counted_rows <- function(tab) {
    key <- function(x) paste(x$t, x$v, x$k, x$N, x$array_sha256)
    r <- tab[tab$tier == "RETRACTED", ]
    tab[tab$tier %in% c("CITED", "VERIFIED") &
        !(tab$tier == "VERIFIED" & key(tab) %in% key(r)), ]
}

## stair-step best known N: smallest N among the counted rows whose k
## reaches at least the requested k
best_known <- function(tab, t, v, k) {
    s <- counted_rows(tab)
    s <- s[s$t == t & s$v == v & s$k >= k, ]
    if (nrow(s) == 0) return(NA_real_)
    min(s$N)
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
