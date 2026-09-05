dyn.load("count_core.so")
suppressMessages(library(CAs))
count_core <- function(x, t, vs, rowmult = TRUE) {
    storage.mode(x) <- "integer"
    .Call("C_count_core", x, as.integer(t), as.integer(vs), as.integer(rowmult))
}
set.seed(1)
## a realistically sized job: N=200, k=40 mixed columns, t=3
vs <- sample(2:4, 40, replace = TRUE)
x <- sapply(vs, function(v) c(sample(0:(v-1)), sample(0:(v-1), 200 - v, replace = TRUE)))
x <- matrix(as.integer(x), 200, 40)
t1 <- system.time(r <- count_core(x, 3, vs, rowmult = TRUE))
t2 <- system.time(cv <- coverage(x, 3, verbose = 1))
cat("colsets:", length(r$tots), "\n")
cat("agree:", isTRUE(all.equal(r$ncovered, as.numeric(cv$ncovereds))), "\n")
cat("count_core (with per-row multiplicities):", t1[3], "s\n")
cat("coverage():                              ", t2[3], "s\n")
cat("speedup:", round(t2[3]/t1[3]), "x\n")
