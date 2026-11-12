import sys
q=337
S=[int(x) for x in open(sys.argv[1])]
chi=[0]*q
for i in range(1,q): chi[i*i%q]=1
z=None;R=[]
for line in open(sys.argv[2]):
    if line.startswith('z '): z=line.split()[1]
    elif line.startswith('R '): R.append(line.split()[1])
rows=[]
for x in range(q):
    r=[]
    for y in S:
        s=(x+y)%q
        r.append(chi[s] if s else int(z[x]))
    rows.append(r)
for rr in R: rows.append([int(rr[j]) for j in range(len(S))])
with open(sys.argv[3],'w') as f:
    for r in rows: f.write(' '.join(map(str,r))+'\n')
print(len(rows),len(rows[0]))
