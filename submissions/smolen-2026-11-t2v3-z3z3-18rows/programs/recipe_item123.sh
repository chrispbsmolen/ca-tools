#!/bin/bash
# recipe_item123.sh  (item123, 2026-11-10)  Builds from nothing, and logs with hashes (DECISIONS B7):
#   CA(18;2,52,3)   exhaustive orbit search, group Z3 x Z3 on 18 rows (no input array, no random numbers)
#   CA(30;2,975,3)  profile product of that array with the table's own CA(15;2,20,3)
#   CA(24;2,209,3)  profile product with the orthogonal array OA(9,4,3), then seeded column extension (ext2t),
#                   stopped on a COUNT: the array saved after the 14th added column (209 columns).
# usage: bash recipe_item123.sh TAG      (writes everything into the new folder run_TAG/ and RECIPE_TAG.log)
# Needs cc, python3, sha256sum or shasum. The only input file is CA_15_2_20_3_fd13075b.txt (ca-tools table/arrays).
set -e
cd "$(dirname "$0")"; TAG=${1:?give a tag}; D=run_$TAG; [ -e "$D" ] && { echo "$D exists, nothing overwritten"; exit 1; }
mkdir "$D"; LOG=$PWD/RECIPE_$TAG.log; : > "$LOG"
sha(){ if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -c1-64; else shasum -a 256 "$1" | cut -c1-64; fi; }
say(){ echo "$*" | tee -a "$LOG"; }
say "recipe_item123 tag $TAG on $(uname -sm); cc: $(cc --version | head -1); python: $(python3 --version 2>&1)"
for f in recipe_item123.sh orbq7.c mkgrp.py pprod.py ext2t.c chk.py CA_15_2_20_3_fd13075b.txt; do say "sha256 $f $(sha $f)"; done
cc -O3 -o "$D/orbq7" orbq7.c; cc -O3 -o "$D/ext2t" ext2t.c -lm
cd "$D"
C="python3 ../mkgrp.py z3z3 a,a,b,b,c,c 0 > z_18_aabbcc_f0.txt"; python3 ../mkgrp.py z3z3 a,a,b,b,c,c 0 > z_18_aabbcc_f0.txt
say "step1 | $C | out z_18_aabbcc_f0.txt $(sha z_18_aabbcc_f0.txt)"
C="./orbq7 z_18_aabbcc_f0.txt 4 20 w18"; ./orbq7 z_18_aabbcc_f0.txt 4 20 w18 > step2.out 2>&1
say "step2 | $C | no seed, runs to completion | out w18_dump_18_52.txt $(sha w18_dump_18_52.txt) | $(grep COMPLETE step2.out) | $(grep histogram step2.out)"
cp w18_dump_18_52.txt CA_18_2_52_3.txt; say "check | $(python3 ../chk.py CA_18_2_52_3.txt 2 3)"
C="python3 ../pprod.py CA_18_2_52_3.txt 0 1 ../CA_15_2_20_3_fd13075b.txt 0 3 CA_30_2_975_3.txt"; $C > step3.out 2>&1
say "step3 | $C | out CA_30_2_975_3.txt $(sha CA_30_2_975_3.txt) | $(tail -n 1 step3.out)"; say "check | $(python3 ../chk.py CA_30_2_975_3.txt 2 3)"
python3 -c "open('oa9.txt','w').write(''.join('%d %d %d %d\n'%(i,j,(i+j)%3,(i+2*j)%3) for i in range(3) for j in range(3)))"
say "step4 | rows (i, j, i+j, i+2j) mod 3 for i, j in 0..2 | out oa9.txt $(sha oa9.txt) | $(python3 ../chk.py oa9.txt 2 3)"
C="python3 ../pprod.py CA_18_2_52_3.txt 0 1 oa9.txt 0 1 p24_195.txt"; $C > step5.out 2>&1
say "step5 | $C | out p24_195.txt $(sha p24_195.txt) | $(tail -n 1 step5.out)"
mkdir out
C="./ext2t p24_195.txt 24 195 0 0 13 100000 0.7 out/t24a -chain 30 -ntry 200 -kick 200000"
# seed 13. The program adds one column at a time and saves the array after each. The recipe takes the array saved at
# 209 columns (the 14th added column) and then stops the program. The seconds argument (100000) is only an abort limit.
$C > step6.out 2>&1 & PID=$!
while [ ! -f out/t24a_24_209.txt ] && kill -0 $PID 2>/dev/null; do sleep 2; done; sleep 2; kill $PID 2>/dev/null; wait $PID 2>/dev/null || true
say "step6 | $C | seed 13, stopped after the array at 209 columns was saved | in p24_195.txt $(sha p24_195.txt) | out out/t24a_24_209.txt $(sha out/t24a_24_209.txt) | $(grep '_209.txt' step6.out | tail -n 1)"
cp out/t24a_24_209.txt CA_24_2_209_3.txt; say "check | $(python3 ../chk.py CA_24_2_209_3.txt 2 3)"
for f in CA_18_2_52_3.txt CA_30_2_975_3.txt CA_24_2_209_3.txt; do say "DONE $f sha256 $(sha $f)"; done
