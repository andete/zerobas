; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; Part of zerobas-disk, included by disk.asm (build with `pasmo -I disk`).
; page-0 DOS environment: lay_page0_env + inter-slot vector handlers + int_h trampoline (Interface B)
; CLEAN-ROOM: every constant, address and algorithm here traces to a public source
; or a black-box oracle probe; nothing is derived from disassembly. See disk/PROVENANCE.md.

; --- step 6: the page-0 MSX-DOS environment (provider-oracle-scope.md §8.4/§8.6)
; With RAM switched into page 0 the page-0 BIOS ROM is gone, so the standard
; inter-slot primitives the boot code + MSXDOS.SYS reach through ($000C RDSLT,
; $0014 WRSLT, $001C CALSLT, $0024 ENASLT, $0030 CALLF) and the maskable-interrupt
; vector ($0038) no longer exist. lay_page0_env writes a JP-vector table into
; those page-0 cells pointing at OUR OWN handlers, which live here in page 1 (slot
; 3-1, never remapped during boot, so they survive every page-0 change).
;
; CLEAN-ROOM: the vector SHAPE is the documented MSX inter-slot layout (MSX2 TH
; ch.2; the §8.6 black-box trace confirmed live cells $000C/$001C/$0024/$0030/
; $0038 in the working boot's page 0). The reference kernel's $DDxx targets are
; opaque and never read/replicated — our targets are our own RAM-resident code.
;
; KEY ADVANTAGE (§8.4): our disk ROM stays in page 1 throughout boot, so the disk
; path needs no real inter-slot switch — the $0030 CALLF handler routes H.PHYD's
; CALLF straight to our DSKIO with a direct call. RDSLT/WRSLT/CALSLT operate on
; the currently-mapped memory (sufficient while the boot's targets — our page-1
; ROM and page-3 work area — stay mapped); ENASLT does a real primary-slot switch.
; If the Tier-1 trap (a3) shows the boot reaches a genuinely-unmapped slot through
; one of these, that handler is deepened then — never by reading the boot code.
lay_page0_env:
                ld      hl, p0_env_tab
lpe_loop:
                ld      e, (hl)
                inc     hl
                ld      d, (hl)
                inc     hl              ; DE = page-0 cell address
                ld      a, d
                or      e
                ret     z               ; cell 0 -> table end
                ld      a, $C3          ; JP opcode
                ld      (de), a
                inc     de
                ld      a, (hl)         ; target low
                ld      (de), a
                inc     hl
                inc     de
                ld      a, (hl)         ; target high
                ld      (de), a
                inc     hl
                jr      lpe_loop
; (cell, handler) pairs; terminated by a 0 cell. No two JP triples overlap.
p0_env_tab:
                dw      $000C, rdslt_h  ; RST 8  RDSLT  (read byte from a slot)
                dw      $0014, wrslt_h  ; RST 10 WRSLT  (write byte to a slot)
                dw      $001C, calslt_h ; RST 18 CALSLT (inter-slot call)
                dw      $0024, enaslt_h ; ENASLT (enable slot in a page)
                dw      $0030, callf_body ; RST 30 CALLF (inter-slot call by inline operand)
                dw      $0038, int_h    ; maskable-interrupt vector
                dw      0               ; end of table

; callf_body — the $0030 RST 30h / CALLF handler (the load-bearing one).
; CALLF is `F7 <slot> <lo> <hi>`: RST 30h pushes the return address (which points
; at the inline operand) and lands here. H.PHYD ($FFA7 = F7 87 10 40 C9) is exactly
; this — every PHYDIO from the boot/DOS reaches our DSKIO through it. The callee
; (DSKIO, $4010) takes A,B,C,DE,HL and CY=read/write, so this handler must deliver
; ALL of them UNTOUCHED. It saves the caller's registers to page-3 scratch, reads
; the operand off the stack to find the target address + the post-operand return,
; then arranges the stack so a plain `ret` jumps to the target with every register
; (and the carry flag) restored, and the target's own RET lands on the byte after
; the operand (H.PHYD's trailing C9). Our disk ROM is in page 1, so the target is
; directly reachable — no real inter-slot switch needed. (§8.4)
; Only `ld`/`inc hl`/`pop`/`push`/`ret` are used between entry and the call, none
; of which touch the flags, so the caller's CY (the DSKIO read/write bit) survives.
callf_body:
                jp      callf_body_body     ; Tier-2 3b: divert; veneer fills the gap
                ds      $41FD - $, $00      ; anchor the canonical address
                jp      k_41FD              ; $41FD: COMMAND.COM-load kernel veneer
                ds      $4217 - $, $00      ; pad to rdslt_h (net-zero: stays $4217)

; rdslt_h ($000C RDSLT) — read the byte at HL. The standard RDSLT takes the slot
; id in A; during boot every address the code reads through RDSLT is in an already-
; mapped page (our page-1 ROM or the page-3 work area), so we read the live memory
; directly. (Deepened in a3 only if a trap shows a genuinely-unmapped target.)
rdslt_h:
                ld      a, (hl)
                ret

; wrslt_h ($0014 WRSLT) — write E to the byte at HL (mapped-memory case, as RDSLT).
wrslt_h:
                ld      (hl), e
                ret

; calslt_h ($001C CALSLT) — inter-slot call to IX (slot id in IYh). The boot's
; CALSLT targets during the DOS load are in already-mapped pages (our page-1 disk
; ROM / page-3 work area), so this calls IX directly while passing A,BC,DE,HL
; through untouched. Stashes HL only to build the return address, then reloads it
; before the jump so the callee sees the caller's HL. (Deepened in a3 if needed.)
calslt_h:
                ld      (CALSLT_HL), hl ; stash HL to free a pair for the return push
                ld      hl, calslt_back
                push    hl              ; return address for the simulated call
                ld      hl, (CALSLT_HL) ; restore caller HL (pass-through intact)
                jp      (ix)            ; "call" IX; its RET lands on calslt_back
calslt_back:
                ret

; enaslt_h ($0024 ENASLT) — enable slot (A = slot id Fx00SSPP) in the page of HL.
; Real primary-slot switch: derive the page from HL bits 15-14 and write the
; matching 2-bit field of $A8 to the slot's primary number. The secondary ($FFFF)
; is left as-is — sufficient for our config, where the only expanded target the
; boot enables (slot 3-1 in page 1) already carries the right secondary (page 1 is
; our ROM throughout). Runs from page 1, so it survives switching any other page.
; Clobbers A,F (ENASLT convention). (Documented simplification; widen in a3 if a
; trap shows an expanded ENASLT to a not-yet-selected secondary.)
enaslt_h:
                push    bc
                push    de
                ld      b, a            ; B = slot id
                ld      a, h
                rlca
                rlca
                and     3
                ld      c, a            ; C = page number (0..3) = shift count
                ld      a, b
                and     3               ; A = primary slot number (low 2 bits)
                ld      e, a            ; E = primary value (to be shifted)
                ld      d, 3            ; D = field mask (to be shifted)
                inc     c               ; +1 so the dec-first loop runs `page` times
ena_shift:
                dec     c
                jr      z, ena_apply
                sla     e
                sla     e               ; primary value <<= 2 per page
                sla     d
                sla     d               ; mask <<= 2 per page
                jr      ena_shift
ena_apply:
                in      a, ($A8)
                ld      b, a            ; B = old $A8
                ld      a, d
                cpl                     ; ~mask
                and     b               ; clear this page's 2-bit field
                or      e               ; OR in the new primary slot
                out     ($A8), a
                pop     de
                pop     bc
                ret

; int_h ($0038) — DOS maskable-interrupt vector while RAM is in page 0 (installed by
; lay_page0_env; per O-1/§8.70 installing $0038 is the disk ROM's job). The body lives
; in the free tail (int_h_body) and chains to the main-BIOS KEYINT (A-2/§8.70): a bare
; VDP ack is NOT enough — the kernel needs H.KEYI/H.TIMI/keyboard/JIFFY, which only the
; main-ROM KEYINT runs. This slot stays 6 bytes (jp + ds 3) so dskio does not shift.
int_h:
                jp      int_h_body      ; -> free-tail main-ROM KEYINT chain (A-2)
                ds      3, $00          ; net-zero: keep dskio at its canonical offset

