# How these arrays were built

Construction: the cyclic array on Z63 of the table's CA(126;5,28,2), used on more shifts, with one, three or four
added rows and their complements that repair every 5-set of shifts the 126 rows leave uncovered.

CA(128; 5, 32, 2), CA(132; 5, 35, 2) and CA(134; 5, 36, 2).

1. The 126 rows. As in the submission smolen-2026-11-t5-126at26, f is the binary vector of length 63
   011011011010001111001100000010111011000110100001010100011101111, constant on the orbits of x -> 2x. The entry in
   row x and column d is f(x + d), and the 63 rows and their 63 complements give 126 rows. Taking the cyclic shifts
   of one binary vector together with their complements is the cyclic construction of Colbourn and Keri (Binary
   covering arrays and existentially closed graphs, LNCS 5557 (2009) 22-33).

2. The bad sets. programs/bad5.c lists every set of five shifts on which the 126 rows miss a pattern: 7,245 of the
   7,028,847 sets. 3,717 of them miss 16 patterns and are never used. The other 3,528 miss exactly one pattern p
   and its complement, and p always has one column against the other four.

3. The added rows. A row r and its complement repair such a set when r equals p or its complement on the five
   columns, that is, when r_i + r_j = p_i + p_j modulo 2 for the columns i, j of the set. So one added row and its
   complement repair a whole family of bad sets exactly when these equations have a common solution.

4. The search. The shifts and the added rows are chosen together so that no 16-pattern set lies inside the chosen
   shifts and every other bad set inside them is repaired.
   - 32 shifts, one added row and its complement, 128 rows: programs/pick2.py 32 1 1 12 anneals the set of shifts
     and refits the row in turn; programs/mk2.py solves the equations and writes the array. Shifts 3 4 6 7 9 10 11
     13 16 17 18 20 22 25 27 28 29 30 33 35 37 44 46 48 49 51 52 53 54 56 57 60 (28 bad sets, one family).
   - 35 shifts, three added rows and their complements, 132 rows: programs/joint.c 35 3 1 4000000 0.5 anneals
     shifts and rows together; programs/mk3.py writes the array.
   - 36 shifts, four added rows and their complements, 134 rows: programs/joint.c 36 4 2 8000000 0.3.
   Both programs use fixed seeds and stop on a move count.

Not reached with these programs: 37 shifts with four added rows and their complements, and 33 shifts with two.

The arrays were checked exactly with ca_verify on all sets of five columns (201,376 for k = 32, 324,632 for k = 35,
376,992 for k = 36).

Built from: the vector f alone.

Program: programs/recipe.sh compiles programs/bad5.c and programs/joint.c and runs the steps above. It is
deterministic. Two complete runs from scratch gave the same three arrays and the same log
(programs/recipe_log.txt). Needs a C compiler and python 3.
