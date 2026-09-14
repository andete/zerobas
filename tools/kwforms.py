#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-KWTIER1 — how many FORMS a keyword must be shown to handle, per keyword.

🎚️ JOOST'S RULE (2026-09-14): a keyword reaches TIER 1 when it is knife-proven
CONNECTED, has rows covering N distinct FORMS, and carries no open TIER item --
"N should depend on the complexity of each individual keyword".

🔴 N IS AUTHORED HERE AND NOT DERIVED FROM OUR OWN HANDLER, AND THAT IS THE WHOLE
POINT. The tempting mechanical route -- count the optional-argument branches in
`basic/*.asm` -- is CIRCULAR: a keyword we implemented too simply would get a
lower bar and pass more easily, so the test would be graded against the thing
under test. The bar comes from the REFERENCE's syntax. Where the tree has no
grammar table (247 spec docs, all organised by slice, none per keyword), the form
list is written out by hand WITH ITS REASON and is reviewable as data.

🎯 A FORM IS A DISTINCT BEHAVIOUR THE VERB MUST GET RIGHT, not a distinct input.
`PSET(1,1),15` and `PSET(2,2),7` are ONE form sampled twice -- which is exactly
what the sweep held before this file existed, and why the tier table counts
DISTINCT `FORM:` tags rather than rows.

⚠️ ABSENCE FROM THIS TABLE IS NOT N=0. A keyword with no entry has no authored
bar yet, and `tier_table` must treat it as UNRATED rather than as satisfied --
the `kwcover` lesson: an instrument that reports a plausible answer from a missing
input is worse than one that refuses.
"""
from __future__ import annotations

# 🎚️ COMPOSITE STATEMENTS (Joost, 2026-09-14: "one could consider the ON + second
# keyword one composite keyword requiring its own tests"). `ON KEY GOSUB` and
# `ON n GOTO` share nothing but a token; `LINE INPUT` and `LINE (x,y)-(x,y)` are
# entirely different statements. Tiering the FIRST keyword of a statement would let
# a graphics row vouch for console input, and it is what let `ON` reach TIER 1 on
# three rows that spoke for three of its EIGHT composites.
# 🔴 MOST SPECIFIC FIRST, AND THE ORDER IS LOAD-BEARING: `ON ERROR GOTO` must win
# over `ON GOTO`, and `ON GOTO` must never match an `ON ERROR GOTO` body. Each
# pattern is the set of keywords that must ALL appear; longer sets are tried first.
# ⚠️ GROUNDED IN WHAT THIS TREE SHIPS, not in the MSX manual: every one below has a
# handler here (the ON-traps are ex_on_key / ex_on_interval / ex_on_strig /
# eos_common, basic/interp.asm:284).
COMPOSITES: tuple[tuple[frozenset[str], str], ...] = tuple(
    (frozenset(ws.split()), name) for ws, name in (
        ("ON ERROR GOTO",   "ON ERROR GOTO"),
        ("ON KEY GOSUB",    "ON KEY GOSUB"),
        ("ON STOP GOSUB",   "ON STOP GOSUB"),
        ("ON SPRITE GOSUB", "ON SPRITE GOSUB"),
        ("ON STRIG GOSUB",  "ON STRIG GOSUB"),
        ("ON INTERVAL GOSUB", "ON INTERVAL GOSUB"),
        ("ON GOSUB",        "ON GOSUB"),
        ("ON GOTO",         "ON GOTO"),
        ("LINE INPUT",      "LINE INPUT"),
        ("DEF FN",          "DEF FN"),
        ("DEF USR",         "DEF USR"),
        ("PUT SPRITE",      "PUT SPRITE"),
        ("PRINT USING",     "PRINT USING"),
    ))
COMPOSITES = tuple(sorted(COMPOSITES, key=lambda e: -len(e[0])))


def composite_name(words) -> str | None:
    """The composite statement `words` names, or None.

    `words` is the set of KEYWORDS a crunch body contains. The most specific
    pattern wins, so `{ON, ERROR, GOTO}` is `ON ERROR GOTO` and never `ON GOTO`."""
    ws = set(words)
    for need, name in COMPOSITES:
        if need <= ws:
            return name
    return None


# 🎚️ STATEMENTS NO DERIVATION CAN REACH (D-KWSUBJECT, 2026-09-14). Joost: "bare
# print and print # and print using have a different function" -- so the channel
# forms are separate subjects, and a row must be able to SAY so.
# 🔴 `composite_name` ABOVE CANNOT PRODUCE THESE, BY CONSTRUCTION: it matches sets
# of KEYWORDS, and what separates `PRINT #1,A` from `PRINT A` is the `#`, which is
# punctuation -- the crunch bodies are keyword-identical. The same holds for
# `INPUT #` vs `INPUT` and `GET #` vs a bare GET. They are listed here so that
# `tier_table.known_subject` accepts them from a `SUBJECT:` tag, and so that a
# TYPO in such a tag is refused rather than silently creating a bucket nothing
# counts. A name here is a scoreable subject; it is NOT a claim that a bar has
# been authored for it (that is `FORMS`, and absence there is UNRATED).
UNDERIVABLE: tuple[str, ...] = (
    "PRINT #",
    "INPUT #",
    "GET #",
    "PUT #",
)


# 🔴 KEYWORDS WITH NO BARE STATEMENT FORM AT ALL. Splitting composites out made
# five keywords read "no known gap, no row" -- which for these five is not a gap
# but the TRUTH ABOUT THE LANGUAGE: MSX1 has no bare `ON`, `DEF`, `GET`, `PUT` or
# `USING` statement. Every one of them exists only inside a composite, so a row of
# their own is not something that could ever be written.
# 🎯 `INPUT` IS DELIBERATELY NOT HERE, and that is the whole value of the list:
# `INPUT` lost its rows to `INPUT #` too, but bare console `INPUT "x";A$` is a real
# statement this tree implements and has NEVER had a row. Without this distinction
# both read identically and a genuine hole hides behind four false ones.
NO_BARE_FORM: frozenset[str] = frozenset(("DEF", "GET", "ON", "PUT", "USING"))


def subject_names() -> set[str]:
    """Every statement name this file knows that is not a plain keyword."""
    return {name for _, name in COMPOSITES} | set(UNDERIVABLE)


# keyword -> (forms, why this is the set)
FORMS: dict[str, tuple[tuple[str, ...], str]] = {
    "PSET": (
        ("colour-explicit", "colour-default", "step-relative", "mode-screen3"),
        "MSX1 syntax is `PSET [STEP](x,y)[,colour]`, so the switches are STEP and "
        "the optional colour; the bitmap mode is the fourth because SCREEN 3 is "
        "MULTICOLOUR with its own VRAM layout, and the plot and the read-back both "
        "take a different address calculation there. The MSX2-only logical "
        "OPERATOR argument is deliberately NOT counted -- this is an MSX1 tree.",
    ),
    "PRESET": (
        ("colour-default", "colour-explicit", "step-relative", "mode-screen3"),
        "`PRESET [STEP](x,y)[,colour]` -- the same shape as PSET, so the same four. "
        "The default form ERASES (it draws in the background) while the explicit "
        "form draws in the colour given, which is why both are forms and not one "
        "form sampled twice.",
    ),
    "COLOR": (
        ("foreground", "background", "border"),
        "`COLOR [fg][,bg][,border]` -- three POSITIONS, and the form that matters "
        "is the OMISSION: a parser that shifted `COLOR ,5` left would write the "
        "background value into the foreground. Each lands in a declared cell "
        "(FORCLR $F3E9, BAKCLR $F3EA, BDRCLR $F3EB), so all three are readable. "
        "This is deliberately a DIFFERENT SHAPE from PSET/PRESET -- positional "
        "omission rather than an optional trailing argument and a mode.",
    ),
    "MID$": (
        ("substring-3arg", "substring-to-end", "assign"),
        "MID$(s,n[,m]) reads, and MID$(A$,n,m)=s WRITES -- and the write is a SEPARATE handler (ex_mid_stmt, basic/str-engine.asm), so no read row reaches it. Three behaviours: the explicit length, the default length that runs to the end of the string, and the in-place replacement.",
    ),
    "INSTR": (
        ("search", "search-from"),
        "INSTR([start,]s1,s2) -- with and without the start position, which is a different search and not a different input: instr_b searches 'ABA' for 'A' from 2, so a start that is parsed and IGNORED finds the FIRST A and reads 1 instead of 3.",
    ),
    "DIM": (
        ("one-dimensional", "multi-dimensional"),
        "DIM <name>(<bounds>) -- one subscript or several. The multi-dimensional form has to COMBINE the subscripts into one offset, which the single-subscript form cannot exercise at all; the row reads the written cell AND the one with the subscripts SWAPPED.",
    ),
    "DEFINT": (
        ("single-letter", "letter-range"),
        "DEFINT <letter>|<letter>-<letter>[,...] -- ex_deftype (basic/usr.asm) parses range items and rejects a reversed one, so the range is a second behaviour. The comma LIST is repetition of these two, not a third form.",
    ),
    "DEFSNG": (
        ("single-letter", "letter-range"),
        "As DEFINT. WARNING: its range row must make the default WRONG first -- single precision is already the default, so DEFSNG A-C alone proves nothing. The row runs DEFINT A-C first and then measures that DEFSNG A-C undid it.",
    ),
    "DEFDBL": (
        ("single-letter", "letter-range"),
        "As DEFINT. WARNING: 1/3 is the discriminator and 1.5 is not -- 1.5 is exact in single precision too, so only a value needing the extra digits shows that the letter really became double. Measured .33333333333333, fourteen digits.",
    ),
    "DEFSTR": (
        ("single-letter", "letter-range"),
        "As DEFINT. Its range row reads a VALUE against an ERROR: without the range the assignment to C is a Type mismatch.",
    ),
    "VARPTR": (
        ("variable", "file-channel"),
        "VARPTR(<var>) and VARPTR(#<n>). AUTHORED AT 2 KNOWING THIS TREE CAN ONLY MEET 1: VARPTR(#n) is recorded as DEFERRED (docs/TODO-done.md), so VARPTR stands at 1/2 the way LOCATE stands at 3/4. The bar comes from the reference's syntax, not from what we chose to build. The variable form is scored by varptr_b and NOT by varptr, which reads VARPTR(B)>0 -- a BOOLEAN, which cannot see the address.",
    ),
    "CHR$": (
        ("code-to-char",),
        "`CHR$(<code>)` -- one argument, one behaviour.",
    ),
    "HEX$": (
        ("to-hex",),
        "`HEX$(n)` -- one argument, one behaviour.",
    ),
    "OCT$": (
        ("to-octal",),
        "`OCT$(n)` -- one argument, one behaviour.",
    ),
    "BIN$": (
        ("to-binary",),
        "`BIN$(n)` -- one argument, one behaviour.",
    ),
    "STR$": (
        ("number-to-string",),
        "`STR$(n)` -- one argument, one behaviour. The leading space MSX prints for a non-negative number is part of the reading, not furniture.",
    ),
    "LEFT$": (
        ("prefix",),
        "`LEFT$(s,n)` -- two required arguments, one behaviour.",
    ),
    "RIGHT$": (
        ("suffix",),
        "`RIGHT$(s,n)` -- the mirror of LEFT$, one behaviour.",
    ),
    "CVI": (
        ("string-to-int",),
        "`CVI(s)` -- one argument, one behaviour, the reading half of MKI$. The rows read the VALUE back through a round trip, including -1 and 32767, so the sign and the top of the range are seen.",
    ),
    "CVS": (
        ("string-to-single",),
        "`CVS(s)` -- as CVI, for single precision; `cvs_b` reads 1.5 back, so the fraction is seen and not only an integer.",
    ),
    "CVD": (
        ("string-to-double",),
        "`CVD(s)` -- as CVI, for double precision; `cvd_b` reads .1 back.",
    ),
    "LET": (
        ("assign",),
        "`LET <var>=<expr>` -- one behaviour. MSX allows the keyword to be omitted, but that is the ABSENCE of this statement rather than a second form of it.",
    ),
    "REM": (
        ("comment",),
        "`REM <anything>` -- one behaviour: the rest of the line is skipped. The row's discriminator is that `REM z` raises NO error, which a REM that did not skip would.",
    ),
    "STOP": (
        ("break",),
        "`STOP` -- no arguments, one behaviour. The row's discriminator is the `Break in 10` message, not the marker before it.",
    ),
    "END": (
        ("terminate",),
        "`END` -- no arguments, one behaviour. The row puts statements AFTER the END that would change the answer if it did not stop, so a parsed-and-ignored END is visible.",
    ),
    "SPACE$": (
        ("pad",),
        "`SPACE$(n)` -- one argument, one behaviour. ⚠️ N=1 is earned by `space_b`, which reads the BYTES: the original row reads `LEN(SPACE$(3))`, and a LENGTH cannot see CONTENT.",
    ),
    "MKI$": (
        ("int-to-string",),
        "`MKI$(n)` -- one argument, one behaviour. ⚠️ Same axis: `mki` reads only the LENGTH, which any two bytes pass. `mki_b` reads both bytes of 258 = $0102, so the VALUE and the BYTE ORDER are seen.",
    ),
    "ERASE": (
        ("free-array",),
        "`ERASE <array>` -- one behaviour. ⚠️ The original row prints a constant `[ok]`; `erase_b` reads the EFFECT, which is that the name becomes free to DIM again.",
    ),
    "LINE": (
        ("segment", "box", "filled-box", "step-relative", "omitted-start",
         "colour-default"),
        "`LINE [[STEP](x1,y1)] - [STEP](x2,y2) [,[c][,B|BF]]` (basic/graphics.asm). "
        "Six behaviours, and the three suffix forms really are three: a segment, an "
        "outlined box and a FILLED box are different drawings between the same two "
        "points. The first coordinate is OPTIONAL -- omitted, it continues from the "
        "last point (GRPAC) -- which is a form no other graphics verb here has. "
        "This is the widest N in the table and it should be: LINE has more distinct "
        "shapes than any other MSX1 graphics statement.",
    ),
    "POINT": (
        ("pixel-read",),
        "`POINT(x,y)` -- one argument pair, one behaviour. The bar is met only "
        "because `pointkw_b` reads a pixel that was NEVER set as well as one that "
        "was: the original row read back the pixel it had just drawn, which a POINT "
        "returning a constant passes.",
    ),
    "VPEEK": (
        ("address-read",),
        "`VPEEK(<vram address>)` -- one argument, one behaviour, the reading half "
        "of VPOKE. The row writes a known byte with VPOKE and reads it back, so it "
        "cannot pass on a constant.",
    ),
    "CSRLIN": (
        ("row-read",),
        "`CSRLIN` takes no argument and reports the cursor ROW -- one behaviour. "
        "⚠️ N=1 is met by `csrlind`, which reads the DELTA across a PRINT rather "
        "than the absolute row: the absolute value is ambient scroll state and the "
        "unanchored row measured the boot banner, not the keyword.",
    ),
    "POS": (
        ("column-read",),
        "`POS(<dummy>)` reports the cursor COLUMN -- one behaviour. The row prints "
        "four spaces first, so the answer is a known non-zero column and not the "
        "0 an auto-dimmed array would give.",
    ),
    "LPOS": (
        ("column-read",),
        "`LPOS(<dummy>)` is the printer's head column, the same shape as POS. "
        "🔴 THE `LPRINT` IS THE ROW: a bare `LPOS(0)` reads 0, which is exactly "
        "what a stub reads, and that left the word unattributed once already.",
    ),
    "INP": (
        ("port-read",),
        "`INP(<port>)` -- one argument, one behaviour. N=1, and the row that earns "
        "it is `inp_b`: the original `INP(&HA8)>0` is a BOOLEAN and passes on any "
        "wrong non-zero read, which is the fourth screening axis and was INP's "
        "only evidence.",
    ),
    "TRON": (
        ("toggle",),
        "`TRON` takes no arguments, so one form. The bar is met by `tron_b`, which "
        "reads the TRACE ITSELF -- the original row printed a constant `[ok]` that "
        "a TRON doing nothing prints just as happily (the third screening axis).",
    ),
    "TROFF": (
        ("toggle",),
        "`TROFF` likewise. ⚠️ Its row needs a line AFTER the TROFF, because the "
        "trace prints a line number BEFORE executing that line -- so the line "
        "carrying TROFF is traced whether or not TROFF works.",
    ),
    "CIRCLE": (
        ("centre-radius", "arc", "step-relative", "aspect", "colour-default"),
        "`CIRCLE [STEP](x,y),r[,[c][,[start][,[end][,aspect]]]]` (basic/graphics.asm). "
        "Five behaviours: the plain circle, the start/end ARC, the STEP-relative "
        "centre, the ASPECT that turns it into an ellipse, and the omitted colour "
        "that must come from FORCLR. N is 5 and not 4 because the aspect changes "
        "the SHAPE while the arc changes only which part is drawn -- a handler can "
        "get either right and the other wrong.",
    ),
    "POKE": (
        ("address-value",),
        "`POKE <address>,<value>` -- two REQUIRED arguments and no optional part, "
        "no mode and no coordinate, so the whole surface is one form. The row "
        "reads the byte back through PEEK, so a POKE that parsed and wrote nothing "
        "fails; that is what makes N=1 a bar rather than a formality.",
    ),
    "VPOKE": (
        ("address-value",),
        "`VPOKE <vram address>,<value>` -- the same shape as POKE and the same N. "
        "🔴 `vpoke_b` (the last byte of VRAM) and `vpoke_b2` (the maximum value) "
        "are SAMPLES of this one form, not extra forms, and they are tagged with "
        "the same name on purpose: counting them separately would let three "
        "readings of one behaviour satisfy an N of three.",
    ),
    "OUT": (
        ("port-value",),
        "`OUT <port>,<value>` -- two required arguments, one behaviour. `out_b` "
        "reads the delivered byte back through the PSG's own readback port, which "
        "is what separates it from `outkw`, a row that writes only the address "
        "latch and never looks.",
    ),
    "SOUND": (
        ("register-value",),
        "`SOUND <register>,<value>` -- one behaviour, and writing register 7 is "
        "not a different form from writing register 0, only a different input. "
        "`sound_b` reads the byte back out of the PSG.",
    ),
    "VDP": (
        ("read", "write"),
        "`VDP(n)` is BOTH an expression and an assignment TARGET, and the two are "
        "different handlers -- the `$C8` selector in basic/expr.asm and "
        "`ex_vdp_assign` in basic/interp.asm. A read row cannot speak for the "
        "write at all, which is exactly the case N is meant to catch. ⚠️ NEITHER "
        "form can see the CHIP: MSX VDP registers are write-only, so every reader "
        "sees the RGnSAV mirror. The bar is the two ACCESS PATHS, and that limit "
        "is stated in the write row rather than left for someone to assume away.",
    ),
    "TIME": (
        ("read", "write"),
        "`TIME` is a pseudo-variable with a read selector (`$CB`) and a separate "
        "write handler (`ex_time_assign`), so the two halves are two forms. "
        "⚠️ THE READ ROW IS A BOOLEAN AND HAS TO BE: zerobas is 2.5-3.8x slower "
        "than the reference (the open TIER 4 item), so a delay loop's TIME VALUE "
        "would diverge on INTERPRETER SPEED and be reported as a TIME defect. The "
        "VALUE is scored by the write row, which reads back what it wrote and has "
        "no speed dependence.",
    ),
    "BEEP": (
        ("no-argument",),
        "MSX1 `BEEP` takes NO arguments, so its whole surface is one form and N=1 "
        "is the honest bar rather than a low one. What makes the evidence "
        "non-vacuous is not a second form but what the row READS: `beep_b` scores "
        "the PSG mixer register BEEP restores (184 where the same program without "
        "it reads 191), so a BEEP that parsed and did nothing fails.",
    ),
    "CLS": (
        ("no-argument",),
        "`CLS` takes no arguments either. Same shape as BEEP and the same answer "
        "to the same objection: `clskw` reads CSRLIN back, because a bare marker "
        "would have been printed just as happily by a CLS that parsed and did "
        "nothing -- scoring the parse and calling it the behaviour.",
    ),
    "WIDTH": (
        ("text-width", "mode1-width"),
        "`WIDTH <columns>` has one argument and no optional parts, so the second "
        "form is not a second argument -- it is a second CELL. MSX keeps the width "
        "per mode (LINL40 $F3AE for SCREEN 0, LINL32 $F3AF for SCREEN 1) and WIDTH "
        "writes whichever belongs to the current mode, so a handler that always "
        "wrote LINL40 passes the first and fails the second. N is 2 because the "
        "mode is the only dimension this verb has.",
    ),
    "LOCATE": (
        ("column", "row", "omitted-column", "cursor-switch"),
        "`LOCATE [X][,Y][,switch]` -- the COLOR shape (positional omission) with a "
        "third argument on top. The omission is a form in its own right because an "
        "omitted axis KEEPS its value, so a parser that shifted left would write "
        "the row's value into the column. ⚠️ THE CURSOR SWITCH IS AUTHORED EVEN "
        "THOUGH THIS TREE CANNOT PASS IT: basic/missing.asm records O-3, the third "
        "argument is parsed and domain-checked and then IGNORED because nothing "
        "here reads CSRSW. The bar comes from the REFERENCE's syntax, so a form we "
        "chose not to implement leaves LOCATE short of TIER 1 -- which is the "
        "measurement working, not a bookkeeping problem to tidy away.",
    ),
    "SCREEN": (
        ("mode", "sprite-size", "key-click"),
        "MSX1 `SCREEN [mode][,sprite size][,key click][,baud][,printer]`. The "
        "first three are the ones a 1985 listing uses; the cassette baud rate and "
        "printer type are deliberately NOT counted, being rig settings rather than "
        "screen behaviour. ⚠️ Like LOCATE, this is authored ahead of what the tree "
        "can show: the sprite size is real (G7_RESIDENT, read back through RG1SAV) "
        "and the key click has no cell any row can read here.",
    ),
    "CLEAR": (
        ("bare", "string-space", "himem"),
        "MSX1 syntax is `CLEAR [<string space>[,<himem>]]`, so the whole surface is "
        "three: the bare form (which resets variables), the string-space argument, "
        "and the HIMEM ceiling. There is no fourth -- unlike PSET this verb has no "
        "mode or coordinate dimension, which is why N is 3 here and 4 there.",
    ),
}


def forms_for(kw: str) -> tuple[str, ...] | None:
    """The authored form list for `kw`, or None when no bar has been authored."""
    e = FORMS.get(kw)
    return e[0] if e else None


def n_for(kw: str) -> int | None:
    """N for `kw`, or None when UNRATED (no entry). None is not zero."""
    f = forms_for(kw)
    return len(f) if f else None
