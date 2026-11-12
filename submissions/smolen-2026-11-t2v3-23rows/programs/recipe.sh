#!/bin/bash
# recipe.sh - builds CA(23;2,138,3) twice from the two ingredient files in programs/ and writes RECIPE.txt and
# REPLAY.log. Run from the submission folder:  bash programs/recipe.sh
# Needs cc, python3, sha256sum (or shasum -a 256). About 15 minutes per build. Seed 2003. No clock in the search:
# each ext2t run is stopped when the named array has been saved.
set -e
SUB=$(cd "$(dirname "$0")/.." && pwd); P="$SUB/programs"
sha() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }
R="$SUB/RECIPE.txt"; L="$SUB/REPLAY.log"
{
echo "RECIPE for CA_23_2_138_3.txt, written by programs/recipe.sh"
echo "date (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "machine: $(uname -sm); compiler: $(cc --version | head -1); python: $(python3 --version)"
echo "seed: 2003 (both ext2t runs); temperatures 0.65 and 0.40; stop rule: each ext2t run is stopped when its target array has been saved; drop1 is exhaustive"
for f in CA_17_2_29_3_16af2149.txt OA_9_2_4_3.txt pprod.py ext2t.c drop1.c; do echo "sha256 programs/$f $(sha "$P/$f")"; done
} > "$R"
: > "$L"; OK=1
until_file() { # file pid
  while [ ! -f "$1" ] && kill -0 $2 2>/dev/null; do sleep 2; done; sleep 2; kill $2 2>/dev/null; wait $2 2>/dev/null || true; }
for pass in build replay; do
  W=$(mktemp -d); cd "$W"; mkdir out
  say() { echo "[$pass] $*" | tee -a "$R" >> "$L"; }
  say "\$ cc -O3 -o ext2t programs/ext2t.c -lm ; cc -O3 -o drop1 programs/drop1.c"
  cc -O3 -o ext2t "$P/ext2t.c" -lm; cc -O3 -o drop1 "$P/drop1.c"
  say "\$ python3 programs/pprod.py programs/CA_17_2_29_3_16af2149.txt 7 16 programs/OA_9_2_4_3.txt 0 1 p23a.txt"
  python3 "$P/pprod.py" "$P/CA_17_2_29_3_16af2149.txt" 7 16 "$P/OA_9_2_4_3.txt" 0 1 p23a.txt > p.out; say "$(tail -n 1 p.out) | sha256 p23a.txt $(sha p23a.txt)"
  say "\$ ./ext2t p23a.txt 23 110 0 0 2003 1000000 0.65 out/a2003 -chain 40 -fr 15,16,17,18,19,20,21,22 -ntry 200 -kick 200000   (stopped when out/a2003_23_136.txt is saved)"
  ./ext2t p23a.txt 23 110 0 0 2003 1000000 0.65 out/a2003 -chain 40 -fr 15,16,17,18,19,20,21,22 -ntry 200 -kick 200000 > a.out 2>&1 & until_file out/a2003_23_136.txt $!
  grep FOUND a.out | tail -n 2 >> "$L"; say "sha256 out/a2003_23_136.txt $(sha out/a2003_23_136.txt)"
  say "\$ ./ext2t out/a2003_23_136.txt 23 136 0 0 2003 1000000 0.40 out/b2003 -chain 4 -frl 23 -ntry 200   (stopped when out/b2003_23_137.txt is saved)"
  ./ext2t out/a2003_23_136.txt 23 136 0 0 2003 1000000 0.40 out/b2003 -chain 4 -frl 23 -ntry 200 > b.out 2>&1 & until_file out/b2003_23_137.txt $!
  grep FOUND b.out | tail -n 2 >> "$L"; say "sha256 out/b2003_23_137.txt $(sha out/b2003_23_137.txt)"
  say "\$ ./drop1 out/b2003_23_137.txt"
  ./drop1 out/b2003_23_137.txt > d.out; cat d.out >> "$L"; say "$(head -n 1 d.out)"
  say "sha256 out/b2003_23_137.txt.plus1 $(sha out/b2003_23_137.txt.plus1)"
  if cmp -s out/b2003_23_137.txt.plus1 "$SUB/CA_23_2_138_3.txt"; then say "IDENTICAL to CA_23_2_138_3.txt"; else say "MISMATCH with CA_23_2_138_3.txt"; OK=0; fi
  cd "$SUB"; rm -rf "$W"
done
{
echo "sha256 CA_23_2_138_3.txt (submitted) $(sha "$SUB/CA_23_2_138_3.txt")"
if [ $OK = 1 ]; then echo "RESULT: build and replay both IDENTICAL to the submitted file"; else echo "RESULT: MISMATCH"; fi
} | tee -a "$R" >> "$L"
tail -1 "$R"
