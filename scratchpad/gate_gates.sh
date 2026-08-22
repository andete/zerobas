#!/bin/zsh
set -e
cd /Users/joost/projects/zerobas
L=scratchpad/gate_gates
rm -rf build
make repack-machine > $L.repack.log 2>&1 || { echo "FAILED repack"; tail -20 $L.repack.log; exit 1; }
echo "### ROM identity vs the carve commit"
shasum -a 256 build/basic-reloc.rom build/sub.rom build/disk.rom | cut -c1-8,65-
make basic-reloc > $L.basic-reloc.log 2>&1 || { echo "FAILED basic-reloc"; tail -30 $L.basic-reloc.log; exit 1; }
grep -E 'measure:|dead \(|OK: no unreachable' $L.basic-reloc.log
for t in unit-test deadcode wall-assertion-check redundant-load-check rowshape-check injector-check preflight-check latch-check diskdep-check diskdep-selftest; do
  echo "### $t"
  make $t > $L.$t.log 2>&1 || { echo "FAILED $t"; tail -20 $L.$t.log; exit 1; }
  tail -2 $L.$t.log
done
echo "ALL GATE-HALF GATES OK"
