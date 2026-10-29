# genpp.py t q s n seed out : random cyclic family over GF(q), q a prime power <= 16 (Conway polynomials as in
# repcheck_pp.c / gfield.h); rows A^a with A a companion matrix of projective order m=(q^t-1)/(q-1).
import sys, random
from math import gcd
t,q,s,n,seed,out=[int(x) for x in sys.argv[1:6]]+[sys.argv[6]]
random.seed(seed)
p=next(d for d in range(2,q+1) if q%d==0); e=1
while p**e<q: e+=1
F={4:[1,1],8:[1,1,0],9:[2,2],16:[1,1,0,0]}.get(q)
def dig(a): return [(a//p**i)%p for i in range(e)]
def code(c): return sum(c[i]*p**i for i in range(e))
def add(a,b): return code([(x+y)%p for x,y in zip(dig(a),dig(b))])
def mul(a,b):
    A,B=dig(a),dig(b); pr=[0]*(2*e)
    for i in range(e):
        for j in range(e): pr[i+j]=(pr[i+j]+A[i]*B[j])%p
    for d in range(2*e-2,e-1,-1):
        c=pr[d]
        if c:
            pr[d]=0
            for i in range(e): pr[d-e+i]=(pr[d-e+i]-c*F[i])%p
    return code(pr[:e])
MUL=[[mul(a,b) for b in range(q)] for a in range(q)]; ADD=[[add(a,b) for b in range(q)] for a in range(q)]
m=(q**t-1)//(q-1)
def mm(A,B):
    R=[[0]*t for _ in range(t)]
    for i in range(t):
        for j in range(t):
            s_=0
            for k in range(t): s_=ADD[s_][MUL[A[i][k]][B[k][j]]]
            R[i][j]=s_
    return R
def mp(A,x):
    R=[[int(i==j) for j in range(t)] for i in range(t)]
    while x:
        if x&1: R=mm(R,A)
        A=mm(A,A); x>>=1
    return R
def scal(M): return all(M[i][j]==(M[0][0] if i==j else 0) for i in range(t) for j in range(t))
pf=[f for f in range(2,m+1) if m%f==0 and all(f%d for d in range(2,int(f**.5)+1))]
while True:
    c=[random.randrange(q) for _ in range(t)]
    if c[0]==0: continue
    A=[[0]*t for _ in range(t)]
    for i in range(1,t): A[i][i-1]=1
    for i in range(t): A[i][t-1]=c[i]
    if scal(mp(A,m)) and not any(scal(mp(A,m//f)) for f in pf): break
lines=[f"# random cyclic family t={t} q={q} n={n} k={m*s} m={m} s={s} seed={seed}"]
for r in range(n):
    while True:
        a=random.randrange(1,m)
        if gcd(a,m)==1: break
    B=mp(A,a); row=[0]*(m*s)
    for i in range(s):
        v=[random.randrange(q) for _ in range(t)]
        if not any(v): v[0]=1
        for cc in range(m):
            cd=0
            for j in range(t): cd=cd*q+v[j]
            row[cc*s+i]=cd
            nv=[]
            for ii in range(t):
                s_=0
                for jj in range(t): s_=ADD[s_][MUL[B[ii][jj]][v[jj]]]
                nv.append(s_)
            v=nv
    lines.append(" ".join(map(str,row)))
open(out,"w").write("\n".join(lines)+"\n")
