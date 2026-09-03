; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — sub.asm
; ===========================================================================
; The virtual zerobas machine's built-in MSX2-style sub-ROM: a standalone 32 KB
; ROM spanning BOTH pages of an internal expanded subslot (slot 3-2 on the
; merged/main machine; RAM stays 3-0, disk stays 3-1). It ships as a plain
; `.rom` like disk.rom — no C-BIOS interaction, no IPS splice, no relocation of
; stock code, so the output firewall (0 C-BIOS-leak bytes) is trivially clean.
; See docs/spec-basic-subrom.md and sub/PROVENANCE.md.
;
; ⚠️ THIS PARAGRAPH DESCRIBED THE S2a SKELETON AND WAS YEARS OF WORK OUT OF DATE
; (corrected 2026-09-03, D-DEFERSWEEP). It said: "an empty container that carries
; only the discovery signature and one round-trip PING per page. It has no real
; tenants yet — the first (float.asm's tokeniser+formatter) arrives with the
; S2b/eviction session ... The main ROM does not yet call in." Every clause of
; that is now false, and this is the sub-ROM's ENTRY file — the first thing a
; reader opens. `make basic-reloc` counts 15 page-0 tenants and 24 page-1 ones
; over 35 tenant sources here, and the main ROM reaches them through
; `subrom_call` from ~98 sites. The pings and the boot gate below are still real,
; but they are now the SKELETON UNDER a full building, not the building.
; A deferral is a promise with a trigger; nothing in this tree watched this one.
;
; TWO OPPOSITE ISLANDS (spec §3b). CALSLT switches only the called page, so:
;   * PAGE 0 ($0000-$3FFF) — while a page-0 tenant runs, slot-0 page 1 (main
;     BASIC) stays visible but the BIOS/low-region/ISR are switched out; run
;     under DI. Signature `CD` lives here at $0000.
;   * PAGE 1 ($4000-$7FFF) — while a page-1 tenant runs, the BIOS is visible but
;     main BASIC is switched out; may EI. Deliberately NOT an "AB" header at
;     $4000 (the cartridge/disk boot scan checks $4000 for 'A'/'B'; a passive
;     sub-ROM must not be CALSLTed as a cartridge — D-7).
; Pages 2/3 (program RAM, sysvars) stay visible from either page, so the PINGs
; can write their page tag to SUB_PING in RAM from both sides.
;
; CLEAN-ROOM: every byte here is own-design. Discovery convention (sub-ROMs
; carry `CD`, cartridges `AB`; EXBRSA $FAF8 records the sub-ROM slot) is from the
; MSX2 Technical Handbook / MSX Assembly Page (allowed). Nothing is derived from
; any stock ROM's code. See sub/PROVENANCE.md.
; ===========================================================================

                include "equates.inc"

; Shared RAM-cell addresses (TKPOS/TKDIG/TKPC/TKSRCSAVE/... used by tkfloat.asm),
; from the SAME sysvars.inc the merged main ROM uses, so a sub-ROM tenant's RAM
; scratch is byte-address-identical to the main ROM's — no marshalling translation.
; sysvars.inc is pure equates (emits no bytes), so it does not perturb this ROM's
; $0000-based layout.
;
; This file used to also define `ROM_BASE equ $2812` here, because sysvars.inc and
; the 20 other shared basic/*.inc files it pulls in carried `IF ROM_BASE` gates that
; had to be evaluated on THIS side too. Those gates are gone (RETIRE THE LEAN 16 KB
; CART S3, docs/spec-lean-retire-s3-gates.md §2.1) and nothing here reads the symbol
; any more. SUB_BUILD stays — it gates body .inc files that genuinely differ by side.
SUB_BUILD       equ     1   ; shared body .inc files that differ by side test this
                include "basic/sysvars.inc"

; ===========================================================================
; PAGE 0 — $0000-$3FFF (the callable-from-main region; `CD` signature)
; ===========================================================================
                org     $0000

; --- Sub-ROM signature (MSX2 sub-ROM ID; §3c/D-3) --------------------------
; `CD` at $0000 marks a sub-ROM (vs `AB` for a cartridge). init_ext_roms
; (S2b) RDSLT-checks $0000/$0001 for 'C'/'D' to discover and record our slot.
                db      "CD"                    ; $0000: sub-ROM signature
                dw      0                        ; $0002: INIT entry — none (passive
                                                 ;        callee, no boot CALSLT, D-7)
                dw      0                        ; $0004: reserved
                dw      0                        ; $0006: reserved
                dw      0,0,0,0                  ; $0008-$000F: reserved (RST area,
                                                 ;   unused — tenants run under DI)

; --- $0038 interrupt trampoline entry (subrom trampoline slice) ------------
; The maskable-interrupt vector for the page-0 island. While a page-0 tenant runs
; EI, an IRQ lands here with page 0 = sub-ROM; jump to the RAM-resident stub, which
; maps the BIOS back into page 0, runs the real ISR, and returns (see
; basic/subromcall.asm sub_int_template, docs/spec-basic-subrom-trampoline.md). One
; instruction, executed BEFORE any slot switch, so it never pages out its own
; continuation. SUB_INT_RAM is a fixed RAM address, so this `jp` is byte-identical
; every build and needs no relocation.
;
; ⚠️ THIS VECTOR IS WHY THE ENTRY TABLE NOW SITS ABOVE IT (D-P0BASE, docs/spec-
; rom-region-p0base.md). The table used to start at $0010 and grow UP INTO this
; fixed address: 13 rows filled $0010..$0036 and a 14th would have ended at $0039,
; on top of the vector. That capped the page-0 island at 13 tenants while 3913 B
; of its space sat free -- a capacity wall nobody had connected to the ROM REGION
; STRUCTURE REVIEW's "future evictions should prefer page 0" rule
; (docs/rom-region-structure-review.md §6). The base moved to $0040 instead.
    IF $ > $0038
                db      SUB_P0_HEADER_OVERRAN_0038__RESERVED_AREA_TOO_BIG
    ENDIF
                ds      $0038 - $, $FF          ; pad the reserved header up to the vector
                jp      SUB_INT_RAM             ; $0038: -> the RAM trampoline

; --- Page-0 entry table (append-only jp table; base $0040, §3c/D-5) --------
; IX = SUBROM_ENTRY_BASE_P0 + 3*index dispatches here. Index 0 = the S2a PING.
; Future page-0 tenants append below and never move an existing entry, so a
; main-ROM stub hard-codes only its index. The base is $0040, not $0010: past the
; fixed $0038 vector (see above), and a round number so `base + 3*index` is
; checkable by hand -- index 8 = $0058, index 12 = $0064. $003B..$003F is dead
; pad; so is $0010..$0037, which has the side benefit that the RST addresses
; $10/$18/$20/$28/$30 now land on $FF rather than mid-instruction inside a row.
;
; TWO ASSERTS, and they guard different things.
;
;  * the BASE assert is new with D-P0BASE: it is what stops the base being set
;    back below the vector, the only remaining way to re-create the collision
;    this layout exists to remove. Nothing checked that before.
;  * the DRIFT assert is the one the table has always carried -- the header above
;    must not push the table off its published base, because every main-ROM stub
;    computes the entry address from that base and NOTHING cross-checks the two
;    `equ` mirrors (sub/equates.inc and basic/sysvars.inc).
;
; ⚠️ THE DRIFT ASSERT IS `>`, NOT `-`, AND THAT IS LOAD-BEARING. It used to read
; `IF $ - SUBROM_ENTRY_BASE_P0` because the table began immediately after the
; 16-byte header, so `$` was either exactly the base or wrong. There is a `ds`
; pad in front of it now, and a pad FORCES `$` to the base -- which would make an
; equality test true by construction and the assert vacuous
; (docs/spec-rom-region-p0base.md §5.2 K2: the knife that found this was aimed at
; something else). `>` still judges: it is what a header growing past $0040 trips,
; and it fires before the `ds` is asked for a negative count.
    IF SUBROM_ENTRY_BASE_P0 <= $003A
                db      SUB_P0_BASE_BELOW_0038_VECTOR__TABLE_WOULD_CLOBBER_IT
    ENDIF
    IF $ > SUBROM_ENTRY_BASE_P0
                db      SUB_P0_HEADER_OVERRAN_ITS_BASE__TABLE_WOULD_DRIFT
    ENDIF
                ds      SUBROM_ENTRY_BASE_P0 - $, $FF   ; $003B..$003F: dead pad
sub_p0_table:
                jp      sub_p0_ping             ; index 0 (SUBROM_IDX_PING)
                jp      tokenise                ; index 1 (SUBROM_IDX_TOKENISE): the WHOLE
                                                ;   tokeniser (wave 2). The tk_float crunch
                                                ;   is no longer a dispatch entry — it is an
                                                ;   in-slot `jp tk_float` from tk_loop.
                jp      dtk_tenant              ; index 2 (SUBROM_IDX_DETOK): the LIST /
                                                ;   ASCII-SAVE detokeniser core (wave 3);
                                                ;   fills DETOKBUF, resident side drains it.
                jp      sub_int_selftest        ; index 3 (SUBROM_IDX_INTTEST): the interrupt
                                                ;   self-test — runs EI, verifies the $0038
                                                ;   trampoline serviced the timer (JIFFY++).
                jp      ary_engine              ; index 4 (SUBROM_IDX_ARY): the numeric-array
                                                ;   engine (arrays slice-1 SPLIT design,
                                                ;   docs/spec-basic-arrays.md §10) — a
                                                ;   pure-RAM leaf (descriptor walk, offset
                                                ;   arithmetic, alloc, bound checks). Main-ROM
                                                ;   stub is basic/arrays.asm `ary_engine_call`.
                jp      strheap_engine          ; index 5 (SUBROM_IDX_STRHEAP): the string
                                                ;   heap engine (arrays slice-4a, docs/spec-
                                                ;   basic-arrays-slice4a-string-heap.md §9) —
                                                ;   heap_alloc + GC compaction, a pure-RAM
                                                ;   leaf. Main-ROM stubs are basic/str-
                                                ;   engine.asm `call_strheap` + one SH_*
                                                ;   wrapper per op (op 0 ALLOC has none
                                                ;   any more -- D-SEEDPROSE).
                jp      pu_tofield_tenant       ; index 6 (SUBROM_IDX_PU_TOFIELD): PRINT USING
                                                ;   format scanner — emit leading literals +
                                                ;   identify the next field (docs/spec-evict-
                                                ;   printusing.md). Main stub basic/printusing.asm.
                jp      pu_tail_tenant          ; index 7 (SUBROM_IDX_PU_TAIL): PRINT USING
                                                ;   trailing-literal emitter. Both are pure
                                                ;   PU_*-RAM+pchar leaves; render into DETOKBUF.
                jp      graphics_tenant         ; index 8 (SUBROM_IDX_GRAPHICS): the SCREEN-2
                                                ;   geometry engine's page-0 island (graphics
                                                ;   arc). GFX_OP-selector dispatched (G2):
                                                ;   0=floor self-test (G1) 1=PSET/PRESET plot
                                                ;   2=POINT read. docs/spec-basic-graphics-g2.md.
                jp      deftype_tenant          ; index 9 (SUBROM_IDX_DEFTYPE): DEFINT/
                                                ;   DEFSNG/DEFDBL/DEFSTR (sub/deftype.asm),
                                                ;   carved out of the resident to fund G6
                                                ;   DRAW. docs/spec-eviction-g6-space.md.
                jp      readdata_tenant         ; index 10 (SUBROM_IDX_READVAL): the READ/DATA
                                                ;   value engine (sub/readdata.asm) -- carved
                                                ;   out to fund G7 sprites. Result rides back
                                                ;   in RDV_ST/RDV_VAL (registers cannot);
                                                ;   D-READVAR added the RDV_MODE INPUT cell
                                                ;   (numeric int16 / raw span -> STRSCR) and a
                                                ;   third RDV_ST value, 2 = not a number.
                                                ;   docs/spec-eviction-g7-space.md,
                                                ;   docs/spec-basic-readvar.md.
                jp      beep_tenant             ; index 11 (SUBROM_IDX_BEEP): the BEEP
                                                ;   body (sub/beep.asm) -- carved out to
                                                ;   fund input-devices slice I1. No args,
                                                ;   no result, cannot fail.
                                                ;   docs/spec-basic-input-devices.md §7.
                jp      fld_lookup_tenant       ; index 12 (SUBROM_IDX_FLDLOOK): the
                                                ;   FIELDed-variable READ hook's pure-RAM
                                                ;   half (sub/fldlook.asm) -- carved out
                                                ;   of basic/field.asm to fund D-CLP.
                                                ;   HL = the located field-table entry.
                jp      lrset_store_tenant      ; index 13 (SUBROM_IDX_LRSETST): the
                                                ;   LSET/RSET record-field STORE
                                                ;   (sub/lrsetst.asm) -- carved out of
                                                ;   basic/field.asm to fund D-FLDARY.
                                                ;   No args, no result: every input is
                                                ;   already a RAM cell (LRSET_DEST/W/
                                                ;   JUST, STRPTR, FSECTOR_BUF).
                                                ; ⚠️ 14 rows = $0040..$0069. This is the
                                                ;   FIRST index past the old $0038
                                                ;   ceiling: the table grew up into the
                                                ;   fixed vector until D-P0BASE moved
                                                ;   the base above it, and index 12's
                                                ;   note ("INDEX 13 IS FREE and the
                                                ;   table has no cap") is now cashed.

                jp      deffn_tenant            ; index 14 (SUBROM_IDX_DEFFN): DEF FN's
                                                ;   PARSE (sub/deffn.asm) -- D-DEFFNEV.
                                                ;   A CALSLT is not resumable, so this is
                                                ;   re-entered once per bounce and recovers
                                                ;   its phase from L.

                jp      pu_sign_tenant          ; index 15 (SUBROM_IDX_PUSIGN): PRINT
                                                ;   USING's `+`/`-` sign placement
                                                ;   (D-PUSIGN, docs/spec-basic-pufloat.md).
                                                ;   Pure RAM -- NUMBUF in, NUMBUF out,
                                                ;   the new length in A -- so it meets the
                                                ;   page-0 closure rule with nothing to
                                                ;   marshal.

; --- Page-0 PING (S2a boot-gate tenant) -----------------------------------
; Proves a CALSLT to SUBROM_ENTRY_BASE_P0 mapped slot 3-2 into PAGE 0 and that
; page-3 RAM is reachable from there: stamp SUB_PING with the page-0 tag and
; return. The distinct tag ($C0 vs the page-1 $C1) is what proves page-correct
; mapping — the two pings live in different pages of the same subslot, so only a
; page-selective CALSLT reaches each.
;
; Its address is immaterial -- it is reached only through its own `jp` row in the
; table above. (It used to carry a note explaining why it sat AFTER the $0038
; vector; the table sits after the vector now too, so the note said nothing.)
sub_p0_ping:
                ld      a,SUB_PING_P0
                ld      (SUB_PING),a
                ret


; --- Interrupt self-test tenant (index 3; the subrom-inttest gate) ---------
; A standing self-check that this page-0 island is interrupt-live. Entered under DI
; by CALSLT (spec §2.2 opt-in = EI after entry, DI before ret): read JIFFY, EI, spin
; well past one 50/60 Hz frame (~1.7 M cycles), DI, store the JIFFY delta in
; SUB_INT_DELTA. With the trampoline installed the timer ISR runs through the
; sub-ROM $0038 -> RAM stub, so the delta is >= 1; with it absent (or if the tenant
; stayed DI) it is 0. A byte delta suffices (~24-28 ticks < 256).
sub_int_selftest:
                ld      a,(JIFFY)               ; JIFFY low byte before
                ld      b,a
                ei
                ld      hl,0
sis_spin:
                dec     hl                      ; 0 -> 65536 iters (~1.7 M cycles) >> one frame
                ld      a,h
                or      l
                jr      nz,sis_spin
                di
                ld      a,(JIFFY)               ; JIFFY low byte after
                sub     b                       ; delta (mod 256; >= 1 if the timer ticked)
                ld      (SUB_INT_DELTA),a
                ret

; --- Page-0 tenants -------------------------------------------------------
; WAVE 2 (index 1 = tokenise): the WHOLE tokeniser body, evicted from the repack
; main ROM's basic/interp.asm and reunited here with the wave-1 tk_float literal
; crunch. It is pure buffer computation over page-2/3 RAM — no BIOS / low-region /
; ISR touch (leaf-audit, spec §3) — so it is a valid page-0 tenant run under DI.
; Its only non-RAM callees are pure leaves co-resident in this page:
;   * upcase / cmp16_bits / neg_de  — clones in tkfloat.asm (below).
;   * is_letter                     — clone right below (the tokeniser's
;                                     identifier path; not needed by the crunch).
;                                     ⚠️ is_ident_cont USED to be cloned beside
;                                     it and is gone — D-CNAME's CALL device-name
;                                     range test was its last caller sub-side
;                                     (docs/spec-basic-cname.md §3.1).
;   * tk_float                      — the wave-1 crunch, now reached by an ordinary
;                                     in-slot `jp tk_float` from tk_loop (wave 1's
;                                     per-literal CALSLT + disposition protocol were
;                                     reverted, spec §5).
;   * kwtable                       — a byte-identical DUPLICATE of the resident
;                                     repack copy (§4: the resident copy stays for
;                                     LIST/detok, which is I/O-bound and can't go
;                                     sub-side; a page-0 tenant can't see the
;                                     main-ROM low region either, so it needs its
;                                     own copy). Same kwtable.inc + same org
;                                     gating -> the two images can't drift.
                include "tkfloat.asm"
                include "basic/tokenise.inc"

; WAVE 3 (index 2 = detok): the LIST / ASCII-SAVE detokeniser core, evicted from
; the repack main ROM's basic/list.asm. Re-binds pchar/print_string/div10 to
; DETOKBUF appends and shares the co-located kwtable with the tokeniser above (so
; the resident kwtable is dropped). Its resident stub is basic/list.asm `detok`.
                include "detok.asm"

; ARRAYS SLICE-1 SPLIT (index 4 = ary_engine): the numeric-array engine
; (docs/spec-basic-arrays.md §10), moved whole into the sub-ROM because it
; overran the repack ROM by ~284 B as a monolithic main-ROM feature. Pure-RAM
; leaf: no BIOS / low-region / main-ROM-resident touch (leaf-audit, §10.1) —
; calls nothing outside this file. Its own header has the full rationale.
                include "arrays.asm"

; ARRAYS SLICE-4a (index 5 = strheap_engine): the string heap engine (docs/
; spec-basic-arrays-slice4a-string-heap.md), a sibling pure-RAM leaf sharing
; this page with the array engine above (co-resident, so aeng_copy_str/
; ary_alloc can call its heap_alloc/strheap_gc entry points directly, no
; CALSLT). Its own header has the full rationale.
                include "strheap.asm"

; PRINT USING format scanners (index 6/7 = pu_tofield_tenant / pu_tail_tenant):
; the two pure PU_*-RAM+pchar leaves evicted from basic/printusing.asm to free
; page-1 window space (docs/spec-evict-printusing.md). Reuses detok.asm's
; sub-local pchar (DETOKBUF append), included above — so this must follow it.
                include "printusing.asm"

; GRAPHICS ARC SLICE G1 (index 8 = graphics_selftest): the SCREEN-2 geometry
; engine's page-0 island — the VDP direct-port I/O floor + its interrupt-under-
; draw self-test (docs/spec-basic-graphics-g1.md). Self-contained: touches only
; the VDP ports + page-3 RAM result cells, calls nothing else in this file.
                include "graphics.asm"
                include "deftype.asm"
; --- READ/DATA value engine (G7 eviction, docs/spec-eviction-g7-space.md) ---
; The largest of the three carves that fund G7's resident half. Its body is the
; shared basic/readdata-body.inc, and it brings page 0 its own tok_skip copy
; (basic/tokskip-body.inc).
                include "readdata.asm"
; --- BEEP body (I1 funding carve, docs/spec-basic-input-devices.md §7) -------
; Direct PSG blip + busy-wait; no shared .inc, since BEEP has no resident copy to
; stay in step with.
                include "beep.asm"
; --- FIELDed-variable READ hook (D-CLP funding carve, docs/decision-clearpool-
; funding.md). A pure RAM leaf: the resident stub (basic/field.asm) has already
; located the field-table entry and selected its channel, so this side only
; copies the record slice into FLD_DESC and builds the RVDESC descriptor. No
; shared .inc -- there is no resident twin of this shape.
                include "fldlook.asm"
; --- LSET/RSET record-field STORE (D-FLDARY funding carve, docs/spec-basic-
; fldary.md §6.4). The other pure RAM leaf of the same FIELD layer: the resident
; stub (basic/field.asm) has already selected the channel, so this side only
; space-fills the field and copies the value in. No shared .inc -- there is no
; resident twin of this shape any more; pu_deref_body, its one low-region
; callee, is inlined here in 5 B.
                include "lrsetst.asm"
                include "deffn.asm"

; --- sub-local is_letter (byte-identical own-design clone) ------------------
; The resident copy stays in the main ROM (basic/interp.asm) for the rest of the
; interpreter; a page-0 tenant can't reach it, so the tokeniser's identifier path
; uses this co-located clone. is_letter -> upcase (tkfloat.asm).
;
; ⚠️ THE is_ident_cont CLONE THAT USED TO SIT HERE IS GONE, AND THE DEAD-CODE
; GATE IS WHY (D-CNAME §3.1, docs/spec-basic-cname.md). basic/vars.asm is NOT
; included by this file, so basic/tokenise.inc's tcn_name was the clone's ONLY
; caller anywhere sub-side; D-CNAME's range test replaced that call, which
; orphaned 16 bytes, and `make basic-reloc`'s hard dead-code gate (0 dead, both
; builds) fails the build rather than shipping them. The deletion was FORCED by
; measurement, not argued -- knife K6 restores the clone with no caller and the
; build is what goes red.
;
; is_letter itself keeps a caller (basic/tokenise.inc tk_notkw), which is why it
; survives the same edit. The main ROM's own is_ident_cont (basic/vars.asm) keeps
; all three of its callers and is untouched.
is_letter:
                push    af
                call    upcase
                cp      'A'
                jr      c,sil_no
                cp      'Z'+1
                jr      nc,sil_no
                pop     af
                scf
                ret
sil_no:
                pop     af
                or      a                   ; CF clear
                ret

; --- sub-local keyword table (duplicate of the resident repack copy, §4) -----
; Assembled from the SAME basic/kwtable.inc as the
; resident repack copy, so the two are byte-identical by construction; the reloc
; build's byte-identity assert (tools/check_reloc.py) is the standing guard.
                include "basic/kwtable.inc"

; --- pad page 0 to the $4000 boundary --------------------------------------
; __MEAS_SUB_P0_END is a ZERO-BYTE measurement label: page-0 free space is
; $4000 - __MEAS_SUB_P0_END, read out of build/sub.sym by
; tools/check_sub_walls.py on every `make basic-reloc` (docs/spec-subwall-
; readout.md). It is the sub-ROM twin of basic/'s __MEAS_LOW_END /
; __MEAS_PAGE1_END, and it lands here because for the sub ROM's whole life the
; two walls had no gated readout at all: every figure was hand-measured per
; slice, and two of them were wrong -- D-LPTVERB's own `kwtable` entries cost
; 17 B of THIS page while its as-built table recorded "sub sides unchanged".
;
; ⚠️ THE LABEL, NOT A TRAILING-$FF SCAN, IS THE MEASUREMENT. This page pads with
; $FF, not $00, so a byte scan cannot tell pad from content that happens to end
; in $FF and can only ever OVER-report. The checker prints both and treats
; scan < label as proof the .sym and the .rom are from different builds.
__MEAS_SUB_P0_END:
                ds      $4000 - $, $FF

; ===========================================================================
; PAGE 1 — $4000-$7FFF (the BIOS-visible island; NOT an "AB" header)
; ===========================================================================
; $4000 deliberately holds a non-"AB" marker: try_init_slot RDSLT-checks $4000
; for 'A'/'B' on every expanded secondary (including 3-2), and a passive sub-ROM
; must not be picked up as a bootable cartridge (D-7). "S1" = sub-ROM page 1.
                db      "S1"                    ; $4000: page-1 marker (NOT 'A','B')
                dw      0                        ; $4002: reserved
                dw      0                        ; $4004: reserved
                dw      0                        ; $4006: reserved
                dw      0,0,0,0                  ; $4008-$400F: reserved

; --- Page-1 entry table (append-only jp table; base $4010, §3c/D-5) --------
; Mirrors the $4010 disk-DSKIO offset so a page-1 CALSLT looks exactly like the
; disk case the codebase already runs. Index 0 = the S2a PING.
    IF $ - SUBROM_ENTRY_BASE_P1
                db      SUB_P1_TABLE_NOT_AT_4010__HEADER_SIZE_DRIFT
    ENDIF
sub_p1_table:
                jp      sub_p1_ping             ; index 0: round-trip ping
                jp      fp_sqrt                 ; index 1 (SUBROM_IDX_SQR): SQR(x)'s
                                                ;   Heron/Newton body (math-pack slice
                                                ;   1b), migrated from main-ROM page-0
                                                ;   low (docs/spec-basic-subrom-
                                                ;   mathpack.md). Main-ROM stub is
                                                ;   basic/expr.asm `evmc_sqr`.
                jp      fp_atan                 ; index 2 (SUBROM_IDX_ATN): ATN(x)'s
                                                ;   reduction + minimax-polynomial body
                                                ;   (math pack slice 2a, docs/spec-
                                                ;   basic-mathpack-slice2.md §11) -- the
                                                ;   FIRST transcendental tenant. Main-ROM
                                                ;   stub is basic/expr.asm `evmc_atn`.
                jp      fp_exp                  ; index 3 (SUBROM_IDX_EXP): EXP(x)'s
                                                ;   table-assisted range reduction +
                                                ;   minimax-polynomial body (math pack
                                                ;   slice 2b, docs/spec-basic-mathpack-
                                                ;   slice2.md §12). Main-ROM stub is
                                                ;   basic/expr.asm `evmc_exp`.
                jp      fp_log                  ; index 4 (SUBROM_IDX_LOG): LOG(x)'s
                                                ;   split + breakpoint-table reduction +
                                                ;   minimax-polynomial body (math pack
                                                ;   slice 2b, docs/spec-basic-mathpack-
                                                ;   slice2.md §12). Main-ROM stub is
                                                ;   basic/expr.asm `evmc_log`.
                jp      fp_pow                  ; index 5 (SUBROM_IDX_POW): `^`'s
                                                ;   int-path square-and-multiply /
                                                ;   frac-path EXP(y*LOG(x)) body (math
                                                ;   pack slice 2c, docs/spec-basic-
                                                ;   mathpack-slice2.md §13). Main-ROM
                                                ;   stub is basic/float-arith.asm
                                                ;   `combine_pow`.
                jp      fp_sin                  ; index 6 (SUBROM_IDX_SIN): SIN(x)'s
                                                ;   sincos_kernel + quadrant-select
                                                ;   (math pack slice 2d, docs/spec-
                                                ;   basic-mathpack-slice2.md §14).
                                                ;   Main-ROM stub is basic/expr.asm
                                                ;   `evmc_sin`.
                jp      fp_cos                  ; index 7 (SUBROM_IDX_COS): COS(x),
                                                ;   same sincos_kernel (math pack
                                                ;   slice 2d, §14). Main-ROM stub is
                                                ;   basic/expr.asm `evmc_cos`.
                jp      fp_tan                  ; index 8 (SUBROM_IDX_TAN): TAN(x) =
                                                ;   SIN(x)/COS(x) (math pack slice 2d,
                                                ;   §14). Main-ROM stub is basic/
                                                ;   expr.asm `evmc_tan`.
                jp      fp_rnd                  ; index 9 (SUBROM_IDX_RND): RND(x)'s
                                                ;   14-digit BCD LCG advance (math
                                                ;   pack slice 2e, docs/spec-basic-
                                                ;   mathpack-slice2.md §15). LAST
                                                ;   slice-2 tenant. Main-ROM stub is
                                                ;   basic/expr.asm `evmc_rnd`.
                jp      format_tenant           ; index 10 (SUBROM_IDX_FORMAT): CALL
                                                ;   FORMAT's sector-build/write bulk
                                                ;   (docs/spec-evict-call-format.md),
                                                ;   evicted to fund error-handling
                                                ;   S2b. A SPLIT design (not a whole
                                                ;   leaf): the interactive menu +
                                                ;   dispatch stay main-resident
                                                ;   (basic/format.asm `do_format`);
                                                ;   this tenant is the pure geometry
                                                ;   -driven build/write engine, with
                                                ;   its own sub-local CALSLT write
                                                ;   path (main's write_sector is
                                                ;   page-1-main-resident, invisible
                                                ;   here).
                jp      scan_stmt_end           ; index 11 (SUBROM_IDX_SCANSTMT):
                                                ;   RESUME NEXT's quote-aware
                                                ;   statement-advance (sub/
                                                ;   errtrap.asm, docs/spec-basic-
                                                ;   error-handling-s2b-packet.md
                                                ;   §5.5) -- a PURE LEAF (playbook
                                                ;   §3A): walks only tokenised
                                                ;   program RAM text, calls
                                                ;   nothing in main. Main-ROM
                                                ;   stub is basic/interp.asm
                                                ;   `ex_resume`'s res_next arm.
                jp      fatprim_tenant          ; index 12 (SUBROM_IDX_FATPRIM):
                                                ;   the FAT12 primitive/sector
                                                ;   layer (docs/spec-evict-
                                                ;   diskfile-cluster.md §11,
                                                ;   Phase 1) -- ONE selector-
                                                ;   dispatched entry (DISKOP_OP
                                                ;   picks the routine) covering
                                                ;   all 15 marshalled
                                                ;   primitives, a pure
                                                ;   RAM+BIOS(CALSLT) leaf like
                                                ;   format_tenant/scan_stmt_end.
                                                ;   Main-ROM stubs are the
                                                ;   resident shims in
                                                ;   basic/fat.asm (repack).
                jp      dirverb_tenant          ; index 13 (SUBROM_IDX_DIRVERB):
                                                ;   the KILL/NAME directory-verb
                                                ;   I/O bodies (docs/spec-evict-
                                                ;   diskfile-cluster.md §12,
                                                ;   Phase 2) -- ONE selector-
                                                ;   dispatched entry (DISKOP_OP
                                                ;   picks KILL's delete loop vs
                                                ;   NAME's dir-entry stamp), each
                                                ;   calling the Phase-1 fatprim
                                                ;   primitives sub-locally. Main-
                                                ;   ROM heads are the repack
                                                ;   ELSE branches of do_kill/
                                                ;   do_name (basic/files.asm).
                jp      play_parse_tenant       ; index 14 (SUBROM_IDX_PLAY_PARSE):
                                                ;   the audio Slice-2a MML parser
                                                ;   (sub/playparse.asm) -- a pure
                                                ;   RAM leaf turning up to three MML
                                                ;   voice strings into PLAY_OP_*
                                                ;   packet queues (VOICxQ) + MUSICF.
                                                ;   Its main-ROM head is ex_play
                                                ;   (basic/play.asm).
                jp      lineedit_tenant         ; index 15 (SUBROM_IDX_LINEEDIT):
                                                ;   the numbered-line editor's
                                                ;   TXTTAB-memmove engine (docs/
                                                ;   spec-eviction-g4-space.md §4,
                                                ;   carve #2) -- LE_OP-selector
                                                ;   dispatched (0=store/delete via
                                                ;   SL_NUM/SL_TOK, 1=relink-only).
                                                ;   Calls vars_reset (resident-ABI
                                                ;   import). Main-ROM stubs are
                                                ;   basic/program.asm `store_line`/
                                                ;   `relink`.
                jp      casmatch_tenant         ; index 16 (SUBROM_IDX_CASMATCH):
                                                ;   the cassette Tier-3 name-match/
                                                ;   data-skip engine (docs/spec-
                                                ;   eviction-g5-space.md) -- a pure
                                                ;   RAM+BIOS leaf (TAPION/TAPIN +
                                                ;   CAS_WANT*/CAS_HDRNAME/CAS_HDRID/
                                                ;   CAL_BUF/CAL_CNT), no resident-ABI
                                                ;   import. Reports back via
                                                ;   CM_STATUS (subrom_call clears CF
                                                ;   on return, so it can't ride
                                                ;   back directly). Main-ROM stub is
                                                ;   basic/cload.asm `cas_open_match`.
                jp      title_tenant            ; index 17 (SUBROM_IDX_TITLE): the
                                                ;   startup header (show_title +
                                                ;   banner_text). Page-1 because it
                                                ;   calls INITXT/CHPUT. No args, no
                                                ;   result, no RAM state -- the
                                                ;   simplest tenant here. Main-ROM
                                                ;   stub is basic/title.asm
                                                ;   `show_title`, which needs no
                                                ;   absent-sub-ROM error path (no
                                                ;   header printed is a fine
                                                ;   degradation).
                jp      fcbname_tenant          ; index 18 (SUBROM_IDX_FCBNAME): the
                                                ;   disk 8.3-FCB-name builder
                                                ;   (build_83_name), evicted to fund
                                                ;   interrupt-traps T1 (docs/spec-
                                                ;   basic-interrupt-traps.md §10.4).
                                                ;   Page-1 (the page-0 table is full
                                                ;   to the $0038 vector); a pure RAM
                                                ;   leaf with an inlined upcase.
                                                ;   Marshals HL/CF via BN_PTR/BN_STAT.
                                                ;   Main-ROM stub is basic/bload.asm
                                                ;   `build_83_name` (repack branch).
                jp      circleparse_tenant      ; index 19 (SUBROM_IDX_CIRCLEPARSE):
                                                ;   CIRCLE's grammar walk + angle/aspect
                                                ;   float math, evicted as an eval-bounce
                                                ;   co-routine (docs/spec-circle-
                                                ;   coroutine-space.md) to reclaim ~542 B
                                                ;   of resident page-1 for the interrupt-
                                                ;   trap arc. Reaches the low-region float
                                                ;   pack (fp_sqrt pattern); bounces
                                                ;   eval/parse_coord to ex_circle.
                jp      bload_tenant            ; index 20 (SUBROM_IDX_BLOAD): the whole
                                                ;   BLOAD verb body -- device dispatch,
                                                ;   the cassette load loop and the disk
                                                ;   load loop (docs/spec-traps-t3-key.md
                                                ;   §7.6), evicted from main page 1 to
                                                ;   fund interrupt-traps T3. PAGE 1 on
                                                ;   purpose: it sits beside fatprim and
                                                ;   calls fat_mount/fat_find/fat_open/
                                                ;   fat_read_file_sector SUB-LOCALLY,
                                                ;   which is what makes the carve
                                                ;   possible. Main-ROM stub is
                                                ;   basic/bload.asm `do_bload`; the ,R
                                                ;   handoff stays resident there.
                jp      save_tenant             ; index 21 (SUBROM_IDX_SAVE): BLOAD's
                                                ;   MIRROR -- the four SAVE-family WRITE
                                                ;   engines (BSAVE/disk, BSAVE/tape,
                                                ;   SAVE/disk, and the shared cassette
                                                ;   tokenised writer), evicted from main
                                                ;   page 1 to fund `TIME` + interrupt-
                                                ;   traps T5 from one carve (docs/
                                                ;   decision-fund-time-and-t5.md).
                                                ;   PAGE 1 beside fatprim, whose WRITE
                                                ;   primitives it calls sub-locally.
                                                ;   The PARSE stays resident (it uses
                                                ;   `eval`), so nothing rides but the
                                                ;   SV_OP selector and SV_STAT.
                jp      errmsg_tenant           ; index 22 (SUBROM_IDX_ERRMSG): the
                                                ;   fourteen ERR codes zerobas never
                                                ;   RAISES but must still be able to
                                                ;   PRINT, plus the out-of-table
                                                ;   `Unprintable error` fallback for
                                                ;   every other code main routes here
                                                ;   (D-MSGSUB, docs/spec-basic-msgsub.md).
                                                ;   PAGE 1 for title_tenant's reason --
                                                ;   CHPUT is page-0 BIOS -- and because
                                                ;   main's own printer is main PAGE 1 and
                                                ;   so unreachable from EITHER island.
                                                ;   NOTHING MARSHALS: the sole input is
                                                ;   ERRFLG, already in RAM. Main stub is
                                                ;   the MSGESC_SUB arm of print_msg_stopcr
                                                ;   (basic/program.asm `pm_sub`).
                jp      parseln_tenant          ; index 23 (SUBROM_IDX_PARSELN): the ASCII
                                                ;   line-number scanner dl_store runs once
                                                ;   per typed/loaded numbered line, evicted
                                                ;   from main page 1 to open rank 4 of the
                                                ;   ROM REGION STRUCTURE REVIEW (D-EVLNO,
                                                ;   docs/spec-rom-region-evict-lineno.md).
                                                ;   PAGE 1 for a reason unlike any row
                                                ;   above: the body calls NOTHING AT ALL,
                                                ;   so it is legal on either island -- and
                                                ;   the PAGE-0 TABLE ABOVE IS FULL, which
                                                ;   is what actually decides it. Marshals
                                                ;   BC/HL out through PLN_NUM/PLN_PTR.

; --- Page-1 PING (S2a boot-gate tenant) -----------------------------------
; Proves a CALSLT to $4010 mapped slot 3-2 into PAGE 1 (main BASIC switched out,
; BIOS in) and that page-3 RAM is still reachable: stamp SUB_PING with the
; page-1 tag and return.
sub_p1_ping:
                ld      a,SUB_PING_P1
                ld      (SUB_PING),a
                ret

; --- Page-1 tenants ---------------------------------------------------------
; fp_sqrt (math-pack slice 1b -> subrom-mathpack migration, 2026-07-13): the
; FIRST page-1 tenant and the FIRST non-leaf tenant (calls back into main-ROM-
; resident code across the CALSLT via the imported resident ABI below). See
; docs/spec-basic-subrom-mathpack.md and this cluster's own header comment
; (moved verbatim from basic/float-arith.asm, only the FACTYP/DE finalization
; removed — now done by the caller, evmc_sqr, per §3/§4).
;
; Resident-ABI import (spec §4): the 9 addresses below are generated by
; tools/gen_resident_abi.py from build/basic-reloc.sym on every build (Makefile
; rule), so a page-0-low shift can never leave this ROM calling stale
; addresses — the build-order dependency (basic-reloc.sym -> this .inc ->
; sub.rom) forces a regen, and `make subrom-abi-check` is a standing strong
; consistency gate (re-diffs the shipped sub.rom against a fresh regen).
                include "basic-resident-abi.inc"

                include "fp_sqrt.asm"

; fp_atan (math pack slice 2a, docs/spec-basic-mathpack-slice2.md §11): the
; SECOND page-1 tenant and the FIRST transcendental. Reuses the identical
; resident-ABI import above (its own callee list is a SUBSET of fp_sqrt's --
; no new symbols needed) and math-coeffs.inc's generated FPNUM constant
; records (own decimal minimax, tools/gen_math_coeffs.py -- never the MSX
; ROM's own coefficients, which are binary-format anyway).
                include "math-coeffs.inc"
                include "fp_atan.asm"

; fp_exp + fp_log (math pack slice 2b, docs/spec-basic-mathpack-slice2.md
; §12): the THIRD and FOURTH page-1 tenants, delivered as a matched pair --
; both reuse fp_atan.asm's fat_copy18/fp_poly_horner directly (same
; assembly unit) and fp_exp.asm's own new fexp_cmp16/fexp_tbl18addr helpers
; (fp_log.asm calls the latter too, see each file's own header for the
; reuse rationale). Same math-coeffs.inc (already included above) supplies
; EXP_COEF/LOG_COEF/EXP_RC/EXP_C1/EXP_C2/LN10_C1/LN10_C2/POW8_TBL/EXP_TCOR/
; LNK_TBL/NEGLNK_TBL/LOG_BP.
                include "fp_exp.asm"
                include "fp_log.asm"

; fp_pow (math pack slice 2c, docs/spec-basic-mathpack-slice2.md §13): the
; FIFTH page-1 tenant, the `^` operator. Reuses fp_atan.asm's fat_copy18
; directly (same assembly unit) and, for its fractional path, calls
; fp_exp/fp_log DIRECTLY (same assembly unit, both already included above)
; -- the first tenant-to-tenant composition, no nested subrom_call. Same
; resident-ABI surface subset as the other page-1 tenants; no new
; math-coeffs.inc constants (POW needs none of its own).
                include "fp_pow.asm"

; fp_sin (math pack slice 2d, docs/spec-basic-mathpack-slice2.md §14): the
; SIXTH/SEVENTH/EIGHTH page-1 tenants (fp_sin/fp_cos/fp_tan, one body file
; sharing the sincos_kernel). Reuses fp_atan.asm's fat_copy18/fp_poly_horner
; directly (same assembly unit) and math-coeffs.inc's SIN_COEF/COS_COEF/
; TWO_OVER_PI/SIN_C1/SIN_C2 records (already included above). Same
; resident-ABI surface subset as the other page-1 tenants; no new
; math-coeffs.inc constants beyond what's already emitted.
                include "fp_sin.asm"

; fp_rnd (math pack slice 2e, docs/spec-basic-mathpack-slice2.md §15): the
; NINTH and LAST page-1 tenant, RND(x). Reuses fsc_pack_arga directly
; (fp_sin.asm, same assembly unit, already included above) for its own
; zero-safe FAC pack tail; needs NEITHER fat_copy18/fp_poly_horner NOR any
; math-coeffs.inc record (its own A/C constants are page-1 data local to
; fp_rnd.asm) -- RND is the only slice-2 tenant that calls no resident fp
; op at all (§15.2). Resident-ABI surface subset: dig15_iszero +
; arga_pack_fac only (no widen_fac_to/widen_uint_to, since RND never widens
; an fp record through the resident ops either).
                include "fp_rnd.asm"

; CALL FORMAT build/write engine (index 10 = format_tenant, sub/format.asm): the
; TENTH page-1 tenant and the FIRST that is a SPLIT (not a whole leaf) — its
; main-side counterpart (basic/format.asm) keeps the interactive menu resident.
; Needs no resident-ABI import (unlike fp_sqrt/the transcendentals): it is a
; pure RAM + BIOS(CALSLT) leaf, own header has the full rationale.
                include "format.asm"

; scan_stmt_end (index 11 = SUBROM_IDX_SCANSTMT, sub/errtrap.asm): RESUME
; NEXT's statement-advance (error-handling S2b). A pure-leaf tenant (needs no
; resident-ABI import, same shape as fp_rnd/format_tenant) -- args/result
; marshalled through RAM (SSE_IN/SSE_OUT/SSE_EOL), own header has the full
; rationale.
                include "errtrap.asm"

; FAT12 primitive/sector layer (index 12 = fatprim_tenant, sub/fatprim.asm):
; the TWELFTH page-1 tenant, Phase 1 of the disk/file cluster eviction
; (docs/spec-evict-diskfile-cluster.md §11). Needs no resident-ABI import
; (same shape as fp_rnd/format_tenant/scan_stmt_end): a pure RAM+BIOS(CALSLT)
; leaf -- own header has the full rationale.
                include "fatprim.asm"

; KILL/NAME directory-verb I/O bodies (index 13 = dirverb_tenant, sub/
; dirverb.asm): the THIRTEENTH page-1 tenant, Phase 2 of the disk/file cluster
; eviction (docs/spec-evict-diskfile-cluster.md §12). Needs no resident-ABI
; import (same shape as fatprim_tenant): a pure RAM+BIOS(CALSLT) leaf whose two
; bodies call the Phase-1 fatprim primitives (included just above) sub-locally.
; Placed AFTER fatprim so its sub-local calls resolve within the same page-1
; region -- own header has the full rationale.
                include "dirverb.asm"

; fat_rand_* random-access record engine (index 12 = fatprim_tenant, extra
; fp_table rows 15-17; sub/randio.asm): docs/spec-eviction-g4-space.md §3,
; carve #1 of the G4-space eviction slice. Needs no resident-ABI import (same
; shape as fatprim_tenant/dirverb_tenant): a pure RAM+BIOS(CALSLT) leaf whose
; bodies call the Phase-1 fatprim primitives (included just above) sub-
; locally. Placed AFTER fatprim (+ dirverb) so its sub-local calls resolve
; within the same page-1 region -- own header has the full rationale.
                include "randio.asm"
                include "fiawalk.asm"

; play_parse_tenant (audio Slice 2a MML parser, docs/spec-basic-audio-play-
; slice2a.md). A pure RAM leaf: reads the marshalled per-voice MML (ptr,len) from
; the VCBs + AUDIO_VMASK, parses each string into its VOICxQ ring buffer, sets
; MUSICF last. No resident-ABI import (calls nothing in main); its note->period
; table + tempo->frame math are self-contained page-1 data.
                include "playparse.asm"

; lineedit_tenant (numbered-line editor TXTTAB-memmove engine, index 15,
; sub/lineedit.asm): docs/spec-eviction-g4-space.md §4, carve #2 of the
; G4-space eviction slice. Needs the resident-ABI import above (calls
; vars_reset directly, page-0 low-region resident -- own header has the
; full closure rationale for why this is not a straddle).
                include "lineedit.asm"

; casmatch_tenant (cassette Tier-3 name-match/data-skip engine, index 16,
; sub/casmatch.asm): docs/spec-eviction-g5-space.md. No resident-ABI import
; (a pure RAM+BIOS leaf, own header has the full closure rationale).
                include "casmatch.asm"
; Startup header (index 17 = title_tenant, sub/title.asm): a pure BIOS leaf
; (INITXT/CHPUT), no resident-ABI import, no marshalling.
                include "title.asm"

; 8.3-FCB-name builder (index 18 = fcbname_tenant, sub/fcbname.asm): the
; interrupt-traps T1 funding carve (docs/spec-basic-interrupt-traps.md §10.4).
; A pure RAM leaf with an inlined upcase clone, no resident-ABI import; marshals
; HL/CF through BN_PTR/BN_STAT. Its own header has the full rationale.
                include "fcbname.asm"

; CIRCLE-parse co-routine (index 19 = circleparse_tenant, sub/circleparse.asm):
; CIRCLE's whole grammar walk + angle/aspect float math, evicted as an eval-bounce
; co-routine to reclaim ~542 B of resident page-1 for the interrupt-trap arc
; (docs/spec-circle-coroutine-space.md). Needs the resident-ABI float imports
; (fp_add/sub/mul/div/cmp, dig15_iszero, widen_uint_to, flt_to_int16 -- all
; low-region, the fp_sqrt pattern). Bounces eval/parse_coord back to ex_circle.
                include "circleparse.asm"

; BLOAD verb body (index 20 = bload_tenant, sub/bload.asm): the whole verb --
; device dispatch, the cassette load loop, the disk load loop -- evicted from
; main page 1 to fund interrupt-traps T3 (docs/spec-traps-t3-key.md §7.6). PAGE 1
; so it can call fatprim's fat_mount/fat_find/fat_open/fat_read_file_sector
; sub-locally; must therefore follow fatprim.asm and fcbname.asm here.
                include "bload.asm"

; SAVE-family write engines (index 21 = save_tenant, sub/save.asm): BLOAD's
; mirror -- BSAVE/disk, BSAVE/tape, SAVE/disk and the shared cassette tokenised
; writer, evicted from main page 1 to fund `TIME` and interrupt-traps T5 from
; one carve (docs/decision-fund-time-and-t5.md, D-FUND-1). PAGE 1 for the same
; reason BLOAD is: it calls fatprim's fat_mount/fat_dir_create/
; fat_flush_data_sector/fat_dir_update sub-locally, so it must follow
; fatprim.asm here. Unlike BLOAD the PARSE stays resident (it uses `eval`), so
; nothing rides but SV_OP/SV_STAT.
                include "save.asm"

; Error-message host (index 22 = errmsg_tenant, sub/errmsg.asm), D-MSGSUB: the
; fourteen ERR codes zerobas never RAISES but must still be able to PRINT, plus
; the out-of-table fallback for every other code main routes here. PAGE 1 for
; title_tenant's reason -- CHPUT is page-0 BIOS -- and because main's own printer
; is unreachable from EITHER island (print_string/print_msg are main page 1). A
; pure RAM+BIOS leaf with no sub-local callees, so its position here is free.
; docs/spec-basic-msgsub.md.
                include "errmsg.asm"

; ASCII line-number scanner (index 23 = parseln_tenant, sub/lineno.asm), D-EVLNO:
; the first per-file eviction of the ROM REGION STRUCTURE REVIEW's rank-4 tier,
; costed by building it (docs/spec-rom-region-evict-lineno.md). A CLOSED leaf --
; it calls nothing at all, sub-local or otherwise -- so its position here is free
; and it would be legal on page 0 too; it is here because the page-0 table is full
; to the $0038 vector. Marshals BC/HL through PLN_NUM/PLN_PTR.
                include "lineno.asm"

; --- pad page 1 to the 32 KB ($8000) end -----------------------------------
; __MEAS_SUB_P1_END: page-1 free space is $8000 - __MEAS_SUB_P1_END. Same
; mechanism and same reasons as __MEAS_SUB_P0_END above; both are read by
; tools/check_sub_walls.py as a step of `make basic-reloc`.
__MEAS_SUB_P1_END:
                ds      $8000 - $, $FF
