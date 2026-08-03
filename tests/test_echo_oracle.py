#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ECHO (docs/spec-probe-echo.md) -- the delivery echo oracle's JUDGEMENT.

Pure host Python: no emulator, no ROM. It exists because the emulator half of
this guard has NO permanent positive control -- a batch of identical cases does
not reproduce the delivery race (predecessor content moves the alignment,
docs/spec-probe-delivery.md §8.4), so the only emulator reproduction is phase O's
exact 35 payloads, which would go silent the day a ROM change shifted it. These
rows cannot go silent.

The screens below are the ones MEASURED on the two machines
(docs/echo-delivery-characterization.md §1), including the fault screen the
machine actually produced.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "probes", "lib"))
import omsx_repl  # noqa: E402

COLS, ROWS = omsx_repl.COLS, omsx_repl.ROWS

# the two geometries, MEASURED -- see spec-probe-echo.md §2.1. They differ in
# BOTH numbers, which is the whole reason neither may be hard-coded.
VG8020 = dict(margin=2, linlen=37)
ZEROBAS = dict(margin=1, linlen=39)

fails = []


def check(label, got, want):
    if got != want:
        fails.append(f"{label}: got {got!r}, want {want!r}")
    print(f"  {'PASS' if got == want else 'FAIL'}  {label:<46} {got!r}")


def screen(text_rows, *, margin, linlen):
    """A name-table capture: each logical row placed at `margin`, wrapping at
    `linlen` onto the next row exactly as both machines do."""
    out = []
    for t in text_rows:
        while True:
            out.append(" " * margin + t[:linlen])
            t = t[linlen:]
            if not t:
                break
    out += [""] * (ROWS - len(out))
    return "".join(r.ljust(COLS)[:COLS] for r in out[:ROWS])


def verdicts(slots, dumps):
    """dumps: list of (scrmod, geometry, text_rows) or None, aligned with slots."""
    e = {i: (sm, g["linlen"], screen(rows, **g))
         for i, d in enumerate(dumps) if d for sm, g, rows in [d]}
    return [t[3] for t in omsx_repl.echo_verdicts(slots, e)]


print("=== D-ECHO comparator ===")

# --- 1. the fault, exactly as the machine produced it ------------------------
# D-DELIVER §2.3: `10 ON ERROR GOTO 40` was typed, the machine swallowed `10 O`,
# the screen editor read back the remainder and BASIC rejected it.
slots = [(0, "CLS"), (0, "10 ON ERROR GOTO 40")]
check("head-swallowed line is MANGLED",
      verdicts(slots, [(0, ZEROBAS, ["ZB"]),
                       (0, ZEROBAS, ["ZBN ERROR GOTO 40", "Syntax error", "ZB"])]),
      ["BLIND/rewrote", "MANGLED"])

# the GREEN control: the same slots, the line delivered intact
check("intact line is OK",
      verdicts(slots, [(0, ZEROBAS, ["ZB"]),
                       (0, ZEROBAS, ["ZB10 ON ERROR GOTO 40", "ZB"])]),
      ["BLIND/rewrote", "OK"])

# --- 2. neither geometry may be hard-coded (the K6 shape, made permanent) ----
for name, geo in (("VG8020 margin 2/width 37", VG8020),
                  ("zerobas margin 1/width 39", ZEROBAS)):
    pre = "Ok" if geo is VG8020 else "ZB"
    check(f"intact line is OK on {name}",
          verdicts([(0, "CLS"), (0, "PRINT 1")],
                   [(0, geo, [pre]), (0, geo, [pre, "PRINT 1", " 1", pre])]),
          ["BLIND/rewrote", "OK"])

# --- 3. a wrapped echo is still found ---------------------------------------
# 38 chars: longer than the reference's 37-column window, so its echo spans two
# rows. A row-at-a-time comparison reads <none> here (basic_probe_lnblank.py's
# left-margin incident); the stream reconstruction must not.
LONG = "A$=" + '"' + "0" * 33 + '"'
assert len(LONG) == 38, len(LONG)
for name, geo in (("VG8020", VG8020), ("zerobas", ZEROBAS)):
    check(f"wrapped {len(LONG)}-char echo is OK on {name}",
          verdicts([(0, "CLS"), (0, LONG)],
                   [(0, geo, ["Ok"]), (0, geo, ["Ok", LONG, "Ok"])]),
          ["BLIND/rewrote", "OK"])

# --- 4. the refusals -- a guard that cannot judge must SAY SO ----------------
# the first slot reads OK with no baseline at all -- finding the typed text is
# positive evidence and needs no growth proof; only the ABSENCE of it does.
check("a payload that clears its own echo is not MANGLED",
      verdicts([(0, "PRINT 1"), (0, "CLS")],
               [(0, ZEROBAS, ["ZBPRINT 1", " 1", "ZB"]), (0, ZEROBAS, ["ZB"])]),
      ["OK", "BLIND/rewrote"])

# 🔴 THE ROW THAT WOULD HAVE CAUGHT THE REGRESSION. `linemax` types a
# 254-character line and then LISTs it; the listing scrolls the `LIST` echo off
# the top while leaving the screen with MORE rows than before. A row-count
# growth test called that MANGLED and turned a 60/60 gate into exit 2. Content
# the screen HELD and no longer holds is what distinguishes a scroll from an
# append -- a row count cannot.
check("a payload whose output SCROLLS its echo away is not MANGLED",
      verdicts([(0, "POKE&HC100,7"), (0, "LIST")],
               [(0, ZEROBAS, ["ZB10 " + "?" * 249, "ZBPOKE&HC100,7", "ZB"]),
                (0, ZEROBAS, ["?" * 249, "?" * 249, "?" * 249, "ZB"])]),
      ["OK", "BLIND/rewrote"])

# 🔴 THE 59-FIRE STORM. `missing` types `WIDTH 40:CLS:PRINT "AB";CHR$(35)`: the
# CLS wipes the echo and the PRINT puts `AB#` up. Nothing was "lost" -- the
# previous screen held only `Ok` and the reference's permanent function-key row,
# and a clear brings both straight back -- so a lost-content test cannot see it.
# What is missing is any TRUNCATED ECHO: no suffix of the typed line is on screen.
FURNITURE = "color   auto    goto    list    run"
check("a payload that clears THEN prints is not MANGLED",
      verdicts([(0, "CLS"), (0, 'WIDTH 40:CLS:PRINT "AB";CHR$(35)')],
               [(0, VG8020, ["Ok", FURNITURE]),
                (0, VG8020, ["AB#", "Ok", FURNITURE])]),
      ["BLIND/rewrote", "BLIND/noecho"])

# the same shape with a payload that IS just a clear (`width` case 0)
check("a payload that is only CLS is not MANGLED",
      verdicts([(0, "SCREEN 0:WIDTH 40"), (0, "CLS")],
               [(0, VG8020, ["Ok", FURNITURE]), (0, VG8020, ["Ok", FURNITURE])]),
      ["BLIND/rewrote", "BLIND/noecho"])

# and the GREEN control for both: the same screens, but with a truncated echo
# on them -- the suffix is what separates a wiped echo from a swallowed head.
check("a truncated echo on the same screen IS MANGLED",
      verdicts([(0, "CLS"), (0, "PRINT CHR$(35)")],
               [(0, VG8020, ["Ok", FURNITURE]),
                (0, VG8020, ["Ok", "NT CHR$(35)", "Syntax error", FURNITURE])]),
      ["BLIND/rewrote", "MANGLED"])

# 🔴 CAUGHT BY THE ZERO-RED CONTROL, NOT BY INSPECTION. `lnblank` types
# `2\t0 REMX`; the ROM renders the tab as blanks, so the typed text is never a
# substring of the screen while ` REMX` is -- and it fired on the REFERENCE,
# which mis-delivers nothing. A payload the screen cannot spell back is refused,
# and the baseline SURVIVES, so the following slot is judged normally.
check("a payload with a control character is refused",
      verdicts([(0, "CLS"), (0, "2\t0 REMX"), (0, "PRINT 1")],
               [(0, ZEROBAS, ["ZB"]), (0, ZEROBAS, ["ZB2      0 REMX", "ZB"]),
                (0, ZEROBAS, ["ZB2      0 REMX", "ZBPRINT 1", " 1", "ZB"])]),
      ["BLIND/rewrote", "BLIND/unprintable", "OK"])

check("SCRMOD != 0 is BLIND, not MANGLED",
      verdicts([(0, "CLS"), (0, "PRINT 1")],
               [(0, ZEROBAS, ["ZB"]), (2, ZEROBAS, ["garbage"])]),
      ["BLIND/rewrote", "BLIND/mode"])

# a blind slot destroys the BASELINE, so the NEXT slot has nothing to compare to
check("the slot after a blind slot is blind too",
      verdicts([(0, "CLS"), (0, "PRINT 1"), (0, "PRINT 2")],
               [(0, ZEROBAS, ["ZB"]), (2, ZEROBAS, ["garbage"]),
                (0, ZEROBAS, ["ZBxxxxx", "ZB"])]),
      ["BLIND/rewrote", "BLIND/mode", "BLIND/rewrote"])

check("a missing dump is NODUMP", verdicts([(0, "PRINT 1")], [None]), ["NODUMP"])

check("a blank screen is not MANGLED",
      verdicts([(0, "CLS"), (0, "PRINT 1")],
               [(0, ZEROBAS, ["ZB"]), (0, ZEROBAS, [])]),
      ["BLIND/rewrote", "BLIND/rewrote"])

# --- 5. mis_echoed reports only MANGLED, and names the case -----------------
e = {0: (0, 39, screen(["ZB"], **ZEROBAS)),
     1: (0, 39, screen(["ZBN ERROR GOTO 40", "Syntax error", "ZB"], **ZEROBAS))}
check("mis_echoed names (case, slot, typed)",
      omsx_repl.mis_echoed(omsx_repl.echo_verdicts(
          [(7, "CLS"), (7, "10 ON ERROR GOTO 40")], e)),
      [(7, 1, "10 ON ERROR GOTO 40",
        ["ZBN ERROR GOTO 40", "Syntax error", "ZB"])])

# --- 6. the guard is switchable, and OFF must emit nothing ------------------
os.environ["ZEROBAS_ECHOGUARD"] = "off"
slots_out = []
tcl = omsx_repl._tcl("/tmp/unused", [("direct", ["PRINT 1"])], 8.0, 2.5, 2.5,
                     ("CLS",), "screen", None, 12.0, (), slots_out)
check("ZEROBAS_ECHOGUARD=off emits no __echo proc", "__echo" in tcl, False)
check("ZEROBAS_ECHOGUARD=off records no slots", slots_out, [])
del os.environ["ZEROBAS_ECHOGUARD"]
omsx_repl.echo_guard_on._said = False
slots_out = []
tcl = omsx_repl._tcl("/tmp/unused", [("direct", ["PRINT 1"])], 8.0, 2.5, 2.5,
                     ("CLS",), "screen", None, 12.0, (), slots_out)
check("armed, it emits the proc", "proc __echo" in tcl, True)
check("armed, it records every injection slot", slots_out,
      [(0, "CLS"), (0, "PRINT 1")])

print()
if fails:
    print(f"{len(fails)} FAILED:")
    for f in fails:
        print("  " + f)
    sys.exit(1)
print("ALL PASS")
