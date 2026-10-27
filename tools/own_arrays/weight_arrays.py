#!/usr/bin/env python3
"""Algebraic binary arrays built here (2026-10-27), no external ingredient.
 (a) k = t+1: all vectors of even weight in {0,1}^(t+1): an OA of strength t with 2^t runs.
 (b) k = t+2: all vectors whose weight lies in a residue class set W hitting every window of
     three consecutive weights {a, a+1, a+2}, a = 0..t: for a pair of columns and any fixed
     assignment of the other t columns of weight a, the four completions have weights a, a+1,
     a+1, a+2, so one of them is in the array. W = {2,5,8} for t = 6 (85 runs), {2,5} for t = 5
     (42), {1,4} for t = 4 (21), {1,4} for t = 3 (10). These sizes equal the Johnson-Entringer
     values floor((2^(t+2) - 1)/3) that Colbourn's table lists.
Usage: weight_arrays.py outdir"""
import itertools, sys, os
out=sys.argv[1]
def write(fn, rows):
    with open(os.path.join(out,fn),'w') as f:
        for r in rows: f.write(' '.join(map(str,r))+'\n')
    print(fn, len(rows), 'rows')
for t in (4,5,6):
    k=t+1
    rows=[v for v in itertools.product((0,1),repeat=k) if sum(v)%2==0]
    write(f'oa_{len(rows)}_{t}_{k}_2.txt', rows)
W={3:{1,4},4:{1,4},5:{2,5},6:{2,5,8}}
for t,ws in W.items():
    k=t+2
    rows=[v for v in itertools.product((0,1),repeat=k) if sum(v) in ws]
    write(f'wt_{len(rows)}_{t}_{k}_2.txt', rows)
