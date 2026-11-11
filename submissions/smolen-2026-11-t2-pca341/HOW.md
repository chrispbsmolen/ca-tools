# How this array was built

Construction: the product of partitioned covering arrays of C. J. Colbourn and J. Torres-Jimenez, Profiles of
covering arrays of strength two, J. Algorithms Comput. 44 (2013) 31-59 (a generalization of the direct product
of Colbourn, Martirosyan, Mullen, Shasha, Sherwood and Yucas 2006), applied twice to the Bose array. This is
the table's CITED row t2-v11-k1705-1, "PCAx2PCA", CA(341; 2, 1705, 11), built here with own code.

Built from: only the Bose array OA(121; 2, 12, 11) (Bose 1938), made by the program. No stored array goes in.

A partitioned covering array has v rows P that differ pairwise in every one of its first k1 columns. The
product of two of them, D1 (N rows, k columns, k1 of them partitioned) and D2 (M, l, l1), has the columns
(i, j) with i < k1 or j < l1, so k l1 + k1 (l - l1) columns, and N + M - v rows: the v rows of P (row r
reads D1[r][i] where j < l1 and D2[r][j] otherwise), the other rows of D1 (reading D1[x][i]) and the other
rows of D2 (reading D2[y][j]). The Bose OA(121; 2, 12, 11) is a PCA with its first 11 rows (the rows that
read b in the first 11 columns) and k1 = 11. Twice:

| step | array | columns | rows |
|---|---|---|---|
| 1 | OA x OA | 12 x 11 + 11 x 1 = 143 | 121 + 121 - 11 = 231 |
| 2 | (step 1) x OA | 143 x 11 + 132 x 1 = 1705 (132 of the 143 columns partitioned) | 231 + 121 - 11 = 341 |

After step 1 the new P is the first 11 rows that come from the first ingredient and are not in the old P;
the columns in which they show 11 distinct symbols (132 of 143) are the partitioned ones and are put first,
with the symbols exchanged so that row r of P reads r. The program (`pca_product`, `pca_status` and `pca` in
`programs/make_leaves.py`) makes exactly these choices.

Program, standard library only:

    python3 submissions/smolen-2026-11-t2-pca341/programs/make_leaves.py /tmp/out CA_341_2_1705_11.txt

It writes `CA_341_2_1705_11.txt` with sha256 dddae14c654ca9ffab3b7632f29ff6606676b91bc858c5c7652ad511c79216f6,
the file here. `ca_verify` (repository root) at t = 2, v = 11 verified it on every pair of columns on
2026-11-11 (1,452,660 pairs). `tools/constant_rows.c` finds 1 constant row (rows pairwise different in every
column) in the whole array.

Why. The array is the same size as Colbourn's CITED row, so the frame does not change when it enters. It is
entered so that `product-ctj-1` certificates can name it by its hash: as the second ingredient of products
with small arrays of 13 to 20 columns it gives CA(489; 2, 22165, 11) to CA(540; 2, 34100, 11) (folder
`smolen-2026-11-t2-gaps-pca`). It is too large to be a file ingredient of a certificate (the exhaustive check
of an ingredient there is limited to 3 x 10^8 entry reads).

Credit: Colbourn and Torres-Jimenez 2013 (the construction), Bose 1938 (the ingredient). U. Groemping's R
package CAs builds an array of the same size with `recBoseCA(2, 1705, 11, type = "PCA")`; it is not the
same array and was not used.
