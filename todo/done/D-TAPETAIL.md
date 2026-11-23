- [x] ✅ **D-TAPETAIL — THE CASSETTE SAVE VERBS' BAD TAILS PRINTED `load error`; THE VG-8020 RAISES
      2 / 5, AND A TAPE BSAVE HAS NO `,S` FLAG ON EITHER REFERENCE (measured and FIXED 2026-10-07)**
      🎚️ TIER 3 — common errors: a mistyped SAVE / CSAVE / BSAVE to tape.
      📏 Under ON ERROR on the diskless VG-8020
      ([`tapetail_before.out`](scratchpad/tapetail_before.out)): `SAVE "CAS:X" Q`
      2, `CSAVE "X",3` 5, `CSAVE "X",1,2` 2 -- ours `load error` for all three
      (predicted 2/5/2 -- hit). 🎯 Predicted `BSAVE "CAS:X",a,b,S` to be 2 too --
      **MISSED: it SAVES**. MSX1 BASIC has no `,S`: S is a variable, the exec.
      Then the CF-3300 also said OK, and OK cannot tell "S is a variable" from
      "S is the VRAM flag" -- so a DISCRIMINATOR: `S=70000` first. A variable
      exec overflows, a flag ignores S. **6 on the VG-8020 AND the CF-3300**
      ([`tapetail_s.out`](scratchpad/tapetail_s.out),
      [`tapetail_big.out`](scratchpad/tapetail_big.out); predicted, hit): a tape
      BSAVE takes `,S` as a variable on both; Disk BASIC's flag is a disk-BSAVE
      thing.
      ✅ basic/save.asm: `csav_speed` raises 5 on a bad speed and 2 on junk (its
      CF exit and the caller's `jp c,load_error` gone); SAVE"CAS:"'s junk test
      ends at 0 OR `:` and raises 2 (it took `:` for junk before); the tape BSAVE
      parses its 4th slot with `bsave_opt4_cas` -- an exec expression only -- and
      BOTH arms type the exec as an address (`eval_addr` + `check_expr_errors`:
      a disk `,70000` is 6 and `,"A"` 13 on the CF-3300, the file not created).
      Main page 1 85 → 77 B.
      Gate `tapetail-acceptance`
      ([`probes/basic/basic_probe_tapetail.py`](probes/basic/basic_probe_tapetail.py)),
      eleven rows on both machines, 11/11
      ([`tapetail_after.out`](scratchpad/tapetail_after.out)); the two disk exec
      rows witness the FILE (F/N), not only the error
      ([`tapetail_witness.out`](scratchpad/tapetail_witness.out)). Knives
      ([`tapetail_knives.py`](scratchpad/tapetail_knives.py),
      [`tapetail_knives.out`](scratchpad/tapetail_knives.out)): K-TT1 (the tape
      arm back on the disk parser) moves exactly bsavesx/bsavesbig/dbsavesbig,
      K-TT2 (the exec's type check cut) dbsavebig/dbsavestr/bsavesbig/dbsavesbig
      -- 🎯 predicted only the first two, MISSED
      ([`tapetail_knives_miss.out`](scratchpad/tapetail_knives_miss.out)): on
      tape the save completes and the pending 6 surfaces at the NEXT line
      (`6 in 40`), so ERL witnesses it there -- K-TT3 csavespd, K-TT4 savejunk.
      ⚠️ Measured but NOT in `tools/kwerrset.py`'s sets: CSAVE's 5 / 2 (its
      `save-to-tape` set is {13, 24}) and BSAVE's exec 6 (`with-entry` is {2,
      13}) -- the denominator comes from the enumerated batches; widening it is
      a separate decision.
