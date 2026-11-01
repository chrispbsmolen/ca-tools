# Submitting covering arrays to the table

This directory is how anyone adds an explicit covering array to the
provenance table in `table/`. You open a pull request, the repository
checks your arrays itself and reports on the pull request, and when
it is merged the table gains the rows that record them, with your
credit. No maintainer has to look at the arrays for that to happen. The current table is
published as a web page from `docs/index.html` (GitHub Pages, served
from the `docs/` folder of `main` and regenerated on every push to
`main`).

## What a submission looks like

A submission is one new directory, `submissions/<slug>/`, where the
slug is a short name of your choosing made of letters, digits, dots,
hyphens and underscores, for example `smith-t4-v3-2026-11`. It holds
a file named `claims.csv` and the array files that file names.
Nothing else in the repository should change in your pull request.

`claims.csv` has exactly this header and one row per array:

    t,v,k,N,file,source_detail,construction,credit,notes

`t` is the strength, `v` the number of symbols, `k` the number of
columns and `N` the number of runs (rows) of the array. `file` is the
name of the array file in the same directory. `source_detail` is the
recipe someone else would use to obtain or regenerate the array: a
repository URL with a commit, a DOI, or the exact generating command
and software version. `construction` names the construction or
search that produced the array, in the words a covering array
researcher would use: the recursive construction and its ingredients
(for example "Raaphorst-Moura-Stevens extension, q = 7, m = 2"), the
search method (for example "simulated annealing from the
CA(136; 4, 179, 2) with one column added"), or an algebraic source.
It is required, because the construction is what another researcher
needs in order to know how the array can be used as an ingredient
(constant rows, how it splits). Write `unknown` only if you cannot
say. `credit` is the person, group or paper to be credited. `notes`
is free text and may be empty; the check already records the
previous best, so there is no need to repeat it here. Fields that contain
commas must be enclosed in double quotes, as in any CSV file, and no
field may contain a line break.

Each array file is plain text with one run per line. Entries are
separated by spaces, tabs or commas. Symbols are either `0` to `v-1`
or `1` to `v`; the check detects which. A don't-care entry, an entry
that may take any value, is written `NA`, `-`, `*`, `x` or `-1`.
These are the conventions of `ca_verify.c`, except that the check is
stricter about anything else: a header line, a comment or any other
token is an error rather than being skipped. The file must have
exactly `N` non-blank lines of exactly `k` entries each.

The directory `submissions/example/` is a complete worked example:
the 9-run orthogonal array OA(9; 2, 4, 3) over GF(3), whose rows are
(a, b, a+b, a+2b mod 3), with its `claims.csv`. Nine runs is the best
known size for strength 2, four columns and three symbols, so the
check records it as `equals_best`. (It is a different array from the
Dwyer array already stored as `table/arrays/CA_9_2_4_3.txt`. A
verbatim copy of that file would be rejected as a duplicate.) The
example directory itself is never checked or recorded.

## What a claim means

The table uses stair-step semantics. A row (t, v, k, N) says that N
runs suffice for a strength-t covering array on up to k columns over
v symbols, because deleting columns from a covering array leaves a
covering array. So the best known N at (t, v, k) is the smallest N
among table rows with the same t and v and at least k columns. Your
claim is compared with that number. If you have one array that
serves a whole range of k, submit it once at its largest k; it then
also improves every smaller k for which it beats the table.

Only rows of tier CITED (the dated Colbourn snapshot and other
traceable sources) and VERIFIED (arrays checked exhaustively) count
for the comparison. SCREENED rows (below) are recorded but do not
set the best known value.

## What happens on a pull request

When a pull request touches `submissions/`, the workflow
`.github/workflows/verify-submission.yml` runs
`tools/check_submission.py` on every submission directory the pull
request changes. The tools, the verifier and the table it compares
against always come from the main branch, never from the pull
request, so nothing in a submission is ever executed.

For every claim, the check reads the array, confirms it has N rows
and k columns with symbols in range, puts it in canonical form
(0-based integer symbols, one run per line, values separated by
single spaces, `NA` for don't-care, a newline after every line) and
computes the SHA-256 of that text. The hash is the array's identity:
an array whose hash is already in the table is a duplicate and is
rejected, however it was formatted. The check then runs `ca_verify`
at strength t on the canonical array and looks up the current best
known N.

The check posts its report as a comment on the pull request. The
report gives a verdict for every claim, the reasons for any failure,
the exact uncovered combination (columns and values) if the array is
not covering, and timings. The report usually appears within a few
minutes of opening the pull request. A maintainer then reviews and
merges, usually within a few days, and the table updates on its own
after the merge.

There are two outcomes. If every claim passes, the check passes and
the comment says so. Nothing is written to your branch. When the pull
request is merged, the workflow `.github/workflows/table-page.yml` on
the main branch runs the same check on your submission again, against
the table as it is at that moment, and if every claim still passes it
appends one row per array to `table/ca_table.csv` and to
`table/MANIFEST.csv` and adds the canonical array files to
`table/arrays/`. Merged submissions are added one at a time, each
against the newest table, so two submissions can never overwrite or
conflict with each other. The result is posted on the pull request.
If a claim no longer passes at that point (for example because
someone else's array with the same hash was added first), nothing of
that submission is added and the comment says why. If any claim fails
the check on the pull request, the check fails, the comment says why,
and nothing is added. Fix the problem and push again; every push is
checked afresh.

Two more lines in the report are for you and for the maintainer.
"Similarity" compares the array with every known array of the same
N, k and v, including the arrays withdrawn on 2026-10-27, by a
fingerprint that does not change when rows or columns are reordered
or symbols renamed. A match does not fail the claim, since small
optimal arrays are often unique and can be found independently, but
it is flagged and the maintainer decides. "Prior work to cite" names
the source of the entry your array is compared with and any
reference in `../table/references.csv` that matches it or
your construction, so that a paper built on the result can cite the
work it improves on.

A passing claim is classified against the table. `exceeds_table`
means N is smaller than the current best known value, a new record.
`equals_best` means N equals it. `above_table` means N is larger: the
array is still recorded as verified, with a note that it is not an
improvement. The table rows record which of these applied and the
value the claim was compared with. The comparison uses the CITED and
VERIFIED rows, including a CITED value that has a DISPUTED row (see
table/README.md), so a claim larger than a disputed value is classed
`above_table`, even when it is smaller than every verified array at
those parameters.

## Size limits

An array file may be at most 50 MiB, and the files of one submission
together at most 200 MiB. A file over the first limit fails its claim
before it is read, and a submission over the second is refused before
any claim is checked. The report states the size.

The limits come from storage. GitHub refuses any file over 100 MiB,
warns above 50 MiB, and recommends keeping a repository under 1 GB,
and the table keeps a copy of every accepted array. For scale, the
largest arrays stored as plain text, CA(1078; 2, 8000, 19) and
Bergeron's CA(20216; 3, 401, 19) and its two neighbors, are 18 to 20
MiB each as text. One array, CA(1870; 2, 17576, 25), is 82 MiB as text
and is stored gzip-compressed by the maintainer under the rule in
`../table/README.md`; a submitted file stays within the limits above.
Array text compresses well, so git stores the whole repository, those
files included, in far less than its size as text.

GitHub's web page accepts uploads only up to 25 MiB per file, so an
array file larger than that has to be added with git from your own
machine.

An array too large for these limits can still enter the table. It stays
in a public deposit (a Zenodo record, or a release of this repository),
and the submission names it in `submissions/<slug>/external.csv`
instead of adding the file:

    t,v,k,N,location,sha256,source_detail,construction,credit,notes

`location` is the https URL of the file, or of a zip archive followed by
`::` and the member name, for example
`https://zenodo.org/records/123/files/arrays.zip::part1/CA_x.txt`.
`sha256` is the SHA-256 of the array's canonical form (0-based, single
spaces, `NA` for don't-care, a line feed after every row), the same
hash the check reports for an ordinary submission. The other fields are
as in `claims.csv`.

The pull request check does not download these. A maintainer runs
`python3 tools/external_array.py submissions/<slug>` on a larger
machine. It downloads each file, rebuilds the canonical form as a
stream, compares the hash, runs `ca_verify` at strength t (in full
within the time budget, otherwise on the same deterministic column
windows as the pull request check, which gives SCREENED), compares the
size with the table, and with `--apply` adds the rows and an entry in
`table/EXTERNAL.csv`. The table then names the exact array, where it is
and how it was checked, without holding a copy, and the page links to
the deposit. Anyone can fetch and confirm an external array with
`python3 tools/external_array.py --fetch LOCATION SHA256 OUT`.

## Certificates: covering perfect hash families

A covering array given by a covering perfect hash family (CPHF) can be
submitted as the family instead of the array. The submission holds
`submissions/<slug>/certificates.csv`

    t,v,k,N,file,mode,source_detail,construction,credit,notes

and the family files it names, each at most 50 MiB: n lines of k
integers, each integer a vector of GF(v)^t written in base v, most
significant digit first (for v = p^e the digits are field elements
coded as in `../tools/cphf/cphfcheck.c`, Conway polynomials; v up to 32,
t up to 8). `mode` says how the family is checked: `full` (every set of
t columns), or `cyclic s` (the shift of columns by s is a symmetry of
every row, certified by the checker before it relies on it, and then
every t-set whose smallest column is below s is checked). Either may end
in ` affine` when every vector has first coordinate 1 (points of an
affine space); the array then has n(v^t - v) + v runs instead of
n(v^t - 1) + 1. N must be the size the family gives.

The pull request check does not run these, because an exact check can
take hours. A maintainer runs
`python3 tools/check_certificates.py submissions/<slug>`. It checks every
family exactly with `../tools/cphf/cphfcheck.c` (never by sampling),
expands it to the covering array in the table's canonical form and hashes
it as a stream, and compares N with the table. With `--apply` the family
goes to `table/certificates/`, is listed in `CERTIFICATES.csv`, and the
array enters as a VERIFIED row whose stamp begins `cphfcheck`, with the
array's SHA-256. Anyone can rebuild the array from the family with
`cphfcheck FILE t v expand OUT [affine]` and compare the hash.

A family with no symmetry the checker can use, and too many t-sets to
check every one, cannot enter as VERIFIED. Write first (an issue), so
that the check can be planned.

## Large arrays: the screened status

The pull request check runs on a GitHub-hosted runner with 2 cores
and a 6-hour job limit. Each array gets a budget of 15 minutes of
wall-clock time, and a whole pull request gets 300 minutes. The work
of an exhaustive check grows like C(k, t) times v^t; when that number
exceeds 10^10, or when an exhaustive check does not finish within
its budget, the check screens the array instead of verifying it.

A screen picks 20 random sets of 30 columns, seeded from the array's
own hash so anyone can repeat it, and verifies each of these
sub-arrays exhaustively at strength t. If any of them has an
uncovered combination the array is not a covering array, and the
claim fails with that combination as proof. If all of them pass, the
claim is recorded with tier `SCREENED` and MANIFEST status
`screened`, never `VERIFIED`. A screened row is evidence, not proof,
and it does not count as the best known value. Anyone with a bigger
machine can verify the array in full later with `ca_verify` and
record that as a new VERIFIED row. If even the screen cannot finish
within the budget, the claim fails; such arrays need a maintainer
with more computing power.

Arrays with at most 30 columns are never screened: the screen would
be the full check, so they get the full check.

## Credit and the rows that are written

Your `credit` field goes into the notes of the table row exactly as
you wrote it, after `credit: `. Your `source_detail` becomes the
row's `source_detail` and your `construction` the row's
`construction`, both exactly as written. Each new `ca_table.csv` row
has source class `S7`, the pull request number as `snapshot_id`, the
array's SHA-256, a stamp of the form `ca_verify <commit> <date>
github-actions`, the entry date, and notes that state the credit, the
comparison with the previous best and its source, the submission
slug, and your notes. The MANIFEST row also records the array's
constant rows, the largest number of rows that symbol permutations
within columns make constant, computed by `tools/constant_rows.c`
(the computation of `cafast::maxconstant_c`); the report states it.
The canonical file is named `CA_N_t_k_v.txt`;
if that name is already taken by a different array, the first eight
hex digits of the hash are appended, as in `CA_9_2_4_3_9133df95.txt`.

## Pull requests from forks

Most submitters will open the pull request from a fork. That works
exactly as above: the check fetches your branch as data, reports on
the pull request, and the rows are added after merge. Nothing needs
write access to your fork.

## Rules (since 2026-10-31)

1. Say how the work was done. In the pull request text, name the tools
   that found the arrays and wrote the claims and text, AI systems
   included, and who takes responsibility for the submission. The
   check decides whether an array is accepted, not the tools used, but
   readers deserve to know.
2. Arrays, not assertions. A claim is accepted only with an array the
   check can verify, or a certificate the table can check with its own
   tool. A proof, size or bound supported only by a description, or by
   a model's statement, is not entered. Sizes from a self-published
   deposit (for example a personal Zenodo record) enter only as arrays
   through this check, not as cited rows (`../table/README.md`,
   "Admissible sources").
3. Certificates. A claim given by a certificate instead of a written
   array is accepted only for a certificate type that the table can
   check with its own independent tool. Today that is the cyclic
   covering perfect hash families of `../tools/cphf/`. The pull
   request check does not run those tools, so open an issue first;
   other certificate types are declined until such a tool exists.
4. Licence. By opening a pull request you confirm that you may release
   the arrays and that you license them under CC BY 4.0, as the arrays
   built by this project are. An array derived from someone else's
   published array must name that array in `source_detail`, and it is
   stored only if its source allows redistribution.
5. Real names. Credit goes to real people by their real names, as it
   did in the tables this one continues. Every submission names the
   person or people responsible, each with an email address where the
   maintainer can reach them and an affiliation ("Independent
   researcher" is an affiliation), in the pull request text or sent to
   the maintainer at chrispbsmolen@gmail.com. An ORCID iD is welcome
   and is listed when given. An organization or an AI system may be
   named alongside a person, never instead of one. Pseudonymous credit
   arranged before 2026-10-31 stays as it was; it is not available for
   new submissions.

## Checking locally before you submit

You can run the same check on your own machine with Python 3 and a C
compiler:

    cc -O3 -pthread -o ca_verify ca_verify.c
    python3 tools/check_submission.py submissions/<slug>

It prints the report and writes it, a JSON summary and the rows it
would append to `check-<slug>/`. Nothing in `table/` changes unless
you add `--apply`. Locally the per-array budget defaults to 20
minutes; `--budget-minutes`, `--screen-threshold` and `--threads`
change the limits.
