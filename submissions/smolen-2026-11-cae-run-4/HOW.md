# smolen-2026-11-cae-run-4: 30 arrays at cited best known sizes that had no array

Construction: one per array, named in claims.csv and below. Constructions are published theorems (references in
builds_on); searches are column extension at the record number of rows (the idea of the CA Extender of
Torres-Jimenez, Acevedo-Juarez and Avila-George 2021) with this project's own annealer casa.c.

Built from: real arrays only: arrays of this table (named by file), table certificates and constructions, Bose
orthogonal arrays and construction functions of the R package CAs 0.24.4 by Ulrike Groemping (constructions; where a
CAs function uses stored data of other authors, claims.csv names them), and arrays of this same submission.

Program: programs/ (build.py with laws.py and recipes.json for constructions; build.R with recipes.csv for PCA
products; casa.c and chain_ext.py with the start files for searches). Per array:
- CA(10070; 3, 20, 20): ordered design plus binary patches, Cohen-Colbourn-Ling 2008 Construction 1 of [table array CA_18_3_20_2.txt (Chateauneuf-Kreher doubling: a strength-3 array on ceil(k/2) columns doubled with a streng)]. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(1035; 2, 575, 23): CAs 0.24.4 construction recBoseCA_PCA (CAs:::labelToCode("recBoseCA_PCA", 2, 575, 23)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(104976; 4, 5, 18): composition of alphabets, CKRS 2010 (3) of [binary weight-class array, weights [0, 2, 4] on 5 columns; table array CA_6561_4_10_9.txt (Dwyer CA_Database source code "OA" (Aaron Dwyer's abbreviation for the method; many of his)] {'v1': 2}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(1056; 2, 576, 23): CAs 0.24.4 construction recBoseCA_CA (CAs:::labelToCode("recBoseCA_CA", 2, 576, 23)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(10648; 3, 4, 22): composition of alphabets, CKRS 2010 (3) of [table array CA_8_3_4_2.txt (Chateauneuf-Kreher doubling: a strength-3 array on ceil(k/2) columns doubled with a streng); CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 3, 12, 11))] {'v1': 2}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(12165; 3, 24, 22): fusing symbols, CKRS 2010 Lemma 3.1 of [Bush / Bose orthogonal array OA(23^3; 3, 24, 23)] {'from_v': 23}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(12167; 3, 24, 23): Bush / Bose orthogonal array OA(23^3; 3, 24, 23). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(13357; 3, 40, 19): Chateauneuf-Kreher doubling of [Bush / Bose orthogonal array OA(19^3; 3, 20, 19); CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 2, 20, 19))]. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(160000; 4, 5, 20): composition of alphabets, CKRS 2010 (3) of [binary weight-class array, weights [0, 2, 4] on 5 columns; composition of alphabets, CKRS 2010 (3) of [binary weight-class array, weights [0, 2, 4] on 5 columns; table array CA_625_4_6_5.txt (Dwyer CA_Database source code "OA" (Aaron Dwyer's abbreviation for the method; many of his)] {'v1': 2}] {'v1': 2}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(194481; 4, 5, 21): composition of alphabets, CKRS 2010 (3) of [table array CA_81_4_5_3.txt (Dwyer CA_Database source code "OA" (Aaron Dwyer's abbreviation for the method; many of his); table array CA_2401_4_8_7.txt (Dwyer CA_Database source code "OA" (Aaron Dwyer's abbreviation for the method; many of his)] {'v1': 3}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(234256; 4, 5, 22): composition of alphabets, CKRS 2010 (3) of [binary weight-class array, weights [0, 2, 4] on 5 columns; Bush / Bose orthogonal array OA(11^4; 4, 12, 11)] {'v1': 2}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(23805; 3, 48, 23): Chateauneuf-Kreher doubling of [Bush / Bose orthogonal array OA(23^3; 3, 24, 23); CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 2, 24, 23))]. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(360; 2, 21, 18): CAs 0.24.4 construction projBoseCA (CAs:::labelToCode("projBoseCA", 2, 21, 18)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(361; 2, 20, 19): CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 2, 20, 19)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(528; 2, 25, 22): CAs 0.24.4 construction projBoseCA (CAs:::labelToCode("projBoseCA", 2, 25, 22)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(529; 2, 24, 23): CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 2, 24, 23)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(561; 2, 323, 17): CAs 0.24.4 construction recBoseCA_PCA (CAs:::labelToCode("recBoseCA_PCA", 2, 323, 17)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(576; 2, 324, 17): CAs 0.24.4 construction recBoseCA_CA (CAs:::labelToCode("recBoseCA_CA", 2, 324, 17)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(5832; 3, 4, 18): composition of alphabets, CKRS 2010 (3) of [table array CA_8_3_4_2.txt (Chateauneuf-Kreher doubling: a strength-3 array on ceil(k/2) columns doubled with a streng); table array CA_729_3_10_9.txt (Dwyer CA_Database source code "OA" (Aaron Dwyer's abbreviation for the method; many of his)] {'v1': 2}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(622; 2, 26, 24): CAs 0.24.4 construction fuseBoseCA (CAs:::labelToCode("fuseBoseCA", 2, 26, 24)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(624; 2, 27, 24): CAs 0.24.4 construction projBoseCA (CAs:::labelToCode("projBoseCA", 2, 27, 24)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(6579; 3, 11, 18): ordered design plus binary patches, Cohen-Colbourn-Ling 2008 Construction 1 of [table array CA_12_3_11_2.txt (Paley construction from the quadratic residues of GF(q))]. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(6859; 3, 20, 19): Bush / Bose orthogonal array OA(19^3; 3, 20, 19). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(703; 2, 399, 19): CAs 0.24.4 construction recBoseCA_PCA (CAs:::labelToCode("recBoseCA_PCA", 2, 399, 19)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(720; 2, 400, 19): CAs 0.24.4 construction recBoseCA_CA (CAs:::labelToCode("recBoseCA_CA", 2, 400, 19)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(8000; 3, 6, 20): composition of alphabets, CKRS 2010 (3) of [table array CA_64_3_6_4.txt (Dwyer CA_Database source code "OA" (Aaron Dwyer's abbreviation for the method; many of his); table array CA_125_3_6_5.txt (Dwyer CA_Database source code "OA" (Aaron Dwyer's abbreviation for the method; many of his)] {'v1': 4}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(83521; 4, 18, 17): Bush / Bose orthogonal array OA(17^4; 4, 18, 17). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(8930; 3, 11, 20): ordered design plus binary patches, Cohen-Colbourn-Ling 2008 Construction 1 of [table array CA_12_3_11_2.txt (Paley construction from the quadratic residues of GF(q))]. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(9537; 3, 36, 17): Chateauneuf-Kreher doubling of [Bush / Bose orthogonal array OA(17^3; 3, 18, 17); CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 2, 18, 17))]. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(9690; 3, 14, 20): ordered design plus binary patches, Cohen-Colbourn-Ling 2008 Construction 1 of [Shokri-Moura x-plication, theorem 2, q = 2 (tools/sm_xplication.py)]. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.

Each array was checked exactly (ca_profile when built, ca_verify on all t-sets before submission).
