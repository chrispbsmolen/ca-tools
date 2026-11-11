# How this array was built

Construction: profile product of the table's CA(18; 2, 52, 3) with the table's own CA(11; 2, 5, 3), followed by
column extension.

CA(26; 2, 296, 3).

Step 1, the product. The profile product (the method of Colbourn and Torres-Jimenez 2013, "Profiles of covering
arrays of strength two", Thm 4.2 / Cor 4.5. No array of theirs is used) takes an array A with N rows and k columns
and an array B with M rows and l columns. If two rows of A agree in d1 columns and two rows of B agree in d2
columns, the product has N + M - 3 rows and k x l - d1 x d2 columns. A is the table's CA(18; 2, 52, 3) of submission
smolen-2026-11-t2v3-z3z3-18rows, rows 0 and 1, which agree in 13 columns. B is the table's own CA(11; 2, 5, 3)
(CA_11_2_5_3_c33e3aff.txt), rows 0 and 4, which agree in 1 column. The product has 18 + 11 - 3 = 26 rows and
52 x 5 - 13 x 1 = 247 columns. There is no search in this step. Program programs/pprod.py.

Step 2, column extension. Program programs/ext2t.c adds one column at a time at 26 rows and saves the array after
each added column. Each new column starts as the best of 200 random columns. Simulated annealing with exact counts
on all column pairs then repairs it, and only the new column may change (temperature 0.7, seed 13). A column that
stays stuck for 200000 moves is thrown away and drawn again. The array taken is the one saved at 296 columns, at
move 125,556,965 of the run, about 11 minutes on one core. The first 247 columns are exactly the product of step 1.

Other choices were tried and gave fewer columns in the same time. Rows 0 and 1 of B gave 293 columns with three
seeds. Rows 0 and 2 of A gave 292.

The array was checked exactly with ca_verify on all pairs of columns, and with a separate brute force check.

Replication. programs/recipe.sh builds the array twice from the two table files and writes RECIPE.txt and
REPLAY.log, with the sha256 of every program, input and output. The extension is stopped on a count (the array
saved at 296 columns). Its seconds argument is only an abort limit. Both builds were made on Linux x86_64.

Built from: the table's CA(18; 2, 52, 3) (table/arrays/CA_18_2_52_3.txt) and the table's own CA(11; 2, 5, 3)
(table/arrays/CA_11_2_5_3_c33e3aff.txt). No array of Torres-Jimenez is an ingredient or start.

Program: programs/ in this folder (recipe.sh, pprod.py, ext2t.c). The programs were written by AI models for this
project.

To rebuild, from this folder inside a clone of the repository:
    python3 programs/pprod.py ../../table/arrays/CA_18_2_52_3.txt 0 1 ../../table/arrays/CA_11_2_5_3_c33e3aff.txt 0 4 p26_247.txt
    cc -O3 -o ext2t programs/ext2t.c -lm
    mkdir out && ./ext2t p26_247.txt 26 247 0 0 13 1000000 0.7 out/t26 -chain 80 -ntry 200 -kick 200000
and stop the last command once out/t26_26_296.txt has been saved. The value 80 after -chain must stay as written,
because it enters the search path.
