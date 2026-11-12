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
                ; 🔴 D-PLAYQUEUE (2026-10-31): PLAY APPENDS. This tenant used to
                ; reset each mentioned voice's buffer and PAUSE it while parsing
                ; (D-GCDI5); a PLAY while a voice played threw its queue away -- a
                ; song played bar by bar from DATA kept only the last bar (396
                ; jiffies on the VG-8020, 104 here: scratchpad/playqueue_measure.out).
                ; Now each voice's packets go into its 128-byte RING after what is
                ; queued, nothing is paused (the drain only reads up to QD_PUT,
                ; which is published once a window is written), and a full ring
                ; returns PLAY_MORE: main waits a frame and calls again, because a
                ; page-1 tenant must not wait. A call with AUDIO_STATUS = PLAY_MORE
                ; is such a continuation; any other value starts a new PLAY.
                ei
                ld      a,(AUDIO_STATUS)
                cp      PLAY_MORE
                call    nz,pt_fresh         ; a new PLAY: snapshot each voice's state
                call    pt_parse
                di                          ; the trampoline contract: DI before ret
                ret
; --- pt_fresh: a new PLAY. When every string is empty (or none is named) the PLAY
; queues and counts NOTHING (D-PLAYEMPTY: the reference's MUSICF reads 0 right after
; `PLAY""`); otherwise ALL THREE voices take part -- one not named, or named with "",
; parses nothing and queues only its end marker (the VG-8020: `PLAY "C"` puts an FF on
; voices B and C too, scratchpad/plycnt_run2.out), where the voices sync. Each voice's
; parse state (+13..+19, +22) is snapshotted into VCX_SNAP and VCX_DONE zeroed.
pt_fresh:
                ld      bc,$0001            ; B = voice index 0, C = voice-0 mask bit
pf_lp:
                push    bc
                call    pt_vcb_ix           ; IX = VCB base (preserves B)
                pop     bc
                ld      a,(AUDIO_VMASK)
                and     c
                jr      z,pf_empty          ; not named
                ld      a,(ix+VCX_VCXLEN)
                or      a
                jr      nz,pf_snap
                ld      a,c
                cpl
                ld      hl,AUDIO_VMASK
                and     (hl)
                ld      (hl),a              ; named with "": not a voice that counts
pf_empty:
                ld      (ix+VCX_VCXLEN),0   ; parses nothing: only its end marker
pf_snap:
                xor     a
                ld      (ix+VCX_DONE),a
                ld      (ix+VCX_DONE+1),a
                push    bc
                push    ix
                pop     hl
                ld      de,VCX_ENVPER
                add     hl,de               ; HL = +13
                push    hl
                ld      de,VCX_SNAP-VCX_ENVPER
                add     hl,de
                ex      de,hl               ; DE = the snapshot
                pop     hl
                ld      bc,VCX_ENVSH-VCX_ENVPER+1
                ldir                        ; +13..+19
                ld      a,(ix+VCX_ENVDIRTY)
                ld      (de),a              ; +22, the eighth byte
                pop     bc
                rlc     c
                inc     b
                ld      a,b
                cp      3
                jr      c,pf_lp
                ld      hl,AUDIO_VMASK
                ld      a,(hl)
                or      a
                jr      z,pf_none
                ld      (hl),7              ; every voice takes part
                ret
pf_none:
                pop     hl                  ; nothing to play: no parse, no voice, no count --
                di                          ; leave the tenant (the trampoline contract: DI);
                ret                         ; AUDIO_STATUS stays main's 0
; --- pt_parse: one WINDOW over the voices still in AUDIO_VMASK -------------------
; A finished voice leaves AUDIO_VMASK; a full ring ends the window (PLAY_MORE).
pt_parse:
                ld      bc,$0001            ; B = voice index 0, C = voice-0 mask bit
pt_vloop:
                ld      a,(AUDIO_VMASK)
                and     c                   ; is this voice still to do?
                jr      z,pt_vnext
                push    bc                  ; pt_voice reuses B (source count) + clobbers C
                ld      (PLY_XSP),sp        ; PLAY X (§7.12): SP here = "depth 0"
                call    pt_voice            ; parse voice B into its ring; CF=1 on error/full
                ; back to where PLY_XSP saved SP, after the push bc above: depth 2
                ; z80flow: ld-sp 2
                ld      sp,(PLY_XSP)        ; drop any X levels an early exit left behind
                pop     bc                  ; (ld sp does not touch the flags)
                push    af                  ; the voice's result
                push    bc
                call    pt_publish          ; QD_PUT := the window's; start idle music
                pop     bc
                pop     af
                ret     c                   ; error, or PLAY_MORE -- AUDIO_STATUS says which
                ld      a,c
                cpl
                ld      hl,AUDIO_VMASK
                and     (hl)
                ld      (hl),a              ; this voice is done
pt_vnext:
                rlc     c                   ; next voice's mask bit (1->2->4)
                inc     b
                ld      a,b
                cp      3
                jr      c,pt_vloop
                ld      hl,PLYCNT
                inc     (hl)                ; a PLAY statement queued
                xor     a
                ld      (AUDIO_STATUS),a    ; 0 = ok
                ret
; --- pt_publish: B = voice, C = its bit. QD_PUT := VCX_WPUT; when it queued
; something and the music is idle, START it as the VG-8020's PLAY does -- STRTMS's
; own st_go (basic/biosfnk.asm, page 0: mapped under this tenant): PLYCNT - 1, MUSICF
; := 7. The statement's +1 comes at its end (pt_parse), so a PLAY that started nets 0
; and one queued behind playing music leaves 1 for the sync (scratchpad/plycnt_run.out).
; No tick runs between the two: htimi_guard skips the servicer while this tenant
; holds page 1.
pt_publish:
                call    pt_vcb_ix
                call    pt_qd
                ld      a,(ix+VCX_WPUT)
                ld      (iy+QD_PUT),a
                cp      (iy+QD_GET)
                ret     z                   ; nothing queued
                ld      a,(MUSICF)
                or      a
                ret     nz                  ; playing: this statement waits for the sync
                jp      st_go

; --- pt_init: seed the PLAY defaults into all three VCBs and empty the rings --
; At cold boot, and again after BEEP / a break / an abort (psv_flush zeroes the
; tempo, basic/playsvc.asm).
pt_init:
                ld      ix,VCBA
                ld      b,3
pi_lp:
                ld      (ix+VCX_OCTAVE),PLAY_DEF_OCTAVE
                ld      (ix+VCX_NOTEL),PLAY_DEF_NOTEL
                ld      (ix+VCX_TEMPO),PLAY_DEF_TEMPO
                ld      (ix+VCX_VOLUME),PLAY_DEF_VOLUME
                ld      (ix+VCX_ENVSH),0
                ld      (ix+VCX_ENVPER),255 ; M255, the default (M255C sends nothing on
                ld      (ix+VCX_ENVPER+1),0 ; the VG-8020, scratchpad/playq_run2.out)
                ld      (ix+VCX_ENVDIRTY),0 ; no M pending (BEEP drops one, measured)
                ld      (ix+VCX_FRAMES),0   ; no note running
                ld      (ix+VCX_FRAMES+1),0
                ld      de,VCB_STRIDE
                add     ix,de
                djnz    pi_lp
                xor     a
                ld      (MUSICF),a
                ld      (PLYCNT),a
                ; the three ring descriptors (D-PLAYQUEUE: once, at the cold seed --
                ; a PLAY no longer resets them; BEEP / a break empty them through
                ; psg_silence, basic/sound.asm)
                ld      iy,QUETAB
                ld      hl,VOICAQ
                ld      b,3
pi_q:
                ld      (iy+QD_PUT),a
                ld      (iy+QD_GET),a
                ld      (iy+QD_PUTBAK),a    ; BAKFLG 0, as the VG-8020's reads
                ld      (iy+QD_SIZE),127    ; the VG-8020's value (a mask), measured
                ld      (iy+QD_ADDR),l
                ld      (iy+QD_ADDR+1),h
                ld      de,128
                add     hl,de
                ld      de,QD_STRIDE
                add     iy,de
                djnz    pi_q
                ret

; (pt_commit -- MUSICF ORed in after the whole parse, D-MUSICF -- went in
; D-PLAYQUEUE: pt_publish starts each voice once its window is in the ring, and
; never touches a bit it did not set.)
; --- pt_voice: parse voice B's MML string into its ring buffer --------------
;   in:  B = voice index 0..2 (its VCB has VCXPTR/VCXLEN marshalled by ex_play)
;   out: CF=0 ok / CF=1 error (AUDIO_STATUS = ERR code). Clobbers everything.
; X<var>; pushes a level per nested string, and an early exit may leave
; levels pending (pt_parse drops them with ld sp,(PLY_XSP))
; z80flow: stack-effect var
pt_voice:
                ld      a,b
                ld      (VOICEN),a
                ld      (QUEUEN),a
                call    pt_vcb_ix           ; IX = VCB base (preserves B)
                call    pt_qd               ; IY = ring desc (preserves B)
                call    pt_window           ; state from the snapshot, CNT 0, the room
                ld      l,(ix+VCX_VCXPTR)
                ld      h,(ix+VCX_VCXPTR+1)
                ld      (MCLPTR),hl         ; MML source cursor
                ld      b,(ix+VCX_VCXLEN)   ; B = source bytes remaining
pt_ch_loop:
                call    px_getc             ; fetch + advance the source cursor (upcased)
                jp      c,px_eos            ; end of THIS string: pop an X level, or end the voice
                cp      ' '
                jr      z,pt_ch_loop        ; skip spaces
                cp      'A'
                jr      c,pt_nn
                cp      'G'+1
                jr      c,pt_note_letter    ; A..G -> a note
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
                cp      'X'
                jp      z,pt_cmd_x          ; X<var>; -- substring execution (§7.12)
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
                jp      px_err              ; AUDIO_STATUS := 5, CF=1: abort the voice

; --- pt_num8: the `=name;` / digit operand of N O L T V S -> A = L = 0..255; -
; no digits or > 255 -> ERR 5. The error path drops this call's own return
; address first, so pt_illegal's `ret` leaves at the same depth as the
; inline `jp nc,pt_illegal / ... / jp nz,pt_illegal` it replaces (D-REREAD sub
; batch 2). Flags on return: Z (H = 0) -- every caller re-tests A itself.
pt_num8:
                call    pt_numeq
                jr      nc,pn8_bad
                ld      a,h
                or      a
                ld      a,l
                ret     z
pn8_bad:
                pop     af                  ; drop the command's return address
                jr      pt_illegal

pt_voice_end:
                ld      a,1
                call    pt_pkt              ; END: 1 B, where the voices sync
                ret     c
                ld      a,PK_END
                jp      pt_put              ; CF=0

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
                adc     a,h
                sub     l
                ld      h,a
                ld      c,(hl)              ; C = semitone 0..11
                call    pqs_peek            ; accidental? (only if a char remains)
                jr      c,pnl_base
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
                call    px_getc             ; consume the accidental (B > 0: peeked)
pnl_base:
                ld      a,(ix+VCX_OCTAVE)
                dec     a
                ld      hl,pt_oct12
                add     a,l
                ld      l,a
                adc     a,h
                sub     l
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
                adc     a,h
                sub     l
                ld      h,a
                ld      a,(hl)
                inc     hl
                ld      h,(hl)
                ld      l,a                 ; HL = tone period
                ld      (PLY_LASTDUR),hl    ; kept across pt_length (it clobbers DE)
                call    pt_length           ; HL = frame duration
                ret     c
                ex      de,hl               ; DE = frames
                ld      hl,(PLY_LASTDUR)    ; HL = period
                ld      a,(ix+VCX_ENVDIRTY)
                rlca
                rlca
                rlca                        ; $40 (an M since the last note) -> +2 B
                add     a,5
                call    pt_pkt
                ret     c
                ; THE VG-8020's NOTE (D-BIOSRUNG / STRTMS, scratchpad/playq_run*.out):
                ; [n << 5 | frames 12..8] [frames 7..0] [vol] ([M hi] [M lo]) [tone hi]
                ; [tone lo], n = the bytes after the two duration bytes: 3, or 5 with M
                ld      a,(ix+VCX_ENVDIRTY)
                ld      c,a                 ; C = $40 after an M that changed the period
                add     a,$60               ; n = 3 ($60), or 5 ($A0) with the M bytes
                or      d                   ; | frames 12..8
                call    pt_put
                ld      a,e
                call    pt_put              ; frames 7..0
                call    pt_note_amp         ; A = $90 | shape, or $80 | volume
                or      c                   ; | $40: the M bytes follow
                call    pt_put
                bit     6,c
                jr      z,pep_tone
                ld      a,(ix+VCX_ENVPER+1)
                call    pt_put              ; M, big-endian
                ld      a,(ix+VCX_ENVPER)
                call    pt_put
pep_tone:
                ld      a,h
                call    pt_put              ; tone period, big-endian
                ld      a,l
                call    pt_put
pep_done:
                ld      (ix+VCX_ENVDIRTY),0 ; the envelope is carried
                jp      pt_ch_loop

; --- pt_note_amp: A = the note packet's vol byte, before M's $40 -------------
; (the PSG gets it whole: R13 in envelope mode, its low 5 bits as the amplitude)
pt_note_amp:
                ld      a,(ix+VCX_ENVSH)    ; $80 | shape in envelope mode (bits 4-6 0)
                or      $10
                ret     m                   ; envelope: $90 | the shape (S0 $90, S8 $98)
                ld      a,(ix+VCX_VOLUME)   ; 0..15 (V refuses more)
                or      $80                 ; $80 | the volume: V10 $8A, V0 $80 (a note)
                ret

; --- pt_cmd_rest: queue a REST packet (3 B: tag, duration) for the parsed length
; 🎵 D-PLAYBARER (2026-11-05): a BARE `R` is a QUARTER whatever `L` says, and `R.`
; is ERR 5 -- both references (scratchpad/playrate_dots2.out, playrate_rest_3way.out,
; playrate_rdot.out: 8 bare R under L8 = 8 x R4 on the VG-8020 and the CF-3300; an
; explicit R4. / R64. takes its dots). N0 is a rest of 5 ticks whatever T / L say
; (pt_rest_n0; the VG-8020's queue, scratchpad/playq_run4.out / playq_run6.out).
pt_cmd_rest:
                call    pt_numeq            ; HL = an explicit length, CF=1
                jr      c,pcr_len
                call    pqs_peek
                jr      c,pcr_q             ; end of the string: a quarter
                cp      '.'
                jp      z,pt_illegal        ; `R.`: ERR 5 on both references
pcr_q:
                ld      hl,4
                scf
pcr_len:
                call    pt_length_k         ; HL = frames (the explicit length checked)
                jr      pcr_pkt
pt_rest_n0:
                ld      hl,5                ; N0: 5 ticks (CF clear from the `or a`)
pcr_pkt:
                ret     c
                ld      a,3
                call    pt_pkt              ; REST: 3 B
                ret     c
                ld      a,h
                or      PK_REST             ; [$20 | frames 12..8] [frames 7..0] [$80]
                call    pt_put
                ld      a,l
                call    pt_put
                ld      a,$80               ; volume 0, no tone
                call    pt_put
                jp      pt_ch_loop

; --- pt_cmd_n: N n -> note by absolute number (0 = rest) --------------------
pt_cmd_n:
                call    pt_num8             ; A = L = the 0..255 operand, or ERR 5
                cp      97
                jp      nc,pt_illegal       ; > 96
                or      a
                jr      z,pt_rest_n0        ; N0 = a 5-tick rest
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
                call    pt_num8             ; A = L = the 0..255 operand, or ERR 5
                or      a
                jp      z,pt_illegal
                cp      9
                jp      nc,pt_illegal
                ld      (ix+VCX_OCTAVE),a
                jp      pt_ch_loop
pt_cmd_length:
                call    pt_num8             ; A = L = the 0..255 operand, or ERR 5
                or      a
                jp      z,pt_illegal
                cp      65
                jp      nc,pt_illegal
                ld      (ix+VCX_NOTEL),a
                jp      pt_ch_loop
pt_cmd_tempo:
                call    pt_num8             ; A = L = the 0..255 operand, or ERR 5
                cp      32
                jp      c,pt_illegal
                ld      (ix+VCX_TEMPO),a
                jp      pt_ch_loop
pt_cmd_volume:
                call    pt_num8             ; A = L = the 0..255 operand, or ERR 5
                cp      16
                jp      nc,pt_illegal
                ld      (ix+VCX_VOLUME),a
                res     7,(ix+VCX_ENVSH)    ; V disables envelope mode
                jp      pt_ch_loop
pt_cmd_env_shape:
                call    pt_num8             ; A = L = the 0..255 operand, or ERR 5
                cp      16
                jp      nc,pt_illegal
                or      $80                 ; set envelope-mode bit
                ld      (ix+VCX_ENVSH),a
                jp      pt_ch_loop          ; S queues nothing: every envelope note
                                            ; carries its shape (the vol byte)
pt_cmd_env_per:
                call    pt_numeq    
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
                ld      a,(ix+VCX_ENVPER)
                cp      l
                jr      nz,pcm_new
                ld      a,(ix+VCX_ENVPER+1)
                cp      h
                jp      z,pt_ch_loop        ; the same period: nothing sent (the VG-8020,
                                            ; scratchpad/playq_run5.out: M is sent when
                                            ; its VALUE changes, M255 at the default too)
pcm_new:
                ld      (ix+VCX_ENVPER),l
                ld      (ix+VCX_ENVPER+1),h
                ld      a,$40               ; M: the next note carries the period

; --- pt_emit_env: S / M queue nothing of their own (D-PLAYQUEUE: measured, an S
; costs the reference's queue 0 B and an M 2 B, on the NEXT note). A = the
; dirty bits to add; the next note carries them (pt_emit_pitch).
pt_emit_env:
                or      (ix+VCX_ENVDIRTY)
                ld      (ix+VCX_ENVDIRTY),a
                jp      pt_ch_loop

; --- pt_length: parse optional length digits + dots -> HL = frame count ------
;   uses IX (VCX_TEMPO/VCX_NOTEL), MCLPTR/B. CF=1 (+ AUDIO_STATUS) on a bad length.
; (pt_length_eq -- `call pt_numeq / jr pt_length_k` -- went with N0's L length: its last
; caller; D-BIOSRUNG 2026-11-12. R takes `=name;` through pt_cmd_rest's own pt_numeq.)
pt_length:
                call    pt_number
pt_length_k:
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
                call    pqs_peek
                jr      c,pl_calc
                cp      '.'
                jr      nz,pl_calc
                call    px_getc             ; consume the dot (B > 0: peeked)
                inc     c
                jr      pl_dots
pl_calc:
                ld      d,(ix+VCX_TEMPO)    ; D = tempo, E = length, C = dots
                jr      pt_getframes
pl_bad:
                jp      pt_illegal          ; AUDIO_STATUS := 5, CF=1, ret (the same
                                            ; four instructions, one copy)

; --- pt_getframes: D=tempo, E=length, C=dots -> HL = frames -----------------
;   frames = 12000 / tl  (floor; tl = tempo*length), VG-8020-pinned
;   (docs/audio-slice3-characterization.md §1). Dots: the first dot adds
;   ceil(base/2), each subsequent dot floor of the running addend -- realised by a
;   single `inc de` before the halving loop (the +1 survives only the first srl,
;   giving ceil; later iterations halve the already-floored addend). tests/mml_ref.py
;   note_frames is the oracle. Preserves B (source count); clobbers A, C, DE, HL.
pt_getframes:
                push    bc                  ; save B (source count); C = dots
                ; 🐌 D-PLAYPHASE (2026-11-05): tl = tempo*length by shift-and-add, 8
                ; steps. It was `tempo` repeated adds -- 120 at T120, ~3000 T a note,
                ; a third of a PLAY window call, which with them cost about a whole
                ; frame: the blocked PLAY then noticed room in the frame it appeared
                ; or the next by sub-frame phase (basic/play.asm, pld_go).
                ld      a,d                 ; A = tempo
                ld      hl,0
                ld      d,0                 ; DE = length
                ld      b,8
pgf_mul:
                add     hl,hl
                rla                         ; tempo's next bit, high first
                jr      nc,pgf_mul0
                add     hl,de
pgf_mul0:
                djnz    pgf_mul
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
                ; 🎵 D-PLAYRATE (2026-11-05): a MINIMUM OF 5 FRAMES, after the dots --
                ; every note and every rest, on the VG-8020 (50 Hz) and the CF-3300
                ; (60 Hz) alike: B - A = 5n + 1 for n short notes, T32..T255, L8..L64,
                ; dotted, N, V0 (scratchpad/playrate_grid_3way.out, playrate_dots_3way.out).
                ; Not a fill rate: short notes behind long ones are as slow
                ; (playrate_measure_3way.out row 10). It was a minimum of 1.
                ld      a,h
                or      a
                ret     nz
                ld      a,l
                cp      5
                ret     nc
                ld      l,5
                or      a                   ; CF = 0: callers read CF as an error (`ret c`)
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
                call    pqs_peek
                jr      c,pn_end
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
                call    px_getc             ; advance the source cursor (B > 0: peeked)
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

; --- pt_numeq (D-PLAYEQ): a command's number, or `=name;` -----------------------
; `PLAY "T=T;V=V;"` was ERR 5 here in every form. Measured on the VG-8020
; (scratchpad/playeq_measure.out): T V N O L S M R take `=name;`, a note does not
; (`C=I%;` is 5, and it still is: notes call pt_number); the value is cut the way
; CINT cuts (O=8.6 is O8) and past an int16 is 6 (M=65535); an undefined name is
; 0, a string 13, a missing `;` 5, spaces are skipped, a literal or `(` is 5.
; The name is looked up the way `X` looks up its string -- the tenant walks the
; scalar chain itself (Joost 2026-09-24) -- matching name AND type, since A% and
; A! are separate variables. An ARRAY ELEMENT (`V=I%(1);`, which the VG-8020
; takes) is 5 here: its subscript needs the expression evaluator
; (D-PLAYEQARR, TODO.md).
;   in/out as pt_number: HL = value, CF=1. An error never returns here: it
;   drops this call's return address and leaves the way a command's own error
;   exit does (pt_illegal / px_err), so it lands in pt_vparse.
pt_numeq:
                call    pqs_peek
                jp      c,pt_number
                cp      '='
                jp      nz,pt_number
                call    px_getc             ; the `=`
                call    px_nosp
                jp      c,pqe_bad
                call    px_letter
                jp      nc,pqe_bad          ; a name starts with a letter
                ld      h,a                 ; H = name0
                ld      l,0                 ; L = name1 (none yet)
pqe_name:
                call    px_nosp
                jp      c,pqe_bad           ; ended before `;`
                cp      ';'
                jr      z,pqe_dscal         ; no suffix: DEFTBL decides the type
                cp      '('
                jr      z,pqe_darr          ; D-PLAYEQARR: an array, no suffix
                ld      c,2
                cp      '%'
                jr      z,pqe_suf
                ld      c,4
                cp      '!'
                jr      z,pqe_suf
                ld      c,8
                cp      '#'
                jr      z,pqe_suf
                cp      '$'
                jp      z,pqe_tm            ; a string: Type mismatch
                call    px_letter
                jr      c,pqe_id
                cp      '0'
                jp      c,pqe_bad
                cp      '9'+1
                jp      nc,pqe_bad          ; an operator, ...: 5
pqe_id:
                inc     l
                dec     l
                jr      nz,pqe_name         ; 3rd+ characters are ignored
                ld      l,a                 ; name1
                jr      pqe_name
pqe_suf:
                call    px_nosp             ; `;` or `(` must follow the suffix
                jp      c,pqe_bad           ; (spaces between are fine: `V=I% ;`)
                cp      ';'
                jr      z,pqe_scal
                cp      '('
                jr      z,pqe_arr
                jp      pqe_bad
pqe_darr:
                call    pqe_dtype
pqe_arr:
                ; --- D-PLAYEQARR: `=A(i,j);` ----------------------------------
                push    de                  ; the queue write pointer
                call    pqe_elem            ; HL = the element's value (0: never
                                            ; dimensioned), C = the type
                call    px_nosp
                jp      c,pqe_bad
                cp      ';'
                jp      nz,pqe_bad          ; `=A(1)` not followed by `;`
                jr      pqe_conv
pqe_dscal:
                call    pqe_dtype
pqe_scal:
                push    de
                call    pqe_find            ; HL = the scalar's value, or 0
pqe_conv:
                call    pqe_cut             ; HL = the int16
                pop     de
                scf
                ret

; pqe_dtype: H = name0 -> C = DEFTBL's type (2 / 4 / 8); a string is 13.
pqe_dtype:
                call    px_dtlook
                jp      z,pqe_tm
                ld      c,a
                ret
; px_dtlook: H = name0 -> A = DEFTBL[name0-'A'], Z iff a string type. Keeps HL.
; Shared by pqe_dtype and pt_cmd_x's px_deftype (D-REREAD sub batch 2).
px_dtlook:
                ld      a,h
                sub     'A'
                push    hl
                ld      hl,DEFTBL
                add     a,l
                ld      l,a
                jr      nc,px_dt1
                inc     h
px_dt1:
                ld      a,(hl)
                pop     hl
                cp      DEFTBL_STR
                ret

; pqe_find: HL = key (H name0, L name1), C = type -> HL = the scalar's value
; address, or 0 when there is no such variable. Preserves BC, DE.
pqe_find:
                push    de
                push    bc
                ex      de,hl               ; DE = key
                ld      hl,(PRGEND)
                inc     hl
                inc     hl                  ; the scalar region's base
pqf_lp:
                push    hl
                ld      bc,(ARYTAB)
                or      a
                sbc     hl,bc
                pop     hl
                jr      nc,pqf_none         ; reached ARYTAB: not defined
                ld      a,(hl)
                cp      d
                jr      nz,pqf_skip
                inc     hl
                ld      a,(hl)
                dec     hl
                cp      e
                jr      nz,pqf_skip
                inc     hl
                inc     hl
                ld      a,(hl)              ; this entry's type
                dec     hl
                dec     hl
                pop     bc
                push    bc
                cp      c
                jr      nz,pqf_skip
                inc     hl
                inc     hl
                inc     hl                  ; HL -> the value
                jr      pqf_ret
pqf_skip:
                inc     hl
                inc     hl
                ld      a,(hl)              ; this entry's type -> its stride
                inc     hl
                cp      1
                jr      nz,pqf_st
                ld      a,3                 ; a string's value is a 3-byte descriptor
pqf_st:
                add     a,l
                ld      l,a
                jr      nc,pqf_lp
                inc     h
                jr      pqf_lp
pqf_none:
                ld      hl,0
pqf_ret:
                pop     bc
                pop     de
                ret

; pqe_cut: HL = a value's address (0: undefined, the value 0), C = its type ->
; HL = the int16, cut toward 0 as CINT cuts; past an int16 is 6 (pqe_abort).
; Preserves B. Clobbers C, DE.
pqe_cut:
                ld      a,h
                or      l
                ret     z                   ; undefined: 0
                ld      a,c
                cp      2
                jr      nz,pqc_flt
                ld      a,(hl)              ; an integer: as it is
                inc     hl
                ld      h,(hl)
                ld      l,a
                ret
pqc_flt:
                ; BCD (docs/concepts/numbers.md): byte 0 = sign | exponent+64,
                ; then two digits a byte, value .d1d2... x 10^(exponent).
                ld      a,(hl)
                and     $7F
                sub     65                  ; integer digits - 1; carry: |x| < 1
                jr      c,pqc_zero          ; (byte 0 = 0, the value 0, too)
                cp      5
                jp      nc,pqe_ovf          ; six or more digits
                inc     a
                ld      c,a                 ; C = the digits to take
                push    hl                  ; the value (its sign is in byte 0)
                inc     hl
                ld      de,0
pqc_dig:
                ld      a,(hl)
                rrca
                rrca
                rrca
                rrca
                and     $0F                 ; the high digit
                call    pqe_acc
                dec     c
                jr      z,pqc_mag
                ld      a,(hl)
                and     $0F                 ; the low digit
                call    pqe_acc
                inc     hl
                dec     c
                jr      nz,pqc_dig
pqc_mag:
                pop     hl
                ld      a,d
                cp      $80
                jr      c,pqc_sign          ; < 32768
                jp      nz,pqe_ovf
                ld      a,e
                or      a
                jp      nz,pqe_ovf          ; > 32768
                bit     7,(hl)
                jp      z,pqe_ovf           ; +32768
pqc_sign:
                ld      a,(hl)              ; byte 0: the sign
                ex      de,hl               ; HL = the magnitude
                rlca
                ret     nc
                xor     a
                sub     l
                ld      l,a
                sbc     a,a
                sub     h
                ld      h,a                 ; HL = -HL
                ret
pqc_zero:
                ld      hl,0
                ret

; pqe_acc: DE = DE*10 + A (a digit). Past 32769 -- DE already 3277 or more --
; is 6 (pqe_abort). Preserves HL, BC.
pqe_acc:
                push    hl
                push    af
                ld      a,d
                cp      $0C
                jr      c,pa_ok             ; < 3072
                jp      nz,pqe_ovf          ; >= 3328
                ld      a,e
                cp      $CD
                jp      nc,pqe_ovf          ; >= 3277
pa_ok:
                ld      h,d
                ld      l,e
                add     hl,hl
                push    hl
                add     hl,hl
                add     hl,hl
                pop     de
                add     hl,de               ; HL = 10 * DE
                pop     af
                ld      e,a
                ld      d,0
                add     hl,de
                ex      de,hl
                pop     hl
                ret

; pqe_elem (D-PLAYEQARR): HL = key, C = type, the `(` read -> HL = the element's
; value address, 0 for an array never dimensioned; C = the type; the `)` read.
; Measured (scratchpad/playarr_measure.out): each subscript a number (its
; fraction cut) or a plain variable; an expression is 2; out of range or the
; wrong count is 9; a never-dimensioned array reads 0 within the automatic bound
; of 10. Column-major (sub/arrays.asm header): off += i_k * M; M *= b_k + 1.
; Its locals live in an IX FRAME on the stack -- no RAM cell (D-WSZERO) -- and
; IX, DE and B (PLAY's bytes left, which only px_getc moves) come back.
;   frame: +0 type  +1 dimensions still to take ($FF: never dimensioned)
;          +2/3 off  +4/5 M  +6/7 the next bound (0: never dimensioned)
pqe_elem:
                push    de
                push    ix
                ld      ix,-8
                add     ix,sp
                ld      sp,ix               ; 8 bytes of locals
                ld      (ix+0),c
                ex      de,hl               ; DE = key
                ld      hl,(ARYTAB)
pqa_find:
                ld      a,(hl)
                or      a
                jr      z,pqa_none          ; the terminator: never dimensioned
                cp      d
                jr      nz,pqa_skip
                inc     hl
                ld      a,(hl)
                inc     hl
                cp      e
                jr      nz,pqa_skip2
                ld      a,(hl)              ; this array's type
                dec     hl
                dec     hl
                cp      (ix+0)
                jr      z,pqa_have
pqa_skip:
                inc     hl
                inc     hl
pqa_skip2:
                inc     hl
                inc     hl                  ; HL -> the stride (+4)
                push    de
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = the stride
                dec     hl
                dec     hl
                dec     hl
                dec     hl
                dec     hl                  ; HL -> the descriptor again
                add     hl,de
                pop     de
                jr      pqa_find
pqa_none:
                ld      (ix+1),$FF
                ld      hl,0
                jr      pqa_set
pqa_have:
                inc     hl
                inc     hl
                inc     hl
                ld      a,(hl)              ; ndim
                ld      (ix+1),a
                inc     hl
                inc     hl
                inc     hl                  ; HL -> bound0
pqa_set:
                ld      (ix+6),l
                ld      (ix+7),h
                xor     a
                ld      (ix+2),a
                ld      (ix+3),a            ; off = 0
                ld      (ix+5),a
                inc     a
                ld      (ix+4),a            ; M = 1
pqa_sub:
                call    pqe_subscript       ; DE = i, A = `,` or `)`
                push    af
                ld      a,(ix+1)
                or      a
                jp      z,pqe_r9            ; more subscripts than dimensions
                dec     a
                ld      (ix+1),a
                ld      l,(ix+6)
                ld      h,(ix+7)
                ld      a,h
                or      l
                jr      nz,pqa_b1
                ld      hl,10               ; never dimensioned: the bound is 10
                jr      pqa_b2
pqa_b1:
                ld      a,(hl)
                inc     hl
                push    af
                ld      a,(hl)
                inc     hl
                ld      (ix+6),l
                ld      (ix+7),h            ; the next bound
                ld      h,a
                pop     af
                ld      l,a                 ; HL = this dimension's bound
pqa_b2:
                push    hl
                or      a
                sbc     hl,de               ; bound - i
                pop     hl
                jp      c,pqe_r9            ; i > bound: Subscript out of range
                inc     hl                  ; HL = bound + 1
                push    hl
                ld      l,(ix+4)
                ld      h,(ix+5)            ; HL = M, DE = i
                call    pqe_mul             ; HL = M * i
                ld      e,(ix+2)
                ld      d,(ix+3)
                add     hl,de
                ld      (ix+2),l
                ld      (ix+3),h            ; off += M * i
                pop     de                  ; DE = bound + 1
                ld      l,(ix+4)
                ld      h,(ix+5)
                call    pqe_mul
                ld      (ix+4),l
                ld      (ix+5),h            ; M *= bound + 1
                pop     af                  ; A = the terminator
                cp      ','
                jr      z,pqa_sub
                ld      a,(ix+6)
                or      (ix+7)
                jr      z,pqa_out           ; never dimensioned: HL = 0 below
                ld      a,(ix+1)
                or      a
                jp      nz,pqe_r9           ; fewer subscripts than dimensions
                ld      l,(ix+0)
                ld      h,0                 ; elsize = the type: 2, 4 or 8
                ld      e,(ix+2)
                ld      d,(ix+3)
                call    pqe_mul             ; HL = elsize * off
                ld      e,(ix+6)
                ld      d,(ix+7)            ; the bound pointer has walked onto
                add     hl,de               ; the element data
pqa_out:
                ld      a,(ix+6)
                or      (ix+7)
                jr      nz,pqa_ret
                ld      hl,0
pqa_ret:
                ld      c,(ix+0)
                ex      de,hl
                ld      hl,8
                add     hl,sp
                ld      sp,hl               ; drop the locals
                ex      de,hl
                pop     ix
                pop     de
                ret

; pqe_subscript: -> DE = the subscript, A = the char after it (`,` or `)`; else
; Syntax error 2). A number (its fraction skipped) or a plain variable.
; Preserves B's meaning (only px_getc moves it), IX, and the caller's C? no: C is
; reloaded by pqe_elem from its frame.
pqe_subscript:
                call    px_nosp
                jp      c,pqe_bad
                cp      '0'
                jr      c,pqs_notdig
                cp      '9'+1
                jr      nc,pqs_notdig
                sub     '0'
                ld      e,a
                ld      d,0
pqs_dig:
                call    pqs_peek
                jr      c,pqs_end
                cp      '0'
                jr      c,pqs_dot
                cp      '9'+1
                jr      nc,pqs_dot
                call    px_getc
                sub     '0'
                call    pqe_acc
                jr      pqs_dig
pqs_dot:
                cp      '.'
                jr      nz,pqs_end
                call    px_getc             ; the fraction is cut
pqs_frac:
                call    pqs_peek
                jr      c,pqs_end
                cp      '0'
                jr      c,pqs_end
                cp      '9'+1
                jr      nc,pqs_end
                call    px_getc
                jr      pqs_frac
pqs_end:
                call    px_nosp
                jp      c,pqe_bad
                jr      pqs_term
pqs_notdig:
                call    px_letter
                jp      nc,pqs_syn          ; `-1`, `(`, `)` ...: Syntax error
                ld      h,a
                ld      l,0
pqs_nm:
                call    px_nosp
                jp      c,pqe_bad
                call    px_letter
                jr      c,pqs_id
                cp      '0'
                jr      c,pqs_nmend
                cp      '9'+1
                jr      nc,pqs_nmend
pqs_id:
                inc     l
                dec     l
                jr      nz,pqs_nm
                ld      l,a
                jr      pqs_nm
pqs_nmend:
                ld      c,2
                cp      '%'
                jr      z,pqs_suf
                ld      c,4
                cp      '!'
                jr      z,pqs_suf
                ld      c,8
                cp      '#'
                jr      z,pqs_suf
                cp      '$'
                jp      z,pqe_tm
                push    af
                call    pqe_dtype           ; C = DEFTBL's type
                pop     af
                jr      pqs_look
pqs_suf:
                call    px_nosp
                jp      c,pqe_bad
pqs_look:
                push    af                  ; the char after the name
                call    pqe_find
                call    pqe_cut             ; HL = the value
                pop     af
                ex      de,hl               ; DE = the subscript
                bit     7,d
                jp      nz,pqe_r9           ; a negative variable: out of range
pqs_term:
                cp      ','
                ret     z
                cp      ')'
                ret     z
pqs_syn:
                ld      a,2                 ; an operator or anything else: Syntax error
                jr      pqe_abort
; pqs_peek: A = the next source char without taking it; CF=1 at the end.
pqs_peek:
                ld      a,b
                or      a
                scf
                ret     z
                push    hl
                ld      hl,(MCLPTR)
                ld      a,(hl)
                pop     hl
                or      a                   ; CF=0
                ret

; pqe_mul: HL = HL * DE (16 bits: the arrays fit in 64 KB). Preserves BC.
pqe_mul:
                push    bc
                ld      b,h
                ld      c,l                 ; BC = multiplicand
                ld      hl,0
                ld      a,16
pqm_lp:
                add     hl,hl
                ex      de,hl
                add     hl,hl
                ex      de,hl
                jr      nc,pqm_no
                add     hl,bc
pqm_no:
                dec     a
                jr      nz,pqm_lp
                pop     bc
                ret

; --- the error exits: back to pt_voice's caller from ANY depth -------------------
; SP := PLY_XSP-2, pt_voice's own return, the frame `X`'s levels unwind to; then
; px_err stores the code and returns CF=1, the way a command's error exit does.
pqe_r9:
                ld      a,9                 ; Subscript out of range
                jr      pqe_abort
pqe_ovf:
                ld      a,6                 ; Overflow
                jr      pqe_abort
pqe_tm:
                ld      a,13                ; Type mismatch
                jr      pqe_abort
pqe_bad:
                ld      a,5                 ; Illegal function call
pqe_abort:
                ld      hl,(PLY_XSP)
                dec     hl
                dec     hl
                ; back to pt_voice's caller from ANY depth: for every routine nested
                ; inside pt_voice this never returns to its own caller
                ; z80flow: abort
                ld      sp,hl
                jp      px_err

; --- PLAY X<var>; -- substring execution (docs/spec-basic-audio-play.md §7.12) --
; 🏗️ Joost, 2026-09-24: *"Tenant walks the chain"*. The tenant resolves the name
; ITSELF by walking the scalar chain in RAM ([name0][name1][type][value] from
; (PRGEND)+2 up to (ARYTAB) -- the layout sub/arrays.asm's scv_find walks), so
; nothing bounces back to main and the parse stays ONE atomic CALSLT.
; MEASURED BEHAVIOUR it reproduces (§7.1, scratchpad/playx_probe.py, VG-8020):
;   * a CALL, not a jump: the outer string resumes after `;`; no scope (state set
;     inside persists); it NESTS;
;   * the `;` is mandatory -> ERR 5 without it; an UNDEFINED string is EMPTY (no
;     error, the outer string continues); a NUMERIC name -> ERR 13;
;   * the return points live on the STACK and overflow is ERR 7 (§7.8,
;     scratchpad/playxrec_selfrec_probe.py).
; KEY RULES = var_name_key's (basic/vars.asm): name0 = first letter, name1 =
; second letter (upcased) or digit, 0 if none; 3rd+ chars ignored; spaces inside
; the name skipped. No suffix -> DEFTBL's default for name0 (3 = string).
; 🔴 A SAVED LEVEL SITS *BENEATH* THE RETURN ADDRESS, because every command's
; error exit is a bare `ret` that must still land in pt_vparse -- which then
; restores SP from PLY_XSP and drops whatever levels were pending.
; ⚠️ It skips fn_shadow_find (DEF FN formals): PLAY is a statement and cannot
; run while an FN expression is being evaluated.
; ⚠️ scv_find's walk and this one must agree on the chain layout.
pt_cmd_x:
                call    px_nosp             ; A = first non-space char (upcased)
                jp      c,pt_illegal        ; string ended: no name -> ERR 5
                call    px_letter
                jp      nc,pt_illegal       ; a name starts with a letter
                ld      h,a                 ; H = name0
                ld      l,0                 ; L = name1 (none yet)
px_name:
                call    px_nosp
                jp      c,pt_illegal        ; ended before `;` -> ERR 5
                cp      ';'
                jr      z,px_deftype        ; no suffix: DEFTBL decides the type
                cp      '$'
                jr      z,px_dollar
                cp      '%'
                jr      z,px_numeric
                cp      '!'
                jr      z,px_numeric
                cp      '#'
                jr      z,px_numeric
                call    px_letter           ; a letter ...
                jr      c,px_ident
                cp      '0'                 ; ... or a digit continues the name
                jp      c,pt_illegal
                cp      '9'+1
                jp      nc,pt_illegal
px_ident:
                inc     l
                dec     l
                jr      nz,px_name          ; 3rd+ characters are ignored
                ld      l,a                 ; name1
                jr      px_name
px_deftype:
                call    px_dtlook
                jr      z,px_walk_go
px_numeric:
                ld      a,13                ; a numeric name -> Type mismatch
                jr      px_err
px_dollar:
                call    px_getc             ; the `;` must follow the suffix
                jp      c,pt_illegal
                cp      ';'
                jp      nz,pt_illegal
px_walk_go:
                ; --- the chain walk: HL = key -> HL = descriptor, or "undefined"
                push    de                  ; DE is the queue write pointer
                push    bc                  ; B = bytes left in THIS string
                ld      b,h
                ld      c,l                 ; BC = key (scv_find's register form)
                ld      hl,(PRGEND)
                inc     hl
                inc     hl                  ; scalar-region base
                ld      de,(ARYTAB)         ; scalar-region end
px_walk:
                or      a
                sbc     hl,de
                add     hl,de
                jr      z,px_undef          ; reached ARYTAB: not defined
                ld      a,(hl)
                cp      b
                jr      nz,px_skip
                inc     hl
                ld      a,(hl)
                dec     hl
                cp      c
                jr      nz,px_skip
                inc     hl
                inc     hl
                ld      a,(hl)              ; type
                dec     hl
                dec     hl
                dec     a                   ; type 1 = string
                jr      z,px_found
px_skip:
                inc     hl
                inc     hl
                ld      a,(hl)              ; this entry's type -> its stride
                inc     hl
                cp      1
                jr      nz,px_st
                ld      a,3                 ; a string's value is a 3-byte descriptor
px_st:
                add     a,l
                ld      l,a
                jr      nc,px_walk
                inc     h
                jr      px_walk
px_undef:
                pop     bc
                pop     de
                jp      pt_ch_loop          ; undefined -> EMPTY, no error, carry on
px_found:
                ld      de,3
                add     hl,de               ; HL -> [len][ptr]
                ld      c,(hl)              ; C = length
                inc     hl
                ld      a,(hl)
                inc     hl
                ld      h,(hl)
                ld      l,a                 ; HL = body
                ; stack headroom: the levels live on the machine stack, whose
                ; floor is the pool's CTLLIM -- under 256 B left is ERR 7, the
                ; reference's answer to unbounded nesting (§7.8)
                push    hl                  ; (body)
                ld      hl,0
                add     hl,sp
                ld      de,(CTLLIM)
                or      a
                sbc     hl,de               ; HL = SP - floor
                jr      c,px_oom_body       ; already below the floor
                ld      a,h
                or      a                   ; Z = under 256 B of headroom
                pop     hl                  ; body back (pop keeps the flags)
                jr      nz,px_room
                jr      px_oom
px_oom_body:
                pop     hl
px_oom:
                pop     bc
                pop     de
                ld      a,7                 ; Out of memory
px_err:
                ld      (AUDIO_STATUS),a
                scf
                ret
px_room:
                ; enough stack: save the OUTER cursor beneath the return address
                ex      de,hl               ; DE = body
                ld      a,c                 ; A = body length
                pop     bc                  ; B = bytes left in the outer string
                ld      hl,(MCLPTR)         ; outer cursor
                ld      (MCLPTR),de         ; parse the body next
                pop     de                  ; DE = the queue write pointer again
                ex      (sp),hl             ; stack top = outer cursor, HL = return
                push    bc                  ; outer bytes-left
                push    hl                  ; return address back on top
                ld      b,a                 ; B = the body's length
                jp      pt_ch_loop
; px_eos: THIS string is exhausted. Depth 0 (SP one return address below
; PLY_XSP) ends the voice; otherwise pop one level and resume the outer string.
px_eos:
                ld      hl,(PLY_XSP)
                dec     hl
                dec     hl                  ; SP at depth 0 (just the return address)
                or      a
                sbc     hl,sp
                jp      z,pt_voice_end
                pop     hl                  ; return address
                pop     bc                  ; B = the outer string's bytes left
                ex      (sp),hl             ; HL = outer cursor, return address on top
                ld      (MCLPTR),hl
                jp      pt_ch_loop
; px_getc: next source char, upcased. CF=1 when the string is exhausted.
px_getc:
                ld      a,b
                or      a
                scf
                ret     z
                push    hl
                ld      hl,(MCLPTR)
                ld      a,(hl)
                inc     hl
                ld      (MCLPTR),hl
                pop     hl
                dec     b
                call    pt_upcase
                or      a                   ; CF=0
                ret
; px_nosp: px_getc, skipping spaces.
px_nosp:
                call    px_getc
                ret     c
                cp      ' '
                jr      z,px_nosp
                ret
; px_letter: CF=1 iff A is 'A'..'Z' (A preserved).
px_letter:
                cp      'A'
                ccf
                ret     nc
                cp      'Z'+1
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

; --- pt_qd: B = voice -> IY = its QUETAB ring descriptor (preserves B) ------
pt_qd:
                ld      iy,QUETAB
                ld      a,b
                or      a
                ret     z
                ld      de,QD_STRIDE
                add     iy,de
                dec     a
                ret     z
                add     iy,de
                ret

; --- pt_window: IX = VCB, IY = ring. Restore the parse state from the snapshot
; (a no-op on a voice's first window), CNT := 0, WPUT := QD_PUT, ROOM := the
; ring's free bytes (one is always left empty: put = get means EMPTY).
pt_window:
                push    bc
                push    ix
                pop     hl
                ld      de,VCX_SNAP
                add     hl,de               ; HL = the snapshot
                push    ix
                pop     de
                push    hl
                ld      hl,VCX_ENVPER
                add     hl,de
                ex      de,hl               ; DE = +13
                pop     hl
                ld      bc,VCX_ENVSH-VCX_ENVPER+1
                ldir
                ld      a,(hl)
                ld      (ix+VCX_ENVDIRTY),a
                pop     bc
                xor     a
                ld      (ix+VCX_CNT),a
                ld      (ix+VCX_CNT+1),a
                ld      a,(iy+QD_PUT)
                ld      (ix+VCX_WPUT),a
                ld      e,a
                ld      a,(iy+QD_GET)
                scf
                sbc     a,e                 ; get - put - 1
                and     127
                ld      (ix+VCX_ROOM),a
                ret

; --- pt_pkt: A = the next packet's size. Decide whether pt_put writes it:
;   already queued by an earlier window (CNT+size <= DONE): skip it (PKMODE 0);
;   else it must FIT this window's room: write it (PKMODE 1, DONE and ROOM move);
;   else the ring is full: AUDIO_STATUS = PLAY_MORE, CF=1 (unwinds like an error).
;   Preserves BC, DE, HL.
pt_pkt:
                push    hl
                push    de
                ld      e,a
                ld      d,0
                ld      l,(ix+VCX_CNT)
                ld      h,(ix+VCX_CNT+1)
                add     hl,de               ; HL = CNT + size
                ld      (ix+VCX_CNT),l
                ld      (ix+VCX_CNT+1),h
                ld      a,(ix+VCX_DONE)
                sub     l
                ld      a,(ix+VCX_DONE+1)
                sbc     a,h                 ; CF iff DONE < CNT + size: not queued yet
                ld      a,0
                jr      nc,pk_mode          ; queued already: skip it
                ld      a,(ix+VCX_ROOM)
                sub     e
                jr      c,pk_full
                ld      (ix+VCX_ROOM),a
                ld      (ix+VCX_DONE),l
                ld      (ix+VCX_DONE+1),h
                ld      a,1
pk_mode:
                ld      (PLY_PKMODE),a
                pop     de
                pop     hl
                or      a                   ; CF=0
                ret
pk_full:
                ld      a,PLAY_MORE
                ld      (AUDIO_STATUS),a
                pop     de
                pop     hl
                scf
                ret

; --- pt_put: A = a packet byte -> the ring at VCX_WPUT (when PKMODE says write).
;   Preserves BC, DE, HL, IX, IY; CF=0.
pt_put:
                push    hl
                push    de
                ld      e,a
                ld      a,(PLY_PKMODE)
                or      a
                jr      z,pp_done           ; a packet an earlier window queued
                ld      l,(iy+QD_ADDR)
                ld      h,(iy+QD_ADDR+1)
                ld      a,(ix+VCX_WPUT)
                inc     a                   ; PRE-increment, as the VG-8020's rings (its
                and     127                 ; first packet sits at index 1, PUT = the
                ld      (ix+VCX_WPUT),a     ; last byte written: scratchpad/playq_run7.out)
                add     a,l
                ld      l,a
                adc     a,h
                sub     l
                ld      h,a                 ; HL = base + WPUT
                ld      (hl),e
pp_done:
                pop     de
                pop     hl
                or      a
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
