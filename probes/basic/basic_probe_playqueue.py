#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""playqueue-acceptance (D-PLAYQUEUE): a PLAY while a voice is still playing APPENDS
to its 128-byte queue, waits when the queue is full, and the voices sync at each
PLAY's end -- with the reference's queue byte counts and BEEP's reset.

Found by the program ladder's L4_music: a song played bar by bar from DATA kept
only its last bar (396 jiffies on the VG-8020, 104 here). Four programs, both
zerobas targets against the VG-8020: the queue bytes each MML element costs, read
from QUETAB's put pointer (scratchpad/playqbytes_measure.bas, playqbytes2_measure.bas),
an M with no note after it across a PLAY and a BEEP (plaympend_measure.bas), and
the timing behaviour (playqueue_gate.bas: the block points' spacing exact, totals
within a few jiffies -- the reference's PLAY starts a little later, D-PLAYRATE).

Clean-room: a tape in; the printer port out; QUETAB is documented work-area RAM.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs                                  # noqa: E402

PROGS = [("scratchpad/playqbytes_measure.bas", 16),
         ("scratchpad/playqbytes2_measure.bas", 11),
         ("scratchpad/plaympend_measure.bas", 3),
         ("scratchpad/playqueue_gate.bas", 5)]


def main():
    bad = 0
    for prog, rows in PROGS:
        text = open(os.path.join(REPO, prog)).read()
        ref = run_programs.run(run_programs.REF, "playqueue", text)
        rl = ref[1].replace("\r", "").splitlines()
        print(f"{prog}\n  {run_programs.REF:30} {ref[0]}  {len(rl)} rows")
        for m in run_programs.ZB:
            zb = run_programs.run(m, "playqueue", text)
            zl = zb[1].replace("\r", "").splitlines()
            diff = [(a, b) for a, b in zip(rl, zl) if a != b]
            ok = len(rl) == rows and zl == rl
            bad += not ok
            print(f"  {m:30} {zb[0]}  {len(diff)} differ  {'SAME' if ok else 'DIVERGES'}")
            for a, b in diff:
                print(f"      ref {a!r}  zb {b!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: PLAY appends, waits when the queue is full and "
          f"syncs the voices, as on the VG-8020")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
