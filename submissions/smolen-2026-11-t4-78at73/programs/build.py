import sys
q=73; lines=open(sys.argv[1]).read().split('\n')
z=[l[2:] for l in lines if l.startswith('z ')][0]; R=[l[2:] for l in lines if l.startswith('R ')]
sq={(i*i)%q for i in range(1,q)}
rows=[]
for x in range(q):
    rows.append(''.join(z[x] if (x+y)%q==0 else ('1' if (x+y)%q in sq else '0') for y in range(q)))
rows+=R
open(sys.argv[2],'w').write('\n'.join(' '.join(r) for r in rows)+'\n')
print(len(rows),len(rows[0]))
