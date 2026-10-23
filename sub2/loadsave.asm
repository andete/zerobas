; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; loadsave.asm -- zerobas-sub2 PAGE 0: the program SAVE / LOAD statements SAVE,
; CSAVE, BSAVE, LOAD, CLOAD, BLOAD and the name arm of RUN (D-P0CB slice C2,
; docs/spec-sub2-p0cb.md §5). Moved out of main page 1 (basic/save.asm,
; basic/cload.asm, basic/bload.asm) and main's low region (tape_parse_cut,
; basic/main.asm) on 2026-10-21. Only what these verbs alone reach moved: the
; PARSE -- the name and its device, the option tails (`,R` / `,S` / `,A`, BLOAD's
; offset, BSAVE's addresses and fourth slot, CSAVE's speed) -- and the decision
; each statement makes at its end.
;
; THE LOADERS AND WRITERS STAY IN MAIN, and are reached through p0cb:
;   do_tape_prog     the tape program reader. Its TAPION / TAPIN loop is
;                    REAL-TIME (basic/cload.asm, tape/tape.asm): one p0cb runs it
;                    whole in main, so not one cycle between two TAPINs changes.
;   disk_prog_load   autoexec_run (main's init) calls it too.
;   sv_tenant / bload_sub   the sub-ROM tape engines (sub/save.asm, sub/bload.asm)
;                    are reached through an INLINE-byte call (sc_inl1), which a
;                    p0cb'd caller cannot hand over: IX is p0cb's target. So each
;                    keeps a main wrapper that carries its byte.
;   load_commit_prog, cas_ascii_load, cas_write_ea_header, cas_ascii_finish,
;   list_all, fopen_cross ...   shared with OPEN / CLOSE / LIST / disk.rom.
;
; Entered through trap_tenant (sub2/trapstmt.asm) -> file_tenant
; (sub2/filestmt.asm), which forwards every token it does not own here. Main's
; six entry labels share ex_open's ONE byte, `ld c,a` in front of ex_sub2
; (basic/program.asm): exec_stmt hands a handler A = its token. RUN's name arm is
; the exception -- main keeps bare RUN and RUN <line> (basic/cload.asm do_run)
; and sends only a NAME here, with C = RUN_TOKEN.
;   in   HL = the cursor ON the statement token (exec_stmt's contract) -- for
;             RUN, on the first non-space byte AFTER it (do_run's skipsp_test)
;        A = C = the token
;   out  DE = the main address to continue at, HL = what it expects (below)
; ex_sub2 then does `push de / ret` with the stack exactly as the statement was
; entered, so a continuation behaves as main's `jp` to it did. The continuations:
;   exec_stmt       HL = the cursor   (SAVE / BSAVE to disk: `ks_nz_diskerr`)
;   disk_error      nothing; raises a pending DSKIO code, else PRINTS `load
;                   error` and RETURNS to the statement's caller
;   end_line_end    nothing; the line (and a run) ends -- LOAD without ,R,
;                   CLOAD, SAVE "CAS:", SAVE ,A
;   run_prog_top    nothing; LOAD ,R and RUN <name> run the loaded program
;   load_handoff    nothing (it reads FN_RESUME); BLOAD, and ,R's call into the
;                   loaded code -- the $6CF3 pin's lh_back is behind it
;   bp_ret          a bare `ret`: what main's handler did with `ret` / `ret c` --
;                   a load that FAILED and already reported (D-RUNTAIL / D-CASTAIL
;                   defect B), and the tape writes' `jp sv_tenant`, whose `ret z`
;                   returned from the handler
; None of them is ever reached through p0cb: execution must not go on INSIDE
; this CALSLT (a loaded program would run with page 0 on this ROM).
;
; Every other main routine is reached through p0cb (sub2/p0cb.asm) with its
; `p0_` alias from basic-resident-abi.inc; `rst $10` / `rst $18` are this ROM's
; RST 10h / 18h (main's CHRGTR / OUTDO). A raise reached through p0cb never
; returns -- raise_error resets SP and runs main's error path with main's page 0
; mapped -- exactly as the `jp` it replaces never returned. The one HOOK call
; (SAVE ,A's `call H_CHCLOSE`) goes through p0cb as well: the hook's CALLF is
; main's RST 30h. The shared tails fs_syntax (stmt_error, ERR 2), fs_illegal
; (gb_illegal, ERR 5), fs_dio (dpl_dio, ERR 19), fs_exec and fs_disk_error are
; sub2/filestmt.asm's.
; The code is otherwise main's, statement for statement, and each arm keeps the
; original's order of checks, so the errors and their order are the ones the
; save / load / tape gates already pin. The history behind each check is in git
; (basic/save.asm, cload.asm and bload.asm before D-P0CB slice C2); what is kept
; here is the measured rule each one encodes.

; --- the dispatch -------------------------------------------------------------
ls_tenant:                                  ; A = C = the token (file_tenant's tail)
                cp      SAVE_TOKEN
                jp      z,ls_save
                cp      CSAVE_TOKEN
                jp      z,ls_csave
                cp      BSAVE_TOKEN
                jp      z,ls_bsave
                cp      LOAD_TOKEN
                jp      z,ls_load
                cp      CLOAD_TOKEN
                jp      z,ls_cload
                cp      BLOAD_TOKEN
                jp      z,ls_bload
                ; FALL THROUGH: RUN_TOKEN is the only other token main sends
                ; (do_run's name arm); no other reaches here

; ===========================================================================
; RUN <name expression>   (main's do_run, from its fname_dev on)
; ===========================================================================
; A tokenised or ASCII program from disk or tape, then RUN at TOP LEVEL
; (run_prog_top: D-RUNTAIL). A load that FAILED has already reported and runs
; NOTHING -- not the resident program (D-RUNTAIL / D-CASTAIL defect B). The `,R`
; tail is accepted and harmless (pcr_load); running is implicit. CAS_VERIFY is
; cleared HERE rather than before do_run's dispatch: only the tape reader reads
; it, and bare RUN / RUN <line> load nothing.
ls_run:                                     ; HL on the first non-space byte
                xor     a
                ld      (CAS_VERIFY),a      ; RUN"CAS:" is a real load, never verify
                call    ls_fname_dev        ; Z = "CAS:" (HL past it), else the disk
                jr      z,lrn_cas
                ld      ix,p0_pdfcb_resume
                call    p0cb                ; DISK_FCB; HL resumes in the text
                call    ls_pcr_load         ; the only '"' is fname_expr's own
                ld      ix,p0_disk_prog_load
                call    p0cb                ; CF = failed, already reported
                jr      lrn_loaded
lrn_cas:
                ld      ix,p0_cas_capture_cut
                call    p0cb                ; -> CAS_WANT + CAS_WANT_ON (D-CASDOT)
                ld      hl,(FN_RESUME)      ; D-FNRUN: resume past the EXPRESSION
                call    ls_pcr_load         ; (+ a harmless ,R: run is implicit)
                ld      ix,p0_do_tape_prog
                call    p0cb                ; tokenised OR $EA ASCII; CF = failed
lrn_loaded:
                jr      c,ls_ret            ; failed and reported: run NOTHING
ls_run_top:                                 ; main's `jp run_prog_top`: a CONTINUATION
                ld      de,p0_run_prog_top
                ret

; ===========================================================================
; LOAD <name>[,R]   (main's do_load)
; ===========================================================================
; The name is a string EXPRESSION (D-FNEXPR2); "CAS:" (or no disk: D-NODISKVERBS)
; is the tape, else the disk. LOAD RETURNS TO COMMAND LEVEL (D-MERGERET: the
; statement stream is gone), or with ,R runs the program at top level.
ls_load:
                inc     hl                  ; past the LOAD token (main's ex_load)
                xor     a
                ld      (CAS_VERIFY),a      ; LOAD is a real load, never CLOAD? verify
                call    ls_fname_dev
                jr      nz,lld_disk         ; no "CAS:" prefix -> disk (HL restored)
                ld      ix,p0_cas_capture_cut
                call    p0cb                ; -> CAS_WANT + CAS_WANT_ON; a . ends the name
                ld      hl,(FN_RESUME)      ; the ,R tail lives in the PROGRAM TEXT
                call    ls_pcr_load
                ld      ix,p0_do_tape_prog
                call    p0cb                ; CF = failed, already reported
                jr      lld_loaded
lld_disk:
                ld      ix,p0_pdfcb_resume
                call    p0cb                ; DISK_FCB; HL resumes in the text
                call    ls_pcr_load         ; ,R tail only -- no quote in the text
                ld      ix,p0_disk_prog_load
                call    p0cb                ; CF = failed, already reported
lld_loaded:                                 ; main's dl_loaded
                jr      c,ls_ret            ; failed: ,R must not run what was resident
                ld      a,(RUNFLAG)
                or      a
                jr      nz,ls_run_top       ; ,R: RUN the loaded program, at TOP LEVEL
ls_end_line:                                ; main's `jp end_line_end`: a CONTINUATION
                ld      de,p0_end_line_end
                ret
ls_ret:                                     ; main's handler `ret` (bp_ret is one)
                ld      de,p0_bp_ret
                ret

; ===========================================================================
; CLOAD["name"]  /  CLOAD?["name"]   (main's do_cload)
; ===========================================================================
; The device is the tape. `CLOAD?` tokenises to CLOAD + PRINT ('?') and is the
; VERIFY form. The name is a string EXPRESSION (D-CSAVEEXPR: `CLOAD 5` is 13) and
; HONOURED (Tier-3); no name = the next file. CLOAD SEARCHES FOR A TOKENISED FILE
; (D-CASTYPE: bit 7 of CAS_WANT_ON). It ends the LINE, load or verify alike
; (D-CLOADPROG); a failed load has already reported and only returns.
ls_cload:
                inc     hl                  ; past the CLOAD token (main's ex_cload)
                xor     a
                ld      (CAS_VERIFY),a      ; default: a real load (not CLOAD?)
                ld      ix,p0_skip_spaces
                call    p0cb
                cp      PRINT_TOKEN         ; CLOAD? -> compare-mode verify
                jr      nz,lcl_name
                inc     hl                  ; past the '?' (PRINT_TOKEN)
                ld      a,1
                ld      (CAS_VERIFY),a      ; compare, do not store
                xor     a
                ld      (CAS_VMIS),a        ; fresh verify (no mismatch yet)
                ld      ix,p0_skip_spaces
                call    p0cb
lcl_name:                                   ; A = (HL): a name, or a terminator
                or      a
                jr      z,lcl_noname        ; bare CLOAD / CLOAD? -> next tape file
                cp      COLON
                jr      z,lcl_noname        ; CLOAD : ... -> bare form
                ld      ix,p0_fname_expr
                call    p0cb                ; HL -> the staged '"'-terminated copy
                ld      ix,p0_cas_capture_name
                call    p0cb                ; -> CAS_WANT + CAS_WANT_ON=1 (no ,R)
                jr      lcl_load
lcl_noname:
                xor     a
                ld      (CAS_WANT_ON),a     ; no name -> load the next tape file
lcl_load:
                ld      hl,CAS_WANT_ON
                set     7,(hl)              ; D-CASTYPE: a tokenised ($D3) file only
                ld      ix,p0_do_tape_prog
                call    p0cb
                jr      c,ls_ret            ; failed: already reported
                jr      ls_end_line         ; D-CLOADPROG: the line ends

; ===========================================================================
; BLOAD <name>[,R|,S][,offset]   (main's do_bload)
; ===========================================================================
; The name is evaluated here (D-FNEXPR2: str_eval is main's) and crosses STAGED
; in STRSCR; the whole tail is parsed here too, BEFORE the device is touched
; (D-BLOADOFS). The sub-ROM tenant (sub/bload.asm) decides the device, reads a
; tape, and for a disk file answers BL_STAT = FOPEN_SEL_BLOAD, which disk.rom
; loads through fopen_cross. BL_STAT / the status: 0 loaded -> load_handoff (the
; ,R call into the loaded code, and the rest of the line); 1 -> disk_error (ERR
; 70 on an empty drive, else `load error`, printed); n -> raise ERR n.
ls_bload:
                inc     hl                  ; past the BLOAD token (main's ex_bload)
                ld      ix,p0_fname_expr
                call    p0cb                ; HL -> the staged '"'-terminated copy
                ld      (BL_PTR),hl         ; staged name ptr -> tenant
                call    ls_pcr_bload        ; D-BLOADOFS: the whole tail, HERE
                ld      ix,p0_fch_park
                call    p0cb                ; D-ASAVECHAN2: park the live channel
                xor     a                   ; D-CASFCB: a tape BLOAD's search skips
                ld      ix,p0_cas_bufp_set  ;  other files through channel #0's
                call    p0cb                ;  buffer
                ; 📼 D-BLOADSTK (2026-10-23): the LOAD runs in main, not under this
                ; tenant's CALSLT. Run from here (p0cb -> bload_sub -> its sub-ROM
                ; call) a tape BLOAD sat ~26 B deeper than the VG-8020's, inside RAM a
                ; no-CLEAR loader fills ($F072 against $F08C, scratchpad/bloadstk_*.out),
                ; and the load wrote over live return addresses. main's bload_cont
                ; makes the call and decides on BL_STAT, as this did.
                ld      de,p0_bload_cont    ; a CONTINUATION
                ret

; ===========================================================================
; SAVE <name>[,A]   (main's do_save)
; ===========================================================================
; The name is a string EXPRESSION (D-FNEXPR2). Disk: tokenised unless `,A`;
; the end of the statement is required BEFORE any write (D-SAVECOLON: junk is
; ERR 2 and nothing is created), then disk.rom writes it through fopen_cross and
; the rest of the line runs. Tape: ALWAYS ASCII ($EA), `,A` or not (D-CASSAVE).
ls_save:
                inc     hl                  ; past the SAVE token (main's ex_save)
                call    ls_fname_dev
                jr      z,lsv_cas           ; matched "CAS:" -> tape (HL past the prefix)
                ld      ix,p0_pdfcb_resume
                call    p0cb                ; DISK_FCB; HL -> the tail
                ld      ix,p0_skip_comma
                call    p0cb
                jr      z,lsv_ascii_flag    ; SAVE"name",<flag> -> check for ,A
                dec     hl                  ; stmt_bare_end opens with rst $10
                ld      ix,p0_stmt_bare_end
                call    p0cb                ; Z iff 0 or ':'
                jp      nz,fs_syntax        ; junk: ERR 2, nothing written
                push    hl                  ; the statement's end, for exec_stmt
                ld      a,FOPEN_SEL_SAVE    ; D-SAVEPORT: disk.rom writes it
lsv_cross:                                  ; BSAVE's disk arm joins here (main's sv_cross)
                ld      ix,p0_fopen_cross
                call    p0cb                ; unclaimed -> ERR 5; A = DISKOP_STATUS, Z iff 0
                pop     hl                  ; flags survive the pop
                jp      nz,fs_disk_error    ; main's ks_nz_diskerr: 3 = mount / full /
                jp      fs_exec             ; write / I-O; 0 = written, the line runs on
lsv_ascii_flag:
                call    ls_flag_a
                ; SAVE ,A to disk (main's ascii_save): the LIST walk into the
                ; file, with NO channel live -- which is how disk.rom tells this
                ; stream from an OPEN's (D-ASAVEDOUT)
                ld      ix,p0_fch_park
                call    p0cb                ; D-ASAVECHAN
                ld      a,FOPEN_SEL_MAKE
                ld      ix,p0_fopen_cross
                call    p0cb                ; unclaimed -> ERR 5; Z iff created
                jp      nz,fs_disk_error    ; the pending code (a continuation)
                xor     a
                ld      (PRDEV),a           ; 0 = the disk sink (D-ASAVEDEV)
                inc     a
                ld      (PRDEST),a          ; 1 = pchar -> the file
                ld      ix,p0_list_all
                call    p0cb                ; list_ALL: a preceding LIST range must not
                                            ; cut the save short (D-LSTRNG)
                ld      a,$1A               ; Ctrl-Z soft-EOF (ASCII program terminator)
                rst     $18
                xor     a
                ld      (PRDEST),a          ; restore the screen sink before Close
                ld      ix,H_CHCLOSE        ; disk.rom: the partial sector + the entry
                call    p0cb                ; (a HOOK: its CALLF is main's RST 30h)
                ei                          ; a CALLF returns DI (cg_back's note)
                jp      ls_end_line         ; D-KWSAVEEND: the run stops, as LIST's does
lsv_cas:
                call    ls_tape_parse_cut   ; TSV_NAME; a . ends the name (D-CASDOT)
                ld      hl,(FN_RESUME)      ; D-FNEXPR2: resume past the EXPRESSION
                ld      ix,p0_skip_comma
                call    p0cb
                jr      z,lsv_cas_flag      ; SAVE"CAS:name",<flag> -> check for ,A
                or      a
                jr      z,ls_cas_ascii_save
                cp      ':'
                jp      nz,fs_syntax        ; D-TAPETAIL: junk after the name is 2
                jr      ls_cas_ascii_save   ; D-CASSAVE: no flag -> ASCII, as ,A does
lsv_cas_flag:
                call    ls_flag_a
                ; FALL THROUGH
; ls_cas_ascii_save -- main's cas_ascii_save: SAVE"CAS:" as an ASCII listing. The
; $EA header block, then the LIST walk through the tape sink (PRDEV 3 ->
; cas_wbyte, 256-byte blocks), then the Ctrl-Z and the pad. D-CASWBRK: a tape SAVE
; in a program leaves the run BEFORE it writes (DIRECTF = 1: a break is `19 in
; 65535`). D-NODISKVERBS: it ENDS the run (CSAVE does not).
ls_cas_ascii_save:
                ld      a,1
                ld      (DIRECTF),a
                xor     a                   ; D-CASFCB: through channel #0's buffer
                ld      ix,p0_cas_bufp_set
                call    p0cb
                ld      ix,p0_cas_write_ea_header
                call    p0cb                ; $EA header block (name in TSV_NAME)
                jp      c,fs_dio            ; D-CASWBRK: Ctrl-STOP -> 19, raised
                ld      a,1
                ld      (PRDEST),a          ; route pchar (LIST's emit) to a sink
                ld      a,3
                ld      (PRDEV),a           ; sink 3 = cassette (cas_wbyte)
                ld      ix,p0_list_all
                call    p0cb
                ld      ix,p0_cas_ascii_finish
                call    p0cb                ; Ctrl-Z EOF + pad the final block (flush)
                xor     a
                ld      (PRDEST),a          ; restore the screen sink
                ld      (PRDEV),a           ; restore the default (disk) device
                jp      ls_end_line

; ls_flag_a -- main's sav_flag_a: the `,A` of SAVE"...",A, disk and tape alike.
; in: HL at the ','. out: HL past the 'A', the end of the statement checked;
; else a TRAPPABLE ERR 2 (D-SAVETAIL), and `SAVE "X.BAS",A:PRINT 1` is legal
; (D-SAVECOLON: end of STATEMENT, not of line).
ls_flag_a:
                rst     $10                 ; past the ','
                ld      ix,p0_upcase
                call    p0cb                ; accept ,a as well
                cp      'A'
                jp      nz,fs_syntax        ; only ,A is supported
                ld      ix,p0_stmt_bare_end
                call    p0cb                ; past the 'A'
                jp      nz,fs_syntax        ; trailing junk after ,A
                ret

; ===========================================================================
; BSAVE <name>,start,end[,exec|,S]   (main's do_bsave)
; ===========================================================================
; The name is a string EXPRESSION; the addresses are expressions, each behind a
; REQUIRED comma (D-SAVETRAP: a missing one is a trappable 2). Disk: the fourth
; slot is `,S` (VRAM) or the exec expression (D-BSAVEVAR), the statement must END
; before the open (no file is written on junk), then disk.rom writes it
; (FOPEN_SEL_BSAVE) through SAVE's tail. Tape: `,exec` only (D-TAPETAIL: S is
; the exec VARIABLE there), then the sub-ROM's tape engine.
ls_bsave:
                inc     hl                  ; past the BSAVE token (main's ex_bsave)
                xor     a
                ld      (VRAM_FLAG),a       ; default RAM source; ",S" sets it below
                call    ls_fname_dev
                jr      z,lbs_cas           ; matched "CAS:" -> tape (HL past the prefix)
                ld      ix,p0_pdfcb_resume
                call    p0cb                ; DISK_FCB; HL -> the tail
                call    ls_comma_eval       ; ,start
                ld      (CURPTR),de         ; the source walk cursor
                ld      (EXECPTR),de        ; default exec = start
                call    ls_comma_eval       ; ,end
                ld      (DSV_END),de        ; the last data byte (inclusive)
                call    ls_opt4             ; A = 0 none / 1 ",S" / 2 exec in DE
                or      a
                jr      z,lbs_open          ; no 4th arg -> exec defaulted to start
                cp      2
                jr      z,lbs_set_exec      ; expression -> exec address
                ld      a,1                 ; ",S" -> stream data from VRAM
                ld      (VRAM_FLAG),a
                jr      lbs_open
lbs_set_exec:
                ld      (EXECPTR),de
lbs_open:
                ld      ix,p0_mxf_require_end
                call    p0cb                ; HL on the 0 / ':'; else ERR 2, no file
                push    hl                  ; the cursor, for lsv_cross's pop
                ld      ix,p0_fch_park
                call    p0cb                ; D-ASAVECHAN: park the live channel
                ld      a,FOPEN_SEL_BSAVE   ; disk.rom's hk_dpbsave
                jp      lsv_cross           ; SAVE's tail: the crossing + decode
lbs_cas:
                call    ls_tape_parse_cut   ; TSV_NAME; a . ends the name (D-CASDOT)
                ld      hl,(FN_RESUME)      ; resume past the EXPRESSION
                call    ls_comma_eval       ; ,start
                ld      (CURPTR),de
                ld      (EXECPTR),de        ; default exec = start
                call    ls_comma_eval       ; ,end
                ld      (TSV_END),de
                call    ls_opt4_cas         ; A = 0 none / 2 exec in DE
                or      a
                jr      z,lbs_cas_open      ; no 4th arg
                ld      (EXECPTR),de
lbs_cas_open:
                ld      a,SV_OP_BSV_CAS     ; BSAVE -> tape
ls_sv_tenant:                               ; main's `jp sv_tenant`: the tape engine,
                ld      ix,p0_sv_tenant     ; which raises 19 on a break and otherwise
                call    p0cb                ; RETURNED FROM THE HANDLER (`ret z`) --
                jp      ls_ret              ; so this statement's continuation is a `ret`

; ls_opt4 -- main's bsave_opt4: the disk BSAVE's 4th slot.
; out: A = 0 none (HL at the terminator) / 1 ",S" (HL past the S) / 2 the exec
; (DE = value, HL past it); or ERR 2 raised. An `S` is ALWAYS the flag: `,SX`
; is 2 on the CF-3300 (D-BSAVEVAR); any other start is the exec expression.
ls_opt4:
                ld      ix,p0_skip_comma
                call    p0cb
                jr      z,lo4_have
lo4_none:
                xor     a                   ; no 4th argument (A=0, CF clear)
                ret
lo4_have:
                rst     $10                 ; past the comma
                ld      ix,p0_upcase
                call    p0cb
                cp      'S'
                jr      nz,lo4_expr         ; anything else starts the exec expression
                ld      ix,p0_stmt_bare_end
                call    p0cb                ; Z iff the statement ends here
                jp      nz,fs_syntax        ; `,SX` / `,S+1`: 2 on the CF-3300
                ld      a,1                 ; A = 1: ",S" flag
                or      a                   ; CF clear
                ret
; ls_opt4_cas -- main's bsave_opt4_cas: the tape BSAVE's 4th slot, ,exec only
ls_opt4_cas:
                ld      ix,p0_skip_comma
                call    p0cb
                jr      nz,lo4_none         ; no 4th argument
                rst     $10                 ; past the comma
lo4_expr:
                ld      ix,p0_eval_addr
                call    p0cb                ; DE = exec, an ADDRESS (D-TAPETAIL)
                ld      ix,p0_check_expr_errors
                call    p0cb                ; a string 13, past 65535 6
                ld      a,2                 ; A = 2: expression
                or      a                   ; CF clear
                ret

; ls_comma_eval -- main's expect_comma_eval: a REQUIRED ',' (ERR 2, raised and
; trappable: D-SAVETRAP), then the expression. DE = value, HL advanced.
ls_comma_eval:
                ld      ix,p0_req_comma
                call    p0cb                ; past the comma, or ERR 2
                ld      ix,p0_eval
                jp      p0cb                ; DE = value, HL advanced

; ===========================================================================
; CSAVE "name"[,speed]   (main's do_csave)
; ===========================================================================
; Tokenised ($D3) to tape, through the sub-ROM's tape engine. The name is NOT
; optional (D-CSAVENAME): bare `CSAVE` / `CSAVE:` are 24, `CSAVE,2` is 2. It is
; a string EXPRESSION (D-CSAVEEXPR) and raw (no dot cut). CSAVE does NOT end the
; run (tapetail's csaveok).
ls_csave:
                inc     hl                  ; past the CSAVE token (main's ex_csave)
                ld      ix,p0_skipsp_test
                call    p0cb
                jr      z,lcs_noname        ; bare CSAVE -> Missing operand
                cp      COLON
                jr      z,lcs_noname        ; `CSAVE:` -> Missing operand
                cp      ','
                jp      z,fs_syntax         ; `CSAVE,2` -> Syntax error (measured)
                ld      ix,p0_fname_expr
                call    p0cb                ; HL -> the staged '"'-terminated copy
                call    ls_tape_parse_name  ; fills TSV_NAME from the staged copy
                ld      hl,(FN_RESUME)      ; resume just past the expression
                call    ls_csav_speed       ; optional ,1/,2 speed; raises 5 / 2 itself
                ld      a,SV_OP_SAV_CAS     ; CSAVE -> tape, tokenised (D-CASSAVE)
                jr      ls_sv_tenant
lcs_noname:
                ld      ix,p0_loc_missing   ; ERR 24
                jp      p0cb

; ls_csav_speed -- main's csav_speed: the optional ,speed of CSAVE. 1 = 1200,
; 2 = 2400 baud: the active LOW word ACT_LOW ($F406) is set to the reference word
; (TAPOON's cas_seed seeds the tables). > 255 or not 1/2 is 5, junk after it 2
; (D-TAPETAIL, VG-8020). In: HL past the name. Out: HL advanced.
ls_csav_speed:
                ld      ix,p0_skipsp_test
                call    p0cb
                ret     z                   ; end of statement -> no speed
                cp      COLON
                ret     z                   ; ':' separator -> no speed
                cp      ','
                jp      nz,fs_syntax        ; junk after the name
                inc     hl                  ; past the comma
                ld      ix,p0_eval
                call    p0cb                ; DE = speed value, HL past it
                ld      a,d
                or      a
                jp      nz,fs_illegal       ; > 255 -> 5
                ld      a,e
                cp      1
                jr      z,lcsp_1200
                cp      2
                jp      nz,fs_illegal       ; only ,1 / ,2: `CSAVE "X",3` is 5
                ld      de,CAS_LOW_2400     ; selected active-LOW word
                jr      lcsp_apply
lcsp_1200:
                ld      de,CAS_LOW_1200
lcsp_apply:
                ld      (ACT_LOW),de        ; active LOW = the selected rate
                ld      ix,p0_skipsp_test
                call    p0cb                ; HL is past the speed
                ret     z                   ; clean end
                cp      COLON
                ret     z
                jp      fs_syntax           ; junk: `CSAVE "X",1,2` is 2

; ===========================================================================
; the shared parse helpers
; ===========================================================================
; ls_fname_dev -- main's fname_dev (D-NGRAM16): the filename EXPRESSION, then
; "is it the tape?". out: Z = "CAS:" (HL past it) -- or no disk ROM at all
; (D-NODISKVERBS; a `d:` name raises 56 there); NZ = the disk (HL restored).
; fname_expr JUMPS OUT on a non-string name, and both of its exits raise, so
; the frame this call adds is discarded with the rest.
ls_fname_dev:
                ld      ix,p0_fname_expr
                call    p0cb                ; HL -> the staged '"'-terminated copy
                ld      de,p0_dev_cas       ; main's data: dev_cmp reads it
                ld      ix,p0_dev_cmp
                call    p0cb                ; Z + HL past the prefix iff it matched
                ret     z                   ; "CAS:" -> the tape arm
                ld      ix,p0_nodisk_dev
                jp      p0cb                ; no disk -> Z (tape), `d:` -> 56, else NZ

; ls_pcr_load -- main's pcr_load: LOAD / RUN's option tail, `,R` or nothing.
; An unknown flag, junk after it and `,S` (BLOAD's option, not LOAD's) are a
; TRAPPABLE 2 (D-LOADTAIL). Out: RUNFLAG (and VRAM_FLAG = 0).
ls_pcr_load:
                call    ls_pcr_noquote
                jp      c,fs_syntax         ; unknown option or junk after it
                ld      a,(VRAM_FLAG)
                or      a
                jp      nz,fs_syntax        ; ,S
                ret
; ls_pcr_noquote -- main's pcr_noquote: one optional flag, ,R or ,S, then only a
; terminator. in: HL past the name (FN_RESUME). out: CF on any error; else CF
; clear, RUNFLAG = 1 iff ,R, VRAM_FLAG = 1 iff ,S.
ls_pcr_noquote:
                xor     a
                ld      (RUNFLAG),a         ; default: no ,R handoff
                ld      (VRAM_FLAG),a       ; default: RAM load
                ld      ix,p0_skipsp_test
                call    p0cb
                jr      z,lpn_ok            ; end of statement -> plain load
                cp      COLON
                jr      z,lpn_ok            ; statement separator -> plain load
                cp      ','
                jr      nz,lpn_err          ; junk after the name -> error
                rst     $10                 ; past the comma
                ld      ix,p0_upcase
                call    p0cb                ; accept ,r / ,s as well
                cp      'R'
                jr      z,lpn_run
                cp      'S'
                jr      z,lpn_vram
                jr      lpn_err             ; unrecognized flag -> error
lpn_run:
                ld      a,1
                ld      (RUNFLAG),a
                jr      lpn_flag_end
lpn_vram:
                ld      a,1
                ld      (VRAM_FLAG),a
lpn_flag_end:
                ld      ix,p0_stmt_bare_end
                call    p0cb                ; past the letter; Z iff the end
                jr      z,lpn_ok
lpn_err:
                scf
                ret
lpn_ok:
                or      a                   ; CF clear = success
                ret

; ls_pcr_bload -- main's pcr_bload: BLOAD's tail `[,R|,S][,offset]` (D-BLOADOFS),
; parsed BEFORE the disk is touched. The offset is an ADDRESS (-32768..65535,
; wrapping; a string 13, 70000 6), added to start, end and exec by the tenant.
; Out: RUNFLAG, VRAM_FLAG, BL_OFS, FN_RESUME (past the tail, for load_handoff).
ls_pcr_bload:
                ld      hl,0
                ld      (BL_OFS),hl         ; no offset
                ld      hl,(FN_RESUME)
                xor     a
                ld      (RUNFLAG),a
                ld      (VRAM_FLAG),a
                ld      ix,p0_skipsp_test
                call    p0cb
                jr      z,lpb_done          ; `BLOAD "f"`
                cp      COLON
                jr      z,lpb_done
                cp      ','
                jp      nz,fs_syntax
                rst     $10                 ; past the comma
                ld      ix,p0_upcase
                call    p0cb
                ld      de,RUNFLAG
                cp      'R'
                jr      z,lpb_flag
                ld      de,VRAM_FLAG
                cp      'S'
                jr      nz,lpb_ofs          ; not a flag: the offset itself
lpb_flag:
                ld      a,1
                ld      (de),a
                ld      ix,p0_stmt_bare_end
                call    p0cb                ; past the letter; Z iff the end
                jr      z,lpb_done
                cp      ','
                jp      nz,fs_syntax
                inc     hl                  ; past the comma
lpb_ofs:
                ld      ix,p0_eval_addr
                call    p0cb                ; DE = the offset, wrapped to 16 bits
                ld      ix,p0_check_expr_errors
                call    p0cb                ; a string 13, past 65535 6
                ld      (BL_OFS),de
                ld      ix,p0_skipsp_test
                call    p0cb
                jr      z,lpb_done
                cp      COLON
                jp      nz,fs_syntax
lpb_done:
                ld      (FN_RESUME),hl
                ret

; ls_tape_parse_cut -- main's tape_parse_cut (SAVE"CAS:" / BSAVE"CAS:"):
; ls_tape_parse_name, then main's cas_name_cut (TSV_NAME is CAS_WANT, D-TSVOVL:
; a '.' and what follows become spaces; a '.' first is 56). CSAVE's name is raw
; and calls ls_tape_parse_name alone.
ls_tape_parse_cut:
                call    ls_tape_parse_name
                ld      ix,p0_cas_name_cut
                jp      p0cb
; ls_tape_parse_name -- main's tape_parse_name: up to 6 name chars to TSV_NAME,
; space-padded. in: HL at the first char of the STAGED copy (RAM, '"'-ended).
; out: HL on the closing '"' (or a NUL). Clobbers A, B, DE. A RAM-only leaf.
ls_tape_parse_name:
                ld      de,TSV_NAME
                ld      b,6
ltpn_loop:
                ld      a,(hl)
                or      a
                jr      z,ltpn_pad          ; end of line -> pad remaining
                cp      '"'
                jr      z,ltpn_pad          ; closing quote -> pad remaining
                ld      (de),a
                inc     hl
                inc     de
                djnz    ltpn_loop
ltpn_skip:                                  ; 6 chars consumed: skip to the '"'
                ld      a,(hl)
                or      a
                ret     z                   ; unterminated string -> stop
                cp      '"'
                ret     z                   ; closing quote found
                inc     hl
                jr      ltpn_skip
ltpn_pad:                                   ; HL on '"' or NUL: pad with ' '
                ld      a,b
                or      a
                ret     z                   ; nothing to pad
ltpn_fill:
                ld      a,' '
                ld      (de),a
                inc     de
                djnz    ltpn_fill
                ret
