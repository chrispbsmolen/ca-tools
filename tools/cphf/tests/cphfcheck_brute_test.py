"""Cross-check of cphfcheck against an independent brute force (own field arithmetic, rank by
elimination in Python): random families, uncovered counts must agree.
Run from tools/cphf after building cphfcheck there:  python3 tests/cphfcheck_brute_test.py SEED"""
import itertools, random, subprocess, sys
CONWAY={4:(2,[1,1]),8:(2,[1,1,0]),9:(3,[2,2]),16:(2,[1,1,0,0]),25:(5,[2,4]),27:(3,[1,2,0]),32:(2,[1,0,1,0,0])}
class F:
    def __init__(s,q):
        s.q=q
        if q in CONWAY: s.p,s.f=CONWAY[q]; s.e=len(s.f)
        else: s.p,s.f,s.e=q,[],1
    def vec(s,a): return [ (a//s.p**i)%s.p for i in range(s.e)]
    def code(s,v): return sum(c*s.p**i for i,c in enumerate(v))
    def add(s,a,b): return s.code([(x+y)%s.p for x,y in zip(s.vec(a),s.vec(b))])
    def mul(s,a,b):
        A,B=s.vec(a),s.vec(b); pr=[0]*(2*s.e)
        for i in range(s.e):
            for j in range(s.e): pr[i+j]=(pr[i+j]+A[i]*B[j])%s.p
        for d in range(2*s.e-2,s.e-1,-1):
            c=pr[d]; pr[d]=0
            for i in range(s.e): pr[d-s.e+i]=(pr[d-s.e+i]-c*s.f[i])%s.p
        return s.code(pr[:s.e])
    def inv(s,a): return next(b for b in range(1,s.q) if s.mul(a,b)==1)
    def neg(s,a): return next(b for b in range(s.q) if s.add(a,b)==0)
def rank(Fq,rows):
    M=[r[:] for r in rows]; r=0; t=len(M[0])
    for c in range(t):
        piv=next((i for i in range(r,len(M)) if M[i][c]),None)
        if piv is None: continue
        M[r],M[piv]=M[piv],M[r]; iv=Fq.inv(M[r][c]); M[r]=[Fq.mul(x,iv) for x in M[r]]
        for i in range(len(M)):
            if i!=r and M[i][c]:
                f=Fq.neg(M[i][c]); M[i]=[Fq.add(x,Fq.mul(f,y)) for x,y in zip(M[i],M[r])]
        r+=1
    return r
def digits(x,q,t): return [ (x//q**(t-1-j))%q for j in range(t)]
random.seed(int(sys.argv[1]) if len(sys.argv)>1 else 1)
cases=[(3,25,14,1),(3,17,14,1),(3,27,12,1),(3,32,12,1),(3,19,14,1),(3,23,14,1),(4,16,9,1),(4,9,10,1)]
allok=True
for t,q,k,n in cases:
    Fq=F(q); fam=[[random.randrange(q**t) for _ in range(k)] for _ in range(n)]
    if random.random()<0.5:   # make some rows affine
        for r in fam:
            for c in range(k): r[c]=(r[c]%q**(t-1))+q**(t-1)
    open('rnd.txt','w').write('\n'.join(' '.join(map(str,r)) for r in fam)+'\n')
    unc=0
    for S in itertools.combinations(range(k),t):
        if not any(rank(Fq,[digits(fam[r][c],q,t) for c in S])==t for r in range(n)): unc+=1
    out=subprocess.run(['./cphfcheck','rnd.txt',str(t),str(q),'full','2'],capture_output=True,text=True).stdout
    got=int(out.split('uncovered ')[1].split()[0])
    ok=(got==unc); allok&=ok
    print(f't={t} q={q} k={k} n={n}: brute {unc}, cphfcheck {got} {"OK" if ok else "MISMATCH"}')
print('ALL OK' if allok else 'MISMATCHES')
