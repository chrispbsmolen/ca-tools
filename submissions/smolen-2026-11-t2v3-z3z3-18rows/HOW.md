# How these arrays were built

Construction: an 18-row array found by exhaustive search among arrays invariant under the group Z3 x Z3 acting on
the rows, and two arrays made from it by the profile product.

CA(18; 2, 52, 3), CA(30; 2, 975, 3) and CA(24; 2, 209, 3).

1. CA(18; 2, 52, 3). The group Z3 x Z3 has four subgroups of order 3. Take three of them, and for each take two
   copies of its three cosets. That gives 18 rows in six orbits of 3, and the group permutes the rows. Applying a
   group element to a column gives another column. A column whose 9 images are pairwise qualitatively independent
   (every pair of them shows all 9 symbol pairs) is kept, one per orbit and up to renaming of symbols. There are
   90,720 such orbits among 62,681,346 candidate columns. Two orbits are joined when every column of one is
   qualitatively independent of every column of the other. Four mutually joined orbits are a covering array with
   18 rows and 36 columns. The program lists all such sets of four up to the normaliser of the group. There are
   27 in the order used, and no set of five exists. For each set of four the program lists every further column
   that is qualitatively independent of all 36 columns, and finds the largest set of such columns that are
   independent of one another. 16 of the sets take 1 further column, 9 take 4, and 2 take 16. The array here is
   the first set that takes 16, which gives 36 + 16 = 52 columns. The search is exhaustive and uses no random
   numbers. Programs programs/mkgrp.py (the group as row permutations) and programs/orbq7.c (the search).

2. CA(30; 2, 975, 3). Profile product (the method of Colbourn and Torres-Jimenez 2013, "Profiles of covering
   arrays of strength two", Thm 4.2 / Cor 4.5. No array of theirs is used). A is the 18-row array above, rows 0 and
   1, which agree in 13 columns. B is the table's CA(15; 2, 20, 3), rows 0 and 3, which agree in 5 columns. The
   product has 18 + 15 - 3 = 30 rows and 52 x 20 - 13 x 5 = 975 columns. There is no search in this step. Program
   programs/pprod.py.

3. CA(24; 2, 209, 3). The same product with B the orthogonal array OA(9, 4, 3) whose rows are (i, j, i+j, i+2j)
   mod 3, rows 0 and 1, which agree in 1 column. It has 18 + 9 - 3 = 24 rows and 52 x 4 - 13 = 195 columns. Then
   column extension at 24 rows. Program programs/ext2t.c adds one column at a time and saves the array after each
   added column. Each new column starts as the best of 200 random columns. Simulated annealing with exact counts
   on all column pairs then repairs it, and only the new column may change (temperature 0.7, seed 13). A column
   that stays stuck for 200000 moves is thrown away and drawn again. The array saved after the 14th added column
   has 209 columns and is the array of this submission. It was saved at move 19,751,928 of the run. The first
   195 columns are exactly the product.

Each array was checked exactly with ca_verify on all pairs of columns, and with the separate brute force check
programs/chk.py.

Replication. One script, programs/recipe_item123.sh, builds all three arrays from nothing and writes the recipe
log itself, with the sha256 of every program, input and output. It was run twice in separate new folders on
Linux x86_64. Both runs gave identical files, and these are the files of this submission. The logs are
programs/RECIPE_build.log and programs/RECIPE_replay.log. The extension step is stopped on a count (the array
saved at 209 columns). Its seconds argument is only an abort limit.

Built from: the table's CA(15; 2, 20, 3) and the orthogonal array OA(9, 4, 3) written above. The 18-row array has
no input array. No array of Torres-Jimenez is an ingredient or start, and no array here has the fingerprint of
one of his arrays.

Program: programs/ in this folder (recipe_item123.sh, mkgrp.py, orbq7.c, pprod.py, ext2t.c, chk.py, and the
ingredient CA_15_2_20_3_fd13075b.txt). The search program orbq7.c was written by an AI model for this project.

To rebuild:
    cd programs && bash recipe_item123.sh mytag
which runs
    python3 mkgrp.py z3z3 a,a,b,b,c,c 0 > z_18_aabbcc_f0.txt
    cc -O3 -o orbq7 orbq7.c && ./orbq7 z_18_aabbcc_f0.txt 4 20 w18
    python3 pprod.py CA_18_2_52_3.txt 0 1 CA_15_2_20_3_fd13075b.txt 0 3 CA_30_2_975_3.txt
    python3 pprod.py CA_18_2_52_3.txt 0 1 oa9.txt 0 1 p24_195.txt
    cc -O3 -o ext2t ext2t.c -lm
    ./ext2t p24_195.txt 24 195 0 0 13 100000 0.7 out/t24a -chain 30 -ntry 200 -kick 200000
and stops the last command once out/t24a_24_209.txt has been saved. The whole script takes about four minutes
on one core. The value after -chain must stay 30, because it enters the search path.
