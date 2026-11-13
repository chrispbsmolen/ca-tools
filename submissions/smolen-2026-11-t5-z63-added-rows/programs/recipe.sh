#!/bin/sh
# Rebuild CA(128;5,32,2), CA(132;5,35,2) and CA(134;5,36,2) from the binary vector f on Z63 alone.
# Run from the repository root. Needs a C compiler and python 3. Deterministic: fixed seeds, searches stop on a move count.
set -e
P=$(pwd)/submissions/smolen-2026-11-t5-z63-added-rows/programs
D=$(mktemp -d)
cp $P/bad5.c $P/pick2.py $P/mk2.py $P/joint.c $P/mk3.py $D/
cd $D
F=011011011010001111001100000010111011000110100001010100011101111
python3 -c "import sys;print('python',sys.version.split()[0])"; cc --version | head -1
sha256sum bad5.c pick2.py mk2.py joint.c mk3.py
cc -O3 -o bad5 bad5.c && cc -O3 -o joint joint.c -lm
./bad5 $F > bad63.txt; sha256sum bad63.txt
python3 pick2.py 32 1 1 12 | tail -1 > found32.txt; cat found32.txt
python3 mk2.py CA_128_5_32_2.txt $(sed 's/.* D //' found32.txt)
./joint 35 3 1 4000000 0.5 > j_35_3.txt; head -1 j_35_3.txt
./joint 36 4 2 8000000 0.3 > j_36_4.txt; head -1 j_36_4.txt
python3 mk3.py CA_132_5_35_2.txt j_35_3.txt
python3 mk3.py CA_134_5_36_2.txt j_36_4.txt
sha256sum CA_128_5_32_2.txt CA_132_5_35_2.txt CA_134_5_36_2.txt
