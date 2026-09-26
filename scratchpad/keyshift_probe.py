"""Does the function-key line show F6..F10 while SHIFT is held? (Filed
2026-09-25 from the N-set probe: the VG-8020's FNKSWI reads 1 = F1..F5 at rest,
and its interrupt evidently maintains it -- inferred, NOT observed. TIER 3:
measure before building.)

The program waits, then -- while the harness still holds SHIFT (key matrix row 6
bit 0) -- copies the bottom screen row out of VRAM with VPEEK and reads FNKSWI,
and prints both AFTER the key is released (`holds` releases it just before the
capture). A second case does the same with no key held, as the control.

Both machines boot with the key line shown (D-KEYBOOT). Clean room: typed
BASIC, the key matrix, VRAM contents, a documented cell. No ROM byte.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
SHIFT = (6, 0x01)
# "stored" mode numbers the lines itself (10, 20, ...): the body carries none
PROG = ["FOR I=1 TO 1500:NEXT",
        "A$=\"\":FOR X=0 TO 39:C=VPEEK(920+X):IF C<32 THEN C=46",
        "A$=A$+CHR$(C):NEXT:F=PEEK(&HFBCD)",
        "FOR I=1 TO 900:NEXT",
        "PRINT \"<\";A$;\">\";F"]
# The control HOLDS A KEY TOO: an unheld case gets no hold time, so the first
# run's control was captured before its program printed anything (both sides).
# CTRL, like SHIFT, produces no character -- but should not switch the key line.
CTRL = (6, 0x02)
CASES = [("shift", [SHIFT]), ("ctrl", [CTRL])]


def answer(raw):
    t = " ".join("".join(raw or "").split())
    i = t.rfind("<")
    j = t.rfind(">")
    if i < 0 or j < i:
        return None
    return t[i + 1:j].strip() + " | FNKSWI=" + t[j + 1:].split()[0] if j + 1 < len(t) else None


def main():
    got = {}
    for m in (REF, ZB):
        raws = omsx_repl.run_cases(m, [("stored", PROG) for _ in CASES],
                                   batch=False, cap_gap=8.0,
                                   holds=[h for _k, h in CASES], hold_secs=10.0)
        got[m] = [answer(r) for r in raws]
    for i, (k, _h) in enumerate(CASES):
        print(f"{k:6s} ref: {got[REF][i]}")
        print(f"{'':6s} zb : {got[ZB][i]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
