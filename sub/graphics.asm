; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; graphics.asm — the SCREEN-2 geometry engine's page-0 sub-ROM island.
; Slice G1 (docs/spec-basic-graphics-g1.md): the VDP-access FLOOR + its
; interrupt-under-draw proof. No user-visible statement yet — G1 exists to build
; and *prove* the architecture every later slice (PSET/LINE/CIRCLE/PAINT/DRAW)
; rides on, before any feature does.
;
; WHY PAGE 0. This island is reached via subrom_call to SUBROM_IDX_GRAPHICS=8
; ($0028), which runs under the RAM interrupt trampoline (basic/subromcall.asm),
; so a tenant may EI and keep interrupts serviced through the paged-out BIOS. A
; long draw therefore does NOT starve H.TIMI/JIFFY — music keeps playing, exactly
; as it does on a real MSX (arc D1, docs/spec-basic-graphics.md §2). A page-0
; island has the BIOS switched out, so it CANNOT CALSLT WRTVRM — hence direct VDP
; port I/O (D2), which a pixel engine wants anyway (no CALSLT-per-byte).
;
; THE RACE IT CLOSES (D2/§3). Reading the VDP status port ($99), which the frame
; ISR does every VBLANK to ack the interrupt, RESETS the VDP address read/write
; latch flip-flop (published TMS9918A behaviour). If a VBLANK lands between the two
; $99 address-latch writes, the second write is taken as a fresh first byte → the
; address is wrong and the data byte lands in the wrong VRAM cell. gfx_vram_wr/rd
; therefore perform the whole address-setup + data transfer as ONE di-guarded unit
; (the same atomicity WRTVRM has), so no ISR can interleave the latch. The guard is
; a handful of T-states; the compute BETWEEN byte accesses stays fully interruptible.
;
; Clean-room: own-design. VDP ports + the status-read-resets-latch contract are the
; public TMS9918A hardware contract (called/observed, never a ROM disassembly —
; basic/PROVENANCE.md, [[no-reference-rom-disasm]]); the self-test, the guard
; discipline, and gfx_calc_addr are zerobas's own.

; --- G1 floor self-test VRAM window ----------------------------------------
; A block that is UNUSED by the display (and so never written by the cursor/ISR)
; in BOTH SCREEN 0 and SCREEN 1 — whichever the machine booted into — so a
; mismatch can only come from the latch race, never from a legitimate ISR VRAM
; write. SCREEN 0 uses $0000-$03BF (name) + $0800-$0FFF (font); SCREEN 1 uses
; $0000-$07FF (pattern) + $1800-$1AFF (name) + $2000-$27FF (colour). $2000-$3FFF
; is touched by neither's cursor/sprite path — safe headless scratch here.
GFX_ST_BASE     equ     $2000
GFX_ST_END      equ     $4000       ; one past the last cell (8 KB pass)

; ===========================================================================
; graphics_tenant — index-8 entry (SUBROM_IDX_GRAPHICS), selector-dispatched on
; GFX_OP (arc D5, the fatprim/dirverb pattern). Entered under DI by CALSLT.
;   GFX_OP = 0  -> graphics_selftest  (G1 floor gate; the floor probe sets it)
;          = 1  -> gfx_plot           (PSET/PRESET: one colour-clash RMW pixel)
;          = 2  -> gfx_point          (POINT: read one pixel's colour)
; The short pixel ops (1/2) never spin long enough for the EI-during-draw question
; to bite (arc §2), so they use the lean gfx_rd_raw/gfx_wr_raw (no per-access di/ei;
; the VDP fetch-window NOPs in gfx_rd_raw are the real correctness detail). Only the
; long self-test EI's and uses the di-guarded gfx_vram_wr/rd.
; ===========================================================================
graphics_tenant:
                ld      a,(GFX_OP)
                ; --- G6/D-G6-3: stamp the SHARED graphics attribute. Every graphics
                ; statement that resolves a colour leaves it in GFX_C, so stamping
                ; here covers PSET/PRESET/LINE/CIRCLE/PAINT in ONE place and costs the
                ; space-blocked resident nothing. Excluded: POINT (op 2) never sets a
                ; colour, so GFX_C is stale there; DRAW (op 6) owns ATRBYT itself (it
                ; READS it and writes only on `C n`, spec §6); op 0 is the floor probe.
                cp      2
                jr      z,gt_nostamp
                cp      6
                jr      z,gt_nostamp
                cp      7                   ; G7: sprites carry a PER-SPRITE colour that
                jr      nc,gt_nostamp       ; is measurably NOT ATRBYT (notes G1) -- ops
                                            ; 7/8 must not stamp it
                or      a
                jr      z,gt_nostamp
                push    af
                ld      a,(GFX_C)
                ld      (ATRBYT),a
                pop     af
gt_nostamp:
                dec     a
                jp      z,gfx_plot          ; GFX_OP == 1
                dec     a
                jp      z,gfx_point         ; GFX_OP == 2
                dec     a
                jp      z,gfx_line_op       ; GFX_OP == 3 (LINE / box -- G3)
                dec     a
                jp      z,gfx_circle_op     ; GFX_OP == 4 (CIRCLE -- G4)
                dec     a
                jp      z,gfx_paint_op      ; GFX_OP == 5 (PAINT -- G5)
                dec     a
                jp      z,gfx_draw_op       ; GFX_OP == 6 (DRAW -- G6)
                dec     a
                jp      z,gfx_spr_wpat      ; GFX_OP == 7 (SPRITE$(n)= pattern write -- G7)
                dec     a
                jp      z,gfx_spr_rpat      ; GFX_OP == 8 (SPRITE$(n) pattern read -- G7)
                dec     a
                jp      z,gfx_spr_attr      ; GFX_OP == 9 (PUT SPRITE attribute merge -- G7)
                dec     a
                jp      z,gfx_spr_xsave     ; GFX_OP == 10 (snapshot the attribute x bytes)
                dec     a
                jp      z,gfx_spr_xrest     ; GFX_OP == 11 (restore them after CHGMOD)
                dec     a
                jp      z,gfx_spr_size_apply ; GFX_OP == 12 (apply SCREEN's sprite size)
                dec     a
                jp      z,gfx_vdp_wr        ; GFX_OP == 13 (VDP(n) = v -- G8)
                dec     a
                jp      z,gfx_base_wr       ; GFX_OP == 14 (BASE(n) = v -- G8)
                ; GFX_OP == 0 (or any other value) -> the G1 floor self-test
                ; (falls through to graphics_selftest below).

; ===========================================================================
; graphics_selftest — GFX_OP=0, the interrupt-under-draw gate body (index 8).
; Entered under DI by CALSLT. Proves BOTH architectural properties in one run:
;   * interrupts are SERVICED while drawing under EI  -> JIFFY delta >= 1
;   * the di-guarded latch keeps every VRAM access correct under those interrupts
;     -> a full write-then-read-back of an 8 KB block has ZERO mismatches.
; Writes f(addr)=low(addr) XOR high(addr) to every cell, then reads every cell
; back and counts cells != f(addr). Both passes run with interrupts LIVE, so ~8
; VBLANKs fire during them; with the guard, all land correctly (BAD=0); with the
; guard stripped (pasmo --equ GFX_UNGUARDED=1, the §4 teeth check) the racing ISR
; corrupts the latch and BAD>0 — proving this gate can actually fail.
; Results: GFX_DJ = JIFFY delta, GFX_BAD = mismatch count (basic/sysvars.inc).
; ===========================================================================
graphics_selftest:
                ld      a,(JIFFY)           ; snapshot the frame counter (low byte)
                ld      (GFX_DJ),a          ; GFX_DJ temporarily holds J0
                ei                          ; interrupts ON: the ISR now reads $99 each VBLANK
                ; --- write pass: f(addr) to every cell in [BASE,END) ---
                ld      hl,GFX_ST_BASE
                ld      de,GFX_ST_END
gst_wr:
                ld      a,l
                xor     h                   ; A = f(addr) = low XOR high
                ld      c,a
                call    gfx_vram_wr         ; VRAM[HL] = C (di-guarded); HL/DE preserved
                inc     hl
                ld      a,h
                cp      d
                jr      nz,gst_wr
                ld      a,l
                cp      e
                jr      nz,gst_wr
                ; --- read-back pass: count cells that do NOT hold f(addr) ---
                ld      hl,GFX_ST_BASE
                ld      de,GFX_ST_END
                ld      b,0                 ; B = mismatch count (saturating)
gst_rd:
                call    gfx_vram_rd         ; A = VRAM[HL] (di-guarded); HL/DE/B preserved
                ld      c,a                 ; C = value read back
                ld      a,l
                xor     h                   ; A = expected f(addr)
                cp      c
                jr      z,gst_rd_next
                inc     b                   ; mismatch
                jr      nz,gst_rd_next
                dec     b                   ; saturate at 255 (never wraps to a false 0)
gst_rd_next:
                inc     hl
                ld      a,h
                cp      d
                jr      nz,gst_rd
                ld      a,l
                cp      e
                jr      nz,gst_rd
                di                          ; leave the EI region cleanly before returning
                ld      a,b
                ld      (GFX_BAD),a         ; publish the mismatch count
                ld      a,(JIFFY)           ; JIFFY after
                ld      hl,GFX_DJ
                sub     (hl)                ; delta = now - J0 (mod 256; >=1 iff serviced)
                ld      (GFX_DJ),a
                ret

; ===========================================================================
; gfx_vram_wr — write one byte to VRAM, di-guarded (the atomic latch unit).
;   in:  HL = VRAM address, C = data byte.   out: (VRAM[HL] = C).
;   clobbers A only; preserves HL / BC / DE.
; The whole address-setup + data write is one DI unit, so no ISR $99 status read
; can reset the latch mid-setup, and no ISR VRAM access can clobber the loaded
; address before the data byte lands.
; ===========================================================================
gfx_vram_wr:
    IF GFX_UNGUARDED = 0
                di
    ENDIF
                ld      a,l
                out     (VDP_ADDR),a        ; address low
                ld      a,h
                or      $40                 ; write-enable bit
                out     (VDP_ADDR),a        ; address high | $40
                ld      a,c
                out     (VDP_DATA),a        ; store (auto-increments the VDP pointer)
    IF GFX_UNGUARDED = 0
                ei
    ENDIF
                ret

; ===========================================================================
; gfx_vram_rd — read one byte from VRAM, di-guarded.
;   in:  HL = VRAM address.   out: A = data byte.
;   preserves HL / BC / DE.
; ===========================================================================
gfx_vram_rd:
    IF GFX_UNGUARDED = 0
                di
    ENDIF
                ld      a,l
                out     (VDP_ADDR),a        ; address low
                ld      a,h
                out     (VDP_ADDR),a        ; address high (NO $40 -> read mode)
    IF GFX_UNGUARDED = 0
                nop                         ; THE VDP FETCH WINDOW (see gfx_rd_raw's
                nop                         ; header): $98 is only valid once the VDP has
                nop                         ; fetched VRAM[addr] into its read-ahead latch,
                nop                         ; ~30 T after the address write. Without these
                nop                         ; the read returns the STALE previous byte --
                nop                         ; which G7's sprite block reads hit at once (a
                nop                         ; 4-byte attribute read came back ROTATED).
                nop                         ; Part of "the guard", so the teeth check
                nop                         ; (GFX_UNGUARDED=1) strips it too -- measured:
    ENDIF                                   ; with the settle present and only the DI
                                            ; stripped, the floor gate no longer fails, i.e.
                                            ; what it was really detecting all along was the
                                            ; MISSING FETCH WINDOW, not the latch race.
                                            ; [[vdp-direct-port-read-fetch-window]]
                in      a,(VDP_DATA)        ; fetch (auto-increments)
    IF GFX_UNGUARDED = 0
                ei
    ENDIF
                ret

; ===========================================================================
; gfx_calc_addr — SCREEN-2 pixel (x,y) -> pattern-plane VRAM byte address + mask.
;   in:  D = y (0..191), E = x (0..255).
;   out: HL = pattern byte address = (y>>3)*256 + (x>>3)*8 + (y&7)
;        C  = MSB-first bit mask = $80 >> (x&7).
;   Colour-plane byte is HL + GFX_COLOR_OFST (G2). Pure leaf (no ports, no RAM) —
;   host-unit-tested against the §11.2 pinned landings (tests/test_graphics.py).
;   clobbers A/B; preserves DE.
; ===========================================================================
gfx_calc_addr:
                ; --- mask = $80 >> (x & 7) ---
                ld      a,e
                and     $07
                jr      z,gca_mask_hi       ; x&7 = 0 -> mask = $80
                ld      b,a                 ; B = shift count 1..7
                ld      a,$80
gca_mask_lp:
                rrca                        ; $80>>1=$40, ... ; never wraps for count<=7
                djnz    gca_mask_lp
                jr      gca_mask_set
gca_mask_hi:
                ld      a,$80
gca_mask_set:
                ld      c,a                 ; C = bit mask
                ; --- addr low = (x & $F8) + (y & 7) ---   ((x>>3)*8 == x & $F8)
                ld      a,e
                and     $F8
                ld      l,a
                ld      a,d
                and     $07
                add     a,l                 ; <=248 + <=7 = <=255, no carry into H
                ld      l,a
                ; --- addr high = y >> 3 ---
                ld      a,d
                rrca
                rrca
                rrca
                and     $1F                 ; y<=191 -> y>>3 <= 23
                ld      h,a
                ret

; ===========================================================================
; gfx_wr_raw / gfx_rd_raw — one VRAM byte via direct ports for the SHORT G2 pixel
; ops. in gfx_wr_raw: HL=addr, C=data. gfx_rd_raw: HL=addr -> A=data. Clobbers A.
;
; NO per-access di/ei. The G1 self-test's gfx_vram_wr/rd guard EACH access because
; they run EI (to prove interrupts stay live); a SHORT PSET/POINT never needs that.
; PROVEN empirically (basic_probe_graphics.py differential): the ISR is NOT the
; hazard here -- a whole-op di made no difference. The real one is the VDP FETCH
; WINDOW below.
;
; THE VDP FETCH WINDOW (gfx_rd_raw). On the TMS9918 (and openMSX's cycle-accurate
; model) a VRAM read is: set the address (two $99 writes, high byte without $40),
; then read $98 -- but the byte is valid only AFTER the VDP has fetched VRAM[addr]
; into its read-ahead latch. Read $98 too soon and you get the STALE previous latch.
; The BIOS RDVRM gets the gap for free (SETRD's ei/ret + the call/ret framing, ~30
; T-states); our tight in-line read has ZERO gap, so the $98 read races the fetch.
; The symptom was maddening whack-a-mole: a plot's colour read (the 2nd of two
; back-to-back reads) intermittently returned the pattern byte, and which cases
; failed shifted with unrelated timing (a STEP-token parse upstream flipped it).
; The eight NOPs are that settle window (~32 T-states, matching RDVRM); the G2
; differential is byte-identical to the VG-8020 with them, and regressed without.
gfx_wr_raw:
                ld      a,l
                out     (VDP_ADDR),a        ; address low
                ld      a,h
                or      $40                 ; write-enable bit
                out     (VDP_ADDR),a        ; address high | $40
                ld      a,c
                out     (VDP_DATA),a        ; store (auto-increments)
                ret
gfx_rd_raw:
                ld      a,l
                out     (VDP_ADDR),a        ; address low
                ld      a,h
                out     (VDP_ADDR),a        ; address high (NO $40 -> read mode)
                nop                         ; VDP fetch window (~32 T; see above) --
                nop                         ; without it the read races the VDP's
                nop                         ; read-ahead fetch and returns a stale byte
                nop
                nop
                nop
                nop
                nop
                in      a,(VDP_DATA)        ; fetch (now VRAM[addr] is in the latch)
                ret

; ===========================================================================
; gfx_plot — GFX_OP=1: plot ONE SCREEN-2 pixel with the colour-clash RMW (§3).
; The resident stub has already range-checked (0..255 x 0..191) and marshalled
; the target into GXPOS/GYPOS (low byte = coord) and the resolved colour into
; GFX_C. Reads the pattern AND colour bytes FIRST (back-to-back, no interleaved
; write), applies the pinned clash rule (gfx_color_rmw), then writes. Publishes
; CLOC/CMASK (the drawn pixel's address + mask -- work-area faithful, §6). Runs
; fully DI (gfx_rd_raw/gfx_wr_raw); returns nothing.
; ===========================================================================
gfx_plot:
                ld      a,(GXPOS)           ; x (low byte; 0..255 guaranteed in-range)
                ld      e,a
                ld      a,(GYPOS)           ; y (low byte; 0..191)
                ld      d,a
                call    gfx_calc_addr       ; HL = pattern addr, C = mask (B clobbered)
                ld      (CLOC),hl           ; publish the computed pixel address
                ld      a,c
                ld      (CMASK),a           ; publish the mask
                call    gfx_rd_raw          ; A = current pattern byte (HL preserved)
                ld      e,a                 ; E = pattern byte (D=y no longer needed)
                ld      a,h                 ; colour addr = pattern addr + $2000
                add     a,$20               ; pattern high <= $17 -> no carry out
                ld      h,a
                call    gfx_rd_raw          ; A = current colour byte (cur); HL = colour addr
                ld      b,a                 ; B = cur colour byte
                ld      a,(GFX_C)           ; A = resolved plot colour c (0..15)
                call    gfx_color_rmw       ; CF=1 -> set (A=new colour); CF=0 -> clear
                jr      nc,gp_clear
                ; --- SET: write the new colour byte, then set the pattern bit ---
                ld      c,a                 ; C = new colour byte = (c<<4)|(cur&$0F)
                call    gfx_vram_wr         ; colour[HL] = C   (HL = colour addr)
                ld      a,h                 ; back to the pattern addr
                sub     $20
                ld      h,a
                ld      a,(CMASK)
                or      e                   ; pattern (E) |= mask
                ld      c,a
                jp      gfx_vram_wr         ; pattern[HL] = C ; ret
gp_clear:
                ; --- CLEAR: colour byte untouched, clear the pattern bit (§3 branch 3) ---
                ld      a,h                 ; HL is the colour addr -> back to pattern addr
                sub     $20
                ld      h,a
                ld      a,(CMASK)
                cpl                         ; A = ~mask
                and     e                   ; pattern (E) &= ~mask
                ld      c,a
                jp      gfx_vram_wr         ; pattern[HL] = C ; ret

; ===========================================================================
; gfx_point — GFX_OP=2: read one pixel's colour into GFX_RES (POINT). The resident
; stub has range-checked (off-screen -> -1 without calling us) and marshalled the
; target into GFX_PTX/GFX_PTY. Reads the pattern bit and the group colour byte and
; returns the fg nibble if the bit is set, else the bg nibble. Read-only: writes
; no work-area cell (POINT does not move the last-referenced point).
; ⚠️ D-GIRDOM: this arm used to read GXPOS/GYPOS, like GFX_OP=1 still does. It
; does not any more, and the difference is not cosmetic: GXPOS/GYPOS is
; BASIC-visible, so the resident write that fed this read was a MEASURABLE side
; effect of a function that both references keep read-only (rows w.pt.on /
; w.pt.step). GFX_OP=1 keeps GXPOS/GYPOS because PSET/PRESET move the work area
; anyway -- the cells are the marshalling AND the contract there.
; ===========================================================================
gfx_point:
                ld      a,(GFX_PTX)
                ld      e,a
                ld      a,(GFX_PTY)
                ld      d,a
                call    gfx_calc_addr       ; HL = pattern addr, C = mask
                call    gfx_rd_raw          ; A = pattern byte (HL/BC/DE preserved -> C=mask)
                ld      d,a                 ; D = pattern byte
                ld      e,c                 ; E = mask
                ld      a,h                 ; colour addr = pattern addr + $2000
                add     a,$20               ; pattern high <= $17, so +$20 never carries out
                ld      h,a
                call    gfx_rd_raw          ; A = colour byte (D/E preserved)
                ld      c,a                 ; C = colour byte
                ld      a,d                 ; A = pattern byte
                ld      b,e                 ; B = mask
                call    gfx_point_extract   ; A = pixel colour nibble
                ld      (GFX_RES),a
                ret

; ===========================================================================
; gfx_color_rmw — the SCREEN-2 colour-clash decision (pure leaf; §3/§11.3).
;   in:  A = plot colour c (0..15), B = current colour byte `cur`.
;   out: CF = 1 -> SET the pixel bit; A = new colour byte = (c<<4) | (cur & $0F).
;        CF = 0 -> CLEAR the pixel bit; colour byte left untouched.
; Rule: if c equals cur's low (bg) nibble -> the pixel reads as background, so
; CLEAR the bit and leave the colour byte alone; else SET the bit AND write the
; hi (fg) nibble = c, PRESERVING the lo (bg) nibble -- the 8-pixel colour clash
; (a later pixel in the group rewrites the shared fg nibble). PSET never writes
; the bg nibble. Host-unit-tested (tests/test_graphics.py). Clobbers A/B/C.
; ===========================================================================
gfx_color_rmw:
                ld      c,a                 ; C = c (plot colour)
                ld      a,b
                and     $0F                 ; A = bg nibble = cur & $0F
                cp      c
                jr      z,gcr_clear         ; c == bg -> clear the pixel, colour untouched
                ld      b,a                 ; B = bg nibble
                ld      a,c
                rlca
                rlca
                rlca
                rlca                        ; A = c << 4 (c<=15 -> hi nibble=c, lo=0)
                or      b                   ; A = (c<<4) | bg
                scf                         ; CF = 1 -> set the bit, write A as the colour
                ret
gcr_clear:
                or      a                   ; CF = 0 -> clear the bit; colour untouched
                ret

; ===========================================================================
; gfx_point_extract — read a pixel's colour from its pattern+colour bytes (pure
; leaf; POINT). in: A = pattern byte, B = mask, C = colour byte. out: A = the
; pixel's colour nibble -- the hi (fg) nibble if the pattern bit is set, else the
; lo (bg) nibble. Host-unit-tested. Clobbers A/flags; preserves BC/DE/HL.
; ===========================================================================
gfx_point_extract:
                and     b                   ; pattern & mask -> Z iff the bit is clear
                ld      a,c                 ; A = colour byte (flags from `and b` intact)
                jr      z,gpe_bg
                rrca                         ; bit set -> fg = hi nibble -> shift down
                rrca
                rrca
                rrca
gpe_bg:
                and     $0F                 ; low nibble (bg, or the shifted-down fg)
                ret

; ===========================================================================
; G3 -- LINE (+ ,B / ,BF box). GFX_OP=3, GFX_MODE selects segment/outline/fill.
; docs/spec-basic-graphics-g3.md. The FIRST long, EI-during-draw op (arc D1): the
; tenant EIs at the top so a long draw keeps H.TIMI/JIFFY alive (music plays), and
; drops to a BRIEF di ONLY around each pixel's read-modify-write (gfx_plot_cur).
;
; Rasteriser (own-design, host-fit to the VG-8020 -- spec §4.1): integer Bresenham,
; endpoints sorted so the MAJOR axis ascends (=> drawing is direction-independent,
; measured), err = dmaj>>1, minor step when err >= dmaj (then err -= dmaj). Runs over
; the TRUE int16 endpoints and plots only in-range pixels -- that per-pixel mask IS
; the clip (spec §3.4/§4.4): off-screen portions silently produce no pixel, on-screen
; portions draw. The pure stepping (gfx_bres_init/gfx_bres_next, RAM state only, no
; ports) is host-unit-tested against the captured reference bitmaps (tests/test_
; graphics.py) -- the crux-1 de-risker, emulator-free. gfx_calc_addr / gfx_color_rmw
; are reused verbatim from G1/G2; the per-pixel reads reuse gfx_rd_raw for its VDP
; fetch-window settle ([[vdp-direct-port-read-fetch-window]]) -- now INSIDE the di
; bracket, since with interrupts live both the latch-reset race and the read-ahead
; race apply per pixel.
; ===========================================================================
gfx_line_op:
                ; --- work area: GXPOS/GYPOS + GRPACX/GRPACY = p2, the segment's
                ; endpoint (spec G3 §11.5). Moved here from the resident elg_draw
                ; by G8's space carve. Order matters for the CIRCLE spokes, which
                ; call this op internally: gco_done draws the spokes FIRST and
                ; writes the circle's own work-area values AFTER, so a spoke's
                ; endpoint never survives as the last-referenced point.
                ld      hl,(GFX_X2)
                ld      (GXPOS),hl
                ld      (GRPACX),hl
                ld      hl,(GFX_Y2)
                ld      (GYPOS),hl
                ld      (GRPACY),hl
                ei                          ; interrupts LIVE for the (possibly long) draw
                ld      a,(GFX_MODE)
                or      a
                jr      z,glo_seg           ; mode 0 -> one segment
                dec     a
                jr      z,glo_box           ; mode 1 -> box outline
                call    gfx_box_fill        ; mode 2 -> box fill
                jr      glo_done
glo_seg:
                call    gfx_draw_seg
                jr      glo_done
glo_box:
                call    gfx_box_outline
glo_done:
                di                          ; leave the EI region before returning via CALSLT
                ret

; ---------------------------------------------------------------------------
; gfx_draw_seg -- rasterise+plot the segment currently in GFX_X1/Y1/GFX_X2/Y2.
; Plots dmaj+1 pixels (start + one per major step). Assumes interrupts are already
; EI (caller = gfx_line_op / the box helpers); each pixel's VDP RMW is di-guarded
; inside gfx_plot_cur. Clobbers everything.
; ---------------------------------------------------------------------------
gfx_draw_seg:
                call    gfx_bres_init       ; state <- endpoints; CX/CY = start; CNT = dmaj
gds_loop:
                call    gfx_plot_cur        ; plot (CX,CY) if on-screen (di-guarded RMW)
                ld      hl,(GFX_CNT)
                ld      a,h
                or      l
                ret     z                   ; no steps left -> the last pixel is drawn
                dec     hl
                ld      (GFX_CNT),hl
                call    gfx_bres_next        ; advance one major step
                jr      gds_loop

; ---------------------------------------------------------------------------
; gfx_plot_cur -- plot the pixel at (GFX_CX,GFX_CY) IF it is on-screen (the clip,
; spec §4.2), read-modify-write with the colour clash. GFX_C = colour. Interrupts
; are EI on entry; we di ONLY around the VDP access (arc §2). Off-screen -> no-op.
; ---------------------------------------------------------------------------
gfx_plot_cur:
                ld      hl,(GFX_CX)
                ld      a,h
                or      a
                ret     nz                  ; x high byte != 0 -> x<0 or x>255 -> clip (skip)
                ld      hl,(GFX_CY)
                ld      a,h
                or      a
                ret     nz                  ; y high byte != 0 -> clip
                ld      a,l
                cp      192
                ret     nc                  ; y >= 192 -> clip
                ; --- on-screen: brief di around the read-modify-write ---
                di
                ld      a,(GFX_CY)
                ld      d,a                 ; D = y (0..191)
                ld      a,(GFX_CX)
                ld      e,a                 ; E = x (0..255)
                call    gfx_rmw_at
                ei
                ret

; ---------------------------------------------------------------------------
; gfx_rmw_at -- plot one pixel with the colour-clash RMW. in: D=y, E=x (both in
; range, caller-checked), GFX_C = colour 0..15. Caller HOLDS DI. Uses gfx_rd_raw
; (VDP fetch-window settle) for reads and gfx_wr_raw for writes -- so the di bracket
; is the caller's alone (no premature ei). Updates CLOC/CMASK. Clobbers A/BC/HL.
; This is G2 gfx_plot's body with raw writes; G2's gfx_plot is left untouched.
; ---------------------------------------------------------------------------
gfx_rmw_at:
                call    gfx_calc_addr       ; HL = pattern addr, C = mask (B clobbered)
                ld      (CLOC),hl
                ld      a,c
                ld      (CMASK),a
                call    gfx_rd_raw          ; A = pattern byte (HL preserved)
                ld      e,a                 ; E = pattern byte
                ld      a,h                 ; colour addr = pattern addr + $2000
                add     a,$20               ; pattern high <= $17 -> no carry out
                ld      h,a
                call    gfx_rd_raw          ; A = colour byte (HL = colour addr)
                ld      b,a
                ld      a,(GFX_C)
                call    gfx_color_rmw       ; CF=1 set (A=new colour) / CF=0 clear
                jr      nc,gra_clear
                ld      c,a                 ; new colour byte
                call    gfx_wr_raw          ; colour[HL] = C
                ld      a,h
                sub     $20                 ; back to pattern addr
                ld      h,a
                ld      a,(CMASK)
                or      e                   ; pattern |= mask
                ld      c,a
                jp      gfx_wr_raw          ; pattern[HL] = C ; ret
gra_clear:
                ld      a,h
                sub     $20
                ld      h,a
                ld      a,(CMASK)
                cpl                         ; ~mask
                and     e                   ; pattern &= ~mask
                ld      c,a
                jp      gfx_wr_raw

; ---------------------------------------------------------------------------
; gfx_bres_init -- set up Bresenham state from GFX_X1/Y1/GFX_X2/Y2 (spec §4.1).
; Sorts so the MAJOR axis ascends (direction independence). Sets GFX_CX/CY = the
; start (min-major) point, GFX_DMAJ/DMIN, GFX_ERR = DMAJ>>1, GFX_CNT = DMAJ,
; GFX_STEEP (0 = x-major, 1 = y-major), GFX_SMIN (minor step $0001/$FFFF).
; Pure (RAM only, no ports) -> host-unit-testable. Clobbers A/BC/DE/HL.
; ---------------------------------------------------------------------------
gfx_bres_init:
                ld      hl,(GFX_X2)
                ld      de,(GFX_X1)
                or      a
                sbc     hl,de               ; HL = x2 - x1 (signed)
                call    gfx_abs16           ; HL = |dx|, A = sign(dx) ($01/$FF)
                ld      (GFX_DMAJ),hl       ; provisional adx
                ld      (GFX_SDX),a
                ld      hl,(GFX_Y2)
                ld      de,(GFX_Y1)
                or      a
                sbc     hl,de               ; HL = y2 - y1
                call    gfx_abs16           ; HL = |dy|, A = sign(dy)
                ld      (GFX_DMIN),hl       ; provisional ady
                ld      (GFX_SDY),a
                ; --- steep = ady > adx ? ---
                ld      hl,(GFX_DMIN)       ; ady
                ld      de,(GFX_DMAJ)       ; adx
                or      a
                sbc     hl,de               ; ady - adx
                jr      c,gbi_shallow       ; ady < adx -> x-major
                ld      a,h
                or      l
                jr      z,gbi_shallow       ; ady == adx -> x-major (45 deg, measured)
                ; --- steep (y-major): DMAJ=ady, DMIN=adx (swap) ---
                ld      a,1
                ld      (GFX_STEEP),a
                ld      hl,(GFX_DMAJ)
                ld      bc,(GFX_DMIN)
                ld      (GFX_DMIN),hl       ; DMIN = adx
                ld      (GFX_DMAJ),bc       ; DMAJ = ady
                ld      a,(GFX_SDY)
                cp      $01
                jr      nz,gbi_st_p2        ; dy < 0 -> start p2, SMIN = -sign(dx)
                call    gbi_start_p1
                ld      a,(GFX_SDX)
                call    gbi_smin
                jr      gbi_fin
gbi_st_p2:
                call    gbi_start_p2
                ld      a,(GFX_SDX)
                xor     $FE                 ; flip sign byte: $01<->$FF
                call    gbi_smin
                jr      gbi_fin
gbi_shallow:
                xor     a
                ld      (GFX_STEEP),a       ; x-major; DMAJ=adx, DMIN=ady already
                ld      a,(GFX_SDX)
                cp      $01
                jr      nz,gbi_sh_p2        ; dx < 0 -> start p2, SMIN = -sign(dy)
                call    gbi_start_p1
                ld      a,(GFX_SDY)
                call    gbi_smin
                jr      gbi_fin
gbi_sh_p2:
                call    gbi_start_p2
                ld      a,(GFX_SDY)
                xor     $FE
                call    gbi_smin
gbi_fin:
                ld      hl,(GFX_DMAJ)
                ld      (GFX_CNT),hl        ; CNT = dmaj (major steps after the start)
                srl     h
                rr      l                   ; HL = dmaj >> 1
                ld      (GFX_ERR),hl
                ret

; start-point setters + minor-sign helper (used by gfx_bres_init)
gbi_start_p1:
                ld      hl,(GFX_X1)
                ld      (GFX_CX),hl
                ld      hl,(GFX_Y1)
                ld      (GFX_CY),hl
                ret
gbi_start_p2:
                ld      hl,(GFX_X2)
                ld      (GFX_CX),hl
                ld      hl,(GFX_Y2)
                ld      (GFX_CY),hl
                ret
; gbi_smin -- A = $01 (>=0) or $FF (<0) -> GFX_SMIN = $0001 / $FFFF.
gbi_smin:
                cp      $01
                jr      z,gbi_smin_pos
                ld      hl,$FFFF
                ld      (GFX_SMIN),hl
                ret
gbi_smin_pos:
                ld      hl,$0001
                ld      (GFX_SMIN),hl
                ret

; ---------------------------------------------------------------------------
; gfx_bres_next -- advance the Bresenham state one MAJOR step (spec §4.1). Major
; coordinate += 1 (sorted ascending); err += dmin; if err >= dmaj: minor += SMIN,
; err -= dmaj. err stays in [0,dmaj) via a carry-aware compare/subtract, so it is
; correct for full 16-bit deltas (the transient err+dmin can be 17-bit). Pure (RAM
; only) -> host-testable. Clobbers A/BC/DE/HL.
; ---------------------------------------------------------------------------
gfx_bres_next:
                ; --- major step: STEEP ? CY++ : CX++ ---
                ld      a,(GFX_STEEP)
                or      a
                jr      nz,gbn_major_y
                ld      hl,(GFX_CX)
                inc     hl
                ld      (GFX_CX),hl
                jr      gbn_err
gbn_major_y:
                ld      hl,(GFX_CY)
                inc     hl
                ld      (GFX_CY),hl
gbn_err:
                ; --- err += dmin ; carry (bit 16) means definitely >= dmaj ---
                ld      hl,(GFX_ERR)
                ld      de,(GFX_DMIN)
                add     hl,de               ; HL = err+dmin ; CF = 17th bit
                ld      de,(GFX_DMAJ)
                jr      c,gbn_step          ; overflow past 65535 -> >= dmaj -> step
                or      a
                sbc     hl,de               ; HL = (err+dmin) - dmaj ; CF=1 iff < dmaj (borrow)
                jr      nc,gbn_step_stored  ; no borrow -> HL is the new err in [0,dmaj); step
                add     hl,de               ; borrow: restore err+dmin, NO minor step
                ld      (GFX_ERR),hl
                ret
gbn_step:
                or      a
                sbc     hl,de               ; HL = (65536+HL) - dmaj = new err (borrow expected)
gbn_step_stored:
                ld      (GFX_ERR),hl
                ; --- minor step: STEEP ? CX += SMIN : CY += SMIN ---
                ld      de,(GFX_SMIN)
                ld      a,(GFX_STEEP)
                or      a
                jr      nz,gbn_minor_x
                ld      hl,(GFX_CY)
                add     hl,de
                ld      (GFX_CY),hl
                ret
gbn_minor_x:
                ld      hl,(GFX_CX)
                add     hl,de
                ld      (GFX_CX),hl
                ret

; ---------------------------------------------------------------------------
; gfx_abs16 -- HL = |HL| (signed 16-bit). Returns A = $01 if original HL >= 0,
; else $FF. Clobbers A/flags; DE preserved. Pure leaf (host-testable).
; ---------------------------------------------------------------------------
gfx_abs16:
                bit     7,h
                jr      z,gab_pos
                xor     a
                sub     l
                ld      l,a
                sbc     a,a                 ; A = 0 - borrow = $FF if borrow else $00
                sub     h                   ; A = (0 or -1) - h ...
                ld      h,a                 ; HL = 0 - HL (two's complement negate)
                ld      a,$FF
                ret
gab_pos:
                ld      a,$01
                ret

; ---------------------------------------------------------------------------
; gfx_box_outline -- ,B: the four inclusive edges of the rectangle whose corners
; are GFX_X1/Y1 and GFX_X2/Y2 (spec §5). Each edge is a segment through gfx_draw_seg
; (axis-aligned => dmin=0). Corners are stashed first because gfx_draw_seg consumes
; GFX_X1..Y2 for each edge. Interrupts already EI (caller). Clobbers everything.
; ---------------------------------------------------------------------------
gfx_box_outline:
                call    gfx_box_stash       ; TX1/TY1/TX2/TY2 = the two corners
                ; top edge: (TX1,TY1)-(TX2,TY1)
                ld      hl,(GFX_TX1)
                ld      (GFX_X1),hl
                ld      hl,(GFX_TY1)
                ld      (GFX_Y1),hl
                ld      hl,(GFX_TX2)
                ld      (GFX_X2),hl
                ld      hl,(GFX_TY1)
                ld      (GFX_Y2),hl
                call    gfx_draw_seg
                ; bottom edge: (TX1,TY2)-(TX2,TY2)
                ld      hl,(GFX_TX1)
                ld      (GFX_X1),hl
                ld      hl,(GFX_TY2)
                ld      (GFX_Y1),hl
                ld      hl,(GFX_TX2)
                ld      (GFX_X2),hl
                ld      hl,(GFX_TY2)
                ld      (GFX_Y2),hl
                call    gfx_draw_seg
                ; left edge: (TX1,TY1)-(TX1,TY2)
                ld      hl,(GFX_TX1)
                ld      (GFX_X1),hl
                ld      (GFX_X2),hl
                ld      hl,(GFX_TY1)
                ld      (GFX_Y1),hl
                ld      hl,(GFX_TY2)
                ld      (GFX_Y2),hl
                call    gfx_draw_seg
                ; right edge: (TX2,TY1)-(TX2,TY2)
                ld      hl,(GFX_TX2)
                ld      (GFX_X1),hl
                ld      (GFX_X2),hl
                ld      hl,(GFX_TY1)
                ld      (GFX_Y1),hl
                ld      hl,(GFX_TY2)
                ld      (GFX_Y2),hl
                jp      gfx_draw_seg

; ---------------------------------------------------------------------------
; gfx_box_fill -- ,BF: solid rectangle GFX_X1/Y1..GFX_X2/Y2 as horizontal scanline
; segments (spec §5). Iterates y from TY1 toward TY2 by +-1 (draw order is
; irrelevant for a solid fill), one gfx_draw_seg per row. Clobbers everything.
; ---------------------------------------------------------------------------
gfx_box_fill:
                call    gfx_box_stash
                ; X extent is constant across rows: X1=TX1, X2=TX2
                ld      hl,(GFX_TX1)
                ld      (GFX_X1),hl
                ld      hl,(GFX_TX2)
                ld      (GFX_X2),hl
                ; row step = sign(TY2-TY1) ; count = |TY2-TY1| + 1
                ld      hl,(GFX_TY2)
                ld      de,(GFX_TY1)
                or      a
                sbc     hl,de
                call    gfx_abs16           ; HL = |dy|, A = sign
                inc     hl
                ld      (GFX_FILLCNT),hl    ; scanline count
                cp      $01
                jr      z,gbf_ystep_pos
                ld      hl,$FFFF
                jr      gbf_ystep_set
gbf_ystep_pos:
                ld      hl,$0001
gbf_ystep_set:
                ld      (GFX_YSTEP),hl
                ld      hl,(GFX_TY1)
                ld      (GFX_Y1),hl         ; first row = TY1
gbf_loop:
                ld      hl,(GFX_Y1)
                ld      (GFX_Y2),hl         ; horizontal segment: Y2 = Y1
                call    gfx_draw_seg
                ld      hl,(GFX_FILLCNT)
                dec     hl
                ld      (GFX_FILLCNT),hl
                ld      a,h
                or      l
                ret     z
                ld      hl,(GFX_Y1)
                ld      de,(GFX_YSTEP)
                add     hl,de
                ld      (GFX_Y1),hl
                jr      gbf_loop

; gfx_box_stash -- copy the two corners GFX_X1/Y1/X2/Y2 into GFX_TX1/TY1/TX2/TY2.
gfx_box_stash:
                ld      hl,(GFX_X1)
                ld      (GFX_TX1),hl
                ld      hl,(GFX_Y1)
                ld      (GFX_TY1),hl
                ld      hl,(GFX_X2)
                ld      (GFX_TX2),hl
                ld      hl,(GFX_Y2)
                ld      (GFX_TY2),hl
                ret

; ===========================================================================
; G4 -- CIRCLE (+ ellipse aspect + start/end-angle arcs + negative-angle
; spokes). GFX_OP=4. docs/spec-basic-graphics-g4.md. Reuses G3's EI-between-
; pixels / DI-per-pixel gfx_plot_cur VERBATIM (spec §2) -- the only new tenant
; code is the midpoint-circle octant generator (spec §4.1), the per-point 8.8
; minor scale (§4.2), and the integer cross-product arc mask (§5.2). Spokes
; are NOT tenant code at all: the resident marshals a separate GFX_OP=3 line
; call (spec §5.3), reusing the landed G3 op.
;
; Own-design integer midpoint circle (host-fit against 6 captured VG-8020
; circles, scratchpad/g4_circle_fit.py -- spec §4.1):
;   x=0, y=r, d=1-r
;   while x<=y: emit the 8 mirrored octant points; if d<0: d+=2x+3
;               else: d+=2(x-y)+5, y--; x++
; State lives in GFX_QX/QY/QD (own cells, distinct from G3's GFX_CX/CY --
; those are reserved for the FINAL absolute screen point fed to gfx_plot_cur,
; per spec §6 "plot scratch ... reuse G3 GFX_CX/CY for the plotted pixel").
;
; Per-point minor scale (§4.2): the resident resolves aspect into GFX_ASPMAJ
; (which raw offset is the SCALED one -- y if x-major, x if y-major) and an
; 8.8 fixed-point GFX_ASPS (256 = no scale). The tenant applies
; off' = sign(off)*((|off|*ASPS+128)>>8) to whichever offset GFX_ASPMAJ
; selects, for EVERY mirrored point (gfx_circ_scale).
;
; Arc mask (D-ARCMASK, 2026-08-17, docs/arcmask-msx1-characterization.md):
; when GFX_ARCF=1, a point is kept iff its (octant, in-octant step index)
; pair lies in the CLOSED cyclic interval between the two marshalled
; boundaries -- the STEP-INDEX WEDGE (gfx_circ_keep). The octant is STATIC
; per mirror position (gco_emit8 passes it as a literal), the step index is
; the loop's own qx, and the test runs on the RAW point BEFORE the minor
; scale -- measured: the reference masks pre-scale (the r=700 ASPS=35 arc row
; is byte-exact only that way). Boundaries, wrap flag and pending-spoke
; endpoint vectors are computed once per CIRCLE by gfx_circ_wedge_prep from
; the (oct_raw, u14) records sub/circleparse.asm marshals. This RETIRES the
; 2026-07-21 cross-product wedge (gfx_cross_ge0, the QTAB boundary vectors,
; GFX_ARCBIG) -- see the section header above gwp_pos for the measurement
; that refuted it and the rule that replaced it.
;
; 🔴 BOUNDED-DOMAIN NOTE -- REWRITTEN BY D-CIRCDOM, WHICH MEASURED IT FALSE.
; It used to read "guaranteed for the blessed r<=255 domain", and there is no
; r<=255 anywhere in the tree. The radius domain is enforced at exactly two
; sites and it is 0..32767:
;
;   UPPER  basic/graphics.asm cp_req_int -> gfx_eval_int16   ERR 6 for |r|>=32768
;   LOWER  sub/circleparse.asm cpt_after_r `jp m,cpt_err5`   ERR 5 for r<0
;
; D-CIRCDOM also measured a PRODUCT precondition -- |v|*ASPS <= 65535 -- and
; found it FALSE and reachable, because the multiply kept only the low 16 bits.
;
; 🔴 THAT HALF IS FIXED (D-CIRCOVF, docs/circovf-msx1-oracle.md). There is now
; no precondition on the product at all: gfx_circ_scale carries it at full
; width through gfx_mul16r. (D-CIRCOVF also widened gfx_cross_ge0 to 32 bits
; for the same reason; D-ARCMASK then retired that routine outright -- the
; arc mask no longer multiplies at all.) The whole 0..32767 radius domain is
; honest.
;
; THE ORACLE THAT WAS MISSING, AND WHY IT WAS MISSING. D-CIRCDOM's six DIFF rows
; all have the REFERENCE drawing 0 px on screen -- they say "zerobas paints where
; the reference paints nothing" and cannot say what right looks like. That is a
; theorem, not a gap in the corpus: an overflowing point has a scaled minor
; offset >= 256 and the screen is 192 tall, so no overflowing point can be on
; screen WHILE THE CENTRE IS -- and every CIRCLE row in the tree's history is
; centred at (128,96). Moving the centre off screen along the MINOR axis puts
; the overflowing part of the figure on the visible band, and the reference then
; draws it. Measured, whole pattern plane, VG-8020 vs zerobas-before:
;
;   CIRCLE(128,445),284         ref 256 px 05f66505   zerobas-before   9 px
;   CIRCLE(128,445),300         ref 256 px 328ae002   zerobas-before   0 px
;   CIRCLE(128,448),528,,,,.5   ref 253 px 2f2dda11   zerobas-before   0 px
;   CIRCLE(262,96),528,,,,2     ref  71 px 345fa7bd   zerobas-before 121 px
;   CIRCLE(128,445),255         ref  55 px 72c98b29   CONTROL, identical
;   CIRCLE(128,346),500,,,,.5   ref 256 px 722d4c19   CONTROL, identical
;
; All four DIFF rows match a FULL-WIDTH, ROUND-HALF-UP product byte for byte; a
; saturating model and the wrapping model are both refuted at sha1 level. Note
; the fourth row: zerobas painted MORE than the reference there, the opposite
; direction to all six of D-CIRCDOM's. Never crashes, before or after.
;
; ⚠️ D-CIRCDOM already corrected the old note's blast radius (it said a large
; radius "may mis-rasterise the ARC MASK"; gfx_circ_scale runs on EVERY point of
; EVERY circle). That correction stands.
;
; 🔴 AND THE `$8000` COUPLING THIS HEADER USED TO WARN ABOUT DOES NOT BIND. It
; said fixing the overflow would make `$8000` reachable at gfx_circ_scale's
; re-negate. The arithmetic is right and the conclusion is design-dependent:
; ASPS=256 is the only value that reaches 32768 and the only value for which the
; scale is the IDENTITY, so four bytes of branch cap the result at 32767 there
; and 32639 on the multiply arm. What DID become reachable was gfx_cross_ge0's
; products -- widened by D-CIRCOVF, then retired with the whole routine by
; D-ARCMASK (the step-index mask has no products).
; ===========================================================================
gfx_circle_op:
                ei                          ; interrupts LIVE for the (possibly long) draw
                ld      a,(GFX_ARCF)
                or      a
                jr      z,gco_noarc         ; full circle/ellipse -- wedge unused
                call    gfx_circ_wedge_prep ; M + S/E wedge + spoke vectors
                                            ; from GFX_SOCT/EOCT (D-ARCMASK)
gco_noarc:
                call    gfx_circ_init
gco_loop:
                ; while QX <= QY -- SIGNED compare. r=0 (and the last step of any
                ; radius) can drive QY to -1, which an UNSIGNED cf-based test reads
                ; as 65535 (>= QX), never terminating -- found live via r_zero
                ; drawing extra garbage octant points (see the G4 slice report).
                ; sbc hl,de sets S = bit15 of the 16-bit result (unlike add hl,de,
                ; sbc DOES affect S/Z), so "QY-QX < 0" (QX>QY) is a plain `jp m`.
                ld      hl,(GFX_QY)
                ld      de,(GFX_QX)
                or      a
                sbc     hl,de               ; HL = QY - QX (signed)
                jp      m,gco_done          ; QY < QX -> done
                call    gco_emit8
                call    gfx_circ_next
                jr      gco_loop
gco_done:
                ; --- deferred spokes + work area (G8 space carve, 2026-07-22) ---
                ; These used to be the resident circ_draw's tail: ~120 B of pure
                ; marshalling whose only real work was two more subrom_calls back
                ; into THIS island. Folding them in makes each of those a plain
                ; internal `call gfx_line_op` and funds G8's resident half without
                ; evicting anything outside the graphics arc
                ; (docs/spec-basic-graphics-g8.md §6). Order is load-bearing: the
                ; spokes are drawn AFTER the arc (§9 G4-spoke), and the work-area
                ; writes keep G4's signed-off GXPOS=r / GYPOS=cy residue quirk.
                ld      a,(GFX_SNEG)
                or      a
                call    nz,gco_spoke_s
                ld      a,(GFX_ENEG)
                or      a
                call    nz,gco_spoke_e
                ld      hl,(GFX_CXC)
                ld      (GRPACX),hl
                ld      hl,(GFX_CYC)
                ld      (GRPACY),hl
                ld      hl,(GFX_R)
                ld      (GXPOS),hl          ; quirk: GXPOS = r
                ld      hl,(GFX_CYC)
                ld      (GYPOS),hl          ; quirk: GYPOS = cy
                di                          ; leave the EI region before returning via CALSLT
                ret

; --- gco_spoke_s / gco_spoke_e / gco_spoke: a radius spoke ------------------
; A negative start/end angle asks for a radius line from the centre out along
; that boundary vector (spec G4 §5.3). IN (gco_spoke): HL = the vector's base
; cell (X at +0, Y at +2). Runs the island's own line op directly -- no CALSLT.
gco_spoke_s:
                ld      hl,GFX_SVX
                jr      gco_spoke
gco_spoke_e:
                ld      hl,GFX_EVX
gco_spoke:
                push    hl
                ld      hl,(GFX_CXC)
                ld      (GFX_X1),hl
                ld      hl,(GFX_CYC)
                ld      (GFX_Y1),hl
                pop     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = vector X
                inc     hl
                push    hl                  ; stash the Y-cell address
                ld      hl,(GFX_CXC)
                add     hl,de
                ld      (GFX_X2),hl
                pop     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = vector Y
                ld      hl,(GFX_CYC)
                add     hl,de
                ld      (GFX_Y2),hl
                xor     a
                ld      (GFX_MODE),a        ; segment, not a box
                jp      gfx_line_op         ; tail call: its ret serves ours

; ===========================================================================
; G4 arc boundary -- D-ARCMASK STEP-INDEX WEDGE (2026-08-17). Replaces the
; 2026-07-21 trig-free QTAB boundary-VECTOR design and its cross-product mask
; (docs/arcmask-msx1-characterization.md).
;
; The retired design computed S/E as rounded exact rays (round(r*|cos|),
; -round(r*|sin|)) and kept a point iff it lay in the cross-product wedge.
; Its "host-fit ALL MATCH" evidence was real and its corpus could not see the
; question: radii 4..20, every arc row r=15, where the divergence is 0.5 px.
; Measured on 54 whole reference planes at radii to 700, the exact-ray rule
; reproduces 2-4; the rule below reproduces 53 (the 54th is the spoke-line
; row, filed separately). With o = floor(theta/(pi/4)) and u the fraction
; into that octant, the reference's boundary is the octant loop's STEP INDEX
; distributed LINEARLY over the angle:
;
;     M   = floor(r/sqrt(2))     the octant's top step index
;     pos = floor(u*M)           position along the octant, always
;     k   = pos                  in an EVEN octant (step rises with theta)
;     k   = M - pos              in an ODD octant  (step falls with theta)
;
; both boundaries INCLUSIVE, and the angle marshalled at SINGLE precision
; (sub/circleparse.asm cpt_boundary_prep). Every arithmetic choice below was
; simulated at width against the banked planes before this asm existed
; (scratchpad/arcmask_asmsim2.py) -- the circovf_asmsim discipline.
; ===========================================================================

; ---------------------------------------------------------------------------
; gwp_pos -- IN: HL = u14 (0..16383). OUT: HL = (u14*M)>>14, 0..M-1.
; Uses GFX_M. Clobbers A, BC, DE.
; ---------------------------------------------------------------------------
gwp_pos:
                ld      de,(GFX_M)
                call    gfx_mul16u32        ; DE:HL = u14*M (<= 16383*23169 < 2^29)
                ld      a,h                 ; >>14 == (high<<2) | (H>>6)
                rlca
                rlca
                and     3
                ex      de,hl               ; HL = high word (<= 5791)
                add     hl,hl
                add     hl,hl               ; HL = high<<2
                ld      e,a
                ld      d,0
                add     hl,de
                ret

; ---------------------------------------------------------------------------
; gfx_circ_wedge_prep -- once per arc CIRCLE, BEFORE the octant loop:
;   GFX_M      = floor(r/sqrt(2))
;   GFX_WS_O/P = start boundary (octant, pos); GFX_WE_O/P = end boundary
;   GFX_WRAPF  = pair S > pair E lexicographically (the wedge crosses 0)
;   GFX_FULLW  = pairs equal but the RAW (oct,u14) records differ -- a
;                near-2*pi sweep, keep everything (the old ARCBIG wrap case)
;   GFX_SVX/EVX = pending spokes' endpoint vectors: the OCTANT POINT at the
;                boundary, minor-scaled. Measured (G4-arcbnd round 3, banked
;                since July, read by D-ARCMASK): the reference's spoke at
;                -0.01 lands on the octant point (15,0), NOT on the retired
;                QTAB vector's nudged (15,-1).
; Clobbers everything incl. GFX_QX/QY/QD (gfx_circle_op re-inits after) and
; GFX_PX/PY/GFX_CS_AX as walk scratch (dead until the draw starts).
; ---------------------------------------------------------------------------
gfx_circ_wedge_prep:
                ; M = floor(r/sqrt2): candidate (r*46341)>>16, then ONE floor
                ; correction -- 46341/65536 > 1/sqrt2, so the candidate only
                ; ever OVERSHOOTS, by at most 1; it is wrong on 410 of the
                ; 32768 radii (arcmask_asmsim2.py, exhaustive), and M is right
                ; iff 2*M*M <= r*r (both fit 32 bits).
                ld      hl,(GFX_R)
                ld      de,46341
                call    gfx_mul16u32        ; DE:HL = r*46341
                ex      de,hl               ; HL = candidate M = bits 16..31
                ld      (GFX_M),hl
                ld      d,h
                ld      e,l
                call    gfx_mul16u32        ; DE:HL = M*M
                add     hl,hl
                rl      e
                rl      d                   ; DE:HL = 2*M*M (< 2^31, no carry out)
                ld      (GFX_CS_M1),hl
                ld      (GFX_CS_M1+2),de
                ld      hl,(GFX_R)
                ld      d,h
                ld      e,l
                call    gfx_mul16u32        ; DE:HL = r*r
                ld      (GFX_CS_M2),hl
                ld      (GFX_CS_M2+2),de
                ld      hl,GFX_CS_M2
                ld      de,GFX_CS_M1
                call    gfx_cmp32           ; CF=1 iff r*r < 2*M*M -> overshoot
                jr      nc,gwp_mok
                ld      hl,(GFX_M)
                dec     hl
                ld      (GFX_M),hl
gwp_mok:
                ; --- the two wedge boundaries -------------------------------
                ld      hl,(GFX_SU14)
                call    gwp_pos
                ld      (GFX_WS_P),hl
                ld      a,(GFX_SOCT)
                and     7
                ld      (GFX_WS_O),a
                ld      hl,(GFX_EU14)
                call    gwp_pos
                ld      (GFX_WE_P),hl
                ld      a,(GFX_EOCT)
                and     7
                ld      (GFX_WE_O),a
                ; --- WRAPF / FULLW ------------------------------------------
                xor     a
                ld      (GFX_WRAPF),a
                ld      (GFX_FULLW),a
                ld      a,(GFX_WE_O)
                ld      b,a
                ld      a,(GFX_WS_O)
                cp      b                   ; OS vs OE
                jr      c,gwp_spokes        ; OS < OE -> plain wedge
                jr      nz,gwp_wrap         ; OS > OE -> wraps 0
                ld      hl,(GFX_WE_P)
                ld      de,(GFX_WS_P)
                or      a
                sbc     hl,de               ; PE - PS
                jr      c,gwp_wrap          ; PE < PS -> wraps 0
                ld      a,h
                or      l
                jr      nz,gwp_spokes       ; PE > PS -> plain wedge
                ; pairs EQUAL: FULLW iff the RAW records differ (near-2*pi)
                ld      hl,GFX_SOCT
                ld      de,GFX_EOCT
                ld      b,4
gwp_raw:
                ld      a,(de)
                cp      (hl)
                jr      nz,gwp_full
                inc     hl
                inc     de
                djnz    gwp_raw
                jr      gwp_spokes          ; raw-identical -> zero-width wedge
gwp_full:
                ld      a,1
                ld      (GFX_FULLW),a
                jr      gwp_spokes
gwp_wrap:
                ld      a,1
                ld      (GFX_WRAPF),a
gwp_spokes:
                ; --- pending spokes: endpoint := octant point at boundary ---
                ld      a,(GFX_SNEG)
                or      a
                jr      z,gwp_no_s
                ld      a,(GFX_WS_O)
                ld      hl,(GFX_WS_P)
                ld      de,GFX_SVX
                call    gwp_spoke_vec
gwp_no_s:
                ld      a,(GFX_ENEG)
                or      a
                ret     z
                ld      a,(GFX_WE_O)
                ld      hl,(GFX_WE_P)
                ld      de,GFX_EVX
                ; fall through into gwp_spoke_vec; its ret serves ours

; ---------------------------------------------------------------------------
; gwp_spoke_vec -- IN: A = boundary octant (0..7), HL = boundary pos,
; DE = dest vector base (X at +0, Y at +2). Walks the midpoint loop to step
; k = pos (even octant) / M-pos (odd), mirrors (qx,qy) into the octant,
; applies the minor scale, stores the (vx,vy) the spoke line will draw to.
; Clobbers everything + GFX_QX/QY/QD + GFX_PX/PY/GFX_CS_AX scratch.
; ---------------------------------------------------------------------------
gwp_spoke_vec:
                push    de                  ; [dest base]
                push    af                  ; [octant]
                bit     0,a
                jr      z,gsv_keven
                ex      de,hl
                ld      hl,(GFX_M)
                or      a
                sbc     hl,de               ; k = M - pos (pos <= M-1 -> k >= 1)
gsv_keven:
                ld      (GFX_PX),hl         ; PX = k (walk target)
                call    gfx_circ_init
gsv_walk:
                ld      hl,(GFX_QX)
                ld      de,(GFX_PX)
                or      a
                sbc     hl,de
                jr      z,gsv_have          ; qx == k -> found
                ld      hl,(GFX_QX)
                ld      (GFX_PY),hl         ; prev qx
                ld      hl,(GFX_QY)
                ld      (GFX_CS_AX),hl      ; prev qy
                call    gfx_circ_next
                ld      hl,(GFX_QY)
                ld      de,(GFX_QX)
                or      a
                sbc     hl,de               ; still qx <= qy ?
                jp      p,gsv_walk
                ld      hl,(GFX_PY)         ; walked off the end (k beyond the
                ld      (GFX_QX),hl         ; octant, e.g. M-0 at r=24 where the
                ld      hl,(GFX_CS_AX)      ; loop tops out at M+1) -> use the
                ld      (GFX_QY),hl         ; LAST emitted step
gsv_have:
                pop     af                  ; octant
                ; mirror (qx,qy) into the octant. From the static map:
                ;   x-source is qy (swapped) for octants 0,3,4,7 <=> (o+1)&2=0
                ;   vx negative for octants 2,3,4,5             <=> (o+2)&4!=0
                ;   vy negative for octants 0,1,2,3             <=> o<4
                ld      c,a
                inc     a
                and     2
                jr      nz,gsv_noswap
                ld      hl,(GFX_QY)
                ld      de,(GFX_QX)
                jr      gsv_signs
gsv_noswap:
                ld      hl,(GFX_QX)
                ld      de,(GFX_QY)
gsv_signs:
                ld      a,c
                add     a,2
                and     4
                jr      z,gsv_xpos          ; vx stays positive
                xor     a                   ; negate HL (vx)
                sub     l
                ld      l,a
                sbc     a,a
                sub     h
                ld      h,a
gsv_xpos:
                ld      a,c
                and     4
                jr      nz,gsv_ypos         ; octant >= 4 -> vy positive
                call    gfx_neg16_de        ; vy := -vy
gsv_ypos:
                ld      (GFX_PX),hl         ; vx
                ld      (GFX_PY),de         ; vy
                ld      a,(GFX_ASPMAJ)
                or      a
                jr      z,gsv_scy
                ld      hl,(GFX_PX)
                call    gfx_circ_scale      ; minor is X (y-major)
                ld      (GFX_PX),hl
                jr      gsv_store
gsv_scy:
                ld      hl,(GFX_PY)
                call    gfx_circ_scale      ; minor is Y (x-major, default)
                ld      (GFX_PY),hl
gsv_store:
                pop     de                  ; dest base
                ld      hl,(GFX_PX)
                ld      a,l
                ld      (de),a
                inc     de
                ld      a,h
                ld      (de),a
                inc     de
                ld      hl,(GFX_PY)
                ld      a,l
                ld      (de),a
                inc     de
                ld      a,h
                ld      (de),a
                ret

; ---------------------------------------------------------------------------
; gfx_circ_init -- IN: GFX_R (radius). OUT: GFX_QX=0, GFX_QY=r, GFX_QD=1-r
; (spec §4.1). Pure (RAM only, no ports) -> host-unit-testable, mirroring
; G3's gfx_bres_init. Clobbers A, DE, HL.
; ---------------------------------------------------------------------------
gfx_circ_init:
                ld      hl,(GFX_R)
                ld      (GFX_QY),hl
                ld      hl,0
                ld      (GFX_QX),hl
                ld      hl,1
                ld      de,(GFX_R)
                or      a
                sbc     hl,de
                ld      (GFX_QD),hl
                ret

; ---------------------------------------------------------------------------
; gfx_circ_next -- advance the midpoint-circle state one step (spec §4.1):
; d<0 ? d+=2x+3 : (d+=2(x-y)+5, y--); x++. Pure (RAM only) -> host-unit-
; testable, mirroring G3's gfx_bres_next. Clobbers A, DE, HL.
; ---------------------------------------------------------------------------
gfx_circ_next:
                ld      hl,(GFX_QD)
                bit     7,h
                jr      z,gco_else
                ld      hl,(GFX_QX)
                add     hl,hl               ; 2x
                ld      de,3
                add     hl,de
                ld      de,(GFX_QD)
                add     hl,de
                ld      (GFX_QD),hl
                jr      gco_incx
gco_else:
                ld      hl,(GFX_QX)
                ld      de,(GFX_QY)
                or      a
                sbc     hl,de               ; x - y (signed; may be negative)
                add     hl,hl               ; 2(x-y)
                ld      de,5
                add     hl,de
                ld      de,(GFX_QD)
                add     hl,de
                ld      (GFX_QD),hl
                ld      hl,(GFX_QY)
                dec     hl
                ld      (GFX_QY),hl
gco_incx:
                ld      hl,(GFX_QX)
                inc     hl
                ld      (GFX_QX),hl
                ret

; ---------------------------------------------------------------------------
; gco_emit8 -- emit the 8 mirrored points of the current (GFX_QX,GFX_QY):
; (+-x,+-y) and (+-y,+-x), each through gfx_circ_emit_point. Clobbers
; everything.
; ---------------------------------------------------------------------------
; Each mirror carries its STATIC octant (D-ARCMASK): the octant of a mirror
; position never depends on the point, so the mask needs no per-point atan --
; the `ld a,N` immediately before each call IS the direction decomposition.
; (BASIC angle = atan2(-dy, dx); octant o covers [o*pi/4, (o+1)*pi/4).)
gco_emit8:
                ld      bc,(GFX_QX)
                ld      de,(GFX_QY)
                ld      a,6
                call    gfx_circ_emit_point ; (+x,+y)  octant 6
                ld      bc,(GFX_QX)
                ld      de,(GFX_QY)
                call    gfx_neg16_de
                ld      a,1
                call    gfx_circ_emit_point ; (+x,-y)  octant 1
                ld      bc,(GFX_QX)
                call    gfx_neg16_bc
                ld      de,(GFX_QY)
                ld      a,5
                call    gfx_circ_emit_point ; (-x,+y)  octant 5
                ld      bc,(GFX_QX)
                call    gfx_neg16_bc
                ld      de,(GFX_QY)
                call    gfx_neg16_de
                ld      a,2
                call    gfx_circ_emit_point ; (-x,-y)  octant 2
                ld      bc,(GFX_QY)
                ld      de,(GFX_QX)
                ld      a,7
                call    gfx_circ_emit_point ; (+y,+x)  octant 7
                ld      bc,(GFX_QY)
                ld      de,(GFX_QX)
                call    gfx_neg16_de
                ld      a,0
                call    gfx_circ_emit_point ; (+y,-x)  octant 0
                ld      bc,(GFX_QY)
                call    gfx_neg16_bc
                ld      de,(GFX_QX)
                ld      a,4
                call    gfx_circ_emit_point ; (-y,+x)  octant 4
                ld      bc,(GFX_QY)
                call    gfx_neg16_bc
                ld      de,(GFX_QX)
                call    gfx_neg16_de
                ld      a,3
                call    gfx_circ_emit_point ; (-y,-x)  octant 3
                ret

; ---------------------------------------------------------------------------
; gfx_circ_emit_point -- IN: A = the mirror's static octant (0..7), BC=dx
; (raw octant offset, signed), DE=dy (raw). The arc mask (gfx_circ_keep) runs
; FIRST, on the RAW point -- the octant plus the loop's own qx -- because the
; reference masks BEFORE the minor scale: the r=700 ASPS=35 arc row is
; byte-exact only pre-scale (D-ARCMASK, arcmask_refmodel2.py). Then the
; minor-axis 8.8 scale (GFX_ASPMAJ selects which of dx/dy), then the plot at
; (GFX_CXC+dx',GFX_CYC+dy') via gfx_plot_cur (its own clip + DI-guarded RMW).
; Clobbers everything.
; ---------------------------------------------------------------------------
gfx_circ_emit_point:
                ld      (GFX_PX),bc
                ld      (GFX_PY),de
                call    gfx_circ_keep       ; CF=1 iff this point survives (A=octant)
                ret     nc
                ld      a,(GFX_ASPMAJ)
                or      a
                jr      z,gcep_scaley
                ; y-major (aspect>1): the MINOR axis is x
                ld      hl,(GFX_PX)
                call    gfx_circ_scale
                ld      (GFX_PX),hl
                jr      gcep_plot
gcep_scaley:
                ; x-major (aspect<=1, incl. the no-scale default): minor is y
                ld      hl,(GFX_PY)
                call    gfx_circ_scale
                ld      (GFX_PY),hl
gcep_plot:
                ld      hl,(GFX_CXC)
                ld      de,(GFX_PX)
                add     hl,de
                ld      (GFX_CX),hl
                ld      hl,(GFX_CYC)
                ld      de,(GFX_PY)
                add     hl,de
                ld      (GFX_CY),hl
                jp      gfx_plot_cur        ; tail call: clip + DI-guarded RMW; ret

; ---------------------------------------------------------------------------
; gfx_circ_scale -- IN: HL=v (signed raw offset). OUT: HL = sign(v) *
; ((|v|*GFX_ASPS+128)>>8), the 8.8 minor scale (spec §4.2). Clobbers A, BC, DE.
;
; 🔴 THE "BOUNDED-DOMAIN" LINE THAT USED TO BE HERE IS RETIRED (D-CIRCDOM). It
; read "|v|*ASPS assumed <=65535 (true for |v|<=255, ASPS<=256 -- the blessed
; r<=255 domain)", and docs/fixpoint8000-msx1-sweep.md §4.2 rested FOUR $8000
; verdicts on it. One comment, four rows, and it stated an OVERFLOW bound while
; being cited for a $8000 bound. Both halves are now separated and sited:
;
;  * DOMAIN. There is no r<=255 rule anywhere. The radius is 0..32767, enforced
;    at basic/graphics.asm cp_req_int (gfx_eval_int16, ERR 6 at |r|>=32768) and
;    sub/circleparse.asm cpt_after_r (`jp m,cpt_err5`, ERR 5 at r<0). ASPS is
;    0..256 by construction (minor_ratio = aspect if aspect<1 else 1/aspect).
;
;  * $8000 AT gfx_abs16 (the call below). Input is GFX_PX/GFX_PY = +-GFX_QX /
;    +-GFX_QY from gco_emit8, and gfx_circ_init seeds QY=r with QY only ever
;    decrementing and QX climbing while QX<=QY -- so |v| <= r <= 32767.
;    $8000 UNREACHABLE, by the int16 coercion above, NOT by 255.
;
;  * $8000 AT THE RE-NEGATE (the `xor a / sub l / ...` tail below). 🔴 THE
;    REASON CHANGED IN D-CIRCOVF AND THE VERDICT DID NOT. It used to be 0..255
;    BY CONSTRUCTION, via a `ld l,h / ld h,0` that also caused the overflow
;    below; removing that truncation is exactly what D-CIRCDOM predicted would
;    make $8000 reachable here for the first time. It did not, because of the
;    branch above: ASPS is 0..256, and ASPS=256 -- the ONLY value whose exact
;    (32767*256+128)>>8 is 32768 -- is also the only value for which this whole
;    routine is the IDENTITY, so it never reaches the multiply. The two arms
;    cap at |v| <= 32767 and at (32767*255+128)>>8 = 32639 respectively.
;    $8000 UNREACHABLE, now by a 32767 bound rather than a 255 one.
;    ⚠️ THAT MAKES THE IDENTITY ARM LOAD-BEARING FOR CORRECTNESS, not just for
;    speed. Deleting it reinstates the fixed point. Knifed: K-CO2 in
;    scratchpad/circovf_knives.py reddens 19 rows, EXACT against a prediction
;    derived from the gate's own case list.
;
;  * OVERFLOW. FIXED (D-CIRCOVF, docs/circovf-msx1-oracle.md). gfx_mul16r
;    carries |v|*ASPS in a 24-bit accumulator, so there is no product bound left
;    to state. The reference was MEASURED to compute this product at full width
;    and round half-up: four rows on three code paths, byte-identical across the
;    whole 6144-byte plane, with a saturating model and the old wrapping model
;    both refuted at sha1 level. See gfx_circle_op's header for the row table.
; ---------------------------------------------------------------------------
gfx_circ_scale:
                call    gfx_abs16           ; HL=|v|, A=sign ($01 pos / $FF neg)
                push    af
                ld      de,(GFX_ASPS)
                ld      a,d
                or      a
                jr      nz,gcs_signed       ; ASPS=256 (D=1) -> scale is the
                                            ; IDENTITY: (|v|*256+128)>>8 = |v|,
                                            ; and HL is already |v|. This is the
                                            ; default and every aspect of exactly
                                            ; 1; it also keeps the result at
                                            ; <= 32767 -- see the header.
                ld      a,e                 ; A = ASPS, 0..255
                ex      de,hl               ; DE = |v|
                call    gfx_mul16r          ; HL = (|v|*ASPS+128)>>8, full width
gcs_signed:
                pop     af
                cp      $01
                ret     z                   ; was non-negative -> done
                ; negate HL (own-design two's-complement negate, gfx_abs16's idiom).
                ; HL is 0..255 here BY CONSTRUCTION (the `ld l,h / ld h,0` two lines
                ; up), so this negate cannot meet $8000 -- D-CIRCDOM, see header.
                xor     a
                sub     l
                ld      l,a
                sbc     a,a
                sub     h
                ld      h,a
                ret

; ---------------------------------------------------------------------------
; gfx_circ_keep -- the D-ARCMASK step-index wedge test. IN: A = the current
; mirror's STATIC octant (0..7); reads GFX_QX (the loop's step index -- always
; min(|dx|,|dy|)), GFX_M and the wedge cells. OUT: CF=1 iff the point is
; plotted: always when GFX_ARCF=0 or GFX_FULLW=1; else iff the point's
; normalized (octant,pos) pair lies in the CLOSED cyclic interval from
; (GFX_WS_O,GFX_WS_P) to (GFX_WE_O,GFX_WE_P) -- lexicographic pair compares,
; wrap decided once per CIRCLE (GFX_WRAPF). Pure 16-bit RAM arithmetic: this
; replaces two gfx_cross_ge0 calls per point -- four 16x16->32 multiplies and
; two 32-bit compares -- with at most three 16-bit compares, which is the
; whole of the 5-6x arc slowdown D-ARCMASK measured against the reference.
; Clobbers A, BC, DE, HL.
; ---------------------------------------------------------------------------
gfx_circ_keep:
                ld      c,a                 ; C = octant
                ld      a,(GFX_ARCF)
                or      a
                jr      z,gck_keep          ; full circle/ellipse -> keep
                ld      a,(GFX_FULLW)
                or      a
                jr      nz,gck_keep         ; near-2*pi wedge -> keep
                ; pos = qx (even octant) / M - qx (odd octant)
                ld      hl,(GFX_QX)
                bit     0,c
                jr      z,gck_norm
                ex      de,hl
                ld      hl,(GFX_M)
                or      a
                sbc     hl,de               ; M - qx (may be -1: qx tops at M+1)
gck_norm:
                ; normalize (C,HL) to 0 <= pos <= M-1. One step each way
                ; suffices (qx <= M+1); M=0 (r<=1) skips -- pos is 0 either
                ; way, matching arcmask_asmsim2's draw_pair exactly.
                ld      de,(GFX_M)
                ld      a,d
                or      e
                jr      z,gck_pair
                bit     7,h
                jr      z,gck_n2
                add     hl,de               ; pos<0 -> borrow an octant
                dec     c
                jr      gck_pair
gck_n2:
                or      a
                sbc     hl,de
                jr      c,gck_n2u           ; pos < M -> in range; undo
                inc     c                   ; pos >= M -> carry an octant
                jr      gck_pair
gck_n2u:
                add     hl,de
gck_pair:
                ld      a,c
                and     7
                ld      c,a                 ; C = octant 0..7, HL = pos
                ; B := 1 iff P >= S  (octant compare, pos breaks the tie)
                ld      b,1
                ld      a,(GFX_WS_O)
                cp      c
                jr      c,gck_e             ; OS < Po -> P > S
                jr      nz,gck_plt_s        ; OS > Po -> P < S
                ld      de,(GFX_WS_P)
                push    hl
                or      a
                sbc     hl,de               ; pos - PS
                pop     hl
                jr      nc,gck_e            ; pos >= PS -> P >= S
gck_plt_s:
                ld      b,0
gck_e:
                ; A := 1 iff P <= E
                ld      a,(GFX_WE_O)
                cp      c
                jr      c,gck_pgt_e         ; OE < Po -> P > E
                jr      nz,gck_ple          ; OE > Po -> P < E
                ld      de,(GFX_WE_P)
                or      a
                sbc     hl,de               ; pos - PE (HL dead afterwards)
                jr      z,gck_ple
                jr      c,gck_ple
gck_pgt_e:
                xor     a
                jr      gck_comb
gck_ple:
                ld      a,1
gck_comb:
                ld      d,a
                ld      a,(GFX_WRAPF)
                or      a
                ld      a,d
                jr      nz,gck_or
                and     b                   ; plain wedge: P>=S AND P<=E
                jr      gck_fin
gck_or:
                or      b                   ; wraps 0:     P>=S OR  P<=E
gck_fin:
                or      a
                jr      nz,gck_keep
                ret                         ; CF=0 (the `or a` cleared it) -> reject
gck_keep:
                scf
                ret

; ---------------------------------------------------------------------------
; gfx_mul16u32 -- HL:DE := HL * DE, the FULL 32-bit unsigned product (own copy
; of the classic shift-out-the-multiplier form -- a page-0 tenant cannot reach
; the main-ROM low region, which is swapped OUT for the duration of this
; CALSLT). Clobbers A, BC.
;
; D-CIRCOVF replaced gfx_mul16u (low-16-only) with this full-width form for
; gfx_cross_ge0's 2^30 products. D-ARCMASK then RETIRED gfx_cross_ge0 -- the
; arc mask is a step-index wedge now -- and the callers of this multiply are
; gfx_circ_wedge_prep's three init-time products (M candidate, M*M, r*r) and
; gwp_pos's u14*M, all once per CIRCLE, none per point.
; ---------------------------------------------------------------------------
; OUT: DE = product HIGH word, HL = product LOW word.
gfx_mul16u32:
                ld      b,h
                ld      c,l                 ; BC = multiplicand
                ld      hl,0                ; DE:HL = multiplier:accumulator
                ld      a,16
gm32_lp:
                add     hl,hl
                rl      e
                rl      d                   ; DE:HL <<= 1; the bit leaving D is
                                            ; the next multiplier bit, MSB first
                jr      nc,gm32_skip
                add     hl,bc
                jr      nc,gm32_skip
                inc     de                  ; carry from the low word into the high
gm32_skip:
                dec     a
                jr      nz,gm32_lp
                ret

; ---------------------------------------------------------------------------
; gfx_cmp32 -- unsigned compare of two 4-byte little-endian magnitudes.
; IN: HL -> a, DE -> b. OUT: CF=1 iff a < b. Clobbers A, B, DE, HL.
; A borrow-propagating subtract from the LSB up; ex/inc/djnz all leave CF
; alone, so the final borrow IS the comparison.
; ---------------------------------------------------------------------------
gfx_cmp32:
                ld      b,4
                or      a                   ; CF = 0 going in
gcm_lp:
                ld      a,(hl)
                ex      de,hl
                sbc     a,(hl)
                ex      de,hl
                inc     hl
                inc     de
                djnz    gcm_lp
                ret

; ---------------------------------------------------------------------------
; gfx_mul16r -- HL := (DE * A + 128) >> 8, the 8.8 round-half-up scale, with
; the product carried at FULL WIDTH. IN: DE = 0..32767, A = 0..255.
; OUT: HL = 0..32639. Clobbers A, BC, DE.
;
; D-CIRCOVF. This exists because `(|v|*ASPS+128)>>8` computed through
; gfx_mul16u WRAPS: that routine keeps the low 16 bits, and |v|*ASPS reaches
; 8355585. The 24-bit accumulator below is C:HL, shifted left once per
; multiplier bit (MSB first, `add a,a` supplying the bit), so it never
; discards one. 32767*255 = 8355585 < 2^24, so C cannot carry out.
;
; MEASURED, not assumed: the reference computes this product exactly and
; rounds half-up. Four rows on three code paths (default aspect, aspect<1,
; aspect>1) matched a full-width prediction BYTE FOR BYTE across the whole
; 6144-byte pattern plane, while a saturating model and the wrapping model
; were both refuted -- docs/circovf-msx1-oracle.md §3.
;
; ⚠️ THE OUTPUT IS DELIBERATELY NOT NARROWED TO A BYTE. The `ld l,h / ld h,0`
; pair this replaces at both callers was the reason three of D-CIRCDOM's five
; `$8000` verdicts held "by construction" (§6). They still hold -- see
; gfx_circ_scale's header for the arithmetic -- but they now hold on a bound
; of 32767, not 255. (gfx_cross_ge0, whose products were sized off that
; bound, is retired -- D-ARCMASK.)
; ---------------------------------------------------------------------------
gfx_mul16r:
                ld      hl,0
                ld      c,l                 ; C:HL = 0, the 24-bit accumulator
                ld      b,8
gmr_lp:
                add     hl,hl
                rl      c                   ; C:HL <<= 1
                add     a,a                 ; next multiplier bit (MSB first)
                jr      nc,gmr_skip
                add     hl,de
                jr      nc,gmr_skip
                inc     c                   ; carry into the top byte
gmr_skip:
                djnz    gmr_lp
                ld      de,128
                add     hl,de               ; round half-up
                jr      nc,gmr_rnd
                inc     c
gmr_rnd:
                ld      l,h
                ld      h,c                 ; HL = (product + 128) >> 8
                ret

; ---------------------------------------------------------------------------
; gfx_neg16_bc / gfx_neg16_de -- two's-complement negate BC / DE in place
; (gfx_abs16's own idiom). Clobbers A.
; 🔴 $8000 REACHABILITY (D-CIRCDOM). docs/fixpoint8000-msx1-sweep.md §4.2 marked
; these "out of domain, callers are the circle/arc vectors, same bound" -- citing
; gfx_circ_scale's "blessed r<=255" comment, which never existed as a rule. The
; verdict stands; the reason is different and is worth stating because it is the
; ONLY one of the five sites bounded by the radius rather than by a truncation:
; the ONLY callers are gco_emit8's eight mirror emits, which pass GFX_QX / GFX_QY
; and nothing else. gfx_circ_init seeds QY=r, gfx_circ_next only ever decrements
; QY and increments QX, and gco_loop stops once QX>QY -- so both are in -1..r,
; and r is 0..32767 (sub/circleparse.asm cpt_after_r). The largest magnitude that
; can arrive here is $7FFF, one short of the fixed point. If the radius domain
; ever widens, THIS is the site that needs a $8000 arm first.
; ---------------------------------------------------------------------------
gfx_neg16_bc:
                xor     a
                sub     c
                ld      c,a
                sbc     a,a
                sub     b
                ld      b,a
                ret
gfx_neg16_de:
                xor     a
                sub     e
                ld      e,a
                sbc     a,a
                sub     d
                ld      d,a
                ret

; ===========================================================================
; G5 -- PAINT (SCREEN-2 flood fill). GFX_OP=5. docs/spec-basic-graphics-g5.md.
; Reuses G3's EI-between-pixels / DI-per-pixel gfx_rmw_at RMW and G2's
; gfx_point_extract read verbatim -- the only new tenant code is the scanline
; span-fill engine itself (spec §4, own-design Smith-style) and its
; fixed-capacity span stack (GFX_PSTK, sysvars.inc; D3).
;
; INSIDE TEST (own-design; spec §4 permits "any correct flood algorithm" since
; the final bitmap is traversal-order-independent, §4 crux). A pixel "needs
; fill" (gfx_paint_inside) iff its LIVE effective colour is neither B NOR
; ALREADY C. The spec's own step-1/2 wording says "not-yet-B"; this tenant
; also stops at "already C" -- a pixel we (or a coincidentally pre-existing
; C-coloured pixel) already painted -- for two reasons: (1) it is the ONLY
; termination argument available without Smith's parent-direction/overhang
; bookkeeping (spec's own ~5 B/entry stack-entry estimate), since re-scanning
; an already-filled span with a bare "!=B" test bounces forever between two
; open rows (traced by hand: neither row ever stops testing "fillable", so
; neighbour pushes recur without end); testing "!=C" too makes every re-scan
; of an already-painted span an immediate, cheap no-op, giving the standard
; amortized-O(area) termination with a plain 3 B/entry (y,xL,xR) stack -- see
; sysvars.inc's GFX_PSTK header for the capacity this buys back. (2) it
; matches a well-known PUBLIC MSX/GW-BASIC PAINT-dialect quirk (paint also
; stops at a point already the same colour as the paint colour) -- so this is
; not merely a safe internal shortcut, it is plausibly the MORE faithful
; choice. When C==B this collapses to plain "!=B" (spec's own BOUNDED case).
; NOT measured by the pinned battery either way (no captured case has a
; coincidental pre-existing-C pixel inside an otherwise-open region); flagged
; here as the one place this slice's own algorithm choice could in principle
; diverge from an untested reference edge case.
;
; EI/DI discipline (spec §2/§4): gfx_paint_op EIs once for the whole
; (possibly long) fill; gfx_paint_read (the border test) and gfx_paint_plot
; (the paint) each bracket their OWN di/ei around their VDP access -- finer
; grain than "between spans" (spec's own words), matching G3/G4's per-pixel
; RMW discipline exactly, just applied to reads too (PAINT is the first op
; whose EI'd loop also does VDP READS, not just writes).
;
; Overflow (D3, measured): gfx_pstk_push sets GFX_POVF=1 and simply declines
; to store past capacity; the flood loop notices GFX_POVF after every
; gfx_paint_process and aborts immediately (di, ret) with an INCOMPLETE
; bitmap -- irrelevant, since the resident raises ERR 7 (Out of memory) on
; return, which aborts the whole statement (raise_error resets SP).
; ===========================================================================

; ---------------------------------------------------------------------------
; gfx_pstk_addr -- IN: A = index (0..GFX_PSTK_CAP-1). OUT: HL = GFX_PSTK +
; index*GFX_PSTK_ENTSZ. Pure address arithmetic. Clobbers DE/HL; A preserved.
; ---------------------------------------------------------------------------
gfx_pstk_addr:
                ld      l,a
                ld      h,0                 ; HL = index
                ld      e,a
                ld      d,0                 ; DE = index
                add     hl,hl               ; HL = index*2
                add     hl,de               ; HL = index*3 (GFX_PSTK_ENTSZ)
                ld      de,GFX_PSTK
                add     hl,de
                ret

; ---------------------------------------------------------------------------
; gfx_pstk_reset -- empties the span stack and clears the overflow flag.
; Clobbers A.
; ---------------------------------------------------------------------------
gfx_pstk_reset:
                xor     a
                ld      (GFX_PTOP),a
                ld      (GFX_POVF),a
                ret

; ---------------------------------------------------------------------------
; gfx_pstk_push -- IN: A=y, B=xL, C=xR. Pushes one span entry. On overflow
; (GFX_PTOP already at capacity) sets GFX_POVF=1 and drops the entry instead
; of storing it -- the caller (gfx_paint_flood) checks GFX_POVF and aborts the
; fill (spec §4 D3: overflow -> ERR 7, raised by the resident). Clobbers
; A/DE/HL; B/C preserved.
; ---------------------------------------------------------------------------
gfx_pstk_push:
                push    af                  ; stash y
                ld      a,(GFX_PTOP)
                cp      GFX_PSTK_CAP
                jr      c,gpp_ok
                pop     af
                ld      a,1
                ld      (GFX_POVF),a
                ret
gpp_ok:
                call    gfx_pstk_addr       ; HL = slot addr (A=index still loaded; BC preserved)
                pop     af                  ; A = y
                ld      (hl),a
                inc     hl
                ld      (hl),b
                inc     hl
                ld      (hl),c
                ld      a,(GFX_PTOP)
                inc     a
                ld      (GFX_PTOP),a
                ret

; ---------------------------------------------------------------------------
; gfx_pstk_pop -- OUT: CF=1 and A=y,B=xL,C=xR (an entry was popped), or CF=0
; (the stack was already empty; A/B/C untouched). Clobbers A/DE/HL (+B/C on
; success only).
; ---------------------------------------------------------------------------
gfx_pstk_pop:
                ld      a,(GFX_PTOP)
                or      a
                jr      z,gpop_empty
                dec     a
                ld      (GFX_PTOP),a
                call    gfx_pstk_addr       ; HL = slot addr
                ld      a,(hl)
                inc     hl
                ld      b,(hl)
                inc     hl
                ld      c,(hl)
                scf
                ret
gpop_empty:
                or      a
                ret

; --- (removed) gfx_border_read ----------------------------------------------
; The original PAINT border test: read a pixel's effective colour 0..15,
; di-guarded, for use inside gfx_paint_op's EI'd fill. It was SUPERSEDED by
; gfx_paint_read below, which returns the same colour AND reports whether the
; pixel's pattern bit is set -- the empirical VG-8020 PAINT bug fix
; (docs/spec-basic-graphics-g5.md). Every caller moved to gfx_paint_read and
; this one was left behind, unreferenced, for the whole G5..R1 span; pasmo had
; been reporting it on every build inside the warning noise.
; Deleted 2026-07-30 by docs/spec-deadcode-gate.md §3 (24 B of sub page 0), the
; first finding of the standing gate this slice lands
; (tools/check_dead_code.py).

; ---------------------------------------------------------------------------
; gfx_paint_plot -- paints the pixel at (GFX_PTESTY,GFX_PTESTX) with GFX_C.
; di-guarded RMW (mirrors gfx_plot_cur's discipline; skips its 16-bit clip
; test -- unnecessary here, the fill never generates an out-of-range pixel).
; Clobbers everything.
; ---------------------------------------------------------------------------
gfx_paint_plot:
                ld      a,(GFX_PTESTY)
                ld      d,a
                ld      a,(GFX_PTESTX)
                ld      e,a
                di
                call    gfx_rmw_at
                ei
                ret

; ---------------------------------------------------------------------------
; gfx_paint_read -- IN: D=y,E=x (di-guarded; clobbers BC/DE/HL). Reports the
; pixel's effective colour AND whether its PATTERN BIT is set (drawn) vs clear
; (never-drawn background). OUT: A = effective colour nibble 0..15;
; Zf=1 iff the bit is CLEAR (background).
;
; WHY THIS EXISTS (BUG FIX, empirically found via the VG-8020 PAINT
; differential, docs/spec-basic-graphics-g5.md): a group's shared colour
; byte only ever changes a SET-bit pixel's apparent colour (its own bit
; picks fg vs bg; painting a DIFFERENT pixel in the same group only changes
; fg, never bg) -- so a never-drawn (bit-clear) pixel ALWAYS reads back as
; the group's background nibble, by construction, REGARDLESS of what
; happens to paint elsewhere in its group. If "border" is tested purely as
; "effective colour == GFX_B" (gfx_paint_inside's original form), a caller
; that passes a border colour equal to the CURRENT background (e.g.
; `PAINT(100,100),7,1` with BAKCLR=1) would see every untouched neighbour
; pixel read as B and refuse to extend AT ALL, even though nothing was ever
; actually drawn there -- measured on the reference to still flood (a
; background match on B is NOT a real border). "Border" therefore means a
; DRAWN pixel (bit set) whose colour is B; an undrawn pixel is never a
; border, independent of colour.
; ---------------------------------------------------------------------------
gfx_paint_read:
                di
                call    gfx_calc_addr       ; HL = pattern addr, C = mask
                call    gfx_rd_raw          ; A = pattern byte
                ld      d,a                 ; D = pattern byte
                ld      e,c                 ; E = mask
                ld      a,h                 ; colour addr = pattern addr + $2000
                add     a,$20               ; pattern high <= $17 -> no carry out
                ld      h,a
                call    gfx_rd_raw          ; A = colour byte
                ld      c,a                 ; C = colour byte
                ld      a,d                 ; A = pattern byte
                and     e                   ; Zf=1 iff the bit is clear (background)
                push    af                  ; save that Zf across gfx_point_extract
                ld      a,d
                ld      b,e                 ; B = mask (gfx_point_extract's own IN)
                call    gfx_point_extract   ; A = effective colour nibble (clobbers flags)
                ld      b,a                 ; stash colour (LD r,r' never touches flags)
                pop     af                  ; restore the bit-clear Zf (A now stale)
                ld      a,b                 ; A = colour nibble; Zf still the bit test
                ei
                ret

; ---------------------------------------------------------------------------
; gfx_paint_inside -- IN: (GFX_PTESTY)=y, (GFX_PTESTX)=x. OUT: CF=1 iff the
; pixel "needs fill": a DRAWN pixel counts as border/already-done if its
; colour is GFX_B/GFX_C; an UNDRAWN (background) pixel can never be "border"
; (gfx_paint_read's own header) but is still short-circuited by the
; "already C" rule if its background nibble happens to coincide with GFX_C
; (a PAINT whose C equals the current background is a no-op everywhere,
; matching the PSET clash rule "c==bg -> clear bit"). Used ONLY to decide
; whether to PUSH a pixel as the start of a NEW span (gfx_paint_flood's seed
; test -- see ITS header for why the seed itself no longer even calls this --
; and gfx_paint_scan_row's neighbour-row scan): the "already C" stop is what
; keeps an already-fully-painted region from being re-pushed onto the span
; stack over and over (the D3 stack-budget property). NOT used for
; extend_lr's own L/R walk -- see gfx_paint_passable below (a SEPARATE bug
; fix: the "already C" stop here would otherwise also block extend_lr from
; walking PAST a border pixel that colour-clash "ate" from an adjacent
; painted pixel, since that eaten pixel now incidentally reads as C too;
; extend_lr needs the looser passable test to keep walking into newly-opened
; territory beyond it). Clobbers everything.
; ---------------------------------------------------------------------------
gfx_paint_inside:
                ld      a,(GFX_PTESTY)
                ld      d,a
                ld      a,(GFX_PTESTX)
                ld      e,a
                call    gfx_paint_read      ; A = colour; Zf=1 iff bit clear (background)
                ld      b,a                 ; B = colour (LD doesn't touch flags)
                jr      z,gpi_bg            ; background -> B can never block it (skip)
                ld      a,(GFX_B)
                cp      b
                ret     z                   ; drawn AND == B -> CF=0 (border, not inside)
gpi_bg:
                ld      a,(GFX_C)
                cp      b
                ret     z                   ; == C already -> CF=0 (own-design stop)
                scf
                ret

; ---------------------------------------------------------------------------
; gfx_paint_passable -- IN/OUT/clobbers same as gfx_paint_inside, but CF=1
; iff the pixel is not a DRAWN==B border (an undrawn/background pixel is
; always passable regardless of colour -- gfx_paint_read's own header; an
; already-C pixel is ALSO passable here, unlike gfx_paint_inside). Used ONLY
; by gfx_paint_extend_lr's L/R walk (own header): a span's visual extent is
; bounded purely by actual DRAWN border pixels, not by "have I already
; painted this" -- that distinction belongs to the push decision
; (gfx_paint_inside above), not the walk. Re-painting an already-C pixel
; while walking through it is a safe no-op (the clash RMW is idempotent when
; the group's fg is already C). BUG FIX: without this split, a border pixel
; incidentally recoloured to C by an adjacent painted pixel's group-clash
; (the "border eaten" mechanism, spec §3) would falsely look like an
; impassable stop to extend_lr too, trapping the fill inside the (now
; partially C-coloured) wall instead of continuing outward -- confirmed
; empirically (VG-8020 differential: a thin 1-px LINE...,B wall correctly
; gets "eaten" up to the wall pixel itself on the pre-fix build, but the
; fill never continued past it into the newly-open region beyond).
; ---------------------------------------------------------------------------
gfx_paint_passable:
                ld      a,(GFX_PTESTY)
                ld      d,a
                ld      a,(GFX_PTESTX)
                ld      e,a
                call    gfx_paint_read      ; A = colour; Zf=1 iff bit clear (background)
                ld      b,a                 ; B = colour (LD doesn't touch flags)
                jr      z,gpsb_ok           ; background -> always passable
                ld      a,(GFX_B)
                cp      b
                ret     z                   ; drawn AND == B -> CF=0 (border, blocked)
gpsb_ok:
                scf
                ret                         ; background, or drawn-but-!=B -> CF=1

; ---------------------------------------------------------------------------
; gfx_paint_op -- GFX_OP=5 entry. EI for the (possibly long) fill; DI only
; around each pixel's VDP access (gfx_paint_read/gfx_paint_plot each
; bracket their own). Seed = (GXPOS,GYPOS) low bytes, already range-checked
; on-screen by the resident (off-screen seed is ERR 5 there -- the tenant
; never sees one). GFX_C/GFX_B = the resident-marshalled paint/border colours.
; ---------------------------------------------------------------------------
gfx_paint_op:
                ei
                call    gfx_pstk_reset
                call    gfx_paint_flood
                di
                ret

; ---------------------------------------------------------------------------
; gfx_paint_extend_lr -- given a starting span (GFX_PFY,GFX_PXL,GFX_PXR)
; already known to lie inside the fillable region, extend PXL leftward and
; PXR rightward while Inside (stop at a B/already-C pixel or the x=0/255
; screen edge) -- spec §4 step 1's "walk left/right" shape. Shared by
; gfx_paint_flood (the seed, where PXL=PXR=seedx to start) AND
; gfx_paint_process (every span POPped off the stack, not just the seed):
; gfx_paint_scan_row only tests columns WITHIN its caller's [xL,xR] (its own
; header), so a pushed sub-span's [xL,xR] is maximal *within that scanned
; range*, NOT necessarily the row's true geometric extent -- if a bounding
; wall on the row ABOVE/BELOW ends partway (a concave notch reopening into a
; wider area), the true width is only found by re-walking every popped span
; exactly like the seed. Safe to call unconditionally (no separate "is xL
; still inside" gate needed). Uses gfx_paint_PASSABLE (not gfx_paint_inside)
; for its own walk -- BUG FIX (empirically found via the VG-8020 differential,
; docs/spec-basic-graphics-g5.md): a wall pixel "eaten" by an adjacent
; painted pixel's group-clash now incidentally reads as C, and the stricter
; gfx_paint_inside would treat that as a stop too, trapping the fill instead
; of letting it continue into the newly-open territory beyond. Repainting an
; already-C pixel while walking through it is a safe no-op.
;
; PAINTS EACH NEWLY-DISCOVERED PIXEL IMMEDIATELY (2nd half of the same bug
; fix): a group-clash only takes effect the instant a pixel in that group is
; actually painted, not merely tested-passable -- so if we only RECORDED the
; new bound here and left the actual painting to gfx_paint_process's later
; "paint xL..xR" loop, a wall pixel one step further out (a DIFFERENT VRAM
; group) would still see the old (un-eaten) colour when ITS OWN passability
; is tested moments later in this same walk, and extend_lr would stop one
; group too early. Painting inline as we cross each new pixel means the very
; next pixel's border_read sees the clash's effect immediately, letting the
; walk cross a whole chain of single-pixel-wide "eaten" walls in one pass
; (this call site's caller re-paints the same range again afterwards via its
; own idempotent loop -- harmless).
; Updates GFX_PXL/GFX_PXR in place. Clobbers everything + GFX_PSCX scratch.
; ---------------------------------------------------------------------------
gfx_paint_extend_lr:
gpel_left:
                ld      a,(GFX_PXL)
                or      a
                jr      z,gpel_left_done    ; x=0 -> screen edge, stop
                dec     a
                ld      (GFX_PSCX),a        ; candidate x
                ld      (GFX_PTESTX),a
                ld      a,(GFX_PFY)
                ld      (GFX_PTESTY),a
                call    gfx_paint_passable
                jr      nc,gpel_left_done
                ld      a,(GFX_PSCX)
                ld      (GFX_PXL),a
                call    gfx_paint_plot      ; paint NOW (GFX_PTESTX/Y still set)
                jr      gpel_left
gpel_left_done:
gpel_right:
                ld      a,(GFX_PXR)
                cp      255
                jr      z,gpel_right_done   ; x=255 -> screen edge, stop
                inc     a
                ld      (GFX_PSCX),a
                ld      (GFX_PTESTX),a
                ld      a,(GFX_PFY)
                ld      (GFX_PTESTY),a
                call    gfx_paint_passable
                jr      nc,gpel_right_done
                ld      a,(GFX_PSCX)
                ld      (GFX_PXR),a
                call    gfx_paint_plot      ; paint NOW (GFX_PTESTX/Y still set)
                jr      gpel_right
gpel_right_done:
                ret

; ---------------------------------------------------------------------------
; gfx_paint_flood -- MAIN (spec §4 step 1): extend the seed to its maximal
; span (gfx_paint_extend_lr), push it, then drain the stack via
; gfx_paint_process until empty or GFX_POVF fires. Clobbers everything.
;
; BUG FIX (empirically found via the VG-8020 differential, docs/spec-basic-
; graphics-g5.md): the seed pixel is ALWAYS painted and used as the flood
; origin, UNCONDITIONALLY -- it is NOT skipped just because its own effective
; colour already happens to equal GFX_B (or GFX_C). Measured on the
; reference: `PAINT(100,100),7,1` on a plain background already == the
; given border (1) still floods (does NOT no-op); `PAINT(16,16),7,15` with
; the seed placed EXACTLY on a drawn border pixel (colour 15 == the given
; border) also floods past it. "== B stops the walk" only applies to
; pixels the flood extends INTO (gfx_paint_extend_lr/scan_row), never to the
; seed's own starting point. Painting an already-B/already-C seed pixel is a
; safe, idempotent RMW either way.
; ---------------------------------------------------------------------------
gfx_paint_flood:
                ld      a,(GYPOS)
                ld      (GFX_PFY),a
                ld      a,(GXPOS)
                ld      (GFX_PXL),a
                ld      (GFX_PXR),a
                call    gfx_paint_extend_lr
                ; --- push the discovered seed span, then drain the stack ---
                ld      a,(GFX_PXL)
                ld      b,a
                ld      a,(GFX_PXR)
                ld      c,a
                ld      a,(GFX_PFY)
                call    gfx_pstk_push       ; A=y,B=xL,C=xR
gpf_drain:
                call    gfx_pstk_pop
                ret     nc                  ; stack empty -> fill complete
                ld      (GFX_PFY),a
                ld      a,b
                ld      (GFX_PXL),a
                ld      a,c
                ld      (GFX_PXR),a
                call    gfx_paint_process
                ld      a,(GFX_POVF)
                or      a
                ret     nz                  ; overflow signalled mid-process -> abort
                jr      gpf_drain

; ---------------------------------------------------------------------------
; gfx_paint_process -- PROCESS(y,xL,xR) (spec §4 steps 1b/2), reading
; (GFX_PFY)/(GFX_PXL)/(GFX_PXR): FIRST re-extend [xL,xR] to its true maximal
; extent (gfx_paint_extend_lr -- see its header for why this is needed on
; every popped span, not just the seed), THEN paint the (possibly wider)
; span (idempotent where some pixels are already C), THEN for row y-1 and
; y+1 (clipped to 0..191) scan columns [xL,xR] for maximal Inside sub-spans
; and push each via gfx_paint_scan_row. Clobbers everything + GFX_PSCX
; scratch.
; ---------------------------------------------------------------------------
gfx_paint_process:
                call    gfx_paint_extend_lr
                ; --- paint xL..xR at row y ---
                ld      a,(GFX_PXL)
                ld      (GFX_PSCX),a
gpp_paint_lp:
                ld      a,(GFX_PFY)
                ld      (GFX_PTESTY),a
                ld      a,(GFX_PSCX)
                ld      (GFX_PTESTX),a
                call    gfx_paint_plot
                ld      hl,GFX_PXR
                ld      a,(GFX_PSCX)
                cp      (hl)
                jr      z,gpp_paint_done
                inc     a
                ld      (GFX_PSCX),a
                jr      gpp_paint_lp
gpp_paint_done:
                ; --- neighbour row y-1 (skip if y==0) ---
                ld      a,(GFX_PFY)
                or      a
                jr      z,gpp_up_done
                dec     a
                call    gfx_paint_scan_row
gpp_up_done:
                ; --- neighbour row y+1 (skip if y==191) ---
                ld      a,(GFX_PFY)
                cp      191
                ret     z
                inc     a
                jp      gfx_paint_scan_row  ; tail call: ret serves both

; ---------------------------------------------------------------------------
; gfx_paint_scan_row -- IN: A = row ny (0..191, caller-clipped). Scans
; columns (GFX_PXL)..(GFX_PXR) of row ny for maximal Inside sub-spans and
; pushes each (spec §4 step 2). Own scratch: GFX_PSCY (the row, stashed since
; gfx_paint_inside clobbers everything) + GFX_PSCX (scan cursor, reused from
; gfx_paint_process's paint pass above -- dead by this point) + GFX_PSPA
; (pending sub-span's start column). Clobbers everything.
; ---------------------------------------------------------------------------
gfx_paint_scan_row:
                ld      (GFX_PSCY),a
                ld      a,(GFX_PXL)
                ld      (GFX_PSCX),a
gpsr_loop:
                ld      hl,GFX_PXR
                ld      a,(GFX_PSCX)
                cp      (hl)
                jr      z,gpsr_test         ; PSCX == PXR -> last column, still test it
                jr      nc,gpsr_ret         ; PSCX > PXR -> row fully scanned
gpsr_test:
                ld      a,(GFX_PSCY)
                ld      (GFX_PTESTY),a
                ld      a,(GFX_PSCX)
                ld      (GFX_PTESTX),a
                call    gfx_paint_inside
                jr      nc,gpsr_advance     ; not inside -> skip this column
                ; --- found the start of a sub-span; extend right while
                ; Inside and while still within [xL,xR] ---
                ld      a,(GFX_PSCX)
                ld      (GFX_PSPA),a        ; span start = current column
gpsr_extend:
                ld      hl,GFX_PXR
                ld      a,(GFX_PSCX)
                cp      (hl)
                jr      nc,gpsr_span_end    ; PSCX>=PXR -> can't extend further
                inc     a
                ld      (GFX_PTESTX),a
                ld      a,(GFX_PSCY)
                ld      (GFX_PTESTY),a
                call    gfx_paint_inside
                jr      nc,gpsr_span_end    ; next column not inside -> span ends
                ld      a,(GFX_PTESTX)
                ld      (GFX_PSCX),a        ; commit the extension
                jr      gpsr_extend
gpsr_span_end:
                ld      a,(GFX_PSPA)
                ld      b,a
                ld      a,(GFX_PSCX)
                ld      c,a
                ld      a,(GFX_PSCY)
                call    gfx_pstk_push       ; A=y,B=xL,C=xR
                ld      a,(GFX_POVF)
                or      a
                jr      nz,gpsr_ret         ; overflow -> unwind, caller aborts
gpsr_advance:
                ld      hl,GFX_PXR
                ld      a,(GFX_PSCX)
                cp      (hl)
                ret     z                   ; was the last column -> row scan done
                inc     a
                ld      (GFX_PSCX),a
                jr      gpsr_loop
gpsr_ret:
                ret

; ===========================================================================
; G6 -- DRAW (the MML-style macro language). GFX_OP=6.
; docs/spec-basic-graphics-g6.md. The LAST drawing statement before sprites.
;
; The tenant interprets a command string that the resident has already
; PRE-PASSED (spec §7): the buffer at GFX_DBUF holds the source bytes verbatim
; except that `=var;` has become a 3-byte binary literal escape (GFX_DESC + int16
; LE) and `X strvar;` has been spliced inline. So the tenant never touches a BASIC
; variable -- which it could not do safely anyway: a page-0 tenant has the float
; pack (page-0 low) switched out from under it, so the int coercion behind `=var;`
; is unreachable here. Everything below is pure buffer walking + integer maths.
;
; Movement renders through the LANDED G3 segment primitive (gfx_draw_seg over
; GFX_X1/Y1/X2/Y2), so DRAW inherits G3's rasteriser, its per-pixel clip-by-
; masking, and its EI-between-pixels/DI-per-pixel-RMW discipline for free. That
; identity is MEASURED, not assumed: `PSET(20,20):DRAW"M53,37"` and the same LINE
; produce byte-identical bitmaps (spec §2, scratchpad/g6_draw_notes.md §9).
;
; Own-design; the DRAW *language* is the public MSX-BASIC language reference and
; every numeric rule below (the scale arithmetic, the angle's relative-only
; rotation, the persistent state, the GXPOS residue) is this project's own
; black-box measurement -- no disassembly. See sub/PROVENANCE.md.
; ===========================================================================
gfx_draw_op:
                ld      (GFX_DSP),sp        ; error tail restores this (§ helpers below)
                ei                          ; interrupts LIVE for the whole draw (arc D1)
                ld      a,(GFX_DRESUME)
                or      a
                jp      nz,gdo_resume
                ; --- fresh entry: frame 0 = a COPY of the DRAW string ---
                xor     a
                ld      (GFX_RES),a         ; 0 = ok until something raises
                ld      (GFX_DREQ),a
                ld      (GFX_DFTOP),a
                ld      (GFX_DSUBN),a
                ld      hl,GFX_DBUF
                ld      (GFX_DFREE),hl
                call    gdrw_pushframe      ; (GFX_DVAL,GFX_DVLEN) -> a new frame
                jp      gdo_loop

                ; --- re-entry after the resident resolved one substitution ---
                ; The cursor was rewound to this command's start, so banking the
                ; value and falling into the loop simply re-parses the command --
                ; which now finds the value ready in a GFX_DSUB slot.
gdo_resume:
                xor     a
                ld      (GFX_DREQ),a
                ld      a,(GFX_DSUBN)
                add     a,a                 ; slot index -> byte offset
                ld      e,a
                ld      d,0
                ld      hl,GFX_DSUB
                add     hl,de
                ld      de,(GFX_DVAL)
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ld      a,(GFX_DVLEN)
                ld      (GFX_DSUBLEN),a     ; only X uses the length half
                ld      a,(GFX_DSUBN)
                inc     a
                ld      (GFX_DSUBN),a
                jp      gdo_loop_cmd        ; cursor is already at the command start

gdo_loop:
                xor     a
                ld      (GFX_DSUBN),a       ; a NEW command: no banked values carry over
                                            ; (a resume enters at gdo_loop_cmd instead, so
                                            ; M's two substitutions do accumulate)
                call    gdrw_peek     
                jp      c,gdo_frame_end     ; end of this frame
gdo_loop_cmd:
                ld      hl,(GFX_DPTR)
                ld      (GFX_DCMD),hl       ; the rewind point for a substitution
                xor     a
                ld      (GFX_DSUBI),a       ; no substitution consumed yet this pass
                ld      (GFX_DFB),a         ; a fresh command: no prefixes pending
                ld      (GFX_DFN),a
gdo_pfx:
                call    gdrw_getc           ; A = next char, upcased
                cp      'B'
                jr      nz,gdo_notb
                ld      a,1
                ld      (GFX_DFB),a         ; B = move without drawing
                jr      gdo_pfx_next
gdo_notb:
                cp      'N'
                jr      nz,gdo_dispatch
                ld      a,1
                ld      (GFX_DFN),a         ; N = draw, then restore the position
gdo_pfx_next:
                call    gdrw_peek     
                jp      c,gdo_frame_end     ; a bare trailing B / N is accepted (measured)
                jr      gdo_pfx
                ; --- command letter dispatch ---
gdo_dispatch:
                ld      hl,gdrw_dirtab      ; the eight direction letters first
                ld      b,8
                ld      c,0                 ; C = index into gdrw_dirvec
gdo_dscan:
                cp      (hl)
                jr      z,gdo_dir
                inc     hl
                inc     c
                djnz    gdo_dscan
                cp      'M'
                jp      z,gdo_m
                cp      'C'
                jr      z,gdo_c
                cp      'S'
                jr      z,gdo_s
                cp      'A'
                jr      z,gdo_a
                cp      'X'
                jp      z,gdo_x
                jp      gdrw_err5           ; unknown letter -> ERR 5

; --- C n: colour. It is the SHARED graphics attribute (spec §6): DRAW READS
; ATRBYT and writes it only here, which is what makes `LINE ..,4 : DRAW"BM..R8"`
; draw in 4 and `DRAW"C6.." : SCREEN2 : DRAW".."` still draw in 6 (both measured).
gdo_c:
                call    gdrw_arg_req
                ld      hl,(GFX_DARG)
                ld      a,h
                or      a
                jp      nz,gdrw_err5        ; >255 or negative -> ERR 5
                ld      a,l
                cp      16
                jp      nc,gdrw_err5        ; C > 15 -> ERR 5 (measured)
                ld      (GFX_C),a           ; the colour this DRAW plots with
                ld      (ATRBYT),a          ; ...and the shared attribute, so it sticks
                jr      gdo_next

; --- S n: scale, quarter units; S0 means 4 (measured against a pre-set S8 AND
; S2, so it is a real reset to 4, not "leave unchanged"). ⚠️ THAT MAPPING IS
; WHAT MAKES 0 A USABLE SENTINEL for the never-set state `gdrw_scale` reads: no
; explicit `S` can ever store it, so "never set" and "S0" stay distinct even
; though S0 is otherwise indistinguishable from S4.
gdo_s:
                call    gdrw_arg_req
                ld      hl,(GFX_DARG)
                ld      a,h
                or      a
                jp      nz,gdrw_err5        ; S > 255 -> ERR 5 (measured: S255 ok, S256 not)
                ld      a,l
                or      a
                jr      nz,gdo_s_set
                ld      a,4                 ; S0 == S4
gdo_s_set:
                ld      (GFX_DSCALE),a
                jr      gdo_next

; --- A n: angle 0..3 = 0/90/180/270 degrees.
gdo_a:
                call    gdrw_arg_req
                ld      hl,(GFX_DARG)
                ld      a,h
                or      a
                jp      nz,gdrw_err5
                ld      a,l
                cp      4
                jp      nc,gdrw_err5        ; A > 3 -> ERR 5 (measured)
                ld      (GFX_DANGLE),a
                jr      gdo_next

; --- U D L R E F G H: move `n` (default 1) in the letter's direction; E F G H
; move n in BOTH axes. C = the letter's index into gdrw_dirvec.
gdo_dir:
                ld      hl,gdrw_dirvec
                ld      b,0
                sla     c                   ; 2 bytes per entry: [sx][sy]
                add     hl,bc
                push    hl                  ; -> the (sx,sy) pair
                call    gdrw_arg_opt        ; count; absent -> 1 (measured: bare `U` = 1)
                call    gdrw_scale          ; GFX_DARG = the scaled, signed distance
                pop     hl
                ld      a,(hl)
                inc     hl
                ld      b,(hl)              ; A = sx, B = sy  (each -1 / 0 / +1)
                push    bc
                call    gdrw_axis           ; HL = sx * distance
                ld      (GFX_DDX),hl
                pop     bc
                ld      a,b
                call    gdrw_axis           ; HL = sy * distance
                ld      (GFX_DDY),hl
                call    gdrw_rotate         ; the angle applies to RELATIVE motion (§4)
                call    gdrw_move_rel
                jr      gdo_next

; --- end of one command: an optional single ';' terminates it. A LEADING ';', a
; doubled ';;' or a ',' between commands is ERR 5 (measured) -- which falls out
; of consuming at most one here and letting the next dispatch reject the rest.
gdo_next:
                call    gdrw_peek     
                jp      c,gdo_frame_end
                call    gdrw_peek
                cp      ';'
                jp      nz,gdo_loop
                call    gdrw_getc           ; consume the terminator
                jp      gdo_loop

; --- a frame ran out: pop back to the X that pushed it, or finish -----------
gdo_frame_end:
                ld      a,(GFX_DFTOP)
                dec     a
                jr      z,gdo_done          ; frame 0 exhausted -> the statement is done
                ld      (GFX_DFTOP),a
                dec     a
                add     a,a
                add     a,a                 ; 4 B per saved frame
                ld      e,a
                ld      d,0
                ld      hl,GFX_DFSTK
                add     hl,de
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                ld      (GFX_DPTR),de       ; the outer frame's cursor (past its ';')
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                ld      (GFX_DEND),de
                jp      gdo_loop
gdo_done:
                xor     a
                ld      (GFX_DREQ),a        ; nothing left to resolve -> the resident stops
                di                          ; leave the EI region before returning via CALSLT
                ret

; --- exit to the resident to have ONE substitution resolved -----------------
; in: A = the request kind (1 = int, 2 = string). The name text is already in
; GFX_DEXP. The cursor rewinds to the command start, so the re-entry simply
; re-parses this command with the value banked (spec §7 / D-G6-1b).
gdo_want:
                ld      (GFX_DREQ),a
                ld      hl,(GFX_DCMD)
                ld      (GFX_DPTR),hl
                ld      sp,(GFX_DSP)        ; reached from deep inside the parser
                di
                ret

; --- X expr$; -- execute a substring -----------------------------------------
; Measured: it executes, continues after the ';', nests, state set inside it
; PERSISTS on return, and an empty string is a no-op. Pushing a frame gives all
; five for free -- the persistent S/A/colour cells are simply never saved.
gdo_x:
                call    gdrw_sub_scan       ; text -> GFX_DEXP; cursor past the ';';
                                            ; CF=1 iff a resolved value is waiting
                jr      c,gdo_x_have
                ld      a,2                 ; ask the resident for a STRING
                jr      gdo_want
gdo_x_have:
                ld      (GFX_DVAL),hl       ; the string's body address
                ld      a,(GFX_DSUBLEN)
                ld      (GFX_DVLEN),a
                or      a
                jp      z,gdo_next          ; empty string -> nothing to execute
                call    gdrw_pushframe
                jp      gdo_loop

; ---------------------------------------------------------------------------
; gdrw_pushframe -- copy the string at (GFX_DVAL, GFX_DVLEN bytes) onto the end
; of GFX_DBUF and make it the current frame, saving the outer frame's cursor.
; Copying is what makes the co-routine safe: the resident's eval between round
; trips can reuse the temp-string pool a DRAW argument may live in, so reading a
; body in place across a round trip would be a use-after-free.
; ---------------------------------------------------------------------------
gdrw_pushframe:
                ld      a,(GFX_DFTOP)
                or      a
                jr      z,gpf_no_save       ; frame 0 has no outer frame to save
                cp      GFX_DFCAP
                jp      nc,gdrw_err5        ; X nested too deep (own-design cap, D-G6-4)
                dec     a
                add     a,a
                add     a,a
                ld      e,a
                ld      d,0
                ld      hl,GFX_DFSTK
                add     hl,de
                ld      de,(GFX_DPTR)
                ld      (hl),e
                inc     hl
                ld      (hl),d
                inc     hl
                ld      de,(GFX_DEND)
                ld      (hl),e
                inc     hl
                ld      (hl),d
gpf_no_save:
                ld      a,(GFX_DFTOP)
                inc     a
                ld      (GFX_DFTOP),a
                ; --- append the body at GFX_DFREE ---
                ld      de,(GFX_DFREE)
                ld      (GFX_DPTR),de       ; the new frame starts here
                ld      hl,(GFX_DVAL)
                ld      a,(GFX_DVLEN)
                or      a
                jr      z,gpf_empty
                ld      b,a
gpf_copy:
                ld      a,(hl)
                ld      (de),a
                inc     hl
                inc     de
                push    hl
                ld      hl,GFX_DBUF + GFX_DBUF_CAP
                or      a
                sbc     hl,de
                pop     hl
                jp      c,gdrw_err5         ; the frames outgrew the buffer (D-G6-4)
                djnz    gpf_copy
gpf_empty:
                ld      (GFX_DEND),de
                ld      (GFX_DFREE),de
                ret

; ---------------------------------------------------------------------------
; gdrw_sub_scan -- at a `=`/`X` argument: copy the text up to the next ';' into
; GFX_DEXP (NUL-terminated) and advance the cursor past that ';'. No ';' before
; the frame ends -> ERR 5, exactly the measured `DRAW"U=V"` / `DRAW"XA$"`.
; out: CF=1 and HL = the value the resident already resolved for this position;
;      CF=0 if it has not been resolved yet (the caller must request it).
; ---------------------------------------------------------------------------
gdrw_sub_scan:
                ld      de,GFX_DEXP
                ld      b,GFX_DEXP_CAP
gss_lp:
                call    gdrw_peek_raw       ; the name is DATA: no upcasing
                jp      c,gdrw_err5         ; frame ended with no ';'
                cp      ';'
                jr      z,gss_end
                ld      (de),a
                inc     de
                call    gdrw_bump
                djnz    gss_lp
                jp      gdrw_err5           ; longer than the expression scratch
gss_end:
                call    gdrw_bump           ; consume the ';'
                xor     a
                ld      (de),a              ; NUL-terminate for the resident's eval
                ; --- is this position's value already resolved? ---
                ld      a,(GFX_DSUBI)
                ld      c,a
                ld      a,(GFX_DSUBN)
                cp      c
                ret     z                   ; CF=0: not yet -- the caller requests it
                ld      a,c
                add     a,a
                ld      e,a
                ld      d,0
                ld      hl,GFX_DSUB
                add     hl,de
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                ld      a,c
                inc     a
                ld      (GFX_DSUBI),a       ; this slot is now consumed
                ex      de,hl               ; HL = the banked value
                scf
                ret

; --- M: absolute when the FIRST operand has no sign prefix, relative when it is
; '+'/'-' prefixed -- and then the SECOND operand's prefix is optional (measured:
; `M+20,10` is relative in both axes, `M20,+10` is absolute in both).
gdo_m:
                call    gdrw_arg_signed     ; -> GFX_DARG, A = 1 iff a sign was present
                ld      hl,(GFX_DARG)
                ld      (GFX_DTX),hl        ; provisional: absolute target X
                push    af
                call    gdrw_peek     
                jr      c,gdo_m_syn
                call    gdrw_getc
                cp      ','
                jr      nz,gdo_m_syn        ; `M100` (no 2nd operand) -> ERR 5 (measured)
                call    gdrw_arg_signed
                ld      hl,(GFX_DARG)
                ld      (GFX_DTY),hl
                pop     af
                or      a
                jp      z,gdo_m_abs         ; no sign on operand 1 -> absolute move
                ; --- relative: both operands are scaled AND rotated ---
                ld      hl,(GFX_DTX)
                ld      (GFX_DARG),hl
                call    gdrw_scale
                ld      hl,(GFX_DARG)
                ld      (GFX_DDX),hl
                ld      hl,(GFX_DTY)
                ld      (GFX_DARG),hl
                call    gdrw_scale
                ld      hl,(GFX_DARG)
                ld      (GFX_DDY),hl
                call    gdrw_rotate
                call    gdrw_move_rel
                jp      gdo_next
gdo_m_syn:
                jr      gdrw_err5
gdo_m_abs:
                ; absolute: neither the scale nor the angle applies (both measured)
                call    gdrw_move_abs
                jp      gdo_next

; ---------------------------------------------------------------------------
; gdrw_err5 -- every parse/range rejection lands here. The tenant's entry SP is
; restored so a helper nested any number of calls deep can just jump here.
; ---------------------------------------------------------------------------
gdrw_err5:
                ld      sp,(GFX_DSP)
                ld      a,5                 ; Illegal function call (the whole §5 table
                ld      (GFX_RES),a         ; is ERR 5 bar the resident's Type mismatch)
                jp      gdo_done

; --- direction letters, and their unit vectors (E F G H move in BOTH axes) ---
gdrw_dirtab:    db      'U', 'D', 'L', 'R', 'E', 'F', 'G', 'H'
gdrw_dirvec:    db      0,-1                ; U
                db      0,1                 ; D
                db      -1,0                ; L
                db      1,0                 ; R
                db      1,-1                ; E
                db      1,1                 ; F
                db      -1,1                ; G
                db      -1,-1               ; H

; ---------------------------------------------------------------------------
; gdrw_axis -- in: A = a unit sign (-1/0/+1), GFX_DARG = distance.
; out: HL = sign * distance. Clobbers A/DE.
; ---------------------------------------------------------------------------
gdrw_axis:
                ld      hl,0
                or      a
                ret     z                   ; sign 0 -> no motion on this axis
                ld      hl,(GFX_DARG)
                inc     a
                ret     nz                  ; sign was +1 (A was $FF+1=0 only for -1)
                jp      gdrw_negate_hl      ; sign -1 -> HL = -distance

; ---------------------------------------------------------------------------
; gdrw_rotate -- apply the persistent angle to (GFX_DDX,GFX_DDY). One 90-degree
; step is (dx,dy) -> (dy,-dx): measured, A1 turns U into L and E into H.
; ---------------------------------------------------------------------------
gdrw_rotate:
                ld      a,(GFX_DANGLE)
                or      a
                ret     z
                ld      b,a
gdrw_rot_step:
                push    bc
                ld      hl,(GFX_DDX)
                ld      (GFX_DTMP),hl       ; stash the old dx
                ld      hl,(GFX_DDY)
                ld      (GFX_DDX),hl        ; dx' = dy
                ld      hl,(GFX_DTMP)
                call    gdrw_negate_hl
                ld      (GFX_DDY),hl        ; dy' = -dx
                pop     bc
                djnz    gdrw_rot_step
                ret

; ---------------------------------------------------------------------------
; gdrw_negate_hl -- HL = -HL.
; ---------------------------------------------------------------------------
gdrw_negate_hl:
                ld      a,h
                cpl
                ld      h,a
                ld      a,l
                cpl
                ld      l,a
                inc     hl
                ret

; ---------------------------------------------------------------------------
; gdrw_scale -- the measured scale arithmetic (spec §3, the pin that reproduces
; every large-count wrap AND the negative rounding):
;
;     distance = signed16( (n * S) mod 65536 ) / 4, truncating TOWARD ZERO
;
; in/out: GFX_DARG. The product is taken mod 65536 deliberately -- that wrap is
; exactly what makes `U32767` move DOWN one pixel on the reference.
;
; TWO measured departures from that one-line model, both D-DSCALE
; (docs/spec-basic-lineerr.md §12), neither one visible without a LARGE count:
;
;   * S = 0 is the NEVER-SET state, not `S4`. From boot both references move the
;     full count -- `DRAW"BU40000"` moves 40000, `DRAW"S4BU40000"` moves 7232 --
;     so the multiply does not run at all until an `S` has been executed. The
;     cell starts at 0 (basic/interp.asm cold-boot hook) and `gdo_s` maps `S0`
;     to 4, so 0 is a sentinel no explicit `S` can collide with.
;   * The sign boundary is $8001, NOT $8000. `$FFFC` reads as -4 (S4U32767
;     moves DOWN 1) but `$8000` reads as +32768 (S4U8192 moves UP 8192, and so
;     do S2U16384 / S8U4096 / S1U32768 / S4U24576 / S4U-8192 -- five (n,S) pairs
;     at the same product). $8000 is the ONE 16-bit value that is its own two's
;     -complement negation, which is why the twelve points §3's model was fitted
;     and falsified on never saw it.
; ---------------------------------------------------------------------------
gdrw_scale:
                ld      a,(GFX_DSCALE)
                or      a
                ret     z                   ; NEVER SET: no multiply, no divide --
                                            ; GFX_DARG passes straight through
                ld      de,(GFX_DARG)
                ld      hl,0
                ld      b,a
gdrw_sc_mul:
                add     hl,de               ; HL = n * S, mod 65536 by construction
                djnz    gdrw_sc_mul
                bit     7,h
                jr      nz,gdrw_sc_neg
gdrw_sc_pos:
                srl     h                   ; non-negative: a plain logical >>2
                rr      l
                srl     h
                rr      l
                jr      gdrw_sc_store
gdrw_sc_neg:
                call    gdrw_negate_hl      ; negative: divide the MAGNITUDE, then negate
                bit     7,h                 ; ...unless the magnitude is STILL
                jr      nz,gdrw_sc_pos      ; negative, which happens for $8000
                                            ; alone: both references read that
                                            ; product as +32768 (measured)
                srl     h                   ; -> truncation toward zero (measured:
                rr      l                   ;    S3U-10 gives 7, not floor's 8)
                srl     h
                rr      l
                call    gdrw_negate_hl
gdrw_sc_store:
                ld      (GFX_DARG),hl
                ret

; ---------------------------------------------------------------------------
; gdrw_move_rel -- target = cursor + (GFX_DDX,GFX_DDY), then draw/move.
; ---------------------------------------------------------------------------
gdrw_move_rel:
                ld      hl,(GRPACX)
                ld      de,(GFX_DDX)
                add     hl,de
                ld      (GFX_DTX),hl
                ld      hl,(GRPACY)
                ld      de,(GFX_DDY)
                add     hl,de
                ld      (GFX_DTY),hl
                ; fall through

; ---------------------------------------------------------------------------
; gdrw_move_abs -- draw (unless B) from the cursor to (GFX_DTX,GFX_DTY), then
; advance the cursor (unless N). Off-screen parts clip by masking, inherited
; from the G3 primitive; GRPAC follows the UNCLIPPED coordinate (measured).
; ---------------------------------------------------------------------------
gdrw_move_abs:
                ld      a,(GFX_DFB)
                or      a
                jr      nz,gdrw_mv_cursor   ; B prefix: move only, and GXPOS is NOT
                                            ; touched by a blank move (measured)
                ld      hl,(GRPACX)
                ld      (GFX_X1),hl
                ld      hl,(GRPACY)
                ld      (GFX_Y1),hl
                ld      hl,(GFX_DTX)
                ld      (GFX_X2),hl
                ld      hl,(GFX_DTY)
                ld      (GFX_Y2),hl
                call    gfx_draw_seg        ; the landed G3 rasteriser (EI already on)
                call    gdrw_gxpos
gdrw_mv_cursor:
                ld      a,(GFX_DFN)
                or      a
                ret     nz                  ; N prefix: the position does not advance
                ld      hl,(GFX_DTX)
                ld      (GRPACX),hl
                ld      hl,(GFX_DTY)
                ld      (GRPACY),hl
                ret

; ---------------------------------------------------------------------------
; gdrw_gxpos -- the GXPOS/GYPOS residue after a drawn segment. MEASURED rule
; (notes §5): the pending-target cells end at whichever endpoint has the GREATER
; y, ties going to the target -- so a downward or horizontal move leaves the
; target there, while an upward move leaves the START there. Same class of
; observable-but-odd residue as G4's `GXPOS=r` quirk; matched because GXPOS is
; PEEKable and it costs a comparison.
; ---------------------------------------------------------------------------
gdrw_gxpos:
                ld      hl,(GFX_DTY)
                ld      de,(GFX_Y1)         ; Y1 = the start y (gfx_draw_seg preserves
                                            ; the marshalled endpoint cells)
                or      a
                sbc     hl,de               ; target.y - start.y
                jp      m,gdrw_gx_start     ; target is HIGHER up -> the start wins
                ld      hl,(GFX_DTX)
                ld      (GXPOS),hl
                ld      hl,(GFX_DTY)
                ld      (GYPOS),hl
                ret
gdrw_gx_start:
                ld      hl,(GFX_X1)
                ld      (GXPOS),hl
                ld      hl,(GFX_Y1)
                ld      (GYPOS),hl
                ret

; ---------------------------------------------------------------------------
; Buffer walking. GFX_DPTR is the cursor, GFX_DEND one past the last byte.
;   gdrw_peek  -- A = the next char (upcased), cursor unmoved; CF=1 at the end
;   gdrw_getc  -- the same, and consumes it (a fetch past the end is ERR 5, not
;                 a silent stop: the only way to reach it is a command whose
;                 required argument ran off the end)
;   (gdrw_skipws-- RETIRED by D-DRAWERR: `gdrw_peek` skips whitespace itself
;                 now, so "skip then peek" and "peek" are the same call.)
; Both preserve BC/DE/HL -- the decimal accumulator in gdrw_arg_try runs in DE
; ACROSS these calls, so a helper that clobbered it would corrupt every
; multi-digit count.
;
; 🔴 D-DRAWERR: "IGNORABLE ANYWHERE" WAS WRITTEN HERE AND IMPLEMENTED NOWHERE
; NEAR ANYWHERE. `gdrw_skipws` had exactly FOUR call sites, all of them BETWEEN
; commands, and `gdrw_arg_try` peeked with no skip in front of it -- so a space
; before, inside or after an argument ended the number. Measured on both
; references, three rows that each fail differently under the old code:
;
;     DRAW"R 10"    -> 17,4   (a space before the argument)      row d.sp.sgn's twin d.spc2
;     DRAW"R1 0"    -> 17,4   (a space INSIDE the number: R10)   row d.sp.num
;     DRAW"M 53,37" -> 53,37  (a space before an M operand)      row d.sp.m1
;
; `DRAW"R1 0"` is the decisive one -- it says the rule is not "skip before an
; argument" but **skip before every character fetch**, which is why the skip
; belongs in `gdrw_peek` itself rather than at the call sites. Its four callers
; now call `gdrw_peek` directly and the separate 16-byte body is gone.
; ⚠️ THE ALIAS `gdrw_skipws equ gdrw_peek` WAS TRIED FIRST AND `make
; subrom-closure-check` REFUSED IT -- correctly. That checker classifies a
; callee by whether it is a LABEL defined in the sub sources, and an `equ`
; carries no section, so the alias resolved to a bare address that read as
; "main BIOS < $2812". Its own docstring already records this hole for
; resident-ABI `equ`s; the remedy is not to widen the checker but not to
; introduce an unclassifiable symbol.
; ⚠️ `gdrw_peek_raw` deliberately does NOT skip: `gdrw_sub_scan` walks a `=var;`
; expression with it, and that text is DATA whose spaces the resident's own
; evaluator must see.
; ---------------------------------------------------------------------------
gdrw_peek_raw:
                push    hl
                push    de
                ld      hl,(GFX_DPTR)
                ld      de,(GFX_DEND)
                or      a
                sbc     hl,de               ; CF=1 iff cursor < end
                ccf                         ; -> CF=1 iff cursor >= end (exhausted)
                jr      c,gdrw_pk_out
                ld      hl,(GFX_DPTR)
                ld      a,(hl)
                or      a                   ; CF=0: a character was returned
gdrw_pk_out:
                pop     de                  ; (pop does not disturb the flags)
                pop     hl
                ret
gdrw_peek:
                call    gdrw_peek_raw
                ret     c
                cp      ' '                 ; D-DRAWERR: whitespace is ignorable
                jr      z,gdrw_pk_ws        ; before EVERY fetch, not just between
                cp      9                   ; commands -- `DRAW"R1 0"` is R10 on
                jr      z,gdrw_pk_ws        ; both references (row d.sp.num)
                cp      'a'
                jr      c,gdrw_pk_ok
                cp      'z'+1
                jr      nc,gdrw_pk_ok
                sub     32                  ; lowercase command letters are accepted
gdrw_pk_ok:
                or      a                   ; CF=0
                ret
gdrw_pk_ws:
                call    gdrw_bump           ; consume it and look again
                jr      gdrw_peek
gdrw_bump:
                push    hl
                ld      hl,(GFX_DPTR)
                inc     hl
                ld      (GFX_DPTR),hl
                pop     hl
                ret
gdrw_getc:
                call    gdrw_peek
                jp      c,gdrw_err5         ; ran off the end mid-command -> ERR 5
                push    af
                call    gdrw_bump
                pop     af
                ret

; ---------------------------------------------------------------------------
; Argument parsing.
;   gdrw_arg_opt    -- optional: a missing argument means 1 (bare `U` = 1)
;   gdrw_arg_req    -- required: a missing argument is ERR 5 (bare `S`/`A`/`C`)
;   gdrw_arg_signed -- required, and returns A=1 iff a '+'/'-' sign was present
;                      (that presence is what makes `M` relative, spec §3)
; All three leave the value in GFX_DARG. A value is either decimal digits or the
; resident pre-pass's GFX_DESC escape (a resolved `=var;`), optionally signed.
; A decimal value above 65535 is ERR 5 (measured: `U99999`).
; ---------------------------------------------------------------------------
gdrw_arg_opt:
                call    gdrw_arg_try
                ret     c                   ; got one
                ld      hl,1
                ld      (GFX_DARG),hl       ; absent -> 1
                ret
gdrw_arg_req:
                call    gdrw_arg_try
                ret     c
                jp      gdrw_err5           ; required argument missing
gdrw_arg_signed:
                call    gdrw_arg_try
                jp      nc,gdrw_err5
                ld      a,(GFX_DTMP)        ; gdrw_arg_try stashed the sign-seen flag
                ret

; gdrw_arg_try -- CF=1 if an argument was parsed (into GFX_DARG), CF=0 if the
; next token is not one. GFX_DTMP = 1 iff a sign prefix was present.
gdrw_arg_try:
                xor     a
                ld      (GFX_DTMP),a        ; no sign seen yet
                ld      (GFX_DTMP+1),a      ; ...and not negative
                call    gdrw_peek
                jp      c,gdrw_at_none      ; end of buffer -> there is no argument
                cp      '+'
                jr      z,gdrw_at_sign
                cp      '-'
                jr      nz,gdrw_at_body
                ld      a,1
                ld      (GFX_DTMP+1),a      ; negate at the end
gdrw_at_sign:
                call    gdrw_getc           ; consume the sign
                ld      a,1
                ld      (GFX_DTMP),a        ; a sign WAS present (M's abs/rel switch)
gdrw_at_body:
                call    gdrw_peek
                jp      c,gdrw_err5         ; a lone sign with no value -> ERR 5
                cp      '='
                jr      z,gdrw_at_sub
                cp      '0'
                jr      c,gdrw_at_none
                cp      '9'+1
                jr      nc,gdrw_at_none
                ; --- decimal digits ---
                ld      de,0
gdrw_at_digit:
                call    gdrw_peek
                jr      c,gdrw_at_end
                cp      '0'
                jr      c,gdrw_at_end
                cp      '9'+1
                jr      nc,gdrw_at_end
                call    gdrw_getc
                sub     '0'
                ld      c,a
                push    bc
                ld      h,d
                ld      l,e
                add     hl,hl               ; *2
                jp      c,gdrw_err5         ; > 65535 -> ERR 5 (measured: U99999)
                ld      b,h
                ld      c,l
                add     hl,hl               ; *4
                jp      c,gdrw_err5
                add     hl,hl               ; *8
                jp      c,gdrw_err5
                add     hl,bc               ; *10
                jp      c,gdrw_err5
                pop     bc
                ld      b,0
                add     hl,bc               ; + the digit
                jp      c,gdrw_err5
                ex      de,hl
                jr      gdrw_at_digit
gdrw_at_end:
                ld      (GFX_DARG),de
                jr      gdrw_at_sign_apply
gdrw_at_sub:
                call    gdrw_getc           ; consume the '='
                call    gdrw_sub_scan       ; text -> GFX_DEXP; cursor past the ';'
                jr      c,gdrw_at_sub_have
                ld      a,1                 ; not resolved yet: ask the resident for an
                jp      gdo_want            ; int16 and re-parse this command on re-entry
gdrw_at_sub_have:
                ld      (GFX_DARG),hl       ; the banked, already-coerced int16
gdrw_at_sign_apply:
                ld      a,(GFX_DTMP+1)
                or      a
                jr      z,gdrw_at_ok
                ld      hl,(GFX_DARG)
                call    gdrw_negate_hl
                ld      (GFX_DARG),hl
gdrw_at_ok:
                scf                         ; CF=1: an argument was parsed
                ret
gdrw_at_none:
                ld      a,(GFX_DTMP)
                or      a
                jp      nz,gdrw_err5        ; a sign with no number -> ERR 5
                or      a                   ; CF=0: there was no argument here
                ret

; ===========================================================================
; G7 -- sprites (docs/spec-basic-graphics-g7.md). GFX_OP = 7 / 8 / 9.
; ===========================================================================
;   GFX_OP = 7  -> gfx_spr_wpat: write pattern entry GFX_SN from GFX_VBUF
;          = 8  -> gfx_spr_rpat: read  pattern entry GFX_SN into GFX_VBUF
;          = 9  -> gfx_spr_attr: merge the given PUT SPRITE arguments into the
;                                attribute entry for plane GFX_SN
;
; THE SPLIT (spec §8): the resident half evaluates -- `eval`, the string heap and
; the token cursor are page-1 resident -- and everything downstream of the values
; is decided HERE, where there is sub-ROM room: the 8/32-byte entry size from
; RG1SAV, the entry address and its `& $3FFF` wrap, the zero-pad, the domain
; checks (which come back as GFX_RES = 5 for the resident to raise), the
; early-clock rule for a negative x, the x4 pattern scaling in 16x16 mode, and
; the merge that makes an omitted argument keep the byte already in the entry.
; That is what keeps the space-blocked resident half small.
;
; VRAM access uses the di-guarded gfx_vram_wr / gfx_vram_rd (the G1 floor
; primitives), so each byte's address latch is atomic against the ISR. At most 32
; bytes move, so these never spin long enough for the EI-during-work question to
; arise (spec §2); they run under the DI CALSLT entered with, like the G2 pixel
; ops. Clean-room: own-design; table addresses + the VDP port contract are
; published hardware documentation, every behavioural rule is our own black-box
; measurement (scratchpad/g7_sprite_notes.md). No disassembly.

; --- gvw_body / gvr_body: move B bytes between VRAM (HL) and RAM (DE) -------
gvw_body:
                ld      a,(de)
                ld      c,a
                call    gfx_vram_wr         ; di-guarded byte (HL/BC/DE preserved)
                inc     hl
                inc     de
                djnz    gvw_body
                ret
gvr_body:
                call    gfx_vram_rd         ; A = VRAM[HL], di-guarded
                ld      (de),a
                inc     hl
                inc     de
                djnz    gvr_body
                ret

; --- gfx_spr_addr: pattern entry GFX_SN -> HL = address, B = entry size -----
; The address is deliberately NOT clamped: `SPRITE$(255)` in 16x16 mode wraps
; inside the 16 KB of VRAM, which is what the reference measurably does (D-G7-5).
; n outside 0..255 -> CF set, GFX_RES = 5.
gfx_spr_addr:
                ld      a,(RG1SAV)
                and     $02                 ; bit 1 = 16x16 (bit 0 is magnification,
                ld      b,8                 ; which does not change the entry size)
                jr      z,gsa_size
                ld      b,32
gsa_size:
                ld      de,(GFX_SN)
                ld      a,d
                or      a
                jr      nz,gfx_spr_err5     ; n < 0 or n > 255 -> ERR 5
                ld      hl,0
                ld      a,b
gsa_mul:
                add     hl,de               ; HL = size * n
                dec     a
                jr      nz,gsa_mul
                ld      de,GFX_SPAT_BASE
                add     hl,de
                ld      a,h
                and     $3F                 ; AND $3FFF -- VRAM wraps, it does not clamp
                ld      h,a
                or      a                   ; CF = 0: address valid
                ret
gfx_spr_err5:
                ld      a,5                 ; the resident raises this as ERR 5
                ld      (GFX_RES),a
                scf
                ret

; --- gfx_spr_wpat: GFX_OP = 7, SPRITE$(n) = <string> -----------------------
; The resident supplies the first min(len,32) body bytes in GFX_VBUF and their
; count in GFX_VLEN; the rest of the entry is zero-padded here (a short string
; pads, a long one was already truncated by the copy).
gfx_spr_wpat:
                call    gfx_spr_addr
                ret     c
                push    hl                  ; [entry address]
                push    bc                  ; [entry size]
                ; stage the entry: the resident hands over the string DESCRIPTOR
                ; ([len][ptr] in page-3 RAM, which this page can read), so the copy,
                ; the truncate and the zero-pad all happen here.
                ld      hl,(GFX_SDESC)
                ld      a,(hl)
                inc     hl
                ld      c,a                 ; C = the assigned length
                ld      a,(hl)
                inc     hl
                ld      h,(hl)
                ld      l,a                 ; HL = body address
                ld      de,GFX_VBUF
                ld      b,32
gsw_lp:
                ld      a,c
                or      a
                jr      z,gsw_zero          ; body exhausted -> zero-pad the rest
                dec     c
                ld      a,(hl)
                inc     hl
                jr      gsw_put
gsw_zero:
                xor     a
gsw_put:
                ld      (de),a
                inc     de
                djnz    gsw_lp              ; a longer string is simply never read
                pop     bc                  ; [entry size]
                pop     hl                  ; [entry address]
                ld      de,GFX_VBUF
                jp      gvw_body            ; B = the entry size

; --- gfx_spr_rpat: GFX_OP = 8, A$ = SPRITE$(n) -----------------------------
; Always hands back EXACTLY the entry size (8 or 32) -- never the length that was
; assigned. The resident allocates a temp string of GFX_VLEN and copies GFX_VBUF.
gfx_spr_rpat:
                call    gfx_spr_addr
                ret     c
                ld      a,b
                ld      (GFX_VLEN),a
                ld      de,GFX_VBUF
                jp      gvr_body

; --- gfx_spr_attr: GFX_OP = 9, PUT SPRITE ----------------------------------
; A read-modify-write of the 4-byte entry [y][x][pattern][colour], because every
; argument but the plane is optional and an omitted one keeps the byte that is
; already there. Coordinates are stored MOD 256, with no clip and no error --
; unlike every other graphics statement in the arc.
gfx_spr_attr:
                ld      hl,(GFX_SN)
                ld      a,h
                or      a
                jr      nz,gfx_spr_err5
                ld      a,l
                cp      32
                jr      nc,gfx_spr_err5     ; plane > 31 -> ERR 5
                ld      h,0
                add     hl,hl
                add     hl,hl
                ld      de,GFX_SATR_BASE
                add     hl,de
                push    hl                  ; [entry address]
                ld      de,GFX_VBUF
                ld      b,4
                call    gvr_body            ; the merge base = the current entry
                ld      a,(GFX_SFLAGS)
                bit     0,a
                jr      z,gsat_colour       ; coordinates omitted -> keep y AND x
                ld      a,(GYPOS)
                ld      (GFX_VBUF),a        ; y, mod 256
                ld      a,(GFX_VBUF+3)
                and     $7F                 ; x >= 0 clears the early-clock bit again
                ld      c,a
                ld      hl,(GXPOS)
                ld      a,h
                or      a
                jp      p,gsat_xpos
                ld      a,l                 ; negative x: attr_x = (x + 32) AND $FF ...
                add     a,32
                ld      l,a
                ld      a,c
                or      $80                 ; ... and the early-clock bit goes on
                ld      c,a
gsat_xpos:
                ld      a,l
                ld      (GFX_VBUF+1),a
                ld      a,c
                ld      (GFX_VBUF+3),a
gsat_colour:
                ld      a,(GFX_SFLAGS)
                bit     1,a
                jr      z,gsat_pattern
                ld      hl,(GFX_SC)
                ld      a,h
                or      a
                jr      nz,gsat_err5
                ld      a,l
                cp      16
                jr      nc,gsat_err5        ; colour > 15 -> ERR 5
                ld      c,a
                ld      a,(GFX_VBUF+3)
                and     $80                 ; keep the early-clock bit just computed
                or      c
                ld      (GFX_VBUF+3),a
gsat_pattern:
                ld      a,(GFX_SFLAGS)
                bit     2,a
                jr      z,gsat_store
                ld      hl,(GFX_SPATN)
                ld      a,h
                or      a
                jr      nz,gsat_err5        ; negative / > 255 -> ERR 5
                ld      a,(RG1SAV)
                and     $02
                ld      a,l
                jr      z,gsat_pat_ok       ; 8x8: stored as-is, domain 0..255
                cp      64
                jr      nc,gsat_err5        ; 16x16: domain 0..63 ...
                add     a,a                 ; ... and the stored byte is 4n
                add     a,a
gsat_pat_ok:
                ld      (GFX_VBUF+2),a
gsat_store:
                pop     hl                  ; [entry address]
                ld      de,GFX_VBUF
                ld      b,4
                jp      gvw_body
gsat_err5:
                pop     hl                  ; drop the guarded entry address
                jp      gfx_spr_err5

; --- gfx_spr_xsave / gfx_spr_xrest: GFX_OP = 10 / 11 -----------------------
; A mode set initialises the 32 attribute entries to y=209, pattern=plane and
; colour=FORCLR -- and measurably LEAVES THE X BYTE ALONE, so a stale x survives
; `SCREEN 2`. Our runtime's mode set is C-BIOS CHGMOD, which was measured doing
; the same init EXCEPT that it also zeroes x (scratchpad/g7_chgmod_init.py). The
; resident therefore brackets its CHGMOD with these two: snapshot the 32 x bytes
; into GFX_VBUF, then put them back. Everything else about the init already
; matches, so nothing is re-implemented here that the BIOS already gets right.
gfx_spr_xsave:
                ld      hl,GFX_SATR_BASE+1  ; the x byte of plane 0
                ld      de,GFX_VBUF
                ld      b,32
gsxs_lp:
                call    gfx_vram_rd
                ld      (de),a
                inc     de
                jr      gsxs_step
gfx_spr_xrest:
                call    gfx_spr_size_apply  ; re-apply SCREEN's sprite-size bits, which
                                            ; CHGMOD has just overwritten in register 1
                ld      hl,GFX_SATR_BASE+1
                ld      de,GFX_VBUF
                ld      b,32
gsxr_lp:
                ld      a,(de)
                ld      c,a
                call    gfx_vram_wr
                inc     de
                inc     hl                  ; 4 bytes per attribute entry
                inc     hl
                inc     hl
                inc     hl
                djnz    gsxr_lp
                ret
gsxs_step:
                inc     hl
                inc     hl
                inc     hl
                inc     hl
                djnz    gsxs_lp
                ret

; --- gfx_spr_size_apply: GFX_OP = 12 -- SCREEN's sprite size -> VDP register 1
; The size bits live in RG1SAV 1..0 and must survive CHGMOD, which rewrites the
; register from its own table (spec G7 §5). The write is a direct port pair here
; rather than BIOS WRTVDP: a page-0 tenant has no BIOS, and this island exists
; precisely to own the VDP ports. RG1SAV is updated to match, so anything that
; reads the mirror (the entry-size and pattern-scaling paths above) agrees.
gfx_spr_size_apply:
                ld      a,(RG1SAV)
                and     $FC
                ld      c,a
                ld      a,(GFX_SSIZE)
                and     $03
                or      c
                ld      (RG1SAV),a
                di                          ; the 2-byte register write is one latch unit
                out     (VDP_ADDR),a
                ld      a,$81               ; $80 | 1 = "write VDP register 1"
                out     (VDP_ADDR),a
                ei
                ret

; ===========================================================================
; G8 -- VDP(n)= and BASE(n)= (docs/spec-basic-graphics-g8.md).
; The READ halves are resident (plain work-area fetches, expr.asm); only the
; WRITES land here, because only this island owns the VDP ports. Both ops take
; the index in GFX_G8N and the value in GFX_G8V, and report a domain miss the
; way every other graphics tenant op does: GFX_RES = the ERR code, 0 = ok.
; ===========================================================================

; --- gfx_vdp_wr: GFX_OP = 13 -- VDP(n) = v ---------------------------------
; n in 0..7 (VDP(8) is the read-only status copy -> ERR 5), v in 0..255 after
; the resident's truncating coercion (spec §4.3). The write updates the RAM
; mirror AND the chip -- a mirror-only write would pass every read-back
; assertion while doing nothing, which is what the gate's TIME-freeze teeth
; check exists to catch.
gfx_vdp_wr:
                ld      hl,(GFX_G8N)
                ld      de,(GFX_G8V)
                ld      a,h
                or      a
                jr      nz,g8_err5          ; index outside 0..255 -> ERR 5
                ld      a,l
                cp      8
                jr      nc,g8_err5          ; 8 (read-only) and beyond -> ERR 5
                ld      a,d
                or      a
                jr      nz,g8_err5          ; value outside 0..255 -> ERR 5
                ld      c,l                 ; C = register number
                ld      a,e                 ; A = value
                jp      g8_wrvdp

g8_err5:
                ld      a,5                 ; Illegal function call
                ld      (GFX_RES),a
                ret

; --- g8_wrvdp: A -> VDP register C, RAM mirror included --------------------
; The published WRTVDP contract, reimplemented for a page-0 island (there is no
; BIOS to call here). The two port writes are ONE latch unit, so an ISR status
; read cannot land between them -- the arc-wide D2 race. Clobbers HL, B.
g8_wrvdp:
                ld      hl,RG0SAV
                ld      b,0
                add     hl,bc
                ld      (hl),a              ; mirror first: readers see the new value
                di
                out     (VDP_ADDR),a
                ld      a,c
                or      $80                 ; $80 | n = "write VDP register n"
                out     (VDP_ADDR),a
                ei
                ret

; --- gfx_base_wr: GFX_OP = 14 -- BASE(n) = v -------------------------------
; Validate (spec §4.4 step 1), store the word, and -- only when the slot's group
; is the current screen mode -- reprogram R0..R6 (step 4).
gfx_base_wr:
                ld      hl,(GFX_G8N)
                ld      a,h
                or      a
                jr      nz,g8_err5
                ld      a,l
                cp      20
                jr      nc,g8_err5          ; n outside 0..19 -> ERR 5
                call    g8_group            ; A = n mod 5 (slot kind), B = group
                ld      c,a                 ; C = slot kind
                ld      de,(GFX_G8V)
                ld      a,d
                and     $C0
                jr      nz,g8_err5          ; negative or >= $4000 -> ERR 5
                call    g8_grain            ; HL = grain-1, the alignment mask
                ld      a,e
                and     l
                jr      nz,g8_err5
                ld      a,d
                and     h
                jr      nz,g8_err5          ; not a multiple of the grain -> ERR 5
                ; --- store the word at BASETAB + 2n
                ld      hl,(GFX_G8N)
                add     hl,hl
                ld      bc,BASETAB
                add     hl,bc
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ; --- reprogram only when the slot's group IS the current mode
                ld      a,(GFX_G8N)
                call    g8_group            ; B = the slot's group
                ld      a,(SCRMOD)
                cp      b
                ret     nz                  ; cross-group write: stored, nothing programmed
                ; fall through with A = SCRMOD

; --- g8_reprogram: program R0..R6 from a group's five table words ----------
; IN: A = the current screen mode. THE SOURCE GROUP IS g8_gmap[mode], not the
; mode itself: SCREEN 1 programs from group 2 and SCREEN 2 from group 3,
; ignoring the register the written slot owns. That is the reference's own
; behaviour -- measured and poison-tested (spec §4.4) -- and reproducing it is
; signed-off decision D8-1. R7 is untouched, and R0/R1 keep every non-mode bit,
; so a `SCREEN 2,1` sprite size survives a BASE write (measured).
g8_reprogram:
                ld      hl,g8_gmap
                ld      e,a
                ld      d,0
                add     hl,de
                ld      a,(hl)              ; A = source group g
                ld      (GFX_G8N),a         ; stash it: the mask + mode-bit decisions
                                            ; below need it, and the marshalled index
                                            ; has done its job by now
                ; IX = BASETAB + 10g (the group's five words)
                ld      l,a
                ld      h,0
                ld      d,h
                ld      e,l
                add     hl,hl               ; 2g
                add     hl,hl               ; 4g
                add     hl,de               ; 5g
                add     hl,hl               ; 10g
                ld      de,BASETAB
                add     hl,de
                push    hl
                pop     ix
                ; --- R2..R6, each the group's word divided by its granularity.
                ; Unrolled: five rows of a table-driven loop cost more here than
                ; they save, and this reads as the spec's own table.
                ld      l,(ix+0)
                ld      h,(ix+1)
                ld      b,10
                ld      c,2                 ; R2 = name / $400
                call    g8_wrshifted
                ld      l,(ix+2)
                ld      h,(ix+3)
                ld      b,6
                ld      c,3                 ; R3 = colour / $40
                call    g8_wrshifted
                ld      l,(ix+4)
                ld      h,(ix+5)
                ld      b,11
                ld      c,4                 ; R4 = pattern generator / $800
                call    g8_wrshifted
                ld      l,(ix+6)
                ld      h,(ix+7)
                ld      b,7
                ld      c,5                 ; R5 = sprite attribute / $80
                call    g8_wrshifted
                ld      l,(ix+8)
                ld      h,(ix+9)
                ld      b,11
                ld      c,6                 ; R6 = sprite pattern generator / $800
                call    g8_wrshifted
                ; --- R0/R1: mode bits only, everything else preserved
                ld      a,(RG0SAV)
                and     $FD                 ; clear M3
                ld      e,a
                ld      a,(GFX_G8N)
                cp      2
                ld      a,e
                jr      nz,g8_rp_r0
                or      $02                 ; GRAPHIC 2 -> M3
g8_rp_r0:
                ld      c,0
                call    g8_wrvdp
                ld      a,(RG1SAV)
                and     $E7                 ; clear M1 (bit 4) and M2 (bit 3)
                ld      e,a
                ld      a,(GFX_G8N)
                or      a
                jr      nz,g8_rp_notext
                ld      a,e
                or      $10                 ; group 0 (text) -> M1
                jr      g8_rp_r1
g8_rp_notext:
                cp      3
                ld      a,e
                jr      nz,g8_rp_r1
                or      $08                 ; group 3 (multicolor) -> M2
g8_rp_r1:
                ld      c,1
                jp      g8_wrvdp

; --- g8_wrshifted: HL >> B -> VDP register C (with GRAPHIC 2's low bits) ---
; In GRAPHIC 2 the colour register's low 7 bits and the pattern-generator
; register's low 2 bits must all be 1 (published TMS9918A contract, and
; measured: colour $2000 -> $FF, pattern $0000 -> $03). Only a group-2
; reprogram sees that; every other group divides plainly. Clobbers A, B, HL.
g8_wrshifted:
                srl     h
                rr      l
                djnz    g8_wrshifted
                ld      a,l
                push    af
                ld      a,(GFX_G8N)         ; the source group
                cp      2
                jr      nz,g8_ws_plain
                ld      a,c
                cp      3
                jr      z,g8_ws_colour
                cp      4
                jr      nz,g8_ws_plain
                pop     af
                or      $03                 ; pattern generator
                jp      g8_wrvdp
g8_ws_colour:
                pop     af
                or      $7F                 ; colour table
                jp      g8_wrvdp
g8_ws_plain:
                pop     af
                jp      g8_wrvdp

; --- g8_group: A = n (0..19) -> A = n mod 5, B = n / 5 ---------------------
; A compare ladder over a bounded index: smaller and faster than a divide.
g8_group:
                ld      b,0
g8_grp_lp:
                cp      5
                ret     c
                sub     5
                inc     b
                jr      g8_grp_lp

; --- g8_grain: B = group, C = slot kind -> HL = grain-1 (alignment mask) ---
; name $400, colour $80, pattern $800, sprite attribute $80, sprite pattern
; $800 -- except that in GROUP 2 the colour and pattern bases are $2000-granular,
; the one place the table is not uniform (measured, spec §4.4). Preserves BC/DE.
g8_grain:
                push    de
                ld      hl,g8_graintab
                ld      d,0
                ld      e,c
                add     hl,de
                add     hl,de
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                ex      de,hl               ; HL = the plain grain mask
                ld      a,b
                cp      2
                jr      nz,g8_gr_done
                ld      a,c
                cp      1
                jr      z,g8_gr_g2
                cp      2
                jr      nz,g8_gr_done
g8_gr_g2:
                ld      hl,$1FFF            ; group 2 colour/pattern: $2000-granular
g8_gr_done:
                pop     de
                ret

; The screen mode -> the group the reprogram actually READS. Modes 0 and 3 read
; their own; SCREEN 1 reads group 2 and SCREEN 2 reads group 3. The reference's
; whole off-by-one is this one table (spec §4.4, poison-tested).
g8_gmap:        db      0, 2, 3, 3
g8_graintab:    dw      $03FF, $007F, $07FF, $007F, $07FF
