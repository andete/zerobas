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
bl_skip_spaces  equ     skip_spaces
bl_upcase       equ     upcase
bl_load_error   equ     load_error

; --- do_bload: resident marshalling stub (repack build) ---------------------
; The whole verb body (do_bload..disk_load_fin) moved to sub/bload.asm, a PAGE-1
; tenant co-resident with fatprim (docs/spec-traps-t3-key.md §7.6). Marshal the
; one input (HL = token cursor) and the one output (BL_STAT) through RAM:
; subrom_call clobbers every register and forces CF=0 on return.
;
; The `,R` handoff CANNOT move: it ends in `jp (hl)` into the loaded program and
; never returns, so running it inside the tenant's CALSLT would leave main page 1
; switched out forever. The tenant returns normally and we do the handoff here.
do_bload:
                ld      (BL_PTR),hl         ; token cursor -> tenant
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_BLOAD
                call    subrom_call
                jp      c,subrom_absent_error
                ld      a,(BL_STAT)
                or      a
                jp      nz,load_error       ; the tenant hit load_error; report once here
                jp      load_handoff        ; plain BLOAD returns; ,R jumps to EXECPTR

; parse_disk_fcb stays RESIDENT even though the verb around it left: nine callers
; outside bload.asm use it (do_files, do_kill, do_name, do_open, do_run, ex_merge,
; bsv_is_disk, sav_is_disk, dl_is_disk). The tenant gets its own copy via
; bload-body.inc; a sub-ROM duplicate costs no main page-1 bytes.
                include "basic/pdfcb-body.inc"

; load_handoff — shared ,R exec handoff, RESIDENT in both builds (see above).
load_handoff:
                ld      a,(RUNFLAG)
                or      a
                ret     z                   ; plain BLOAD: return to caller
                ld      hl,(EXECPTR)
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
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FCBNAME
                call    subrom_call
                jp      c,subrom_absent_error
                ld      hl,(BN_PTR)         ; tenant wrote back the advanced ptr
                ld      a,(BN_STAT)
                rra                         ; BN_STAT bit0 -> CF (1 = reject)
                ret

; parse_close_run — shared tail parse used by BOTH the tape and disk paths.
; Consumes the closing '"' and an optional single option flag (,R run or ,S
; VRAM); sets RUNFLAG / VRAM_FLAG accordingly.
;   in:  HL -> the closing '"' of the device string
;   out: CF set on ANY syntax error (missing quote, unrecognized flag, or junk
;        after the flag — caller -> load_error); CF clear on success, with
;        RUNFLAG = 1 iff ,R and VRAM_FLAG = 1 iff ,S.
; "Honest at the walls" (closure-spec item 2): an unrecognized flag or a trailing
; token (a second flag, or the deferred ,offset — Q1.2/Q1.4) is a clean error,
; never a silent no-op. Only ONE option flag is allowed, so ,R and ,S cannot
; combine.
parse_close_run:
                ld      a,(hl)
                cp      '"'                 ; closing quote required
                jr      nz,pcr_err
                inc     hl
                xor     a
                ld      (RUNFLAG),a         ; default: no ,R handoff
                ld      (VRAM_FLAG),a       ; default: RAM load
                call    skip_spaces
                ld      a,(hl)
                or      a
                jr      z,pcr_ok            ; end of statement -> plain load
                cp      COLON
                jr      z,pcr_ok            ; statement separator -> plain load
                cp      ','
                jr      nz,pcr_err          ; junk after the quote -> error
                ; --- one option flag: ,R (run) or ,S (VRAM) ----------------
                inc     hl                  ; past the comma
                call    skip_spaces
                ld      a,(hl)
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
                inc     hl                  ; past the flag letter
                call    skip_spaces
                ld      a,(hl)
                or      a
                jr      z,pcr_ok
                cp      COLON
                jr      z,pcr_ok
                ; fall through to pcr_err
pcr_err:
                scf
                ret
pcr_ok:
                or      a                   ; CF clear = success
                ret

; device name accepted by this build. Source: spec-bload-r.md §5 ("CAS:").
dev_cas:
                db      "CAS:",0

; --- error path: stop the tape, drop a marker, report, return to the prompt -
; Reached when a cassette BIOS call fails (CF set), the file is not binary, or
; the arguments do not parse. Under bare C-BIOS this fires immediately: its
; TAPION/TAPIN are stubs that always set CF (observable as $EE at ERRMARK).
load_error:
                call    TAPIOF
                ld      a,$EE
                ld      (ERRMARK),a
                ld      hl,err_io
                call    print_msg                   ; D-MSGENC
                ret
err_io:
                db      "load",MSGESC_ERROR,0       ; 13 B -> 6 B
