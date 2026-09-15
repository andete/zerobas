"""D-DISKDISP: is a Disk-BASIC verb's TOKEN in the main BASIC ROM or the disk ROM?

The answer decides what a relocation may move. `spec-diskbasic-relocation.md`'s
Mechanism section says the dispatch is `$4004` STATEMENT expansion;
`disk/docs/expansion-protocol.md` §1 says `+0004` is the `CALL`-statement handler,
which is a different thing. Run each verb as a BARE STATEMENT under `ON ERROR` on
a machine with NO DISK ROM: a word BASIC does not know answers Syntax error, and a
word whose handler refuses answers Illegal function call.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402
# 🔴 THE CONTROLS COME FIRST. The claim under test is "ERR 5 means the word IS a
# token whose handler refused; a word BASIC does not know answers ERR 2". That is
# only a claim about the machine if a word BASIC certainly does not know really
# does answer 2 -- so `FROG` and `ZQ` are here, and if they answer 5 the whole
# inference is dead.
def prog(stmt):
    b = ["ON ERROR GOTO 0", stmt, 'PRINT"<X>":END', 'PRINT"<E";ERR;">":END']
    b[0] = "ON ERROR GOTO %d" % (10 * len(b))
    return b
WORDS = ["FROG", "ZQ", "FILES", "KILL", "NAME", "COPY", "MERGE",
         "FIELD", "LFILES", "BEEP", "CLS"]
CASES = [(w, prog(w)) for w in WORDS]
for mach in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK",
             "C-BIOS_MSX1_EU_REPACK_DISK"):
    print("===", mach, flush=True)
    raws = omsx_repl.run_cases(mach, [("stored", l) for _, l in CASES],
                               batch=True, cap_gap=8.0)
    for (n, _), raw in zip(CASES, raws):
        t = " ".join("".join(raw or "").split()); r = t.rfind("RUN")
        tail = t[r+3:] if r >= 0 else t
        i = tail.find("<"); j = tail.find(">", i+1) if i >= 0 else -1
        print(f"  {n:8} {(tail[i:j+1] if i>=0 and j>i else '?'+tail[:60])!r}", flush=True)
