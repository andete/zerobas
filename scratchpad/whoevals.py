import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402
# WHO evaluates the argument -- main BASIC BEFORE the hook, or the disk-ROM
# handler AFTER it?  Un-claim the hook and watch which error wins.
#   still ERR 13 (Type mismatch) -> BASIC evaluated FIRST; no call-back needed
#   ERR 5 instead                -> the hook was consulted BEFORE evaluation
REF, KW = "National_CF-3300", dict(boot=14.0, reset=("", "SCREEN 0"))
H_FILE, H_KILL = 0xFE7B, 0xFDFE
def prog(pokes, stmt):
    b = [None] + ["POKE %d,201" % a for a in pokes] + \
        [stmt, 'PRINT"<X>":END', 'PRINT"<E";ERR;">":END']
    b[0] = "ON ERROR GOTO %d" % (10*len(b)); return b
CASES = [
    ("files_num_base",   prog([],        "FILES 5")),        # ERR 13 baseline
    ("files_num_unhook", prog([H_FILE],  "FILES 5")),        # 13 => BASIC first
    ("files_cat_unhook", prog([H_FILE], 'A$="A":FILES A$+"B"')),
    ("files_lit_unhook", prog([H_FILE], 'FILES"*.BAS"')),    # known ERR 5
    ("kill_num_unhook",  prog([H_KILL],  "KILL 5")),
]
raws = omsx_repl.run_cases(REF, [("stored", l) for _, l in CASES],
                           batch=False, cap_gap=8.0, **KW)
for (n, _), raw in zip(CASES, raws):
    t = " ".join("".join(raw or "").split()); r = t.rfind("RUN")
    tail = t[r+3:] if r >= 0 else t
    i = tail.find("<"); j = tail.find(">", i+1) if i >= 0 else -1
    print(f"  {n:17} {(tail[i:j+1] if i>=0 and j>i else '?'+tail[:40])!r}", flush=True)
