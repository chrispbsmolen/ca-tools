# smolen-2026-11-engine-colext-2: CA(121; 2, 114, 7) by column extension at the record size

Construction: column extension at a fixed number of rows. Start from a real array that already has the record
number of rows at fewer columns, add the missing columns at random, and repair the whole array by simulated
annealing until every pair of columns shows all 49 symbol pairs. The idea of extending columns at fixed N is that
of the CA Extender (Torres-Jimenez, Acevedo-Juarez and Avila-George 2021); the annealing program is this
project's own (tools/own_arrays/casa.c). No array of Torres-Jimenez is used.

Built from: CA(121; 2, 109, 7), the PCA product of Bose orthogonal arrays (Colbourn and Torres-Jimenez 2013),
built by the construction functions of the R package CAs 0.24.4 (CAs:::labelToCode("pcaCA", 2, 109, 7));
programs/start_121x114.txt is that array with five added columns of random symbols.

Program: programs/casa.c (copy of tools/own_arrays/casa.c). To rebuild:

    cc -O2 -o casa programs/casa.c -lm
    ./casa 121 2 114 7 1 600 0.5 0.99995 CA_121_2_114_7.txt programs/start_121x114.txt

The annealer is randomised but seeded (seed 1); it reached zero holes after 40 s and a rebuild gave the identical
array. The result was checked exactly with ca_verify on all 6,441 column pairs, and screened against the
Torres-Jimenez fingerprints.
