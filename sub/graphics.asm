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
                dec     a
                jp      z,gfx_plot          ; GFX_OP == 1
                dec     a
                jp      z,gfx_point         ; GFX_OP == 2
                dec     a
                jp      z,gfx_line_op       ; GFX_OP == 3 (LINE / box -- G3)
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
; target into GXPOS/GYPOS. Reads the pattern bit and the group colour byte and
; returns the fg nibble if the bit is set, else the bg nibble. Read-only: writes
; no work-area cell (POINT does not move the last-referenced point).
; ===========================================================================
gfx_point:
                ld      a,(GXPOS)
                ld      e,a
                ld      a,(GYPOS)
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
