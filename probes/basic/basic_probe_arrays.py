#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Differential arrays probe (docs/spec-basic-arrays.md §9.7) — prove zerobas's
numeric-array slice behaves byte-for-byte like the stock VG-8020 across the §4.1
characterization matrix.

Reference: stock Philips_VG_8020 (real MSX-BASIC 1.0). zerobas: the repack build
(C-BIOS_MSX1_EU_REPACK_DISK — arrays are repack-only). Drives both via the
KEYBUF-injection REPL harness (omsx_repl) and compares the printed value span OR
the error-message tail for each case. Observed outputs only, no ROM disassembly.

The VG-8020 reference machine is NOT in the default (homebrew) openMSX machine
path; point the harness at a build that has it, e.g.:
  OPENMSX=/Users/joost/projects/openmsx/derived/aarch64-darwin-opt/bin/openmsx \\
    python3 probes/basic/basic_probe_arrays.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import omsx_repl as R  # noqa: E402

REF = "Philips_VG_8020"
ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
OMSX = os.environ.get("OPENMSX")  # None -> find_omsx default (must resolve REF)

# Each case: (label, mode, lines, kind). kind "value" compares the [..] span;
# "err" compares the error-message tail; "either" compares whichever the
# reference produced (some cases abort mid-line before the PRINT).
CASES = [
    ("autodim.bound10.ok",  "direct", ['A(10)=9:PRINT"[";A(10);"]"'],            "value"),
    ("autodim.11.oor",      "direct", ['A(11)=9:PRINT"[";A(11);"]"'],            "err"),
    ("autodim.touch.max",   "direct", ['A(5)=1:PRINT"[";A(10);"]"'],             "value"),
    ("dim.inclusive",       "direct", ['DIM B(5):B(5)=3:PRINT"[";B(5);"]"'],     "value"),
    ("dim.over.oor",        "direct", ['DIM B(5):B(6)=3:PRINT"[";B(6);"]"'],     "err"),
    ("base0",               "direct", ['DIM B(2):B(0)=7:PRINT"[";B(0);"]"'],     "value"),
    ("autoinit0",           "direct", ['DIM B(3):PRINT"[";B(2);"]"'],            "value"),
    ("redim",               "direct", ['DIM B(3):DIM B(3):PRINT"[ok]"'],         "err"),
    ("multidim.val",        "stored", ['DIM C(2,3):C(1,2)=5', 'PRINT"[";C(1,2);"]"'], "value"),
    ("multidim.init0",      "direct", ['DIM C(2,3):PRINT"[";C(2,3);"]"'],        "value"),
    ("multidim.wrongn.oor", "direct", ['DIM C(2,3):PRINT"[";C(1);"]"'],          "err"),
    ("typeindep",           "stored", ['A(1)=11:A%(1)=22', 'PRINT"[";A(1);",";A%(1);"]"'], "value"),
    ("neg.illegal",         "direct", ['DIM B(5):PRINT"[";B(-1);"]"'],           "err"),
    ("float.elem",          "direct", ['DIM D(3):D(1)=1.5:PRINT"[";D(1);"]"'],   "value"),
    ("multi.array.per.dim", "stored", ['DIM P(2),Q(3):P(2)=7:Q(3)=8', 'PRINT"[";P(2);Q(3);"]"'], "value"),
    ("ordering.2x2",        "stored",
        ['DIM C(1,1):C(0,0)=1:C(1,0)=2:C(0,1)=3:C(1,1)=4',
         'PRINT"[";C(0,0);C(1,0);C(0,1);C(1,1);"]"'], "value"),
    # --- variable-subscript regression class (slice-1 fix, 2026-07-15) -----
    # Root causes guarded forever: (1) fac_to_int_strict clobbers HL on the
    # float path only, so any VARIABLE (default double) subscript/bound
    # trashed ary_parse_subs's cursor -> phantom "syntax error" while literal
    # (int) subscripts sailed through; (2) the shared ARY_NIDX/ARY_IDX param
    # block was written incrementally per subscript, so a NESTED array rvalue
    # X(X(0)) re-entrantly clobbered the outer parse's partial count/values.
    ("var.subscript",       "stored", ['DIM X(3):I=1:X(I)=5', 'PRINT"[";X(I);"]"'], "value"),
    ("var.dim.bound",       "stored", ['N=4:DIM X(N):X(4)=7', 'PRINT"[";X(4);"]"'], "value"),
    ("nested.subscript",    "stored", ['DIM X(3):X(0)=2:X(2)=9', 'PRINT"[";X(X(0));"]"'], "value"),
    ("for.loop.fill",       "stored", ['DIM X(3):FOR I=0 TO 3:X(I)=I:NEXT', 'PRINT"[";X(3);"]"'], "value"),
    # DIM-then-use at MAXDIM guards the aeng_dim key-write path (a clobbered
    # ARY_KEY made every DIM'd descriptor invisible; small bounds silently
    # fell through to auto-dim, 4-dim exposed it as a phantom auto-dim OOM).
    ("dim.then.use.4d",     "stored", ['DIM C(1,1,1,1):C(1,1,1,1)=6', 'PRINT"[";C(1,1,1,1);"]"'], "value"),
    # error-surface casing: DIM OOM is reference-verbatim "Out of memory";
    # DIM with a negative bound is "Illegal function call" (tenant-side check)
    ("dim.oom.casing",      "direct", ['DIM X(5000):PRINT"[x]"'],  "err"),
    ("dim.neg.illegal",     "direct", ['DIM E(-1):PRINT"[x]"'],    "err"),

    # === arrays slice 2: ERASE (docs/spec-basic-arrays-slice2-erase.md §5) =====
    # Value/behaviour cases are STORED (no runtime error -> both machines run to
    # completion, so the "[..]" span is differential). Every ERROR-tier case is
    # DIRECT and kept < 40 chars: zerobas's stored-RUN does NOT abort on a runtime
    # error (pre-existing landmine, review finding F2) whereas the reference's
    # does, so a stored error case's screen tail structurally diverges (REF shows
    # "... in NN" + halts, ZB continues) -- direct mode aborts the whole line on
    # BOTH, giving a clean differential tail. Direct lines must fit one 40-col row
    # or the echo-anchor scrape (screen_tail) can't find the wrapped command.
    #
    # value/behaviour (differential "[..]" span):
    ("erase.then.print",    "stored", ['DIM A(5):A(3)=7', 'ERASE A', 'PRINT"[";A(3);"]"'], "value"),
    ("erase.then.autodim",  "stored", ['DIM A(5):A(3)=7', 'ERASE A', 'A(2)=4', 'PRINT"[";A(2);A(3);"]"'], "value"),
    ("erase.preserves.other","stored",['DIM A(5),B(5):A(3)=7:B(3)=9', 'ERASE A', 'PRINT"[";B(3);"]"'], "value"),
    ("erase.middle.compacts","stored",['DIM A(5),B(5),C(5):B(3)=8:C(3)=9', 'ERASE B', 'PRINT"[";C(3);"]"'], "value"),
    ("erase.list.two",      "stored", ['DIM A(5),B(5):A(3)=7:B(3)=9', 'ERASE A,B', 'A(3)=1:B(3)=2', 'PRINT"[";A(3);B(3);"]"'], "value"),
    ("erase.type.indep",    "stored", ['DIM A(5),A%(5):A(3)=1.5:A%(3)=7', 'ERASE A', 'PRINT"[";A%(3);"]"'], "value"),
    ("erase.typed.pct",     "stored", ['DIM A%(5):A%(3)=7', 'ERASE A%', 'DIM A%(5)', 'PRINT"[";A%(3);"]"'], "value"),
    ("erase.enables.redim", "stored", ['DIM A(5)', 'ERASE A', 'DIM A(3)', 'PRINT"[ok]"'], "value"),
    ("erase.longname",      "stored", ['DIM AB(5):AB(3)=7', 'ERASE AB', 'AB(3)=1', 'PRINT"[";AB(3);"]"'], "value"),
    ("erase.redim.diffdim", "stored", ['DIM A(5)', 'ERASE A', 'DIM A(2,2):A(1,1)=3', 'PRINT"[";A(1,1);"]"'], "value"),
    ("erase.hash.matches",  "stored", ['DIM A(5):A(3)=7', 'ERASE A#', 'PRINT"[";A(3);"]"'], "value"),
    # Tier B -- Illegal function call (differential; reference-verbatim capital):
    ("undeclared.erase",    "direct", ['ERASE A'],                  "err"),
    ("double.erase",        "direct", ['DIM A(5):ERASE A:ERASE A'], "err"),
    ("erase.wrongtype",     "direct", ['DIM A(5):A(3)=7:ERASE A%'], "err"),
    ("erase.bang.matches",  "direct", ['DIM A(5):A(3)=7:ERASE A!'], "err"),
    ("erase.str.undeclared","direct", ['ERASE A$'],                 "err"),
    ("erase.bang.undecl",   "direct", ['ERASE A!'],                 "err"),
    # F1 regression: a `$` name must NOT match the numeric `A` (vnk_dollar hardcodes
    # VARTYPE=8 == default double, so keying on VARTYPE alone freed `A`; ex_erase
    # now forces type=1 for a string name -> no numeric match -> IFC, A intact).
    ("erase.str.after.dim", "direct", ['DIM A(5):A(3)=7:ERASE A$'], "err"),
    # left-to-right, first-bad-name-wins (§3):
    ("erase.partial.first", "direct", ['DIM A(5):ERASE A,B'],       "err"),
    ("erase.badname.first", "direct", ['DIM B(5):ERASE Z,B'],       "err"),
    # Tier A -- syntax error (NON-differential: zerobas house-style lowercase
    # "syntax error" vs the reference's capital "Syntax error", same documented
    # deviation as every other zerobas syntax error; gated against the zb text):
    ("erase.bare.noarg",    "direct", ['ERASE'],                    "synerr"),
    ("erase.leading.comma", "direct", ['ERASE ,A'],                 "synerr"),
    ("erase.number",        "direct", ['ERASE 5'],                  "synerr"),
    ("erase.trailing.comma","direct", ['DIM A(5):ERASE A,'],        "synerr"),
    ("erase.double.comma",  "direct", ['DIM A(5):ERASE A,,B'],      "synerr"),
    ("erase.paren.form",    "direct", ['DIM A(5):ERASE A()'],       "synerr"),
    ("erase.sub.form",      "direct", ['DIM A(5):ERASE A(1)'],      "synerr"),
]

# Tier-A house-style text (zerobas prints lowercase where the reference prints
# capitalised; not differential-gateable, asserted against this literal).
ZB_SYNTAX_ERROR = "syntax error"

# Crunch-identity rows (§2): the exact stored-line token bytes. Checked BOTH ways
# (zerobas == VG-8020 reference AND == this literal), the same discipline
# basic_probe_crunch.py uses for the string keywords. $A5 = ERASE, $2C = ',' .
CRUNCH_CASES = [
    ("crunch.erase.a",  "ERASE A",   "a5204100"),
    ("crunch.erase.ab", "ERASE A,B", "a520412c4200"),
]
TXTTAB = 0xF676  # 2-byte LE pointer to the BASIC text base (both machines)


def _last_line(mode, lines):
    """The cmdline whose echo anchors the tail scrape."""
    return lines[-1] if mode == "direct" else lines[-1]


def compare(i, ref, zb):
    label, mode, lines, kind = CASES[i]
    cmd = _last_line(mode, lines)
    if kind == "value":
        rv = R.result_span(ref) if mode == "stored" else R.result_span_after_echo(ref, cmd)
        zv = R.result_span(zb) if mode == "stored" else R.result_span_after_echo(zb, cmd)
        return rv is not None and rv == zv
    if kind == "err":
        rt = R.screen_tail(ref, cmd)
        zt = R.screen_tail(zb, cmd)
        return bool(rt) and rt == zt
    if kind == "synerr":
        # NON-differential: zerobas lowercase house text (the reference prints
        # capitalised "Syntax error" -- documented deviation). Assert the zb tail
        # is exactly the house string; ref is ignored for the verdict.
        return R.screen_tail(zb, cmd) == ZB_SYNTAX_ERROR
    # "either": compare value if ref printed one, else the tail
    rv = R.result_span_after_echo(ref, cmd)
    if rv is not None:
        return rv == R.result_span_after_echo(zb, cmd)
    return bool(R.screen_tail(ref, cmd)) and R.screen_tail(ref, cmd) == R.screen_tail(zb, cmd)


def _line_tokens(raw):
    """Body token bytes (hex) of a stored line: the bytes after the 4-byte
    header (link + line number), dropping the trailing 0x00. None if the line
    never stored (a crunch that errored on entry leaves the program empty)."""
    if not raw:
        return None
    b = bytes.fromhex(raw)
    return b[4:].hex() if len(b) >= 5 else None


def crunch_check():
    """§2 crunch identity: prove ERASE tokenises byte-for-byte like the VG-8020
    AND matches the captured literal. Its own stored_line capture pass (the value/
    error cases above scrape the SCREEN; crunch reads the stored program image),
    so it runs outside run_differential. Returns (npass, ntotal)."""
    specs = [("direct", [f"1 {body}"]) for _, body, _ in CRUNCH_CASES]
    ref = R.run_cases(REF, specs, batch=True, reset=("NEW",),
                      capture=("stored_line", TXTTAB), omsx=OMSX)
    zb = R.run_cases(ZB, specs, batch=True, reset=("NEW",),
                     capture=("stored_line", TXTTAB), omsx=OMSX)
    npass = 0
    for (label, _body, want), rr, zr in zip(CRUNCH_CASES, ref, zb):
        rt, zt = _line_tokens(rr), _line_tokens(zr)
        ok = zt == want and zt == rt
        npass += ok
        tag = "PASS" if ok else "FAIL"
        detail = "" if ok else f"want={want} ref={rt} zb={zt}"
        print(f"  {tag}  {label:<22} {detail}")
    return npass, len(CRUNCH_CASES)


def main():
    specs = [(m, l) for _, m, l, _ in CASES]
    verdicts, refs, zbs = R.run_differential(
        REF, ZB, specs, compare, reset=("NEW", "CLS"), omsx=OMSX)
    npass = sum(verdicts)
    for i, (label, mode, lines, kind) in enumerate(CASES):
        cmd = _last_line(mode, lines)
        rv = (R.result_span(refs[i]) if mode == "stored"
              else R.result_span_after_echo(refs[i], cmd))
        zv = (R.result_span(zbs[i]) if mode == "stored"
              else R.result_span_after_echo(zbs[i], cmd))
        rt, zt = R.screen_tail(refs[i], cmd), R.screen_tail(zbs[i], cmd)
        tag = "PASS" if verdicts[i] else "FAIL"
        detail = f"ref={rv!r}/{rt!r}  zb={zv!r}/{zt!r}" if not verdicts[i] else ""
        print(f"  {tag}  {label:<22} {detail}")
    cpass, ctotal = crunch_check()
    npass += cpass
    total = len(CASES) + ctotal
    print(f"=== arrays: {npass}/{total} {'ALL PASS' if npass == total else 'SOME FAILED'} ===")
    return 0 if npass == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
