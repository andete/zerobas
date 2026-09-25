"""D-KEYBOOT: does zerobas boot with the function-key line shown, as the VG-8020
does? Three readings on a fresh boot with NO reset typed first (a `KEY` or
`SCREEN` before the reading would erase the very state under test):

  row23   the bottom screen row, as text, right after boot (+ one PRINT)
  cnsdfg  PEEK(&HF3DE), the documented function-key display flag
  bound   the console's last usable row: where plain scrolling stops
          (CLS:FOR I=1 TO 30:PRINT:NEXT:Y=CSRLIN) -- 22 with the line reserved

Both zerobas builds, each against the VG-8020 (see PAIRS). Clean room: typed BASIC, a documented cell, screen text.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

# 🎨 BOTH zerobas builds against the VG-8020: the boot screen is presentational,
# and a presentational reference split ships the VG value on both targets
# (Joost, 2026-09-04). The CF-3300 cannot be read here anyway -- it boots in
# SCREEN 1, and with no reset typed the text scrape reads the wrong plane
# (measured: `x @@ @@H0 h P P`).
PAIRS = [("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"),
         ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK")]
CASES = [
    ("row23",  ["PRINT 7"]),
    ("cnsdfg", ["PRINT12345;PEEK(&HF3DE)"]),
    ("bound",  ["CLS:FORI=1TO30:PRINT:NEXT:Y=CSRLIN:PRINT12345;Y"]),
]


def rows(raw):
    return [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
            for r in range(omsx_repl.ROWS)]


def answer(k, raw):
    rs = rows(raw)
    if k == "row23":
        # words only: the two machines lay the labels out at different widths
        return " ".join(rs[-1].split()) or "<blank>"
    hit = [r for r in rs if r.startswith("12345 ")]
    return hit[-1].split()[1] if hit else None


def main():
    bad = total = 0
    for ref, zb in PAIRS:
        got = {}
        for m in (ref, zb):
            specs = [("direct", lines) for _k, lines in CASES]
            got[m] = omsx_repl.run_cases(m, specs, batch=False, reset=(),
                                         boot=8.0, capture="screen")
        print(f"== {ref} vs {zb}")
        for i, (k, _l) in enumerate(CASES):
            r, z = answer(k, got[ref][i] or ""), answer(k, got[zb][i] or "")
            same = r is not None and r == z
            total += 1
            bad += not same
            print(f"{'SAME' if same else 'DIFF'} {k:7s} ref: {r}   zb: {z}")
    print(f"\nDIFF: {bad}/{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
