# How these arrays were built

Construction: a complement-doubled circulant of one binary function on Z63 that is invariant under x -> 2x, with
the columns chosen to avoid every bad set of five shifts.

CA(126; 5, 28, 2), and with 26 of the shifts, CA(126; 5, 26, 2).

1. The function. Let f be a function from Z63 to {0, 1} that is constant on the 13 orbits of the map x -> 2x (the
   cyclotomic classes of 2 modulo 63, the Frobenius orbits of GF(64)*). There are 8192 such functions, 4096 up to
   complement, since a complemented f gives the same array. programs/gdev.c scores all of them on a fixed sample of
   5-sets and keeps the best.
   f = 011011011010001111001100000010111011000110100001010100011101111.

2. The rows. For x in Z63 and a shift d, the entry in row x and column d is f(x + d). The 63 rows and their 63
   complements give 126 rows. A set of five shifts is good when these 126 rows show all 32 patterns on it.
   programs/gdev.c lists the bad sets exactly. 7,245 of the 7,028,847 sets of five shifts are bad (0.103 percent).

3. The columns. programs/palsub.c looks for a set of shifts containing no bad 5-set. With seed 1 it finds 28 shifts
   (30 38 51 1 6 37 44 48 17 61 42 46 39 11 18 26 0 52 2 7 24 54 62 12 47 9 10 43) and, in a separate run, 26
   shifts (61 15 60 36 34 59 47 62 33 8 22 27 41 14 20 49 51 38 43 44 35 18 5 13 52 45). programs/build.py writes
   the arrays.

The arrays were checked exactly with ca_verify on all sets of five columns (98,280 for k = 28, 65,780 for k = 26),
and again by an independent bitmask count. The 26-column array was also rebuilt independently from f and the 26
shifts alone.

Built from: nothing; the construction starts from Z63, the map x -> 2x and fixed seeds. No array of Torres-Jimenez
is an ingredient or start.

Program: programs/recipe.sh compiles programs/gdev.c and programs/palsub.c, runs programs/mkcls.py, gdev, palsub
and programs/build.py. It is deterministic. A complete run from scratch reproduced both arrays exactly
(programs/recipe_log.txt). Needs gcc and python 3.
