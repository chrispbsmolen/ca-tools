import sys, numpy as np, random
q=337
chi=[0]*q
for i in range(1,q): chi[i*i%q]=1
pairs=set()
for line in open('need337.txt'):
    b,c,d,e,p=map(int,line.split())
    cols=[0,b,c,d,e]; bits=[(p>>j)&1 for j in range(5)]
    for t in range(q):
        cc=[(x+t)%q for x in cols]
        key=tuple(sorted(zip(cc,bits)))
        pairs.add(key)
pairs=sorted(pairs)
print(len(pairs), file=sys.stderr)
C=np.array([[c for c,b in k] for k in pairs],dtype=np.int16)
Bt=np.array([[b for c,b in k] for k in pairs],dtype=np.int8)
nopt=[]
for k in pairs:
    n=0
    for j,(y,bj) in enumerate(k):
        x=(-y)%q
        if all(chi[(x+yl)%q]==bl for l,(yl,bl) in enumerate(k) if l!=j): n+=1
    nopt.append(n)
nopt=np.array(nopt)
np.savez('need337_full.npz',C=C,B=Bt,nopt=nopt)
print('pairs',len(pairs),'options hist',np.bincount(nopt))
