- [ ] 🐛 **`VAL` STOPS AT A TAB OR A LINE FEED INSIDE A NUMBER, AND REJECTS A GAP AFTER `&`: THE VG-8020 SKIPS BOTH
      (D-VALWS, found 2026-11-24 by D-KWSPEC's strings probe).**
      🎚️ TIER 1 — `VAL("1"+CHR$(9)+"2")` is ordinary typed BASIC (a TAB-separated line read from a file is the
      everyday shape) and answers a different number, no error anywhere.
      🤖 **AUTONOMOUS** — measured by [`knum.py`](../../probes/basic/spec/knum.py) ->
      [`KNM_run1.out`](../../scratchpad/KNM_run1.out), rules R-VAL-SPACE and R-VAL-PREFIX on
      [VAL.md](../../docs/keywords/VAL.md). The VG-8020 skips space, TAB (`CHR$(9)`) and LF (`CHR$(10)`) wherever it
      skips a space in a decimal number -- before it, after the sign, between digits, around the point, inside the
      exponent -- and also between `&` and its letter (H / O / B), never after the letter. zerobas skips spaces only,
      and nothing after `&`: `VAL(CHR$(9)+"12")` 12 there / 0 here, `VAL("1"+CHR$(9)+"2")` 12 / 1,
      `VAL("1E"+CHR$(9)+"3")` 1000 / 1, `VAL("-"+CHR$(9)+"12")` -12 / 0 (KNM VL 45-47, 160-163); `VAL("& H10")`,
      `VAL("&  H10")`, `VAL("& O17")`, `VAL("& B101")` and the TAB / LF forms 16 / 15 / 5 there, error 2 here (KNM VL
      84, 164-168). Other control characters (CR, 11, 12, 28, 31, 127, 160) are skipped by neither: 0 on both.
      ➡️ When picked up: the decimal path is `tk_float` (sub/tkfloat.asm, the tokeniser's scanner, which `VAL`
      calls) and the prefix path `sh_val_parse` (sub/strheap.asm). `READ` and typed program lines share the
      scanner: a row each for `READ` of a TAB-split `DATA` item and for a typed literal, against the reference,
      before changing the skip set. The acceptance is the two rules and their controls in
      [`knum_controls.py`](../../probes/basic/spec/knum_controls.py) (zerobas's rules, FALSE on 9 and 6 of the
      reference's cases).
