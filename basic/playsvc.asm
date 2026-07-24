; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; playsvc.asm — the live PLAY music servicer (audio arc, Slice 3).
; ===========================================================================
; play_service drains one frame of PLAY music each VBLANK. It is the async half
; of PLAY: the parser tenant (sub/playparse.asm) fills the three VOICxQ packet
; queues and sets MUSICF; from then on this routine, reached from C-BIOS's $0038
; timer ISR through the H.TIMI ($FD9F) hook, dequeues one frame's worth per voice
; and writes the PSG directly. See docs/audio-slice3-characterization.md — every
; behavioral constant here (frame = the packet's own dur field; silence = amp 0;
; R7 never touched; MUSICF bit cleared at OP_END) was pinned by a per-VBLANK PSG
; register trace of the real VG-8020, black-box, no disassembly.
;
; PLACEMENT (docs §4a, a grounded deviation from spec §3.B). This is main-ROM
; PAGE-1 resident, reached from H.TIMI by a NEAR JP -- not a page-0 window resident
; and not a sub-ROM tenant. The spec required page-0 residence to survive a VBLANK
; landing mid page-1-tenant CALSLT; but subrom_call runs every page-1 tenant under
; DI (basic/subromcall.asm) and no page-1 tenant opts into EI, so a VBLANK NEVER
; fires while main page 1 is switched out. In every case where H.TIMI actually runs
; (EI main-ROM code; or a page-0 tenant's EI, which leaves page 1 mapped), main
; page 1 is present -- so a page-1-resident servicer is always mapped, and the
; §4.3 reentrancy hazard is void. Page 0 has only 19 B free; page 1 has ~930 B.
;
; INTERRUPT DISCIPLINE. Entered with interrupts already disabled (the ISR); it must
; stay DI (never EI) and is therefore inherently non-reentrant -- no busy flag
; needed. It is register-transparent (saves/restores everything it uses), the
; H.TIMI convention. It touches only the PSG ($A0/$A1), the RAM queues, MUSICF, and
; the per-voice VCX_FRAMES counters -- never JIFFY or the keyboard.
;
; Repack-only, like ex_sound / ex_play: the whole body is under IF ROM_BASE < $4000
; (the H.TIMI seam only makes sense with the servicer present, and the servicer is
; reachable only in the repacked page-1 window). The lean 16 KB ROM is byte-identical.
;
; CLEAN-ROOM: own-design drain loop + packet decode. The queue packet format is
; own-design (sub/playparse.asm); the work-area addresses (MUSICF/QUETAB/VCB) are
; the MSX2 Technical Handbook layout, also reserved by our C-BIOS target. H.TIMI /
; the $0038 ISR contract is the published BIOS work-area appendix. No ROM bytes
; lifted ([memory: no-reference-rom-disasm]).

    IF ROM_BASE < $4000

; play_install: point H.TIMI at play_service. Called once at boot from init_ext_roms
; (basic/initext.asm), after the extension-ROM scan. H.TIMI is C9-free on our target
; (verified: $FD9F = C9 C9 C9 C9 C9 after boot -- neither C-BIOS nor the disk ROM
; hooks it), so a bare JP with no chain; play_service's own MUSICF==0 fast-out makes
; the always-installed seam cheap. Clobbers A, HL.
; (Interrupt-traps T1 will re-point this at htimi_service once ZTRAP is re-sited off
; the C-BIOS work-area collision — see basic/traps.asm / main.asm.)
play_install:
                ld      a,$C3               ; JP opcode
                ld      (H_TIMI),a
                ld      hl,play_service
                ld      (H_TIMI+1),hl
                ret

; play_service: H.TIMI seam target. One frame of drain across the 3 voice queues.
play_service:
                push    af
                ld      a,(MUSICF)
                or      a
                jr      nz,psv_run
                pop     af
                ret                         ; no music active -> fast out (common)
psv_run:
                push    bc
                push    de
                push    hl
                push    ix
                push    iy
                ld      ix,VCBA             ; voice 0 VCB
                ld      iy,QUETAB           ; voice 0 ring descriptor
                ld      bc,$0001            ; B = voice index 0, C = voice bitmask $01
psv_loop:
                ld      a,(MUSICF)
                and     c
                call    nz,psv_voice        ; service voice B when its MUSICF bit is set
                inc     b
                ld      a,b
                cp      3
                jr      z,psv_ret
                ld      de,VCB_STRIDE
                add     ix,de
                ld      de,QD_STRIDE
                add     iy,de
                sla     c                   ; advance to the next voice's mask bit
                jr      psv_loop
psv_ret:
                pop     iy
                pop     ix
                pop     hl
                pop     de
                pop     bc
                pop     af
                ret

; psv_voice: service one active voice. IN: IX = its VCB, IY = its ring descriptor,
; B = voice index (0..2), C = its MUSICF/voice bitmask. Preserves B/C/IX/IY (the
; loop state); freely uses A/DE/HL.
;
; Counter model (docs §2): a note occupies exactly `dur` consecutive VBLANKs with
; no gap. VCX_FRAMES holds the frames still to run for the current note. When it is
; 0 we fetch+program the next packet THIS frame, load VCX_FRAMES=dur, then fall
; through to tick it down once (so this frame counts as the note's first). The seed
; 0 the parser leaves makes the first VBLANK after a PLAY fetch packet 0.
psv_voice:
                ld      l,(ix+VCX_FRAMES)
                ld      h,(ix+VCX_FRAMES+1)
                ld      a,h
                or      l
                jr      nz,psv_tick         ; still running -> just count this frame down
psv_fetch:
                ld      l,(iy+QD_ADDR)
                ld      h,(iy+QD_ADDR+1)
                ld      a,(iy+QD_GET)
                add     a,l
                ld      l,a
                ld      a,h
                adc     a,0
                ld      h,a                 ; HL = read pointer (buffer base + get)
                ld      a,(hl)              ; packet opcode
                cp      PLAY_OP_END
                jr      z,psv_end
                cp      PLAY_OP_ENV
                jr      z,psv_env
                ; --- OP_NOTE [op, per_lo, per_hi, amp, dur_lo, dur_hi] --------
                inc     hl
                ld      e,(hl)              ; period lo
                inc     hl
                ld      d,(hl)              ; period hi   (DE = 12-bit tone period)
                inc     hl                  ; -> amp byte
                ld      a,d
                or      e
                jr      z,psv_amp           ; period 0 -> REST: leave the tone regs (§2)
                ld      a,b
                add     a,a                 ; A = 2v = tone-period LOW register
                out     ($A0),a
                ld      a,e
                out     ($A1),a
                ld      a,b
                add     a,a
                inc     a                   ; A = 2v+1 = tone-period HIGH register
                out     ($A0),a
                ld      a,d
                out     ($A1),a
psv_amp:
                ld      a,(hl)              ; amplitude byte (0..15, or $10 = follow env)
                ld      e,a
                ld      a,b
                add     a,8                 ; A = 8+v = amplitude register
                out     ($A0),a
                ld      a,e
                out     ($A1),a
                inc     hl
                ld      e,(hl)              ; dur lo
                inc     hl
                ld      d,(hl)              ; dur hi   (DE = frame duration)
                ld      (ix+VCX_FRAMES),e   ; counter = dur
                ld      (ix+VCX_FRAMES+1),d
                ld      a,(iy+QD_GET)
                add     a,6                 ; step past the 6-byte NOTE packet
                ld      (iy+QD_GET),a
                ; fall through: consume this frame as the note's first frame
psv_tick:
                ld      l,(ix+VCX_FRAMES)
                ld      h,(ix+VCX_FRAMES+1)
                dec     hl
                ld      (ix+VCX_FRAMES),l
                ld      (ix+VCX_FRAMES+1),h
                ret

; OP_ENV [op, shape, per_lo, per_hi]: program the PSG envelope (R11/R12 = period,
; R13 = shape, written last so it triggers). Consumes NO frame -> loop to fetch the
; following packet in the same VBLANK (S/M always precede a note).
psv_env:
                inc     hl
                ld      d,(hl)              ; D = envelope shape (kept across the period writes)
                inc     hl
                ld      a,11
                out     ($A0),a
                ld      a,(hl)              ; envelope period fine
                out     ($A1),a
                inc     hl
                ld      a,12
                out     ($A0),a
                ld      a,(hl)              ; envelope period coarse
                out     ($A1),a
                ld      a,13
                out     ($A0),a
                ld      a,d
                out     ($A1),a             ; shape last -> restart the envelope
                ld      a,(iy+QD_GET)
                add     a,4                 ; step past the 4-byte ENV packet
                ld      (iy+QD_GET),a
                jr      psv_fetch

; OP_END: the voice's queue is drained. Silence its channel (amp 0; the reference
; leaves the tone period as-is) and clear its MUSICF bit. Leaves VCX_FRAMES at 0.
psv_end:
                ld      a,b
                add     a,8                 ; amplitude register 8+v
                out     ($A0),a
                xor     a
                out     ($A1),a             ; amplitude 0 -> channel silent
                ld      a,c
                cpl                         ; ~(this voice's bit)
                ld      e,a
                ld      a,(MUSICF)
                and     e
                ld      (MUSICF),a          ; clear the voice's MUSICF bit
                ret

    ENDIF
