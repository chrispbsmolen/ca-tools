# Replay record for CA(18; 2, 52, 3), CA(30; 2, 975, 3) and CA(24; 2, 209, 3)

sha256 of the three arrays of this submission:
- CA_18_2_52_3.txt  219977d44260bce42019d2acf50cb5020f2b29e6483ba76721f51e4dc36f5414
- CA_30_2_975_3.txt 2ba16ae457fbcab3e610f605446e2b826a409bc1c65a9cf4eb7404e66924a870
- CA_24_2_209_3.txt 47c88f55453517431e920ee88665baf2be34dea370a02481fad9bdbcdc2e70f3

Three separate executions of recipe_item123.sh on Linux x86_64 (gcc 13.3.0, Python 3.13) on 2026-11-10 gave these
identical files. Each run was made in a new empty folder.

1. Tag build. Log RECIPE_build.log.
2. Tag replay. Log RECIPE_replay.log.
3. Tag third, run from a copy of this submission folder. Log RECIPE_third_from_submission_folder.log.

The arrays were first found the same day by the same commands run by hand, and those first files are identical to
the files above. The run has not been repeated on another kind of machine. The 18-row search and the products use
integers only. The extension step (ext2t.c) uses a seeded generator and one floating point comparison per move.

orbq7_run_log.txt and ext2t_run_log.txt are the full outputs of the two search steps in run 1. In the extension
run the array at 209 columns was saved at move 19,751,928.

To replay, run `bash recipe_item123.sh sometag` in this folder (it needs cc and python3) and compare the sha256 of
the three files it writes into run_sometag/. It takes about four minutes on one core.
