- [x] 🐛 **`VAL` STOPS AT A TAB OR A LINE FEED INSIDE A NUMBER, AND REJECTS A GAP AFTER `&`: THE VG-8020 SKIPS BOTH
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
      84, 164-168); also BEFORE `&`: `VAL(CHR$(9)+"&HFF")` and the LF form are 255 there, 0 here (KNM VL 196, 197;
      goldfish pass 1, 2026-11-24). `"& "` and `"&"+CHR$(9)` (a gap, then the end) are error 2 on both. Other
      control characters (CR, 11, 12, 28, 31, 127, 160) are skipped by neither: 0 on both.
      ➡️ When picked up: the decimal path is `tk_float` (sub/tkfloat.asm, the tokeniser's scanner, which `VAL`
      calls) and the prefix path `sh_val_parse` (sub/strheap.asm). `READ` and typed program lines share the
      scanner: a row each for `READ` of a TAB-split `DATA` item and for a typed literal, against the reference,
      before changing the skip set. The acceptance is the two rules and their controls in
      [`knum_controls.py`](../../probes/basic/spec/knum_controls.py) (zerobas's rules, FALSE on 11 and 6 of the
      reference's cases).
      📏 SCOPE MEASURED BEFORE THE FIX (2026-11-25, scratchpad/readtab_probe.py; AE_readtab.out, AE_readtab_load.out,
      AE_readtab_prefix.out): IT IS ONE SCANNER RULE ON THE REFERENCE, NOT VAL'S. (1) READ of a DATA item `1<TAB>2` /
      `1<LF>2` (the space POKEd to 9 / 10 in the stored line; a control POKEs 'X' -- Syntax error on both, so the POKE
      lands): 12 on the VG-8020, **Syntax error in 10 on zerobas**; `1E<TAB>2` 100 there, the error here. (2) A typed
      literal can only carry a TAB through LOAD of an ASCII program (the editor turns the key into spaces): the
      CF-3300 tokenises `10 A=1<TAB>2` as `A=12` (LIST shows it closed up), zerobas keeps the TAB (`A=1 2`) and RUN is
      Syntax error. (3) The `&` prefix with a gap, LOADed: the CF-3300 crunches `A=& H10` and `A=&<TAB>H10` to `&H10`
      (16) and READs `DATA & H10` as 16; zerobas: Syntax error. So the fix covers the TOKENISER (basic/tokenise.inc
      tk_hex), READ and VAL. All three paths sit in the SUB ROM's page 0 (tkf_fetch $01CA -- the one place tk_float
      reads the source, which the tokeniser, READ and VAL all call; tk_hex $050C; VAL's svp_base $1A70), which has
      2 B free: ~25 B needed (a shared skip-blank helper, TAB / LF in tkf_fetch with `cp ' '` kept last for its
      callers' flags, the two & sites) -- a sub page-0 carve first. Not yet located: READ's DATA `&` path.
      ✅ FIXED 2026-11-25 (the decimal half): sub/tkfloat.asm tkf_fetch -- the one place tk_float reads the source,
      for the tokeniser, READ and VAL alike -- skips TAB and LF as it skips a space (`cp ' '` kept last for its
      callers' flags), +8 B in the sub ROM's page 0, made room for by a jp -> jr carve there (2 -> 17 B free: 14 sites
      in basic/tokenise.inc, sub/arrays.asm, sub/strheap.asm, sub/deffn.asm, sub2/filestmt.asm; tools/check_tenant_closure.py
      learned that `jr p0cb` is the same IX-target transfer as `jp p0cb`, selftest arms B1j / B1n). Now SAME as the
      reference: READ of `1<TAB>2` / `1<LF>2` 12, `1E<TAB>2` 100, `VAL("1"+CHR$(9)+"2")` 12, and a LOADed
      `A=1<TAB>2` stored as `A=12` (scratchpad/AE_readtab_after.out, AE_readtab_load_after.out); VAL.md's R-VAL-SPACE
      holds on zerobas (spec-live). The `&` half -- a gap after `&`, a TAB before it -- needs ~8 B per site and is
      D-AMPGAP (TIER 6).
