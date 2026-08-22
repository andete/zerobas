#!/usr/bin/env python3
"""DEF FN SCOUT, round 1 — what does the reference STORE?

`make kwsweep` at `4b2c5a5`: MISSING=1, and it is `deffn`.
    DEF FNA(X)=X+1:PRINT"[";FNA(2);"]"   ref '[ 3 ]'   zb 'Syntax error in 10'
It is the ONLY genuinely missing MSX1 reserved word, and `TODO.md` has carried
its price as *"an arc, not a slice (200-400 B): a definition table, argument
binding, re-entrant evaluation"* — an ASSERTION that has never been measured.
SCREEN 3 sat in exactly that position ("unpriced, NEVER SCOUTED") until it was
priced and FIT, so the first job is to stop guessing.

🎯 AND THE FIRST THING TO MEASURE IS THE CRUNCH, NOT THE BEHAVIOUR. D-FNRUN's
whole finding was that a filed DECLINE was refuted by the STORED TOKEN BYTES:
what a statement costs is decided by what the tokeniser has to emit, and this
tree has no `FN` token at all (`basic/kwtable.inc` has a row for "DEF" and none
for "FN"). Whether `FN` is its own token, whether `DEF FN` is one token or two,
and whether the NAME is stored as ASCII or as a variable reference are all
questions the reference answers by what it puts in memory.

⚠️ THE PROGRAM IS NEVER RUN. The dump starts at line 100, so lines 10/20 are
crunched and stored but never executed -- which is the only way to read zerobas's
crunch of a statement it cannot execute. `TXTTAB` ($F676) is read at run time
rather than assumed, because the program area start differs between a
disk-equipped machine and a bare one.
"""
from __future__ import annotations
import os, re, sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_M, boot=8.0, reset=("NEW",)),
}
_only = os.environ.get("DEFFN_SIDES")
if _only:
    SIDES = {k: v for k, v in SIDES.items() if k in _only.split(",")}

# the dumper: read TXTTAB, then 4 rows of 16 bytes as hex, each fenced so the
# scrape can find it even if the screen wraps around it
# 🔴 THE DUMP IS A DIRECT-MODE COMMAND, NOT PART OF THE PROGRAM. Round 1 put it
# at lines 100..140 and ran `RUN 100`, and on zerobas that returned NOTHING with
# the raw screen reading `Syntax error in 10` -- so a line the dump was supposed
# to READ stopped the dump from running at all. A stored line this build cannot
# execute must be read WITHOUT executing anything, which direct mode does.
# ⚠️ The echo of this command cannot be mistaken for its output: the fence wants
# exactly 32 hex digits between < and >, which the source text does not contain.
DUMP_DIRECT = ('T=PEEK(&HF676)+256*PEEK(&HF677):FORJ=0TO3:S$="":FORI=0TO15:'
               'S$=S$+RIGHT$("0"+HEX$(PEEK(T+J*16+I)),2):NEXT:'
               'PRINT"<";S$;">":NEXT')

SUBJECTS = {
    # the kwsweep row itself, split so the definition and the call are separate
    # stored lines and their bytes can be told apart
    "deffn.basic":  ["10 DEF FNA(X)=X+1", "20 PRINT FNA(2)"],
    # a two-letter name and a different parameter letter: says whether the name
    # is stored as ASCII characters or as something narrower
    "deffn.name2":  ["10 DEF FNQZ(Y)=Y*2", "20 PRINT FNQZ(3)"],
    # 🟢 CONTROL: `DEF USR` already exists here and already crunches. If its bytes
    # match on all three sides, the dumper and the DEF token are fine and any
    # divergence in the FN rows is about FN.
    "defusr.ctl":   ["10 DEF USR=&HC000", "20 PRINT USR(0)"],
    # ...and a plain expression with a variable call-shape, so "A(2)" as an ARRAY
    # reference can be told from "FNA(2)" as a function call in the crunch.
    "array.ctl":    ["10 DIM A(5)", "20 PRINT A(2)"],
}

# ===========================================================================
# ROUND 2 — the SEMANTICS, because they are what the price is made of.
#
# 🎯 ROUND 1 DECODED, and the two controls (`defusr.ctl`, `array.ctl`) are
# BYTE-IDENTICAL on all three sides, so the dumper and the DEF path are sound and
# any FN divergence is about FN:
#
#   10 DEF FNA(X)=X+1   ->  97 20 DE 41 28 58 29 EF 58 F1 12 00
#                           DEF sp FN  A  (  X  )  =  X  +  1  eol
#   10 DEF FNQZ(Y)=Y*2  ->  97 20 DE 51 5A 28 59 29 EF 59 F3 13 00
#   10 DEF USR=&HC000   ->  97 20 DD EF 0C 00 C0 00
#
# `FN` IS ONE TOKEN, $DE -- the byte immediately after `USR`'s $DD, which this
# tree already emits and already dispatches. The NAME is stored as plain ASCII
# after the token, arbitrary length, exactly like a variable name; there is no
# name table in the crunch. That already contradicts half of the filed price
# ("a definition table"): the reference keeps the definition wherever it keeps
# variables, and reads the name out of the program text at run time.
#
# ⚠️ SO THE REMAINING COST IS RUNTIME SEMANTICS, AND EVERY ONE OF THESE ROWS
# CHANGES THE DESIGN. Whether the parameter is a REAL variable that survives the
# call decides whether a save/restore is needed at all; whether more than one
# parameter is legal decides whether there is a list walk; whether a string form
# exists decides whether the entry is typed. Guessing any of them from the
# manual is how a filed price gets to be wrong by 3x.
# 🔴 ROUND 2's READOUT WAS BROKEN AND ITS OWN CONTROL CAUGHT IT. Every one of the
# eleven rows came back as the SOURCE TEXT -- `b.ctl` returned '";X+1;"' -- because
# the fixture ended in `PRINT"[";V;"]"` typed in DIRECT mode, so the line's ECHO
# sits on the screen containing `[";V;"]`, and the `[...]` regex found THAT. All
# eleven "agreed" and not one was a measurement.
# 🎯 THE FIX IS THE ONE THE PAINT PROBES ALREADY USE: clear the screen between the
# echo and the print. Each case is now (setup lines, the expression to capture),
# and the harness appends `CLS:PRINT"[";<expr>;"]"` on its own line -- so the only
# `[...]` left on the screen is the answer. The error handler clears too.
# 🟢 `b.ctl` stays, and it is now load-bearing twice: it says the fixture runs AND
# that the readout reads the output rather than the source.
BEHAV: dict[str, tuple[list[str], str]] = {
    # does calling FNA(2) clobber a REAL variable X? MS BASIC binds through the
    # ordinary variable table, which would leave X = 2, not 5.
    "b.param":    (['X=5:DEF FNA(X)=X+1', 'Y=FNA(2)'], 'Y;X'),
    # ...and the same question when the parameter name is NOT otherwise used
    "b.paramnew": (['DEF FNA(Q)=Q+1', 'Y=FNA(7)'], 'Y;Q'),
    # calling an undefined function -- which ERR?
    "b.undef":    ([], 'FNZ(1)'),
    # ...and calling one defined on a LATER line (never executed yet)
    "b.forward":  (['GOTO 60', 'DEF FNA(X)=X+1'], 'FNA(2)'),
    # a string-typed function
    "b.str":      (['DEF FNA$(X$)=X$+"!"'], 'FNA$("hi")'),
    # more than one parameter: legal, or Syntax error?
    "b.two":      (['DEF FNA(X,Y)=X+Y'], 'FNA(2,3)'),
    # no parameter at all
    "b.noarg":    (['DEF FNA=7'], 'FNA'),
    # redefinition
    "b.redef":    (['DEF FNA(X)=X+1', 'DEF FNA(X)=X+2'], 'FNA(1)'),
    # one function calling another -- says whether evaluation must be re-entrant
    "b.nested":   (['DEF FNA(X)=X+1', 'DEF FNB(X)=FNA(X)*2'], 'FNB(3)'),
    # direct recursion -- what the reference DOES, not what it should
    "b.recurse":  (['DEF FNA(X)=FNA(X)'], 'FNA(1)'),
    # 🟢 CONTROL: an ordinary expression through the same fixture shape.
    "b.ctl":      (['X=5'], 'X+1'),
}

BR = re.compile(r"\[([^\]]*)\]")
ERRRE = re.compile(r"^\s*([A-Z][A-Za-z' ]+ error|Illegal function call|Overflow|"
                   r"Out of memory|Type mismatch|Subscript out of range|"
                   r"Undefined user function|Redimensioned array)", re.M)


def face(cap):
    if cap is None:
        return "<NO CAPTURE>"
    m = BR.search("".join(cap))
    if m:
        return " ".join(m.group(1).split()) or "<empty>"
    e = ERRRE.search("".join(cap))
    return f"<{e.group(1).strip()}>" if e else "<NO OUTPUT>"


def run_behav(label) -> None:
    lines, expr = BEHAV[label]
    body = ["10 ON ERROR GOTO 900"]
    body += [f"{20 + 10 * k} {ln}" for k, ln in enumerate(lines)]
    # 🔴 ROUND 3's CAPTURE LINE WAS ITSELF A SYNTAX ERROR ON TWO ROWS. It built
    # `60 V=<expr>`, and `b.param`'s expr is `Y;X` -- two values, which is PRINT
    # syntax and not an expression -- so both references reported ERR 2 AT 60 and
    # the row read as a divergence about DEF FN. It was a divergence about the
    # harness. The expression now goes straight into the PRINT, after the CLS
    # that removes the echoes, so any number of values is fine and nothing is
    # assigned on the way.
    body += [f'60 CLS:PRINT"[";{expr};"]":END']
    body += ['900 CLS:PRINT"[ERR";ERR;"AT";ERL;"]":END']
    row = {}
    for side, cfg in SIDES.items():
        caps = omsx_repl.run_cases(
            cfg["machine"], [("direct", list(cfg["reset"]) + body + ["RUN"])],
            batch=False, boot=cfg["boot"], step=8.0, cap_gap=10.0, timeout=300.0)
        row[side] = face(caps[0])
        print(f"  {side:7s} {label:11s} -> {row[side]!r}", flush=True)
        if os.environ.get("DEFFN_RAW"):
            print("      RAW " + repr((caps[0] or "")[-400:]), flush=True)
    if "vg8020" in row and "cf3300" in row:
        agree = "refs-agree" if row["vg8020"] == row["cf3300"] else "REFS DIFFER"
        zbm = ("zb=" + ("same" if row.get("zb") == row["vg8020"] else "DIFF")
               if "zb" in row else "zb=<not run>")
    else:
        agree, zbm = "one-ref-only", "no ref this round"
    print(f"  ROW {label:11s} {agree:12s} {zbm}\n", flush=True)


FENCE = re.compile(r"<([0-9A-Fa-f]{32})>")


def dump(cap):
    """Rows of hex, TRUNCATED at the end-of-program marker.

    🔴 THE UNTRUNCATED VERSION SCORED RAM GARBAGE AS A DIVERGENCE, and the proof
    is a control that changed verdict with its subject unchanged: `defusr.ctl`
    read BYTE-IDENTICAL on all three sides in round 1 and `REFS DIFFER` in
    round 3, on the same program. Nothing about DEF USR moved between those
    rounds -- what moved is that the dump began in direct mode, so the bytes
    AFTER the stored program (the direct-line buffer and uninitialised RAM)
    landed inside the compared window. A control that flips without its subject
    moving is a statement about the instrument.
    🎯 A stored MSX program ends at a line whose 2-byte LINK is $0000, so the
    program is everything up to and including the first `00 00` that follows a
    line's terminating `00`. Everything past it is not ours to compare.
    """
    if cap is None:
        return None
    txt = "".join(cap)
    rows = FENCE.findall(" ".join(txt.split()))
    if not rows:
        return None
    b = bytes.fromhex("".join(rows))
    end = len(b)
    i = 0
    while i + 1 < len(b):                       # walk the link chain
        link = b[i] | (b[i + 1] << 8)
        if link == 0:
            end = i + 2
            break
        nxt = i + (link - (b[0] | (b[1] << 8)) + 0)  # links are absolute
        # absolute links: convert by walking to the next 00-terminated line
        j = i + 4
        while j < len(b) and b[j] != 0:
            j += 1
        i = j + 1
    else:
        end = len(b)
    return [b[:end].hex().upper()]


def main() -> int:
    want = sys.argv[1:] or list(SUBJECTS) + list(BEHAV)
    for label in want:
        if label in BEHAV:
            run_behav(label)
            continue
        prog = SUBJECTS[label] + [DUMP_DIRECT]
        row = {}
        for side, cfg in SIDES.items():
            caps = omsx_repl.run_cases(
                cfg["machine"], [("direct", list(cfg["reset"]) + prog)],
                batch=False, boot=cfg["boot"], step=8.0, cap_gap=10.0, timeout=300.0)
            row[side] = dump(caps[0])
            print(f"  {side:7s} {label:12s} {row[side]}", flush=True)
            if os.environ.get("DEFFN_RAW"):
                print("      RAW " + repr((caps[0] or "")[-500:]), flush=True)
        if "vg8020" in row and "cf3300" in row:
            agree = "refs-agree" if row["vg8020"] == row["cf3300"] else "REFS DIFFER"
            zbm = ("zb=" + ("same" if row.get("zb") == row["vg8020"] else "DIFF")
                   if "zb" in row else "zb=<not run>")
        else:
            agree, zbm = "one-ref-only", "no ref this round"
        print(f"  ROW {label:12s} {agree:12s} {zbm}\n", flush=True)
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
