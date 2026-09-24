#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KWPLAY scout 3 -- `PLAY"N40"` sounds a DIFFERENT NOTE here than on the
reference, and this asks by how much and over what range.

Scout 1 read the channel-A tone period back off the PSG while the note sounded
(the method and its control are documented there). `PLAY"L1C"` agreed exactly --
172/1, i.e. 428, C4 -- so the tone TABLE is right. `PLAY"L1N40"` did not: the
VG-8020 answered 83/1 = 339 and this tree 104/1 = 360. 360/339 = 1.062, which is
2^(1/12) to three figures: ONE SEMITONE, not a random table error.

  n=1 and n=96 are the ENDS of the published range, so a base that is off by one
  shows up as a different note at BOTH ends -- or as an error at one of them,
  which is louder still.
  n=38..42 straddle the measured disagreement, so the reading says whether the
  offset is CONSTANT (every n shifted the same way -- a base) or grows.
  n=0 is the published REST, and n=97 is out of range: `<E 5 >` is the answer a
  bounds check gives, and a period is the answer a missing one gives.

⚠️ n=0 SOUNDS NOTHING, so its R0/R1 reading is whatever was there before and
is NOT a verdict about pitch -- it is only asked to see whether it RAISES.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK")
NS = (0, 1, 2, 38, 39, 40, 41, 42, 96, 97)


def prog(mml: str) -> list[str]:
    b = ["ON ERROR GOTO 0",
         'PLAY"L1%s"' % mml,
         "FOR I=1 TO 200:NEXT",
         'PRINT"<";',
         "OUT&HA0,0:PRINT INP(&HA2);",
         "OUT&HA0,1:PRINT INP(&HA2);",
         'PRINT">":END',
         'PRINT"<E";ERR;">":END']
    b[0] = "ON ERROR GOTO %d" % (10 * len(b))
    return b


CASES = [("c4_ref", prog("C"))] + [("n%02d" % n, prog("N%d" % n)) for n in NS]


def main() -> int:
    cells: dict = {}
    for mach in MACHINES:
        print("===", mach, flush=True)
        specs = [("stored", lines) for _, lines in CASES]
        raws = omsx_repl.run_cases(mach, specs, batch=False, cap_gap=8.0)
        for (name, _), raw in zip(CASES, raws):
            txt = " ".join("".join(raw or "").split())
            r = txt.rfind("RUN")
            tail = txt[r + 3:] if r >= 0 else txt
            i, j = tail.find("<"), -1
            if i >= 0:
                j = tail.find(">", i + 1)
            cell = tail[i:j + 1] if i >= 0 and j > i else "?" + tail[:40]
            per = ""
            m = cell.replace("<", " ").replace(">", " ").split()
            if len(m) == 2 and m[0].lstrip("-").isdigit():
                per = "  period=%d" % (int(m[1]) * 256 + int(m[0]))
            cells.setdefault(mach, {})[name] = cell
            print(f"  {name:8} {cell!r}{per}", flush=True)
    verdict(cells.get(MACHINES[1], {}), cells.get(MACHINES[0], {}))
    return 0


def verdict(zb: dict, ref: dict) -> None:
    """🎯 THE VERDICT CHANNEL (D-RECLENV's shape, 2026-09-25): `DIFF <label>` per
    row where zerobas and the VG-8020 differ, then the sweep's `DIFF: n/m`.
    ⚠️ `n00` IS NOT SCORED -- the header says why: N0 is the REST, it sounds
    nothing, and its R0/R1 reading is whatever the previous note left."""
    rows = [k for k in zb if k != "n00"]
    bad = [k for k in rows if zb[k] != ref.get(k)]
    for k in bad:
        print(f"DIFF {k}  zb={zb[k]!r}  {MACHINES[0]}={ref.get(k)!r}", flush=True)
    print(f"DIFF: {len(bad)}/{len(rows)} rows diverging vs {MACHINES[0]} "
          f"(n00 unscored: a rest)", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
