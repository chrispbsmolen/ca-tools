# build.py PTS OUT BX BY : words (t, t+u, t+v, x, y) for every point line of PTS ("x y u v"); array = block tables read through the words.
import sys, numpy as np, itertools, collections
pts=[tuple(map(int,l.split())) for l in open(sys.argv[1])]
W=np.array([(t,(t+u)%11,(t+v)%11,x,y) for (x,y,u,v) in pts for t in range(11)])
assert len(set(map(tuple,W)))==len(W)
viol=0
for r in (1,2):
    for S in itertools.combinations(range(5),r):
        T=[i for i in range(5) if i not in S]
        cs=collections.Counter(map(tuple,W[:,list(S)])); ct=collections.Counter(map(tuple,W[:,T]))
        viol+=sum(1 for w in W if cs[tuple(w[list(S)])]>1 and ct[tuple(w[T])]>1)
B=[np.loadtxt(f,dtype=int) for f in ('B_Q1.txt','B_Q2.txt','B_P.txt',sys.argv[3],sys.argv[4])]
A=np.vstack([B[i][:,W[:,i]] for i in range(5)])
np.savetxt(sys.argv[2],A,fmt='%d'); print('points',len(pts),'words',len(W),'split violations',viol,'array',A.shape)
