import sys
q=167
mask=open(sys.argv[1]).read().split()[0]
chi=[0]*q
for i in range(1,q): chi[i*i%q]=1
z=None;R=[]
for line in open(sys.argv[2]):
    if line.startswith('z '): z=line.split()[1]
    elif line.startswith('R '): R.append(line.split()[1])
rows=[]
for x in range(q):
    if mask[x]!='1': continue
    rows.append([chi[(x+y)%q] if (x+y)%q else int(z[x]) for y in range(q)])
for rr in R: rows.append([int(c) for c in rr[:q]])
open(sys.argv[3],'w').write(''.join(' '.join(map(str,r))+'\n' for r in rows))
print(len(rows),len(rows[0]))
