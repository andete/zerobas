#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LINEMAX -- HOW LONG A LINE EACH MACHINE ACCEPTS, and what it does past that.

WHY THIS EXISTS
===============
`LINEMAX equ 96` (basic/sysvars.inc:760) against the reference's ~250+ is a
measured divergence: docs/arrdim-c-vg8020-characterization.md §4 put zerobas's
last INTACT line at 95 characters and the VG-8020's at 250 (the `line` battery in
basic_probe_arrdim.py, which stopped there). Four `cap` rows in that probe were
filed under the WRONG CAUSE for a whole slice because the dimension cap masked
this one. This probe is the slice's own measurement.

WHAT THE arrdim `line` BATTERY COULD NOT ANSWER
===============================================
It reads a PROXY -- `20` + padding + `A=7`, so an intact line assigns 7 and a
truncated one leaves A at 0. That is a yes/no per length. It cannot say:

  * the reference's EXACT ceiling (it stopped at 250, three short of the input
    line the arrdim probe's own apparatus guard assumes);
  * WHAT truncation means -- are the extra characters DROPPED and the rest of the
    line kept, or is the whole line REFUSED? A proxy at the line's END reads 0 for
    both, and the disposition a faithful implementation must copy is exactly that
    difference;
  * whether the TOKENISED line has a limit of its own that bites first.

THE INSTRUMENT: THE STORED LINE'S OWN BYTES
===========================================
Every battery here reads `("stored_line", TXTTAB)` -- omsx_repl dereferences the
BASIC text base and returns the first stored line's exact bytes (link, line
number, tokens, terminator), or `""` when the program is EMPTY, i.e. the line was
rejected on entry. So "dropped the tail" and "refused the line" are different
readings, not the same 0, and a truncation point is COUNTED rather than inferred.

`REM` is what makes it 1:1. REM keeps the rest of its line VERBATIM on both
machines (basic/tokenise.inc:99/181; standard MS-BASIC), so `20 REM` + N-6 filler
characters stores exactly one token plus the surviving filler: count the filler
bytes and you have the machine's input-line ceiling as a NUMBER, with no proxy
variable and no error-message wording in the way.

⚠️ THIS PROBE DOES NOT INHERIT arrdim's `ECHO_MAX` GUARD, and that is a decision,
not an oversight. That guard exists because an echo-anchored readout cannot match
a line whose echo WRAPS (the fault that made eleven D-CLP rows read `<none>` on
BOTH machines and score PASS). Nothing here anchors on an echo -- the readout is
a memory capture -- so the guard has nothing to protect. The `dir` battery is the
one exception: it IS echo-anchored, so its rows keep the limit explicitly.

⚠️ NOR does it inherit the 255-character cap arrdim puts on a non-anchor line.
Finding out what happens PAST that cap is half the point, so the `rem` battery
deliberately runs to 300. That means a `rem` row past ~255 cannot distinguish
"the machine refused it" from "the harness could not deliver it": the KEYBUF
injection path is itself under test there. `rem-40` is the two-sided control (a
length no machine truncates), and `rem-100` is the CALIBRATION row -- zerobas is
predicted to store exactly 89 filler bytes there (95 characters minus `20 REM`).
A run where that row reads anything else is measuring the apparatus, not the
machine, and no other row in it may be read as a finding.

THE THIRD CONSUMER
==================
`ascii_read_lines` (basic/files.asm:1461) bounds an ASCII-LOADed line with the
IDENTICAL idiom and the same constant, and neither battery above touches it: both
type at the prompt. The `cas` battery carries a long line in on a cassette ASCII
tape instead, which is the only ASCII-program path the VG-8020 can be given
without a disk.
"""
from __future__ import annotations
import argparse, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import omsx_repl  # noqa: E402

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

# ⚠️ THE APPARATUS HAD THE ANSWER HARD-CODED, AND IT WAS A GUESS.
# omsx_repl.MAX_BUF is 250, commented "MSX line-input buffer (BUF/LINBUF) holds
# ~255 chars incl CR" -- a round number nobody measured, which REFUSES to inject a
# longer line. The arrdim `line` battery's top row is 250. So
# docs/arrdim-c-vg8020-characterization.md §4's "the reference's is 250" is the
# HARNESS's ceiling reported as the MACHINE's: every length past it was
# unreachable, not accepted-and-tested. The reference's real ceiling has never
# been measured, and finding it is this probe's first job -- so the cap is lifted
# here, deliberately and locally, to a value above the longest row below. Once the
# machine's own number is measured, omsx_repl's constant should be set to it and
# its comment stop guessing.
omsx_repl.MAX_BUF = 320

TXTTAB = 0xF676          # sysvar: pointer to the BASIC text base (both machines)
REM_TOKEN = 0x8F         # basic/sysvars.inc:242 (MSX2 TH Table 2.20)

# The echo-anchored `dir` battery's own limit -- the reference's boot LINLEN, the
# tighter of the two machines (docs/width-vg8020-characterization.md). Only the
# `dir` battery reads an echo; see the docstring on why the other batteries do
# not carry this guard.
ECHO_MAX = 37

FILLER = "X"             # a filler char that is not a keyword and starts no literal


# --- the `rem` battery: WHERE THE INPUT LINE ENDS, COUNTED --------------------
# `20 REM` + (n-6) filler. The stored line is [link:2][lineno:2][$8F][filler][00],
# so the surviving filler count IS the machine's ceiling minus 6 -- a number, not a
# yes/no. An EMPTY program means the line was refused outright.
def _rem_case(n):
    assert n >= 8
    return (f"rem-{n}", "rem", ["20 REM" + FILLER * (n - 6)])


# 40 = the two-sided control. 90..100 brackets zerobas's predicted 95 (with
# rem-100 as the calibration row). 248..300 brackets the reference's, and runs
# PAST the 255 that arrdim's apparatus assumes -- the point being to find out.
CASES = [_rem_case(n) for n in
         (40, 90, 94, 95, 96, 97, 100, 200, 248, 250, 252, 253, 254, 255,
          256, 257, 260, 300)]


# --- the `tok` battery: DOES THE *CRUNCHED* LINE HAVE A LIMIT OF ITS OWN? -----
# ⚠️ THE CRUNCH EXPANDS. A double literal is DBL_TOKEN + 8 value bytes
# (basic/sysvars.inc:288, sub/tkfloat.asm tkf_double), so the two characters `0#`
# become NINE bytes -- 4.5x. zerobas's TOKBUF is 96 bytes ($E160..$E1BF, with
# ARYTAB/the error-trap block/ZTRAP/POOLSIZE/STRTAB directly above it) and the
# crunch writes there with NO bound anywhere in tokenise.inc, so eleven `0#`
# groups -- a TWENTY-FIVE character line -- is predicted to write past it.
#
# That prediction is what this battery exists to falsify or confirm, and it is
# INDEPENDENT of line length: if it holds, the buffer overruns today, at
# LINEMAX=96, and any LINEMAX rise makes it worse. The reference's own refusal
# point is the other half -- black-box, it is the only measurement of how big a
# crunch buffer a faithful implementation needs.
#
# Readout: the stored bytes. A machine that refuses stores nothing (""); one that
# accepts stores 9 bytes per group; one that overruns stores whatever its wreckage
# leaves behind.
#
# ⚠️ THE PAYLOAD CARRIES `A=`, AND THAT IS NOT COSMETIC. The first cut of this
# battery used `20 ` + the literals, and its two-sided control FAILED for a reason
# that had nothing to do with buffers: the reference read the line number as
# **200**, storing `#` verbatim and one literal fewer. Its line-number scan SKIPS
# THE BLANK and keeps accumulating digits, where zerobas stops at the space -- a
# real divergence of its own (filed separately; it is not this slice's), which
# here was purely a confound. A letter after the space stops the scan on both
# machines, so `A=` makes the two crunch the SAME source.
def _tok_case(k):
    return (f"tok-{k}", "tok", ["20 A=" + "0#" * k])


# k=5 (15 chars, ~47 crunched bytes) is the two-sided control -- comfortably inside
# every buffer involved. 11/12 bracket zerobas's predicted 96-byte overrun (9k+2 >
# 95). 34/35/36 bracket ~318 crunched bytes, and 45 is where zerobas's OWN input
# truncation pins its crunch output at its maximum (95 source characters = 45
# groups), i.e. the worst case a 96-byte TOKBUF has to survive TODAY. 124 runs the
# reference to the same place (254 characters).
CASES += [_tok_case(k) for k in (5, 10, 11, 12, 20, 30, 34, 35, 36, 40, 45, 124)]

# --- the `tokx` battery: WHAT THE MACHINE SAYS, at the same lengths -----------
# The `tok` battery reads the stored bytes, which is the right instrument for
# "what did the crunch produce" and the WRONG one for "what did the machine do
# about it": a machine that REFUSES the line and a machine that never reaches the
# capture at all read `""` and `None`, and only the first of those is a behaviour.
# The first `tok` run came back `None` on the REFERENCE for every row past ~400
# crunched bytes -- which is either an error-and-recover the memory capture cannot
# see, or a wedge. One claim per row, so it gets its own battery and its own
# readout: the screen.
#
# The subject line's echo WRAPS (it is up to 253 characters), so nothing can
# anchor on it. `tokx` therefore reads the raw screen and strips the payload's own
# characters back off -- whatever remains is what the machine printed.
#
# ⚠️ EVERY tokx ROW LEADS WITH `CLS`, and that is the control's whole story: the
# first cut did not, so the readout swept up each machine's BOOT BANNER -- and the
# two banners differ by construction, so `tokx-5` (a length nothing truncates)
# "diverged" on text neither machine had printed in response to anything. The
# banner cannot be filtered (it is machine-specific by design); it has to be
# CLEARED. `CLS` leads the case rather than riding in `reset` because these rows
# are isolated, and an isolated row runs boot-per-case with no reset at all.
def _tokx_case(k):
    return (f"tokx-{k}", "tokx", ["CLS", "20 A=" + "0#" * k])


CASES += [_tokx_case(k) for k in (5, 12, 30, 35, 40, 45, 124)]


# --- the `bnd` battery: the reference's crunch bound, TO THE BYTE -------------
# `tok`/`tokx` bracket it between 308 accepted and 317 refused, because a double
# literal moves in steps of nine. A trailing run of name characters moves it in
# steps of ONE (each is copied verbatim), so 34 literals + m filler characters
# crunches to exactly 308+m and walks the boundary out. The number that comes out
# of this is what a faithful crunch buffer has to be sized to -- measured
# black-box, from the outside, never read out of the reference ROM.
#
# Source length is 73+m, comfortably inside BOTH machines' input lines, so nothing
# here is confounded by the §1 truncation.
def _bnd_case(m):
    return (f"bnd-{m}", "bnd", ["CLS", "20 A=" + "0#" * 34 + FILLER * m])


CASES += [_bnd_case(m) for m in (0, 1, 2, 4, 6, 7, 8, 9, 10)]


# --- the `lnum` battery: THE EXPANSION THE LEAN CART *CAN* REACH --------------
# ⚠️ "The lean build has no float pack, so its crunch cannot expand" is REASONING,
# and it is wrong. The float literal is only the WIDEST expansion, not the only
# one: a line-number reference crunches to `$0E` + a 16-bit word -- THREE bytes
# from as little as ONE source character (basic/tokenise.inc branch_lineno, MSX2
# TH Figure 2.12). In an `ON..GOTO` list every `,1` is two characters and four
# bytes, so a 95-character line reaches ~174 -- past a 96-byte TOKBUF, in a build
# with no float literals anywhere.
#
# This battery is what decides whether the §2 defect is repack-only. It is asked
# of the LEAN cart (`--zb-machine C-BIOS_MSX1_EU_BASIC`) as well as the repack
# build, because the two crunch it differently and only one of them was suspected.
def _lnum_case(k):
    return (f"lnum-{k}", "tok", ["20 ONAGOTO1" + ",1" * k])


CASES += [_lnum_case(k) for k in (5, 20, 22, 23, 30, 42)]


# --- the `code` battery: WHICH ERR CODE `Line buffer overflow` IS -------------
# The message is measured (§2); the CODE is what an implementation actually
# raises, and zerobas's err_msgtab (basic/interp.asm:940) stops at 24, so
# whatever this reads may need a new entry. Asked by measuring rather than
# recalled from an error-code list: the refusal happens at line ENTRY, not during
# RUN, so the only way to see the code is to ask afterwards.
CASES += [
    ("code-over", "corrupt",
     ["CLS", "20 A=" + "0#" * 40, 'PRINT"[";ERR;"]"']),
    ("code-ctl", "corrupt",
     ["CLS", "20 A=" + "0#" * 5, 'PRINT"[";ERR;"]"']),
    # control: the same shape at a length nothing refuses -- pins what ERR reads
    # when NO error happened, so the overrun row's value is a difference.
]


# --- the `corrupt` battery: DOES THE OVERRUN ACTUALLY BREAK ANYTHING? ---------
# ⚠️ "IT WROTE PAST THE BUFFER" IS NOT A DEFECT UNTIL SOMETHING READS THE DAMAGE.
# `tok` measures that zerobas stores 407 crunched bytes into a 96-byte TOKBUF; the
# 311 bytes past the end land on ARYTAB ($E1C0 -- the scalar/array boundary, the
# FIRST cell after the buffer), the whole error-trap block, the 54-byte ZTRAP
# table, TRAPENA/TRAPSTK, POOLSIZE ($E232) and into STRTAB ($E240). This battery
# is what makes that legible as behaviour, and it is also the row that can
# FALSIFY a fix: bound the crunch and these must go green; leave TOKBUF where it
# is and no amount of LINEMAX work can move them.
#
# The overrunning line is typed DIRECT, so no program line is involved and the
# readout is not competing with a stored-line syntax error. 45 literals is
# zerobas's worst case (92 source characters, inside the 95 it accepts).
CASES += [
    ("corrupt-num", "corrupt",
     ["CLS", "A=" + "0#" * 45, "B=7", 'PRINT"[";B;"]"']),
    # ARYTAB is TOKBUF+96 exactly -- the first cell the overrun reaches.
    ("corrupt-str", "corrupt",
     ["CLS", "A=" + "0#" * 45, 'B$="HI"', 'PRINT"[";B$;"]"']),
    # POOLSIZE/STRTAB sit 210+ bytes past TOKBUF, well inside a 407-byte write.
    ("corrupt-ctl", "corrupt",
     ["CLS", "A=" + "0#" * 5, "B=7", 'PRINT"[";B;"]"']),
    # The LEAN cart's own overrun, via line-number references instead of float
    # literals (see the `lnum` battery): 174 crunched bytes into the same 96, and
    # in the lean build TOKBUF+96 is VARTAB -- the LIVE variable table. `A=0` so
    # the ON..GOTO falls through and the only thing under test is the crunch.
    ("corrupt-lnum", "corrupt",
     ["CLS", "A=0", "B=7", "ONAGOTO1" + ",1" * 42, 'PRINT"[";B;"]"']),
    # the two-sided control: the SAME shape at a length that does NOT overrun
    # (5 literals = 47 bytes), so a red corrupt-num/-str is the overrun and not
    # the direct line, the `A=` payload, or the readout.
]

# Every `tok`/`tokx` row is a SUSPECTED WEDGER on zerobas: the overrun lands on
# ARYTAB, the error-trap state and the trap table, so a shared boot would carry one
# row's wreckage into every row after it. They run boot-per-case.
ISOLATED = {lbl for lbl, bat, _ in CASES if bat in ("tok", "tokx")}

# Which capture each battery reads. Two batteries read the stored line's bytes;
# `tokx` reads the screen. They cannot share a run.
CAPTURE = {"rem": "line", "tok": "line",
           "tokx": "screen", "bnd": "screen", "corrupt": "screen"}


def decode(hexstr):
    """The stored line's bytes -> a readable summary. `""` = empty program (the
    line was REFUSED on entry); None = no capture at all (apparatus failure), a
    DIFFERENT reading that must never be folded into the first."""
    if hexstr is None:
        return None
    if hexstr == "":
        return "REFUSED (empty program)"
    b = bytes.fromhex(hexstr)
    if len(b) < 5:
        return f"RUNT {b.hex()}"
    lineno = b[2] | (b[3] << 8)
    body = b[4:]
    if body and body[-1] == 0:
        body = body[:-1]
    if body and body[0] == REM_TOKEN:
        tail = body[1:]
        pure = len(tail) == tail.count(ord(FILLER))
        return (f"line {lineno} REM +{len(tail)} filler"
                + ("" if pure else f" (NOT all filler: {tail.hex()})"))
    return f"line {lineno} {len(body)} tok bytes {body.hex()}"


def say(raw, lines):
    """What the machine PRINTED, with the subject line's own echo stripped off.
    A screen row built only from characters the CASE ITSELF typed is echo, not
    output; the prompt rows go too. None = no capture at all (the machine never
    reached it -- a WEDGE, not a message).

    ⚠️ THE ECHO ALPHABET IS DERIVED FROM THE CASE, never hard-coded. It was
    hard-coded once ("0#A=2CLS "), and the `bnd` battery -- whose payload adds a
    filler character the list did not have -- duly reported its own echo as
    machine output on every row. A readout that has to be updated by hand each
    time a battery is added is a readout that will silently stop working."""
    if raw is None:
        return None
    typed = set("".join(lines))
    # ⚠️ THE LAST ROW IS NOT OUTPUT. The reference draws the FUNCTION-KEY line
    # there (`color auto goto list run`) and zerobas draws nothing, so leaving it
    # in made every row differ on furniture -- the same shape as the boot banner
    # the CLS above fixed, one row further down. Dropping the bottom row is
    # machine-agnostic and changes no machine state (unlike `KEY OFF`).
    rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
            for r in range(omsx_repl.ROWS - 1)]
    out = []
    for r in rows:
        for p in omsx_repl.PROMPTS:         # a row can be prompt + echo
            if r.startswith(p):
                r = r[len(p):].strip()
        if r and set(r) - typed:            # not an echo of what this case typed
            out.append(r)
    return "|".join(out) if out else "<nothing printed>"


# --- the `cas` battery: THE THIRD CONSUMER, the one nobody types into ---------
# `ascii_read_lines` (basic/files.asm:1461) bounds an ASCII-LOADed line with the
# SAME `(LINEBUF+LINEMAX-1) & $FF` idiom and the SAME constant as the keyboard
# reader, and neither battery above can reach it: both type at the prompt. That
# the two share an idiom is a reason to EXPECT them to agree, not a measurement
# that they do -- and the reference could disagree with BOTH (its ASCII loader is
# not obliged to share its editor's ceiling).
#
# The VG-8020 has no disk, so the only ASCII-program path both machines accept is
# a cassette: an $EA tape carrying `20 REM` + filler, `LOAD"CAS:"`, then the same
# byte-exact stored-line readout the `rem` battery uses. Each row needs its OWN
# tape, so unlike every other battery these cannot share a run.
CAS_CASES = [("cas-40", 40), ("cas-100", 100), ("cas-250", 250)]


def run_cas(ref_machine, zb_machine):
    """Drive the `cas` rows: one tape and one boot per row per machine."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import tempfile
    from basic_probe_cas_ascii import build_ascii_cas  # noqa: E402

    rows = []
    for label, n in CAS_CASES:
        tape = tempfile.mktemp(suffix=".cas", prefix="linemax_")
        with open(tape, "wb") as f:
            f.write(build_ascii_cas("LMAX", ["20 REM" + FILLER * (n - 6)]))
        got = {}
        for tag, machine in (("ref", ref_machine), ("zb", zb_machine)):
            raw = omsx_repl.run_case(
                machine, "direct", ['LOAD"CAS:"'],
                capture=("stored_line", TXTTAB), boot=10.0, step=20.0,
                prologue=(f"cassetteplayer insert {{{tape}}}",))
            got[tag] = decode(raw)
        os.unlink(tape)
        rows.append((label, n, got["ref"], got["zb"]))
    return rows


def reader(case):
    """The decoder for one case's raw capture. `corrupt` is the odd one out: its
    claim is not "what did the machine print" but "does the NEXT statement still
    work", so it reads the bracketed value after its own short anchor line."""
    label, battery, lines = case
    if CAPTURE[battery] == "line":
        return decode
    if battery != "corrupt":
        return lambda raw: say(raw, lines)
    anchor = lines[-1]
    return lambda raw: (None if raw is None else
                        (omsx_repl.result_span_after_echo(raw, anchor)
                         or "<none>"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default=REF_MACHINE)
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE)
    ap.add_argument("--only")
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--cas", action="store_true",
                    help="run the cassette ASCII-LOAD battery INSTEAD of the "
                         "typed ones: it needs a tape and a boot per row, so it "
                         "cannot share a run with them")
    args = ap.parse_args()

    if args.cas:
        npass = 0
        for label, n, rt, zt in run_cas(args.machine, args.zb_machine):
            ok = rt is not None and zt is not None and rt == zt
            npass += 1 if ok else 0
            print(f"{'PASS' if ok else 'FAIL':5} cas  {label:11} {n:4} src chars")
            print(f"        ref: {rt}")
            print(f"        zb : {zt}")
        print(f"\n{npass}/{len(CAS_CASES)} rows agree with the reference")
        return 1 if (args.gate and npass != len(CAS_CASES)) else 0

    sel = [c for c in CASES if not args.only or args.only in c[0]]
    if not sel:
        print("APPARATUS FAILURE: no rows selected")
        return 1

    # The batteries do not share a capture, so they do not share a run. Rows are
    # grouped by capture and reported back in the order they were selected.
    verdicts = [None] * len(sel)
    ref_raws = [None] * len(sel)
    zb_raws = [None] * len(sel)

    for cap_kind in ("line", "screen"):
        idxs = [i for i, (_l, b, _n) in enumerate(sel)
                if CAPTURE[b] == cap_kind]
        if not idxs:
            continue
        capture = ("stored_line", TXTTAB) if cap_kind == "line" else "screen"

        def compare(j, rr, zz, _i=idxs):
            rd = reader(sel[_i[j]])
            a, b = rd(rr), rd(zz)
            return a is not None and b is not None and a == b

        v, rr, zz = omsx_repl.run_differential(
            args.machine, args.zb_machine,
            [("direct", sel[i][2]) for i in idxs], compare,
            batch=True, reset=("NEW",), capture=capture,
            isolate={j for j, i in enumerate(idxs)
                     if sel[i][0] in ISOLATED})
        for j, i in enumerate(idxs):
            verdicts[i], ref_raws[i], zb_raws[i] = v[j], rr[j], zz[j]

    npass = 0
    for i, (label, battery, lines) in enumerate(sel):
        read = reader(sel[i])
        rt, zt = read(ref_raws[i]), read(zb_raws[i])
        ok = verdicts[i]
        npass += 1 if ok else 0
        mark = "PASS" if ok else "FAIL"
        print(f"{mark:5} {battery:4} {label:11} "
              f"{max(len(l) for l in lines):4} src chars")
        print(f"        ref: {rt}")
        print(f"        zb : {zt}")
        sys.stdout.flush()

    print(f"\n{npass}/{len(sel)} rows agree with the reference")

    # --- the CALIBRATION check, before any verdict is read as a finding -------
    # rem-40 must agree (a length neither machine truncates) and rem-100 must read
    # exactly 89 surviving filler bytes on zerobas -- 95 characters minus `20 REM`,
    # the prediction LINEMAX=96 makes. Either one wrong and the apparatus, not the
    # machine, is what this run measured.
    bad = []
    for i, (label, _b, _l) in enumerate(sel):
        if (label in ("rem-40", "tok-5", "tokx-5", "corrupt-ctl")
                and not verdicts[i]):
            bad.append(f"{label} (a two-sided control) does not agree")
        if label == "rem-100":
            got = decode(zb_raws[i])
            if got != "line 20 REM +89 filler":
                bad.append(f"rem-100 zerobas reads {got!r}, not the +89 filler "
                           f"LINEMAX=96 predicts")
    if bad:
        print("\nAPPARATUS FAILURE -- no row in this run is a finding:")
        for m in bad:
            print(f"  {m}")
        return 1

    return 1 if (args.gate and npass != len(sel)) else 0


if __name__ == "__main__":
    sys.exit(main())
