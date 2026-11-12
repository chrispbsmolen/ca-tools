# How this array was built

Construction: the cyclotomic (quadratic character) array for q = 337, restricted to 192 of its columns chosen by
weighted simulated annealing, with its diagonal cells and 8 added rows chosen by simulated annealing, finished by
an exact single-cell repair.

CA(345; 5, 192, 2).

1. The base array. Rows and columns are the residues modulo 337. The entry at row x and column y is 1 when x + y is
   a nonzero square modulo 337 and 0 when it is a non-square. This is the cyclotomic array of Colbourn 2010 for
   q = 337 and two symbols, the Paley matrix. The 337 cells with x + y = 0 are left free.

2. The columns. programs/need5s.c and programs/expand.py list the patterns on sets of five columns that the base
   rows leave uncovered, with the free cells that could cover each one. programs/genpw.py weights each pattern by
   the inverse of the number of those choices, so patterns that are hard to cover count more. programs/subselw.c
   chooses 192 of the 337 columns by simulated annealing over column swaps to minimise the weighted total inside
   the chosen columns (seed 2, 1,500,000 moves, temperature 0.5). The chosen columns are programs/sub_A.txt, and
   programs/mklist.py writes the patterns that remain.

3. The diagonal and the added rows. The unknowns are the free diagonal cells and 8 added rows. A move changes one
   cell, and the cost is the number of listed patterns still uncovered. Simulated annealing at the fixed
   temperature 0.35 (programs/ls2m.c, seed 1, 35,363,840 moves) stopped with 163 patterns uncovered.
   programs/build.py writes the 345 x 192 array.

4. The repair. programs/repi.c flips single cells anywhere in the array. It keeps exact incremental lists of the
   uncovered patterns and of the patterns covered by only one row, and at each step takes an uncovered pattern and
   the best row one cell away from covering it, accepting a worse move with probability exp(-delta / T). Four
   stages, each started from the best state of the one before:
     seed 21, T 0.35, 1 thread,  400 accepted flips: 163 to 4 uncovered
     seed 31, T 0.22, 1 thread,  400 accepted flips: 4 to 3
     seed 41, T 0.2,  2 threads, 200 accepted flips: 3 to 1
     seed 77, T 0.2,  2 threads, stopped at 0 after 207 accepted flips
   The number of threads changes the order of the work and so the result; it is part of the recipe.

The array was checked exactly with ca_verify on all 2,063,130,048 sets of five columns.

Built from: the quadratic character of GF(337) only. No array of Torres-Jimenez is an ingredient or start.

Program: programs/run_recipe.sh runs every step in an empty directory with the sources beside it, stops on move
and flip counts only, logs the sha256 of every source and output, and compares each stage with the original files:
    bash run_recipe.sh
Sources: programs/need5s.c, expand.py, genpw.py, subselw.c, mklist.py, ls2m.c, build.py, repi.c (gcc -O3; Python 3
with numpy). A complete run from scratch reproduced every stage and the final array exactly
(programs/recipe_log.txt).
