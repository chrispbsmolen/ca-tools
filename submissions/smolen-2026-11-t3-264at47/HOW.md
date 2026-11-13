# How this array was built

Construction: the row blocks of the table's own CA(49;3,352,2) with one block replaced by a smaller one, and a new
code of 264 words over the five blocks built from lines in Z11 x Z11.

CA(47; 3, 264, 2).

1. The blocks. The rows of the table's CA(49;3,352,2) (Power CT, file table/arrays/CA_49_3_352_2.txt) fall into five
   blocks of 11, 11, 11, 10 and 6 rows, in which a column shows one of 11, 11, 11, 8 or 4 distinct patterns
   (programs/alg2.py writes them). Here the block of 10 rows is replaced by a new block of 8 rows with 5 patterns,
   found by one SAT call (programs/blk.py 8 5). So the array has 11 + 11 + 11 + 8 + 6 = 47 rows, and every column
   is a word (a, b, c, x, y) over alphabets of sizes 11, 11, 11, 5 and 4.

2. The condition. In each block, any three distinct patterns show all six non-constant triples of symbols, and two
   distinct patterns show both 01 and 10. The constant triples come from two of the blocks of 11 rows. From this
   a set of words gives a strength-3 covering array if and only if no word agrees, coordinate by coordinate, with
   one of two other words in each coordinate. This is the column replacement of Colbourn and Torres-Jimenez (2010)
   and Colbourn and Zhou (2012), and the condition on the words is that of a 2-frameproof code (Blackburn, SIAM J.
   Discrete Math. 16 (2003) 499-510), also called a separating hash family of type {1,2}.

3. The code. Write a word as (t, t + u, t + v, x, y) with t, u, v in Z11, so a slab (x, y) holds the 11 words of a
   point (u, v). Two points lie on a common line of a class when they share u, share v, or share v - u. Three
   rules make the words meet the condition. Points of slabs that share x or share y never share a class line. In
   a slab with two or more points, each point shares no class line with any other point. All points are distinct.
   One point in each of the 20 slabs gives the 220 words of the truncated Power CT code. Here slab (0, 0) holds
   5 points and each of the other 19 slabs holds one, 24 points and 264 words in all. programs/lin3.py 5 4 5 24
   places them by one call to CaDiCaL 1.5.3 (python-sat 1.9.dev22). programs/build.py checks the condition on the
   words for every split of the five coordinates and writes the array.

In this model 24 points is the most that one slab with several points allows for these alphabets: 6 points in that
slab leave at most 19 points for the other slabs, and no choice with 19 has room for the 6.

The array was checked exactly with ca_verify on all 3,031,864 sets of three columns.

Built from: the table's own CA(49;3,352,2), whose blocks of 11, 11, 11 and 6 rows are reused as pattern tables, and
the block of 8 rows built here.

Program: programs/recipe.sh copies table/arrays/CA_49_3_352_2.txt and runs programs/alg2.py, programs/blk.py,
programs/lin3.py and programs/build.py. It is deterministic. Two complete runs from scratch gave the same array
and the same log (programs/recipe_log.txt). Needs python 3.13, numpy and python-sat 1.9.dev22.
