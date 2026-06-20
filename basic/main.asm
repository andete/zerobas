; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; zerobas — main.asm
; ===========================================================================
; A clean-room, game-loader-scoped MSX1 BASIC, built as a standalone 16 KB
; cartridge ROM. See README.md and PROVENANCE.md.
;
; CLEAN-ROOM DISCIPLINE: every constant, address, and algorithm in this repo
; is traceable to an allowed source (MSX2 Technical Handbook, MSX Assembly
; Page, hardware datasheets, C-BIOS sources, or this project's own black-box
; oracle observations). Nothing is derived from an MSX-BASIC / GW-BASIC
; disassembly or a reference ROM disassembly. See PROVENANCE.md.
;
; Runtime model: this is an "AB" cartridge. The BIOS finds the header at $4000
; during boot and calls INIT. INIT never returns — it tokenises a line, the
; executor dispatches it, and the BLOAD handler hands off to the loaded binary.
; C-BIOS's CALBAS ($0159) is therefore never touched.
; ===========================================================================

                include "basic/sysvars.inc"

                org     $4000

; --- MSX cartridge header (MSX2 Technical Handbook, cartridge ROM format) ---
; 16 bytes: ID, INIT, STATEMENT, DEVICE, TEXT, then 6 reserved bytes. INIT
; therefore begins at $4010.
                db      "AB"            ; ROM signature
                dw      init            ; INIT entry point
                dw      0               ; STATEMENT expansion handler (none)
                dw      0               ; DEVICE expansion handler (none)
                dw      0               ; TEXT (BASIC program pointer) (none)
                dw      0,0,0           ; reserved (pads header to 16 bytes)

; Interpreter front-end: defines `init` (the cartridge header points at it),
; the tokeniser, and the executor.
                include "basic/interp.asm"

; Startup header (defines `show_title`).
                include "basic/title.asm"

; Keyboard line editor + read/eval loop (defines `repl`, `print_string`).
                include "basic/repl.asm"

; Integer variable store (defines `var_get`, `var_set`, `clear_vars`) + the
; minimal string-variable store (defines `str_find`, `str_get_key`,
; `str_set_key`, `var_str_type`).
                include "basic/vars.asm"

; Minimal string-VALUE layer for PRINT/LET (defines `str_eval`, `print_strval`).
                include "basic/strvar.asm"

; 16-bit integer expression evaluator (defines `eval`).
                include "basic/expr.asm"

; The POKE statement handler (defines `do_poke`).
                include "basic/poke.asm"

; The VPOKE / OUT statement handlers (defines `do_vpoke`, `do_out`).
                include "basic/vdpio.asm"

; The CLEAR statement handler (defines `ex_clear`).
                include "basic/clear.asm"

; DEF USR statement + USR() function (defines `ex_def`, `ev_usr`, `clear_usrtab`).
                include "basic/usr.asm"

; The PRINT statement (defines `ex_print`, `print_number`, `print_crlf`).
                include "basic/print.asm"

; Screen-setup verbs SCREEN/COLOR/CLS/WIDTH/KEY (defines `ex_screen`, …).
                include "basic/screen.asm"

; The LIST statement + the detokeniser (defines `ex_list`, `detok`).
                include "basic/list.asm"

; The BLOAD statement handler and the ,R handoff (defines `do_bload`).
                include "basic/bload.asm"

; The CLOAD / LOAD"CAS:" cassette program-load handlers (defines `do_cload`,
; `do_load`). Reuses bload.asm's `load_error` / `dev_cas` and program.asm's
; `relink` / `new_prog`, so it follows bload.asm in the include order.
                include "basic/cload.asm"

; Stored numbered-line program: storage, NEW, RUN (defines `dispatch_line`).
                include "basic/program.asm"

; --- pad to a full 16 KB page ($4000-$7FFF) -------------------------------
; Fill with $00 (not $FF): empty C-BIOS page 1 is $00, so when this image is
; shipped as a slot-0 page-1 *patch* (see build-patches.sh) the diff carries
; only zerobas's real code, not 16 KB of padding. As a cartridge the fill byte
; is never executed, so $00 vs $FF is immaterial there.
                ds      $8000 - $, $00
