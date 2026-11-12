# How this array was built

Construction: the cyclotomic (quadratic character) array for q = 337, restricted to 192 of its columns chosen by
simulated annealing, with its diagonal cells and 9 added rows chosen by simulated annealing, finished by an exact
single-cell repair.

CA(346; 5, 192, 2).

1. The base array. Rows and columns are the residues modulo 337. The entry at row x and column y is 1 when x + y is
   a nonzero square modulo 337 and 0 when it is a non-square. This is the cyclotomic array of Colbourn 2010 for
   q = 337 and two symbols, the Paley matrix. The 337 cells with x + y = 0, where the character is not defined, are
   left free.

2. The columns. Only 192 columns are needed. programs/need5s.c and programs/expand.py list the patterns on sets of
   five columns that the base rows leave uncovered. programs/subsel.c chooses 192 of the 337 columns by simulated
   annealing so that as few of those patterns as possible fall inside the chosen columns (seed 1, 1,500,000 moves,
   temperature 1.0). The chosen columns are in programs/sub_T1.0.txt, and programs/mklist.py writes the patterns
   that remain.

3. The diagonal and the added rows. The unknowns are the free diagonal cells and 9 added rows. A move changes one
   cell, and the cost is the number of listed patterns still uncovered. Simulated annealing at the fixed temperature
   0.35 (programs/ls2m.c, seed 1, 35,363,840 moves) stopped with 113 patterns uncovered. programs/build.py writes the
   346 x 192 array from it.

4. The repair. programs/repcm.c flips single cells anywhere in the array, keeping exact lists of the uncovered
   patterns and of the patterns covered by only one row, and accepts a flip that lowers the number uncovered or,
   at temperature 0.5, one that does not. Run 1 (seed 1, 99 iterations) reached 20 uncovered and run 2 (seed 2,
   from that array) reached 0 after 62 iterations.

The array was checked exactly with ca_verify on all 2,063,130,048 sets of five columns.

Built from: the quadratic character of GF(337) only. No array of Torres-Jimenez is an ingredient or start.

Program: programs/run_recipe.sh runs every step in an empty directory with the sources beside it, stops on move and
iteration counts only, and logs the sha256 of every source and output. A second run from scratch reproduced the
array exactly (programs/recipe_log.txt):
    bash run_recipe.sh
Sources: programs/need5s.c, expand.py, subsel.c, mklist.py, ls2m.c, build.py, repcm.c (gcc -O3; Python 3 with
numpy).
