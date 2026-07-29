#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Characterize -- and now GATE -- what ONE FILE CHANNEL COSTS on an MSX1.

Originally the question was: zerobas spends 562 B per channel and caps at
FCH_CEIL=2; what does the reference actually spend, and what is its ceiling?
Answer: 267 B/channel, dynamically, ceiling exactly 15. D-FCH then made zerobas
use the SAME MECHANISM -- carved out of the FRE(0) pool at MAXFILES time,
ceiling 15 -- at its own honest 50 B/channel (a zerobas block IS 50 B; its
sector staging is the shared FSECTOR_BUF write-back cache, so it charges what it
uses rather than padding to match a number).

So this is now an ACCEPTANCE GATE. It returns non-zero on oracle drift, on any
divergence not in the explicit KNOWN_DIVERGE allowlist (each entry naming the
item that owns it), and on the mechanism assertions: per-channel, LINEAR, with a
ceiling of 15, on BOTH machines.

⚠️ WHY THIS PROBE EXISTS RATHER THAN AN `omsx_repl` BATTERY. The earlier attempt
read `<none>` on every row and was mis-read as "the CF-3300 won't answer". It is
an APPARATUS failure: `omsx_repl` scrapes the SCREEN 0 name table at VRAM $0000
at 40 columns (probes/lib/omsx_repl.py SCR_ADDR/COLS, whose comment already
flags this), but **CF-3300 Disk BASIC boots to SCREEN 1** — measured here, not
assumed: `scrmod=$01`, `linlen=$1d` (29), name table **$1800 at 32 columns**.
This probe reads the geometry out of RAM and picks the name table from it, so it
works on both machines.

⚠️ `FRE(0)` IS IMPURE — it counts down to the STACK POINTER, and every extra
expression-nesting level costs 6 bytes (docs/binfre-vg8020-characterization.md
§3.1). Every reading below is therefore the byte-identical expression
`PRINT FRE(0)` at identical depth. Do not "simplify" one row's expression.

CONTROLS (a ladder this clean is exactly when to try hardest to falsify it):
  * `ctl_syntax` types a misspelled keyword and MUST show `Syntax error` — if it
    comes back clean the harness is not typing and every number here is worthless;
  * `ctl_noop` types `REM MAXFILES=8`: echoed, parsed, and MUST NOT move FRE(0)
    — so the ladder's movement is attributable to the statement, not the typing;
  * note `MAXFILES=1` reads the SAME as an untouched boot because 1 IS the Disk
    BASIC default — that row CANNOT distinguish "the statement ran" from "the
    line was never typed", and is not load-bearing. The rows that carry the
    result are 0/2/3/4/8/15, which all move.

CLEAN-ROOM: black-box only — typed BASIC in, screen + documented sysvars out.
No reference ROM is read or disassembled.

DISK SAFETY: every case runs on a /tmp COPY of the test image; the committed
.dsk is never mounted (OPEN FOR OUTPUT would mutate it).
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))

import argparse
import concurrent.futures as cf
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time

OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"
SRC_DSK = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "disk", "test720.dsk")

# side -> (machine, has-date-prompt, boot instant in emulated seconds)
MACHINES = {
    "ref": ("National_CF-3300", True, 12.0),
    "zb":  (os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"),
            False, 8.0),
}

# label -> typed lines. Keep <= 6 lines: the 24-row screen scrolls.
CASES = [
    ("ctl_syntax", ["MAXFILEZ=2", "PRINT FRE(0)"]),
    ("ctl_noop",   ["REM MAXFILES=8", "PRINT FRE(0)"]),
    ("boot",  ["PRINT FRE(0)"]),
    ("mf0",   ["MAXFILES=0", "PRINT FRE(0)"]),
    ("mf1",   ["MAXFILES=1", "PRINT FRE(0)"]),
    ("mf2",   ["MAXFILES=2", "PRINT FRE(0)"]),
    ("mf3",   ["MAXFILES=3", "PRINT FRE(0)"]),
    ("mf4",   ["MAXFILES=4", "PRINT FRE(0)"]),
    ("mf8",   ["MAXFILES=8", "PRINT FRE(0)"]),
    ("mf15",  ["MAXFILES=15", "PRINT FRE(0)"]),
    ("mf16",  ["MAXFILES=16", "PRINT FRE(0)"]),
    ("mf255", ["MAXFILES=255", "PRINT FRE(0)"]),
    # is the buffer charged when the channel is DECLARED or when it is OPENED?
    ("open_after", ["MAXFILES=2", 'OPEN "ZQ.DAT" FOR OUTPUT AS #1', "PRINT FRE(0)"]),
    # which pool pays? (FRE("") is the string pool -- a separate allocator)
    ("str0",  ["MAXFILES=0", 'PRINT FRE("")']),
    ("str8",  ["MAXFILES=8", 'PRINT FRE("")']),
    # incidental, kept because the cost pass found it: LOF on a fresh OUTPUT
    # channel. `lof_existing` is its two-sided control -- it MUST agree (26).
    ("lof_new",      ['OPEN "ZQ.DAT" FOR OUTPUT AS #1', "PRINT LOF(1)"]),
    ("lof_existing", ['OPEN "HI.TXT" FOR INPUT AS #1', "PRINT LOF(1)"]),

    # --- SEMANTICS battery: what MAXFILES must DO, for the dynamic-allocation
    # spec. Reallocating the channel table moves the top of the pool, so these
    # ask what the reference does to everything living under it. Measured, not
    # assumed -- the spec's behaviour section is written from these rows.
    ("sem_var",     ["A=5", "MAXFILES=2", "PRINT A"]),            # vars survive?
    ("sem_var_ctl", ["A=5", "REM MAXFILES=2", "PRINT A"]),        # ...control
    # ⚠️ `PRINT A$` was the original form and it is UNMEASURABLE: a cleared A$
    # prints an empty line, which this probe's readout scores as `<none>` -- and
    # `<none>` on BOTH sides compares EQUAL and reports PASS whether or not
    # either machine ran the statement (the clearpool-slice trap). LEN(A$) puts
    # a NUMBER on the screen, so the row can actually fail.
    ("sem_str",     ['A$="XY"', "MAXFILES=2", "PRINT LEN(A$)"]),  # strings survive?
    ("sem_str_ctl", ['A$="XY"', "REM MAXFILES=2", "PRINT LEN(A$)"]),  # ...control
    ("sem_same",    ["A=5", "MAXFILES=1", "PRINT A"]),            # no-change reallocs?
    ("sem_reopen",  ["MAXFILES=2", 'OPEN "HI.TXT" FOR INPUT AS #1',
                     "MAXFILES=2", "PRINT LOF(1)"]),              # open chan survives?
    ("sem_zero",    ["MAXFILES=0", 'OPEN "HI.TXT" FOR INPUT AS #1']),   # 0 = no I/O?
    ("sem_hinum",   ["MAXFILES=1", 'OPEN "HI.TXT" FOR INPUT AS #2']),   # #n > MAXFILES
    ("sem_clear",   ["CLEAR 500", "MAXFILES=2", 'PRINT FRE("")']),      # pool kept?

    # --- RESERVATION battery (D-FCH §3.2). ⚠️ THE LADDER ABOVE CAN BE GREEN
    # WHILE MEASURING NOTHING: it reads FRE(0), which is what the interpreter
    # SAYS is left, and a build that subtracted the channel table from the
    # REPORT but not from the ALLOCATOR'S CEILING would produce a perfect
    # 50 B/channel slope while reserving nothing at all — the arrays would grow
    # straight through the table and be shredded by the next channel switch.
    # These two rows close that hole, and they are TWO-SIDED on purpose:
    #   dim_fits — ask for FRE(0) MINUS 800 B: must succeed on both machines.
    #              (Guards the other direction: a build that reported the floor
    #              while allocating against the lower ceiling would OOM here.)
    #   dim_over — ask for FRE(0) PLUS 400 B: must raise Out of memory.
    # The overshoot is chosen against the FAILURE it must catch, not for round
    # numbers: at MAXFILES=15 an unreserved zerobas table is 750 B of slack, so
    # 400 B of overshoot lands INSIDE it and would silently succeed. Both rows
    # size themselves from the machine's OWN FRE(0), so they are a real
    # differential rather than a zerobas-only constant.
    ("dim_fits", ["10 MAXFILES=15", "20 N=INT(FRE(0)/2)-400", "30 DIM A%(N)",
                  "40 PRINT 7777", "RUN"]),
    ("dim_over", ["10 MAXFILES=15", "20 N=INT(FRE(0)/2)+200", "30 DIM A%(N)",
                  "40 PRINT 7777", "RUN"]),

    # --- ERR CODES. The spec needs the NUMBERS, and they are disk-range codes
    # well above zerobas's err_msgtab (which stops at 25). Trapped with
    # ON ERROR/ERR so the code is read, not inferred from the message wording.
    ("err_over",    ["10 ON ERROR GOTO 100", "20 MAXFILES=16", "30 END",
                     "100 PRINT ERR", "RUN"]),
    ("err_badchan", ["10 ON ERROR GOTO 100", "20 MAXFILES=1",
                     '30 OPEN "HI.TXT" FOR INPUT AS #2', "40 END",
                     "100 PRINT ERR", "RUN"]),
    ("err_notopen", ["10 ON ERROR GOTO 100", "20 PRINT LOF(1)", "30 END",
                     "100 PRINT ERR", "RUN"]),

    # --- S-FCH-2 ERR 52/59, UNCONFOUNDED. ⚠️ `err_badchan` above was read by
    # spec §5c as "ERR 52 is not trappable" and a forced-abort raiser (ONEFLG:=1,
    # left set) was specced on that reading. IT IS A CONFOUND: the row types
    # `MAXFILES=1` BETWEEN the ON ERROR and the failing OPEN, and MAXFILES --
    # like a plain CLEAR -- DISARMS the handler on the reference (mf_disarm /
    # clr_disarm below, each with a two-sided control). With nothing in between,
    # ERR 52 traps like any other code. These rows raise 52 two ways that touch
    # no MAXFILES at all, and 59 likewise, so what they measure is the CODE.
    ("bfn_trap",  ["10 ON ERROR GOTO 100", '20 OPEN "HI.TXT" FOR INPUT AS #2',
                   "30 END", "100 PRINT 7000+ERR", "RUN"]),   # #2 > default MAXFILES=1
    ("bfn_zero",  ["10 ON ERROR GOTO 100", '20 OPEN "HI.TXT" FOR INPUT AS #0',
                   "30 END", "100 PRINT 7000+ERR", "RUN"]),   # #0 is out of range always
    ("fno_eof",   ["10 ON ERROR GOTO 100", "20 B=EOF(1)",
                   "30 END", "100 PRINT 7000+ERR", "RUN"]),   # EOF, not just LOF
    # ...and the two-sided control that makes those three mean anything: the SAME
    # shape with a known-trappable code must read 7005 on both machines. Without
    # it, a build where NO handler ever fires would score all three "agree" on
    # the abort text. (gate-can-be-green-while-measuring-nothing)
    ("bfn_ctl",   ["10 ON ERROR GOTO 100", "20 B=SQR(-1)",
                   "30 END", "100 PRINT 7000+ERR", "RUN"]),

    # --- the DISARM finding itself, filed as a gate row so it cannot be lost.
    # Reference: MAXFILES (and CLEAR) disarm an armed ON ERROR handler; zerobas
    # does not. Each has its own two-sided control with the statement REMmed out,
    # which must trap on both machines -- otherwise the disarm row is measuring
    # "this program never traps at all".
    ("mf_disarm", ["10 ON ERROR GOTO 100", "20 MAXFILES=1", "30 B=SQR(-1)",
                   "40 END", "100 PRINT 7777", "RUN"]),
    ("mf_ctl",    ["10 ON ERROR GOTO 100", "20 REM MAXFILES=1", "30 B=SQR(-1)",
                   "40 END", "100 PRINT 7777", "RUN"]),
    ("clr_disarm", ["10 ON ERROR GOTO 100", "20 CLEAR", "30 B=SQR(-1)",
                    "40 END", "100 PRINT 7777", "RUN"]),
    ("clr_ctl",    ["10 ON ERROR GOTO 100", "20 REM CLEAR", "30 B=SQR(-1)",
                    "40 END", "100 PRINT 7777", "RUN"]),
]

# The reference's own recorded answers. Re-checking that the oracle still
# reproduces these is what makes it an oracle (memory: validate-oracle-artifacts).
# value = the last integer printed, or an error string seen on screen.
REF_EXPECT = {
    "ctl_syntax": "SYNTAX",
    "ctl_noop":   23430,
    "boot":       23430,
    "mf0":        23697,
    "mf1":        23430,
    "mf2":        23163,
    "mf3":        22896,
    "mf4":        22629,
    "mf8":        21561,
    "mf15":       19692,
    "mf16":       "IFC",
    "mf255":      "IFC",
    "open_after": 23163,
    "str0":       200,
    "str8":       200,
    "lof_new":    0,
    "lof_existing": 26,
    # semantics battery (§9 of the characterization)
    "sem_var":     0,        # MAXFILES CLEARS variables
    "sem_var_ctl": 5,        # ...and the control proves the statement did it
    "sem_same":    0,        # ...even when the value does not change
    "sem_str":     0,        # ...strings too (LEN, not PRINT A$ -- see the case)
    "sem_str_ctl": 2,        # ...and its two-sided control keeps "XY"
    "sem_reopen":  "FNO",    # ...and CLOSES open channels
    "sem_zero":    "BFN",    # MAXFILES=0 -> OPEN is Bad file number
    "sem_hinum":   "BFN",    # #n above MAXFILES -> Bad file number
    "sem_clear":   500,      # ...but the CLEAR-set string pool size SURVIVES
    # reservation battery (D-FCH §3.2) -- FRE(0) is HONEST about the allocator
    "dim_fits":    7777,     # FRE(0)-800 B of array fits
    "dim_over":    "OOM",    # FRE(0)+400 B of array does not
    # error CODES, trapped via ON ERROR/ERR (§10 of the characterization)
    "err_over":    5,        # MAXFILES=16 -> ERR 5 Illegal function call
    "err_badchan": "BFN",    # ...prints `Bad file number in 30` PAST the handler --
                             # because line 20's MAXFILES DISARMED it (mf_disarm),
                             # NOT because ERR 52 is untrappable (bfn_trap)
    "err_notopen": 59,       # LOF on a closed channel -> ERR 59 File not OPEN
    # S-FCH-2 unconfounded (recorded 2026-07-29): ERR 52 and ERR 59 both TRAP.
    "bfn_trap":    7052,
    "bfn_zero":    7052,
    "fno_eof":     7059,
    "bfn_ctl":     7005,     # the two-sided control: a known-trappable code
    # the disarm finding: MAXFILES and CLEAR both disarm; the controls both trap.
    "mf_disarm":   "IFC",    # handler did NOT run -> the S1 abort text instead
    "mf_ctl":      7777,     # ...and with MAXFILES REMmed out it DOES run
    "clr_disarm":  "IFC",
    "clr_ctl":     7777,
}

# Error CLASSES, not wordings. zerobas prints its OWN lowercase messages by
# deliberate provenance policy (basic/PROVENANCE.md §851: own wording, never the
# reference's verbatim strings), so `Syntax error` vs `syntax error` is the
# firewall working as designed -- NOT a divergence. Comparing the raw text would
# emit a false divergence on every error row and bury the real findings.
ERR_CLASSES = {
    "SYNTAX": ("syntax error",),
    "IFC":    ("illegal function call",),
    "FNF":    ("file not found",),
    "BFN":    ("bad file number",),
    "FNO":    ("file not open",),
    "OOM":    ("out of memory",),
}

# How each case is compared between the two machines:
#   "class"  — compare the error class / integer verbatim (a real differential)
#   "absfre" — INFORMATIONAL ONLY. Absolute FRE(0) differs between machines by
#              design (different RAM maps); only the SLOPE across the ladder is
#              meaningful, and that is derived separately below.
COMPARE = {
    "boot": "absfre", "ctl_noop": "absfre", "open_after": "absfre",
    "mf0": "absfre", "mf1": "absfre", "mf2": "absfre", "mf3": "absfre",
    "mf4": "absfre", "mf8": "absfre", "mf15": "absfre",
}

# --- GATE: divergences that are FILED AND EXPECTED, with the item that owns
# each. Everything NOT listed here is a regression and fails the run. The list
# is the honest statement of what D-FCH has not built yet; it shrinks as those
# items land, and it must never grow silently. ⚠️ A row is allowlisted with the
# value it is EXPECTED to diverge to, so a row that starts failing DIFFERENTLY
# still trips the gate.
KNOWN_DIVERGE = {
    # ✅ S-FCH-2 ALL-RESIDENT LANDED 2026-07-29 (docs/spec-basic-filechan-alloc.md
    # §5d): ERR 52 `bad file number` and ERR 59 `file not open` are raised and
    # printed by the resident ROM, as ORDINARY TRAPPABLE codes through a sparse
    # arm off raise_error's out-of-table branch. That closed FOUR rows that used
    # to live on this list -- sem_zero, sem_hinum, sem_reopen and err_notopen --
    # and is why they are gone rather than updated.
    #
    # ⚠️ `err_badchan` SURVIVES, AND ITS OWNER CHANGED. It is NOT an S-FCH-2 row
    # any more: bfn_trap/bfn_zero prove ERR 52 traps, and mf_disarm/clr_disarm
    # (each two-sided) prove why this one does not -- line 20's `MAXFILES=1`
    # DISARMS the handler on the reference, and does not on zerobas. So the
    # reference reports past the handler while zerobas traps and prints 52. The
    # divergence that remains is "CLEAR/MAXFILES do not disarm ON ERROR", an
    # ERROR-HANDLING defect measured 2026-07-29 and filed in TODO.md -- and it
    # contradicts the standing hypothesis recorded at basic/sysvars.inc's ONELIN
    # ("NOT clear_vars, so NEW/CLEAR alone do not disarm a handler").
    "err_badchan": ("BFN", 52),
    "mf_disarm":   ("IFC", 7777),
    "clr_disarm":  ("IFC", 7777),
    # Filed separately in TODO.md: LOF on a freshly-created OUTPUT channel reads
    # -1 where the reference reads 0. A LOF bug, not an allocation one -- its
    # two-sided control `lof_existing` agrees at 26 on both machines.
    "lof_new":     (0, -1),
}


def err_class(text: str):
    """Map a screen line to an error class, or None if it is not an error."""
    low = text.lower()
    for cls, needles in ERR_CLASSES.items():
        for n in needles:
            if n in low:
                return cls
    return None


def tcl_quote(s: str) -> str:
    # CR must be the ESCAPE \r; a raw 0x0d breaks Tcl's line parsing and the
    # Enter event is silently dropped.
    out = []
    for ch in s:
        if ch == "\r":
            out.append("\\r")
        elif ch in '"\\[]$':
            out.append("\\" + ch)
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def build_tcl(out_path: str, lines, date_prompt: bool, boot_t: float) -> str:
    L = ["set throttle off",
         f"set __f [open {{{out_path}}} w]",
         "proc __hex {a l} { binary scan [debug read_block memory $a $l] H* h; return $h }",
         "proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h; return $h }",
         "proc __dump {} {",
         "  global __f",
         '  puts $__f "meta scrmod=[__hex 0xFCAF 1] linlen=[__hex 0xF3B0 1]'
         ' himem=[__hex 0xFC4A 2] txttab=[__hex 0xF676 2]"',
         '  puts $__f "scr0=[__hex_v 0x0000 960]"',
         '  puts $__f "scr1=[__hex_v 0x1800 768]"',
         "  flush $__f",
         "}"]
    t = boot_t
    if date_prompt:
        L.append(f'after time {t} {{ type "\\r" }}')   # clear "Enter date"
        t += 4.0
    for ln in lines:
        # openMSX drops a CR that shares a burst with text under `throttle off`,
        # so each Enter is its own event ~3s after its command.
        L.append(f"after time {t} {{ type {tcl_quote(ln)} }}")
        L.append(f'after time {t + 3.0} {{ type "\\r" }}')
        t += 4.5
    L.append(f"after time {t + 2.0} {{ __dump }}")
    L.append(f"after time {t + 4.0} {{ close $__f; exit }}")
    return "\n".join(L) + "\n"


def decode(hexv: str, cols: int):
    data = bytes.fromhex(hexv)
    return [("".join(chr(c) if 32 <= c < 127 else " "
                     for c in data[r * cols:(r + 1) * cols])).strip()
            for r in range(len(data) // cols)]


def run_case(side: str, label: str, lines):
    machine, date_prompt, boot_t = MACHINES[side]
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix=f"cc_{side}_{label}_",
                                      delete=False).name
    shutil.copy(SRC_DSK, dsk)              # /tmp copy -- never the committed image
    out = f"/tmp/chancost_{side}_{label}.txt"
    tcl = out + ".tcl"
    with open(tcl, "w") as fh:
        fh.write(build_tcl(out, lines, date_prompt, boot_t))
    if os.path.exists(out):
        os.unlink(out)
    proc = subprocess.Popen(
        [OMSX, "-machine", machine, "-diska", dsk,
         "-command", "set renderer none", "-script", tcl],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + 200
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        os.unlink(dsk)
        return side, label, None, ["TIMEOUT"], ""
    os.unlink(dsk)
    if not os.path.exists(out):
        return side, label, None, ["NO CAPTURE (machine/ROMs missing?)"], ""
    s0, s1, meta, scrmod = [], [], "", 0
    for line in open(out):
        line = line.rstrip("\n")
        if line.startswith("scr0="):
            s0 = decode(line.partition("=")[2], 40)
        elif line.startswith("scr1="):
            s1 = decode(line.partition("=")[2], 32)
        else:
            meta = line
            for tok in line.split():
                if tok.startswith("scrmod="):
                    scrmod = int(tok.split("=")[1], 16)
    # geometry MEASURED, not assumed
    rows = [r for r in (s1 if scrmod == 1 else s0) if r]
    value = None
    for r in rows:                                   # an error outranks a number
        cls = err_class(r)
        if cls:
            value = cls
    if value is None:
        nums = [int(r) for r in rows if re.fullmatch(r"-?\d+", r)]
        value = nums[-1] if nums else None
    return side, label, value, rows, meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated case labels")
    ap.add_argument("--side", choices=("ref", "zb", "both"), default="both")
    ap.add_argument("-v", "--verbose", action="store_true", help="print screens")
    args = ap.parse_args()
    if not os.path.isfile(SRC_DSK):
        print(f"missing test image: {SRC_DSK}")
        return 2
    cases = CASES
    if args.only:
        want = {s.strip() for s in args.only.split(",") if s.strip()}
        cases = [c for c in CASES if c[0] in want]
        if not cases:
            print(f"--only matched no cases: {sorted(want)}")
            return 2
    sides = ("ref", "zb") if args.side == "both" else (args.side,)
    jobs = [(s, lbl, lines) for lbl, lines in cases for s in sides]
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(lambda j: run_case(*j), jobs))
    by = {(s, l): (v, rows, meta) for s, l, v, rows, meta in results}

    print(f"{'case':<14} {'reference':>14} {'zerobas':>14}   verdict")
    print("-" * 70)
    oracle_bad, diverge = [], []
    for label, _ in cases:
        rv = by.get(("ref", label), (None, [], ""))[0] if "ref" in sides else "-"
        zv = by.get(("zb", label), (None, [], ""))[0] if "zb" in sides else "-"
        mode = COMPARE.get(label, "class")
        note = ""
        if "ref" in sides and label in REF_EXPECT and rv != REF_EXPECT[label]:
            note = f"ORACLE DRIFT (recorded {REF_EXPECT[label]!r})"
            oracle_bad.append(label)
        elif args.side == "both":
            if mode == "absfre":
                # absolute pool sizes are not comparable between machines --
                # only the ladder's SLOPE is, and that is derived below.
                note = "informational (slope below)"
            elif rv == zv:
                note = "agree"
            elif KNOWN_DIVERGE.get(label) == (rv, zv):
                note = "diverges (FILED — ON ERROR disarm / LOF, TODO)"
            else:
                note = "DIVERGES"
                diverge.append((label, rv, zv))
        print(f"{label:<14} {str(rv):>14} {str(zv):>14}   {note}")
        if args.verbose:
            for s in sides:
                for r in by.get((s, label), (None, [], ""))[1]:
                    print(f"      {s} | {r}")

    print()
    if "ref" in sides:
        print("meta(ref):", by.get(("ref", cases[0][0]), (None, [], ""))[2])
    if "zb" in sides:
        print("meta(zb) :", by.get(("zb", cases[0][0]), (None, [], ""))[2])

    # --- THE DERIVED ANSWER: per-channel slope + ceiling, both machines ---
    ladder = [("mf0", 0), ("mf1", 1), ("mf2", 2), ("mf3", 3),
              ("mf4", 4), ("mf8", 8), ("mf15", 15)]
    print()
    summary = {}
    for s in sides:
        pts = [(n, by[(s, l)][0]) for l, n in ladder
               if (s, l) in by and isinstance(by[(s, l)][0], int)]
        slopes = {(pts[i - 1][1] - pts[i][1]) / (pts[i][0] - pts[i - 1][0])
                  for i in range(1, len(pts))} if len(pts) >= 2 else set()
        # The ceiling is only a CEILING if the rows above it actually ran and
        # were rejected. On a subsetted run the largest surviving n is just the
        # largest n we asked about -- reporting that as "the ceiling" would be a
        # number the run never measured.
        ran = {l for l, _ in cases}
        full_ladder = all(l in ran for l, _ in ladder) and {"mf16"} <= ran
        ceiling = max((n for n, _ in pts), default=None)
        summary[s] = (sorted(slopes), ceiling if full_ladder else None)
        shape = ("statically reserved (MAXFILES does not move FRE(0))"
                 if slopes == {0.0} else
                 f"{sorted(slopes)[0]:g} B/channel, charged from the FRE(0) pool"
                 if len(slopes) == 1 else "NOT LINEAR — investigate")
        ceil_txt = (f"highest accepted MAXFILES = {ceiling}" if full_ladder
                    else f"ceiling NOT MEASURED (partial ladder; largest tried {ceiling})")
        print(f"{s:>4}: per-channel = {shape}; {ceil_txt}")

    if oracle_bad:
        print(f"\nORACLE DRIFT on {oracle_bad} — the reference no longer reproduces "
              f"its own recorded answers; fix the apparatus before trusting anything.")
        return 1
    full_run = args.side == "both" and len(cases) == len(CASES)
    if full_run:
        rs, rc = summary.get("ref", ([], None))
        zs, zc = summary.get("zb", ([], None))
        print()
        print("HEADLINE:")
        print(f"  reference charges {rs[0]:g} B per channel, dynamically, up to {rc};")
        print(f"  zerobas   charges {zs[0]:g} B per channel, dynamically, up to {zc}.")
        print("  (D-FCH §3.2: both MECHANISMS are now the same -- carved out of the")
        print("   FRE(0) pool at MAXFILES time, ceiling 15. The per-channel CONSTANTS")
        print("   differ because a zerobas block IS 50 B: its sector staging is the")
        print("   shared FSECTOR_BUF cache, so it charges what it uses.)")

    if oracle_bad:
        print(f"\nORACLE DRIFT on {oracle_bad} — the reference no longer reproduces "
              f"its own recorded answers; fix the apparatus before trusting anything.")
        return 1
    if diverge:
        print(f"\n{len(diverge)} UNFILED divergence(s) vs the reference:")
        for label, rv, zv in diverge:
            print(f"  {label}: reference {rv!r}, zerobas {zv!r}")
        return 1
    # --- the GATE proper: the mechanism assertions, only on a full run --------
    if full_run:
        bad = []
        for s in ("ref", "zb"):
            slopes, ceiling = summary.get(s, ([], None))
            if slopes == [0.0]:
                bad.append(f"{s}: MAXFILES does not move FRE(0) (statically reserved)")
            elif len(slopes) != 1:
                bad.append(f"{s}: per-channel charge is NOT LINEAR: {slopes}")
            if ceiling != 15:
                bad.append(f"{s}: highest accepted MAXFILES is {ceiling}, want 15")
        if bad:
            print("\nGATE FAILED:")
            for b in bad:
                print(f"  {b}")
            return 1
        print("\nGATE: both machines charge per-channel, linearly, ceiling 15 — "
              f"{len(cases)} cases, {len(KNOWN_DIVERGE)} filed divergences.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
