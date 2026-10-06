; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas — main.asm
; ===========================================================================
; A clean-room MSX1 BASIC, assembled as one contiguous slot-0 image spanning the
; reclaimed page-0 low region ($2812-$3FFF) plus page 1 ($4000-$7FFF). This is the
; ONLY entry point: `pasmo basic/main.asm` is the whole interpreter build, and the
; merged main ROM (zerobas-main-eu.ips/.bps) is this image spliced into a repacked
; C-BIOS. See README.md and PROVENANCE.md.
;
; CLEAN-ROOM DISCIPLINE: every constant, address, and algorithm in this repo
; is traceable to an allowed source (MSX2 Technical Handbook, MSX Assembly
; Page, hardware datasheets, C-BIOS sources, or this project's own black-box
; oracle observations). Nothing is derived from an MSX-BASIC / GW-BASIC
; disassembly or a reference ROM disassembly. See PROVENANCE.md.
;
; Runtime model: the "AB" header stays pinned at $4000. The BIOS finds it during
; boot and calls INIT. INIT never returns — it tokenises a line, the executor
; dispatches it, and the BLOAD handler hands off to the loaded binary. C-BIOS's
; CALBAS ($0159) is therefore never touched.
; ===========================================================================

; --- image base (cbios-repack arc, WS-2) -----------------------------------
; The C-BIOS repack (docs/spec-cbios-repack-tooling.md) reclaims $2812-$3FFF of
; page 0 *contiguous below* page 1, so BASIC is one ~21.5 KB $2812-$7FFF image.
; See docs/cbios-repack-ws2-audit.md — the hardcoded-address audit proved the
; interpreter is 100% label-based, so this org is the only base-dependent site in
; the whole source.
;
; ⚠️ THIS IS A CONSTANT, NOT A KNOB. Until 2026-07-29 it was `ROM_BASE`, an
; IFNDEF-overridable symbol with a second setting ($4000) that selected a 16 KB
; page-1-only "lean" cartridge — a BASIC missing seven source files. That build is
; retired and its 284 `IF ROM_BASE` gates are gone (RETIRE THE LEAN 16 KB CART S3,
; docs/spec-lean-retire-s3-gates.md). Renamed so no reader takes it for a variant
; selector: there is one image, and this is where it starts.
;
; Defined BEFORE sysvars.inc, which sites the string-engine RAM layout (STRMAX /
; STRSCR / the temp ring — see sysvars.inc "string-variable store" and
; docs/spec-basic-string-engine.md §5).
BASIC_ORG:      equ     $2765

; SUB_BUILD distinguishes this main-ROM assembly from sub/sub.asm, which shares
; several body .inc files with it (bload-body.inc's ,R handoff differs by side).
SUB_BUILD       equ     0
; D-FATENG Option 2 (Joost, 2026-09-18): the FAT12 engine becomes ONE SOURCE in
; TWO ROMs -- basic/fat-prim-body.inc assembled into disk.rom as well, so
; `disk/fat.asm`'s own copy can go. The bodies differ in exactly one place: how a
; sector primitive reaches DSKIO. In disk.rom it is LOCAL; everywhere else it is
; a CALSLT into whatever disk ROM holds the slot. DISK_BUILD gates that, on the
; SUB_BUILD pattern above -- "it gates body .inc files that genuinely differ by
; side" (sub/sub.asm:54).
DISK_BUILD      equ     0
                include "basic/sysvars.inc"

                org     BASIC_ORG

; --- reclaimed low region ($2812-$3FFF) ------------------------------------
; The reclaimed page-0 span is filled up to the header. The string-engine arc
; (S3) is its first tenant: the keyword crunch table (moved down
; from page 1 — which is full to $7FFF — to free room for the engine's growth, spec
; §5b) and the string engine itself (concat spine now; the S4 functions later). The
; interpreter is 100% label-based (docs/cbios-repack-ws2-audit.md), so code here is
; reached from page 1 by ordinary in-slot calls/jumps. Whatever space is left below
; the header is padded $00. (The zerobas-tape page-0 completions live at their own
; org $09EE — C-BIOS gap-1 fill, below this region — and are spliced by the merged
; main-ROM build; D5 as revised 2026-07-11 when float F2 filled the whole window,
; retiring the old $3A72–$3C43 mid-region hole. This region is BASIC's to $4000.)
; kwtable is NO LONGER included resident (subrom arc WAVE 3): both of its code
; readers are now sub-side — match_kw (the wave-2 tokeniser) and detok_kw/detok_kw2
; (the wave-3 detokeniser) — so the sole copy lives in sub/sub.asm. Dropping the
; resident table recovers wave-2's duplication + its low-region bytes and removes
; the drift risk (one source of truth). docs/spec-basic-subrom-wave3-detok.md §2.
                include "basic/str-engine.asm"
                include "basic/input.asm"
                include "basic/float.asm"
                include "basic/float-arith.asm"
; zerobas-sub discovery recorder + dispatch helper (subrom S2b): lives in the
; page-0 low region freed by evicting the float PRINT formatter (page 1 is full).
                include "basic/subromcall.asm"
; The screen editor's cell helpers (D-EDCTRL): low, because the sub-ROM readline
; tenant calls them from page 1 and main's own editing keys call them too.
                include "basic/edscreen.asm"
; Interrupt-traps T3: the KEY event source. Low-region (not page 1) because it
; fires from inside C-BIOS's keyboard scan, i.e. the $0038 ISR, which can land
; while a sub-ROM page-1 tenant owns page 1 — and a skipped frame would LEAK an
; undiverted keystroke. Page 0 is always mapped. See basic/keytrap.asm.
                include "basic/keytrap.asm"
; (Interrupt-traps T4's SPRITE event source is NOT included here: it is inlined
; into htimi_guard by subromcall.asm above, via basic/sprtrap-body.inc — it must
; run ahead of that guard's page-1 slot test. D-T4-2, spec-traps-t4-sprite.md §3.1.)
; Arrays slice-1 (docs/spec-basic-arrays.md §10, SPLIT design): the main-ROM
; glue half — DIM/subscript parsing (needs `eval`) and the FAC<->element
; copy/coercion (needs var_store_fac's value-field codec). The engine itself
; (descriptor walk, offset arithmetic, alloc, bound checks) is a sub-ROM
; page-0 tenant (sub/arrays.asm, SUBROM_IDX_ARY) — moved there because the
; monolithic design overran this low region by ~284 B. Like str-engine/input/
; float/float-arith/subromcall above it lands in the reclaimed low region
; rather than page 1 (page 1 is otherwise full to $7FFF). References
; vars.asm/expr.asm/float-arith.asm/float.asm/interp.asm labels defined
; LATER in this same assembly (var_name_key, eval, stmt_error, ...) —
; forward references across `include`s are fine for a whole-file multi-pass
; assembler like pasmo; only ORG-based layout needs include order.
                include "basic/arrays.asm"

; --- D-DEFFN's PROMOTION: two page-1 leaves brought DOWN into the low region --
; 💰 THIS IS WHAT ACTUALLY LANDS DEF FN, and it is the move this file's own
; header block describes from the other direction: R1 promoted the 80 B message
; pool UP into page 1 when the low region was full, "page 1 and the low region
; are co-mapped slot-0 pages, so a pressure-placed leaf can be moved between
; them freely and the walls are COUPLED". DEF FN needed the reverse: after the
; carves, page 1 was 110 B over its $8000 ceiling with 129 B free below $4000,
; so the gap arithmetic (`scratchpad/deffn_measure_over.py`) was already
; negative -- but a NEGATIVE GAP IS NOT A BUILD. Only moving real bytes across
; the boundary makes the assert stop firing, and 112 B is what these two are.
;
; ⚠️ WHY THESE TWO. `basic/sound.asm`'s own header named its placement as
; pressure and not contract, in its own words -- *"Lands in page 1 (which the
; disk/file eviction freed to ~1.1 KB) rather than the now-full reclaimed low
; region"* -- which is the definition of a promotable leaf, written down by the
; slice that placed it. `basic/poke.asm` is the smallest statement handler in
; the ROM (29 B) and reaches only `eval_addr` + `eval_byte_checked`, both
; already low-region. NEITHER is in the resident-ABI closure and neither runs
; from the $0038 ISR, so neither has a reason to be page-1 resident; the two
; gates that would object -- check_resident_abi.py and check_tenant_closure.py
; -- run in `make basic-reloc` either way.
; 🔴 AND THE DIRECTION MATTERS: promoting DOWN can never break reachability,
; because low-region code is visible whenever page 0 is mapped, which is always
; except inside a page-0 CALSLT (where no MAIN code runs at all). It is the
; other direction -- leaving something in page 1 that the ISR or a page-1 tenant
; needs -- that this tree has been bitten by (basic/subromcall.asm htimi_guard).
                include "basic/poke.asm"
                include "basic/sound.asm"
; D-MISSOP: PROMOTED FROM PAGE 1 (7 B). `show_title` is a two-instruction stub
; -- `ld ix,<tenant slot>` + `jp subrom_call` -- whose only callee, subrom_call,
; is ALREADY in the low region, and whose only caller is `init`, once, just
; before the REPL. It is the same argument poke.asm's promotion above makes, and
; the direction is the safe one: promoting DOWN cannot break reachability.
; It funds D-MISSOP's 6 B at ev_f_err/fperr_to_err, which page 1 could not hold
; (measured 4 B over the $8000 ceiling before this move).
                include "basic/title.asm"

; --- (moved out) the low-region message pool -------------------------------
; The D-LINEMAX / S-FCH-2 message strings and the ERR 52/59 raisers used to sit
; here, at the very top of the low region, and only because page 1 could not
; hold them (see their own header, now in page 1 below). The ROM REGION
; STRUCTURE REVIEW measured them PRESSURE-PLACED, not contract-forced -- 0 of
; their 9 labels are in the resident-ABI or $0038-ISR closure, and no sub-ROM
; source references any of them -- so R1 promoted the whole 80 B block into the
; page-1 tail that R1's dead-code carve had just freed. That converts a page-1
; saving into relief on the HARD wall: page 1 and the low region are co-mapped
; slot-0 pages, so a pressure-placed leaf can be moved between them freely and
; the walls are COUPLED. docs/spec-rom-region-rebalance-r1.md B,
; docs/rom-region-structure-review.md §5.


; mxf_require_end — MAXFILES's operand must be the LAST thing in the statement
; (D-MAXFTAIL). Sited here for the same reason the two raisers below page 1's tail
; were: page 1 pays one `call` and nothing else. It is reached from files.asm by an
; ordinary in-slot call — the two regions are co-mapped slot-0 pages.
; ⚠️ `stmt_bare_end` (interp.asm) does its own `inc hl` — it REPLACES a caller's
; opening advance rather than following it — so the `dec hl` cancels that and
; leaves HL where eval_byte_arg left it. On the Z path HL has been walked past any
; spaces onto the ':' or the $00, which is what exec_stmt wants anyway.
mxf_require_end:
                dec     hl
                call    stmt_bare_end       ; Z iff the statement ends here
                ret     z
                jp      stmt_error          ; anything else -> ERR 2, raised BEFORE
                                            ; the CLEAR that would eat the variables

; 🔴 D-DOMAIN: COLOR VALIDATED NOTHING. `COLOR 99`, `COLOR -1`, `COLOR 256`,
; `COLOR 15,99` and `COLOR 15,4,99` were all ACCEPTED here and are all
; `Illegal function call` on BOTH references. The domain is pinned by rows, not
; guessed: 0 and 15 are legal, **16 is the first illegal one**, and `COLOR 256`
; is ALSO ERR 5 -- so the test must see the whole 16-bit value, because 256's
; low byte is 0 and would pass a byte-only check.
; 💰 The three call sites stay 3 bytes each (`call eval` -> `call clr_eval`), so
; page 1 pays NOTHING; the helper itself lives in the low region.
; clr_eval — evaluate a COLOR component and require 0..15.
; out: E = the value, D = 0. Anything else raises ERR 5 and does not return.
clr_eval:
                call    eval
                ld      a,d                 ; the HIGH byte first: 256 has a low
                or      a                   ; byte of 0 and must NOT pass
                jr      nz,clr_ill
                ld      a,e
                cp      16
                ret     c                   ; 0..15 -> good
clr_ill:
                ; 🟢 D-PARTIAL: NOTHING TO UNDO HERE, WHICH IS THE POINT. A
                ; save-and-restore shape would need an arm at every exit — and
                ; `clr_missing` and any error raised inside `eval` both reach
                ; `raise_error`, which resets SP, so two of the four exits could
                ; not run one. The shadow makes them all atomic without an arm.
                jp      gb_illegal          ; ERR 5 Illegal function call

; clr_prep — snapshot FORCLR+BAKCLR into the shadow before COLOR parses anything.
; Called from ex_color's first instruction; page 1 pays only the `call`.
; ⚠️ IT MUST PRESERVE HL ITSELF: HL is the text cursor, live in every statement
; handler. An earlier attempt at this fix used HL as scratch here and turned every
; `COLOR` in the tree into ERR 2 — the probe's CONTROL row is what caught it.
; 🎯 THE SNAPSHOT IS ALSO WHAT MAKES AN OMITTED ARGUMENT WORK: `COLOR ,bg` never
; writes the fg slot, so the commit puts the old foreground back unchanged.
clr_prep:
                push    hl
                ld      hl,(FORCLR)
                ld      (CLR_SAVE),hl
                pop     hl
                ret

; clr_commit — publish the shadow pair, once the whole statement has parsed.
; Called from INSIDE clr_apply's existing `push hl` window and BEFORE `call
; CHGCLR`, which reads the three sysvars — so it needs no HL guard of its own.
; It leaves A alone; since D-ADDR29 S3 (2026-09-25) clr_apply loads SCRMOD AFTER
; this call (it copies FORCLR to ATRBYT first), so that no longer matters.
clr_commit:
                ld      hl,(CLR_SAVE)
                ld      (FORCLR),hl         ; FORCLR+BAKCLR are adjacent
                ret

; low-region overflow guard: the low-region tenants must not reach the $4000 header.
; If they do, the `ds` below would be negative (pasmo warns + emits nothing, a silent
; corruption), so assert first — an overrun references an undefined symbol -> clean
; ERROR whose name is the diagnostic (mirrors the $8000 page-1 guard in main.asm).
    IF $ > $4000
                db      STRING_ENGINE_OVERRAN_4000_HEADER__LOW_REGION_FULL__TRIM_OR_SPLIT
    ENDIF
; Measurement label (subrom wave-2 pre-gate, spec §7.1): low-region free =
; $4000 - __MEAS_LOW_END. Emits no bytes; read from the reloc sym by check_reloc.py.
__MEAS_LOW_END:
                ds      $4000 - $, $00

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

; The BOOT-TIME half of the zerobas-sub plumbing (defines `try_sub_slot`,
; `sub_int_install`) — PROMOTED here out of the page-0 low region to fund the KEY
; trap's $0038-path hook, which cannot leave it.
                include "basic/subrom-boot.asm"

; Keyboard line editor + read/eval loop (defines `repl`, `print_string`).
                include "basic/repl.asm"
                include "basic/edctrl.asm"   ; D-EDCTRL: CTRL-B/E/F/N/U at the editor

; Integer variable store (defines `var_get`, `var_set`, `clear_vars`) + the
; minimal string-variable store (defines `str_find`, `str_get_key`,
; `str_set_key`, `var_str_type`).
                include "basic/vars.asm"

; Minimal string-VALUE layer for PRINT/LET (defines `str_eval`, `print_strval`).
                include "basic/strvar.asm"

; 16-bit integer expression evaluator (defines `eval`).
                include "basic/expr.asm"


; The TIME pseudo-variable's WRITE half (defines `ex_time_assign`); the READ
; half is a factor and lives in expr.asm beside ERL, whose unsigned-word-to-FAC
; tail it shares. Repack-only. docs/spec-basic-time.md.
                include "basic/time.asm"

; The VPOKE / OUT statement handlers (defines `do_vpoke`, `do_out`).
                include "basic/vdpio.asm"

; The CLEAR statement handler (defines `ex_clear`).
                include "basic/clear.asm"

; DEF USR statement + USR() function (defines `ex_def`, `ev_usr`, `clear_usrtab`).
                include "basic/usr.asm"
; DEF FN / FN — the last missing MSX1 reserved word (D-DEFFN). Needs `eval`,
; `str_eval` and the typed variable store, so it is main-resident and page 1;
; the shadow LOOKUP is the sub-ROM half (sub/arrays.asm scv_find).
                include "basic/deffn.asm"

; The PRINT statement (defines `ex_print`, `pn_fmt`, `pnum_fit`, `print_crlf`).
                include "basic/print.asm"

; PRINT USING formatted output (defines `ex_print_using`; reuses print.asm's div10
; + pchar + the string layer), so it follows print.asm in the include order.
                include "basic/printusing.asm"

; Screen-setup verbs SCREEN/COLOR/CLS/WIDTH/KEY (defines `ex_screen`, …).
                include "basic/screen.asm"


; Audio Slice 2a (docs/spec-basic-audio-play-slice2a.md): the PLAY statement's
; resident stub (defines `ex_play`) — evaluates up to three MML string arguments
; and marshals each into its VCB, then hands off to the page-1 MML-parser tenant
; (sub/playparse.asm) with one subrom_call. Repack-only like `ex_sound` (the tenant
; it drives is page-1, reachable only in the repack build);.
                include "basic/play.asm"

; Audio Slice 3 (docs/audio-slice3-characterization.md): the live music servicer
; (defines `play_service` + `play_install`) — drained from C-BIOS's $0038 ISR via
; the H.TIMI seam. Main-ROM PAGE-1 resident, reached by a near JP (NOT page-0, NOT a
; tenant — §4a: page-1 tenants run DI so the ISR never fires with page 1 switched
; out). Repack-only like ex_sound/ex_play;.
                include "basic/playsvc.asm"

; Interrupt traps slice T1 (docs/spec-basic-interrupt-traps.md): basic/traps.asm holds
; the RESIDENT half — event_poll (per-frame trap detection at the H.TIMI seam),
; htimi_service (chains event_poll -> play_service), and trap_init (ZTRAP zero-fill
; $E1D1..$E21F at cold boot + RUN). WIRED 2026-07-24: play_install points H.TIMI at
; htimi_guard (subromcall.asm), which now falls through to htimi_service instead of
; straight to play_service, and `call trap_init` runs in ier_done + run_prog. The
; earlier "wiring crashes the boot" blocker was the H.TIMI/page-1 seam hazard, now fixed
; by htimi_guard (docs/traps-t1-wiring-blocker.md, spec-traps-t1-htimi-page1-safety.md);
; the ZTRAP RAM home at $E1D1 was never the problem. Inert until the arming statements
; (INTERVAL ON etc.) land — TRAPENA stays 0 so event_poll fast-outs every frame.
                include "basic/traps.asm"

; Graphics Slice G2 (docs/spec-basic-graphics-g2.md): the resident PSET/PRESET/POINT
; stubs (defines `ex_pset`, `ex_preset`, `ev_f_point`, `parse_coord`, `gfx_in_range`).
; Eval the coordinate/colour expressions + STEP/clip/SCREEN policy, then marshal a
; tiny param block and hand off the pixel RMW to the page-0 tenant (sub/graphics.asm)
; via one subrom_call. Repack-only (repack-only in the old two-build tree), landing
; in the page-1 tail freed by the disk/file eviction (the reclaimed low region is full)
; -- same placement rationale as sound/play above.
                include "basic/graphics.asm"

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
; fat.asm engine (`fat_mount` / `fat_find`) + bload.asm's `load_error`, so it
; follows them in the include order. (It named `read_sector` until D-SEEDHOLE2:
; the FILES walk itself was evicted to a sub-ROM tenant by 0cbf495, and the
; callerless main-side read_sector shim went with the last of the carve.)
                include "basic/files.asm"

; Random-access record verbs (Phase 2c): FIELD / LSET / RSET. Builds on the
; file-channel manager (fch_select/fch_check) in files.asm and the string layer,
; so it follows files.asm + strvar.asm in the include order.
                include "basic/field.asm"

; CALL FORMAT (defines `ex_call`/`ex_call_us`; the menu is resident, the sector
; build/write bulk is a sub-ROM tenant with its own write path -- see
; basic/format.asm's REPACK EVICTION note). It still reuses fat.asm's resident
; layer, so it follows fat.asm + files.asm in the include order.
                include "basic/format.asm"

; Stored numbered-line program: storage, NEW, RUN (defines `dispatch_line`).
                include "basic/program.asm"

; LOCATE / SWAP / TRON / TROFF / MOTOR -- the MISSING class. Calls onoff_decode
; and trap_syntax (program.asm) and ln_div_entry (program.asm), so it follows
; program.asm in the include order.
                include "basic/missing.asm"

; ===========================================================================
; PROMOTED FROM THE LOW REGION BY R1 (docs/spec-rom-region-rebalance-r1.md B)
; ===========================================================================
; This block spent the whole D-LINEMAX / S-FCH-2 era in the page-0 low region,
; for one reason its own comments state plainly: page 1 could not hold it. It is
; PRESSURE-PLACED, never contract-forced -- nothing here is reachable from a
; page-1 sub-ROM tenant's resident-ABI callbacks or from the $0038 ISR, and no
; sub/ source names any of these 8 symbols (verified, review §5). Meanwhile
; EVERY reader was already in page 1: err_msgtab (interp.asm), dl_overflow
; (program.asm), and files.asm's six OPEN reject sites. So the move puts the
; data beside the code that reads it, and hands the low region its first free
; bytes since the wall closed.
; ⚠️ A page-0 sub-ROM tenant can still reach this -- main page 1 stays MAPPED
; during a page-0 CALSLT (it is page 0 that switches out). Promotion is strictly
; safer here than the low-region siting was, not merely neutral.

; --- Low-region string pool (D-LINEMAX, spec §4 Q2) -------------------------
; Message text that page-1 code points at but does not execute. A string is pure
; data with no call graph, so the only question placement has to answer is "is
; page 0 mapped when it is READ?" — and for a REPL-time report it always is: the
; reader is resident dispatch_line, never a sub-ROM tenant (a page-0 tenant runs
; with this whole region switched OUT, which is what pins code here, not data).
;
; Sited here because page 1 could not hold it. Q2 deferred placement to
; implementation with "measure the walls before choosing"; measured from clean at
; implementation time, page 1 had 10 B free and the low region 32 B, against a
; 42-byte need — so the choice was not between homes, it was a split across both.
;
; 🎯 D-MSGMIGRATE EMPTIED THIS POOL. `Line buffer overflow` (ERR 25) and
; `Overflow` (ERR 6) are now em_linebuf_overflow / em_overflow in sub/errmsg.asm,
; keyed on ERRFLG. Both of their readers -- err_msgtab and program.asm's
; dl_overflow -- became ERRFLG-keyed in the same edit, which is what let BOTH go
; rather than only the table-reached one.
;
; 🔴 THE SECOND ONE ONLY MOVED BECAUSE A DEFECT WAS FIXED, AND THAT IS WORTH
; KEEPING HERE. dl_overflow's float arm stored NO ERRFLG at all, so `PRINT ERR`
; after `20 A=1E99` read a stale code -- while its sibling arm had been
; deliberately fixed to read 25. Measured on both references 2026-08-02: they
; read 6. The fix (TKOVF carries 6 instead of a bare flag, sub/tkfloat.asm) made
; the arms symmetric, deleted dl_overflow's branch, and only THEN was err_overflow
; migratable. docs/spec-basic-msgmigrate.md §6.4.
;
; ⚠️ D-MSGEXACT's note on why these two strings cannot SHARE storage still holds
; and now lives sub-side: ERR 6 is `Overflow` (capital) and ERR 25 is `Line buffer
; overflow` (lowercase tail), so one blob cannot spell a letter two ways. The
; overlap that D-LINEMAX relied on is arithmetically impossible, not merely
; unfashionable -- do not re-attempt it in sub/errmsg.asm either.

; --- S-FCH-2's sparse arm: DELETED (D-MSGMIGRATE) ---------------------------
; `rerr_sparse` (23 B here) and `rerr_sparse2` (27 B, basic/missing.asm) existed
; only to choose between five message strings for the out-of-dense codes
; 52/59/55/58/61. All five migrated to the sub-ROM tenant, at which point every
; arm of both routines read `ld hl,err_subhosted / jp raise_error_hl` -- which is
; exactly what `rerr_unprintable` (basic/interp.asm) already was. So raise_error's
; out-of-table test now jumps straight there and 50 B of dispatch is gone.
;
; ⚠️ WHAT HAD TO BE SHOWN UNCHANGED WAS THE TRAP DECISION, NOT THE MESSAGE. Both
; deleted arms ended at `jp raise_error_hl`, and so does rerr_unprintable, so
; 52/55/58/59/61 still trap into an armed ON ERROR handler exactly as D-NOTOPEN2
; measured on the CF-3300. The two raisers below are untouched: they enter through
; `raise_error`, never through the selector.
;
; 🎯 AND THE SELECTOR WAS ITS OWN REFUTATION. `rerr_sparse` opened with
; `ld a,(ERRFLG)` -- re-reading the error code rather than trusting A. That single
; line is what refutes the filed claim that these five were unmigratable "because
; rerr_sparse reaches them by its own `ld hl`, a different key". Same key.

; The two raisers. Sited here (not in files.asm/expr.asm) so page 1 pays nothing
; for them; reached by ordinary in-slot `jp` from page 1, both regions mapped.
; 🔴 D-MAXFTAIL (2026-09-07): oo_fail_bfn's own header calls this "main.asm's
; low region", and it is NOT — these sit at $7FEE, in page 1's TAIL. The claim
; cost a build: a body appended here on the strength of it landed in the scarce
; page. The genuine low region is the include block near the top of this file,
; above __MEAS_LOW_END, which is where mxf_require_end went instead.
oo_fail_bfn:                                ; OPEN's bad-file-number reject (ERR 52)
                xor     a                   ; -- same FCH_MODE clear oo_fail_syn does
                ld      (FCH_MODE),a        ; (the provisional mode must not survive
                                            ; a failed OPEN)
err_badfnum_raise:                          ; D-CHDIR: PRINT#/INPUT# the wrong way (52)
                ld      a,52
                jp      raise_error
err_notopen_raise:                          ; EOF()/LOF() on a closed channel (ERR 59)
                ld      a,59
                jp      raise_error

; D-MSGMIGRATE: err_bad_filenum (ERR 52) and err_file_notopen (ERR 59) are gone
; from main -- em_bad_filenum / em_file_notopen in sub/errmsg.asm. err_bad_filenum
; was one of MSGESC_FILE's two users; err_bad_filemode (basic/missing.asm) was the
; other, and it migrated too, so that phrase is deleted from msg_phrase_tab.
; (DT-6 (space plan B-9, 2026-10-05) then retired msg_phrase_tab itself and every escape but MSGESC_SUB:
; main's strings are plain text, so the leading-letter reasoning below is
; history -- the TEXT constraint it records still holds.)
;
; ⚠️ D-MSGEXACT's reading about ERR 59 is preserved because it still constrains the
; TEXT, which the move does not change: `File not OPEN` cannot use the "file "
; phrase, because the escapes deliberately exclude a message's LEADING letter so
; each message spells its own case, and here the phrase would be the first thing
; printed. Sub-side the point is moot -- the tenant stores plain strings -- but it
; is the reason the two messages ever differed in encoding.

; --- overflow guard: the image must not overrun the $8000 ceiling ----------
; $8000 is the top of slot-0 page 1. If a future feature pushes code past it, the
; pad below would be a *negative* `ds`, which pasmo assembles as a WARNING with
; exit 0 (a truncated/empty ROM) — a silent corruption the build would not catch.
; So assert first: on overflow this references an undefined symbol, forcing a
; clean ERROR (exit 1) whose NAME is the diagnostic. When it fits, the IF body
; emits nothing.
;
; ⚠️ The escape this used to name — "gate the feature on ROM_BASE" — no longer
; exists (S3, above): there is no second build to exclude a feature from. The
; remaining moves are to TRIM it or to EVICT it to a sub-ROM tenant
; (docs/subrom-tenant-playbook.md), which is what the diagnostic now says.
;
; Two checks: a moderate overrun leaves $ in $8001-$FFFF (caught by the first); a
; catastrophic one (>32 KB past the ceiling) wraps $ past 64 KB back below the org,
; where the location counter can never legitimately sit (caught by the second).
    IF $ > $8000
                db      BASIC_IMAGE_OVERRAN_8000_CEILING__TRIM_IT_OR_EVICT_TO_SUBROM
    ENDIF
    IF $ < BASIC_ORG
                db      BASIC_IMAGE_WRAPPED_PAST_64K__FEATURE_FAR_TOO_LARGE__SPLIT_IT
    ENDIF

; Measurement label (subrom wave-2 pre-gate, spec §7.1): page-1 free =
; $8000 - __MEAS_PAGE1_END. Emits no bytes; the wave-2 win — evicting the whole
; tokeniser to sub-ROM — shows up here as the page-1 tail growing. Read from the
; sym by check_reloc.py.
__MEAS_PAGE1_END:

; --- pad to the $8000 page ceiling -----------------------------------------
; Fill with $00 (not $FF): empty C-BIOS page 1 is $00, so when this image is
; shipped as a slot-0 page-1 *patch* (see build-patches.sh) the diff carries
; only zerobas's real code, not the padding. As a cartridge the fill byte is
; never executed, so $00 vs $FF is immaterial there.
                ds      $8000 - $, $00


; MAKING ROOM lever B: BASIC code in C-BIOS's own padding (page 0, same slot).
; Must come LAST -- it moves `org` below $2812; tools/split_islands.py cuts it out.
                include "basic/islands.asm"
