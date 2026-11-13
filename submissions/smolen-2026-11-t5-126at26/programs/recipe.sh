#!/bin/bash
# Rebuild CA(126;5,26,2) and CA(126;5,28,2). Run from the repository root. Needs gcc and python 3. Deterministic (fixed seeds).
set -e
P=$(pwd)/submissions/smolen-2026-11-t5-126at26/programs
D=$(mktemp -d); cd $D
gcc -O3 -o gdev $P/gdev.c -lm
gcc -O3 -o palsub $P/palsub.c -lm
python3 $P/mkcls.py zn 63 2 > c_63_2.txt
TOP=1 ./gdev 63 0 cls 1 0 1 c_63_2.txt | sed -n 2p | sed 's/.*f=//' > f63.txt
cat f63.txt
./gdev 63 0 scan 0 0 0 f63.txt
./palsub bad.bin 63 26 1 20000000 0.3 > D26.out
./palsub bad.bin 63 28 1 20000000 0.3 > D28.out
tail -1 D26.out; tail -1 D28.out
python3 $P/build.py f63.txt D26.out CA_126_5_26_2.txt
python3 $P/build.py f63.txt D28.out CA_126_5_28_2.txt
sha256sum CA_126_5_26_2.txt CA_126_5_28_2.txt
echo "output in $D"
