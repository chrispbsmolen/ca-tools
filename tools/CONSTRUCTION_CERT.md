# Construction certificates

A construction certificate proves a covering array by its recipe instead of by checking every
t-set of the array. Nine constructions are known to the checker, each with its theorem stated
and proved below. They are Power CZ (`powercz-1`, Colbourn and Zhou 2012), Power CZ with relabelled
blocks and constant tuples proved by enumeration (`powercz-2`, since 2026-11-03), fusing one symbol
(`fuse-1`, Colbourn, Keri, Rivas Soriano and Schlage-Puchta 2010, Lemma 3.1), the derived array of
a lower strength (`derive-1`), the direct product of two strength-2 arrays (`product-1`), and the
two strength-4 constructions of Shokri, Moura and Stevens from truncated Moebius planes (`sms51-1`
and `sms65-1`, since 2026-11-10), the strength-3 x-plications of Shokri and Moura
(`sm-xplication-1`, since 2026-11-10), and the product of Colbourn and Torres-Jimenez that saves one
row for each constant row of either ingredient (`product-ctj-1`, since 2026-11-11). Since
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

## Power CZ with relabelled blocks (powercz-2)

`powercz-2` extends `powercz-1` in two ways, for binary arrays (v = 2). Each row of the hash
family may carry its own permutation of the ingredient's columns, and the constant tuples (weight
0, all entries 0, and weight t, all entries 1) may be proved by an exact enumeration done by the
checker, instead of being declared by some block. The second change is what lets every block drop
its constant rows. The first is what makes the enumeration come out empty. For the CA(1400; 5,
10201, 2) of `submissions/smolen-2026-11-powercz10201/`, seven blocks of a 200-row Paley ingredient
without its two constant rows replace the 2 + 7 x 200 = 1402 rows of Power CT with shared constant
rows. Both changes are new in this repository (2026-11-03). The method underneath is Colbourn and
Zhou's (Theorem 2.2 with Lemma 2.3, `power-cz2012`), and `builds_on` gets that reference as for
`powercz-1`.

### The construction

As in `powercz-1` there is a hash family H (M rows, k columns, row i over 0..w_i-1 after the
forbidden values are removed) and one binary ingredient Q_i with R_i rows and w_i columns per row,
declared to cover a set D_i of weights. Row i may also give a permutation pi_i of 0..w_i-1 (the
identity when it gives none). Block i of the array is A_i[r][c] = Q_i[r][pi_i(H[i][c])], so the
symbol x of row i selects column pi_i(x) of the ingredient. A set E of enumerated weights is a
subset of {0, t}.

### The theorem

Let H' be the family with H'[i][c] = pi_i(H[i][c]). For a weight in E write z for its constant
value (z = 0 for weight 0, z = 1 for weight t). Call a set of ingredient columns bad for z when no
row of the ingredient is constant z on it. The image of a set T of array columns in block i is
the set {H'[i][c] for c in T} of ingredient columns. Suppose that

* (W), (A) and (Q) hold as for `powercz-1`,
* (S') every weight w not in E is declared in more than (e-1) w (t-w) rows,
* (E1) for every weight in E, no ingredient has a set of fewer than t columns that is bad for z,
* (E2) for every weight in E, no t-set T of array columns has, in every block i, an image of t
  columns that is bad for z.

Then the array is a CA(sum R_i; t, k, 2).

### Proof

Relabelling. A permutation is a bijection, so two columns of H' agree in row i exactly when they
agree in row i of H. H' therefore has the widths and the agreement bound of H, and the array is
the `powercz-1` array of H' with the same ingredients. The proof of `powercz-1` covers a target
tuple using (S) for that tuple's species only. So every tuple whose weight is not in E is covered
by (W), (A), (Q) and (S').

Constant tuples. Take a weight in E, its value z, and a t-set T of array columns. If the image of
T in some block i has s < t columns, (E1) gives a row of Q_i that is constant z on the image, and
the row of the array from that row of Q_i is constant z on T. Otherwise every image has t
columns. If some image is not bad, a row of that block is constant z on T. So z^t is missed on T
only when every image has t columns and is bad, and (E2) says this never happens. This is the
collapse argument. A t-set whose image collapses in some block is covered there because the
collapsed image is a smaller set, which (E1) pads, and repeated columns cost nothing when every
target value is the same.

### How the checker verifies (E1) and (E2)

(E1) is checked by listing, for each ingredient and each s = 1, ..., t-1, the s-sets of columns
that are bad for z. Every count must be 0. (A bad s-set makes every larger set containing it bad,
so the counts stop at the first s that has one.)

(E2) is checked for e = 2 by enumeration. Choose two rows a and b of the family. By (A) with e = 2,
two distinct columns agree in at most one row, so the map c -> (H'[a][c], H'[b][c]) is injective.
For every bad t-set X_a = {x_1 < ... < x_t} of Q_a, every bad t-set X_b of Q_b and every bijection
sigma from X_a to X_b (t! of them), the checker looks up for each j the column c_j with values
(x_j, sigma(x_j)) in rows a and b. When all t exist they are t distinct columns (their values in
row a differ), a candidate. The candidate survives if no other block has a row constant z on its
image (the test ANDs, over the t columns, the rows equal to z, so a collapsed image is tested as
the smaller set it is). The weight passes when there is no survivor.

The enumeration is exhaustive. Let T violate (E2). Its images X_a and X_b are bad t-sets, and
sigma(H'[a][c]) = H'[b][c] for c in T is a bijection between them. At (X_a, X_b, sigma) the
lookup returns exactly the columns of T, and T survives the test of the other blocks. Conversely
a survivor is a t-set whose images in rows a and b are bad t-sets and which has no row constant z
in any other block, so it violates (E2). Different triples give different t-sets (the t-set
determines its images and sigma), so the number of survivors is exactly the number of t-sets of
array columns that miss z^t, given (E1). The tests compare that number with a brute-force count.

The checker takes a and b with the smallest product of the numbers of bad t-sets (the first such
pair in order). If some block has no bad t-set, the product is 0 and so is the count. (E1) is
needed only for the two blocks a and b (in the other blocks the test sees a collapsed image as
it is), but the checker requires it of every ingredient, which is simpler to state. It is not
redundant. The fixed example of the tests (t = 3, an explicit family of three columns) has a
t-set that collapses onto a bad 2-set in rows a and b and misses 000, and the enumeration without
(E1) accepts it. An ingredient that covers weight 1 on every t-set has no bad (t-1)-set for z = 0
(the tuple with t-1 zeros and a one would be missing), and one that covers weight t-1 has none
for z = 1, so (E1) holds automatically for ingredients that declare weights 1 and t-1.

Only the constant tuples may be enumerated. For a tuple with two different values, a t-set whose
image collapses two columns with different targets cannot be covered in that block at all, and
the padding argument above fails. The checker refuses any other weight in `enumerate_weights`.
The enumeration is implemented for e = 2 only. For e >= 3 a column is determined by e rows, which
would need e lists and (t!)^(e-1) bijections. A certificate with `enumerate_weights` and another
e is refused as malformed.

### Format

As for `powercz-1` (section "Certificate format" above), with `"construction": "powercz-2"`, v = 2,
2 <= t <= 7, and two more keys.

* `"enumerate_weights": [0, t]` at the top level (optional, default empty) lists the weights
  proved by enumeration, a subset of {0, t} without repeats. When it is not empty, e must be 2.
* `"relabel": [pi(0), ..., pi(w-1)]` in a family row (optional, default the identity), for a
  Reed-Solomon or an explicit family. Here w is the row's width after the forbidden values are
  removed, and the symbol x of the row (numbered 0..w-1 in increasing order, as in `powercz-1`)
  selects ingredient column pi(x).

A `powercz-1` certificate with either key is malformed, so `powercz-1` is unchanged.

### The checks

| name | hypothesis |
|---|---|
| field, shape, width, ingredient_hash | as for `powercz-1` |
| agreement | (A) on the relabelled family H' (the same as on H) |
| relabel | every `relabel` is a permutation of the columns 0..w_i-1 of its row's ingredient (otherwise it is reported and not applied) |
| quilting | (Q), exact, every t-set of columns of every file or inline ingredient |
| species | (S'), every weight not in `enumerate_weights` declared in more than (e-1) tau rows |
| enumeration | (E1) and (E2) for every weight in `enumerate_weights`, with the survivor count, which must be 0 |
| symbols, N, k, sha256 | as for `powercz-1`, on the array assembled with the relabelling |

The quilting check, the lists of bad sets and the enumeration run in the C helper
`tools/cz2help.c`. The checker compiles it at run time with `cc -O3` into a temporary folder (as
`tools/check_upgrades.py` builds `ca_verify`), after checking that the source has the sha256
recorded in `construction_cert.py` (`HELPER_SHA256`). The tool hash in a row's stamp (the sha256 of
`construction_cert.py`) therefore fixes the helper too, and a change to `cz2help.c` must update that
constant. The helper reads the ingredients as the checker parsed them (written to temporary files)
and exits with an error on anything unexpected, which fails the check. It refuses work above 10^11
operations on 64-bit words. Without a compiler, when the build fails or when the source hash
differs, exact Python code does the same work and refuses (fails the check, never passes it) above
3 x 10^8 entry reads, the limit of inline ingredients. For the 1400 certificate that limit is far
exceeded, so a run without `cc` rejects it. The environment variable `CONSTRUCTION_CERT_NO_HELPER=1`
forces the Python path.

### Example

The certificate `submissions/smolen-2026-11-powercz10201/CA_1400_5_10201_2.cert.json` (relabel
lists shortened here)

    {"format": "construction-cert-1", "construction": "powercz-2",
     "t": 5, "v": 2, "e": 2, "field": {"q": 101, "p": 101, "m": 1},
     "family": {"type": "reed-solomon", "rows": [
        {"point": 0, "forbidden": [], "ingredient": "S14_101", "relabel": [76, 0, 47, ...]},
        ... points 1 to 6, each with its own relabel ...]},
     "ingredients": {"S14_101": {"file": "S14_101.txt", "sha256": "fea4d881...",
                                 "covers": {"weights": [1, 4]}}},
     "enumerate_weights": [0, 5],
     "expected": {"N": 1400, "k": 10201, "array_sha256": "049f3a68..."}}

S14_101 is the Paley-type CA(202; 5, 101, 2) of q = 101 without its two constant rows. The checker
reports (about 20 s on the 2-core VM, 15 s of it the quilting check of C(101, 5) = 79,208,745
column sets)

    pass [enumeration]
      weight 0: tuple 0^5; bad s-sets (s = 1..5) per ingredient: S14_101 0/0/0/0/759; blocks 0 and 1,
      69129720 cases, 69129720 give array columns, 0 survivors (cz2help)
      weight 5: ... the same numbers ...
      weight 0       tau  0  need >=  1  have  0  (enumerated)
      weight 1       tau  4  need >=  5  have  7
      weight 2       tau  6  need >=  7  have  7
    N = 1400  k = 10201  t = 5  v = 2  sha256 = 049f3a6878cf9a73eae8b73a0267dadbc279cea6ea5cceb1ded0301dbed0d1ad
    CERTIFICATE VALID

With the identity relabelling in every row the same certificate is rejected by the enumeration,
with 20873 survivors for weight 0 and 20873 for weight 5 (all of them t-sets of columns that miss
the constant tuple). This agrees with two separate programs written before the checker.

### Tests of powercz-2

`tools/tests_construction/test_powercz2.py` has three parts.

1. The real certificate passes and rebuilds the array of sha256 049f3a68.... The identity
   relabelling is rejected with 20873 survivors per weight. Planted faults are rejected by the
   check they target. These are a relabel that is not a permutation (a repeated entry, one entry
   short, an entry out of range), a wrong ingredient hash, a family row removed (species), weight
   5 declared by the ingredient (quilting), an ingredient without one row (quilting), a repeated
   point (agreement), weight 5 missing from `enumerate_weights` (species), e = 1 or 3, weight 2 in
   `enumerate_weights`, and either new key in a `powercz-1` certificate (malformed). Without the
   helper, and with a helper source of another sha256, the certificate is rejected.
2. The helper against the Python code on random binary arrays (t = 2 to 6), the number of
   missing (t-set, tuple) pairs with the first miss, and the bad-set counts for z = 0 and 1.
3. Random small certificates (t = 3, 4, q = 5, 7, e = 2, 3 to 6 rows, forbidden values, column
   limits, random relabellings) against an independent oracle with its own Reed-Solomon
   evaluation, relabelling and assembly and a brute-force count over every t-set. The assertions
   are (A1) every accepted certificate gives a covering array with the independently computed
   sha256, (A2) every survivor count equals the brute-force number of t-sets missing the constant
   tuple, (A3) the helper and the Python code give the same verdict, failures and counts, (A4)
   every case whose declared weights are true, whose species rule holds, whose ingredients have
   no bad set below t and whose array misses no constant tuple is accepted, and (A5) planted
   faults on accepted cases are caught by their check. Two mutants must each accept a
   non-covering array, the enumeration check disabled (random cases with the identity
   relabelling) and the condition (E1) dropped (the fixed example above).

#### Results (2026-11-03)

| | seed 20261103 | seed 777 |
|---|---|---|
| real certificate and its 17 planted faults | all as intended | (not run, `--skip-real`) |
| identity relabelling, survivors for weights 0 and 5 | 20873 and 20873 | |
| helper vs Python, quilting / bad-set comparisons | 200 / 400, 0 differences | 200 / 400, 0 differences |
| random certificates / accepted | 200 / 84 | 200 / 101 |
| accepted but not covering (A1) | 0 | 0 |
| survivor counts compared with brute force (A2), of these nonzero | 459, 30 | 459, 18 |
| helper and Python verdicts, failures and counts equal (A3) | 200 of 200 | 200 of 200 |
| A4 cases, of these rejected | 84, 0 | 101, 0 |
| planted faults on accepted cases (A5), caught | 85, 85 | 101, 101 |
| mutant without the enumeration check, non-covering arrays accepted | 3 | 4 |
| mutant without (E1), non-covering arrays accepted | 1 (the fixed example) | 1 |

The run with the real certificate takes about 280 s on the 2-core VM (each full check of the
1400 certificate takes about 19 s), the run without it about 70 s. The suites of the other
constructions pass unchanged (`test_construction_cert.py --cases 40`, `test_kinds.py --cases 400`,
`test_real_certs.py`).

    python3 tools/tests_construction/test_powercz2.py --cases 200 --seed 20261103
    python3 tools/tests_construction/test_powercz2.py --cases 200 --seed 777 --skip-real

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
product-1; they are the construction `product-ctj-1` below.

    {"format": "construction-cert-1", "construction": "product-1", "t": 2, "v": 3,
     "first": {"rows": [[0, 0, 0, 0], ...]}, "second": {"table": "<array_sha256>"},
     "constant_rows": [0, null],                      (optional, default [null, null])
     "expected": {"N": 17, "k": 16, "array_sha256": "..."}}

## The product with constant rows of both ingredients (product-ctj-1)

Source: C. J. Colbourn and J. Torres-Jimenez, Profiles of covering arrays of strength two, J.
Algorithms Comput. 44 (2013) 31-59, Corollary 4.3 (`pca-ct2013`), which bounds CAN(2, k1 k2, v) by
CAN(2, k1, v) + CAN(2, k2, v) - min(v, s1 + s2) when the two arrays have s1 and s2 rows that can be
made constant together. U. Groemping's R package CAs builds it as `productCA`. product-1 saves at
most one row (a constant row of the second ingredient that repeats one of the first), so on the
same ingredients it can be up to v - 1 rows larger.

Theorem. Let A be a CA(N1; 2, k1, v) and B a CA(N2; 2, k2, v), k1, k2 >= 2. Let S be a set of rows of
A that differ pairwise in every column, T a set of rows of B with the same property, and |S| + |T|
<= v. In every column of A exchange symbols so that the rows of S read distinct constant symbols
(the set sigma), and in every column of B so that the rows of T read distinct constant symbols (the
set tau), sigma and tau disjoint. Index the k1 k2 columns by pairs (i, j). Take, for every row x of A
not in S, the row with x[i] in column (i, j), and for every row y of B not in T, the row with y[j]
in column (i, j). The result is a CA(N1 + N2 - |S| - |T|; 2, k1 k2, v).

The exchanges exist: in a column, the rows of S show |S| distinct symbols (they differ pairwise),
so a permutation of the v symbols takes them to sigma, and the same for T and tau, which has room
because |S| + |T| <= v. Exchanging symbols within a column keeps a covering array covering.

Proof. Take two columns (i, j) and (i', j') and a pair (x, y) of symbols. Every row of A in S shows
only symbols of sigma, and every row of B in T only symbols of tau.

1. j = j' (so i and i' differ). If x and y differ, A covers (x, y) in columns i, i' in some row; that
   row is not constant, so it is not in S, and its row in the first part shows (x, y). If x = y, B
   has a row with x in column j that is not constant: B covers (x, z) in columns j and j'' for some
   z other than x and some other column j'' (k2 >= 2, v >= 2). That row is not in T, and its row in
   the second part shows x in both columns (i, j) and (i', j).
2. j and j' differ. B covers (x, y) in columns j, j' in some row y0. If y0 is not in T, its row in
   the second part shows (x, y). If y0 is in T, then x = y = c with c in tau. If i and i' differ, A
   covers (c, c) in columns i, i' in some row; that row shows c, which is not in sigma, so it is not
   in S, and its row in the first part shows (c, c). If i = i', any row of A with c in column i
   will do, and it is not in S for the same reason.

Every pair is covered, and the array has N1 - |S| + N2 - |T| rows.

Nested ingredients and the columns option. An ingredient may itself be a product of this kind. The
theorem applied to it gives a covering array of strength 2 over v symbols, so only the arrays at the
leaves need a coverage check (exhaustive for a file or inline array, the table's for a table array).
The first k' columns of a CA(N; 2, k, v), 2 <= k' <= k, form a CA(N; 2, k', v), so an ingredient
may keep only its first `columns` columns; the constant rows S or T are then rows of the array as
kept, and they need to differ only in the columns kept.

What the checker verifies, at every product of the certificate (the top one and every nested one),
before rebuilding:

| name | hypothesis |
|---|---|
| shape, ingredient_hash, ingredient_ca, ingredient_table | every leaf is a CA(N; 2, k, v) over 0..v-1 (as for the other array constructions) |
| ctj_strength | t = 2 |
| ctj_columns | every `columns` value keeps at least 2 and at most all the columns of its array |
| ctj_rows | every row named in S or T is a row of its ingredient (as kept), and no row is named twice |
| ctj_constant | every two rows of S differ in every column, and every two rows of T |
| ctj_budget | \|S\| + \|T\| <= v |
| ctj_nested | every nested product has the N and k its specification declares |

then symbols, alphabet, N, k and sha256 of the rebuilt array as for the other constructions.

The exchange is fixed so that the hash can be reproduced: in every column the row S[r] (in the order
the certificate lists S) gets symbol r, and the other symbols of 0..v-1 take the other values in
increasing order of both; the row T[r] gets |S| + r, and the other symbols take the values outside
|S|..|S|+|T|-1 in increasing order. Rows keep their order (the rows of A not in S, then the rows of
B not in T), and column (i, j) is column i k2 + j, as in product-1. A nested product is built the
same way and then cut to its `columns`.

Format (`construction-cert-1`, keys `first`, `second`, `constant`):

    {"format": "construction-cert-1", "construction": "product-ctj-1", "t": 2, "v": 25,
     "first": {"file": "CA_727_2_30_25.txt", "sha256": "..."},
     "second": {"product": {"first": {"file": "CA_727_2_30_25.txt", "sha256": "..."},
                            "second": {"file": "CA_727_2_30_25.txt", "sha256": "..."},
                            "constant": [[0, 1, ..., 24], []]},
                "N": 1429, "k": 900},
     "constant": [[0, 1, ..., 24], []],
     "expected": {"N": 2131, "k": 27000, "array_sha256": "..."}}

`constant` is [S, T] (row numbers, 0-based; default [[], []]). An ingredient is an array (`rows`,
`file` with `sha256`, or `table`, section "Ingredients from the table") or `{"product": {"first",
"second", "constant"}, "N", "k"}`, either with an optional `"columns": k'`. Nesting is limited to 8
levels, and a nested product is held in memory up to 5 x 10^7 entries. The top product is hashed row
by row as it is built, so its size is limited only by the route (`check_constructions.py`). A
certificate that leaves out a constant row it could have used is still valid; it only proves a
larger array.

The rows S and T are not searched for by the checker. The certificate names them; a largest such
set is a largest clique of the graph whose vertices are the rows and whose edges join rows that
differ in every column (`tools/constant_rows.c`, the count the table records for its arrays).

### Tests of product-ctj-1

`tools/tests_construction/test_ctj.py` writes random small certificates (v = 2 to 4, leaves of 2 to
4 columns built with v rows that differ pairwise in every column, about half of them with a nested
product and a quarter of the ingredients cut by `columns`, leaves inline, in files or in a small
table of its own), valid ones and ones with one planted fault each: two rows of S agreeing in one
column (half the time a new row that agrees with a named row in the last column only), |S| + |T| =
v + 1, a row number out of range or named twice, a wrong N or k in a nested specification, `columns`
of 1 or above k, a leaf with a missing pair, a leaf symbol v, a file with a wrong sha256, a table
row of strength 1, t = 3, and an expected N, k or sha256 that is wrong. It rebuilds each array with
its own code, evaluates every hypothesis by its definition, and checks every rebuilt array with
`ca_verify`, itself compared with a Python brute force. For a fault in S or T the certificate's
expected values are those of the array the checker builds anyway, so that the planted fault is the
only failure, and the test counts how many of those arrays are not covering arrays. Then each check
is disabled in turn, and two boundary mutants are applied (|S| + |T| <= v + 1, and S compared
without its last column). symbols and alphabet are implied for this kind by shape and ctj_budget
(a leaf over 0..v-1, exchanged within 0..v-1), so their mutants are reported but not required to
die.

#### Results (2026-11-11)

| | seed 20261110 | seed 777 |
|---|---|---|
| certificates / with a nested product | 300 / 152 | 300 / 159 |
| valid certificates accepted | 100 of 100 | 100 of 100 |
| faulted certificates accepted | 0 of 200 | 0 of 200 |
| certificates satisfying every hypothesis / of these not covering (A4) | 100 / 0 | 100 / 0 |
| ca_verify vs brute force | 174 arrays, 0 disagreements | 171 arrays, 0 disagreements |
| arrays built anyway with \|S\| + \|T\| = v + 1 / not covering | 14 / 14 | 13 / 13 |
| arrays built anyway with two rows of S or T agreeing / not covering | 14 / 4 | 21 / 11 |
| A1, A2, A3, A4 violations | 0 | 0 |
| mutants surviving (15 required) | 0 | 0 |

Mutants (seed 20261110), the cases that kill each and the non-covering arrays each accepts: disable
shape 18 / 0, ingredient_hash 12 / 0, ingredient_ca 13 / 7, ctj_strength 14 / 0, ctj_columns 19 / 0,
ctj_rows 16 / 0, ctj_constant 14 / 4, ctj_budget 19 / 0, ctj_nested 13 / 0, ingredient_table 15 / 0,
N 22 / 0, k 14 / 0, sha256 11 / 0; ctj_budget with v + 1 19 / 0; ctj_constant without the last
column 7 / 1. Disabling symbols or alphabet changes no result (0 / 0). With ctj_budget disabled the
arrays with |S| + |T| = v + 1 are still refused, by alphabet (they use the symbol v), which is why
that mutant accepts no non-covering array. ctj_rows and ctj_columns guard the recording (a row
number out of range is skipped by the rebuild, a `columns` of 1 or above k changes the array) and
are each reported by the check itself. The suites of the other kinds (`test_kinds.py`,
`test_route.py`, `test_real_certs.py`) pass unchanged with the new code.

    python3 tools/tests_construction/test_ctj.py --cases 300 --seed 20261110
    python3 tools/tests_construction/test_ctj.py --cases 300 --seed 777

## Shokri, Moura and Stevens: sms51-1 and sms65-1

Source: K. Shokri, L. Moura and B. Stevens, Existence of 3 anti-cocircular truncated Moebius planes
and constructions of strength-4 covering arrays, arXiv:2510.13122v3 (16 Oct 2026), `mobius-sms2025`
in `table/references.csv` (added to `builds_on` when it is missing). `sms51-1` is their Theorem 5.1,
CA(3q^4 - 2; 4, (q^2+1)/2, q). `sms65-1` is their Theorem 6.2, CA(3q^4 + (q - 2)N; 4, q^2 + 1, q)
from a CA(N; 3, (q^2+1)/2, q), with N = 2q^3 - q as in their Corollary 6.5. Both are for odd prime
powers q. Their proof rests on Theorem 4.25 (three truncated Moebius planes are anti-cocircular),
which they prove with pencils of quadrics and a quartic surface. The checker does not use that
proof. It checks the property itself for the given q, exactly, by listing circles, and then uses
only the linear algebra written out below. Since 2026-11-10.

### Setting

* q = p^m is odd, the field elements are the labels 0..q-1 of Power CZ (base-p digits, a monic
  `modulus` for m > 1). half = (q^2+1)/2, and n = (q^4-1)/(q-1) = (q^2+1)(q+1).
* A monic quartic f over F_q (`quartic`, five labels, constant term first). alpha is the class of
  x in F_q[x]/(f), and L(y) is the coordinate vector of y in the basis 1, alpha, alpha^2, alpha^3.
  The checker lists L(alpha^e) for e = 0..q^4-2 by multiplying by x and reducing.
* A(G), for a matrix G with r rows, is the array of the q^r rows u G, u in F_q^r, in the order of
  `itertools.product(range(q), repeat=r)` (u_0 most significant), row = sum of u_i times row i of G.
* Three multipliers l1, l2, l3 (`multipliers`, default [1, 2, 4], the paper's). Column c of the full
  ovoid (0 <= c < q^2+1) has, in labeling j, the exponent E_j(c) = l_j (q+1) c mod n. Its x is
  c mod half.

### The arrays

sms51-1, with a choice p in {0,1}^half (`p`, a string): the columns are c_i = i + p_i half,
0 <= i < half. Block j (j = 1, 2, 3) is A(G_j), with column i of G_j equal to
L(alpha^(l_j (q+1) c_i mod (q^4-1))). The array is block 1, block 2 without its first row (u = 0),
and block 3 without its first row: 3q^4 - 2 rows, half columns. This is `tools/sms_theorem51.py`.

sms65-1: with G0 the 4 x (q^2+1) matrix of columns L(alpha^(l1 (q+1) c mod (q^4-1))), H2 and H4 the
4 x half matrices of columns L(alpha^(l2 (q+1) x)) and L(alpha^(l3 (q+1) x)), and R the ingredient
(N rows, half columns), the array is, in this order,

    A(G0)
    A(H2) | A(H2)
    A(H4) | A(H4) + e_0
    R | R + e_1, ..., R | R + e_(q-2)

where e_r is the label r + 1 (so e_0 = 1 and the e_r are all the nonzero elements), and + adds a
field element to every entry. It has 3q^4 + (q-2)N rows and q^2 + 1 columns. This is
`tools/sms_theorem62.py`.

### Three lemmas

Lemma 1 (independent columns). If the columns of G at a set T are linearly independent, the
map u -> (u G restricted to T) is onto F_q^T, so A(G) shows every tuple on T, and so does
A(G) + d for every fixed vector d (a translate of an onto map is onto).

Lemma 2 (hyperplanes). Let D0 = {e : 0 <= e < n, the first coordinate of alpha^e is 0}. Suppose
alpha has order q^4 - 1 and D0 has no period mod n. Then nonzero vectors L(alpha^(e_1)), ...,
L(alpha^(e_r)) lie in a common hyperplane exactly when some s in Z_n has e_i + s mod n in D0 for
every i, and the hyperplanes containing them correspond one to one to these s.
Proof. Let phi_s be the first coordinate of alpha^s y, a linear functional of y (multiplication by
alpha^s is F_q-linear and invertible, so phi_s is not zero). alpha^n has order q - 1, so it lies in
F_q^* (the q - 1 roots of y^(q-1) = 1 in the field F_(q^4) are F_q^*), and so the first coordinate
of alpha^(e+s) is 0 exactly when (e + s) mod n is in D0. The points alpha^e, 0 <= e < n, are n
pairwise non-proportional vectors (alpha^d is not in F_q for 0 < d < n), so they are all the
points of PG(3, q). If phi_s and phi_s' were proportional for s != s' mod n, their zero sets among
these points would agree, D0 - s = D0 - s', and D0 would have the period s - s'. So the n
functionals are pairwise non-proportional; there are n classes of nonzero functionals in all, so
every hyperplane is the kernel of exactly one phi_s.
Consequences: 4 vectors are linearly dependent exactly when some s contains them (they span at
most 3 dimensions); 3 vectors are independent exactly when exactly one s contains them (a
3-dimensional span lies in one hyperplane, a span of 2 or fewer in q + 1 or more).

Lemma 3 (the shift). E_j(c + 1) = E_j(c) + l_j (q+1) mod n, and E_j is well defined on c mod
q^2 + 1 because l_j (q+1)(q^2+1) = l_j n. So a set T of columns lies in hyperplane s of labeling
j exactly when T + 1 lies in hyperplane s - l_j (q+1). Any property "some s contains T" is the
same for T and every translate of T. The same holds for the exponents l (q+1) x with x mod half
when l is even, since l (q+1) half is then a multiple of n.

### Theorem 5.1 as checked (sms51-1)

Hypotheses: (Q) alpha has order q^4 - 1 (`quartic`); (P) |D0| = q^2+q+1 and D0 has no period
(`hyperplanes`, tested for the divisors of n); (ACTM) no 4-set of columns of the full ovoid with
pairwise distinct x lies in a common hyperplane in all three labelings (`actm`).

Claim: the sms51-1 array is a CA(3q^4 - 2; 4, half, q).

Proof. Take 4 distinct columns i, j, k, l and the columns c_i, c_j, c_k, c_l of the full ovoid;
their x are i, j, k, l, distinct. By (ACTM) there is a labeling j' in which no hyperplane contains
them; by Lemma 2 (with (Q) and (P)) the 4 columns of G_j' are then linearly independent (the
vectors L(alpha^(l (q+1) c)) and the exponents E_j'(c) differ only by a factor in F_q^*), and by
Lemma 1 block j' shows every tuple on them. The two rows removed are all-zero rows (u = 0), equal
to the first row of block 1, which is kept. []

(ACTM) is Theorem 4.25 of the paper for every p at once. The checker tests it by Lemma 3 only for
the 4-sets containing column 0 (a bad 4-set T stays bad when moved by -c for c in T, and x stays
distinct because half divides q^2+1). For each of the q^2+q+1 hyperplanes s1 of labeling 1
through column 0, it lists the other columns Y in s1 with x != 0. For each pair b, c of Y with
distinct x it intersects the masks of hyperplanes of labelings 2 and 3 through 0, b, c (each mask
the set {s : E + s in D0}, a rotation of D0), and tests every further d in Y with x different from
the three. A bad 4-set {0, b, c, d} lies in some hyperplane of labeling 1 (Lemma 2), so b, c, d are
in Y for that s1 and the test meets it. Nothing is sampled. At q = 25 the test meets
1,480,648 triples (b, c, d), in about a second.

### Theorem 6.2 as checked (sms65-1)

Hypotheses: (Q), (P), (ACTM) as above, with l2 and l3 even (a certificate with an odd l2 or l3 is
malformed); (C3) any 3 columns of H2 are linearly independent, and any 3 of H4 (`caps`: exactly one
common hyperplane, by Lemma 3 tested for the 3-sets with column 0); (C2) for x != x', the columns
x, x + half, x', x' + half of G0 are linearly independent (`pairs`: no common hyperplane, tested
for x = 0); (R) the ingredient is a CA(N; 3, half, q) (`cubic`, `lines`, `points`, `orthogoval`
below, or the checks of an array ingredient).

Claim: the sms65-1 array X is a CA(3q^4 + (q-2)N; 4, q^2+1, q).

Proof. Take 4 distinct columns of X and a tuple. Write each column as c = x + p half. The x occur
at most twice (p is 0 or 1).
1. The four x are distinct. By (ACTM) some labeling has no common hyperplane. If it is labeling 1,
   G0 is independent on the 4 columns (Lemma 2) and block 0 shows the tuple (Lemma 1). If it is
   labeling 2 or 3: since l2 and l3 are even, E_2(c) = l2 (q+1) x mod n, so the vectors of H2 (of
   H4) at the four x are independent, and block 1 (block 2, a translate by e_0 on the right half)
   shows every tuple on the 4 columns (Lemma 1).
2. Exactly one x repeats: columns (x, 0) and (x, 1), and two more columns with distinct x' and x''.
   Let the tuple have a at (x, 0) and a + d at (x, 1). If d = 0: by (C3) the vectors of H2 at
   x, x', x'' are independent, so some u gives the tuple's values at x, x', x'' in A(H2), and block 1
   repeats the left half on the right half, so its row shows a at both (x, 0) and (x, 1) and the
   wanted values elsewhere. If d = e_0: the same with H4 and block 2, where the right half carries
   + e_0 (the wanted values at columns with p = 1 are taken minus e_0 first). If d = e_r, r >= 1:
   R covers 3 columns (R) so some row of R has a at x and the wanted values at x', x'' (minus e_r
   where p = 1), and block 2 + r shows the tuple. The e_r with 0 cover every d.
3. Two x repeat: columns x, x + half, x', x' + half. By (C2) they are independent in G0 and block 0
   shows every tuple. []

The proof is the paper's (its cases 1, 2, 3), with the geometry replaced by the checked (ACTM),
(C2), (C3). The paper gets (C2) from its Corollary 4.6 and (C3) from the ovoid (no three points
collinear).

### The ingredient R

`"ingredient": {"orthogoval": {"cubic": [b0, b1, b2, 1], "points": [j_0, ..., j_(half-1)]}}` builds
R as `tools/sms_theorem62.py` does. beta is the class of x modulo the cubic, L3 the coordinates in
1, beta, beta^2. G1 has the columns L3(beta^(j_i)) and G2 the columns L3(beta^(-j_i)), each column
divided by its first coordinate. R is A(G1) followed by A(G2) without its rows u = (u0, 0, 0), so
2q^3 - q rows. These are the two planes of their Theorem 3.3 (an orthogoval pair, Colbourn, Ingalls,
Jedwab, Saaltink, Smith and Stevens 2024, `orthogoval-cijsss2024`), truncated and with the q
repeated constant rows removed, which is the idea of their Theorem 3.4 (Torres-Jimenez and
Izquierdo-Marquez 2018, `epv-ti2018`) and gives the size of Remark 6.4. It is not checked to be the
same array as theirs; Theorem 6.2 takes any CA(N; 3, half, q).

Hypotheses: (Q3) beta has order q^3 - 1 (`cubic`); (P3) D3 = {e < q^2+q+1 : the first coordinate of
beta^e is 0} has q + 1 elements and no period (`lines`); `points`: every beta^(j_i) and beta^(-j_i)
has a nonzero first coordinate; (O) every 3 of the columns are independent in G1 or in G2
(`orthogoval`).

Claim: R is a CA(2q^3 - q; 3, half, q). Proof. Lemma 2 holds in F_q^3 with D3 (the same proof with
q^2+q+1 points and lines). Scaling a column changes neither its point nor the rank of a set of
columns, and makes the first row of G1 and of G2 all ones. Take 3 columns and a tuple y. If they are
independent in G1, A(G1) shows y (Lemma 1). Otherwise, by (O), they are independent in G2 and A(G2)
shows y in some row u. If that row was removed, u = (u0, 0, 0), so y is constant u0, and the row
u = (u0, 0, 0) of A(G1) is constant u0 too (its first row is all ones). []

(O) is checked over the q^2+q+1 lines of plane 1: the 3-sets dependent in G1 are exactly those on a
line (Lemma 2), and for each the masks of plane 2 are intersected. At q = 25 there are 187,223 such 3-sets.
The two planes are orthogoval on all their points (their Theorem 3.3), so (O) can fail only when a point is
repeated or the cubic is not primitive; the check does not rely on that.

An array ingredient (`{"table": ...}`, `{"file": ..., "sha256": ...}` or `{"rows": ...}`) is also
accepted: it must have exactly half columns, and it is checked as in the other constructions
(`shape`, `ingredient_hash`, `ingredient_ca` at strength 3, or `ingredient_table`).

### Format

    {"format": "construction-cert-1", "construction": "sms51-1", "t": 4, "v": 25,
     "field": {"q": 25, "p": 5, "m": 2, "modulus": [1, 1, 1]},
     "quartic": [7, 0, 0, 5, 1],
     "p": "000...0",                                   (half characters 0 or 1)
     "multipliers": [1, 2, 4],                         (optional, the default)
     "expected": {"N": 1171873, "k": 313, "array_sha256": "..."}}

    {"format": "construction-cert-1", "construction": "sms65-1", "t": 4, "v": 17,
     "field": {"q": 17, "p": 17, "m": 1},
     "quartic": [...], "multipliers": [1, 2, 4],
     "ingredient": {"orthogoval": {"cubic": [...], "points": [...]}},
     "expected": {"N": 397698, "k": 290, "array_sha256": "..."}}

t must be 4 and v = q odd, 3 <= q <= 31 (the q^4 - 1 powers are listed in Python). Unknown and
duplicate keys are rejected. `python3 tools/sms_theorem51.py q --certificate C.json > A.txt` and
`python3 tools/sms_theorem62.py q --certificate C.json > A.txt` write the certificate with the N, k
and sha256 of the array they print, so the checker's rebuild is compared with an independent one.

### The checks

| name | hypothesis |
|---|---|
| field | as for Power CZ |
| quartic | (Q) |
| hyperplanes | (P) |
| actm | (ACTM) |
| caps, pairs | (C3), (C2) (sms65-1) |
| cubic, lines, points, orthogoval | the orthogoval ingredient (sms65-1) |
| shape, ingredient_hash, ingredient_ca, ingredient_table | an array ingredient (sms65-1) |
| symbols, N, k, sha256, alphabet | as for the other constructions |

The rebuild works on rows as byte strings of labels: F_q addition is a carry-free integer addition
of a digit coding (base 2p - 1 per base-p digit) followed by a byte translation, and the canonical
text is made by interleaving translated byte strings. The tests compare it with the numpy scripts.

### Cost

The hyperplane checks run only when (Q) holds and D0 has q^2+q+1 elements (otherwise they fail with "not
checked"), so a degenerate quartic cannot make them slow, and each stops at its first bad set. On the 2-core VM
the nine certificates of `submissions/smolen-2026-11-sms-certificates/` take 1 to 32 s each, nearly all of it the
rebuild (CA(1890050; 4, 626, 25), 1.18 x 10^9 entries, 32 s). `tools/check_constructions.py` allows these two
kinds up to 2 x 10^9 entries (`MAX_ENTRIES_FAST`; 10^9 for the others).

### Tests of sms51-1 and sms65-1

`tools/tests_construction/test_sms.py` has three parts.

1. The scripts and the checker at q = 3, 5, 7, 9: for both constructions the script's certificate is accepted,
   the array the checker writes is byte for byte the script's, and `ca_verify` verifies it on every 4-set
   (at q = 9, 19681 x 41 and 29826 x 82). A reducible modulus (y^2 at q = 9) is reported by `field`.
2. Random certificates over q = 3, 5, 7 with random multipliers, p, quartics (primitive or not), ingredients
   (the orthogoval recipe with random cubics and points, or an inline array, sometimes changed), planted
   faults, and targeted cases in which a single hypothesis fails (multipliers found with the oracle for
   actm, caps and pairs alone, a repeated point, a point with first coordinate 0, a broken or narrowed inline
   ingredient). An independent oracle decides every hypothesis by its definition with integer determinants
   mod q (every 4-set and 3-set, no hyperplanes, no shift), rebuilds the array with numpy and checks it with
   `ca_verify`. Assertions as for the other kinds (A1 to A4), and every check agrees with the oracle on its own
   hypothesis. Then each check is disabled in turn and three boundary mutants are applied (actm also over
   4-sets with a repeated x; caps for H2 only; orthogoval without the 3-sets that repeat a point).
3. The nine real certificates pass with their recorded sha256, and planted faults on the q = 13 and 17
   certificates (the quartic x^4, multipliers [1, 2, 2], [2, 2, 4] and [1, 2(q^2+1), 4], a repeated point, the
   cubic x^3, N + 1, p one bit short) are rejected by the intended check.

Results (2026-11-10, seed 20261110, 60 random and 8 targeted certificates, 244 s):

| | |
|---|---|
| certificates accepted / satisfying every hypothesis | 16 / 16 |
| accepted but not covering (A3), hypotheses true but not covering (A4) | 0, 0 |
| checks compared with the oracle, disagreements | 270, 0 |
| mutants killed | 15 of 15 that a certificate here can reach, with the 3 boundary mutants |
| mutants that accept a non-covering array | disable actm 3, caps 2, pairs 1, orthogoval 1, ingredient_ca 1; caps for H2 only 2; orthogoval without repeated points 1 |

Six checks cannot fail alone on these cases and are reported, not counted as survivors: `hyperplanes` and
`lines` (implied by `quartic` and `cubic`, Singer's theorem; kept because the proof above uses them and not that
theorem), `field` (the random fields are prime; part 1 plants a reducible modulus), `symbols` and `alphabet`
(every sms array has a zero row and only field labels), and `ingredient_hash` (no file ingredient here; it is the
shared code of `test_kinds.py`).

    python3 tools/tests_construction/test_sms.py --cases 60 --seed 20261110
    python3 tools/tests_construction/test_sms.py --cases 40 --quick --skip-real     (about 2 minutes)

## Shokri and Moura, x-plication: sm-xplication-1

Source: K. Shokri and L. Moura, New families of strength-3 covering arrays using linear feedback shift
register sequences, J. Combin. Des. 33 (2025) 156-171 (`lfsr-sm2025` in `table/references.csv`, added to
`builds_on` when it is missing). The journal text was not read here. The theorems and proofs were read in
Chapter 5 of K. Shokri's PhD thesis (University of Ottawa, 2026, doi:10.20381/ruor-31663, `thesis-s2026`),
which says the chapter was published in that paper; the numbering below is the thesis's. Since 2026-11-10.

The thesis proves one general theorem (Theorem 5.2.6, a Roux-type construction) and gets its arrays by
choosing ingredients and then deleting rows of the last row block that repeat rows the other blocks
already give. The checker checks the general theorem, with the deletion built in, for the given q and
ingredients, exactly. It does not take the thesis's word for the deleted rows: it checks that what is
left still covers.

### Setting

* q = p^m, field elements are the labels 0..q-1 of Power CZ (base-p digits, a monic `modulus` for m > 1).
  k0 = q^2 + q + 1.
* A monic cubic f (`cubic`, four labels, constant term first); alpha is the class of x in F_q[x]/(f) and
  L(y) the coordinate vector of y in the basis 1, alpha, alpha^2. G1 is the 3 x k0 matrix with columns
  L(alpha^j), G2 the one with columns L(alpha^-j), 0 <= j < k0 (thesis Construction 3.1.1 and Theorem
  3.2.4; alpha^-j = alpha^((q^3 - 1 - j) mod (q^3 - 1))).
* A(G), for a matrix G with 3 rows, is the array of the q^3 rows u G, u in F_q^3, in the order of
  `itertools.product(range(q), repeat=3)` (u_0 most significant).
* P is the CA(2q^2 - q; 2, q^2 + 2q, q) of Corollary 5.1.9, cut to its first k0 columns. Its ingredient is
  the Bush OA(q^2; 2, q + 1, q): the polynomials c0 + c1 X evaluated at the q `points` (a list of the labels
  in some order) and c1. Rows: (c1, c0) for c1 = 1..q-1, c0 = 0..q-1 (labels), twice, then the constant rows
  0..q-1. Columns: j q + z with value F(c1, c0; z), F(c1', c0'; j) and the constant a in the three row parts;
  then q columns j (c1, F(c1', c0'; j), 0); then q columns z (F(c1, c0; z), c1', 0). F(c1, c0; z) is
  c0 + c1 a_z, a_z the z-th point. This is Theorem 5.1.8 with the Bush array as both ingredients.
* D (`dca`) is an m x x array of labels, m >= 2. x is the number of column blocks.
* E_D is the set of the m q vectors D[r] + a (a added to every entry), r < m, a in F_q (the CA(mq; 2, x, q)
  of thesis Proposition 5.1.16 when D is a DCA).
* `last` is a list of 3 x x matrices H_1, H_2, ... . C' is the rows of A(H_1), A(H_2), ... in this order,
  without the rows that are in E_D and without repeats (the first copy is kept).

### The array

Column l k0 + i is column i of column block l (0 <= l < x, 0 <= i < k0). With B_0 = A(G1), B_1 = A(G2) and
B_r = P for 2 <= r < m, row block r is B_r with D[r][l] added to every entry of column block l. The last
row block has, for each row c of C', the entry c_l in every column of block l. The array X has
N = 2q^3 + (m - 2)(2q^2 - q) + |C'| rows and x k0 columns. This is `tools/sm_xplication.py`.

### The theorem as checked

Hypotheses:

* (H1) `points`: any two columns of G1 are linearly independent, and any two of G2.
* (H2) `cphf`: no 3 columns are linearly dependent in G1 and in G2 (the two rows form a CPHF(2; k0, q, 3),
  thesis Theorem 3.2.4).
* (H3) `P`: P is a CA(2q^2 - q; 2, k0, q), checked on every pair of columns.
* (H4) `dca`: D is a difference covering array DCA(m; 2, x, q): for any two columns l < l' the differences
  D[r][l'] - D[r][l], r < m, take all q values.
* (H5) `last`: E = E_D together with C' covers every 3-set of the x columns (nothing to check for x < 3).

`cubic` (alpha has order q^3 - 1, the thesis's hypothesis) is checked too, but the proof does not use it.

Claim: X is a CA(N; 3, x k0, q).

Proof. By Lemma 1 of the sms section, (H1) makes A(G1) and A(G2) show every pair on any two columns,
and every symbol in every column. (H3) gives the same for P. So every base block B_r shows every pair on
any two of its columns. Take three distinct columns (l, i), (l', i'), (l'', i'') of X and a tuple
(s, s', s'').

1. i, i', i'' are distinct. By (H2) G1 or G2 is independent on columns i, i', i''; say G_g, g in {1, 2}.
   By Lemma 1 the block B_(g-1) shows every triple on them, in particular (s - D[g-1][l], s' - D[g-1][l'],
   s'' - D[g-1][l'']), and row block g - 1 of X then shows (s, s', s'').
2. Exactly two of i, i', i'' are equal; rename so that i = i'' != i'. The columns are distinct, so
   l != l''. By (H4) some row r of D has D[r][l''] - D[r][l] = s'' - s. B_r shows the pair
   (s - D[r][l], s' - D[r][l']) on its columns i, i'; that row of row block r has s at (l, i), s' at
   (l', i') and s - D[r][l] + D[r][l''] = s'' at (l'', i).
3. i = i' = i'', so l, l', l'' are distinct. By (H5) some e in E has (e_l, e_l', e_l'') = (s, s', s'').
   If e is in C', the last block shows it on every column of blocks l, l', l'', so on these. If
   e = D[r] + a, B_r has a row with the symbol a in column i, and that row of row block r has
   a + D[r][l] = e_l at (l, i), and the same at (l', i) and (l'', i). []

The thesis's Theorem 5.2.6 is the case where C' is a CA(N2; 3, x, q) (then (H5) holds whatever E_D is);
deleting from it the rows that are in E_D, as the thesis does for each instance, keeps (H5), since E_D
is shown by the first m row blocks in every column block triple (case 3). The checker does not assume
that the rows deleted are the thesis's: it computes E_D and C' and checks (H5) on all of E.

### The instances

| construction | thesis | x | D | last | |C'| | N |
|---|---|---|---|---|---|---|
| 2-plication | Theorem 5.2.7 | 2 | columns 0 and 1 of the multiplication table: D[r] = (0, a_r) | none | 0 | 4q^3 - 5q^2 + 2q |
| q-plication | Theorem 5.2.8 | q | the multiplication table D[r][c] = a_r a_c (Theorem 5.1.11) | the rows a_c^2, a_c, 1 (Bush OA(q^3; 3, q, q), Corollary 5.1.2) | q^3 - q^2 | 5q^3 - 6q^2 + 2q |
| q^2-plication | Theorem 5.2.11 | q^2 | D (x) D without one zero row, 2q - 1 rows (Theorem 5.1.13) | G1' = (1, a_z, a_j) at j q + z (Table 5.3) and G2' (the columns of G2 at the same points) | 2q^3 - 2q^2 + q - 1 | 8q^3 - 10q^2 + 4q - 1 |
| q^2-plication, even q | Corollary 5.2.12 | q^2 | as 5.2.11 | G1' and G2' = (1, x^2 + y, y^2 + by + cx) at G1' column (1, x, y) | 2q^3 - 2q^2 | 8q^3 - 10q^2 + 3q |
| (q^2-q+1)-plication | Theorem 5.2.13 | q^2 - q + 1 | as 5.2.11, without the q - 1 columns where G2' has first entry 0 | G1'' and G2'' (the same columns, G2'' scaled to first entry 1) | 2q^3 - 2q^2 | 8q^3 - 10q^2 + 3q |

Here a_0 = 0 and a_i = e^(i-1), e the smallest primitive label, are the `points` of the script, and D (x) D
has, in column j q + z, a_r a_z in its first q rows and a_r a_j in the other q - 1 (r = 1..q-1). In 5.2.12,
b and c make X^3 + bX + c irreducible: G2' maps the affine points by the map (x, y) -> (x^2 + y, y^2 + by +
cx) of C. J. Colbourn, C. Ingalls, J. Jedwab, M. Saaltink, K. W. Smith and B. Stevens, Sets of mutually
orthogoval projective and affine planes, Combin. Theory 4 (2024), Corollary 3.4 and Theorem 3.8
(`orthogoval-cijsss2024`), which the thesis cites as its Proposition 3.3.3. In every instance E_D is the
part of A(G1') (or of the Bush OA) the thesis deletes, so C' is what the thesis keeps; the counts in the
table are what the script and the checker find.

Two places where the thesis is not exact, found here:

1. Theorem 5.2.13 says G2' always has exactly q - 1 columns with first entry 0 ("the first rows of G1 and
   G^-1 have exactly two zeros in the same position"). That depends on the cubic. Over all primitive
   cubics the number is q - 1 for some and q + 1 for the others: at q = 3, 4, 5, 7, 8, 9 the counts of
   cubics with q - 1 against q + 1 are 2 : 2, 6 : 6, 12 : 8, 21 : 15, 72 : 72, 40 : 56. With q + 1 the
   construction has 2 columns fewer per block (x = q^2 - q - 1). The script takes the first cubic with
   q - 1; the checker needs nothing of the kind, since it checks (H5) for the D and the matrices given.
2. The proofs take "the CA(2q^2 - q; 2, q^2 + q + 1, q) in Corollary 5.1.9", which has q^2 + 2q columns. The
   script and the checker use its first q^2 + q + 1, and (H3) is checked on them.

The thesis's Theorem 5.2.8 proof needs the columns of the Bush array in the order of the rows of D (Table
5.1 and 5.2); that is so here, and the checker's (H5) would fail otherwise.

Because C' drops every row already in E_D or already listed, it can be shorter than the thesis's last block.
For q >= 3 in all the tests it is exactly the thesis's. At q = 2, A(G2') repeats rows the thesis keeps (3 for
Theorem 5.2.11, 6 for Corollary 5.2.12), so the checker's array has N = 28 and 24 against the thesis's 31 and 30;
both still cover (the test checks them with `ca_verify`), and neither is of interest for v = 2. A certificate's
N is always the checker's count.

### Format

    {"format": "construction-cert-1", "construction": "sm-xplication-1", "t": 3, "v": 25,
     "field": {"q": 25, "p": 5, "m": 2, "modulus": [1, 1, 1]},
     "cubic": [c0, c1, c2, 1],
     "points": [0, 1, ...],                    (optional, default 0..q-1; P is evaluated at them)
     "dca": [[...], ...],                      (m rows of x labels, m >= 2)
     "last": [[[...], [...], [...]], ...],     (3 x x matrices, possibly none)
     "expected": {"N": 74425, "k": 16275, "array_sha256": "..."}}

t must be 3 and v = q <= 32. Unknown and duplicate keys are rejected. `python3 tools/sm_xplication.py
THEOREM q --certificate C.json > A.txt` (THEOREM 2, q, q2, q2even or q2q1) writes the certificate with
the N, k and sha256 of the array it prints; the script follows the thesis's own deletions, so the
checker's rebuild (with E_D computed) is compared with an independent one.

### The checks

| name | hypothesis |
|---|---|
| field | as for Power CZ |
| cubic | alpha has order q^3 - 1 |
| points | (H1) |
| cphf | (H2): for every pair of normalized functionals h1, h2, at most 2 columns where h1 vanishes on G1 and h2 on G2 (3 vectors of F_q^3 are dependent exactly when a nonzero functional vanishes on all three); (q^2+q+1)^2 pairs of bit masks |
| P | (H3), every pair of columns |
| dca | (H4), every pair of columns |
| last | (H5), every 3-set of the x columns over all of E |
| symbols, N, k, sha256, alphabet | as for the other constructions |

The rebuild uses the byte-string rows of the sms kinds.

### Cost

On the 2-core VM the ten certificates of `submissions/smolen-2026-11-sm-xplication/` take 0.4 s (q^2-plication,
q = 7) to about a minute (q-plication at q = 25, CA(74425; 3, 16275, 25), 1.21 x 10^9 entries), nearly all of it
the rebuild. `tools/check_constructions.py` allows this kind the 2 x 10^9 entries of the sms kinds.

### Tests of sm-xplication-1

`tools/tests_construction/test_smx.py`, three parts.

1. The script and the checker for all five theorems at small q (q = 2 to 7): the script's certificate is
   accepted, the array the checker writes is byte for byte the script's, and `ca_verify` verifies it on every
   3-set (at q = 2 for 5.2.11 and 5.2.12 the checker's array is the shorter one described above, and both are
   verified). The
   script reproduces, with the same sha256, the 12 arrays of Bai XunDi (Zenodo 23787055) the table has as
   VERIFIED rows for prime q (2-plication at q = 3, 5, 7, 9, 13, 17, 19, q-plication at q = 5, 7, 9, 11, 13)
   and the three arrays of T. N. Sitjar from the thesis (Corollary 5.2.12 at q = 4; Theorems 5.2.11 and 5.2.13
   at q = 5, with the cubic x^3 + 3x + 2 his generator chooses). For q = 4, 8, 16 Bai's arrays are the same rows
   in another order (his G2 is ours times an invertible matrix); the test compares them as sets of rows.
2. Random certificates (random q, D, cubics primitive or not, last matrices from the instances or random,
   planted faults) against an independent oracle that decides every hypothesis by its definition (3 x 3 and
   2 x 2 determinants over F_q, numpy counts), builds the array with numpy and checks it with `ca_verify`.
   Assertions as for the sms kinds (A1 to A4). Then each check is disabled in turn, and boundary mutants are
   applied.
3. The ten real certificates pass with their recorded sha256, and planted faults on the two q = 7 certificates
   (a non-primitive cubic, one entry of D, G2' replaced by G1', no last block, N + 1) are rejected by the
   intended check; a checker whose recipe for P is broken (column 0 replaced by column 1) rejects them by `P`.

Results (2026-11-10, seed 20261110, 60 random and 8 targeted certificates, 121 s with part 1 and part 3):

| | |
|---|---|
| certificates satisfying every hypothesis / their arrays not covering (A4) | 32 / 0 |
| accepted but not covering (A3) | 0 |
| checks compared with the oracle, disagreements | 408, 0 |
| mutants killed | 13 of 13 that a certificate here can reach |
| mutants that accept a non-covering array | disable dca 3, last 6; dca on adjacent columns only 2; last on consecutive 3-sets only 1 |
| published arrays rebuilt with the same sha256 | 18 of 18 |

Six mutants are reported, not counted as survivors: disabling `points` or `cphf` alone (a primitive cubic implies
both, by Singer's theorem and by Raaphorst et al., Theorem 3.2.4; with `cubic` disabled as well both are killed),
`P` (Corollary 5.1.9 holds for every order of the points; part 3 breaks the recipe instead), `field` (part 1
plants a reducible modulus), `symbols` and `alphabet` (every array has a zero row and only field labels). The
mutants that need a non-primitive cubic are killed by one case each.

    python3 tools/tests_construction/test_smx.py --cases 60 --seed 20261110      (about 2 minutes)
    python3 tools/tests_construction/test_smx.py --quick --cases 30 --skip-real  (seconds)

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
