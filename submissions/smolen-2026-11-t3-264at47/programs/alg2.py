import numpy as np, itertools, collections
A=np.array([l.split() for l in open('a352.txt') if l.strip()],dtype=int)
blocks={'Q1':range(0,11),'Q2':range(11,22),'P':range(22,33),'X':range(33,43),'Y':range(43,49)}
W=[];mats={}
for n,rows in blocks.items():
    pats={};key=[]
    for c in range(352):
        t=tuple(A[list(rows),c]); key.append(pats.setdefault(t,len(pats)))
    W.append(key); mats[n]=np.array(list(pats.keys())).T; print(n,mats[n].shape)
W=np.array(W).T
np.save('words352.npy',W)
for n,M in mats.items():
    np.savetxt(f'B_{n}.txt',M,fmt='%d')
    q=M.shape[1]; bad=0; hist=collections.Counter()
    for a,b,c in itertools.combinations(range(q),3):
        s=set(zip(M[:,a],M[:,b],M[:,c])); miss=[p for p in itertools.product([0,1],repeat=3) if p not in s]
        hist[tuple(miss)]+=1
    pb=0
    for a,b in itertools.permutations(range(q),2):
        if len(set(zip(M[:,a],M[:,b])))<4: pb+=1
    print(n,'triple miss hist',dict(hist),'pairs lacking a pattern',pb)
# frameproof check
n=5; viol=0
for r in range(1,3):
    for S in itertools.combinations(range(n),r):
        T=[i for i in range(n) if i not in S]
        cs=collections.Counter(map(tuple,W[:,list(S)])); ct=collections.Counter(map(tuple,W[:,T]))
        v=sum(1 for w in W if cs[tuple(w[list(S)])]>1 and ct[tuple(w[T])]>1); viol+=v
        print(S,'S-classes',len(cs),'T-classes',len(ct),'viol',v)
print('total FP violations',viol)
