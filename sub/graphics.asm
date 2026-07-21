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
                dec     a
                jp      z,gfx_circle_op     ; GFX_OP == 4 (CIRCLE -- G4)
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
; Arc mask (§5.2): when GFX_ARCF=1, a mirrored+scaled point P=(GFX_PX,GFX_PY)
; (the offset from centre, BEFORE the centre is added back) is kept iff it
; lies in the CCW wedge from the boundary vectors S (GFX_SVX/SVY) to E
; (GFX_EVX/EVY): cross(S,P)>=0 AND cross(P,E)>=0 when the sweep is <=pi
; (GFX_ARCBIG=0), OR when >pi (GFX_ARCBIG=1). All cross-product sign tests
; are INTEGER (gfx_cross_ge0, own 16x16 unsigned multiply + sign-magnitude
; decomposition) -- the tenant has no float, per the arc's own "no tenant
; float" rule (spec §5.2/§9 G4-e). S/E share the SAME r-scaled (and, where
; applicable, minor-scaled) magnitude used for the spoke endpoints (spec
; §5.3) -- an implementation choice where the spec leaves the S/E scale
; unspecified ("scaled to small integers"); see the G4 slice report for the
; rationale (untested combined ellipse+arc case).
;
; REVISED 2026-07-21 (spec §5.2.1): S/E and GFX_ARCBIG are now TENANT-
; computed (gfx_circ_bvec_prep, below), from the resident-marshalled
; GFX_SBRAD/EBRAD (brad) + GFX_SSGNC/SSGNS/ESGNC/ESGNS (quadrant signs) --
; the TRIG-FREE replacement for the original float SIN/COS pipeline, which
; infinite-looped in the sub-ROM math pack's own series fp_mul. Own-design,
; host-fit against every captured arc + boundary re-capture BEFORE coding
; (scratchpad/g4_trigfree_final_model.py: ALL MATCH); ARCBIG's own wrap-
; around fix (gfx_circ_arcbig_calc) is the reason it moved tenant-side too:
; a naive mod-256 boundary diff collapses a near-2*pi sweep (e.g. 0->6.28)
; to a false zero when BOTH ends round to the same 256-bucket, so the
; resolution needs the RAW (unmasked) brad pair, which only the tenant sees
; whole (the resident marshals two separate int16 cells, never subtracts
; them itself).
;
; Bounded-domain note (mirrors spec §4.1's own 16-bit-clean domain, r<=255):
; gfx_mul16u / gfx_cross_ge0 keep only the LOW 16 bits of each product, which
; is exact as long as no factor pair exceeds 65535 -- guaranteed for the
; blessed r<=255 domain (offsets and boundary-vector magnitudes both <=255).
; A radius far outside that domain may mis-rasterise the arc mask (never
; crash) -- the same documented residual as G3's off-screen-span perf note.
; ===========================================================================
gfx_circle_op:
                ei                          ; interrupts LIVE for the (possibly long) draw
                ld      a,(GFX_ARCF)
                or      a
                jr      z,gco_noarc         ; full circle/ellipse -- S/E/ARCBIG unused
                call    gfx_circ_bvec_prep  ; S/E/ARCBIG from GFX_SBRAD/EBRAD (§5.2.1)
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
                di                          ; leave the EI region before returning via CALSLT
                ret

; ===========================================================================
; G4 arc boundary -- TRIG-FREE (spec §5.2.1 REVISED 2026-07-21). Own-design,
; host-fit against every captured VG-8020 arc + boundary re-capture BEFORE
; coding (scratchpad/g4_trigfree_final_model.py: ALL MATCH). Replaces the
; original float SIN/COS pipeline, whose series fp_mul infinite-looped in the
; CIRCLE call context (scratchpad/g4_hang_probe.py). The resident half
; (basic/graphics.asm gfx_circ_boundary_prep) marshals, per boundary (start
; and end): brad = round(|angle|*128/pi) as a RAW/unmasked int16 (ONE bounded
; fp_mul -- not a series), and the quadrant signs sign_c/sign_s ($01/$FF/$00)
; from THREE bounded fp_cmp compares (continuous, NOT derived from brad --
; a brad-derived quadrant collapses the near-cardinal 1.57-vs-1.58 precision
; the reference is shown to preserve, since both round to the identical
; brad=64). This tenant half turns (brad, sign_c, sign_s) into the actual
; vector via an integer quarter-wave sine table (QTAB) -- genuinely no float
; here, per the arc's "no tenant float" rule (spec §5.2/§9 G4-e).
; ===========================================================================

; ---------------------------------------------------------------------------
; QTAB -- 65-entry quarter-wave magnitude table: QTAB[i] = round(256*sin(2*pi*
; i/256)) for i=0..64, CAPPED at 255 (i=62/63/64 round to 256, which overflows
; an unsigned byte -- capping loses <0.4% relative magnitude at those 3
; entries only, verified harmless against the round-to-pixel domain: r=15's
; capped-vs-uncapped magnitude at i=64 both round to 15 -- scratchpad/
; g4_trigfree_final_model.py). Folded via symmetry (gfx_qtab_fold) to cover
; the full 256-entry circle from a 65-byte table -- the letter's "64-entry
; quarter + symmetry" option, chosen to keep the page-0 tenant lean.
; ---------------------------------------------------------------------------
QTAB:
                db      0,   6,  13,  19,  25,  31,  38,  44,  50,  56
                db      62,  68,  74,  80,  86,  92,  98, 104, 109, 115
                db      121, 126, 132, 137, 142, 147, 152, 157, 162, 167
                db      172, 177, 181, 185, 190, 194, 198, 202, 206, 209
                db      213, 216, 220, 223, 226, 229, 231, 234, 237, 239
                db      241, 243, 245, 247, 248, 250, 251, 252, 253, 254
                db      255, 255, 255, 255, 255

; ---------------------------------------------------------------------------
; gfx_qtab_fold -- IN: A = b (any byte 0..255). OUT: A = fold index 0..64
; s.t. QTAB[fold(b)] = round(256*|sin(2*pi*b/256)|) (own-design quarter-wave
; symmetry: m = b mod 128; if m>64 then m := 128-m). Clobbers B.
; ---------------------------------------------------------------------------
gfx_qtab_fold:
                and     $7F
                cp      65
                ret     c                   ; m<=64 -> keep as-is
                ld      b,a
                ld      a,128
                sub     b
                ret

; ---------------------------------------------------------------------------
; gfx_qtab_lookup -- IN: A = b (any byte 0..255). OUT: A = QTAB[fold(b)] =
; round(256*|sin(2*pi*b/256)|), 0..255. Clobbers B, HL, DE.
; ---------------------------------------------------------------------------
gfx_qtab_lookup:
                call    gfx_qtab_fold
                ld      l,a
                ld      h,0
                ld      de,QTAB
                add     hl,de
                ld      a,(hl)
                ret

; ---------------------------------------------------------------------------
; gfx_circ_bvec_mag -- IN: A = tab (0..255, unsigned QTAB value). Uses GFX_R
; (radius, 0..255 domain). OUT: HL = round(r*tab/256) = (r*tab+128)>>8,
; unsigned. The SAME round-half-up 8.8-style shape as gfx_circ_scale.
; Clobbers A, BC, DE.
; ---------------------------------------------------------------------------
gfx_circ_bvec_mag:
                ld      e,a
                ld      d,0
                ld      hl,(GFX_R)
                call    gfx_mul16u          ; HL := r * tab (bounded: <=255*255)
                ld      de,128
                add     hl,de
                ld      l,h
                ld      h,0                 ; HL = (r*tab+128) >> 8
                ret

; ---------------------------------------------------------------------------
; gfx_circ_bvec_nudge -- IN: HL = unsigned magnitude; (GFX_CS_T1) = sign
; ($01/$FF/$00). OUT: HL = the signed, nudged component: 0 if sign=0;
; sign*HL if HL!=0; else +-1 (the near-cardinal nudge, spec §5.4/§5.2.1).
; Clobbers A, BC.
; ---------------------------------------------------------------------------
gfx_circ_bvec_nudge:
                ld      a,(GFX_CS_T1)
                or      a
                jr      z,gcbn_zero
                ld      b,h
                ld      c,l
                ld      a,c
                or      b
                jr      nz,gcbn_apply       ; magnitude != 0 -> apply the sign
                ld      hl,1                ; magnitude==0, sign!=0 -> nudge to +-1
gcbn_apply:
                ld      a,(GFX_CS_T1)
                or      a
                ret     p                   ; sign>=0 ($01) -> HL already correct
                xor     a                   ; negative: two's-complement negate HL
                sub     l
                ld      l,a
                sbc     a,a
                sub     h
                ld      h,a
                ret
gcbn_zero:
                ld      hl,0
                ret

; ---------------------------------------------------------------------------
; gfx_circ_bvec -- compute ONE boundary vector (S or E) from its resident-
; marshalled record. IN: HL = src record base (GFX_SBRAD or GFX_EBRAD:
; brad_lo,brad_hi,signc,signs -- 4 bytes); DE = dest vector base (GFX_SVX or
; GFX_EVX; Y half at dest+2). OUT: (dest)/(dest+2) = the minor-scaled Vx,Vy.
; Magnitude: round(r*QTAB[fold(brad)]/256); cos = sin folded at (brad+64).
; Sign: the resident's continuous quadrant compare (NOT re-derived here --
; see basic/graphics.asm gfx_circ_boundary_prep for why). Nudge: magnitude
; rounds to 0 but sign!=0 -> +-1. Screen convention: Vy = -(sin component).
; The minor-axis 8.8 scale (gfx_circ_scale) is applied to whichever of Vx/Vy
; GFX_ASPMAJ selects -- the SAME rule gfx_circ_emit_point uses for octant
; points. Clobbers everything + GFX_CS_AX/AY/BX/BY/T1 scratch (dead here,
; called only before the octant loop starts).
; ---------------------------------------------------------------------------
gfx_circ_bvec:
                ld      (GFX_CS_AY),de      ; stash dest base
                ld      a,(hl)
                ld      (GFX_CS_AX),a       ; stash bradlo (only byte that matters)
                inc     hl
                inc     hl                  ; skip bradhi
                ld      a,(hl)
                ld      (GFX_CS_BX),a       ; sign_c
                inc     hl
                ld      a,(hl)
                ld      (GFX_CS_BY),a       ; sign_s
                ; --- X = cos component ---
                ld      a,(GFX_CS_AX)
                add     a,64                ; b_cos = bradlo+64 (mod 256, byte wrap)
                call    gfx_qtab_lookup     ; A = |cos| table value
                call    gfx_circ_bvec_mag   ; HL = round(r*A/256)
                ld      a,(GFX_CS_BX)
                ld      (GFX_CS_T1),a
                call    gfx_circ_bvec_nudge ; HL = signed nudged X
                ld      a,(GFX_ASPMAJ)
                or      a
                jr      z,gcbv_x_store
                call    gfx_circ_scale      ; X is minor iff ASPMAJ=1 (y-major)
gcbv_x_store:
                ld      de,(GFX_CS_AY)
                ld      a,l
                ld      (de),a
                inc     de
                ld      a,h
                ld      (de),a
                ; --- Y = sin component ---
                ld      a,(GFX_CS_AX)
                call    gfx_qtab_lookup     ; A = |sin| table value
                call    gfx_circ_bvec_mag   ; HL = round(r*A/256)
                ld      a,(GFX_CS_BY)
                ld      (GFX_CS_T1),a
                call    gfx_circ_bvec_nudge ; HL = signed nudged (pre-negate) Y
                ld      a,(GFX_ASPMAJ)
                or      a
                jr      nz,gcbv_y_scaled
                call    gfx_circ_scale      ; Y is minor iff ASPMAJ=0 (incl. default)
gcbv_y_scaled:
                xor     a                   ; screen convention: Vy = -(sin component)
                sub     l
                ld      l,a
                sbc     a,a
                sub     h
                ld      h,a
                ld      de,(GFX_CS_AY)
                inc     de
                inc     de                  ; dest+2 = Vy cell
                ld      a,l
                ld      (de),a
                inc     de
                ld      a,h
                ld      (de),a
                ret

; ---------------------------------------------------------------------------
; gfx_circ_arcbig_calc -- sets GFX_ARCBIG from GFX_SBRAD/GFX_EBRAD (spec
; §5.2.1 REVISED). diff8 = (brad_e - brad_s) mod 256; ARCBIG = diff8>128,
; EXCEPT: if diff8==0 but the RAW (unmasked) brad_e != brad_s -- a near-full-
; turn wrap where BOTH ends round to the SAME 256-bucket (e.g. start=0,
; end=6.28 -> brad_e=256, brad_s=0; a naive mod-256 diff collapses this to a
; falsely-zero sweep) -- ARCBIG is forced true (a near-2*pi sweep IS >pi).
; Host-fit + validated: scratchpad/g4_trigfree_final_model.py (arc_full628,
; arc_wrap both MATCH only with this fix). Clobbers everything.
; ---------------------------------------------------------------------------
gfx_circ_arcbig_calc:
                ld      hl,(GFX_EBRAD)
                ld      de,(GFX_SBRAD)
                or      a
                sbc     hl,de               ; HL = raw_e - raw_s (16-bit, may be negative)
                ld      a,l                 ; A = diff8 (mod-256 wrap; correct regardless
                                            ; of HL's sign via two's complement)
                or      a
                jr      nz,gac_have_diff8
                ld      a,h
                or      a
                jr      z,gac_small         ; HL==0 exactly -> truly coincident -> small
                ld      a,1                 ; HL!=0 but low byte 0 -> exact-256-wrap -> big
                ld      (GFX_ARCBIG),a
                ret
gac_have_diff8:
                cp      129
                jr      c,gac_small         ; diff8 in 1..128 -> not big
                ld      a,1
                ld      (GFX_ARCBIG),a
                ret
gac_small:
                xor     a
                ld      (GFX_ARCBIG),a
                ret

; ---------------------------------------------------------------------------
; gfx_circ_bvec_prep -- compute S, E (GFX_SVX/SVY/EVX/EVY) and GFX_ARCBIG from
; the resident-marshalled brad/sign records, once per CIRCLE arc call, BEFORE
; the octant loop starts (spec §5.2.1 REVISED). Clobbers everything.
; ---------------------------------------------------------------------------
gfx_circ_bvec_prep:
                ld      hl,GFX_SBRAD
                ld      de,GFX_SVX
                call    gfx_circ_bvec
                ld      hl,GFX_EBRAD
                ld      de,GFX_EVX
                call    gfx_circ_bvec
                jp      gfx_circ_arcbig_calc    ; tail call: ret serves both

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
gco_emit8:
                ld      bc,(GFX_QX)
                ld      de,(GFX_QY)
                call    gfx_circ_emit_point ; (+x,+y)
                ld      bc,(GFX_QX)
                ld      de,(GFX_QY)
                call    gfx_neg16_de
                call    gfx_circ_emit_point ; (+x,-y)
                ld      bc,(GFX_QX)
                call    gfx_neg16_bc
                ld      de,(GFX_QY)
                call    gfx_circ_emit_point ; (-x,+y)
                ld      bc,(GFX_QX)
                call    gfx_neg16_bc
                ld      de,(GFX_QY)
                call    gfx_neg16_de
                call    gfx_circ_emit_point ; (-x,-y)
                ld      bc,(GFX_QY)
                ld      de,(GFX_QX)
                call    gfx_circ_emit_point ; (+y,+x)
                ld      bc,(GFX_QY)
                ld      de,(GFX_QX)
                call    gfx_neg16_de
                call    gfx_circ_emit_point ; (+y,-x)
                ld      bc,(GFX_QY)
                call    gfx_neg16_bc
                ld      de,(GFX_QX)
                call    gfx_circ_emit_point ; (-y,+x)
                ld      bc,(GFX_QY)
                call    gfx_neg16_bc
                ld      de,(GFX_QX)
                call    gfx_neg16_de
                call    gfx_circ_emit_point ; (-y,-x)
                ret

; ---------------------------------------------------------------------------
; gfx_circ_emit_point -- IN: BC=dx (raw octant offset, signed), DE=dy (raw).
; Applies the minor-axis 8.8 scale (GFX_ASPMAJ selects which of dx/dy), the
; arc mask (gfx_circ_keep), and if kept, plots (GFX_CXC+dx',GFX_CYC+dy') via
; gfx_plot_cur (its own clip + DI-guarded RMW). Clobbers everything.
; ---------------------------------------------------------------------------
gfx_circ_emit_point:
                ld      (GFX_PX),bc
                ld      (GFX_PY),de
                ld      a,(GFX_ASPMAJ)
                or      a
                jr      z,gcep_scaley
                ; y-major (aspect>1): the MINOR axis is x
                ld      hl,(GFX_PX)
                call    gfx_circ_scale
                ld      (GFX_PX),hl
                jr      gcep_test
gcep_scaley:
                ; x-major (aspect<=1, incl. the no-scale default): minor is y
                ld      hl,(GFX_PY)
                call    gfx_circ_scale
                ld      (GFX_PY),hl
gcep_test:
                call    gfx_circ_keep       ; CF=1 iff this point survives the arc mask
                ret     nc
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
; ((|v|*GFX_ASPS+128)>>8), the 8.8 minor scale (spec §4.2). Bounded-domain:
; |v|*ASPS assumed <=65535 (true for |v|<=255, ASPS<=256 -- the blessed
; r<=255 domain). Clobbers A, BC, DE.
; ---------------------------------------------------------------------------
gfx_circ_scale:
                call    gfx_abs16           ; HL=|v|, A=sign ($01 pos / $FF neg)
                push    af
                ex      de,hl               ; DE=|v|
                ld      hl,(GFX_ASPS)
                call    gfx_mul16u          ; HL = ASPS * |v|  (HL:=HL*DE)
                ld      de,128
                add     hl,de
                ld      l,h
                ld      h,0                 ; HL = (|v|*ASPS+128) >> 8
                pop     af
                cp      $01
                ret     z                   ; was non-negative -> done
                ; negate HL (own-design two's-complement negate, gfx_abs16's idiom)
                xor     a
                sub     l
                ld      l,a
                sbc     a,a
                sub     h
                ld      h,a
                ret

; ---------------------------------------------------------------------------
; gfx_circ_keep -- IN: GFX_PX/PY = the current (scaled) point P. OUT: CF=1
; iff P should be plotted: always when GFX_ARCF=0 (full circle/ellipse); else
; the arc mask (spec §5.2) -- cross(S,P)>=0 AND cross(P,E)>=0 when
; GFX_ARCBIG=0 (sweep<=pi), OR when GFX_ARCBIG=1 (sweep>pi). Clobbers
; everything + GFX_CS_*/GFX_CS_T1 scratch.
; ---------------------------------------------------------------------------
; G4-arcbnd (pinned, scratchpad/g4_arc_boundary_capture.py): BOTH boundary
; tests are INCLUSIVE (<=0), matched exact (0 diffs) on every pinned arc +
; a 7-point boundary sweep, once combined with the resident's near-zero
; nudge (gfx_round_nonzero, basic/graphics.asm) that keeps S/E direction
; information the reference itself is shown to preserve at near-cardinal
; angles. cross(S,P)<=0 == cross(P,S)>=0 and cross(P,E)<=0 == cross(E,P)>=0
; (anticommutativity), so both reuse gfx_cross_ge0 with swapped arguments --
; no separate "<=0" primitive needed.
gfx_circ_keep:
                ld      a,(GFX_ARCF)
                or      a
                jr      z,gck_keep
                ; --- S-side: cross(S,P)<=0  <=>  cross(P,S)>=0 ---
                ld      hl,(GFX_PX)
                ld      (GFX_CS_AX),hl
                ld      hl,(GFX_PY)
                ld      (GFX_CS_AY),hl
                ld      hl,(GFX_SVX)
                ld      (GFX_CS_BX),hl
                ld      hl,(GFX_SVY)
                ld      (GFX_CS_BY),hl
                call    gfx_cross_ge0
                sbc     a,a                 ; A = $FF if CF=1 else $00
                ld      (GFX_CS_T1),a
                ; --- E-side: cross(P,E)<=0  <=>  cross(E,P)>=0 ---
                ld      hl,(GFX_EVX)
                ld      (GFX_CS_AX),hl
                ld      hl,(GFX_EVY)
                ld      (GFX_CS_AY),hl
                ld      hl,(GFX_PX)
                ld      (GFX_CS_BX),hl
                ld      hl,(GFX_PY)
                ld      (GFX_CS_BY),hl
                call    gfx_cross_ge0
                sbc     a,a
                ld      b,a                 ; B = cross(P,E)<=0 flag
                ld      a,(GFX_CS_T1)       ; A = cross(S,P)<=0 flag
                ld      c,a
                ld      a,(GFX_ARCBIG)
                or      a
                jr      nz,gck_or
                ld      a,c
                and     b
                jr      gck_final
gck_or:
                ld      a,c
                or      b
gck_final:
                or      a
                jr      z,gck_reject
gck_keep:
                scf
                ret
gck_reject:
                or      a
                ret

; ---------------------------------------------------------------------------
; gfx_cross_ge0 -- cross(A,B) = Ax*By - Ay*Bx, reading vector A from
; GFX_CS_AX/AY and vector B from GFX_CS_BX/BY (caller-populated). OUT: CF=1
; iff cross(A,B)>=0. Sign-magnitude decomposition (gfx_abs16 + gfx_mul16u,
; own 16x16->16 unsigned multiply) -- bounded-domain (see this section's
; header). Clobbers AF, BC, DE, HL.
; ---------------------------------------------------------------------------
gfx_cross_ge0:
                ; term1 = |Ax|*|By|, sign1 = sign(Ax) xor sign(By)
                ld      hl,(GFX_CS_AX)
                call    gfx_abs16           ; HL=|Ax|, A=sign1a
                ld      b,a
                ex      de,hl               ; DE=|Ax|
                ld      hl,(GFX_CS_BY)
                call    gfx_abs16           ; HL=|By|, A=sign1b
                xor     b                   ; A=0 (same sign) or nonzero (differ)
                push    af                  ; [stack: sign1 flag]
                ex      de,hl               ; HL=|Ax|, DE=|By|
                call    gfx_mul16u          ; HL := |Ax| * |By| = mag1
                push    hl                  ; [stack: sign1 flag, mag1]
                ; term2 = |Ay|*|Bx|, sign2 = sign(Ay) xor sign(Bx)
                ld      hl,(GFX_CS_AY)
                call    gfx_abs16
                ld      b,a
                ex      de,hl
                ld      hl,(GFX_CS_BX)
                call    gfx_abs16
                xor     b                   ; A = sign2 flag
                push    af                  ; stash it -- gfx_mul16u clobbers BC, so C
                                            ; cannot hold it across the call below
                ex      de,hl               ; HL=|Ay|, DE=|Bx|
                call    gfx_mul16u          ; HL := mag2
                pop     af
                ld      c,a                 ; C = sign2 flag (restored AFTER mul16u)
                pop     de                  ; DE = mag1
                pop     af                  ; A = sign1 flag
                or      a
                jr      nz,gcx_1neg
                ; --- sign1 non-negative (term1 >= 0) ---
                ld      a,c
                or      a
                jr      nz,gcx_keep         ; term1>=0, term2<0 -> sum always >=0
                ; both non-negative: keep iff mag1>=mag2.  HL=mag2, DE=mag1
                ex      de,hl               ; HL=mag1, DE=mag2
                or      a
                sbc     hl,de               ; mag1-mag2 ; CF=1 iff mag1<mag2
                ccf
                ret
gcx_1neg:
                ld      a,c
                or      a
                jr      z,gcx_negpos
                ; both negative: keep iff mag2>=mag1.  HL=mag2, DE=mag1
                or      a
                sbc     hl,de               ; mag2-mag1 ; CF=1 iff mag2<mag1
                ccf
                ret
gcx_negpos:
                ; term1<0, term2>=0: keep only if BOTH magnitudes are zero
                ld      a,h
                or      l
                or      d
                or      e
                jr      nz,gcx_reject
gcx_keep:
                scf
                ret
gcx_reject:
                or      a
                ret

; ---------------------------------------------------------------------------
; gfx_mul16u -- HL := HL * DE, low 16 bits, unsigned (own copy of expr.asm's
; mul16 -- a page-0 tenant cannot reach the main-ROM low region, which is
; swapped OUT for the duration of this CALSLT). Clobbers A, BC, DE.
; ---------------------------------------------------------------------------
gfx_mul16u:
                ld      b,h
                ld      c,l                 ; BC = original HL (multiplicand)
                ld      hl,0
                ld      a,16
gmu_lp:
                add     hl,hl
                ex      de,hl
                add     hl,hl
                ex      de,hl
                jr      nc,gmu_skip
                add     hl,bc
gmu_skip:
                dec     a
                jr      nz,gmu_lp
                ret

; ---------------------------------------------------------------------------
; gfx_neg16_bc / gfx_neg16_de -- two's-complement negate BC / DE in place
; (gfx_abs16's own idiom). Clobbers A.
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
