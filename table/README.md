# A provenance-tracked table of best-known covering array sizes

Dated snapshot, 2026-08-23. This table replaces folklore with
evidence: every entry says where it came from, and several hundred
entries carry machine verification stamps tied to explicit arrays you
can check yourself. It is complete as it stands. No future updates are
promised by anyone; the format below makes it maintainable by whoever
finds that worth doing.

## What is here

- `ca_table.csv` - the table, 14,174 rows, append-only, one row per
  evidence event. Schema below.
- `ca_table.rda` - the same table as a compressed R data frame
  (object `ca_table`), regenerated from the CSV by
  `ca_table.R::make_rda()`.
- `ca_table.R`, `ca_table.py` - small query helpers for R and Python
  (best known N, stair-step, verified rows). No dependencies.
- `arrays/` - 258 explicit arrays in canonical form (0-based integer
  symbols, one run per line, space separated; `NA` marks a don't-care
  entry, see below). 224 equal the best-known size for their
  parameters; 34 are SMALLER than the snapshot's recorded best (the
  MANIFEST `status` column separates `equals_best` from
  `exceeds_snapshot`). File names are `CA_N_t_k_v.txt`, with a hash
  suffix where two distinct arrays share parameters.
- `MANIFEST.csv` - one row per array file: parameters, status,
  SHA-256 of the canonical file content, retrieval recipe,
  verification stamp.
- `VERIFICATION_LOG.md` - the record of the verification runs that
  produced the stamps.
- `verify_pipeline.R` - the canonicalization, hashing, and
  verification code used to stamp rows, so anyone can stamp new ones
  the same way.

Some arrays contain `NA` don't-care entries. Verification uses the
"promise" semantics: coverage holds on the concrete entries alone, so
these arrays remain covering no matter how the don't-cares are filled.

The 34 `exceeds_snapshot` arrays are published work, chiefly
Torres-Jimenez arrays shipped in the CAs package, whose run sizes beat
the November 2024 snapshot's recorded rung at their parameters. The
improvements belong to their published sources; this table's
contribution is only the verification stamp and the side-by-side
accounting. Each such row's notes name the snapshot value it beats.

## Schema

`t, v, k, N` is the claim, with stair-step semantics: the row means
"N runs suffice for a strength-t covering array on up to k columns of
v symbols". `tier` is the evidence class:

- `CITED` - traceable to a dated snapshot or publication, no array in
  hand. The 13,641 baseline rows are the November 2024 status of the
  Colbourn tables, taken from the `colbournBigFrame` snapshot that
  Ulrike Groemping preserved in her CAs package after the original
  site (public.asu.edu/~ccolbou) became unavailable.
- `VERIFIED` - an explicit array is in hand and was checked
  exhaustively by the caverify kernel at the claimed strength. The
  row carries the array's SHA-256 (canonical form) and a stamp naming
  the caverify version, date, and machine.
- `FAILED_PENDING_RECHECK` - a verification attempt that failed its
  dimension check. Kept because history is never rewritten; each such
  row is superseded by a later resolution row. The three present at
  publication all trace to one discrepancy, the Dwyer CA_Database
  files hold fewer rows than their names and catalogued counts
  state, cause undetermined. All three arrays verify at their
  actual, smaller sizes.
- `DISPUTED` - reserved for verification failures that survive
  recheck. None at publication.

`source_id` names the source class (S1 Colbourn snapshot, S4 NIST
covering array library, S5 Dwyer CA_Database, S6 the CAs package's
data and constructions, S7 literature). `source_detail` is the exact
retrieval or generation recipe. `snapshot_id` dates the source.
`lb, lb_evidence` are reserved for lower-bound evidence and are empty
in this version.

## Querying

    Rscript -e 'source("ca_table.R"); tab <- load_ca_table(); best_known(tab, 5, 3, 7)'
    python3 ca_table.py best 5 3 7
    python3 ca_table.py verified 5 3

Both return 351 for the first query, and the second shows the stamp:
that array is in `arrays/CA_351_5_7_3.txt`, its SHA-256 is in the
table, and you can re-verify it yourself in one line with the
caverify package.

## How to append a row (maintainer's guide)

The table is append-only. To add a claim with evidence:

1. Get the array (download, construct, or receive it) and note the
   exact recipe: URL and date, or the generating call and package
   version, or the DOI.
2. Canonicalize: 0-based integer symbols, one run per line, space
   separated, newline endings. `verify_pipeline.R::canon_serialize`
   does this; `canon_sha256` hashes it.
3. Verify: `verify_claim(D, t, v, k, N, source_id, source_detail)`
   runs caverify at strength t and returns an append-ready row with
   the hash and stamp filled in. A failed check returns a
   FAILED_PENDING_RECHECK row; recheck from a fresh copy before
   concluding anything, catalogues go stale (see the log).
4. Append the row to `ca_table.csv`, never edit existing rows. A
   better N is a new row; a correction is a new row whose notes
   reference what it supersedes.
5. Regenerate `ca_table.rda` with `make_rda()`, and if you add the
   array to `arrays/`, add its MANIFEST.csv line.

Admissible sources and the full protocol are in
TABLE_REGISTRATION.md in the maintainers' records; the short version
is: dated, re-fetchable or re-derivable sources only.

## Attribution

The baseline is the work of Charles J. Colbourn (the covering array
tables, 2005-2024) as preserved by Ulrike Groemping. Explicit arrays
come from the NIST covering array library (IPOG-F), the Dwyer
CA_Database (github.com/aadwyer/CA_Database), and the constructions
and data of the CAs R package (Groemping). Verification stamps were
produced with the caverify R package (this repository). The arrays
themselves are mathematical objects; each file's origin is in the
MANIFEST.
