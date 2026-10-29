# gen.py t p s n seed out : random cyclic family over GF(p), p prime: rows A^a (A companion of a
# primitive polynomial of degree t, so A has projective order m=(p^t-1)/(p-1)), s orbits with random seeds.
import sys, random, itertools
t,p,s,n,seed,out=int(sys.argv[1]),int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4]),int(sys.argv[5]),sys.argv[6]
random.seed(seed); m=(p**t-1)//(p-1)
def mat_mul(A,B): return [[sum(A[i][k]*B[k][j] for k in range(t))%p for j in range(t)] for i in range(t)]
def mat_pow(A,e):
    R=[[int(i==j) for j in range(t)] for i in range(t)]
    while e:
        if e&1: R=mat_mul(R,A)
        A=mat_mul(A,A); e>>=1
    return R
def is_scalar(M): return all(M[i][j]==(M[0][0] if i==j else 0) for i in range(t) for j in range(t))
def proj_order_ok(A):
    if not is_scalar(mat_pow(A,m)): return False
    for r in set(f for f in range(2,m+1) if m%f==0 and all(f%d for d in range(2,int(f**.5)+1))):
        if is_scalar(mat_pow(A,m//r)): return False
    return True
while True:
    c=[random.randrange(p) for _ in range(t)]
    if c[0]==0: continue
    A=[[0]*t for _ in range(t)]
    for i in range(1,t): A[i][i-1]=1
    for i in range(t): A[i][t-1]=c[i]
    if proj_order_ok(A): break
from math import gcd
lines=[f"# random cyclic family t={t} q={p} n={n} k={m*s} m={m} s={s} seed={seed}"]
for r in range(n):
    while True:
        a=random.randrange(1,m)
        if gcd(a,m)==1: break
    B=mat_pow(A,a)
    seeds=[[random.randrange(p) for _ in range(t)] for _ in range(s)]
    for x in seeds:
        if not any(x): x[0]=1
    row=[None]*(m*s)
    for i in range(s):
        v=seeds[i]
        for cc in range(m):
            code=0
            for j in range(t): code=code*p+v[j]
            row[cc*s+i]=code
            v=[sum(B[ii][jj]*v[jj] for jj in range(t))%p for ii in range(t)]
    lines.append(" ".join(map(str,row)))
open(out,"w").write("\n".join(lines)+"\n")
