# Eager exact SAT for CA(259;6,18,2): Z17 x mult subgroup(m) on cols 0..16, col 17 fixed, 4 const rows + orbit words.
# usage: eager.py m budget_conflicts stab1 stab2 ...   (stab h = word invariant under subgroup of order h; orbit size 17*m/h)
import sys,time,itertools,os
from pysat.solvers import Cadical153
m=int(sys.argv[1]); budget=int(sys.argv[2]); stabs=[int(a) for a in sys.argv[3:]]
K=18;P=17; cgen=pow(3,16//m,P)
assert os.environ.get("NOASSERT") or 17*sum(m//h for h in stabs)==255 and all(m%h==0 for h in stabs)
def img(S,j,b):
    c=pow(cgen,j,P); return tuple(sorted(((c*x+b)%P) if x<P else x for x in S))
sets=[];seen=set()
for S in itertools.combinations(range(K),6):
    if S in seen: continue
    sets.append(S)
    for j in range(m):
        for b in range(P): seen.add(img(S,j,b))
nv=0;cyc=[];nco=[]
for h in stabs:
    d=pow(cgen,m//h,P); idv=[-1]*K; n=0
    for x in range(P):
        if idv[x]<0:
            y=x
            while idv[y]<0: idv[y]=nv+n; y=d*y%P
            n+=1
    idv[17]=nv+n; n+=1; nv+=n; cyc.append(idv); nco.append(m//h)
print("classes",len(sets),"bits",nv,flush=True)
sol=Cadical153(); nxt=nv+1; mv={}
lit=lambda v:v+1
def rowcols(i,j,b,S):
    ci=pow(cgen,(-j)%m,P)
    return [cyc[i][((ci*(x-b))%P) if x<P else 17] for x in S]
rowlist=[(i,j,b) for i in range(len(stabs)) for j in range(nco[i]) for b in range(P)]
def const_covered(S,p):
    rest=[(p>>q)&1 for q,x in enumerate(S) if x<P]
    return len(set(rest))<=1
nclauses=0
for S in sets:
    for p in range(64):
        if const_covered(S,p): continue
        cl=[];seenk=set()
        for (i,j,b) in rowlist:
            cols=rowcols(i,j,b,S); need={};ok=True
            for q,c in enumerate(cols):
                bit=(p>>q)&1
                if need.setdefault(c,bit)!=bit: ok=False;break
            if not ok: continue
            key=frozenset(need.items())
            if key in seenk: continue
            seenk.add(key)
            v=mv.get(key)
            if v is None:
                v=nxt;nxt+=1;mv[key]=v
                for c,bit in key: sol.add_clause([-v, lit(c) if bit else -lit(c)])
            cl.append(v)
        sol.add_clause(cl); nclauses+=1
print("aux",nxt-1-nv,"bigclauses",nclauses,flush=True)
# symmetry breaking: complement of Z17 cols & of col17 (global): first word's first cycle bit and col17 bit = 0
sol.add_clause([-lit(cyc[0][0])]); sol.add_clause([-lit(cyc[0][17])])
# identical-stab words: lex order on bit vectors
def vec(i): return sorted(set(cyc[i]))
for i in range(len(stabs)-1):
    if stabs[i]==stabs[i+1]:
        a=vec(i);b=vec(i+1); n=len(a)
        prev=None
        for k in range(n):
            x,y=lit(a[k]),lit(b[k])
            if prev is None: sol.add_clause([-x,y])
            else: sol.add_clause([-prev,-x,y])
            e=nxt;nxt+=1
            base=[] if prev is None else [-prev]
            sol.add_clause(base+[x,y,e]); sol.add_clause(base+[-x,-y,e])
            prev=e
sol.conf_budget(budget); t0=time.time(); r=sol.solve_limited()
print("RESULT",{True:"SAT",False:"UNSAT",None:"BUDGET"}[r],"stabs",stabs,"m",m,"t %.1f"%(time.time()-t0),flush=True)
if r:
    ms=set(l for l in sol.get_model() if l>0); print("BITS",[1 if lit(v) in ms else 0 for v in range(nv)])
if r and os.environ.get("OUT"):
    bits=[1 if lit(v) in ms else 0 for v in range(nv)]
    rows=[]
    for a in range(4): rows.append([ (a>>1) if x<P else (a&1) for x in range(K)])
    for (i,j,b) in rowlist:
        ci=pow(cgen,(-j)%m,P)
        rows.append([bits[cyc[i][((ci*(x-b))%P) if x<P else 17]] for x in range(K)])
    open(os.environ["OUT"],"w").write("\n".join("".join(map(str,rw)) for rw in rows)+"\n"); print("ROWS",len(rows))
