#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FCBSTRIDE -- 265 or 267? Measure it before any stride is laid down.

Joost ruled 2026-09-16 that the channel block takes the MSX FCB shape. Two of
our own numbers disagree by 2 and nothing has ever reconciled them:
  * `FRE(0)` charges **267** a channel (D-MAXFRE, both references, linear to the
    ceiling, and the VG-8020 does it while DISKLESS);
  * `VARPTR(#n)` strides **265** (D-VARPTRN, both references).
The hypothesis is that they measure different things -- 265 is the FCB proper
(9 header + 256 record) and the other 2 a per-channel pointer entry in a separate
table, which is how MSX's `FILTAB` is publicly documented. **265 + 2 = 267 fits
exactly, and an arithmetic coincidence is not a measurement.**

🎯 THE ROW THAT DECIDES IT is not the stride -- it is where `VARPTR(#1)` MOVES TO
when a channel is added:
  * a layout of `[pointers: 2n][FCBs: 265n]` growing from a fixed top shifts
    `VARPTR(#1)` by **267** per extra channel while the #1->#2 stride stays 265;
  * an INTERLEAVED `[FCB][ptr][FCB][ptr]` layout would make the STRIDE 267, which
    is already refuted.
So a 267 shift with a 265 stride confirms the two-table reading, and any other
pair refutes it.

⚠️ `MAXFILES=` MAY CLEAR VARIABLES (it re-allocates), so every reading is its own
case and the arithmetic is done HERE, not in BASIC.
⚠️ zerobas answers ERR 2 to `VARPTR(#n)` -- that is the gap being closed, so its
VARPTR cells are EXPECTED to be errors and its `FRE` cells are the live control.
🔴 The CF-3300 is absent: boot-per-case delivery to it is mangled for this probe
shape (a known D-KWPLAY apparatus failure). Two sides, said out loud.
"""
import sys, os, re
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = ("C-BIOS_MSX1_EU_REPACK_DISK", "Philips_VG_8020")


def prog(*body: str) -> list[str]:
    """Trap line derived from the FINAL list -- `10*(len(body)+2)` is `END`."""
    lines = ["ON ERROR GOTO @T"] + list(body) + ["END", 'PRINT"<E";ERR;">":END']
    lines[0] = "ON ERROR GOTO %d" % (10 * len(lines))
    for l in lines:
        assert len(l) <= 34, (len(l), l)
        assert "@" not in l, l
    return lines


CASES = [
    # where FCB #1 sits, as the channel count grows: the deciding row
    ("p1_varptr1_mf1", prog("MAXFILES=1", 'PRINT"<V";VARPTR(#1);">"')),
    ("p2_varptr1_mf2", prog("MAXFILES=2", 'PRINT"<V";VARPTR(#1);">"')),
    ("p3_varptr1_mf3", prog("MAXFILES=3", 'PRINT"<V";VARPTR(#1);">"')),
    # the stride, re-confirmed rather than inherited
    ("s1_stride_12",   prog("MAXFILES=2", "A=VARPTR(#1)", "B=VARPTR(#2)",
                            'PRINT"<V";B-A;">"')),
    ("s2_stride_13",   prog("MAXFILES=3", "A=VARPTR(#1)", "C=VARPTR(#3)",
                            'PRINT"<V";C-A;">"')),
    # and the FRE charge, which is the other half of the disagreement
    ("f0_fre_mf0",     prog("MAXFILES=0", 'PRINT"<V";FRE(0);">"')),
    ("f1_fre_mf1",     prog("MAXFILES=1", 'PRINT"<V";FRE(0);">"')),
    ("f2_fre_mf2",     prog("MAXFILES=2", 'PRINT"<V";FRE(0);">"')),
    ("f3_fre_mf3",     prog("MAXFILES=3", 'PRINT"<V";FRE(0);">"')),
]


def main() -> int:
    for mach in MACHINES:
        print("===", mach, flush=True)
        specs = [("stored", lines) for _, lines in CASES]
        try:
            raws = omsx_repl.run_cases(mach, specs, batch=False, cap_gap=10.0)
        except Exception as exc:                       # noqa: BLE001
            print(f"  🔴 APPARATUS FAILURE on {mach}: "
                  f"{str(exc).splitlines()[0][:160]}", flush=True)
            continue
        vals = {}
        for (name, _), raw in zip(CASES, raws):
            txt = " ".join("".join(raw or "").split())
            i = txt.rfind("<V")
            j = txt.find(">", i + 1)
            if i >= 0 and j > i:
                cell = txt[i:j + 1]
                m = re.search(r"-?\d+", cell)
                if m:
                    vals[name] = int(m.group())
            else:
                k = txt.rfind("<E")
                cell = txt[k:k + 9] if k >= 0 else "<no reading>"
            print(f"  {name:16} {cell!r}", flush=True)
        # the arithmetic, done here and never in BASIC
        def d(a, b):
            if a in vals and b in vals:
                return vals[b] - vals[a]
            return None
        print(f"    VARPTR(#1) shift per channel : "
              f"mf1->mf2 {d('p1_varptr1_mf1', 'p2_varptr1_mf2')}, "
              f"mf2->mf3 {d('p2_varptr1_mf2', 'p3_varptr1_mf3')}", flush=True)
        print(f"    FRE charge per channel       : "
              f"{d('f1_fre_mf1', 'f0_fre_mf0')}, "
              f"{d('f2_fre_mf2', 'f1_fre_mf1')}, "
              f"{d('f3_fre_mf3', 'f2_fre_mf2')}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
