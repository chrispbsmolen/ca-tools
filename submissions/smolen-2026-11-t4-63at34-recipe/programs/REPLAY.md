# Replay record for CA(63; 4, 34, 2)

The array in this folder has sha256 ae7873c971663e377bf5c1657b61329494bfa5ae7ffe198ccef00b3e758f90b1.

The script recipe63.sh was run twice from nothing on an Apple Silicon Mac (arm64), 2026-11-10 and 2026-11-11, in two
separate folders. Each run compiled fa_det.c, started from CA_66_4_38_2.txt and wrote its own log. RECIPE.log is the
log of the first run and REPLAY.log is the log of the second. Both runs ended in round 8 with the identical array
(compared with cmp). The two logs hold the same commands with the same sha256 of every input and output. They differ
only in the order of the three lines of a round, because the three runs of a round work in parallel, and in the
seconds each run took.

Every run stops on a count of moves (option -I), never on a clock, so the result does not depend on the load of the
machine. The full replay has been made on one type of machine only. On Linux x86_64 the first two steps were run
and gave the identical 65-row and 64-row arrays (sha256 464f17b4... and 5a1d7385..., as in the logs); the rounds at
63 rows were not replayed there. The program uses the exp function of the C library in its acceptance test, so a
different machine type could in principle take a different path in the rounds.

To replay, copy fa_det.c, recipe63.sh and CA_66_4_38_2.txt into an empty folder and run `bash recipe63.sh` there. It
needs cc. It uses 3 cores and took about four and a half hours here (9 rounds of about 30 minutes).
