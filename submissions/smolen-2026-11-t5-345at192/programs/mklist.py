import sys, numpy as np
q=337
d=np.load('need337_full.npz'); C=d['C']; B=d['B']
S=[int(x) for x in open(sys.argv[1])]; idx={c:i for i,c in enumerate(S)}
chi=[0]*q
for i in range(1,q): chi[i*i%q]=1
out=open(sys.argv[2],'w'); n=0
for k in range(len(C)):
    cols=C[k]
    if not all(int(c) in idx for c in cols): continue
    # relabel; keep original column order sorted by new label
    items=sorted((idx[int(c)],int(c),int(B[k][j])) for j,c in enumerate(cols))
    p=sum(b<<j for j,(_,_,b) in enumerate(items))
    opts=[]
    for j,(_,y,bj) in enumerate(items):
        x=(-y)%q
        if all(chi[(x+yl)%q]==bl for l,(_,yl,bl) in enumerate(items) if l!=j): opts.append("%d:%d"%(x,bj))
    out.write("5 "+" ".join(str(i) for i,_,_ in items)+" %d "%p+" ".join(opts)+"\n"); n+=1
print(n)
