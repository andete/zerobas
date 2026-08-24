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

    # === arrays slice 3: STRING arrays (docs/spec-basic-arrays-slice3-strings.md
    # §6) — every semantic mirrors the numeric slice (base-0, DIM inclusive,
    # auto-dim upper 10, same four error dispositions) plus the string-value
    # additions (store/load, auto-init "", element string-ops, value-copy
    # semantics). Value/behaviour cases are STORED (both machines run to
    # completion, differential on the "[..]" span); every error-tier case is
    # DIRECT (the same stored-RUN-doesn't-abort landmine as slice 1/2).
    ("strarr.store.load",       "stored", ['DIM S$(3):S$(1)="HI"', 'PRINT"[";S$(1);"]"'], "value"),
    ("strarr.autodim.bound10.ok","direct",['S$(10)="Z":PRINT"[";S$(10);"]"'],            "value"),
    ("strarr.autodim.11.oor",   "direct", ['S$(11)="Z":PRINT"[";S$(11);"]"'],            "err"),
    ("strarr.autoinit.empty",   "stored", ['DIM S$(3)', 'PRINT"[";S$(2);"]"'],           "value"),
    ("strarr.autoinit.len0",    "stored", ['DIM S$(3)', 'PRINT"[";LEN(S$(2));"]"'],      "value"),
    ("strarr.dim.inclusive",    "stored", ['DIM S$(5):S$(5)="E"', 'PRINT"[";S$(5);"]"'], "value"),
    ("strarr.base0",            "stored", ['DIM S$(2):S$(0)="Z"', 'PRINT"[";S$(0);"]"'], "value"),
    ("strarr.dim.over.oor",     "direct", ['DIM S$(5):S$(6)="X":PRINT"[x]"'],            "err"),
    ("strarr.redim",            "direct", ['DIM S$(3):DIM S$(3):PRINT"[ok]"'],           "err"),
    ("strarr.neg.illegal",      "direct", ['DIM S$(5):PRINT"[";S$(-1);"]"'],             "err"),
    ("strarr.multidim.val",     "stored", ['DIM S$(2,3):S$(1,2)="HI"', 'PRINT"[";S$(1,2);"]"'], "value"),
    ("strarr.multidim.init0",   "stored", ['DIM S$(2,3)', 'PRINT"[";S$(2,3);"]"'],       "value"),
    ("strarr.multidim.wrongn.oor","direct",['DIM S$(2,3):PRINT"[";S$(1);"]"'],           "err"),
    # type-independence (S / S% / S$ coexist as distinct arrays, §2 probe #10):
    ("strarr.typeindep.dbl",    "stored", ['S(1)=11:S$(1)="Q"', 'PRINT"[";S(1);S$(1);"]"'], "value"),
    ("strarr.typeindep.pct",    "stored", ['S%(1)=5:S$(1)="Q"', 'PRINT"[";S%(1);S$(1);"]"'], "value"),
    # element string-ops (§2 probe #11 — element is a first-class rvalue):
    ("strarr.len",              "stored", ['DIM S$(3):S$(1)="ABC"', 'PRINT"[";LEN(S$(1));"]"'], "value"),
    ("strarr.mid",              "stored", ['DIM S$(3):S$(1)="ABC"', 'PRINT"[";MID$(S$(1),2);"]"'], "value"),
    ("strarr.left",             "stored", ['DIM S$(3):S$(1)="ABC"', 'PRINT"[";LEFT$(S$(1),2);"]"'], "value"),
    ("strarr.concat",           "stored", ['DIM S$(3):S$(1)="AB"', 'PRINT"[";S$(1)+"C";"]"'], "value"),
    # 3 copy directions + the NO-ALIAS case (§2 probe #12/#13 — value-copy
    # semantics: elements hold copies, no aliasing):
    ("strarr.copy.scalar2elem", "stored", ['DIM S$(3):A$="HI":S$(1)=A$', 'PRINT"[";S$(1);"]"'], "value"),
    ("strarr.copy.elem2elem",   "stored", ['DIM S$(3):S$(1)="HI":S$(2)=S$(1)', 'PRINT"[";S$(2);"]"'], "value"),
    ("strarr.copy.elem2scalar", "stored", ['DIM S$(3):S$(1)="HI":A$=S$(1)', 'PRINT"[";A$;"]"'], "value"),
    ("strarr.noalias",          "stored", ['DIM S$(3):S$(1)="HI":S$(2)=S$(1)', 'S$(1)="XY"', 'PRINT"[";S$(2);"]"'], "value"),
    # ERASE / CLEAR free the array contents (§2 probe #14):
    ("strarr.erase.frees",      "stored", ['DIM S$(3):S$(1)="HI"', 'ERASE S$', 'PRINT"[";S$(1);"]"'], "value"),
    ("strarr.clear.frees",      "stored", ['DIM S$(3):S$(1)="HI"', 'CLEAR', 'PRINT"[";S$(1);"]"'], "value"),
    # Arrays slice-4a (§14/§15): a string-array element is now a HEAP-backed
    # [len][ptr] descriptor, DECOUPLED from STRMAX (255). A 90-char STRING$
    # into an element is no longer clamped to the old 64 -- it holds the full
    # 90, matching the reference exactly. So this is now a normal differential
    # "value" test (was the slice-3 "zbval" 64-clamp deviation, now retired).
    ("strarr.longstr.90",       "stored", ['DIM S$(1):S$(1)=STRING$(90,65)', 'PRINT"[";LEN(S$(1));"]"'], "value"),
    # --- ADVERSARIAL: variable/nested/self-ref subscripts, the slice-1 lesson
    # applied to strings (the literal-only string cases above hid nothing this
    # time -- verified -- but the gate must exercise the array IDIOM, not just
    # literals; every case here confirmed reference-identical 2026-07-15).
    ("strarr.varsub",           "stored", ['I=1:S$(I)="HI"', 'PRINT"[";S$(I);"]"'], "value"),
    ("strarr.nestsub",          "stored", ['A(0)=1:S$(A(0))="HI"', 'PRINT"[";S$(A(0));"]"'], "value"),
    ("strarr.selfconcat.var",   "stored", ['I=1:S$(I)="AB"', 'S$(I)=S$(I)+"C"', 'PRINT"[";S$(I);"]"'], "value"),
    ("strarr.two.elem.concat",  "stored", ['S$(1)="A":S$(2)="B"', 'PRINT"[";S$(1)+S$(2);"]"'], "value"),
    ("strarr.for.store",        "stored", ['DIM S$(3)', 'FORI=1TO3:S$(I)=CHR$(64+I):NEXT', 'PRINT"[";S$(1);S$(2);S$(3);"]"'], "value"),
    ("strarr.md.varsub",        "stored", ['I=1:J=2:DIM S$(2,3)', 'S$(I,J)="HI"', 'PRINT"[";S$(I,J);"]"'], "value"),
    ("strarr.if.cmp",           "stored", ['S$(1)="A"', 'IFS$(1)="A"THEN?"[Y]"ELSE?"[N]"'], "value"),
    ("strarr.dim.varbound",     "stored", ['N=4:DIM S$(N)', 'S$(N)="Z"', 'PRINT"[";S$(N);"]"'], "value"),
    # D1 (slice-3 regression fix): a DIM target must start with a letter -- a
    # bare `$` or a digit name is a syntax error (was silently accepted; the
    # deleted slice-2 `$`-reject had masked it). Tier-A, house-lowercase.
    ("strarr.dim.bare.dollar",  "direct", ['DIM $(5):PRINT"[x]"'], "synerr"),
    ("strarr.dim.digit.name",   "direct", ['DIM 1(5):PRINT"[x]"'], "synerr"),
    # Arrays slice-4a (§14/§15): with 3-byte [len][ptr] elements a big string
    # DIM now FITS (the slice-3 inline-65-byte OOM is gone) -- DIM S$(1000)
    # succeeds on both, differential. (Was "strarr.dim.huge.oom"/zberr.)
    ("strarr.dim.large.ok",     "stored", ['DIM S$(1000):S$(500)="Z"', 'PRINT"[";S$(500);"]"'], "value"),
    # Arrays slice-4a DIM-after-heap-pressure (Fable gate: S3, ary_alloc's
    # ceiling=FRETOP + GC-before-OOM retry, aal_ceil_try). Churn a SCALAR to
    # fill the heap with garbage (1 root -> the reference's own GC stays fast),
    # THEN DIM a numeric array whose growth meets the string-heap boundary and
    # must reclaim before it fits; A$ and the array element both survive.
    # Differential.
    # zb-only (zbval): the reference's tiny default string space (~200 B, no
    # CLEAR) can't even hold a 250-char STRING$ ("Out of string space"), so it
    # is not an oracle for zb's whole-free-RAM heap under this churn. The
    # result is derivable-correct.
    ("strarr.dim.aftergc",      "stored",
        ['CLEAR 4000:FORI=1TO70:A$=STRING$(250,65):NEXT', 'DIM B(500):B(250)=99',
         'PRINT"[";LEN(A$);"/";B(250);"]"'], "zbval"),
    # Arrays slice-4a GC INTEGRITY (Fable gate): keep only a FEW live string-
    # array elements (5) but CHURN them hard (15 rounds x 5 reassigns = 75
    # allocations of 250 B = ~18 KB), orphaning the old heap bodies. That
    # exceeds zb's ~15 KB heap so a compacting GC fires mid-churn WITH the 5
    # elements live as roots -- exercising array-element ptr fix-up. Only 5
    # roots keeps the REFERENCE's own (O(n^2)) GC fast enough to not time out
    # the differential (a 50-element churn timed the reference out). Both
    # machines end with S$(3) = 250 'B's, GC or not (GC is unobservable).
    ("strarr.gc.churn",         "stored",
        ['CLEAR 4000:DIM S$(5):FORI=1TO5:S$(I)=STRING$(250,65):NEXT',
         'FORJ=1TO15:FORI=1TO5:S$(I)=STRING$(250,66):NEXT:NEXT',
         'PRINT"[";LEN(S$(3));LEFT$(S$(3),1);"]"'], "zbval"),

    # === arrays slice-4b: numeric SCALAR relocation into the contiguous ====
    # chain (docs/spec-basic-arrays-slice4b-scalar-reloc.md §9). Scalars now
    # live in the SAME [PRGEND+2, FRETOP) region arrays/strings do, sharing
    # the insert-and-shift + FRETOP collision/GC-once-retry mechanism.
    #
    # Type round-trip: A%/A!/A#/default-double are four DISTINCT chain
    # entries (unchanged identity rule, now over the relocated store).
    ("scalar.types.roundtrip",  "stored",
        ['A%=1:A!=2.5:A#=3.5:A=4',
         'PRINT"[";A%;A!;A#;A;"]"'], "value"),
    # Many-scalar program: 26 distinct default-double scalars (26*11=286 B)
    # comfortably exceeds the pre-4b fixed pool's ~11-25 scalar ceiling --
    # the fixed cap is GONE (§0 "removes the fixed scalar cap").
    (
        "scalar.many.overflow128", "stored",
        # 26 single-letter names in chunks of 6 (each stored LINE must clear
        # the KEYBUF-injection 40-byte cap, probes/lib/omsx_repl.py) -- A=1
        # .. Z=26, 26*11=286 B of default-double entries, well past the
        # pre-4b fixed pool's ~11-25 scalar ceiling.
        [":".join(f"{chr(ord('A') + k + j)}={k + j + 1}" for j in range(min(6, 26 - k)))
         for k in range(0, 26, 6)]
        + ['PRINT"[";A;M;Z;"]"'],
        "value",
    ),
    # Interleave scalar creation with array growth (§9's own worked example)
    # -- the insert-shift's core hazard. Assert array CONTENT survives (not
    # just length -- the standing 4a lesson), across TWO separate arrays
    # each shifted by a LATER scalar's insertion.
    ("scalar.array.interleave", "stored",
        ['DIM A(5):A(2)=11:B=1',
         'DIM C(5):C(3)=22:D=2:E=3',
         'PRINT"[";A(2);B;C(3);D;E;"]"'], "value"),
    # String-array elements survive scalar shifts: their descriptor MOVES
    # with the array block, but the heap `ptr` value (and hence the string
    # CONTENT) must stay valid (§7's own "string-array element load/store"
    # note; no GC root touched by a plain scalar insert).
    ("strarr.scalar.shift.survive", "stored",
        ['DIM S$(3):S$(0)="hello":X=1:Y=2:Z=3',
         'PRINT"[";S$(0);X;Y;Z;"]"'], "value"),
    # Edit clears scalars too (§7.1, §3b Q2): a program EDIT (storing a new
    # numbered line via the REPL) invalidates PRGEND's own downstream
    # scalar-region base, so relink's vars_reset must clear scalars, not
    # just arrays -- the deliberate MSX-faithful behaviour change from
    # pre-4b zerobas (which kept scalars across an edit as an off-to-the-
    # side-pool artifact). A%=5 in direct mode, then STORE a numbered line
    # (an edit), then re-read A% -- must read back 0 on BOTH machines now.
    ("scalar.edit.clears",      "direct",
        ['A%=5', '10 PRINT 1', 'PRINT"[";A%;"]"'], "value"),
    # VARPTR: the gate asserts the VALUE AT THE RETURNED ADDRESS immediately
    # after VARPTR (§7.2 -- no gate can pin a moving address, since a later
    # allocation is free to relocate it).
    ("scalar.varptr.value",     "direct",
        ['A%=5', 'PRINT"[";PEEK(VARPTR(A%));"]"'], "value"),
    # VARPTR(A$) fix (post-slice-4c follow-up): a `$`-suffixed name resolves
    # (VARTYPE)=8 in vnk_dollar (the DEFTBL/suffix numeric slot, not a
    # string-ness flag), so pre-fix ev_f_varptr allocated a phantom NUMERIC
    # entry B# for VARPTR(B$) instead of returning B$'s own STRING
    # descriptor -- PEEK(VARPTR(B$)) read a stray byte of the numeric
    # double's (auto-init 0) value field instead of the descriptor's LEN
    # byte. Fixed by detecting string-ness via var_str_type (before
    # var_name_key resolves VARTYPE) and passing type=1 to var_alloc_or_
    # find, selecting the SAME stride-6 [len][ptr] entry str_set_key uses.
    # Differential (VARPTR/PEEK are standard MSX-BASIC, and B$ already
    # exists before VARPTR is called, satisfying the reference's own
    # "argument must already exist" VARPTR requirement -- see the h2.*
    # cases' comments above). NON-VACUOUS (verified by hand 2026-07-17,
    # `git stash` on the expr.asm fix + rebuild): pre-fix zb read ' 0 '
    # (the phantom B#'s zero value byte); post-fix zb reads ' 2 ', matching
    # the VG-8020 reference exactly (both ' 2 ' for B$="hi").
    ("scalar.varptr.str.value", "direct",
        ['B$="hi"', 'PRINT"[";PEEK(VARPTR(B$));"]"'], "value"),
    # FOR/NEXT + READ over a typed (post-relocation) loop/target variable --
    # the shim path (var_get/var_set, vars.asm) now also routes through the
    # relocated chain via var_load_fac/var_store_fac's own thin ARY-tenant
    # glue.
    ("scalar.for.read.typed",   "stored",
        ['DATA 10,20,30', 'DIM X(3):FORI=1TO3:READV:X(I)=V:NEXT',
         'PRINT"[";X(1);X(2);X(3);"]"'], "value"),
    # zb-only (zbval, the established 4a precedent -- the reference's tiny
    # default string space can't run a heap-pressure churn without CLEAR):
    # a scalar creation that COLLIDES with a tight FRETOP, GCs once, and
    # succeeds (§3a steps 3-4) -- the SAME mechanism arrays' own OOM-retry
    # uses, now reachable from scalar creation too.
    ("scalar.collision.gc.ok",  "stored",
        ['CLEAR 4000:FORI=1TO70:A$=STRING$(250,65):NEXT', 'ZZ=12345',
         'PRINT"[";LEN(A$);"/";ZZ;"]"'], "zbval"),

    # --- §13a: STALE ARRAY-ELEMENT ADDRESS (docs/spec-basic-arrays-slice4b-
    # scalar-reloc.md §13a). ex_let_arr/ex_let_arr_str resolve the element
    # address, then `eval`/`str_eval` the RHS -- and VARPTR(newvar) is the
    # ONLY eval-time scalar allocator, so a FRESH var inside the RHS shifts
    # the whole array region mid-store, staling the address the LET is about
    # to write through. Fixed via an ARYTAB before/after delta correction
    # (basic/vars.asm ary_snapshot_offset/ary_apply_offset*, page-1 -- the
    # low region had no headroom for the arithmetic).
    #
    # ALL THREE are zb-only (zbval): triggering the shift needs a variable
    # VARPTR has never touched before (find-only would just skip the
    # allocation and never reproduce the hazard) -- and the VG-8020
    # reference's own VARPTR requires its argument to already exist,
    # raising "Illegal function call" on a fresh name (confirmed empirically,
    # 2026-07-17: `PRINT VARPTR(ZZ)` on a never-referenced ZZ -> "Illegal
    # function call"; `ZZ=1:PRINT VARPTR(ZZ)` succeeds). zerobas's own
    # auto-allocating VARPTR (a pre-existing, signed-off slice-4b design
    # choice, §3a -- not touched by this fix) is exactly what CAN hit this
    # class, so the reference can never be an oracle for it; not a
    # regression in the differential coverage, a genuinely zb-only mechanism
    # (same class as the GC-collision/churn cases just above).
    #
    # 🏁 RETIRED 2026-08-19 (D-VPTRDOM) — FIVE ROWS, AND THE CLASS THEY GUARD
    # IS NOW UNREACHABLE RATHER THAN UNTESTED. `scalar.varptr.elem`,
    # `scalar.varptr.neighbor`, `strarr.varptr.neighbor`,
    # `h2.varptr.strarg.elem` and `h2.varptr.defstr.elem` all forced the §13a
    # mid-eval ARYTAB shift the ONLY way it could be forced: zerobas's
    # auto-allocating VARPTR. That was a signed-off slice-4b design choice
    # (§3a) and it is gone — `VARPTR(<unset>)` is `Illegal function call` here
    # now, matching BOTH references, which this very comment block had already
    # recorded as their behaviour since 2026-07-17.
    #
    # 🎯 SO THERE IS NO LONGER ANY EVAL-TIME SCALAR ALLOCATOR ON ANY OF THE
    # THREE SIDES, and §13a's corruption REQUIRED one. The class is not merely
    # untestable, it is unreachable by construction: no program any side accepts
    # can shift ARYTAB mid-statement.
    # ⚠️ THE GUARDS STAY IN THE TREE — ex_let_arr's ary_snapshot_offset /
    # ary_apply_offset and D-LVFIX's tgt_desc correction are cheap, their
    # argument is static, and a future eval-time allocator needs them back. What
    # is gone is the ability to TEST them from BASIC.
    # 🔴 AND THAT COSTS K-LV5 ITS LIVE DETECTOR (m.arydrift in
    # basic_probe_lvfix.py). Recorded, not absorbed.
    # ⚠️ REWRITING THEM TO PASS WAS CONSIDERED AND REFUSED: with no mid-eval
    # allocator, any rewrite (pre-setting the variable, say) stops reaching the
    # correction at all — the rows would go green while gating nothing, and a
    # vacuous row is worse than an honestly retired one.
    #
    # The original reasoning is kept below verbatim, because it is the record of
    # WHY the correction exists and it is still the argument for keeping it.
    #
    # scalar.varptr.elem: the exact repro (§13a "Repro"). A(0)=VARPTR(B)
    # allocates B mid-eval, shifting A's own element out from under the
    # already-resolved store address -- pre-fix this corrupted memory and
    # HUNG the interpreter (confirmed via probes/lib/omsx_repl.py
    # run_case(...) timing out, 2026-07-17). Asserted PORTABLY (no hardcoded
    # address, which would be fragile to any unrelated memory-layout change):
    # re-read VARPTR(B) (now a plain find, B already exists) and compare
    # against what A(0) actually stored -- must be the SAME value, i.e. the
    # store landed at the address VARPTR(B) really is, not a stale one.
    # scalar.varptr.neighbor: the OTHER repro (§13a "Repro" 2nd form) -- a
    # NEIGHBOUR element (not the one being stored) must survive the shift.
    # Pre-fix this also corrupted memory/hung (the stale address could land
    # anywhere in the shifted region, including atop A(3)'s own slot).
    # strarr.varptr.neighbor: the STRING sibling (ex_let_arr_str) -- a
    # numeric VARPTR sub-argument INSIDE the string RHS (STRING$'s charcode
    # argument) allocates mid-str_eval, exercising ary_apply_offset_hl_sub
    # (the HL-preserving variant, since str_eval leaves the cursor live in
    # HL rather than parked in IX like the numeric routine). `MID$("XYZ",
    # VARPTR(D),1)` (the task's own suggested form) does NOT work here: a
    # freshly-allocated scalar's address is a large magnitude (e.g.
    # -32719, confirmed empirically) that MID$'s position argument rejects
    # as out of 1..LEN(string$) range ("Illegal function call") regardless
    # of the shift/correction fix -- an argument-DOMAIN error, unrelated to
    # this bug. `VARPTR(D) AND 255` sidesteps that (any byte 0..255 is a
    # valid STRING$ charcode) while still exercising the identical hazard
    # (a numeric VARPTR call nested inside the string RHS expression).
    # Asserted on the NEIGHBOUR S$(3) (not S$(0), whose own STRING$-built
    # content depends on the unpredictable VARPTR byte) -- "world" must
    # survive untouched.

    # === arrays slice-4c: string-scalar unification (docs/spec-basic- =======
    # arrays-slice4c-string-scalar-unification.md §9). String scalars are
    # now ordinary chain entries sharing [PRGEND+2, ARYTAB) with numeric
    # scalars/arrays, and their descriptors are GC roots walked by
    # sg_walk_scalars (sub/strheap.asm) instead of the retired STRTAB pool.
    #
    # H1 battery (§6, the LOAD-BEARING fix): A$=<source>, A$ FRESH, with RAM
    # churned near FRETOP so the TARGET alloc (A$'s own insert) can collide
    # and trigger strheap_gc mid-store. Without the H1 temp-stack source-
    # snapshot, a source that is a string-array element (its descriptor
    # address moves with the insert-shift) or an RVDESC/temp value not
    # re-snapshotted goes STALE across the shift+GC -- silently wrong
    # content. zb-only (zbval): the reference's ~200 B default string space
    # can't complete a 70x STRING$(250) churn (confirmed empirically -- the
    # reference run never reaches the PRINT), so it is not an oracle here
    # (the same "zb-only heap-pressure" class as scalar.collision.gc.ok /
    # strarr.gc.churn above).
    ("h1.srcarrelem",  "stored",
        ['CLEAR 4000:DIM S$(1):S$(0)="hello":FORI=1TO70:Z$=STRING$(250,65):NEXT:A$=S$(0)',
         'PRINT"[";A$;"]"'], "zbval"),
    # h1.srcconcat: source = a `+` concat result. Empirically, str_eval's own
    # concat spine (str_concat_tail) ALREADY snapshots operand 1 into an
    # owned temp-stack entry before appending (so THIS specific shape is
    # safe independent of the H1 fix -- confirmed by temporarily disabling
    # the fix and re-running: this case still passed) -- kept in the
    # battery anyway per the contract's explicit case list (§9) as a
    # standing regression guard, not because it isolates the bug alone.
    ("h1.srcconcat",   "stored",
        ['CLEAR 4000:B$="foo":C$="bar":FORI=1TO70:Z$=STRING$(250,65):NEXT:A$=B$+C$',
         'PRINT"[";A$;"]"'], "zbval"),
    # h1.self: A$=A$ with A$ fresh (reads STR_EMPTY, then allocates). A
    # degenerate/edge member of the battery per the contract's own listing.
    ("h1.self",        "stored",
        ['CLEAR 4000:FORI=1TO70:Z$=STRING$(250,65):NEXT:A$=A$',
         'PRINT"[";A$;"]"'], "zbval"),
    # NON-VACUOUS proof for h1.srcarrelem (recorded here, verified by hand
    # during implementation): reverting the H1 snapshot (str_set_key using
    # the raw source pointer DE directly, no str_snapshot_to_temp) turns
    # this case's printed value from "hello" into garbage (observed:
    # single stray byte "!") -- the array-region shift from A$'s own insert
    # moved S$(0)'s descriptor out from under the held (now-stale) source
    # address. h1.srcconcat/h1.self were unaffected by the same revert (see
    # their own comments above).

    # H2 (§6): a mid-eval scalar allocator (VARPTR) whose ARGUMENT is a
    # STRING variable -- the §13a numeric-VARPTR fix (scalar.varptr.elem
    # above) generalised to a STRING-triggered shift. Since the VARPTR(A$)
    # fix (commit d92c3da), `VARPTR(B$)` allocates a real stride-6 STRING
    # scalar (type 1), so evaluating it inside the RHS opens a 6-byte hole
    # at ARYTAB and shifts the array region up -- with the numeric element
    # A(0) already resolved (held) across the eval. This case proves the 4b
    # delta-correction fires for that string-sized shift too (it keys on the
    # ARYTAB delta, stride-agnostic -- confirmed empirically by the Fable
    # d92c3da review's 17-case battery incl. multi-shift + GC-interleave).
    # "value-at-address" checked like scalar.varptr.elem: re-read VARPTR(B$)
    # after B$ already exists (a plain find, no further shift) and compare.
    # zb-only for the same reason as every other auto-allocating-VARPTR case
    # (scalar.varptr.elem/neighbor, strarr.varptr.neighbor above): the
    # reference's VARPTR requires its argument to already exist.
    # h2.varptr.defstr.elem: the SAME string-triggered shift as strarg.elem
    # above, but reaching type 1 via a DEFSTR-typed BARE name (var_name_key ->
    # deftbl_lookup -> type 1) rather than the `$` suffix (var_str_type). Both
    # now allocate a stride-6 string entry post-d92c3da; this case is retained
    # to cover the DEFTBL type-resolution path specifically (the two routes to
    # a string scalar exercise different key/type code in var_name_key).

    # GC-root correctness (§9): several string SCALARS + a string ARRAY
    # element, then a real compacting GC (70x STRING$(250) churn), then
    # assert EVERY string scalar's content survived -- proves
    # sg_walk_scalars enumerates the chain roots at the correct entry+3
    # offset (a revert to entry+2 turns this case red -- verified by hand,
    # see tests/test_arrays.py Case 9c for the isolated non-emulator proof
    # of the same offset). zb-only (heap-pressure churn).
    ("gcroot.scalars.survive", "stored",
        ['CLEAR 4000:A$="alpha":B$="beta":C$="gamma":DIM S$(1):S$(0)="delta"',
         'FORI=1TO70:Z$=STRING$(250,65):NEXT',
         'PRINT"[";A$;B$;C$;S$(0);"]"'], "zbval"),

    # Edit-clears-all (§7.1/§7 deliverable 1): the case 4b's OWN spec
    # explicitly withheld ("would have gone red on the interim state" --
    # 4b left string scalars in the untouched fixed STRTAB pool, surviving
    # an edit). Now string scalars are chain-resident, cleared by the SAME
    # vars_reset a numeric-scalar edit already clears through -- DIFFEREN-
    # TIAL (confirmed empirically: the VG-8020 reference ALSO clears both
    # A$ and A on a program-line store, i.e. real MSX-BASIC's own faithful
    # "edit clears all variables" behaviour -- not a zb-only property).
    ("scalar.edit.clears.str", "direct",
        ['A$="X"', 'A=5', '10 PRINT 1', 'PRINT"[";A$;A;"]"'], "value"),

    # OOM (§7.3): the fixed 8-slot STRTAB cap is GONE; string-scalar count
    # is now bounded only by the shared free chain region, and exhausting
    # it must raise a SURFACED "Out of memory" (matching the array/numeric-
    # scalar OOM disposition), NOT silently drop the assignment (the old
    # STRTAB-full contract). A run of distinct one-letter `$` names must
    # exhaust the shared free chain region deterministically. zberr (zb-only:
    # the byte-for-byte ceiling arithmetic is zb's own chain layout, not a
    # property the reference's differently-shaped variable table can be an
    # oracle for) -- asserted against the reference-wording ZB_OOM literal,
    # the SAME string arrays' own OOM already uses.
    #
    # 🔴 THE SQUEEZE WAS `CLEAR 200,&H8050` UNTIL 2026-08-24 (D-HIMRANGE,
    # docs/spec-basic-himrange.md). &H8050 (32848) set HIMEM just above the
    # program so FRETOP=min(HIMEM,TXTMAX) left only ~77 B of chain room and
    # ~12 names exhausted it. But &H8050 is **ERR 7 (Out of memory) on the
    # VG-8020 AND the CF-3300** -- a ceiling below what BASIC needs for the
    # program + string space -- and zerobas now raises that too. The range
    # check GUARANTEES >=678 B of headroom by design, so no legal ceiling can
    # squeeze to 77 B. Instead a legal ceiling (50000) is set and a big array
    # DIM Z(1840) consumes the room the tight ceiling used to deny (MEASURED:
    # room ~14899 B, DIM fit boundary N~1853; N=1840 fits with ~104 B margin
    # and leaves an ~18-name gap, so of A$..Z$ the last 8 OOM). SAME code
    # path: str_set_key's scalar allocation still hits the full-region OOM;
    # the array just fills the region the ceiling used to.
    #
    # NON-VACUOUS proof (recorded here, verified by hand during
    # implementation): before wiring the FPERR check into ex_let_str
    # (basic/interp.asm), str_set_key's own scalar-chain-OOM correctly set
    # FPERR via ary_errmap, but NOTHING checked it afterward -- the
    # assignment silently dropped exactly like the pre-4c fixed-pool
    # contract (observed: no "Out of memory" text anywhere in the capture).
    ("scalar.str.chain.oom",   "direct",
        ['CLEAR 200,50000', 'DIM Z(1840)']
        + [f'{c}$="1"' for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"],
        "zberr"),

    # === VARPTR of an ARRAY ELEMENT (post-4c faithfulness follow-up, ==========
    # docs/spec-basic-varptr-array-element.md). Pre-slice ev_f_varptr expected
    # ')' right after the name, so a subscript '(' fell to a "syntax error";
    # the reference resolves the element and returns its value-field address.
    # ev_f_varptr now reuses ary_op0_resolve (op=0 RESOLVE, auto-dim on read --
    # the SAME resolver ev_f_arr uses) when the char after the name is '('. As
    # with the scalar VARPTR cases, no gate pins the moving ADDRESS itself --
    # each asserts the byte(s) AT the returned address, immediately, or the
    # error tail. Reference behaviour black-box characterised on VG-8020
    # 2026-07-18 (docs spec §2).
    #
    # numeric element: PEEK the value field. A%(0)=513 ($0201) -> low byte 1.
    ("arrelem.varptr.num",      "direct",
        ['A%(0)=513', 'PRINT"[";PEEK(VARPTR(A%(0)));"]"'], "value"),
    # multi-dimensional element resolves (DIM B(2,3); the default-double
    # element's first byte matches between machines).
    ("arrelem.varptr.multidim", "direct",
        ['DIM B(2,3):B(1,1)=513', 'PRINT"[";PEEK(VARPTR(B(1,1)));"]"'], "value"),
    # string element: VARPTR returns the [len][ptr] descriptor address; PEEK
    # of byte 0 is the length. S$(0)="hi" -> 2.
    ("arrelem.varptr.str",      "direct",
        ['S$(0)="hi"', 'PRINT"[";PEEK(VARPTR(S$(0)));"]"'], "value"),
    # auto-dim on read: VARPTR(GG(0)) on an undeclared array dims GG to 10
    # (read semantics), so GG(10) is then in range and reads 0 -- if VARPTR did
    # NOT auto-dim, the line would abort before the PRINT. Both machines -> 0.
    ("arrelem.varptr.autodim",  "direct",
        ['Z=VARPTR(GG(0))', 'PRINT"[";GG(10);"]"'], "value"),
    # element address is distinct from the same-named scalar's (E(0) vs E).
    ("arrelem.varptr.distinct", "direct",
        ['DIM E(3):E(0)=9:E=8', 'PRINT"[";VARPTR(E(0))<>VARPTR(E);"]"'], "value"),
    # out-of-range subscript -> the reference's "Subscript out of range"
    # (deferred FPERR, surfaced at the PRINT boundary; differential).
    ("arrelem.varptr.oor",      "direct",
        ['DIM C(2)', 'PRINT"[";VARPTR(C(5));"]"'], "err"),
    # negative subscript -> "Illegal function call" (differential).
    ("arrelem.varptr.neg",      "direct",
        ['DIM D(2)', 'PRINT"[";VARPTR(D(-1));"]"'], "err"),
    # empty subscript -> the deferred syntax error (zerobas lowercase house
    # text vs the reference's capitalised "Syntax error" -- documented
    # deviation, so synerr not err). A LET (not PRINT"[";...) so no leading
    # bracket precedes the aborting error -- the tail is the bare house text.
    ("arrelem.varptr.empty",    "direct",
        ['A=VARPTR(H())'], "synerr"),
    # H4 re-entrancy (Fable review): the subscript is itself an array rvalue,
    # so the inner ev_f_arr runs the SAME parse machinery ary_op0_resolve does.
    # X(0)=2, X(2)=513 -> VARPTR(X(X(0)))=VARPTR(X(2)); X default-double, so
    # PEEK of the value field's first byte matches the reference.
    # ROOT CAUSE (2026-07-20), for the record: this failed 67-vs-18 not because
    # of re-entrancy but because ev_f_varptr never set FACTYP=2. It returns the
    # address in DE, and the subscript's own eval() left FACTYP=8 with the
    # SUBSCRIPT still in FAC -- so PRINT/LET read FAC and ignored DE, i.e.
    # VARPTR(X(X(0))) evaluated to 2 (=X(0)) and PEEK(2) is 18. A LITERAL
    # subscript leaves FACTYP=2, which is why every other varptr case above
    # passed. Fixed by a set_factyp_int_ret in expr.asm's vptr_arr.
    ("arrelem.varptr.nested",   "direct",
        ['DIM X(3):X(0)=2:X(2)=513', 'PRINT"[";PEEK(VARPTR(X(X(0))));"]"'], "value"),
    # ...and the SIMPLER form of that same FACTYP bug, which was ungated: a
    # plain SCALAR-variable subscript is also non-literal, so it too left
    # FACTYP=8 (V default-double). Cheaper than the nested case and fails
    # independently of the array-re-entrancy path -- keep BOTH so a regression
    # in either can't hide behind the other.
    ("arrelem.varptr.varsub",   "direct",
        ['DIM X(3):X(2)=513:V=2', 'PRINT"[";PEEK(VARPTR(X(V)));"]"'], "value"),
    # malformed close: a subscript with no outer ')' (VARPTR(A(0)) missing one
    # ')'). ev_f_arr consumes the subscript's own ')', then vptr_close finds no
    # VARPTR ')' -> the CHECKED deferred syntax error (Fable review: pre-fix
    # this silently returned 0 because the reject went through the bare ERRMARK
    # ev_f_err). LET so no bracket precedes the abort; synerr (lowercase house).
    ("arrelem.varptr.noparen",  "direct",
        ['DIM A(3):B=VARPTR(A(0)'], "synerr"),
]

# --- S6 2nd-review GC-STRESS battery (its OWN pass, gc_stress_check below, with
# a big per-case step -- these churn 400-800 loop iterations + real GC pauses,
# far longer than the main batch's per-case time). The GC sort buffer moved
# from the high-RAM hardware stack (which grew down through the disk resident
# work area $F242+, corruptible under DI) to DETOKBUF ($BE00). The path is
# chosen by ROOT COUNT: n<=256 -> DETOKBUF sub-quadratic sort; n>256 -> gc_slow
# (in-place O(n^2) selection, no buffer). ALL zb-only (the reference's ~200 B
# default string space can't hold these churns); each asserts the DERIVABLE-
# correct value and forces a real compacting GC (refill garbage + live > zb's
# ~15 KB heap). (label, lines, expected_span).
GC_STRESS = [
    # (a)+(c-high) gc_slow path: >256 LIVE roots force the O(n^2) fallback and
    # exercise the switch on the OVER-256 side. STRING$(35) keeps 270 live bodies
    # (9450 B) well under the ~15 KB heap so the refill fires gc_slow a bounded
    # 1-2 times (STRING$(50)=13500 B near-fills the heap -> GC thrashes on nearly
    # every reassign, 270 * O(n^2), which blows the capture window).
    # STRENGTHENED (Fable 2026-07-17 gate-gap): the old assert summed only LEN(),
    # which lives in the DESCRIPTOR and is UNTOUCHED by a body-move bug -> it
    # passed even with every body corrupted. Now do a per-element CONTENT compare
    # (F = count of elements whose bytes != STRING$(35,66)); F=0 witnesses the
    # actual heap bodies survived GC. Kept the sum + both boundary chars too.
    # A pre-built reference R$ (one heap body) drives the CONTENT compare instead
    # of allocating a STRING$ temp per element -- else 270 allocs in a near-full
    # heap balloon the run past the capture window.
    # ⚠️ EVERY `CLEAR` IN THIS GROUP WAS RE-SIZED 2026-07-29 (D-LINEMAX), and the
    # reason matters more than the numbers. D-LINEMAX re-homed three line buffers
    # into page 2 and lowered TXTMAX $BE00 -> $B700 to fund them, so the program
    # area shrank by 1792 B: boot FRE(0) is 15667 -> 13875, MEASURED on the built
    # machine, not computed. `CLEAR 14000` now leaves 75 free bytes and `CLEAR
    # 15000` cannot be satisfied at all, so all five rows below died on their
    # FIRST line -- the readout came back as the typed echo, which is what a
    # statement that never ran looks like through an echo-anchored reader.
    #
    # These reservations were always generous, never load-bearing: each row's
    # expected value is derived from its OWN data (root count x string length, or
    # four poked sentinels), never from a capacity reading, so no assertion here
    # depends on the pool size. All five now reserve 11500.
    #
    # ⚠️ UPDATE 2026-07-29 (D-FCH §3.3): the premise above has MOVED AGAIN, in the
    # other direction. TOKBUF and LINEBUF left page 2 for the window S-FCH-1 freed
    # in page 3, so TXTMAX rose $B700 -> $BB00 and boot FRE(0) is now **14899**
    # (measured, not computed). The 11500 reservations still fit with room to
    # spare, so nothing here needed re-sizing and the payload shrinks above were
    # deliberately LEFT as they are -- restoring them is a separate call, not a
    # silent side effect of a RAM change. Note the capacity D-LINEMAX cost the
    # suite (a ~12 KB string workload) is affordable again.
    #
    # ⚠️ THE ROOT COUNT IS THE SUBJECT IN EVERY ROW; THE STRING LENGTH NEVER WAS.
    # 270 (> 256 -> gc_slow), 200 (< 256 -> the DETOKBUF fast path + sort), and the
    # 256/257 PAIR (the exact path switch, 2N=512 B filling DETOKBUF exactly) are
    # what these cases pin. So where a pool had to shrink, the PAYLOAD shrank and
    # the roots did not: 270x35 -> 270x20 (T 9450 -> 5400), 200x60 -> 200x40
    # (T 12000 -> 8000), and both edge rows 40 -> 20 chars (LEN 40 -> 20). Every
    # path under test is unchanged, and the per-element CONTENT compare that makes
    # this group non-vacuous (F=0 over every element, not a LEN() sum) is untouched.
    #
    # ⚠️ SHRINKING THE PAYLOAD IS ALSO WHAT KEPT THEM FAST ENOUGH TO READ. Forcing
    # GC is the point -- each row writes its live set TWICE -- but GC fires once per
    # pool-full, so a live set near the pool ceiling means O(n) collections of O(n)
    # work each. At 11500 with the ORIGINAL payloads, gc.n270.slow and gc.n257.edge
    # ran past the capture window and read back as their own typed echo, which is
    # indistinguishable from a wedge. The header on gc.n270.slow already warned
    # about exactly this; a tighter pool is what made it bite two rows.
    #
    # ⚠️ REAL COVERAGE WAS LOST, AND IT IS NOT HIDDEN: this group no longer proves
    # that a ~12 KB string workload runs at all -- 12000 bytes live no longer fits
    # in 13875 with working room for GC. That capability is what the RAM cut spent.
    # It is a capacity loss, not a test weakened to fit.
    ("gc.n270.slow",
     ['CLEAR 11500:DIM S$(270):FORI=1TO270:S$(I)=STRING$(20,65):NEXT',
      'FORI=1TO270:S$(I)=STRING$(20,66):NEXT',
      'R$=STRING$(20,66):F=0:T=0:FORI=1TO270:T=T+LEN(S$(I)):IFS$(I)<>R$THENF=F+1',
      'NEXT:PRINT"[";F;T;LEFT$(S$(1),1);LEFT$(S$(270),1);"]"'],
     " 0  5400 BB"),
    # (b)+(c-low) DETOKBUF fast path, ~200 roots (under the 256 cap) -> the
    # switch's UNDER-256 side + the DETOKBUF sort. Per-element CONTENT check.
    ("gc.n200.detok",
     ['CLEAR 11500:DIM S$(200):FORI=1TO200:S$(I)=STRING$(40,65):NEXT',
      'FORI=1TO200:S$(I)=STRING$(40,66):NEXT',
      'R$=STRING$(40,66):F=0:T=0:FORI=1TO200:T=T+LEN(S$(I)):IFS$(I)<>R$THENF=F+1',
      'NEXT:PRINT"[";F;T;LEFT$(S$(100),1);"]"'],
     " 0  8000 B"),
    # (c-boundary) pin the EXACT 256/257 path switch. n=256 (last DETOKBUF slot,
    # 2N=512 B fills the buffer exactly) and n=257 (first gc_slow) must BOTH keep
    # every body intact through a forced GC. One case per side; content-checked.
    ("gc.n256.edge",
     ['CLEAR 11500:DIM S$(256):FORI=1TO256:S$(I)=STRING$(20,65):NEXT',
      'FORI=1TO256:S$(I)=STRING$(20,66):NEXT',
      'R$=STRING$(20,66):F=0:FORI=1TO256:IFS$(I)<>R$THENF=F+1',
      'NEXT:PRINT"[";F;LEN(S$(256));LEFT$(S$(256),1);"]"'],
     " 0  20 B"),
    ("gc.n257.edge",
     ['CLEAR 11500:DIM S$(257):FORI=1TO257:S$(I)=STRING$(20,65):NEXT',
      'FORI=1TO257:S$(I)=STRING$(20,66):NEXT',
      'R$=STRING$(20,66):F=0:FORI=1TO257:IFS$(I)<>R$THENF=F+1',
      'NEXT:PRINT"[";F;LEN(S$(257));LEFT$(S$(257),1);"]"'],
     " 0  20 B"),
    # (e) DISK-INTERLEAVED GC -- the exact $F240 bug class. Stamp sentinels into
    # the disk resident work-area cells the old high-RAM stack buffer would
    # trample (W50A9_WRKB $F242 / CURDRV $F247 / RES_STUBS $F24E / DRVTBL $F348),
    # force a heavy GC with ~100 array roots (the old 200-byte buffer at SP-200
    # reached $F242+), then read them back: intact IFF GC used DETOKBUF, not the
    # stack. FAILS on the old $F240 code (NON-VACUOUS). Leaving the sentinels is
    # harmless -- gc_stress runs last, then the next suite reboots.
    ("gc.diskcells",
     ['CLEAR 11500:POKE&HF242,111:POKE&HF247,122:POKE&HF24E,133:POKE&HF348,144',
      'DIM S$(100):FORI=1TO100:S$(I)=STRING$(100,65):NEXT',
      'FORI=1TO100:S$(I)=STRING$(100,66):NEXT',
      'PRINT"[";PEEK(&HF242);PEEK(&HF247);PEEK(&HF24E);PEEK(&HF348);"]"'],
     " 111  122  133  144 "),
    # BUG B (Fable 2026-07-17) -- a FRESH string-scalar slot's stale [len][ptr]
    # must NOT survive as a phantom GC root. RE-TUNED TWICE since the original:
    #   * slice-4c dissolved the fixed STRTAB pool ($E240-$E268 freed), so the
    #     original $E242 slot-0 POKE seeds dead RAM now. A fresh string scalar
    #     is a stride-6 [name0][name1][type][len][ptr:2] entry INSERTED at
    #     ARYTAB (end of the unified scalar chain, sub/arrays.asm scv_alloc);
    #     the BUG-B neutralizer is scv_alloc's zero-fill (scva_zero_lp) of the
    #     3-byte value field. Seed address is therefore VARPTR-anchored: with
    #     A$ the LAST scalar created, the next entry lands at VARPTR(A$)+3 and
    #     its descriptor at VARPTR(A$)+6.
    #   * the error-handling arc S1 D-1 fix (untrapped runtime error ABORTS
    #     the RUN) killed the old 64-element over-fill: the FOR loop's first
    #     OOM now aborts, so the old construction left >250 B free and P$
    #     stored fine. DIRECT mode (4th field) + a CLEAR-shrunk heap replace
    #     it: each direct line survives the previous line's abort, and
    #     a legal CLEAR (>= TXTMAX) pins the heap ceiling (C=min(HIMEM,TXTMAX)=
    #     TXTMAX, FRETOP reset to C) so no fill loop is needed at all. (Was
    #     `CLEAR,&H82C0` until D-HIMRANGE made that ceiling ERR 7 -- see the
    #     Sizing note below.)
    # ⚠️ RE-TARGETED A THIRD TIME (D-CLP, 2026-07-29) -- THE ORIGINAL WINDOW NO
    # LONGER EXISTS, so the old construction was asserting an unreachable state.
    # It required, in order: (a) build a 250-byte temp, (b) SUCCEED at
    # str_set_key's H1 snapshot, (c) FAIL op=12 sh_var_store's own
    # heap_alloc(250), leaving the freshly inserted P$ entry at its scv_alloc
    # zero-fill. The CLEAR string-pool partition removed BOTH halves of that:
    #   * str_snapshot_keep returns a source that is ALREADY a temp unchanged
    #     and sh_var_store ADOPTS a temp's body -- so from str_set_key, SH_SRC
    #     is always either a temp (adopted, cannot fail) or STR_EMPTY (len 0,
    #     trivially succeeds). **op=12's OOM branch is unreachable from the
    #     scalar LET path.**
    #   * scv_ceil_try's GC-retry arm was deleted as dead code (its ceiling is
    #     now the fixed pool floor, which GC cannot move), so no GC runs between
    #     the insert and the store either.
    # Those were exactly the two things that made a stale slot observable as a
    # LIVE PHANTOM ROOT, so BUG B's hazard is now structurally absent rather
    # than merely untriggered. The zero-fill ITSELF is still asserted directly,
    # and more strongly, by tests/test_arrays.py ("'S$' entry = [name0][name1]
    # [type=1][len=0][ptr=0] fully zero-filled 3 B") -- which reads the slot
    # right after scv_alloc with no store in between, i.e. exactly the moment
    # this black-box case could only ever approximate.
    #
    # What this case pins NOW is the surviving observable half: a fresh scalar
    # slot must be OWNED by the store, never left holding whatever bytes were
    # there. The seed is unchanged in spirit -- [200][$82A0], with the ptr inside
    # [FRETOP,C) so it would be a live root if it survived -- and the readout is
    # the descriptor's own length byte. Genuine path: LEN(P$)=250 and W=250.
    # Seed survived (slot never written): W=200, and LEN would read 200 over a
    # garbage body. Store OOM'd: LEN=0. NON-VACUOUS in every direction.
    # Sizing: 🔴 RE-TARGETED A FOURTH TIME (D-HIMRANGE, 2026-08-24). The old
    # `CLEAR 400,&H82C0` set the ceiling to $82C0 (33472), which is now
    # **ERR 7 Out of memory on the VG-8020 AND the CF-3300** (below the program +
    # string space) -- zerobas raises it too. A legal ceiling >= TXTMAX pins the
    # pool just as deterministically, WITHOUT a magic low address: C =
    # min(HIMEM,TXTMAX) = TXTMAX = $BB00 for any HIMEM >= TXTMAX, so
    # `CLEAR 400,50000` -> C=$BB00, pool [$B970,$BB00). A$ costs 60
    # (FRETOP=$BAC4), P$'s temp 250 -> 310 of 400, and the seed ptr $BAE0 sits
    # inside [FRETOP,C)=[$BAC4,$BB00) exactly as $82A0 did in the old window.
    ("gc.bugB.phantom",
     ['CLEAR 400,50000',
      'V=0:A$=STRING$(60,66)',
      'V=VARPTR(A$):POKEV+6,200',
      'POKEV+7,&HE0:POKEV+8,&HBA',
      'P$=STRING$(250,67)',
      'W=PEEK(V+6)',
      'PRINT"[";LEN(P$);W;"]"'],
     " 250  250 ", "direct"),
]

# BUG A + BUG C regression cases (Fable 2026-07-17), DIRECT mode (fast; the
# error-disposition ones must run in DIRECT so the abort is observable -- the
# stored-RUN "doesn't halt on runtime error" landmine). zb house behaviour
# (lowercase message / in-place MID$ overwrite), asserted against the literal.
# (label, lines, expected_span).
ABC_REGRESSION = [
    # BUG A: MID$(A$,n)=RHS whose RHS pushes >=3 temps. CHR$(66)+CHR$(67) is the
    # coordinator's exact repro; the old MIDS_DEST=$E3D9 aliased the 3rd temp
    # slot's ptr field -> sh_mid_store LDIR'd through garbage (no-op / corruption).
    # Now MIDS_DEST=TMISMATCH+1 ($E3E6), clear of the pool: A$ -> "BCLLO".
    ("bugA.mid3temp",
     ['A$="HELLO":MID$(A$,1)=CHR$(66)+CHR$(67)', 'PRINT A$'], "BCLLO"),
    # BUG C: a '+' commits to string concat but the trailing operand is numeric.
    # Old code silently re-drove numerically (" 0"); now a deferred Type mismatch.
    ("bugC.concat.typemis",
     ['A$="HELLO"', 'PRINT A$+5'], "Type mismatch"),
    # BUG C: LEFT$/MID$/RIGHT$ with a missing 2nd arg. The old IX-clobber-on-NC
    # re-drove into ev_f with garbage IX and SPUN the print loop emitting " 0";
    # now ev_rel restores IX + ev_ff_strnum defers FPERR=4 -> clean syntax error.
    ("bugC.leftmiss.syntax",  ['PRINT LEFT$("AB")'],  "Syntax error"),
    ("bugC.midmiss.syntax",   ['PRINT MID$("AB")'],   "Syntax error"),
    # regression guard: the VALID forms still work (no over-eager error).
    ("bugC.left.ok",          ['PRINT LEFT$("ABCDE",3)'], "ABC"),
    ("bugC.strcmp.ok",        ['A$="XY":PRINT A$="XY"'],  "-1"),
    # BUG C straggler (Fable pass 4): CVI without '(' -- ev_ff_cvi's missing-'('
    # exit was a bare ev_f_err (no FPERR) -> silent " 0"; now deferred syntax
    # error. ref (VG-8020) = "Syntax error"; zb house-lowercase.
    ("bugC.cvi.noparen",      ['PRINT CVI'],             "Syntax error"),
    ("bugC.cvi.ok",           ['B$="XY":PRINT CVI(B$)'], "22872"),
    # KNOWN RESIDUAL 2 follow-up (2026-07-17): two PRE-EXISTING function-domain
    # value errors used a bare ev_f_err (ERRMARK only, no FPERR) -> silent " 0".
    # 🔴 THESE TWO SAT RED AT 149/151 FOR MONTHS AND THE EXPECTATION WAS THE BUG.
    # They were filed as "zerobas prints the wrong case"; they are nothing of the
    # kind. D-MISS-2 folded INSTR's position check into eval_pos_arg
    # (basic/interp.asm), whose reject path is gb_illegal -> raise_error(5) ->
    # err_msgtab[5], i.e. the CAPITALISED string -- the lowercase ev_f_ifc route
    # these rows assert was DELETED by that slice (basic/str-engine.asm documents
    # the deletion). The rows kept measuring a path that no longer existed, and a
    # red row assumed stale is a red row that measures nothing.
    # D-MSGEXACT then made `Illegal function call` the ONLY spelling tree-wide, so
    # asc.empty (still a genuine FPERR=3 site) reads identically to the INSTR pair.
    ("ifc.instr.zero",        ['PRINT INSTR(0,"AB","A")'],   "Illegal function call"),
    ("ifc.instr.neg",         ['PRINT INSTR(-1,"AB","A")'],  "Illegal function call"),
    ("ifc.asc.empty",         ['PRINT ASC("")'],             "Illegal function call"),
    # regression guards: valid INSTR/ASC unchanged (no over-eager IFC).
    ("ifc.instr.ok",          ['PRINT INSTR(1,"AB","A")'],   "1"),
    ("ifc.instr.ok2",         ['PRINT INSTR(2,"ABAB","AB")'], "3"),
    ("ifc.asc.ok",            ['PRINT ASC("A")'],            "65"),
    # LEN(5) FINALLY (2026-07-17): a string fn given a NUMERIC arg is "type
    # mismatch" (ref), was silent " 0" then a wrong "syntax error". ev_str_arg's
    # non-string exit -> ev_f_tmm (FPERR=10). First-error-wins SPLITS numeric-arg
    # (type mismatch) from a nested-malformed string fn (syntax error) -- the
    # latter enabled by routing str_fn_*'s structural exits through str_arg_empty.
    ("tmm.len.num",           ['PRINT LEN(5)'],              "Type mismatch"),
    ("tmm.asc.num",           ['PRINT ASC(5)'],              "Type mismatch"),
    ("tmm.val.num",           ['PRINT VAL(5)'],              "Type mismatch"),
    # regression guard: a nested MALFORMED string fn stays "syntax error" (NOT
    # type mismatch) -- the case the str_arg_empty retarget protects.
    ("tmm.len.nested.syn",    ['PRINT LEN(LEFT$("AB"))'],    "Syntax error"),
    ("tmm.rt.nested.syn",     ['PRINT LEN(RIGHT$("AB"))'],   "Syntax error"),
    # regression guard: valid nested/plain string args still compute.
    ("tmm.len.chr.ok",        ['PRINT LEN(CHR$(65))'],       "1"),
    ("tmm.len.str.ok",        ['PRINT LEN("HELLO")'],        "5"),
]

# zbval: NON-DIFFERENTIAL, house-expected printed VALUE (keyed by label). Used
# for a property the reference is NOT a meaningful oracle for -- here, GC
# integrity: whether zb's OWN compacting collector corrupts memory is a
# zb-internal property (the reference has different memory behaviour and its
# slow O(n^2) collector / smaller RAM can't even complete the churn), so the
# result is asserted against the DERIVABLE-correct value. The spans use MSX
# PRINT's leading-space-for-non-negatives convention (observed, not asserted
# from memory). strarr.gc.churn: 5 elements, each finally STRING$(250,66) ->
# LEN=250 (" 250 ") + LEFT$=first char ("B") -> span " 250 B".
ZBVAL_EXPECT = {
    "strarr.gc.churn": " 250 B",
    "strarr.dim.aftergc": " 250 / 99 ",
    # scalar.collision.gc.ok (arrays slice-4b §9): 70 x STRING$(250) leaves
    # A$ holding the LAST one (LEN=250); ZZ=12345 -- the SCALAR_ALLOC that
    # must collide-then-GC-then-succeed.
    "scalar.collision.gc.ok": " 250 / 12345 ",
    # §13a stale-array-element-address fix (see the CASES entries above for
    # why these are zb-only): observed 2026-07-17 on the repack build via
    # probes/lib/omsx_repl.py directly, post-fix.
    "scalar.varptr.elem": "-1 ",
    "scalar.varptr.neighbor": " 22 ",
    "strarr.varptr.neighbor": "world",
    # arrays slice-4c (§9): H1 battery + H2 + GC-root correctness.
    "h1.srcarrelem": "hello",
    "h1.srcconcat": "foobar",
    "h1.self": "",
    "h2.varptr.strarg.elem": "-1 ",
    "h2.varptr.defstr.elem": "-1 ",
    "gcroot.scalars.survive": "alphabetagammadelta",
}

# Tier-A house-style text (zerobas prints lowercase where the reference prints
# capitalised; not differential-gateable, asserted against this literal).
ZB_SYNTAX_ERROR = "Syntax error"

# §7 D-2: zb raises this where the reference succeeds (the inline-element memory
# cost of the signed-off slice-3 element format). Reference wording, matched
# against zb's own tail (observed 2026-07-15, DIM S$(1000) on the repack build).
ZB_OOM = "Out of memory"

# Crunch-identity rows (§2): the exact stored-line token bytes. Checked BOTH ways
# (zerobas == VG-8020 reference AND == this literal), the same discipline
# basic_probe_crunch.py uses for the string keywords. $A5 = ERASE, $2C = ',' .
CRUNCH_CASES = [
    ("crunch.erase.a",  "ERASE A",   "a5204100"),
    ("crunch.erase.ab", "ERASE A,B", "a520412c4200"),
    # arrays slice 3 (§2): "no tokeniser/detokeniser change" pin -- DIM S$(5)
    # crunches exactly like the numeric DIM A(5) case (basic-arrays.md §5),
    # `$`=$24 riding inside the crunched name with no new token.
    ("crunch.dim.s5",   "DIM S$(5)", "8620532428162900"),
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
    if kind == "zbval":
        # NON-differential: assert zb's own printed value against the derivable-
        # correct expectation (ZBVAL_EXPECT[label]); ref is ignored (not a
        # meaningful oracle -- see ZBVAL_EXPECT's comment).
        zv = R.result_span(zb) if mode == "stored" else R.result_span_after_echo(zb, cmd)
        return zv == ZBVAL_EXPECT[label]
    if kind == "zberr":
        # NON-differential the OTHER way: zb ERRORS where the reference SUCCEEDS
        # (§7 D-2 -- the inline 65-byte string element makes a big DIM exhaust
        # RAM that the reference's 3-byte [len][ptr] descriptors survive). Assert
        # zb's own error tail only; ref is ignored (it prints a value).
        return R.screen_tail(zb, cmd) == ZB_OOM
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


# --- INPUT chain-OOM (arrays slice-4c §7.3 follow-up, post-4c Fix 1) -------
# console/LINE INPUT/INPUT# string-store now SURFACES a scalar-CHAIN OOM
# (str_set_key's own ARY_OP=5 path, exactly like ex_let_str's already-shipped
# check just above -- scalar.str.chain.oom in CASES) instead of silently
# swallowing it (basic/input.asm inpc_vstr/inpc_line, basic/files.asm
# inp_readvar; reuses check_expr_errors/check_expr_errors_popbc, interp.asm,
# rather than a bespoke checker). zb-only (zberr-class): the tight CLEAR
# ceiling is zb's own chain layout, same disposition as scalar.str.chain.oom.
# LINE INPUT is used here (not console INPUT) because it needs no field-list
# bookkeeping and exercises the SP-clean-site helper (check_expr_errors);
# console INPUT's own extra-word-drop helper (check_expr_errors_popbc) is
# exercised live by every "multi"/"redo"/"extra" case in basic_probe_
# input.py (input-acceptance) already, just never at OOM. Each LINE INPUT
# statement needs its OWN typed response line before the next statement can
# run, so this can't fit the (label, mode, lines, kind) CASES shape (whose
# "err"/"zberr" dispositions anchor on lines[-1] -- here that would be a
# RESPONSE, not the command) -- it gets its own small battery + check
# function instead (like ABC_REGRESSION/GC_STRESS below), anchoring
# screen_tail on the LAST LINE INPUT statement's own echo explicitly.
#
# 🔴 THE SQUEEZE WAS `CLEAR,&H8050` THEN `CLEAR 200,&H8050`; IT IS NOW A LEGAL
# CEILING + A ROOM-FILLING DIM (D-HIMRANGE, 2026-08-24). History: the leading-
# comma `CLEAR,&H8050` (a Syntax error on both references) was retired by
# D-CLRFIX (-4 B); `CLEAR 200,&H8050` replaced it -- but &H8050 (32848) is
# **ERR 7 Out of memory on the VG-8020 AND the CF-3300** (a ceiling below the
# program + string space), and D-HIMRANGE makes zerobas raise that too. The
# range check GUARANTEES >=678 B of chain headroom, so no legal ceiling can
# squeeze the chain; `CLEAR 200,50000 : DIM Z(1840)` consumes the room instead
# (see scalar.str.chain.oom's own header for the sizing). SAME OOM path.
# NON-VACUOUS (verified by hand 2026-07-17, `git stash` on the input.asm/
# files.asm fix + rebuild): pre-fix the tail after the LAST 'LINE INPUT Z$'
# echo was plain '1' (the response, silently accepted, no OOM text -- the
# retired pre-4c STRTAB-full "silent drop" contract survived into the INPUT
# path even after ex_let_str's own fix); post-fix it is '1|Out of memory'.
INPUT_OOM = [
    ("scalar.input.chain.oom",
     ['CLEAR 200,50000', 'DIM Z(1840)'] +
     [ln for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" for ln in (f'LINE INPUT {c}$', '1')],
     "LINE INPUT Z$", "1|Out of memory"),
]


def input_oom_check():
    """INPUT chain-OOM battery (see INPUT_OOM's own header comment above).
    Returns (npass, ntotal)."""
    specs = [("direct", lines) for _, lines, _cmd, _want in INPUT_OOM]
    out = R.run_cases(ZB, specs, batch=True, reset=("NEW", "CLS"),
                      step=6.0, boot=8.0, omsx=OMSX)
    npass = 0
    for (label, _lines, cmd, want), zr in zip(INPUT_OOM, out):
        got = R.screen_tail(zr, cmd)
        ok = got == want
        npass += ok
        print(f"  {'PASS' if ok else 'FAIL':4}  {label:<22} "
              f"{'' if ok else f'want={want!r} zb={got!r}'}")
    return npass, len(INPUT_OOM)


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


def gc_stress_check():
    """S6 GC-stress battery (zb-only): heavy string-array churns that force a
    real compacting GC on BOTH paths (n<=256 DETOKBUF sort / n>256 gc_slow) and
    the disk-work-area-intact case. Its OWN pass with a LARGE per-case step --
    each case runs 400-800 interpreted-BASIC allocations + GC pauses, well past
    the main batch's per-case time. Non-differential (the VG-8020's ~200 B
    string space can't run these), asserted against the derivable-correct span.
    Returns (npass, ntotal)."""
    # Each case runs in its OWN single-case batch with a large step: these
    # churns run far past the multi-case batch's per-case window (which would
    # misalign the capture), so one boot each keeps the capture clean.
    npass = 0
    for entry in GC_STRESS:
        label, lines, want = entry[0], entry[1], entry[2]
        mode = entry[3] if len(entry) > 3 else "stored"  # default stored; error-
        # dependent cases opt into "direct" (D-1: a runtime error aborts the RUN,
        # so a stored program can't observe state past its first error).
        zr = R.run_cases(ZB, [(mode, lines)], batch=True, reset=("NEW", "CLS"),
                         step=150.0, boot=8.0, omsx=OMSX)[0]
        got = R.result_span(zr)
        ok = got == want
        npass += ok
        print(f"  {'PASS' if ok else 'FAIL':4}  {label:<22} "
              f"{'' if ok else f'want={want!r} zb={got!r}'}")
    return npass, len(GC_STRESS)


def abc_regression_check():
    """BUG A/B/C regressions (Fable 2026-07-17), zb-only house behaviour: DIRECT
    mode so the deferred type-mismatch / syntax-error aborts are observable (the
    stored-RUN 'no runtime-error halt' landmine). Asserted against the literal
    span after the echoed command. Returns (npass, ntotal)."""
    specs = [("direct", lines) for _, lines, _ in ABC_REGRESSION]
    out = R.run_cases(ZB, specs, batch=True, reset=("NEW", "CLS"),
                      step=6.0, boot=8.0, omsx=OMSX)
    npass = 0
    for (label, lines, want), zr in zip(ABC_REGRESSION, out):
        cmd = lines[-1]
        # screen_tail (not result_span): the error-message cases print no '['..']'
        # bracket, so grab the raw text between the echo and the prompt.
        got = R.screen_tail(zr, cmd)
        ok = got == want
        npass += ok
        print(f"  {'PASS' if ok else 'FAIL':4}  {label:<22} "
              f"{'' if ok else f'want={want!r} zb={got!r}'}")
    return npass, len(ABC_REGRESSION)


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
    print("--- BUG A/B/C regressions (Fable 2026-07-17; zb house behaviour) ---")
    apass, atotal = abc_regression_check()
    npass += apass
    print("--- S6 GC-stress (zb-only; DETOKBUF sort / gc_slow / disk-cell intact) ---")
    gpass, gtotal = gc_stress_check()
    npass += gpass
    print("--- INPUT chain-OOM (post-4c Fix 1; zb-only) ---")
    ipass, itotal = input_oom_check()
    npass += ipass
    total = len(CASES) + ctotal + atotal + gtotal + itotal
    print(f"=== arrays: {npass}/{total} {'ALL PASS' if npass == total else 'SOME FAILED'} ===")
    return 0 if npass == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
