#!/bin/sh
# 🔬 Falsify tools/check_temp_root.py: each rule must go RED on its own plant,
# the STALE control must fire, and a clean tree must go GREEN.
set -u
cd /Users/joost/projects/zerobas
P=probes/basic/basic_probe_beep.py
A=tools/temp-root-allow.txt
cp $P /tmp/_teeth_p.bak; cp $A /tmp/_teeth_a.bak
pass=0; fail=0
judge() { # name, expect-rc, grep-pattern
  out=$(python3 tools/check_temp_root.py 2>&1); rc=$?
  if [ "$rc" = "$2" ] && printf '%s' "$out" | grep -q "$3"; then
    echo "  PASS  $1"; pass=$((pass+1))
  else
    echo "  FAIL  $1  (rc=$rc, wanted $2 matching '$3')"
    printf '%s\n' "$out" | tail -3 | sed 's/^/        /'; fail=$((fail+1))
  fi
}

echo "GREEN control (clean tree):"
judge "clean tree passes" 0 "ALL PASS"

echo "RULE 1 -- a bare tempfile call in a file that reaches no chokepoint:"
printf 'import tempfile\ntempfile.mkdtemp(prefix="x_")\n' > probes/basic/_teeth_orphan.py
judge "orphan bare tempfile is RED" 1 "reaches no chokepoint"
rm -f probes/basic/_teeth_orphan.py

echo "RULE 2 -- a second module setting the root:"
printf 'import tempfile\ntempfile.tempdir = "/nope"\n' > probes/basic/_teeth_root.py
judge "second tempdir assignment is RED" 1 "only probes/lib/probe_tmp.py may"
rm -f probes/basic/_teeth_root.py

echo "RULE 3 -- a NEW hardcoded literal:"
cp $P /tmp/_teeth_p2 && printf '\nX = "/tmp/brand_new_leak.txt"\n' >> $P
judge "new /tmp literal is RED" 1 "brand_new_leak"
cp /tmp/_teeth_p.bak $P

echo "CONTROL -- an allowlist entry that stops matching:"
printf '%s\n' 'probes/basic/basic_probe_beep.py:"/tmp/this_never_existed.txt"' >> $A
judge "stale pin is RED" 1 "STALE"
cp /tmp/_teeth_a.bak $A

echo "GREEN control again (restored):"
judge "tree restored, passes again" 0 "ALL PASS"
rm -f /tmp/_teeth_p.bak /tmp/_teeth_a.bak /tmp/_teeth_p2
echo; echo "TEETH: $pass passed, $fail failed"
[ "$fail" = 0 ]
