; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; keytrap.asm -- the KEY interrupt trap's EVENT SOURCE now lives in the BIOS (D-KEYTRAPREF).
; ===========================================================================
; 2026-11-22 (Joost: "do the key trap properly"): the reference's keyboard scan itself
; diverts a trapped function key, on the published cells -- FNKFLG(n) non-zero and a
; program running -> not typed; its TRPTBL entry ON -> the event bit (bit 2), and not
; STOPped -> ONGSBF := 1 (measured on the VG-8020: scratchpad/keytrapref_vg2.out ..
; keytrapref_vg5.out). The repack's C-BIOS does exactly that (cbios-repack/
; key-trap-bios.patch), so BASIC keeps only its own half: KEY(n) writes FNKFLG
; (basic/trapstmt.asm), the table is the reference's TRPTBL layout (ZTRAP, basic/
; sysvars.inc), TRAPPEND is ONGSBF, and check_traps scans it descending. The old
; zkey_hook (a RAM vector at $FFCF, H_ZKEY, installed at boot) is gone with
; key-trap-hook.patch.
;
; CLEAN-ROOM: the rule is measured black-box on the VG-8020's work-area RAM (FNKFLG, TRPTBL, ONGSBF,
; KEYBUF, CURLIN -- published cells) with keys pressed on the matrix; no reference-ROM byte, no
; disassembly.


; es_latch -- D-BRKLATCH step 2 (2026-11-12), page 0 AFTER the pins (page 1's last
; region had 10 B; basic/input.asm, before the crt_rows pin, has its pad's 3 B): THE latch consumer, called with A = INTFLG
; (non-zero) and HL = the statement about to run, from rp_exec AND from exec_stmt (every
; statement: the VG-8020 broke at the USR's statement, `Break in 20`, where the
; line-start-only check broke one statement later -- scratchpad/brkconsume_run.out). 4 ->
; stop_pause, then on (or 3 from it); 3 -> rp_break below. RETURNS when the program goes
; on (a pause ended, a STOP trap took the press); a break DROPS this call's return and
; leaves through do_break, at the caller's own depth -- as ex_stop's `jr do_break` does
; from a statement handler. A and HL only on the returning paths (KILBUF / trap_pend /
; stop_pause touch nothing else): exec_stmt's dispatch keeps B / C.
es_latch:
                cp      3
                jp      z,rp_break          ; page 1 (basic/program.asm)
                cp      4
                ret     nz                  ; no other value is latched (not measured)
                push    hl
                call    stop_pause          ; basic/input.asm: 4 resumed, 3 CTRL-STOP
                pop     hl
                cp      3
                ret     nz
                jp      rp_break            ; A = 3 from the pause
