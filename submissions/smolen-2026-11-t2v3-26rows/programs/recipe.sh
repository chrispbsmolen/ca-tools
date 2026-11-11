#!/bin/bash
# recipe.sh - builds CA(26;2,296,3) twice from two arrays of the table and writes RECIPE.txt and REPLAY.log.
# Run from the submission folder, inside a clone of ca-tools (it reads ../../table/arrays):  bash programs/recipe.sh
# Needs cc, python3, sha256sum (or shasum -a 256). About 25 minutes. Seed 13, temperature 0.7, no clock in the search.
set -e
SUB=$(cd "$(dirname "$0")/.." && pwd); TA="$SUB/../../table/arrays"
sha() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }
R="$SUB/RECIPE.txt"; L="$SUB/REPLAY.log"
{
echo "RECIPE for CA_26_2_296_3.txt, written by programs/recipe.sh"
echo "date (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "machine: $(uname -sm); compiler: $(cc --version | head -1); python: $(python3 --version)"
echo "seed: 13 (ext2t); temperature 0.7; stop rule: the run is stopped when the array with 296 columns has been saved"
echo "inputs: table/arrays/CA_18_2_52_3.txt $(sha "$TA/CA_18_2_52_3.txt")"
echo "inputs: table/arrays/CA_11_2_5_3_c33e3aff.txt $(sha "$TA/CA_11_2_5_3_c33e3aff.txt")"
for f in pprod.py ext2t.c; do echo "sha256 programs/$f $(sha "$SUB/programs/$f")"; done
} > "$R"
: > "$L"; OK=1
for pass in build replay; do
  W=$(mktemp -d); cd "$W"; mkdir out
  say() { echo "[$pass] $*" | tee -a "$R" >> "$L"; }
  say "\$ cc -O3 -o ext2t programs/ext2t.c -lm"; cc -O3 -o ext2t "$SUB/programs/ext2t.c" -lm
  say "\$ python3 programs/pprod.py table/arrays/CA_18_2_52_3.txt 0 1 table/arrays/CA_11_2_5_3_c33e3aff.txt 0 4 p26_247.txt"
  python3 "$SUB/programs/pprod.py" "$TA/CA_18_2_52_3.txt" 0 1 "$TA/CA_11_2_5_3_c33e3aff.txt" 0 4 p26_247.txt > p.out; say "$(tail -n 1 p.out) | sha256 p26_247.txt $(sha p26_247.txt)"
  say "\$ ./ext2t p26_247.txt 26 247 0 0 13 1000000 0.7 out/t26 -chain 80 -ntry 200 -kick 200000"
  ./ext2t p26_247.txt 26 247 0 0 13 1000000 0.7 out/t26 -chain 80 -ntry 200 -kick 200000 > e.out 2>&1 & PID=$!
  while [ ! -f out/t26_26_296.txt ] && kill -0 $PID 2>/dev/null; do sleep 3; done; sleep 3; kill $PID 2>/dev/null; wait $PID 2>/dev/null || true
  echo "----- [$pass] FOUND lines of ext2t -----" >> "$L"; grep FOUND e.out >> "$L"
  say "sha256 out/t26_26_296.txt $(sha out/t26_26_296.txt)"
  if cmp -s out/t26_26_296.txt "$SUB/CA_26_2_296_3.txt"; then say "IDENTICAL to CA_26_2_296_3.txt"; else say "MISMATCH with CA_26_2_296_3.txt"; OK=0; fi
  cd "$SUB"; rm -rf "$W"
done
{
echo "sha256 CA_26_2_296_3.txt (submitted) $(sha "$SUB/CA_26_2_296_3.txt")"
if [ $OK = 1 ]; then echo "RESULT: build and replay both IDENTICAL to the submitted file"; else echo "RESULT: MISMATCH"; fi
} | tee -a "$R" >> "$L"
tail -1 "$R"
