# lin3.py m n s K : a code over (11,11,11,m,n) from lines of Z11 x Z11. A word is (t, t+u, t+v, x, y); slab (x,y) holds points (u,v).
# Slab (0,0) holds s points that share no class line (u, v or v-u) with any other point. Every other slab holds at most one point.
# Slabs that share x or share y hold no two points on a common class line. No point is used twice. K points in all (CaDiCaL).
import sys, itertools
from pysat.solvers import Cadical153
from pysat.card import CardEnc, EncType
m,n,s,K=map(int,sys.argv[1:5])
P=[(u,v) for u in range(11) for v in range(11)]
def coll(p,q): return p[0]==q[0] or p[1]==q[1] or (p[1]-p[0]-q[1]+q[0])%11==0
near={p:[q for q in P if q!=p and coll(p,q)] for p in P}
slabs=[(x,y) for x in range(m) for y in range(n) if (x,y)!=(0,0)]
var={}
for p in P: var['S',p]=len(var)+1
for sl in slabs:
    for p in P: var[sl,p]=len(var)+1
cl=[]
for p in P:
    for q in near[p]:
        if p<q: cl.append([-var['S',p],-var['S',q]])
    for sl in slabs:
        cl.append([-var['S',p],-var[sl,p]])
        for q in near[p]: cl.append([-var['S',p],-var[sl,q]])
for sl in slabs:
    for a,b in itertools.combinations([var[sl,p] for p in P],2): cl.append([-a,-b])
for a,b in itertools.combinations(slabs,2):
    same=(a[0]==b[0] or a[1]==b[1])
    for p in P:
        cl.append([-var[a,p],-var[b,p]])
        if same:
            for q in near[p]: cl.append([-var[a,p],-var[b,q]])
top=len(var)
c1=CardEnc.equals(lits=[var['S',p] for p in P],bound=s,top_id=top,encoding=EncType.seqcounter); top=max(top,c1.nv); cl+=c1.clauses
reg=[var[sl,p] for sl in slabs for p in P]
if K-s==len(slabs):
    for sl in slabs: cl.append([var[sl,p] for p in P])
else:
    c2=CardEnc.atleast(lits=reg,bound=K-s,top_id=top,encoding=EncType.seqcounter); cl+=c2.clauses
# symmetry: translation of the plane and scaling keep the three classes: fix one special at (0,0)
if s>0: cl.append([var['S',(0,0)]])
S=Cadical153(bootstrap_with=cl); ok=S.solve()
print('m',m,'n',n,'s',s,'K',K,'SAT' if ok else 'UNSAT',flush=True)
if ok:
    mod=set(l for l in S.get_model() if l>0)
    with open(f'pts_{m}_{n}_{K}.txt','w') as f:
        for p in P:
            if var['S',p] in mod: f.write(f'0 0 {p[0]} {p[1]}\n')
        for sl in slabs:
            for p in P:
                if var[sl,p] in mod: f.write(f'{sl[0]} {sl[1]} {p[0]} {p[1]}\n')
