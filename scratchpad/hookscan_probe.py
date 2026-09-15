"""D-NODISKGAP: which hook cells does a REAL disk ROM claim?

Joost asked whether the diskless refusals are "exactly because of the hooks for
disk verbs". They are -- and this says how many: 27 cells, against the 14 equates
basic/sysvars.inc names. The 14 unnamed ones are where FIELD's slot lives.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402
# Which hook cells does a REAL disk ROM claim?  expansion-protocol.md §2 read
# three of them off the CF-3300 exactly this way: after boot each claimed hook
# holds `F7 <slot> <lo> <hi> C9` -- RST 30h = CALLF = $F7 -- so a PEEK sweep of
# the hook area names every slot the disk ROM took, INCLUDING the ones
# basic/sysvars.inc has no equate for.  Black-box observation, not disassembly.
# ⚠️ The `IF` must END ITS BODY: the packer merged `NEXT` onto it on the first
# cut, so the loop only advanced when the condition was TRUE.  The V$ pad forces
# the break.
L = ["FOR A=64922 TO 65487", 'W$="WWWWWWWWWWWWWWWWWWWW"',
     "IF PEEK(A)=247 THEN PRINT A;", 'V$="VVVVVVVVVVVV"', "NEXT",
     'PRINT"<END>"']
for i, b in enumerate(omsx_repl.as_stored(":".join(L))):
    print(f"  {10*(i+1):4} {b}")
raws = omsx_repl.run_cases("National_CF-3300", [("stored", L)], batch=False,
                           cap_gap=20.0, timeout=420.0, boot=14.0,
                           reset=("", "SCREEN 0"))
t = " ".join("".join(raws[0] or "").split())
r = t.rfind("RUN")
print(t[r:][:1200] if r >= 0 else t[-1200:])
