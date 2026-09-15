import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402
# WHO EVALUATES?  Keep the cell's `F7` CALLF SIGNATURE and redirect only the
# SLOT+ADDRESS, so the existence check still passes but the handler is a RET we
# control.  The earlier attempt poked byte 0 and destroyed the signature, which
# is why it proved nothing.
#
#   H_FILE cell $FE7B = 65147:  F7 87 <lo> <hi> C9
#     byte1 65148 <- 0x83 = 131   page-3 RAM slot (measured: A8=0xFC, FFFF
#                                 inverted -> page 3 = slot 3-0, slot 3 expanded)
#     byte2 65149 <- 0xCF = 207   target $FFCF -- H_ZKEY, which the CF-3300
#     byte3 65150 <- 0xFF = 255   provably does NOT claim, and which already
#                                 holds C9 C9 C9 (an unclaimed hook IS a RET)
#
# READING `FILES 5`:
#   ERR 13  -> BASIC checked the cell, then EVALUATED, then called: JOOST'S SHAPE
#   anything else -> evaluation was the HANDLER's job and our RET skipped it
REF, KW = "National_CF-3300", dict(boot=14.0, reset=("", "SCREEN 0"))
RE = [(65148, 131), (65149, 207), (65150, 255)]          # redirect, signature kept
def prog(pokes, stmt):
    b = [None] + ["POKE %d,%d" % (a, v) for a, v in pokes] + \
        [stmt, 'PRINT"<X>":END', 'PRINT"<E";ERR;">":END']
    b[0] = "ON ERROR GOTO %d" % (10*len(b)); return b
CASES = [
    ("base_num",      prog([],                              "FILES 5")),
    ("base_lit",      prog([],                             'FILES"*.BAS"')),
    ("redir_num",     prog(RE,                              "FILES 5")),
    ("redir_lit",     prog(RE,                             'FILES"*.BAS"')),
    ("redir_scf_num", prog(RE + [(65487, 55), (65488, 201)], "FILES 5")),
    ("redir_xor_num", prog(RE + [(65487, 175), (65488, 201)], "FILES 5")),
]
raws = omsx_repl.run_cases(REF, [("stored", l) for _, l in CASES],
                           batch=False, cap_gap=10.0, **KW)
for (n, _), raw in zip(CASES, raws):
    t = " ".join("".join(raw or "").split()); r = t.rfind("RUN")
    tail = t[r+3:] if r >= 0 else t
    i = tail.find("<"); j = tail.find(">", i+1) if i >= 0 else -1
    print(f"  {n:14} {(tail[i:j+1] if i>=0 and j>i else '?'+tail[:45])!r}", flush=True)
