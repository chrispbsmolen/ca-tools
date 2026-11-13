# qmodel.py: build a 2-frameproof code over (11,11,11,8,4) from the quotient-plane model, then the 49-row array.
# words (a,b,c,x,y); slab (x,y) holds lines {(a0+t, a0+u+t, a0+v+t)} = point (u,v) of Q=Z11^2; classes: u, v, v-u.
import sys, itertools, random, numpy as np
from pysat.solvers import Cadical153
special=[(0,0),(1,2),(2,1)][:int(sys.argv[1])]   # s special points in slab (0,0)
seed=int(sys.argv[2]) if len(sys.argv)>2 else 1
random.seed(seed)
fu={p[0] for p in special}; fv={p[1] for p in special}; fd={(p[1]-p[0])%11 for p in special}
pts=[(u,v) for u in range(11) for v in range(11) if u not in fu and v not in fv and (v-u)%11 not in fd]
slabs=[(x,y) for x in range(8) for y in range(4) if (x,y)!=(0,0)]
var={}
for s in slabs:
    for p in pts: var[s,p]=len(var)+1
cl=[]
for s in slabs: cl.append([var[s,p] for p in pts])
def coll(p,q): return p[0]==q[0] or p[1]==q[1] or (p[1]-p[0]-q[1]+q[0])%11==0
for s,t in itertools.combinations(slabs,2):
    same=(s[0]==t[0] or s[1]==t[1])
    for p in pts:
        for q in pts:
            if (same and coll(p,q)) or p==q: cl.append([-var[s,p],-var[t,q]])
S=Cadical153(bootstrap_with=cl)
# random phase via assumptions-free shuffle: add a few random unit hints
ok=S.solve()
print('special',special,'regular candidates',len(pts),'SAT',ok)
if not ok: sys.exit()
m=set(l for l in S.get_model() if l>0)
assign={(0,0):list(special)}
for s in slabs: assign[s]=[p for p in pts if var[s,p] in m][:1]
words=[]
for (x,y),ps in assign.items():
    for (u,v) in ps:
        for t in range(11): words.append((t,(t+u)%11,(t+v)%11,x,y))
W=np.array(words); print('words',len(W),'distinct',len(set(words)))
np.savetxt(f'code_s{len(special)}.txt',W,fmt='%d')
B=[np.loadtxt(f'B_{n}.txt',dtype=int) for n in ('Q1','Q2','P','X','Y')]
A=np.vstack([B[i][:,W[:,i]] for i in range(5)])
np.savetxt(f'CA_49_{len(W)}_s{len(special)}.txt',A,fmt='%d'); print(A.shape)
