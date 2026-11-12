# writes pw_winv.txt: each (set,pattern) pair with weight 1/nopt (nopt = number of diagonal cells that could cover it)
import numpy as np
d=np.load('need337_full.npz'); C=d['C']; n=d['nopt']
with open('pw_winv.txt','w') as o:
    for r,k in zip(C,n): o.write(' '.join(map(str,r))+' %.6f\n'%(1.0/k))
