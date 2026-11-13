# build.py FFILE DFILE OUT : rows x in Z_n, columns d in D, entry f((x+d) mod n), then the complements of all rows.
import sys
f=[int(c) for c in open(sys.argv[1]).read().strip()]; n=len(f)
D=[int(x) for x in open(sys.argv[2]).read().split(':')[1].split()]
rows=[[f[(x+d)%n] for d in D] for x in range(n)]
rows+=[[1-v for v in r] for r in rows]
open(sys.argv[3],'w').write("\n".join(" ".join(map(str,r)) for r in rows)+"\n")
print(len(rows),"rows",len(D),"columns")
