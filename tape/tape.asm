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
PSG_WRITE:      equ     $A1             ; PSG value write port (R15 = general-output port B)
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
; Oracle-sourced reference LOW words (black-box VG-8020, matching sysvars.inc):
; SCREEN,,,1 leaves CS120 LOW = bytes 53 5C; SCREEN,,,2 sets CS240 LOW = 25 2D.
; cas_seed writes these when the work area is blank (real BIOS cold-init does the
; same); csav_speed then only picks which one is the active word.
CAS_LOW_1200:   equ     $5C53           ; CS120 reference low-signal length word (53 5C)
CAS_LOW_2400:   equ     $2D25           ; CS240 reference low-signal length word (25 2D)
LOWLIM:         equ     $FCA4           ; read discrimination threshold work byte (real sysvar)
; CASBAUD: our resolved-baud cache for one write session. TAPOON computes the
; baud from the active table above and stores it here (0 = 1200, $FF = 2400);
; TAPOUT/TAPOOF read it cheaply per byte, so the per-bit cost stays a single
; load and the FSK stays tight enough to read back at 2400. Parked on WINWID
; ($FCA5), a cassette READ var that is idle during a write -- not one of the
; write-timing tables, so it never collides. It is a derived cache, not a baud
; selector: the system's choice still lives in the active table, read each TAPOON.
CASBAUD:        equ     $FCA5           ; = WINWID (resolved-baud cache; see above)
; Touch-panel coordinate latches -- the real MSX work bytes GTPAD writes on a
; contacted sense and the X/Y sub-calls read back (C-BIOS systemvars.asm, an
; allowed source: "FC9C last read Y-position of a touchpad", "FC9D last read X").
; Zeroed by cold-init, so an untouched panel reads 0. See gtpad below.
PADY:           equ     $FC9C           ; touch-panel latched Y (C-BIOS PADY)
PADX:           equ     $FC9D           ; touch-panel latched X (C-BIOS PADX)
; FREE_ORG history: $3A72 until 2026-07-11 (D5, spec-cbios-repack-tooling.md §6);
; retargeted to $09EE when the float pack (F2) grew the merged-ROM BASIC window
; over the old block (D5 revision, same spec). $09EE-$0D00 is 0x00 fill in ALL
; twelve C-BIOS main variants (MSX1/2/2+ x generic/EU/JP/BR, measured 2026-07-11
; by tools/build_patches.py verify_all_variants -- the MSX2 mains have content up
; to $09ED, so the old MSX1-only gap start $09D9 is NOT universal). Layout fact
; observed from the BSD-licensed C-BIOS artifacts themselves; no reference ROM.
FREE_ORG:       equ     $09EE           ; start of unused page-0 ROM fill (all variants)

; Printer (Centronics) interface ports -- MSX2 Technical Handbook Ch.5a §4.1
; "Printer interface": port 91H = 8-bit data latch; port 90H bit 0 (WRITE) =
; STROBE*, active-low ("send data when 0"); port 90H bit 1 (READ) = status,
; 0 = READY, 1 = BUSY. Used by our LPTOUT below.
PRN_DATA:       equ     $91             ; data latch (write)
PRN_STAT:       equ     $90             ; status (read bit1) / strobe (write bit0)
PRN_BUSY:       equ     %00000010       ; port 90H read bit 1: 1 = BUSY, 0 = READY

;--------------------------------------------------------------------------------
; Tuning constants.
;--------------------------------------------------------------------------------
CASW_1:         equ     $0B             ; PPI BSR command: Port C bit 5 := 1
CASW_0:         equ     $0A             ; PPI BSR command: Port C bit 5 := 0
MOTOR_ON:       equ     $08             ; PPI BSR command: Port C bit 4 := 0 (motor on)
MOTOR_OFF:      equ     $09             ; PPI BSR command: Port C bit 4 := 1 (motor off)

; djnz half-period iteration counts. NOT copied loop counts, and since D-CASDUTY
; no longer computed from the documented tone either: each is SOLVED from a
; direct measurement of the reference machine's own waveform.
; 🔬 THE INSTRUMENT (scratchpad/kwdrain_castrace.py): a watchpoint on the PPI
; control register logs both edges of every cassette cycle against openMSX's own
; clock, and the VG-8020 runs the same CSAVE through the same watchpoint -- two
; half-period sequences in T-STATES, with no recording in between. Every earlier
; reading in this defect came from a recorded WAV, which is the writer convolved
; with the cassette port and quantised to 44.1 kHz; that is why they could rank
; two builds and never say WHICH emission was late.
;
;                 short tone HI / LO      long tone HI / LO
;   VG-8020         740 / 756  (+16)       1492 / 1476  (-16)
;   zerobas was     720 / 779  (+59)       1448 / 1554  (+106)
;   zerobas now     748 / 750  ( +2)       1504 / 1498  (  -6)
;
; The reference's high half is EXACTLY 740 in all 19532 short cycles and ours was
; EXACTLY 720 in all 6368: the variation is entirely in the LOW half, on both
; machines, because that is the half the `ret` and the caller's next `call` run
; inside. Full-cycle periods already agreed (1499 against 1496) -- what was wrong
; was the SPLIT, by about four times the reference's own asymmetry.
; 🔬 THE MODEL THE TRACE FITS, which is what makes these solved and not swept: a
; djnz iteration costs 14 T (not 13 -- M1 contention), a high half carries 20 T of
; overhead and a plain low half 92 T, so half = 14*count + b. Two tones at two
; counts (50 -> 720 and 102 -> 1448) determine both figures with nothing over.
; A bit's LAST low half carries the per-bit tail as well, b = 210.
;   CAS_HHALF  52 -> 748 high, 52-CAS_DUTY = 47 -> 750 low
;   CAS_LHALF 106 -> 1504 high, and 106-CAS_BITCOMP0 = 92 -> 1498 for a '0' bit
;   52-CAS_BITCOMP = 39 -> 756 for a '1' bit's last cycle and the byte boundary
; ⚠️ ITERATIONS, NOT SAMPLES: a tail is a fixed T-state cost, so the same count is
; right at both bauds. Each must stay BELOW the smallest half-period count in use
; (CAS_HHALF24 = 24) or the subtraction would wrap.
; ⚠️ 2400 BAUD IS NOT MEASURED against an oracle -- the trace above is a 1200-baud
; CSAVE. Only the identity CAS_LHALF24 == CAS_HHALF is carried up to it.
; 🔴 THE DUTY FIX AND THE LEADER LENGTH ARE COUPLED, MEASURED, AND NOT OBVIOUS:
; with the reference-matching duty and the OLD 4000-cycle leader the VG-8020
; stops decoding our header entirely -- worse than the lopsided waveform it
; replaced. The standard 16000-cycle leader restores it. Shorten CAS_LONGLEN and
; this waveform stops being readable; the two constants must move together.
CAS_HHALF:      equ     52              ; 1200 baud high tone ~2400 Hz half cycle
CAS_LHALF:      equ     106             ; 1200 baud low  tone ~1200 Hz half cycle
CAS_HHALF24:    equ     24              ; 2400 baud high tone ~4800 Hz half cycle
CAS_LHALF24:    equ     CAS_HHALF       ; 2400's low tone IS 1200's high tone --
                                        ; an identity, so it cannot drift apart

CAS_LONGLEN:    equ     16000           ; long header (new file), full hi-freq cycles
CAS_SHORTLEN:   equ     4000            ; short header (between blocks)
; The three low-half corrections, each solved from the model above against the
; reference's own figures. CAS_DUTY applies to EVERY cycle (the ret/call
; overhead); the other two additionally absorb the per-bit tail on the two bit
; paths, which differ because the '0' and '1' arms reach the next cycle
; differently.
CAS_DUTY:       equ     5               ; every low half: ret + the caller's call
CAS_BITCOMP:    equ     13              ; '1' bit and the stop-bit/byte boundary
CAS_BITCOMP0:   equ     14              ; '0' bit: its own tail, its own figure
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
; LPTOUT jump vector ($00A5), repointed into our code. C-BIOS ships $00A5 as a
; stub (JP into an unimplemented routine), so BDOS $05 LSTOUT / BASIC LPRINT
; produce nothing on the C-BIOS target. We supply a real LPTOUT below; this is a
; "select improvement" beyond cassette -- see DESIGN.md "Scope". $00A5 is a
; standard BIOS jump-table entry (C3 xx xx) in all 12 C-BIOS main ROMs, so
; overwriting its target byte-safely repoints it (build-time asserted).
;================================================================================
                org     $00A5
                jp      lptout          ; $00A5 LPTOUT

;================================================================================
; GTPAD ($00DB) / GTPDL ($00DE) jump vectors, repointed into our code. C-BIOS
; ships both as debug stubs that CHPUT the literal text "GTPAD"/"GTPDL" onto the
; user's screen (they were never implemented), so on the C-BIOS target BASIC's
; PAD()/PDL() -- and any other caller -- get garbage. We supply real routines
; below (decision D-I-6: complete a stubbed $00xx vector in the BIOS, not in
; basic.rom). Both are standard C3-xx-xx JP entries in every C-BIOS main ROM
; (build-time asserted, tools/build_patches.py), so repointing their targets is
; byte-safe. $00DB..$00E0 are the two JPs, contiguous with the cassette block.
;================================================================================
                org     $00DB
                jp      gtpad           ; $00DB GTPAD
                jp      gtpdl           ; $00DE GTPDL

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
; cas_seed: seed-if-zero of the CS120/CS240 reference LOW words. On a real MSX the
; main-BIOS cold-init fills these tables; the C-BIOS + zerobas-tape stack has no
; such cold-init (no BIOS seed, no cold-init hook, no SCREEN,,,baud), so a blank
; work area leaves them reading 0. TAPOON calls this first so the whole write
; stack has valid reference tables regardless of caller -- BASIC (csav_speed) then
; only sets the active word. Seed-if-zero, never clobber: the pair is only ever
; both-blank (cold) or both-set (a genuine cold-init), so CS120_LOW == 0 is a
; sufficient sentinel and a legitimately-seeded table is left untouched.
; Changes: AF, HL
cas_seed:
                ld      hl,(CS120_LOW)
                ld      a,h
                or      l
                ret     nz              ; already seeded -> leave it
                ld      hl,CAS_LOW_1200
                ld      (CS120_LOW),hl
                ld      hl,CAS_LOW_2400
                ld      (CS240_LOW),hl
                ret

;--------------------------------
; cas_baud: detect the active write baud from the cassette work area, honouring
; whatever the system selected -- no private flag. When a baud is chosen (e.g.
; SCREEN ,,,baud), the system copies its reference table CS120 ($F3FC, 1200) or
; CS240 ($F401, 2400) into the active LOW slot ($F406). We compare the active
; LOW word against CS120 first, then CS240: a CS240 match means 2400, anything
; else -- a CS120 match or any unrecognised value -- defaults to the MSX-standard
; 1200. TAPOON's cas_seed guarantees CS120/CS240 hold their real reference words
; before we get here, so an unselected baud (active still 0) simply matches
; neither table and falls to the 1200 default via the catch-all no-match path.
; Pure comparison against the live tables: no copied timing constants.
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
                ld      a,c
                sub     CAS_DUTY        ; D-CASDUTY: the ret/call overhead lands
                ld      b,a             ; in the low half of EVERY cycle
cas_cycle_l:    djnz    cas_cycle_l
                ret

;--------------------------------
; cas_cycle_last: cas_cycle for the FINAL cycle of a data bit -- the low half is
; shortened by E because the per-bit tail (pop/pop/djnz/rra/push/push/jr/call)
; runs after the line goes low and before the next cycle raises it, so that time
; is part of THIS half-period whether we count it or not.
; In: C = half-period count, E = the tail to subtract (CAS_BITCOMP/CAS_BITCOMP0).
; TAPOUT's BIOS contract is "Changes: all", so E is ours to use.
; 🎯 ONLY the final cycle of a bit: a `1` bit's first cycle is followed by a bare
; `call cas_cycle` and measures clean, and the LEADER loop measures clean too --
; both keep the uncompensated routine, which is what the measurement says they
; should. Input/Output/Changes as cas_cycle.
cas_cycle_last:
                ld      a,CASW_1
                out     (PPI_REGS),a
                ld      b,c
cas_cyl_h:      djnz    cas_cyl_h
                ld      a,CASW_0
                out     (PPI_REGS),a
                ld      a,c
                sub     e               ; E = this path's tail, set by the caller
                ld      b,a
cas_cyl_l:      djnz    cas_cyl_l
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
                call    cas_seed        ; ensure CS120/CS240 hold their reference words
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
                ld      e,CAS_BITCOMP0
                call    cas_cycle_last  ; D-CASCOMP: the bit's LAST cycle
                jr      tapout_next
tapout_one:
                call    cas_short       ; '1' bit: two high-freq cycles
                call    cas_cycle       ; first cycle: measures clean, uncompensated
                ld      e,CAS_BITCOMP
                call    cas_cycle_last  ; D-CASCOMP: the bit's LAST cycle
tapout_next:
                pop     bc
                pop     af
                djnz    tapout_bit
                call    cas_short       ; 2 stop bits = four high-freq cycles
                call    cas_cycle
                call    cas_cycle
                call    cas_cycle
                ; 🔴 D-CASCOMP: THE BYTE BOUNDARY IS A TAIL TOO, and a bigger one
                ; than a bit boundary -- this cycle is followed by `or a`, `ret`,
                ; and the NEXT tapout's `di` / `push af` / `call cas_long` before
                ; any line change. Compensating only the bit boundaries left the
                ; reference DECODING but garbling the name; this is the other site.
                ld      e,CAS_BITCOMP
                call    cas_cycle_last
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

;================================================================================
; $00A5 LPTOUT -- send one character to the Centronics printer port.
;
; C-BIOS stubs this vector, so on the C-BIOS target BDOS $05 LSTOUT (and BASIC
; LPRINT) produce no output. zerobas-disk's lstout_body deliberately DELEGATES to
; main-BIOS $00A5 (the two-interface rule), so supplying a real LPTOUT here makes
; list output work with zero change to the disk ROM.
;
; Protocol (MSX2 Technical Handbook Ch.5a §4.1 "Printer interface"): wait until
; port 90H bit 1 (READ) is 0 (READY), latch the byte to port 91H, then pulse the
; active-low STROBE* on port 90H bit 0 -- assert with a $00 write, release with a
; $FF write. The whole-byte $00/$FF strobe writes reproduce the on-the-wire
; sequence observed on real hardware (disk/docs/tier2-lstout-characterisation.md
; §3.2), so a printer driven by our LPTOUT sees exactly the standard waveform.
;
; In:      A = character to print
; Out:     CY reset (success -- we block until READY, so we do not report failure)
; Changes: F only. A and every other register are preserved, per the published
;          LPTOUT contract (map.grauw.nl msxbios: "Affected: F"). We save the char
;          in B (restored) because reading the status port clobbers A.
lptout:
                push    bc
                ld      b,a             ; save char (A must be preserved on return)
lptout_wait:
                in      a,(PRN_STAT)    ; 90H read: bit 1 = status
                and     PRN_BUSY
                jr      nz,lptout_wait  ; 1 = BUSY -> spin until READY (0)
                ld      a,b
                out     (PRN_DATA),a    ; 91H: latch the data byte
                xor     a
                out     (PRN_STAT),a    ; 90H <- $00: STROBE* asserted (bit0 = 0)
                dec     a               ; A = $FF
                out     (PRN_STAT),a    ; 90H <- $FF: STROBE* released (bit0 = 1)
                ld      a,b             ; restore the character to A
                pop     bc
                or      a               ; CY = 0 (success)
                ret

;================================================================================
; General-purpose joystick-port I/O for the analog input devices, shared by
; GTPDL and GTPAD. Source for the port wiring: MSX2 Technical Handbook ch.5
; (figs. 5.21/5.22), corroborated by our own black-box oracle characterisation
; (scratchpad/i2_input_notes.md). The PSG's second 8-bit port (register 15,
; output) drives the two joystick connectors; register 14 (input) reads the one
; the select bit points at:
;
;   R15 b6 = 0  -> R14 b0..b5 read joystick port 1 terminals 1,2,3,4,6,7
;   R15 b6 = 1  -> ... port 2
;   R15 b4      -> port-1 8th terminal (the pulse/clock output line)
;   R15 b5      -> port-2 8th terminal
;   R15 b7      -> keep 1 (kana lamp off); R15 b0..b3 = terminals 6/7 outputs
;
; No reference ROM was read: the bit meanings are the published PSG-port map and
; the pin identities were recovered from openMSX as a black box (i2_pinmap.py /
; i2_frame.py), the same footing as the cassette FSK derivation above.
;================================================================================

;--------------------------------
; psg_r15: write A to PSG register 15 (the output port).  Changes: AF
psg_r15:
                push    af
                ld      a,15
                out     (PSG_REGS),a    ; select R15
                pop     af
                out     (PSG_WRITE),a   ; R15 <- A
                ret

;--------------------------------
; $00DE GTPDL -- read one paddle (a dial that turns a variable resistor). The
; paddle is a retriggerable one-shot (TH fig. 5.24): pulse the port's 8th
; terminal and the dial answers on its data terminal, held for 10 us..3 ms in
; proportion to the angle. GTPDL times that pulse -- ~11.8 us per count (3 ms/255)
; -- capping at 255, which is also the idle reading when no paddle pulls the line.
;
; PDL index -> terminal was settled two ways (TH's published circuit AND our
; black-box mirror test, i2_input_notes.md §2): odd index = port 1, even = port 2,
; and paddle k (1..6) of that port answers on R14 bit (k-1).
;
; In:  A = paddle number 1..12
; Out: A = 0..255   (255 = at rest / no device)
; Changes: AF, BC, HL   (IX/IY/DE preserved; the BASIC wrapper guards IX anyway)
gtpdl:
                dec     a               ; 0..11
                ld      l,a             ; L = index-1
                srl     a               ; A = terminal bit position 0..5 = (n-1)>>1
                ld      b,a
                ld      a,1
                inc     b               ; shift (bit+1) times, leaving 1<<bit
gtpdl_mk:
                dec     b
                jr      z,gtpdl_mkd
                add     a,a
                jr      gtpdl_mk
gtpdl_mkd:
                ld      h,a             ; H = R14 mask for this paddle's terminal
                bit     0,l             ; index-1 bit0: 0 -> port 1 (odd n), 1 -> port 2
                ld      a,$BF           ; port 1 8th-terminal HIGH: b7=1 b6=0(if1) b5=1 b4=1
                ld      c,$AF           ; port 1 8th-terminal LOW : b4=0
                jr      z,gtpdl_go
                ld      a,$FF           ; port 2 8th-terminal HIGH: b7=1 b6=1(if2) b5=1 b4=1
                ld      c,$DF           ; port 2 8th-terminal LOW : b5=0
gtpdl_go:
                ; A = 8th-terminal-high value, C = 8th-terminal-low value, H = mask.
                ; The one-shot triggers on the 8th terminal's HIGH->LOW edge and
                ; then holds its data terminal high for the dial-proportional time
                ; while the 8th terminal stays low; GTPDL counts that window. (Edge
                ; and levels recovered from the openMSX device as a black box,
                ; scratchpad/i2_input_notes.md; nothing-plugged idles high -> 255.)
                di                      ; the count is a real-time measurement
                ld      b,a             ; B = 8th-terminal-high value
                ld      a,15
                out     (PSG_REGS),a    ; select R15 (once, for all three writes)
                ld      a,c
                out     (PSG_WRITE),a   ; 8th terminal low  (defined start level so the
                                        ;  next write is always a real rising edge)
                ld      a,b
                out     (PSG_WRITE),a   ; 8th terminal high -> RISING edge. A touch panel
                                        ;  starts its conversion here, so its EOC line
                                        ;  reads low through the count (-> PDL 0), while a
                                        ;  paddle ignores it. All three writes precede the
                                        ;  paddle's trigger below, so its window is unmoved.
                ld      a,c
                out     (PSG_WRITE),a   ; 8th terminal low -> FALLING edge (paddle trigger);
                                        ;  hold low across the count
                ld      a,14
                out     (PSG_REGS),a    ; select R14 for the read loop
                ; The loop is timed, not incidental: openMSX holds the dial's data
                ; terminal high for a fixed window (~4.7 ms-equivalent for a centred
                ; paddle) and the count = window / loop-time, so the loop-time SETS
                ; the 0..255 scale. This body is 36 T/iteration (in 11 + and 4 +
                ; jr-nt 7 + dec 4 + jp 10), which lands the centred paddle on 128 and
                ; caps at 255 -- both pinned by the Phase D gate, not asserted here.
                ; jp (a flat 10 T) rather than jr keeps the period at exactly 36.
                ld      c,255           ; count DOWN so 255 iterations = the cap
gtpdl_loop:
                in      a,(PSG_STAT)    ; read R14                          (11)
                and     h               ; isolate this paddle's terminal    (4)
                jr      z,gtpdl_done    ; low -> one-shot expired -> stop    (7/12)
                dec     c               ; one more count                    (4)
                jp      nz,gtpdl_loop   ; until the window caps at 255       (10)
gtpdl_done:                             ; count = 255 - c (c=0 on the cap path)
                ld      a,255
                sub     c
                ei
                ret

;--------------------------------
; $00DB GTPAD -- read the touch panel (a NEC uPD7001 4-channel serial ADC). The
; TH publishes the caller contract (List 5.8: sense with A&3 = 0, then read the
; X / Y) and the uPD7001's own datasheet (1982 NEC Microcomputer Catalog
; pp.479-482, A/Clean) publishes the serial protocol. 📏 THE PIN MAP IS MEASURED
; (D-PADTRACE, 2026-09-27, scratchpad/padtrace_probe.py + padtrace_decode.py): the
; VG-8020's I/O PORT traffic during each PAD(n), windowed, with the rig's mouse
; holding the pen -- ports only, no ROM byte. Port 1:
;   R15 (out): b0 = SCK (terminal 6), b1 = DI (terminal 7, the channel select),
;              b4 = /CS (terminal 8, low = selected)
;   R14 (in):  b0 = pen contact (terminal 1, low = touched), b1 = end of
;              conversion (terminal 2), b2 = SO (terminal 3), b3 = the pen SWITCH
;              (terminal 4, low = pressed)
; Port 2 by the same terminals: SCK b2, DI b3, /CS b5 (no port-2 trace exists).
;
; A = device*4 + sub:  device 0/1 = touch panel 1/2; sub 0 sense (report whether
; the panel is contacted, $FF/$00), 1 = X (channel 0), 2 = Y (channel 3), 3 =
; button ($FF pressed else $00). BASIC passes 0..7 only; ids 8..19 (light pen,
; mouse) are real BIOS surface but out of this arc's scope -> 0.
;
; 🔴 D-I-7's TWO GUESSES ARE RETIRED BY THAT TRACE. The address phase was omitted
; ("the data path's values are not validatable": an undriven panel converts to 0)
; and the clock was driven on R15 b4 -- which is /CS -- so nothing converted and
; X/Y read 0 while the VG-8020 followed the pen; and the switch was read off R14
; b4 where the trace shows b3. A FRAME, as traced: wait for end-of-conversion,
; select with SCK high and DI set, then eight times SCK low / read SO / SCK high,
; then deselect. The value read is the conversion the PREVIOUS frame's DI chose
; (DI 0 = X, DI 1 = Y): the reference's frames read X X Y X Y after a discarded
; first, e.g. 22 22 23 22 23 for PAD(1)=22 PAD(2)=23. Three frames give the same
; X and Y: discard (select X), X (select Y), Y.
;
; The X/Y LATCH (TH List 5.8, matched to the VG-8020): a `sense` (sub 0) that
; finds the panel contacted runs the conversion and stores the coordinates in
; PADX/PADY; a sense that finds it NOT contacted leaves them untouched. The X/Y
; sub-calls just read PADX/PADY. So X/Y report the last CONTACTED reading -- which
; is why, in a `FOR i=0 TO 7` sweep, an empty port 2's X/Y still read the value a
; contacted port 1 latched two calls earlier, and why nothing-plugged reads 0
; (the latch is never written). This reproduces the reference bit-for-bit; the
; latch is the mechanism, not a workaround (user's call: bug-for-bug where
; achievable, 2026-07-23).
;
; In:  A = 0..19    Out: A = $00/$FF (sense/button) or 0..255 (X/Y)
; Changes: AF, BC, DE, HL
gtpad:
                cp      8
                jr      c,gtpad_tp      ; 0..7 -> touch panel
                xor     a               ; 8..19: light pen / mouse -> not supported
                ret
gtpad_tp:
                ld      c,a
                and     3               ; sub-function 0..3
                ld      e,a
                ld      a,c
                rrca
                rrca
                and     1               ; device 0/1 -> selects the port
                ; Per port: B = R15 with the 8th terminal HIGH and the port selected
                ; for reading (b6), C = same with the 8th terminal LOW (the SCK/CS
                ; drive line).  device 0 -> port 1 (b6=0, drive b4); device 1 ->
                ; port 2 (b6=1, drive b5).
                ld      b,$BF           ; port 1 read select: b7=1 b6=0 b5=1 b4=1
                ld      c,$8D           ; port 1 frame: selected, SCK high, DI 0
                                        ; (the trace's own value)
                ld      hl,$0110        ; H = SCK (b0), L = /CS (b4); DI = SCK*2
                jr      z,gtpad_dev
                ld      b,$FF           ; port 2 read select: b7=1 b6=1 b5=1 b4=1
                ld      c,$C7           ; port 2 frame: selected, SCK high, DI 0
                ld      hl,$0420        ; H = SCK (b2), L = /CS (b5)
gtpad_dev:
                ; X (sub 1) and Y (sub 2) are pure latch reads -- no port I/O, no di.
                ld      a,e
                cp      1
                jr      z,gtpad_getx
                cp      2
                jr      z,gtpad_gety
                di                      ; sense / button touch the port
                or      a
                jr      z,gtpad_sense   ; sub 0
                ; sub 3: the pen SWITCH (terminal 4, R14 b3, active low -- the
                ; trace's B3 against BB; D-I-7 read b4, and PAD(3) read 0)
                call    gtpad_selread   ; select the port, read R14
                and     %00001000
                ei
                ld      a,0
                ret     nz              ; high = not pressed -> $00
                dec     a               ; low  = pressed     -> $FF
                ret
gtpad_getx:
                ld      a,(PADX)        ; last contacted X (0 if never contacted)
                ret
gtpad_gety:
                ld      a,(PADY)        ; last contacted Y
                ret
gtpad_sense:
                call    gtpad_contact
                jr      nz,gtpad_sense_no
                push    bc              ; [C = the DI-0 frame value]
                call    gtpad_frame     ; discarded -- it selects X (DI 0)
                ld      a,h
                add     a,a             ; the DI bit is the SCK bit's neighbour
                or      c
                ld      c,a             ; DI 1
                call    gtpad_frame     ; A = X, and it selects Y
                ld      (PADX),a
                pop     bc              ; DI 0 again
                call    gtpad_frame     ; A = Y
                ld      (PADY),a
                ei
                ld      a,$FF           ; contacted -> $FF
                ret
gtpad_sense_no:
                ei
                xor     a               ; not contacted -> $00, latch left as-is
                ret

;--------------------------------
; gtpad_selread: select the port (B) and read R14 into A.  Changes: AF
gtpad_selread:
                ld      a,b
                call    psg_r15         ; R15 = B (select port, 8th terminal high)
                ld      a,14
                out     (PSG_REGS),a
                in      a,(PSG_STAT)
                ret

;--------------------------------
; gtpad_contact: Z set iff the selected panel is contacted (R14 b0 low). Changes: AF
gtpad_contact:
                call    gtpad_selread
                and     %00000001       ; terminal 1, active low
                ret                     ; Z = contacted

;--------------------------------
; gtpad_frame: one uPD7001 frame, as the VG-8020 runs it (D-PADTRACE). In: C = the
; R15 value "selected, SCK high, DI as wanted", H = the port's SCK bit, L = its
; /CS bit. Out: A = the 8 bits read off SO (R14 b2), MSB first -- the conversion
; the PREVIOUS frame's DI selected. Changes: AF, DE   (B, C, H, L preserved)
gtpad_frame:
                ld      e,0             ; end-of-conversion wait, bounded: a JOYSTICK
gtpad_eoc:                              ; in the port holds terminal 2 (down) low
                ld      a,14            ; for as long as it is pushed
                out     (PSG_REGS),a
                in      a,(PSG_STAT)
                and     %00000010       ; R14 b1 = end of conversion
                jr      nz,gtpad_go
                dec     e
                jr      nz,gtpad_eoc
gtpad_go:
                ld      d,0             ; D = accumulated byte
                ld      e,8             ; 8 result bits
gtpad_cbit:
                ld      a,c
                call    psg_r15         ; selected, SCK high (DI held)
                ld      a,c
                xor     h
                call    psg_r15         ; SCK low
                ld      a,14
                out     (PSG_REGS),a
                in      a,(PSG_STAT)
                and     %00000100       ; SO = R14 b2 (terminal 3)
                sla     d               ; make room (MSB first); clobbers flags...
                or      a               ; ...so re-test the SO bit still in A
                jr      z,gtpad_cnext
                inc     d               ; SO high -> set this bit
gtpad_cnext:
                dec     e
                jr      nz,gtpad_cbit
                ld      a,c
                call    psg_r15         ; SCK high
                ld      a,c
                or      l
                call    psg_r15         ; deselect -- the conversion starts
                ld      a,d
                ret

tape_end:       ; marks the end of the routine block (the patch slices to here)
; Guard: cassette routines must stay in the first 16K (page 0); the second 16K
; ($4000-$7FFF) is paged out for BASIC/cartridges. A negative ds here means the
; code crossed $4000 -- move it to a smaller free region.
                ds      $4000 - tape_end
