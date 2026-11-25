- [ ] **D-KWSPEC — ELEPHANT / GOLDFISH SPEC PAGES FOR THE BASIC KEYWORDS**
      🎚️ TIER 1 — Joost 2026-11-23, third of "3, 2, 1".
      🤖 **AUTONOMOUS** — docs/keywords/*.md exist as user pages; make them specs with executable rules, region by
      region (as the BIOS), the VG-8020 the reference. BASIC graduates to C-BIOS eventually: these pages are what a
      port is checked against.
      **First unit (2026-11-23, scaffold + pilot):** the plan is docs/keywords/spec-plan.md (14 regions, strings
      first; harnesses; the spec page = the user page + the contract sections), the queue docs/keywords/spec-index.md
      (generated, tools/kw_spec_index.py). Pilot: LEFT$ / RIGHT$ / MID$ (function) at DRAFT 1 from
      probes/basic/spec/kslice.py (1,224 cases a machine, scratchpad/KSL_run1.out), rules modules
      probes/basic/spec/{left_s,right_s,mid_s}_rules.py -- every rule holds on the VG-8020, zerobas agrees in every
      case. NEXT: the review passes on the three pages (spec-method §6); a keyword probe in spec_live (plan §7.1);
      then the rest of the strings region. Joost to rule: "What we found" on a FINAL page, and the cassette
      statements (plan §2, §4).
      **Second unit (2026-11-24): LEN / ASC / CHR$ / SPACE$ / STRING$ / INSTR at DRAFT 1** from
      probes/basic/spec/kstr.py (2,044 cases a machine, scratchpad/KST_run1.out; plan §6, "The second unit"), on
      the shared RAM-record harness probes/basic/spec/ramrec.py (plan §7.2, now built; kslice byte-identical
      through it). Every rule holds on the VG-8020, every output is read; kstr_controls.py shows ten rival rules
      FALSE on the reference's cases. zerobas differs in 39 cases, filed: D-INSTREMPTY (INSTR with an empty
      string to find and a start past the end), D-CLOSESPACE (a space before `)` after INSTR's / STRING$'s
      string argument).
      **Third unit (2026-11-24): STR$ / VAL / HEX$ / OCT$ / BIN$ at DRAFT 1** from probes/basic/spec/knum.py (571
      cases a machine, scratchpad/KNM_run1.out; plan §6, "The third unit"): a typed argument's own bytes recorded
      before the call, string results byte for byte. Every rule holds on the VG-8020, every output is read;
      knum_controls.py shows 17 rival rules FALSE. STR$ / HEX$ / OCT$ / BIN$ agree in every case; VAL differs in
      19, filed: D-VALWS (TAB / LF inside a number, a gap after `&`), D-VALEXP (the exponent byte's wrap and a
      zero's digit bytes). The strings region's 14 keywords are all at DRAFT 1.
      **Maths, first unit (2026-11-24): ABS / SGN / INT / FIX / SQR at DRAFT 1** from probes/basic/spec/kmath.py (160
      cases a keyword on each machine, scratchpad/KMA_run1.out; plan §6, "The maths region's first unit"): the
      result's TYPE is seen through the probe's own USR routine (VALTYP + DAC), checked per argument by an apparatus
      row. Every rule holds on the VG-8020, every output is read; kmath_controls.py shows 18 rival rules FALSE. SGN
      agrees in every case; filed (all invisible to PRINT): D-ABSINTEDGE (ABS(-32768%) a double here, a single
      there), D-INTNEGTYPE (INT of a negative fraction: integer -1 / a double there, the argument's type here),
      D-ZEROLET (an exponent-0 single with digit bytes stored as zeros here), D-SQRZERO (SQR(0%) keeps leftover
      digit bytes here). SQR's known last-digit difference re-measured: the reference is within 3 units of the
      14th digit, not "one unit low" (page corrected).
      **Maths, second unit (2026-11-24): EXP / LOG / SIN / COS / TAN / ATN at DRAFT 1** from
      probes/basic/spec/ktrans.py (255 cases a keyword on each machine, scratchpad/KTR_run1.out; plan §6, "The maths
      region's second unit"), kmath's frame unchanged. The rules are BOUNDS against exact targets (ktrans_model.py,
      60+ digits), each the reference's measured worst rounded up; the trig reduction (p = x * 0.15915494309190 in
      14 digits; COS from r14(1/4 - p)) is now a rule fitting all 431 nonzero SIN / COS results. Every rule holds on
      the VG-8020, every output is read; ktrans_controls.py shows 27 rival rules FALSE. Filed: D-TRIGHALF (TIER 1,
      near a half / whole turn zerobas keeps more of the angle: SIN(3.1415926535898#) differs in its leading
      digits), D-SINDIGITS (zerobas's sine up to 6.1 units off, the reference's 1.9), D-TRANSZERO (TIER 6, the zero
      results' digit bytes). LOG / ATN pages corrected (LOG's reference error 8.3 units, not 5; ATN's worst 2.7 on
      both machines).
      **Maths, third unit (2026-11-24): RND at DRAFT 1** from probes/basic/spec/krnd.py, a SEQUENCE harness (556 steps
      a machine, scratchpad/KRN_run1.out; plan §6, "The maths region's third unit"): each record holds the step's
      result AND the generator's state after it (RNDX, $F857, the published cell). The generator is a rule on the
      bytes -- S' = (21132486540519 S + 14389820420821) mod 10^14, a reseed from the argument's 14 mantissa digits,
      S0 = 40649651372358 -- predicting every step one at a time AND every group from power-on / CLEAR alone
      (R-RND-CHAIN); krnd_controls.py shows 20 rivals FALSE. Every rule holds on the VG-8020, every output is read.
      zerobas agrees in every number and in RNDX except: D-RNDLINE (TIER 1, a typed program line resets the state
      there, not here), D-RNDZERO (TIER 6, state 0's result bytes), and RND("A" (D-ARGTYPEORDER, noted). The maths
      region's 12 keywords are all at DRAFT 1. NEXT: the review passes on the strings and maths pages (spec-method
      §6), RND's included; a keyword probe in spec_live (plan §7.1); then the conversion region (plan §2 row 3).
      **Flow, first unit (2026-11-25): FOR / NEXT at DRAFT 1** from probes/basic/spec/kfor.py (43 cases,
      scratchpad/KFR_run1.out; plan §6 "The flow region's first unit"); kfor_controls.py: 8 rivals FALSE. Filed:
      D-FORFRAME (TIER 3, a failed FOR keeps its frame -- a hang under RESUME NEXT), D-FORINTLIM, D-FORSTEP0,
      D-NEXTCREATE (TIER 6). NEXT: the flow region's next unit (GOTO / GOSUB / RETURN; FOR inside GOSUB), and D-FORFRAME.
      **Flow, second unit (2026-11-25): GOTO / GOSUB / RETURN at DRAFT 1** from probes/basic/spec/kgosub.py (30 cases,
      scratchpad/KGS_run1.out; plan §6 "The flow region's second unit"); kgosub_controls.py: 6 rivals FALSE. Filed:
      D-GOTOSPACE (TIER 1, `GO TO` with one space). NEXT: the flow region's last unit (IF, END, STOP, CONT, RUN), then
      D-GOTOSPACE.
      **Flow, third unit (2026-11-25): IF at DRAFT 1** from probes/basic/spec/kif.py (32 cases, scratchpad/KIF_run1.out;
      plan §6 "The flow region's third unit"); kif_controls.py: 5 rivals FALSE; zerobas agrees on every case. NEXT: END /
      STOP / CONT / RUN (a screen-based harness: they stop or restart the recording program).
      **Flow, last unit (2026-11-25): END / STOP / CONT / RUN at DRAFT 1** from probes/basic/spec/kstop.py, the first
      SCREEN-reading keyword probe (19 cases, scratchpad/KSP_run1.out; tools/spec_live.py's new `live_copy` hook re-runs
      it); kstop_controls.py: 7 rivals FALSE; zerobas agrees on all 19. THE FLOW REGION IS COMPLETE AT DRAFT 1. NEXT:
      the goldfish review passes over the flow pages, then region 6 (errors: ERR ERL ERROR RESUME TRON TROFF REM DEF*).
      **Goldfish pass 1 over the flow region (2026-11-25)**: scratchpad/REVIEW-m2-gkwfor.md, -gkwgosub.md, -gkwif.md,
      -gkwstop.md (about 150 findings; plan §6 "Goldfish pass 1 over the flow region"). ALL FOUR MODELS ARE PER-CASE
      TABLES -- the rework (interpreter models, one-law rivals, the separating cases, frames free of the keyword under
      test) is open, unit by unit. **Errors region, first unit (2026-11-25): DEFINT / DEFSNG / DEFDBL / DEFSTR at
      DRAFT 1** from probes/basic/spec/kdeftype.py (58 cases, scratchpad/KDT_run1.out), the first INTERPRETER model
      (kdeftype_model.py; kdeftype_controls.py: 11 one-law rivals FALSE). Behaviour agrees on all 58; filed
      D-VARLAYOUT (TIER 6, the variable entry's order). NEXT: rework the flow models (FOR / NEXT first), then
      ERROR / ERR / ERL / RESUME / ON ERROR.
      **FOR / NEXT reworked (2026-11-25)**: kfor_model.py an interpreter, 21 one-law controls, group FY (33 cases;
      plan §6). Filed D-NEXTFRAME, D-FORCOMMA (TIER 6); D-FORINTLIM widened, D-FORSTEP0 pinned. NEXT: the same
      rework for GOTO / GOSUB / RETURN, IF, END / STOP / CONT / RUN.
      **GOTO / GOSUB / RETURN reworked (2026-11-25)**: kgosub_model.py an interpreter, 13 one-law controls, group FY
      (21 cases, all predictions held; plan §6). Filed D-GOSUBFRAME (TIER 6). NEXT: IF, then END / STOP / CONT / RUN.
      **IF reworked (2026-11-25)**: kif_model.py an interpreter, 12 one-law controls, group FY (28 cases; 26
      predictions held, the 2 misses became stated laws), an IF-free error handler. zerobas agrees on all 60. NEXT:
      END / STOP / CONT / RUN, the last of the four.
      **END / STOP / CONT / RUN reworked (2026-11-25)**: kstop_model.py predicts the whole screen, 26 one-law controls,
      group FY (34 cases). Filed D-ENDCLOSE, D-DELNOLINE, D-RUNCONT (TIER 6). GOLDFISH PASS 1 OVER THE FLOW REGION IS
      ACTED ON IN FULL. NEXT: region 6's remaining units -- ERROR / ERR / ERL / RESUME / ON ERROR, then TRON / TROFF /
      REM.
      **Errors region, second unit (2026-11-25): ERROR / ERR / ERL / RESUME at DRAFT 1** from probes/basic/spec/kerr.py
      (40 screen cases, scratchpad/KER_run1.out); kstop_model.py's small BASIC is now the one interpreter for screen
      probes; kerr_controls.py: 13 one-law rivals. Filed D-RESUMEMISS (TIER 3, a hang) and D-ONERRVAR (TIER 6). NEXT:
      D-RESUMEMISS (tier 3 ranks first), then TRON / TROFF / REM.
      D-RESUMEMISS FIXED (2026-11-25, size-neutral). **Errors region, last unit (2026-11-25): TRON / TROFF / REM at
      DRAFT 1** from probes/basic/spec/ktron.py (25 screen cases, scratchpad/KTN_run1.out); 11 one-law controls;
      zerobas agrees on all 25. REGION 6 IS COMPLETE AT DRAFT 1. NEXT: region 7 (program: NEW LIST LLIST DELETE RENUM
      AUTO DATA READ RESTORE DIM ERASE CLEAR), and a goldfish pass over region 6.
      **Goldfish pass 1 over region 6 (2026-11-25)**: scratchpad/REVIEW-m2-gkwdeft.md, -gkwerr.md, -gkwtron.md (~140
      findings). WORKING RULE (proposed to Joost): every rule needs a one-law control FALSE on its own cases (plan §6).
      DEF types reworked (group FY, 33 cases; the ran byte; 18 controls, every rule pinned). NEXT: ERROR / RESUME,
      then TRON / TROFF / REM (a wrong PRINT law in the shared BASIC first), then region 7.
