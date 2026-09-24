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
        ("MAX FILES",       "MAX FILES"),
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
    # 🔴 `INPUT$` IS NOT A KEYWORD IN THE TOKEN TABLE AND MUST STILL BE A SUBJECT.
    # basic/kwtable.inc says it outright: for MKI$ "the '$' is PART of the keyword,
    # UNLIKE INPUT$" -- MSX tokenises `INPUT` and the `$` separately, so the table
    # rightly holds only INPUT. But `INPUT$(n)` is a FUNCTION with its own
    # evaluator (str_inputd, basic/strvar.asm) and nothing to do with the INPUT
    # statement, so a reading of it scored for INPUT would be attributing a
    # function's gap to a statement. Without this entry it scored for NOBODY.
    "INPUT$",
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
# 🎚️ SYNTAX PARTICLES (Joost, 2026-09-14: *"Drop them and mark them"*). These
# appear ONLY as syntax INSIDE another statement and have no behaviour of their
# own: there is no `THEN` statement, only `IF ... THEN`. They belong in the TOKEN
# denominator (the reference tokenises them, so we must too) and NOT in the
# STATEMENT one, where they were inflating the count with things a user cannot
# write.
# ⚠️ THE OPERATORS ARE DELIBERATELY NOT HERE. `AND OR NOT XOR EQV IMP MOD` are
# also never statements, but unlike a particle each has BEHAVIOUR OF ITS OWN worth
# tiering -- `A AND B` has a truth table to get right, `THEN` has nothing to get
# right. They stay in the statement set, marked as operators.
# 🔴 `AS` IS NOT IN THE TABLE. It is part of `OPEN ... AS #n` and `FIELD ... AS`
# but this tree's kwtable.inc does not tokenise it separately -- measured, not
# assumed, and the reason this list is five and not six.
PARTICLES: frozenset[str] = frozenset(("THEN", "ELSE", "TO", "STEP", "OFF"))

# 🎚️ OPERATORS -- kept in the statement denominator, marked so the table does not
# call them statements. See PARTICLES above for why the two classes are split.
OPERATORS: frozenset[str] = frozenset(
    ("AND", "OR", "NOT", "XOR", "EQV", "IMP", "MOD"))

# 🎚️ REFUSE-ON-SIGHT WORDS (Joost, 2026-09-14: *"Drop them and mark them"*, the
# same ruling he gave the particles). `SET`, `IPL` and `CMD` answer **ERR 5 on BOTH
# REFERENCES** -- they are tokenised, and then the handler refuses. They therefore
# have NO HAPPY PATH ON THIS MACHINE AT ALL, and a TIER 1 bar reading "refuses
# correctly" would be a TIER 5 reading wearing a TIER 1 label.
# 🎯 So they are counted as TOKENS -- the reference tokenises them, so we must --
# and marked in the table under their own class, rather than sitting in the
# STATEMENT denominator as three things that can never be awarded.
# ⚠️ MEASURED, NOT ASSUMED: each row's note records the reading. `set` is
# "ERR 5 on every machine with a disk ROM and on the diskless VG-8020 too"
# (D-DONOTHING3), `ipl` is "Illegal function call on the CF-3300 as well as on
# zerobas", `cmd` is "the third refuse-on-sight word; ERR 5 on both references".
# ⚠️ `ATTR$` JOINED 2026-09-14 (D-KWSIX). `sysvars.inc` says it outright:
# `ATTR_TOKEN equ $E9 ; ATTR$ — tokenised, then ERR 5 (no function)`, and the
# row's own note agrees: *"bare ATTR$ raises Illegal function call -- so the word
# IS a token here"*. Tokenised and refused is the same shape as SET/IPL/CMD.
# ⚠️ `CALL` JOINED 2026-09-17 (D-AKCM, scratchpad/akcm_probe.py). `CALL FOO`,
# the `_FOO` shorthand and a bare `CALL` are **ERR 2 on BOTH references** and
# here. `CALL <name>` is a real MSX statement -- it dispatches to an EXTENSION
# ROM -- and on a bare MSX1 there is none to dispatch to, so the word has no
# happy path on this machine. Same conclusion as SET/IPL/CMD, by a different
# error: those are tokenised and refused with ERR 5, this one has nothing to
# call. 🔴 ITS ONLY ROW (`callkw`) AGREES ON THAT ERROR, which is precisely what
# this tree does not award on.
REFUSE_ONLY: frozenset[str] = frozenset(("SET", "IPL", "CMD", "ATTR$", "CALL"))

# ⚠️ `MAX` JOINED 2026-09-14 (D-KWSIX): `MAX_TOKEN equ $CD ; MAX — 1st half of
# MAXFILES (statement: MAX FILES = n)`, and kwtable holds `MAX` and `FILES` as
# SEPARATE one-byte words. There is no bare `MAX` statement -- the row's note says
# *"bare MAX is a Syntax error on a real machine"* -- so it is `ON`'s shape exactly,
# and `MAX FILES` is the composite.
NO_BARE_FORM: frozenset[str] = frozenset(
    ("DEF", "GET", "ON", "PUT", "USING", "MAX"))


def subject_names() -> set[str]:
    """Every statement name this file knows that is not a plain keyword."""
    return {name for _, name in COMPOSITES} | set(UNDERIVABLE)


# 🎚️ COMPOSITE AND CHANNEL STATEMENTS ARE FIRST-CLASS (Joost, 2026-09-14: of the
# tier doc's "deliberately not in the 159-keyword denominator" -- *"why not? They
# should have the same TIER and tests"*). Their bars are authored here beside the
# keywords', from the same source: the REFERENCE's syntax.

# keyword -> (forms, why this is the set)
FORMS: dict[str, tuple[tuple[str, ...], str]] = {
    # 🎚️ THE REFUSE-ON-SIGHT WORDS, BARRED HERE BY JOOST'S 2026-09-17 REFINEMENT:
    # *"works correctly in the happy path, unless there is no happy path in which
    # case it works correctly in the normal failing path"*. Each of these HAS a
    # normal path -- it is the refusal -- so each can reach TIER 1 by matching the
    # reference's error, and each is back in the STATEMENT denominator.
    # 🔴 N = 1 FOR ALL FIVE, AND THAT IS THE POINT, NOT LAZINESS. A form is a
    # distinct BEHAVIOUR, not a distinct input, and these words have exactly one
    # behaviour on this machine. More spellings would all read THE SAME ERROR --
    # `SET PASSWORD` and `SET SCREEN` are one refusal sampled twice -- and awarding
    # on a second row that agrees for the same reason is the thing this tree does
    # not do.
    "SET": (
        ("refuse",),
        "`SET <anything>` is Illegal function call on BOTH references and here "
        "(measured: `SET PASSWORD`). MSX2 gives SET real jobs; on MSX1 there are "
        "none, so the whole behaviour is the refusal and the bar is that the ERROR "
        "CODE matches -- a word that refused with a different code, or refused "
        "where the reference did something, would fail this.",
    ),
    "IPL": (
        ("refuse",),
        "`IPL` is Illegal function call on both references and here. One "
        "behaviour; see SET above for why N is 1.",
    ),
    "CMD": (
        ("refuse",),
        "`CMD\"X\"` is Illegal function call on both references and here. One "
        "behaviour; see SET above.",
    ),
    # 🔴 `ATTR$` AND `CALL` CANNOT REACH TIER 1, AND NOT FOR WANT OF A ROW.
    # Measured 2026-09-17: neither is a knife target -- `ATTR$` is absent from the
    # 49 FUNCTION targets and `CALL`'s statement target resolves to a BLIND row --
    # because THERE IS NO HANDLER TO CUT. `SET`/`IPL`/`CMD` have handlers that
    # actively refuse with ERR 5, which an absent word cannot imitate (it parses
    # the word as a variable and gives ERR 2), so a cut moves their reading and
    # the knife proves them CONNECTED. `ATTR$` and `CALL` refuse BY BEING ABSENT:
    # `CALL FOO` is ERR 2 whether the word is dispatched or merely misparsed, so
    # no row can tell a present handler from a missing one.
    # 🎯 THE CRUNCH LAYER STILL PROVES THE TOKEN EXISTS -- that is a different
    # claim, and the one worth having. What is unprovable is that anything is
    # REACHED. This is the honest shape of "agreeing on an absence both sides
    # produce", and the table says `not knife-proven CONNECTED` rather than
    # pretending otherwise.
    "ATTR$": (
        ("refuse",),
        "`ATTR$` is tokenised and then refused -- `sysvars.inc` says so outright "
        "(`ATTR_TOKEN equ $E9 ; ATTR$ -- tokenised, then ERR 5 (no function)`) and "
        "the row agrees. One behaviour.",
    ),
    "CALL": (
        ("refuse",),
        "`CALL <name>` dispatches to an EXTENSION ROM and a bare MSX1 has none, so "
        "`CALL FOO`, the `_FOO` shorthand and a bare `CALL` are all **ERR 2** on "
        "both references and here (D-AKCM). 🔴 A DIFFERENT ERROR FROM THE OTHER "
        "FOUR, which is why the bar is 'matches the reference' and not 'raises 5'. "
        "The `_FOO` shorthand is the same behaviour by another spelling, so it is "
        "not a second form.",
    ),

    # 🟢 D-KWEDIT (2026-09-16). These two were filed as UNRATEABLE, and the reason
    # was the MODE they had been measured in, not the verbs: run from inside a
    # program `DELETE` stops the run and `RENUM` breaks the execution pointer. They
    # are DIRECT-MODE EDITOR COMMANDS, and the bar below is what the REFERENCE
    # accepts at the prompt -- measured row by row, not read off our handler.
    "DELETE": (
        ("delete-line", "delete-range", "delete-to-line"),
        "`DELETE <line>` / `DELETE <from>-<to>` / `DELETE -<to>` -- three SELECTIONS, "
        "and the listing afterwards separates all three (Z1+Z3, Z1, Z3). "
        "🔴 THREE AND NOT FOUR: the symmetrical-looking `DELETE <from>-` is REFUSED "
        "by both references with `Illegal function call` (measured), so an open-ended "
        "RIGHT form does not exist in MSX1 and a bar of four could never be met. "
        "Its row is kept, without a FORM: tag, to hold that asymmetry pinned.",
    ),
    "RENUM": (
        ("renumber-all", "renumber-from", "renumber-partial", "renumber-increment"),
        "`RENUM` / `RENUM <new>` / `RENUM <new>,<old>` / `RENUM <new>,,<step>` -- four "
        "behaviours: the defaults, a new start, renumbering only from an OLD line on, "
        "and a new increment. The middle argument is the one a parser can shift left, "
        "which is why the omitted-middle form is counted separately. "
        "⚠️ Their rows start the program at 5/7/9 and not 10/20/30: bare RENUM "
        "renumbers from 10 by 10, so on an already-10/20/30 program it is a NO-OP and "
        "the row would be agreeing on a constant.",
    ),
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
    "ERROR": (
        ("raise",),
        "ERROR <code> -- one behaviour: raise the code given. Its two rows raise 7 and 53 and read ERR *and* ERL back, so a handler that raised a constant, or lost the line number, is visible; they are the same form sampled twice.",
    ),
    "NEW": (
        ("erase-program",),
        "NEW -- no arguments, one behaviour. The row's discriminator is that the statement AFTER it is never reached and no error is raised: before D-NEWSTMT this row carried `Syntax error in 10`.",
    ),
    "LLIST": (
        ("list-to-printer",),
        "LLIST -- the printer sibling of LIST. One behaviour, and the reading is the LISTING ITSELF taken off the printer log rather than the screen, which is what separates it from LIST.",
    ),
    "LPRINT": (
        ("print-to-printer",),
        "LPRINT <list> -- one behaviour. The reading is LPOS, the head column, because the printed text never reaches the screen; a LPRINT that printed nothing leaves the head at 0.",
    ),
    "LFILES": (
        ("catalogue-to-printer",),
        "LFILES -- the directory to the printer. One behaviour, and the reading is that the head is back at column 0 because every entry ended its own line.",
    ),
    "LIST": (
        ("bare-list", "single-line", "range"),
        "LIST / LIST <line> / LIST <from>-<to> -- three behaviours: the whole program, one line, and a range. Only the bare form has a row; selecting WHICH lines to print is the part a bare LIST cannot exercise at all.",
    ),
    "FILES": (
        ("bare", "pattern"),
        "FILES [<pattern>] -- the whole directory or a filtered one. The existing row is the PATTERN form; the bare catalogue has no row, and a FILES that ignored its pattern would pass the row it has.",
    ),
    "WAIT": (
        ("port-mask", "port-mask-xor"),
        "WAIT <port>,<mask>[,<xor>] -- the optional third operand INVERTS the sense of the test, so a WAIT that parsed and dropped it would spin forever on exactly the inputs the two-argument form returns on.",
    ),
    "RESUME": (
        ("next", "bare", "line"),
        "RESUME / RESUME NEXT / RESUME <line> -- three DIFFERENT places to continue: the statement that failed, the one after it, and an explicit line. Only RESUME NEXT has a row, and re-running the failing statement is the form most likely to loop forever if it is wrong.",
    ),
    "LOF": (
        ("length",),
        "LOF(<channel>) -- one argument, one behaviour. The row opens a fixture of known size and reads the length back, so a stub answering 0 fails.",
    ),
    "EOF": (
        ("at-end",),
        "EOF(<channel>) -- one argument, one behaviour. The row READS THE FILE TO ITS END FIRST, so the answer is -1 against the 0 a stub gives; asking EOF of a freshly opened file would have been 0 either way.",
    ),
    "LOC": (
        ("position",),
        "LOC(<channel>) -- one argument, one behaviour. The row consumes a known number of bytes first, so the position is a VALUE and not the 0 it starts at.",
    ),
    "KILL": (
        ("delete-file",),
        "KILL <file> -- one behaviour. The row reads DSKF BEFORE and AFTER and scores the DIFFERENCE, so it sees the space the file gave back rather than merely that the statement parsed.",
    ),
    "COPY": (
        ("file-to-file",),
        "COPY <src> TO <dst> -- one behaviour. The row opens the DESTINATION and reads its length, so a COPY that created nothing, or an empty file, fails.",
    ),
    "LSET": (
        ("left-justify",),
        "LSET <field>=<string> -- one behaviour, and the row reads the FIRST byte of the fielded buffer. That is what separates it from RSET: left-justified the first byte is the data, right-justified it is a pad space.",
    ),
    "RSET": (
        ("right-justify",),
        "RSET <field>=<string> -- the mirror of LSET, and the pair is what makes each row a reading: the same program with the other verb answers the other value.",
    ),
    "DSKO$": (
        ("write-sector",),
        "DSKO$ <drive>,<sector> -- one behaviour. The row POKEs a known byte into the sector buffer, writes, re-reads through a DIFFERENT sector to flush, and reads the byte back -- so it sees the write reach the medium.",
    ),
    "GOSUB": (
        ("call",),
        "GOSUB <line> -- one behaviour. The row's subroutine sets a variable the caller then prints, so a GOSUB that parsed and did not branch leaves 0.",
    ),
    "READ": (
        ("read-data",),
        "READ <var>[,<var>...] -- one behaviour; reading several variables is repetition of it, not a second form. The row reads, RESTOREs and reads again, scoring the SUM, so a READ that always returned the first item is still visible.",
    ),
    "DSKI$": (
        ("read-sector",),
        "DSKI$(<drive>,<sector>) -- one behaviour, the RAW SECTOR read. The row reads sector 7, the root directory, whose first entry is TEST.BIN, so the buffer's first byte is the code of T, 84 -- a value, not a length.",
    ),
    "STRING$": (
        ("repeat",),
        "STRING$(n,c) -- one behaviour: n copies of a character.",
    ),
    "INKEY$": (
        ("poll-key",),
        "INKEY$ -- no arguments, one behaviour: take one character from the keyboard buffer if there is one. WARNING: it does NOT block, which is why its row stuffs KEYBUF directly rather than waiting, and why the typed-response channel cannot be used for it.",
    ),
    "ASC": (
        ("code-of",),
        "ASC(a$) -- one argument, one behaviour: the code of the FIRST character.",
    ),
    "LEN": (
        ("length",),
        "LEN(a$) -- one argument, one behaviour.",
    ),
    "ATN": (
        ("arctangent",),
        "ATN(x) -- one argument, one behaviour. The row scales by 1000 and truncates so the reading is an INTEGER both machines must agree on rather than a float rendering.",
    ),
    "COS": (
        ("cosine",),
        "COS(x) -- one argument, one behaviour. COS(0) is 1, so unlike SIN and TAN its row escapes the argument where a do-nothing function gives the right answer.",
    ),
    "SIN": (
        ("sine",),
        "SIN(x) -- one argument, one behaviour. WARNING: SIN(0) is 0 and so is a stub, so N=1 is earned by sin_b at an argument where 0 is the WRONG answer.",
    ),
    "TAN": (
        ("tangent",),
        "TAN(x) -- as SIN, and for the same reason: TAN(0) is 0 too.",
    ),
    "RND": (
        ("reseeded-draw",),
        "RND(x) -- one behaviour. A NEGATIVE argument RESEEDS, which is what makes the draw reproducible, and rnd_b reads the value (438 on both references). The plain row asks only whether the result is under 1, which is true of any conforming implementation.",
    ),
    "MOD": (
        ("modulo",),
        "a MOD b -- one behaviour. It is an OPERATOR, not a statement, and it is kept in the statement denominator because it has a result to get right.",
    ),
    "AND": (
        ("bitwise-and",),
        "a AND b -- one behaviour, and a truth table to get right; the row reads 5 AND 3 = 1.",
    ),
    "OR": (
        ("bitwise-or",),
        "a OR b -- 5 OR 3 = 7.",
    ),
    "XOR": (
        ("bitwise-xor",),
        "a XOR b -- 5 XOR 3 = 6.",
    ),
    "EQV": (
        ("equivalence",),
        "a EQV b -- 5 EQV 3 = -7. Measurably indistinguishable from XOR in PRECEDENCE (logtab's own comment says the order between them is a free choice), but not in RESULT.",
    ),
    "IMP": (
        ("implication",),
        "a IMP b -- 5 IMP 3 = -5.",
    ),
    "NOT": (
        ("bitwise-not",),
        "NOT a -- unary and right-associative; NOT 0 = -1.",
    ),
    "SWAP": (
        ("exchange",),
        "SWAP <var>,<var> -- one behaviour. The row reads BOTH variables back, so a SWAP that copied one way leaves the pair visible.",
    ),
    "DSKF": (
        ("free-space",),
        "DSKF(<drive>) -- one argument, one behaviour. The row reads 707 free KB on the 720 KB fixture, against a stub's 0.",
    ),
    "MERGE": (
        ("merge-file",),
        "MERGE <file> -- one behaviour. WARNING: MERGE RETURNS TO COMMAND LEVEL, so the row reads the marker BEFORE it and NOT the one after -- the absence is the reading, and the marker before proves the program got that far.",
    ),
    "FIELD": (
        ("bind-buffer",),
        "FIELD #<n>,<width> AS <var$>[,...] -- one behaviour; several fields is repetition of it. The row is a full round trip: FIELD binds, LSET fills, PUT writes record 1 and GET reads it back.",
    ),
    "CSAVE": (
        ("save-to-tape",),
        "CSAVE <name> -- one behaviour. THE ROW READS THE TAPE, not the screen, which is why it needs a blank-tape rig: every screen form of the reading was measured to be ambiguous.",
    ),
    "PAINT": (
        ("flood", "fill-colour", "border-colour"),
        "PAINT [STEP](x,y)[,<colour>[,<border>]] -- the flood itself, the fill colour and the BORDER colour that stops it are three behaviours; a fill that ignored its border leaks. All three have rows since D-KWPAINT2 (2026-09-24); the border one is in SCREEN 3, because in SCREEN 2 a border that differs from the fill is not a boundary at all.",
    ),
    "FRE": (
        ("free-ram", "free-string-space"),
        "FRE(0) reports free RAM and FRE("") free STRING space -- two different pools, not two inputs. WARNING: N=1 is not met by `fre`, which asks FRE(0)>1000, a BOOLEAN; `fre_b` reads the DELTA across a DIM, which is what makes the reading machine-independent.",
    ),
    "CLOAD": (
        ("load-named", "load-next"),
        "CLOAD <name> finds a named file; bare CLOAD takes the NEXT on the tape. Two search behaviours. The row's reading is the machine's own `Found:` line.",
    ),
    "AUTO": (
        ("bare", "start", "start-increment"),
        "AUTO / AUTO <start> / AUTO <start>,<increment> -- three behaviours; only the start form has a row. WARNING: this row must stay LAST by placement, because it leaves the machine in line-entry mode.",
    ),
    "GOTO": (
        ("jump",),
        "GOTO <line> -- one behaviour. WARNING: it has NO happy-path row at all. GOTO is the apparatus of dozens of rows and the subject of none; its only row is the PROVES-T3 `GOTO 9999` error case. Being used is not being measured.",
    ),
    "RESTORE": (
        ("bare", "line"),
        "RESTORE / RESTORE <line> -- reset the DATA pointer to the start, or to a specific line. Only the bare form has a row.",
    ),
    "RETURN": (
        ("bare", "line"),
        "RETURN / RETURN <line> -- return to the caller, or to an explicit line (D-RETLN). Only the bare form has a row.",
    ),
    "RUN": (
        ("bare", "line", "file"),
        "RUN / RUN <line> / RUN <file> -- three behaviours: restart, start at a line, and load-and-run. Only the line form has a row.",
    ),
    "IF": (
        ("then", "else", "goto"),
        "IF <expr> THEN ... / ... ELSE ... / IF <expr> GOTO <line> -- three behaviours. Only THEN has a row; ELSE is scored for the ELSE particle, which is a token and not a statement.",
    ),
    "CLOSE": (
        ("all", "channel"),
        "CLOSE / CLOSE #<n> -- close everything, or one channel. Only the channel form has a row.",
    ),
    "SAVE": (
        ("tokenised", "ascii"),
        "SAVE <file> writes the TOKENISED program; SAVE <file>,A writes ASCII. Two different file formats, not two inputs.",
    ),
    "BSAVE": (
        ("range", "with-entry"),
        "BSAVE <file>,<start>,<end>[,<entry>] -- the optional ENTRY address is what makes the image runnable, so it is a second behaviour.",
    ),
    "BLOAD": (
        ("plain", "run", "vram"),
        "BLOAD <file>[,R][,S] -- load, load-and-RUN, and load to VRAM (S). Three destinations/behaviours; only the plain load has a row.",
    ),
    "ABS": (
        ("magnitude",),
        "ABS(x) -- one argument, one behaviour.",
    ),
    "SGN": (
        ("sign",),
        "SGN(x) -- one argument, one behaviour; the row reads the sign of a negative.",
    ),
    "INT": (
        ("floor",),
        "INT(x) -- one argument, one behaviour. It FLOORS (toward minus infinity) where FIX truncates toward zero, which is why the two are separate keywords and not one form sampled twice.",
    ),
    "FIX": (
        ("truncate",),
        "FIX(x) -- truncates TOWARD ZERO where INT floors. One behaviour.",
    ),
    "CINT": (
        ("to-integer",),
        "CINT(x) -- one argument, one behaviour, the integer coercion.",
    ),
    "CSNG": (
        ("to-single",),
        "CSNG(x) -- one argument, one behaviour.",
    ),
    "CDBL": (
        ("to-double",),
        "CDBL(x) -- one argument, one behaviour.",
    ),
    "SQR": (
        ("square-root",),
        "SQR(x) -- one argument, one behaviour.",
    ),
    "EXP": (
        ("exponential",),
        "EXP(x) -- one argument, one behaviour.",
    ),
    "LOG": (
        ("logarithm",),
        "LOG(x) -- one argument, one behaviour.",
    ),
    "ERL": (
        ("error-line",),
        "ERL -- no argument, one behaviour: the LINE the trapped error occurred on. Its row reads it inside a handler, so a constant 0 fails.",
    ),
    "ERR": (
        ("error-code",),
        "ERR -- no argument, one behaviour: the CODE of the trapped error. Its rows read 7 and 53, so a handler returning a constant is visible.",
    ),
    "USR": (
        ("default", "numbered"),
        "USR(x) and USR<n>(x) -- MSX has TEN user-routine vectors and the digit "
        "selects which, so the numbered form reaches a DIFFERENT address and is "
        "not a second input to the same behaviour. Only the default has a row.",
    ),
    "PEEK": (
        ("address-read",),
        "PEEK(<address>) -- one argument, one behaviour, the reading half of POKE. N=1 is earned by peek_b and not by peek, which asks PEEK(0)>=0 -- a BOOLEAN that is true of every possible byte.",
    ),
    "MKS$": (
        ("single-to-string",),
        "MKS$(n) -- one argument, one behaviour. The row does NOT predict the single-precision byte layout; it prints the length AND the first byte, and what makes that a reading is that both machines must agree on the byte. A length alone is what four arbitrary bytes read.",
    ),
    "MKD$": (
        ("double-to-string",),
        "MKD$(n) -- as MKS$, for the 8-byte double encoding.",
    ),
    "PUT #": (
        ("fielded-record",),
        "PUT #<channel>,<record> -- one behaviour, the random-file record WRITE. It is not covered by GET #'s row: that does a round trip on record 1 only, so a PUT # ignoring the record number would pass it. The row writes TWO records with different values and reads both back.",
    ),
    "PRINT #": (
        ("channel-write",),
        "PRINT #<channel>,<list> -- one behaviour. Joost ruled bare PRINT, PRINT # and PRINT USING three different functions; this is the channel one, and it reads the bytes back through a second OPEN so an empty file fails.",
    ),
    "PUT SPRITE": (
        ("position", "colour-and-pattern"),
        "PUT SPRITE <plane>,(<x>,<y>)[,<colour>[,<pattern>]] -- the attribute entry carries a POSITION and a colour/pattern pair, and they are different bytes of it. The existing row reads ONE byte of the attribute table, so it sees the position and nothing else; N=2 says so rather than letting one reading stand for the whole entry.",
    ),
    "DEF FN": (
        ("numeric", "string-valued"),
        "DEF FN<name>[(<args>)]=<expr> -- the RESULT TYPE is the second form and not a detail: a string-valued FN needs a GC root the numeric one does not (Joost ruled that root takes the control-frame pool), so the two are different machinery. Argument COUNT is repetition, not a form.",
    ),
    "PRINT": (
        ("semicolon", "comma-zone", "trailing-suppress", "tab-item", "spc-item"),
        "Bare PRINT -- five behaviours, and only the two PRINT ITEMS have rows. The separators are the rest: ; concatenates, , advances to the next 14-column zone, and a TRAILING separator suppresses the newline. WARNING: PRINT is the apparatus of almost every row in this sweep and is therefore constantly exercised and almost never the SUBJECT -- being used is not being measured.",
    ),
    "ON GOTO": (
        ("index-goto",),
        "ON <expr> GOTO <line>[,<line>...] -- one behaviour: select the nth target by the expression's value. A longer target list is repetition of it. The row requires the SECOND target, so an ON that ignores the index and an ON that never jumps give two different wrong answers.",
    ),
    "ON GOSUB": (
        ("index-gosub",),
        "ON <expr> GOSUB <line>[,...] -- the GOSUB sibling, and a SEPARATE statement rather than a form of ON GOTO: it must also RETURN. The row reaches the second target and returns, so a call that never returns is visible too.",
    ),
    "ON ERROR GOTO": (
        ("on-error", "disable"),
        "ON ERROR GOTO <line> installs a handler (the row tags it on-error) and ON ERROR GOTO 0 DISABLES error trapping -- two behaviours, and the disable is the one a program uses to hand an error back to BASIC. Only the install has a row.",
    ),
    "INPUT$": (
        ("console", "channel"),
        "INPUT$(n) reads n characters from the KEYBOARD and INPUT$(n,#f) from a "
        "CHANNEL -- two sources, two forms. Both ship: the console form landed "
        "2026-09-16 (D-INPDCON) as a FOURTH ARL_GETBYTE source rather than a "
        "second copy of the read loop, str_inputd_read already consuming n bytes "
        "into STRSCR through that vector. It had been the LAST MISSING keyword in "
        "the sweep -- str_inputd required `,#f` and fell to str_eval_no without "
        "it. The CHANNEL form shipped long before but had NO ROW OF ITS OWN: it "
        "was exercised only inside printhash, as the instrument reading PRINT #'s "
        "bytes back, so it scored that verb and not this one.",
    ),
    "INPUT": (
        ("no-prompt", "prompt", "multi-variable"),
        "Bare CONSOLE INPUT -- three behaviours: the promptless read, the PROMPT literal printed before it, and ONE typed line SPLIT on commas into SEVERAL variables. The channel form is a different statement (INPUT #), per Joost's ruling. WARNING: until D-KWRESPOND there was no row at all -- both of INPUT's rows drove the FILE form and belong to INPUT #, so the console statement a 1985 listing uses most had never been measured.",
    ),
    "LINE INPUT": (
        ("whole-line", "prompt"),
        "LINE INPUT [<prompt>;]<var> -- the whole point is that it does NOT split: commas and leading spaces are KEPT where INPUT would have split at the comma and eaten the space. That is the whole-line form; the prompt is the second.",
    ),
    "INPUT #": (
        ("string-read",),
        "INPUT #<channel>,<var> -- one behaviour. Joost ruled bare INPUT and INPUT # different functions, and they are: the console form waits on the keyboard, this one reads a channel. Both of its rows drive this one form; input_b is a better instrument for it, not a second form.",
    ),
    "GET #": (
        ("fielded-record",),
        "GET #<channel>[,<record>] -- one behaviour, the random-file record read into the FIELD buffer. The row does a PUT/GET round trip so it reads the record back rather than merely that the statement parsed.",
    ),
    "DRAW": (
        ("movement", "move-absolute", "move-relative", "blank-prefix",
         "no-update-prefix", "colour", "scale", "angle", "substring-exec",
         "variable-substitution"),
        "The command string is a small language, and docs/spec-basic-graphics-g6.md "
        "\u00a71 enumerates the whole MSX1 surface: the eight direction letters "
        "`U D L R E F G H` (ONE behaviour -- move and draw; the eight directions are "
        "its inputs), ABSOLUTE and RELATIVE `M` (different addressing, so two), the "
        "`B` blank prefix (move without drawing) and `N` no-update prefix (draw, "
        "then return to the start), `C` colour, `S` scale, `A` angle, `X` substring "
        "execution and `=var;` substitution. AUTHORED AT TEN KNOWING THE TREE'S ROWS "
        "MEET ONE -- the bar is the reference's syntax, the same way PRINT USING is "
        "5 and LOCATE 3/4. \u26a0\ufe0f `drawkw`/`drawkw_b` both pass `C15`, which is the "
        "DEFAULT FOREGROUND, so neither says anything about `C`.",
    ),
    "PLAY": (
        ("notes", "note-number", "rest", "octave",
         "default-length", "tempo", "volume", "envelope", "multi-voice",
         "substring-exec"),
        "`PLAY \"<mml>\"[,\"<mml>\"[,\"<mml>\"]]` -- the MML subset is the statement, "
        "and docs/spec-basic-audio-play.md \u00a72.2 lists it from published sources: "
        "`A`-`G` notes with accidental and length, `N n` note numbers, `R` rests, "
        "`O n` octave, `L n` default length (with `.`), `T n` "
        "tempo, `V n` volume, `S n`/`M n` envelope, up to THREE voice strings, and "
        "`X var;` substring execution. \u26a0\ufe0f `&` is NOT MSX1 MML -- the VG-8020 "
        "raises ERR 5 and so does this tree -- so it is not a form. \U0001f534 AND "
        "NEITHER ARE `>` AND `<`, WHICH IS WHY THIS BAR WAS ELEVEN AND IS NOW TEN: "
        "D-KWPLAY (2026-09-15) gave both references three spellings each -- `>C`, "
        "` > C`, `O5<C` -- and got Illegal function call from every one, while this "
        "tree SOUNDED the shifted note. Octave-shift left the bar and the two "
        "commands left the tenant in the same slice. ⚠️ THE ROWS READ THE PSG "
        "BACK -- `OUT&HA0,r` then `INP(&HA2)`, live while the note sounds -- because "
        "`PLAY(n)` answers only WHICH VOICE, which covers multi-voice and nothing "
        "else; duration (`L`, `T`) waits in FRAMES via `TIME`, never in iterations.",
    ),
    "LOAD": (
        ("plain", "run"),
        "`LOAD \"<file>\"[,R]` -- load, and load-and-RUN. The `,R` form speaks "
        "through the LOADED program, which is why `PROG3.BAS` exists. \U0001f534 THIS "
        "NOTE USED TO SAY THE PLAIN FORM WAS UNOBSERVABLE -- \"both REPLACE the "
        "running program, so the plain form leaves nothing to print with and its "
        "reading would be an ABSENCE both machines produce\" -- and that was true "
        "when written and STALE from D-KWLOG (2026-09-13) onward: `NEEDS-LOG:` + "
        "`RESPOND:LLIST` reads a LISTING out of a host file, so the program never "
        "has to run. Joost's ruling (\"just validate the program in ram or llist "
        "it\") had already been applied to `DELETE`/`RENUM`; `LOAD` was simply "
        "never revisited. The `load_b` row closes it (D-LOADPLAIN).",
    ),
    "MOTOR": (
        ("toggle", "on", "off"),
        "`MOTOR [ON|OFF]` -- three behaviours, and the bare one is not a spelling of "
        "either: it TOGGLES. All three are readable, because bit 4 of PPI port C is "
        "the motor line itself.",
    ),
    "NAME": (
        ("rename",),
        "`NAME \"<old>\" AS \"<new>\"` -- one behaviour, and its reading has to be that "
        "the NEW name carries the OLD file's bytes; that the statement did not raise "
        "is not the same claim.",
    ),
    "OPEN": (
        ("input", "output", "append", "random"),
        "`OPEN <file> [FOR <mode>] AS #<n>` -- FOR INPUT, FOR OUTPUT and FOR APPEND "
        "are three sequential modes that differ in where the channel STARTS and "
        "whether the file is truncated, and the FOR-LESS form is a fourth: RANDOM "
        "access, on which FIELD/PUT/GET are legal and a sequential channel refuses "
        "them. The device names (`CAS:`, `LPT:`, `CRT:`) are the same four modes "
        "against a different medium, not a fifth behaviour.",
    ),
    "KEY": (
        ("assign", "list", "display-on", "display-off"),
        "`KEY <n>,<string>` assigns a function-key expansion; `KEY LIST` prints all "
        "ten; `KEY ON` and `KEY OFF` show and hide the function-key LINE. The last "
        "two are a display behaviour and not a pair of flags. \u26a0\ufe0f They have NO ROW "
        "and the reason is measured: the key line's LAYOUT differs between the "
        "machines -- LINLEN reads 37 on the VG-8020 and 39 on zerobas "
        "(scratchpad/keyline_probe.py) -- so a fixed VRAM offset reads the "
        "reference's text and the other side's blank, and the first attempt scored "
        "SUPPORTED on a space from both.",
    ),
    "SPRITE": (
        ("pattern-write", "enable", "disable"),
        "`SPRITE$(<n>)=<pattern>` writes the pattern table; `SPRITE ON` and "
        "`SPRITE OFF` decide whether a COLLISION is delivered to the trap. "
        "\U0001f534 `SPRITE STOP` IS NOT A FOURTH: docs/spec-traps-t4-sprite.md \u00a71.3 "
        "`G_stop_latch` measured it identical to `SPRITE OFF` with no latch, so a "
        "STOP row is the disable form sampled twice -- worth having, because a tree "
        "that made STOP a no-op would leave the trap enabled and no OFF row could "
        "see it.",
    ),
    "PDL": (
        ("read",),
        "`PDL(<n>)`, n = 1..12 -- six paddles per joystick port, and ONE behaviour: "
        "read paddle n's count. Which port an index falls in is addressing, not a "
        "second behaviour. \u26a0\ufe0f The bar is 1 and the ROW still had to change: an "
        "EMPTY port idles at 255, so `PDL(1)` reading 255 is satisfied by a function "
        "that answers 255 to everything. A plugged paddle reads 128.",
    ),
    "PAD": (
        ("touch-status", "coordinate", "switch"),
        "`PAD(<n>)`, n = 0..7 -- two devices of four indices each, and the four are "
        "three DIFFERENT QUANTITIES: n=0/4 is the touch SENSE (-1 or 0), n=1,2/5,6 "
        "are the X and Y COORDINATES, and n=3/7 is the SWITCH. Reading a coordinate "
        "is not reading a sense bit. \U0001f534 THE SWITCH IS INSTRUMENT-BLOCKED, AND "
        "THAT IS NOW MEASURED RATHER THAN ASSERTED (D-RIGBLOCK, 2026-09-15): "
        "openMSX's ONLY input-injection surface is the MSX KEY MATRIX "
        "(`keymatrixdown`/`keymatrixup`), and its `joystickports` debuggable READS "
        "(63, all lines idle) but does not take a write -- the value is recomputed "
        "from the connector, so a write is accepted and changes nothing. An "
        "unpressed switch reads 0, which is what a stub reads.",
    ),
    "STICK": (
        ("cursor-keys", "joystick-port"),
        "`STICK(<n>)` -- n=0 reads the CURSOR KEYS off the keyboard matrix and n=1/2 "
        "read a JOYSTICK PORT's direction lines. Different hardware, different code "
        "inside GTSTCK, so two behaviours and not two indices. \U0001f534 THE PORT FORM IS "
        "INSTRUMENT-BLOCKED, AND IT IS WORSE THAN \"driven from the host\" "
        "(D-RIGBLOCK, 2026-09-15): THIS openMSX HAS NO JOYSTICK PLUGGABLE AT ALL. "
        "Asked directly, `joyporta` accepts `mouse`, `trackball`, `arkanoidpad`, "
        "`paddle`, `ninjatap` and `touchpad`; `joystick1`, `joystick2`, "
        "`keyjoystick1` and `keyjoystick2` are every one of them \"No such "
        "pluggable\". So there is nothing to plug and nothing to poke.",
    ),
    "STRIG": (
        ("space-bar", "joystick-trigger"),
        "`STRIG(<n>)` -- n=0 is the SPACE BAR, read off the keyboard matrix; n=1..4 "
        "are the two triggers of each joystick port, read off the PSG. The same "
        "split as STICK and for the same reason. \U0001f534 The trigger form is "
        "INSTRUMENT-BLOCKED for the same measured reason STICK's port form is "
        "(D-RIGBLOCK, 2026-09-15) -- no joystick pluggable exists in this openMSX, "
        "and the `joystickports` debuggable will not take a write.",
    ),
    "FOR": (
        ("ascending", "step", "negative-step"),
        "`FOR <var>=<a> TO <b> [STEP <c>]` -- the IMPLIED step of 1, an explicit "
        "STEP, and a NEGATIVE step. The third is not a third operand: the sign of "
        "the step REVERSES the terminating comparison, so a loop that tests `<=` "
        "unconditionally runs a descending loop exactly once. Where the test HAPPENS "
        "(at NEXT, so the body always runs at least once) belongs to NEXT's bar.",
    ),
    "FN": (
        ("numeric", "string-valued"),
        "`FN<name>(<args>)` is the CALL side of DEF FN, and it mirrors DEF FN's own "
        "bar because the two return paths differ: a numeric function answers in the "
        "float accumulator and a string-valued one through a descriptor.",
    ),
    "DATA": (
        ("numeric", "quoted-string", "unquoted-string", "empty-item"),
        "`DATA <constant>[,<constant>]...` -- and three of the four are about where "
        "an ITEM ENDS. A numeric constant; a QUOTED string, inside which neither `,` "
        "nor `:` terminates (docs/spec-basic-datacolon.md found the missing quote "
        "state twice, once in the body scan and once in the skip); an UNQUOTED "
        "string, which keeps internal spaces and is trimmed at the edges; and an "
        "EMPTY item, which reads as 0 or the empty string rather than being skipped.",
    ),
    "VAL": (
        ("integer", "fraction", "exponent", "radix-prefix", "partial-parse"),
        "`VAL(<string>)` re-implements the tokeniser's numeric scanner over "
        "arbitrary user text, and docs/spec-basic-val.md measured the reference "
        "across 40 shapes: a signed INTEGER, a FRACTION, an EXPONENT (`E` or `D`), "
        "a RADIX PREFIX (`&H`/`&O`/`&B`), and a PARTIAL PARSE that stops at the "
        "first byte it cannot use. \u26a0\ufe0f VAL never raises on junk -- it returns 0 -- "
        "so every one of these is a SILENT wrong answer when it is missing, which "
        "is why they are forms and not error cases.",
    ),
    "DEF USR": (
        ("default", "numbered"),
        "`DEF USR[<n>]=<address>` -- the digit selects WHICH of the ten user-routine "
        "vectors is written, so the numbered form stores to a DIFFERENT CELL. That "
        "is the same split `USR`'s own bar makes, one level up: there it is which "
        "vector is CALLED, here it is which vector is SET.",
    ),
    "ON STOP GOSUB": (
        ("arm", "disarm"),
        "`ON STOP GOSUB [<line>]` -- ONE handler line, not a list (that is KEY and "
        "STRIG), and the bare form CLEARS the slot. docs/spec-traps-t1-stop-reslice.md "
        "\u00a75.1 has the arm leaving the STATE untouched (arm \u2260 enable) and "
        "docs/spec-traps-t4-sprite.md \u00a71.5 has the reference accepting the bare form "
        "and clearing the handler. \u26a0\ufe0f Unlike SPRITE and KEY, a cleared slot with the "
        "entry still ON does NOT swallow the event: both machines BREAK, which is "
        "what makes the two forms separable at all.",
    ),
    "ON KEY GOSUB": (
        ("arm", "list-positional", "empty-slot-clears"),
        "`ON KEY GOSUB <list>` -- the list is the statement. docs/spec-traps-t3-key.md "
        "measured all three on the reference: K1 arms KEY 1 from a single-entry list, "
        "K8 shows the list is POSITIONAL (slot n is function key n, so `100,200` with "
        "`KEY(2) ON` fires 200), and T5 shows an EMPTY slot leaves the entry enabled "
        "with no handler -- the key is still swallowed and nothing fires. Ten slots "
        "are accepted and an eleventh is ERR 2; that is a DOMAIN, not a fourth form.",
    ),
    "ON STRIG GOSUB": (
        ("arm", "list-positional", "empty-slot-clears"),
        "`ON STRIG GOSUB <list>` -- the same three as ON KEY, measured in "
        "docs/spec-traps-t2-strig.md: Q1 arms trigger 0 from a single-entry list, R5 "
        "has slot n = trigger n, and S3 has a listed-empty slot CLEAR that handler. "
        "Trigger 0 is the SPACE BAR, which is why all three are reachable with a key "
        "matrix and no joystick.",
    ),
    "ON INTERVAL GOSUB": (
        ("arm", "disarm"),
        "`ON INTERVAL=<n> GOSUB [<line>]` -- two behaviours, and the second is the "
        "BARE one: docs/spec-traps-t5-interval.md \u00a71.6 measured that "
        "`ON INTERVAL=10 GOSUB` with no line is ACCEPTED and CLEARS the handler "
        "(`R_bare_disarms`: 6 fires before, 0 after). That is not `INTERVAL OFF` -- "
        "the state byte and the handler link are independent -- so arming and "
        "disarming are two different things this statement does. The period `n` is "
        "an ARGUMENT, not a form.",
    ),
    "ON SPRITE GOSUB": (
        ("arm", "disarm"),
        "`ON SPRITE GOSUB [<line>]` -- the same two as ON INTERVAL, and measured the "
        "same way: docs/spec-traps-t4-sprite.md \u00a71.4 `R_bare_disarms` has the bare "
        "form clearing the handler slot while the state byte survives, so firing "
        "stops without the trap being disabled.",
    ),
    "MAX FILES": (
        ("set",),
        "MAXFILES=<n> -- one syntax and one behaviour: re-allocate the file-control "
        "blocks. There is no bare MAX FILES and no second operand, so the bar is 1. "
        "Its row scores the IMPLICIT CLEAR the re-allocation performs (measured, and "
        "the trap that cost openkw_b four sweeps), which is what separates a MAXFILES "
        "that RAN from one that only parsed; that a second channel then really exists "
        "is shown independently by openkw_b's `AS#2`.",
    ),
    "PRINT USING": (
        ("integer-field", "fraction-field", "sign", "string-field", "exponential"),
        "PRINT USING <format>;<list> -- the format string is a small language and its field types are the forms: the integer field #, the fractional field #.##, an explicit sign, the string fields ! and \\ \\, and the exponential ^^^^. Only the first two have rows. AUTHORED AT FIVE KNOWING THE TREE MEETS TWO: the bar is the reference's syntax, the same way LOCATE is 3/4 and VARPTR 1/2.",
    ),
    "BASE": (
        ("read", "write"),
        "BASE(n) is both an expression and an assignment TARGET -- ex_base_assign (basic/interp.asm) is a separate handler from the read selector, exactly like VDP(n). WARNING: the write row uses index 5 and not 2. BASE(2) is the SCREEN 0 name table, and writing it MOVES THE TEXT PLANE the capture scrapes; BASE(5) belongs to SCREEN 1, which is not on screen.",
    ),
    "NEXT": (
        ("bare", "named", "comma-list"),
        "NEXT / NEXT <var> / NEXT <var>,<var> -- three behaviours, and the split is in the source: ex_next parks 0 for a bare NEXT (take the TOP frame) and nx_comma parks 1 (basic/program.asm), so the named and list forms take a different path through the frame search. A bare NEXT cannot exercise the matching at all.",
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
        "VARPTR(<var>) and VARPTR(#<n>). AUTHORED AT 2 KNOWING THIS TREE CAN ONLY MEET 1. The bar comes from the reference's syntax, not from what we chose to build. The variable form is scored by varptr_b and NOT by varptr, which reads VARPTR(B)>0 -- a BOOLEAN, which cannot see the address. 🔴 THE FILE-CHANNEL FORM'S DEFERRAL HAS A MEASURED REASON SINCE 2026-09-16 (D-VARPTRN): both references answer an ADDRESS where this tree answers Syntax error, so the form is genuinely missing -- but the only axis a row can AGREE on is the STRIDE (the base is machine-specific and cancels, as varptr_b does for arrays), and the references stride at 265 (MSX's FCB: 256-byte record + 9 header) against our FCH_CTXSZ of 306. Matching it means adopting MSX's FCB LAYOUT, which is a channel-table change rather than a VARPTR one. Awaiting Joost.",
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
        "than the reference (the open on-par-speed item), so a delay loop's TIME VALUE "
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
        ("text-width", "mode1-width", "same-width"),
        "`WIDTH <columns>` has one argument and no optional parts, so the second "
        "form is not a second argument -- it is a second CELL. MSX keeps the width "
        "per mode (LINL40 $F3AE for SCREEN 0, LINL32 $F3AF for SCREEN 1) and WIDTH "
        "writes whichever belongs to the current mode, so a handler that always "
        "wrote LINL40 passes the first and fails the second. ➕ D-WIDTHKEEP "
        "(2026-09-24): the THIRD form is the width ALREADY in force, which the "
        "reference treats as a no-op -- screen, cursor and per-mode cell all "
        "untouched -- where a handler that always re-inits clears the screen. "
        "Neither of the first two rows could see it: both read cells, and the "
        "cells agree either way.",
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
