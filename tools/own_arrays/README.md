# Arrays built by this project (source S8)

Scripts written for ca-tools in October 2026. No array of Torres-Jimenez's group is
used anywhere. One array, CA(32; 4, 13, 2), is derived from a published array of
another group (the CKRS CA(64; 5, 14, 2), credited in its row); several start from
Paley arrays produced by the CAs package's construction `paleyCA`. The methods
belong to their authors: Paley matrices (Paley 1933), row elimination in the spirit
of Nayeri, Colbourn and Konjevod (2013), the weight-class sizes of Johnson and
Entringer (1989). Every array was verified in full with `../../ca_verify.c`
before entry (VERIFICATION_LOG.md, 2026-10-27).

Build and run (gcc, Python 3; `pip install python-sat` for casat.py):

    gcc -O2 -o casa casa.c -lm            # casa N t k v seed maxseconds [T0] [alpha] [outfile] [initfile]
    gcc -O2 -o nck nck_early.c            # nck N t k v infile outprefix seed maxseconds [kkeep]  (first version)
    gcc -O2 -o nck2 nck.c                 # same arguments, env SHAKE (default 10)
    gcc -O2 -o nck_lite nck_lite.c        # nck_lite N t k infile outprefix seed maxseconds [kkeep]  (v = 2)
    python3 weight_arrays.py outdir
    python3 casat.py N t k v outfile [solver] [timeout_s]

Paley and CKRS starting arrays, in R with CAs 0.24.4:

    library(CAs)
    write.table(paleyCA(4, 89), "paley_4_89.txt", row.names = FALSE, col.names = FALSE)   # likewise paleyCA(t, k)
    A <- ckrsCA(5, 14, 2); B <- A[A[, 1] == 0, -1]                                        # CA(32; 4, 13, 2)

CA(258; 5, 130, 2) is CA(259; 5, 132, 2) cut to its first 130 columns, then row
elimination. RUNS.txt gives the command, seed and time limit that produced each
stored array, and marks those run again after storing that gave the same file byte
for byte (the weight-class, even-weight, SAT, annealing and CKRS arrays, and the
row-elimination arrays CA(39; 4, 20, 2), CA(87; 4, 89, 2), CA(107; 4, 113, 2) and
CA(159; 5, 80, 2); the nck_lite runs, 25 to 30 minutes each, were not repeated). Row elimination has a time limit, so a repeat on another
machine can stop at a different size. RUNS.txt also lists the exploratory runs. The
stored arrays are what the table relies on, and each is verified.

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
