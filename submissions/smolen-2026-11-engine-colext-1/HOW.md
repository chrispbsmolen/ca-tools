# smolen-2026-11-engine-colext-1: CA(105; 2, 80, 7) by column extension at the record size

Construction: column extension at a fixed number of rows. Start from a real array that already has the record
number of rows at one column fewer, add the missing column at random, and repair the whole array by simulated
annealing until every pair of columns shows all 49 symbol pairs. The idea of extending columns at fixed N is that
of the CA Extender (Torres-Jimenez, Acevedo-Juarez and Avila-George 2021); the annealing program is this
project's own (tools/own_arrays/casa.c). No array of Torres-Jimenez is used.

Built from: CA(105; 2, 79, 7), the PCA product of Bose orthogonal arrays (Colbourn and Torres-Jimenez 2013),
built by the construction functions of the R package CAs 0.24.4; programs/start_105x80.txt is that array with
one added column of random symbols.

Program: programs/casa.c (copy of tools/own_arrays/casa.c). To rebuild:

    cc -O2 -o casa programs/casa.c -lm
    ./casa 105 2 80 7 1 180 0.5 0.99995 CA_105_2_80_7.txt programs/start_105x80.txt

The annealer is randomised but seeded (seed 1); it reached zero holes after 3.5 s here. The result was checked
exactly with ca_verify on all 3,160 column pairs, and screened against the Torres-Jimenez fingerprints.
