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
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402
import omsx_repl  # noqa: E402  (the ONE injector -- see build_tcl)

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
# no matrix scan is involved, so nothing can double.
#
# 🔴 THE INJECTOR ITSELF COMES FROM `omsx_repl.key_proc()` AND IS NOT COMPOSED HERE
# (D-LASTINJ, docs/spec-probe-lastinj.md §3.3). This file used to carry its own copy
# of the pre-D-LATCH body — write the payload at KEYBUF, set GETPNT := KEYBUF — which
# is the delivery race D-LATCH characterised: an `after time` callback landing on the
# ONE instruction boundary at C-BIOS `chget`'s `ld de,(PUTPNT)` leaves HL holding the
# PRE-injection GETPNT, so `ld a,(hl)` starts reading at KEYBUF + len(previous line).
# The copy here was byte-equivalent to the frozen body `make latch-check` row A forces
# and requires to MANGLE, so this file shipped the fault after the shared injector had
# been fixed. It was measured latent rather than harmless: 0 of 16 slots landed on the
# trigger, but the swallow law's PRECONDITION (GETPNT left at KEYBUF + len(predecessor)
# by the drained previous line) held at 15/15 slots that have a predecessor, and slot 11
# landed at $119B — inside `chget`'s wait loop, one boundary off the fatal one
# (docs/lastinj-characterization.md §4). `key_proc` writes at the CURRENT GETPNT and
# never moves it, which is immune by construction rather than by alignment.
#
# The addresses live in `omsx_repl` too, so this file no longer carries a second copy
# of the memory map. Uses only the PUBLISHED MSX BIOS contract (MSX2 Technical Handbook
# system-variable map) — no ROM disassembly: KEYBUF $FBF0 (40-byte circular type-ahead
# buffer), GETPNT $F3FA / PUTPNT $F3F8 (the read / write cursors CHSNS+CHGET consult;
# empty when GETPNT==PUTPNT). Verified black-box that C-BIOS honours it (a real MSX1
# like the CF-3300 does by construction — this is where the standard comes from).


def build_tcl(out_path, lines, cf3300):
    for ln in lines:
        if len(ln) + 1 > omsx_repl.KEYBUF_SZ:   # +1 for the trailing CR
            raise ValueError(f"REPL line too long for KEYBUF "
                             f"({len(ln)+1}>{omsx_repl.KEYBUF_SZ}): {ln!r}")
    body = []
    t = 12 if cf3300 else 8
    step = 8 if cf3300 else 5      # emulated seconds per line: enough to consume +
                                   # execute (disk PUT/GET are slow) before the next
                                   # inject overwrites the buffer. CF-3300 is slower.
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
            # __key: the ONE injector, imported rather than copied, so what runs
            # here cannot drift from what `make latch-check` scores.
            + omsx_repl.key_proc()
            # __inj: __key plus the submitting CR (appended here so a literal CR
            # byte never has to survive Tcl brace-quoting) — the same two-proc
            # split omsx_repl itself emits.
            + "proc __inj {s} { append s \"\\r\"; __key $s }\n"
            + "\n".join(body) + "\n")


def run(machine, lines, out, cf3300=False, timeout=220.0):
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="zgp_", delete=False).name
    shutil.copy(SRC_DSK, dsk)
    open(out + ".tcl", "w").write(build_tcl(out, lines, cf3300))
    if os.path.exists(out):
        os.unlink(out)
    proc = subprocess.Popen(
        omsx_preflight.guarded([OMSX, "-machine", machine, "-diska", dsk,
         "-command", "set renderer none; set sound_driver null", "-script", out + ".tcl"]),
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
    ap.add_argument("--machine", default=os.environ.get("ZEROBAS_BASIC_MACHINE"))
    ap.add_argument("--ref-machine", default="National_CF-3300")
    ap.add_argument("--no-ref", action="store_true")
    args = ap.parse_args()
    if not args.machine:
        sys.exit("no zerobas machine: pass --machine or set $ZEROBAS_BASIC_MACHINE; there is no default,\n"
                 "one would silently pick the BUILD under test "
                 "(docs/spec-lean-retire-s1-explicit-machine.md).")
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
