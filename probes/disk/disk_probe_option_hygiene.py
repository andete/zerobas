#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Behavioural probe: BSAVE/BLOAD option-parse HYGIENE — a malformed option flag
must be REJECTED (our `load error`), never silently perform the operation.

Closure-spec item 2 (disk/docs/spec-diskbasic-option-closure.md), "honest at the
walls": before this pass, BLOAD silently ignored any comma-flag that was not `R`
and BSAVE mis-evaluated a stray 4th token as an exec address — a typo produced a
silent wrong-address load/save, the exact trap that hid the VRAM `,S` gap. The
parsers now recognize exactly `R`/`S` (BLOAD) and `S`/numeric-exec (BSAVE) and
reject everything else.

OURS-ONLY, by design (NOT a CF-3300 differential). Our reject model is
`load_error` (print "load error", CONTINUE the program); stock MSX raises a
`Syntax error` that HALTS the program — so on the shared cases (`,X`, BSAVE `,Q`)
the two AGREE that no load/save happens but DIVERGE on control flow, and for the
deferred `,offset` case we DELIBERATELY diverge from stock (stock supports an
offset; we reject it until the offset follow-on lands, closure-spec Q1.4). The
common, gate-able truth — "a malformed option performs NO silent operation" — is
asserted here on our machine. Provenance: exercises our own ROM only; no stock
ROM is read.

The `.bas` test program (readable BASIC, tokenised by OUR OWN ROM crunch via
bas_tokenise.py). load_error is non-fatal on our ROM, so all four negatives run
in one boot; each records a witness of RAM $C000 (the wiped region) so a silent
load is caught:

    10 FORI=0TO16:POKE&HC000+I,I*3+7:NEXT     ' pattern in RAM
    20 BSAVE"A:SV.BIN",&HC000,&HC010           ' a valid BSAVE file to (not) load
    30 FORI=0TO16:POKE&HC000+I,&HA5:NEXT        ' wipe the region to $A5
    40 BLOAD"A:SV.BIN",X                         ' NEG1 unrecognized flag -> reject
    41 POKE&HD0F0,PEEK(&HC000)                    ' witness1 (expect $A5 = not loaded)
    50 BLOAD"A:SV.BIN",S,100                      ' NEG2 deferred ,offset -> reject
    51 POKE&HD0F1,PEEK(&HC000)                    ' witness2 (expect $A5 = not loaded)
    60 BSAVE"A:SV2.BIN",&HC000,&HC010,Q          ' NEG3 bad 4th token -> reject (no create)
    70 BLOAD"A:SV.BIN"                            ' POSITIVE control: valid load DOES restore
    71 POKE&HD0F2,PEEK(&HC000)                    ' witness3 (expect $07 = pattern[0], loaded)
    80 POKE&HD0FF,&H99                            ' DONE sentinel

Checks (all on OUR machine):
  1. VACUITY / non-fatal: $D0FF == $99 -- the program ran through ALL four negatives
     to completion (proves each reject was a non-fatal `load error`, not a crash).
  2. NEG1 witness1 ($D0F0) == $A5 -- BLOAD",X" did NOT load (region stayed wiped).
  3. NEG2 witness2 ($D0F1) == $A5 -- BLOAD",S,100" (deferred offset) did NOT load.
  4. NEG3: SV2.BIN is ABSENT from the disk -- BSAVE",Q" rejected BEFORE the file
     create (the bad 4th token never reached disk_write_begin).
  5. POSITIVE control witness3 ($D0F2) == $07 (pattern[0]) -- the plain BLOAD"A:SV.BIN"
     DID restore the region, proving the file + load path are healthy, so the four
     rejections above were genuine wall-rejections, not a broken/unreadable file.

TEST DISK SAFETY: a FRESH /tmp image built by this probe; disk/test720.dsk is
never touched. Clean-room: `.bas` source is our own program, tokenised by our own
ROM; the disk image is built per the public FAT12 spec.

Prerequisites: `make all` then `make machines-oracle` so C-BIOS_MSX1_EU_BASIC_DISK
reflects the build under test.

    python3 probes/disk/disk_probe_option_hygiene.py
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_sys.path.insert(0, _os.path.join(_ROOT, "tools"))  # make_test_dsk.py (Fat12Image)

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from make_test_dsk import Fat12Image  # noqa: E402  (path set up above)
from bas_tokenise import make_basic_file  # noqa: E402  (our-ROM tokeniser helper)

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"

OURS_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE")

TXTBASE = 0x8001

BIN_START = 0xC000
BIN_END = 0xC010
WIPE_BYTE = 0xA5
W1_ADDR, W2_ADDR, W3_ADDR = 0xD0F0, 0xD0F1, 0xD0F2
DONE_ADDR = 0xD0FF
DONE_BYTE = 0x99
POISON = 0x11                              # pre-boot poison for every witness cell

# pattern[0] = (0*3+7) = 7; the POSITIVE control expects this back at $C000.
PATTERN0 = (0 * 3 + 7) & 0xFF
assert PATTERN0 != WIPE_BYTE

AUTOEXEC_LINES = [
    (10, "FORI=0TO16:POKE&HC000+I,I*3+7:NEXT"),
    (20, 'BSAVE"A:SV.BIN",&HC000,&HC010'),
    (30, f"FORI=0TO16:POKE&HC000+I,&H{WIPE_BYTE:02X}:NEXT"),
    (40, 'BLOAD"A:SV.BIN",X'),                       # NEG1 unrecognized flag
    (41, f"POKE&H{W1_ADDR:04X},PEEK(&HC000)"),
    (50, 'BLOAD"A:SV.BIN",S,100'),                   # NEG2 deferred offset
    (51, f"POKE&H{W2_ADDR:04X},PEEK(&HC000)"),
    (60, 'BSAVE"A:SV2.BIN",&HC000,&HC010,Q'),        # NEG3 bad 4th token (no create)
    (70, 'BLOAD"A:SV.BIN"'),                          # POSITIVE control
    (71, f"POKE&H{W3_ADDR:04X},PEEK(&HC000)"),
    (80, f"POKE&H{DONE_ADDR:04X},&H{DONE_BYTE:02X}"),
]


def build_disk() -> str:
    img = Fat12Image()
    img.add_file("AUTOEXEC", "BAS", make_basic_file(AUTOEXEC_LINES, TXTBASE))
    fd, path = tempfile.mkstemp(suffix=".dsk", prefix="opt_hygiene_probe_")
    os.close(fd)
    with open(path, "wb") as f:
        f.write(img.finish())
    return path


# --- offline FAT12 root-dir scan: is `name8.ext3` present? (public FAT spec) ---
def file_present(dsk_path: str, name8: str, ext3: str) -> bool:
    img = open(dsk_path, "rb").read()

    def rd16(o):
        return img[o] | (img[o + 1] << 8)
    rsvd, nfat, root_ent, spf = rd16(14), img[16], rd16(17), rd16(22)
    bps = rd16(11)
    root_start = rsvd + nfat * spf
    root_off = root_start * bps
    want = (name8.encode().ljust(8)[:8] + ext3.encode().ljust(3)[:3]).upper()
    for i in range(root_ent):
        e = img[root_off + i * 32: root_off + i * 32 + 32]
        if not e or e[0] in (0x00, 0xE5):
            continue
        if bytes(e[0:11]).upper() == want:
            return True
    return False


def cold_boot_and_capture(machine: str, dsk: str, out_path: str,
                          timeout: float = 60.0) -> dict:
    tcl = f"""set throttle off
set renderer none
proc poison {{}} {{
  foreach a {{0x{W1_ADDR:04X} 0x{W2_ADDR:04X} 0x{W3_ADDR:04X} 0x{DONE_ADDR:04X}}} {{
    debug write memory $a 0x{POISON:02X}
  }}
}}
after time 1 {{ poison }}
proc cap {{}} {{
  set f [open {{{out_path}}} w]
  puts $f "done=[format %02X [debug read memory 0x{DONE_ADDR:04X}]]"
  puts $f "w1=[format %02X [debug read memory 0x{W1_ADDR:04X}]]"
  puts $f "w2=[format %02X [debug read memory 0x{W2_ADDR:04X}]]"
  puts $f "w3=[format %02X [debug read memory 0x{W3_ADDR:04X}]]"
  close $f
  exit
}}
after time 25 {{ cap }}
"""
    tcl_path = out_path + ".tcl"
    open(tcl_path, "w").write(tcl)
    if os.path.exists(out_path):
        os.unlink(out_path)
    cmd = [OMSX, "-machine", machine, "-diska", dsk, "-script", tcl_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT cold-booting {machine} with {dsk}")
    if not os.path.exists(out_path):
        sys.exit(f"no capture from {machine} (ROMs/machine missing?)")
    d = {}
    for ln in open(out_path):
        k, _, v = ln.strip().partition("=")
        d[k] = v
    for k in ("done", "w1", "w2", "w3"):
        if k not in d:
            sys.exit(f"capture from {machine} missing key {k!r}: {d!r}")
    return d


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ours-machine", default=OURS_MACHINE)
    args = ap.parse_args()
    if not args.ours_machine:
        sys.exit("no zerobas machine: pass --ours-machine or set $ZEROBAS_BASIC_MACHINE; there is no\n"
                 "default, one would silently pick the BUILD under test "
                 "(docs/spec-lean-retire-s1-explicit-machine.md).")

    print("BSAVE/BLOAD option-parse hygiene: a malformed flag must be rejected "
          "(our `load error`), never silently perform the op. OURS-ONLY behavioural.")

    dsk = build_disk()
    ok = True
    try:
        cap = cold_boot_and_capture(args.ours_machine, dsk, "/tmp/opt_hygiene_ours.txt")
        done = int(cap["done"], 16)
        w1, w2, w3 = int(cap["w1"], 16), int(cap["w2"], 16), int(cap["w3"], 16)
        sv2 = file_present(dsk, "SV2", "BIN")

        c_done = done == DONE_BYTE
        print(f"  [{'PASS' if c_done else 'FAIL'}] non-fatal vacuity: (${DONE_ADDR:04X})=${done:02X} "
              f"(expect ${DONE_BYTE:02X} -- ran through all four negatives)")

        c1 = w1 == WIPE_BYTE
        print(f"  [{'PASS' if c1 else 'FAIL'}] NEG1 BLOAD\"..\",X unrecognized flag: "
              f"$C000=${w1:02X} (expect ${WIPE_BYTE:02X} -- NOT loaded)")

        c2 = w2 == WIPE_BYTE
        print(f"  [{'PASS' if c2 else 'FAIL'}] NEG2 BLOAD\"..\",S,100 deferred offset: "
              f"$C000=${w2:02X} (expect ${WIPE_BYTE:02X} -- NOT loaded)")

        c3 = not sv2
        print(f"  [{'PASS' if c3 else 'FAIL'}] NEG3 BSAVE\"..\",Q bad 4th token: "
              f"SV2.BIN {'absent' if c3 else 'PRESENT'} (expect absent -- rejected before create)")

        c4 = w3 == PATTERN0
        print(f"  [{'PASS' if c4 else 'FAIL'}] POSITIVE control BLOAD\"..\" (no flag): "
              f"$C000=${w3:02X} (expect ${PATTERN0:02X} -- valid load DID restore)")

        ok = c_done and c1 and c2 and c3 and c4
    finally:
        os.unlink(dsk)

    print("\n" + ("ALL PASS -- every malformed BSAVE/BLOAD option is rejected without "
                  "silently performing the operation, and the valid load still works"
                  if ok else "FAIL -- see per-check results above"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
