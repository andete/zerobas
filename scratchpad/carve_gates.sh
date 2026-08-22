#!/bin/zsh
set -e
cd /Users/joost/projects/zerobas
L=scratchpad/carve_gates
for t in unit-test deadcode wall-assertion-check redundant-load-check rowshape-check injector-check preflight-check latch-check diskdep-check diskdep-selftest; do
  echo "### $t"
  make $t > $L.$t.log 2>&1 || { echo "FAILED $t"; tail -20 $L.$t.log; exit 1; }
  tail -3 $L.$t.log
done
echo "ALL FAST GATES OK"
