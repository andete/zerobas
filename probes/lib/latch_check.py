#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""latch_check -- force the delivery race onto its own trigger and score it.

D-LATCH (docs/spec-probe-latch.md). The batched-injection race D-DELIVER and
D-ECHO characterised has a trigger exactly one instruction wide: the openMSX
`after time` callback that performs an injection must land on the boundary
between C-BIOS `chget`'s

    chget_wait:  ld hl,(GETPNT)      <-- HL latched here
                 ld de,(PUTPNT)      <-- the callback must land HERE
                 rst $20             (DCOMPR)
                 jr nz,chget_char
                 ei / halt / jr chget_wait

An injector that moves GETPNT BACKWARDS (write at KEYBUF, GETPNT := KEYBUF) is
then invisible to the CPU: HL still holds the pre-injection GETPNT, which the
drained predecessor left at KEYBUF + len(that line incl. CR), so `ld a,(hl)`
starts reading the fresh buffer from offset N. That is the swallow law, exactly.

WHY THIS GATE EXISTS AT ALL. `omsx_repl.key_proc` now writes at the current
GETPNT and never moves it, so the race no longer occurs -- which means the two
delivery oracles lose the only live subject they ever had. D-ECHO §3.5 was
explicit that cross-oracle disagreement was their only positive control, and it
fires exactly when the race does. Removing the fault without replacing that
control is how a guard goes green while measuring nothing
([[gate-can-be-green-while-measuring-nothing]]).

So this gate does not wait for the race: it FORCES it, with a CPU breakpoint at
the trigger address, and scores both injectors on the same boundary:

    row A  the OLD injector, forced -> must MANGLE     (the positive control)
    row B  omsx_repl.key_proc, forced -> must DELIVER  (the fix)
    row C  omsx_repl.key_proc on the three SAFE boundaries -> must DELIVER

Row A is what stops this gate from passing vacuously: if the experiment ever
stops reproducing -- a different C-BIOS, a different openMSX scheduling model --
row A goes green and the gate FAILS, rather than quietly certifying nothing
([[coverage-gate-cannot-see-a-gutted-guard]]).

Row B imports the injector from `omsx_repl` rather than copying it, so the thing
under test cannot drift from the thing shipped. Row A's body is frozen here on
purpose: it is a historical artefact, not a maintained code path.

⚠️ SUBJECT-ONLY. The addresses are derived from the published `CHGET $009F`
jump-table entry and checked against C-BIOS's own source byte signature (C-BIOS
is BSD-2 source this repo already carries patches against). The reference
machine is NOT driven here: locating the same boundary in it would need a
disassembly this project does not do [[no-reference-rom-disasm]]. Its role in
D-LATCH is the zero-RED outcome control it has always been -- it mis-delivers
nothing, with either injector.

⚠️ IT CANNOT JUDGE WHAT IT CANNOT IDENTIFY. If `$009F` is not a `jp`, or the
seven bytes at `chget_wait` are not `2A FA F3 ED 5B F8 F3`, this exits NON-ZERO
saying so. A guard that cannot judge must say so, not pass
([[guard-that-cannot-judge-must-say-so]]).
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from omsx_run import find_omsx                       # noqa: E402
import omsx_preflight                                # noqa: E402
import omsx_repl as R                                # noqa: E402

MACHINE = "C-BIOS_MSX1_EU_REPACK_DISK"
CHGET_ENTRY = 0x009F                 # published MSX BIOS jump table
# chget = call H_CHGE (3) + push hl (1) + push de (1) -> chget_wait
WAIT_OFF = 5
# ld hl,(GETPNT) = 2A FA F3 ; ld de,(PUTPNT) = ED 5B F8 F3
SIG = "2afaf3ed5bf8f3"
TARGET = '10 PRINT"ABCDEFG"'         # stored line 10; a mangle rejects it outright

# The pre-D-LATCH injector, FROZEN. Not imported, not maintained: it is the
# fault, kept only so the gate has a subject that must still fail.
OLD_KEY = """proc __key {s} {
  set n [string length $s]
  for {set i 0} {$i < $n} {incr i} {
    debug write memory [expr {%(KB)d + $i}] [scan [string index $s $i] %%c] }
  debug write memory %(GP)d [expr {%(KB)d & 0xFF}]
  debug write memory %(GP1)d [expr {(%(KB)d >> 8) & 0xFF}]
  set p [expr {%(KB)d + $n}]
  debug write memory %(PP)d [expr {$p & 0xFF}]
  debug write memory %(PP1)d [expr {($p >> 8) & 0xFF}]
}
""" % dict(KB=R.KEYBUF, GP=R.GETPNT, GP1=R.GETPNT + 1,
           PP=R.PUTPNT, PP1=R.PUTPNT + 1)

_PROBE = """set throttle off
set f [open {%(OUT)s} w]
%(KEY)s
proc __inj {s} { append s "\\r"; __key $s }
proc __lines {p} {
  set cur [expr {[debug read memory $p] + 256*[debug read memory [expr {$p+1}]]}]
  set out {}
  for {set i 0} {$i < 128} {incr i} {
    set link [expr {[debug read memory $cur] + 256*[debug read memory [expr {$cur+1}]]}]
    if {$link == 0} { break }
    lappend out [expr {[debug read memory [expr {$cur+2}]] + 256*[debug read memory [expr {$cur+3}]]}]
    if {$link <= $cur} { break }
    set cur $link }
  return [join $out ,] }
proc fire {} {
  global f bpid
  puts $f "hl=[format %%04X [reg hl]]"
  __inj {%(TARGET)s}
  debug remove_bp $bpid }
after time  8.0 {
  set e [debug read memory %(ENTRY)d]
  set b [expr {[debug read memory %(ENTRY1)d] + 256*[debug read memory %(ENTRY2)d]}]
  binary scan [debug read_block memory [expr {$b + %(WAIT)d}] 7] H* sig
  puts $f "entry=$e"
  puts $f "chget=$b"
  puts $f "sig=$sig"
  flush $f
  __inj {NEW} }
after time 10.0 { __inj {%(PRED)s} }
%(ARM)s
after time 15.0 {
  puts $f "chain=[__lines %(TXTTAB)d]"
  flush $f; close $f; exit }
"""


def _run(key_body: str, addr: str | None, pred: str) -> dict:
    """One boot. `addr` None = no breakpoint armed at all -- the locate-only run,
    which must not inject a stray target line just to read three sysvars."""
    out = tempfile.NamedTemporaryFile(suffix=".txt", prefix="latch_",
                                      delete=False).name
    tcl = out + ".tcl"
    arm = ("" if addr is None else
           f"after time 12.0 {{ global bpid; "
           f"set bpid [debug set_bp {addr} {{}} {{ fire }}] }}")
    with open(tcl, "w") as f:
        f.write(_PROBE % dict(OUT=out, KEY=key_body, TARGET=TARGET, PRED=pred,
                              ARM=arm, ENTRY=CHGET_ENTRY,
                              ENTRY1=CHGET_ENTRY + 1, ENTRY2=CHGET_ENTRY + 2,
                              WAIT=WAIT_OFF, TXTTAB=R.TXTTAB))
    if os.path.exists(out):
        os.unlink(out)
    cmd = [find_omsx(None), "-machine", MACHINE,
           "-command", "set renderer none; set sound_driver null",
           "-script", tcl]
    subprocess.run(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=180)
    got: dict = {}
    if os.path.exists(out):
        for ln in open(out):
            k, _, v = ln.strip().partition("=")
            got[k] = v
        os.unlink(out)
    os.unlink(tcl)
    return got


def address() -> tuple[int, str]:
    """Locate `chget_wait` and vouch for it, or raise SystemExit."""
    got = _run(R.key_proc(), None, "CLS")         # locate only: no breakpoint
    if not got:
        raise SystemExit("latch-check: CANNOT JUDGE -- no output from openMSX "
                         f"(machine {MACHINE} missing? run `make repack-machine`)")
    if got.get("entry") != "195":                 # $C3 = jp
        raise SystemExit(f"latch-check: CANNOT JUDGE -- {CHGET_ENTRY:#06x} holds "
                         f"opcode {got.get('entry')}, not a `jp`")
    wait = int(got["chget"]) + WAIT_OFF
    if got.get("sig") != SIG:
        raise SystemExit(
            f"latch-check: CANNOT JUDGE -- chget_wait ({wait:#06x}) reads "
            f"{got.get('sig')!r}, not the {SIG!r} this gate was written against "
            "(ld hl,(GETPNT) / ld de,(PUTPNT)). The trigger this scores may have "
            "moved; re-derive it before trusting either delivery oracle.")
    return wait, got["chget"]


def main() -> int:
    wait, base = address()
    fatal, safe = wait + 3, [wait, wait + 7, wait + 12]
    print(f"latch-check: chget ${int(base):04X}  chget_wait ${wait:04X}  "
          f"trigger ${fatal:04X}")
    rows: list[tuple[str, bool]] = []

    # Row A -- the positive control. The frozen pre-D-LATCH injector, forced
    # onto the trigger, must still lose the head of the line.
    for pred, swallow in [("CLS", 4), ("CLS:CLS", 8), ("CLS:REM123456", 14)]:
        got = _run(OLD_KEY, hex(fatal), pred)
        bad = got.get("chain") == "10"
        want = R.KEYBUF + swallow
        rows.append((f"A  old injector, forced, predecessor {swallow:2d} B  "
                     f"-> MANGLED (HL ${want:04X})", not bad
                     and got.get("hl") == f"{want:04X}"))

    # Row B -- the fix, same boundary, same predecessors.
    for pred, swallow in [("CLS", 4), ("CLS:CLS", 8), ("CLS:REM123456", 14)]:
        got = _run(R.key_proc(), hex(fatal), pred)
        rows.append((f"B  key_proc,     forced, predecessor {swallow:2d} B  "
                     f"-> DELIVERED", got.get("chain") == "10"))

    # Row C -- the fix on the neighbouring boundaries, which were never fatal.
    for addr, what in zip(safe, ["ld hl,(GETPNT)", "rst $20", "jr chget_wait"]):
        got = _run(R.key_proc(), hex(addr), "CLS:REM123456")
        rows.append((f"C  key_proc,     forced at ${addr:04X} ({what})"
                     f"{'':<3}-> DELIVERED", got.get("chain") == "10"))

    for label, ok in rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    bad = sum(1 for _, ok in rows if not ok)
    print(f"latch-check: {len(rows) - bad}/{len(rows)} rows")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
