; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; subromcall.asm — zerobas-sub discovery recorder + dispatch helper
; (included by basic/main.asm,
; in the PAGE-0 low region freed by evicting the float PRINT formatter).
; docs/spec-basic-subrom.md §3c/§3g, WAVE-1 AMENDMENT.
;
; WHY PAGE 0. init_ext_roms (basic/initext.asm) lives in page 1, whose tail is
; nearly full; these ~90 B of bodies would overrun the $8000 ceiling there. They
; belong in the space the formatter eviction frees (page 0 low region). Their
; callers reach them under normal (fully slot-0-mapped) contexts — try_sub_slot
; from the boot scan, subrom_call from the PRINT stub — so a page-1→page-0 call
; is fine. subrom_call issuing a page-0 CALSLT from page-0 code is also fine:
; CALSLT restores page 0 to slot 0 before returning, exactly as the 163 disk
; call sites already switch their OWN page (page 1) out across a CALSLT.
;
; SOURCES (allowed, new vs initext.asm's block): CD sub-ROM signature + EXBRSA
; $FAF8 sub-ROM-slot work area — MSX2 Technical Handbook. The RDSLTs read only
; our OWN sub-ROM bytes; no C-BIOS code is read or relocated (firewall §3g).
;
; Clean-room: nothing here is derived from a disassembly or byte-copy of any
; reference BIOS/BASIC ROM. The RDSLTs read only our own sub-ROM's signature
; bytes; the CD signature / EXBRSA / CALSLT contracts are public MSX2 Technical
; Handbook ABIs, and the dispatch glue is own-design. See basic/PROVENANCE.md.

; try_sub_slot and sub_int_install were PROMOTED out of this file and into main
; page 1 (basic/subrom-boot.asm) to fund the KEY trap's low-region hook — see that
; file's header for the rule that permits it. Both are boot-time-only, so neither
; a page-1 tenant nor the $0038 ISR can reach them. What is left here is what must
; stay below $4000: the runtime dispatcher, the ISR guard, and the trampoline body.

; subrom_call: dispatch to a sub-ROM page-0 tenant. IX = entry address
; (SUBROM_ENTRY_BASE_P0 + 3*index); args/results marshalled in page-2/3 RAM by
; the caller. Returns CF=1 WITHOUT calling if the sub-ROM is absent (reduced
; builds); CF=0 after a completed call. The tenant runs with slot-0 page 0 (BIOS
; + $0038 ISR) switched out, so the whole call is under DI (§3b/§3d); CALSLT
; clobbers all registers — the caller guards anything live (e.g. the text cursor).
; --- deffn_subcall: `ld ix,<the DEF FN tenant's entry>` + `call subrom_call`
; stood open-coded at all FOUR DEF FN dispatch sites (basic/deffn.asm x3 for
; FNF_SAVE / the request read / FNF_RESTORE, basic/interp.asm x1 for
; FNF_UNWIND) at 7 B each. Behind this 3 B call they cost 3, and the helper
; costs only the `ld` because it FALLS THROUGH into subrom_call below: 12 B,
; D-LONGRUN (scratchpad/longrun_scout.py, the run at 4 sites that the 8-site
; floor in scratchpad/pair_carve_scout.py could not report).
; 🟢 THE FALL-THROUGH IS LEGAL, AND THE ANSWER WAS NOT IN THIS FILE.
; subrom_call is the FIRST code here, so what decides it is whether the include
; BEFORE this one in basic/main.asm falls forward -- basic/float-arith.asm, and
; it ends `ret`. No label shares subrom_call's address and nothing jumps to the
; byte before it, so the only way in here is this label.
; 🟢 IDENTICAL BEHAVIOUR, and why: `ld ix,nn` sets no flags and touches no other
; register, so L (the FNF_* op code), A, DE and HL reach the tenant exactly as
; they did open-coded; and `call deffn_subcall` pushes exactly the ONE return
; address `call subrom_call` pushed, so subrom_call's own `ret` lands back at
; the site with CF (absent vs completed) intact and SP unchanged.
; ⚠️ EVERY OTHER subrom_call CALLER IS UNAFFECTED -- they load their own index
; and call the label below directly; this is one more entry, not a funnel.
deffn_subcall:
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_DEFFN

subrom_call:
                ld      a,(SUBSLOT_OK)
                or      a
                scf
                ret     z                   ; absent -> CF=1, no call (caller errors)
                push    de                  ; a tenant may take DE as an arg (crunch: dest)
                ld      a,(SUBSLOT)
                ld      d,a
                ld      e,0
                push    de
                pop     iy                  ; IYh = sub-ROM slot id (CALSLT ABI)
                pop     de                  ; restore the tenant's DE arg
                di
                call    CALSLT              ; HL/DE pass through; tenant runs under DI
                ei
                or      a                   ; CF=0: call completed (A = tenant's result)
                ret

; subrom_absent_error: defensive statement abort for a sub-ROM-backed statement in
; a build without the sub-ROM (never reached on the merged machine, which always
; ships it — §3d). Mirrors fp_runtime_error's tail (zero PRDEST, print, ret to the
; statement driver's caller); own lowercase wording, D-8/D-2 pattern.
subrom_absent_error:
                xor     a
                ld      (PRDEST),a
                ld      hl,err_subrom_absent
                jp      print_msg           ; D-MSGENC: err_subrom_absent aliases
                                            ; err_illegal_fn, which is now encoded
err_subrom_absent equ   err_illegal_fn      ; share interp.asm's identical "illegal
                                            ; function call" string (both repack-only) —
                                            ; reclaims 24 B in this LOW region to fund
                                            ; D-2's run-mode " in <line>" suffix in
                                            ; fre_abort_low (arrays.asm). Direct print,
                                            ; no suffix (unchanged behaviour).

; htimi_guard: page-1-safety gate for the H.TIMI PLAY servicer seam
; (docs/spec-traps-t1-htimi-page1-safety.md). play_install points H.TIMI here
; instead of straight at play_service. WHY: play_service is main-ROM PAGE-1
; resident, but a VBLANK can land while page 1 is switched out to a sub-ROM
; page-1 tenant — the FATPRIM tenant's dskio_calslt CALSLTs DSKIO, which EIs,
; so the "page-1 tenants always run DI" invariant (playsvc.asm) does NOT hold.
; Jumping into play_service's address then executes sub-ROM garbage (a wild
; boot crash whose severity tracks play_service's shifted address — a bounded
; failure band; see docs/traps-t1-wiring-blocker.md). This guard is PAGE-0
; resident (always mapped when H.TIMI runs: page 0 is untouched during a page-1
; tenant, and the $0038 sub-ROM trampoline has mapped main page 0 back before
; its `call $0038` during a page-1... page-0 tenant). It reads the page-1
; primary-slot field and only falls through to play_service when main-ROM is
; mapped there; otherwise it skips PLAY this frame (an inaudible <=1-frame drain
; deferral during the rare tenant window). Register-transparent (only AF), DI.
;
; MAIN-ROM = PRIMARY SLOT 0 (page-1 field bits 3-2 == 00) is a standing merged-
; machine invariant (C-BIOS boots our 32 KB ROM from slot 0; same assumption
; init_ext_roms already relies on) — so a zero page-1 primary field means main
; ROM is mapped, and any nonzero value means a sub-ROM (slot 3-x) tenant owns
; page 1. Primary-only test (D-2 sign-off): sufficient for the slot-0-main /
; slot-3-2-sub layout. SOURCES: port $A8 primary-slot field (MSX2 TH slot
; architecture); own-design gate. No reference-ROM disassembly.
htimi_guard:
                push    af
    IF TRAPS_T4
                ; SPRITE trap (T4): sampled HERE, ahead of the slot test, because it
                ; must run on EVERY frame -- including the ones this guard is about to
                ; skip. That is the whole point of D-T4-2 (spec-traps-t4-sprite.md
                ; §3.1): the source is low-region so no page-1 tenant window can hide
                ; a collision from it. INLINED (not called) because the low region is
                ; T4's binding wall and a call+ret is 4 B of it; see the file header.
                include "basic/sprtrap-body.inc"
    ENDIF
                in      a,(PSLTREG)         ; current slot config (page-1 = bits 3-2)
                and     %00001100           ; isolate the page-1 primary field
                jr      nz,htg_skip         ; nonzero -> a sub-ROM tenant owns page 1
                pop     af
                jp      htimi_service       ; main page 1 mapped -> safe: poll traps then
                                            ; fall into play_service; its ret -> ISR.
                                            ; (htimi_service is basic/traps.asm; before it
                                            ; was wired this jumped straight to play_service.)
htg_skip:
                pop     af
                ret                         ; skip PLAY (+ trap poll) this frame; -> ISR

; ===========================================================================
; Interrupt trampoline — install + template (docs/spec-basic-subrom-trampoline.md)
; ===========================================================================
; Lets a page-0 sub-ROM tenant run EI. While a page-0 tenant runs, CALSLT has
; switched slot-0 page 0 (BIOS + the real $0038 ISR) OUT and mapped the sub-ROM
; in, so the CPU's $0038 vector reads sub-ROM bytes — an interrupt there would
; crash. The sub-ROM therefore carries its OWN $0038 (`jp SUB_INT_RAM`) pointing
; at a RAM-resident stub that maps the BIOS back into page 0, `call $0038`s the
; real ISR, maps the sub-ROM back, and RETIs. The stub lives in RAM (page 3,
; always mapped) so the page-0 slot write never pages out its own next instruction
; (spec §1.2). A tenant opts in simply by running EI after entry and DI before ret;
; short tenants (ping/tokenise/detok) keep running fully-DI and are unaffected.
;
; CANONICAL MECHANISM. A RAM-resident inter-slot caller is exactly what the MSX
; BIOS itself installs: RDPRIM $F380 / WRPRIM $F385 / CLPRIM $F38C are copied into
; RAM at boot (C-BIOS main.asm) precisely so the $A8-writing code does not page
; itself out. So this stub is the STANDARD technique, not a novel one. We do NOT
; route through CLPRIM, though: CLPRIM restores the caller's slot with interrupts
; in the CALLER's state, and our target — the real ISR — ends EI/RETI, so a
; CLPRIM tail would run its slot-restore interrupts-live (an IRQ landing just after
; page 0 flips back to sub-ROM re-enters $0038). Our stub adds the explicit `di`
; before the switch-back that CLPRIM lacks — the adaptation an interrupt target
; needs. So: CLPRIM is the precedent, this is CLPRIM + an interrupt-safe DI guard.
;
; SOURCES (allowed): $0038 maskable-interrupt vector + CLPRIM $F38C RAM inter-slot
; primitive (published MSX contracts — CALLed/cited, never read/disassembled,
; exactly as the disk ROM calls BIOS entries); $A8 primary + $FFFF secondary slot
; registers — MSX2 TH slot architecture; the host-adaptive page-0 primary switch
; mirrors our own disk/init.asm page0_ram_in. No C-BIOS code is read or relocated
; (firewall §3g / cbios-repack-provenance.md). Own-design divergence (the DI-guarded
; adaptation) logged in sub/PROVENANCE.md.

; sub_int_template: the RAM trampoline, copied verbatim to SUB_INT_RAM. Entered
; from the sub-ROM $0038 with IFF already cleared by the CPU. POSITION-INDEPENDENT
; — every memory reference is absolute ($A8/$FFFF/$0038 and the fixed INT_* cells),
; no internal branch — so the flat copy runs correctly at its RAM address. Only A
; and C are touched before the ISR call (the real ISR saves/restores the rest, as
; any transparent maskable handler must), so preserving AF/BC is sufficient.
sub_int_template:
                push    af
                push    bc
                ; --- page 0: sub-ROM -> MAIN (BIOS); primary field only (main
                ;     slot is unexpanded, so no page-0 subslot to set) ---
                in      a,(PSLTREG)
                and     %11111100
                ld      c,a
                ld      a,(INT_MAIN_PRIM)
                or      c
                out     (PSLTREG),a
                ; page 0 now = BIOS; $0038 reads the real `JP int_h`.
                call    $0038               ; VDP ack, JIFFY++, H.TIMI/H.KEYI hooks
                di                          ; the ISR EI'd on the way out; guard the switch-back
                ; --- page 0: MAIN -> sub-ROM (primary, then subslot) ---
                in      a,(PSLTREG)
                and     %11111100
                ld      c,a
                ld      a,(INT_SUB_PRIM)
                or      c
                out     (PSLTREG),a
                ld      a,($FFFF)           ; slot-3 secondary reg (reads inverted)
                cpl                         ; -> live value
                and     %11111100
                ld      c,a
                ld      a,(INT_SUB_SUBSL)
                or      c
                ld      ($FFFF),a
                pop     bc
                pop     af
                ei
                reti                        ; resume the tenant, interrupts live
sub_int_template_end:

; --- RND_SEED tail-slack guard (math pack slice 2e, docs/spec-basic- -------
; mathpack-slice2.md §15.3). RND_SEED (basic/sysvars.inc) lives in the
; UNUSED tail of the SUB_INT_RAM reservation above ($F142..$F148, inside the
; conservative 64-byte reservation that runs $F10A..$F149) -- safe only as
; long as the copied stub (sub_int_template..sub_int_template_end) never
; grows past that reservation. This build-time assert makes any future
; growth that would collide FAIL THE BUILD loudly (an undefined symbol,
; pasmo's own diagnostic) instead of silently overlapping RND_SEED at
; runtime. Currently 47<=56 (RND_SEED-SUB_INT_RAM=$F142-$F10A=$38=56).
    IF (sub_int_template_end - sub_int_template) > (RND_SEED - SUB_INT_RAM)
                db      RND_SEED_COLLIDES_WITH_GROWN_INT_TRAMPOLINE__MOVE_RND_SEED
    ENDIF
