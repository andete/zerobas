#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Error-MESSAGE TEXT characterization -- the exact wording, on both references.

WHY THIS PROBE EXISTS
=====================
Until 2026-08-02 this tree had a POLICY of not comparing message text to the
reference. probes/basic/error_acceptance.py states it outright:

    "Wording stays house-style (we don't copy MSX's verbatim text -- so we DON'T
     compare the message string to the reference)"

So the corpus was STRUCTURALLY BLIND to message wording: every error class it
covers agrees NUMERICALLY (`PRINT ERR`) and the text was never an observable.
The policy has been reversed -- zerobas now wants the EXACT reference message
for every error -- and that reversal needs a denominator before it needs an
implementation. This probe is that denominator.

⚠️ IT MEASURES THE REFERENCES, NOT ZEROBAS'S CORRECTNESS. Its job is to answer
"what exactly does an MSX1 print for error n", per machine, verbatim. The zb
side is captured too, but as the CURRENT-STATE column of a characterization
table, not as a pass/fail. The acceptance gate that asserts zb == ref is a
separate, later artifact (docs/spec-basic-msgexact.md) -- writing the gate and
the denominator in one file is how a readout ends up agreeing with itself.

THE INSTRUMENT: `ERROR n` IN DIRECT MODE
========================================
`ERROR n` raises code n through the same dispatcher every real site funnels
into, prints its message, and returns to the prompt. So a direct-mode walk over
n enumerates the WHOLE message table in one boot per machine -- no per-site
trigger to invent, and no trigger-specific behaviour to disentangle from the
wording. Codes are walked CONTIGUOUSLY (1..26), not sampled: the spec-level
question is "which codes exist and what do they say", and a gap in the walk is
exactly where a wrong answer hides ([[one-row-cannot-separate-two-rules]]).

26 is deliberate -- one PAST the documented last entry (25, `Line buffer
overflow`). It is the CONTROL that proves the walk can see the table's END:
if 26 reads the same as 25, the readout is not tracking the table at all.

THE DISK RANGE (50..64) IS A SECOND, SEPARATE WALK. The VG-8020 has no disk
ROM, so it is expected to answer `Unprintable error` across that whole span
while the CF-3300 answers with real disk wording. That DISAGREEMENT is the
point: it is what proves each machine is being read on its own terms rather
than one answer being echoed for both. A row where both refs agree in that
range would be the suspicious one.

⚠️ WHAT THIS PROBE CANNOT REACH, AND SAYS SO RATHER THAN GUESSING
=================================================================
Four messages are NOT `ERROR n`-reachable and are therefore NOT in this walk:

  `Break`             CTRL-STOP / the STOP statement, not an ERR code at all
  `?Redo from start`  INPUT re-prompt -- needs interactive data entry
  `?Extra ignored`    INPUT surplus -- same
  `Verify error`      cassette VERIFY -- needs a tape image

They are listed here so the denominator states its own hole instead of reading
as complete coverage. `STOP`/`INPUT` are cheap follow-ups (a stored program and
an injected data line); the tape one needs the CAS: harness. None of them is
guessed at from a published reference -- an unmeasured message stays UNMEASURED
in the output table, spelled `<not-measured>`.

READOUT
=======
`omsx_repl.screen_tail(raw, cmdline)` -- the rows between the echoed command and
the next prompt. That is the same readout D-LSTRNG introduced, and it is the
first in this tree to read an error MESSAGE rather than an error CODE.

⚠️ TWO DISTINCT EMPTY SENTINELS, ALWAYS ([[readout-blind-to-its-own-subject]]).
`None` = the echo row was never found, i.e. the machine never ran the case (a
wedge, a date prompt, a SCREEN-1 name table read through a SCREEN-0 scraper).
`""` = the case ran and printed NOTHING. Collapsing those two would report a
dead machine as "this code is silent", which is a fact about the emulator being
reported as a fact about MSX-BASIC. They print as `<none>` and `<empty>`.

SELF-CHECK: THE READOUT MUST BE ABLE TO DISAGREE
================================================
`--selfcheck` runs before the walk and fails the whole run if it does not hold.
Two codes with KNOWN-DIFFERENT wording (2 `Syntax error`, 11 `Division by zero`)
must read back DIFFERENT strings on the same machine. A readout that returns a
constant -- the screen scraper landing on the prompt row, say -- would otherwise
report perfect agreement across all 41 rows and look like a clean measurement.
This is the cheap version of "construct a case the machine definitely gets
wrong and check the readout returns something DIFFERENT from the correct case".
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))   # bas_tokenise
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402
from bas_tokenise import make_multiline_program  # noqa: E402
from cas_encode import build_cas_basic  # noqa: E402
from omsx_run import _tcl_dquote  # noqa: E402

OMSX = (os.environ.get("OPENMSX") or shutil.which("openmsx")
        or "/opt/homebrew/bin/openmsx")

ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SRC_DSK = os.path.join(REPO, "disk", "test720.dsk")

# side -> how to drive it. Mirrors basic_probe_lnblank.py's SIDES verbatim: the
# CF-3300's leading "" is its BOOT DATE PROMPT (a bare CR accepts the default;
# at the BASIC prompt every later one is a no-op), and its 4.5 s cadence is
# measured, not guessed -- D-LOF caught it EATING keystrokes at shorter ones.
# `SCREEN 0` is explicit because the CF-3300 boots Disk BASIC in SCREEN 1, whose
# name table this scraper does not read.
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW", "SCREEN 0", "CLS"), diska=None),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "NEW", "SCREEN 0", "CLS"), diska=SRC_DSK),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5,
                   reset=("NEW", "SCREEN 0", "CLS"), diska=None),
}
REF_SIDES = ("vg8020", "cf3300")

# The two walks. `main` is the dense err_msgtab domain plus one past its end;
# `disk` is the sparse disk range.
#
# ⚠️ CORRECTION, 2026-08-02 -- THE DOCSTRING'S PREDICTION ABOUT THE DISK RANGE
# WAS WRONG, AND THE MEASUREMENT IS WHAT SAYS SO. It predicted the VG-8020 would
# answer `Unprintable error` across 50..64 for want of a disk ROM. It does not:
# it answers 50..59 verbatim (`FIELD overflow` ... `File not OPEN`) and only
# falls to `Unprintable error` at 60. So codes 50..59 live in MAIN BASIC on a
# diskless machine, and only 60..64 are the disk ROM's own. The two references
# therefore agree on 1..59 and differ ONLY on 60..64 -- which is still the
# per-machine-terms check that paragraph wanted, just at a boundary five codes
# further along than predicted. Kept as a written-down wrong prediction rather
# than quietly corrected: the boundary is the finding.
MAIN_CODES = list(range(1, 27))
DISK_CODES = list(range(50, 65))

# --- the battery `ERROR n` CANNOT REACH -------------------------------------
# Four reference messages are not ERR codes raised through the dispatcher, so a
# code walk is structurally blind to them. Each is (label, mode, lines, echo-key).
#
#   brk / brk-run   `STOP` -- prints `Break`, and in a RUN carries " in <line>".
#                   Not an ERR code at all (no err_msgtab entry, no ERR value).
#   redo / extra    INPUT's re-prompt and surplus-data notes. Driven in DIRECT
#                   mode with the data line injected as its own step: after RUN
#                   the machine is sitting at INPUT's `?` prompt, so the next
#                   injected line IS the answer. The echo key is the answer text
#                   -- INPUT echoes it as `? X`, and _echo_idx matches on
#                   endswith, so `X` finds that row.
#
# `Verify error` (ERR 20's wording, cassette VERIFY) is STILL NOT MEASURED here:
# it needs a tape image and the CAS: harness. It is `<not-measured>` in the
# denominator rather than taken from a published reference.
EXTRA = [
    ("brk",     "direct", ["STOP"],                        "STOP"),
    ("brk-run", "direct", ["10 STOP", "RUN"],              "RUN"),
    ("redo",    "direct", ["10 INPUT A", "RUN", "X"],      "X"),
    ("extra",   "direct", ["10 INPUT A", "RUN", "1,2"],    "1,2"),
]

# --- the self-check pair: two codes whose wording is known to differ ----------
# If these read back EQUAL, the readout is not reading the message.
SELFCHECK = (2, 11)


def cases_for(codes: list[int]) -> list[tuple[str, list[str]]]:
    return [("direct", [f"ERROR {n}"]) for n in codes]


def measure(side: str, codes: list[int], *, omsx: str | None = None,
            boot_per_case: bool = False) -> dict[int, str | None]:
    """Drive one side over `codes`, returning code -> screen_tail (or None).

    ONE BOOT for the whole walk. Safe here because no row READS state a previous
    row left behind: every case raises its own code and prints its own message.
    (basic_probe_lnblank.py's `err` battery could NOT batch -- its control read
    the ERRCODE the previous row had just set. That trap does not apply to a
    walk whose only observable is the text printed by the case itself.)
    """
    cfg = dict(SIDES[side])
    machine = cfg.pop("machine")
    diska = cfg.pop("diska")
    reset = cfg.pop("reset")
    tmp = None
    if diska:
        # ⚠️ never hand openMSX the committed image -- a /tmp copy, always.
        tmp = tempfile.NamedTemporaryFile(suffix=".dsk", prefix=f"msgx_{side}_",
                                          delete=False).name
        shutil.copy(diska, tmp)
    try:
        cases = cases_for(codes)
        raws = omsx_repl.run_cases(machine, cases, batch=not boot_per_case,
                                   reset=reset, capture="screen",
                                   omsx=omsx, diska=tmp, **cfg)
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)
    out: dict[int, str | None] = {}
    for n, raw in zip(codes, raws):
        out[n] = omsx_repl.screen_tail(raw, f"ERROR {n}")
    return out


def measure_extra(side: str, *, omsx: str | None = None
                  ) -> dict[str, str | None]:
    """Drive the EXTRA battery (the messages `ERROR n` cannot reach).

    ⚠️ BOOT-PER-CASE, deliberately. `brk-run`/`redo`/`extra` each STORE a line
    and leave the machine mid-INPUT or stopped; batching them would let one
    case's stored program and pending prompt answer the next case's readout.
    Four cases is cheap enough that isolation is the obvious call. Because
    boot-per-case IGNORES `reset` (omsx_repl.run_cases), the reset lines are
    PREPENDED to each case body instead -- the CF-3300's boot date-prompt CR and
    the SCREEN 0 the scraper needs live there, and dropping them would leave it
    at a date prompt being read through a SCREEN-0 scraper (`<none>` on every
    row, which would report as "the CF-3300 declines to answer").
    """
    cfg = dict(SIDES[side])
    machine = cfg.pop("machine")
    diska = cfg.pop("diska")
    reset = cfg.pop("reset")
    tmp = None
    if diska:
        tmp = tempfile.NamedTemporaryFile(suffix=".dsk", prefix=f"msgx_{side}_",
                                          delete=False).name
        shutil.copy(diska, tmp)
    try:
        cases = [(mode, list(reset) + lines) for _, mode, lines, _ in EXTRA]
        raws = omsx_repl.run_cases(machine, cases, batch=False,
                                   capture="screen", omsx=omsx, diska=tmp, **cfg)
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)
    return {label: omsx_repl.screen_tail(raw, key)
            for (label, _, _, key), raw in zip(EXTRA, raws)}


# --- the `verify` battery: ERR 20's wording, via a REAL cassette mismatch -----
# `Verify error` is not `ERROR n`-reachable in a way that proves the wording of
# the string the tape path actually prints, and it is the last hole in the
# denominator. Rig: type a program that POKEs 0x98, mount a tape holding the
# 0x99 version, `CLOAD?` -> the compare fails -> the message.
#
# ⚠️ THIS CANNOT REUSE basic_probe_cas_verify.py. That probe hardcodes
# `-machine ZB_MACHINE` + `-cart`, so it can only ever read ZEROBAS -- and its
# assertion is `"verify error" in scr.lower()`, i.e. CASE-INSENSITIVE. It is
# structurally incapable of seeing the very thing measured here. (That is the
# corpus-wide blindness this whole slice is about, present in the one probe that
# already prints this message.)
#
# ⚠️ VG-8020 ONLY, AND THE REASON IS THE TAPE IMAGE, NOT LAZINESS. The tokenised
# CAS is built with absolute line links for TXTBASE $8001, which is the VG-8020's
# BASIC text base. The CF-3300 boots Disk BASIC with a HIGHER TXTTAB, so the same
# image does not describe its memory. Running it there would measure the tape
# format, not the message. Recorded as a single-reference reading rather than
# silently presented as a two-reference lock.
TXTBASE = 0x8001
WITNESS = 0xD0FF
VERIFY_MACHINE = "Philips_VG_8020"


def measure_verify(*, machine: str = VERIFY_MACHINE, omsx: str | None = None,
                   cap_time: float = 60.0, timeout: float = 140.0) -> str | None:
    """Drive one CLOAD? mismatch on `machine`; return the collapsed screen text.

    Returns None if the capture never landed (a wedge) -- distinct from "" for a
    screen that captured but printed nothing, same two-sentinel rule as the rest
    of this probe.
    """
    binary = omsx or OMSX
    tmp = tempfile.mkdtemp(prefix="msgx_verify_")
    cas = os.path.join(tmp, "v_diff.cas")
    # tape holds the 0x99 program; memory will hold 0x98 -> a one-byte mismatch
    with open(cas, "wb") as f:
        f.write(build_cas_basic("V", make_multiline_program(
            [(10, f"POKE&H{WITNESS:04X},&H99")], TXTBASE)))
    out = os.path.join(tmp, "cap.txt")
    # ⚠️ TIMINGS ARE THE VG-8020'S, NOT basic_probe_cas_verify.py's. That probe
    # types at 6.0 s on the REPACK machine; on the VG-8020 that is BEFORE the
    # prompt (omsx_repl.SIDES gives it boot=8.0), and the first measurement run
    # proved it -- the program line never appeared on screen at all and the
    # readout returned a boot banner. Everything is pushed past the real boot.
    typed = [(12.0, f"10 POKE&H{WITNESS:04X},&H98"), (15.0, "\r"),
             (18.0, "CLOAD?"), (20.0, "\r")]
    # ⚠️ `autoruncassettes` MUST BE OFF. openMSX types CLOAD+RUN by itself when a
    # cassette is mounted; the first run here captured `CLOAD Found:V Ok RUN Ok`
    # as boot output, which means the tape had ALREADY BEEN CONSUMED before the
    # probe's own CLOAD? ran -- so the readout would have measured a tape at its
    # end, not a verify mismatch. basic_probe_cas_verify.py does not hit this
    # because its rig differs; anything new driving a cassette does.
    lines = ["set throttle off",
             "set autoruncassettes off",
             "set renderer none; set sound_driver null"]
    for delay, text in typed:
        lines.append(f"after time {delay} {{ type {_tcl_dquote(text)} }}")
    lines += [
        "proc cap {} {",
        f"  set f [open {{{out}}} w]",
        "  binary scan [debug read_block {VRAM} 0x0000 960] H* h0; puts $f \"s0=$h0\"",
        "  close $f; exit }",
        f"after time {cap_time} {{ cap }}",
    ]
    tcl = out + ".tcl"
    with open(tcl, "w") as f:
        f.write("\n".join(lines) + "\n")
    # ⚠️ ORDER MATTERS. openMSX processes command-line options IN SEQUENCE, and
    # the auto-run fires when the cassette is INSERTED -- so the setting has to
    # be off BEFORE `-cassetteplayer`, not merely somewhere in the -script (which
    # runs too late; the first fix attempt put it there and the tape was still
    # consumed at boot).
    cmd = [binary, "-machine", machine,
           "-command", "set autoruncassettes off",
           "-cassetteplayer", cas, "-script", tcl]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    scr = None
    if os.path.exists(out):
        scr = ""
        for ln in open(out):
            k, _, v = ln.strip().partition("=")
            if k == "s0":
                scr += "".join(chr(c) if 32 <= c < 127 else " "
                               for c in bytes.fromhex(v))
        scr = re.sub(r"\s+", " ", scr).strip()
    shutil.rmtree(tmp, ignore_errors=True)
    return scr


def show(v: str | None) -> str:
    """Two distinct empty sentinels, never collapsed."""
    if v is None:
        return "<none>"
    if v == "":
        return "<empty>"
    return v


def selfcheck(readings: dict[int, str | None], side: str) -> list[str]:
    a, b = SELFCHECK
    va, vb = readings.get(a), readings.get(b)
    problems = []
    if va is None or vb is None:
        problems.append(
            f"{side}: selfcheck codes {a}/{b} did not both read "
            f"({show(va)} / {show(vb)}) -- the walk never reached them")
    elif va == vb:
        problems.append(
            f"{side}: selfcheck FAILED -- ERROR {a} and ERROR {b} read the SAME "
            f"string {va!r}. The readout is not tracking the message; every "
            f"'agrees' below would be an artefact.")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sides", default="vg8020,cf3300",
                    help="comma-separated: vg8020,cf3300,zb (default both refs)")
    ap.add_argument("--walk", default="main,disk",
                    help="comma-separated: main (1..26), disk (50..64), "
                         "extra (the non-ERROR-n messages)")
    ap.add_argument("--omsx", default=None)
    ap.add_argument("--boot-per-case", action="store_true",
                    help="isolation escape hatch: one boot per code")
    args = ap.parse_args()

    sides = [s for s in args.sides.split(",") if s]
    walks = [w for w in args.walk.split(",") if w]
    for s in sides:
        if s not in SIDES:
            print(f"unknown side {s!r}", file=sys.stderr)
            return 2

    codes: list[int] = []
    if "main" in walks:
        codes += MAIN_CODES
    if "disk" in walks:
        codes += DISK_CODES
    want_extra = "extra" in walks
    want_verify = "verify" in walks
    if want_verify:
        print(f"# measuring Verify error on {VERIFY_MACHINE} (cassette rig) ...",
              file=sys.stderr, flush=True)
        vscr = measure_verify(omsx=args.omsx)
        print()
        print(f"VERIFY ({VERIFY_MACHINE}, single-reference -- see module notes)")
        print("  screen: " + show(vscr))
        print()
        if not codes and not want_extra:
            return 0
    if not codes and not want_extra:
        print("no walk selected", file=sys.stderr)
        return 2

    readings: dict[str, dict[int, str | None]] = {}
    extras: dict[str, dict[str, str | None]] = {}
    for s in sides:
        if codes:
            print(f"# measuring {s} ({SIDES[s]['machine']}) over {len(codes)} codes ...",
                  file=sys.stderr, flush=True)
            readings[s] = measure(s, codes, omsx=args.omsx,
                                  boot_per_case=args.boot_per_case)
        else:
            readings[s] = {}
        if want_extra:
            print(f"# measuring {s} extra battery ({len(EXTRA)} cases, "
                  f"boot-per-case) ...", file=sys.stderr, flush=True)
            extras[s] = measure_extra(s, omsx=args.omsx)

    problems = []
    if "main" in walks:
        for s in sides:
            problems += selfcheck(readings[s], s)

    print()
    if codes:
        print("ERR | " + " | ".join(s.ljust(28) for s in sides))
        print("----+-" + "-+-".join("-" * 28 for _ in sides))
        for n in codes:
            cells = [show(readings[s].get(n)).ljust(28) for s in sides]
            print(f"{n:3d} | " + " | ".join(cells))
        print()
    if want_extra:
        print("EXTRA   | " + " | ".join(s.ljust(28) for s in sides))
        print("--------+-" + "-+-".join("-" * 28 for _ in sides))
        for label, _, _, _ in EXTRA:
            cells = [show(extras[s].get(label)).ljust(28) for s in sides]
            print(f"{label:7s} | " + " | ".join(cells))
        print(f"{'verify':7s} | " + " | ".join(
            "<not-measured>".ljust(28) for _ in sides))
        print()

    # Agreement summary across the two references only -- the whole point of a
    # two-reference lock is that a rule BOTH show is a property of MSX-BASIC.
    refs = [s for s in sides if s in REF_SIDES]
    if len(refs) == 2:
        a, b = refs
        same = [n for n in codes if readings[a].get(n) == readings[b].get(n)]
        diff = [n for n in codes if readings[a].get(n) != readings[b].get(n)]
        print(f"references agree on {len(same)}/{len(codes)} codes")
        if diff:
            print(f"references DIFFER on: {', '.join(str(n) for n in diff)}")

    if problems:
        print()
        for p in problems:
            print("!! " + p)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
