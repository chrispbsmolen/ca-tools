# How this array was built

Construction: column extension of the table's CA(130;4,167,2) by two columns chosen by simulated annealing and one
added row, finished by an exact single-cell repair.

CA(131; 4, 169, 2).

1. The base. The table's own CA(130;4,167,2) (table/arrays/CA_130_4_167_2.txt, submission
   smolen-2026-11-t4-130at167: the quadratic character array of GF(167) with rows removed, its diagonal and 16 added
   rows chosen by search, and an exact repair). sha256 3488ce29cad2349d27d23416623deb8c4f6d5e1e17d088d2590bf6ef0579754c.

2. Two new columns. For a new column to keep strength 4 with every triple of old columns, the rows that cover each
   pattern on that triple must not all carry the same value in the new column. programs/colopt.c chooses the 130
   entries of one new column by simulated annealing to minimise the number of such single-valued row sets (arguments
   167 130 15 0.5 40000, seed 5 for the first column and seed 6 for the second; outputs programs/c1.out and c2.out).

3. One added row. A row of 169 random entries (Python random.seed(1)) is appended. The 131 x 169 array then misses
   89 patterns on sets of four columns.

4. The repair. programs/repi4.c flips single cells anywhere in the array, keeping exact incremental lists of the
   uncovered patterns and of the patterns covered by only one row (seed 1, temperature 0.25, 1 thread). It reached
   0 after 721 accepted flips.

The array was checked exactly with ca_verify on all 32,795,126 sets of four columns.

Built from: the table's CA(130;4,167,2) only, itself built from the quadratic character of GF(167). No array of
Torres-Jimenez is an ingredient or start.

Program: programs/recipe.sh runs every step with the base array beside it under the name it expects. A complete run
from scratch reproduced the array exactly (programs/recipe_log.txt):
    cp table/arrays/CA_130_4_167_2.txt h000_fresh_20261113T0130.txt
    bash recipe.sh
Sources: programs/colopt.c and repi4.c (gcc -O2; Python 3).
