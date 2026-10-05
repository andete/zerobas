#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-EDCTRL, cause 1: which CODE does a program read for a CTRL key?

scratchpad/edctrl_probe.py showed CTRL-E typed at the editor landing as a
lowercase `e` on ours -- so the key never reached sub/readline.asm as $05. This
asks the keyboard layer alone, below the editor: `A$=INPUT$(1):PRINT ASC(A$)`,
then the key, on the VG-8020 and on ours.

Headless, fresh boot per key. Clean room: typed keys and VRAM only.

    python3 -u scratchpad/ctrlkey_probe.py
"""
import os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
KEYS = {"CTRL-A": "\\x01", "CTRL-B": "\\x02", "CTRL-E": "\\x05", "CTRL-F": "\\x06",
        "TAB": "\\x09", "CTRL-N": "\\x0e", "CTRL-U": "\\x15", "CTRL-Z": "\\x1a",
        "ESC": "\\x1b", "plain e": "e"}


def measure(machine, key):
    out = os.path.join(HERE, "ctrlkey.txt")
    tcl = f'''after time 14 {{type "CLS\\r"}}
after time 15 {{type "A\\$=INPUT\\$(1):PRINT\\"\\[\\";ASC(A\\$);\\"\\]\\"\\r"}}
after time 18 {{type "{key}"}}
after time 21 {{ set f [open "{out}" w]
  set s ""
  for {{set i 0}} {{$i < 400}} {{incr i}} {{ set c [debug read VRAM $i]
    if {{$c < 32 || $c > 126}} {{append s "."}} else {{append s [format %c $c]}} }}
  puts $f $s
  close $f; exit }}
'''
    tf = os.path.join(HERE, "ctrlkey.tcl")
    open(tf, "w").write(tcl)
    if os.path.exists(out):
        os.remove(out)
    subprocess.run(["openmsx", "-machine", machine, "-command",
                    "set save_settings_on_exit false; set renderer none; set sound_driver null",
                    "-script", tf], capture_output=True, timeout=120)
    if not os.path.exists(out):
        return "<no reading>"
    m = re.findall(r"\[\s*(-?\d+)\s*\]", open(out).read())
    return m[-1] if m else "<no [n]>"


def main():
    bad = 0
    for name, key in KEYS.items():
        r, z = measure(REF, key), measure(ZB, key)
        bad += r != z
        print(f"{'SAME' if r == z else 'DIFF'} {name:8} ref {r:>6}   zb {z:>6}")
    print(f"\nDIFF: {bad}/{len(KEYS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
