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
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_BLOAD
                call    sc_call             ; D-SCCALL: tenant call + absent raise
                ; D-BLNF: BL_STAT is now THREE-VALUED, and the third value is why
                ; BLOAD could not be fixed by D-LOADERR-FIX's DISKOP_OP test. The
                ; tenant calls the REAL sub-side fat_find as a plain in-page call,
                ; so nothing writes DISKOP_OP and df_or_loaderr (basic/files.asm)
                ; is blind to this verb. The tenant tells the two apart at its own
                ; mount/find boundary instead and files WHICH it was.
                ;   0 -> loaded
                ;   1 -> `load error`, PRINTED, program runs on
                ;   n -> RAISE MSX ERR n, program stops
                ; 🎯 D-BLMODE MADE THE THIRD VALUE A **CODE** RATHER THAN ADDING A
                ; FOURTH INDEX, and that is the whole main-side cost of the new face:
                ; `cp 1` for `dec a` is one byte, and `jp raise_error` costs the same
                ; three `jp df_notfound` did, because A is already the code the
                ; tenant filed. A fourth enumerated value would have been six.
                ; 53 = `File not found` (D-BLNF), 61 = `Bad file mode` (D-BLMODE).
                ; ⚠️ 1 STILL COVERS THE CASSETTE, the parse rejects and a failed
                ; mount. Only an arm that PROVED the volume mounted files a code.
                ; ⚠️ AND SO BLOAD CANNOT RAISE ERR 1 THROUGH THIS CELL -- see
                ; sub/bload.asm, where the hazard is written down beside the arms.
                ld      a,(BL_STAT)
                or      a
                jr      z,load_handoff      ; plain BLOAD returns; ,R jumps to EXECPTR
                cp      1
                jp      z,disk_error        ; the tenant hit load_error: ERR 70 on an empty drive
                                            ; (D-DISKERR), else `load error` -- the tape path has
                                            ; no DSKIO and keeps its face
                jp      raise_error         ; A = the tenant's ERR code — never returns

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
                call    sc_call             ; D-SCCALL: tenant call + absent raise
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
; token (a second flag, or the deferred ,offset — Q1.2/Q1.4) is a clean error,
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
                jp      print_msg                   ; D-MSGENC
err_io:
                db      "load",MSGESC_ERROR,0       ; 13 B -> 6 B
