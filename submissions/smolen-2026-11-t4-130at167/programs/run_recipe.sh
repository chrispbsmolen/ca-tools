#!/bin/bash
# RECIPE for CA(130;4,167,2): Paley GF(167) chi(x+y), greedy row elimination to 114 kept rows, diagonal cells FREE,
# 16 free rows, ls2m (diagonal bits + free rows, hole list from holes4w), then repi4 exact cell repair.
# Run in an empty directory with the sources beside it. Stops on move/flip counts only. Seeds: ls2m 1, repi4 1.
set -e
LOG=recipe_log.txt; : > $LOG
sha(){ sha256sum "$1" | awk '{print $1}'; }
log(){ echo "$@" | tee -a $LOG; }
log "RECIPE CA(130;4,167,2) started $(date -u +%FT%TZ)"
for f in greedy.c holes4w.c ls2m.c build4.py repi4.c; do log "source $f sha256 $(sha $f)"; done
gcc -O3 -march=native -o greedy greedy.c
gcc -O3 -march=native -o holes4w holes4w.c 2>/dev/null
gcc -O3 -o ls2m ls2m.c -lm 2>/dev/null
gcc -O3 -march=native -pthread -o repi4 repi4.c -lm
log "cmd: ./greedy 167 114 (deterministic row elimination, fixed diagonal 0)"; ./greedy 167 114 > greedy114.log
grep '^MASK' greedy114.log | awk '{print $2}' > mask_114.txt; log "mask_114.txt sha256 $(sha mask_114.txt)"
log "cmd: ./holes4w 167 mask_114.txt need_114.txt"; ./holes4w 167 mask_114.txt need_114.txt | tee -a $LOG
log "need_114.txt sha256 $(sha need_114.txt)"
log "cmd: ./ls2m 167 16 need_114.txt 0.35 -8000000 1 > p16.out   (negative secs = move count 8,000,000)"; nice -n 10 ./ls2m 167 16 need_114.txt 0.35 -8000000 1 > p16.out 2> p16.err
log "p16.out sha256 $(sha p16.out) first line: $(head -1 p16.out)"
python3 build4.py mask_114.txt p16.out p16_start.txt | tee -a $LOG
log "p16_start.txt sha256 $(sha p16_start.txt)"
log "cmd: THREADS=1 ./repi4 p16_start.txt 1 0.25 3000 p16r"; THREADS=1 nice -n 10 ./repi4 p16_start.txt 1 0.25 3000 p16r > p16r.out 2> p16r.err || true
log "repi4 end: $(tail -1 p16r.err)"
log "p16r_130.txt sha256 $(sha p16r_130.txt)"
log "expected original sha256 3488ce29cad2349d27d23416623deb8c4f6d5e1e17d088d2590bf6ef0579754c"
if [ "$(sha p16r_130.txt)" = "3488ce29cad2349d27d23416623deb8c4f6d5e1e17d088d2590bf6ef0579754c" ]; then log "REPRODUCED EXACTLY"; else log "DIFFERENT from original"; fi
log "finished $(date -u +%FT%TZ)"
