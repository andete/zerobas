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
BASIC_ORG:      equ     $2812

; SUB_BUILD distinguishes this main-ROM assembly from sub/sub.asm, which shares
; several body .inc files with it (bload-body.inc's ,R handoff differs by side).
SUB_BUILD       equ     0
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

; The PRINT statement (defines `ex_print`, `print_number`, `print_crlf`).
                include "basic/print.asm"

; PRINT USING formatted output (defines `ex_print_using`; reuses print.asm's div10
; + pchar + the string layer), so it follows print.asm in the include order.
                include "basic/printusing.asm"

; Screen-setup verbs SCREEN/COLOR/CLS/WIDTH/KEY (defines `ex_screen`, …).
                include "basic/screen.asm"

; Audio slice 1 (docs/spec-basic-audio-play.md §3.D): the SOUND statement handler
; (defines `ex_sound`) — a small synchronous resident leaf that coerces/masks the
; register+value and writes the PSG directly. Lands in page 1 (which the disk/file
; eviction freed to ~1.1 KB) rather than the now-full reclaimed low region.
                include "basic/sound.asm"

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
; ⚠️ THE TWO STRINGS OVERLAP, AND THAT IS LOAD-BEARING, NOT A FLOURISH. ERR 25's
; text ENDS with ERR 6's text, so `err_overflow` is simply a pointer 12 bytes into
; `err_linebuf_overflow`: 23 bytes total instead of 34. That 11 bytes is not spare
; change here -- the split above needed 42 bytes against 10 free in page 1 and 32
; in the low region, and the overlap is what closed the gap and left both walls
; with margin instead of landing at exactly zero.
;
; ⚠️ CONSEQUENCE FOR ANY LATER EDIT: these are ONE string with two entry points.
; Re-wording ERR 25's tail, or ERR 6 at all, silently corrupts the other message
; -- and err_overflow has TWO readers (err_msgtab entry 6 and program.asm's
; dl_overflow float arm), neither of which is near this line. Split them back into
; two independent `db`s before changing either, and re-measure both walls.
; ⚠️ D-MSGENC (docs/spec-basic-msgenc-carve.md §4.4) DELIBERATELY LEFT THE OVERLAP
; ALONE. Phrase-encoding these as two independent strings costs 21 + 9 = 30 B
; against the 23 B they already share -- a 7 B LOSS sitting inside a column that
; still reads as a saving. All the slice takes here is §4.2's baked CRLF, which
; the overlap does not depend on: 23 B -> 21 B, and ERR 25 still falls through.
err_linebuf_overflow:
                db      "Line buffer "      ; ERR 25 (D-LINEMAX R-2) -- falls through
err_overflow:                               ; ERR 6 -- the shared tail, read on its own
                db      "overflow",0

; --- S-FCH-2: the SPARSE disk-range error codes (docs/spec-basic-filechan- ---
; alloc.md §5c, redesigned 2026-07-29). err_msgtab is DENSE and stops at 25;
; reaching 52/59 densely would cost 34 more words. These two codes are the only
; disk-range codes any zerobas verb raises, so raise_error's out-of-table arm
; comes here instead of straight to `rerr_unprintable`, and a two-entry
; straight-line compare beats both a dense extension and a walked side-table.
;
; Sited in the low region, whole: page 1 pays exactly ONE byte for this (the
; `jr` -> `jp` at raise_error's range test). Both raisers live here too, so the
; six OPEN reject sites in files.asm keep their existing 3-byte `jp cc,<label>`.
;
; ⚠️ BOTH CODES ARE ORDINARY TRAPPABLE ERRORS, and that is a MEASURED CORRECTION
; to §5c, which read the gate's `err_badchan` row as "ERR 52 is not trappable"
; and specced a raiser that forced ONEFLG=1 to reach raise_error's abort arm.
; Measured on the CF-3300 2026-07-29, two unconfounded ways:
;   `10 ON ERROR GOTO 100 : 20 OPEN"HI.TXT" FOR INPUT AS #2` -> handler runs, ERR 52
;   ...AS #0                                                 -> handler runs, ERR 52
;   `20 B=EOF(1)` on a never-opened channel                  -> handler runs, ERR 59
; The err_badchan row's non-trap is a CONFOUND: it types `MAXFILES=1` between the
; arm and the error, and MAXFILES (like a plain CLEAR) DISARMS the handler on the
; reference. So there is no forced abort here, no ONEFLG store, and §5c's open
; ONEFLG question does not arise on this path at all.
rerr_sparse:                                ; A = ERRCODE-1, CF set. Re-read the code
                ld      a,(ERRCODE)         ; rather than compare 51/58: the table
                                            ; bound and this arm are already "one fact
                                            ; in two places" once (err_msgtab's own
                                            ; comment, and it DRIFTED) -- 3 bytes buys
                                            ; a test that reads as the code it names.
                ld      hl,err_bad_filenum
                cp      52
                jr      z,rsp_go
                ld      hl,err_file_notopen
                cp      59
                jr      z,rsp_go
                jp      rerr_sparse2        ; D-NOTOPEN2's 55/58/61, then unprintable.
                                            ; Sited in page 1 (basic/missing.asm tail)
                                            ; because those three cost 72 B and THIS
                                            ; region is the hard wall -- so this line
                                            ; is a 0-byte change to the low region.
rsp_go:
                jp      raise_error_hl      ; the SHARED trap decision -- so 52/59 trap
                                            ; into an armed handler like every other
                                            ; code, which is what the reference does

; The two raisers. Sited here (not in files.asm/expr.asm) so page 1 pays nothing
; for them; reached by ordinary in-slot `jp` from page 1, both regions mapped.
oo_fail_bfn:                                ; OPEN's bad-file-number reject (ERR 52)
                xor     a                   ; -- same FCH_MODE clear oo_fail_syn does
                ld      (FCH_MODE),a        ; (the provisional mode must not survive
                                            ; a failed OPEN)
                ld      a,52
                jp      raise_error
err_notopen_raise:                          ; EOF()/LOF() on a closed channel (ERR 59)
                ld      a,59
                jp      raise_error

; D-MSGENC: new messages are phrase-encoded too. Neither of these can use any of
; the four ORIGINAL escapes, so this slice adds the fifth, MSGESC_FILE ("file "),
; which both of them share -- 30 B of literal text becomes 22 B plus a 6 B table
; entry. ⚠️ THE DIRECTION OF THAT TRADE WAS DECIDED BY THE MEASUREMENT, NOT BY
; THE ARITHMETIC: the phrase table is PAGE 1 and these strings are LOW REGION, so
; on the FIRST clean build (page 1 19 B free, low 1 B free) it spends the roomy
; wall to relieve the scarce one. Costed the other way round from an estimate it
; would have read as a 2-byte loss and been declined.
err_bad_filenum:
                db      "bad ",MSGESC_FILE,"number",0   ; ERR 52 -- 16 B -> 12 B
err_file_notopen:
                db      MSGESC_FILE,"not open",0        ; ERR 59 -- 14 B -> 10 B

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
