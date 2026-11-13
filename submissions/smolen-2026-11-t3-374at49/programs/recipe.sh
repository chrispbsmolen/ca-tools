#!/bin/sh
# Rebuild CA(49;3,374,2) and its first 359 columns, CA(49;3,359,2), from the table's own CA(49;3,352,2).
# Run from the repository root. Needs python 3 with numpy and python-sat (CaDiCaL 1.5.3). Deterministic.
set -e
D=$(mktemp -d)
cp table/arrays/CA_49_3_352_2.txt $D/a352.txt
cp submissions/smolen-2026-11-t3-374at49/programs/alg2.py submissions/smolen-2026-11-t3-374at49/programs/qmodel.py $D/
cd $D
sha256sum a352.txt
python3 alg2.py | tail -1
python3 qmodel.py 3
python3 -c "
import numpy as np
A=np.loadtxt('CA_49_374_s3.txt',dtype=int); np.savetxt('CA_49_3_374_2.txt',A,fmt='%d'); np.savetxt('CA_49_3_359_2.txt',A[:,:359],fmt='%d')"
sha256sum CA_49_3_374_2.txt CA_49_3_359_2.txt
echo "output in $D"
