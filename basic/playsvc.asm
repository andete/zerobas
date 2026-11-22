; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; playsvc.asm — the background music player (audio arc, Slice 3; rebuilt 2026-11-21).
; ===========================================================================
; play_service plays one frame of the queued music. PLAY's parser tenant
; (sub/playparse.asm) -- or any program, through PUTQ ($00F9) -- fills the three
; queues (QUETAB $F959, VOICAQ / VOICBQ / VOICCQ) in the VG-8020's packet format and
; STRTMS ($0099) starts them; from then on this routine plays them from the BIOS's
; OWN timer interrupt: C-BIOS's $0038 handler calls isr_music (basic/subromcall.asm,
; page 0) in place of its `ld (JIFFY),hl` ($170F, basic/islands.asm), and isr_music
; maps main page 1 in and calls here when MUSICF is not 0. No BASIC set-up is needed,
; and a program that takes H.TIMI over still hears its music (H.TIMI is called first,
; as before; it now carries only the traps poll).
;
; THE MODEL, black-box (probes/bios/play_trace.py: PUTQ'd packets + STRTMS, every PSG
; write per frame, scratchpad/playtrace_run1.out; the VG-8020 and the NMS 8250 the
; same in all 12 scenarios; zerobas against the VG-8020: scratchpad/playtrace_run2.out). Per frame, for voices A, B, C in that order whose MUSICF
; bit is set: the voice block's FIRST WORD ($FB41 / $FB66 / $FB8B -- STRTMS sets it to
; 1) counts down by one; when it reaches 0 the next packet is read:
;   - the queue empty: nothing -- the word stays 0, so the next frame takes it to
;     $FFFF (a voice whose queue runs dry is silent for 65536 frames: measured);
;   - $FF (the end): R(8+v) := 0 and the voice's MUSICF bit is cleared;
;   - otherwise [n << 5 | dur 12..8] [dur 7..0] [vol] ...: the word := dur (0 counts
;     as 65536), R(8+v) := vol; for n = 1 (a rest) nothing more; else R13 := vol when
;     vol bit 4 (the envelope) is set, then, when vol bit 6 is set, the M bytes (high,
;     low in the queue) as R11 := low, R12 := high, then the tone (high, low) as
;     R(2v) := low, R(2v+1) := high.
; After the three voices, when MUSICF is 0 the next round starts as STRTMS (PLYCNT
; not 0: PLYCNT - 1, MUSICF 7, the words := 1). A frame with MUSICF 0 does nothing,
; whatever PLYCNT says. R7 is never written.
;
; INTERRUPT DISCIPLINE. Called by isr_music inside the BIOS's interrupt handler, DI,
; which has saved every register (main and alternate, IX, IY) and needs none of them
; after: play_service clobbers what it likes and stays DI.
;
; CLEAN-ROOM: own code; the model is the black-box trace above (PSG port writes and
; work-area RAM, never a ROM byte). The work-area addresses are the published layout.

; play_install: point H.TIMI at htimi_guard (BASIC's traps poll). Called once at boot
; from init_ext_roms (basic/initext.asm), after the extension-ROM scan. The music is no
; longer on this hook: the BIOS's own interrupt plays it (isr_music). Clobbers A, HL.
play_install:
                ld      a,$C3               ; JP opcode
                ld      (H_TIMI),a
                ld      hl,htimi_guard      ; page-1-safety gate (subromcall.asm): a
                ld      (H_TIMI+1),hl       ; VBLANK can land while page 1 is a sub-ROM
                ret                         ; tenant (FATPRIM's DSKIO EIs). See docs/
                                            ; spec-traps-t1-htimi-page1-safety.md.

; play_service: one frame of the music (the model above). IN: MUSICF not 0 (isr_music
; tests it), main page 1 mapped, DI. Clobbers every register.

; psv_voice: IX = the voice's block, IY = its queue's descriptor, B = the voice, C = its
; bit. Count the block's first word down; at 0 read a packet.
; psv_pair: A = a register; reads high then low from the queue, writes R(A) := low,
; then R(A+1) := high.
; psg_out: PSG register A := E; A and E kept.
; psv_end: the voice's end marker -- R(8+v) := 0, its MUSICF bit cleared.
; psv_get: A = the queue's next byte. The get index is stepped FIRST (the VG-8020's
; rings: GET = the last byte read) and masked with the descriptor's size byte.
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
