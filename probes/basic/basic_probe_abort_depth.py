#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CUR-D untrapped-abort acceptance (docs/spec-basic-abort-depth.md).

VG-8020 differential over the UNTRAPPED abort path: raise an error from BELOW
statement-handler depth with NO handler armed, and compare what the user
actually sees on screen.

⚠️ NOT ONE ROW MAY ARM `ON ERROR`. That is the entire point of this probe and
it is why it exists as a separate gate from `basic_probe_intarg.py`.
`raise_error` has two branches: the TRAP branch resets SP (`ld sp,(SAVSTK)`)
and jumps to the handler, and the ABORT branch prints and returns. Arming a
handler selects the trap branch -- the one that was always correct. The 36
asserted rows of the intarg gate all arm `ON ERROR GOTO` and read `ERR`, and
they were ALL PASS on the same build where `WIDTH 99999` typed at the prompt
printed no error at all and left the screen unusable. An `ON ERROR` added to
this file would silently turn it into a second copy of that gate.

⚠️ EVERY VALUE ROW IS BRACKET-DELIMITED (`PRINT "[";...;"]"`). The junk an
aborted statement leaves behind can be WHITESPACE -- `SPACE$(-1)` returned into
`str_fn_space` with A=5 and built a five-space string -- and a right-stripped
screen scrape reads that as clean. The brackets are load-bearing, not cosmetic.

READOUT. The comparison is the echo-anchored tail (the rows between the echoed
command and the closing prompt), because the RAW scrape can never match across
the two machines -- they carry different prompts and the reference paints a
function-key row. The raw scrape is captured anyway and printed on failure,
because it is the only readout that shows the severe symptom: when `WIDTH 300`
returns into `ex_width` with A=5 the screen is re-inited to width 5, and the
tail readout reports `<no echo>` because the echo it anchors on is gone.

Boot-per-case throughout: the WIDTH rows leave the machine unusable by
construction, so they cannot share a boot with anything.

Message CASE is folded before comparison. zerobas ships two spellings of the
same message on purpose -- lowercase house style, and the reference-verbatim
capitalised text on the arrays path (basic/arrays.asm:44) -- so `overflow` vs
`Overflow` is a documented divergence, not this slice's subject.
"""
from __future__ import annotations
import argparse, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import omsx_repl  # noqa: E402

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

COLS, ROWS = 40, 24

# (label, lines). The CONTROL rows come first and are read first: they prove
# the abort mechanism is reachable and the readout works before any other row
# is read as a finding.
CASES = [
    # --- controls -------------------------------------------------------------
    ("ctl_value",    ['CLS', 'PRINT "[";LEN("abc");"]"']),
    ("ctl_abort",    ['CLS', 'PRINT "[";ASC("");"]"']),
    # --- S-AD-2: the FIRST line after a cold boot, no CLS prologue ------------
    # SAVSTK is written by dl_cmd/run_prog immediately before the run loop is
    # entered and is NOT initialised at boot; this row is the measurement that
    # the anchor is live on the very first statement a machine ever runs.
    ("boot_first",   ['PRINT "[";ASC("");"]"']),
    # --- get_byte_arg callers (the four the roadmap knew about) ---------------
    ("width_ill",    ['CLS', 'WIDTH 300']),
    ("width_ovf",    ['CLS', 'WIDTH 99999']),
    ("space_neg",    ['CLS', 'PRINT "[";SPACE$(-1);"]"']),
    ("space_ovf",    ['CLS', 'PRINT "[";SPACE$(99999);"]"']),
    ("string_neg",   ['CLS', 'PRINT "[";STRING$(-1,65);"]"']),
    ("string_ovf",   ['CLS', 'PRINT "[";STRING$(99999,65);"]"']),
    ("string_chr",   ['CLS', 'PRINT "[";STRING$(5,256);"]"']),
    ("on_ill",       ['CLS', 'ON 256 GOTO 10']),
    ("on_ovf",       ['CLS', 'ON 99999 GOTO 10']),
    # --- ev_ff_arg leaves (the five the roadmap did NOT know about) ----------
    ("stick_ill",    ['CLS', 'PRINT "[";STICK(9);"]"']),
    ("strig_ill",    ['CLS', 'PRINT "[";STRIG(9);"]"']),
    ("vpeek_neg",    ['CLS', 'PRINT "[";VPEEK(-1);"]"']),
    ("vpeek_ill",    ['CLS', 'PRINT "[";VPEEK(16384);"]"']),
    ("peek_ovf",     ['CLS', 'PRINT "[";PEEK(99999);"]"']),
    ("inp_ovf",      ['CLS', 'PRINT "[";INP(99999);"]"']),
    ("vpoke_ill",    ['CLS', 'VPOKE 16384,0']),
    # --- S-AD-3: raised from inside a PAGE-0 SUB-ROM TENANT ------------------
    # ary_engine (sub/arrays.asm) runs with main page 1 visible, so unlike a
    # page-1 tenant it CAN reach raise_error. The SP reset unwinds out of the
    # tenant call; this row pins the message, and `tenant_after` pins that the
    # machine is still usable afterwards.
    ("tenant_ary",   ['CLS', 'DIM Q(3):PRINT "[";Q(9);"]"']),
    ("tenant_after", ['CLS', '10 DIM Q(3)', '20 PRINT "[";Q(9);"]"',
                      '30 PRINT "[NOTREACHED]"', 'RUN']),
    # --- run mode: the " in <line>" suffix must survive the unwind -----------
    ("run_suffix",   ['CLS', '10 PRINT "[";ASC("");"]"', 'RUN']),
    ("run_below",    ['CLS', '10 PRINT "[";SPACE$(-1);"]"', 'RUN']),
]


def capture(machine, lines, label=""):
    """-> (tail, raw). `tail` is the compared readout; `raw` is diagnostic.

    ONE retry on an apparatus timeout, and it announces itself. This matrix is
    46 boots and `omsx_repl.run_case` raises SystemExit on a timeout, so a
    single host-level flake (openMSX intermittently hanging at launch, seen
    2026-07-28) would otherwise discard the whole run. A retry that ALSO times
    out is left to propagate: a real hang must stay loud, and a silent retry
    loop would turn a wedged machine into a slow green."""
    try:
        scr = omsx_repl.run_case(machine, "direct", lines)
    except SystemExit as e:
        print(f"      APPARATUS: {e} on {label or lines[-1]!r} — retrying ONCE")
        sys.stdout.flush()
        scr = omsx_repl.run_case(machine, "direct", lines)
    if scr is None:
        return None, None
    rows = [scr[r * COLS:(r + 1) * COLS] for r in range(ROWS)]
    raw = "|".join(r.rstrip() for r in rows if r.strip())
    tail = omsx_repl.screen_tail(scr, lines[-1])
    return (tail if tail is not None else "<no echo>"), raw


def norm(s):
    """Fold message case (the documented two-spelling divergence, spec §7).
    Runs of spaces are COLLAPSED but never dropped, so whitespace-only junk
    still differs from no junk at all."""
    if s is None:
        return None
    return " ".join(s.casefold().replace("|", " | ").split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default=REF_MACHINE)
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE)
    ap.add_argument("--only")
    ap.add_argument("--gate", action="store_true",
                    help="fail on any divergence (the standing gate); without "
                         "it every row is reported as a straight differential")
    args = ap.parse_args()

    npass = ntot = 0
    for label, lines in CASES:
        if args.only and args.only not in label:
            continue
        ref_t, ref_r = capture(args.machine, lines, label)
        zb_t, zb_r = capture(args.zb_machine, lines, label)
        same = ref_t is not None and zb_t is not None and norm(ref_t) == norm(zb_t)
        ntot += 1
        npass += 1 if same else 0
        print(f"{'PASS' if same else 'FAIL':5} {label:13} {lines[-1][:32]:32} "
              f"{'SAME' if same else 'DIFF'}")
        if not same:
            print(f"        ref tail: {ref_t!r}")
            print(f"        zb  tail: {zb_t!r}")
            print(f"        zb  raw : {zb_r!r}")
        sys.stdout.flush()

    print(f"\n{npass}/{ntot} rows agree with the reference")
    if ntot == 0:
        print("APPARATUS FAILURE: no rows ran")
        return 1
    if args.gate and npass != ntot:
        print("SOME FAILED")
        return 1
    print("ALL PASS" if npass == ntot else "REPORTED (not gated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
