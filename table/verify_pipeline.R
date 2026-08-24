## verify_pipeline.R - verification pipeline for the provenance table
## Per TABLE_REGISTRATION.md (approved 2026-08-23), section 7.
##
## canon_serialize: canonical form = 0-based integer symbols, one run
## per line, k space-separated values, "NA" for flexible entries, \n
## endings, no header, no trailing whitespace. SHA-256 over UTF-8.
##
## verify_claim: dimensions against the claim, symbols in range, then
## ca_verify at strength t. Emits an append-ready row or a failure.

suppressMessages({ library(caverify); library(digest) })

canon_serialize <- function(x) {
    stopifnot(is.matrix(x))
    mn <- min(x, na.rm = TRUE)
    if (mn == 1) x <- x - 1L          ## canonical form is 0-based
    stopifnot(min(x, na.rm = TRUE) >= 0)
    paste0(paste(apply(x, 1, function(r)
        paste(ifelse(is.na(r), "NA", r), collapse = " ")),
        collapse = "\n"), "\n")
}

canon_sha256 <- function(x) digest::digest(canon_serialize(x),
                                           algo = "sha256", serialize = FALSE)

machine_tag <- function() {
    si <- Sys.info()
    paste0(si["sysname"], "-", si["machine"])
}

verify_claim <- function(x, t, v, k, N, source_id, source_detail,
                         snapshot_id = "", notes = "") {
    x <- as.matrix(x); storage.mode(x) <- "integer"
    dims_ok <- (nrow(x) == N && ncol(x) == k)
    r <- ca_verify(x, t, v = v)
    ok <- dims_ok && isTRUE(r$covered)
    row <- data.frame(
        t = t, v = v, k = k, N = format(N, scientific = FALSE, trim = TRUE),
        tier = if (ok) "VERIFIED" else "FAILED_PENDING_RECHECK",
        source_id = source_id,
        source_detail = source_detail,
        snapshot_id = snapshot_id,
        array_sha256 = canon_sha256(x),
        verify_stamp = paste0("caverify ", packageVersion("caverify"), " ",
                              format(Sys.Date()), " ", machine_tag()),
        entered = format(Sys.Date()),
        notes = if (dims_ok) notes else
            paste0("DIM MISMATCH: got ", nrow(x), "x", ncol(x),
                   " expected ", N, "x", k, ". ", notes),
        lb = "", lb_evidence = "",
        stringsAsFactors = FALSE
    )
    list(ok = ok, covered = isTRUE(r$covered), dims_ok = dims_ok, row = row)
}

## ---- prototype run: one array from each source family ----
## (run with VP_PROTO=1 Rscript verify_pipeline.R; inert when sourced)
if (nzchar(Sys.getenv("VP_PROTO"))) {
    suppressMessages(library(CAs))
    rows <- list(); fails <- 0

    ## S6: her construction, KSK(k=10) claims the Colbourn best-known
    ## entry (t=2, v=2, k=10, N=6) exactly
    D <- KSK(k = 10)
    res <- verify_claim(D, 2, 2, 10, 6, "S6",
                        "CAs::KSK(k=10), CAs 0.24",
                        notes = "matches Colbourn best-known entry")
    cat("KSK(10) -> covered:", res$covered, " dims:", res$dims_ok, "\n")
    rows <- c(rows, list(res$row)); fails <- fails + !res$ok

    ## S5: Dwyer explicit array, CA_9_2_4_3 claims (2,3,4,9), also the
    ## Colbourn best-known
    D <- dwyerCA(2, 4, 3)
    res <- verify_claim(D, 2, 3, 4, 9, "S5",
                        "aadwyer/CA_Database Repository/CA/CA_9_2_4_3.txt via CAs::dwyerCA, CAs 0.24",
                        notes = "matches Colbourn best-known entry")
    cat("Dwyer CA_9_2_4_3 -> covered:", res$covered, " dims:", res$dims_ok, "\n")
    rows <- c(rows, list(res$row)); fails <- fails + !res$ok

    ## S4: NIST explicit array, ca.2.2^10 claims (2,2,10,8), verified
    ## but weaker than the best-known 6
    D <- nistCA(2, 10, 2)
    res <- verify_claim(D, 2, 2, 10, 8, "S4",
                        "math.nist.gov/coveringarrays ipof ca.2.2^10.txt via CAs::nistCA, CAs 0.24",
                        notes = "IPOG-F array; verified, not best-known")
    cat("NIST ca.2.2^10 -> covered:", res$covered, " dims:", res$dims_ok, "\n")
    rows <- c(rows, list(res$row)); fails <- fails + !res$ok

    out <- do.call(rbind, rows)
    write.csv(out, "prototype_verified_rows.csv", row.names = FALSE)
    cat("prototype rows written:", nrow(out), " failures:", fails, "\n")
    if (fails == 0) cat("PIPELINE PROTOTYPE PASS\n") else cat("PIPELINE PROTOTYPE FAIL\n")
}
