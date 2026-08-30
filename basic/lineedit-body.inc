; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; lineedit-body.inc — store_line/prog_find_del/delete_at/open_gap/relink
; shared body (the numbered-line editor's TXTTAB memmove engine).
;
; ⛔⛔ THIS FILE IS NOT ASSEMBLED. NOTHING INCLUDES IT. ⛔⛔
; Measured 2026-08-30 (D-TRUNCLOAD follow-up, `make shared-body-check`): it is
; the ONLY `.inc` under basic/ or sub/ that no source includes. The live code is
; sub/lineedit.asm's page-1 tenant. The Makefile still lists this file as a
; dependency of the sub ROM, which can never affect the build.
;
; 🔴 AND THE TWO COPIES HAVE DIVERGED. D-TRUNCLOAD bounded the live `relink`
; walk to `HL >= PRGEND` -- an equality test never fires again once
; `skip_to_eol` overshoots on a truncated store, and relink then walks RAM
; forever (docs/spec-basic-truncload.md §5). `rl_lp` below still reads `==`.
; It is left that way ON PURPOSE: syncing a dead copy restores the illusion that
; either one is authoritative. Read sub/lineedit.asm.
;
; Whether this file is deleted or kept as a historical record is Joost's call
; (tools/shared-body-allow.txt).
;
; docs/spec-eviction-g4-space.md §4 (carve #2). Extracted verbatim from
; basic/program.asm so the SAME source fed two homes until the lean cart retired:
;   * (retired) inline in basic/program.asm, at this
;     file's ORIGINAL position (right after dl_overflow/is_cmd/parse_lineno/
;     new_prog/run_prog/do_break/ex_stop/ex_cont/find_line_bc, before
;     "ex_gosub: GOSUB <line>") -- BYTE-IDENTICAL to the pre-eviction build
;     (this file is a pure relocation of that exact code, nothing added/
;     removed/reordered).
;   * sub-ROM PAGE-1 tenant (sub/lineedit.asm, repack): store_line/relink
;     become resident marshalling shims (basic/program.asm's own `IF
;     branch) that `subrom_call` lineedit_tenant; prog_find_del/delete_at/
;     open_gap AND the relink LOOP move whole into sub/lineedit.asm (own
;     header has the full rationale, incl. why err_mem itself stays
;     resident even though sl_oom's code does not).
;
; Clean-room: our own code, extracted verbatim from basic/program.asm (see
; that file's header for the full line-link-format / editor provenance).

; --- store_line: insert / replace / delete a numbered line -------------------
; in: BC = line number, HL = crunched token body (0-terminated, in TOKBUF).
; An empty body (first byte 00) deletes the line; otherwise the line replaces
; any existing line of the same number, else is inserted in number order.
store_line:
                xor     a
                ld      (CONTVALID),a       ; editing the program invalidates CONT
                ld      (SL_NUM),bc
                ld      (SL_TOK),hl
                ld      a,(hl)
                or      a
                jr      z,sl_delete         ; empty body -> delete only
                ; line size = 4 (link+lineno) + body length (incl 00), found by a
                ; token-aware walk so embedded 00 operand bytes don't truncate it.
                call    skip_to_eol         ; HL (= TOKBUF) -> past the body's 00
                ld      de,(SL_TOK)
                or      a
                sbc     hl,de               ; HL = body length incl. terminator
                ld      bc,4
                add     hl,bc               ; HL = full line size
                ld      (SL_SIZE),hl
                ld      b,h
                ld      c,l                 ; BC = size (for the bounds check)
                ; bounds: PRGEND + size must stay below TXTMAX
                ld      hl,(PRGEND)
                add     hl,bc
                ld      de,TXTMAX
                or      a
                sbc     hl,de               ; (PRGEND+size) - TXTMAX
                jr      nc,sl_oom           ; >= TXTMAX -> out of memory
                call    prog_find_del       ; SL_SLOT = insertion point (post-delete)
                call    open_gap            ; make room of SL_SIZE at SL_SLOT
                ld      hl,(SL_SLOT)
                ld      (hl),0              ; link placeholder (relink fills it)
                inc     hl
                ld      (hl),0
                inc     hl
                ld      a,(SL_NUM)          ; line number, LE
                ld      (hl),a
                inc     hl
                ld      a,(SL_NUM+1)
                ld      (hl),a
                inc     hl
                ld      de,(SL_TOK)         ; source = tokenised body
                ex      de,hl               ; HL = source, DE = dest (after lineno)
                ld      bc,(SL_SIZE)        ; body length = full size - 4 header bytes
                dec     bc
                dec     bc
                dec     bc
                dec     bc
                ldir                        ; copy body incl. its 00 terminator
                jp      relink
sl_delete:
                call    prog_find_del       ; deletes a matching line if present
                jp      relink
sl_oom:
                ld      a,$CC               ; out-of-memory landmark (distinct byte)
                ld      (ERRMARK),a
                ld      a,7                 ; ERR 7: out of memory (error-handling S2a)
                jp      raise_error
err_mem:        db      "out of memory",13,10,0

; --- prog_find_del: locate the slot for SL_NUM, deleting an exact match ------
; Walks the (currently valid) link chain. Sets SL_SLOT to the first line whose
; number >= SL_NUM (or the end marker). If a line of exactly SL_NUM exists, it
; is removed first so the caller can insert in its place. Clobbers A, BC, DE, HL.
prog_find_del:
                ld      hl,TXTBASE
pfd_lp:
                ld      e,(hl)              ; DE = link
                inc     hl
                ld      d,(hl)
                dec     hl
                ld      a,d
                or      e
                jr      z,pfd_here          ; end marker -> insert here, no match
                push    hl                  ; stored number at slot+2..+3
                inc     hl
                inc     hl
                ld      c,(hl)
                inc     hl
                ld      b,(hl)              ; BC = stored line number
                pop     hl
                ld      de,(SL_NUM)
                ld      a,c                 ; compare stored(BC) - target(DE)
                sub     e
                ld      a,b
                sbc     a,d
                jr      c,pfd_next          ; stored < target -> keep walking
                ; stored >= target: this is the slot
                ld      a,c                 ; exact match?
                cp      e
                jr      nz,pfd_here
                ld      a,b
                cp      d
                jr      nz,pfd_here
                ld      (SL_SLOT),hl        ; same number -> delete then reuse slot
                call    delete_at
                ld      hl,(SL_SLOT)
                ret
pfd_here:
                ld      (SL_SLOT),hl
                ret
pfd_next:
                ld      e,(hl)              ; reload link (the compare clobbered DE
                inc     hl                  ;  with SL_NUM), then advance to it
                ld      d,(hl)
                ex      de,hl               ; HL = link -> next line
                jr      pfd_lp

; --- delete_at: remove the line whose slot is in SL_SLOT ---------------------
; Shifts the rest of the program (including the end marker) down over it and
; shrinks PRGEND. Clobbers A, BC, DE, HL.
delete_at:
                ld      hl,(SL_SLOT)
                inc     hl                  ; skip link(2)+lineno(2) -> body
                inc     hl
                inc     hl
                inc     hl
                call    skip_to_eol         ; HL = next-line address (token-aware)
                ex      de,hl               ; DE = next-line address
                ; count = (PRGEND+2) - next   (bytes to move, incl. end marker)
                push    de                  ; next (move source)
                ld      hl,(PRGEND)
                inc     hl
                inc     hl
                or      a
                sbc     hl,de
                ld      b,h
                ld      c,l                 ; BC = count
                ; PRGEND -= (next - slot)
                ld      hl,(SL_SLOT)
                ex      de,hl               ; DE = slot, HL = next
                or      a
                sbc     hl,de               ; HL = removed size (next - slot)
                ex      de,hl               ; DE = size, HL = slot
                ld      hl,(PRGEND)
                or      a
                sbc     hl,de
                ld      (PRGEND),hl
                pop     hl                  ; HL = next (source)
                ld      de,(SL_SLOT)        ; DE = slot (dest)
                ld      a,b
                or      c
                ret     z                   ; nothing trailing to move
                ldir
                ret

; --- open_gap: insert SL_SIZE bytes at SL_SLOT, shifting the tail up ----------
; Moves [SL_SLOT .. PRGEND+1] (program tail incl. end marker) up by SL_SIZE and
; grows PRGEND. Caller has already bounds-checked. Clobbers A, BC, DE, HL.
open_gap:
                ld      hl,(PRGEND)         ; count = (PRGEND+2) - slot
                inc     hl
                inc     hl
                ld      de,(SL_SLOT)
                or      a
                sbc     hl,de
                ld      b,h
                ld      c,l                 ; BC = count
                ld      hl,(PRGEND)
                inc     hl                  ; HL = last tail byte (PRGEND+1) = source end
                ld      de,(SL_SIZE)
                push    hl
                add     hl,de               ; dest end = source end + size
                ex      de,hl               ; DE = dest end
                pop     hl                  ; HL = source end
                ld      a,b
                or      c
                jr      z,og_end
                lddr                        ; shift the tail upward
og_end:
                ld      hl,(PRGEND)         ; PRGEND += SL_SIZE
                ld      de,(SL_SIZE)
                add     hl,de
                ld      (PRGEND),hl
                ret

; --- relink: recompute every line's link pointer, stopping at the end marker -
; A line's link = the address of the following line's link field. Clobbers
; A, DE, HL (repack: also B, C -- the tail vars_reset now chains into
; heap_reset for the 4c string-scalar clear; all four relink call sites are
; indifferent to BC afterward).
relink:
                ld      hl,TXTBASE
rl_lp:
                ld      a,(PRGEND+1)        ; reached the end marker (HL == PRGEND)?
                cp      h                   ; (a fresh line's link is a placeholder
                jr      nz,rl_more          ;  0000, so we cannot stop on link==0)
                ld      a,(PRGEND)
                cp      l
                jr      nz,rl_more          ; HL != PRGEND -> more lines to link
                jp      vars_reset          ; arrays slice-1 (§9.6) + slice-4b (§3b/Q2):
                                            ; every relink call (store_line edits,
                                            ; Q-9c, AND CLOAD/LOAD's own program
                                            ; replacement) invalidates any live
                                            ; scalars/arrays -- tail call, vars_reset/
                                            ; ary_reset ends in `ret`. This is the
                                            ; slice-4b "edit clears scalars too"
                                            ; behaviour change (deliberate, MSX-
                                            ; faithful, §7.1).
rl_more:
                push    hl                  ; remember this link field
                inc     hl                  ; skip link (2) + lineno (2)
                inc     hl
                inc     hl
                inc     hl
                call    skip_to_eol         ; HL = next line (token-aware end-find)
                ex      de,hl               ; DE = next-line address
                pop     hl                  ; HL = link field to fill
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ex      de,hl               ; HL = next-line address
                jr      rl_lp
