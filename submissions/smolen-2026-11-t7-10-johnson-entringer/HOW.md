Construction: Johnson-Entringer weight-class arrays at k = t + 2, for t = 7, 8, 9 and 10: all binary vectors of length t + 2 whose weight has a fixed residue mod 3 (0 for t = 7 and 8, 1 for t = 9 and 10), giving floor(2^(t+2)/3) rows
Built from: nothing
Program: python3 -c 'import itertools,sys; t,r=int(sys.argv[1]),int(sys.argv[2]); [print(*x) for x in itertools.product((0,1), repeat=t+2) if sum(x)%3==r]' 7 0 > CA_170_7_9_2.txt (then 8 0, 9 1, 10 1). The CAs function JE(t, t+2) of U. Groemping builds the same construction.
AI tools used: yes
