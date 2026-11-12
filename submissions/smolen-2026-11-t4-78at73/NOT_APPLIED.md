# Not added to the table

Checked again on main at c14a8ef; it did not pass. Delete this file to try again.

## Covering array submission check: `smolen-2026-11-t4-78at73`

**Result: FAIL.** 1 of 1 claims passed; nothing is applied to the table until every claim passes.

Checked 2026-11-12 with `ca_verify` (ca_verify c14a8ef 2026-11-12 github-actions), 2 threads, budget 15.0 min per array, full check when its predicted time is at most 40 percent of that, otherwise a screen of 20 windows x 30 columns. Total time 0.0 s.

| # | file | t | v | k | N | result | status | vs table | previous best | time |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | CA_78_4_73_2.txt | 4 | 2 | 73 | 78 | PASS | verified | exceeds_table | 79 | 0.0 s |

### Credit check

Flags for the maintainer's review of credit. They do not affect the result above; the maintainer reads the credit of every submission before merging.

- claims.csv row 1, CA(78; 4, 73, 2) `CA_78_4_73_2.txt`, **named**: the text names Torres-Jimenez, and none of the 16 references with that author (afso-atji2018, caex-tjaa2021, cphf-itaa2018, cphf-ti2018, ...) is in builds_on

### Submission problems

- **HOW.md has no "Program:" part**

### Details

**1. CA_78_4_73_2.txt** (PASS)

- sha256 (canonical form): `49706c1c24a340bb28c726e2fab0c8bec2fc716d75d773573bb610a322ef2b3f`
- construction: Cyclotomic (quadratic character) array for q = 73 with its 73 diagonal cells chosen by search and 5 rows added by simulated annealing
- builds on: cyclotomy-c2010;paley-p1933;new https://github.com/chrispbsmolen/ca-tools/tree/main/submissions/smolen-2026-11-t4-78at73/programs
- verified exhaustively at strength 4 in 0.0 s
- constant rows: 2 of 2 can be made constant by permuting symbols within columns (computed in 0.0 s)
- table: exceeds_table; previous best 79 (row k=79, CITED S1 colbourn-2024-11-ug: Derive from strength 5)
- similarity: no match (no known array with the same N, k and v)
- prior work to cite: the previous best is an entry of the Colbourn tables (November 2024 status, preserved in the CAs package as colbournBigFrame), labelled "Derive from strength 5"; C. J. Colbourn, Covering arrays from cyclotomy, Des. Codes Cryptogr. 55 (2010) 201-219, doi:10.1007/s10623-009-9333-8; R. E. A. C. Paley, On orthogonal matrices, J. Math. Phys. 12 (1933) 311-320, doi:10.1002/sapm1933121311; the method of this submission, described at https://github.com/chrispbsmolen/ca-tools/tree/main/submissions/smolen-2026-11-t4-78at73/programs; this table: C. Smolen, ca-tools, https://github.com/chrispbsmolen/ca-tools, with the commit used
- note: builds_on names a new method (https://github.com/chrispbsmolen/ca-tools/tree/main/submissions/smolen-2026-11-t4-78at73/programs); the maintainer confirms it before the merge


Not applied: the submission did not pass.
