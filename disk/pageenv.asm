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
; those page-0 cells pointing at OUR OWN handlers. The SYNCHRONOUS handlers (RDSLT/
; WRSLT/CALSLT/ENASLT/CALLF) live here in page 1 and are only ever reached while page 1
; is the disk ROM, so they survive every page-0 change. The MASKABLE-INTERRUPT handler
; is the EXCEPTION (A-3): $0038 fires asynchronously, including AFTER COMMAND.COM
; reclaims page 1 as the TPA (wa_seg_ram) — so it must NOT live in page 1. It is
; installed into always-mapped high RAM (INT_H_HIRAM) and $0038 points there.
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
                ; A-3: install the maskable-interrupt handler into ALWAYS-MAPPED high RAM
                ; ($DDAE) BEFORE pointing $0038 at it, so the first interrupt after the
                ; COMMAND.COM handoff (page 1 -> RAM) has a live handler instead of $FF
                ; (tier2-a3-spec.md). Interrupts are OFF here; page 1 (LDIR source) is
                ; mapped; page 3 (dest) is RAM. Clobbers A/BC/DE/HL like the loop below.
                ld      hl, int_h_hiram_tmpl
                ld      de, INT_H_HIRAM
                ld      bc, int_h_hiram_end - int_h_hiram_tmpl
                ldir
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
; p0_env_tab (cell, handler pairs; terminated by a 0 cell) now lives in the free
; tail (runtime.asm) — M22a freed $41D6..$41F2 (the table's own span + the
; $0030 entry's 3-byte `jp callf_body_body` veneer) to make room for the BDOS
; $0C CPMVER canonical page-1 entry at $41EF, which the shared kernel calls
; directly. Previously un-wired: the CALL landed on the table's own zero-
; terminator byte and NOP-slid into the CALLF veneer, which misparsed 3 kernel
; CODE bytes as a CALLF operand and warm-booted the machine by GTIME
; (docs/tier2-m22-cpmver-spec.md §4.1). The table's $0030 entry now points
; DIRECTLY at callf_body_body (label reference, position-free); moving the
; table or deleting the veneer changes nothing about lay_page0_env's own loop.
                ds      $41EF - $, $00      ; pad (frees the old table tail + callf_body jp)
k_41EF:
                jp      cpmver_body         ; $41EF: BDOS $0C CPMVER canonical entry (M22a)
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
; 🔴 D-DOSMODE40 (2026-10-10): A PAGE-0 TARGET IS NOT MAPPED -- page 0 is DOS's RAM.
; COMMAND.COM's `MODE 40` calls INITXT ($006C, slot 0) through here, and the bare
; `jp (ix)` this was ran DOS's RAM at $006C instead: LINL40 changed, the screen did
; not (scratchpad/dosmode_run.out, dosmode_trace.out). The body moved to the fill
; above `ds $5FE5` (calslt_body, kernel.asm); this slot keeps its 13 bytes so dskio
; stays at its canonical offset.
calslt_h:
                jp      calslt_body
                ds      10, $00         ; net-zero: the old body's 13 bytes

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
                ; D-INTHDEAD (2026-09-09): the `jp int_h_body` that lived here is GONE
                ; with its body. $0038 has pointed at INT_H_HIRAM since A-3 --
                ; `p0_env_tab` says so in its own entry, "(NOT page-1 int_h: page 1 is
                ; reclaimed by the TPA)" -- so nothing has reached this label since.
                ; ⚠️ THE SIX BYTES STAY. The slot is what keeps dskio at its canonical
                ; offset; reclaiming them is an address shift, which is a different
                ; change with a different gate to satisfy.
                ds      6, $00          ; net-zero: keep dskio at its canonical offset

