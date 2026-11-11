#!/bin/bash
# recipe63.sh: rebuild CA(63;4,34,2) from the table's CA(66;4,38,2) under DECISIONS B7 (recipe rule).
# Every command, with the sha256 of its inputs and outputs, is appended to RECIPE.log by this script.
# All runs stop on a move count (-I), so the result does not depend on the machine or its load.
# usage: bash recipe63.sh [MOVES_PER_RUN=55000000] [MAX_ROUNDS=16]     (3 processes in parallel in each round)
cd "$(dirname "$0")"
MOVES=${1:-55000000}; MAXR=${2:-16}
sha(){ if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -c1-64; else shasum -a 256 "$1" | cut -c1-64; fi; }
cc -O3 -o fa_det fa_det.c -lm || exit 1
LOG=RECIPE.log; : > $LOG
echo "recipe63 start; fa_det.c sha256 $(sha fa_det.c); base CA_66_4_38_2.txt sha256 $(sha CA_66_4_38_2.txt); moves per run $MOVES" >> $LOG
run(){ # label input output args...
  local label=$1 in=$2 out=$3; shift 3
  local res; res=$(./fa_det $in 4 "$@" 2>/dev/null | tail -n 1)
  echo "$label | ./fa_det $in 4 $* | in $(sha $in) | out $(sha $out) | $res" >> $LOG; }
run "step1 66 -> 65 rows, columns 19,32,9,16 dropped" CA_66_4_38_2.txt s1_65_34.txt 0.5 1 1 s1_65_34.txt -D 19,32,9,16 -K 1 -A -m 8 -I 2000000
run "step2 65 -> 64 rows" s1_65_34.txt s2_64_34.txt 0.5 1 2 s2_64_34.txt -K 1 -A -m 8 -I 30000000
cur=s2_64_34.txt; K="-K 1"; r=0
while [ $r -lt $MAXR ]; do
  for j in 1 2 3; do
    seed=$((100*(r+1)+j)); T=0.60; [ $j = 2 ] && T=0.55; [ $j = 3 ] && T=0.65
    run "round $r run $j (63 rows)" $cur r${r}_$j.txt $T 1 $seed r${r}_$j.txt $K -A -m 4 -I $MOVES &
  done; wait
  best=999999; pick=""
  for j in 1 2 3; do h=$(grep "round $r run $j " $LOG | sed 's/.*best=\([0-9]*\).*/\1/'); if [ "$h" -lt "$best" ]; then best=$h; pick=r${r}_$j.txt; fi; done
  echo "round $r: best $best holes in $pick (lowest hole count, lowest run number on ties)" >> $LOG
  if [ "$best" = 0 ]; then cp $pick CA_63_4_34_2.txt; echo "DONE CA_63_4_34_2.txt sha256 $(sha CA_63_4_34_2.txt)" >> $LOG; break; fi
  cur=$pick; K=""; r=$((r+1))
done
tail -n 2 $LOG
