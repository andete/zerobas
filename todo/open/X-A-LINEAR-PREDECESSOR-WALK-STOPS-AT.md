- [ ] ⚠️ **A linear predecessor walk stops at `ENDIF` and calls it an
      instruction.** Filed 2026-08-22 by D-DUPSPAN,
      [`docs/spec-basic-dupspan.md`](docs/spec-basic-dupspan.md) §2.1.
      D-DUPSPAN's fallthrough survey reported `gfx_syntax` as a fallthrough
      target because the line above it is `ENDIF`, which
      `check_tenant_closure._is_terminator` correctly says is not a terminator —
      **but a conditional-assembly directive is not an instruction, and a walk
      that stops at one has stopped in the wrong place.** Both arms of its
      `IF G6_RESIDENT` end in `jp exec_stmt`, so the real answer is "not a
      fallthrough target", and the +22 B measurement is what settled it.
      `_is_terminator` itself is fine; what needs the fix is any CALLER that
      walks backwards over source lines. 🔴 **This one over-reported and cost
      nothing. The same walk under-reports whenever the ENDIF's arms do NOT both
      terminate**, and that direction is silent.
      📏 **MEASURED 2026-08-28 (D-ENDIFWALK),**
      [`docs/spec-endifwalk.md`](docs/spec-endifwalk.md). **The class is 68 span
      pairs, and `ENDIF` is under half of it**: `endif` 32, **`if` 22**,
      **`include` 13**, `else` 1, over 1476 main + 1485 sub pairs. The other 36
      are the same defect unnamed — and `include` is the one that mattered.
      🔴 **IN `check_dead_code` IT FAILS THE OTHER WAY ROUND FROM THIS ITEM'S
      READING.** A phantom fallthrough edge makes the next label REACHABLE, so it
      HIDES dead code — a gate going quiet, and that same sweep is a HARD gate
      inside `make basic-reloc`. Corrected verdicts: **30 phantom edges, 18 agree,
      20 undecidable** (their opening `IF` is in a PREVIOUS span, so a per-span
      walk cannot see the arms; those keep their edge — a guessed True deletes a
      real edge, a guessed False only keeps a phantom one).
      ✅ **AND IT WAS HIDING AN 11 B DEAD ROUTINE, NOW REMOVED.**
      `skip_to_eol`/`ste_done` (`basic/interp.asm`) survived the G4 line-editor
      eviction as a SECOND COPY: `sub/lineedit.asm:738` defines its own and holds
      all EIGHT callers, while main's whole 50-file closure contained exactly one
      mention — `jr skip_to_eol` INSIDE THE ROUTINE'S OWN BODY. ⚠️ NOT the
      `IF SUB_BUILD` shape (fix 4, `disk_putword`, where deletion broke the build):
      that is ONE definition in a shared `.inc`; this was TWO definitions and the
      sub build does not include `basic/interp.asm` at all. Main page 1 was
      **94 B → 105 B free on 2026-08-28**; battery 43/43, `deadcode` clean.
      🎯 It hid because `tok_skip_to`'s span ends on
      `include "basic/tokskip-body.inc"`, whose real last instruction is the
      unconditional `jr tsk_data`.
      ✅ **BOTH REMAINING SPANS ADJUDICATED AND THE `include` HALF OF THE WALK
      FIXED (2026-08-28).** `fat_delete` was the SAME SHAPE AGAIN: `basic/fat.asm`
      is main-only, the body `.inc` and BOTH callers are sub-only, and main's copy
      was the thirteenth uniform resident shim with **no caller** — the twelve
      above it are called by name from `files.asm`, but KILL does not use the
      primitive layer at all (`ld a,DISKOP_SEL_KILL / call subrom_call`, its own
      comment saying the tenant calls `fat_delete` sub-locally). ⚠️ Checked, not
      assumed, that no resident-ABI list or dispatch table reaches it by ADDRESS.
      **+5 B.** `__MEAS_SUB_P1_END` is `ds`-padding read from the SYM file by
      `check_sub_walls.py` — true and useless as a finding; fix (9) skips a span
      whose only code line is a `ds`, PROVES it narrow (a `db` table stays
      reportable), and PRINTS what it skipped.
      📏 **TOTAL 16 B of main page 1 from code no gate could see: 94 B → 110 B free
      on 2026-08-28.** `--blind` still exits non-zero (the allowlist canary fires,
      so the sweep has not gone quiet); battery 43/43, 5 flakes recovered serially
      on a contended host.
      ➡️ **STILL OPEN: the `IF`/`ELSE`/`ENDIF` half — 55 of the 68 pairs.** Deciding
      one needs EVERY ARM to terminate, and **20 conditionals OPEN IN A PREVIOUS
      SPAN**, where a per-span walk cannot see the arms at all; that needs
      file-level structure. Those keep their edges, which is the safe direction (a
      guessed "terminates" invents a finding; a guessed "does not" only hides one),
      and the 20 are enumerable by name from the verdict scout.
      📏 **PRICED 2026-09-27 (loop), before anyone builds the file-level walk:**
      the verdict scout today reads **24 PHANTOM EDGES REMOVED** (the decidable
      ELSE/IF/ENDIF spans) and **24 UNDECIDABLE**, and the impact scout — the
      dead-code gate re-run with the corrected walk — reports **0 NEW dead-code
      lines** (0 before, 0 after). So the decidable half hides no bytes today;
      the file-level walk is worth building only for the 24 undecidable spans,
      with an expected yield measured at zero for their decidable siblings.
      Scouts: [`scratchpad/endif_walk_sweep.py`](scratchpad/endif_walk_sweep.py),
      [`scratchpad/endif_walk_verdict.py`](scratchpad/endif_walk_verdict.py),
      [`scratchpad/endif_walk_impact.py`](scratchpad/endif_walk_impact.py).
      🎚️ APPARATUS — predecessor walk
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended
      (include half SHIPPED 2026-08-28 with 16 B recovered; what remains is the
      IF/ELSE/ENDIF half, which needs a file-level walk, not a per-span one).
