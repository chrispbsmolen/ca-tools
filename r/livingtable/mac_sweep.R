## mac_sweep.R - engine organ 5 validation, complete, one run.
## (1) BASELINE sweep: every recipe rebuilt, sizes vs the book.
## (2) SWAP sweep: same, with a one-row-fatter SCA_LCDST(5, 3)
##     served everywhere (pure local computation, no downloads,
##     parallel-safe).
## (3) AGREEMENT: the set of entries the sweep says changed must
##     equal the graph mode's predicted cascade. Sweep wins disputes.
## Pilot-measured projection: ~10-20 minutes total at 13 workers.
## Run from r/livingtable/ (paths adjusted for the repository layout):
##   Rscript mac_sweep.R | tee results/mac_sweep_result.txt
## Inputs: data/engine_nodes.csv, data/ca_edges_v2.csv, data/engine_links.csv.
## Output: data/sweep_agreement.csv.
suppressMessages({library(CAs); library(parallel)})
nds <- read.csv("data/engine_nodes.csv", stringsAsFactors = FALSE)
ed  <- read.csv("data/ca_edges_v2.csv", stringsAsFactors = FALSE)
lk  <- read.csv("data/engine_links.csv", stringsAsFactors = FALSE)
ns  <- asNamespace("CAs")
target <- "SCA_LCDST(5, 3)"
orig <- eval(parse(text = target)[[1]], envir = ns)
repl <- rbind(as.matrix(orig), as.matrix(orig)[1, ])
mkenv <- function(shim) {
    if (!shim) return(ns)
    e <- new.env(parent = ns)
    tcall <- parse(text = target)[[1]]
    fname <- as.character(tcall[[1]])
    ta <- paste(deparse(as.list(tcall)[-1]), collapse = "")
    rf <- get(fname, envir = ns)
    assign(fname, function(...) { g <- paste(deparse(list(...)), collapse = "")
        if (identical(g, ta)) repl else rf(...) }, envir = e)
    e
}
sweep <- function(shim, label) {
    env <- NULL
    one <- function(i) {
        if (is.null(env)) env <<- mkenv(shim)   ## per-worker env
        A <- tryCatch({ setTimeLimit(elapsed = 60, transient = TRUE)
            eval(parse(text = nds$canon_code[i])[[1]], envir = env) },
            error = function(e) e)
        setTimeLimit(elapsed = Inf)
        if (inherits(A, "error")) NA_integer_ else nrow(as.matrix(A))
    }
    nc <- max(1L, detectCores() - 2L)
    t0 <- Sys.time()
    r <- unlist(mclapply(seq_len(nrow(nds)), one, mc.cores = nc))
    cat(label, "sweep:", round(as.numeric(Sys.time() - t0, units = "mins"), 1), "min;",
        sum(is.na(r)), "construct errors\n")
    r
}
base <- sweep(FALSE, "baseline")
swp  <- sweep(TRUE,  "swap")
ids <- paste(nds$catalogue, nds$cat_row)
cat("\nbaseline vs book: ", sum(!is.na(base) & base == nds$N), "of",
    nrow(nds), "match\n")
mism <- which(!is.na(base) & base != nds$N)
if (length(mism)) { cat("baseline mismatches (investigate):\n")
    print(data.frame(id = ids[mism], book = nds$N[mism],
                     swept = base[mism])[1:min(10, length(mism)), ],
          row.names = FALSE) }
## agreement: sweep-changed set vs graph cascade prediction
changed <- ids[!is.na(base) & !is.na(swp) & swp != base]
direct <- unique(paste(ed$catalogue[ed$ingredient_call == target],
                       ed$cat_row[ed$ingredient_call == target]))
kids_of <- split(lk$child, lk$parent)
seen <- direct; frontier <- direct
while (length(frontier)) {
    nxt <- setdiff(unique(unlist(kids_of[frontier])), seen)
    seen <- c(seen, nxt); frontier <- nxt }
cascade <- seen
cat("\nsweep says changed:", length(changed),
    " graph cascade predicts at most:", length(cascade), "\n")
outside <- setdiff(changed, cascade)
cat("changed entries OUTSIDE the predicted cascade (must be 0):",
    length(outside), "\n")
if (length(outside)) print(outside)
absorbed <- setdiff(intersect(cascade, ids[!is.na(base) & !is.na(swp)]), changed)
cat("cascade members that absorbed the change (allowed):",
    length(absorbed), "\n")
verdict <- length(outside) == 0
cat("\nTWO-MODE AGREEMENT:", if (verdict) "PASS" else "FAIL",
    "\nSWEEP DONE\n")
res <- data.frame(id = ids, N_book = nds$N, N_base = base, N_swap = swp)
write.csv(res, "data/sweep_agreement.csv", row.names = FALSE)
