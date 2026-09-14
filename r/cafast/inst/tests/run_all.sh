#!/bin/sh
# Runs every battery of the cafast package against the installed package.
# Needs R with CAs, caverify, lhs and cafast installed. Run from this folder:
#   sh run_all.sh 2>&1 | tee run_all_result.txt
set -e
for f in test_count_core.R test_nck_faces.R test_maxconstant.R test_powerct.R test_nck_driver.R; do
  echo "=== $f"; Rscript $f; echo
done
echo "ALL CAFAST TESTS DONE"
