; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; bload.asm — the BLOAD statement handler.
;
; This is the *interpreter half* of BLOAD: it does NOT decode the cassette
; signal itself (that is the BIOS "device half" — TAPION/TAPIN). It parses its
; arguments from the crunched token stream, drives the documented cassette BIOS
; contract to read a BSAVE-format binary, places the bytes in RAM, and (for ,R)
; performs the handoff by jumping to the exec address.
;
; Derived only from basic-spec/docs/spec-bload-r.md and spec-tokenise.md (this
; project's own black-box oracle observations) + the MSX2 Technical Handbook.
; No disassembly.
;
; Entry: do_bload, HL -> the bytes after the BLOAD token. spec-tokenise.md: the
; arguments are kept verbatim as ASCII, i.e. `"CAS:",R` followed by 0x00.
;
; Device-string grammar (this build):
;   "CAS:"            -> tape path (verbatim, unchanged from the original)
;   "A:name"/"B:name" -> disk path, explicit drive letter (case-insensitive)
;   "name"            -> disk path, defaults to drive A
; A disk filename needs NO new token: BLOAD arguments are kept verbatim ASCII in
; the crunch stream (spec-tokenise.md), so the tokeniser is untouched.

; The shared bodies (bload-body.inc, pdfcb-body.inc) call the interpreter's
; helpers under bl_-prefixed names so each side can bind them: resident these are
; zero-byte EQUs onto the real routines;
; in the tenant they bind to page-1-local clones (sub/bload.asm).
bl_upcase       equ     upcase
bl_load_error   equ     load_error

; --- do_bload: resident marshalling stub (repack build) ---------------------
; The verb body (device dispatch, the 8.3 name, the cassette load) is the sub-ROM
; PAGE-1 tenant sub/bload.asm (docs/spec-traps-t3-key.md §7.6). Marshal the one
; input (HL = token cursor) and the one output (BL_STAT) through RAM:
; subrom_call clobbers every register and forces CF=0 on return.
; 🏗️ D-ROMSIZE step 1 (2026-10-19): THE DISK LOAD IS disk.rom's (hk_dpbload),
; through H_FOPEN -- the cell the CF-3300's BLOAD enters, once, like LOAD / MERGE
; (disk/docs/spec-diskcode-eviction.md §6.6ab / §6.6v / §8.2: DE = 1, HL = the
; program-verb buffer; never $FE76, no per-byte cell). The tenant still decides
; the device and parses the name into DISK_FCB_NAME; for a disk file it answers
; BL_STAT = FOPEN_SEL_BLOAD and main makes the crossing. Until this date the
; tenant read the file itself, over the sub-ROM's second FAT engine (its READ
; half and a fatio-body copy, the last users of either -- both gone).
;
; The `,R` handoff CANNOT move: it ends in `jp (hl)` into the loaded program and
; never returns, so running it inside the tenant's CALSLT would leave main page 1
; switched out forever. The tenant returns normally and we do the handoff here.
do_bload:
                ; ✅ D-FNEXPR2: THE FILENAME IS EVALUATED **HERE**, NOT IN THE
                ; TENANT, AND THAT IS FORCED RATHER THAN CHOSEN. `str_eval` is
                ; main PAGE 1, which is switched OUT while a page-1 sub-ROM
                ; tenant runs -- the same constraint this file's header already
                ; states for the rest of the parse ("every one of these verbs
                ; PARSES with eval, which is main page 1 and therefore switched
                ; out"). So the one thing BLOAD's parse still did sub-side, the
                ; opening quote gate, comes back to the resident half; what
                ; crosses is the STAGED name in STRSCR (RAM, mapped on both
                ; sides) plus FN_RESUME for the `,R` tail.
                ; 🎯 AND IT COSTS THE TENANT NOTHING TO GIVE UP: the 9 B gate it
                ; drops pays for the two `ld hl,(FN_RESUME)` its arms gain.
                call    fname_expr          ; HL -> the staged '"'-terminated copy
                ld      (BL_PTR),hl         ; staged name ptr -> tenant
                call    pcr_bload           ; D-BLOADOFS: the whole tail, HERE
                call    fch_park            ; D-ASAVECHAN2 (2026-10-03): park the live
                                            ; channel -- the tenant's disk read reused its
                                            ; engine globals, and an open INPUT file lost
                                            ; its place, an OUTPUT one its bytes
                                            ; (scratchpad/chanside_probe.py). Kept when
                                            ; the read moved to disk.rom (2026-10-19),
                                            ; as BSAVE kept it: FCH_ACTIVE = 0 after a
                                            ; BLOAD is what every measured row saw
                xor     a                   ; D-CASFCB: a tape BLOAD's search skips
                call    cas_bufp_set        ;  other files through channel #0's buffer
                                            ;  -- the tenant calls the SUB-side
                                            ;  cas_open_match, never main's stub, so
                                            ;  it is set here (casbin bty / bbare
                                            ;  read PEEK 0 without it)
                call    sc_inl1             ; D-STUBINL: D-SCCALL: tenant call + absent raise
                db      low (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_BLOAD)
                ; D-BLNF: BL_STAT is THREE-VALUED -- and since 2026-10-19 the
                ; disk load answers in the SAME code through DISKOP_STATUS:
                ;   0 -> loaded
                ;   1 -> `load error`, PRINTED, program runs on -- unless a DSKIO
                ;        failure is pending, which disk_error RAISES (70, ...)
                ;   n -> RAISE MSX ERR n, program stops
                ; 🎯 D-BLMODE MADE THE THIRD VALUE A **CODE** RATHER THAN ADDING A
                ; FOURTH INDEX: `cp 1` for `dec a` is one byte, and `jp raise_error`
                ; costs the same three `jp df_notfound` did, because A is already
                ; the code. 53 = `File not found` (D-BLNF), 61 = `Bad file mode`
                ; (D-BLMODE) -- both disk.rom's now; the tenant files 19 (tape
                ; I/O, D-CASBIN), 56 / 62 (a bad name or drive) and 1.
                ; ⚠️ 1 COVERS THE CASSETTE, a failed mount and a short file. Only
                ; an arm that PROVED the volume mounted files 53 / 61.
                ; ⚠️ AND SO BLOAD CANNOT RAISE ERR 1 THROUGH THIS CELL -- see
                ; sub/bload.asm, where the hazard is written down beside the arms.
                ; 🏗️ 2026-10-19: FOPEN_SEL_BLOAD ($5A, not an MSX error code, so
                ; never one the tenant files) means "a DISK file, its name is in
                ; DISK_FCB_NAME": the selector is ALREADY in A for fopen_cross,
                ; which crosses H_FOPEN to disk.rom's hk_dpbload and comes back
                ; with A = DISKOP_STATUS in this same code -- 5 B of main page 1
                ; for the whole move. Unclaimed (a foreign disk ROM): ERR 5, as
                ; LOAD / SAVE / BSAVE answer there.
                ld      a,(BL_STAT)
                cp      FOPEN_SEL_BLOAD
                call    z,fopen_cross       ; disk.rom loads it; A = its status
                or      a
                jr      z,load_handoff      ; plain BLOAD returns; ,R jumps to EXECPTR
                cp      1
                jp      z,disk_error        ; a load error: ERR 70 on an empty drive (D-DISKERR,
                                            ; disk.rom's mount), else `load error` -- the tape
                                            ; path has no DSKIO and keeps its face
                jp      raise_error         ; A = the tenant's ERR code — never returns

; parse_disk_fcb stays RESIDENT even though the verb around it left: nine callers
; outside bload.asm use it (do_files, do_kill, do_name, do_open, do_run, ex_merge,
; bsv_is_disk, sav_is_disk, dl_is_disk). The tenant gets its own copy via
; bload-body.inc; a sub-ROM duplicate costs no main page-1 bytes.
                include "basic/pdfcb-body.inc"

; load_handoff — shared ,R exec handoff, RESIDENT in both builds (see above).
load_handoff:
                ; D-SAVECOLON: `ret z` ended the LINE, so `BLOAD "Y.BIN":PRINT 1`
                ; never printed (the CF-3300 does; scratchpad/colon_probe.py). The
                ; tenant parses the `,R`/`,S` tail and now leaves the cursor past it
                ; in FN_RESUME (sub/bload.asm pcr_ok); plain BLOAD continues there.
                ; D-BLOADRTAIL (2026-10-14): `,R` CALLS the program, and when it
                ; returns the rest of the line runs -- `BLOAD"CAS:T",R:PRINT"[OK]"`
                ; prints [OK] on the VG-8020, direct and in a program, whatever
                ; the code does to HL/DE/BC. This was `jp (hl)`: the program's `ret`
                ; went back past the statement, so the line (and in a program, the
                ; RUN) ended silently -- tape loaders of the shape `BLOAD"CAS:",R`
                ; then more BASIC stopped at the prompt after `Found:`. The cursor
                ; rides the STACK across the call, not FN_RESUME: the loaded code
                ; is free to use RAM that is ours (workspace) but free on the
                ; reference.
                ld      hl,(FN_RESUME)
                push    hl                  ; the statement cursor, kept on the stack
                ld      hl,(EXECPTR)
                ld      a,(RUNFLAG)
                or      a
                call    nz,lh_runr          ; ,R: run it; it RETURNS here (D-VARTABADOPT:
                                            ; lh_runr syncs VARTAB first, basic/missing.asm)
lh_back:                                    ; D-BASICINT: $6CF3's target -- a game that
                                            ; pops our return and jumps there lands here
                                            ; with the cursor on top, as after a `ret`
                pop     hl
                jp      lh_adopt            ; the rest of the line runs, ,R or not --
                                            ; after adopting a VARTAB the code moved
lh_jphl:
                jp      (hl)

; build_83_name — convert the filename at HL into the 11-byte 8.3 field at
; DISK_FCB_NAME. EVICTED to a sub-ROM PAGE-1 tenant (SUBROM_IDX_FCBNAME) in the
; repack build to free page-1 space for the interrupt-traps T1 slice (docs/spec-
; basic-interrupt-traps.md §10.4, D-T-8c/D-T-8d). The body is shared
; byte-identically via basic/fcbname-body.inc, which is now included from the
; ONE home (sub-ROM-resident in the tenant); until 2026-07-29 an `ELSE` branch
; also inlined it here for the byte-frozen lean 16 KB cart. The casmatch /
; cas_open_match precedent.
; --- build_83_name: resident marshalling shim (repack build) ----------------
; The body (build_83_name..bn_star_fill, basic/fcbname-body.inc) moved whole to
; sub/fcbname.asm (SUBROM_IDX_FCBNAME, a page-1 tenant). Marshal the one register
; input (HL = source ptr) and the two outputs (HL advanced -> closing quote, CF =
; reject) through RAM: subrom_call clobbers every register and forces CF=0 on
; return, so neither HL nor CF can ride back directly (the fatprim/casmatch
; pattern). BN_PTR carries the pointer both ways; BN_STAT carries CF back.
;   in:  HL -> first filename char.  out: HL -> closing '"', CF = reject.
build_83_name:
                ld      (BN_PTR),hl         ; source ptr -> tenant
                call    sc_inl1             ; D-STUBINL: D-SCCALL: tenant call + absent raise
                db      low (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FCBNAME)
                ld      hl,(BN_PTR)         ; tenant wrote back the advanced ptr
                ld      a,(BN_STAT)
                rra                         ; BN_STAT bit0 -> CF (1 = reject)
                ret

; pcr_noquote — shared option-flag tail used by BOTH the tape and disk paths.
; Parses an optional single option flag (,R run or ,S VRAM); sets RUNFLAG /
; VRAM_FLAG accordingly.
;   in:  HL -> the statement tail, past the filename (FN_RESUME)
;   out: CF set on ANY syntax error (unrecognized flag, or junk
;        after the flag — caller -> load_error); CF clear on success, with
;        RUNFLAG = 1 iff ,R and VRAM_FLAG = 1 iff ,S.
;
; 🔴 THE `parse_close_run` HEAD IS GONE FROM THIS COPY TOO (D-FNRUN), AND THE
; DEAD-CODE GATE DID NOT ASK FOR IT. Four instructions consumed a closing '"'
; out of program text; D-FNEXPR2 retired three of their four callers and
; `do_run` was the fourth, so once RUN took a string EXPRESSION the head had no
; caller in EITHER build. The sub-ROM copy was reported as a 6 B unreachable
; span the moment it went dead. This one was not — and the reason is worth more
; than the six bytes:
;
;   `check_dead_code.py` seeds the MAIN build with `{init} | (labels named
;   anywhere under sub/ or tools/)`, and `external_names()` scrapes every
;   IDENTIFIER in those trees including the ones inside COMMENTS.
;
; So the three mentions of `parse_close_run` in sub/bload.asm's own comment --
; the comment D-FNEXPR2 wrote to explain why the head was removed THERE -- were
; seeding the label here. **Documenting a removal is what stopped the gate
; asking for the same removal in the other build.** Falsified rather than
; reasoned about: mangling those three mentions drops the seed count 304 -> 303
; and the span is reported immediately. Filed in TODO.md as a gate residual,
; because the mechanism is general and this is one instance of it.
; "Honest at the walls" (closure-spec item 2): an unrecognized flag or a trailing
; token (a second flag, or an argument) is a clean error -- LOAD / RUN's tail;
; BLOAD's, which takes an `,offset`, is pcr_bload below (D-BLOADOFS) --
; never a silent no-op. Only ONE option flag is allowed, so ,R and ,S cannot
; combine.
pcr_noquote:
                xor     a
                ld      (RUNFLAG),a         ; default: no ,R handoff
                ld      (VRAM_FLAG),a       ; default: RAM load
                call    skipsp_test
                jr      z,pcr_ok            ; end of statement -> plain load
                cp      COLON
                jr      z,pcr_ok            ; statement separator -> plain load
                cp      ','
                jr      nz,pcr_err          ; junk after the quote -> error
                ; --- one option flag: ,R (run) or ,S (VRAM) ----------------
                rst    $10                ; past the comma
                call    upcase              ; accept ,r / ,s as well
                cp      'R'
                jr      z,pcr_run
                cp      'S'
                jr      z,pcr_vram
                jr      pcr_err             ; unrecognized flag -> error
pcr_run:
                ld      a,1
                ld      (RUNFLAG),a
                jr      pcr_flag_end
pcr_vram:
                ld      a,1
                ld      (VRAM_FLAG),a
pcr_flag_end:
                ; after the flag ONLY a statement terminator is allowed; a second
                ; flag or a trailing ,offset is rejected (not silently ignored).
                call    stmt_bare_end       ; D-BAREEND: Z iff the statement ends here
                jr      z,pcr_ok
                ; fall through to pcr_err
pcr_err:
                scf
                ret
pcr_ok:
                or      a                   ; CF clear = success
                ret

; --- pcr_bload: BLOAD's tail `[,R|,S][,offset]`, parsed in MAIN -------------
; ✅ D-BLOADOFS (2026-10-07). The offset is the documented fourth form, and the
; CF-3300 (probes/disk/disk_probe_bloadofs.py) adds it to the header's start,
; END and EXEC alike (`,R,&H1000` runs the code at exec+&H1000), wrapping at 16
; bits; it is an ADDRESS (-32768..65535: decimal 61440 is &HF000), a string is
; 13 and 70000 is 6. Parsed HERE rather than in the tenant because `eval` is
; main page 1, switched out while a page-1 tenant runs (the SAVE family's
; reason), and BEFORE the disk is touched: a bad tail never opens the file.
; Out: RUNFLAG, VRAM_FLAG, BL_OFS, FN_RESUME (past the tail, for load_handoff).
pcr_bload:
                ld      hl,0
                ld      (BL_OFS),hl         ; no offset
                ld      hl,(FN_RESUME)
                xor     a
                ld      (RUNFLAG),a
                ld      (VRAM_FLAG),a
                call    skipsp_test
                jr      z,pcb_done          ; `BLOAD "f"`
                cp      COLON
                jr      z,pcb_done
                cp      ','
                jp      nz,stmt_error
                rst     $10                 ; past the comma
                call    upcase
                ld      de,RUNFLAG
                cp      'R'
                jr      z,pcb_flag
                ld      de,VRAM_FLAG
                cp      'S'
                jr      nz,pcb_ofs          ; not a flag: the offset itself
pcb_flag:
                ld      a,1
                ld      (de),a
                call    stmt_bare_end       ; past the letter; Z iff the end
                jr      z,pcb_done
                cp      ','
                jp      nz,stmt_error
                inc     hl                  ; past the comma
pcb_ofs:
                call    eval_addr           ; DE = the offset, wrapped to 16 bits
                call    check_expr_errors   ; a string 13, past 65535 6
                ld      (BL_OFS),de
                call    skipsp_test
                jr      z,pcb_done
                cp      COLON
                jp      nz,stmt_error
pcb_done:
                ld      (FN_RESUME),hl
                ret

; --- pcr_load: LOAD / RUN's option tail -- pcr_noquote, then a TRAPPABLE 2 ---
; ✅ D-LOADTAIL (2026-10-07): `LOAD "X.BAS",Q`, `RUN "A",5` and the cassette
; faces read `2 in 30` under ON ERROR on the CF-3300 / VG-8020; ours took the
; parse failure to load_error, which PRINTS AND RETURNS (D-LOADERRRET), so the
; program ran on. `,S` is BLOAD's option, not LOAD's: `LOAD "X.BAS",S` is 2 on
; the CF-3300 where ours accepted it and searched the disk (53)
; (probes/disk/disk_probe_loadtail.py). The four LOAD / RUN sites call this.
pcr_load:
                call    pcr_noquote
                jp      c,stmt_error        ; unknown option or junk after it
                ld      a,(VRAM_FLAG)
                or      a
                jp      nz,stmt_error       ; ,S
                ret

; (dev_cas, the "CAS:" device name, moved past the $73E5 pin on 2026-10-19 --
; basic/field.asm, after lrset_rhs: its 5 B pay for do_bload's FOPEN_SEL_BLOAD
; crossing above, so nothing in front of $6CF3 changes size.)

; --- error path: stop the tape, drop a marker, report, return to the prompt -
; Reached when a cassette BIOS call fails (CF set), the file is not binary, or
; the arguments do not parse. Under bare C-BIOS this fires immediately: its
; TAPION/TAPIN are stubs that always set CF (observable as $EE at ERRMARK).
load_error:
                call    TAPIOF
                ld      a,$EE
                ld      (ERRMARK),a
                ld      hl,err_io
                jp      print_msg                   ; D-MSGENC
err_io:
                db      "load error",0
