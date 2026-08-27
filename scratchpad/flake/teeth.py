#!/usr/bin/env python3
"""Does the new diagnosis NAME its cause -- and stay SILENT on a healthy run?

🔴 A DIAGNOSTIC THAT ALWAYS PRINTS IS NOISE, and one that never prints is the
hole it replaces. Both senses are needed: forced failures that must each be
named DIFFERENTLY, and a green control that must say nothing at all.

🔴 AND THE FIRST DRAFT OF THIS FILE WENT RED THREE TIMES FOR ITS OWN REASONS,
which is the same class as a falsification going green for the wrong one:
  * `-machine No_Such_Machine` never reaches the launch -- `omsx_preflight`
    refuses it first, loudly and correctly. A cause the tree ALREADY handles.
  * `ZEROBAS_OMSX_ABSCAP=1` is defeated by `abscap_s = max(timeout, ...)`, so
    the case needs `timeout=1` as well.
  * `ZEROBAS_OMSX_STALL=1` on an ordinary case loses a race with the run, which
    finishes in ~1.5 s wall. The timeline has to be long enough to lose.
  * `pkill` defaults to SIGTERM, not SIGKILL. openMSX HANDLES SIGTERM and exits
    0, so "openMSX exited CLEANLY (0)" was the right answer to the wrong
    question. Both signals are now cases, because they are different events and
    must read differently: a graceful termination is not a crash.
🎯 Three drafts, three reds, and the code was correct every time. A forcing
function is a claim about the mechanism, and it is as falsifiable as the fix.
"""
import os, subprocess, sys

HERE = os.path.abspath(".")
MACH = "C-BIOS_MSX1_EU_REPACK_DISK"

# A long BOOT makes the timeline take many WALL seconds under throttle-off
# (~0.003 s wall per emulated s), so a watchdog has something to fire during.
SNIP = '''
import sys, os
sys.path.insert(0, "probes/lib")
import omsx_repl
kw = {}
if os.environ.get("ZBTIMEOUT"):
    kw["timeout"] = float(os.environ["ZBTIMEOUT"])
try:
    c = omsx_repl.run_cases(os.environ["ZBM"], [("direct", ['PRINT"[";1+1;"]"'])],
                            batch=False, boot=float(os.environ["ZBBOOT"]),
                            step=2.5, **kw)
    print("RESULT", repr(omsx_repl.result_span(c[0])))
except SystemExit as e:
    print("SystemExit:", e)
'''

KILLER = '''
import subprocess, sys, time
time.sleep(float(sys.argv[1]))
subprocess.run(["pkill", sys.argv[2], "-x", "openmsx"])
'''


def run(env, kill_after=None, sig="-9"):
    e = dict(os.environ, ZBM=MACH, **env)
    k = None
    if kill_after is not None:
        k = subprocess.Popen([sys.executable, "-c", KILLER,
                              str(kill_after), sig])
    p = subprocess.run([sys.executable, "-c", SNIP], cwd=HERE, env=e,
                       capture_output=True, text=True, timeout=900)
    if k:
        k.wait()
    diag = [l for l in p.stderr.splitlines() if l.startswith("omsx_repl:")]
    body = [l for l in p.stdout.splitlines()
            if l.startswith(("RESULT", "SystemExit"))]
    return diag, body


CASES = [
    ("GREEN control -- a healthy boot-per-case run",
     dict(ZBBOOT="8"), None, "-9",
     "prints NOTHING and returns ' 2 '",
     lambda t, d: not d and "RESULT ' 2 '" in t),
    ("RED -- the STALL watchdog (heartbeat stops)",
     dict(ZBBOOT="4000", ZEROBAS_OMSX_STALL="1"), None, "-9",
     "names `stall watchdog`",
     lambda t, d: "stall watchdog" in t),
    ("RED -- the ABSCAP backstop (needs timeout=1 too)",
     dict(ZBBOOT="4000", ZEROBAS_OMSX_ABSCAP="1", ZBTIMEOUT="1"), None, "-9",
     "names `abscap watchdog`",
     lambda t, d: "abscap watchdog" in t),
    ("RED -- openMSX CRASHES (SIGKILLed mid-run)",
     dict(ZBBOOT="4000"), 6.0, "-9",
     "names `terminated ON ITS OWN` and `signal 9`",
     lambda t, d: "terminated ON ITS OWN" in t and "signal 9" in t),
    ("RED -- openMSX is TERMINATED gracefully (SIGTERM mid-run)",
     dict(ZBBOOT="4000"), 6.0, "-15",
     "names `exited CLEANLY (0)` -- a graceful stop is NOT a crash",
     lambda t, d: "exited CLEANLY (0)" in t),
]

if subprocess.run(["pgrep", "-x", "openmsx"], capture_output=True).stdout.strip():
    sys.exit("REFUSING: another openmsx is running -- the SIGKILL case would "
             "hit it, and a falsification that damages a neighbour is not one.")

bad = 0
for title, env, kill_after, sig, want, judge in CASES:
    diag, body = run(env, kill_after, sig)
    print(f"\n=== {title}\n    want: {want}")
    for l in diag:
        print(f"    STDERR  {l}")
    for l in body:
        print(f"    STDOUT  {l}")
    if not diag and not body:
        print("    (nothing printed)")
    ok = judge(" ".join(diag + body), diag)
    print(f"    -> {'PASS' if ok else 'FAIL'}")
    bad += not ok

print(f"\nTEETH: {len(CASES)} case(s), {bad} failed")
sys.exit(1 if bad else 0)
