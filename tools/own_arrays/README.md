# Arrays built by this project (source S8)

Scripts written for ca-tools in October 2026. No array of Torres-Jimenez's group is
used anywhere, as an input or at any earlier step. Some constructions leave no choice
and give his rows again: CA(10; 3, 5, 2) and CA(32; 5, 6, 2) (the rows of his files in
another order), and the starting CA(179; 4, 358, 2) of CA(154; 4, 225, 2) and the
arrays with k = 281, 289, 297 and 324, computed from `CAs:::paley_mat(359)`, which has
exactly the rows of his TJ2level ca179.4.2.358. Some arrays are derived from
published arrays of other groups, credited in their rows: CA(32; 4, 13, 2) and
CA(79; 5, 15, 2) from CKRS arrays (Colbourn, Keri, Rivas Soriano and Schlage-Puchta
2010, `CAs::ckrsCA`), CA(401; 6, 27, 2), CA(411; 6, 28, 2) and CA(420; 6, 29, 2) from the
CA(440; 6, 30, 2) of Wagner, Kampel and Simos 2021 (`CAs::WKS_CAs`). Many start from Paley arrays (Paley 1933) produced by the
CAs package's `paleyCA` and `paley_mat` or computed here. The methods belong to their
authors: row elimination in the spirit of Nayeri, Colbourn and Konjevod (2013), the tabu
search of Nurmela (2004), simulated annealing as in Torres-Jimenez and Rodriguez-Tello
(2012), column extension after the idea of Torres-Jimenez, Acevedo-Juarez and
Avila-George (2021, "CA Extender"), the generalized direct product of Colbourn and
Torres-Jimenez (2013, Corollary 4.3), the weight-class sizes of Johnson and Entringer
(1989) (references below); the programs are this project's own implementations.
Every array was verified in full with `../../ca_verify.c` before entry (VERIFICATION_LOG.md, 2026-10-27 and 2026-10-28).

Build and run (gcc or clang, Python 3; `pip install python-sat` for casat.py):

    gcc -O2 -o casa casa.c -lm            # casa N t k v seed maxseconds [T0] [alpha] [outfile] [initfile]
    gcc -O2 -o nck nck_early.c            # nck N t k v infile outprefix seed maxseconds [kkeep]  (first version)
    gcc -O2 -o nck2 nck.c                 # same arguments, env SHAKE (default 10)
    gcc -O2 -o nck_lite nck_lite.c        # nck_lite N t k infile outprefix seed maxseconds [kkeep]  (v = 2)
    python3 weight_arrays.py outdir
    python3 casat.py N t k v outfile [solver] [timeout_s]

and for the arrays of 2026-10-28 (usage in each file's header):

    gcc -O3 -march=native -DW=2 -o catabu2 catabu.c -lm      # catabu t k infile N_in target outprefix seed maxsec
                                                            #   [tenure] [noise] [colsel] [attemptsec] [temp] [restore]
                                                            #   (t = 3, 4; v = 2; N <= 64 W; W = 3, 4, 5 likewise)
    gcc -O3 -march=native -DW=2 -o catabu2 catabu_v1.c -lm   # first version, arguments up to attemptsec
    gcc -O3 -march=native -o ext2 ext2.c -lm                  # [env ...] ext2 N K v seed maxsec outprefix [initfile|-] [k0]  (t = 2)
    python3 prod2.py A B out                                  # generalized direct product, t = 2 (OA9 = Bose OA(9;2,4,3))
    python3 plan_products.py INGDIR OUTDIR [--build]          # product plans over the arrays in INGDIR
    gcc -O3 -march=native -o cycsa cycsa.c -lm                # cycsa t k m s f seed maxsec outprefix [options]
    gcc -O3 -march=native -o binsa binsa.c -lm                # binsa N t k seed maxsec outprefix [options]  (v = 2)
    gcc -O3 -march=native -o ccsel ccsel.c -lm                # ccsel q t k ndel seed maxsec outfile [-x] [-n]
    gcc -O3 -march=native -o pal5 pal5.c -lm                  # pal5 paleyfile k d seed maxsec outfile
    gcc -O3 -march=native -fopenmp -o pal6 pal6.c -lm         # pal6 paleyfile k d seed maxsec outfile

Paley, CKRS and WKS starting arrays, in R with CAs 0.24.4 (0-based, one row per line):

    library(CAs)
    write.table(paleyCA(4, 89), "paley_4_89.txt", row.names = FALSE, col.names = FALSE)   # likewise paleyCA(t, k)
    A <- ckrsCA(5, 14, 2); B <- A[A[, 1] == 0, -1]                                        # CA(32; 4, 13, 2)
    P <- CAs:::paley_mat(359); write.table(P, "paley359.txt", row.names = FALSE, col.names = FALSE)
    write.table(P[P[, 1] == 1, -1], "CA_179_4_358_2.txt", row.names = FALSE, col.names = FALSE)
    write.table(ckrsCA(5, 15, 2), "ckrs_5_15.txt", row.names = FALSE, col.names = FALSE)
    write.table(WKS_CAs[["30"]], "wks_6_30.txt", row.names = FALSE, col.names = FALSE)

CA(258; 5, 130, 2) is CA(259; 5, 132, 2) cut to its first 130 columns, then row
elimination. RUNS.txt gives the command, seed and time limit that produced each
stored array, and marks those run again after storing that gave the same file byte
for byte (the weight-class, even-weight, SAT, annealing and CKRS arrays, and the
row-elimination arrays CA(39; 4, 20, 2), CA(87; 4, 89, 2), CA(107; 4, 113, 2) and
CA(159; 5, 80, 2); the nck_lite runs, 25 to 30 minutes each, were not repeated; for
2026-10-28 see its section C). Searches with a time limit can stop at a different size
on another machine. RUNS.txt also lists the exploratory runs. The stored arrays are
what the table relies on, and each is verified.

References:

- C. J. Colbourn, G. Kéri, P. P. Rivas Soriano, J.-C. Schlage-Puchta, Covering and
  radius-covering arrays: constructions and classification, Discrete Appl. Math. 158
  (2010) 1158-1180, doi:10.1016/j.dam.2010.03.008.
- C. J. Colbourn, J. Torres-Jimenez, Profiles of covering arrays of strength two,
  J. Algorithms Comput. 44 (2013) 31-60, doi:10.22059/jac.2013.7914 (Corollary 4.3: a CA(N; 2, k, v) with r disjoint
  rows and a CA(M; 2, l, v) with s disjoint rows give a CA(N + M - min(v, r + s); 2, kl, v)).
- D. S. Johnson, R. C. Entringer, Largest induced subgraphs of the n-cube that contain
  no 4-cycles, J. Combin. Theory Ser. B 46 (1989) 346-355, doi:10.1016/0095-8956(89)90054-3.
- P. Nayeri, C. J. Colbourn, G. Konjevod, Randomized post-optimization of covering arrays,
  European J. Combin. 34 (2013) 91-103, doi:10.1016/j.ejc.2012.07.017.
- K. J. Nurmela, Upper bounds for covering arrays by tabu search, Discrete Appl. Math. 138
  (2004) 143-152, doi:10.1016/S0166-218X(03)00291-9.
- R. E. A. C. Paley, On orthogonal matrices, J. Math. Phys. 12 (1933) 311-320,
  doi:10.1002/sapm1933121311.
- J. Torres-Jimenez, E. Rodriguez-Tello, New bounds for binary covering arrays using
  simulated annealing, Inform. Sci. 185 (2012) 137-152, doi:10.1016/j.ins.2011.09.020.
- J. Torres-Jimenez, B. Acevedo-Juarez, H. Avila-George, Covering array EXtender, Appl.
  Math. Comput. 402 (2021) 126122, doi:10.1016/j.amc.2021.126122.
- M. Wagner, L. Kampel, D. E. Simos, Heuristically enhanced IPO algorithms for covering
  array generation, IWOCA 2021, LNCS 12757 (2021) 571-586, doi:10.1007/978-3-030-79987-8_40.

| array | method |
|---|---|
| CA(10; 3, 5, 2) | weight-class array built here (weight_arrays.py): all binary 5-vectors of weight 1 or 4; Johnson-Entringer size |
| CA(15; 3, 12, 2) | simulated annealing built here (casa.c), random start, no ingredient |
| CA(16; 3, 14, 2) | simulated annealing built here (casa.c), random start, no ingredient |
| CA(17; 3, 16, 2) | SAT built here (casat.py, CaDiCaL 1.5.3 via python-sat), no ingredient |
| CA(16; 4, 5, 2) | even-weight binary 5-vectors (OA of strength 4), built here (weight_arrays.py) |
| CA(21; 4, 6, 2) | weight-class array built here: binary 6-vectors of weight 1 or 4; Johnson-Entringer size |
| CA(32; 4, 13, 2) | derived from CAs::ckrsCA(5,14,2) = CKRS CA(64;5,14,2): the 32 rows with 0 in column 1, column dropped |
| CA(39; 4, 20, 2) | CAs::paleyCA(4,20) [Double(rbind(1,paley_mat(19))), 40 rows] then row elimination (nck_early.c) |
| CA(87; 4, 89, 2) | CAs::paleyCA(4,89) [paley_mat(89)[-1,], 88 rows] then row elimination (nck_early.c) |
| CA(107; 4, 113, 2) | CAs::paleyCA(4,113) [paley_mat(113)[-1,], 112 rows] then row elimination (nck_early.c) |
| CA(32; 5, 6, 2) | even-weight binary 6-vectors (OA of strength 5), built here |
| CA(42; 5, 7, 2) | weight-class array built here: binary 7-vectors of weight 2 or 5; Johnson-Entringer size |
| CA(159; 5, 80, 2) | CAs::paleyCA(5,80) [Double(rbind(1,paley_mat(79))), 160 rows] then row elimination (nck.c) |
| CA(225; 5, 114, 2) | CAs::paleyCA(5,114) [Double(paley_mat(113)), 226 rows] then row elimination (nck_lite.c) |
| CA(251; 5, 128, 2) | CAs::paleyCA(5,128) [Double(paley_mat(127)[-1,]), 252 rows] then row elimination (nck_lite.c) |
| CA(258; 5, 130, 2) | our CA(259;5,132,2) (Paley doubling plus row elimination) cut to 130 columns, then row elimination (nck_lite.c) |
| CA(259; 5, 132, 2) | CAs::paleyCA(5,132) [Double(paley_mat(131)[-1,]), 260 rows] then row elimination (nck_lite.c) |
| CA(271; 5, 138, 2) | CAs::paleyCA(5,138) [Double(paley_mat(137)[-1,]), 272 rows] then row elimination (nck_lite.c) |
| CA(64; 6, 7, 2) | even-weight binary 7-vectors (OA of strength 6), built here |
| CA(85; 6, 8, 2) | weight-class array built here: binary 8-vectors of weight 2, 5 or 8; Johnson-Entringer size |
| CA(11; 2, 5, 3) | SAT built here (casat.py, CaDiCaL 1.5.3), no ingredient; size is optimal (Kokkala et al. 2020) |
| CA(12; 2, 7, 3) | SAT built here (casat.py), no ingredient |
| CA(13; 2, 9, 3) | SAT built here (casat.py), no ingredient |
| CA(14; 2, 10, 3) | SAT built here (casat.py), no ingredient |

Added 2026-10-28 (RUNS.txt, section C):

| array | method |
|---|---|
| CA(94; 4, 97, 2) | CAs::paleyCA(4,97) (Paley 1933; 96 rows, 97 columns), then row elimination and tabu search built here (catabu_v1.c, the first version of catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(98; 4, 101, 2) | CAs::paleyCA(4,101) (Paley 1933; 100 rows, 101 columns), reduced to 99 rows by row elimination (nck_early.c), then to 98 rows by row elimination and tabu search built here (catabu_v1.c, the first version of catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(101; 4, 103, 2) | CAs::paleyCA(4,107) (Paley 1933; 106 rows, 107 columns), a random 103-subset of its columns (colsel 1), then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(102; 4, 107, 2) | CAs::paleyCA(4,107) (Paley 1933; 106 rows, 107 columns), reduced to 103 rows by row elimination (nck_early.c), then to 102 rows by row elimination and tabu search built here (catabu_v1.c, the first version of catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(105; 4, 109, 2) | CAs::paleyCA(4,113) (Paley 1933; 112 rows, 113 columns), a random 109-subset of its columns (colsel 1), then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(106; 4, 111, 2) | CAs::paleyCA(4,113) (Paley 1933; 112 rows, 113 columns), a random 111-subset of its columns (colsel 1), then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(123; 4, 148, 2) | CAs::paleyCA(4,149) (Paley 1933; 146 rows, 149 columns), its first 148 columns, then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(123; 4, 150, 2) | CAs::paleyCA(4,151) (Paley 1933; 148 rows, 151 columns), its first 150 columns, then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(126; 4, 154, 2) | CAs::paleyCA(4,157) (Paley 1933; 154 rows, 157 columns), its first 154 columns, then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(126; 4, 156, 2) | CAs::paleyCA(4,157) (Paley 1933; 154 rows, 157 columns), its first 156 columns, then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(128; 4, 159, 2) | CAs::paleyCA(4,163) (Paley 1933; 160 rows, 163 columns), its first 159 columns, then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(128; 4, 162, 2) | CAs::paleyCA(4,163) (Paley 1933; 160 rows, 163 columns), its first 162 columns, then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(133; 4, 173, 2) | CAs::paleyCA(4,179) (Paley 1933; 175 rows, 179 columns), its first 173 columns, then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(135; 4, 179, 2) | CAs::paleyCA(4,181) (Paley 1933; 180 rows, 181 columns), its first 179 columns, then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(137; 4, 187, 2) | CAs::paleyCA(4,191) (Paley 1933; 186 rows, 191 columns), its first 187 columns, then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(138; 4, 191, 2) | CAs::paleyCA(4,193) (Paley 1933; 188 rows, 193 columns), its first 191 columns, then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(138; 4, 192, 2) | CAs::paleyCA(4,193) (Paley 1933; 188 rows, 193 columns), a random 192-subset of its columns (colsel 7), then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(141; 4, 199, 2) | CAs::paleyCA(4,211) (Paley 1933; 206 rows, 211 columns), its first 199 columns, then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(148; 4, 200, 2) | CAs::paleyCA(4,211) (Paley 1933; 206 rows, 211 columns), its first 200 columns, then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(149; 4, 222, 2) | CAs::paleyCA(4,223) (Paley 1933; 217 rows, 223 columns), its first 222 columns, then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(154; 4, 225, 2) | a CA(179;4,358,2) taken from the Paley matrix of order 359 (CAs:::paley_mat(359), Paley 1933: its 179 rows with 1 in the first column, that column dropped), a random 225-subset of its columns (colsel 5), then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(156; 4, 257, 2) | CAs::paleyCA(4,263) (Paley 1933; 256 rows, 263 columns), its first 257 columns, then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(157; 4, 268, 2) | CAs::paleyCA(4,269) (Paley 1933; 261 rows, 269 columns), its first 268 columns, then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(158; 4, 272, 2) | CAs::paleyCA(4,277) (Paley 1933; 269 rows, 277 columns), its first 272 columns, then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(160; 4, 281, 2) | a CA(179;4,358,2) taken from the Paley matrix of order 359 (CAs:::paley_mat(359), Paley 1933: its 179 rows with 1 in the first column, that column dropped), its first 281 columns, then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(161; 4, 289, 2) | a CA(179;4,358,2) taken from the Paley matrix of order 359 (CAs:::paley_mat(359), Paley 1933: its 179 rows with 1 in the first column, that column dropped), its first 289 columns, then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(163; 4, 297, 2) | a CA(179;4,358,2) taken from the Paley matrix of order 359 (CAs:::paley_mat(359), Paley 1933: its 179 rows with 1 in the first column, that column dropped), its first 297 columns, then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(165; 4, 324, 2) | a CA(179;4,358,2) taken from the Paley matrix of order 359 (CAs:::paley_mat(359), Paley 1933: its 179 rows with 1 in the first column, that column dropped), its first 324 columns, then row elimination and tabu search built here (catabu.c: row elimination after Nayeri, Colbourn and Konjevod 2013, tabu search after Nurmela 2004) |
| CA(15; 2, 20, 3) | tabu search from a random start built here (ext2.c; tabu search after Nurmela 2004), all 20 columns at once, no ingredient |
| CA(16; 2, 21, 3) | simulated annealing with Nurmela-style moves from a random start built here (ext2.c), columns added one at a time from 10 (the column-extension idea of Torres-Jimenez, Acevedo-Juarez and Avila-George 2021), no ingredient |
| CA(17; 2, 29, 3) | simulated annealing with Nurmela-style moves from a random start built here (ext2.c), columns added one at a time from 20 (the column-extension idea of Torres-Jimenez, Acevedo-Juarez and Avila-George 2021), no ingredient |
| CA(22; 2, 107, 3) | generalized direct product (prod2.py; Colbourn and Torres-Jimenez 2013, Cor. 4.3) of our CA(15;2,20,3) (the array of this table, ext2.c tabu search) and the Bose OA(9;2,4,3), a CA(22;2,80,3), extended column by column to 107 columns by simulated annealing (ext2.c; the column-extension idea of Torres-Jimenez, Acevedo-Juarez and Avila-George 2021) |
| CA(28; 2, 449, 3) | generalized direct product (prod2.py; Colbourn and Torres-Jimenez 2013, Cor. 4.3) of our CA(15;2,20,3) (the array of this table) with itself, a CA(28;2,400,3), extended column by column to 449 columns by simulated annealing (ext2.c; the column-extension idea of Torres-Jimenez, Acevedo-Juarez and Avila-George 2021) |
| CA(54; 5, 9, 2) | simulated annealing from a random start built here (cycsa.c, plain mode, fixed temperature; after Torres-Jimenez and Rodriguez-Tello 2012), no ingredient |
| CA(56; 5, 10, 2) | simulated annealing from a random start built here (cycsa.c, plain mode, fixed temperature; after Torres-Jimenez and Rodriguez-Tello 2012), no ingredient |
| CA(79; 5, 15, 2) | simulated annealing with row deletion built here (binsa.c; after Torres-Jimenez and Rodriguez-Tello 2012), started from the first 87 rows of the CA(88;5,15,2) of Colbourn, Keri, Rivas Soriano and Schlage-Puchta 2010 (CAs::ckrsCA(5,15,2)) |
| CA(134; 5, 35, 2) | doubled Paley matrix of order 67 (Paley 1933; computed here, the array of CAs::paleyCA(5,68)) with one Paley row and its complement deleted, 34 Paley columns and the doubling column chosen by simulated annealing over column subsets (ccsel.c) |
| CA(357; 5, 194, 2) | the Paley matrix of order 359 (CAs:::paley_mat(359), Paley 1933, a CA(359;5,359,2)) without rows 0 and 1, 194 columns chosen by simulated annealing over column subsets and one cell changed (pal5.c) |
| CA(401; 6, 27, 2) | row deletion with simulated-annealing repair built here (binsa.c; after Torres-Jimenez and Rodriguez-Tello 2012, focused moves after Nurmela 2004), started from the first 27 columns of the CA(440;6,30,2) of Wagner, Kampel and Simos 2021 (CAs::WKS_CAs, entry 30) |
| CA(411; 6, 28, 2) | row deletion with simulated-annealing repair built here (binsa.c; after Torres-Jimenez and Rodriguez-Tello 2012, focused moves after Nurmela 2004), started from the first 28 columns of the CA(440;6,30,2) of Wagner, Kampel and Simos 2021 (CAs::WKS_CAs, entry 30) |
| CA(420; 6, 29, 2) | row deletion with simulated-annealing repair built here (binsa.c; after Torres-Jimenez and Rodriguez-Tello 2012, focused moves after Nurmela 2004), started from the first 29 columns of the CA(440;6,30,2) of Wagner, Kampel and Simos 2021 (CAs::WKS_CAs, entry 30) |
| CA(716; 6, 91, 2) | the doubled Paley matrix of order 359 (CAs:::Double(rbind(1, paley_mat(359))), Paley 1933, a CA(720;6,360,2)) without Paley rows 0 and 1 and their complements, 91 Paley columns chosen by simulated annealing over column subsets and 16 cells changed (pal6.c) |
