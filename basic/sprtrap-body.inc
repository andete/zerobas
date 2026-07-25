; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; sprtrap-body.inc — the SPRITE collision trap's event source (arc slice T4).
; ===========================================================================
; docs/spec-traps-t4-sprite.md. One stanza: sample the VDP sprite-collision
; status once per frame and raise the SPRITE entry's PENDING bit. The parse
; surface (`ON SPRITE GOSUB`, `SPRITE ON|OFF|STOP`) is page-1 code elsewhere;
; the DISPATCH half is the arc's shared check_traps, unchanged.
;
; A `.inc` BODY, INLINED INTO htimi_guard, not a routine: the low region is the
; scarce wall here (T4 measured 27 B of it against 14 B free), and a `call` plus
; a `ret` is 4 of those bytes for no benefit -- there is exactly one call site
; and there can only ever be one, since the whole point of D-T4-2 is that this
; must run on the ISR path ahead of the page-1 slot test. Kept as its own file
; rather than buried in subromcall.asm so the source rationale below stays with
; the code (the repo's existing *-body.inc idiom).
;
; THE SOURCE IS `STATFL`, NOT A PORT READ — and the alternative is impossible,
; not merely worse (spec §2, D-T-4). C-BIOS's $0038 handler does
;       in   a,(VDP_STAT)
;       ld   (STATFL),a
;   ... then call H_TIMI
; and S#0 is READ-TO-CLEAR. Anything hanging off the H.TIMI seam therefore runs
; AFTER the BIOS has already consumed the collision bit, every frame, so a second
; direct port read there can never see it — there is no race to characterize,
; the BIOS always wins. That same ordering is what makes STATFL exact rather than
; merely workable: it is written BEFORE the hook, so we read the CURRENT frame's
; sample with no one-frame lag. MEASURED 198/200 and 199/200 sampled iterations
; hit on the VG-8020 and the repack build, 0/200 on both no-collision controls.
;
; A LEVEL, SAMPLED PER FRAME — NOT AN EDGE. While two sprites overlap the
; reference fires EVERY frame, indefinitely: 31 fires against a JIFFY delta of 30
; over the same window (spec §1.1). So there is deliberately NO edge shadow here
; and no arming seed — bit 6 of the SPRITE entry stays unused, and a collision
; that predates `SPRITE ON` fires immediately (measured). Do not "harmonise" this
; with ep_strig's edge detection; T2 and T4 differ by measurement.
;
; WHY THE LOW REGION AND NOT event_poll (D-T4-2, spec §3.1). event_poll is main
; page-1 resident and htimi_guard SKIPS it whenever a sub-ROM page-1 tenant owns
; page 1. The tempting argument is that this costs SPRITE nothing, since sprites
; only move when the program runs PUT SPRITE and it cannot do that while blocked
; inside a tenant. That argument is true today and is the wrong thing to depend
; on: it is a claim about which page-1 tenants touch sprite VRAM (bload_tenant and
; title_tenant DO write VRAM), so every future tenant silently becomes a fresh
; obligation to re-audit, with nothing in the build to catch a miss. Page 0 is
; untouched during a page-1 tenant, so a low-region stanza is correct BY
; CONSTRUCTION and needs no premise at all — the same reasoning that put
; htimi_guard itself and keytrap.asm in page 0. This touches only RAM, so it has
; no page-1 dependency to give up.
;
; INTERRUPT DISCIPLINE: inlined into htimi_guard ahead of that guard's slot test,
; on the $0038 ISR path, DI. htimi_guard has already pushed AF and reloads A right
; after this body (`in a,(PSLTREG)`), so A is free here; HL is NOT, and is saved on
; EVERY path including the not-armed fast-out.
;
; Repack-only, like the rest of the trap machinery.
;
; CLEAN-ROOM: own-design. STATFL ($F3E7) and S#0 bit 5 are the PUBLISHED MSX work
; area and VDP status-register contract; the C-BIOS ISR ordering quoted above was
; read from C-BIOS SOURCE, which is a build input, not a stock reference ROM. No
; ROM bytes lifted.

                push    hl
                ld      hl,ZTRAP+ZTI_SPRITE*ZTRAP_ENTSZ
                bit     0,(hl)              ; state bit 0 = ON (01) or SERVICING (11);
                jr      z,sp_done           ; OFF (00) / STOP (10) are not sampled at all
                                            ; -- the same one-bit test ep_strig uses, and
                                            ; SERVICING must count so a collision during
                                            ; the handler latches and fires after RETURN.
                ld      a,(STATFL)          ; the ISR's S#0 copy for THIS frame
                and     $20                 ; bit 5 = C, the sprite-collision flag
                jr      z,sp_done
                ; A plain RAM load: reading STATFL does NOT consume the flag, which
                ; is required -- an enabled trap must not change what a program sees
                ; through VDP(8). MEASURED: VDP(8) reads $BF while colliding whether
                ; the trap is enabled or not, and VDP(8) IS STATFL (spec §1.6).
                set     7,(hl)              ; the entry's PENDING
                ld      (TRAPPEND),a        ; wake the run-loop dispatcher. A is still
                                            ; the $20 the `and` left -- TRAPPEND is a
                                            ; pure "nonzero = something pending" gate
                                            ; (every reader does `or a` / `jr nz`), so
                                            ; the usual `ld a,1` is 2 wasted low bytes.
sp_done:
                pop     hl
