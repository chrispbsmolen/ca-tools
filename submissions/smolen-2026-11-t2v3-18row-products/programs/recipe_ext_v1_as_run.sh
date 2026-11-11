#!/bin/bash
# recipe_ext.sh TAG ROWS...  (item123 step 29)  e.g.  bash recipe_ext.sh A 31 35 37
# For each row count: profile product of the CA(18;2,52,3) with an own array (pprod.py, no search), then column extension
# with ext2t.c (seed 13, temperature 0.7, -ntry 200, -kick 200000), one column at a time. The recipe takes the array saved
# at the stated number of columns and then stops the program: a COUNT, never the clock (the seconds argument is an abort
# limit only). Writes run_ext_TAG/ and RECIPE_ext_TAG.log with the sha256 of every program, input and output.
# A row count whose final file already exists in run_ext_TAG/ is skipped, so an interrupted recipe can be continued.
cd "$(dirname "$0")"; TAG=${1:?tag}; shift; D=run_ext_$TAG; mkdir -p "$D/out"; LOG=RECIPE_ext_$TAG.log
sha(){ if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -c1-64; else shasum -a 256 "$1" | cut -c1-64; fi; }
say(){ echo "$*" | tee -a $LOG; }
say "recipe_ext tag $TAG rows $* on $(uname -sm); cc: $(cc --version | head -1); python: $(python3 --version 2>&1); $(date -u +%FT%TZ)"
for f in recipe_ext.sh pprod.py ext2t.c CA_18_2_52_3.txt CA_16_2_21_3_81545e9f.txt CA_20_2_61_3_b108f1a5.txt CA_21_2_93_3.txt CA_22_2_107_3_eed6545c.txt; do say "sha256 $f $(sha $f)"; done
[ -x "$D/ext2t" ] || cc -O3 -o "$D/ext2t" ext2t.c -lm
for N in "$@"; do
  case $N in
    31) B=CA_16_2_21_3_81545e9f.txt; R="0 8";   K0=1066; K1=1252; CH=600;;
    33) B=CA_18_2_52_3.txt;          R="0 1";   K0=2535; K1=2637; CH=900;;
    35) B=CA_20_2_61_3_b108f1a5.txt; R="0 3";   K0=3003; K1=3355; CH=900;;
    36) B=CA_21_2_93_3.txt;          R="14 20"; K0=4563; K1=4914; CH=1500;;
    37) B=CA_22_2_107_3_eed6545c.txt; R="15 16"; K0=5252; K1=5730; CH=1500;;
    *) echo "unknown row count $N"; exit 1;;
  esac
  FIN=$D/CA_${N}_2_${K1}_3.txt
  if [ -f $FIN ]; then say "rows $N: $FIN exists, skipped"; continue; fi
  C1="python3 pprod.py CA_18_2_52_3.txt 0 1 $B $R $D/p${N}_$K0.txt"; $C1 > $D/p$N.out 2>&1
  say "rows $N step 1 | $C1 | $(tail -n 1 $D/p$N.out) | out p${N}_$K0.txt $(sha $D/p${N}_$K0.txt)"
  rm -f $D/out/t${N}_*
  C2="./ext2t p${N}_$K0.txt $N $K0 0 0 13 1000000 0.7 out/t$N -chain $CH -ntry 200 -kick 200000"
  ( cd $D && $C2 > e$N.out 2>&1 ) & PID=$!
  while [ ! -f $D/out/t${N}_${N}_$K1.txt ] && kill -0 $PID 2>/dev/null; do sleep 3; done; sleep 3; kill $PID 2>/dev/null; wait $PID 2>/dev/null
  cp $D/out/t${N}_${N}_$K1.txt $FIN
  say "rows $N step 2 | $C2 | seed 13, stopped after the array at $K1 columns was saved | $(grep "_$K1.txt" $D/e$N.out | tail -n 1) | out $(basename $FIN) $(sha $FIN)"
done
say "recipe_ext tag $TAG finished $(date -u +%FT%TZ)"
