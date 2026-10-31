; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; keytrap.asm — the KEY interrupt-trap EVENT SOURCE (arc slice T3).
; ===========================================================================
; docs/spec-traps-t3-key.md §4. Only the event source lives here; the parse
; surface (`ON KEY GOSUB`, `KEY(n) ON|OFF|STOP`) is zerobas-sub2's since D-P0CB
; slices B / D (sub2/trapstmt.asm, reached from program.asm's ex_on_key stub and,
; for KEY(n), from sub2/scrstmt.asm's KEY) and the dispatch half is the shared check_traps machinery in traps.asm.
;
; WHY THIS IS A C-BIOS HOOK AND NOT A MATRIX POLL (D-T3-1, measured).
; KEY is a DELIVERY trap, not an edge trap like STRIG: it fires once per BIOS
; key-delivery event — the initial make AND every auto-repeat — and a trapped
; key is DIVERTED, removed from the input stream before anything can read it.
; Neither published ISR hook can do that: H.KEYI ($FD9A) and H.TIMI ($FD9F)
; both run BEFORE the keyboard scan on C-BIOS *and* on the VG-8020 (D-T3-3), so
; neither can see — let alone remove — the current frame's KEYBUF insertion. A
; sweep of all ~112 hook slots with a program running found no post-scan seam
; (spec §4.1). So zerobas patches C-BIOS to add one, exactly as a real MSX does
; it (there BASIC *is* the BIOS and the KEY trap sits inside the scan).
;
; The patch is deliberately THIN — five bytes at put_key_fnk that call a RAM
; vector — and ALL policy lives here. Teaching C-BIOS about ZTRAP would put
; BASIC policy in the BIOS and force a repacked-ROM sha1 re-pin on every
; semantic change. See cbios-repack/key-trap-hook.patch.
;
; WHY THE LOW REGION AND NOT PAGE 1. The hook fires from inside C-BIOS's
; keyboard scan, i.e. from the $0038 timer ISR — and a VBLANK can land while
; main page 1 is switched out to a sub-ROM page-1 tenant (FATPRIM's dskio_calslt
; CALSLTs DSKIO, which EIs; docs/spec-traps-t1-htimi-page1-safety.md). A page-1
; handler would need the htimi_guard treatment, and skipping a frame is fine for
; PLAY but NOT for KEY: a skipped frame leaks an undiverted keystroke into
; KEYBUF, which is a correctness divergence, not a deferral. Page 0 is untouched
; during a page-1 tenant, so a low-region handler is ALWAYS mapped and needs no
; guard at all. The handler touches only RAM, so it has no page-1 dependency to
; give up. This is the same reasoning that put htimi_guard itself in page 0.
;
; ⚠️ GATED OFF (TRAPS_T3 = 0, basic/sysvars.inc). T3 needs 236 B — 66 of them
; here in the low region, which has 6 free — so the slice is written but NOT
; FUNDED, pending the re-decision of D-T3-5 (the carve; spec §7.1/§7.2). This
; file assembles clean but HAS NEVER BEEN RUN. Under the arc's standing lesson
; that says nothing whatsoever about its correctness: treat every line below as
; unverified until `make key-trap-acceptance` exists and passes.
;
; CLEAN-ROOM: own-design. The hook CONTRACT is ours; NEWKEY/$FBE5 and the
; row-6-bit-0 SHIFT position are the published MSX key-matrix work area, and the
; 5-byte JP hook-vector idiom is the standard MSX H.* hook convention (H.TIMI is
; already installed this way by play_install). No reference-ROM bytes.

    IF TRAPS_T3

; (zkey_install has been PROMOTED to basic/subrom-boot.asm — page 1. It is
; boot-time-only, so it was never pinned here; T4's SPRITE stanza needs the low
; region for the one thing that genuinely cannot leave it. zkey_hook below stays,
; and the promoted installer still takes its address as plain data.
; docs/spec-traps-t4-sprite.md §5.)

; zkey_hook: the C-BIOS put_key_fnk hook target — one function-key DELIVERY.
;   IN:  A  = the BIOS's fn-key index 0..4 (F1..F5; SHIFT is NOT folded in by
;             C-BIOS — measured, D-T3-7).
;   OUT: A  = the SHIFT-folded index 0..9 (F1..F10). The hook contract is A
;             IN/OUT so that an UNTRAPPED SHIFT+F1 expands FNKSTR slot 5 (F6's
;             string) as a real MSX does, instead of slot 0. That is a
;             pre-existing C-BIOS divergence which T3 closes for one `ld`.
;        CF=1 -> SWALLOW this delivery (the trap took it: the key is diverted
;                and never reaches KEYBUF); CF=0 -> expand FNKSTR[A] as usual.
;   Preserves BC, DE, HL, IX, IY. Entered DI, from inside the timer ISR.
;
; Diversion follows the STATE ALONE (spec §1.2/§2): an entry that is ON with an
; EMPTY handler slot still swallows its key and fires nothing. Sampling while ON
; *or* SERVICING is T2's rule — both have state bit 0 set (ON=01, SERVICING=11)
; and neither unsampled state does (OFF=00, STOP=10) — so the test is one
; `bit 0`. A press during SERVICING latches and fires after RETURN, delivered by
; trap_return_check's existing TRAPPEND re-raise (spec §1.3 W1). No edge shadow
; and no seeding rule: the event is a DELIVERY, not a level, so a key already
; held when the trap is enabled simply produces its next repeat delivery — there
; is no spurious edge to suppress. Auto-repeat is inherited from the host BIOS's
; own decode, which is more faithful than replicating the VG-8020's constants.
zkey_hook:
                push    hl
                ld      hl,NEWKEY+6         ; matrix row 6, bit 0 = SHIFT
                bit     0,(hl)              ; the matrix is ACTIVE LOW: 0 = down
                jr      nz,zkh_noshift
                add     a,5                 ; F1..F5 + SHIFT -> F6..F10 (D-T3-7)
zkh_noshift:
                ; HL = the entry of KEY k+1 = ZTRAP + 3*(ZTI_KEY1+9-k), all on ZTRAP's
                ; page (guard below), so only L is computed: no page-1 ztrap_entry
                ; (unreachable when a page-1 tenant owns the page), and BC / DE are
                ; never touched (D-REREAD batch 6, was key_entry_index + a 16-bit
                ; multiply).
; THE BAND IS LAID OUT REVERSED — KEY 10 at ZTI_KEY1, KEY 1 at ZTI_KEY1+9. The
; reference services the family HIGH-NUMBERED FIRST (spec §1.3 V2: F1+F2+F3 in
; one frame are serviced 3 -> 2 -> 1), while ct_find scans ZTRAP ASCENDING and
; fires the first entry it finds. Reversing the layout gets the measured order
; for ZERO bytes in ct_find and, crucially, without touching the scan direction
; that T2's already-landed STRIG band depends on. D-T3-4 requires this match
; unconditionally, so it is not gated on a byte count.
                ld      h,a                 ; H = the folded index k (the A-out value)
                ld      a,low (ZTRAP+(ZTI_KEY1+9)*ZTRAP_ENTSZ)
                sub     h
                sub     h
                sub     h                   ; 3k <= 27: no borrow out of the band
                ld      l,a
                ld      a,h                 ; A = the folded index again (A-out)
                ld      h,high ZTRAP
                bit     0,(hl)              ; ON or SERVICING -> this key is trapped
                jr      nz,zkh_trap
                or      a                   ; CF=0 -> expand FNKSTR[A] as usual
zkh_out:
                pop     hl
                ret
zkh_trap:
                set     7,(hl)              ; ZTS_PENDING: an event is awaiting dispatch
                ld      l,low TRAPPEND      ; same page as ZTRAP (guard below)
                ld      (hl),1              ; wake the run-loop dispatcher
                scf                         ; CF=1 -> swallow the delivery
                jr      zkh_out
    IF ZTRAP_ENTSZ != 3 || (high ZTRAP) != (high (ZTRAP+(ZTI_KEY1+9)*ZTRAP_ENTSZ)) || (high TRAPPEND) != (high ZTRAP)
                db      ZKEY_HOOK_ASSUMES_THE_KEY_BAND_AND_TRAPPEND_ON_ZTRAPS_PAGE
    ENDIF

    ENDIF
