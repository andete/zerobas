; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — equates.inc
; ===========================================================================
; Shared constants for the built-in MSX2-style sub-ROM (docs/spec-basic-subrom.md).
; ===========================================================================

; --- Entry-table bases (the $4010-style fixed dispatch contract, §3c/D-5) -----
; One append-only `jp` table per page; a tenant is addressed by
; IX = base + 3*index. Page 0 tenants see main BASIC (slot-0 page 1) but not the
; BIOS and run under DI; page 1 tenants see the BIOS but not main BASIC. The two
; pages are opposite islands (§3b). Entry 0 of each is the S2a round-trip PING.
SUBROM_ENTRY_BASE_P0    equ     $0010   ; page-0 table (clear of the CD header)
SUBROM_ENTRY_BASE_P1    equ     $4010   ; page-1 table (mirrors the $4010 disk DSKIO)

; --- Page-0 tenant indices (append-only; IX = SUBROM_ENTRY_BASE_P0 + 3*index) --
; index 0 = the S2a round-trip PING (kept as a standing discovery self-check).
; index 1 = the WHOLE TOKENISER (WAVE 2 eviction, sub/tokenise.inc + the wave-1
; tk_float crunch sub/tkfloat.asm, now its in-slot callee); its main-ROM stub is
; basic/interp.asm `tokenise`. Wave 2 repurposed wave 1's per-literal tk_float
; entry into this whole-body entry (the float stub + per-literal CALSLT were
; reverted, spec §5) — the crunch is no longer a dispatch target, just an internal
; `jp tk_float` from the co-located loop. Never renumber an existing entry —
; a main-ROM stub hard-codes only its index.
; index 2 = the DETOKENISER CORE (WAVE 3 eviction, sub/detok.asm): the token->text
; walk (detok/dt_*/detok_op/detok_kw*/the number renderers) rewritten to append into
; DETOKBUF instead of streaming through pchar. Its main-ROM stub is basic/list.asm
; `detok`; the resident side drains DETOKBUF via print_string (honouring PRDEST, so
; the one core feeds both LIST->screen and ASCII-SAVE->disk). Reuses the co-located
; sub kwtable (shared with the wave-2 tokeniser -> the resident copy is now dropped,
; spec §2). docs/spec-basic-subrom-wave3-detok.md.
SUBROM_IDX_PING         equ     0
SUBROM_IDX_TOKENISE     equ     1
SUBROM_IDX_DETOK        equ     2
; index 3 = the INTERRUPT SELF-TEST tenant (trampoline slice, sub/sub.asm
; sub_int_selftest): a standing self-check that a page-0 tenant can run EI and
; have interrupts serviced through the sub-ROM's own $0038 trampoline. It reads
; JIFFY, EI's, spins past one 50/60 Hz frame, DI's, and stores the JIFFY delta in
; SUB_INT_DELTA; the subrom-inttest gate CALSLTs it and asserts delta >= 1 (which
; reads 0 if the trampoline is absent or the tenant left interrupts off).
; docs/spec-basic-subrom-trampoline.md.
SUBROM_IDX_INTTEST      equ     3
; index 4 = the ARRAY ENGINE tenant (arrays slice-1 SPLIT design, sub/
; arrays.asm ary_engine): docs/spec-basic-arrays.md §10. A pure-RAM leaf --
; ary_find/ary_alloc/ary_resolve (the descriptor walk, offset arithmetic,
; bound/negative/wrong-ndim checks, DIM allocation) -- reading the ARY_OP..
; ARY_ERR param block (basic/sysvars.inc §10.2). Its main-ROM stub is
; basic/arrays.asm `ary_engine_call` (ex_dim / ex_let_arr / ev_f_arr).
SUBROM_IDX_ARY          equ     4
; index 5 = the STRING HEAP tenant (arrays slice-4a, sub/strheap.asm
; strheap_engine): docs/spec-basic-arrays-slice4a-string-heap.md §9. A
; pure-RAM leaf -- heap_alloc (bump allocator on the downward frontier
; FRETOP) + GC (root enumeration over STRTAB/array elements/the temp-
; descriptor stack, then compaction) -- reading the SH_OP..SH_ERR param
; block (basic/sysvars.inc). Its main-ROM stub is basic/str-engine.asm
; `str_heap_alloc`. Also called IN-PAGE (no CALSLT) by sub/arrays.asm's
; aeng_copy_str (string array element store) and ary_alloc's own GC-before-
; OOM retry (§5.4), since both are co-resident in the same sub-ROM page-0
; image.
SUBROM_IDX_STRHEAP      equ     5
; index 6/7 = the PRINT USING FORMAT SCANNERS (eviction, sub/printusing.asm):
; pu_to_field (emit leading literals + identify the next field) and pu_emit_tail
; (emit trailing literals). Pure leaves over PU_* RAM + pchar -- the fragile value-
; render/deref paths (pu_do_number/pu_do_string/pu_fmt_int) stay resident. The two
; tenants render literals into DETOKBUF (sub-local pchar re-bind); their main-ROM
; stubs (basic/printusing.asm) drain DETOKBUF via print_string
; (honouring PRDEST, so the file form PRINT# USING is untouched). TOFIELD returns
; the no-field flag in A (0=field found, 1=none). docs/spec-evict-printusing.md.
SUBROM_IDX_PU_TOFIELD   equ     6
SUBROM_IDX_PU_TAIL      equ     7

; --- Page-1 tenant index kept in sync with basic/sysvars.inc (spec sync note) --
; SUBROM_IDX_FORMAT = 10 (basic/sysvars.inc SUBROM_ENTRY_BASE_P1 list, after
; SUBROM_IDX_RND=9): format_tenant (sub/format.asm), the CALL FORMAT eviction
; (docs/spec-evict-call-format.md). Unlike the page-0 indices above, page-1
; tenants are reached sub-side by their real label name (sub_p1_table's
; `jp format_tenant`), not by this index -- only the main-ROM stub computes
; `IX = SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FORMAT`. Defined here anyway so the
; two files never drift on the numeric value (spec §6 sync requirement).
SUBROM_IDX_FORMAT       equ     10
; index 11 = scan_stmt_end (error-handling S2b RESUME NEXT's statement-advance
; helper, sub/errtrap.asm), a pure-leaf tenant (docs/subrom-tenant-playbook.md
; §3A: walks only tokenised program RAM text, calls nothing in main). Args/
; result marshalled through RAM (SSE_IN/SSE_OUT/SSE_EOL, basic/sysvars.inc).
SUBROM_IDX_SCANSTMT     equ     11
; index 12 = fatprim_tenant (sub/fatprim.asm): the FAT12 primitive/sector
; layer (docs/spec-evict-diskfile-cluster.md §11, Phase 1 of the disk/file
; cluster eviction) -- ONE selector-dispatched entry covering all 15
; marshalled primitives (DISKOP_OP, basic/sysvars.inc, picks the routine;
; only the main-ROM stubs compute `IX = SUBROM_ENTRY_BASE_P1 +
; 3*SUBROM_IDX_FATPRIM`, same sync-note pattern as SUBROM_IDX_FORMAT above).
SUBROM_IDX_FATPRIM      equ     12
; index 13 = dirverb_tenant (sub/dirverb.asm): the directory-verb I/O bodies
; (docs/spec-evict-diskfile-cluster.md §12, Phase 2 of the disk/file cluster
; eviction) -- ONE selector-dispatched entry covering KILL's delete loop and
; NAME's dir-entry stamp (DISKOP_OP, basic/sysvars.inc, picks the body). Both
; bodies call the Phase-1 fatprim primitives (fat_delete / read_sector /
; fatprim_write_sector) SUB-LOCALLY, no marshalling. Only the main-ROM heads
; compute `IX = SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_DIRVERB`.
SUBROM_IDX_DIRVERB      equ     13
; index 14 = play_parse_tenant (sub/playparse.asm): the audio Slice-2a MML parser
; (docs/spec-basic-audio-play-slice2a.md). A pure RAM leaf -- reads the per-voice
; MML (ptr,len) from the VCBs + AUDIO_VMASK, parses each string into its VOICxQ
; ring buffer (own-design PLAY_OP_* packets), sets MUSICF last. Reached sub-side by
; label (sub_p1_table `jp play_parse_tenant`); only ex_play (basic/play.asm)
; computes IX = SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_PLAY_PARSE.
SUBROM_IDX_PLAY_PARSE   equ     14
; index 15 = lineedit_tenant (sub/lineedit.asm) -- see basic/sysvars.inc for
; the full comment (kept in sync there, spec sync note pattern).
SUBROM_IDX_LINEEDIT     equ     15
; index 16 = casmatch_tenant (sub/casmatch.asm): the cassette Tier-3 name-
; match / data-skip engine (docs/spec-eviction-g5-space.md) -- cas_open_match
; + cas_skip_data (basic/cload.asm), evicted whole to free page-1 tail space
; for the G5 PAINT slice. A pure RAM+BIOS leaf (TAPION/TAPIN + CAS_WANT*/
; CAS_HDRNAME/CAS_HDRID/CAL_BUF/CAL_CNT, all visible sub-side) -- no
; marshalling beyond a CM_STATUS byte (CF cannot ride back through
; subrom_call directly). Its main-ROM stub is basic/cload.asm
; `cas_open_match`. NOTE: 16 is the actual next-free index (15/LINEEDIT was
; the last taken at the time this spec was written -- the index-drift lesson
; from commit 136aee8, heeded here).
SUBROM_IDX_CASMATCH     equ     16

; show_title + banner_text (basic/title.asm), evicted to PAGE 1 to fund the
; input-devices I2 slice's measured 55 B page-1 deficit (docs/spec-basic-input-
; devices.md §9.5). Page 1 because its only edges are INITXT/CHPUT (page-0 BIOS,
; invisible to a page-0 tenant). No marshalling of any kind. Its main-ROM stub is
; basic/title.asm `show_title`. 17 is the next-free index (16/CASMATCH was last).
SUBROM_IDX_TITLE        equ     17

; build_83_name (basic/bload.asm), evicted to PAGE 1 to fund interrupt-traps T1
; (docs/spec-basic-interrupt-traps.md §10.4, D-T-8c/D-T-8d). Page 1 because the
; page-0 dispatch table is full to the $0038 vector; a page-1 tenant can't reach
; the resident upcase, so sub/fcbname.asm inlines a clone. Marshals HL/CF via
; BN_PTR/BN_STAT. Its main-ROM stub is basic/bload.asm `build_83_name` (repack
; branch). 18 is the next-free index (17/TITLE was last). Reached sub-side by
; label (sub_p1_table `jp fcbname_tenant`); only the stub computes
; IX = SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FCBNAME.
SUBROM_IDX_FCBNAME      equ     18

; errmsg_tenant (sub/errmsg.asm), D-MSGSUB: the fourteen ERR codes zerobas never
; RAISES but must still be able to PRINT -- 12/15/18/19 (dense holes) and
; 50/51/53/54/56/57/60/62/63/64 (sparse), plus the out-of-table `Unprintable
; error` fallback for everything else main routes here. PAGE 1 for title_tenant's
; reason (CHPUT is page-0 BIOS) AND because main's own printer is unreachable
; from either island -- print_string $4673 / print_msg $7717 are main page 1,
; which a page-1 CALSLT switches out, so duplicating the emitter here is
; contract-forced. Nothing marshals: the sole input is ERRFLG, already in RAM.
; docs/spec-basic-msgsub.md. 22 is the next-free PAGE-1 index (21/SAVE was last;
; the page-0 table is full to the $0038 vector). Reached sub-side by label
; (sub_p1_table `jp errmsg_tenant`); only basic/program.asm `pm_sub` computes
; IX = SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_ERRMSG.
SUBROM_IDX_ERRMSG       equ     22

; --- D-EVLNO (docs/spec-rom-region-evict-lineno.md) ---------------------------
; index 23 = parseln_tenant (sub/lineno.asm): the ASCII line-number scanner
; dl_store runs once per typed/loaded numbered line, evicted from main page 1 to
; open rank 4 of the ROM REGION STRUCTURE REVIEW (73 B out, 18 B stub back).
; PAGE 1 for a reason unlike every tenant above it: the body calls NOTHING AT ALL
; -- no BIOS, no main low region, no main page 1 -- so it is legal on EITHER
; island, and the tie is broken by capacity, the page-0 table being full to the
; $0038 vector. Marshals BC/HL out through PLN_NUM/PLN_PTR; HL rides in.
; Reached sub-side by label (sub_p1_table `jp parseln_tenant`); only
; basic/program.asm `parse_lineno` computes
; IX = SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_PARSELN.
SUBROM_IDX_PARSELN      equ     23

; --- S2a boot-gate scratch (page-3 RAM, visible from either sub-ROM page) ------
; The skeleton PING tenants write a page-tag byte here so the boot-gate probe can
; confirm a CALSLT to each entry round-tripped through the correct page. This is
; a fixed own-choice RAM cell in the repack-only free window ($F105, right after
; the float pack's last claim PLF_RA2 $F103 and below zerobas-disk's DRVA_DPB
; $F195 — see basic/sysvars.inc). S2a proves the mechanism by injection, so the
; main ROM does not yet reference this cell; S2b's dispatch stub will formalise
; the SUB_ARG/result marshalling block that starts here.
SUB_PING                equ     $F105   ; PING page tag: $C0 (page 0) / $C1 (page 1)
SUB_PING_P0             equ     $C0     ; written by the page-0 ping
SUB_PING_P1             equ     $C1     ; written by the page-1 ping

; --- Graphics arc, Slice G1 (page-0 tenant; docs/spec-basic-graphics-g1.md) ----
; index 8 = graphics_selftest / the SCREEN-2 geometry engine's page-0 island
; (sub/graphics.asm). Page-0 (EI-capable via the RAM interrupt trampoline) so a
; long draw keeps interrupts live -- music keeps playing (arc D1). Reached by
; IX = SUBROM_ENTRY_BASE_P0 + 3*8 = $0028; G1 ships only the floor (VDP port I/O
; primitives + the interrupt-under-draw self-test), no statement/token yet.
SUBROM_IDX_GRAPHICS     equ     8

; --- G7 eviction (page-0 tenants; docs/spec-eviction-g7-space.md) ------------
; index 9 = deftype_tenant (the G6 carve; full comment in basic/sysvars.inc).
; index 10 = readdata_tenant (sub/readdata.asm): the READ/DATA value engine
; (read_one_value + data_seek + data_parse_int), carved out of the resident to
; fund G7's sprite statements. Page-0 CLEAN: tokenised program RAM + ASCII
; parsing only -- no eval, no float pack, no BIOS.
SUBROM_IDX_READVAL      equ     10

; --- I1 funding carve (page-0 tenant; docs/spec-basic-input-devices.md §7) ---
; index 11 = beep_tenant (sub/beep.asm): the BEEP body (direct PSG blip + the
; busy-wait), carved out of the resident to fund the STICK/STRIG slice. Page-0
; CLEAN: port I/O and a counted delay only -- no BIOS, no low region. Its `ei`
; across the delay relies on the sub-ROM's own page-0 $0038 trampoline.
SUBROM_IDX_BEEP         equ     11

; --- D-CLP funding carve (page-0 tenant; docs/decision-clearpool-funding.md) --
; index 12 = fld_lookup_tenant (sub/fldlook.asm): the FIELDed-variable READ
; hook's pure-RAM half -- copy the record slice out of FSECTOR_BUF into FLD_DESC
; and wrap it as an RVDESC rvalue descriptor. Carved out of basic/field.asm to
; fund the CLEAR string-pool partition's 22 B of main page 1. The resident stub
; keeps fld_find + fch_select (shared services that could not move anyway) and
; passes the located entry pointer in HL. Page-0 CLEAN: RAM only -- mk_rvdesc,
; the one low-region callee of the original body, is inlined sub-side.
; ⚠️ THIS IS THE LAST PAGE-0 INDEX THAT FITS. The table starts at $0010 and the
; $0038 interrupt-trampoline vector is fixed, so 13 rows x 3 B = $0010..$0036
; leaves exactly ONE spare byte. Index 13 needs the table relocated (or the
; vector reached by a `jp` from a row), not just another line.
SUBROM_IDX_FLDLOOK      equ     12

; GFX_UNGUARDED: the G1 "teeth check" toggle (spec §4). Default 0 = the DI guard
; around the 2-byte VDP address latch is present (shipped). Building the sub-ROM
; with `pasmo --equ GFX_UNGUARDED=1` strips the guard, so the floor gate can
; confirm it then FAILs (latch race observed) -- proving the guarded pass is a
; real result, not a test that cannot fail. NEVER shipped =1.
    IFNDEF GFX_UNGUARDED
GFX_UNGUARDED           equ     0
    ENDIF
