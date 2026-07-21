; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — lineedit.asm  (numbered-line editor TXTTAB-memmove tenant)
; ===========================================================================
; store_line's insert/delete body (prog_find_del/delete_at/open_gap/the
; token-body copy) + the relink loop, evicted from the repack main ROM's
; basic/program.asm into sub-ROM PAGE 1 (docs/spec-eviction-g4-space.md §4,
; carve #2 of the G4-space eviction slice). dispatch_line/store_line's own
; parse head stays MAIN-RESIDENT and already marshals its two inputs into RAM
; before this carve even existed (SL_NUM = target line number, SL_TOK = the
; crunched token-body pointer, basic/sysvars.inc) -- nothing new to marshal.
; The tenant reports back only an OOM status byte (LE_STATUS); the resident
; store_line head does the existing `ld a,7 / jp raise_error` (raise_error is
; main PAGE-1 resident, unreachable from here) -- the exact head/body split
; docs/spec-eviction-g4-space.md §4 calls for.
;
; ONE index, SELECTOR-DISPATCHED (LE_OP, aliased onto the SAME DISKOP_OP/
; DISKOP_STATUS cells fatprim/dirverb/audio already share -- one subrom_call
; reaches exactly one tenant, so the separate value namespaces never
; collide): LE_OP_STORE (0) processes SL_NUM/SL_TOK exactly like the
; original store_line (empty body -> delete; else bounds-check + insert),
; LE_OP_RELINK (1) just runs the relink loop -- reached by the RESIDENT
; `relink:` shim (basic/program.asm) for cload.asm's own 2 plain `call
; relink` sites, which still need a working resident label since the loop
; itself no longer lives there.
;
; WHY vars_reset IS NOT A STRADDLE. relink's own tail (repack) calls
; vars_reset (arrays slice-1/4b's scalar-region re-anchor + arrays-slice-4c's
; string-heap reset, basic/arrays.asm) to invalidate live scalars/arrays on
; every program edit. vars_reset is assembled in the main-ROM PAGE-0 LOW
; REGION (< $4000, e.g. $3D92 -- confirmed via build/basic-reloc.sym), NOT
; page 1: while a page-1 tenant runs, only main PAGE 1 is switched out (the
; BIOS + our own low region stay mapped, sub/sub.asm's own header, "PAGE 1 --
; the BIOS is visible but main BASIC is switched out"), so an ordinary
; in-slot `call vars_reset` from HERE reaches it directly, no subrom_call/
; CALSLT bounce needed. It is added to the resident-ABI import list
; (sub/basic-resident-abi.inc, tools/gen_resident_abi.py REQUIRED) purely so
; a future page-0-low shift can never leave this tenant calling a stale
; address (the same staleness guard fp_sqrt's 9 symbols already get) --
; NOT because it needs subrom_call marshalling. tools/check_tenant_
; closure.py's --page1 walk (a page-1 tenant's callee must be sub-local page
; 1 or < $4000) confirms this is closure-clean.
;
; skip_to_eol + tok_skip (+ tsk1/tsk2/tsk4/tsk8/tsk_str/tsk_rem/tsk_data) are
; DUPLICATED sub-locally, verbatim from basic/interp.asm: skip_to_eol itself
; calls tok_skip (a token-aware skip, needed so a stored line's own operand
; bytes -- e.g. a float literal's $00 mantissa byte -- are never mistaken for
; the line/statement terminator), and tok_skip is a pure leaf (reads only the
; tokenised program-text bytes at HL, calls nothing else) -- safe to
; duplicate, no straddle. (Bigger than the spec's own "~10 B" estimate, which
; only accounted for skip_to_eol itself and missed its tok_skip dependency;
; flagged here rather than silently eating the difference out of the G4
; budget.)
;
; CLEAN-ROOM: original code, extracted verbatim from our own basic/program.asm
; (basic/lineedit-body.inc / basic/interp.asm -- see those files' headers for
; the full line-link-format / token-stream provenance: MSX2 Technical
; Handbook Table 2.20 / Figure 2.12 for the control-flow token set, the
; line-link layout + text base allowed-source/oracle-confirmed). The
; dispatch/marshalling glue is own-design, the fatprim/dirverb precedent +
; MSX2 Technical Handbook CALSLT ABIs. No reference-ROM disassembly. See
; sub/PROVENANCE.md.
; ===========================================================================

; --- lineedit_tenant: the SUBROM_IDX_LINEEDIT entry -------------------------
lineedit_tenant:
                ld      a,(LE_OP)
                or      a
                jp      z,le_store              ; LE_OP_STORE = 0
                ; fall through -> LE_OP_RELINK = 1: relink only (cload.asm's
                ; own call sites); tail: vars_reset; ret
                jp      relink_body

; --- le_store: store_line's own body (empty body -> delete; else bounds-
; check + insert), byte-for-byte the same logic as the pre-eviction
; store_line, minus the OOM raise (LE_STATUS reports it back instead).
; Inputs: SL_NUM (line number), SL_TOK (crunched token-body pointer, both
; RAM, set by the resident head before subrom_call).
le_store:
                ld      hl,(SL_TOK)
                ld      a,(hl)
                or      a
                jr      z,le_delete             ; empty body -> delete only
                ; line size = 4 (link+lineno) + body length (incl 00), found
                ; by a token-aware walk so embedded 00 operand bytes don't
                ; truncate it.
                call    skip_to_eol             ; HL (= SL_TOK) -> past the body's 00
                ld      de,(SL_TOK)
                or      a
                sbc     hl,de                   ; HL = body length incl. terminator
                ld      bc,4
                add     hl,bc                   ; HL = full line size
                ld      (SL_SIZE),hl
                ld      b,h
                ld      c,l                     ; BC = size (for the bounds check)
                ; bounds: PRGEND + size must stay below TXTMAX
                ld      hl,(PRGEND)
                add     hl,bc
                ld      de,TXTMAX
                or      a
                sbc     hl,de                   ; (PRGEND+size) - TXTMAX
                jr      nc,le_oom               ; >= TXTMAX -> out of memory
                call    prog_find_del           ; SL_SLOT = insertion point (post-delete)
                call    open_gap                ; make room of SL_SIZE at SL_SLOT
                ld      hl,(SL_SLOT)
                ld      (hl),0                  ; link placeholder (relink fills it)
                inc     hl
                ld      (hl),0
                inc     hl
                ld      a,(SL_NUM)              ; line number, LE
                ld      (hl),a
                inc     hl
                ld      a,(SL_NUM+1)
                ld      (hl),a
                inc     hl
                ld      de,(SL_TOK)             ; source = tokenised body
                ex      de,hl                   ; HL = source, DE = dest (after lineno)
                ld      bc,(SL_SIZE)            ; body length = full size - 4 header bytes
                dec     bc
                dec     bc
                dec     bc
                dec     bc
                ldir                            ; copy body incl. its 00 terminator
                jr      le_ok
le_delete:
                call    prog_find_del           ; deletes a matching line if present
le_ok:
                xor     a
                ld      (LE_STATUS),a           ; 0 = ok
                jp      relink_body             ; tail: vars_reset; ret
le_oom:
                ld      a,1
                ld      (LE_STATUS),a           ; 1 = out of memory
                ret

; --- prog_find_del: locate the slot for SL_NUM, deleting an exact match ----
; Walks the (currently valid) link chain. Sets SL_SLOT to the first line
; whose number >= SL_NUM (or the end marker). If a line of exactly SL_NUM
; exists, it is removed first so the caller can insert in its place.
; Clobbers A, BC, DE, HL. Verbatim from basic/program.asm.
prog_find_del:
                ld      hl,TXTBASE
pfd_lp:
                ld      e,(hl)                  ; DE = link
                inc     hl
                ld      d,(hl)
                dec     hl
                ld      a,d
                or      e
                jr      z,pfd_here              ; end marker -> insert here, no match
                push    hl                      ; stored number at slot+2..+3
                inc     hl
                inc     hl
                ld      c,(hl)
                inc     hl
                ld      b,(hl)                  ; BC = stored line number
                pop     hl
                ld      de,(SL_NUM)
                ld      a,c                     ; compare stored(BC) - target(DE)
                sub     e
                ld      a,b
                sbc     a,d
                jr      c,pfd_next              ; stored < target -> keep walking
                ; stored >= target: this is the slot
                ld      a,c                     ; exact match?
                cp      e
                jr      nz,pfd_here
                ld      a,b
                cp      d
                jr      nz,pfd_here
                ld      (SL_SLOT),hl            ; same number -> delete then reuse slot
                call    delete_at
                ld      hl,(SL_SLOT)
                ret
pfd_here:
                ld      (SL_SLOT),hl
                ret
pfd_next:
                ld      e,(hl)                  ; reload link (the compare clobbered DE
                inc     hl                      ;  with SL_NUM), then advance to it
                ld      d,(hl)
                ex      de,hl                   ; HL = link -> next line
                jr      pfd_lp

; --- delete_at: remove the line whose slot is in SL_SLOT --------------------
; Shifts the rest of the program (including the end marker) down over it and
; shrinks PRGEND. Clobbers A, BC, DE, HL. Verbatim from basic/program.asm.
delete_at:
                ld      hl,(SL_SLOT)
                inc     hl                      ; skip link(2)+lineno(2) -> body
                inc     hl
                inc     hl
                inc     hl
                call    skip_to_eol             ; HL = next-line address (token-aware)
                ex      de,hl                   ; DE = next-line address
                ; count = (PRGEND+2) - next   (bytes to move, incl. end marker)
                push    de                      ; next (move source)
                ld      hl,(PRGEND)
                inc     hl
                inc     hl
                or      a
                sbc     hl,de
                ld      b,h
                ld      c,l                     ; BC = count
                ; PRGEND -= (next - slot)
                ld      hl,(SL_SLOT)
                ex      de,hl                   ; DE = slot, HL = next
                or      a
                sbc     hl,de                   ; HL = removed size (next - slot)
                ex      de,hl                   ; DE = size, HL = slot
                ld      hl,(PRGEND)
                or      a
                sbc     hl,de
                ld      (PRGEND),hl
                pop     hl                      ; HL = next (source)
                ld      de,(SL_SLOT)            ; DE = slot (dest)
                ld      a,b
                or      c
                ret     z                       ; nothing trailing to move
                ldir
                ret

; --- open_gap: insert SL_SIZE bytes at SL_SLOT, shifting the tail up --------
; Moves [SL_SLOT .. PRGEND+1] (program tail incl. end marker) up by SL_SIZE
; and grows PRGEND. Caller has already bounds-checked. Clobbers A, BC, DE,
; HL. Verbatim from basic/program.asm.
open_gap:
                ld      hl,(PRGEND)             ; count = (PRGEND+2) - slot
                inc     hl
                inc     hl
                ld      de,(SL_SLOT)
                or      a
                sbc     hl,de
                ld      b,h
                ld      c,l                     ; BC = count
                ld      hl,(PRGEND)
                inc     hl                      ; HL = last tail byte (PRGEND+1) = source end
                ld      de,(SL_SIZE)
                push    hl
                add     hl,de                   ; dest end = source end + size
                ex      de,hl                   ; DE = dest end
                pop     hl                      ; HL = source end
                ld      a,b
                or      c
                jr      z,og_end
                lddr                            ; shift the tail upward
og_end:
                ld      hl,(PRGEND)             ; PRGEND += SL_SIZE
                ld      de,(SL_SIZE)
                add     hl,de
                ld      (PRGEND),hl
                ret

; --- relink_body: recompute every line's link pointer, stopping at the end
; marker, then vars_reset. A line's link = the address of the following
; line's link field. Clobbers A, DE, HL, B, C. Verbatim from basic/
; program.asm's `relink` (repack arm), renamed here to avoid confusion with
; the resident marshalling shim of the same name (basic/program.asm) -- this
; IS the loop that shim's LE_OP_RELINK reaches, and le_store's own tail
; above reaches it directly (sub-local, no double subrom_call).
relink_body:
                ld      hl,TXTBASE
rlb_lp:
                ld      a,(PRGEND+1)            ; reached the end marker (HL == PRGEND)?
                cp      h                       ; (a fresh line's link is a placeholder
                jr      nz,rlb_more             ;  0000, so we cannot stop on link==0)
                ld      a,(PRGEND)
                cp      l
                jr      nz,rlb_more             ; HL != PRGEND -> more lines to link
                jp      vars_reset              ; tail call (own header: page-0 low-region
                                                ; resident, directly reachable here)
rlb_more:
                push    hl                      ; remember this link field
                inc     hl                      ; skip link (2) + lineno (2)
                inc     hl
                inc     hl
                inc     hl
                call    skip_to_eol             ; HL = next line (token-aware end-find)
                ex      de,hl                   ; DE = next-line address
                pop     hl                      ; HL = link field to fill
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ex      de,hl                   ; HL = next-line address
                jr      rlb_lp

; --- tok_skip: advance HL past one token, including its operand bytes ------
; Sub-local duplicate of basic/interp.asm tok_skip (own header: skip_to_eol's
; own dependency, a pure leaf, safe to duplicate). Verbatim (ROM_BASE is
; $2812 here too, so the repack-only SNG/DBL float-literal cases are
; included, matching this sub-ROM's repack-only existence).
tok_skip:
                ld      a,(hl)
                inc     hl
                cp      HEX_TOKEN               ; $0C ,word
                jr      z,tsk2
                cp      INT2_TOKEN              ; $1C ,word
                jr      z,tsk2
                cp      LINENO_TOKEN            ; $0E ,word
                jr      z,tsk2
                cp      LINEADDR_TOKEN          ; $0D ,word
                jr      z,tsk2
                cp      OCT_TOKEN               ; $0B ,word
                jr      z,tsk2
                cp      INT1_TOKEN              ; $0F ,byte
                jr      z,tsk1
                cp      PEEK_PREFIX             ; $FF ,function-token byte
                jr      z,tsk1
                cp      SNG_TOKEN               ; $1D ,4 float value bytes. A mantissa
                jr      z,tsk4                  ; byte can be $00 (e.g. .5 -> 1D 40 50 00
                cp      DBL_TOKEN               ; 00), so without this stride skip_to_eol
                jr      z,tsk8                  ; mistakes it for the line/stmt terminator
                                                ; -- a stored `10 A=1.5` would never RUN.
                cp      '"'                     ; string literal
                jr      z,tsk_str
                cp      REM_TOKEN               ; REM -> rest of line
                jr      z,tsk_rem
                cp      DATA_TOKEN              ; DATA -> verbatim body to ':' / EOL
                jr      z,tsk_data
                ret                             ; 0-operand token / plain byte
tsk1:
                inc     hl
                ret
tsk2:
                inc     hl
                inc     hl
                ret
tsk8:                                           ; DBL_TOKEN: 8 value bytes (4 here + 4 in tsk4)
                inc     hl
                inc     hl
                inc     hl
                inc     hl
tsk4:                                           ; SNG_TOKEN: 4 value bytes
                inc     hl
                inc     hl
                inc     hl
                inc     hl
                ret
tsk_str:
                ld      a,(hl)
                or      a
                ret     z
                inc     hl
                cp      '"'
                jr      nz,tsk_str
                ret
tsk_rem:
                ld      a,(hl)
                or      a
                ret     z
                inc     hl
                jr      tsk_rem
tsk_data:                                       ; DATA body: verbatim ASCII to ':' or EOL,
                ld      a,(hl)                  ; left un-consumed (the ':' / 00 is stepped
                or      a                       ; by the caller's outer loop). Skipping the
                ret     z                       ; body as a unit means a stray control byte
                cp      COLON                   ; in it can never be misread as an operand-
                ret     z                       ; bearing token -- same end position as the
                inc     hl                      ; old byte-by-byte walk on valid DATA.
                jr      tsk_data

; --- skip_to_eol: HL at a token body -> HL just past the line's 00 ---------
; terminator. Token-aware (steps whole tokens via tok_skip above), so an
; operand byte equal to 00 is not mistaken for the terminator. Sub-local
; duplicate of basic/interp.asm skip_to_eol (verbatim).
skip_to_eol:
                ld      a,(hl)
                or      a
                jr      z,ste_done
                call    tok_skip
                jr      skip_to_eol
ste_done:
                inc     hl                      ; advance past the 00 terminator
                ret
