"""D-KEYCLS: does the function-key line survive the statements that clear or
re-initialise the text screen? Found 2026-09-26 by scratchpad/keyshift_probe.py:
after the harness's CLS, zerobas's VRAM row 23 read blank where the VG-8020's
held `color auto goto list run`.

Each case runs on a fresh boot (key line shown, D-KEYBOOT) and reads the
bottom screen row as words, and one case reads the scroll bound after a
re-init (22 while the row is reserved). `KEY OFF:CLS` is the negative: the
line must STAY off. Clean room: typed BASIC, screen text.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
CASES = [
    ("cls",        ["CLS"]),
    ("screen0",    ["SCREEN 0"]),
    ("width40",    ["WIDTH 40"]),
    ("roundtrip",  ["SCREEN 1:SCREEN 0"]),
    ("keyon_cls",  ["KEY OFF:KEY ON:CLS"]),
    ("keyoff_cls", ["KEY OFF:CLS"]),
    # (SCREEN 1 is NOT a case: this scrape reads the SCREEN 0 name table, and
    # in SCREEN 1 it returns pattern-table bytes on BOTH machines.)
    ("bound",      ["SCREEN 0:FORI=1TO30:PRINT:NEXT:Y=CSRLIN:PRINT12345;Y"]),
]


def answer(k, raw):
    rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
            for r in range(omsx_repl.ROWS)]
    if k == "bound":
        hit = [r for r in rows if r.startswith("12345 ")]
        return hit[-1].split()[1] if hit else None
    return " ".join(rows[-1].split()) or "<blank>"


def main():
    specs = [("direct", lines) for _k, lines in CASES]
    got = {m: [answer(k, r or "") for (k, _l), r in
               zip(CASES, omsx_repl.run_cases(m, specs, batch=False, reset=(),
                                              boot=8.0, capture="screen"))]
           for m in (REF, ZB)}
    bad = 0
    for i, (k, lines) in enumerate(CASES):
        r, z = got[REF][i], got[ZB][i]
        same = r is not None and r == z
        bad += not same
        print(f"{'SAME' if same else 'DIFF'} {k:11s} ref: {r}   zb: {z}")
    print(f"\nDIFF: {bad}/{len(CASES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
