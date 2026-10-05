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

; --- sc_inl0/sc_inl1/sr_inl0/sr_inl1: a tenant call with its entry INLINE -----
; 💰 D-STUBINL (B1 of the 2026-10-03 space hunt; landed as space plan B-11,
; 2026-10-05). A resident tenant call was `ld ix,BASE+3*idx` (4 B) + `call
; sc_call` / `call subrom_call` (3 B). Behind these four entries it is `call
; <stub>` (3 B) + `db low (BASE+3*idx)` (1 B): the stub reads the byte after the
; call, builds IX from it (the high byte is the table's: $00 for the page-0
; table, $40 for the page-1 one), steps the return address past the byte, and
; either falls into sc_call below (sc_inl*: raise if the sub-ROM is absent) or
; jumps to the raw subrom_call (sr_inl*: CF=1 iff absent, the site decides). A
; `jp sc_call` / `jp subrom_call` tail becomes `call` + `db` + `ret` (5 B
; against 7). Mode in A: bit 7 = raw, bits 6..0 = high byte / 2, so one
; `add a,a` yields CF = raw and A = the high byte. Preserves BC/DE/HL (the
; tenants' argument registers); clobbers A, F and IX -- subrom_call overwrites A
; before the CALSLT anyway, so A was never a tenant input. Documented opcodes
; only: the host core (tests/z80.py) runs a DD-prefixed reg/reg move on the
; PLAIN register, so `ld ixh,a` / `ld ixl,a` would have broken every host test
; that crosses the sub-ROM bridge.
; ⚠️ A NEW CALL SHAPE: a site that forgets its `db` executes the next opcode as
; the index, and NO emulator gate would see which. `make stubinl-check`
; (tools/check_stub_inline.py) refuses a stub reached by anything but `call`, a
; `call` not followed by its `db low (...)`, a db naming the OTHER table, a label
; on the db, and a stub used in a body that sub/ or disk/ also assembles.
; 🎯 SITED LOW, beside subrom_call, and sc_call moved here with it. disk.rom and
; the sub-ROM's page-1 tenants call main's LOW routines while page 1 is THEIR
; ROM, so a low routine that called a page-1 stub would jump into the wrong
; ROM. Low is reachable from every context that can run main code.
; ⏱ ~130 cycles per tenant call. The per-element / per-string-op paths keep
; their open-coded `ld ix` for that reason: ary_engine_call (arrays.asm),
; call_strheap (str-engine.asm) and str_set_key (vars.asm).
STUBINL_P0H     equ     high SUBROM_ENTRY_BASE_P0
STUBINL_P1H     equ     high SUBROM_ENTRY_BASE_P1
                IF STUBINL_P1H & $81
                db      STUBINL_P1_HIGH_BYTE_NOT_ENCODABLE__FIX_THE_MODE_CONSTANTS
                ENDIF
                IF STUBINL_P0H
                db      STUBINL_P0_HIGH_BYTE_NOT_ZERO__sc_inl0_HARDCODES_IT
                ENDIF
sr_inl1:
                ld      a,$80 | STUBINL_P1H/2   ; raw call, page-1 table
                jr      inl_go
sr_inl0:
                ld      a,$80                   ; raw call, page-0 table
                jr      inl_go
sc_inl1:
                ld      a,STUBINL_P1H/2         ; raise if absent, page-1 table
                jr      inl_go
sc_inl0:
                xor     a                       ; raise if absent, page-0 table
inl_go:
                add     a,a                 ; CF = raw flag, A = the entry's high byte
                ex      (sp),hl             ; HL -> the inline byte; caller's HL parked
                push    hl
                ld      l,(hl)              ; L = the entry's low byte
                ld      h,a
                push    hl
                pop     ix                  ; IX = the tenant's entry
                pop     hl
                inc     hl                  ; past the byte
                ex      (sp),hl             ; caller's HL back; return address fixed
                jr      c,subrom_call       ; raw: subrom_call's CF returns to the site
                ; falls into sc_call
; --- sc_call: subrom_call, and raise if the sub-ROM is absent -------------
; 🔁 RE-SITED LOW by space plan B-11 (2026-10-05): the stubs above fall into
; it, and they must be low (see their header). The paragraph below that says
; "SITED IN PAGE 1" is its history, from when low was the scarce wall.
; 💰 D-SCCALL, the fifth instruction pair. `call subrom_call` /
; `jp c,subrom_absent_error` — every marshalled call into a sub-ROM tenant —
; stood at SIXTEEN sites, SIX bytes each, so a 3-byte `call sc_call` saves **3 B
; per site**: the largest per-site saving of the five pairs.
; 🎯 SITED IN PAGE 1 THOUGH BOTH CALLEES LIVE LOW. subrom_call and
; subrom_absent_error are in basic/subromcall.asm, a low-region include, and the
; helper could sit beside them — but 15 of the 16 sites are in page 1 and LOW is
; the scarce wall (9 B against 104 B). Putting the 7 bytes in page 1 turns the one
; low site into a +3 B gain instead of a −4 B loss. Which region a helper lives in
; is a reading of today's split, not a property of the helper.
; ⚠️ It adds ONE stack frame while subrom_call runs its CALSLT. The absent path
; never returns (subrom_absent_error raises, and raise_error resets SP), and the
; present path returns through this `ret` with subrom_call's registers and flags
; untouched — which is the whole contract the 16 sites already relied on.
; 🔴 THIS BODY ATE ITSELF ON THE FIRST RUN — FOR THE SECOND TIME IN ONE NIGHT.
; The script writes the helper and THEN sweeps for the pair, and the helper's body
; IS the pair, so it became `sc_call: call sc_call / ret`: infinite recursion, in
; the routine 16 sites had just been pointed at. `skip_comma` did exactly this
; hours earlier and the docstring of the sweep tool WARNS about it — a warning is
; not a guard. Caught both times by the same arithmetic: 16 pairs removed against
; 17 calls added [[a-mechanical-fix-can-break-a-different-invariant]].
; ➕ C4 (space plan B-3, 2026-10-04): TWO MORE ENTRIES, BY `jp` — tokenise
; (interp.asm) and call_strheap (str-engine.asm) open-coded the same contract as
; `call subrom_call / ret nc / jp subrom_absent_error` and now tail-jump here, so
; no frame is added for them. COUNTED 2026-10-04, not carried: 17 `call sc_call`
; sites and 5 `jp sc_call` entries (cload, field, program, and these two) -- the
; "16" above is the D-SCCALL-day figure and has grown since.
; 🔁 RECOUNTED 2026-10-05 (space plan B-11): D-STUBINL moved every cold site to
; the inline-index stubs above, which FALL INTO this body. Direct users left: two
; `call sc_call` (ary_engine_call, str_set_key) and one `jp sc_call`
; (call_strheap) -- the hot paths, kept open-coded for speed.
sc_call:
                call    subrom_call
                jr      c,subrom_absent_error   ; jr: both low, same file (B-11)
                ret

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
; mathpack-slice2.md §15.3). RND_SEED USED TO live in the unused tail of the
; SUB_INT_RAM reservation above ($F142..$F148, inside the conservative 64-byte
; reservation that runs $F10A..$F149), and this assert was bounded by it.
; 🔁 D-ADDR29 RNDX (2026-09-25) moved the seed to the published RNDX+1
; ($F858), so the bound is now the next CLAIMED cell, INT_MAIN_PRIM ($F14A) --
; bounding it by RND_SEED would have let the stub grow ~1.8 KB unchecked, the
; exact "derived constant falsified from another file" shape. The assert still
; makes any growth that would collide FAIL THE BUILD loudly (an undefined
; symbol, pasmo's own diagnostic). Currently 47 <= 64.
    IF (sub_int_template_end - sub_int_template) > (INT_MAIN_PRIM - SUB_INT_RAM)
                db      INT_TRAMPOLINE_GREW_INTO_INT_MAIN_PRIM__SHRINK_OR_MOVE
    ENDIF

; --- fch_park (D-ASAVECHAN, 2026-10-03): park the live file channel --------
; Saves the active channel's engine state into its context and hands the engine
; globals to nobody (fch_claim with A = 0), so the next statement that names the
; channel reloads it. For the verbs that stream through those SAME globals
; without chan_gate's bracket -- SAVE ,A (ascii_save), the BSAVE and BLOAD
; tenants: an open OUTPUT file lost every byte beside them, an INPUT one its
; place (scratchpad/asavechan_probe.py, chanside_probe.py).
; Sited in the LOW region on purpose: its three callers are page 1, which had no
; room, and a `call` here is a byte cheaper than the inline pair at each site.
fch_park:
                xor     a
                jp      fch_claim
