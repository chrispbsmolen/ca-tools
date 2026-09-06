## mac_cyclotomy_followup.R - two follow-up jobs after audit2.
## Job A: multi-window screens for every row that passed only the
##        first-50 screen: last 50 columns + two random 50-column
##        windows. A failure in ANY window proves the row broken.
## Job B: type-3b repair screens for the two giant failures
##        (q=2161 v=20, q=2311 v=21): build the 3b sibling and
##        screen it the same four ways (full verification of these
##        is infeasible anywhere; screens are marked as screens).
## Run from r/livingtable/ (paths adjusted for the repository layout):
##   Rscript mac_cyclotomy_followup.R | tee results/cyclotomy_followup_result.txt
## Input: data/cyclotomy_audit2.csv (produced by mac_cyclotomy_audit2.R).
## Output: data/cyclotomy_screen4.csv (shipped).
suppressMessages({library(CAs); library(caverify); library(parallel)})
set.seed(20260830)
screen4 <- function(A, t, v) {
    k <- ncol(A)
    wins <- list(head = 1:min(50, k), tail = max(1, k - 49):k)
    if (k > 50) { wins$rand1 <- sort(sample(k, 50)); wins$rand2 <- sort(sample(k, 50)) }
    for (w in names(wins)) {
        r <- tryCatch(ca_verify(A[, wins[[w]], drop = FALSE], t, v = v),
                      error = function(e) NULL)
        if (is.null(r) || !isTRUE(r$covered)) return(w)
    }
    "pass"
}
cat("== Job A: multi-window screens on audit2 SCREEN50 passes ==\n")
a2 <- read.csv("data/cyclotomy_audit2.csv")
todo <- a2[a2$mode == "SCREEN50" & a2$ok %in% TRUE, ]
one <- function(i) {
    t <- todo$t[i]; k <- todo$k[i]; v <- todo$v[i]
    A <- tryCatch({ setTimeLimit(elapsed = 120, transient = TRUE)
                    suppressWarnings(suppressMessages(cyclotomyCA(t, k, v))) },
                  error = function(e) e)
    setTimeLimit(elapsed = Inf)
    if (inherits(A, "error"))
        return(data.frame(t=t,k=k,v=v,type=todo$type[i],q=todo$q[i],
                          result="construct err"))
    A <- as.matrix(A); storage.mode(A) <- "integer"
    data.frame(t=t,k=k,v=v,type=todo$type[i],q=todo$q[i],
               result=screen4(A, t, v))
}
nc <- max(1L, detectCores() - 2L)
res <- NULL
chunks <- split(seq_len(nrow(todo)), ceiling(seq_len(nrow(todo)) / (nc * 2)))
for (ch in chunks) {
    out <- mclapply(ch, one, mc.cores = nc)
    bad <- sapply(out, function(x) !is.data.frame(x))
    for (j in which(bad)) out[[j]] <- one(ch[j])
    res <- rbind(res, do.call(rbind, out))
    write.csv(res, "data/cyclotomy_screen4.csv", row.names = FALSE)
    cat("progress:", nrow(res), "of", nrow(todo),
        " new failures:", sum(res$result != "pass" & res$result != "construct err"), "\n")
}
f <- res[!(res$result %in% c("pass", "construct err")), ]
cat("Job A done.", nrow(res), "rows;", nrow(f), "NEW failures\n")
if (nrow(f)) print(f, row.names = FALSE)

cat("\n== Job B: type-3b repair screens for the giant failures ==\n")
for (p in list(c(2161, 20), c(2311, 21))) {
    q <- p[1]; v <- p[2]
    A <- tryCatch({ setTimeLimit(elapsed = 300, transient = TRUE)
                    suppressWarnings(suppressMessages(cyc(q, v, type = "3b"))) },
                  error = function(e) e)
    setTimeLimit(elapsed = Inf)
    if (inherits(A, "error")) { cat("q=", q, " 3b construct error: ",
        conditionMessage(A), "\n", sep=""); next }
    A <- as.matrix(A); storage.mode(A) <- "integer"
    w <- screen4(A, 3, v)
    cat("q=", q, " v=", v, " type 3b: built ", nrow(A), " x ", ncol(A),
        "  screen4: ", if (w == "pass") "ALL WINDOWS PASS" else paste("FAILS at", w),
        "\n", sep="")
}
cat("\nALL FOLLOW-UP JOBS DONE\n")
