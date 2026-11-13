# blk.py r q : an r x q binary block in which any 3 distinct columns show all six non-constant triples (then every pair shows 01 and 10).
import sys, itertools
from pysat.solvers import Cadical153
r,q=int(sys.argv[1]),int(sys.argv[2])
v=lambda i,j:i*q+j+1
nv=r*q; cl=[]
for a,b,c in itertools.combinations(range(q),3):
    for pat in itertools.product([0,1],repeat=3):
        if len(set(pat))==1: continue
        sel=[]
        for i in range(r):
            nv+=1; sel.append(nv)
            for col,bit in zip((a,b,c),pat): cl.append([-nv, v(i,col) if bit else -v(i,col)])
        cl.append(sel)
S=Cadical153(bootstrap_with=cl); ok=S.solve(); print(r,q,'SAT' if ok else 'UNSAT')
if ok:
    mod=set(l for l in S.get_model() if l>0)
    open(f'B_{q}keys_{r}rows.txt','w').write('\n'.join(' '.join('1' if v(i,j) in mod else '0' for j in range(q)) for i in range(r))+'\n')
