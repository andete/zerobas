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
- ex_data + ex_restore        DATA pointer lifecycle (program.asm). READ has
  rows; RESTORE <line> edge cases (undefined line, after merge) unknown.
- ex_deftype (usr.asm)        DEFINT/SNG/DBL/STR letter-range parse.
- ex_time_assign + TIME       time.asm; interval-trap acceptance touches TIME
  only as a counter.
- ex_call_us (format.asm)     CALL statement surface.
- ex_key_stmt (program.asm)   KEY n,"s" is NOT-THIS-ONE (blocked ~160 B), but
  KEY LIST / KEY ON/OFF mechanism unreviewed.
- ex_motor (missing.asm)      MOTOR ON/OFF -> cassette relay; tape arc never
  reviewed the VERB (bios_probe_stmotr covers the BIOS call).
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
