# Statement-review tier: draft worklist (analysed 2026-08-31 while the D-CLAMPPITCH battery ran)

Denominator: 133 ex_/ev_f_ handlers; 48 have a same-named spec, 85 do not.
The 85 are NOT 85 holes -- most are covered under ARC names. Grouping, with
the crude signal refined by which arc/gate actually exercises the file:

## Likely THIN (no arc obviously owns the mechanism) — review these first
- ex_out, ex_poke, ex_vpoke   raw I/O trio (interp.asm). intarg-acceptance
  covers the D-F2-2 byte-coercion SURFACE; nobody has reviewed the port/address
  MECHANISM (16-bit domains, the D-PLAYCORNER wrap class lives here).
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
