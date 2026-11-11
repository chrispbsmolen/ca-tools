#!/bin/bash
# recipe.sh - builds CA(20;3,28,2), CA(21;3,32,2) and CA(24;3,42,2) from nothing, twice, and writes RECIPE.txt (every
# command, the hash of the program source, the hash of every output) and REPLAY.log. Run from the submission folder:
#     bash programs/recipe.sh
# No random numbers, no time limit, no input array. Needs cc and sha256sum (or shasum -a 256). About 25 minutes.
set -e
SUB=$(cd "$(dirname "$0")/.." && pwd)
sha() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }
R="$SUB/RECIPE.txt"; L="$SUB/REPLAY.log"
{
echo "RECIPE for CA_20_3_28_2.txt, CA_21_3_32_2.txt, CA_24_3_42_2.txt, written by programs/recipe.sh"
echo "date (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "machine: $(uname -sm); compiler: $(cc --version | head -1)"
echo "seeds: none (exhaustive search, no random numbers); stop rule: search runs to completion, no clock"
echo "inputs: none (no input array)"
echo "sha256 programs/orbfree3.c $(sha "$SUB/programs/orbfree3.c")"
} > "$R"
: > "$L"
OK=1
for pass in build replay; do
  W=$(mktemp -d); cd "$W"
  say() { echo "[$pass] $*" | tee -a "$R" >> "$L"; }
  say "\$ cc -O3 -o orbfree3 programs/orbfree3.c"; cc -O3 -o orbfree3 "$SUB/programs/orbfree3.c" 2>/dev/null
  one() { # N m tag k file cycles...
    n=$1; m=$2; tag=$3; k=$4; f=$5; shift 5
    say "\$ ./orbfree3 $n $m $tag $*"; ./orbfree3 $n $m $tag "$@" > run_$tag.log
    echo "----- [$pass] stdout of orbfree3 $n $m $tag $* -----" >> "$L"; cat run_$tag.log >> "$L"
    say "sha256 ${tag}_ext_${n}_${k}.txt $(sha ${tag}_ext_${n}_${k}.txt)"
    if cmp -s ${tag}_ext_${n}_${k}.txt "$SUB/$f"; then say "IDENTICAL to $f"; else say "MISMATCH with $f"; OK=0; fi
  }
  one 20 4 a 28 CA_20_3_28_2.txt 6 6 3 3 1 1
  one 21 3 b 32 CA_21_3_32_2.txt 9 9 3
  one 24 4 c 42 CA_24_3_42_2.txt 8 8 4 4
  cd "$SUB"; rm -rf "$W"
done
{
for f in CA_20_3_28_2.txt CA_21_3_32_2.txt CA_24_3_42_2.txt; do echo "sha256 $f (submitted) $(sha "$SUB/$f")"; done
if [ $OK = 1 ]; then echo "RESULT: build and replay both IDENTICAL to the submitted files"; else echo "RESULT: MISMATCH"; fi
} | tee -a "$R" >> "$L"
tail -1 "$R"
