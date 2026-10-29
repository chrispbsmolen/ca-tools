TJcat entries that CAs can already build (Christopher Smolen, 2026-10-29)

32 of the 2-level TJcat entries without an array name and without a replaceable entry
(CAs 0.25, GitHub version of 2026-10-27) are built by CAs functions alone, with no
stored array:

  ca.5.2^(p-1).txt   derive(cyc(p, 2))   for the 31 primes p = 1231, 1283, ..., 1619
  ca.5.2^503.txt     cyc(503, 2)

Each gives exactly the TJcat size. derive() keeps the rows with a 1 in the first column,
the less frequent value, so no extra argument is needed.

Files

  TJcat_cyclotomy_replacements.csv   one line per entry: the call, the dimensions, the MD5
                                     and SHA-256 of the array as written by
                                     write.table(A, row.names = FALSE, col.names = FALSE),
                                     and the check of its parent
  rebuild_and_compare.R              rebuilds all 32 with CAs and compares them with the
                                     checked arrays
  ../../tools/cyccheck/              the code of the checks: cyccheck.c (CPU), cyccheck_metal.m
                                     (GPU), brute.c and brute3.c (brute force, no symmetry),
                                     gpu_test.sh (compares GPU, CPU and brute force)

The checks

cyc(p, 2) is the p x p circulant of the quadratic nonresidue indicator (row r, column c
holds 1 when c - r is a nonresidue mod p), which was confirmed for all 32 calls. Its
strength was checked in full, strength 6 for the 31 primes and strength 5 for 503, with
no uncovered column set in any of them. The strength 5 of derive(cyc(p, 2)) follows from
the strength 6 of cyc(p, 2). These are also full checks of the strength 6 CYCLOTOMYcat
entries for these primes.

The checker uses two symmetries of the circulant, both verified on the array before use.
Shifting rows and columns together maps the array to itself, so every column set has a
shifted copy that contains column 0. Multiplying column and row indices by a quadratic
residue also maps it to itself, so the second column can be taken as 1 or as the smallest
nonresidue. It therefore checks every set {0, 1, ...} and {0, n0, ...} completely.

The checker was compared with two brute force programs that use neither symmetry. They
gave identical counts of uncovered sets at strengths 4, 5 and 6 on cases where coverage
fails (for example p = 313, 337 and 379 at strength 5 and p = 131 at strength 6), the
same verdicts at strength 4 for primes from 61 to 103, and a circulant with two flipped
entries was rejected. The large checks ran on the GPU of a MacBook Pro (Apple M4 Max),
between 4 and 12 minutes per prime. The GPU version (cyccheck_metal.m) gives the
same counts as the CPU version (cyccheck.c) on all test cases.
