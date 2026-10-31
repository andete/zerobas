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
; PLACEMENT (docs §4a). This is main-ROM PAGE-1 resident, reached from H.TIMI --
; not page-0 window resident, not a sub-ROM tenant. The spec required page-0
; residence to survive a VBLANK landing mid page-1-tenant CALSLT (spec §4.3
; reentrancy hazard: main page 1 switched out to a sub-ROM tenant when the ISR
; fires -> the H.TIMI JP lands in sub-ROM bytes). The original §4a rationale for
; keeping page-1 residence claimed that invariant could never be reached because
; "every page-1 tenant runs DI and none opts into EI" -- this was WRONG: the
; FATPRIM tenant's dskio_calslt CALSLTs the disk ROM's DSKIO, which EIs, so a
; VBLANK CAN fire while main page 1 is switched out (this crashed the boot for a
; band of page-1 sizes -- docs/traps-t1-wiring-blocker.md). FIX: H.TIMI no longer
; points here directly; play_install routes it through htimi_guard (PAGE-0
; resident, always mapped when the ISR runs), which only falls through to
; play_service when main-ROM owns page 1, and skips PLAY one frame otherwise.
; So the servicer STAYS page-1 resident (page 0 has ~6 B free, page 1 ~860 B) and
; the reentrancy hazard is closed by the guard, not by an untrue DI invariant.
; See docs/spec-traps-t1-htimi-page1-safety.md.
;
; INTERRUPT DISCIPLINE. Entered with interrupts already disabled (the ISR); it must
; stay DI (never EI) and is therefore inherently non-reentrant -- no busy flag
; needed. It is register-transparent (saves/restores everything it uses), the
; H.TIMI convention. It touches only the PSG ($A0/$A1), the RAM queues, MUSICF, and
; the per-voice VCX_FRAMES counters -- never JIFFY or the keyboard.
;
; Repack-only, like ex_sound / ex_play: the whole body is under IF the repack build
; (the H.TIMI seam only makes sense with the servicer present, and the servicer is
; reachable only in the repacked page-1 window). The.
;
; CLEAN-ROOM: own-design drain loop + packet decode. The queue packet format is
; own-design (sub/playparse.asm); the work-area addresses (MUSICF/QUETAB/VCB) are
; the MSX2 Technical Handbook layout, also reserved by our C-BIOS target. H.TIMI /
; the $0038 ISR contract is the published BIOS work-area appendix. No ROM bytes
; lifted ([memory: no-reference-rom-disasm]).


; play_install: point H.TIMI at htimi_guard (which gates play_service). Called once
; at boot from init_ext_roms (basic/initext.asm), after the extension-ROM scan. H.TIMI
; is C9-free on our target (verified: $FD9F = C9 C9 C9 C9 C9 after boot -- neither
; C-BIOS nor the disk ROM hooks it), so a bare JP with no chain; play_service's own
; MUSICF==0 fast-out makes the always-installed seam cheap. Clobbers A, HL.
; (Interrupt-traps T1 will re-point this at htimi_service, which htimi_guard will gate
; the same way -- the guard sits in front of whatever the H.TIMI target is.)
play_install:
                ld      a,$C3               ; JP opcode
                ld      (H_TIMI),a
                ld      hl,htimi_guard      ; page-1-safety gate (subromcall.asm), NOT
                ld      (H_TIMI+1),hl       ; play_service directly: a VBLANK can land
                ret                         ; while page 1 is a sub-ROM tenant (FATPRIM's
                                            ; DSKIO EIs) -> play_service would be paged
                                            ; out. See docs/spec-traps-t1-htimi-page1-
                                            ; safety.md + traps-t1-wiring-blocker.md.

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
                ld      a,(MUSICF)
                or      a
                call    z,psv_sync          ; nobody playing: release the waiting voices
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
                ; 🔴 D-PLAYQUEUE (2026-10-31): THE QUEUE IS A RING NOW, read up to
                ; QD_PUT and wrapped at 128 (sysvars.inc, PK_*: the reference's
                ; packet sizes). An empty ring is not the end -- a PLAY still being
                ; written (main waiting for room) may not have reached its end
                ; marker yet -- so the voice stays on and looks again next frame.
                ld      a,(iy+QD_GET)
                cp      (iy+QD_PUT)
                ret     z                   ; nothing queued yet
                call    psv_get
                cp      PK_END
                jp      nc,psv_end
                cp      PK_REST
                jr      nc,psv_rest
                push    af                  ; [byte 0: tag | shape<<2 | envset<<1]
                call    psv_get
                ld      e,a                 ; E = period low
                call    psv_get
                ld      d,a                 ; D = amplitude
                push    de                  ; [b0][amp:per_lo]
                call    psv_get
                ld      e,a                 ; frames low
                call    psv_get             ; per_hi<<4 | frames_hi
                ld      d,a
                and     $0F
                ld      (ix+VCX_FRAMES+1),a
                ld      (ix+VCX_FRAMES),e
                ld      a,b
                add     a,a                 ; A = 2v = tone-period LOW register
                out     ($A0),a
                pop     hl                  ; H = amplitude, L = period low
                ld      a,l
                out     ($A1),a
                ld      a,b
                add     a,a
                inc     a                   ; A = 2v+1 = tone-period HIGH register
                out     ($A0),a
                ld      a,d
                rrca
                rrca
                rrca
                rrca
                and     $0F
                out     ($A1),a
                pop     af                  ; A = byte 0
                ld      e,a
                cp      PK_NOTEP
                jr      c,psv_noper         ; NOTE: no envelope period follows
                push    hl                  ; H = the amplitude (psv_get uses HL --
                                            ; the first cut wrote the buffer's high
                                            ; byte, $F9, as an envelope note's volume)
                ld      a,11
                out     ($A0),a
                call    psv_get
                out     ($A1),a             ; envelope period fine
                ld      a,12
                out     ($A0),a
                call    psv_get
                out     ($A1),a             ; envelope period coarse
                pop     hl
psv_noper:
                bit     1,e
                jr      z,psv_amp           ; no S or M since the last note
                ld      a,13
                out     ($A0),a
                ld      a,e
                rrca
                rrca
                and     $0F
                out     ($A1),a             ; shape last -> restart the envelope
psv_amp:
                ld      a,b
                add     a,8                 ; A = 8+v = amplitude register
                out     ($A0),a
                ld      a,h
                out     ($A1),a
psv_tick:
                ld      l,(ix+VCX_FRAMES)
                ld      h,(ix+VCX_FRAMES+1)
                dec     hl
                ld      (ix+VCX_FRAMES),l
                ld      (ix+VCX_FRAMES+1),h
                ret
psv_rest:
                call    psv_get
                ld      (ix+VCX_FRAMES),a
                call    psv_get
                ld      (ix+VCX_FRAMES+1),a
                ld      h,0                 ; amplitude 0: silent (the tone registers stay)
                jr      psv_amp
; psv_get: A = the ring's next byte; QD_GET steps on, wrapping at 128. Uses HL.
psv_get:
                ld      l,(iy+QD_ADDR)
                ld      h,(iy+QD_ADDR+1)
                ld      a,(iy+QD_GET)
                add     a,l
                ld      l,a
                adc     a,h
                sub     l
                ld      h,a                 ; HL = base + get
                ld      a,(iy+QD_GET)
                inc     a
                and     127
                ld      (iy+QD_GET),a
                ld      a,(hl)
                ret
; psv_end: a PLAY's end marker. The voice goes silent and WAITS (QD_PUTBAK = 1,
; its MUSICF bit clear, so PLAY(n) reads 0 -- measured, scratchpad/
; playsync_measure.out) until no voice is playing; play_service then releases
; every waiting voice together (psv_sync). That is the VG-8020's sync: a voice
; reaching its end marker waits for every voice still playing, even when the
; next PLAY named only that voice.
psv_end:
                ld      a,b
                add     a,8                 ; amplitude register 8+v
                out     ($A0),a
                xor     a
                out     ($A1),a             ; amplitude 0 -> channel silent
                inc     a
                ld      (iy+QD_PUTBAK),a    ; waiting
                ld      a,c
                cpl                         ; ~(this voice's bit)
                ld      e,a
                ld      a,(MUSICF)
                and     e
                ld      (MUSICF),a          ; clear the voice's MUSICF bit
                ret
; psv_sync: no voice is playing -- every voice waiting at an end marker steps on
; together; one with more queued plays it from the next frame (its frames are 0).
psv_sync:
                ld      iy,QUETAB
                ld      bc,$0301            ; B = 3 voices, C = voice-0 bit
pss_lp:
                ld      a,(iy+QD_PUTBAK)
                or      a
                jr      z,pss_next
                xor     a
                ld      (iy+QD_PUTBAK),a
                ld      a,(iy+QD_GET)
                cp      (iy+QD_PUT)
                jr      z,pss_next          ; nothing after the end marker: idle
                ld      a,(MUSICF)
                or      c
                ld      (MUSICF),a
pss_next:
                ld      de,QD_STRIDE
                add     iy,de
                sla     c
                djnz    pss_lp
                ret
; psv_flush: BEEP, a break, an abort (psg_silence, basic/sound.asm, under its DI)
; reset PLAY as the VG-8020 does: the queues EMPTY -- they are rings kept across
; PLAYs now (D-PLAYQUEUE), so stopped music must not resume -- and the PLAY
; settings go back to their defaults: after `PLAY"T255L16"` and BEEP, a `C`
; lasts 27 jiffies on the VG-8020 (T120 L4) and lasted 3 here; a TRAPPED error
; keeps them on both (scratchpad/playbeepstate_measure.out; a break and an
; untrapped abort reach here too and were not measured separately). A zero
; tempo is the parser's cold-boot sign: the next PLAY re-runs pt_init
; (sub/playparse.asm), which seeds the defaults and the rings. Clobbers A.
psv_flush:
                xor     a
                ld      (VCBA+VCX_TEMPO),a
                ret
