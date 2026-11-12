#!/bin/bash
# RECIPE for CA(345;5,192,2). Run in an empty directory with the sources beside it (need5s.c expand.py genpw.py subselw.c mklist.py build.py ls2m.c repi.c).
# Construction: Paley chi(x+y) over GF(337), free diagonal, 192 columns chosen by weighted-cost swap annealing (subselw, weight 1/nopt),
# 8 free rows set by ls2m (diagonal bits + free rows), then four stages of exact single-cell repair by repi.c (incremental, deterministic).
# THREADS is part of the recipe (stages 1-2 THREADS=1, stages 3-4 THREADS=2). Everything stops on move or flip counts, never on a clock or a kill.
# Seeds: subselw 2, ls2m 1, repi 21 / 31 / 41 / 77.
set -e
LOG=recipe_log.txt; : > $LOG
sha(){ sha256sum "$1" | awk '{print $1}'; }
log(){ echo "$@" | tee -a $LOG; }
chk(){ if [ "$(sha $1)" = "$2" ]; then log "  MATCH original $1 $2"; else log "  DIFFERENT from original $1 (original $2)"; fi; }
log "RECIPE CA(345;5,192,2) started $(date -u +%FT%TZ)"
for f in need5s.c expand.py genpw.py subselw.c mklist.py build.py ls2m.c repi.c; do log "source $f sha256 $(sha $f)"; done
gcc -O3 -march=native -o need5s need5s.c
gcc -O3 -o subselw subselw.c -lm 2>/dev/null
gcc -O3 -o ls2m ls2m.c -lm 2>/dev/null
gcc -O3 -march=native -pthread -o repi repi.c -lm
log "cmd: ./need5s 337 > need337.txt"; nice -n 10 ./need5s 337 > need337.txt 2> need337.err; log "need337.txt sha256 $(sha need337.txt) lines $(wc -l < need337.txt)"
log "cmd: python3 expand.py (need337_full.npz, 226464 pairs)"; python3 expand.py 2>&1 | tee -a $LOG
python3 genpw.py; log "pw_winv.txt sha256 $(sha pw_winv.txt)"
log "cmd: ./subselw 337 192 pw_winv.txt 1500000 2 0.5 sub_A.txt   (swarm: lineage A, weighted cost 1/nopt, seed 2, T 0.5)"; nice -n 10 ./subselw 337 192 pw_winv.txt 1500000 2 0.5 sub_A.txt 2>/dev/null | tee -a $LOG
log "sub_A.txt sha256 $(sha sub_A.txt)"
log "cmd: python3 mklist.py sub_A.txt need_A.txt"; python3 mklist.py sub_A.txt need_A.txt | tee -a $LOG
log "need_A.txt sha256 $(sha need_A.txt)"
log "cmd: ./ls2m 337 8 need_A.txt 0.35 -35363840 1 > A_ls2.out   (negative secs = move count)"; nice -n 10 ./ls2m 337 8 need_A.txt 0.35 -35363840 1 > A_ls2.out 2> A_ls2.err
log "A_ls2.out sha256 $(sha A_ls2.out) first line: $(head -1 A_ls2.out)"
python3 build.py sub_A.txt A_ls2.out A_start.txt | tee -a $LOG
log "A_start.txt sha256 $(sha A_start.txt) (345 rows, 163 holes)"; chk A_start.txt e7637382f7eaa23d3132dfba185e3e1b1a227382b7b7c32217587952cfa35128
log "STAGE 1: THREADS=1 ./repi A_start.txt 21 0.35 400 r1   (best state at acc 353, 4 holes)"
THREADS=1 nice -n 10 ./repi A_start.txt 21 0.35 400 r1 > r1.out 2> r1.err || true
log "r1_best.txt sha256 $(sha r1_best.txt) ($(grep -v progress r1.err | tail -2 | head -1))"; chk r1_best.txt d0b3bc1360f87f1db0300626a4093dd2a2560943ee0d2dd112249adf5b9b9a32
log "STAGE 2: THREADS=1 ./repi r1_best.txt 31 0.22 400 r2   (3 holes)"
THREADS=1 nice -n 10 ./repi r1_best.txt 31 0.22 400 r2 > r2.out 2> r2.err || true
log "r2_best.txt sha256 $(sha r2_best.txt) ($(grep -v progress r2.err | tail -2 | head -1))"; chk r2_best.txt fa4ae57105f51e592372c469105916e7993ef87bb4d62f12cc711e141928743d
log "STAGE 3: THREADS=2 ./repi r2_best.txt 41 0.2 200 r3   (1 hole at acc 186)"
THREADS=2 nice -n 10 ./repi r2_best.txt 41 0.2 200 r3 > r3.out 2> r3.err || true
log "r3_best.txt sha256 $(sha r3_best.txt) ($(grep -v progress r3.err | tail -2 | head -1))"; chk r3_best.txt 6a28139e0fd78aaaae8bfeb782ed90654b7d6b00ecf189448d6d413c6476b4cc
log "STAGE 4: THREADS=2 ./repi r3_best.txt 77 0.2 3000 r4   (zero)"
THREADS=2 nice -n 10 ./repi r3_best.txt 77 0.2 3000 r4 > r4.out 2> r4.err || true
log "r4 end: $(tail -1 r4.err)"
log "r4_345.txt sha256 $(sha r4_345.txt)"; chk r4_345.txt 00b38ecd6c3734d069e291c060c81e57d94511c27001ae042d63fe41a964a518
log "finished $(date -u +%FT%TZ)"
