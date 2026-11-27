Construction: even-weight binary vectors of length t+1, the orthogonal array OA(2^t; t, t+1, 2) of index 1 (a full factorial in t factors plus its parity column), for t = 7, 8, 9 and 10
Built from: nothing
Program: python3 -c 'import itertools,sys; t=int(sys.argv[1]); [print(*x, sum(x)%2) for x in itertools.product((0,1), repeat=t)]' 7 > CA_128_7_8_2.txt (and 8, 9, 10 likewise). Ulrike Groemping's R command (DoE.base::desnum(FrF2::FrF2(2^t, t+1))+1)/2 gives the same array up to the order of rows and the labelling of the last column.
AI tools used: yes
