## engine_walker.R - engine organ 3: the propagation walker.
## Given a starting recipe ("catalogue row"), finds every recipe
## transitively built on it, rebuilds each by executing its recorded
## recipe code, and verifies each rebuilt array with caverify at its
## declared strength. This is the rebuild-and-verify loop.
## Usage: Rscript engine_walker.R "PCAcat 101"   (run from r/livingtable/)
## Inputs: data/engine_nodes.csv, data/engine_links.csv.
## Output: data/cascade_<start>.csv. (paths adjusted for the repository layout)
suppressMessages({library(CAs); library(caverify)})
nodes <- read.csv("data/engine_nodes.csv", stringsAsFactors = FALSE)
links <- read.csv("data/engine_links.csv", stringsAsFactors = FALSE)
start <- commandArgs(TRUE)[1]
kids_of <- split(links$child, links$parent)
seen <- character(0); frontier <- start
while (length(frontier)) {
    nxt <- setdiff(unique(unlist(kids_of[frontier])), seen)
    seen <- c(seen, nxt); frontier <- nxt
}
cat("cascade from", start, ":", length(seen), "dependent recipes\n\n")
res <- NULL
for (id in seen) {
    n <- nodes[paste(nodes$catalogue, nodes$cat_row) == id, ]
    A <- tryCatch({ setTimeLimit(elapsed = 120, transient = TRUE)
        eval(parse(text = n$canon_code)[[1]], envir = asNamespace("CAs")) },
        error = function(e) e)
    setTimeLimit(elapsed = Inf)
    if (inherits(A, "error")) {
        cat(id, ": construct err:", substr(conditionMessage(A), 1, 50), "\n")
        res <- rbind(res, data.frame(id = id, N_book = n$N, N_built = NA,
                                     verified = NA)); next
    }
    A <- as.matrix(A); storage.mode(A) <- "integer"
    r <- tryCatch(ca_verify(A, n$t, v = n$v), error = function(e) NULL)
    ok <- !is.null(r) && isTRUE(r$covered)
    cat(sprintf("%-14s book N=%5d  rebuilt %5d x %-4d  verified: %s\n",
        id, n$N, nrow(A), ncol(A), ok))
    res <- rbind(res, data.frame(id = id, N_book = n$N, N_built = nrow(A),
                                 verified = ok))
}
cat("\nCASCADE RESULT:", sum(res$verified %in% TRUE), "of", nrow(res),
    "rebuilt and verified;",
    sum(!is.na(res$N_built) & res$N_built == res$N_book),
    "match the book's recorded N exactly\n")
write.csv(res, paste0("data/cascade_", gsub(" ", "_", start), ".csv"),
          row.names = FALSE)
