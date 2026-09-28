"""D-DISKERRS, the drive-letter shape: which drive letters does the reference refuse?

T6 batch 8 (scratchpad/t6enum_b8_zb.out) found every `Q:` accepted on zerobas --
OPEN, KILL, SAVE, RUN -- where the CF-3300 raises 62 Bad drive name. Before a
rule is written, each letter is asked, one boot per case, the CF-3300 against
zerobas's DISK build (a private disk image each), trapped by ON ERROR:

    OPEN "<d>:F.TXT" FOR OUTPUT AS #1        for d in A..H, Q, and a lower-case a

    python3 -u scratchpad/drvname_probe.py
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl, t6enum_probe as t

LETTERS = list("ABCDEFGH") + ["Q", "a"]


def main():
    got = {}
    for m, cf in (("National_CF-3300", True), ("C-BIOS_MSX1_EU_REPACK_DISK", False)):
        cs = [("direct", t.program(f'OPEN "{d}:F.TXT" FOR OUTPUT AS #1')) for d in LETTERS]
        raws = omsx_repl.run_cases(m, cs, batch=False,
                                   reset=("", "SCREEN 0", "CLS") if cf else ("CLS",),
                                   boot=14.0 if cf else 8.0, capture="screen",
                                   diska=t._disk_image(), step=8.0, cap_gap=20.0)
        got[m] = [t.reading(r) for r in raws]
    print(f"{'drive':6} {'CF-3300':>12} {'zerobas':>12}")
    for i, d in enumerate(LETTERS):
        a, b = got["National_CF-3300"][i], got["C-BIOS_MSX1_EU_REPACK_DISK"][i]
        print(f"{'  ' if a == b else '✗ '}{d + ':':6} {str(a):>12} {str(b):>12}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
