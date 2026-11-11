# Replay record

sha256 of the five arrays of this submission:
- CA_31_2_1252_3.txt 2a1e0bbf549e9f9a9938abaa6e120dc8fd55d5fbb7d3e9dd12118c39a7e0d5a3
- CA_33_2_2637_3.txt 0430aae1f20bfe6f79eee086694bcf96281a0fecf51dadb033e6277d41b32cc9
- CA_35_2_3355_3.txt 082347a26af245c7ac80d410ff0272e6899729256953f3f43fa3815fcdbaa82f
- CA_36_2_4914_3.txt 92fa2c914dc14a9c7548ca76f1afdc774d872d125051ebb6ef697077fda0af83
- CA_37_2_5730_3.txt 6a30b06edecfd6511890bb5781ffe51e367e26bd17ccd3a4b99474f603e7ced4

Two separate executions on Linux x86_64 (gcc 13.3.0) on 2026-11-11 gave identical files.

1. First run, by hand, the commands of recipe_ext.sh typed one array at a time. The lines the extension program
   printed for every saved array are in ext2t_first_run_NN_found_lines.txt (NN = rows).
2. Recipe run. `bash recipe_ext.sh A 31 35 37` and `bash recipe_ext.sh B 33 36`. Logs RECIPE_ext_A.log and
   RECIPE_ext_B.log, written by the script. Each array was saved at the same move number as in the first run
   (52,664,081 at 31 rows, 10,840,043 at 33, 8,760,971 at 35, 4,930,914 at 36, 4,793,497 at 37) and is identical
   to the first-run file.

One correction to the script. The recipe run used the version kept here as recipe_ext_v1_as_run.sh, and the logs
carry that version's sha256. That version copied the right array at the right count, but its stop command did not
end the extension program, which kept running in the background until it was stopped by hand. recipe_ext.sh is
the same script with that one line corrected (`exec` added, so the stop reaches the program). The corrected line
does not touch the search. The corrected script as a whole has not been run end to end.

The run has not been repeated on another kind of machine. The products use integers only. The extension step
uses a seeded generator and one floating point comparison per move.
