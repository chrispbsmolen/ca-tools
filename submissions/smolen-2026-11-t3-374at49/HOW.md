# How these arrays were built

Construction: the table's own CA(49;3,352,2) read as a code over its five row blocks, then a new code with more
words built from lines in Z11 x Z11.

CA(49; 3, 374, 2), and its first 359 columns, CA(49; 3, 359, 2).

1. The blocks. The rows of the table's CA(49;3,352,2) (Power CT, file table/arrays/CA_49_3_352_2.txt) fall into five
   blocks of 11, 11, 11, 10 and 6 rows. In each block a column shows one of 11, 11, 11, 8 or 4 distinct patterns
   (programs/alg2.py writes them). So every column is a word (a, b, c, x, y) over alphabets of sizes 11, 11, 11, 8
   and 4, and the array is the five pattern tables read through the words.

2. The condition. In each block, any three distinct patterns show all six non-constant triples of symbols, and two
   equal patterns with a third show both 00z and 11z. The constant triples come from two of the blocks. From this a
   set of words gives a strength-3 covering array if and only if no word agrees, coordinate by coordinate, with one
   of two other words in each coordinate. For a split of the five coordinates into S and T this asks that every
   word be the only one with its S part or the only one with its T part. programs/alg2.py checks all splits for the
   352 words and finds no violation. The construction is the column replacement of Colbourn and Torres-Jimenez
   (2010) and Colbourn and Zhou (2012), and the condition on the words is that of a 2-frameproof code (Blackburn,
   SIAM J. Discrete Math. 16 (2003) 499-510), also called a separating hash family of type {1,2}. The 352 words
   are their truncated polynomial code.

3. Why the 352 could not be extended. The 352 words hold one word for every (c, x, y), so a new word always repeats
   some (c, x, y) and some (a, b) pair, and the condition fails.

4. The new code. Write a word as (t, t + u, t + v, x, y) with t, u, v in Z11, so a slab (x, y) holds the 11 words of
   a point (u, v). Two points lie on a common line of a class when they share u, share v, or share v - u. The
   splits force three rules. Points of slabs that share x or share y never share a class line. In a slab with two
   or more points, each point shares no class line with any other point. All points are distinct. One point per
   slab gives back 352 words. Slab (0, 0) with the three points (0, 0), (1, 2), (2, 1) and one point in each of the
   other 31 slabs gives 34 points and 374 words. programs/qmodel.py places the 31 points by one call to CaDiCaL 1.5.3
   (python-sat 1.9.dev22) on the three rules and writes the array.

The arrays were checked exactly with ca_verify on all sets of three columns (8,649,124 for k = 374, 7,647,059 for
k = 359), and again by an independent bitmask count.

Built from: the table's own CA(49;3,352,2), whose row blocks are reused as pattern tables. No array of
Torres-Jimenez is an ingredient or start.

Program: programs/recipe.sh copies table/arrays/CA_49_3_352_2.txt, runs programs/alg2.py and programs/qmodel.py with
the argument 3 (the number of points in slab (0, 0)), and cuts the first 359 columns. It is deterministic. A
complete run from scratch reproduced both arrays exactly (programs/recipe_log.txt). Needs python 3.13, numpy and
python-sat 1.9.dev22.
