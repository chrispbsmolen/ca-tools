# mk3.py OUT JOINTFILE : array from f on Z63 on the shifts D of the joint.c output, plus each row R (restricted to D) and its complement.
import sys
f='011011011010001111001100000010111011000110100001010100011101111'; n=63
L=open(sys.argv[2]).read().split('\n'); D=[int(x) for x in [l for l in L if l.startswith('D')][0].split()[1:]]
R=[l.split()[1] for l in L if l.startswith('R ')]
A=[[int(f[(x+d)%n]) for d in D] for x in range(n)]; A+=[[1-v for v in r] for r in A]
for r in R:
    row=[int(r[d]) for d in D]; A.append(row); A.append([1-v for v in row])
open(sys.argv[1],'w').write('\n'.join(' '.join(map(str,r)) for r in A)+'\n'); print(len(A),'rows',len(D),'columns')
