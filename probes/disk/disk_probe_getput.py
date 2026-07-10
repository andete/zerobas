#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional + differential oracle for zerobas-BASIC random-access GET/PUT
(Phase 2c slice 2).

A random file's record buffer (FIELDed into A$/B$) is written to disk record N with
PUT #f,N and read back with GET #f,N. The record length is 256 bytes, so records 1
and 2 share one 512-byte disk sector — PUT #1,2 must read-modify-write that sector to
preserve record 1. The test writes two records, CLOSES, REOPENS (proving the
directory entry was stamped with size + first cluster so the file is found again),
re-FIELDs, and reads both records back:

  OPEN "D.DAT" AS #1 : FIELD #1,5 AS A$,5 AS B$
  LSET A$="alpha" : RSET B$="bet" : PUT #1,1     ' record 1 = "alpha" + "  bet"
  LSET A$="gamma" : LSET B$="delta" : PUT #1,2    ' record 2 = "gamma" + "delta"
  CLOSE
  OPEN "D.DAT" AS #1 : FIELD #1,5 AS A$,5 AS B$
  GET #1,1 : PRINT "<";A$;"|";B$;">"              ' -> <alpha|  bet>
  GET #1,2 : PRINT "<";A$;"|";B$;">"              ' -> <gamma|delta>
  CLOSE

The two printed lines are each `<` + 11 chars + `>` (5 + '|' + 5). Reading the right
bytes back after a close/reopen proves the whole path: chain allocation, the shared-
sector read-modify-write, and the directory stamp. The real National CF-3300 produces
the byte-identical pair.

Strictly black-box: types REPL lines, reads VRAM. /tmp copy of the disk only.
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"
ZEROBAS = os.environ.get("ZEROBAS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC_DSK = os.environ.get("DISK_DSK", os.path.join(ZEROBAS, "disk", "test720.dsk"))

PROGRAM = [
    'open"d.dat" as #1',
    'field#1,5 as a$,5 as b$',
    'lset a$="alpha"',
    'rset b$="bet"',
    "put#1,1",
    'lset a$="gamma"',
    'lset b$="delta"',
    "put#1,2",
    "close",
    'open"d.dat" as #1',
    'field#1,5 as a$,5 as b$',
    "get#1,1",
    'print"<";a$;"|";b$;">"',
    "get#1,2",
    'print"<";a$;"|";b$;">"',
    "close",
]
EXPECT = ["alpha|  bet", "gamma|delta"]   # record 1 (RSET "bet"), record 2 (LSET "delta")


# REPL line delivery: inject each line straight into the MSX BIOS type-ahead
# buffer (KEYBUF) rather than emulating keystrokes with openMSX `type`. The `type`
# command drives the keyboard MATRIX, whose per-key press/scan alignment is timing-
# fragile: under load a leading key can register twice ("print"->"pprint" -> a
# spurious `syntax error`), and the exact alignment shifts with any change to CPU
# timing — e.g. adding one real BASIC keyword costs an extra match_kw scan per word,
# which silently tipped this into failure. Injection is deterministic and content-
# insensitive: the interpreter reads these bytes through CHGET exactly as typed, but
# no matrix scan is involved, so nothing can double. Uses only the PUBLISHED MSX BIOS
# contract (MSX2 Technical Handbook system-variable map) — no ROM disassembly:
#   KEYBUF $FBF0 (40-byte circular type-ahead buffer), GETPNT $F3FA / PUTPNT $F3F8
#   (the read / write cursors CHSNS+CHGET consult; empty when GETPNT==PUTPNT).
# Verified black-box that C-BIOS honours it (a real MSX1 like the CF-3300 does by
# construction — this is where the standard comes from).
_KEYBUF = 0xFBF0
_GETPNT = 0xF3FA
_PUTPNT = 0xF3F8
_KEYBUF_SZ = 40


def build_tcl(out_path, lines, cf3300):
    for ln in lines:
        if len(ln) + 1 > _KEYBUF_SZ:            # +1 for the trailing CR
            raise ValueError(f"REPL line too long for KEYBUF ({len(ln)+1}>{_KEYBUF_SZ}): {ln!r}")
    body = []
    t = 12 if cf3300 else 8
    step = 8 if cf3300 else 5      # emulated seconds per line: enough to consume +
                                   # execute (disk PUT/GET are slow) before the next
                                   # inject resets KEYBUF. CF-3300 is slower.
    if cf3300:
        body.append('after time 11 { __inj "" }')   # initial CR to reach the prompt
    for ln in lines:
        body.append(f'after time {t} {{ __inj {{{ln}}} }}')
        t += step
    va = "0x1800" if cf3300 else "0x0000"
    key = "scr1" if cf3300 else "scr0"
    sz = 768 if cf3300 else 960
    body.append(f'after time {t+5} {{ puts $__f "{key}=[__hex_v {va} {sz}]";'
                f' flush $__f; close $__f; exit }}')
    return ("set throttle off\n"
            f"set __f [open {{{out_path}}} w]\n"
            "proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h;"
            " return $h }\n"
            # __inj: write "<line>\r" into KEYBUF and point GETPNT/PUTPNT at it so
            # CHGET delivers it. Both cursors are reset each call — safe because the
            # per-line step guarantees the prior line was fully consumed (buffer empty).
            "proc __inj {s} {\n"
            "  append s \"\\r\"\n"
            "  set n [string length $s]\n"
            "  for {set i 0} {$i < $n} {incr i} {\n"
            f"    debug write memory [expr {{{_KEYBUF} + $i}}] [scan [string index $s $i] %c]\n"
            "  }\n"
            f"  debug write memory {_GETPNT} [expr {{{_KEYBUF} & 0xFF}}]\n"
            f"  debug write memory [expr {{{_GETPNT}+1}}] [expr {{({_KEYBUF} >> 8) & 0xFF}}]\n"
            f"  set p [expr {{{_KEYBUF} + $n}}]\n"
            f"  debug write memory {_PUTPNT} [expr {{$p & 0xFF}}]\n"
            f"  debug write memory [expr {{{_PUTPNT}+1}}] [expr {{($p >> 8) & 0xFF}}]\n"
            "}\n"
            + "\n".join(body) + "\n")


def run(machine, lines, out, cf3300=False, timeout=220.0):
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zgp_", delete=False).name
    shutil.copy(SRC_DSK, dsk)
    open(out + ".tcl", "w").write(build_tcl(out, lines, cf3300))
    if os.path.exists(out):
        os.unlink(out)
    proc = subprocess.Popen(
        [OMSX, "-machine", machine, "-diska", dsk,
         "-command", "set renderer none", "-script", out + ".tcl"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        os.unlink(dsk)
        sys.exit(f"TIMEOUT running {machine}")
    os.unlink(dsk)
    key = "scr1=" if cf3300 else "scr0="
    # Each output line is `<` + 11 chars + `>`; the echoed PRINT command has a
    # different interior length, so an exact-11 capture isolates the real outputs.
    text = ""
    for ln in open(out):
        if ln.startswith(key):
            d = bytes.fromhex(ln.strip().partition("=")[2])
            text = "".join(chr(c) if 32 <= c < 127 else " " for c in d)
    return re.findall(r"<(.{11})>", text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default=os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_BASIC_DISK"))
    ap.add_argument("--ref-machine", default="National_CF-3300")
    ap.add_argument("--no-ref", action="store_true")
    args = ap.parse_args()
    rc = 0

    got = run(args.machine, PROGRAM, "/tmp/zgp.txt")
    print(f"--- zerobas GET/PUT round-trip ---\nrecords: {got}")
    okf = got == EXPECT
    print("functional:", "PASS" if okf else f"FAIL (expected {EXPECT})")
    rc = rc or (0 if okf else 1)

    if not args.no_ref:
        ref = run(args.ref_machine, PROGRAM, "/tmp/zgp_ref.txt", cf3300=True)
        print(f"\n--- CF-3300 differential ---\nrecords: {ref}")
        okr = ref == got == EXPECT
        print("differential:", "PASS — identical to zerobas" if okr
              else "FAIL — CF-3300 differs")
        rc = rc or (0 if okr else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
