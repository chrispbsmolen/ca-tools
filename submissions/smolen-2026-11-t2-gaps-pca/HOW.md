# How these arrays were built

Construction: the product of C. J. Colbourn and J. Torres-Jimenez, Profiles of covering arrays of strength
two, J. Algorithms Comput. 44 (2013) 31-59, Corollary 4.3, as certificates of the kind `product-ctj-1` of
`tools/construction_cert.py` (theorem and proof in `tools/CONSTRUCTION_CERT.md`), exactly as in
`smolen-2026-11-t2-gaps`. Each row here is the product of one small array and the PCA array
CA(341; 2, 1705, 11), so N = N1 + 341 - (s1 + 1), where s1 is the number of rows of the small array that
differ pairwise in every column and 1 that number for the PCA array.

Built from:

| file | construction | reference | rows that differ pairwise in every column |
|---|---|---|---|
| the table's CA(341; 2, 1705, 11), array_sha256 dddae14c654ca9ffab3b7632f29ff6606676b91bc858c5c7652ad511c79216f6 | product of partitioned covering arrays applied twice to the Bose OA(121; 2, 12, 11) (PCAx2PCA), entered by `smolen-2026-11-t2-pca341` | Colbourn and Torres-Jimenez 2013; Bose 1938 | 1 |
| OA_121_2_12_11.txt | Bose OA(121; 2, 12, 11) | Bose 1938 | 1 |
| CA_156_2_13_11.txt, CA_157_2_14_11.txt | the arrays CA(156; 2, 13, 11) and CA(157; 2, 14, 11), taken from CAs (data CKRS_CAs) | Colbourn, Keri, Rivas Soriano and Schlage-Puchta 2010 | 7 and 5 |
| CA_171_2_17_11.txt to CA_201_2_20_11.txt | the all-zero row and the cyclic shifts of a starter vector under the cyclic group on the 10 nonzero symbols | Meagher and Stevens 2005 (starters as listed in CAs) | 1 |

`programs/make_leaves.py` (standard library only) writes every file above except the two CKRS arrays,
which are `CKRS_CAs[["CA(156;2,13,11)"]]` and `CKRS_CAs[["CA(157;2,14,11)"]]` of CAs 0.24.4 (the data is
0-based already):

    python3 submissions/smolen-2026-11-t2-gaps-pca/programs/make_leaves.py /tmp/leaves

Order of entry. The certificates name the PCA array by its hash, so they pass only once
`smolen-2026-11-t2-pca341` is in the table. On main the table page workflow enters the rows of `claims.csv`
folders before those of `constructions.csv` folders in the same run, so pushing both together works. Before
that entry, `python3 tools/check_constructions.py submissions/smolen-2026-11-t2-gaps-pca --light` fails with
"not the array_sha256 of a counted VERIFIED row". Checked on a copy of the table with that row entered: 7 of 7
pass, and `ca_verify` verified the six rebuilt arrays it could check within two minutes.

| row | ingredients | widths where it lowers the lookup (after `smolen-2026-11-t2-gaps`) | lookup there before / after | CAs productCA, same files / CAs's own arrays |
|---|---|---|---|---|
| CA(460; 2, 20460, 11) | OA 121@12 x PCA 341@1705 | 20,450-20,460 | 468 / 460 | 460 / 460 |
| CA(489; 2, 22165, 11) | CKRS 156@13 x PCA 341@1705 | 22,023-22,165 | 492 / 489 | 489 / 489 |
| CA(492; 2, 23870, 11) | CKRS 157@14 x PCA 341@1705 | 22,177-23,870 | 497 / 492 | 492 / 492 |
| CA(510; 2, 28985, 11) | MS 171@17 x PCA 341@1705 | 27,649-28,985 | 511 and 517 / 510 | 510 / 510 |
| CA(520; 2, 30690, 11) | MS 181@18 x PCA 341@1705 | 29,173-30,690 | 521 and 527 / 520 | 520 / 520 |
| CA(530; 2, 32395, 11) | MS 191@19 x PCA 341@1705 | 30,889-32,395 | 531, 533 and 538 / 530 | 530 / 530 |
| CA(540; 2, 34100, 11) | MS 201@20 x PCA 341@1705 | 32,605-34,100 | 543 / 540 | 540 / 540 |

Together they lower the lookup at 7,706 more widths, by up to 8 rows. Six rows of `smolen-2026-11-t2-gaps`
(CA(460; 2, 20449, 11), CA(492; 2, 22176, 11), CA(511; 2, 28314, 11), CA(521; 2, 29887, 11), CA(531; 2, 31460,
11) and CA(533; 2, 32032, 11)) are then no longer steps of the frame; they stay in the table as rows. If this
folder does not pass, the rows of `smolen-2026-11-t2-gaps` stand alone.

CAs's `pcaCA` gives 531 rows at every width up to 35,805 with one starter vector of the CAs data
`LCDSTStarters` (16 columns, one fixed symbol; Colbourn's table labels CA(161; 2, 16, 11) "Fix 1 symbols
(Colbourn)"). Its origin is not traced here; it is left to the maintainer and not used. After this folder the
table is above that from 32,396 to 35,805 columns (538, 540 and 543: by 7 to 12 rows).

Credit: Colbourn and Torres-Jimenez 2013 (the product, and the PCA product); Bose 1938; Colbourn, Keri, Rivas
Soriano and Schlage-Puchta 2010 (the arrays CA(156; 2, 13, 11) and CA(157; 2, 14, 11)); Meagher and Stevens
2005 (the starters); U. Groemping's R package CAs (the data of the CKRS arrays and of the starters, and
`productCA`, which gives the same sizes).
