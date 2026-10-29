#!/bin/bash
# gpu_test.sh - build the Metal checker and compare it with the CPU checker (cyccheck.c).
#   ./gpu_test.sh          build, compare counts on the test cases, time q=1231 at strength 5
#   ./gpu_test.sh full     the same, then the full strength-6 check of q=1231 on the GPU (timing)
# Everything is written to gpu_test.txt as well as the screen.
cd "$(dirname "$0")"
OUT=gpu_test.txt
exec > >(tee "$OUT") 2>&1
echo "$(date '+%F %T') gpu_test start on $(uname -s)-$(uname -m)"
clang -O2 -fobjc-arc -framework Metal -framework Foundation -o cyccheck_metal cyccheck_metal.m || { echo "BUILD FAILED (Metal host)"; exit 1; }
clang -O3 -o cyccheck_cpu1 cyccheck.c || { echo "BUILD FAILED (CPU checker)"; exit 1; }
echo "built; sha256 cyccheck_metal.m $(shasum -a 256 cyccheck_metal.m | cut -c1-12)"
fail=0
for spec in "73 4" "103 4" "313 5" "337 5" "61 5" "131 6"; do
  c=$(./cyccheck_cpu1 $spec - 1 | grep "second element" | tr '\n' ' ')
  g=$(./cyccheck_metal $spec - | grep "second element" | tr '\n' ' ')
  if [ "$c" = "$g" ] && [ -n "$c" ]; then echo "q t = $spec: GPU agrees with CPU: $g"
  else echo "q t = $spec: MISMATCH"; echo "   CPU: $c"; echo "   GPU: $g"; ./cyccheck_metal $spec - | tail -4; fail=1; fi
done
python3 -c "
q=1231
x=[0]+[0 if pow(i,(q-1)//2,q)==1 else 1 for i in range(1,q)]
x[100]^=1; x[200]^=1
open('bad1231.txt','w').write(''.join(map(str,x)))"
./cyccheck_metal 1231 6 bad1231.txt | grep -q "symmetry certificate failed" && echo "broken vector rejected" || { echo "broken vector NOT rejected"; fail=1; }
[ $fail = 0 ] || { echo "TEST FAILED"; exit 1; }
echo "all comparisons passed"
echo "--- timing: q=1231 t=5 (GPU), then CPU 1 thread for comparison"
./cyccheck_metal 1231 5 - | tail -2
s=$(date +%s); ./cyccheck_cpu1 1231 5 - 1 | tail -1; echo "CPU 1 thread: $(( $(date +%s) - s )) s"
if [ "${1:-}" = full ]; then
  echo "--- full strength 6 check of q=1231 on the GPU"
  ./cyccheck_metal 1231 6 - | tail -3
fi
echo "$(date '+%F %T') gpu_test done"
