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
; This is the S2a SKELETON: an empty container that carries only the discovery
; signature and one round-trip PING per page. It has no real tenants yet — the
; first (float.asm's tokeniser+formatter) arrives with the S2b/eviction session,
; appended to the entry tables below. The main ROM does not yet call in; S2a's
; boot gate drives the CALSLTs by injection from the openMSX debugger.
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

; Shared RAM-cell addresses (TKPOS/TKDIG/TKPC/TKSRCSAVE/... used by tkfloat.asm).
; ROM_BASE selects the repack cell layout from the SAME sysvars.inc the merged
; main ROM uses, so a sub-ROM tenant's RAM scratch is byte-address-identical to
; the main ROM's — no marshalling translation. sysvars.inc is pure equates
; (emits no bytes), so it does not perturb this ROM's $0000-based layout.
ROM_BASE        equ     $2812
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

; --- Page-0 entry table (append-only jp table; base $0010, §3c/D-5) --------
; IX = SUBROM_ENTRY_BASE_P0 + 3*index dispatches here. Index 0 = the S2a PING.
; Future page-0 tenants (float.asm's tokeniser+formatter first) append below and
; never move an existing entry, so a main-ROM stub hard-codes only its index.
    IF $ - SUBROM_ENTRY_BASE_P0
                db      SUB_P0_TABLE_NOT_AT_0010__HEADER_SIZE_DRIFT
    ENDIF
sub_p0_table:
                jp      sub_p0_ping             ; index 0 (SUBROM_IDX_PING)
                jp      tokenise                ; index 1 (SUBROM_IDX_TOKENISE): the WHOLE
                                                ;   tokeniser (wave 2). The tk_float crunch
                                                ;   is no longer a dispatch entry — it is an
                                                ;   in-slot `jp tk_float` from tk_loop.

; --- Page-0 PING (S2a boot-gate tenant) -----------------------------------
; Proves a CALSLT to $0010 mapped slot 3-2 into PAGE 0 and that page-3 RAM is
; reachable from there: stamp SUB_PING with the page-0 tag and return. The
; distinct tag ($C0 vs the page-1 $C1) is what proves page-correct mapping — the
; two pings live in different pages of the same subslot, so only a page-selective
; CALSLT reaches each.
sub_p0_ping:
                ld      a,SUB_PING_P0
                ld      (SUB_PING),a
                ret

; --- Page-0 tenants -------------------------------------------------------
; WAVE 2 (index 1 = tokenise): the WHOLE tokeniser body, evicted from the repack
; main ROM's basic/interp.asm and reunited here with the wave-1 tk_float literal
; crunch. It is pure buffer computation over page-2/3 RAM — no BIOS / low-region /
; ISR touch (leaf-audit, spec §3) — so it is a valid page-0 tenant run under DI.
; Its only non-RAM callees are pure leaves co-resident in this page:
;   * upcase / cmp16_bits / neg_de  — clones in tkfloat.asm (below).
;   * is_letter / is_ident_cont     — clones right below (the tokeniser's
;                                     identifier path; not needed by the crunch).
;   * tk_float                      — the wave-1 crunch, now reached by an ordinary
;                                     in-slot `jp tk_float` from tk_loop (wave 1's
;                                     per-literal CALSLT + disposition protocol were
;                                     reverted, spec §5).
;   * kwtable                       — a byte-identical DUPLICATE of the resident
;                                     repack copy (§4: the resident copy stays for
;                                     LIST/detok, which is I/O-bound and can't go
;                                     sub-side; a page-0 tenant can't see the
;                                     main-ROM low region either, so it needs its
;                                     own copy). Same kwtable.inc + same ROM_BASE
;                                     gating -> the two images can't drift.
                include "tkfloat.asm"
                include "basic/tokenise.inc"

; --- sub-local is_letter / is_ident_cont (byte-identical own-design clones) --
; Resident copies stay in the main ROM (basic/interp.asm is_letter, basic/vars.asm
; is_ident_cont) for the rest of the interpreter; a page-0 tenant can't reach them,
; so the tokeniser's identifier path uses these co-located clones. is_letter ->
; upcase (tkfloat.asm), is_ident_cont -> is_letter — the whole chain is here.
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
is_ident_cont:
                call    is_letter           ; letter -> CF set, A preserved
                ret     c
                cp      '0'
                jr      c,siic_no
                cp      '9'+1
                jr      nc,siic_no
                scf                          ; digit -> CF set
                ret
siic_no:
                or      a                    ; CF clear
                ret

; --- sub-local keyword table (duplicate of the resident repack copy, §4) -----
; Assembled from the SAME basic/kwtable.inc under the SAME ROM_BASE (<$4000) as the
; resident repack copy, so the two are byte-identical by construction; the reloc
; build's byte-identity assert (tools/check_reloc.py) is the standing guard.
                include "basic/kwtable.inc"

; --- pad page 0 to the $4000 boundary --------------------------------------
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

; --- Page-1 PING (S2a boot-gate tenant) -----------------------------------
; Proves a CALSLT to $4010 mapped slot 3-2 into PAGE 1 (main BASIC switched out,
; BIOS in) and that page-3 RAM is still reachable: stamp SUB_PING with the
; page-1 tag and return.
sub_p1_ping:
                ld      a,SUB_PING_P1
                ld      (SUB_PING),a
                ret

; --- pad page 1 to the 32 KB ($8000) end -----------------------------------
                ds      $8000 - $, $FF
