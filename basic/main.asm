; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

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

; --- ROM base (cbios-repack arc, WS-2) -------------------------------------
; The shipping build is a 16 KB slot-0 page-1 image based at $4000 (the default
; below). The C-BIOS repack (docs/spec-cbios-repack-tooling.md) reclaims
; $2812-$3FFF of page 0 *contiguous below* page 1, letting BASIC grow into one
; ~21.5 KB $2812-$7FFF image. That relocated variant is assembled by the thin
; wrapper basic/main-reloc.asm, which pre-defines ROM_BASE=$2812 before including
; this file. Nothing else in the build sets ROM_BASE, so the default keeps the
; production basic.rom byte-identical. See docs/cbios-repack-ws2-audit.md — the
; hardcoded-address audit proved the interpreter is 100% label-based, so the only
; base-dependent site in the whole source is this org.
    IFNDEF ROM_BASE
ROM_BASE:       equ     $4000
    ENDIF

                org     ROM_BASE

; --- reclaimed low region ($2812-$3FFF), relocated variant only ------------
; When based below $4000 we pad the reclaimed page-0 span up to the header. It is
; reserved (all $00) for now: this arc delivers the space + the assemble-clean
; layout, not its occupants. Future BASIC growth and the WS-3 splice place code
; here (the zerobas-tape page-0 completions keep their own org $3A72 and are
; spliced by the merged main-ROM build, D5 — they are not carved out here).
    IF ROM_BASE < $4000
                ds      $4000 - $, $00
    ENDIF

; --- MSX cartridge header (MSX2 Technical Handbook, cartridge ROM format) ---
; 16 bytes: ID, INIT, STATEMENT, DEVICE, TEXT, then 6 reserved bytes. INIT
; therefore begins at $4010. The header stays pinned at $4000 in every variant:
; C-BIOS's cartridge boot scan looks for the "AB" header in page 1 ($4000), never
; page 0, so relocation appends space *below* the header rather than moving it.
                db      "AB"            ; ROM signature
                dw      init            ; INIT entry point
                dw      0               ; STATEMENT expansion handler (none)
                dw      0               ; DEVICE expansion handler (none)
                dw      0               ; TEXT (BASIC program pointer) (none)
                dw      0,0,0           ; reserved (pads header to 16 bytes)

; Interpreter front-end: defines `init` (the cartridge header points at it),
; the tokeniser, and the executor.
                include "basic/interp.asm"

; Extension-ROM boot-scan helper (defines `init_ext_roms`): scans the remaining
; slots for "AB" ROMs (e.g. zerobas-disk) and CALSLTs their INIT before the REPL.
                include "basic/initext.asm"

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

; PRINT USING formatted output (defines `ex_print_using`; reuses print.asm's div10
; + pchar + the string layer), so it follows print.asm in the include order.
                include "basic/printusing.asm"

; Screen-setup verbs SCREEN/COLOR/CLS/WIDTH/KEY (defines `ex_screen`, …).
                include "basic/screen.asm"

; The LIST statement + the detokeniser (defines `ex_list`, `detok`).
                include "basic/list.asm"

; Loader-side FAT12 engine over the standard DSKIO ($4010) sector interface
; (defines `fat_io_open`/`fat_io_getbyte`/`fat_io_create`/`fat_io_putbyte`/
; `fat_io_close` + the FAT12 substrate). The disk verbs in bload.asm / cload.asm /
; save.asm call this; it must be assembled before them.
                include "basic/fat.asm"

; The BLOAD statement handler and the ,R handoff (defines `do_bload`).
                include "basic/bload.asm"

; The CLOAD / LOAD"CAS:" cassette program-load handlers (defines `do_cload`,
; `do_load`). Reuses bload.asm's `load_error` / `dev_cas` and program.asm's
; `relink` / `new_prog`, so it follows bload.asm in the include order.
                include "basic/cload.asm"

; The BSAVE / SAVE disk-write statement handlers (defines `do_bsave`, `do_save`)
; + the shared disk-write helper. Reuses bload.asm's `load_error` / `dev_cas` /
; `parse_disk_fcb` and the fat.asm engine and expr.asm's `eval`, so it follows them.
                include "basic/save.asm"

; Disk BASIC file-channel verbs (Phase 2): FILES (defines `do_files`). Reuses the
; fat.asm engine (`fat_mount` / `read_sector`) + bload.asm's `load_error`, so it
; follows them in the include order.
                include "basic/files.asm"

; Random-access record verbs (Phase 2c): FIELD / LSET / RSET. Builds on the
; file-channel manager (fch_select/fch_valid) in files.asm and the string layer,
; so it follows files.asm + strvar.asm in the include order.
                include "basic/field.asm"

; CALL FORMAT (defines `ex_call`/`ex_call_us`; writes a fresh FAT12 via fat.asm's
; write_sector), so it follows fat.asm + files.asm in the include order.
                include "basic/format.asm"

; Stored numbered-line program: storage, NEW, RUN (defines `dispatch_line`).
                include "basic/program.asm"

; --- pad to a full 16 KB page ($4000-$7FFF) -------------------------------
; Fill with $00 (not $FF): empty C-BIOS page 1 is $00, so when this image is
; shipped as a slot-0 page-1 *patch* (see build-patches.sh) the diff carries
; only zerobas's real code, not 16 KB of padding. As a cartridge the fill byte
; is never executed, so $00 vs $FF is immaterial there.
                ds      $8000 - $, $00
