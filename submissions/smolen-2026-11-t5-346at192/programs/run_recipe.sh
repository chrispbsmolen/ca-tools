#!/bin/bash
# RECIPE for CA(346;5,192,2): Paley GF(337), free diagonal, 192 columns, 9 free rows, exact cell repair. Run in an empty directory with the sources beside it.
# Stops on move/iteration counts only. Seeds: subsel 1, ls2m 1, repcm 1 and 2.
set -e
LOG=recipe_log.txt; : > $LOG
sha(){ sha256sum "$1" | awk '{print $1}'; }
log(){ echo "$@" | tee -a $LOG; }
log "RECIPE CA(346;5,192,2) started $(date -u +%FT%TZ)"
for f in need5s.c expand.py subsel.c mklist.py build.py ls2m.c repcm.c; do log "source $f sha256 $(sha $f)"; done
gcc -O3 -march=native -o need5s need5s.c
gcc -O3 -o subsel subsel.c -lm
gcc -O3 -o ls2m ls2m.c -lm 2>/dev/null
gcc -O3 -march=native -o repcm repcm.c -lm
log "cmd: ./need5s 337 > need337.txt"; nice -n 10 ./need5s 337 > need337.txt 2> need337.err; log "need337.txt sha256 $(sha need337.txt) lines $(wc -l < need337.txt)"
log "cmd: python3 expand.py (writes need337_full.npz) then pairs_cols.txt"; python3 expand.py 2>&1 | tee -a $LOG
python3 - <<'PY'
import numpy as np
d=np.load('need337_full.npz'); np.savetxt('pairs_cols.txt',d['C'],fmt='%d')
PY
log "pairs_cols.txt sha256 $(sha pairs_cols.txt)"
log "cmd: ./subsel 337 192 pairs_cols.txt 1500000 1 1.0 sub_T1.0.txt"; nice -n 10 ./subsel 337 192 pairs_cols.txt 1500000 1 1.0 sub_T1.0.txt 2>&1 | tail -1 | tee -a $LOG
log "sub_T1.0.txt sha256 $(sha sub_T1.0.txt)"
log "cmd: python3 mklist.py sub_T1.0.txt need_sub.txt"; python3 mklist.py sub_T1.0.txt need_sub.txt | tee -a $LOG
log "need_sub.txt sha256 $(sha need_sub.txt)"
log "cmd: ./ls2m 337 9 need_sub.txt 0.35 -35363840 1 > ls2_a.out   (negative secs = move count 35363840)"; nice -n 10 ./ls2m 337 9 need_sub.txt 0.35 -35363840 1 > ls2_a.out 2> ls2_a.err
log "ls2_a.out sha256 $(sha ls2_a.out) first line: $(head -1 ls2_a.out)"
log "cmd: python3 build.py sub_T1.0.txt ls2_a.out A346_start.txt"; python3 build.py sub_T1.0.txt ls2_a.out A346_start.txt | tee -a $LOG
log "A346_start.txt sha256 $(sha A346_start.txt)"
log "cmd: MAXIT=99 ./repcm A346_start.txt 0 1 0 0.5 r1"; MAXIT=99 nice -n 10 ./repcm A346_start.txt 0 1 0 0.5 r1 > r1.out 2> r1.err || true
log "r1_cur_346.txt sha256 $(sha r1_cur_346.txt) ($(tail -2 r1.err | head -1))"
cp r1_cur_346.txt s2_in.txt
log "cmd: MAXIT=100000 ./repcm s2_in.txt 0 2 0 0.5 r2"; MAXIT=100000 nice -n 10 ./repcm s2_in.txt 0 2 0 0.5 r2 > r2.out 2> r2.err || true
log "r2_346.txt sha256 $(sha r2_346.txt) ($(tail -3 r2.err | head -1))"
log "expected original sha256 1c304d397c3de1576eb7380fc8e68a8aa024fe995bd98fbf7b8ced58df2edd83"
if [ "$(sha r2_346.txt)" = "1c304d397c3de1576eb7380fc8e68a8aa024fe995bd98fbf7b8ced58df2edd83" ]; then log "REPRODUCED EXACTLY"; else log "DIFFERENT from original"; fi
log "finished $(date -u +%FT%TZ)"
