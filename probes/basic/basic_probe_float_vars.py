#!/usr/bin/env python3

"""Float VARIABLES probe — characterise, then differentially prove, MSX-BASIC
TYPED numeric variables (Phase-3 float pack F3 S3a;
docs/spec-basic-float-core.md §11.1/§11.2/§11.4). DEF statements
(DEFINT/DEFSNG/DEFDBL/DEFSTR) are a SEPARATE later slice (S3b) — no DEF cases
here.

Each case types one or more `:`-separated statements ending in
`PRINT"[";<vars>;"]"` (or, for the Type-mismatch cases, a bare assignment that
must abort before any PRINT runs) in direct mode and captures the SCREEN 0 name
table, mirroring basic_probe_float_arith.py's bracket technique. Two captures
per case:

- the bracket SPAN (text between the last '[' and the following ']') — the
  printed value(s), spaces exact; None if the ']' never printed (the
  statement aborted before reaching the PRINT);
- the screen TAIL (rows between the echoed command and the closing prompt) —
  pins whether an error message printed and the statement aborted.

The matrix covers: suffix type resolution (`%`/`!`/`#`/unsuffixed-default-
double), the alias case (`A`/`A%`/`A!`/`A#` as up to 4 independent entries),
int-store truncation, single-store 6-digit half-up rounding (incl. carry
renormalise), double-store exactness, cross-type numeric<->string Type
mismatch, round-trip reassignment, the FOR/NEXT unsuffixed-default-double
interaction (D-D: the loop stays int16), a VARPTR-distinctness check, and a
function-over-a-typed-variable case (HEX$ over a single) plus a deliberately
uncertain int-store-domain edge (A%=40000) — the F1/F2 review lesson is that a
matrix asserting only the happy path misses real bugs, so a couple of cases
here are run WITHOUT a pre-baked "expect" and are only resolved by actually
querying the reference.

Characterisation mode (default): print the reference's exact output per case,
plus a self-check against the spec-documented value where one is pinned.
Differential mode (--zb-machine): also run zerobas (repack build) and assert
span/tail equality (REF_MACHINE Philips_VG_8020 vs the repack disk machine).

Clean-room: observed outputs only; the reference ROM is a black box.
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))

import argparse
import os
import re
import subprocess
import sys
import tempfile

OMSX_RUN = os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                        "lib", "omsx_run.py")
REF_MACHINE = "Philips_VG_8020"
COLS, ROWS = 40, 24
NLEN = COLS * ROWS

# Each case: (label, line, kind, expect)
#   kind "value": a normal PRINT — compare the bracket SPAN only (mirrors the
#                 arith probe's "raw" kind: immune to echo-line wrapping).
#   kind "abort": the statement must abort BEFORE any PRINT runs — both sides
#                 must show NO span and a NON-EMPTY tail (an error printed).
#                 Wording is NOT compared (D-2 convention: zerobas's error
#                 text is its own lowercase wording, never the reference's
#                 verbatim string — see e.g. the string-acceptance range-error
#                 case, "Illegal function call" vs "syntax error", both
#                 accepted as long as the ABORT SHAPE matches).
#   expect: the spec-documented value for a characterisation self-check, or
#           None when the case is intentionally open (its whole point is to
#           discover the reference's actual behaviour rather than assert a
#           pre-baked guess — the "false-EXPECTED" review lesson).
CASES = [
    # --- suffix type resolution (§11.1) -------------------------------------
    # Numbers print sign-position (space or '-') + digits + ONE trailing space
    # (spec §9.3, formatter contract) -- confirmed live for the plain int path
    # too (int.trunc.exact below), so every numeric "value" expect carries
    # that same leading/trailing spacing; string-function results (HEX$ etc.,
    # further down) do NOT.
    ("suffix.pct",  'A%=5:PRINT"[";A%;"]"',                      "value", " 5 "),
    ("suffix.bang", 'A!=5:PRINT"[";A!;"]"',                      "value", " 5 "),
    ("suffix.hash", 'A#=5:PRINT"[";A#;"]"',                      "value", " 5 "),
    ("suffix.none", 'A=5:PRINT"[";A;"]"',                        "value", " 5 "),
    # unsuffixed default is DOUBLE, not single: 1/3 unsuffixed must print the
    # full 14-digit double form, identical to the explicit A# case.
    ("suffix.none.dbl", 'A=1/3:PRINT"[";A;"]"',                  "value", " .33333333333333 "),
    ("suffix.hash.dbl", 'A#=1/3:PRINT"[";A#;"]"',                "value", " .33333333333333 "),

    # --- alias case: A/A%/A!/A# up to 4 independent entries (§11.1) ---------
    ("alias.a_bang_hash",
     'A=1:A!=2:A#=3:PRINT"[";A;A!;A#;"]"',                       "value", " 3  2  3 "),
    ("alias.all4",
     'A=1:A%=2:A!=3:A#=4:PRINT"[";A;A%;A!;A#;"]"',                "value", " 4  2  3  4 "),

    # --- int-store: TRUNCATE toward zero (§11.2, same rule as \/MOD) --------
    ("int.trunc.pos", 'A%=1.7:PRINT"[";A%;"]"',                  "value", " 1 "),
    ("int.trunc.neg", 'A%=-1.7:PRINT"[";A%;"]"',                 "value", "-1 "),
    ("int.trunc.exact", 'A%=5:PRINT"[";A%;"]"',                  "value", " 5 "),
    # inclusive strict-int16 boundary (own hypothesis: variable store uses the
    # STRICT domain, -32768..32767, like \/MOD/logical operands, NOT the
    # address domain POKE/HEX$ use — see var_store_fac's header comment,
    # basic/vars.asm).
    ("int.trunc.bound.max", 'A%=32767.9:PRINT"[";A%;"]"',        "value", " 32767 "),
    ("int.trunc.bound.min", 'A%=-32768.9:PRINT"[";A%;"]"',       "value", "-32768 "),

    # --- single-store: ROUND to 6 sig digits, half-up, carry renorm (§11.2) -
    ("sng.round.carry",  'A!=1234567:PRINT"[";A!;"]"',           "value", " 1234570 "),
    ("sng.round.plain",  'A!=123456.7:PRINT"[";A!;"]"',          "value", " 123457 "),
    ("sng.round.third",  'A!=2/3:PRINT"[";A!;"]"',               "value", " .666667 "),
    ("sng.round.allnine", 'A!=1.9999999:PRINT"[";A!;"]"',        "value", " 2 "),

    # --- double-store: exact (14 sig digits) --------------------------------
    ("dbl.exact.third", 'A#=1/3:PRINT"[";A#;"]"',                "value", " .33333333333333 "),
    ("dbl.exact.int",   'A=1234567:PRINT"[";A;"]"',              "value", " 1234567 "),

    # --- cross-type numeric<->string: Type mismatch, statement aborts ------
    ("mismatch.numeric_eq_string", 'A%="X":PRINT"[";A%;"]"',     "abort", None),
    ("mismatch.string_eq_numeric", 'A$=5:PRINT"[";A$;"]"',       "abort", None),

    # --- round-trip via reassignment ----------------------------------------
    ("roundtrip.int",    'A%=5:A%=A%+1:PRINT"[";A%;"]"',         "value", " 6 "),
    ("roundtrip.single", 'A!=1:A!=A!*3:PRINT"[";A!;"]"',         "value", " 3 "),
    ("roundtrip.double", 'A#=1:A#=A#/3:PRINT"[";A#;"]"',         "value", " .33333333333333 "),

    # --- D-D: unsuffixed FOR/NEXT loop var now defaults to double, but the
    # loop math itself stays int16 (documented divergence). MUST run as a
    # STORED program + RUN, not typed direct-mode: a re-entrant NEXT resumes
    # via RESUMEFLAG/RESUMEPTR/CURLINE (program.asm), which only the run_prog
    # line-walking loop consults -- direct-mode dispatch (repl -> dispatch_line
    # -> exec) never checks them, so a direct-mode multi-pass FOR/NEXT silently
    # never reaches its own trailing statements. Confirmed pre-existing on the
    # LEAN (pre-F3, int-only) build too via the host harness -- an existing
    # interpreter scope limit, not an F3 regression -- so this one case is
    # marked "stored" to route through store_line+RUN instead of direct typing.
    ("fornext.default_double", 'FOR I=1 TO 3:NEXT:PRINT"[";I;"]"', "stored", " 4 "),

    # --- VARPTR distinctness: A%/A!/A# are 3 INDEPENDENT entries (A itself is
    # an ALIAS of A#, same entry -- confirmed live on the reference: VARPTR(A)
    # == VARPTR(A#) after `A#=...:A=...`, since the unsuffixed name resolves
    # to the SAME double slot -- so distinctness is only asserted pairwise
    # across %/!/#, never against the bare unsuffixed name). The ADDRESS
    # VALUES themselves are an own-design storage layout (never expected to
    # match the reference's), so only the DISTINCTNESS relation is asserted.
    # (kept short -- LINEBUF is 96 bytes; the earlier single AND-chained line
    # combining all three pairs ran past that and got silently truncated by
    # the keyboard-injection layer, a probe-harness bug in its own right)
    ("varptr.distinct.pct_bang",
     'A%=1:A!=2:PRINT"[";VARPTR(A%)<>VARPTR(A!);"]"',              "value", "-1 "),
    ("varptr.distinct.bang_hash",
     'A!=2:A#=3:PRINT"[";VARPTR(A!)<>VARPTR(A#);"]"',              "value", "-1 "),
    ("varptr.alias_a_eq_hash",
     'A#=3:A=4:PRINT"[";VARPTR(A)=VARPTR(A#);"]"',                 "value", "-1 "),

    # --- function-over-typed: a function argument that is a TYPED variable
    # (not a literal) — the F1/F2 review lesson generalised to F3: always
    # include a function-over-a-variable case, not just function-over-literal
    # (ev_f_var must set FAC/FACTYP/DE exactly like ev_f_float does). HEX$
    # returns a STRING (no number-format padding). ---------------------------
    ("func.hex_over_single", 'A!=2.9:PRINT"[";HEX$(A!);"]"',      "value", "2"),
    ("func.hex_over_double", 'A#=-2.5:PRINT"[";HEX$(A#);"]"',     "value", "FFFE"),

    # --- deliberately OPEN cases (no pre-baked "expect"): the review lesson
    # is that a matrix which only asserts the happy path misses real bugs, so
    # these are resolved by actually querying the reference rather than
    # guessing. int.store.overflow tests var_store_fac's own domain CHOICE
    # (strict vs address) at a value that only the strict domain rejects. ---
    ("int.store.overflow", 'A%=40000:PRINT"[";A%;"]"',            "abort_or_value", None),
    ("int.store.overflow.neg", 'A%=-40000:PRINT"[";A%;"]"',       "abort_or_value", None),

    # --- Fable adversarial-review regressions (three matrix-invisible bugs
    # found 2026-07-12; each case below FAILED before its fix) ---------------
    # Bug A (var_alloc_or_find zero-init used B=0 -> zeroed 256 bytes, ploughing
    # through STRTAB $E240 and wiping earlier string vars' name0). A numeric
    # allocation AFTER a string assignment must leave the string intact.
    ("reg.A.strtab_integrity", 'B$="HI":A=1:PRINT"[";B$;"]"',     "value", "HI"),
    # Bug B (ex_let read the GLOBAL (VARTYPE) after eval, but every RHS variable
    # factor re-runs var_name_key and overwrites it -> cross-type store used the
    # RHS's type, not the LHS's). All four pin the LHS-type latch.
    ("reg.B.crosstype_hash_to_pct", 'A#=2:A%=A#:PRINT"[";A%;"]"', "value", " 2 "),
    ("reg.B.crosstype_pct_in_expr", 'B%=5:A#=B%+1:PRINT"[";A#;"]"', "value", " 6 "),
    ("reg.B.crosstype_unset_pct",  'A!=B%:PRINT"[";A!;"]"',       "value", " 0 "),
    ("reg.B.crosstype_len_fn",     'B$="ABC":A%=LEN(B$):PRINT"[";A%;"]"', "value", " 3 "),
    # Bug C (tok_skip didn't stride the float literals $1D/$1F, so a mantissa
    # $00 byte was mistaken for the line/stmt terminator by skip_to_eol /
    # if_skip_to_else / data_seek). The PRIMARY repro is a STORED program with a
    # float literal (skip_to_eol measures the line at RUN time) -- "stored"
    # kind routes through store_line+RUN.
    ("reg.C.stored_float_literal", 'A=1.5:PRINT"[";A;"]"',        "stored", " 1.5 "),
    # Direct-mode proxy for the same stride via if_skip_to_else: the false IF
    # must skip PAST the THEN clause's `A=1.5` (a $1D literal with $00 mantissa
    # bytes) to reach ELSE -- exercises tok_skip identically without needing a
    # stored program.
    ("reg.C.if_skip_over_float", 'IF 0 THEN A=1.5 ELSE PRINT"[";9;"]"', "value", " 9 "),
]


def run_line(machine, line, base=8.0, tail=8.0, timeout=120):
    """Type one direct-mode line (+ separately-timed Enter), return the SCREEN 0
    name table as one raw row-major string of length NLEN."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="floatvars_")
    os.close(out_fd)
    cmd = [sys.executable, OMSX_RUN, "--machine", machine,
           "--type", line, "--type-delay", str(base),
           "--type", "\r", "--type-delay", str(base + 3),
           "--time", str(base + 3 + tail),
           "--mem", f"VRAM:0x0000:{NLEN}",
           "--out", out_path, "--timeout", str(timeout)]
    subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cap = ""
    if os.path.exists(out_path):
        with open(out_path) as f:
            cap = f.read()
        os.unlink(out_path)
    m = re.search(rf"mem\.VRAM:0x0000:{NLEN}=([0-9a-f]+)", cap)
    if not m:
        return None
    data = bytes.fromhex(m.group(1))
    return "".join(chr(b) if 32 <= b < 127 else " " for b in data)


def run_stored(machine, body, base=8.0, tail=8.0, timeout=120):
    """Store `body` as program line 10, then RUN it -- for constructs (a
    re-entrant NEXT) whose resume-and-loop-back only the run_prog line-walking
    loop honours (RESUMEFLAG/RESUMEPTR/CURLINE, program.asm); direct-mode
    dispatch never consults them, so a direct-mode multi-pass FOR/NEXT never
    reaches its own trailing statements (confirmed pre-existing, F3-unrelated,
    on the lean int-only build too). Returns the raw screen buffer, same shape
    as run_line."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="floatvars_")
    os.close(out_fd)
    cmd = [sys.executable, OMSX_RUN, "--machine", machine,
           "--type", "10 " + body, "--type-delay", str(base),
           "--type", "\r", "--type-delay", str(base + 3),
           "--type", "RUN", "--type-delay", str(base + 6),
           "--type", "\r", "--type-delay", str(base + 9),
           "--time", str(base + 9 + tail),
           "--mem", f"VRAM:0x0000:{NLEN}",
           "--out", out_path, "--timeout", str(timeout)]
    subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cap = ""
    if os.path.exists(out_path):
        with open(out_path) as f:
            cap = f.read()
        os.unlink(out_path)
    m = re.search(rf"mem\.VRAM:0x0000:{NLEN}=([0-9a-f]+)", cap)
    if not m:
        return None
    data = bytes.fromhex(m.group(1))
    return "".join(chr(b) if 32 <= b < 127 else " " for b in data)


def result_span(raw):
    """The printed value: text between the LAST '[' and the following ']'.
    The echoed source line contains '[' too, but the result's '[' is printed
    after it. Returns None if the ']' never printed (statement aborted)."""
    if raw is None:
        return None
    i = raw.rfind("[")
    if i < 0:
        return None
    j = raw.find("]", i)
    if j < 0:
        return None
    return raw[i + 1: j]


def screen_tail(raw, cmdline):
    """All rows between the echoed command line and the closing prompt
    (inclusive of neither), right-stripped, joined with '|'. Pins error
    messages + abort-vs-continue shape. None if the echo row is not found.

    Machine-agnostic: the reference echoes the line verbatim and closes with
    'Ok'; zerobas prefixes the echo with its 'zb>' prompt and closes with a
    bare 'zb>' row — so the echo match is ends-with and both prompt shapes
    terminate the tail."""
    if raw is None:
        return None
    rows = [raw[r * COLS:(r + 1) * COLS].strip() for r in range(ROWS)]
    key = cmdline.strip()
    idx = None
    for i, r in enumerate(rows):
        if r == key or r.endswith(key):
            idx = i  # keep the LAST occurrence
    if idx is None:
        return None
    out = []
    for r in rows[idx + 1:]:
        if r == "Ok" or r == "zb>":
            break
        out.append(r)
    while out and out[-1] == "":
        out.pop()
    return "|".join(out)


def result_span_after_echo(raw, cmdline):
    """Like result_span, but restricted to the rows AFTER the echoed command
    line. Needed here (unlike basic_probe_float_arith.py, whose every case
    errors out MID the same PRINT statement that already emitted the "["
    literal): several F3 cases abort in an EARLIER `:`-separated statement
    (e.g. `A%="X":PRINT"[";A%;"]"`), so the PRINT statement — and its own
    "[" / "]" literals — never actually RUNS at all; the only bracket
    characters anywhere on screen are then the ones sitting in the typed
    ECHO of the source line itself. A plain whole-buffer result_span() would
    misread that echoed source text as if it were real printed output (a
    real bug caught while building this probe — the F1/F2 review lesson
    generalises to probe-harness code too, not just the ROM). Restricting the
    search to rows after the echo makes "no real value was ever printed"
    (CF the "abort" / "abort_or_value" cases below) unambiguous. None if the
    echo row itself can't be found."""
    if raw is None:
        return None
    rows = [raw[r * COLS:(r + 1) * COLS] for r in range(ROWS)]
    stripped = [r.strip() for r in rows]
    key = cmdline.strip()
    idx = None
    for i, r in enumerate(stripped):
        if r == key or r.endswith(key):
            idx = i  # keep the LAST occurrence, same convention as screen_tail
    if idx is None:
        return None
    return result_span("".join(rows[idx + 1:]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE,
                    help=f"reference oracle machine (default {REF_MACHINE})")
    ap.add_argument("--zb-machine", dest="zb_machine",
                    help="differential mode: also run this repack machine and "
                         "assert span/tail equality")
    ap.add_argument("--only", help="substring filter on the case label")
    args = ap.parse_args()

    def capture(machine, line, kind):
        """Return (span, tail) for one case on one machine. Span-extraction
        differs by kind: a "value"/"stored" case ALWAYS reaches its PRINT, so
        the real value is the LAST '[' anywhere on screen -- plain result_span,
        which is immune to the source line wrapping past 40 columns (the
        varptr cases do). An "abort"/"abort_or_value" case may NOT reach its
        PRINT, so its echoed '[' must not be misread as output -- result_span_
        after_echo restricts the search to rows after the echo, at the cost of
        needing the echo row to be findable (so those cases are kept <=40
        cols)."""
        if kind == "stored":
            raw = run_stored(machine, line)
            return result_span(raw), None
        raw = run_line(machine, line)
        if kind == "value":
            return result_span(raw), screen_tail(raw, line)
        return result_span_after_echo(raw, line), screen_tail(raw, line)

    ok = True
    for label, line, kind, expect in CASES:
        if args.only and args.only not in label:
            continue
        ref_span, ref_tail = capture(args.machine, line, kind)
        rs = f"[{ref_span}]" if ref_span is not None else "<no span>"

        if args.zb_machine:
            zb_span, zb_tail = capture(args.zb_machine, line, kind)
            zs = f"[{zb_span}]" if zb_span is not None else "<no span>"

            if kind in ("value", "stored"):
                same = ref_span is not None and ref_span == zb_span
            elif kind == "abort":
                same = (ref_span is None and zb_span is None
                        and bool(ref_tail) and bool(zb_tail))
            else:  # "abort_or_value": accept whichever shape the REFERENCE
                   # took, as long as zerobas took the SAME shape (value vs
                   # abort) and, if a value, the same value.
                if ref_span is None:
                    same = zb_span is None and bool(ref_tail) and bool(zb_tail)
                else:
                    same = zb_span is not None and ref_span == zb_span

            ok = ok and same
            print(f"{'PASS' if same else 'FAIL'}  {label:<24} ref: {rs}")
            if not same:
                print(f"{'':>32}ref tail: {ref_tail!r}")
                print(f"{'':>32}zb  span: {zs}  tail: {zb_tail!r}")
        else:
            note = ""
            if expect is not None:
                match = "OK" if ref_span == expect else "MISMATCH vs spec!"
                note = f"   expect {expect!r} -> {match}"
            elif ref_span is None:
                note = f"   tail: {ref_tail!r}"
            print(f"{label:<24} {rs}{note}")

    if args.zb_machine:
        print("\nALL PASS — float variables (F3 S3a) reference-identical" if ok
              else "\nSOME FAILED")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
