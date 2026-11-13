# smolen-2026-11-cae-run-3: 30 arrays at cited best known sizes that had no array

Construction: one per array, named in claims.csv and below. Constructions are published theorems (references in
builds_on); searches are column extension at the record number of rows (the idea of the CA Extender of
Torres-Jimenez, Acevedo-Juarez and Avila-George 2021) with this project's own annealer casa.c.

Built from: real arrays only: arrays of this table (named by file), table certificates and constructions, Bose
orthogonal arrays and construction functions of the R package CAs 0.24.4 by Ulrike Groemping (constructions; where a
CAs function uses stored data of other authors, claims.csv names them), and arrays of this same submission.
No array of Torres-Jimenez is an ingredient or a start (his methods are cited, no array of his).

Program: programs/ (build.py with laws.py and recipes.json for constructions; build.R with recipes.csv for PCA
products; casa.c and chain_ext.py with the start files for searches). Per array:
- CA(255; 2, 18, 15): CAs 0.24.4 construction projBoseCA (CAs:::labelToCode("projBoseCA", 2, 18, 15)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(256; 2, 17, 16): CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 2, 17, 16)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(2744; 3, 4, 14): composition of alphabets, CKRS 2010 (3) of [table array CA_8_3_4_2.txt (Chateauneuf-Kreher doubling: a strength-3 array on ceil(k/2) columns doubled with a streng); table array CA_343_3_8_7.txt (Dwyer CA_Database source code "OA" (Aaron Dwyer's abbreviation for the method; many of his)] {'v1': 2}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(28561; 4, 14, 13): Bush / Bose orthogonal array OA(13^4; 4, 14, 13). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(288; 2, 19, 16): CAs 0.24.4 construction projBoseCA (CAs:::labelToCode("projBoseCA", 2, 19, 16)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(289; 2, 18, 17): CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 2, 18, 17)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(300; 2, 23, 14): CAs 0.24.4 construction CS_MS (CAs:::labelToCode("CS_MS", 2, 23, 14)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(3185; 3, 11, 14): ordered design plus binary patches, Cohen-Colbourn-Ling 2008 Construction 1 of [table array CA_12_3_11_2.txt (Paley construction from the quadratic residues of GF(q))]. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(3549; 3, 14, 14): ordered design plus binary patches, Cohen-Colbourn-Ling 2008 Construction 1 of [Shokri-Moura x-plication, theorem 2, q = 2 (tools/sm_xplication.py)]. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(38416; 4, 5, 14): composition of alphabets, CKRS 2010 (3) of [binary weight-class array, weights [0, 2, 4] on 5 columns; table array CA_2401_4_8_7.txt (Dwyer CA_Database source code "OA" (Aaron Dwyer's abbreviation for the method; many of his)] {'v1': 2}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(4096; 3, 18, 16): frozen-core extension of Bush / Bose orthogonal array OA(16^3; 3, 17, 16) (4096 rows, 17 columns): base fixed, 0 free rows and 1 free columns annealed (own extv.c, T 1.5). Rebuild: `extv 3 16 programs/start_CA_4096_3_18_16.txt 4096 17 0 1 1 20 1.5 CA_4096_3_18_16.txt` (seeded, deterministic).
- CA(421; 2, 323, 13): CAs 0.24.4 construction pcaCA (CAs:::labelToCode("pcaCA", 2, 323, 13)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(433; 2, 341, 13): CAs 0.24.4 construction pcaCA (CAs:::labelToCode("pcaCA", 2, 341, 13)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(436; 2, 29, 16): CAs 0.24.4 construction CS_MS (CAs:::labelToCode("CS_MS", 2, 29, 16)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(4393; 3, 183, 13): Raaphorst-Moura-Stevens array CA(4393; 3, 183, 13). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(481; 2, 2717, 13): CAs 0.24.4 construction recBoseCA_PCA (CAs:::labelToCode("recBoseCA_PCA", 2, 2717, 13)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(4913; 3, 18, 17): Bush / Bose orthogonal array OA(17^3; 3, 18, 17). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(492; 2, 2730, 13): product of Colbourn and Torres-Jimenez 2013 Cor 4.3 (rows differing in every column removed) of [CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 2, 14, 13)); CAs 0.24.4 construction recBoseCA_PCA (CAs:::labelToCode("recBoseCA_PCA", 2, 195, 13))] {'s': 1, 'r': 1}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(496; 2, 288, 16): CAs 0.24.4 construction recBoseCA_PCA (CAs:::labelToCode("recBoseCA_PCA", 2, 288, 16)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(50625; 4, 5, 15): composition of alphabets, CKRS 2010 (3) of [table array CA_81_4_5_3.txt (Dwyer CA_Database source code "OA" (Aaron Dwyer's abbreviation for the method; many of his); table array CA_625_4_6_5.txt (Dwyer CA_Database source code "OA" (Aaron Dwyer's abbreviation for the method; many of his)] {'v1': 3}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(510; 2, 289, 16): CAs 0.24.4 construction recBoseCA_CA (CAs:::labelToCode("recBoseCA_CA", 2, 289, 16)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(513; 2, 32, 17): CAs 0.24.4 construction CS_CMMSSY (CAs:::labelToCode("CS_CMMSSY", 2, 32, 17)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(534; 2, 440, 14): CAs 0.24.4 construction pcaCA (CAs:::labelToCode("pcaCA", 2, 440, 14)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(536; 2, 445, 14): frozen-core extension of CAs 0.24.4 construction pcaCA (CAs:::labelToCode("pcaCA", 2, 440, 14)) (534 rows, 440 columns): base fixed, 2 free rows and 5 free columns annealed (own extv.c, T 1.5). Rebuild: `extv 2 14 programs/start_CA_536_2_445_14.txt 534 440 2 5 1 20 1.5 CA_536_2_445_14.txt` (seeded, deterministic).
- CA(65534; 4, 17, 15): fusing symbols, CKRS 2010 Lemma 3.1 of [Bush / Bose orthogonal array OA(16^4; 4, 17, 16)] {'from_v': 16}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(65536; 4, 17, 16): Bush / Bose orthogonal array OA(16^4; 4, 17, 16). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(7936; 3, 34, 16): Chateauneuf-Kreher doubling of [Bush / Bose orthogonal array OA(16^3; 3, 17, 16); CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 2, 17, 16))]. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(8187; 3, 273, 14): fusing symbols, CKRS 2010 Lemma 3.1 of [Raaphorst-Moura-Stevens array CA(8191; 3, 273, 16)] {'from_v': 16}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(8189; 3, 273, 15): fusing symbols, CKRS 2010 Lemma 3.1 of [Raaphorst-Moura-Stevens array CA(8191; 3, 273, 16)] {'from_v': 16}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(83519; 4, 18, 16): fusing symbols, CKRS 2010 Lemma 3.1 of [Bush / Bose orthogonal array OA(17^4; 4, 18, 17)] {'from_v': 17}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.

Each array was checked exactly (ca_profile when built, ca_verify on all t-sets before submission).
