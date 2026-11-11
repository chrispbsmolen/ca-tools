# How this array was built

Construction: a doubled Paley array with rows deleted, cut to 34 columns, from which three more rows are removed one
at a time, each removal repaired by simulated annealing on all cells. This is the route of submission
smolen-2026-11-t4-63at34, run again as one scripted chain with a complete recipe, and it replaces that submission's
array.

CA(63; 4, 34, 2).

1. Start. The table's CA(66; 4, 38, 2) is the Paley matrix for q = 37, doubled as rows [0 | M] and [1 | 1-M]
   (Colbourn 2015) with rows deleted (submission smolen-2026-11-debate11). It is included as
   programs/CA_66_4_38_2.txt.

2. Cut to 34 columns. Columns 19, 32, 9 and 16 are dropped. They were chosen one after another so that the three
   rows that do the least unique work are left with as little of it as possible. A row's unique work is the number
   of patterns, over all sets of four columns, that only this row covers.

3. Remove a row and repair, three times. The row with the least unique work is deleted. The array then misses some
   patterns, and simulated annealing repairs it. Every cell of every row may change. Counts on all sets of four
   columns are kept exactly. Each move takes one missing pattern and writes it into the closest of a few random
   rows (a focus move after Nurmela 2004). Program programs/fa_det.c. Every run has a fixed seed and stops on a
   count of moves.
   - 65 rows were reached after 4,467 moves and 64 rows after 547,705 moves (temperature 0.5, seeds 1 and 2). The
     64-row array is programs/CA_64_4_34_2_step2.txt.
   - 63 rows were reached in rounds. A round is three runs of at most 55,000,000 moves each, with seeds
     100(r+1)+1, 100(r+1)+2 and 100(r+1)+3 in round r and temperatures 0.60, 0.55 and 0.65. The next round continues
     from the output with the fewest missing patterns, and the lowest run number decides a draw. Rounds 0 to 4 ended
     with 4 patterns missing, rounds 5 to 7 with 3, and run 1 of round 8 reached 0 after 32,055,360 moves.

The array was checked exactly with ca_verify on all 46,376 sets of four columns.

Replication. The script programs/recipe63.sh runs every command and writes the log itself, with the sha256 of every
input and output (programs/RECIPE.log). A second run of the script from nothing gave the identical array
(programs/REPLAY.log, programs/REPLAY.md). Both runs were on the same type of machine.

Built from the table's own CA(66; 4, 38, 2) only. No array of Torres-Jimenez is an ingredient or start, and the
array does not have the fingerprint of one of his arrays.

Program: programs/ in this folder (recipe63.sh, fa_det.c, the 66-row start and the 64-row array of step 2).

To rebuild:
    cd programs && bash recipe63.sh
