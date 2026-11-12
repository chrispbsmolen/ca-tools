# How this array was built

Construction: profile product of our CA(17; 2, 29, 3) with OA(9, 4, 3), followed by column extension, and at the
end one column replaced by two after an exhaustive list of the columns that fit.

CA(23; 2, 138, 3).

Step 1, the product. The profile product (the method of Colbourn and Torres-Jimenez 2013, "Profiles of covering
arrays of strength two", Thm 4.2 / Cor 4.5. No array of theirs is used) takes an array A with N rows and k columns
and an array B with M rows and l columns. If two rows of A agree in d1 columns and two rows of B agree in d2
columns, the product has N + M - 3 rows and k x l - d1 x d2 columns. A is our CA(17; 2, 29, 3)
(programs/CA_17_2_29_3_16af2149.txt), rows 7 and 16, which agree in 6 columns. B is the orthogonal array OA(9, 4, 3)
with rows (i, j, i+j, i+2j) mod 3 (programs/OA_9_2_4_3.txt), rows 0 and 1, which agree in 1 column. The product has
17 + 9 - 3 = 23 rows and 29 x 4 - 6 x 1 = 110 columns. There is no search in this step. Program programs/pprod.py.

Step 2, column extension with the rows of B free. Program programs/ext2t.c adds one column at a time at 23 rows and
saves the array after each added column. Each new column starts as the best of 200 random columns. Simulated
annealing with exact counts on all column pairs then repairs it. The new column may change, and so may the 8 rows
that come from B (rows 15 to 22, counting from 0) in every column. Temperature 0.65, seed 2003. A column that stays
stuck for 200000 moves is thrown away and drawn again. The array saved at 136 columns, at move 402,147,672, is kept.

Step 3, the same program with all 23 rows free, temperature 0.40, seed 2003. The array saved at 137 columns, at move
12,900,846, is kept. A 138th column was not found this way. Of 75 such runs with different seeds, 29 ended one
uncovered pair short at 138 columns.

Step 4, exact. Program programs/drop1.c takes the array with 137 columns. For each column in turn it removes that
column and lists every column that is qualitatively independent of all 136 remaining columns. A column is one
exactly when each of its three classes of rows meets every class of every remaining column, and one subset-sum
transform over the 2^23 sets of rows decides this for all columns at once, so the list is complete. With column 48
removed (counting from 0) there are exactly 3 such columns, and two of them are qualitatively independent of each
other. The array is the 136 remaining columns followed by those two. Of 26 arrays with 137 columns that were
examined in this way, this was the only one with such a column.

The array takes no 139th column, and the same step applied to it gives nothing. Both were checked with the same
exhaustive lists.

The array was checked exactly with ca_verify on all pairs of columns, and with a separate brute force check.

Replication. programs/recipe.sh builds the array twice from the two ingredient files and writes RECIPE.txt and
REPLAY.log, with the sha256 of every program, input and output. Each extension run is stopped on a count (the array
saved at the stated number of columns). Its seconds argument is only an abort limit. The array was first built on
macOS arm64 and then twice by the recipe script on Linux x86_64. All three files are identical.

Built from: our CA(17; 2, 29, 3) and OA(9, 4, 3), both in programs/. The 17-row array was built in this project on
2026-10-30 by simulated annealing with column extension from a random start (the ext2 program, 17 rows, seed 20103).
No array of Torres-Jimenez is an ingredient or start.

Program: programs/ in this folder (recipe.sh, pprod.py, ext2t.c, drop1.c and the two ingredient arrays). The
programs were written by AI models for this project.

To rebuild:
    bash programs/recipe.sh
which runs the commands listed in RECIPE.txt. About 15 minutes per build on one core.
