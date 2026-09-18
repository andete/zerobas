#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-SEQIO: what does ONE BYTE of sequential file input cost, on the reference
and on zerobas?  Step 7 of the eviction order (spec-diskcode-eviction.md §6.2).

WHY IT GATES CODE.  §6.3 rules out "cursors out, loops left behind" because it
would cost one inter-slot call PER BYTE.  But that is only a defect if the
reference does not already pay something comparable.  The answer decides three
things: whether `PRINT#`'s per-byte case (step 12) is ON-PAR or a regression,
whether the `INPUT#`/`INPUT$` loop duplication (step 11) is required or is bytes
spent for nothing, and how much headroom the whole eviction has.

=== THE FREQUENCY TRAP, HANDLED BEFORE IT BITES ===

`TIME` counts VDP interrupts: **60 Hz on the Japanese National CF-3300, 50 Hz on
our C-BIOS MSX1 EU repack**.  Comparing raw jiffies across the two machines is
wrong by 20% in the direction that flatters us.  So the headline figure is
NORMALISED: every machine also times a calibration loop, and the per-byte cost
is reported in CALIBRATION UNITS -- (io - loop) / bytes / (cal / 1000) -- in
which the tick rate cancels exactly.  Absolute milliseconds are printed too, but
they carry the Hz assumption on their face and the normalised column does not.

=== THE THREE CASES, PER MACHINE ===

  cal   FOR I=1 TO 1000:NEXT              machine speed, nothing else
  loop  FOR I=1 TO 512:A$=B$:NEXT         the same loop and assignment, no I/O
  io    FOR I=1 TO 512:A$=INPUT$(1,#1):NEXT   the same loop WITH a byte read

`io - loop` is the file-input cost with interpreter overhead subtracted, which
is the quantity the design question is about.

⚠️ `loop` IS AN APPROXIMATION AND IS LABELLED AS ONE.  `A$=B$` is a string
assignment, `A$=INPUT$(1,#1)` is a string-valued function call plus the read, so
the subtraction leaves a little function-call overhead inside the "I/O" figure.
That biases the answer AGAINST the per-byte-crossing hypothesis (it makes file
I/O look dearer than it is), so a result that says "the reference does NOT cross
per byte" is not an artifact of this control.  A result the other way would be.

⚠️ IT REFUSES RATHER THAN PRINTING A PLAUSIBLE TABLE:
  * the marker is built at run time (CHR$(64)+CHR$(75) echoes as its source and
    prints as "@K"), so a case that never ran cannot pass by matching the screen
    ECHO of the line that prints it -- the trap D-FATBUF hit
    [[a-probes-fence-is-also-in-the-source-it-echoes]];
  * every case must report a POSITIVE elapsed time, and `io` must exceed `loop`
    -- a file read that costs nothing did not happen;
  * `cal` must be positive on every machine, or the normalisation divides by
    zero and every normalised figure would be meaningless.
"""
import os, shutil, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl                                             # noqa: E402
import fatbuf_probe as FB                                    # noqa: E402

# (machine, boot, step, reset, jiffy Hz). The Hz is an ASSUMPTION from the
# machine's region and is used ONLY for the absolute-ms column; the normalised
# column does not depend on it.
SIDES = [
    # 🔴 `CLS` IS LOAD-BEARING, NOT TIDINESS. Batched cases share one screen, so
    # without a clear the PREVIOUS case's marker is still on it and the parser
    # reads a stale number as this case's answer. That is exactly how zb first
    # reported 249 jiffies for all three cases: `SCREEN 0` clears, so the CF-3300
    # side happened to be right while zb -- whose reset had no clear -- returned
    # case 1's figure three times. The `io > loop` control is what caught it.
    ("cf3300", "National_CF-3300", 14.0, ("", "SCREEN 0", "CLOSE", "NEW", "CLS"), 60),
    ("zb", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"),
     8.0, ("CLOSE", "NEW", "CLS"), 50),
]

N_IO = 512          # bytes read one at a time
STEP = 12.0         # per-case run window: the io case is seconds long
CAP_GAP = 8.0       # settle before the screen is scraped
N_CAL = 1000        # calibration loop iterations
MARK_SRC = "CHR$(64)+CHR$(75)"
MARK = "@K"

# 🔴 STORED MODE, NOT DIRECT, AND THE FIRST CUT GOT THIS WRONG. With `T=TIME` and
# the `PRINT` as separate TYPED lines, the interval measured is the probe's own
# injection delay: every case came back ~541 jiffies == two `step`s of 4.5 s, and
# `cal`/`loop`/`io` were indistinguishable. A stored program runs its lines with
# no gaps, so the clock spans the loop and nothing else. The in-tree precedent is
# scratchpad/bfperf_time.py (D-ARCMASK), which times the same way.
# Each numbered line is "10 " + body, so a body statement may be at most 36 chars.
BODY = {
    "cal": ['T=TIME',
            'FOR I=1 TO %d:NEXT' % N_CAL,
            'U=TIME',
            'PRINT %s;U-T' % MARK_SRC],
    "loop": ['B$="X":T=TIME',
             'FOR I=1 TO %d:A$=B$:NEXT' % N_IO,
             'U=TIME',
             'PRINT %s;U-T' % MARK_SRC],
    "io": ['OPEN"RND.BIN"FOR INPUT AS#1',
           'T=TIME',
           'FOR I=1 TO %d:A$=INPUT$(1,#1):NEXT' % N_IO,
           'U=TIME',
           'PRINT %s;U-T' % MARK_SRC,
           'CLOSE'],
}
ORDER = ["cal", "loop", "io"]


def elapsed(cap):
    """The number printed after the run-time marker, or None.

    ⚠️ THE **LAST** MARKER ON THE SCREEN, NOT THE FIRST. Belt-and-braces beside
    the `CLS` above: if a previous case's line ever survives, this case's own
    output is the later one, so reading the last match cannot return a stale
    figure. Reading the first one did."""
    if not cap:
        return None
    got = None
    for j in range(0, len(cap), 40):
        row = cap[j:j + 40]
        if MARK in row:
            tok = row.split(MARK, 1)[1].strip().split()
            if tok:
                try:
                    got = int(tok[0])
                except ValueError:
                    pass
    return got


def main():
    tmpd = tempfile.mkdtemp(prefix="seqio_")
    dsk = os.path.join(tmpd, "rnd.dsk")
    g = FB.build_disk(dsk, FB.prng(FB.FILESZ))
    print("disk: RND.BIN %d B, chain %s, %d filler files"
          % (FB.FILESZ, g["chain"], g["fillers"]))

    rows = {}
    for tag, machine, boot, reset, hz in SIDES:
        cases = [("stored", BODY[k]) for k in ORDER]
        for k in ORDER:
            for ln in BODY[k]:
                if len(ln) > 36:
                    sys.exit("REFUSING: %s/%s body line %r is %d chars; a stored "
                             "line is '10 ' + body and must fit 39"
                             % (tag, k, ln, len(ln)))
        print("  driving %s (%s) ..." % (tag, machine), flush=True)
        # ⏱️ THE `io` CASE NEEDS ROOM TO FINISH. At the `loop` figure (~3 ms per
        # iteration) 512 reads take several seconds, and the default 2.5 s
        # `step`/`cap_gap` captured the screen mid-RUN: the listing and `RUN`
        # were there, the output was not. A case still running reads exactly
        # like a case that produced nothing.
        caps = omsx_repl.run_cases(machine, cases, batch=True, reset=reset,
                                   boot=boot, step=STEP, cap_gap=CAP_GAP,
                                   diska=dsk, capture="screen")
        vals = {}
        for i, k in enumerate(ORDER):
            v = elapsed(caps[i])
            vals[k] = v
            print("      %-5s %s" % (k, "%d jiffies" % v if v is not None
                                     else "<NO %s WITNESS ON SCREEN>" % MARK))
            if v is None:
                t = caps[i] or ""
                for j in range(0, len(t), 40):
                    if t[j:j + 40].strip():
                        print("        | %s" % t[j:j + 40].rstrip())
                sys.exit("REFUSING: %s/%s printed no %r witness -- the case did "
                         "not run, and a timing read out of it would be noise."
                         % (tag, k, MARK))
        rows[tag] = dict(vals, hz=hz, machine=machine)

    # --- the controls ---------------------------------------------------------
    for tag, v in rows.items():
        if v["cal"] <= 0:
            sys.exit("REFUSING: %s calibration loop measured %d jiffies. The "
                     "normalisation divides by it, so every normalised figure "
                     "would be meaningless." % (tag, v["cal"]))
        if v["io"] <= v["loop"]:
            sys.exit("REFUSING: %s io=%d jiffies is not greater than loop=%d. A "
                     "file read that costs nothing did not happen."
                     % (tag, v["io"], v["loop"]))

    # --- the readout ----------------------------------------------------------
    print()
    print("| machine | cal (%d it) | loop (%d it) | io (%d B) | io-loop | "
          "per byte, cal units | per byte, ms |" % (N_CAL, N_IO, N_IO))
    print("|---|---|---|---|---|---|---|")
    norm = {}
    for tag, _m, _b, _r, _hz in SIDES:
        v = rows[tag]
        d = v["io"] - v["loop"]
        cal_per_it = v["cal"] / float(N_CAL)
        units = (d / float(N_IO)) / cal_per_it
        ms = (d / float(N_IO)) * (1000.0 / v["hz"])
        norm[tag] = (units, ms)
        print("| %s (%d Hz) | %d | %d | %d | %d | %.2f | %.3f |"
              % (tag, v["hz"], v["cal"], v["loop"], v["io"], d, units, ms))

    cf_u, cf_ms = norm["cf3300"]
    zb_u, zb_ms = norm["zb"]
    print()
    print("=" * 72)
    print("THE QUESTION: does the reference already pay a per-byte price big")
    print("enough that an INTER-SLOT CALL PER BYTE would be on-par?")
    print("D-XSLOTPRICE measured OUR crossing at 0.156 ms (main->disk).")
    print()
    print("reference per byte : %.3f ms   (%.2f calibration units)" % (cf_ms, cf_u))
    print("zerobas   per byte : %.3f ms   (%.2f calibration units)" % (zb_ms, zb_u))
    print("zerobas / reference: %.2fx  (normalised, tick-rate independent)"
          % (zb_u / cf_u if cf_u else float("nan")))
    print()
    if cf_ms >= 0.156:
        print("-> the reference's own per-byte cost is AT OR ABOVE one crossing,")
        print("   so a per-byte inter-slot call is within its envelope.")
        print()
        print("   🔴 THIS SETTLES STEPS 11 AND 12 ONLY, NOT STEP 9.")
        print("   INPUT#/INPUT$/PRINT# pay a whole BASIC statement's worth of")
        print("   interpretation per byte, which is what the crossing would hide")
        print("   behind -- that is the case measured here. The tokenised LOAD")
        print("   loop (step 9) runs INSIDE the ROM with no interpreter overhead")
        print("   per byte, so a crossing there is pure addition against nothing.")
        print("   Its cost is NOT measured by this probe and must not be inferred")
        print("   from it.")
    else:
        print("-> the reference's per-byte cost is BELOW one crossing (%.3f ms"
              % cf_ms)
        print("   against 0.156 ms), so adding a crossing per byte would put us")
        print("   outside its envelope. §6.3 stands: MOVE THE LOOP TO THE CURSOR.")
        print("   Steps 11 and 12 keep their loop duplication.")
    hdr = zb_ms + 0.156
    print()
    print("if a crossing were added to zerobas' current path: %.3f ms/byte, "
          "%.2fx the reference" % (hdr, hdr / cf_ms if cf_ms else float("nan")))
    print("=" * 72)
    print()
    print("⚠️  `loop` subtracts a string ASSIGNMENT from a string-valued FUNCTION")
    print("    call, so a little call overhead stays inside the I/O figure. That")
    print("    bias makes file I/O look DEARER, i.e. it favours the per-byte-")
    print("    crossing hypothesis -- so a 'below one crossing' verdict is not an")
    print("    artifact of the control, though the opposite verdict could be.")
    print("⚠️  Absolute ms carry the Hz assumption printed in the table; the")
    print("    calibration-unit column and the zb/reference ratio do not.")
    shutil.rmtree(tmpd, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
