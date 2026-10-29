#!/bin/bash
# gpu_cphf_run.sh FILE...  - run cphfcheck_metal on CPHF files, reading t, q and s from each file's first
# comment line ("# CPHF t=.. q=.. n=.. k=.. m=.. s=.."). Results appended to gpu_cphf_results.txt.
cd "$(dirname "$0")"
for f in "$@"; do
  h=$(head -1 "$f")
  t=$(echo "$h" | sed -n 's/.* t=\([0-9]*\).*/\1/p'); q=$(echo "$h" | sed -n 's/.* q=\([0-9]*\).*/\1/p'); s=$(echo "$h" | sed -n 's/.* s=\([0-9]*\).*/\1/p')
  [ -n "$s" ] || s=1
  echo "== $(date '+%F %T') $f (t=$t q=$q s=$s) sha256 $(shasum -a 256 "$f" | cut -c1-16)" | tee -a gpu_cphf_results.txt
  ./cphfcheck_metal "$f" $t $q $s 2>&1 | tail -4 | tee -a gpu_cphf_results.txt
done
