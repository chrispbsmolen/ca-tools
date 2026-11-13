#!/bin/bash
# Recipe CA(131;4,169,2): extend own CA(130;4,167,2) (h000_fresh_20261113T0130.txt, sha256 3488ce29...) by 2 SA-optimised columns + 1 random row, then repi4.
set -e
IN=h000_fresh_20261113T0130.txt   # the table file table/arrays/CA_130_4_167_2.txt (same sha256), copied under this name
[ "$(sha256sum $IN | cut -c1-64)" = 3488ce29cad2349d27d23416623deb8c4f6d5e1e17d088d2590bf6ef0579754c ]
gcc -O2 -o colopt colopt.c -lm; gcc -O2 -o repi4 repi4.c -lm -lpthread
nice -n 10 ./colopt $IN 167 130 15 0.5 40000 5 2>/dev/null > c1.out
nice -n 10 ./colopt $IN 167 130 15 0.5 40000 6 2>/dev/null > c2.out
python3 - <<'PY'
import random
random.seed(1)
A=[l.split() for l in open('h000_fresh_20261113T0130.txt') if l.strip()]
c1=open('c1.out').read().split('\n')[1];c2=open('c2.out').read().split('\n')[1]
out=[' '.join(A[r]+[c1[r],c2[r]]) for r in range(130)]
out.append(' '.join(str(random.randint(0,1)) for _ in range(169)))
open('ext0.txt','w').write('\n'.join(out)+'\n')
PY
THREADS=1 nice -n 10 ./repi4 ext0.txt 1 0.25 200000 e1 2>&1 | tail -2
sha256sum ext0.txt e1_131.txt
