#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""KEY interrupt-trap acceptance — slice T3 (docs/spec-traps-t3-key.md §8).

Differential of `ON KEY GOSUB` / `KEY(n) ON|OFF|STOP` against the reference oracle
Philips VG-8020, alongside the relocated repack build
(C-BIOS_MSX1_EU_REPACK_DISK, overridable via $ZEROBAS_BASIC_MACHINE). Both carry
BASIC in ROM, so each case is `-machine <name>` only: one boot per case.

WHAT MAKES T3 DIFFERENT FROM THE T1/T2 GATES, and what the apparatus must do
about it:

  * KEY IS A DELIVERY TRAP, NOT AN EDGE TRAP. It fires once per BIOS key-delivery
    event -- the initial make AND every auto-repeat -- so a hold fires many times,
    not once. The repeat CONSTANTS belong to the host BIOS, and zerobas
    deliberately inherits C-BIOS's rather than replicating the VG-8020's (spec
    §4, D-T3-2). So hold-length cases assert the PROPERTY ("a hold repeats":
    cnt >= 2) on each machine independently and are NOT equality-differentials.
    Asserting an exact repeat count across two different BIOSes would be gating
    the wrong thing, and it would fail for a correct implementation.

  * DIVERSION IS THE OTHER HALF OF THE SEMANTICS (§1.2), and it needs a delivery
    COUNT to be observable. The oracle rounds got that with `KEY 1,"X"` -- a
    one-character expansion makes an INKEY$ drain count deliveries exactly. That
    is unavailable here: zerobas does not implement `KEY n,"str"` (screen.asm
    rejects it), and C-BIOS never initialises FNKSTR at all, so on the zerobas
    side an untrapped F1 would deliver NOTHING and the baseline would read 0 for
    a reason that has nothing to do with the trap. Both problems have one fix:
    the program POKEs the expansion straight into FNKSTR ($F87F, 16 B/slot). That
    is machine-agnostic -- the work area is identical on both -- and it is what
    the D-T3-7 oracle round already did.

  * THE BASELINE IS ITSELF AN ASSERTION (§8). An untrapped hold MUST deliver a
    non-zero character count. If it reads 0 the apparatus is broken and the run
    is void, not a pass. Two characterization rounds in this arc agreed on a
    wrong answer because their baseline could not produce a non-zero reading.

APPARATUS (§1.0, a hard requirement of this gate):
  * RAM SENTINELS, never screen text -- the REPL echoes every typed program line.
    $D000 = fire COUNT, $D001 = which handler, $D002 = trapped ERR, $D003 = DONE,
    $D004 = characters that reached INKEY$.
  * EVERY READING IS GATED ON `done`. The capture POLLS $D003 and fires the moment
    the program sets it; a program that errored out or is still running at the
    hard deadline is captured with done==0 and is a FAILURE, never a zero. This
    is the check whose absence voided rounds 1-2 and 5.
  * NO STRING BUILDING. The drain loop tests `INKEY$` inline; it never assigns or
    concatenates. `A$=A$+INKEY$` is what made 4000 iterations never reach the
    sentinel POKE.
  * WINDOWS ARE BOUNDED BY ITERATION COUNT, NEVER BY `TIME`. `TIME` is NOT
    IMPLEMENTED in zerobas (it is absent from basic/kwtable.inc, so it parses as
    the variable `TI` and reads 0 forever) -- a `TIME`-bounded loop there never
    terminates. Run with --calibrate to re-measure the two loop rates; they differ
    by ~7x, which is why the capture polls instead of waiting a fixed time.

FUNCTION KEYS come from the matrix directly: row 6 bit 0 = SHIFT, bits 5/6/7 =
F1/F2/F3; row 7 bits 0/1 = F4/F5. F6-F10 are SHIFT + F1-F5.

Clean-room: observed I/O only.
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))          # siblings
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared

import argparse
import os
import shutil
import signal
import subprocess
import tempfile
import time

from omsx_repl import KEYBUF, GETPNT, PUTPNT, MAX_DIRECT  # noqa: E402

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
if not (os.path.sep in OMSX and os.path.isfile(OMSX)):
    OMSX = "openmsx"

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

CNT, WHO, ERRC, DONE, AUX = 0xD000, 0xD001, 0xD002, 0xD003, 0xD004

# --- the key matrix (published MSX work-area layout) ------------------------
FKEY = {1: (6, 0x20), 2: (6, 0x40), 3: (6, 0x80), 4: (7, 0x01), 5: (7, 0x02)}
SHIFT_ROW, SHIFT_BIT = 6, 0x01


def kdown(n):
    r, b = FKEY[n]
    return f"keymatrixdown {r} {hex(b)}"


def kup(n):
    r, b = FKEY[n]
    return f"keymatrixup {r} {hex(b)}"


def sdown():
    return f"keymatrixdown {SHIFT_ROW} {hex(SHIFT_BIT)}"


def sup():
    return f"keymatrixup {SHIFT_ROW} {hex(SHIFT_BIT)}"


def tap(n, at=1.0, dur=0.15):
    return [(at, kdown(n)), (at + dur, kup(n))]


def hold(n, at=1.0, dur=1.5):
    return [(at, kdown(n)), (at + dur, kup(n))]


def shift_tap(n, at=1.0, dur=0.15):
    """SHIFT down first, released last -- F6..F10 are SHIFT + F1..F5."""
    return [(at - 0.2, sdown()), (at, kdown(n)),
            (at + dur, kup(n)), (at + dur + 0.2, sup())]


def run(machine, prog, events, *, boot=8.0, step=4.0, poll_from=2.0,
        deadline=900.0, timeout=900, screen=False):
    """Boot `machine`, type `prog` + RUN, fire `events` = [(seconds_after_RUN, tcl)],
    then capture the sentinels AS SOON AS $D003 (done) is set -- or at `deadline`
    emulated seconds regardless, which captures done==0 and fails the case. One
    boot per call = power-on fresh. Times are EMULATED seconds (throttle off)."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="keytrap_")
    os.close(out_fd)
    lines = [
        "set throttle off",
        f'proc __cap {{}} {{ set f [open {{{out_path}}} w];'
        f' puts $f "cnt=[debug read memory {CNT}] who=[debug read memory {WHO}]'
        f' err=[debug read memory {ERRC}] done=[debug read memory {DONE}]'
        f' aux=[debug read memory {AUX}] t=[expr {{int([machine_info time])}}]";'
        + (f' binary scan [debug read_block VRAM 0x0000 960] H* h;'
           f' puts $f "screen=$h";' if screen else '')
        + f' close $f; exit }}',
        # poll for `done` so the fast machine is not made to wait for the slow
        # one's window, and the slow one is never truncated (the rates differ ~7x)
        f'proc __poll {{}} {{ if {{[debug read memory {DONE}] != 0}} {{ __cap }}'
        f' else {{ after time 1 __poll }} }}',
        # KEYBUF injection (probes/lib/omsx_repl.py): write the bytes into the
        # 40-byte type-ahead buffer and point GETPNT/PUTPNT at them, so CHGET
        # delivers the line with no matrix scan and no typing schedule.
        "proc __key {s} {\n"
        "  set n [string length $s]\n"
        "  for {set i 0} {$i < $n} {incr i} {\n"
        f"    debug write memory [expr {{{KEYBUF} + $i}}] "
        "[scan [string index $s $i] %c]\n"
        "  }\n"
        f"  debug write memory {GETPNT} [expr {{{KEYBUF} & 0xFF}}]\n"
        f"  debug write memory [expr {{{GETPNT}+1}}] [expr {{({KEYBUF} >> 8) & 0xFF}}]\n"
        f"  set p [expr {{{KEYBUF} + $n}}]\n"
        f"  debug write memory {PUTPNT} [expr {{$p & 0xFF}}]\n"
        f"  debug write memory [expr {{{PUTPNT}+1}}] [expr {{($p >> 8) & 0xFF}}]\n"
        "}",
        "proc __inj {s} { append s \"\\r\"; __key $s }",
    ]
    # PROGRAM ENTRY GOES THROUGH KEYBUF INJECTION, NOT openMSX `type`.
    #
    # This gate was written on the T1/T2 gates' matrix-typing schedule and that
    # schedule is not trustworthy at this program size. Both of its flake modes
    # showed up here, and both are INVISIBLE in the sentinels -- a mangled line
    # means the program never runs, the sentinels read power-on garbage, and the
    # case looks like a semantic failure:
    #   * a swallowed Enter concatenated two lines into
    #     `5 POKE&HD000,0:POKE&HD001,06 POKE&HD002,0:...` -> `Syntax error in 5`;
    #   * overlapping type streams dropped every second character, so
    #     `60 FORI=1TO6000:NEXT` arrived as `6 OI1O0NX`;
    #   * and after widening the schedule, a DOUBLED keystroke turned the error
    #     handler `900 ...` into `9900 ...` -> `undefined line in 1`.
    # Widening the gaps traded one direction of flake for the other, which is the
    # signal that timing is the wrong knob. probes/lib/omsx_repl.py exists exactly
    # for this (docs/spec-acceptance-harness-rework.md): the line lands atomically
    # via `debug write` into the BIOS type-ahead buffer, CHGET delivers it, and the
    # ROM tokenises it exactly as if typed -- with no per-character schedule to
    # race. Lines longer than the 40-byte buffer are chunked with the submitting CR
    # only on the last piece.
    #
    # The FUNCTION-KEY PRESSES still go through the real matrix (keymatrixdown):
    # the trap's event source is the BIOS keyboard scan, so injecting those would
    # bypass the very mechanism under test.
    t = boot
    for text in list(prog) + ["RUN"]:
        if len(text) <= MAX_DIRECT:
            lines.append(f'after time {t:g} {{ __inj {{{text}}} }}')
            t += step
            continue
        chunks = [text[i:i + MAX_DIRECT] for i in range(0, len(text), MAX_DIRECT)]
        for k, c in enumerate(chunks):
            proc = "__inj" if k == len(chunks) - 1 else "__key"   # CR only on last
            lines.append(f'after time {t:g} {{ {proc} {{{c}}} }}')
            t += step
    run_done = t
    last = run_done
    for dt, tcl in events:
        lines.append(f'after time {run_done + dt:g} {{ {tcl} }}')
        last = max(last, run_done + dt)
    lines.append(f"after time {last + poll_from:g} {{ __poll }}")
    lines.append(f"after time {run_done + deadline:g} {{ __cap }}")

    fd, tcl_path = tempfile.mkstemp(suffix=".tcl", prefix="keytrap_")
    os.write(fd, ("\n".join(lines) + "\n").encode())
    os.close(fd)
    cmd = [OMSX, "-machine", machine, "-command", "set renderer none", "-script", tcl_path]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        dl = time.time() + timeout
        while proc.poll() is None and time.time() < dl:
            time.sleep(0.1)
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    finally:
        os.unlink(tcl_path)
    res = None
    if os.path.exists(out_path):
        txt = open(out_path).read().strip()
        os.unlink(out_path)
        if txt:
            res = {}
            for kv in txt.split():
                k, _, v = kv.partition("=")
                res[k] = v if k == "screen" else int(v)
    return res


def show_screen(res):
    """Render the SCREEN 0 name table ($0000, 40x24) captured with screen=True.
    Reading the SCREEN is how three separate apparatus bugs in this gate were
    found -- a mangled program line is invisible in the sentinels, which simply
    read power-on garbage and look like a semantic failure."""
    if not res or "screen" not in res:
        print("  (no screen captured)")
        return
    b = bytes.fromhex(res["screen"])
    for r in range(24):
        row = b[r * 40:(r + 1) * 40]
        line = "".join(chr(c) if 32 <= c < 127 else ("." if c else " ") for c in row)
        if line.strip():
            print(f"  {r:2d}|{line}")


# --- program fragments ------------------------------------------------------
# SPLIT ACROSS TWO LINES ON PURPOSE. A single 66-char clear line was silently
# truncated on the zerobas side (long typed lines drop keystrokes under
# `throttle off` -- the standing harness rule, recorded in the T2 gate), so the
# program never ran and every sentinel read power-on garbage. Both halves are
# under 40 chars, the length the T1/T2 gates have always typed reliably.
CLR = ["5 POKE&HD000,0:POKE&HD001,0", "6 POKE&HD002,0:POKE&HD003,0:POKE&HD004,0"]
ONERR = "1 ONERRORGOTO900"
ERRH = "900 POKE&HD002,ERR:POKE&HD003,1:END"
# FNKSTR seeding: slot k lives at $F87F + 16k, NUL-terminated. Slot 0 (F1) and
# slot 1 (F2) get a one-character expansion so an INKEY$ drain counts DELIVERIES
# exactly -- the machine-agnostic stand-in for the oracle's `KEY 1,"X"`, which
# zerobas does not implement and which C-BIOS would not have initialised anyway.
SEED1 = "2 POKE&HF87F,88:POKE&HF880,0"                      # F1 -> "X"
SEED2 = "3 POKE&HF88F,89:POKE&HF890,0"                      # F2 -> "Y"
# handlers COUNT their fires (a delivery trap only shows its nature in the count)
H1 = "100 POKE&HD000,PEEK(&HD000)+1:POKE&HD001,1:RETURN"
H2 = "200 POKE&HD000,PEEK(&HD000)+1:POKE&HD001,2:RETURN"
H3 = "300 POKE&HD000,PEEK(&HD000)+1:POKE&HD001,3:RETURN"
H6 = "600 POKE&HD000,PEEK(&HD000)+1:POKE&HD001,6:RETURN"

# Observation windows. Bounded by ITERATION COUNT (never TIME -- it does not
# exist on zerobas). Sized from --calibrate so the REFERENCE, the faster of the
# two by ~7x, is still inside the window when the last event lands; the poll
# then captures each machine the moment IT finishes.
WIN = "60 FORI=1TO20000:NEXT"
END = "70 POKE&HD003,1:END"
# the drain: counts characters reaching INKEY$ WITHOUT building a string
DRAIN = "60 FORI=1TO9000:IFINKEY$<>\"\"THENPOKE&HD004,PEEK(&HD004)+1"
DRAIN2 = "65 NEXT"

CALIB = [
    ("cal_window", [*CLR, WIN, END], [], {"done": 1}),
    ("cal_drain", [*CLR, SEED1, DRAIN, DRAIN2, END], [], {"done": 1}),
]

# --- firing: the delivery event (§1.1) --------------------------------------
# label, program, events, expected {sentinel: value}[, equality-differential?]
FIRING = [
    ("A_fires", [*CLR, "10 ON KEY GOSUB 100", "30 KEY(1) ON", WIN, END, H1],
     tap(1), {"cnt": 1, "who": 1, "done": 1}),

    ("B_two_taps", [*CLR, "10 ON KEY GOSUB 100", "30 KEY(1) ON", WIN, END, H1],
     tap(1, 1.0) + tap(1, 3.0), {"cnt": 2, "who": 1, "done": 1}),

    ("C_no_enable", [*CLR, "10 ON KEY GOSUB 100", WIN, END, H1],
     tap(1), {"cnt": 0, "done": 1}),

    ("D_off", [*CLR, "10 ON KEY GOSUB 100", "30 KEY(1) OFF", WIN, END, H1],
     tap(1), {"cnt": 0, "done": 1}),

    # STOP == OFF for KEY: it neither eats the key nor latches it (§1.2 T4, D-T3-6)
    ("E_stop", [*CLR, "10 ON KEY GOSUB 100", "30 KEY(1) STOP", WIN, END, H1],
     tap(1), {"cnt": 0, "done": 1}),

    # the list is positional: slot 1 is KEY 2 (§1.4 K8)
    ("F_positional", [*CLR, "10 ON KEY GOSUB 100,200", "30 KEY(2) ON", WIN, END, H1, H2],
     tap(2), {"cnt": 1, "who": 2, "done": 1}),

    # an EMPTY slot clears that key's handler; the key is still SWALLOWED (§1.2 T5)
    ("G_empty_slot_clears",
     [*CLR, "10 ON KEY GOSUB 100", "12 ON KEY GOSUB", "30 KEY(1) ON", WIN, END, H1],
     tap(1), {"cnt": 0, "done": 1}),

    # SHIFT is discriminated: SHIFT+F1 is KEY 6, not KEY 1 (§1.3 K7)
    ("H_shift_is_key6",
     [*CLR, "10 ON KEY GOSUB 100,,,,,600", "30 KEY(6) ON", WIN, END, H1, H6],
     shift_tap(1), {"cnt": 1, "who": 6, "done": 1}),

    # ...and from the other side: with only KEY(1) ON, SHIFT+F1 never fires (R11)
    ("I_shift_not_key1",
     [*CLR, "10 ON KEY GOSUB 100", "30 KEY(1) ON", WIN, END, H1],
     shift_tap(1), {"cnt": 0, "done": 1}),

    # a press during SERVICING is diverted and LATCHED, firing once after RETURN
    # (§1.3 W1). The handler records entry (1) and exit (2) in `who` so "was it
    # still running?" is OBSERVED -- round 5 assumed it and was void.
    ("J_press_in_handler",
     [*CLR, "10 ON KEY GOSUB 100", "30 KEY(1) ON", WIN, END,
      "100 POKE&HD000,PEEK(&HD000)+1",
      "102 POKE&HD001,1",
      "104 IFPEEK(&HD000)=1THENFORJ=1TO1500:NEXT",
      "106 POKE&HD001,2:RETURN"],
     tap(1, 1.0) + tap(1, 3.0), {"cnt": 2, "who": 2, "done": 1}),

    # the DISPLAY form still parses and still works alongside the trap form (K10)
    ("K_key_off_display",
     [*CLR, "8 KEY OFF", "10 ON KEY GOSUB 100", "30 KEY(1) ON", WIN, END, H1],
     tap(1), {"cnt": 1, "who": 1, "done": 1}),

    # AN EMPTY SLOT MUST NOT END THE LIST: slot 2's target has to survive the
    # omitted slot 1 and still be crunched as a line REFERENCE. This is the
    # narrowest form of the tokeniser bug the K7 case below first exposed
    # (basic/tokenise.inc bl_num) -- without the fix, `600` came through as an
    # ordinary numeric literal and the statement died with `syntax error in 10`.
    ("AA_empty_slot_midlist",
     [*CLR, "10 ON KEY GOSUB 100,,600", "30 KEY(3) ON", WIN, END, H1, H6],
     tap(3), {"cnt": 1, "who": 6, "done": 1}),

    ("L_key4", [*CLR, "10 ON KEY GOSUB 100,100,100,300", "30 KEY(4) ON",
                WIN, END, H1, H3],
     tap(4), {"cnt": 1, "who": 3, "done": 1}),
]

# --- the repeat property (§1.1) --------------------------------------------
# NOT an equality differential: the repeat constants are the HOST BIOS's, and
# zerobas inherits C-BIOS's by design rather than replicating the VG-8020's.
# What is gated is the PROPERTY -- a delivery trap repeats, an edge trap cannot.
REPEAT = [
    ("M_hold_repeats", [*CLR, "10 ON KEY GOSUB 100", "30 KEY(1) ON", WIN, END, H1],
     hold(1, 1.0, 2.0), {"who": 1, "done": 1}, "cnt>=2"),
]

# --- diversion: a trapped key leaves the input stream (§1.2) ----------------
# Every case here holds F1 with a seeded one-character expansion, so `aux` is a
# DELIVERY COUNT. The untrapped rows are the apparatus check: if they read 0 the
# run is VOID, not a pass.
DIVERSION = [
    # T1: no trap at all -> the baseline. MUST be non-zero on both machines.
    ("N_baseline_delivers", [*CLR, SEED1, DRAIN, DRAIN2, END],
     hold(1, 1.0, 2.0), {"done": 1}, "aux>0"),

    # T2: trapped -> fires, and NOTHING reaches the input stream
    ("O_trapped_diverted",
     [*CLR, SEED1, "10 ON KEY GOSUB 100", "30 KEY(1) ON", DRAIN, DRAIN2, END, H1],
     hold(1, 1.0, 2.0), {"aux": 0, "done": 1}, "cnt>=1"),

    # T5: ON with an EMPTY handler slot still swallows -- diversion follows the
    # STATE ALONE. The easy-to-miss one.
    ("P_on_empty_swallows",
     [*CLR, SEED1, "10 ON KEY GOSUB", "30 KEY(1) ON", DRAIN, DRAIN2, END],
     hold(1, 1.0, 2.0), {"cnt": 0, "aux": 0, "done": 1}),

    # T3/T4: OFF and STOP both DELIVER normally
    ("Q_off_delivers",
     [*CLR, SEED1, "10 ON KEY GOSUB 100", "30 KEY(1) OFF", DRAIN, DRAIN2, END, H1],
     hold(1, 1.0, 2.0), {"cnt": 0, "done": 1}, "aux>0"),

    ("R_stop_delivers",
     [*CLR, SEED1, "10 ON KEY GOSUB 100", "30 KEY(1) STOP", DRAIN, DRAIN2, END, H1],
     hold(1, 1.0, 2.0), {"cnt": 0, "done": 1}, "aux>0"),

    # T6: an UNTRAPPED key is unaffected while another key is trapped
    ("S_untrapped_key_unaffected",
     [*CLR, SEED2, "10 ON KEY GOSUB 100", "30 KEY(1) ON", DRAIN, DRAIN2, END, H1],
     hold(2, 1.0, 2.0), {"cnt": 0, "done": 1}, "aux>0"),
]

# --- parse / error surface (§1.4) -- no press needed ------------------------
PARSE = [
    ("T_key0_err5", [*CLR, ONERR, "10 ON KEY GOSUB 100", "30 KEY(0) ON",
                     "40 POKE&HD003,1:END", H1, ERRH], [], {"err": 5, "done": 1}),
    ("U_key11_err5", [*CLR, ONERR, "10 ON KEY GOSUB 100", "30 KEY(11) ON",
                      "40 POKE&HD003,1:END", H1, ERRH], [], {"err": 5, "done": 1}),
    ("V_ten_slots_ok",
     [*CLR, ONERR, "10 ON KEY GOSUB 100,100,100,100,100,100,100,100,100,100",
      "30 KEY(10) ON", "40 POKE&HD003,1:END", H1, ERRH], [], {"err": 0, "done": 1}),
    ("W_eleven_slots_err2",
     [*CLR, ONERR, "10 ON KEY GOSUB 100,100,100,100,100,100,100,100,100,100,100",
      "40 POKE&HD003,1:END", H1, ERRH], [], {"err": 2, "done": 1}),
    ("X_on_key_goto_err2", [*CLR, ONERR, "10 ON KEY GOTO 100",
                            "40 POKE&HD003,1:END", H1, ERRH], [], {"err": 2, "done": 1}),
    ("Y_undef_line_err8", [*CLR, ONERR, "10 ON KEY GOSUB 999",
                           "40 POKE&HD003,1:END", ERRH], [], {"err": 8, "done": 1}),
    ("Z_bare_key_paren_err2", [*CLR, ONERR, "10 ON KEY GOSUB 100", "30 KEY(1)",
                               "40 POKE&HD003,1:END", H1, ERRH], [], {"err": 2, "done": 1}),
]

GROUPS = [("firing: the delivery event", FIRING),
          ("the REPEAT property (per-machine, NOT an equality differential)", REPEAT),
          ("diversion: a trapped key leaves the input stream", DIVERSION),
          ("parse / error surface", PARSE)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE, help="reference oracle machine")
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE)
    ap.add_argument("--only", help="run only cases whose label contains this substring")
    ap.add_argument("--ref-only", action="store_true", help="oracle-lock only")
    ap.add_argument("--zb-only", action="store_true", help="zerobas side only")
    ap.add_argument("--screen", action="store_true",
                    help="dump the SCREEN 0 name table for each case -- the only "
                         "way to tell a mangled typed line from a semantic failure")
    ap.add_argument("--calibrate", action="store_true",
                    help="measure the two loop rates and exit (spec §1.0: "
                         "calibrate, do not assume)")
    args = ap.parse_args()
    ok = True

    def brief(r):
        """the sentinels only -- the raw screen hex is for --screen, not the log"""
        return None if r is None else {k: v for k, v in r.items() if k != "screen"}

    def check(label, cond, detail=""):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL':5} {label}" + (f"  {detail}" if detail else ""))
        ok = ok and cond

    def matches(got, want, prop=None):
        if got is None:
            return False
        # EVERY reading is gated on `done` -- a program that did not finish is a
        # FAILURE, never a zero (spec §1.0/§8).
        if got.get("done") != 1:
            return False
        if not all(got.get(k) == v for k, v in want.items()):
            return False
        if prop:
            key, _, rhs = prop.partition(">=")
            if rhs:
                return got.get(key.strip(), 0) >= int(rhs)
            key, _, rhs = prop.partition(">")
            return got.get(key.strip(), 0) > int(rhs)
        return True

    if args.calibrate:
        print("--- calibration: emulated seconds to complete each window loop ---")
        for label, prog, events, want in CALIB:
            for tag, m in (("ref", args.machine), ("zb ", args.zb_machine)):
                r = run(m, prog, events)
                print(f"  [{tag}] {label:12} {r}")
        print("\nRead `t` = emulated seconds at capture (includes ~8 s boot + the\n"
              "typing schedule). The window must outlast the last event on the\n"
              "FASTER machine; the poll handles the slower one.")
        return 0

    for group, cases in GROUPS:
        print(f"\n--- {group} ---")
        equality = "REPEAT" not in group
        for label, prog, events, want, *rest in cases:
            if args.only and args.only not in label:
                continue
            prop = rest[0] if rest else None
            # the repeat group is per-machine by construction; so is any case
            # whose assertion is a bare property on a BIOS-timed count
            eq = equality and label not in ("N_baseline_delivers",
                                            "O_trapped_diverted",
                                            "Q_off_delivers", "R_stop_delivers",
                                            "S_untrapped_key_unaffected")
            ref = None
            if not args.zb_only:
                ref = run(args.machine, prog, events, screen=args.screen)
                if args.screen:
                    print(f"[ref] {label}"); show_screen(ref)
                check(f"[ref] {label:26} {brief(ref)} want {want}"
                      + (f" {prop}" if prop else ""), matches(ref, want, prop))
            if args.ref_only:
                continue
            zb = run(args.zb_machine, prog, events, screen=args.screen)
            if args.screen:
                print(f"[zb ] {label}"); show_screen(zb)
            good = matches(zb, want, prop)
            if eq and ref is not None:
                good = good and all(zb.get(k) == ref.get(k)
                                    for k in ("cnt", "who", "err", "aux"))
            check(f"[zb ] {label:26} {brief(zb)} want {want}"
                  + (f" {prop}" if prop else "")
                  + (f", == ref" if eq and ref is not None else " (per-machine)"),
                  good)

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
