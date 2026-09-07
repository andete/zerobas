#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-FIELDALIAS — the SHARP form of the shared-buffer question.

D-TWOCHAN measured interleaved SEQUENTIAL reads on two channels and found no
loss, which is what licensed the decision not to reserve the reference's 267 B
per-channel buffers. One pattern is thin evidence for a permanent architectural
choice, and this is the pattern that should have gone first.

## Why this is sharper than the sequential row

`basic/sysvars.inc`: *"FIELD partitions a channel's record buffer into named
slices"*. A FIELD variable is not a copy — it IS a window onto the buffer. So
with per-channel buffers `F$` (on #1) and `G$` (on #2) look at DIFFERENT memory,
and with ONE shared buffer they look at the SAME memory.

That makes the divergence visible WITHOUT any re-read, which is what the
sequential row could not do: there, every observation followed a fresh `GET`, so
a correct re-read hid the sharing. Here the reading is taken from `F$` **after a
GET on the OTHER channel and with no GET on #1 in between**:

    90  GET #1,1
    95  P$=F$      -> AAAAAAAA on any machine
    100 GET #2,1              <- evicts #1's record from a SHARED buffer
    105 Q$=F$      -> AAAAAAAA if #1 has its own buffer
                      ZZZZZZZZ if F$ and G$ are the same memory

`t.same` is the control: `R$=G$` immediately after `GET #2,1` must read
ZZZZZZZZ on both, or the fixture never took and Q$ proves nothing.

⚠️ A DIVERGENCE HERE WOULD NOT REOPEN THE 267 B — it would mean FIELD variables
need their own backing, which is a much smaller thing than a per-channel sector
buffer. Naming that now so the result is not over-read either way.
"""
from __future__ import annotations

import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_tmp                                                  # noqa: E402

FIXTURE = os.path.join(ROOT, "disk", "test720.dsk")
SIDES = {
    "cf3300": ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW")),
    "zb": (os.environ.get("ZEROBAS_BASIC_MACHINE",
                          "C-BIOS_MSX1_EU_REPACK_DISK"), 8.0, ("NEW",)),
}

PROG = ['10 MAXFILES=2',
        '20 OPEN"TFA.DAT"AS #1 LEN=8:FIELD #1,8 AS F$',
        '30 LSET F$="AAAAAAAA":PUT #1,1:CLOSE',
        '40 OPEN"TFB.DAT"AS #1 LEN=8:FIELD #1,8 AS G$',
        '50 LSET G$="ZZZZZZZZ":PUT #1,1:CLOSE',
        '60 OPEN"TFA.DAT"AS #1 LEN=8:FIELD #1,8 AS F$',
        '65 OPEN"TFB.DAT"AS #2 LEN=8:FIELD #2,8 AS G$',
        '70 GET #1,1',
        '75 P$=F$',
        '80 GET #2,1',
        '85 Q$=F$',
        '90 R$=G$',
        '95 CLOSE',
        '99 PRINT"ZW";P$;",";Q$;",";R$;"WZ":END']


def run(side):
    machine, boot, reset = SIDES[side]
    dsk = probe_tmp.tmp(f"fieldalias_{side}.dsk")
    shutil.copyfile(FIXTURE, dsk)
    raw = "".join(omsx_repl.run_cases(
        machine, [("direct", list(reset) + PROG + ["RUN"])], batch=False,
        # cap_gap=60: D-TWOCHAN measured the CF-3300 still RUNNING at 12 s on a
        # program with this many opens; a short window reads `<NO READING>` and
        # invites it to be filed as the reference's behaviour.
        reset=(), boot=boot, step=8.0, cap_gap=60.0, timeout=400.0,
        diska=dsk)[0] or "")
    # the fence is in the SOURCE too (line 99), so: LAST match, and refuse any
    # match carrying source punctuation [[trapsvc-echo-fence]]
    for g in reversed(re.findall(r"ZW([^,]*),([^,]*),([^W]*)WZ", raw)):
        if any(ch in "".join(g) for ch in '"$;'):
            continue
        return [x.strip() or "<empty>" for x in g]
    return None


def main() -> int:
    got = {s: run(s) for s in SIDES}
    for s, v in got.items():
        print(f"  {s:7s} {v if v else '<NO READING (only the echo matched)>'}")
    if not all(got.values()):
        print("\n🔴 INSTRUMENT FAULT: a side produced no reading; nothing "
              "below is scored.")
        return 2

    names = ["P$ (F$ after its own GET)",
             "Q$ (F$ after a GET on #2)  🎯 THE READING",
             "R$ (G$ after GET #2)       control"]
    print(f"\n{'field':34s} {'cf3300':>10s} {'zb':>10s}   verdict")
    dis = []
    for i, nm in enumerate(names):
        c, z = got["cf3300"][i], got["zb"][i]
        v = "SAME" if c == z else "🔴 DIFF"
        if c != z:
            dis.append(nm.split()[0])
        print(f"{nm:34s} {c:>10s} {z:>10s}   {v}")
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'} ===")
    if not dis:
        print("🟢 FIELD variables on two open channels do NOT alias here "
              "either: the per-channel buffer buys nothing zerobas lacks.")
    else:
        print("🔴 FIELD variables ALIAS across channels. This does NOT "
              "reopen the 267 B — it means FIELD needs its own backing, a much "
              "smaller thing than a per-channel sector buffer.")
    return 1 if dis else 0


if __name__ == "__main__":
    raise SystemExit(main())
