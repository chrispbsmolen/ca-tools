# smolen-2026-11-formula-arrays: 42 arrays from published constructions

Each array has the size of the best known value the table cites for it, and the table had no array anyone could
download at that size. All 42 are in the range most used in testing (strength 2 to 6, small alphabets).

Construction: published constructions only, one per array, named in claims.csv:
- Chateauneuf-Kreher doubling (8), with strength-3 and strength-2 ingredients that are themselves formula arrays
  (Paley, Kleitman-Spencer, Power CT, Bush; full factorials for the smallest);
- the Chateauneuf-Colbourn-Kreher starter construction (3);
- cyclotomy (10) and the Paley construction (6);
- the recursive Bose construction of Colbourn, Martirosyan, Mullen, Shasha, Sherwood and Yucas (11);
- the PCA product (1) and the projection of a Bose orthogonal array (1);
- orthogonal arrays of index one, all words plus a sum column (2).
No stored array of any author is an ingredient or a start. In particular no data object of the CAs package
(TJ2level_CAs, CAEX_CAs, TJcat and the other catalogues) is used, and every array passed the fingerprint screen
against table/tj_fingerprints.csv and the withdrawn files.

Built from: nothing but the formulas; the ingredients of the doubling are built by the same formulas.

Program: programs/build.R. It uses the R package CAs 0.24.4 by Ulrike Groemping (CRAN), its construction functions
only, and fills any open entry with set.seed(20261112). From this folder:

    Rscript programs/build.R claims.csv rebuilt

rebuilds all 42 files; the rebuild was compared with the stored files and is identical, file for file.
Each array was checked exactly with ca_verify on all t-sets of columns.
