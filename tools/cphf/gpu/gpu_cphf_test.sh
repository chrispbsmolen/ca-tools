#!/bin/bash
# gpu_cphf_test.sh - build cphfcheck_metal (GPU) and compare it with the expected counts of uncovered
# representatives (computed in the cloud by repcheck_pp.c and by the plain-C transcription emu_kernel.c,
# which agreed on all of them) on 9 test families: t = 4, 5, 6; q = 3, 4, 5, 9; 1, 2 and 3 column orbits.
# Then a family with one changed entry must fail the symmetry certificate. Output also in gpu_cphf_test.txt.
cd "$(dirname "$0")"
exec > >(tee gpu_cphf_test.txt) 2>&1
echo "$(date '+%F %T') gpu_cphf_test on $(uname -s)-$(uname -m)"
clang -O2 -fobjc-arc -framework Metal -framework Foundation -o cphfcheck_metal cphfcheck_metal.m || { echo BUILD FAILED; exit 1; }
echo "built cphfcheck_metal, sha256 of source $(shasum -a 256 cphfcheck_metal.m | cut -c1-12)"
fail=0
while read f t q s want; do
  got=$(./cphfcheck_metal $f $t $q $s | sed -n 's/.*uncovered \([0-9]*\),.*/\1/p')
  if [ "$got" = "$want" ]; then echo "OK   $f t=$t q=$q s=$s uncovered $got"; else echo "FAIL $f t=$t q=$q s=$s expected $want got '$got'"; fail=1; fi
done < expected.txt
./cphfcheck_metal t/bad.txt 5 3 2 | grep -q "certificate FAILED" && echo "OK   changed entry rejected by the certificate" || { echo "FAIL changed entry not rejected"; fail=1; }
[ $fail = 0 ] && echo "ALL TESTS PASSED" || echo "TESTS FAILED"
