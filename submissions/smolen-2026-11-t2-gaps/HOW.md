# How these arrays were built

Construction: the product of C. J. Colbourn and J. Torres-Jimenez, Profiles of covering arrays of strength
two, J. Algorithms Comput. 44 (2013) 31-59, Corollary 4.3: from a CA(N1; 2, k1, v) with s1 rows that differ
pairwise in every column and a CA(N2; 2, k2, v) with s2 such rows, a CA(N1 + N2 - min(v, s1 + s2); 2, k1 k2, v).
U. Groemping's R package CAs builds it as `productCA`. Each array here is a certificate of the kind
`product-ctj-1` of `tools/construction_cert.py` (theorem and proof in `tools/CONSTRUCTION_CERT.md`). The
certificate names the ingredient files, the rows used as constant rows at every product, and the expected N, k
and hash; the checker proves every hypothesis of the theorem and rebuilds the array. Most rows are products of
three or four arrays: an ingredient in brackets below is itself a product, written inside the certificate and
proved by the same theorem, so only the small arrays at the leaves are checked for coverage (exhaustively, by
the checker).

Built from: small arrays over 11, 23 and 25 symbols, all from published constructions, in this folder:

| file | construction | reference | rows that differ pairwise in every column |
|---|---|---|---|
| OA_121_2_12_11.txt, OA_625_2_26_25.txt | Bose orthogonal array OA(q^2; 2, q+1, q) over GF(q) | Bose 1938 | 1 (q on the first q columns) |
| CA_621_2_26_23.txt, CA_725_2_28_25.txt | Bose OA(625; 2, 26, 25) and OA(729; 2, 28, 27) with two symbols fused, one at a time | Colbourn, Keri, Rivas Soriano and Schlage-Puchta 2010, Lemma 3.1 | 21 and 23 |
| CA_167_2_16_11.txt, CA_623_2_28_23.txt, CA_725_2_32_23.txt, CA_727_2_30_25.txt, CA_837_2_34_25.txt, CA_1017_2_40_25.txt | projection of the Bose OA(q^2; 2, q+1, q) with c = q - v symbols removed: CA(q^2 - c; 2, q + 1 + c, v), q = 13, 25, 27, 27, 29, 32 | Colbourn 2008, Theorem 2.3 (Discrete Math. 308, 772-786) | v (the constant rows of the construction) |
| CA_231_2_143_11.txt | product of two partitioned covering arrays, both the Bose OA(121; 2, 12, 11) (PCAx2PCA) | Colbourn and Torres-Jimenez 2013 | 1 |
| CA_171_2_17_11.txt, CA_181_2_18_11.txt, CA_191_2_19_11.txt, CA_201_2_20_11.txt | the all-zero row and the cyclic shifts of a starter vector under the cyclic group on the 10 nonzero symbols | Meagher and Stevens 2005 (starters as listed in CAs, data MeagherStevensStarters) | 1, or 11 with the last column cut off |
| CA_157_2_14_11.txt | the array CA(157; 2, 14, 11) | Colbourn, Keri, Rivas Soriano and Schlage-Puchta 2010, taken from CAs (data CKRS_CAs) | 5 |

The counts are exact maximum cliques of the graph "two rows differ in every column" (`tools/constant_rows.c`).
Every leaf was checked with `ca_verify` at t = 2, and the checker checks each again exhaustively. No
Torres-Jimenez array, and no array found by search, is an ingredient.

One choice matters for the sizes. Colbourn's projection leaves free which of the replacement symbols each row
gets, and some entries are free altogether. `programs/make_leaves.py` makes these choices so that, besides the
v constant rows of the construction, another set of v rows (rows (1, b) of the Bose array) also differ pairwise
in every column. A product then keeps v such rows for the next product, so every product step saves the full v
rows. With the free entries set to 0, a product of a Bose array and a projection keeps only 1, which costs 23 rows
at CA(1927; 2, 20280, 25) (1950) and at CA(2217; 2, 27040, 25) (2240). The fused arrays fill their free entries cyclically,
as CAs does, which keeps 21 and 23 such rows.

Program, standard library only, from the root of the repository:

    python3 submissions/smolen-2026-11-t2-gaps/programs/make_leaves.py /tmp/leaves

writes every leaf above except CA_157_2_14_11.txt, byte for byte (`LEAVES.csv` lists the sha256 of each).
CA_157_2_14_11.txt is `CKRS_CAs[["CA(157;2,14,11)"]]` of CAs 0.24.4 (the data is 0-based already). Then

    python3 tools/check_constructions.py submissions/smolen-2026-11-t2-gaps --light

checks every certificate and rebuilds every array (about 25 minutes on two cores; the largest array is
CA(2421; 2, 36000, 25), 87 million entries). For the 12 rows of at most 50 MiB as text the check also runs
`ca_verify` on the rebuilt array, and the table stores the array; the other 24 are stored as their
certificates, which rebuild them.

Comparison with CAs. For every row, `productCA` of CAs 0.24.4 on the same ingredient files, nested the same
way, gives the same N (last column, first number). With CAs's own versions of the ingredients
(`fuseBushtCA`, `projBoseCA`, `recBoseCA(type = "PCA")`, `CS_MS`, `ckrsCA`) it gives the same N or more
(second number): its projections keep fewer rows that differ in every column. The scripts and logs are in the
working notes of 2026-11-11, not in this folder.

### v = 11

| row | ingredients (leaves in brackets are nested products) | widths it is best for | frame before there | CAs productCA, same ingredient files / CAs's own arrays |
|---|---|---|---|---|
| CA(460; 2, 20449, 11) | PCA 231@143 x PCA 231@143 | 20,001-20,449 | 451 to 475 | 460 / 460 |
| CA(468; 2, 20592, 11) | OA 121@12 x [OA 121@12 x PCA 231@143] | 20,450-20,592 | 475 | 468 / 468 |
| CA(487; 2, 22022, 11) | CKRS 157@14 x [OA 121@12 (first 11 columns) x PCA 231@143] | 20,593-22,022 | 475 to 519 | 487 / 487 |
| CA(492; 2, 22176, 11) | [OA 121@12 x OA 121@12 (first 11 columns)] x [OA 121@12 x CKRS 157@14] | 22,023-22,176 | 519 | 492 / 492 |
| CA(497; 2, 27456, 11) | OA 121@12 x [proj 167@16 x PCA 231@143] | 22,177-27,456 | 519 to 561 | 497 / 502 |
| CA(506; 2, 27648, 11) | [OA 121@12 x OA 121@12] x [OA 121@12 x proj 167@16] | 27,457-27,648 | 561 | 506 / 508 |
| CA(511; 2, 28314, 11) | PCA 231@143 x [OA 121@12 (first 11 columns) x MS 181@18] | 27,649-28,314 | 561 | 511 / 511 |
| CA(517; 2, 29172, 11) | OA 121@12 x [MS 181@18 (first 17 columns) x PCA 231@143] | 28,315-29,172 | 561 | 517 / 517 |
| CA(521; 2, 29887, 11) | PCA 231@143 x [OA 121@12 (first 11 columns) x MS 191@19] | 29,173-29,887 | 561 | 521 / 521 |
| CA(527; 2, 30888, 11) | OA 121@12 x [MS 191@19 (first 18 columns) x PCA 231@143] | 29,888-30,888 | 561 | 527 / 527 |
| CA(531; 2, 31460, 11) | PCA 231@143 x [OA 121@12 (first 11 columns) x MS 201@20] | 30,889-31,460 | 561 | 531 / 531 |
| CA(533; 2, 32032, 11) | CKRS 157@14 x [proj 167@16 x PCA 231@143] | 31,461-32,032 | 561 | 533 / 533 |
| CA(538; 2, 32604, 11) | OA 121@12 x [PCA 231@143 x MS 191@19] | 32,033-32,604 | 561 | 538 / 538 |
| CA(543; 2, 36864, 11) | [OA 121@12 x proj 167@16] x [OA 121@12 x proj 167@16] | 32,605-36,864 | 561 | 543 / 543 |
| CA(547; 2, 38896, 11) | PCA 231@143 x [proj 167@16 x MS 171@17] | 36,865-38,896 | 561 | 547 / 551 |
| CA(556; 2, 39168, 11) | [OA 121@12 x OA 121@12] x [proj 167@16 x MS 171@17] | 38,897-39,168 | 561 | 556 / 560 |
| CA(557; 2, 41184, 11) | PCA 231@143 x [proj 167@16 x MS 181@18] | 39,169-41,184 | 561 | 557 / 561 |

### v = 23

| row | ingredients (leaves in brackets are nested products) | widths it is best for | frame before there | CAs productCA, same ingredient files / CAs's own arrays |
|---|---|---|---|---|
| CA(1821; 2, 20384, 23) | fused 621@26 x [proj 623@28 x proj 623@28] | 20,001-20,384 | 2047 | 1821 / 1821 |
| CA(1823; 2, 21952, 23) | proj 623@28 x [proj 623@28 x proj 623@28] | 20,385-21,952 | 2047 | 1823 / 1823 |
| CA(1923; 2, 23296, 23) | fused 621@26 x [proj 623@28 x proj 725@32] | 21,953-23,296 | 2047 | 1923 / 1923 |
| CA(1925; 2, 25088, 23) | proj 623@28 x [proj 623@28 x proj 725@32] | 23,297-25,088 | 2047 | 1925 / 1925 |
| CA(2025; 2, 26624, 23) | fused 621@26 x [proj 725@32 x proj 725@32] | 25,089-26,624 | 2047 | 2025 / 2025 |
| CA(2027; 2, 28672, 23) | proj 623@28 x [proj 725@32 x proj 725@32] | 26,625-28,672 | 2047 | 2027 / 2027 |

### v = 25

| row | ingredients (leaves in brackets are nested products) | widths it is best for | frame before there | CAs productCA, same ingredient files / CAs's own arrays |
|---|---|---|---|---|
| CA(1927; 2, 20280, 25) | OA 625@26 x [OA 625@26 x proj 727@30] | 20,001-20,280 | 2425 | 1927 / 1939 |
| CA(2027; 2, 21840, 25) | fused 725@28 x [OA 625@26 x proj 727@30] | 20,281-21,840 | 2425 | 2027 / 2027 |
| CA(2029; 2, 23400, 25) | proj 727@30 x [OA 625@26 x proj 727@30] | 21,841-23,400 | 2425 | 2029 / 2029 |
| CA(2127; 2, 23520, 25) | fused 725@28 x [fused 725@28 x proj 727@30] | 23,401-23,520 | 2425 | 2127 / 2127 |
| CA(2129; 2, 25200, 25) | fused 725@28 x [proj 727@30 x proj 727@30] | 23,521-25,200 | 2425 | 2129 / 2129 |
| CA(2131; 2, 27000, 25) | proj 727@30 x [proj 727@30 x proj 727@30] | 25,201-27,000 | 2425 | 2131 / 2131 |
| CA(2217; 2, 27040, 25) | OA 625@26 x [OA 625@26 x proj 1017@40] | 27,001-27,040 | 2425 | 2217 / 2233 |
| CA(2239; 2, 28560, 25) | fused 725@28 x [proj 727@30 x proj 837@34] | 27,041-28,560 | 2425 | 2239 / 2239 |
| CA(2241; 2, 30600, 25) | proj 727@30 x [proj 727@30 x proj 837@34] | 28,561-30,600 | 2425 | 2241 / 2241 |
| CA(2319; 2, 31200, 25) | proj 1017@40 x [OA 625@26 x proj 727@30] | 30,601-31,200 | 2425 | 2319 / 2319 |
| CA(2349; 2, 32368, 25) | fused 725@28 x [proj 837@34 x proj 837@34] | 31,201-32,368 | 2425 | 2349 / 2349 |
| CA(2351; 2, 34680, 25) | proj 727@30 x [proj 837@34 x proj 837@34] | 32,369-34,680 | 2425 | 2351 / 2351 |
| CA(2421; 2, 36000, 25) | proj 727@30 x [proj 727@30 x proj 1017@40] | 34,681-36,000 | 2425 | 2421 / 2421 |


Why these rows. From 20,001 columns on, the frame gives Arhan Canli's wide rows (Sherwood covering perfect hash
families): CA(561; 2, 100000, 11), CA(2047; 2, 100000, 23), CA(2425; 2, 100000, 25), and at v = 11 also the
products 451, 475 and 519 entered on 2026-11-10. Products of small published arrays are smaller at the narrow
end of that range. Each row above is a step of the stair: the smallest product found for the widths up to its
k, among products of up to four of the leaves (exact constant-row counts at every node). Together they lower
the lookup at 20,701 widths at v = 11 (by up to 64 rows), 8,672 at v = 23 (by up to 226) and 16,000 at
v = 25 (by up to 498).

What is left.

- v = 11: from 41,185 columns on the frame (561) is as small as these products. Products with the table's
  CITED rows (Colbourn's tables, some built on Torres-Jimenez search arrays) go lower up to 47,740 columns.
  CAs's `pcaCA` gives 531 rows at every width up to 35,805. It needs one starter vector of the CAs data
  `LCDSTStarters` (16 columns, one fixed symbol, giving CA(161; 2, 16, 11); Colbourn's table labels that
  size "Fix 1 symbols (Colbourn)"). That is below these rows from 31,461 to 35,805 columns (533, 538 and 543:
  by 2 to 12 rows). The origin of that vector is not traced here, so it is left to the maintainer and not
  used. The folder `smolen-2026-11-t2-gaps-pca` lowers
  several of these rows further with the PCA array CA(341; 2, 1705, 11) of `smolen-2026-11-t2-pca341`.
  Once it enters, six rows above (460@20449, 492@22176, 511@28314, 521@29887, 531@31460 and 533@32032) are
  no longer steps of the frame; they stay in the table as rows, and they stand alone if that folder fails.
- v = 23 and v = 25: from 28,673 and 36,001 columns on, these products are not below 2047 and 2425.
- Above a size rule. `tools/consistency.py` will flag 25 of these rows (13 at v = 11, 4 at v = 23, 8 at
  v = 25) as above a DP2 line of `table/derived.csv`, by 1 to 52 rows. Those lines multiply CITED sizes of
  Colbourn's tables whose arrays the table does not hold, mostly simulated annealing and post-optimised rows of
  Torres-Jimenez and "Direct product generalized" rows whose recipes are not traced. The rows still count; the
  maintainer decides whether to list them in `table/above_rule_rows.csv`.
- v = 9: no row. The frame gives CA(369; 2, 59049, 9) from 20,001 columns on. A product below 369 there needs,
  for example, PCA CA(225; 2, 981, 9) times an array of at least 21 columns and at most 152 rows. The only such
  arrays known over 9 symbols are ones the table has only as CITED sizes, with no array: "Brick by Brick
  (TATA)" CA(126; 2, 22, 9), and the Torres-Jimenez simulated annealing arrays CA(142; 2, 23, 9) to
  CA(152; 2, 31, 9). The table does not use either as an ingredient. The
  published constructions give at least 169 rows at 21 columns over 9 symbols (Meagher-Stevens starters stop at
  20 columns, 161 rows; the next projection is CA(249; 2, 24, 9)). A search over all products of up to four
  of the clean arrays (Bose OA(81; 2, 10, 9), its 9-column cut, Meagher-Stevens 105 to 161 rows at 13 to 20
  columns, the projections, fused arrays, PCA CA(153; 2, 99, 9) and CA(225; 2, 981, 9)), even assuming every
  array and every product keeps 9 rows that differ in every column, gives at best 369: a tie, not a gain.
  CAs's own catalogue functions agree (`pcaCA` and `recBoseCA(type = "PCA")` 369, `dpCA` 393). Only the
  LCDST starter CA(142; 2, 21, 9) of CAs (three fixed symbols) would give a gain: CA(364; 2, 20601, 9), 5
  rows on 601 widths. It is left to the maintainer like the v = 11 starter.

Credit: Colbourn and Torres-Jimenez 2013 (the product); Bose 1938; Colbourn 2008 (projection); Colbourn, Keri,
Rivas Soriano and Schlage-Puchta 2010 (fusing, and the array CA(157; 2, 14, 11)); Meagher and Stevens 2005 (the
starters); U. Groemping's R package CAs (the data of the CKRS array and of the starters, and `productCA`, which
gives the same sizes).
