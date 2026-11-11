# How these arrays were built

Construction: profile products of the table's CA(18; 2, 52, 3) with five of our own arrays, each followed by
column extension.

CA(31; 2, 1252, 3), CA(33; 2, 2637, 3), CA(35; 2, 3355, 3), CA(36; 2, 4914, 3) and CA(37; 2, 5730, 3).

Step 1, the product. The profile product (the method of Colbourn and Torres-Jimenez 2013, "Profiles of covering
arrays of strength two", Thm 4.2 / Cor 4.5. No array of theirs is used) takes an array A with N rows and k columns
and an array B with M rows and l columns. If two rows of A agree in d1 columns and two rows of B agree in d2
columns, the product has N + M - 3 rows and k x l - d1 x d2 columns. A is always the table's CA(18; 2, 52, 3) of
submission smolen-2026-11-t2v3-z3z3-18rows, rows 0 and 1, which agree in 13 columns. There is no search in this
step. Program programs/pprod.py.

| rows | B | rows of B | d2 | product columns |
|---|---|---|---|---|
| 31 | the table's CA(16; 2, 21, 3) | 0 and 8 | 2 | 1066 |
| 33 | A itself | 0 and 1 | 13 | 2535 |
| 35 | our CA(20; 2, 61, 3) | 0 and 3 | 13 | 3003 |
| 36 | the table's CA(21; 2, 93, 3) | 14 and 20 | 21 | 4563 |
| 37 | the table's CA(22; 2, 107, 3) | 15 and 16 | 24 | 5252 |

Step 2, column extension. Program programs/ext2t.c adds one column at a time at a fixed number of rows and saves
the array after each added column. Each new column starts as the best of 200 random columns. Simulated annealing
with exact counts on all column pairs then repairs it, and only the new column may change (temperature 0.7,
seed 13). A column that stays stuck for 200000 moves is thrown away and drawn again. Each run was left until no
column had been added for 10 to 15 minutes, and the array taken is the last one saved.

| rows | columns | saved at move |
|---|---|---|
| 31 | 1252 | 52,664,081 |
| 33 | 2637 | 10,840,043 |
| 35 | 3355 | 8,760,971 |
| 36 | 4914 | 4,930,914 |
| 37 | 5730 | 4,793,497 |

The first columns of each array are exactly the product of step 1.

Each array was checked exactly with ca_verify on all pairs of columns.

Replication. programs/recipe_ext.sh builds each array from the ingredient files and writes the recipe log itself,
with the sha256 of every program, input and output. The extension is stopped on a count (the array saved at the
stated number of columns). Its seconds argument is only an abort limit. Each array was built twice on Linux
x86_64, once by hand and once by the recipe script, and the two files are identical, saved at the same move
number. The details and one correction to the script are in programs/REPLAY.md.

Built from: the table's CA(18; 2, 52, 3), CA(16; 2, 21, 3), CA(21; 2, 93, 3) and CA(22; 2, 107, 3), and our
CA(20; 2, 61, 3). Copies of all five are in programs/. No array of Torres-Jimenez is an ingredient or start.

Program: programs/ in this folder (recipe_ext.sh, pprod.py, ext2t.c and the five ingredient arrays). The programs
were written by AI models for this project.

To rebuild one array, for example the 33-row one:
    cd programs && bash recipe_ext.sh mytag 33
which runs
    python3 pprod.py CA_18_2_52_3.txt 0 1 CA_18_2_52_3.txt 0 1 p33_2535.txt
    cc -O3 -o ext2t ext2t.c -lm
    ./ext2t p33_2535.txt 33 2535 0 0 13 1000000 0.7 out/t33 -chain 900 -ntry 200 -kick 200000
and stops the last command once out/t33_33_2637.txt has been saved. The value after -chain must stay as written
in the script (600 at 31 rows, 900 at 33 and 35, 1500 at 36 and 37), because it enters the search path. Each
array takes 20 to 30 minutes on one core. The 37-row run needs about 1.7 GB of memory.
