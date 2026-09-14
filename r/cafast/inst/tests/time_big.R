suppressMessages({library(CAs); library(caverify)})
suppressMessages(library(cafast))
t0 <- Sys.time(); H <- suppressWarnings(suppressMessages(powerCA(6, 361, 3))); th <- as.numeric(Sys.time()-t0, units="secs")
cat(sprintf("hers powerCA(6,361,3): %d rows, %.1f s\n", nrow(H), th))
t0 <- Sys.time(); A <- power_build(6, 361, 3, 19, 2); tb <- as.numeric(Sys.time()-t0, units="secs")
cat(sprintf("ours power_build(6,361,3,19,2): %d rows, %.1f s\n", nrow(A), tb))
set.seed(3); ok <- TRUE; for (j in 1:5) { cols <- sort(sample(361, 20)); if (!isTRUE(ca_verify(A[, cols], 6, v=3)$covered)) ok <- FALSE }
cat("screen 5x20 covers:", ok, "\nTIME BIG DONE\n")
