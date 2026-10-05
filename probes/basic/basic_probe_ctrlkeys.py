#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""ctrlkeys-acceptance (D-CTRLKEYS) -- the code a program reads for a CTRL key.

Until cbios-repack/ctrl-keys.patch (2026-10-05), C-BIOS's key decode ignored
CTRL: CTRL-E read 101 (`e`) where the VG-8020 reads 5, so neither a program nor
the screen editor could see a CTRL key. Two readings, VG-8020 against ours:

  codes   `A$=INPUT$(1):PRINT ASC(A$)`, then CTRL-A/B/E/F/N/U/Z, TAB, ESC and a
          plain `e` (the controls: they never depended on CTRL)
  matrix  CTRL held (row 6 bit 1) over EVERY key of matrix rows 0-5, each code
          POKEd to RAM (a CTRL-L would clear the screen) -- the VG-8020 gives 30
          codes for 48 keys: letters 1..26, `\\` `[` `]` 28 27 29, `` ` `` 0, and
          NOTHING for digits and the other symbols

Headless, fresh boot per reading. Clean room: typed/matrix keys, VRAM and RAM.
Exit 0 all agree; 1 a divergence; 2 the reference gave no reading.

    python3 -u probes/basic/basic_probe_ctrlkeys.py
"""
import os, re, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import probe_tmp                                   # noqa: E402  the one temp root
import omsx_preflight                              # noqa: E402  the spawn guard

REF = "Philips_VG_8020"
ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
KEYS = {"CTRL-A": "\\x01", "CTRL-B": "\\x02", "CTRL-E": "\\x05", "CTRL-F": "\\x06",
        "TAB": "\\x09", "CTRL-N": "\\x0e", "CTRL-U": "\\x15", "CTRL-Z": "\\x1a",
        "ESC": "\\x1b", "plain e": "e"}
MATRIX = [(r, b) for r in range(6) for b in range(8)]


def openmsx(machine, tcl):
    tf = probe_tmp.tmp("ctrlkeys.tcl")
    open(tf, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded(
        ["openmsx", "-machine", machine, "-command",
         "set save_settings_on_exit false; set renderer none; set sound_driver null",
         "-script", tf]), capture_output=True, timeout=180)


def code_of(machine, key):
    out = probe_tmp.tmp("ctrlkeys_code.txt")
    if os.path.exists(out):
        os.remove(out)
    openmsx(machine, f'''after time 14 {{type "CLS\\r"}}
after time 15 {{type "A\\$=INPUT\\$(1):PRINT\\"\\[\\";ASC(A\\$);\\"\\]\\"\\r"}}
after time 18 {{type "{key}"}}
after time 21 {{ set f [open "{out}" w]
  set s ""
  for {{set i 0}} {{$i < 400}} {{incr i}} {{ set c [debug read VRAM $i]
    if {{$c < 32 || $c > 126}} {{append s "."}} else {{append s [format %c $c]}} }}
  puts $f $s
  close $f; exit }}
''')
    if not os.path.exists(out):
        return None
    m = re.findall(r"\[\s*(-?\d+)\s*\]", open(out).read())
    return m[-1] if m else None


def matrix_of(machine):
    out = probe_tmp.tmp("ctrlkeys_matrix.txt")
    if os.path.exists(out):
        os.remove(out)
    lines = ['after time 14 {type "CLS\\r"}',
             'after time 15 {type "10 A\\$=INPUT\\$(1):POKE \\&HD000+N,ASC(A\\$):N=N+1:'
             'POKE \\&HD0FF,N:GOTO 10\\rRUN\\r"}']
    t = 26.0
    for r, b in MATRIX:
        lines += [f"after time {t:.2f} {{keymatrixdown 6 2}}",
                  f"after time {t + 0.05:.2f} {{keymatrixdown {r} {1 << b}}}",
                  f"after time {t + 0.15:.2f} {{keymatrixup {r} {1 << b}}}",
                  f"after time {t + 0.20:.2f} {{keymatrixup 6 2}}"]
        t += 0.35
    lines.append(f'''after time {t + 1:.2f} {{ set f [open "{out}" w]
  set n [debug read memory 0xD0FF]
  set s ""
  for {{set i 0}} {{$i < $n}} {{incr i}} {{ append s "<[debug read memory [expr {{0xD000+$i}}]]>" }}
  puts $f "n=$n $s"
  close $f; exit }}''')
    openmsx(machine, "\n".join(lines) + "\n")
    if not os.path.exists(out):
        return None
    return [int(x) for x in re.findall(r"<(\d+)>", open(out).read())]


def main():
    bad = 0
    for name, key in KEYS.items():
        r, z = code_of(REF, key), code_of(ZB, key)
        if r is None:
            print(f"INSTRUMENT FAULT: the VG-8020 gave no reading for {name}")
            return 2
        bad += r != z
        print(f"{'ok  ' if r == z else 'DIFF'} code   {name:8} VG-8020 {r:>4}   zb {z}")
    r, z = matrix_of(REF), matrix_of(ZB)
    if not r:
        print("INSTRUMENT FAULT: the VG-8020 gave no matrix reading")
        return 2
    bad += r != z
    print(f"{'ok  ' if r == z else 'DIFF'} matrix CTRL x 48 keys: VG-8020 {len(r)} codes, zb {len(z or [])}")
    if r != z:
        print(f"     VG-8020 {r}\n     zb      {z}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: CTRL keys read as on the VG-8020 ({bad} divergence(s))")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
