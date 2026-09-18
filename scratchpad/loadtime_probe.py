#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LOADTIME: what does a TOKENISED `LOAD` cost? ⛔ THIS METHOD CANNOT ANSWER IT.

✅ **ANSWERED THE SAME DAY BY `scratchpad/loadrun_probe.py` (D-LOADRUN)**, which
built the method this header describes and measured **0.2178 ms/byte on zerobas
and 0.0376 on the CF-3300** (spec-diskcode-eviction.md §6.2c). Read that one for
the figure; read this one for why the obvious instrument does not work.

🔴 STATUS 2026-09-18: **INCOMPLETE, AND KEPT FOR ITS DIAGNOSIS.** The disk
builder and the tokenised-program generator below are correct and reusable; the
TIMING METHOD is not, and this header says why so the next attempt does not
rediscover it.

THE FLAW. The two clock reads sit either side of the LOAD in SEPARATE injected
lines, so the second one fires on the HARNESS'S TIMETABLE rather than when the
work finishes. Measured on the CF-3300:

    step=14 s   ctl 1678 jiffies   load 1606    both == the 28 s injection gap
    step= 3 s   ctl  360 jiffies   load  307    both == the 6 s injection gap

In every configuration BOTH cases measure the gap and the load vanishes inside
it; the small differences are jitter, and NEGATIVE, which is what the `load >
ctl` control caught. Shortening `step` below the load does not work either: a
7.6 KB LOAD completes in UNDER 3 SECONDS, which is already below the step the
injector needs (at 3 s the calibration case broke -- its 1000-iteration loop was
still running when the capture fired).

🟢 WHAT IT DID ESTABLISH, as an upper bound: **a 7603-byte tokenised LOAD takes
under 3 s on the CF-3300** -- under ~0.39 ms/byte. ✅ The real figure, measured
by D-LOADRUN, is **0.0376 ms/byte** there, so this bound was honest and an order
of magnitude loose -- which is what an upper bound from a failed instrument is
worth, and why it was not allowed to decide step 9.

➡️ THE METHOD THAT WORKED, now built as `scratchpad/loadrun_probe.py`:
`LOAD"P.BAS",R`, with the marker as the loaded program's FIRST line. The loaded
program runs the instant the load completes, so the second clock read is
triggered by the WORK and no injection gap intervenes.

🔴 AND THE OTHER HALF WAS A SENTENCE IN THIS FILE, BELOW, WHICH IS WRONG:
*"`LOAD"x",R` does not help -- it clears variables too."* It clears VARIABLES.
**`TIME` is a system cell, not a BASIC variable**, so `TIME=0` before the load
survives into the loaded program and is the whole clock. D-LOADRUN proves it
rather than assuming it, with a control that runs a delay loop before the load
and checks the two costs COMPOSE.

🔴 A THIRD THING THIS FILE GOT WRONG, harmlessly: the REM generator below emits
`$8F` + text, but the machine emits **`$8F $20` + text** -- it keeps the space
after `REM`. Both load. D-LOADRUN takes its tokenised lines from a `SAVE` the
machine performs, which is how the difference surfaced at all.

--- the original intent follows ---

Step 9 of the eviction order (spec-diskcode-eviction.md §6.2), and the case

Step 9 of the eviction order (spec-diskcode-eviction.md §6.2), and the case
§6.2a deliberately does NOT cover.  D-SEQIO measured the BASIC-visible byte
verbs -- `INPUT#`/`INPUT$`/`PRINT#` -- where each byte already carries a whole
BASIC statement's worth of interpretation, so an added inter-slot crossing
disappears into it (0.20x the reference).  **The tokenised LOAD loop is the
opposite**: `dpl_*` runs INSIDE the ROM with no interpreter overhead per byte, so
a crossing there is pure addition against nothing.  §6.3 therefore still demands
loop-to-the-cursor for this path -- on an assumption nobody has measured.

WHY THE TIMING IS NOT SELF-REPORTING.  `LOAD` REPLACES THE PROGRAM, so the usual
`T=TIME ... PRINT TIME-T` cannot survive it: the code holding T is gone before it
could print.  (`LOAD"x",R` does not help -- it clears variables too.  🔴 FALSE,
see the correction at the top: it clears VARIABLES, and `TIME` is not one.)  So the
clock is read on BOTH SIDES OF THE LOAD by two SEPARATE injected lines, and the
probe's own injection gap is removed by a control that does the same thing with
no LOAD in between:

    ctl    ?@;TIME  /  (nothing)      /  ?@;TIME      -> the injection gap alone
    load   ?@;TIME  /  LOAD"P.BAS"    /  ?@;TIME      -> gap + the load

    LOAD cost = delta(load) - delta(ctl)

The gap is `step` seconds and identical in both cases because the harness drives
them identically, so it subtracts exactly.  JIFFY resolution is 1/60 s (CF-3300)
or 1/50 s (our EU repack), and the frequency is handled the way D-SEQIO handles
it: a calibration loop per machine, so the headline is tick-rate independent.

THE SUBJECT FILE IS GENERATED, NOT SAVED.  A tokenised MSX BASIC program is
[$FF][link:2][lineno:2][tokens][$00]... [$00$00], and a REM line is simply token
$8F followed by literal text -- so a large program of REM lines can be built in
Python without tokenising anything non-trivial and without spending emulator time
SAVEing one.  Its size is what makes the load measurable.

⚠️ CONTROLS, so a pass cannot be vacuous:
  * both markers must appear on screen in BOTH cases, or a case did not run;
  * delta(load) must EXCEED delta(ctl) -- a load that costs nothing did not
    happen;
  * the loaded program must be VISIBLE afterwards (its line count read back with
    a marker), or `LOAD` failed and the delta is measuring a failed open.
"""
import os, shutil, struct, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl                                              # noqa: E402
import fatbuf_probe as FB                                     # noqa: E402

REM = 0x8F
TXTTAB = 0x8001
PROG_LINES = 380          # -> ~8 KB of tokenised program
REM_TEXT = b"X" * 14
N_CAL = 1000

SIDES = [
    ("cf3300", "National_CF-3300", 14.0, ("", "SCREEN 0", "CLOSE", "NEW", "CLS"), 60),
    ("zb", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"),
     8.0, ("CLOSE", "NEW", "CLS"), 50),
]
# 🔴 STEP MUST BE SHORTER THAN THE LOAD, AND THE FIRST CUT HAD IT BACKWARDS.
# With step=14 s the two clock reads were 28 s apart ON A SCHEDULE, and the load
# finished inside that window -- so BOTH cases measured the gap and nothing else
# (ctl 1678 jiffies, load 1606: the difference was jitter, and NEGATIVE). The
# second read has to be triggered by the WORK, not by the timetable. With a short
# step the second PRINT is already sitting in the key buffer when LOAD starts, so
# it executes the instant LOAD returns -- and the harness's own deferral logic
# (D-LATCH2: never write into a buffer the machine is still consuming) is exactly
# what makes that safe.
STEP, CAP_GAP = 14.0, 8.0
MARK_SRC, MARK = "CHR$(64)+CHR$(75)", "@K"


def tokenised_program(nlines):
    """A valid tokenised MSX BASIC program of `nlines` REM lines."""
    out = bytearray(b"\xFF")
    addr = TXTTAB
    body = []
    for i in range(nlines):
        line = bytes([REM]) + REM_TEXT + b"\x00"
        body.append((10 * (i + 1), line))
    for lineno, line in body:
        nxt = addr + 4 + len(line)
        out += struct.pack("<HH", nxt, lineno) + line
        addr = nxt
    out += b"\x00\x00"
    return bytes(out)


def build_disk(path, prog):
    shutil.copyfile(FB.SRC_DSK, path)
    d = bytearray(open(path, "rb").read())
    bps = struct.unpack("<H", d[11:13])[0]
    spc, rsv = d[13], struct.unpack("<H", d[14:16])[0]
    nf = d[16]
    nroot = struct.unpack("<H", d[17:19])[0]
    spf = struct.unpack("<H", d[22:24])[0]
    csz = bps * spc
    root_sec = rsv + nf * spf
    data_sec = root_sec + (nroot * 32 + bps - 1) // bps
    fat = bytearray(d[rsv * bps: rsv * bps + spf * bps])
    need = (len(prog) + csz - 1) // csz
    free = [c for c in range(2, 300) if FB.fat12_get(fat, c) == 0][:need]
    if len(free) != need:
        sys.exit("REFUSING: need %d free clusters, found %d" % (need, len(free)))
    for i, c in enumerate(free):
        FB.fat12_set(fat, c, 0xFFF if i == need - 1 else free[i + 1])
        off = (data_sec + (c - 2) * spc) * bps
        d[off:off + csz] = prog[i * csz:(i + 1) * csz].ljust(csz, b"\x00")
    for i in range(nf):
        d[(rsv + i * spf) * bps:(rsv + i * spf) * bps + spf * bps] = fat
    ent = (b"P       BAS" + bytes([0x20]) + b"\x00" * 10 +
           struct.pack("<HHHI", 0x6000, 0x5921, free[0], len(prog)))
    assert len(ent) == 32
    for i in range(nroot):
        e = root_sec * bps + i * 32
        if d[e] in (0x00, 0xE5):
            d[e:e + 32] = ent
            break
    else:
        sys.exit("REFUSING: root directory full")
    if len(d) != os.path.getsize(FB.SRC_DSK):
        sys.exit("REFUSING: the built image changed size")
    open(path, "wb").write(bytes(d))
    return len(prog)


def marks(cap):
    """Every number printed after a run-time marker, in screen order."""
    out = []
    if not cap:
        return out
    for j in range(0, len(cap), 40):
        row = cap[j:j + 40]
        if MARK in row:
            tok = row.split(MARK, 1)[1].strip().split()
            if tok:
                try:
                    out.append(int(tok[0]))
                except ValueError:
                    pass
    return out


def main():
    tmpd = tempfile.mkdtemp(prefix="loadtime_")
    dsk = os.path.join(tmpd, "load.dsk")
    prog = tokenised_program(PROG_LINES)
    size = build_disk(dsk, prog)
    print("subject: P.BAS, %d tokenised lines, %d bytes" % (PROG_LINES, size))

    CASES = {
        "cal":  ['T=TIME', 'FOR I=1 TO %d:NEXT' % N_CAL, 'U=TIME',
                 'PRINT %s;U-T' % MARK_SRC],
        "ctl":  ['PRINT %s;TIME' % MARK_SRC, 'A=1', 'PRINT %s;TIME' % MARK_SRC],
        "load": ['PRINT %s;TIME' % MARK_SRC, 'LOAD"P.BAS"',
                 'PRINT %s;TIME' % MARK_SRC],
    }
    ORDER = ["cal", "ctl", "load"]
    rows = {}
    for tag, machine, boot, reset, hz in SIDES:
        for k in ORDER:
            for ln in CASES[k]:
                lim = 36 if k == "cal" else 39
                if len(ln) > lim:
                    sys.exit("REFUSING: %s/%s line %r is %d chars (limit %d)"
                             % (tag, k, ln, len(ln), lim))
        print("  driving %s ..." % machine, flush=True)
        # 🔴 `load` AND `ctl` ARE **DIRECT**, NOT STORED, AND THE FIRST CUT GOT
        # THIS WRONG IN THE WAY THIS PROBE'S OWN DOCSTRING WARNS ABOUT. As a
        # stored program, `20 LOAD"P.BAS"` REPLACES the program while it is
        # running, so line 30 -- the second clock read -- ceased to exist before
        # it could execute: one marker on screen, and the marker-count control
        # caught it. In DIRECT mode there is no program for LOAD to destroy, and
        # the two clock reads are separate injections either side of it.
        # `cal` stays STORED because a timed loop needs a program.
        modes = {"cal": "stored"}
        caps = omsx_repl.run_cases(machine,
                                   [(modes.get(k, "direct"), CASES[k]) for k in ORDER],
                                   batch=True, reset=reset, boot=boot, step=STEP,
                                   cap_gap=CAP_GAP, diska=dsk, capture="screen")
        v = {}
        for i, k in enumerate(ORDER):
            m = marks(caps[i])
            need = 1 if k == "cal" else 2
            if len(m) < need:
                t = caps[i] or ""
                for j in range(0, len(t), 40):
                    if t[j:j + 40].strip():
                        print("     | %s" % t[j:j + 40].rstrip())
                sys.exit("REFUSING: %s/%s printed %d marker(s), needs %d -- the "
                         "case did not run as written" % (tag, k, len(m), need))
            v[k] = m[0] if k == "cal" else m[1] - m[0]
            print("      %-5s %d jiffies" % (k, v[k]))
        rows[tag] = dict(v, hz=hz)

    for tag in rows:
        if rows[tag]["load"] <= rows[tag]["ctl"]:
            sys.exit("REFUSING: %s load=%d is not greater than ctl=%d -- the LOAD "
                     "cost nothing, so it did not happen"
                     % (tag, rows[tag]["load"], rows[tag]["ctl"]))
        if rows[tag]["cal"] <= 0:
            sys.exit("REFUSING: %s calibration measured %d" % (tag, rows[tag]["cal"]))

    print()
    print("| machine | cal | ctl (gap) | load (gap+LOAD) | LOAD | per byte, cal units | per byte, ms |")
    print("|---|---|---|---|---|---|---|")
    norm = {}
    for tag, _m, _b, _r, hz in SIDES:
        r = rows[tag]
        d = r["load"] - r["ctl"]
        cal_it = r["cal"] / float(N_CAL)
        units = (d / float(size)) / cal_it
        ms = (d / float(size)) * (1000.0 / hz)
        norm[tag] = (units, ms, d)
        print("| %s (%d Hz) | %d | %d | %d | **%d** | %.4f | %.4f |"
              % (tag, hz, r["cal"], r["ctl"], r["load"], d, units, ms))

    cu, cms, cd = norm["cf3300"]
    zu, zms, zd = norm["zb"]
    print()
    print("=" * 72)
    print("THE QUESTION: the tokenised LOAD loop runs INSIDE the ROM, with no")
    print("interpreter overhead per byte for a crossing to hide behind. Would one")
    print("inter-slot call per byte (0.156 ms, D-XSLOTPRICE) be affordable here?")
    print()
    print("reference : %.4f ms/byte  (%.4f calibration units)" % (cms, cu))
    print("zerobas   : %.4f ms/byte  (%.4f calibration units)" % (zms, zu))
    print("zb/ref    : %.2fx  (normalised, tick-rate independent)"
          % (zu / cu if cu else float("nan")))
    print()
    hdr = zms + 0.156
    print("with a crossing PER BYTE added to our path: %.4f ms/byte, %.2fx the"
          % (hdr, hdr / cms if cms else float("nan")))
    print("reference -- i.e. a %d KB LOAD would take %.1f s here against the"
          % (size // 1024, hdr * size / 1000.0))
    print("reference's %.1f s." % (cms * size / 1000.0))
    print()
    if hdr <= cms:
        print("-> even WITH a per-byte crossing we stay inside the reference's")
        print("   envelope. §6.3's loop-to-the-cursor requirement does not bind")
        print("   step 9 either, and dpl_* may take a trampoline.")
    else:
        print("-> a per-byte crossing puts this path OUTSIDE the reference's")
        print("   envelope. §6.3 STANDS for step 9: the LOAD loop must move to")
        print("   its cursor, not call across the slot per byte.")
    print("=" * 72)
    print()
    print("⚠️  `ctl` subtracts the probe's own injection gap, which is identical")
    print("    in both cases because the harness drives them identically. It does")
    print("    NOT subtract LOAD's fixed costs (open, directory search, close) --")
    print("    those stay inside the per-byte figure and INFLATE it, so a verdict")
    print("    of 'affordable' is not an artifact of the control.")
    shutil.rmtree(tmpd, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
