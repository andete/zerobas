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
;
; Defined BEFORE sysvars.inc so the string-engine RAM layout there can gate on it
; (STRMAX / STRSCR / the temp ring differ between the lean and repack builds — see
; sysvars.inc "string-variable store" and docs/spec-basic-string-engine.md §5).
    IFNDEF ROM_BASE
ROM_BASE:       equ     $4000
    ENDIF

                include "basic/sysvars.inc"

                org     ROM_BASE

; --- reclaimed low region ($2812-$3FFF), relocated variant only ------------
; When based below $4000 we fill the reclaimed page-0 span up to the header. The
; string-engine arc (S3) is its first tenant: the keyword crunch table (moved down
; from page 1 — which is full to $7FFF — to free room for the engine's growth, spec
; §5b) and the string engine itself (concat spine now; the S4 functions later). The
; interpreter is 100% label-based (docs/cbios-repack-ws2-audit.md), so code here is
; reached from page 1 by ordinary in-slot calls/jumps. Whatever space is left below
; the header is padded $00. (The zerobas-tape page-0 completions live at their own
; org $09EE — C-BIOS gap-1 fill, below this region — and are spliced by the merged
; main-ROM build; D5 as revised 2026-07-11 when float F2 filled the whole window,
; retiring the old $3A72–$3C43 mid-region hole. This region is BASIC's to $4000.)
    IF ROM_BASE < $4000
                include "basic/kwtable.inc"
                include "basic/str-engine.asm"
                include "basic/input.asm"
                include "basic/float.asm"
                include "basic/float-arith.asm"
; low-region overflow guard: the low-region tenants must not reach the $4000 header.
; If they do, the `ds` below would be negative (pasmo warns + emits nothing, a silent
; corruption), so assert first — an overrun references an undefined symbol -> clean
; ERROR whose name is the diagnostic (mirrors the $8000 page-1 guard in main.asm).
    IF $ > $4000
                db      STRING_ENGINE_OVERRAN_4000_HEADER__LOW_REGION_FULL__TRIM_OR_SPLIT
    ENDIF
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

; --- overflow guard: the image must not overrun the $8000 ceiling ----------
; $8000 is the top of slot-0 page 1 in BOTH builds — the lean 16 KB $4000-$7FFF
; image and the repacked ~21.5 KB $2812-$7FFF image (basic/main-reloc.asm). If a
; future feature pushes code past it, the pad below would be a *negative* `ds`,
; which pasmo assembles as a WARNING with exit 0 (a truncated/empty ROM) — a
; silent corruption the build would not catch. So assert first: on overflow this
; references an undefined symbol, forcing a clean ERROR (exit 1) whose NAME is the
; diagnostic. When it fits, the IF body emits nothing, so the shipping basic.rom
; stays byte-identical. A lean-build overflow is the signal to move the feature
; behind `IF ROM_BASE < $4000` (repack-only) or trim it.
;
; Two checks: a moderate overrun leaves $ in $8001-$FFFF (caught by the first); a
; catastrophic one (>32 KB past the ceiling) wraps $ past 64 KB back below the org,
; where the location counter can never legitimately sit (caught by the second).
    IF $ > $8000
                db      BASIC_IMAGE_OVERRAN_8000_CEILING__GATE_FEATURE_ON_ROM_BASE_OR_TRIM
    ENDIF
    IF $ < ROM_BASE
                db      BASIC_IMAGE_WRAPPED_PAST_64K__FEATURE_FAR_TOO_LARGE__SPLIT_IT
    ENDIF

; --- pad to the $8000 page ceiling -----------------------------------------
; Fill with $00 (not $FF): empty C-BIOS page 1 is $00, so when this image is
; shipped as a slot-0 page-1 *patch* (see build-patches.sh) the diff carries
; only zerobas's real code, not the padding. As a cartridge the fill byte is
; never executed, so $00 vs $FF is immaterial there.
                ds      $8000 - $, $00
