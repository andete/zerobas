#!/usr/bin/env python3
r"""D-SCRAPEMODE arms — the guard must REFUSE the off-plane run and PASS the good one.

Both arms run the SAME probe shape on the SAME machine (National_CF-3000); the
ONLY difference is whether `reset` puts it in SCREEN 0. That is what makes this a
red/green pair rather than two unrelated observations.

  RED   reset=("NEW",)                  -> SCREEN 1, scrape off-plane, MUST NOT cache
  GREEN reset=("", "SCREEN 0", "NEW")   -> SCREEN 0, real readings,     MUST cache

🔴 THE CACHE IS THE SUBJECT, so each arm is measured by COUNTING CACHE ENTRIES
for the machine before and after -- not by reading the guard's own message,
which would be the readout agreeing with itself.
[[readout-blind-to-its-own-subject]]
"""
import glob, json, os, subprocess, sys

CACHE = os.path.expanduser("~/.cache/zerobas/refcache")

def entries_for(machine):
    n = 0
    for fp in glob.glob(os.path.join(CACHE, "**", "*.json"), recursive=True):
        try:
            if machine in str(json.load(open(fp)).get("machine", "")):
                n += 1
        except Exception:
            pass
    return n

def purge(machine):
    for fp in glob.glob(os.path.join(CACHE, "**", "*.json"), recursive=True):
        try:
            if machine in str(json.load(open(fp)).get("machine", "")):
                os.unlink(fp)
        except Exception:
            pass

RUNNER = r'''
import sys
sys.path.insert(0, "probes/lib")
import omsx_repl
caps = omsx_repl.run_cases("National_CF-3000",
    [("direct", ["NEW", 'A$="12345"', 'PRINT"[";A$;"]"'])],
    batch=False, reset=%r, boot=8.0, step=8.0, cap_gap=10.0, timeout=300.0)
print("CAPTURE:", repr(caps[0])[:90] if caps[0] else None)
'''

M = "CF-3000"
for tag, reset, must_cache in (
        ("RED   off-plane", ("NEW",), False),
        ("GREEN on-plane ", ("", "SCREEN 0", "NEW"), True)):
    purge(M)
    before = entries_for(M)
    r = subprocess.run([sys.executable, "-c", RUNNER % (reset,)],
                       capture_output=True, text=True,
                       env={**os.environ, "ZEROBAS_REFCACHE": "1"})
    after = entries_for(M)
    cached = after > before
    ok = (cached == must_cache)
    print(f"\n=== {tag}  reset={reset}")
    print(f"    cache entries {before} -> {after}   cached={cached}  "
          f"must_cache={must_cache}   {'✅' if ok else '🔴 WRONG'}")
    said = "NOT CACHING" in r.stderr
    print(f"    guard spoke: {said}")
    for ln in r.stdout.strip().splitlines()[:1]:
        print(f"    {ln}")
    if r.returncode != 0:
        print(f"    rc={r.returncode} stderr tail: {r.stderr[-300:]}")
purge(M)
print("\npurged CF-3000 entries")
