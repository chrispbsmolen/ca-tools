# How these arrays were built

Construction: partial Roux doubling of a Power CT array. Exact, with no search.

CA(59; 3, 1333, 2) and CA(60; 3, 1334, 2).

Start from the table's CA(55; 3, 1331, 2). Write s of its columns a second time, so that each of them has a twin.
A triple of columns that contains a column and its twin is not covered by the 55 rows, because the two always
agree there. Add r helper rows in which each twinned column and its twin are complementary, and the helper entries
of the twinned columns together with one more vector, shared by all other columns, form a strength-2 family on r
rows (one zero row plus a subset of size floor((r-1)/2)+1 of the other r-1 rows). With r helper rows the recipe
doubles up to C(r-1, floor((r-1)/2)+1) - 1 columns. That is 2 columns for r = 4 and 3 columns for r = 5. It is the
first step of submissions/smolen-2026-11-t3-partial-doubling with fewer helper rows, and at full width it is the
Roux doubling.

- CA(59; 3, 1333, 2). 4 helper rows, 2 columns doubled.
- CA(60; 3, 1334, 2). 5 helper rows, 3 columns doubled.

Both arrays were checked exactly with ca_verify on all column triples (393,877,506 and 394,765,284).

Built from: the table's own CA(55; 3, 1331, 2) (table/arrays/CA_55_3_1331_2.txt) only. No array of
Torres-Jimenez is an ingredient or start.

Program: programs/pdgen.py in this folder.

To rebuild (the program uses no random numbers, so the files come out identical every time):
    python3 programs/pdgen.py CA_55_3_1331_2.txt 4 CA_59_3_1333_2.txt
    python3 programs/pdgen.py CA_55_3_1331_2.txt 5 CA_60_3_1334_2.txt
