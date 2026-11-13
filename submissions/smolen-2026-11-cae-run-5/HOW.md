# smolen-2026-11-cae-run-5: 10 arrays at cited best known sizes that had no array

Construction: one per array, named in claims.csv and below. Constructions are published theorems (references in
builds_on); searches are column extension at the record number of rows (the idea of the CA Extender of
Torres-Jimenez, Acevedo-Juarez and Avila-George 2021) with this project's own annealer casa.c.

Built from: real arrays only: arrays of this table (named by file), table certificates and constructions, Bose
orthogonal arrays and construction functions of the R package CAs 0.24.4 by Ulrike Groemping (constructions; where a
CAs function uses stored data of other authors, claims.csv names them), and arrays of this same submission.

Program: programs/ (build.py with laws.py and recipes.json for constructions; build.R with recipes.csv for PCA
products; casa.c and chain_ext.py with the start files for searches). Per array:
- CA(1225; 2, 675, 25): CAs 0.24.4 construction recBoseCA_PCA (CAs:::labelToCode("recBoseCA_PCA", 2, 675, 25)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(1248; 2, 676, 25): CAs 0.24.4 construction recBoseCA_CA (CAs:::labelToCode("recBoseCA_CA", 2, 676, 25)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(15180; 3, 11, 24): ordered design plus binary patches, Cohen-Colbourn-Ling 2008 Construction 1 of [table array CA_12_3_11_2.txt (Paley construction from the quadratic residues of GF(q))]. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(15623; 3, 26, 24): fusing symbols, CKRS 2010 Lemma 3.1 of [Bush / Bose orthogonal array OA(25^3; 3, 26, 25)] {'from_v': 25}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(15625; 3, 26, 25): Bush / Bose orthogonal array OA(25^3; 3, 26, 25). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(19679; 3, 28, 25): fusing symbols, CKRS 2010 Lemma 3.1 of [Bush / Bose orthogonal array OA(27^3; 3, 28, 27)] {'from_v': 27}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(29929; 3, 52, 24): Chateauneuf-Kreher doubling of [fusing symbols, CKRS 2010 Lemma 3.1 of [Bush / Bose orthogonal array OA(25^3; 3, 26, 25)] {'from_v': 25}; CAs 0.24.4 construction fuseBoseCA (CAs:::labelToCode("fuseBoseCA", 2, 26, 24))]. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(30625; 3, 52, 25): Chateauneuf-Kreher doubling of [Bush / Bose orthogonal array OA(25^3; 3, 26, 25); CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 2, 26, 25))]. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(331776; 4, 5, 24): composition of alphabets, CKRS 2010 (3) of [binary weight-class array, weights [0, 2, 4] on 5 columns; composition of alphabets, CKRS 2010 (3) of [binary weight-class array, weights [0, 2, 4] on 5 columns; table array CA_1296_4_5_6.txt (Orthogonal array of index one: all v^t words of length t plus their sum mod v as an extra )] {'v1': 2}] {'v1': 2}. Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.
- CA(625; 2, 26, 25): CAs 0.24.4 construction fuseBushtCA (CAs:::labelToCode("fuseBushtCA", 2, 26, 25)). Rebuild: `python3 programs/build.py programs/recipes.json rebuilt ../..`.

Each array was checked exactly (ca_profile when built, ca_verify on all t-sets before submission).
