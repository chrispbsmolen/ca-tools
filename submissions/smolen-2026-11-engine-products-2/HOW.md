# smolen-2026-11-engine-products-2: 28 strength-2 arrays from products of real arrays

Each array has the size of the best known value the table cites for it, and the table had no array anyone could
download at that size. They were found by trying every product of two real arrays (the table's own arrays and
the construction functions of CAs) and keeping the products that reach a cited best known value.

Construction, one per array, named in claims.csv:
- the PCA product (cut and paste) of Colbourn, Martirosyan, Mullen, Shasha, Sherwood and Yucas (2006), Theorem 3.2,
  in the form of Colbourn and Torres-Jimenez (2013): a PCA(N1; 2, (k1, k2), v) and a PCA(N2; 2, (l1, l2), v) give
  a CA(N1 + N2 - v; 2, k1 l1 + k1 l2 + k2 l1, v) (11 arrays);
- the generalized direct product of Colbourn and Torres-Jimenez (2013), Corollary 4.3: CA(N1; 2, k1, v) and
  CA(N2; 2, k2, v) with c1 and c2 rows that differ in every column give a CA(N1 + N2 - min(v, c1 + c2); 2, k1 k2, v)
  (7 arrays);
- a construction function of CAs used directly, for alphabets 11 to 13 (10 arrays: cover starters of Meagher and
  Stevens and of Colbourn et al. 2006, the fusion construction of Colbourn, Keri, Rivas Soriano and
  Schlage-Puchta, the projection of a Bose orthogonal array, the recursive Bose construction).
Columns 1 to k of each product are kept.

Built from: Bose orthogonal arrays (CAs::SCA_Bose), construction functions of the R package CAs 0.24.4 by Ulrike
Groemping (constructions only; no stored catalogue of CAs is used), and four strength-2 ternary arrays of this
table built by C. Smolen (CA_18_2_52_3.txt, CA_24_2_209_3.txt, CA_27_2_436_3.txt, CA_33_2_2637_3.txt). No array
of Torres-Jimenez is an ingredient (the method of his 2013 paper with Colbourn is cited; no array of his).

Program: programs/build.R with the recipes in programs/recipes.csv. From this folder:

    Rscript programs/build.R programs/recipes.csv rebuilt ../../table/arrays

rebuilds all 28 files; two rebuilds were identical, file for file. Each array was checked exactly with ca_verify
on all column pairs.
