#!/usr/bin/env python3
r"""D-CSAVEEXPR — does the reference take a string EXPRESSION in CSAVE / CLOAD?

`do_csave` and `do_cload` keep a `cp '"'` gate: a literal filename only. Every
other filename verb takes a string expression as of D-FNEXPR2. The entry says the
apparatus is the obstacle, not the price -- these are CASSETTE verbs, so the
reading needs a tape, and the batteries that can drive one are the cassette ones.

So this borrows `basic_probe_cassave.py`'s fixture: a FRESH recording tape per
row (`cassetteplayer new`), one row per run_cases call.

🔴 IT READS THE SCREEN, NOT `ERR`, AND THE FIRST CUT GOT THAT WRONG. `do_csave`
rejects a non-literal with `load_error`, which PRINTS and does not RAISE -- so
`ON ERROR` never fires and an `ERR`-reading probe scores a refused statement as
**0, accepted**. Every zerobas row came back 0 and the filed "literal only" claim
looked stale; the gate is still in the source. `load error` is zerobas's own
message and the machine carries on, which is exactly the reading that hid four
divergences in the channel verbs.

🔴 AND THE DIRECT-MODE REWRITE FAILED THE OTHER WAY. It mapped an EMPTY capture
to "accepted", so every row -- including `CSAVE 5`, which both references raise
ERR 13 for -- read as accepted. Absence of capture is not absence of error. That
is why this now reports TWO INDEPENDENT CHANNELS, trap and screen, and says so
when they disagree: a non-raising error is invisible to the first and a missing
capture is invisible to the second.

🔴 AND THE `<...>` FENCE MATCHED THE ECHOED SOURCE. `PRINT"<";ERR;">"` contains
`<` and `>` in its own text, so on the CLOAD rows -- where CLOAD WIPES THE STORED
PROGRAM and the handler with it -- the regex found `";ERR;"` in the echo of the
line and reported it as a value. Both faults are why this runs in DIRECT mode and
reads the span after each statement's own echo.
"""
import os, re, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW")),
    "zb": dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                      "C-BIOS_MSX1_EU_REPACK_DISK"),
               boot=8.0, step=2.5, reset=("NEW",)),
}
CASES = [
    ("c.lit",    'CSAVE"P"',   'CONTROL: the literal form, accepted on all three'),
    ("s.var",    'CSAVE A$',   'THE SUBJECT: a string VARIABLE'),
    ("s.expr",   'CSAVE A$+""','a string EXPRESSION'),
    ("s.bare",   'CSAVE',      "CSAVE's OPTIONAL argument"),
    ("s.num",    'CSAVE 5',    'a NUMERIC operand'),
    # ⚠️ csav_noname SERVES THREE FORMS, and "bare CSAVE must raise" would change
    # all of them. These separate the one the reference rejects from the ones it
    # may accept -- without them the fix is specified on one row out of three.
    ("s.speed",  'CSAVE,2',    'NO NAME but a speed -- the same csav_noname path'),
    ("s.colon",  'CSAVE:',     'no name, followed by a colon -- also csav_noname'),
    ("c.namesp", 'CSAVE"P",2', 'CONTROL: name AND speed, the fully-formed case'),
]


def trap(side, stmt):
    """Channel 1: does `ON ERROR` see it? Blind to a NON-RAISING `load error`."""
    cfg = SIDES[side]
    wav = os.path.join(tempfile.mkdtemp(prefix="zb_csx_"), "t.wav")
    prog = ['10 A$="P"', '20 ON ERROR GOTO 90', f'30 {stmt}',
            '40 PRINT"ZQ0QZ":END', '90 PRINT"ZQ";ERR;"QZ":END', 'RUN', '@WAIT20']
    raw = "".join(omsx_repl.run_cases(
        cfg["machine"], [("direct", list(cfg["reset"]) + prog)], batch=False,
        reset=(), boot=cfg["boot"], step=cfg["step"], cap_gap=12.0, timeout=300.0,
        prologue=(f"cassetteplayer new {{{wav}}}",))[0] or "")
    # ⚠️ THE MARKERS ARE `ZQ..QZ`, NOT `<..>`: the fence must not occur in the
    # SOURCE it echoes, or the regex reads the typed line as a value.
    # 🔴 TWO MARKER FAULTS, BOTH FOUND BY THIS CHANNEL SAYING THE SAME THING FOR
    # EVERY ROW. (1) MSX prints a number with surrounding spaces, so `ZQ13QZ`
    # never matches -- it is `ZQ 13 QZ`. (2) The no-error marker occurs in the
    # SOURCE, so its echo satisfied the check on every row including the ones
    # that errored. Read only the span AFTER the `RUN` echo, and let both arms
    # use the SAME fence so the value distinguishes them.
    span = omsx_repl.result_span_after_echo(raw, "RUN") or ""
    m = re.findall(r"ZQ\s*(\d+)\s*QZ", span)
    if not m:
        return "<NO READING>"
    return "no trap" if m[-1] == "0" else f"ERR {m[-1]}"


def screen(side, stmt):
    """Channel 2: what did the machine PRINT? Sees `load error`; needs a prompt."""
    cfg = SIDES[side]
    wav = os.path.join(tempfile.mkdtemp(prefix="zb_csy_"), "t.wav")
    lines = list(cfg["reset"]) + ['A$="P"', stmt, "@WAIT20", 'PRINT"ZQ7"']
    raw = "".join(omsx_repl.run_cases(
        cfg["machine"], [("direct", lines)], batch=False, reset=(),
        boot=cfg["boot"], step=cfg["step"], cap_gap=12.0, timeout=300.0,
        prologue=(f"cassetteplayer new {{{wav}}}",))[0] or "")
    if "ZQ7" not in raw:
        return "<NO PROMPT>"
    for word in ("Syntax error", "Type mismatch", "Missing operand",
                 "load error", "Device I/O error", "Illegal function call"):
        if word.lower() in raw.lower():
            return word
    return "silent"


w = max(len(l) for l, _, _ in CASES)
print(f"\n{'row':<{w}}  {'vg8020':>26}  {'cf3300':>26}  {'zb':>26}")
for lab, st, why in CASES:
    cells = []
    for side in ("vg8020", "cf3300", "zb"):
        t, sc = trap(side, st), screen(side, st)
        cells.append(f"{t} / {sc}")
    tag = "refs agree" if cells[0] == cells[1] else "🔴 REFS SPLIT"
    zb = "" if cells[1] == cells[2] else "  zb DIFF"
    print(f"{lab:<{w}}  " + "  ".join(f"{c:>26}" for c in cells) + f"   {tag}{zb}")
    print(f"{'':<{w}}  {st}   -- {why}")
print("\nread: `trap / screen`. A NON-RAISING error reads `no trap / load error` --"
      "\nneither channel alone can say that, which is why both are printed.")
