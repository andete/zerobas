#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Regression guard for arrays slice-4b §13a-F1 (cold-boot wild write).

F1 (Fable adversarial review, 2026-07-17): slice-4b added `call vars_reset` to
`clear_vars`, which reads (PRGEND) and WRITES a $0000 array sentinel THROUGH
(ARYTAB)=(PRGEND)+2. At cold INIT `clear_vars` runs BEFORE `new_prog` sets
PRGEND, so PRGEND still holds power-on RAM garbage -> a wild write. With garbage
PRGEND=$FC48, (PRGEND)+2 == HIMEM ($FC4A), so the boot zeroes HIMEM.

This is GREEN-SUITE-INVISIBLE: openMSX zero-fills RAM, so PRGEND reads $0000 and
the write lands at $0002 (ROM, a silent no-op) -- every differential/acceptance
suite passes. Only PLANTED garbage in PRGEND (as here) exposes it. The fix
removes the `vars_reset` call from `clear_vars` (every caller resets the
scalar+array regions itself AFTER establishing PRGEND).

Method: break at `clear_vars` entry, plant PRGEND=$FC48 + a HIMEM sentinel
($F380); break at `new_prog` entry (after clear_vars ran, before new_prog
rewrites PRGEND); read HIMEM back. FIXED => HIMEM survives ($F380). BUGGY =>
$0000. Non-vacuous: re-adding the `clear_vars` vars_reset call turns it red
(confirmed: pre-fix this probe reads HIMEM=$0000).

Repack-only (clear_vars/vars_reset are IF ROM_BASE < $4000). Runs the installed
repack machine; run `make repack-machine` first. Reads addresses from
build/basic-reloc.sym so it survives relayout.
"""
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYM = os.path.join(ROOT, "build", "basic-reloc.sym")
MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

# Fixed system-var addresses (basic/sysvars.inc; RAM, mapping-independent).
PRGEND = 0xE026
HIMEM = 0xFC4A
GARBAGE_PRGEND = 0xFC48        # +2 == HIMEM: the F1 corruption target
HIMEM_SENTINEL = 0xF380


def find_omsx():
    for c in (os.environ.get("OPENMSX"),
              "/opt/homebrew/bin/openmsx", "openmsx"):
        if c and (os.path.sep not in c or os.path.exists(c)):
            return c
    return "openmsx"


def sym_addr(name):
    with open(SYM) as f:
        for line in f:
            m = re.match(rf"^{name}\s+EQU\s+([0-9A-Fa-f]+)H", line)
            if m:
                return int(m.group(1), 16)
    raise SystemExit(f"symbol {name} not found in {SYM} (run `make basic-reloc`)")


def main():
    clear_vars = sym_addr("clear_vars")
    new_prog = sym_addr("new_prog")
    out = tempfile.NamedTemporaryFile("r", suffix=".txt", delete=False)
    out.close()
    tcl = tempfile.NamedTemporaryFile("w", suffix=".tcl", delete=False)
    tcl.write(f"""
debug set_bp {clear_vars:#06x} {{}} {{
    poke {PRGEND} {GARBAGE_PRGEND & 0xFF} ; poke {PRGEND + 1} {GARBAGE_PRGEND >> 8}
    poke {HIMEM} {HIMEM_SENTINEL & 0xFF} ; poke {HIMEM + 1} {HIMEM_SENTINEL >> 8}
}}
debug set_bp {new_prog:#06x} {{}} {{
    set fh [open "{out.name}" w]
    puts $fh [format "%02x%02x" [peek {HIMEM + 1}] [peek {HIMEM}]]
    close $fh
    exit
}}
after time 20 {{ exit }}
""")
    tcl.close()
    subprocess.run([find_omsx(), "-machine", MACHINE,
                    "-command", "set renderer none", "-script", tcl.name],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=60)
    with open(out.name) as f:
        himem = (f.read().strip() or "????").lower()
    os.unlink(tcl.name)
    os.unlink(out.name)

    want = f"{HIMEM_SENTINEL:04x}"
    if himem == want:
        print(f"PASS  §13a-F1: HIMEM survived garbage-PRGEND cold-boot "
              f"(HIMEM={himem}, sentinel intact)")
        return 0
    print(f"FAIL  §13a-F1: cold-boot wild write through garbage PRGEND -- "
          f"HIMEM={himem} (want {want}; $0000 == the F1 corruption)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
