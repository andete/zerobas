#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-EDFKEY: does PRESSING a function key type its `KEY` string at the editor,
on the VG-8020 and on ours?

Each case types a prefix (openMSX `type`), then presses keys through the matrix
(`keymatrixdown/up`: F1 = row 6 bit 5, F2 bit 6, F3 bit 7, F4 = row 7 bit 0,
F5 bit 1; SHIFT = row 6 bit 0), then optionally types a suffix, and reads the
screen rows 0..CSRY+1 (`.` = space, `#` = the cursor cell) plus CSRX/CSRY.

Headless, fresh boot per case. Clean room: typed/matrix keys, VRAM, work-area RAM.

    python3 -u scratchpad/edfkey_probe.py [CASE ...]
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
FK = {1: (6, 0x20), 2: (6, 0x40), 3: (6, 0x80), 4: (7, 0x01), 5: (7, 0x02)}
# case: (typed prefix, [(fkey, shifted)], typed suffix)
CASES = {
    "f1":        ("", [(1, False)], ""),
    "f2":        ("", [(2, False)], ""),
    "f3":        ("", [(3, False)], ""),
    "f4":        ("", [(4, False)], ""),
    "f5":        ("10 PRINT\\\"[R]\\\"\\r", [(5, False)], ""),
    "f6":        ("", [(1, True)], ""),
    "f7":        ("", [(2, True)], ""),
    "f8":        ("", [(3, True)], ""),
    "f9":        ("", [(4, True)], ""),
    "f10":       ("", [(5, True)], ""),
    "f1f1":      ("", [(1, False), (1, False)], ""),
    "key1abc":   ("KEY 1,\\\"ABC\\\"\\r", [(1, False)], ""),
    "key6abc":   ("KEY 6,\\\"XYZ\\\"\\r", [(1, True)], ""),
    "input_f1":  ("INPUT A\\$\\r", [(1, False)], "\\rPRINT\\\"\\[\\\";A\\$;\\\"\\]\\\"\\r"),
}


def measure(machine, case):
    pre, presses, post = CASES[case]
    out = os.path.join(HERE, "edfkey.txt")
    lines = ['after time 14 {type "CLS\\r"}']
    if pre:
        lines.append(f'after time 15 {{type "{pre}"}}')
    t = 19.0
    for k, sh in presses:
        r, m = FK[k]
        if sh:
            lines.append(f"after time {t:.2f} {{keymatrixdown 6 1}}")
        lines.append(f"after time {t + 0.05:.2f} {{keymatrixdown {r} {m}}}")
        lines.append(f"after time {t + 0.15:.2f} {{keymatrixup {r} {m}}}")
        if sh:
            lines.append(f"after time {t + 0.20:.2f} {{keymatrixup 6 1}}")
        t += 1.0
    if post:
        lines.append(f'after time {t + 0.5:.2f} {{type "{post}"}}')
        t += 3.0
    lines.append(f'''after time {t + 2:.2f} {{ set f [open "{out}" w]
  set y [debug read memory 0xF3DC]
  set s ""
  for {{set r 0}} {{$r <= [expr {{$y + 1}}]}} {{incr r}} {{
    for {{set i 0}} {{$i < 40}} {{incr i}} {{ set c [debug read VRAM [expr {{$r*40+$i}}]]
      if {{$c == 32}} {{append s "."}} elseif {{$c == 255}} {{append s "#"}} elseif {{$c < 32 || $c > 126}} {{append s "?"}} else {{append s [format %c $c]}} }}
    append s "|" }}
  puts $f "csrx=[debug read memory 0xF3DD] csry=$y rows=$s"
  close $f; exit }}''')
    tf = os.path.join(HERE, "edfkey.tcl")
    open(tf, "w").write("\n".join(lines) + "\n")
    if os.path.exists(out):
        os.remove(out)
    subprocess.run(["openmsx", "-machine", machine, "-command",
                    "set save_settings_on_exit false; set renderer none; set sound_driver null",
                    "-script", tf], capture_output=True, timeout=120)
    if not os.path.exists(out):
        return "<no reading>"
    # the prompt's TEXT is an identity marker by design (`ZB`), not an editor fact
    return open(out).read().strip().replace("ZB", "Ok")


def main():
    want = sys.argv[1:] or list(CASES)
    bad = 0
    for k in want:
        r, z = measure(REF, k), measure(ZB, k)
        same = r == z
        bad += not same
        print(f"{'SAME' if same else 'DIFF'} {k:9} ref: {r}\n{'':15}zb:  {z}", flush=True)
    print(f"\nDIFF: {bad}/{len(want)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
