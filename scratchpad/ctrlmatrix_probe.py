#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CTRLKEYS: with CTRL held, which code does EVERY key of matrix rows 0-5
produce -- letters, digits and symbols? One boot per machine: a BASIC loop prints
the code of each key read, while this script holds CTRL (row 6 bit 1) and
presses each (row, bit) in turn through openMSX's keymatrixdown/up.

    python3 -u ctrlmatrix_probe.py [MACHINE ...]
"""
import os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MACHINES = sys.argv[1:] or ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]
KEYS = [(r, b) for r in range(6) for b in range(8)]


def measure(machine):
    out = os.path.join(HERE, f"ctrlmatrix_{machine}.txt")
    lines = [
        'after time 14 {type "CLS\\r"}',
        'after time 15 {type "10 A\\$=INPUT\\$(1):POKE \\&HD000+N,ASC(A\\$):N=N+1:POKE \\&HD0FF,N:GOTO 10\\rRUN\\r"}',
    ]
    t = 26.0
    for r, b in KEYS:
        lines.append(f"after time {t:.2f} {{keymatrixdown 6 2}}")
        lines.append(f"after time {t + 0.05:.2f} {{keymatrixdown {r} {1 << b}}}")
        lines.append(f"after time {t + 0.15:.2f} {{keymatrixup {r} {1 << b}}}")
        lines.append(f"after time {t + 0.20:.2f} {{keymatrixup 6 2}}")
        t += 0.35
    lines.append(f'''after time {t + 1:.2f} {{ set f [open "{out}" w]
  set n [debug read memory 0xD0FF]
  set s ""
  for {{set i 0}} {{$i < $n}} {{incr i}} {{ append s "<[debug read memory [expr {{0xD000+$i}}]]>" }}
  puts $f "n=$n $s"
  close $f; exit }}''')
    tf = os.path.join(HERE, "ctrlmatrix.tcl")
    open(tf, "w").write("\n".join(lines) + "\n")
    if os.path.exists(out):
        os.remove(out)
    subprocess.run(["openmsx", "-machine", machine, "-command",
                    "set save_settings_on_exit false; set renderer none; set sound_driver null",
                    "-script", tf], capture_output=True, timeout=180)
    if not os.path.exists(out):
        return None
    return [int(x) for x in re.findall(r"<\s*(-?\d+)\s*>", open(out).read())]


def main():
    res = {m: measure(m) for m in MACHINES}
    for m, codes in res.items():
        print(f"{m}: {len(codes or [])} codes read (of {len(KEYS)} keys)")
    ref = res[MACHINES[0]]
    for m in MACHINES:
        print(f"\n{m}:")
        print("  " + " ".join(f"{c:3}" for c in (res[m] or [])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
