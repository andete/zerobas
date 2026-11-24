- [x] 🐛 **A SPACE BEFORE THE CLOSING PARENTHESIS AFTER `INSTR`'S / `STRING$`'S STRING ARGUMENT IS A SYNTAX ERROR
      (D-CLOSESPACE, found 2026-11-24 by D-KWSPEC's strings probe).**
      🎚️ TIER 1 — `INSTR(A$,B$ )` and `STRING$(2,A$ )` are ordinary typed BASIC; the VG-8020 accepts them.
      🤖 **AUTONOMOUS** — measured by [`kstr.py`](../../probes/basic/spec/kstr.py) ->
      [`KST_run1.out`](../../scratchpad/KST_run1.out): on the VG-8020 `INSTR(S$,T$ )`, `INSTR( S$ , T$ )`,
      `INSTR( 2 , S$ , T$ )`, `INSTR("ABCDE","CD" )` are all 3 and `STRING$(2,S$ )` is "AA"; zerobas raises
      error 2 for all five (cases KST FX 83, 84, 101, 113, 114; rules R-INSTR-FORMS, R-STRING-FORMS). Narrowed one
      space at a time (KST FX 98-108, 111-112): a space after `(`, before or after any comma, is accepted by both;
      only the space between the LAST string argument and `)` fails. `LEN( S$ )`, `ASC( S$ )`, `STRING$( 2 , 65 )` (a
      numeric last argument) agree. D-ARGSPACE (2026-10-31) fixed the space AFTER a delimiter; this is the one before
      the closing parenthesis.
      ➡️ When picked up: the `)` test after the string argument in INSTR and in STRING$'s string form (str-engine.asm)
      does not skip spaces first; LEFT$ / MID$ / RIGHT$ (numeric last argument) and the other string functions'
      last-argument paths are worth one row each in the same sweep.
      ✅ FIXED 2026-11-24: the `)` test after a string argument read the byte under the cursor without skipping spaces
      (`ld a,(hl)`); INSTR's and STRING$'s (sfg_close, shared by the numeric and string fill, and the empty-fill
      branch) now `call skip_spaces` first (basic/str-engine.asm). The FX group re-run (KST_run1.out): 0 of 129 cases
      differ (were FX 83, 84, 101, 113, 114, 116). The other `ld a,(hl) / cp ')'` sites in str-engine.asm follow a
      NUMERIC last argument (the numeric evaluator skips trailing spaces itself) -- LEFT$ / RIGHT$ / MID$ / LEN / ASC
      agree on kslice / kstr.
