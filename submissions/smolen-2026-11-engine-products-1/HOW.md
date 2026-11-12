# smolen-2026-11-engine-products-1: three product certificates at cited sizes that had no array

Construction: the product of C. J. Colbourn and J. Torres-Jimenez, Profiles of covering arrays of strength two
(2013), Corollary 4.3: from CA(N1; 2, k1, v) and CA(N2; 2, k2, v) with c1 and c2 rows that differ in every column,
a CA(N1 + N2 - (c1 + c2); 2, k1 k2, v). Here one such row is used on each side, so two rows are saved:
CA(138; 2, 504, 7) = OA(49; 2, 8, 7) x CA(91; 2, 63, 7), CA(182; 2, 720, 8) = OA(64; 2, 9, 8) x CA(120; 2, 80, 8)
and CA(232; 2, 990, 9) = OA(81; 2, 10, 9) x CA(153; 2, 99, 9). These three were found by running the table's own
construction laws (tools/derive_table.py) on the table's real arrays only.

Built from: rows of the table only, named by their array_sha256 in each certificate: the Bose orthogonal arrays
and the recursive Bose arrays of submission smolen-2026-11-formula-arrays. No Torres-Jimenez array is used
(the method of his 2013 paper with Colbourn is cited; no array of his).

Program: tools/construction_cert.py (kind product-ctj-1) builds and checks each array from its certificate; the
rows that differ in every column were found with tools/constant_rows. Each built array was also checked exactly
with ca_verify.
