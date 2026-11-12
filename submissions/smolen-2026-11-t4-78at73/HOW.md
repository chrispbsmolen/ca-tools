# How this array was built

Construction: the cyclotomic (quadratic character) array for q = 73, with its 73 diagonal cells chosen by search
and 5 rows added by simulated annealing.

CA(78; 4, 73, 2).

1. The base array. Rows and columns are the residues modulo 73. The entry at row x and column y is 1 when x + y is
   a nonzero square modulo 73 and 0 when it is a non-square. This is the cyclotomic array of Colbourn 2010 for
   q = 73 and two symbols, the Paley matrix. For q = 67, 71 and 79 that array is already a covering array of
   strength 4. For q = 73 it is not, and Lemma 5.1 of that paper lists 73 as an exception. With the fixed value 0
   in the cells where x + y = 0 it misses 2190 patterns, and the all 1 row of his Construction 4.1 part 2 still
   leaves 876 of them.

2. The free diagonal. The character is not defined at 0, so the 73 cells with x + y = 0 can hold either symbol.
   They are left unknown. Then 4380 patterns on sets of four columns are not covered by the remaining rows, and
   every one of them can be covered by 2 or 3 choices of those cells. The program programs/need.c writes the list,
   one pattern per line with the choices that cover it.

3. The search. The unknowns are the 73 free cells and 5 added rows of 73 cells each. A move changes one cell. The
   cost is the number of listed patterns still uncovered. Simulated annealing at the fixed temperature 0.35
   (programs/ls.c) reached 0 after 1,487,564 moves with seed 3. Seeds 1 and 2 stopped with 2 patterns uncovered.
   The result is programs/patch_m5_seed3.txt. Two of the five added rows came out constant, one all 0 and one
   all 1.

4. Writing the array. programs/build.py writes the 73 base rows with the chosen diagonal, then the 5 added rows.

What is known about fewer rows. With no added row, one added row or two added rows there is no solution (exact,
by a SAT solver on the same list). Three and four added rows are undecided. Annealing with four added rows
stopped with 19 patterns uncovered.

The array was checked exactly with ca_verify on all 1,088,430 sets of four columns.

Built from the quadratic character of GF(73) only. No array of Torres-Jimenez is an ingredient or start.

To rebuild:
    cc -O2 -o need programs/need.c
    cc -O2 -o ls programs/ls.c -lm
    ./need 73 > need73.txt
    ./ls 73 5 need73.txt 0.35 4000000000 3 > patch.txt
    python3 programs/build.py patch.txt CA_78_4_73_2.txt
The search uses its own random number generator and whole-number costs. The acceptance test uses exp from the
C library, so a rebuild on another machine can take a different path. programs/patch_m5_seed3.txt is the result
used here.
