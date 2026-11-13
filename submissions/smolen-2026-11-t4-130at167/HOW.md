# How this array was built

Construction: the cyclotomic (quadratic character) array for q = 167 with rows removed greedily to 114, its
diagonal cells and 16 added rows chosen by simulated annealing, finished by an exact single-cell repair.

CA(130; 4, 167, 2).

1. The base array. Rows and columns are the residues modulo 167. The entry at row x and column y is 1 when x + y is
   a nonzero square modulo 167 and 0 otherwise. This is the cyclotomic array of Colbourn 2010 for q = 167 and two
   symbols, the Paley matrix.

2. Row removal. programs/greedy.c removes rows one at a time, each time the kept row that covers the fewest
   (4-set, pattern) pairs alone, until 114 rows are left. It is deterministic. The diagonal cells are 0 during
   this step.

3. The free diagonal. The 114 cells of the kept rows with x + y = 0 are then left free. programs/holes4w.c lists
   the patterns on sets of four columns that the other cells of the kept rows leave uncovered, with the choices of
   diagonal cells that cover each.

4. The diagonal and the added rows. The unknowns are the free diagonal cells and 16 added rows. A move changes one
   cell, and the cost is the number of listed patterns still uncovered. Simulated annealing at the fixed
   temperature 0.35 (programs/ls2m.c, seed 1, 8,000,000 moves) stopped with 33 uncovered. programs/build4.py writes
   the 130 x 167 array.

5. The repair. programs/repi4.c flips single cells anywhere in the array, keeping exact incremental lists of the
   uncovered patterns and of the patterns covered by only one row (seed 1, temperature 0.25, 1 thread). It
   reached 0 after 94 accepted flips.

The array was checked exactly with ca_verify on all 31,256,555 sets of four columns.

Built from: the quadratic character of GF(167) only. No array of Torres-Jimenez is an ingredient or start.

Program: programs/run_recipe.sh runs every step in an empty directory with the sources beside it, stops on move
and flip counts only, and logs the sha256 of every source and output. A complete run from scratch reproduced the
array exactly (programs/recipe_log.txt):
    bash run_recipe.sh
Sources: programs/greedy.c, holes4w.c, ls2m.c, build4.py, repi4.c (gcc -O3; Python 3).
