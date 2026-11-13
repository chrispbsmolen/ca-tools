# mkcls.py: class files for gdev cls. usage: mkcls.py zn N g1[,g2..]  (orbits of multiplication by <g..> on Z_N) | gf64 E (cyclotomic classes of index E in GF(64)*, 0 own class; elements as bit vectors)
import sys
if sys.argv[1]=="zn":
    N=int(sys.argv[2]); gs=[int(x) for x in sys.argv[3].split(",")]
    cl=[-1]*N; k=0
    for x in range(N):
        if cl[x]<0:
            st=[x]; cl[x]=k
            while st:
                y=st.pop()
                for g in gs:
                    z=y*g%N
                    if cl[z]<0: cl[z]=k; st.append(z)
            k+=1
else:
    E=int(sys.argv[2])
    def mul(a,b):
        r=0
        while b:
            if b&1: r^=a
            a<<=1
            if a&64: a^=0b1000011   # x^6+x+1 primitive
            b>>=1
        return r
    cl=[0]*64; x=1
    for i in range(63): cl[x]=1+i%E; x=mul(x,2)
    assert x==1
print(" ".join(map(str,cl)))
