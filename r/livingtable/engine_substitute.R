## engine_substitute.R - engine organ 4: improvement substitution.
## Given an ingredient call and a replacement array, re-evaluates
## every dependent recipe with the replacement served wherever that
## call appears (a shim environment over the CAs namespace), then
## verifies each result with caverify and reports old vs new N.
## Modes:
##   Rscript engine_substitute.R identity "SCA_LCDST(5, 3)" [max]
##     (replacement = the ingredient itself; sizes and verification
##      must be IDENTICAL to the book: validates the plumbing)
##   Rscript engine_substitute.R swap "CALL" file.rds [max]
##     (replacement loaded from an rds; the real propagation)
## Inputs: data/ca_edges_v2.csv, data/engine_nodes.csv. Run from
## r/livingtable/ (paths adjusted for the repository layout).
suppressMessages({library(CAs); library(caverify)})
ed  <- read.csv("data/ca_edges_v2.csv", stringsAsFactors = FALSE)
nds <- read.csv("data/engine_nodes.csv", stringsAsFactors = FALSE)
a <- commandArgs(TRUE)
mode <- a[1]; target <- a[2]
maxn <- if (mode == "swap") as.integer(a[4]) else as.integer(a[3])
if (is.na(maxn)) maxn <- 8L

## the replacement array
ns <- asNamespace("CAs")
orig <- eval(parse(text = target)[[1]], envir = ns)
repl <- if (mode == "identity") orig else readRDS(a[3])
cat("ingredient:", target, " original:", nrow(orig), "x", ncol(orig),
    " replacement:", nrow(repl), "x", ncol(repl), "\n")

## shim: a function of the same name that returns the replacement
## when called with the exact arguments of the target call, and
## delegates to the real function otherwise
tcall <- parse(text = target)[[1]]
fname <- as.character(tcall[[1]])
targ_args <- paste(deparse(as.list(tcall)[-1]), collapse = "")
shim_env <- new.env(parent = ns)
real_fn <- get(fname, envir = ns)
make_shim <- function(real_fn, targ_args, repl) {
    function(...) {
        got <- paste(deparse(list(...)), collapse = "")
        if (identical(got, targ_args)) repl else real_fn(...)
    }
}
assign(fname, make_shim(real_fn, targ_args, repl), envir = shim_env)

## dependents (direct, smallest first, capped for the demo)
dep <- unique(ed[ed$ingredient_call == target, c("catalogue", "cat_row")])
dep$id <- paste(dep$catalogue, dep$cat_row)
dep <- merge(dep, nds, by = c("catalogue", "cat_row"))
dep <- dep[order(as.numeric(dep$N) * as.numeric(dep$k)), ][seq_len(min(maxn, nrow(dep))), ]
cat("re-evaluating", nrow(dep), "dependent recipes (of",
    length(unique(paste(ed$catalogue, ed$cat_row)[ed$ingredient_call == target])), "direct)\n\n")
ok_all <- TRUE
for (i in seq_len(nrow(dep))) {
    n <- dep[i, ]
    A <- tryCatch({ setTimeLimit(elapsed = 120, transient = TRUE)
        eval(parse(text = n$canon_code)[[1]], envir = shim_env) },
        error = function(e) e)
    setTimeLimit(elapsed = Inf)
    if (inherits(A, "error")) { cat(n$id, ": err:",
        substr(conditionMessage(A), 1, 50), "\n"); ok_all <- FALSE; next }
    A <- as.matrix(A); storage.mode(A) <- "integer"
    r <- tryCatch(ca_verify(A, n$t, v = n$v), error = function(e) NULL)
    vok <- !is.null(r) && isTRUE(r$covered)
    same <- (nrow(A) == n$N)
    cat(sprintf("%-14s book N=%4d  new N=%4d  verified: %-5s %s\n",
        n$id, n$N, nrow(A), vok,
        if (mode == "identity") (if (same && vok) "IDENTITY OK" else "MISMATCH")
        else sprintf("(delta %+d)", nrow(A) - n$N)))
    if (mode == "identity" && !(same && vok)) ok_all <- FALSE
    if (!vok) ok_all <- FALSE
}
cat("\n", if (mode == "identity")
    (if (ok_all) "IDENTITY TEST PASS: plumbing verified" else "IDENTITY TEST FAIL")
    else if (ok_all) "SWAP PROPAGATION COMPLETE: all results verified"
    else "SWAP had failures, see above", "\n")
