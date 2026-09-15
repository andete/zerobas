; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — playparse.asm  (audio Slice 2a: the MML parser tenant)
; ===========================================================================
; play_parse_tenant — SUBROM_IDX_PLAY_PARSE (page 1), the heavy PLAY parser
; evicted to the sub-ROM (docs/spec-basic-audio-play-slice2a.md). A pure RAM leaf
; like fatprim/dirverb: the resident ex_play stub (basic/play.asm) evaluates the
; up-to-three MML string arguments and marshals each present voice's (body ptr,
; length) into that voice's VCB (VCXPTR/VCXLEN) plus a voices-present bitmask in
; AUDIO_VMASK; this tenant parses each string into its VOICxQ ring buffer as an
; own-design PLAY_OP_* packet stream, then sets MUSICF LAST (so a Slice-3 VBLANK
; can never drain a half-built queue, arc spec §4.3). NO live drain here — the
; interrupt servicer is Slice 3; PLAY returns immediately after this parse.
;
; The linear MML grammar (Slice 2a; `X` substring-exec is Slice 2b):
;   A-G [#|+|-] [len][.]   note with optional accidental, length, dots
;   N n                    note by absolute number (0 = rest), default length
;   R [len][.]             rest
;   O n / > / <            octave set / up / down (1..8)
;   L n                    default note length (1..64)
;   T n                    tempo (32..255)
;   V n                    volume (0..15)  [also disables envelope mode]
;   S n                    envelope shape (0..15) [enables envelope mode] -> OP_ENV
;   M n                    envelope period (0..65535) -> OP_ENV
;   space                  ignored
; ('&' tie is NOT MSX1 PLAY MML -- the VG-8020 raises Illegal function call for it,
;  empirically confirmed; it lands in the unknown-command path.)
; The per-voice state (octave/length/tempo/volume/envelope) lives in the VCB and
; PERSISTS across PLAY statements (D4-B, faithful); pt_init seeds the cold-boot
; defaults once (TEMPOX==0 sentinel; C-BIOS zeroes $F380.. at boot).
;
; Register allocation during a voice parse: IX = VCB base, IY = QUETAB ring
; descriptor, DE = buffer write pointer, B = source bytes remaining, MCLPTR (RAM)
; = source cursor, HL / A / C = working. A packet byte is appended via pt_put,
; which range-checks against PLY_BUFEND (128-byte VOICxQ) and raises "String too
; long" (ERR 15) on overflow -- the faithful cap, since 128 B is the real MSX
; per-voice buffer size.
;
; CLEAN-ROOM: original code. PLAY MML *syntax* is the public MSX-BASIC language
; reference; the work-area layout is the MSX2 Technical Handbook (also reserved by
; our target C-BIOS). The note->period table and the tempo->frame formula are
; own-design (tests/mml_ref.py is their single source of truth; the exact constant
; is tuned in Slice 3's frame differential). No disassembly.
; ===========================================================================

; --- play_parse_tenant: the SUBROM_IDX_PLAY_PARSE entry --------------------
play_parse_tenant:
                ld      a,(VCBA + VCX_TEMPO)
                or      a
                call    z,pt_init           ; cold-boot seed of the PLAY work area (once)
                ld      bc,$0001            ; B = voice index 0, C = voice-0 mask bit
pt_vloop:
                ld      a,(AUDIO_VMASK)
                and     c                   ; is this voice present?
                jr      z,pt_vnext
                ; D-PLAYEMPTY (2026-09-11, gicini m.empty): an EMPTY string queues
                ; nothing, and the reference's MUSICF reads 0 right after `PLAY""`.
                ; Here the voice's bit was set and cleared only by the next ISR
                ; tick -- a race the row won for months because RUN left a tick
                ; pending at the tenant's EI, and lost once the screen editor's
                ; own tenant call consumed that tick first. Drop the voice from
                ; the commit mask instead: no queue, no bit.
                push    bc
                call    pt_vcb_ix           ; IX = VCB base (preserves B)
                ld      a,(ix+VCX_VCXLEN)
                pop     bc
                or      a
                jr      nz,pt_vparse
                ld      a,c
                cpl
                ld      hl,AUDIO_VMASK
                and     (hl)
                ld      (hl),a              ; this voice is not in the commit
                jr      pt_vnext
pt_vparse:
                push    bc                  ; pt_voice reuses B (source count) + clobbers C
                call    pt_voice            ; parse voice B -> its VOICxQ; CF=1 on error
                pop     bc
                ret     c                   ; parse error -> AUDIO_STATUS already set, bail
pt_vnext:
                rlc     c                   ; next voice's mask bit (1->2->4)
                inc     b
                ld      a,b
                cp      3
                jr      c,pt_vloop
                call    pt_commit           ; MUSICF (LAST) + PLYCNT
                xor     a
                ld      (AUDIO_STATUS),a    ; 0 = ok
                ret

; --- pt_init: seed the cold-boot PLAY defaults into all three VCBs ----------
pt_init:
                ld      ix,VCBA
                ld      b,3
pi_lp:
                ld      (ix+VCX_OCTAVE),PLAY_DEF_OCTAVE
                ld      (ix+VCX_NOTEL),PLAY_DEF_NOTEL
                ld      (ix+VCX_TEMPO),PLAY_DEF_TEMPO
                ld      (ix+VCX_VOLUME),PLAY_DEF_VOLUME
                ld      (ix+VCX_ENVSH),0
                ld      de,VCB_STRIDE
                add     ix,de
                djnz    pi_lp
                xor     a
                ld      (MUSICF),a
                ld      (PLYCNT),a
                ret

; --- pt_commit: publish the parsed queues (MUSICF set LAST) ------------------
; 🔴 OR, NOT STORE (D-MUSICF, 2026-08-31). This was `ld (MUSICF),a` -- a
; wholesale overwrite -- and a PLAY naming FEWER voices than were sounding
; cleared a still-playing voice's bit: its drain stopped, psv_end (the only
; writer of amplitude 0) became unreachable, the channel kept sounding at its
; last amplitude, and PLAY(2) read idle under an audible tone. Both references
; keep the unmentioned voice playing (scratchpad/musicf_probe.py r.drop:
; -1/-1/0 before, 4/4 SAME after). Voices being REPLACED are in both masks, so
; OR is exact; the drain is suspended throughout the tenant (htimi_guard), so
; no torn read.
pt_commit:
                ld      a,(AUDIO_VMASK)
                ld      hl,MUSICF
                or      (hl)                ; unmentioned voices keep playing
                ld      (hl),a
                ld      a,(PLYCNT)
                inc     a
                ld      (PLYCNT),a
                ret

; --- pt_voice: parse voice B's MML string into its ring buffer --------------
;   in:  B = voice index 0..2 (its VCB has VCXPTR/VCXLEN marshalled by ex_play)
;   out: CF=0 ok / CF=1 error (AUDIO_STATUS = ERR code). Clobbers everything.
pt_voice:
                ld      a,b
                ld      (VOICEN),a
                ld      (QUEUEN),a
                call    pt_vcb_ix           ; IX = VCB base (preserves B)
                call    pt_buf              ; IY = ring desc, DE = buffer base (preserves B)
                ld      l,(ix+VCX_VCXPTR)
                ld      h,(ix+VCX_VCXPTR+1)
                ld      (MCLPTR),hl         ; MML source cursor
                ld      b,(ix+VCX_VCXLEN)   ; B = source bytes remaining
pt_ch_loop:
                ld      a,b
                or      a
                jp      z,pt_voice_end
                push    hl                  ; fetch + advance the source cursor
                ld      hl,(MCLPTR)
                ld      a,(hl)
                inc     hl
                ld      (MCLPTR),hl
                pop     hl
                dec     b
                call    pt_upcase
                cp      ' '
                jp      z,pt_ch_loop        ; skip spaces
                cp      'A'
                jr      c,pt_nn
                cp      'G'+1
                jp      c,pt_note_letter    ; A..G -> a note
pt_nn:
                cp      'N'
                jp      z,pt_cmd_n
                cp      'R'
                jp      z,pt_cmd_rest
                cp      'O'
                jp      z,pt_cmd_octave
                cp      'L'
                jp      z,pt_cmd_length
                cp      'T'
                jp      z,pt_cmd_tempo
                cp      'V'
                jp      z,pt_cmd_volume
                cp      'S'
                jp      z,pt_cmd_env_shape
                cp      'M'
                jp      z,pt_cmd_env_per
                ; '&' (tie), '>' and '<' are NOT MSX1 PLAY commands -- BOTH
                ; references raise Illegal function call for all three (D-KWPLAY
                ; 2026-09-15: scratchpad/playpsg_probe.py and playmml_probe.py, in
                ; three spellings each, VG-8020 AND CF-3300). '>' and '<' were
                ; IMPLEMENTED HERE until that measurement -- this tree ACCEPTED two
                ; commands both references refuse -- and docs/spec-basic-audio-play.md
                ; 2.2 had them from a "published MSX Wiki" list, the same way it once
                ; had '&'. They fall through to pt_illegal like any unknown command.
                ; fall through: unrecognised MML command
pt_illegal:
                ld      a,5                 ; Illegal function call
                ld      (AUDIO_STATUS),a
                scf
                ret                         ; abort the voice (CF=1)

pt_voice_end:
                ld      a,PLAY_OP_END
                call    pt_put
                ret     c
                ld      l,(iy+QD_ADDR)      ; put = write pointer - buffer base
                ld      h,(iy+QD_ADDR+1)
                ex      de,hl               ; HL = write ptr, DE = base
                or      a
                sbc     hl,de
                ld      a,l
                ld      (iy+QD_PUT),a       ; store the queue's byte count
                or      a                   ; CF=0 success
                ret

; --- pt_note_letter: A = 'A'..'G' -> compute the note number, then emit ------
; 🔴 ACCIDENTAL FIRST, MOD 12, INSIDE THE OCTAVE (D-CLAMPPITCH, 2026-08-31).
; This used to add the octave base FIRST, apply the accidental to the 0..95
; note number, and clamp the edges (C- at O1 -> note 0, B# at O8 -> note 95).
; The reference does neither the borrow nor the clamp: the PSG trace shows
; `O4 C-` playing B4 (period 227, not B3's 453) and `O4 B#` playing C4 (428,
; not C5's 214) -- the accidental wraps the SEMITONE mod 12 and the octave
; never moves, at the edges and mid-range alike. The two rules COINCIDE on the
; edge rows alone (B1 is both "mod 12 at O1" and "borrow then clamp"), which
; is why scratchpad/clamppitch_probe.py carries the mid-octave separating rows.
; The result is always (octave-1)*12 + 0..11 = 0..95, so the old clamp is
; unreachable and deleted rather than kept as dead reassurance.
pt_note_letter:
                sub     'A'
                ld      hl,pt_semitab
                add     a,l
                ld      l,a
                ld      a,0
                adc     a,h
                ld      h,a
                ld      c,(hl)              ; C = semitone 0..11
                ld      a,b                 ; accidental? (only if a char remains)
                or      a
                jr      z,pnl_base
                push    hl
                ld      hl,(MCLPTR)
                ld      a,(hl)
                pop     hl
                cp      '#'
                jr      z,pnl_sharp
                cp      '+'
                jr      z,pnl_sharp
                cp      '-'
                jr      z,pnl_flat
                jr      pnl_base
pnl_sharp:
                inc     c
                ld      a,c
                cp      12
                jr      c,pnl_eat
                ld      c,0                 ; B# -> C of the SAME octave
                jr      pnl_eat
pnl_flat:
                dec     c
                jp      p,pnl_eat
                ld      c,11                ; C- -> B of the SAME octave
pnl_eat:
                push    hl                  ; consume the accidental
                ld      hl,(MCLPTR)
                inc     hl
                ld      (MCLPTR),hl
                pop     hl
                dec     b
pnl_base:
                ld      a,(ix+VCX_OCTAVE)
                dec     a
                ld      hl,pt_oct12
                add     a,l
                ld      l,a
                ld      a,0
                adc     a,h
                ld      h,a
                ld      a,(hl)              ; (octave-1)*12
                add     a,c
                ld      c,a                 ; C = note number, 0..95 by construction
                ; fall through

; --- pt_emit_pitch: C = note number 0..95 -> emit an OP_NOTE ----------------
pt_emit_pitch:
                ld      hl,pt_period        ; HL = &pt_period[note*2]
                ld      a,c
                add     a,a
                add     a,l
                ld      l,a
                ld      a,0
                adc     a,h
                ld      h,a
                ld      a,(hl)
                inc     hl
                ld      h,(hl)
                ld      l,a                 ; HL = tone period
                ld      a,PLAY_OP_NOTE
                call    pt_put
                ret     c
                ld      a,l
                call    pt_put              ; period low
                ret     c
                ld      a,h
                call    pt_put              ; period high
                ret     c
                call    pt_note_amp         ; A = amplitude (envelope-mode or volume)
                call    pt_put
                ret     c
                ld      (PLY_LASTDUR),de    ; save the write pointer (pt_length clobbers DE)
                call    pt_length           ; HL = frame duration; clobbers DE
                ret     c
                ld      de,(PLY_LASTDUR)    ; restore the write pointer (= frames field)
                ld      a,l
                call    pt_put              ; frames low
                ret     c
                ld      a,h
                call    pt_put              ; frames high
                ret     c
                jp      pt_ch_loop

; --- pt_note_amp: A = amplitude byte for the current voice ------------------
pt_note_amp:
                ld      a,(ix+VCX_ENVSH)
                bit     7,a                 ; envelope mode?
                jr      nz,pna_env
                ld      a,(ix+VCX_VOLUME)
                and     $0F
                ret
pna_env:
                ld      a,(ix+VCX_VOLUME)
                and     $0F                 ; the PSG ignores bits 0-3 in envelope mode,
                or      $10                 ; but the VG-8020 still writes the volume nibble
                ret                         ; alongside bit 4 (measured: S8 default-V -> $18)

; --- pt_cmd_rest: emit a silent OP_NOTE (amp 0) for the parsed length --------
pt_cmd_rest:
                ld      a,PLAY_OP_NOTE
                call    pt_put
                ret     c
                xor     a
                call    pt_put              ; period low = 0
                ret     c
                xor     a
                call    pt_put              ; period high = 0
                ret     c
                xor     a
                call    pt_put              ; amplitude = 0 (silent)
                ret     c
                ld      (PLY_LASTDUR),de    ; save the write pointer (pt_length clobbers DE)
                call    pt_length
                ret     c
                ld      de,(PLY_LASTDUR)
                ld      a,l
                call    pt_put
                ret     c
                ld      a,h
                call    pt_put
                ret     c
                jp      pt_ch_loop

; --- pt_cmd_n: N n -> note by absolute number (0 = rest) --------------------
pt_cmd_n:
                call    pt_number
                jp      nc,pt_illegal
                ld      a,h
                or      a
                jp      nz,pt_illegal       ; > 255
                ld      a,l
                cp      97
                jp      nc,pt_illegal       ; > 96
                or      a
                jp      z,pt_cmd_rest       ; N0 = rest
                ; 🔴 NO `dec a` HERE: `N n` INDEXES pt_period AT n, NOT n-1.
                ; Measured on both references (D-KWPLAY 2026-09-15, scratchpad/
                ; playnote_probe.py): N1 sounds 3228 = pt_period[1] and N96 sounds 13
                ; = pt_period[96], so the reference's N1 is C#1 and its N96 is C9 --
                ; one semitone ABOVE the letter-note range this table indexes from 0.
                ; The `dec a` that used to sit here made every `N n` a semitone flat.
                ld      c,a
                jp      pt_emit_pitch

; --- octave / length / tempo / volume / envelope setters -------------------
pt_cmd_octave:
                call    pt_number
                jp      nc,pt_illegal
                ld      a,h
                or      a
                jp      nz,pt_illegal
                ld      a,l
                or      a
                jp      z,pt_illegal
                cp      9
                jp      nc,pt_illegal
                ld      (ix+VCX_OCTAVE),a
                jp      pt_ch_loop
pt_cmd_length:
                call    pt_number
                jp      nc,pt_illegal
                ld      a,h
                or      a
                jp      nz,pt_illegal
                ld      a,l
                or      a
                jp      z,pt_illegal
                cp      65
                jp      nc,pt_illegal
                ld      (ix+VCX_NOTEL),a
                jp      pt_ch_loop
pt_cmd_tempo:
                call    pt_number
                jp      nc,pt_illegal
                ld      a,h
                or      a
                jp      nz,pt_illegal
                ld      a,l
                cp      32
                jp      c,pt_illegal
                ld      (ix+VCX_TEMPO),a
                jp      pt_ch_loop
pt_cmd_volume:
                call    pt_number
                jp      nc,pt_illegal
                ld      a,h
                or      a
                jp      nz,pt_illegal
                ld      a,l
                cp      16
                jp      nc,pt_illegal
                ld      (ix+VCX_VOLUME),a
                ld      a,(ix+VCX_ENVSH)
                and     $7F                 ; V disables envelope mode
                ld      (ix+VCX_ENVSH),a
                jp      pt_ch_loop
pt_cmd_env_shape:
                call    pt_number
                jp      nc,pt_illegal
                ld      a,h
                or      a
                jp      nz,pt_illegal
                ld      a,l
                cp      16
                jp      nc,pt_illegal
                or      $80                 ; set envelope-mode bit
                ld      (ix+VCX_ENVSH),a
                jp      pt_emit_env
pt_cmd_env_per:
                call    pt_number
                jp      nc,pt_illegal
                ld      a,(PLY_NUMOVF)
                or      a
                jp      nz,pt_illegal       ; M65600 wraps -> ERR 5 on both refs
                                            ; (m.wrap); M65535 itself is LEGAL
                                            ; (m.max), which is why the latch is
                                            ; read here and not the $FFFF value
                ld      a,h
                or      l
                jp      z,pt_illegal        ; M0 -> ERR 5 on both refs (m.zero)
                ld      (ix+VCX_ENVPER),l
                ld      (ix+VCX_ENVPER+1),h
                jp      pt_emit_env

; --- pt_emit_env: OP_ENV = [op, shape, per_lo, per_hi] ---------------------
pt_emit_env:
                ld      a,PLAY_OP_ENV
                call    pt_put
                ret     c
                ld      a,(ix+VCX_ENVSH)
                and     $0F                 ; shape (drop the mode bit)
                call    pt_put
                ret     c
                ld      a,(ix+VCX_ENVPER)
                call    pt_put
                ret     c
                ld      a,(ix+VCX_ENVPER+1)
                call    pt_put
                ret     c
                jp      pt_ch_loop

; --- pt_length: parse optional length digits + dots -> HL = frame count ------
;   uses IX (VCX_TEMPO/VCX_NOTEL), MCLPTR/B. CF=1 (+ AUDIO_STATUS) on a bad length.
pt_length:
                call    pt_number
                jr      c,pl_have
                ld      a,(ix+VCX_NOTEL)    ; no explicit length -> default
                jr      pl_val
pl_have:
                ld      a,h
                or      a
                jr      nz,pl_bad
                ld      a,l
                or      a
                jr      z,pl_bad            ; length 0 invalid
                cp      65
                jr      nc,pl_bad           ; length > 64 invalid
pl_val:
                ld      e,a                 ; E = length
                ld      c,0                 ; C = dot count
pl_dots:
                ld      a,b
                or      a
                jr      z,pl_calc
                push    hl
                ld      hl,(MCLPTR)
                ld      a,(hl)
                pop     hl
                cp      '.'
                jr      nz,pl_calc
                push    hl                  ; consume the dot
                ld      hl,(MCLPTR)
                inc     hl
                ld      (MCLPTR),hl
                pop     hl
                dec     b
                inc     c
                jr      pl_dots
pl_calc:
                ld      d,(ix+VCX_TEMPO)    ; D = tempo, E = length, C = dots
                jp      pt_getframes
pl_bad:
                ld      a,5
                ld      (AUDIO_STATUS),a
                scf
                ret

; --- pt_getframes: D=tempo, E=length, C=dots -> HL = frames -----------------
;   frames = 12000 / tl  (floor; tl = tempo*length), VG-8020-pinned
;   (docs/audio-slice3-characterization.md §1). Dots: the first dot adds
;   ceil(base/2), each subsequent dot floor of the running addend -- realised by a
;   single `inc de` before the halving loop (the +1 survives only the first srl,
;   giving ceil; later iterations halve the already-floored addend). tests/mml_ref.py
;   note_frames is the oracle. Preserves B (source count); clobbers A, C, DE, HL.
pt_getframes:
                push    bc                  ; save B (source count); C = dots
                ld      a,d                 ; tl = tempo*length
                ld      hl,0
                or      a
                jr      z,pgf_have_tl
                ld      b,a
                ld      d,0                 ; DE = length
pgf_mul:
                add     hl,de
                djnz    pgf_mul
pgf_have_tl:
                ex      de,hl               ; DE = tl
                ld      hl,12000
                call    pt_div16            ; HL = 12000 / tl  (floor)
                pop     bc                  ; B = source count, C = dots
                ld      a,c
                or      a
                jr      z,pgf_min
                ld      d,h                 ; DE = base frames (running addend seed)
                ld      e,l
                inc     de                  ; first dot rounds UP: (base+1)>>1 = ceil(base/2)
pgf_dot:
                srl     d
                rr      e
                add     hl,de               ; frames += addend (ceil first, floor after)
                dec     c
                jr      nz,pgf_dot
pgf_min:
                ld      a,h                 ; clamp to a minimum of 1 frame
                or      l
                ret     nz
                inc     hl
                ret

; --- pt_div16: HL / DE -> HL = quotient (floor). Clobbers A, BC; DE kept -----
pt_div16:
                ld      bc,0
pd_lp:
                ld      a,h
                cp      d
                jr      c,pd_done
                jr      nz,pd_sub
                ld      a,l
                cp      e
                jr      c,pd_done
pd_sub:
                or      a
                sbc     hl,de
                inc     bc
                jr      pd_lp
pd_done:
                ld      h,b
                ld      l,c
                ret

; --- pt_number: parse decimal digits at MCLPTR -> HL = value, CF=1 if any ----
;   advances MCLPTR + decrements B per digit. Preserves DE (write ptr), IX, IY.
;   🔴 D-PLAYCORNER (2026-08-31): a number that OVERFLOWS 16 bits used to wrap
;   and ALIAS INTO RANGE -- `T65568` became T32 and PASSED the range check,
;   where both references raise ERR 5 (rows w.twrap/w.owrap/w.vwrap/m.wrap).
;   Now: overflow latches PLY_NUMOVF and the result SATURATES to $FFFF, which
;   every 8-bit-range caller already rejects through its existing `ld a,h /
;   or a` check -- zero call-site changes there. Only M (16-bit domain) must
;   read the latch itself, because a saturated $FFFF is indistinguishable from
;   a legitimate M65535 (row m.max: accepted on both references).
pt_number:
                xor     a
                ld      (PLY_NUMOVF),a      ; overflow latch: clear per literal
                ld      hl,0                ; accumulator
                ld      c,0                 ; digit count
pn_lp:
                ld      a,b
                or      a
                jr      z,pn_end
                push    hl
                ld      hl,(MCLPTR)
                ld      a,(hl)
                pop     hl
                cp      '0'
                jr      c,pn_end
                cp      '9'+1
                jr      nc,pn_end
                sub     '0'                 ; A = digit
                ; overflow test BEFORE the multiply: 10v+d > 65535 iff v > 6553,
                ; or v = 6553 and d >= 6 (65530+5 = 65535 is still exact).
                push    af                  ; A = digit, needed after the test
                ld      a,h
                cp      $19                 ; v >= $1A00 (6656) -> overflow
                jr      c,pn_fits
                jr      nz,pn_ovf           ; $1Axx.. -> overflow
                ld      a,l                 ; H = $19: compare the low byte
                cp      $99
                jr      c,pn_fits           ; < $1999 (6553) -> fits
                jr      nz,pn_ovf           ; > $1999 -> overflow
                pop     af                  ; exactly 6553: only d >= 6 overflows
                push    af
                cp      6
                jr      c,pn_fits
pn_ovf:
                ld      a,1
                ld      (PLY_NUMOVF),a      ; latch; the wrapped value is dead --
                                            ; pn_end saturates it
pn_fits:
                pop     af                  ; A = digit
                push    de                  ; HL = HL*10 + digit
                ex      de,hl
                ld      h,d
                ld      l,e
                add     hl,hl               ; 2*v
                push    hl
                add     hl,hl
                add     hl,hl               ; 8*v
                pop     de                  ; DE = 2*v
                add     hl,de               ; 10*v
                ld      e,a
                ld      d,0
                add     hl,de               ; 10*v + digit
                pop     de                  ; restore write pointer
                push    hl                  ; advance the source cursor
                ld      hl,(MCLPTR)
                inc     hl
                ld      (MCLPTR),hl
                pop     hl
                dec     b
                inc     c
                jr      pn_lp
pn_end:
                ld      a,(PLY_NUMOVF)
                or      a
                jr      z,pn_ret
                ld      hl,$FFFF            ; overflowed -> saturate: every 8-bit
                                            ; range check rejects this
pn_ret:
                ld      a,c
                or      a
                ret     z                   ; no digits -> CF=0, HL = 0
                scf                         ; digits present -> CF=1
                ret

; --- pt_upcase: A in a..z -> A..Z ------------------------------------------
pt_upcase:
                cp      'a'
                ret     c
                cp      'z'+1
                ret     nc
                sub     32
                ret

; --- pt_vcb_ix: B = voice -> IX = VCB base (preserves B) --------------------
pt_vcb_ix:
                ld      ix,VCBA
                ld      a,b
                or      a
                ret     z
                ld      de,VCB_STRIDE
                add     ix,de
                dec     a
                ret     z
                add     ix,de
                ret

; --- pt_buf: B = voice -> IY = ring desc, DE = buffer base, PLY_BUFEND set ---
;   also (re)initialises the QUETAB ring descriptor for this voice.
pt_buf:
                ld      iy,QUETAB
                ld      a,b
                or      a
                jr      z,pb_addr
                ld      de,QD_STRIDE
                add     iy,de
                dec     a
                jr      z,pb_addr
                add     iy,de
pb_addr:
                ld      hl,VOICAQ
                ld      a,b
                or      a
                jr      z,pb_init
                ld      de,128
                add     hl,de
                dec     a
                jr      z,pb_init
                add     hl,de
pb_init:
                ld      (iy+QD_PUT),0
                ld      (iy+QD_GET),0
                ld      (ix+VCX_FRAMES),0   ; Slice 3: reset drain counter so the first
                ld      (ix+VCX_FRAMES+1),0 ;   VBLANK fetches packet 0 (IX = this voice's VCB)
                ld      (iy+QD_PUTBAK),0
                ld      (iy+QD_SIZE),128
                ld      (iy+QD_ADDR),l
                ld      (iy+QD_ADDR+1),h
                ld      de,128
                push    hl
                add     hl,de
                ld      (PLY_BUFEND),hl     ; buffer base + 128
                pop     hl
                ex      de,hl               ; DE = buffer base (write pointer)
                ret

; --- pt_put: append A to (DE); DE++. Overflow -> CF=1 + AUDIO_STATUS=15 ------
;   Preserves HL, BC, IX, IY (and the input A on the success path is consumed).
pt_put:
                push    hl
                ld      hl,(PLY_BUFEND)
                scf
                ccf                         ; clear carry without touching A
                sbc     hl,de               ; end - write ptr: <=0 means full
                pop     hl
                jr      z,pp_ovf
                jr      c,pp_ovf
                ld      (de),a
                inc     de
                ret                         ; CF=0 (sbc left it clear)
pp_ovf:
                ld      a,15                ; String too long
                ld      (AUDIO_STATUS),a
                scf
                ret

; --- data: semitone map, octave*12 table, note->period table ----------------
; pt_semitab[letter-'A'] = semitone (C=0..B=11): A B C D E F G
pt_semitab:     db      9, 11, 0, 2, 4, 5, 7
; pt_oct12[octave-1] = (octave-1)*12
pt_oct12:       db      0, 12, 24, 36, 48, 60, 72, 84
; pt_period[note] : 12-bit PSG tone period, note = (octave-1)*12+semitone,
; 0 = C1 .. 95 = B8, and a 97th entry 96 = C9 that ONLY `N96` reaches (letter notes
; stop at O8 B = 95). BLACK-BOX MEASURED off the VG-8020 (the reference does not equal
; round(clk/16f); 9 of 96 differ by 1 -- docs/audio-slice3-characterization.md);
; entry 96 was measured 2026-09-15 on BOTH references and reads 13 on each.
; Generated by tests/mml_ref.py emit_period_table from its measured REF_PERIODS.
pt_period:
                dw      $0D5D, $0C9C, $0BE7, $0B3C, $0A9B, $0A02, $0973, $08EB
                dw      $086B, $07F2, $0780, $0714, $06AF, $064E, $05F4, $059E
                dw      $054E, $0501, $04BA, $0476, $0436, $03F9, $03C0, $038A
                dw      $0357, $0327, $02FA, $02CF, $02A7, $0281, $025D, $023B
                dw      $021B, $01FD, $01E0, $01C5, $01AC, $0194, $017D, $0168
                dw      $0153, $0140, $012E, $011D, $010D, $00FE, $00F0, $00E3
                dw      $00D6, $00CA, $00BE, $00B4, $00AA, $00A0, $0097, $008F
                dw      $0087, $007F, $0078, $0071, $006B, $0065, $005F, $005A
                dw      $0055, $0050, $004C, $0047, $0043, $0040, $003C, $0039
                dw      $0035, $0032, $0030, $002D, $002A, $0028, $0026, $0024
                dw      $0022, $0020, $001E, $001C, $001B, $0019, $0018, $0016
                dw      $0015, $0014, $0013, $0012, $0011, $0010, $000F, $000E
                dw      $000D
