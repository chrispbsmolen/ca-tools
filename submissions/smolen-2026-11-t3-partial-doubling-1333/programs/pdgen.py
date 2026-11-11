# pdgen.py BASE r OUT [s]: exact partial doubling of a binary strength-3 CA with r helper rows.
# Twins the first s base columns (default: as many as the helper rows allow, C(r-1, (r-1)//2+1) - 1, capped at k).
import sys
from itertools import combinations
from math import comb
A=[list(map(int,l.split())) for l in open(sys.argv[1]) if l.strip()]; k=len(A[0]); r=int(sys.argv[2])
size=(r-1)//2+1; fam=[[0]+[1 if x in s else 0 for x in range(r-1)] for s in combinations(range(r-1),size)]
cap=len(fam)-1 if len(fam)-1<k else k
s=int(sys.argv[4]) if len(sys.argv)>4 else cap
assert s<=cap
if s==k and len(fam)>=k: p=None; F=fam[:k]
else: p=fam[0]; F=fam[1:]
cols=[(i, F[i] if i<s else p) for i in range(k)]+[(i,[1-x for x in F[i]]) for i in range(s)]
R=[[A[q][c[0]] for c in cols] for q in range(len(A))]+[[c[1][b] for c in cols] for b in range(r)]
open(sys.argv[3],'w').write('\n'.join(' '.join(map(str,x)) for x in R)+'\n'); print(len(R),'x',len(cols),'twins',s)
