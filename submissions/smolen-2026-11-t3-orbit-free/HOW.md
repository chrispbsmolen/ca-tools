# How these arrays were built

Construction: an array whose first columns are invariant under a permutation of its rows (a few full column orbits),
extended by further columns, found by exhaustive search.

CA(20; 3, 28, 2), CA(21; 3, 32, 2) and CA(24; 3, 42, 2).

Let tau be a permutation of the N rows with cycles of unequal lengths, and let L be the least common multiple of the
cycle lengths. Applying tau to a binary column gives another column. A column is kept when its L images form a
covering array of strength 3 by themselves, one column per orbit and up to complement. Two or more orbits are joined
when their union is a covering array of strength 3.

The program lists every set of m joined orbits that contains a representative under the normaliser of tau
(rotations of each cycle, and the maps i to u*i on all cycles for u coprime to L). Every set of m joined orbits can
be moved by the normaliser to one of these, so the list is complete up to that symmetry.

For each set the program then lists every further column that keeps strength 3 with the m*L orbit columns. A column
does so exactly when it is constant on none of the four row classes of any pair of orbit columns. One subset-sum
transform over the 2^N sets of rows decides this for all columns at once, so the list of further columns is complete.
The program then finds the largest set of further columns that keeps strength 3 together, by exact search.

| array | cycles of tau | L | orbits kept | m | sets of m orbits | further columns | columns |
|---|---|---|---|---|---|---|---|
| CA(20; 3, 28, 2) | 6, 6, 3, 3, 1, 1 | 6 | 19,140 | 4 | 8 | 4 | 24 + 4 = 28 |
| CA(21; 3, 32, 2) | 9, 9, 3 | 9 | 19,368 | 3 | 2 | 5 | 27 + 5 = 32 |
| CA(24; 3, 42, 2) | 8, 8, 4, 4 | 8 | 317,384 | 4 | 1304 | 10 | 32 + 10 = 42 |

In each case no set of m + 1 orbits exists for that tau. This was checked with the same search asked for larger m.
For 24 rows most sets of four orbits take no further column. Among the first 1000 sets, 80 take four, 4 take five
and 8 take ten. No set takes more than ten. The array is the first set that takes ten. That set has 244
further candidate columns. None of the three arrays takes one more column. This was checked exactly with a SAT solver.

The search is exhaustive and uses no random numbers. Built without OpenMP it visits the sets in a fixed order, so a
rebuild gives the same files. RECIPE.txt and REPLAY.log record two full rebuilds and their hashes.

Each array was checked exactly with ca_verify on all triples of columns, and with a separate brute force check.

The comparison is with the table as it stood on 2026-11-10 (cited sizes from the Colbourn tables of November 2024).
A search of the literature on 2026-11-11 found no smaller array for these parameters. That search is not a proof
that none has been published.

Built from: nothing. There is no input array. No array of Torres-Jimenez is an ingredient or start, and the arrays
do not have the fingerprint of one of his arrays.

Program: programs/ in this folder (orbfree3.c and recipe.sh). The program was written by an AI model for this
project.

To rebuild:
    cc -O3 -o orbfree3 programs/orbfree3.c
    ./orbfree3 20 4 a 6 6 3 3 1 1  &&  cmp a_ext_20_28.txt CA_20_3_28_2.txt
    ./orbfree3 21 3 b 9 9 3        &&  cmp b_ext_21_32.txt CA_21_3_32_2.txt
    ./orbfree3 24 4 c 8 8 4 4      &&  cmp c_ext_24_42.txt CA_24_3_42_2.txt
The first two runs take under a second. The third takes about 10 minutes on one core and under 100 MB of memory.
