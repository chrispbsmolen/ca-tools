# pick2.py K m seed rounds : K shifts and m added row pairs. Alternates (a) annealing on the shift set, cost = bad 5-sets inside it
# not served by the current rows (16-missing sets cost 1000), (b) refitting the m rows to the bad sets inside the current shift set.
import sys, random, math
K,m,seed,rounds=map(int,sys.argv[1:5]); random.seed(seed)
bad=[]
for l in open('bad63.txt'):
    a,b=l.split(':'); S=tuple(map(int,a.split())); P=list(map(int,b.split())); bad.append((S,P))
by=[[] for _ in range(63)]
for i,(S,P) in enumerate(bad):
    for c in S: by[c].append(i)
def served(i,R):
    S,P=bad[i]
    if len(P)>2: return False
    p=P[0]
    for r in R:
        x=[r[c] for c in S]; v=sum(x[j]<<j for j in range(5))
        if v==p or v==31-p: return True
    return False
def fit(D):
    inD=set(D); sets=[i for i,(S,P) in enumerate(bad) if len(P)==2 and all(c in inD for c in S)]
    best=None
    for trial in range(40):
        random.shuffle(sets); groups=[]
        for i in sets:
            S,P=bad[i]; p=P[0]
            for g in groups:
                par=dict(g[0]);pr=dict(g[1])
                def find(x):
                    q=0
                    while par[x]!=x:q^=pr[x];x=par[x]
                    return x,q
                ok=True
                for j in range(1,5):
                    a,b=S[0],S[j];d=(p&1)^(p>>j&1)
                    for z in (a,b):
                        if z not in par:par[z]=z;pr[z]=0
                    ra,qa=find(a);rb,qb=find(b)
                    if ra==rb:
                        if qa^qb!=d:ok=False;break
                    else:par[ra]=rb;pr[ra]=qa^qb^d
                if ok:g[0]=par;g[1]=pr;g[2]+=1;break
            else:
                par={z:z for z in S};pr={z:0 for z in S}
                for j in range(1,5):par[S[j]]=S[0];pr[S[j]]=(p&1)^(p>>j&1)
                groups.append([par,pr,1])
        groups.sort(key=lambda g:-g[2]); cov=sum(g[2] for g in groups[:m])
        if best is None or (len(groups),-cov)<best[0]: best=((len(groups),-cov),groups[:m])
    R=[]
    for par,pr,_ in best[1]:
        r=[]
        for c in range(63):
            q=0;x=c
            if c in par:
                while par[x]!=x:q^=pr[x];x=par[x]
            else: q=random.randint(0,1)
            r.append(q)
        R.append(r)
    while len(R)<m: R.append([random.randint(0,1) for _ in range(63)])
    return best[0][0],R
inD=[False]*63
for c in random.sample(range(63),K): inD[c]=True
R=[[random.randint(0,1) for _ in range(63)] for _ in range(m)]
for rd in range(rounds):
    w=[1000 if len(P)>2 else (0 if served(i,R) else 1) for i,(S,P) in enumerate(bad)]
    cnt=[sum(inD[c] for c in S) for S,P in bad]
    cost=sum(w[i] for i in range(len(bad)) if cnt[i]==5); T=0.6
    ins=[c for c in range(63) if inD[c]]; outs=[c for c in range(63) if not inD[c]]
    for it in range(60000):
        if cost==0: break
        a=random.randrange(len(ins)); b=random.randrange(len(outs)); o=ins[a]; i=outs[b]
        d=0
        for s in by[o]:
            if cnt[s]==5: d-=w[s]
        for s in by[o]: cnt[s]-=1
        for s in by[i]:
            if cnt[s]==4: d+=w[s]
        if d<=0 or random.random()<math.exp(-d/T):
            for s in by[i]: cnt[s]+=1
            ins[a]=i; outs[b]=o; inD[o]=False; inD[i]=True; cost+=d
        else:
            for s in by[o]: cnt[s]+=1
    D=sorted(ins); ng,R2=fit(D)
    print('round',rd,'K',K,'m',m,'unserved',cost,'groups if refit',ng,flush=True)
    if cost==0 or ng<=m:
        print('FOUND K',K,'rows',126+2*min(m,ng) if ng<=m else 126+2*m,'D',' '.join(map(str,D))); break
    R=R2
