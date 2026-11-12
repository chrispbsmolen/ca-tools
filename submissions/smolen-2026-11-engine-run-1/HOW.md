# smolen-2026-11-engine-run-1: 13 arrays at cited best known sizes that had no array

Construction: one per array, named in claims.csv. Search results are column extensions at the record number of rows
(the idea of the CA Extender of Torres-Jimenez, Acevedo-Juarez and Avila-George 2021; the annealer is this project's
own casa.c). Products are the PCA product of Colbourn et al. (2006) in the form of Colbourn and Torres-Jimenez (2013),
and their generalized direct product (Corollary 4.3), built with the R package CAs 0.24.4 by Ulrike Groemping.

Built from: real arrays only, named per claim: Bose orthogonal arrays (CAs::SCA_Bose), construction functions of
CAs 0.24.4 (no stored catalogue), arrays of this table built by C. Smolen, and arrays of this same submission.
No array of Torres-Jimenez is an ingredient or a start (his methods are cited, no array of his).

Program: programs/ (casa.c, chain_ext.py when used, build.R with recipes.csv). Per array:
- CA(123; 2, 120, 7): column extension at fixed N by simulated annealing, starting from the PCA product of Bose orthogonal arrays (Colbourn and Torres-Jimenez 2013) at 109 columns; rebuild with `casa 123 2 120 7 1 600 0.5 0.99995 CA_123_2_120_7.txt programs/start_123x120.txt` (seeded, deterministic).
- CA(115; 2, 101, 7): column extension at fixed N by simulated annealing, starting from the PCA product of Bose orthogonal arrays (Colbourn and Torres-Jimenez 2013) at 91 columns; rebuild with `casa 115 2 101 7 1 600 0.5 0.99995 CA_115_2_101_7.txt programs/start_115x101.txt` (seeded, deterministic).
- CA(69; 2, 252, 5): column extension at fixed N by simulated annealing, starting from the PCA product of Bose orthogonal arrays (Colbourn and Torres-Jimenez 2013) at 224 columns; rebuild with `casa 69 2 252 5 1 600 0.5 0.99995 CA_69_2_252_5.txt programs/start_69x252.txt` (seeded, deterministic).
- CA(127; 2, 135, 7): column extension at fixed N by simulated annealing, starting from the PCA product of Bose orthogonal arrays (Colbourn and Torres-Jimenez 2013) at 120 columns; rebuild with `casa 127 2 135 7 1 600 0.5 0.99995 CA_127_2_135_7.txt programs/start_127x135.txt` (seeded, deterministic).
- CA(361; 3, 9, 6): column extension at fixed N by simulated annealing, starting from the fusion of a Bose orthogonal array (Colbourn, Keri, Rivas Soriano and Schlage-Puchta 2010) at 8 columns; rebuild with `casa 361 3 9 6 1 600 0.5 0.99995 CA_361_3_9_6.txt programs/start_361x9.txt` (seeded, deterministic).
- CA(29; 2, 27, 4): column extension at fixed N by simulated annealing, starting from the table array CA_28_2_24_4.txt (recursive Bose construction (product of Bose orthogonal arrays, partitioned form)) at 24 columns; rebuild with `casa 29 2 27 4 1 600 0.5 0.99995 CA_29_2_27_4.txt programs/start_29x27.txt` (seeded, deterministic).
- CA(116; 2, 103, 7): column extension at fixed N by simulated annealing, starting from the PCA product of Bose orthogonal arrays (Colbourn and Torres-Jimenez 2013) at 91 columns; rebuild with `casa 116 2 103 7 1 600 0.5 0.99995 CA_116_2_103_7.txt programs/start_116x103.txt` (seeded, deterministic).
- CA(117; 2, 104, 7): column extension at fixed N by simulated annealing, starting from the PCA product of Bose orthogonal arrays (Colbourn and Torres-Jimenez 2013) at 91 columns; rebuild with `casa 117 2 104 7 1 600 0.5 0.99995 CA_117_2_104_7.txt programs/start_117x104.txt` (seeded, deterministic).
- CA(21; 2, 7, 4): column extension at fixed N by simulated annealing, starting from the cover starter of Meagher and Stevens 2005 at 6 columns; rebuild with `casa 21 2 7 4 1 600 0.5 0.99995 CA_21_2_7_4.txt programs/start_21x7.txt` (seeded, deterministic).
- CA(124; 2, 128, 7): column extension at fixed N by simulated annealing, starting from the PCA product of Bose orthogonal arrays (Colbourn and Torres-Jimenez 2013) at 109 columns; rebuild with `casa 124 2 128 7 1 600 0.5 0.99995 CA_124_2_128_7.txt programs/start_124x128.txt` (seeded, deterministic).
- CA(118; 2, 108, 7): column extension at fixed N by simulated annealing, starting from the PCA product of Bose orthogonal arrays (Colbourn and Torres-Jimenez 2013) at 91 columns; rebuild with `casa 118 2 108 7 1 600 0.5 0.99995 CA_118_2_108_7.txt programs/start_118x108.txt` (seeded, deterministic).
- CA(119; 2, 109, 7): column extension at fixed N by simulated annealing, starting from the PCA product of Bose orthogonal arrays (Colbourn and Torres-Jimenez 2013) at 91 columns; rebuild with `casa 119 2 109 7 1 600 0.5 0.99995 CA_119_2_109_7.txt programs/start_119x109.txt` (seeded, deterministic).
- CA(100; 3, 10, 4): column extension at fixed N by simulated annealing, starting from the table array CA_88_3_8_4.txt (Chateauneuf-Colbourn-Kreher construction from a starter (CK_NRB)) at 8 columns; rebuild with `casa 100 3 10 4 1 600 0.5 0.99995 CA_100_3_10_4.txt programs/start_100x10.txt` (seeded, deterministic).

Each array was checked exactly with ca_verify on all t-sets of columns.
