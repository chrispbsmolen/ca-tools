# smolen-2026-11-cae-run-2: 30 arrays at cited best known sizes that had no array

Construction: one per array, named in claims.csv and below. Constructions are published theorems (references in
builds_on); searches are column extension at the record number of rows (the idea of the CA Extender of
Torres-Jimenez, Acevedo-Juarez and Avila-George 2021) with this project's own annealer casa.c.

Built from: real arrays only: arrays of this table (named by file), table certificates and constructions, Bose
orthogonal arrays and construction functions of the R package CAs 0.24.4 by Ulrike Groemping (constructions; where a
CAs function uses stored data of other authors, claims.csv names them), and arrays of this same submission.
No array of Torres-Jimenez is an ingredient or a start (his methods are cited, no array of his).

Program: programs/ (build.py with laws.py and recipes.json for constructions; build.R with recipes.csv for PCA
products; casa.c and chain_ext.py with the start files for searches). Per array:
- CA(100000; 5, 6, 10): composition of alphabets, CKRS 2010 (3) of [binary weight-class array, weights [0, 2, 4, 6] on 6 columns; table array CA_3125_5_6_5.txt (Dwyer CA_Database source code "OA" (Aaron Dwyer's abbreviation for the method; many of his)] {'v1': 2}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(10000; 4, 5, 10): composition of alphabets, CKRS 2010 (3) of [binary weight-class array, weights [0, 2, 4] on 5 columns; table array CA_625_4_6_5.txt (Dwyer CA_Database source code "OA" (Aaron Dwyer's abbreviation for the method; many of his)] {'v1': 2}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(1000; 3, 4, 10): composition of alphabets, CKRS 2010 (3) of [table array CA_8_3_4_2.txt (Chateauneuf-Kreher doubling: a strength-3 array on ceil(k/2) columns doubled with a streng); table array CA_125_3_6_5.txt (Dwyer CA_Database source code "OA" (Aaron Dwyer's abbreviation for the method; many of his)] {'v1': 2}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(1100; 3, 6, 10): CAs 0.24.4 construction CKRS (CAs:::labelToCode("CKRS", 3, 6, 10)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(1215; 3, 10, 10): ordered design plus binary patches, Cohen-Colbourn-Ling 2008 Construction 1 of [table array CA_12_3_11_2.txt (Paley construction from the quadratic residues of GF(q))]. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(121; 2, 12, 11): CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 2, 12, 11)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(1331; 3, 12, 11): CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 3, 12, 11)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(1377; 3, 20, 9): Chateauneuf-Kreher doubling of [table array CA_729_3_10_9.txt (Dwyer CA_Database source code "OA" (Aaron Dwyer's abbreviation for the method; many of his); table array CA_81_2_10_9.txt (Dwyer CA_Database source code "OA" (Aaron Dwyer's abbreviation for the method; many of his)]. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(1457; 3, 91, 9): Raaphorst-Moura-Stevens array CA(1457; 3, 91, 9). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(14641; 4, 12, 11): Bush / Bose orthogonal array OA(11^4; 4, 12, 11). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(161051; 5, 12, 11): Bush / Bose orthogonal array OA(11^5; 5, 12, 11). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(169; 2, 14, 13): CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 2, 14, 13)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(2046; 3, 11, 12): ordered design plus binary patches, Cohen-Colbourn-Ling 2008 Construction 1 of [table array CA_12_3_11_2.txt (Paley construction from the quadratic residues of GF(q))]. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(20736; 4, 5, 12): composition of alphabets, CKRS 2010 (3) of [binary weight-class array, weights [0, 2, 4] on 5 columns; table array CA_1296_4_5_6.txt (Orthogonal array of index one: all v^t words of length t plus their sum mod v as an extra )] {'v1': 2}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(2197; 3, 14, 13): CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 3, 14, 13)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(248832; 5, 6, 12): composition of alphabets, CKRS 2010 (3) of [binary weight-class array, weights [0, 2, 4, 6] on 6 columns; composition of alphabets, CKRS 2010 (3) of [binary weight-class array, weights [0, 2, 4, 6] on 6 columns; table array CA_243_5_6_3.txt (Dwyer CA_Database source code "DeMu+" (Aaron Dwyer's abbreviation for the method; many of )] {'v1': 2}] {'v1': 2}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(2541; 3, 24, 11): Chateauneuf-Kreher doubling of [CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 3, 12, 11)); CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 2, 12, 11))]. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(2659; 3, 133, 10): fusing symbols, CKRS 2010 Lemma 3.1 of [Raaphorst-Moura-Stevens array CA(2661; 3, 133, 11)] {'from_v': 11}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(2661; 3, 133, 11): Raaphorst-Moura-Stevens array CA(2661; 3, 133, 11). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(324; 2, 226, 12): frozen-core extension of PCA/direct product DP(CAs projBoseCA, CAs projBoseCA) (CAs productPCA/productCA) (324 rows, 225 columns): base fixed, 0 free rows and 1 free columns annealed (own extv.c, T 1.5). Rebuild: `extv 2 12 programs/start_CA_324_2_226_12.txt 324 225 0 1 1 20 1.5 CA_324_2_226_12.txt` (seeded, deterministic).
- CA(325; 2, 195, 13): CAs 0.24.4 construction recBoseCA_PCA (CAs:::labelToCode("recBoseCA_PCA", 2, 195, 13)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(336; 2, 196, 13): CAs 0.24.4 construction recBoseCA_CA (CAs:::labelToCode("recBoseCA_CA", 2, 196, 13)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(350; 2, 1716, 11): product of Colbourn and Torres-Jimenez 2013 Cor 4.3 (rows differing in every column removed) of [CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 2, 12, 11)); table array CA_231_2_143_11.txt (Recursive Bose construction, partitioned form (Colbourn et al. 2006))] {'s': 1, 'r': 1}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(3559; 3, 134, 10): one column added, CKRS 2010 Thm 3.2 of [fusing symbols, CKRS 2010 Lemma 3.1 of [Raaphorst-Moura-Stevens array CA(2661; 3, 133, 11)] {'from_v': 11}]. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(3610; 3, 362, 10): CAs 0.24.4 construction CYCLOTOMY (CAs:::labelToCode("CYCLOTOMY", 3, 362, 10)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(384; 2, 252, 13): product of Colbourn and Torres-Jimenez 2013 Cor 4.3 (rows differing in every column removed) of [CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 2, 14, 13)); table array CA_217_2_18_13.txt (Cover starter of Colbourn, Martirosyan, Mullen, Shasha, Sherwood and Yucas 2006)] {'s': 1, 'r': 1}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(4225; 3, 28, 13): Chateauneuf-Kreher doubling of [CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 3, 14, 13)); CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 2, 14, 13))]. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(4391; 3, 183, 12): fusing symbols, CKRS 2010 Lemma 3.1 of [Raaphorst-Moura-Stevens array CA(4393; 3, 183, 13)] {'from_v': 13}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(59049; 5, 10, 9): Bush / Bose orthogonal array OA(9^5; 5, 10, 9). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(5975; 3, 184, 12): one column added, CKRS 2010 Thm 3.2 of [fusing symbols, CKRS 2010 Lemma 3.1 of [Raaphorst-Moura-Stevens array CA(4393; 3, 183, 13)] {'from_v': 13}]. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.

Each array was checked exactly (ca_profile when built, ca_verify on all t-sets before submission).
