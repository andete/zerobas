#!/bin/zsh
set -e
cd /Users/joost/projects/zerobas
L=scratchpad/carve_emu
for t in strparen-acceptance namspc-acceptance cassave-acceptance castail-acceptance dskmsg-acceptance fldwidth-acceptance diskbasic-acceptance fat-error-acceptance; do
  echo "### $t"
  make $t > $L.$t.log 2>&1 || { echo "FAILED $t rc=$?"; tail -30 $L.$t.log; exit 1; }
  tail -4 $L.$t.log
done
echo "ALL EMULATOR BATTERIES OK"
