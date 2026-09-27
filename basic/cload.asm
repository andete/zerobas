; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; cload.asm — the CLOAD and LOAD"CAS:" statement handlers.
;
; This is the *interpreter half* of the cassette program-load verbs. Where
; BLOAD (bload.asm) reads a BSAVE *binary image* into raw RAM, CLOAD and
; LOAD"CAS:" read a *tokenised BASIC program* off cassette into the stored-
; program area — the same line-link area that NEW / RUN / LIST manage — and make
; it the current program, as if it had been typed.
;
; Both verbs share one cassette I/O path (do_tape_prog). They differ only in how
; they parse their argument:
;   CLOAD ["filename"]      — the device is implicitly cassette; the optional
;                             quoted name is the tape file to find (we accept and
;                             ignore it: TAPION loads the next file on the tape).
;   LOAD "CAS:filename"     — the OPEN-style form: the device "CAS:" is explicit,
;                             then the optional filename.
;
; Cassette file format (MSX2 Technical Handbook, cassette file format). Like a
; BSAVE binary, a tokenised BASIC file is TWO tape blocks: a header block (10x
; file-id $D3 + a 6-char filename) and a data block (the program-area image) —
; so, like BLOAD, there are TWO TAPION calls, one per block tone. The data block
; omits the binary's 6-byte address header; it is the program image: a chain of
; [link:2 LE][lineno:2 LE][tokens...][00] lines ending in a $0000 link word (the
; same line-link layout zerobas stores at TXTBASE — see program.asm). The device
; half blocks on tape silence once a block's data runs out (it does NOT signal a
; clean end-of-data), so the reader stops EXACTLY at the program's $0000 end-link
; and never reads a byte past it. The saved absolute links are recomputed by
; `relink` after the load, so the loaded program's bytes become byte-identical to
; one typed in.
;
; CLEAN-ROOM: the file-type id ($D3) and the cassette block layout are from the
; MSX2 Technical Handbook (cassette file format, an allowed source); the in-RAM
; line-link program format and TXTBASE are this project's own / oracle-confirmed
; (program.asm, sysvars.inc). TAPION/TAPIN/TAPIOF are the documented BIOS
; contract (sysvars.inc). The "accept and discard the filename, load the next
; tape file" behaviour is an own-design simplification (no tape file catalogue);
; see PROVENANCE.md. No disassembly.

; --- do_cload: CLOAD ["filename"] --------------------------------------------
; Entry: HL -> the bytes after the CLOAD token. An optional quoted filename may
; follow. Tier-3 (spec-cas-tier3-cload.md Item A): the name is now HONOURED — it
; is captured into CAS_WANT and cas_open_match finds the matching tape file
; (skipping earlier non-matching files), instead of blindly loading the next one.
; Bare CLOAD (no name) clears CAS_WANT_ON -> load-next, unchanged.
do_cload:
                xor     a
                ld      (CAS_VERIFY),a      ; default: a real load (not CLOAD?)
                call    skip_spaces
                ; Tier-3 Item B: `CLOAD?` is the VERIFY form. Our tokeniser maps
                ; '?' to PRINT (interp.asm), so `CLOAD?` tokenises to CLOAD_TOKEN
                ; + PRINT_TOKEN — detect that leading PRINT_TOKEN here.
                cp      PRINT_TOKEN         ; CLOAD? -> compare-mode verify
                jr      nz,dcl_name
                inc     hl                  ; past the '?' (PRINT_TOKEN)
                ld      a,1
                ld      (CAS_VERIFY),a      ; compare, do not store
                xor     a
                ld      (CAS_VMIS),a        ; fresh verify (no mismatch yet)
                call    skip_spaces
dcl_name:
                ; A = (hl); HL at the first argument char (name or terminator).
                or      a
                jr      z,dcl_noname        ; bare CLOAD / CLOAD? -> next tape file
                cp      COLON               ; CLOAD : ... -> bare form
                jr      z,dcl_noname
                ; 🟢 D-CSAVEEXPR (2026-09-05): a string EXPRESSION, the same edit
                ; as do_csave's. `CLOAD 5` is `Type mismatch` on BOTH references
                ; and was a non-raising `load error` here.
                ; ⚠️ AND IT IS THE ONLY CLOAD ROW THAT EXISTS. `CLOAD A$` and
                ; `CLOAD"P"` REACH THE TAPE, and a tape search that finds nothing
                ; is the `LOAD"CAS:"` class -- TODO.md records the reference as
                ; NOT RETURNING, "no row can carry this". So the argument is
                ; evaluated on the strength of the PARSE face, which is what the
                ; gate below actually decided, plus the eight verbs already on
                ; fname_expr. That distinction is stated here rather than left
                ; for a reader to assume the whole verb was measured.
                call    fname_expr          ; HL -> the staged '"'-terminated copy
                call    cas_capture_name    ; -> CAS_WANT + CAS_WANT_ON=1
                jp      do_tape_prog        ; (CLOAD has no ,R; trailing chars ignored)
dcl_noname:
                xor     a
                ld      (CAS_WANT_ON),a     ; no name -> load the next tape file
                jp      do_tape_prog

; --- do_load: LOAD <name> | LOAD "CAS:filename" | LOAD "A:filename"[,R] ------
; Entry: HL -> the bytes after the LOAD token. ⚠️ D-FNEXPR2: the argument is a
; string EXPRESSION, not "a quoted device string" as this line read until
; 2026-08-21 -- `LOAD A$` and `LOAD A$+".BAS"` are `File not found` on the
; CF-3300 and were a PRINTED `load error` here (row f.loadvar). It is evaluated
; by `fname_expr` and staged in STRSCR, so everything below reads a staged copy:
; a "CAS:" prefix selects the (unchanged) cassette path; anything else is
; a disk filename (optional "A:"/"B:" drive prefix) read from the disk BDOS layer.
; A "CAS:" filename is parsed-past and ignored (TAPION opens the next tape file);
; a disk LOAD "name",R loads the tokenised BASIC program and runs it.
;
; The "CAS:" prefix is peeked NON-DESTRUCTIVELY (exactly like do_bload): only once
; the full prefix matches do we commit to the tape path, so a name like "CASETTE"
; falls through cleanly to the disk path. That peek is `dev_cmp` now, not the
; hand-rolled loop this file carried -- the THIRD copy of it in the tree, and
; D-FNFUND had collapsed only the two in save.asm because its sweep was on a
; FILE and not on the MECHANISM.
do_load:
                xor     a
                ld      (CAS_VERIFY),a      ; LOAD is a real load, never CLOAD? verify
                ; ✅ D-FNEXPR2: the filename is a string EXPRESSION (row f.loadvar:
                ; `LOAD A$` on a missing file is `File not found` on the CF-3300
                ; and was `load error` here -- PRINTED, so the program ran on).
                call    fname_dev   ; D-NGRAM16
                ; --- device dispatch: "CAS:" -> tape, else -> disk ----------
                ; 🎯 D-FNEXPR2 CARVE: THIS WAS A **THIRD** HAND-ROLLED COPY OF
                ; `dev_cmp`, and D-FNFUND collapsed only the two in save.asm --
                ; its sweep was on `basic/save.asm`, not on the mechanism, which
                ; is the class this project keeps re-learning (grep the SYMBOL,
                ; then grep the MECHANISM). Same upcase, same 0-terminated
                ; prefix, same advance-on-hit / restore-HL-on-miss contract, and
                ; the `push`/`pop` pair goes with it because dev_cmp owns one.
                jr      nz,dl_is_disk       ; no "CAS:" prefix -> disk (HL restored)
dl_is_cas:
                ; HL is now inside the STAGED copy, past "CAS:". Tier-3: CAPTURE
                ; the filename into CAS_WANT (cas_open_match then finds the named
                ; tape file, case-sensitive per spec §A.5). It stops ON the '"'
                ; fname_expr appended to the staging buffer; the `,R` tail is
                ; parsed from FN_RESUME instead, in the PROGRAM TEXT where it
                ; actually lives (D-FNEXPR2). Empty name (LOAD"CAS:") ->
                ; CAS_WANT_ON=0 = load next.
                call    cas_capture_name    ; -> CAS_WANT + CAS_WANT_ON; HL on '"'
dl_cas_close:
                ld      hl,(FN_RESUME)      ; D-FNEXPR2: the closing '"' lives in
                call    pcr_noquote         ; the STAGED copy, so resume past the
                                            ; expression and take only the ,R tail
                jr      c,load_error
                call    do_tape_prog        ; load the tokenised program off tape
                ret     c                   ; D-CASTAIL defect B (docs/spec-basic-
                                            ; castail.md §3.2): the tape load FAILED and
                                            ; has already reported. LOAD"CAS:x",R must
                                            ; not then run whatever was resident -- both
                                            ; references print their message and stop
                                            ; (characterization §4, cas-loadr-brk-res)
                ld      a,(RUNFLAG)          ; ,R ? -> run it; else back to the REPL
                or      a
                jp      z,end_line_end      ; 🔴 D-MERGERET: `ret z` RESUMED THE
                                            ; STATEMENT STREAM, and after a LOAD the
                                            ; program that stream belongs to IS GONE.
                                            ; See the disk arm below for the measured
                                            ; face; this arm is the same code and is
                                            ; changed by the same reasoning, with NO
                                            ; row -- nothing in this tree can PLAY a
                                            ; tape (only record one), which D-KWTAPE
                                            ; measured. Named as unmeasured rather
                                            ; than left inconsistent with its twin.
                jr      run_prog_top        ; RUN the loaded program -- at TOP LEVEL,
                                            ; never nested (§3.1, and see run_prog_top)

; --- do_load disk path: LOAD "A:name"[,R] -----------------------------------
; D-FNEXPR2: this paragraph used to read "HL was advanced partway through the
; 'CAS:' compare and must NOT be trusted — restore the filename start from the
; stack." That was true of the hand-rolled compare loop this file carried; it is
; not true of `dev_cmp`, which restores HL itself on a miss, and the `push`/`pop`
; pair the sentence described no longer exists. Parse the FCB (shared with
; do_bload) out of the staged copy, take the `,R` tail from FN_RESUME, load the
; tokenised program from disk, then run it iff ,R was given (LOAD"name",R = load
; and run; standard MSX behaviour).
dl_is_disk:
                call    pdfcb_resume      ; build DISK_FCB; HL -> closing '"'
                call    pcr_noquote         ; ,R tail only -- no quote in the text
                jr      c,load_error
                call    disk_prog_load      ; load the tokenised program into TXTBASE
                ret     c                   ; D-RUNTAIL defect B (docs/spec-basic-
                                            ; runtail.md §3.2): the load FAILED and has
                                            ; already reported. LOAD"missing",R must not
                                            ; then run whatever was resident -- the
                                            ; CF-3300 prints its message and stops
                                            ; (characterization §4, loadr-miss-res)
                ; ,R ? -> run the freshly loaded program; else back to the REPL.
                ; 🔴 D-MERGERET (2026-09-12): "BACK TO THE REPL" IS WHAT THE COMMENT
                ; SAID AND NOT WHAT `ret z` DID. A `ret` hands control back to the
                ; exec loop, which carries on with the next statement -- of a program
                ; this very statement has just REPLACED. Inside a running program
                ; `10 POKE&HD002,0 / 20 LOAD"PROG.BAS" / 30 POKE&HD002,55` answered
                ; `Syntax error in 49924` -- a line number read out of whatever now
                ; sits under the stale cursor -- where the CF-3300 answers a clean
                ; `Ok` (scratchpad/kwdrain_cmdlevel.out). `end_line_end` is the tail
                ; END, NEW, LIST, DELETE, RENUM and AUTO already share.
                ; 🎯 DIRECT MODE ALREADY AGREED (0 on both) and still does: the same
                ; flag is what `NEW` sets, and a typed `NEW:POKE` measures 0 on both
                ; machines (scratchpad/kwdrain_cmddirect.out).
                ld      a,(RUNFLAG)
                or      a
                jp      z,end_line_end
                jr      run_prog_top        ; RUN the loaded program (program.asm) --
                                            ; at TOP LEVEL, never nested (§3.1)

; --- do_run: RUN | RUN <lineno> | RUN <name expression> ---------------------
; Entry: HL -> the bytes after the RUN token.
;
; RUN <name> is a thin wrapper: load a tokenised BASIC program from disk
; (exactly as LOAD <name> does — same parse_disk_fcb + disk_prog_load path) and
; then RUN it. The implicit run is the only difference from LOAD: there is
; no ,R option, running is the whole point.
;
; ✅ D-FNRUN (docs/spec-basic-fnrun.md): THE NAME IS A STRING EXPRESSION, and
; the reason this verb was left out of D-FNEXPR2 was MEASURED FALSE rather than
; argued away. Both that slice and D-FNEXPR §2 called this dispatch "genuinely
; ambiguous with RUN <lineno>" and priced the fix as a probable DECLINE. It is
; not ambiguous, and the rows that say so read the STORED LINE BYTES rather than
; the screen (t.runnum / t.runvar, byte-identical on vg8020, cf3300 AND zb):
;
;       1 RUN 30   ->  8a 20 0e 1e 00 00      RUN_TOKEN ' ' $0E + word 30
;       1 RUN A$   ->  8a 20 41 24 00         RUN_TOKEN ' ' "A$"
;
; basic/tokenise.inc arms line-number mode on RUN_TOKEN and emits LINENO_TOKEN
; ($0E) for that form and NOTHING ELSE, so the two forms differ in their first
; byte and a test for $0E separates them exactly. The tokeniser had already done
; the work the decline was priced against
; [[a-filed-blocker-can-name-the-wrong-obstacle]].
;
; 🔴 AND WHAT THE OLD DISPATCH DID WITH `RUN A$` WAS NOT A REFUSAL. A non-quote
; fell to `jp run_prog`, so the argument was not rejected, it was EATEN and the
; statement RESTARTED THE PROGRAM -- forever, for a stored `RUN A$`. The
; CF-3300 answers `File not found in 30` (row n.runvar).
;
; Four cases, dispatched on the first non-space byte after RUN:
;   end / ':'      -> a bare tokenised RUN
;   LINENO_TOKEN   -> RUN <lineno> (the tokeniser stored the number as $0E + a
;                     16-bit value). ⚠️ THIS ARM IS UNCHANGED AND STILL WRONG:
;                     both references RESTART AT THAT LINE and we still ignore
;                     the number and restart from the top. Row `n.runline`
;                     holds that divergence open, with `n.runlinectl` as its
;                     green control, so this slice cannot be read as having
;                     fixed a form it merely learned to RECOGNISE.
;   anything else  -> a string EXPRESSION naming a program: evaluate it
;                     (fname_expr), dispatch "CAS:" vs disk, load, and run.
;
; Mirrors do_load's disk path exactly (fname_expr + parse_disk_fcb +
; disk_prog_load), so RUN <name> parses identically to LOAD <name> minus the
; RUNFLAG test. The load logic is NOT duplicated.
do_run:
                xor     a
                ld      (CAS_VERIFY),a      ; RUN"CAS:" is a real load, never verify
                call    skipsp_test ; A = the first non-space byte
                jr      z,dr_stored         ; end of statement -> bare RUN
                cp      COLON
                jr      z,dr_stored         ; `RUN : ...`      -> bare RUN
                cp      LINENO_TOKEN        ; $0E -> RUN <lineno>
                jr      z,dr_lineno         ; D-RUNLINE: start AT that line
                call    fname_dev   ; D-NGRAM16
                                            ; '"'-terminated copy in STRSCR
                ; device dispatch: "CAS:" -> tape, else -> disk (mirrors do_load).
                ; dev_cmp advances HL past a matched prefix and restores it on a miss,
                ; so the disk path below still sees HL at the filename start.
                jr      z,dr_is_cas         ; matched "CAS:" -> tape program run
                call    pdfcb_resume      ; build DISK_FCB; HL -> closing '"'
                call    pcr_noquote         ; the only '"' is fname_expr's own
                jp      c,load_error
                call    disk_prog_load      ; load the tokenised program into TXTBASE
                ret     c                   ; D-RUNTAIL defect B: the load FAILED and has
                                            ; already reported -- RUN"missing" must run
                                            ; NOTHING, not the resident program
                jr      run_prog_top        ; ...and run it (running is implicit), at
                                            ; TOP LEVEL -- see run_prog_top below
dr_stored:
                jr      run_prog_top        ; bare RUN: the stored program from the top,
                                            ; at TOP LEVEL like every sibling arm.
                ; \U0001f7e2 D-BARERUN (2026-09-09): CONVERTED AT LAST, 0 B, AND THE ROW
                ; IS WHAT UNBLOCKED IT. This arm stood ⛔ BLOCKED since 2026-08-22
                ; on *"needs a fixture"*: a bare RUN CLEARS VARIABLES, so the
                ; program restarts forever on the references too and there is no
                ; value to read back. The fixture that works makes the CORRECT
                ; behaviour visible instead of the wrong one -- an endless
                ; `PRINT"X";` before the RUN, so "restarts forever, silently"
                ; reads as a screen full of X and the defect reads as an error
                ; message among them:
                ;     s.bare   vg 835 X no error | cf 869 X no error | zb 210 X + error
                ;     c.goto   vg 825 X         | cf 897 X          | zb 911 X
                ; `c.goto` is the same endless loop reached by GOTO instead of RUN
                ; -- the control that separates "hangs correctly" from "the
                ; harness captured nothing", which is the trap this row had to
                ; avoid [[an-unnamed-outcome-reads-as-no-outcome]].
                ; The old note, which was right about everything except that the
                ; fixture could not be built:
                                            ; ⚠️ STILL THE ONE ARM D-RUNTAIL DID NOT
                                            ; CONVERT, and D-RUNLINE deliberately left
                                            ; it that way. `jp run_prog_top` is the
                                            ; 0-byte fix and it is NOT shipped, because
                                            ; the form it changes -- a bare RUN inside a
                                            ; RUNNING program -- cannot be rowed the
                                            ; obvious way: RUN clears variables, so a
                                            ; program that reaches a bare RUN restarts
                                            ; FOREVER on the references too. The row has
                                            ; to separate "hangs silently" (correct) from
                                            ; "prints a bogus error then stops" (the
                                            ; defect) on a TIMEOUT, which needs a control
                                            ; of its own. That is the real reason D-FNRUN
                                            ; said "a form no row drives" -- see
                                            ; docs/spec-basic-runline.md §4.

; --- dr_lineno: RUN <lineno> -- restart, then begin AT the named line --------
; D-RUNLINE (docs/spec-basic-runline.md). HL -> the $0E LINENO_TOKEN.
;
; 🎯 NO LINE-FINDER AND NO RUN LOOP IS WRITTEN. `RUN <lineno>` is a bare RUN
; whose CURLINE starts somewhere else, and both halves already exist:
; goto_resolve (interp.asm) is GOTO's own tail -- find_line_bc + the undefined-
; line check (ERR 8) + the GOTOTGT store -- and run_prog_at (program.asm) is
; run_prog entered with GOTOTGT already naming the start line. The operand
; grammar is GOTO's too: $0E + the line number LE.
;
; ⚠️ `ld sp,(SAVSTK)` is run_prog_top's half, inlined rather than jumped to
; because the variant needed is run_prog_AT: RUN discards any GOSUB/FOR context
; between here and the prompt, which is what RUN means (see run_prog_top).
; It sits AFTER goto_resolve deliberately -- an undefined line must raise ERR 8
; from the ORIGINAL depth, so the trap sees the real stack.
dr_lineno:
                inc     hl                  ; past $0E
                ld      c,(hl)              ; target line number, LE (GOTO's grammar)
                inc     hl
                ld      b,(hl)
                call    goto_resolve        ; find_line_bc + ERR 8 + GOTOTGT := the line
                ld      sp,(SAVSTK)         ; ...then top level, as bare RUN does
                jp      run_prog_at
dr_is_cas:
                ; HL is inside the STAGED copy, past "CAS:". Tier-3: CAPTURE the
                ; filename into CAS_WANT (cas_open_match finds the named tape file,
                ; case-sensitive). It stops on fname_expr's appended '"'; the
                ; statement tail is taken from FN_RESUME, exactly like do_load's
                ; dl_is_cas.
                call    cas_capture_name    ; -> CAS_WANT + CAS_WANT_ON; HL on '"'
dr_cas_close:
                ld      hl,(FN_RESUME)      ; D-FNRUN: resume past the EXPRESSION
                call    pcr_noquote         ; (+ a harmless ,R: run is implicit)
                jp      c,load_error
                call    do_tape_prog        ; load the program off tape (tokenised OR
                                            ; $EA ASCII — do_tape_prog's 3-way dispatch)
                ret     c                   ; D-CASTAIL defect B: the load FAILED and has
                                            ; already reported -- RUN"CAS:x" must run
                                            ; NOTHING, not the resident program
                jr      run_prog_top        ; ...and run it, at TOP LEVEL -- see
                                            ; run_prog_top below. D-CASTAIL closes the
                                            ; D-RUNTAIL §9 residual: this site had the
                                            ; IDENTICAL defect A and was left alone only
                                            ; because nothing scored the tape paths.
                                            ; docs/spec-basic-castail.md, measured in
                                            ; docs/castail-msx1-characterization.md.

; --- run_prog_top: enter run_prog at TOP LEVEL, from a statement context ------
; D-RUNTAIL (docs/spec-basic-runtail.md §3.1), measured in
; docs/runtail-msx1-characterization.md.
;
; 🔴 `RUN"A:name"` IS NOT THE REPL'S `RUN` COMMAND. dispatch_line's is_cmd needs
; the byte after "RUN" to be end/space/':' and this one is '"', so the line is
; crunched and reaches do_run as a STATEMENT -- inside the enclosing line's own
; run loop. A plain `jp run_prog` there enters the loop NESTED and overwrites
; CURLINE; when the loaded program ends, run_prog's `ret` lands back in `exec`
; and the ENCLOSING loop resumes with CURLINE pointing at the loaded program's
; end marker. Its "fall through to the next line" then walks off that into
; CURLINE := $0000, finds a NON-zero link there ($C3F3 -- the page-0 ROM's own
; `DI / JP`), re-derives DIRECTF as RUN mode and dispatches the byte at $0004 as
; a BASIC statement. Measured symptom: `Illegal function call in 3346` after
; EVERY RUN"file"/LOAD"file",R -- hit and miss alike -- where 3346 is the word at
; $0002 printed as CURLINE+2 by print_in_lineno. The reference prints nothing.
;
; The REPL's own bare RUN never had this: dl_run's `jp run_prog` is reached at
; dispatch_line's depth, which is the depth whose `ret` returns TO THE PROMPT.
; SAVSTK is exactly that depth -- dispatch_line records it before any statement
; runs (basic/program.asm) -- so restoring it here reproduces the command path's
; shape from a statement context. A stored line's RUN"file" inherits the
; enclosing run_prog's anchor, which is the SAME value for the same reason.
;
; Discarding any GOSUB/FOR context between here and the prompt is not a side
; effect to be tolerated: it is what RUN means.
;
; ⚠️ autoexec_run (below) keeps a plain `jp run_prog` DELIBERATELY: it is called
; from `init`, before the REPL, where SAVSTK has never been written -- and it has
; no enclosing loop to corrupt, so it has no defect A to fix.
run_prog_top:
                ld      sp,(SAVSTK)         ; the prompt-clean depth
                jp      run_prog            ; ...its `ret` now returns to the REPL

; --- cas_capture_name: parse a quoted tape name into CAS_WANT -----------------
; Entry: HL -> the first char of the name (inside the quotes, past the opening
; '"' or the "CAS:" prefix). Copies up to 6 chars — CASE PRESERVED, the CF-3300
; compare is byte-exact (spec §A.5) — into CAS_WANT, space-padding to 6; sets
; CAS_WANT_ON = 1 iff at least one name char was present (else 0 = load next).
; Stops ON the closing '"' or a NUL terminator, leaving HL there for the caller's
; parse_close_run / trailing handling (chars beyond 6 are advanced-over, not
; stored, so HL still lands on the quote). Clobbers A, BC, DE, HL.
cas_capture_name:
                ld      de,CAS_WANT
                ld      bc,$0600            ; D-PEEPHOLE: b=6 slots left in
                                            ; CAS_WANT, c=0 chars copied so far
ccn_lp:
                ld      a,(hl)
                or      a
                jr      z,ccn_pad           ; NUL -> stop
                cp      '"'
                jr      z,ccn_pad           ; closing quote -> stop
                ld      a,b
                or      a
                jr      z,ccn_over          ; CAS_WANT full -> ignore extra name chars
                ld      a,(hl)
                ld      (de),a              ; store this name char (case preserved)
                inc     de
                dec     b
                inc     c
ccn_over:
                inc     hl
                jr      ccn_lp
ccn_pad:
                ld      a,b
                or      a
                jr      z,ccn_flag          ; no slots left -> nothing to pad
ccn_pad_lp:
                ld      a,' '               ; space-pad the remaining slots
                ld      (de),a
                inc     de
                djnz    ccn_pad_lp          ; D-PEEPHOLE: -1 B. djnz sets NO
                                            ; flags, and none are read after --
                                            ; ccn_flag opens `ld a,c / or a`,
                                            ; which redefines them. The `or a`
                                            ; guard above keeps B >= 1, so the
                                            ; B=0 wrap is unreachable either way.
ccn_flag:
                ld      a,c                 ; A = name-char count
                or      a
                jr      z,ccn_set           ; empty name -> store 0 (load next file)
                ld      a,1                 ; a name was given -> match it
ccn_set:
                ld      (CAS_WANT_ON),a
                ret

; --- cas_open_match: resident marshalling shim ------------------------------
; docs/spec-eviction-g5-space.md. The full name-match loop + cas_skip_data
; (com_next/com_hdr/com_cmp/csd_tok/csd_ascii/... -- basic/casmatch-body.inc)
; moved whole to sub/casmatch.asm (SUBROM_IDX_CASMATCH) to free page-1 tail
; space for the G5 PAINT slice. No register inputs to marshal -- the body
; already reads/writes only RAM (CAS_WANT*/CAS_HDRNAME/CAS_HDRID) and BIOS
; (TAPION/TAPIN), both visible from a page-1 tenant. This stub just
; subrom_calls the tenant and converts its CM_STATUS byte back to the
; existing CF-return convention (out: CF clear = matched, CAS_HDRID set / CF
; set = not found or tape error) -- all 3 call sites (do_tape_prog below,
; files.asm merge_cas/oo_dev_cas) are unchanged, they already just test CF.
cas_open_match:
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_CASMATCH
                call    sc_call             ; D-SCCALL: tenant call + absent raise
                ld      a,(CM_STATUS)
                or      a
                ret     z                   ; matched -> CF clear
                scf
                ret

; --- do_tape_prog: the shared cassette BASIC-program load path ----------------
; Finds the requested tape file (cas_open_match: name-matching per Tier-3, or the
; next file for the bare form), then dispatches on its file-type id: $D3 reads a
; tokenised program-area image line-by-line into TXTBASE and relinks it; $EA is an
; ASCII (SAVE"CAS:",A) program handed to cas_ascii_load. TAPIN trashes every
; register, so all state lives in RAM. CLOAD, LOAD"CAS:" and RUN"CAS:" all reach
; here, so all three accept either format and honour the filename transparently.
;
; --- D-CASTAIL: THE CF-OUT CONTRACT (docs/spec-basic-castail.md §3.2) ---------
;   out: CF set = the load FAILED and has ALREADY reported.
; Consumed by `ret c` at dl_cas_close (LOAD"CAS:x",R) and dr_is_cas (RUN"CAS:x"),
; which must then run NOTHING: both references print their message and stop,
; where zerobas ran whatever program was resident (castail characterization §4).
; do_cload reaches here by `jp` and has no ,R, so it consumes no carry.
;
; 🔴 load_error IS NOT TOUCHED, for the reason spec-basic-runtail.md §3.2 gives:
; ~50 jp/call sites across seven files, several of which resume into their caller
; on purpose. The contract is stated on THIS routine's exits, and its producer is
; dpl_err (below) -- `call load_error` + `scf` + `ret`, already written for the
; disk half, so every failure exit here repoints at ZERO delta.
;
; ⚠️ COVERAGE, EXACTLY: only the cas_open_match exit is scored by a row (the
; Ctrl-STOP abort -- the ONLY tape failure a reference reports and returns from;
; a missing tape file just searches past the end of the tape and waits forever,
; characterization §6). The rest carry the contract for COMPLETENESS, and the
; tokenised ($D3) exits are unreachable from every row in the battery.
do_tape_prog:
                call    cas_open_match      ; find the (named) file; header consumed
                jp      c,dpl_err           ; not found / tape error / Ctrl-STOP abort
                ld      a,(CAS_HDRID)
                cp      BASIC_ID            ; tokenised BASIC -> the store/compare loop
                jr      z,ctp_data_tokenised
                cp      ASCII_ID            ; ASCII program -> cas_ascii_load
                jp      nz,dpl_err          ; neither id -> unrecognised file
                ; $EA ASCII: CLOAD? verify is tokenised-only (spec §B) -> reject
                ld      a,(CAS_VERIFY)
                or      a
                jp      nz,dpl_err
                jp      cas_ascii_load
ctp_data_tokenised:
                ; --- data block: skip its leader tone -----------------------
                ; Like BLOAD, the program data is a SEPARATE tape block, so it
                ; needs its own TAPION to re-lock onto the data block's leader.
                call    TAPION
                jp      c,dpl_err           ; D-CASTAIL CF contract

                ; --- start a fresh program: store cursor at the text base ---
                ld      hl,TXTBASE
                ld      (CLPTR),hl
                ld      (CLINK),hl          ; A_0 = the saving machine's text base.
                                            ; The saved link words are consecutive
                                            ; absolute addresses; the first line's
                                            ; predecessor address is the saving
                                            ; machine's text base, assumed == ours
                                            ; (TXTBASE $8001, the MSX disk-BASIC base)

                ; --- read the program image, stopping at the $0000 end-link --
                ; The device half does NOT signal a clean end of data: once the
                ; tape block's bytes run out, TAPIN blocks on silence rather than
                ; returning CF. So we must stop reading EXACTLY when the program
                ; ends — at the $0000 link word that terminates the line-link
                ; chain — never reading a byte past it.
                ;
                ; LENGTH-DRIVEN copy. A token body legitimately contains $00 bytes
                ; (e.g. INT2 `$1C lo hi`, &H `$0C lo hi`, line-number refs), so the
                ; first $00 is NOT the line boundary. The boundary is defined by the
                ; saved link words: each link is the saving machine's absolute
                ; address of the NEXT line, so this line's full length is
                ; (this link) - (previous link) and its body length is that minus the
                ; 4-byte link+lineno header. We copy EXACTLY that many body bytes —
                ; embedded $00s included — landing precisely on the next link word.
                ;
                ; Per line: read the 2-byte link word; $0000 -> end of program.
                ; Otherwise store link word + 2-byte line number verbatim, then copy
                ; the computed body byte count. The saved links are stored as-is;
                ; relink (token-aware) recomputes them below.
ctp_line:
                call    TAPIN               ; link low
                jp      c,dpl_err           ; D-CASTAIL CF contract
                push    af                  ; preserve link-low: TAPIN clobbers C
                call    TAPIN               ; link high
                jr      c,ctp_link_err      ; must pop before leaving
                ld      b,a                 ; B = link high
                pop     af
                ld      c,a                 ; C = link low (restored)
                                            ; BC = saved link word L_n = A_{n+1}
                ld      a,b
                or      c
                jr      z,ctp_done          ; $0000 link -> program complete

                ; body length = L_n - A_n - 4   (A_n = CLINK = previous link word)
                ld      hl,(CLINK)          ; HL = A_n
                ld      (CLINK),bc          ; advance CLINK = L_n for the next line
                ld      a,c
                sub     l
                ld      e,a
                ld      a,b
                sbc     a,h
                ld      d,a                 ; DE = L_n - A_n = full line length
                dec     de
                dec     de
                dec     de
                dec     de                  ; DE = body length (incl. its $00 term)

                ; bounds: this line's header (>=4 bytes) must fit below TXTMAX
                push    de                  ; guard body length across TAPIN/stores
                ld      hl,(CLPTR)
                ld      de,TXTMAX-4
                or      a
                sbc     hl,de
                jr      nc,ctp_oom_pop

                ; store (load) OR compare (CLOAD? verify) the saved link word via
                ; cas_put — one mode-flagged emit point (relink fixes links later).
                ld      a,c
                call    cas_put
                ld      a,b
                call    cas_put

                ; line number (2 bytes)
                call    TAPIN
                jr      c,ctp_err_pop
                call    cas_put
                call    TAPIN
                jr      c,ctp_err_pop
                call    cas_put
                pop     de                  ; DE = body length

                ; token body: copy EXACTLY DE bytes (embedded $00s and all)
ctp_body:
                ld      a,d
                or      e
                jr      z,ctp_line          ; whole body copied -> next line
                push    de                  ; guard remaining count across TAPIN
                ld      hl,(CLPTR)          ; bounds check
                ld      de,TXTMAX
                or      a
                sbc     hl,de
                jr      nc,ctp_oom_pop
                call    TAPIN
                jr      c,ctp_err_pop
                call    cas_put             ; store or compare the body byte
                pop     de                  ; DE = remaining count
                dec     de
                jr      ctp_body

; ctp_link_err — the second TAPIN (link high) failed with CF; AF (link-low) is on
; the stack from the push before that call.  Pop it to restore balance, then error.
ctp_link_err:
                pop     af
                jp      dpl_err             ; D-CASTAIL CF contract

; ctp_err_pop / ctp_oom_pop — body length / remaining count is on the stack; drop
; it before taking the shared error / out-of-memory path so the stack stays balanced.
ctp_err_pop:
                pop     de
                jp      dpl_err             ; D-CASTAIL CF contract
ctp_oom_pop:
                pop     de
                jr      ctp_oom

ctp_done:
                call    TAPIOF              ; motor off (program fully read)
                ld      a,(CAS_VERIFY)
                or      a
                jr      nz,ctp_verify_done  ; CLOAD? -> report, do NOT mutate memory

; --- load_commit_prog: COMMIT A FRESHLY LOADED PROGRAM -----------------------
; D-NGRAM12: the SHARED completion tail of BOTH program loaders. do_tape_prog
; (CLOAD) falls through into it; disk_prog_load (LOAD "file") reaches it as
; `dpl_done`, which is an ALIAS of this label and not a second copy -- its whole
; body was these ten instructions, byte for byte.
; Entered with CLPTR = the store cursor just past the last line.
; Leaves CF CLEAR = loaded, run it (D-CASTAIL / D-RUNTAIL: the SUCCESS half of
; the CF contract both callers publish; `relink`'s own carry is not a result and
; may not be passed off as one, which is what the `or a` is for).
load_commit_prog:
                ; --- write the $0000 end-of-program marker and set PRGEND ---
                ld      hl,(CLPTR)
                ld      (PRGEND),hl         ; end marker sits at the store cursor
                ld      (hl),0
                inc     hl
                ld      (hl),0
                ; keep the TXTTAB sysvar consistent with the program base
                ld      hl,TXTBASE
                ld      (TXTTAB),hl

                ; --- relink: recompute every line's absolute link pointer ---
                ; The saved links were absolute addresses on the saving machine;
                ; relink (program.asm) recomputes them from the loaded bytes, so
                ; the program is now byte-identical to one typed in.
                call    relink
                or      a                   ; D-CASTAIL: the SUCCESS half of the CF
                ret                         ; contract -- CF clear = loaded, run it

; --- ctp_verify_done: CLOAD? end-of-tape -> report Ok / Verify error ----------
; Verify is NON-DESTRUCTIVE: no marker, no PRGEND, no relink — CAS_VMIS holds the
; verdict. A clean CAS_VMIS = identical (silent Ok); otherwise "Verify error".
; Any real difference (including nearly all length changes — the saved link words
; are absolute addresses, so a different program layout differs byte-for-byte and
; trips CAS_VMIS during the body compare) is caught. The one gap is a tape that is
; an EXACT PREFIX of a longer in-memory program (all compared bytes equal, tape
; ends early); that is outside the verify use case (confirming a same-length
; CSAVE round-trip) and is a documented limitation (spec §B).
ctp_verify_done:
                ld      a,(CAS_VMIS)
                or      a
                ret     z                   ; no difference -> Ok (memory intact)
                jr      verify_error        ; a byte differed -> "Verify error"

ctp_oom:
                call    TAPIOF              ; stop the motor before reporting
                ld      a,(CAS_VERIFY)
                or      a
                jr      nz,verify_error     ; CLOAD? overrun = mismatch, do NOT wipe
                ; D-OOMTAIL: the seven instructions that used to sit here were
                ; byte-for-byte dpl_oom's whole body (the comments even said
                ; "mirrors dpl_oom") -- so jump to the mirror instead of
                ; carrying it. 13 B. The D-CASTAIL contract is unchanged: CF=1,
                ; empty program, "Out of memory" -- dpl_oom IS that contract,
                ; and this couples the two halves ON PURPOSE: they are filed as
                ; mirrors, so a future edit to one is an edit to both.
                jp      dpl_oom
err_prog_mem    equ     err_mem             ; repack: share sl_oom's "out of memory"
                                            ; (program.asm) — identical bytes. Part of
                                            ; D-2's self-funding string dedup (S1).

; --- cas_put: store-or-compare one program byte at CLPTR, advance CLPTR --------
; The single mode-flagged emit point of the tokenised tape reader (spec §B).
; CAS_VERIFY=0 (a real CLOAD/LOAD"CAS:"/RUN"CAS:") -> store A at CLPTR (plain
; load). CAS_VERIFY=1 (CLOAD?) -> COMPARE A against the in-memory program byte at
; CLPTR and set the sticky CAS_VMIS on any difference, WITHOUT writing (verify is
; non-destructive). CLPTR advances TXTBASE.. either way, so in verify mode it is
; exactly the in-memory comparand cursor. Preserves BC, DE; clobbers A, HL, flags.
;   in: A = the program byte just read from tape.
; Clobbers A, C, HL (BC is dead at every call site — the link bytes are stored
; before the next TAPIN, and TAPIN then trashes BC anyway).
cas_put:
                ld      c,a                 ; C = the byte
                ld      hl,(CLPTR)
                ld      a,(CAS_VERIFY)
                or      a
                ld      a,c                 ; A = the byte back
                jr      nz,cput_cmp
                ld      (hl),a              ; load mode: store the byte
                jr      cput_adv
cput_cmp:
                cp      (hl)                ; verify: compare vs the in-memory byte
                jr      z,cput_adv
                ld      a,1
                ld      (CAS_VMIS),a        ; mismatch -> sticky
cput_adv:
                inc     hl
                ld      (CLPTR),hl
                ret

; --- verify_error: report a CLOAD? mismatch (memory left untouched) -----------
; D-CASTAIL: this one IS edited in place, unlike load_error, and the reason is a
; COUNT not a principle -- its only two callers (ctp_verify_done, ctp_oom) are
; both inside do_tape_prog, so `scf` here cannot reach anyone else's carry.
verify_error:
                ld      hl,err_verify
                call    print_msg                       ; D-MSGENC
                scf                             ; a mismatch is a FAILED load: CF out
                ret                             ; (docs/spec-basic-castail.md §3.2)
err_verify:     db      "Verify",MSGESC_ERROR,0         ; 15 B -> 8 B

; --- cas_ascii_load: LOAD of an ASCII (SAVE"CAS:",A) cassette program --------
; Reached from do_tape_prog's header dispatch when byte 0 is $EA (ASCII)
; instead of $D3 (tokenised). Mirrors disk ascii_load (files.asm): LOAD
; replaces the current program (new_prog), then the file is tokenised + stored
; line-by-line by the shared MERGE reader (ascii_read_lines, files.asm) — the
; same path disk ASCII LOAD/MERGE use. The only cassette-specific part is the
; byte SOURCE: ascii_read_lines is re-pointed (D2 getbyte indirection,
; ARL_GETBYTE) at cal_getbyte (below), a TAPIN wrapper, instead of the default
; fat_io_getbyte — restored again before returning so a later MERGE/disk LOAD
; is unaffected.
;
; Entry: cas_open_match has already consumed the FULL 16-byte header (10x $EA +
; 6-char name) and matched the requested name; cas_ascii_setup then primes data
; block 1. (Pre-Tier-3 this routine skipped the 15 trailing header bytes itself.)
;
; BLOCK-BUFFERED byte source (D2 refinement, see spec §4): TAPIN is a REAL-TIME
; read — the tape keeps moving whether or not the CPU polls — so tokenising
; BETWEEN two TAPINs desyncs the next byte. ascii_read_lines does a full
; dispatch_line/tokenise/store_line per line, far more than enough to desync (a
; 34-byte file corrupted after line 1 in an unbuffered first cut). So cal_getbyte
; serves bytes instantly from a 256-byte buffer, refilled (cal_refill) by a tight
; TAPIN*256 loop only at a block boundary — exactly how real MSX slurps a block
; then tokenises during the inter-block leader gap. Symmetric with
; fat_io_getbyte serving from the 512-byte FSECTOR_BUF on disk.
;
; DOUBLE-BUFFERED (CAL_BUF / CAL_BUF2, sysvars.inc CAL_CURHI), not single: a
; single buffer's refill-on-drain still calls TAPION for block N+1 only once
; block N is fully drained, i.e. after ascii_read_lines has tokenised every line
; block N held. The tape keeps playing throughout that tokenise work (requirement
; 2 below), so a block with unusually slow-to-tokenise lines (long ones: nested
; parens, several keywords) lets the tape run past block N+1's leader before
; TAPION is even called — TAPION then locks onto whatever cycles happen to be at
; the CURRENT, too-late position, which on a well-formed tape is misaligned data
; rather than a leader, and the very first TAPIN of that "block" fails.
; (Measured: a single buffer here fixed the ORIGINAL bug — a 21-line, 4-block
; real program truncating after line 50 — but only moved the failure to one
; block later, truncating after line 110 instead of surviving to the end.)
;
; So every block is read ONE BLOCK AHEAD of when ascii_read_lines actually needs
; it: cas_ascii_setup primes block 1 into one buffer, then IMMEDIATELY (before
; any tokenising) primes block 2 into the other. Thereafter, cal_getbyte drains
; whichever buffer CAL_CURHI names, and on the byte that drains it, SWAPS to the
; other one (already pre-fetched — an instant swap, no TAPION on the byte-serve
; path) and kicks off refilling the just-freed buffer with the block after next.
; A block's own TAPION therefore always fires when the block BEFORE its
; predecessor drains — one whole block's tokenise time earlier than a single
; buffer gives it, which is what let the same 21-line program's block 4 succeed
; (block 3's slow lines no longer delay block 4's own TAPION — see
; sysvars.inc's CAL_CURHI comment and docs/spec-cas-ascii-saveload.md).
;
; TWO HARD REQUIREMENTS ON cal_refill, both learned the hard way:
;  (1) STATE LIVES IN RAM, NOT ON THE STACK, ACROSS TAPIN. TAPIN clobbers every
;      register AND does not preserve a caller value pushed on the stack across
;      it — a `push hl`/`pop hl` of the buffer pointer around TAPIN reads back the
;      whole block as $00 (confirmed: the exact same tokenised block ctp_body
;      reads byte-perfect came back all-zero through a stack-guarded loop). So the
;      fill keeps its position in CAL_CNT (RAM) and recomputes the address each
;      byte — the same "state in RAM across a BIOS tape call" discipline
;      do_tape_prog's ctp_body uses (it guards CLPTR in RAM, not the stack). The
;      fill TARGET (which buffer) lives in RAM too (CAL_CURHI), for the same reason.
;  (2) THE DATA-BLOCK TAPION MUST BE PROMPT — for EVERY block, not just block 1.
;      Deferring it past new_prog + the ascii-reader entry makes it miss the block
;      leader and fail to relock. Block 1 is primed HERE, right after the header
;      skip, back-to-back like do_tape_prog; block 2 is primed immediately after
;      block 1, just as promptly. cal_getbyte's steady-state read-ahead (below)
;      keeps every later block just as prompt, one block early.
;
; 🔴 D-CAS4BLK (2026-09-27): EVERYTHING ABOVE ASSUMES THE TAPE KEEPS PLAYING, AND
; SINCE THEN IT DOES NOT. cal_refill never stopped the motor, which is why block
; timing mattered at all -- and a 4-block program regressed to 360 of 631 bytes
; once tokenising got slower. It now ends with TAPIOF, so the tape WAITS while a
; block is tokenised and TAPION restarts it at the next block's leader. The
; double buffer and requirement (2) are kept (both still hold, and harmless),
; but they are no longer what makes a long program load.
; ascii_read_lines stops at the first Ctrl-Z ($1A) — which every producer puts in
; the LAST real block (§0.1) — so the reader stops before ever draining the final
; block, and the read-ahead is never asked for a non-existent block on a
; well-formed tape. `,R`/RUN is unchanged — the caller (do_load's LOAD"CAS:",R /
; do_cload) applies RUNFLAG exactly as the tokenised path's `ret`.
cas_ascii_load:
                call    cas_ascii_setup     ; skip the rest of the header + prime block 1
                jp      c,dpl_err           ; header / block-1 unreadable -> load error
                call    new_prog            ; LOAD replaces the current program
                call    cas_ascii_drive     ; read+tokenise+store via the tape source
                jp      c,dpl_err           ; non-numbered line -> abort
                ret                         ; caller handles ,R / returns to the REPL.
                                            ; D-CASTAIL: CF is ALREADY CLEAR here (the
                                            ; `jp c` above did not take), so the ASCII
                                            ; success path needs no `or a` -- 0 bytes

; --- cas_ascii_setup: prime data blocks 1 AND 2 of an $EA cassette file -------
; The whole 16-byte header (id + name) is now consumed upstream by cas_open_match
; (Tier-3 name-matching), so this PRIMES the first data block -- then, for the
; double buffer (cload.asm header comment), the SECOND, just as promptly, before
; any caller processing. Shared by cas_ascii_load (LOAD), merge_cas and
; oo_dev_cas (all of which reach it via cas_open_match).
; Leaves CAL_CURHI = CAL_BUF (block 1 is what gets served first), CAL_CNT = 0,
; and CAL_NEEDFILL reporting whether CAL_BUF2 holds a genuine block 2 (0) or the
; file was only ever one block long (1 -- fine, ascii_read_lines's Ctrl-Z stops
; it inside block 1 well before a block 2 would ever be asked for).
;   out: CF set = data block 1 read failed.
cas_ascii_setup:
                ; 💰 D-CARVECAS: the body (prime block 1, then block 2 at once) is
                ; the casget tenant's op 1 now (sub/casmatch.asm), beside the sub
                ; ROM's own cal_refill; it answers A = $FF when block 1 is
                ; unreadable, and `rra` turns that back into this label's CF.
                ld      l,1
                call    casget_call
                rra                         ; $FF -> CF set, 0 -> CF clear
                ret

; --- cas_ascii_drive: run ascii_read_lines off the tape byte source, then restore
; the default (disk) source and stop the motor. Shared by cas_ascii_load (LOAD) and
; merge_cas (MERGE"CAS:"). The getbyte indirection (ARL_GETBYTE) is pointed at
; cal_getbyte for the read and put back to fat_io_getbyte afterwards so a later
; MERGE / disk LOAD is unaffected.
;   out: CF from ascii_read_lines (set = a non-blank, non-numbered line).
cas_ascii_drive:
                ld      hl,cal_getbyte
                ld      (ARL_GETBYTE),hl
                call    ascii_read_lines    ; tokenise + store; CF set = bad line
                push    af                  ; preserve the ascii_read_lines result CF
                ld      hl,fat_io_getbyte
                ld      (ARL_GETBYTE),hl
                call    TAPIOF              ; motor off (file fully read), as ctp_done
                pop     af
                ret

; --- cal_getbyte: cassette ASCII-load byte source (D2 indirection target) ----
; Serves the next byte from whichever buffer CAL_CURHI names, at position
; CAL_CNT (0..255), instantly — NO tape I/O — so the tokenise/store work
; ascii_read_lines does between calls is harmless. The byte that DRAINS a buffer
; (position wraps 255->0) SWAPS CAL_CURHI to the other one, which the double
; buffer guarantees is ALREADY pre-fetched (an instant swap, no TAPION on this
; path) — then kicks off refilling the just-freed buffer with the block after
; next, so a fresh block is always one full block ahead of when it's needed
; (requirement 2; see the header comment above and sysvars.inc's CAL_CURHI).
; The drained byte is parked in CAL_SAVE across that refill (requirement 1).
;   out: A = byte, CF clear; or CF set = no more data at all.
cal_getbyte:
                ld      a,(CAL_NEEDFILL)
                cp      2
                scf                         ; terminal EOF, latched by a prior drain:
                ret     z                   ; answered here, no crossing
                ; 💰 D-CARVECAS: serving the byte -- and the buffer swap + the
                ; read-ahead refill on the byte that drains one -- is the casget
                ; tenant's op 0 (sub/casmatch.asm). A crosses back as the byte, and
                ; subrom_call's own `or a` is exactly this routine's "CF clear = a
                ; byte" answer, so the tail needs no conversion. The tape timing
                ; requirements above are unchanged: the refill still runs
                ; back-to-back with the drain, one CALSLT later.
                ld      l,0
casget_call:
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_CASGET
                jp      sc_call             ; A = the tenant's answer, CF clear

; --- cas_in_getbyte: OPEN"CAS:" FOR INPUT byte source (ARL_GETBYTE target) ----
; Wraps cal_getbyte with the sequential-file EOF rule: a Ctrl-Z ($1A) in the data
; is end-of-file (§0.1 / MSX2 TH — the same soft-EOF that ends an ASCII program,
; but here INPUT#/LINE INPUT# must STOP on it rather than treat it as a data byte,
; since a data file has no line structure). Returns CF on either a real refill
; failure (cal_getbyte CF) or the Ctrl-Z. read_into_strscr (via arl_getbyte) then
; ends the field/line exactly as it does on a disk fat_io_getbyte EOF.
;   out: A = byte, CF clear; or CF set = end of file.
cas_in_getbyte:
                call    cal_getbyte
                ret     c                   ; source EOF (refill failed)
                cp      $1A
                jr      z,cig_eof           ; Ctrl-Z -> end of file
                or      a                   ; CF clear = valid byte (A = the byte)
                ret
cig_eof:
                scf
                ret

; cal_refill: NO LONGER RESIDENT (D-CARVECAS). Its only main callers were
; cal_getbyte's refill and cas_ascii_setup, and both bodies are the casget
; tenant's now (sub/casmatch.asm), which reaches the sub ROM's own copy of
; basic/cal-refill-body.inc -- the one casmatch already carried. 32 B.

; --- disk_prog_load: load a TOKENISED BASIC program from disk ----------------
; The disk analogue of do_tape_prog. The FCB at DISK_FCB is fully built (drive
; code + 8.3 name) by parse_disk_fcb. This opens the file through the disk ROM's
; BDOS FCB layer, requires the on-disk tokenised-BASIC marker ($FF), streams the
; in-memory line-link image into the stored-program area at TXTBASE, closes the
; file, relinks, and returns — leaving a loaded, current program. The caller
; decides whether to RUN it (LOAD,R) so this is reusable by RUN"filename".
;
; On-disk tokenised-BASIC format (MSX-BASIC file formats, an allowed public
; language reference; see PROVENANCE.md §disk
; LOAD): a leading marker byte $FF (BASIC_DISK_ID), then the in-memory program
; image — the SAME line-link chain do_tape_prog reads:
;   [link:2 LE][lineno:2 LE][tokens...][00] per line, ending in a $0000 link word.
; This is DISTINCT from the BSAVE binary's $FE disk marker.
;
; Unlike the tape path (which has no clean end-of-data and must stop EXACTLY at
; the $0000 end-link), the disk reader has BOTH a real EOF (fat_io_getbyte CF=EOF)
; and the $0000 end-link. The $0000 link is the authoritative end (we stop there
; and close); an EOF encountered mid-line is a truncated/corrupt file -> error.
;
; Uses fat.asm's loader-side FAT12 engine over the standard $4010 DSKIO entry
; (disk-ROM-independent): fat_io_open (mount + find + prime) and fat_io_getbyte
; (the file byte stream). Mirrors do_tape_prog's ctp_line/ctp_body/ctp_done
; line-for-line, but sourcing bytes from fat_io_getbyte. No Close on the read side.
; ⚠️ CF-OUT CONTRACT (D-RUNTAIL, docs/spec-basic-runtail.md §3.2): CF clear =
; a program is loaded; CF SET = the load failed and has ALREADY REPORTED. The
; callers that RUN what was loaded (do_run, do_load's ,R arm) refuse on CF, so a
; RUN"missing" runs NOTHING -- it used to print its message and then run whatever
; program happened to be resident (measured on the CF-3300: it does not,
; docs/runtail-msx1-characterization.md §4).
;
; 🔴 THE CONTRACT IS STATED ON THIS ROUTINE'S OWN EXITS, NOT INSIDE load_error.
; load_error is `jp`ed to from ~50 sites across files/save/print/field/format/
; bload/cload, several of which RESUME into their caller on purpose (see
; save.asm's bsave_opt4 header). An `scf` in load_error would change the returned
; CF for every one of them. So the failure exits below funnel through dpl_err,
; which calls load_error and sets CF itself.
disk_prog_load:
                ; (1) disk ROM slot must have been recorded by the INIT scan.
                call    diskslot_test
                jr      z,dpl_err           ; no disk ROM at all: NO primitive has
                                            ; run, so DISKOP_OP would be stale --
                                            ; and dpl_err is the SAFE tail now
                ; (2) HAND THE WHOLE LOAD TO disk.rom (step 9, D-DPLWIRE).
                ; 🏗️ Joost's ruling (spec-diskcode-eviction.md §6.6m, re-affirmed
                ; in §6.7's *"we do as the reference does"*): mount, directory
                ; search, FAT walk and the entire byte loop live where the
                ; reference keeps them, reached through ONE claimed cell. Main's
                ; side of the contract is the three lines below plus a decode --
                ; it evaluates the filespec, says which verb is asking, and
                ; commits the program that comes back.
                ;
                ; 🔴 THE SELECTOR GOES IN FIRST, and it is not a formality:
                ; FOPEN_SEL aliases DISKOP_OP, and $FE5D is reached on paths that
                ; are not ours, so hk_dpload answers CF=0 to anything that is not
                ; exactly FOPEN_SEL_LOAD ($4C, outside DISKOP_SEL_*'s 0..7 range).
                ; Steps 10-12 (OPEN, MERGE, SAVE) add a value each here and an
                ; arm there; that is the whole shape (§6.6n).
                ;
                ; ⚠️ WHY chan_gate AND NOT A BARE `call H_FOPEN`. The cell is
                ; `F7 <slot> <lo> <hi> C9`; unclaimed it is a bare `ret` and the
                ; call returns with CF as we left it. chan_gate is the one place
                ; that reads that answer -- CF=0 -> ERR 5, trappable, which is
                ; what the reference gives a diskless machine. diskslot_test
                ; above still runs first, so the diskless path is unchanged.
                ld      a,FOPEN_SEL_LOAD
                call    fopen_cross           ; claimed -> disk.rom ran the WHOLE
                                            ; load, and CLPTR/CLINK are seeded
                ; (3) decode what it did. DISKOP_STATUS, not A: that is what
                ; every other hook in hook_tab answers through (hk_files,
                ; hk_kill, hk_copy) and main already decodes it that way.
                ; (A = DISKOP_STATUS, Z iff 0 -- fopen_cross, D-CARVEFO)
                jp      z,dpl_done          ; 0 = loaded -> relink and commit
                dec     a
                jp      z,df_notfound       ; 1 = not found -> ERR 53, and it
                                            ; RAISES: D-LOADERR measured both
                                            ; references stopping here, and
                                            ; do_run must not run the old program
                dec     a
                jr      z,ascii_load        ; 2 = not tokenised -> main re-opens
                                            ; from offset 0 and tokenises
                dec     a
                jr      nz,dpl_oom          ; 4 = out of memory
                ; 3 = mount / I-O. `call`, not `jp`: disk_error raises the MAPPED
                ; code when disk.rom recorded one in DISKOP_ERR (the shared DSKIO
                ; mapping that survived D-DPLMOVE's back-out) and otherwise falls
                ; to the non-raising `load error` -- which must still return with
                ; CF SET, the D-RUNTAIL contract in this routine's header.
                call    disk_error
                scf
                ret
; 🟢 THE TOKENISED LOAD LOOP IS GONE FROM MAIN (step 9, D-DPLWIRE 2026-09-20).
; dpl_line / dpl_body / dpl_get_store / dpl_eof / dpl_oom_pop and dpl_nf lived
; here and are now hk_dpload's, in disk.rom -- 120 B of main page 1 returned.
; dpl_nf went with them because its own header said it was ONLY safe for an arm
; whose CF came DIRECTLY from a main-side fat_io_open; there is no such arm left,
; and DISKOP_OP now carries the SELECTOR, so reading it as a FAT primitive code
; would be exactly the stale-cell bug that header warned about. Not-found is
; disk.rom's DISKOP_STATUS = 1 now, decoded straight to df_notfound.
; What stays: dpl_done (the shared commit), dpl_err, dpl_oom and ascii_load --
; the ASCII path is still main's, because tokenising is.
; dpl_done — program fully read; no Close, the read side has no dirty state.
; D-NGRAM12: an ALIAS, not a second copy. This body WAS ten instructions
; byte-identical to do_tape_prog's completion tail; they are one routine now,
; `load_commit_prog`, which carries the comment. The NAME and its call site
; survive so the disk face still reads as its own.
dpl_done        equ     load_commit_prog

; dpl_err — take the normal error path. Reached on an unexpected EOF mid-program,
; a wrong marker, an Open after the file vanished, a missing disk slot, or any
; ascii_load failure. (No Close: read side has no dirty state.)
; D-RUNTAIL: `call` + `scf`, not `jp` — this IS the CF-set half of the contract
; above, and load_error's own return carry belongs to its other ~50 callers.
;
; ⚠️ D-CASTAIL: SHARED WITH do_tape_prog. Every tape failure exit repoints here
; too (docs/spec-basic-castail.md §3.2), so defect B's PRODUCER costs 0 B on the
; tape path -- these five bytes already say exactly 'reported, and failed'. The
; `dpl_` prefix is therefore no longer disk-only; renaming it would churn eight
; disk call sites and make spec-basic-runtail.md §3.2's table stale for nothing.
; 🔴 dpl_err IS SHARED WITH THE WHOLE CASSETTE PATH (do_tape_prog above, nine
; `jp c,dpl_err` sites) AND THAT IS WHY THE NOT-FOUND TEST IS NOT HERE.
; D-LOADERR's first draft put `call df_or_loaderr` in this tail. It reads
; DISKOP_OP, which only `fatprim_bounce` writes — so on a CASSETTE failure the
; cell is STALE from whatever disk statement ran last, and when that happened to
; be a `fat_find` the machine answered `File not found` to a broken TAPE.
; `castail-acceptance`'s `cas-run-brk` caught it: vg8020/cf3300 `Device I/O
; error`, zerobas `File not found`. An existing gate ran a knife nobody wrote.
; 🎯 SO THE DEFAULT IS INVERTED: this tail is the SAFE one and reading the stale
; cell is OPT-IN, at `dpl_nf` below, reached only from an arm whose CF came
; DIRECTLY from a main-side `fat_io_open`. A new caller that lands here gets the
; unchanged behaviour instead of a wrong message.
dpl_err:
                call    load_error
                scf
                ret
; dpl_oom — store overflow: leave a clean (empty) program, report "out of memory".
; Mirrors ctp_oom for the disk store-overflow case. (No Close: read side is clean.)
dpl_oom:
                call    new_prog            ; leave a clean (empty) program
                ld      a,$CC               ; out-of-memory landmark (as store_line)
                ld      (ERRMARK),a
                ld      hl,err_prog_mem
                call    print_msg           ; D-MSGENC (as ctp_oom above)
                scf                         ; D-RUNTAIL: a store overflow is a FAILED
                ret                         ; load too -- RUN"file" must not then run the
                                            ; empty program new_prog just left

; --- ascii_load — LOAD of an ASCII (SAVE",A") program ------------------------
; Reached from disk_prog_load when the first byte is NOT the $FF tokenised marker.
; LOAD replaces the current program (unlike MERGE, which keeps it): clear it,
; re-open the stream from offset 0 (the marker probe consumed byte 0), then
; tokenise + store each line via the shared MERGE reader (ascii_read_lines,
; files.asm). Returns to disk_prog_load's caller, which honours ,R (RUNFLAG) /
; the implicit RUN"name" exactly as the tokenised path's `ret` does. A file that
; is not line-numbered ASCII (e.g. a BSAVE binary mis-routed here) trips the
; reader's non-numbered-line guard -> load_error. Clean-room: public ASCII format,
; no reference ROM read. See basic/docs/spec-ascii-saveload.md §4.
ascii_load:
                call    new_prog            ; LOAD replaces the current program
                ; 🔴 STEP 11 (D-MERGEPORT): THE RE-OPEN CROSSES NOW. The disk ROM
                ; already has this file open -- hk_dpload read its first byte to
                ; decide the format -- so what main needs is a REWIND, and asking
                ; the disk side to open it again is the rewind. Same selector and
                ; same byte source `MERGE` uses, because on the reference ASCII
                ; `LOAD` and `MERGE` are ONE mechanism: an identical 47-cell set,
                ; counts differing by at most 1 on nine of them (§8.6a).
                call    dsk_aopen           ; mount + find + prime, on the disk side
                jr      c,dpl_err           ; file vanished between opens -> error
                call    dsk_ascii_drive     ; tokenise + store; CF set = bad line
                jr      c,dpl_err           ; non-numbered line / not an ASCII program
                ret                         ; caller handles ,R / returns to the REPL
                                            ; (D-RUNTAIL: CF is clear here -- the `jp c`
                                            ; two lines up did not fire)

; --- autoexec_run: cold-start AUTOEXEC.BAS auto-run (disk/docs/autoexec-bas-spec.md) ---
; Called once from interp.asm's `init`, between the startup banner (show_title)
; and the REPL (jp repl). Public spec (MSX2 Technical Handbook, Ch.3 MSX-DOS,
; boot procedure, an allowed source): "When MSX-DOS is not invoked and DISK-BASIC
; starts, if a BASIC program named AUTOEXEC.BAS exists, it will be carried out."
; Absent / empty -> silent, normal startup (black-box characterised on
; National_CF-3300; see disk/docs/autoexec-bas-spec.md §2).
;
; This is the do_run disk pattern (do_run, above) minus the command parser, plus
; a SILENT presence probe up front: disk_prog_load's own not-found path is the
; noisy load_error (right for a typed RUN"missing", wrong for a boot-time probe
; that must stay quiet on the common no-AUTOEXEC.BAS case). So we fat_mount +
; fat_find ourselves first and ret quietly on "no disk" / "not found" / "empty",
; only reaching disk_prog_load once a non-empty file is confirmed present.
autoexec_run:
                ; (1) no disk ROM recorded by the INIT scan -> silent skip (same
                ; gate disk_prog_load uses).
                call    diskslot_test
                ret     z
                ; (2) stage the upcased 11-byte 8.3 name at DISK_FCB_NAME.
                ld      hl,autoexec_name
                ld      de,DISK_FCB_NAME
                ld      bc,11
                ldir
                ; (3) silent presence probe: mount, then search the root dir.
                call    fat_mount
                ret     c                   ; no / bad disk -> silent skip
                ld      hl,DISK_FCB_NAME
                call    fat_find
                ret     c                   ; not found -> silent skip
                ; (4) empty file (size == 0, all 4 LE bytes) -> silent skip,
                ; matching stock's silent behaviour on a 0-byte AUTOEXEC.BAS.
                ld      hl,FAT_FILESIZE
                ld      a,(hl)
                inc     hl
                or      (hl)
                inc     hl
                or      (hl)
                inc     hl
                or      (hl)                ; Z iff size == 0 (all 4 bytes)
                ret     z
                ; (5) found & non-empty -> load the tokenised program, then RUN
                ; it (clear_vars + control-flow reset), and fall through to the
                ; caller's `jp repl`. disk_prog_load re-opens via fat_io_open
                ; (mount+find+prime again) -- cheap, reuses the whole loader; a
                ; load failure lands in disk_prog_load's load_error (prints +
                ; leaves an empty store), so the trailing run_prog is then a
                ; harmless no-op (error-then-Ok, per spec §3 point 5).
                call    disk_prog_load
                jp      run_prog

; --- autoexec_name: the upcased 11-byte 8.3 name we probe for on cold start ---
; "AUTOEXEC" (8) + "BAS" (3) = exactly 11 non-space characters -- no padding
; needed (see disk/docs/autoexec-bas-spec.md §3 point 2).
autoexec_name:  db      "AUTOEXECBAS"
