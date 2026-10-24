; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; screen.asm — what main keeps of the screen-setup verbs: CLS, and the shared
; function-key-line helpers.
;
;   CLS                                     clear the screen
;
; 🚚 D-P0CB slice D (2026-10-24): SCREEN, COLOR, WIDTH and KEY (OFF / ON / LIST /
; n,"text") are zerobas-sub2's now -- sub2/scrstmt.asm, page 0, reached through
; ONE CALSLT per statement (main's four stmt_table rows land on ex_open's shared
; `ld c,a` byte in front of ex_sub2, basic/program.asm) and calling main back
; through p0cb (docs/spec-sub2-p0cb.md). Their history is this file's before that
; slice. What stays here is what is SHARED or cannot be reached any other way:
;   ex_cls / cls_keyline   CLS (not part of the slice).
;   key_repaint            CLS, the prompt's txt_mode (basic/repl.asm) and, through
;                          p0cb, SCREEN and WIDTH.
;   key_op                 key_repaint's tail by name: KEY ON / OFF's paint and
;                          blank. The keystr tenant is reached through an INLINE
;                          byte (sc_inl0), which a p0cb'd caller cannot hand over.
;   key_drain              KEY LIST / KEY n,"text"'s CONTINUATION: the render
;                          drained by detok_emit's print loop, in main, off sub2's
;                          CALSLT frame.
;
; These are thin wrappers over the documented C-BIOS screen entry points —
; zerobas owns no VDP programming of its own (docs/msx1-basic-bios-coupling.md):
;   CLS -> CLS ($00C3)
;
; Clean-room: original code. Statement *semantics* from the public MSX-BASIC
; language reference; every BIOS entry point and work-area address is traced to
; the MSX Assembly Page / MSX2 Technical Handbook / C-BIOS (see sysvars.inc and
; PROVENANCE.md). No disassembly.
;
; ex_cls is entered with HL on its statement token and continues the line via
; `jp pop_exec`. The C-BIOS entry points make no register guarantees, so HL is
; guarded across every call.

; --- ex_cls: CLS -----------------------------------------------------------
ex_cls:
                ; D-BAREEXTRA (2026-10-24): the statement must END here BEFORE the
                ; screen goes -- `CLS 1` / `CLS=1` raise Syntax error with the screen
                ; intact on the VG-8020; zerobas cleared first (scratchpad/stmteq_run.out).
                call    stmt_bare_end       ; past the CLS token; Z iff 0 or ':'
                jp      nz,stmt_error
                push    hl
                xor     a                   ; CLS requires the zero flag set on entry
                call    CLS
cls_keyline:                                ; B4: CLS's tail (WIDTH shared it until
                                            ; D-P0CB slice D moved WIDTH to sub2)
                call    key_repaint         ; D-KEYCLS: the key line survives CLS
                jp      pop_exec            ; D-POPEXEC: pop hl + exec_stmt

; --- key_repaint (D-KEYCLS, 2026-09-26): put the function-key line back ------
; The VG-8020 keeps its key labels on row 23 across CLS, SCREEN 0, a SCREEN
; round trip and a WIDTH change (scratchpad/keycls_probe.py); here each of them
; cleared the row -- C-BIOS's CLS/INITXT wipe the whole screen and its DSPFNK
; paints nothing (D-DSPFNK) -- and a re-init also reset CRTCNT, so the scroll
; bound moved back onto the key row. When the line is ON and the mode is a text
; mode, this repaints it through the keystr tenant (the KEY ON path) and
; re-reserves the row. Preserves HL (every caller holds the parse cursor).
key_repaint:
                ld      a,(CNSDFG)
                or      a
                ret     z                   ; KEY OFF: nothing to put back
                ld      a,(SCRMOD)
                cp      2
                ret     nc                  ; graphics modes have no key line
                                            ; (SCREEN 1 has one since D-KEYSCR1:
                                            ; ks_geom lays out its 32-column row)
                ld      a,CON_ROWS_KEYON
                ld      (CRTCNT),a          ; the bottom row stays reserved
                ld      a,KEYOP_FNKPAINT
; key_op -- the keystr tenant (sub/keystr.asm) with A = the op (KEYOP_*), KEYARG
; set here; preserves HL and IX. sub2's KEY ON / KEY OFF (sub2/scrstmt.asm) call
; it through p0cb to paint / blank the line once they have set CNSDFG and CRTCNT
; (D-FNKLINE). A name on key_repaint's existing tail: 0 B.
key_op:
                ld      (KEYARG),a
                push    hl
                push    ix
                call    sc_inl0             ; D-STUBINL: D-SCCALL: tenant call + absent raise
                db      low (SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_KEYSTR)
                pop     ix
                pop     hl
                ret

; --- key_drain: KEY LIST / KEY n,"text"'s CONTINUATION (D-P0CB slice D) ---------
; sub2's scr_key (sub2/scrstmt.asm) parses and sets KEYARG (255 = LIST, else the
; key number, with the text staged in STRSCR), then returns this address in DE;
; ex_sub2 jumps here with HL = the cursor and the stack as the statement entered.
; The keystr tenant leaves its render window printable after EVERY op -- KEY
; LIST's ten lines, or a lone NUL for a store -- so the drain is unconditional;
; 🪟 D-DETOKBUF: through detok_emit's windowed loop (KEY LIST's ~200 B do not fit
; one buffer). It runs HERE, not through p0cb, so the print loop is not nested
; under sub2's CALSLT frame. No IX guard: ex_sub2's CALSLT has already spent it.
key_drain:
                push    hl
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_KEYSTR
                call    detok_emit
                jp      pop_exec            ; D-POPEXEC: pop hl + exec_stmt
