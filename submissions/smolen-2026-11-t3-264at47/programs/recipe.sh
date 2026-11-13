#!/bin/sh
# Rebuild CA(47;3,264,2) from the table's own CA(49;3,352,2).
# Run from the repository root. Needs python 3 with numpy and python-sat (CaDiCaL 1.5.3). Deterministic, no random seed.
set -e
P=submissions/smolen-2026-11-t3-264at47/programs
D=$(mktemp -d)
cp table/arrays/CA_49_3_352_2.txt $D/a352.txt
cp $P/alg2.py $P/blk.py $P/lin3.py $P/build.py $D/
cd $D
python3 -c "import sys,pysat,numpy;print('python',sys.version.split()[0],'numpy',numpy.__version__,'python-sat',pysat.__version__)"
sha256sum a352.txt alg2.py blk.py lin3.py build.py
python3 alg2.py | tail -1
python3 blk.py 8 5
python3 lin3.py 5 4 5 24
python3 build.py pts_5_4_24.txt CA_47_3_264_2.txt B_5keys_8rows.txt B_Y.txt
sha256sum B_Q1.txt B_Q2.txt B_P.txt B_Y.txt B_5keys_8rows.txt pts_5_4_24.txt CA_47_3_264_2.txt
