# Cyclic covering perfect hash families (source S8, since 2026-10-28)

Three arrays of the table come from covering perfect hash families (CPHFs)
found here by a search over families with a cyclic symmetry, and checked
here by a separate program. Credit: Christopher Smolen (search and checks,
2026-10-26 to 2026-10-27).

| array | family | certificate | checked by |
|---|---|---|---|
| CA(2663; 5, 121, 3) | CPHF(11; 121, 3, 5) | `../../table/certificates/CPHF_11_121_3_5.txt` | `ca_verify.c` on the array (stored), `repcheck.c` on the family |
| CA(40613; 5, 781, 5) | CPHF(13; 781, 5, 5) | `../../table/certificates/CPHF_13_781_5_5.txt` | `repcheck.c` on the family |
| CA(218479; 5, 2801, 7) | CPHF(13; 2801, 7, 5) | `../../table/certificates/CPHF_13_2801_7_5.txt` | `repcheck.c` on the family |

## What a CPHF is, and how it gives the array

A CPHF(n; k, q, t), q a prime, is an n x k array whose entries are vectors
of GF(q)^t, such that for every set of t columns some row has t linearly
independent vectors in those columns. Sherwood, Martirosyan and Colbourn
(J. Combin. Des. 14 (2006) 202-213, doi:10.1002/jcd.20067) showed that it
gives a covering array CA(n(q^t - 1) + 1; t, k, q): the all-zero run, and for
every row r and every nonzero beta in GF(q)^t the run whose entry in column
c is the inner product of beta with the row's vector in column c.
`cphf_tools.c expand` writes that array in the table's canonical form, and
its SHA-256 is the `array_sha256` of the table row. The CA(40613; 5, 781, 5)
is 63 MB as text and the CA(218479; 5, 2801, 7) about 1.2 GB, so only their
families are stored (49 KB and 196 KB); anyone can rebuild the arrays and
compare the hash (on macOS build with clang and libomp, as for `repcheck`
below; the second form hashes the 1.2 GB array without writing it to disk):

    gcc -O2 -fopenmp -o cphf_tools cphf_tools.c
    ./cphf_tools expand ../../table/certificates/CPHF_13_2801_7_5.txt 5 7 CA_218479_5_2801_7.txt
    sha256sum CA_218479_5_2801_7.txt      # or: shasum -a 256 CA_218479_5_2801_7.txt
    # 432d81f32d1f3ba0637748e35c1c65848abdc0e021052a95d0695f9b48f7e982

    mkfifo ca.fifo; sha256sum < ca.fifo &     # or: shasum -a 256 < ca.fifo &
    ./cphf_tools expand ../../table/certificates/CPHF_13_2801_7_5.txt 5 7 ca.fifo; wait; rm ca.fifo

## The search (symcphf.c)

The columns are indexed by the cyclic group Z_m, here m = k. Row r is given
by a matrix M_r of GL(t, q) whose m-th power is a scalar, and a seed vector
x_r; its entry in column c is M_r^c x_r. Shifting every column by one then
multiplies every vector of the row by M_r (and the vector of the last column
by a nonzero scalar as well), which does not change linear independence. So
a t-set of columns is covered in a row exactly when its shift is, and it is
enough to check the t-sets that contain column 0: C(k - 1, t - 1) of them
instead of C(k, t), 2.56 x 10^12 instead of 1.43 x 10^15 at k = 2801. In all
three families here k = (q^t - 1)/(q - 1) (121, 781 and 2801 for q = 3, 5
and 7, t = 5), and every row's matrix has projective order k (a Singer
cycle of PGL(5, q)); each family's header lists them. The search picks the
first rows by sampling, makes one exact pass over all representatives to
list the uncovered ones, and completes the family greedily on that list.
The commands, seeds and logs are in `RUNS.txt`. Running a command again
gives the same family; the file differs only in its first comment line,
which records the run's wall-clock time, so compare the lines after the
comments rather than the file's hash.

## The check (repcheck.c)

`repcheck.c` was written separately from the search and shares no code with
it. For a stored family it

1. finds, for every row, the matrix A_r with A_r v[c] = v[c + 1] from t
   consecutive independent columns, and checks that relation at every
   column, the wrap A_r v[k - 1] = mu_r v[0] with mu_r nonzero, and that
   A_r is invertible (the symmetry certificate, checked, not assumed);
2. checks every set {0, a, b, c, d} against the rows, exactly: with the
   first four vectors fixed, their 4 x 4 minors give a normal vector n_r,
   and the set is covered in row r exactly when n_r . v_r[d] is nonzero.

It prints the number of uncovered representatives (0 for a CPHF) and the
first ones found. It was tested against `cphf_tools.c check` (a brute force
over all t-sets by determinant): on a 9-row family with k = 121 that is not
a CPHF both report the same failures (875 representatives, 21,175 sets =
875 x 121 / 5), and a family with one changed entry fails the symmetry
certificate.

    gcc -O3 -fopenmp -o repcheck repcheck.c            # macOS: clang with libomp
    ./repcheck ../../table/certificates/CPHF_13_2801_7_5.txt 5 7 14

`repcheck.c` handles t = 5, q prime below 64 and at most 64 rows, and
`cphf_tools.c` rows of at most 70,000 entries; both are used here well
inside those limits, unchanged from the runs recorded (the stamps name
`repcheck.c` by its SHA-256, 1aaaf64c0e47...).

## Credits and bounds

The CPHF method and the CPHF-to-CA construction are those of Sherwood,
Martirosyan and Colbourn (2006). Rows whose columns are consecutive
vectors M^c x of a cyclic matrix (Singer cycles, linear feedback shift
register sequences) are known in the literature on covering arrays, for
example in the work of Raaphorst, Moura and Stevens (2014), of Tzanakis,
Moura, Panario and Stevens (2016), and of Shokri, Moura and Stevens
(arXiv:2510.13122), which this table already cites. What is this
project's here is these three families, the search that found them, its
completion by an exact pass, and the checker. The
existence bound the strength 5 and 6 rows of the table are compared with is
that of Colbourn, Lanus and Sarkar (Des. Codes Cryptogr. 86 (2018) 907-937,
doi:10.1007/s10623-017-0369-x).
