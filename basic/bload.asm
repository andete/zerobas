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
; Entry: ls_bload (sub2/loadsave.asm since D-P0CB slice C2 -- the statement's
; parse left main; bload_sub and load_handoff below are what it calls back and
; continues at), HL -> the BLOAD token. spec-tokenise.md: the arguments are kept
; verbatim as ASCII, i.e. `"CAS:",R` followed by 0x00.
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

; --- do_bload: MOVED to sub2/loadsave.asm (ls_bload), D-P0CB slice C2 -------
; The parse -- the filename expression and the whole `,R` / `,S` / offset tail
; (main's pcr_bload, D-BLOADOFS) -- and the decision on the tenant's BL_STAT run
; in zerobas-sub2 page 0 since 2026-10-21, calling main back through p0cb. What
; stays here: this wrapper, because the sub-ROM BLOAD tenant (sub/bload.asm) is
; reached through an INLINE byte that a p0cb'd caller cannot hand over (IX is
; p0cb's target); bload_cont, the CONTINUATION ls_bload returns in DE since
; D-BLOADSTK (2026-10-23) -- the LOAD itself, D-ROMSIZE step 1's disk crossing
; (FOPEN_SEL_BLOAD -> fopen_cross -> disk.rom hk_dpbload) and the status decision
; run here, off sub2's CALSLT; and load_handoff, where bload_cont goes on -- the
; `,R` call into the loaded program must not run inside sub2's CALSLT either, and
; the pinned $6CF3 lands on its lh_back. The history of each step (D-FNEXPR2, D-ASAVECHAN2, D-CASFCB,
; D-BLNF, D-BLMODE) is in this file's history before the slice.
;   out: BL_STAT (0 loaded / 1 load error / FOPEN_SEL_BLOAD a disk file / n ERR n)
bload_sub:
                call    sc_inl1             ; D-STUBINL: D-SCCALL: tenant call + absent raise
                db      low (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_BLOAD)
                ret

; bload_cont -- ls_bload's CONTINUATION (D-BLOADSTK, 2026-10-23): the load and the
; decision on its status, in main, once sub2's frame is off the stack. Run from the
; tenant, a tape load went ~26 B deeper than the VG-8020's (SP $F072 against $F08C)
; into RAM a no-CLEAR loader may fill. BL_STAT: 0 loaded -> load_handoff; 1 ->
; disk_error (printed); FOPEN_SEL_BLOAD -> disk.rom loads it first; n -> ERR n.
bload_cont:
                call    bload_sub           ; the sub-ROM BLOAD tenant (+ absent raise)
                ld      a,(BL_STAT)
                cp      FOPEN_SEL_BLOAD     ; a DISK file: its name is in DISK_FCB_NAME
                jr      nz,blc_stat
                call    fopen_cross         ; disk.rom loads it; A = its status
blc_stat:
                or      a
                jp      z,load_handoff      ; plain BLOAD returns; ,R calls EXECPTR
                cp      1
                jp      z,disk_error        ; a load error: printed (a continuation)
                jp      raise_error         ; A = the tenant's ERR code

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

; pcr_noquote / pcr_load (LOAD / RUN's `,R` tail, D-LOADTAIL) and pcr_bload
; (BLOAD's `[,R|,S][,offset]`, D-BLOADOFS): MOVED to sub2/loadsave.asm
; (ls_pcr_noquote, ls_pcr_load, ls_pcr_bload), D-P0CB slice C2 -- their only
; callers were the LOAD / RUN <name> / BLOAD arms that moved with them.

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
