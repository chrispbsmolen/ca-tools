# Construction certificates

A construction certificate proves a covering array by its recipe instead of by checking every
t-set of the array. Four constructions are known to the checker, each with its theorem stated
and proved below. They are Power CZ (`powercz-1`, Colbourn and Zhou 2012), fusing one symbol
(`fuse-1`, Colbourn, Keri, Rivas Soriano and Schlage-Puchta 2010, Lemma 3.1), the derived array of
a lower strength (`derive-1`) and the direct product of two strength-2 arrays (`product-1`). Since
2026-11-02 a certificate is also a submission route (`constructions.csv`, section "The submission
route" below), and an ingredient may be an array of the table named by its hash (section
"Ingredients from the table").

## Power CZ (powercz-1)

 For CA(242; 4, 1728, 2) a direct check covers C(1728, 4) = 3.7e11 column
sets; the certificate check of the same array takes about 0.2 s. The checker
`tools/construction_cert.py` (standard library Python) regenerates the hash family, checks every
hypothesis of the coverage proof exactly, rebuilds the array in the table's canonical text and
prints its sha256, so the table records exactly the array that was proved. Nothing is sampled.

Source: C. J. Colbourn and J. Zhou, Improving two recursive constructions for covering arrays,
J. Stat. Theory Pract. 6 (2012) 30-47, doi:10.1080/15598608.2012.647489, Theorem 2.2 with
Lemma 2.3 (statements as transcribed in `r/livingtable/findings/POWERCZ_NOTES.md`). The proof below is
written out in full and is what the checker implements; it does not rely on the paper beyond the
idea.

## The construction

* A hash family H: an M x k array, row i over the symbols 0..w_i-1 (w_i is the width of row i).
  For Power CZ it is the Reed-Solomon family over GF(q): the columns are the q^e polynomials
  f(x) = c_0 + c_1 x + ... + c_{e-1} x^{e-1}, row i is an evaluation point x_i (a field element,
  or "inf", meaning the coefficient c_{e-1}). A row may have forbidden values: every column
  taking a forbidden value in that row is deleted, and the remaining values of the row are
  relabelled 0..w_i-1 in increasing order (w_i = q minus the number of forbidden values).
* One ingredient per row: an R_i x w_i array Q_i over 0..v-1, declared to be a quilting array
  for a set D_i of species (a species is the multiset of the t values of an interaction; for
  v = 2 it is the weight).
* The array: block i is Q_i with column c replaced by column H[i][c] of Q_i, that is
  A_i[r][c] = Q_i[r][H[i][c]]; the blocks are stacked in row order. N = sum of R_i.

## The hypotheses the checker verifies

| name | hypothesis |
|---|---|
| width | (W) w_i >= t for every row i |
| shape | k >= t; every ingredient is a nonempty rectangular array over 0..v-1 with exactly w_i columns for every row i it is assigned to; a column_limit does not exceed the columns kept |
| agreement | (A) any two distinct columns of H agree in at most e-1 rows |
| quilting | (Q) for every ingredient, every t-set of its columns, and every t-tuple whose species is in D_i, some row of Q_i shows the tuple |
| species | (S) for every species S of size t over v symbols, the number of rows i with S in D_i is more than (e-1) tau(S), where tau(S) is the number of pairs of positions with unequal values |
| ingredient_hash | every ingredient file has the sha256 the certificate records |
| field | p is prime, the modulus is monic of degree m, GF(q) has no zero divisors, and (q <= 64) the ring axioms hold exhaustively |
| symbols | the array uses symbol 0 (the table's parser reads it as 0-based only then) |
| N, k, sha256 | the rebuilt array has the certificate's N, k and canonical sha256 |

For t = 4, v = 2, e = 3, (S) reads: weight 2 (tau 4) in more than 8 rows, so all 9; weights 1
and 3 (tau 3) in at least 7; weights 0 and 4 (tau 0) in at least 1. This agrees with our earlier
notes.

(A) is checked exactly by the cheaper of two methods: for every e-subset of rows, the columns'
tuples on those rows are pairwise distinct (two columns agree in at least e rows if and only if
some e-subset of rows maps them to the same tuple), or the direct count over all pairs of
columns. The tests compare both with an independent pairwise count.

The field check is a sanity check only. Soundness does not depend on the generator: (A) is
verified on the family actually generated, so a wrong field, a repeated point or a bug in the
evaluation can only cause a rejection, never a false acceptance.

## Why these hypotheses suffice (proof)

Claim: if (W), (A), (Q), (S) hold and k >= t, the assembled array A is a CA(sum R_i; t, k, v).

Take distinct columns c_1, ..., c_t of A and a target tuple u = (u_1, ..., u_t) over 0..v-1,
with species S. Let P be the set of pairs a < b with u_a != u_b; |P| = tau(S).

1. Separation. For a pair (a, b) in P the columns c_a and c_b agree in at most e-1 rows of H by
   (A). So at most (e-1) tau(S) rows of H give equal symbols to some pair in P. By (S) more than
   (e-1) tau(S) rows have S in D_i, so some row rho with S in D_rho separates every pair in P:
   H[rho][c_a] != H[rho][c_b] whenever u_a != u_b.
2. Induced interaction. In row rho columns with equal symbols have equal target values, so
   g(H[rho][c_a]) = u_a is well defined on the s <= t distinct symbols that occur.
3. Extension to t columns. If s < t (some columns with equal target values collide), choose
   t - s further columns of Q_rho not among those symbols, possible because w_rho >= t by (W).
   For each symbol class of size m with value x give x to m - 1 of the new columns. Now t
   distinct columns of Q_rho carry a tuple whose multiset of values is exactly S.
4. Coverage. S is in D_rho, so by (Q) some row r of Q_rho shows that tuple. The row of A from
   block rho and row r of Q_rho has, in column c_a, Q_rho[r][H[rho][c_a]] = g(H[rho][c_a]) = u_a
   for every a. So u is covered.

(W) is used only in step 3, but it is needed: a quilting array on fewer than t columns has no
t-set, so (Q) holds vacuously for any declared species and such a row would count in (S) without
covering anything. Our earlier notes do not state (W); the paper's widths are all at least t.
The tests show the failure is real (see the mutation table: disabling the width check accepts
non-covering arrays).

(S) with the strict inequality is exactly Lemma 2.3 with s = e. The bound is tight in general:
with ">=" in place of ">" the tests accept non-covering arrays, and the q = 9 recipe (weights 1
and 3 in 5 rows instead of 7) is the known failure of our earlier work.

## Certificate format (construction-cert-1)

A JSON file. Unknown keys and duplicate keys are rejected.

```
{
 "format": "construction-cert-1",
 "construction": "powercz-1",
 "notes": "free text (string or list of strings), optional",
 "t": 4, "v": 2, "e": 3,
 "field": {"q": 9, "p": 3, "m": 2, "modulus": [1, 0, 1]},
 "family": {
   "type": "reed-solomon",
   "rows": [ {"point": 4, "forbidden": [], "ingredient": "S22_13"},
             {"point": "inf", "forbidden": [12], "ingredient": "S14_12"}, ... ],
   "column_limit": 1000                      (optional: keep only the first so many columns)
 },
 "ingredients": {
   "S22_13": {"file": "S22_13.txt", "sha256": "<sha256 of the file bytes>",
              "covers": {"weights": [2, 2]}},
   "tiny":   {"rows": [[0, 1, 1], [1, 0, 1]], "covers": {"species": [[2, 1], [1, 2]]}}
 },
 "expected": {"N": 216, "k": 1368, "array_sha256": "<canonical sha256 of the array>"}
}
```

* Field elements are the integers 0..q-1. For q = p^m the base-p digits of an element, least
  significant first, are the coefficients of a polynomial modulo the monic `modulus` (its
  coefficients constant term first). A prime field (m = 1) takes no modulus. Examples:
  GF(9) with [1, 0, 1] (x^2 + 1), GF(16) with [1, 1, 0, 0, 1] (x^4 + x + 1), as in our gf.py.
* Columns are the coefficient tuples (c_0, ..., c_{e-1}) in lexicographic order with c_0 most
  significant (Python `itertools.product(range(q), repeat=e)`), after deleting the columns with a
  forbidden value; the polynomial is c_0 + c_1 x + ... + c_{e-1} x^{e-1}; point "inf" gives
  c_{e-1}. This is the convention of the build specs from which the four arrays were made.
* `"type": "explicit"` instead gives the rows directly:
  `{"width": w, "values": [k symbols 0..w-1], "ingredient": name}` (no field).
* `covers`: exactly one of `{"weights": [a, b]}` (v = 2: every weight a..b),
  `{"species": [[c_0, ..., c_{v-1}], ...]}` (count vectors summing to t; may be empty), or
  `{"all": true}`.
* An ingredient may instead be `{"table": "<array_sha256>", "covers": ...}`, the array of a
  VERIFIED row of the table (section "Ingredients from the table" below).
* Ingredient files sit beside the certificate (plain names, no paths), whitespace-separated
  integers 0..v-1, one run per line; the sha256 is of the file bytes. Every defined ingredient
  must be assigned to some row.
* The array's canonical text is that of tools/check_submission.py (canon_serialize): one run per
  line, symbols 0-based, single spaces, a line feed after every line.

Usage: `construction_cert.py CERT.json [--write ARRAY.txt] [--quiet]`. Exit 0 only when every
check passes, 1 when a check fails (each failure is printed as `FAIL [check] message`), 2 for a
malformed certificate. It also prints the species table, the certificate's own sha256, and N, k
and the array sha256.

## The four arrays

Certificates in `table/constructions/powercz/` (with the five ingredient files they use), made from our
build specs of the arrays (the construction run of 2026-10-31). The rebuilt sha256 equals the canonical sha256
of the stored array (computed with `check_submission.canonical_of_file`) in all four cases.
The arrays are stored in `table/arrays/` and verified by `ca_verify`, and their table rows name
the certificate in `source_detail`. These four were made and checked by the maintainer before the
submission route existed, and their rows keep their `ca_verify` stamps.

| array | rows of H (width 13 / 12) | rebuilt = stored canonical sha256 | check time |
|---|---|---|---|
| CA(216; 4, 1368, 2) | 3 / 6 | 5c49132e407a66e94957c5fe579c56788f527286bc409ae5491fc6c001722b64 | 0.21 s |
| CA(224; 4, 1476, 2) | 4 / 5 | 5a8352004c792f0ff95f4967f8ffb571364882b0e3b416fbae4fc842556c2b34 | 0.19 s |
| CA(233; 4, 1596, 2) | 5 / 4 | 9fb55bc1f0ddb36b636741ed4176b3a680903754da7a0fd2ed8c1187575beee1 | 0.16 s |
| CA(242; 4, 1728, 2) | 6 / 3 | 336693649e9e2fcdac5ad29e7a57c3063785239b7f7456e6c0a285835d525b0b | 0.21 s |

Times are wall clock for the whole command (Python start, family, all checks, assembly and
hash) on the 2-core test VM.

`table/constructions/powercz_q9_rejected/CA_184_4_729_2.cert.json` is the q = 9 recipe of our earlier work. It
rebuilds exactly the array we stored as FAILED_q9 (sha256 0242863d...), and the checker rejects
it: weights 1 and 3 are declared in 5 rows where 7 are needed.

## Tests of powercz-1

`tools/tests_construction/test_construction_cert.py` (randomized, small parameters) and
`tools/tests_construction/test_real_certs.py`
(planted faults on the four real certificates). The randomized test reimplements independently
of the checker the field arithmetic (multiplication by x with reduction, instead of tables), the
Reed-Solomon family (direct power sums, instead of Horner), every hypothesis by its definition
(pairwise column agreement, every tuple of every declared species on every t-set), the assembly
and the canonical hash. Coverage is decided by `ca_verify.c` from the table repository (exact,
every t-set), itself cross-checked against a pure Python brute force on every small array.

Assertions: (A1) the checker accepts exactly when the independent evaluation finds every
condition true; (A2) a planted fault that takes effect is reported by the check it targets;
(A3) every accepted certificate gives a covering array, and the file the checker writes has the
sha256 it prints, equal to the independently computed one; (A4) every case whose hypotheses hold
gives a covering array (an empirical check of the theorem itself); (A5) both exact agreement
methods agree with the independent pairwise count.

### Results (2026-11-01)

Randomized suite, two seeds, every case exact (no sampling):

| | seed 20261101 | seed 777 |
|---|---|---|
| base scenarios / certificates | 400 / 5510 | 300 / 4146 |
| of these t = 4, v = 2, e = 3 (9 rows, q = 8, 9 or explicit) | 49 base | 29 base |
| valid certificates accepted | 400 of 400 | 300 of 300 |
| accepted certificates whose array is not covering (A3) | 0 | 0 |
| certificates satisfying every hypothesis (independent) / of these not covering (A4) | 1715 / 0 | 1289 / 0 |
| rejected but covering anyway (the hypotheses are sufficient, not necessary) | 2822 | 2077 |
| ca_verify vs Python brute force (arrays with k >= t) | 3504, 0 disagreements | 2601, 0 disagreements |
| agreement: both methods vs independent pairwise count | 5510 families, 0 disagreements | 4146, 0 |
| A1, A2, A3, A4, A5 violations | 0 | 0 |

Configurations: t = 2, 3, 4; v = 2, 3; e = 1, 2, 3; q = 3, 4, 5, 7, 8, 9 (GF(4), GF(8), GF(9) by
modulus); Reed-Solomon families with forbidden values and column limits, and explicit families
(Reed-Solomon with symbols relabelled per row and columns permuted).

Planted faults (seed 20261101; "real" = the fault actually broke the targeted condition by
independent evaluation; "caught" = the checker reported that condition):

| fault | certs | accepted | covering anyway | real | caught |
|---|---|---|---|---|---|
| duplicate evaluation point | 332 | 9 | 138 | 323 | 323 |
| two columns forced to agree in e rows (explicit) | 400 | 0 | 140 | 400 | 400 |
| ingredient missing one pattern of a declared species | 400 | 0 | 236 | 400 | 400 |
| a species in exactly (e-1) tau rows (one too few) | 400 | 0 | 230 | 400 | 400 |
| one ingredient entry changed, hash updated | 400 | 57 | 274 | 343 | 343 |
| ingredient file changed, recorded hash kept | 400 | 0 | 259 | 400 | 400 |
| wrong N / wrong k / wrong array sha256 | 400 each | 0 | | 400 | 400 |
| a row narrowed below t with a vacuous ingredient | 248 | 0 | 166 | 248 | 248 |
| ingredient symbol out of range | 400 | 0 | 5 | 400 | 400 |
| ingredient with one column too many or too few | 400 | 0 | 199 | 400 | 400 |
| reducible field modulus | 130 | 0 | 41 | 130 | 130 |
| array without symbol 0 | 400 | 0 | 0 | 400 | 400 |

The 9 accepted duplicate-point and 57 accepted entry-change certificates are ones where the fault
did not break any condition (independent evaluation), and all of them are covering arrays.

Mutation testing (seed 20261101; seed 777 gives the same picture). Each mutant is killed when
some case's verdict differs from the independent evaluation or a planted fault goes unreported.
"Non-covering" counts certificates the mutant accepts whose array is not a covering array;
"wrong record" counts accepted certificates whose claimed N, k, sha256 or ingredient hashes
differ from the truth.

| mutant | killed by | non-covering accepted | wrong record accepted |
|---|---|---|---|
| disable field | 130 | 0 | 0 |
| disable shape | 800 | 61 | 0 |
| disable width | 248 | 82 | 0 |
| disable ingredient_hash | 400 | 0 | 49 |
| disable agreement | 723 | 454 | 0 |
| disable quilting | 743 | 290 | 0 |
| disable species | 400 | 170 | 0 |
| disable symbols | 400 | 0 | 0 |
| disable N / k / sha256 | 400 each | 0 | 400 each |
| species with >= instead of > | 400 | 170 | 0 |
| agreement bound e instead of e-1 | 526 | 311 | 0 |
| quilting: one tuple per species per t-set suffices | 413 | 197 | 0 |
| quilting: contiguous t-sets only | 169 | 57 | 0 |

No mutant survives. The field and symbols checks are not needed for soundness (0 non-covering
accepted without them): a wrong field can only make the agreement check fail, and an array that
satisfies every hypothesis is covering and so contains symbol 0. They are kept as input
validation and are caught at the reason level by their planted faults.

Real certificates (`tools/tests_construction/test_real_certs.py`): the four pass and match the stored arrays (also
byte for byte with `--write`); a duplicated point (agreement), weights 1 and 3 in 6 rows and
weight 0 in no row (species), an over-claimed ingredient (quilting), wrong N, k, sha256, a
changed forbidden value, a wrong ingredient hash and a duplicate JSON key are all rejected by the
intended check. Every single-entry flip of every ingredient (1684 variants, hash updated) is
rejected by the quilting check exactly when it breaks the declared property (independent
check): 1669 of 1684 do; the 15 that do not are entries of S22_13 that are redundant for weight 2
(the certificate is then rejected only by the array sha256).

Run times: randomized suite 2754 s (seed 20261101) and 2275 s (seed 777), both runs sharing the
2 cores; almost all of it is test-side generation and ca_verify, the checker itself took 31 s and
57 s for all certificates. Commands:

    python3 tools/tests_construction/test_construction_cert.py --cases 400 --seed 20261101
    python3 tools/tests_construction/test_construction_cert.py --cases 300 --seed 777
    python3 tools/tests_construction/test_real_certs.py

The outputs of these runs are not kept in the repository.

## Remarks on the theorem as used

* Our notes' conditions for t = 4, e = 3 are right, and the general form (every species in more
  than (e-1) tau rows, tau the unequal pairs) is exactly what the proof needs. The strict
  inequality matters: with ">=" the tests accept non-covering arrays.
* The notes omit two conditions the proof needs: every row's width must be at least t (otherwise
  an ingredient's quilting property is vacuous), and k >= t. Both hold for all four arrays
  (widths 12 and 13).
* The proof uses only the agreement bound of the family, not that it is Reed-Solomon, distributing
  or built over a field; the checker verifies the bound on the generated family, so the field
  description is not trusted.
* The paper's Theorem 2.1 constant-row saving (chi) is not part of powercz-1; a certificate that
  uses it needs a separate construction id.

## Ingredients from the table

In every construction an ingredient may be given in three ways. `{"rows": [[...], ...]}` puts it
inline, and `{"file": "name.txt", "sha256": "<sha256 of the file bytes>"}` names a file beside the
certificate. Both are checked here exhaustively (a quilting check for Power CZ, every t-set and
every tuple for the other constructions). An inline or file ingredient whose check would read more
than 3 x 10^8 entries is refused, and must be entered in the table first. The third form,
`{"table": "<array_sha256>"}`, names the array of a counted VERIFIED row of the table (tier
VERIFIED and not retracted, `counted()` in `table/ca_table.py`). The checker reads it from
`table/arrays/` (gzip or plain), checks that its canonical text hashes to that value, refuses an
array with don't-care entries, and trusts its coverage as verified by the table. The check
`ingredient_table` then requires the row's strength to be at least the strength the construction
needs of that ingredient, its v to be the v needed, and its N and k to be those of the stored
array. A Power CZ ingredient from the table takes `covers` as usual and is not given to the
quilting check (a covering array of strength at least t covers every species). The array of a
row that is not stored (a certificate row whose array is not in `table/arrays/`) cannot be used
this way yet. `--table-dir DIR` points the checker at a table (by default the `table/` of the
repository).

The other three constructions share these checks.

| name | hypothesis |
|---|---|
| shape | every ingredient is a nonempty rectangular array over 0..v_in-1 (the symbols the theorem needs of it), with at least as many columns as the strength needed of it |
| ingredient_hash | every file ingredient has the sha256 the certificate records |
| ingredient_ca | every inline or file ingredient is a covering array of the strength needed, over v_in symbols (exhaustive) |
| ingredient_table | (only when a table ingredient is named) as above |
| symbols, alphabet | the rebuilt array uses symbol 0, and only symbols 0..v-1 |
| N, k, sha256 | the rebuilt array has the certificate's N, k and canonical sha256 |

An ingredient has no don't-care entries. The format of these three is `construction-cert-1` with
the keys `format`, `construction`, `t`, `v` (of the array built), `expected` (`N`, `k`,
`array_sha256`, as for Power CZ), optional `notes`, and the keys of the construction below.
Unknown and duplicate keys are rejected.

## Fusing a symbol (fuse-1)

Source: C. J. Colbourn, G. Keri, P. P. Rivas Soriano and J.-C. Schlage-Puchta, Covering and
radius-covering arrays: constructions and classification, Discrete Appl. Math. 158 (2010)
1158-1180, Lemma 3.1 (`fuse-ckrs2010` in `table/references.csv`).

Theorem. Let t >= 2, v >= 2, and let A be a CA(N; t, k, v+1) over the symbols 0..v. Let z and r
be two distinct rows of A. In every column c exchange the symbols A[z][c] and v (so row z reads v
everywhere). Delete rows z and r, and in every other row replace an entry v in column c by the
entry R[c] of row r in that column after the exchange (by 0 when R[c] is v). The result is a
CA(N-2; t, k, v).

Proof. Exchanging two symbols in a column keeps a covering array covering, so let A be the array
after the exchanges, with row z constant v. Take t columns c_1, ..., c_t and a tuple u over
0..v-1. Some row X of A shows u, and X is not row z (u has no v). If X is not row r, its entries
in these columns are u (none is v), so after the replacement X still shows u. If X is row r, then
R[c_1] = u_1 is not v. The tuple (v, u_2, ..., u_t) is shown by some row Y of A. Y is not row z,
since u_2 is not v (here t >= 2 is used), and Y is not row r, since R[c_1] is not v. After the
replacement Y has R[c_1] = u_1 in column c_1 and u_2, ..., u_t in the others, so Y shows u. Every
entry of the result is in 0..v-1, and it has N-2 rows.

Hypotheses checked: shape, ingredient_hash, ingredient_ca or ingredient_table (the input is a
CA(N; t, k, v+1)), `fuse_strength` (t >= 2), `fuse_rows` (z and r are two distinct rows of the
input), then symbols, alphabet, N, k, sha256. The rebuild is the rule of `tools/cphf/fuse2.c`
(`+fuse2 v` in `tools/cphf/README.md`) with rows z and r in place of the first two.

    {"format": "construction-cert-1", "construction": "fuse-1", "t": 2, "v": 3,
     "input": {"table": "<array_sha256 of a CA(N; 2, k, 4) of the table>"},
     "rows": [0, 1],                                  (optional, default [0, 1])
     "expected": {"N": 14, "k": 5, "array_sha256": "..."}}

## The derived array (derive-1)

Source: the derived array is folklore of the subject, stated for covering arrays as inequality
(7) of Colbourn, Keri, Rivas Soriano and Schlage-Puchta 2010 (`fuse-ckrs2010`), and used by
`tools/derive_laws.py` for the sizes of `table/derived.csv`.

Theorem. Let t >= 1 and let A be a CA(N; t+1, k+1, v) with k >= t. For a column c and a symbol
s, the rows of A with s in column c, with column c deleted, form a CA(N_s; t, k, v), N_s the
number of those rows. (With s the symbol that occurs least in column c, N_s <= floor(N/v), which
is inequality (7).)

Proof. Take t columns other than c and a tuple u over 0..v-1. The t+1 columns with c added carry
the tuple (s, u) in some row of A (strength t+1). That row has s in column c, so it is one of the
rows kept, and it shows u in the t columns.

Hypotheses checked: shape, ingredient_hash, ingredient_ca or ingredient_table (the input is a
CA(N; t+1, k+1, v)), `derive_column` (c is a column of the input and the result has at least t
columns), `derive_symbol` (s is one of 0..v-1), then symbols, alphabet, N, k, sha256. The rows
kept stay in their order.

    {"format": "construction-cert-1", "construction": "derive-1", "t": 2, "v": 2,
     "input": {"file": "ca3.txt", "sha256": "..."}, "column": 2, "symbol": 1,
     "expected": {"N": 9, "k": 5, "array_sha256": "..."}}

## The direct product (product-1)

Source: the direct product of strength-2 covering arrays, in C. J. Colbourn, S. S. Martirosyan,
G. L. Mullen, D. Shasha, G. B. Sherwood and J. L. Yucas, Products of mixed covering arrays of
strength two, J. Combin. Des. 14 (2006) 124-138 (`product-cmmssy2006`). Saving rows through
constant rows is studied in C. J. Colbourn and J. Torres-Jimenez, Profiles of covering arrays of
strength two, J. Algorithms Comput. 44 (2013) 31-59 (`pca-ct2013`).

Theorem. Let A be a CA(N1; 2, k1, v) and B a CA(N2; 2, k2, v). Optionally make one row a of A
constant 0 by exchanging, in every column, its entry with 0, and the same for one row b of B. Index
the k1 k2 columns by pairs (i, j), i < k1, j < k2, in the order i k2 + j. The rows are, for every
row x of A, the row with x[i] in column (i, j), then, for every row y of B, the row with y[j] in
column (i, j), except the rows y that are constant with a symbol for which A has a constant row.
The result is a CA(N1 + N2 - d; 2, k1 k2, v), d the number of rows left out.

Proof. Take columns (i, j) and (i', j') and a pair (x, y) of symbols. If i and i' differ, A covers
(x, y) in columns i and i' in some row, and its row in the first part shows (x, y). If i = i',
then j and j' differ, and B covers (x, y) in columns j and j' in some row y'. If that row of the
second part was left out, y' is constant and so x = y, and A has the row constant x, whose row in
the first part shows (x, x). Exchanging symbols within a column keeps A and B covering.

Hypotheses checked: shape, ingredient_hash, ingredient_ca or ingredient_table (both inputs are
covering arrays of strength 2 over v symbols), `product_strength` (the certificate says t = 2),
`product_constant_rows` (each given row is a row of its ingredient), then symbols, alphabet, N, k,
sha256. With no constant rows given, rows that happen to be constant still count. Making one row
of each ingredient constant always saves one row, N1 + N2 - 1. The generalized products of
Colbourn and Torres-Jimenez 2013 (Corollary 4.3, as `tools/derive_laws.py` states it for
`table/derived.csv`, CAN(2, k1 k2, v) <= CAN(2, k1, v) + CAN(2, k2, v) - 2) are not part of
product-1, and a certificate that uses them needs a construction id of its own.

    {"format": "construction-cert-1", "construction": "product-1", "t": 2, "v": 3,
     "first": {"rows": [[0, 0, 0, 0], ...]}, "second": {"table": "<array_sha256>"},
     "constant_rows": [0, null],                      (optional, default [null, null])
     "expected": {"N": 17, "k": 16, "array_sha256": "..."}}

## The submission route

A submission `submissions/<slug>/constructions.csv` (`submissions/README.md`, "Construction
certificates") names certificates in its folder, with the fields of `claims.csv`. On the pull
request `tools/check_constructions.py --light` runs the checker and reports. On main
`.github/workflows/table-page.yml` runs it again with the tools of main and enters the rows. The
row of an array built by a certificate is identified, like every array row, by the canonical
sha256 of the rebuilt array (`array_sha256`), and `family_sha256` stays empty. The certificate is
always stored, in `table/constructions/<slug>/` with its file ingredients, and listed in
`table/constructions/CONSTRUCTIONS.csv` (file, t, v, k, N, construction, the certificate's sha256,
array_sha256, the check, and the stored array if any). It is the recipe that rebuilds the array.
The rebuilt array itself is stored in `table/arrays/` by the rules of submitted arrays when it is
at most 50 MiB as text (gzip above 1 MiB). A larger array is kept only as its certificate, and the
row's notes say so. The row's stamp is `construction_cert <tool> <date> <machine> (<construction>,
exact)`, the tool being the first twelve hex digits of the sha256 of `tools/construction_cert.py`,
and its check method (`check_method()` in `table/ca_table.py`) is "construction certificate". When
`ca_verify` can check a stored array within two minutes, it does so as well, and a disagreement
fails the claim. `tools/consistency.py` rebuilds every listed certificate of at most 5 x 10^7
entries and compares the sha256, and requires every row stamped `construction_cert` to have its
listing. A certificate that names a table ingredient therefore stops passing when that row is
retracted, which shows the rows that depend on it.

## Tests of fuse-1, derive-1, product-1 and table ingredients

`tools/tests_construction/test_kinds.py` writes random small certificates of the three
constructions, valid ones and ones with planted faults, with their ingredients inline, in files or
in a small table of their own. It rebuilds each array with its own code, evaluates every
hypothesis by its definition (its own coverage count for every ingredient), and checks every
rebuilt array with `ca_verify`, itself compared with a Python brute force. The assertions are those
of the Power CZ tests (A1 to A4). Then each check is disabled in turn, and three boundary mutants
are applied (fuse_strength with t >= 1, ingredient_table without comparing the strength,
ingredient_ca one strength lower). It also checks Power CZ certificates whose ingredient is a
table array (24 certificates, a row of too low strength refused by ingredient_table).
`tools/tests_construction/test_route.py` runs the route end to end on a copy of the table.

### Results (2026-11-02)

| | seed 20261102 | seed 777 |
|---|---|---|
| certificates (400 per construction) | 1200 | 1200 |
| valid certificates accepted | 402 of 402 | 402 of 402 |
| faulted certificates accepted | 0 of 798 | 0 of 798 |
| certificates satisfying every hypothesis / of these not covering (A4) | 402 / 0 | 402 / 0 |
| ca_verify vs brute force | 972 arrays, 0 disagreements | 1020 arrays, 0 disagreements |
| Power CZ with a table ingredient | 24, 0 errors | 24, 0 errors |
| A1, A2, A3, A4 violations | 0 | 0 |
| mutants surviving (18) | 0 | 0 |

Mutants (seed 20261102), the cases that kill each and the non-covering arrays each accepts:
disable shape 89 / 0, ingredient_hash 66 / 0, ingredient_ca 79 / 45, ingredient_table 88 / 45,
fuse_strength 26 / 2, fuse_rows 28 / 0, derive_column 29 / 0, derive_symbol 27 / 0,
product_strength 27 / 27, product_constant_rows 33 / 0, symbols 49 / 0, alphabet 34 / 0, N 78 / 0,
k 75 / 0, sha256 70 / 0. The boundary mutants: fuse_strength with t >= 1 26 / 2, ingredient_table
without the strength 45 / 45, ingredient_ca one strength lower 79 / 45. The checks that accept no non-covering array
when disabled (fuse_rows, derive_column, derive_symbol, product_constant_rows, shape) guard against
a recipe that cannot be rebuilt or would be recorded wrongly, and their planted faults are each
reported by the check itself. The Power CZ suite (`test_construction_cert.py --cases 40`) passes
unchanged with the new code (15 mutants killed).

    python3 tools/tests_construction/test_kinds.py --cases 400 --seed 20261102
    python3 tools/tests_construction/test_kinds.py --cases 400 --seed 777
    python3 tools/tests_construction/test_route.py
