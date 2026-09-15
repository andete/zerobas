import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402
# Replace the hook body with a handler that RETURNS IMMEDIATELY, having done
# nothing, and see whether BASIC still evaluates the argument afterwards.
#   cell is `F7 87 lo hi C9`; poking byte0/byte1 rewrites the first two bytes.
#   C9 ..    -> bare RET                      ("unclaimed" under OUR convention)
#   37 C9    -> SCF ; RET                     (returns with carry SET)
#   AF C9    -> XOR A ; RET                   (returns with carry CLEAR)
# If BASIC evaluates the argument ITSELF after the hook returns, `FILES 5` should
# still raise Type mismatch for at least one of these. If every immediate-return
# body suppresses the type check, the evaluation was the HANDLER's work.
# \U0001f534 THE REFERENCE'S OWN carry CONVENTION IS UNKNOWN TO US -- CF=1 meaning
# "handled" is OUR invention -- so both carry states are tried rather than
# assuming which one means what.
REF, KW = "National_CF-3300", dict(boot=14.0, reset=("", "SCREEN 0"))
H = 0xFE7B
def prog(pokes, stmt):
    b = [None] + ["POKE %d,%d" % (a, v) for a, v in pokes] + \
        [stmt, 'PRINT"<X>":END', 'PRINT"<E";ERR;">":END']
    b[0] = "ON ERROR GOTO %d" % (10*len(b)); return b
CASES = [
    ("base_num",      prog([],                        "FILES 5")),   # ERR 13
    ("ret_num",       prog([(H,201)],                 "FILES 5")),   # ERR 5 (known)
    ("scf_ret_num",   prog([(H,0x37),(H+1,201)],      "FILES 5")),
    ("xor_ret_num",   prog([(H,0xAF),(H+1,201)],      "FILES 5")),
    ("scf_ret_lit",   prog([(H,0x37),(H+1,201)],     'FILES"*.BAS"')),
    ("xor_ret_lit",   prog([(H,0xAF),(H+1,201)],     'FILES"*.BAS"')),
]
raws = omsx_repl.run_cases(REF, [("stored", l) for _, l in CASES],
                           batch=False, cap_gap=8.0, **KW)
for (n, _), raw in zip(CASES, raws):
    t = " ".join("".join(raw or "").split()); r = t.rfind("RUN")
    tail = t[r+3:] if r >= 0 else t
    i = tail.find("<"); j = tail.find(">", i+1) if i >= 0 else -1
    print(f"  {n:14} {(tail[i:j+1] if i>=0 and j>i else '?'+tail[:40])!r}", flush=True)
