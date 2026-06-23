; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

;================================================================================
; tape.asm -- clean-room MSX cassette (tape) BIOS routines for C-BIOS v0.29 MSX1.
;
; SELF-CONTAINED. This file assembles to *only the bytes our patch adds*: the seven
; repointed cassette jump vectors and the routine bodies in spare ROM. It needs
; no C-BIOS source -- assemble it on its own with pasmo and dist/build-patches.sh
; slices the two changed regions straight out of the output. openMSX tests these
; routines by booting a stock C-BIOS ROM with the resulting patch applied on load.
;
; Everything below is either our own clean-room code (the routine bodies, written
; against a black-box oracle -- see ../docs/clean-room-policy.md) or a published
; address (MSX hardware ports, BIOS work-area slots, and two layout facts of the
; baf2e9c6... v0.29 ROM). No stock-C-BIOS *code* appears here.
;
; FSK at 1200 baud: a '0' bit is one cycle of the low frequency (~1200 Hz), a '1'
; bit is two cycles of the high frequency (~2400 Hz); the leader is a continuous
; high-frequency carrier. The half-period counts are derived from the documented
; FSK frequencies and the 3.58 MHz Z80 clock, then tuned until the recording
; round-trips through tools/omsx/cas_decode.py -- never copied loop counts.
; See ../docs/spec-cassette.md.
;================================================================================

;--------------------------------------------------------------------------------
; Environment: published addresses, NOT code.
;
; MSX hardware ports + BIOS work area (MSX2 Technical Handbook / MSX Assembly
; Page), and one layout fact: FREE_ORG, the start of the unused 0x00 fill in page
; 0 our code lands in. (We implement the motor routine ourselves rather than
; calling C-BIOS's, so its address is no longer a dependency -- see stmotr below.)
; A different C-BIOS build would re-derive only FREE_ORG.
;--------------------------------------------------------------------------------
PSG_REGS:       equ     $A0             ; PSG register-select write port
PSG_STAT:       equ     $A2             ; PSG value read port (CAS-in on R14 bit 7)
PPI_REGS:       equ     $AB             ; i8255 PPI control (BSR) register
PPI_PORTC:      equ     $AA             ; i8255 PPI Port C (motor bit 4, CASW bit 5)
; Active cassette-write timing table. When the baud is selected, the system
; copies one of two reference tables -- CS120 ($F3FC, 1200) or CS240 ($F401,
; 2400) -- into the active LOW/HIGH/HEADER slots ($F406/$F408/$F40A). Verified
; on a real VG-8020 as a black box: `SCREEN ,,,1` leaves the active LOW word at
; CS120 (53 5c), `SCREEN ,,,2` sets it to CS240 (25 2d). TAPOON reads the active
; LOW word (cas_baud) to honour the baud the system chose -- no user-set flag.
; Layout: MSX2 Tech Handbook / MSX Assembly Page, corroborated by C-BIOS
; systemvars.asm and a boot-state oracle dump.
CS120_LOW:      equ     $F3FC           ; 1200-baud reference: low-signal length word
CS240_LOW:      equ     $F401           ; 2400-baud reference: low-signal length word
ACT_LOW:        equ     $F406           ; active low-signal length word (the live baud)
LOWLIM:         equ     $FCA4           ; read discrimination threshold work byte (real sysvar)
; CASBAUD: our resolved-baud cache for one write session. TAPOON computes the
; baud from the active table above and stores it here (0 = 1200, $FF = 2400);
; TAPOUT/TAPOOF read it cheaply per byte, so the per-bit cost stays a single
; load and the FSK stays tight enough to read back at 2400. Parked on WINWID
; ($FCA5), a cassette READ var that is idle during a write -- not one of the
; write-timing tables, so it never collides. It is a derived cache, not a baud
; selector: the system's choice still lives in the active table, read each TAPOON.
CASBAUD:        equ     $FCA5           ; = WINWID (resolved-baud cache; see above)
FREE_ORG:       equ     $3A72           ; start of unused page-0 ROM fill

;--------------------------------------------------------------------------------
; Tuning constants.
;--------------------------------------------------------------------------------
CASW_1:         equ     $0B             ; PPI BSR command: Port C bit 5 := 1
CASW_0:         equ     $0A             ; PPI BSR command: Port C bit 5 := 0
MOTOR_ON:       equ     $08             ; PPI BSR command: Port C bit 4 := 0 (motor on)
MOTOR_OFF:      equ     $09             ; PPI BSR command: Port C bit 4 := 1 (motor off)

; djnz half-period iteration counts. NOT copied loop counts: each is COMPUTED by
; inverting the documented FSK frequency through the cas_cycle half-period cost.
; One half takes ~(26 + 14.4*C) T-states (the 14.4/iter + 26 fixed overhead is
; measured from openMSX as a black box -- an oracle observation, never a ROM
; listing), so on the 3.579545 MHz Z80 a target tone f_FSK needs
;     C = round( ( 3579545 / (2*f_FSK) - 26 ) / 14.4 ).
; That yields 50/102 for 1200 baud's 2400/1200 Hz and 24/50 for 2400 baud's
; 4800/2400 Hz (each within 0.1 of an integer; confirmed by round-trip). 2400 baud
; is the same two tones up one octave -- its low tone (2400 Hz) equals 1200 baud's
; high tone -- so CAS_LHALF24 == CAS_HHALF. See PROVENANCE.md.
CAS_HHALF:      equ     50              ; 1200 baud high tone ~2400 Hz half cycle
CAS_LHALF:      equ     102             ; 1200 baud low  tone ~1200 Hz half cycle
CAS_HHALF24:    equ     24              ; 2400 baud high tone ~4800 Hz half cycle
CAS_LHALF24:    equ     50              ; 2400 baud low  tone ~2400 Hz half cycle

CAS_LONGLEN:    equ     4000            ; long header (new file), full hi-freq cycles
CAS_SHORTLEN:   equ     2000            ; short header (between blocks)
CAS_FLUSHLEN:   equ     32              ; trailing carrier cycles flushed at TAPOOF

; TAPION lock: skip CAS_SKIP edges to clear the motor-restart spin-up, then
; average LOWLIM over CAS_RUNLEN leader halves. CAS_RUNLEN stays 16 (the >>4
; LOWLIM scaling depends on it).
CAS_SKIP:       equ     32
CAS_RUNLEN:     equ     16
; Leading-silence tolerance. openMSX renders a .cas as audio with ~2 s of silence
; before the leader (CasImage.cc LONG_SILENCE), and a real/recorded tape can have
; an arbitrary gap before the carrier too. Before measuring, TAPION waits for the
; first real edge, counting flat timeouts (~256 sample iterations each, ~3 ms)
; against this 16-bit budget; a genuinely dead tape exhausts it and fails. ~1500
; covers ~5 s -- generous, and only spent while the signal is actually absent.
CAS_FLATMAX:    equ     1500

CASIN_R14:      equ     14              ; PSG register holding CAS-in on bit 7

;================================================================================
; All seven cassette jump vectors ($00E1-$00F3), repointed into our code --
; including STMOTR ($00F3), so the patch relies on no stock-C-BIOS motor routine.
;================================================================================
                org     $00E1
                jp      tapion          ; $00E1 TAPION
                jp      tapin           ; $00E4 TAPIN
                jp      tapiof          ; $00E7 TAPIOF
                jp      tapoon          ; $00EA TAPOON
                jp      tapout          ; $00ED TAPOUT
                jp      tapoof          ; $00F0 TAPOOF
                jp      stmotr          ; $00F3 STMOTR

;================================================================================
; Routine bodies, in unused page-0 ROM.
;================================================================================
                org     FREE_ORG

;--------------------------------
; $00F3 STMOTR -- cassette motor control, our own implementation.
; The MSX motor relay is i8255 PPI Port C bit 4 (0 = on), driven through the PPI
; control register's Bit-Set/Reset mode -- the same published mechanism CASW
; (Port C bit 5) uses. Implementing it here means the patch depends on no
; stock-C-BIOS code or address; it works on any C-BIOS build with the spare ROM.
; In:      A = 0 stop, 0xFF toggle, otherwise start  (MSX STMOTR convention)
; Changes: AF only  (so it is safe for the tape routines to call mid-operation)
stmotr:
                or      a
                jr      z,stmotr_off    ; A = 0 -> stop
                inc     a
                jr      z,stmotr_tog    ; A = 0xFF -> toggle
stmotr_on:
                ld      a,MOTOR_ON      ; Port C bit 4 := 0
                out     (PPI_REGS),a
                ret
stmotr_off:
                ld      a,MOTOR_OFF     ; Port C bit 4 := 1
                out     (PPI_REGS),a
                ret
stmotr_tog:
                in      a,(PPI_PORTC)   ; read the Port C output latch
                bit     4,a
                jr      z,stmotr_off    ; bit 4 = 0 (motor on) -> turn off
                jr      stmotr_on

;--------------------------------
; cas_baud: detect the active write baud from the cassette work area, honouring
; whatever the system selected -- no private flag. When a baud is chosen (e.g.
; SCREEN ,,,baud), the system copies its reference table CS120 ($F3FC, 1200) or
; CS240 ($F401, 2400) into the active LOW slot ($F406). We compare the active
; LOW word against CS120 first, then CS240: a CS240 match means 2400, anything
; else -- including a CS120 match, an unrecognised value, or a blank/
; uninitialised work area (active == CS120 == 0) -- defaults to the MSX-standard
; 1200. Pure comparison against the live tables: no copied timing constants.
; Out:     Z set => 1200 baud, Z clear (NZ) => 2400 baud.   Changes: AF, HL
cas_baud:
                push    hl
                ; 1200 (and the safe default): active LOW == CS120 LOW word.
                ld      hl,CS120_LOW
                ld      a,(ACT_LOW)
                cp      (hl)
                jr      nz,cas_baud_chk24
                inc     hl
                ld      a,(ACT_LOW+1)
                cp      (hl)
                jr      z,cas_baud_1200
cas_baud_chk24:
                ; 2400: active LOW == CS240 LOW word.
                ld      hl,CS240_LOW
                ld      a,(ACT_LOW)
                cp      (hl)
                jr      nz,cas_baud_1200
                inc     hl
                ld      a,(ACT_LOW+1)
                cp      (hl)
                jr      nz,cas_baud_1200
                pop     hl              ; matched CS240 -> 2400 baud
                or      $FF             ; A nonzero -> Z clear (NZ)
                ret
cas_baud_1200:
                pop     hl
                xor     a               ; A = 0 -> Z set
                ret

;--------------------------------
; cas_short / cas_long: load C with the high-/low-tone half-period count for the
; active write baud. The baud was resolved once from the work area by TAPOON
; (cas_baud -> CASBAUD); reading the cached byte here keeps the per-bit cost to a
; single load, so the inter-cycle gap stays small and the FSK waveform reads back
; cleanly even at 2400, where a heavier per-bit baud lookup desynced the framing.
; Changes: AF, C
cas_short:
                ld      a,(CASBAUD)
                or      a
                ld      c,CAS_HHALF
                ret     z
                ld      c,CAS_HHALF24
                ret
cas_long:
                ld      a,(CASBAUD)
                or      a
                ld      c,CAS_LHALF
                ret     z
                ld      c,CAS_LHALF24
                ret

;--------------------------------
; cas_cycle: emit ONE full square-wave cycle on CAS-out.
; Input:   C = half-period djnz count (from cas_short / cas_long)
; Changes: AF, B  (preserves C, DE, HL)
cas_cycle:
                ld      a,CASW_1
                out     (PPI_REGS),a
                ld      b,c
cas_cycle_h:    djnz    cas_cycle_h
                ld      a,CASW_0
                out     (PPI_REGS),a
                ld      b,c
cas_cycle_l:    djnz    cas_cycle_l
                ret

;================================
; Clean-room cassette READ path.
;
; CAS-in is PSG register 14 bit 7 (located empirically: PPI Port B bit 7 is
; static, PSG R14 bit 7 carries the FSK).  We latch R14 once (OUT PSG_REGS,14)
; and then sample its read port (IN PSG_STAT) bit 7.
;
; The reader is baud-agnostic: TAPION *measures* the leader's half-period and
; derives the discrimination threshold (LOWLIM); TAPIN then classifies each half
; as short (high freq, a '1' carrier half) or long (low freq, a '0' carrier
; half).  A '0' bit = one long cycle (2 long halves); a '1' bit = two short
; cycles (4 short halves).  Byte framing: start(0)/8 data LSB-first/stop(1).
;================================

;--------------------------------
; cas_latch: select PSG R14 so IN (PSG_STAT) returns the CAS-in byte.
; Changes: AF
cas_latch:
                ld      a,CASIN_R14
                out     (PSG_REGS),a
                ret

;--------------------------------
; cas_half: time one CAS-in half-period -- wait for the next edge, counting.
; Direction-aware: a single "compare to previous level" hot loop (AND $80 / CP D)
; costs ~45 T-states/iteration; splitting the wait into a currently-low and a
; currently-high branch lets the hot path test bit 7 with ADD A,A (bit 7 -> CF)
; instead, dropping it to ~36 T/iteration. The half-period is unchanged, so a
; cheaper iteration means MORE iterations counted per half -- finer resolution.
; That matters only at fast bauds: at 3744 a leader half is just ~3 counts and a
; data '0' half ~6, so the long/short discrimination margin was under one count;
; more counts per half widens it. The interface and the count's meaning are
; unchanged (B = same-level iterations before the edge, starting at 1), so the
; leader-measured LOWLIM self-calibrates to the new, larger counts -- no other
; routine changes.
; In:      D = current CAS-in level (bit 7: $00 or $80)
; Out:     D = new level; B = iteration count to the edge; CF set on timeout.
; Changes: AF, B, D   (R14 must already be latched)
cas_half:
                ld      b,1
                bit     7,d
                jr      nz,cas_half_hi
cas_half_lo:                            ; level low: count until a rising edge
                in      a,(PSG_STAT)
                add     a,a             ; bit 7 -> CF
                jr      c,cas_half_hiset ; CF=1 -> went high (edge)
                inc     b
                jp      nz,cas_half_lo
                scf                     ; counter wrapped -> timeout
                ret
cas_half_hi:                            ; level high: count until a falling edge
                in      a,(PSG_STAT)
                add     a,a             ; bit 7 -> CF
                jr      nc,cas_half_loset ; CF=0 -> went low (edge)
                inc     b
                jp      nz,cas_half_hi
                scf                     ; counter wrapped -> timeout
                ret
cas_half_hiset:
                ld      d,$80           ; new level high
                or      a               ; CF = 0
                ret
cas_half_loset:
                ld      d,$00           ; new level low
                or      a               ; CF = 0
                ret

;--------------------------------
; cas_islong: classify the last half-period (count in B) as long or short.
; LOWLIM is the threshold in QUARTER-count units, so we compare B*4 against it
; -- the extra two fractional bits matter at fast bauds, where short/artifact/
; long counts differ by only ~3 and an integer threshold cannot land between the
; ~1.5x transition artifact and a real ~2x long.
; Out:     CF = 1 if long (low-freq half), 0 if short. Changes: AF (B, D, HL kept)
cas_islong:
                ld      a,b
                add     a,a             ; B*2
                add     a,a             ; B*4
                push    hl
                ld      hl,LOWLIM
                sub     (hl)            ; CF=1 if B*4 < LOWLIM (short)
                pop     hl
                ccf                     ; CF=1 if B*4 >= LOWLIM (long)
                ret

;--------------------------------
; cas_readbit: read one (already aligned) data-bit cell.
; Out:     CF = bit value (0 or 1)
; Changes: AF, B, D   (mid-byte timeouts fall through as a '1', never hang)
cas_readbit:
                call    cas_half        ; first half of the cell
                call    cas_islong      ; long -> '0'
                jr      c,cas_readbit_0
                call    cas_half        ; short -> '1': 2 high cycles = 4 halves
                call    cas_half
                call    cas_half
                scf                     ; CF = 1
                ret
cas_readbit_0:
                call    cas_half        ; long -> '0': 1 low cycle = 2 halves
                or      a               ; CF = 0
                ret

;--------------------------------
; $00E1 TAPION
; Turns the motor on and locks onto the leader tone, deriving the baud
; discrimination threshold (LOWLIM) by measuring the leader's half-period.
; Output:  CF = set if failed (no tape / no leader)
; Changes: all
tapion:
                ld      a,1
                call    stmotr          ; motor on -> inserted tape plays
                di
                call    cas_latch
                in      a,(PSG_STAT)
                and     $80
                ld      d,a             ; current CAS-in level
                ; Lock onto a SUSTAINED leader carrier, tolerating silence and
                ; transients wherever they fall. openMSX prepends ~2 s of silence
                ; before a .cas leader (CasImage.cc LONG_SILENCE) and ~1 s between
                ; blocks (SHORT_SILENCE); a mid-tape motor restart injects a flat
                ; patch, a stray ~100-count half, and chatter. Crucially the
                ; carrier can come BEFORE the silence too (the previous block's
                ; stop bits), so a one-shot "wait then skip" latches onto the stop
                ; bits and then measures across the gap.
                ;
                ; So: (1) WAIT for a real edge, counting flat timeouts against a
                ; 16-bit budget (CAS_FLATMAX) so a dead tape still fails; (2) SKIP
                ; CAS_SKIP edges to clear the spin-up transient / stray halves; (3)
                ; MEASURE CAS_RUNLEN clean halves into LOWLIM. A flat during the
                ; skip OR the measure means we latched onto stop bits / chatter,
                ; not a real leader -- restart from the wait. This locates a run of
                ; CAS_SKIP+CAS_RUNLEN consecutive carrier halves and averages only
                ; those, so a stray boundary half never enters LOWLIM. The loops
                ; stay lean so their per-half overhead matches TAPIN's (a heavier
                ; loop biases the counts, and thus LOWLIM).
tapion_relock:
                ld      bc,CAS_FLATMAX  ; 16-bit flat-timeout budget for this attempt
tapion_wait:
                push    bc
                call    cas_half        ; CF set = flat (silence / spin-up)
                pop     bc
                jr      nc,tapion_skip0 ; a real edge -> carrier present
                dec     bc
                ld      a,b
                or      c
                jr      nz,tapion_wait
                scf                     ; budget exhausted -> no tape, fail
                ret
tapion_skip0:
                ld      b,CAS_SKIP      ; clear the spin-up transient
tapion_skip:
                push    bc
                call    cas_half
                pop     bc
                jr      c,tapion_relock ; flat mid-skip -> not a sustained leader
                djnz    tapion_skip
                ld      hl,0            ; sum CAS_RUNLEN clean leader half-periods
                ld      c,CAS_RUNLEN
tapion_meas:
                call    cas_half
                jr      c,tapion_relock ; flat mid-measure -> restart (don't average it)
                ld      a,l
                add     a,b
                ld      l,a
                jr      nc,tapion_nocy
                inc     h
tapion_nocy:
                dec     c
                jr      nz,tapion_meas
tapion_haveavg:
                ; LOWLIM = 1.75 * avg-short, kept in QUARTER-count units so the
                ; threshold has fractional precision (HL holds the sum of 16
                ; shorts, so avg = HL/16 and 1.75*avg*4 = 7*HL/16). A real long
                ; half is ~2x short; the single transition half at each
                ; leader->data / stop->start boundary measures ~1.5x short, so a
                ; threshold at 1.75x rejects it with symmetric margin -- but at
                ; fast bauds only the fractional precision keeps 1.5x and 2x on
                ; opposite sides. cas_islong compares B*4 against this.
                ld      d,h             ; DE = sum
                ld      e,l
                add     hl,hl           ; 2*sum
                add     hl,hl           ; 4*sum
                add     hl,hl           ; 8*sum
                or      a               ; clear carry for sbc
                sbc     hl,de           ; 7*sum
                ld      b,4             ; >>4  -> 7*sum/16
tapion_avg:
                srl     h
                rr      l
                djnz    tapion_avg
                ld      a,l
                ld      (LOWLIM),a
                or      a               ; CF = 0: locked
                ret

;--------------------------------
; $00E4 TAPIN
; Read one framed byte from the tape (requires a prior TAPION).
; Output:  A = byte read; CF = set on error/timeout
; Changes: all
tapin:
                call    cas_latch
                in      a,(PSG_STAT)
                and     $80
                ld      d,a             ; current level
                ld      hl,0            ; 16-bit start-bit hunt timeout
tapin_hunt:                             ; (must outlast a full ~2 s leader)
                call    cas_half
                ret     c
                call    cas_islong      ; long half -> start bit (a '0')
                jr      c,tapin_start
                dec     hl
                ld      a,h
                or      l
                jr      nz,tapin_hunt
                scf                     ; no start bit found
                ret
tapin_start:
                call    cas_half        ; consume the start bit's 2nd half
                ret     c
                ld      e,0             ; assemble 8 data bits, LSB first
                ld      c,8
tapin_bit:
                call    cas_readbit
                rr      e               ; CF (this bit) -> top of E
                dec     c
                jr      nz,tapin_bit
                ld      a,e
                or      a               ; CF = 0: success
                ret

;--------------------------------
; $00E7 TAPIOF
; Stops reading from the tape: motor off, interrupts back on.
tapiof:
                xor     a
                call    stmotr          ; motor off
                ei
                ret

;--------------------------------
; $00EA TAPOON
; Turns on the cassette motor and writes the header.
; Input:   A  = zero for short header, non-zero for long header
; Output:  CF = reset (success)
; Changes: all
tapoon:
                push    af              ; remember long/short selector
                ; Resolve the system baud BEFORE the motor is on, so cas_baud's
                ; cost does not lengthen the motor-on -> leader gap: at 2400 a
                ; longer gap shifts the spin-up transient and desyncs the
                ; mid-tape TAPION re-lock (CAS_SKIP) on the next block's read.
                call    cas_baud        ; resolve the system baud from the work area
                ld      (CASBAUD),a     ; cache it for this session (0=1200, $FF=2400)
                ld      a,1
                call    stmotr          ; motor on
                di                      ; waveform timing must not be jittered
                call    cas_short       ; C = leader carrier half (cached baud)
                pop     af
                or      a               ; selector zero -> short header
                jr      z,tapoon_short
                ld      de,CAS_LONGLEN
                jr      tapoon_emit
tapoon_short:
                ld      de,CAS_SHORTLEN
tapoon_emit:
                call    cas_cycle
                dec     de
                ld      a,d
                or      e
                jr      nz,tapoon_emit
                or      a               ; CF = 0: success
                ret

;--------------------------------
; $00ED TAPOUT
; Writes data to the tape.
; Input:   A  = data to write
; Output:  CF = set if failed
; Changes: all
; Frames A as: start bit (0), 8 data bits LSB-first, 2 stop bits (1).
tapout:
                di
                push    af              ; save the data byte across cycle calls
                call    cas_long        ; start bit = '0' = one low-freq cycle
                call    cas_cycle
                pop     af
                ld      b,8             ; 8 data bits, LSB first
tapout_bit:
                rra                     ; next data bit -> CF (A rotated)
                push    af              ; preserve A and the rotation carry
                push    bc              ; preserve bit counter (cas_cycle uses B)
                jr      c,tapout_one
                call    cas_long        ; '0' bit: one low-freq cycle
                call    cas_cycle
                jr      tapout_next
tapout_one:
                call    cas_short       ; '1' bit: two high-freq cycles
                call    cas_cycle
                call    cas_cycle
tapout_next:
                pop     bc
                pop     af
                djnz    tapout_bit
                call    cas_short       ; 2 stop bits = four high-freq cycles
                call    cas_cycle
                call    cas_cycle
                call    cas_cycle
                call    cas_cycle
                or      a               ; CF = 0: success
                ret

;--------------------------------
; $00F0 TAPOOF
; Stops writing on the tape: flush a trailing carrier, motor off.
tapoof:
                call    cas_short       ; flush a short trailing carrier (cached baud)
                ld      de,CAS_FLUSHLEN
tapoof_lp:
                call    cas_cycle
                dec     de
                ld      a,d
                or      e
                jr      nz,tapoof_lp
                xor     a
                call    stmotr          ; motor off
                ei
                ret

tape_end:       ; marks the end of the routine block (the patch slices to here)
; Guard: cassette routines must stay in the first 16K (page 0); the second 16K
; ($4000-$7FFF) is paged out for BASIC/cartridges. A negative ds here means the
; code crossed $4000 -- move it to a smaller free region.
                ds      $4000 - tape_end
