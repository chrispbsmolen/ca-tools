#!/usr/bin/env python3
"""pprod.py A i j B p q OUT : profile product (method: Colbourn & Torres-Jimenez 2013, Thm 4.2 / Cor 4.5; own code).
A = CA(N;2,k,3) with rows i,j agreeing in d1 columns (set K2); B = CA(M;2,l,3) with rows p,q agreeing in d2 columns (set L2).
Result CA(N+M-3; 2, k*l - d1*d2, 3): rename per column so A[i]=0 everywhere, A[j]=2 off K2 (0 on K2); B[p]=1 everywhere,
B[q]=2 off L2 (1 on L2). Drop rows A[i], B[p]; merge A[j], B[q] into one row; drop columns K2 x L2."""
import sys
def read(fn):
    return [list(map(int,l.split())) for l in open(fn) if l.strip()]
def ren(A,i,j,vi,vj):
    k=len(A[0]);B=[r[:] for r in A]
    for c in range(k):
        perm={A[i][c]:vi}
        if A[j][c]!=A[i][c]: perm[A[j][c]]=vj
        src=[s for s in range(3) if s not in perm]; dst=[s for s in range(3) if s not in perm.values()]
        for s,d in zip(src,dst): perm[s]=d
        for r in range(len(A)): B[r][c]=perm[A[r][c]]
    return B
A=read(sys.argv[1]);i,j=int(sys.argv[2]),int(sys.argv[3]);B=read(sys.argv[4]);p,q=int(sys.argv[5]),int(sys.argv[6])
A=ren(A,i,j,0,2);B=ren(B,p,q,1,2)
k=len(A[0]);l=len(B[0])
K2=set(c for c in range(k) if A[j][c]==0);L2=set(c for c in range(l) if B[q][c]==1)
cols=[(a,b) for a in range(k) for b in range(l) if not (a in K2 and b in L2)]
rows=[]
for r in range(len(A)):
    if r in (i,j): continue
    rows.append([A[r][a] for a,b in cols])
for r in range(len(B)):
    if r in (p,q): continue
    rows.append([B[r][b] for a,b in cols])
m=[]
for a,b in cols:
    if a in K2: m.append(A[j][a])      # b in L1: A value (0)
    elif b in L2: m.append(B[q][b])    # a in K1: B value (1)
    else: m.append(2)
rows.append(m)
open(sys.argv[7],'w').write(''.join(' '.join(map(str,r))+'\n' for r in rows))
print('rows',len(rows),'cols',len(cols),'d1',len(K2),'d2',len(L2))
