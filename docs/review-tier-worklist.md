# Statement-review tier: draft worklist (analysed 2026-08-31 while the D-CLAMPPITCH battery ran)

Denominator: 133 ex_/ev_f_ handlers; 48 have a same-named spec, 85 do not.
The 85 are NOT 85 holes -- most are covered under ARC names. Grouping, with
the crude signal refined by which arc/gate actually exercises the file:

## Likely THIN (no arc obviously owns the mechanism) — review these first
- ✅ ex_out, ex_poke, ex_vpoke — **REVIEWED 2026-08-31, NO FINDING.** All three
  bodies + the read twins (PEEK/VPEEK/INP, `ev_f_ff`) read in full. The
  suspicion the ranking was built on — a 0..255 value domain the low-byte write
  ignores — is REFUTED by D-F2-2's own VG-8020 table
  ([`spec-basic-df2-2-intarg-coercion.md`](spec-basic-df2-2-intarg-coercion.md)
  §1.1): `OUT p,v` is Group-A ADDRESS domain on the reference (`arg=40000` =
  silent truncate, only >int16 is ERR 6), POKE/VPOKE use the same measured
  domains, VPOKE/VPEEK carry the VRAM 0..16383 leaf, and the missing-paren
  surface (`PRINT PEEK`) was pinned by the I1 differential. `intarg-acceptance`
  gates it per battery. 🎯 The tier's first no-finding: recorded WITH the
  refuting table so nobody re-walks this on the same suspicion.
- ✅ ex_data + ex_restore — **REVIEWED 2026-08-31, THREE REAL DEFECTS**
  (D-DATACOLON, [`spec-basic-datacolon.md`](spec-basic-datacolon.md)): the DATA
  body scan had no quote state at BOTH sites (crunch + runtime skip), bare
  RESTORE's `ret` ended the whole line (`RESTORE:C=9` skipped `C=9`), and junk
  after RESTORE was silence where the references raise ERR 8. 6 DIFF -> 0 on
  7 rows x 3 machines. The reverse of the trio's no-finding.
- ✅ ex_deftype — **REVIEWED 2026-08-31, ONE DEFECT, hidden by a
  wrong-reason SAME** (D-DEFCORNER,
  [`spec-basic-defcorner.md`](spec-basic-defcorner.md)): the item-end check
  accepted any non-comma byte, so `DEFINT AC=7` executed `C=7` as a statement
  (refs: ERR 2). `DEFINT AB` agreed on ERR 2 by coincidence — the separating
  row made the tail harmless and observable. 9 rows x 3 machines, 0 DIFF after.
- ✅ ex_time_assign + TIME — **FALSE THIN ENTRY** (found by reading,
  2026-08-31): `spec-basic-time.md` exists with a 45/45 characterization; the
  stem-match missed it because the handler is `ex_time_assign`. The body is
  exemplary — torn-store DI guard, site-local ERR 24, adjudicated domain.
- ex_call_us (format.asm)     CALL statement surface.
- ex_key_stmt (program.asm)   KEY n,"s" is NOT-THIS-ONE (blocked ~160 B), but
  KEY LIST / KEY ON/OFF mechanism unreviewed.
- ✅ ex_motor — **REVIEWED 2026-08-31, NO FINDING**: measured to its corners
  already (spec §3.5 — `MOTOR STOP` is ERR 2 with a do-not-harmonise warning,
  bare-MOTOR toggles only at a statement boundary).
- ex_locate (missing.asm)     D-LOCATE fixed one arg-shape bug; full review
  pending.
- ex_auto, ex_renum           line-editor verbs, LARGE; lineedit rows exist
  but no mechanism review.

## Covered by an arc under another name (verify the arc actually reads the
## mechanism before skipping)
- graphics.asm handlers (pset/preset/line_gfx/put_sprite/point/vdp/base):
  graphics-acceptance + gateblind sweeps.
- program.asm flow (gosub/return/next/on_*): lineerr shards + trap
  acceptances + D-TRAPSVC/D-ONERRARM.
- field.asm (get/lset/rset): FIELD arc + D-FLDCLOSE; files.asm
  (close/files/kill/merge): disk acceptance + D-OPEN2 rows.
- interp.asm core (let/if/goto/rem/data-sep/end): lineerr + unit tests.
- print/lprint/llist: LPT arc (cbios-lptout-followup) + print specs.
- cload/csave/bload/bsave/save: the cassette + truncload + oomtail work.
- ex_print_using: spec-print-hash-using.

## Method (calibrated on PLAY, 3 commits from 1 verb)
1. Read EVERY layer of the verb first (resident stub, tenant, servicer,
   tables). 2. Code-review for mechanism smells: wholesale stores of shared
   state, 16-bit wrap, clamps nobody measured, "mirrors X" comments, guards
   whose only outcome is deferred. 3. Write differential rows for what the
   review flags -- accept/reject FIRST, then value/trace rows where a screen
   read is blind. 4. Fix against the rows; heavy gates for the touched arc.

⚠️ A RANKED CANDIDATE ROTS. Re-verify "thin" per verb at pick-up time -- this
file records the 2026-08-31 reading, not the truth.
