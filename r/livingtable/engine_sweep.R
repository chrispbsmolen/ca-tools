## engine_sweep.R - engine organ 5: sweep mode, the correctness
## anchor. Re-evaluates EVERY recipe in the web (construct-only,
## sizes recorded; caverify stamping is the walker's job for
## entries that change) under an optional ingredient substitution,
## and diffs against the book. Graph mode must agree with the
## sweep's changed-set exactly; sweep wins disputes.
## Usage:
##   Rscript engine_sweep.R baseline out.csv [start] [end]
##   Rscript engine_sweep.R swap "CALL" repl.rds out.csv [start] [end]
## Input: data/engine_nodes.csv; out.csv is written where given. Run
## from r/livingtable/ (paths adjusted for the repository layout).
suppressMessages(library(CAs))
a <- commandArgs(TRUE)
mode <- a[1]
if (mode == "baseline") { out <- a[2]; lo <- a[3]; hi <- a[4]; shim <- FALSE
} else { target <- a[2]; rds <- a[3]; out <- a[4]; lo <- a[5]; hi <- a[6]; shim <- TRUE }
nds <- read.csv("data/engine_nodes.csv", stringsAsFactors = FALSE)
lo <- if (is.na(lo <- suppressWarnings(as.integer(lo)))) 1L else lo
hi <- if (is.na(hi <- suppressWarnings(as.integer(hi)))) nrow(nds) else min(hi, nrow(nds))
ns <- asNamespace("CAs")
env <- ns
if (shim) {
    repl <- readRDS(rds)
    tcall <- parse(text = target)[[1]]
    fname <- as.character(tcall[[1]])
    targ_args <- paste(deparse(as.list(tcall)[-1]), collapse = "")
    env <- new.env(parent = ns)
    real_fn <- get(fname, envir = ns)
    assign(fname, local({ rf <- real_fn; ta <- targ_args; rp <- repl
        function(...) { g <- paste(deparse(list(...)), collapse = "")
            if (identical(g, ta)) rp else rf(...) } }), envir = env)
}
done <- if (file.exists(out)) read.csv(out, stringsAsFactors = FALSE) else NULL
for (i in lo:hi) {
    id <- paste(nds$catalogue[i], nds$cat_row[i])
    if (!is.null(done) && id %in% done$id) next
    A <- tryCatch({ setTimeLimit(elapsed = 30, transient = TRUE)
        eval(parse(text = nds$canon_code[i])[[1]], envir = env) },
        error = function(e) e)
    setTimeLimit(elapsed = Inf)
    row <- if (inherits(A, "error"))
        data.frame(id = id, N_book = nds$N[i], N_swept = NA,
                   note = substr(conditionMessage(A), 1, 40))
    else data.frame(id = id, N_book = nds$N[i], N_swept = nrow(as.matrix(A)),
                    note = "")
    done <- rbind(done, row)
    if (nrow(done) %% 10 == 0) { write.csv(done, out, row.names = FALSE)
        cat("...", nrow(done), "\n") }
}
write.csv(done, out, row.names = FALSE)
ok <- sum(!is.na(done$N_swept) & done$N_swept == done$N_book)
ch <- done[!is.na(done$N_swept) & done$N_swept != done$N_book, ]
er <- sum(is.na(done$N_swept))
cat("swept:", nrow(done), " match book:", ok, " CHANGED:", nrow(ch),
    " errors:", er, "\n")
if (nrow(ch)) print(head(ch, 15), row.names = FALSE)
