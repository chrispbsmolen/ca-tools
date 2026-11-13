# mk.py OUT d1 d2 ... : array from f on Z63 (rows f(x+d), x in Z63, and complements) on the given shifts, plus added rows.
# Every 5-set of the chosen shifts that misses patterns misses exactly one complementary pair (p, ~p). An added row r serves the set
# when r equals p or ~p on it, i.e. r_i + r_j = p_i + p_j on its columns. Sets are grouped so each group's equations are consistent
# (union-find with parities, sets taken in sorted order, first group that fits); one row and its complement are added per group.
import sys, itertools
f='011011011010001111001100000010111011000110100001010100011101111'; n=63
D=list(map(int,sys.argv[2:])); k=len(D)
A=[[int(f[(x+d)%n]) for d in D] for x in range(n)]; A+= [[1-v for v in r] for r in A]
cols=[sum(A[r][j]<<r for r in range(len(A))) for j in range(k)]; full=(1<<len(A))-1
badsets=[]
for S in itertools.combinations(range(k),5):
    miss=[]
    for p in range(32):
        a=full
        for i,j in enumerate(S):
            a&= cols[j] if p>>i&1 else ~cols[j]&full
            if not a: break
        if not a: miss.append(p)
    if miss:
        assert len(miss)==2 and miss[0]^miss[1]==31, (S,miss)
        badsets.append((S,miss[0]))
import random
bestg=None
for trial in range(200):
  random.seed(trial); order=badsets[:]
  if trial: random.shuffle(order)
  groups=[]
  for S,p in order:
      for g in groups:
          par=dict(g[0]); pr=dict(g[1])
          def find(x):
              q=0
              while par[x]!=x: q^=pr[x]; x=par[x]
              return x,q
          ok=True
          for j in range(1,5):
              a,b=S[0],S[j]; d=(p&1)^(p>>j&1)
              for z in (a,b):
                  if z not in par: par[z]=z; pr[z]=0
              ra,qa=find(a); rb,qb=find(b)
              if ra==rb:
                  if qa^qb!=d: ok=False;break
              else: par[ra]=rb; pr[ra]=qa^qb^d
          if ok: g[0]=par; g[1]=pr; break
      else:
          par={z:z for z in S}; pr={z:0 for z in S}
          for j in range(1,5): par[S[j]]=S[0]; pr[S[j]]=(p&1)^(p>>j&1)
          groups.append([par,pr])
  if bestg is None or len(groups)<len(bestg): bestg=groups
groups=bestg
for par,pr in groups:
    row=[]
    for j in range(k):
        q=0; x=j
        if j in par:
            while par[x]!=x: q^=pr[x]; x=par[x]
        row.append(q)
    A.append(row); A.append([1-v for v in row])
open(sys.argv[1],'w').write('\n'.join(' '.join(map(str,r)) for r in A)+'\n')
print('columns',k,'bad 5-sets',len(badsets),'groups',len(groups),'rows',len(A))
