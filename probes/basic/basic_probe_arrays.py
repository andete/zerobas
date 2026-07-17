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
        ['FORI=1TO70:A$=STRING$(250,65):NEXT', 'DIM B(500):B(250)=99',
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
        ['DIM S$(5):FORI=1TO5:S$(I)=STRING$(250,65):NEXT',
         'FORJ=1TO15:FORI=1TO5:S$(I)=STRING$(250,66):NEXT:NEXT',
         'PRINT"[";LEN(S$(3));LEFT$(S$(3),1);"]"'], "zbval"),
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
    ("gc.n270.slow",
     ['DIM S$(270):FORI=1TO270:S$(I)=STRING$(35,65):NEXT',
      'FORI=1TO270:S$(I)=STRING$(35,66):NEXT',
      'R$=STRING$(35,66):F=0:T=0:FORI=1TO270:T=T+LEN(S$(I)):IFS$(I)<>R$THENF=F+1',
      'NEXT:PRINT"[";F;T;LEFT$(S$(1),1);LEFT$(S$(270),1);"]"'],
     " 0  9450 BB"),
    # (b)+(c-low) DETOKBUF fast path, ~200 roots (under the 256 cap) -> the
    # switch's UNDER-256 side + the DETOKBUF sort. Per-element CONTENT check.
    ("gc.n200.detok",
     ['DIM S$(200):FORI=1TO200:S$(I)=STRING$(60,65):NEXT',
      'FORI=1TO200:S$(I)=STRING$(60,66):NEXT',
      'R$=STRING$(60,66):F=0:T=0:FORI=1TO200:T=T+LEN(S$(I)):IFS$(I)<>R$THENF=F+1',
      'NEXT:PRINT"[";F;T;LEFT$(S$(100),1);"]"'],
     " 0  12000 B"),
    # (c-boundary) pin the EXACT 256/257 path switch. n=256 (last DETOKBUF slot,
    # 2N=512 B fills the buffer exactly) and n=257 (first gc_slow) must BOTH keep
    # every body intact through a forced GC. One case per side; content-checked.
    ("gc.n256.edge",
     ['DIM S$(256):FORI=1TO256:S$(I)=STRING$(40,65):NEXT',
      'FORI=1TO256:S$(I)=STRING$(40,66):NEXT',
      'R$=STRING$(40,66):F=0:FORI=1TO256:IFS$(I)<>R$THENF=F+1',
      'NEXT:PRINT"[";F;LEN(S$(256));LEFT$(S$(256),1);"]"'],
     " 0  40 B"),
    ("gc.n257.edge",
     ['DIM S$(257):FORI=1TO257:S$(I)=STRING$(40,65):NEXT',
      'FORI=1TO257:S$(I)=STRING$(40,66):NEXT',
      'R$=STRING$(40,66):F=0:FORI=1TO257:IFS$(I)<>R$THENF=F+1',
      'NEXT:PRINT"[";F;LEN(S$(257));LEFT$(S$(257),1);"]"'],
     " 0  40 B"),
    # (e) DISK-INTERLEAVED GC -- the exact $F240 bug class. Stamp sentinels into
    # the disk resident work-area cells the old high-RAM stack buffer would
    # trample (W50A9_WRKB $F242 / CURDRV $F247 / RES_STUBS $F24E / DRVTBL $F348),
    # force a heavy GC with ~100 array roots (the old 200-byte buffer at SP-200
    # reached $F242+), then read them back: intact IFF GC used DETOKBUF, not the
    # stack. FAILS on the old $F240 code (NON-VACUOUS). Leaving the sentinels is
    # harmless -- gc_stress runs last, then the next suite reboots.
    ("gc.diskcells",
     ['POKE&HF242,111:POKE&HF247,122:POKE&HF24E,133:POKE&HF348,144',
      'DIM S$(100):FORI=1TO100:S$(I)=STRING$(100,65):NEXT',
      'FORI=1TO100:S$(I)=STRING$(100,66):NEXT',
      'PRINT"[";PEEK(&HF242);PEEK(&HF247);PEEK(&HF24E);PEEK(&HF348);"]"'],
     " 111  122  133  144 "),
    # BUG B (Fable 2026-07-17) -- a FRESH STRTAB slot's stale [len][ptr] read as a
    # phantom GC root. Seed slot 0 (STRTAB=$E240; len@$E242, ptr@$E243/4) with a
    # bogus in-heap descriptor [len=200][ptr=$BD80]. String array elements are heap
    # [len][ptr] descriptors, so DIM S$(64) x STRING$(250) over-fills the ~15 KB
    # heap: the FIRST scalar store (P$ -> slot 0) is HEAP-FULL and OOMs. On the
    # FIXED code ssk_new neutralized slot 0's len, so the OOM'd P$ reads "" ->
    # LEN=0. NON-VACUOUS: on the pre-fix code the stale [200][$BD80] survived and
    # P$ read LEN=200 (verified: reverted ' 200 ' x3 stable vs fixed ' 0 '). LEN(P$)
    # is the deterministic witness; the array-integrity sum can't be pinned here
    # (the fill sits at the OOM boundary), so this asserts LEN(P$) alone.
    ("gc.bugB.phantom",
     ['POKE&HE242,200:POKE&HE243,&H80:POKE&HE244,&HBD',
      'DIMS$(64):FORI=1TO64:S$(I)=STRING$(250,65):NEXT',
      'P$=STRING$(250,67)',
      'PRINT"[";LEN(P$);"]"'],
     " 0 "),
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
     ['A$="HELLO"', 'PRINT A$+5'], "type mismatch"),
    # BUG C: LEFT$/MID$/RIGHT$ with a missing 2nd arg. The old IX-clobber-on-NC
    # re-drove into ev_f with garbage IX and SPUN the print loop emitting " 0";
    # now ev_rel restores IX + ev_ff_strnum defers FPERR=4 -> clean syntax error.
    ("bugC.leftmiss.syntax",  ['PRINT LEFT$("AB")'],  "syntax error"),
    ("bugC.midmiss.syntax",   ['PRINT MID$("AB")'],   "syntax error"),
    # regression guard: the VALID forms still work (no over-eager error).
    ("bugC.left.ok",          ['PRINT LEFT$("ABCDE",3)'], "ABC"),
    ("bugC.strcmp.ok",        ['A$="XY":PRINT A$="XY"'],  "-1"),
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
}

# Tier-A house-style text (zerobas prints lowercase where the reference prints
# capitalised; not differential-gateable, asserted against this literal).
ZB_SYNTAX_ERROR = "syntax error"

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
    for label, lines, want in GC_STRESS:
        zr = R.run_cases(ZB, [("stored", lines)], batch=True, reset=("NEW", "CLS"),
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
    total = len(CASES) + ctotal + atotal + gtotal
    print(f"=== arrays: {npass}/{total} {'ALL PASS' if npass == total else 'SOME FAILED'} ===")
    return 0 if npass == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
