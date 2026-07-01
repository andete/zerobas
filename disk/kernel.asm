; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; Part of zerobas-disk, included by disk.asm (build with `pasmo -I disk`).
; Tier-2 MSX-DOS-1 kernel veneers + relocated bodies (Interface A: the de-facto DOS ABI)
; CLEAN-ROOM: every constant, address and algorithm here traces to a public source
; or a black-box oracle probe; nothing is derived from disassembly. See disk/PROVENANCE.md.

; --- MSX-DOS-1 kernel continuation entry: $50A9 ($4000 + $10A9; a3 §8.26/§8.27) -
; The relocated kernel CALLs $50A9 right after publishing its BDOS vector; on the
; genuine CF-3300 this disk-ROM routine (`CALL $472D` + work-area setup) reaches A>.
; Our code ends far below $50A9, so the entry is positioned with a `ds` fill (like
; $4030). We reproduce the BLACK-BOX contract (disk_probe_dosboot_50a9.py):
;   side effect : W50A9_WRKB ($F242) := $00   (the only non-stack write observed)
;   returns     : A=$00, F=$42 (Z+N) ; DE=IX=$F1AA ; HL=$F359 ; BC, IY preserved
; `sub a` yields exactly A=$00 / F=$42 ($42 = Z|N: 0-0 sets Z+N, clears S/H/PV/C); the
; following loads do not disturb the flags, so the exit AF is exact. Inputs ignored
; (the kernel passes AF=C340 BC=0000 DE=DC80 HL=D606 IX=F195 IY=C0AB; none consumed).
                ds      $4E4B - $, $00  ; pad to the $4E4B kernel veneer (was $50A9 fill)
                jp      k_4E4B          ; $4E4B: COMMAND.COM-load kernel veneer
                ds      $4EDE - $, $00  ; pad to the $4EDE kernel veneer
                jp      k_4EDE          ; $4EDE: COMMAND.COM-load kernel veneer
                ds      $50A9 - $, $00  ; pad remainder up to the kernel's $50A9 target
                sub     a               ; A=$00, F=$42 (Z+N) -- the exact exit AF
                ld      (W50A9_WRKB), a ; $F242 := $00  (the only persistent write)
                ld      de, W50A9_RET_DE ; DE = $F1AA
                ld      ix, W50A9_RET_DE ; IX = $F1AA (= DE)
                ld      hl, W50A9_RET_HL ; HL = $F359
                ret                     ; AF=$0042, BC/IY untouched

; --- MSX-DOS-1 kernel CONIN line-read entry: $50E0 (M12d pin; tier2-conin-spec.md v3) --
; BUFIN (BDOS func $0A) has the relocated kernel CALL a disk-ROM console-line routine;
; the M12d black-box pin (guarded callseq, no stock bytes decoded) fixed the entry as the
; CALL target $50E0 (regs byte-identical ours==stock at first entry: DE=$DA40 HL=$C924
; ret=$D88A) and the register convention as DE -> buffer, [DE]=max length (the published
; BDOS func-$0A layout: [+0]=max/[+1]=count/[+2..]=chars; confirmed by a second pin
; walking HL/D/E across 7 CHGET calls with an injected keystroke). No return register --
; the result lives in the buffer (func-$0A contract). Our `$50B7-$5453` region is our own
; $00 padding (active code ends at the $50A9 routine above), so before this veneer BUFIN
; NOP-slid straight into the $5454 CONOUT veneer below (one garbage char, no block) --
; the M12 root cause. Body = conin_line_body (free tail): reimplements the func-$0A
; buffered-line read from the published CHGET ($009F) / CHPUT ($00A2) / func-$0A buffer
; ABI, clean-room -- the stock routine's internals were never read (spec §3 Option A).
;
; --- MSX-DOS-1 kernel SELDSK-time entry: $50D5 (M17; tier2-m17-spec.md) --------
; While processing BDOS SELDSK (func $0E) the relocated kernel CALLs this page-1
; disk-ROM entry (register-identical ours==stock at entry: AF=0044 BC=D50E DE=D3FF
; HL=D349 IX=F459 IY=DC5B, ret=D88A -- a real CALL boundary, M17 §2.1). Black-box
; contract: read the logical-drive count from $F347 into A, preserve BC/DE/HL/IX/IY
; (return F irrelevant so far, §4). Our $50B8-$5453 block is our own $00 padding, so
; before this veneer the CALL NOP-slid into the $5454 CONOUT veneer and never
; returned to the trampoline -> the M17 SELDSK stall (no A> prompt). Body =
; seldsk_drv_body (free tail); clean-room -- the stock routine's internals were never
; read (only its entry/exit registers + a DATA-cell read-watch of $F347).
                ds      $50D5 - $, $00  ; pad up to the pinned $50D5 kernel entry
seldsk_drv:
                jp      seldsk_drv_body ; -> free-tail: A = ($F347) drive count (M17)
                ds      $50E0 - $, $00  ; pad up to the pinned CONIN line-routine entry
conin:
                jp      conin_line_body ; -> free-tail buffered-line CHGET loop (M13)

; --- MSX-DOS-1 kernel CONOUT entry: $5454 ($4000 + $1454; a3 §8.38) ---------
; The relocated kernel CALLs $5454 to emit its sign-on banner one character at a
; time (the boot's first divergence point, disk_probe_dosboot_pctrace.py). It is
; the disk ROM's CONOUT: output the char in A via the BIOS CHPUT path, preserving
; BC/DE/HL/IX/IY. Black-box call-chain on the stock: $5454 -> $408F -> $001C
; (CALSLT) -> resident kernel -> $F398 -> $00A2 (CHPUT); first call A=$0D (the
; banner's leading CR). $5454 is a HARD IMMEDIATE in MSXDOS.SYS (`CD 54 54`
; present in the pristine just-loaded image, unchanged at call time -- not a
; relocated vector). CLEAN-ROOM: $5454 is a cross-vendor de-facto-standard entry,
; byte-identical across seven vendors' disk ROMs in the shared ASCII-kernel block
; ($4768-$576F) -- the same ABI class as $4010 DSKIO / $4016 GETDPB, never a byte
; copy (oracle-artifacts.md "Cross-vendor disk-ROM set"; spec-diskrom-kernel.md
; §1.3). Our code ends far below $5454, so the entry is positioned with a `ds`
; fill (like $4030/$50A9), consuming otherwise-$00 page padding -- nothing shifts.
; M8/§8.67: the first-cut no-op was PROVEN to be the COMPLETE COMMAND.COM-load
; blocker (aligned pctrace from $0100 diverges at exactly $5454; ours spins in the
; banner loop forever, 56 distinct PCs, while stock proceeds, 482). So CONOUT now
; does the real thing: emit A via the main-ROM CHPUT ($00A2) through a genuine
; inter-slot call. The body lives in the free tail (conout_body); $5454 just diverts
; to it (the 2 extra bytes shift the $5456 bodies gap, absorbed by `ds $5FE5 - $`).
                ds      $5454 - $, $00  ; pad up to the kernel's $5454 CONOUT target
conout:
                jp      conout_body     ; -> free-tail inter-slot CHPUT call (M8)

; ===== Tier-2 3b: relocated Disk-BASIC routine bodies ($5456-$5FE4 gap) =====
; Each colliding routine's body lives here; its low-region slot holds `entry:
; jp entry_body` + the ds-anchored veneer(s) + padding, sized to exactly fill the
; original span (net-zero — nothing downstream shifts). Each body ends with a `jp`
; back to the label that followed it, so fall-through is preserved. Callers reach
; the routine through its unchanged low-region entry label.
fat_find_body:                          ; [fat_find, ff_secloop)
                ld      (FAT_NAMEPTR), hl
                ld      hl, (FAT_FIRSTROOT)
                ld      (FAT_DIRSEC), hl
                ld      hl, (FAT_ROOTSECS)
                ld      (FAT_DIRREM), hl
                jp      ff_secloop

callf_body_body:                        ; [callf_body, rdslt_h) — ends in ret
                ld      (R30_HL), hl    ; stash caller HL
                ld      (R30_BC), bc    ; stash caller BC
                ld      (R30_DE), de    ; stash caller DE
                push    af              ; copy AF out without disturbing the return ptr
                pop     hl              ; HL = AF image (push/pop is SP-neutral)
                ld      (R30_AF), hl    ; stash caller AF (incl. carry)
                pop     hl              ; HL = return addr -> inline operand [slot][lo][hi]
                inc     hl              ; -> lo
                ld      e, (hl)
                inc     hl              ; -> hi
                ld      d, (hl)         ; DE = target address (e.g. $4010)
                inc     hl              ; HL = operand+3 = byte after CALLF (H.PHYD's C9)
                push    hl              ; ultimate return: target's RET lands here
                push    de              ; target address on top
                ld      hl, (R30_AF)    ; restore caller AF (carry = DSKIO read/write)
                push    hl
                pop     af
                ld      bc, (R30_BC)    ; restore caller BC
                ld      de, (R30_DE)    ; restore caller DE
                ld      hl, (R30_HL)    ; restore caller HL (DSKIO transfer address)
                ret                     ; -> target; its RET -> operand+3 -> caller

bdos_seqread_body:                      ; [bdos_seqread, bsr_have) -> falls into bsr_have
                ; EOF once every file byte has been delivered (BYTESLEFT == 0).
                ld      hl, (BDOS_BYTESLEFT)        ; low word
                ld      de, (BDOS_BYTESLEFT + 2)    ; high word
                ld      a, h
                or      l
                or      d
                or      e
                jp      z, bsr_eof                  ; no bytes left -> EOF (jr->jp: relocated)
                ld      a, (BDOS_RECIDX)
                cp      RECPERSEC
                jp      c, bsr_have     ; records still left in SECTOR_BUF (jr->jp)
                call    fat_read_file_sector
                jp      c, bsr_eof      ; chain ended early -> EOF (jr->jp)
                xor     a
                ld      (BDOS_RECIDX), a    ; back to record 0
                jp      bsr_have

bdos_create_body:                       ; [bdos_create, bdos_create_failpop) — ends in ret
                push    de              ; FCB across fat_mount
                call    fat_mount
                jp      c, bdos_create_failpop      ; jr->jp: relocated
                pop     hl              ; HL = FCB
                inc     hl              ; HL = FCB+1 = 8.3 name
                call    fat_dir_create  ; find/make a dir slot, write the entry
                jp      c, bdos_create_err          ; jr->jp: relocated
                ; prime the write iterator: no cluster yet, empty buffer, 0 bytes.
                xor     a
                ld      (BDOS_WRSECIDX), a
                ld      hl, 0
                ld      (BDOS_WRCLUS), hl
                ld      (BDOS_WRFIRST), hl
                ld      (BDOS_WRBUFLEN), hl
                ld      (BDOS_WRBYTES), hl
                ld      (BDOS_WRBYTES + 2), hl
                ld      a, 1
                ld      (BDOS_WRMODE), a    ; file is open for write
                xor     a                   ; A = $00 success
                ret

frs_mul_body:                           ; [frs_mul, frs_eof) loop; entered via frs_mul stub
                add     hl, de
                djnz    frs_mul_body        ; HL = (cluster-2) * secPerClus
                ld      de, (FAT_FIRSTDATA)
                add     hl, de
                ld      a, (FAT_CLUSSEC)
                ld      e, a
                ld      d, 0
                add     hl, de              ; HL = absolute logical sector
                ex      de, hl
                ld      hl, SECTOR_BUF
                call    read_sector
                ret     c
                ld      a, (FAT_CLUSSEC)
                inc     a
                ld      (FAT_CLUSSEC), a
                or      a                   ; Cy = 0 success
                ret

write_sector:                           ; relocated (entry collided with $4935 veneer)
                ld      b, 1            ; one sector
                ld      c, $F9          ; media byte (ignored, single drive)
                ld      a, 0            ; drive 0 (ignored)
                scf                     ; Cy = 1 = WRITE direction (MSX2 TH DSKIO)
                jp      dskio           ; tail-call: dskio returns to our caller

; --- MSX-DOS-1 kernel _GDATE entry: $553C ($4000 + $153C; M9 date slice) ----
; The kernel BDOS dispatcher ($D831; table $D8BE + 3*C) routes _GDATE ($2A) here
; after paging in the disk ROM via the $F368 hook. CF-3300 and C-BIOS are
; clock-less MSX1, so _GDATE returns the documented MSX-DOS-1 default date
; 1984-01-01 (a Sunday) -- a constant, NOT a reproduction of stock's stored
; day-count -> Y/M/D math. Return contract (observed black-box at the GDATE
; return $CC04): HL=year, D=month, E=day, A=day-of-week(0=Sun), BC=0, F=$44.
; `xor a` yields A=$00 and F=$44 (Z|P/V) exactly; the preceding loads do not
; disturb the flags. CLEAN-ROOM: documented default + black-box return contract;
; no stock bytes. $553C fell inside fac_loop_body; that body is relocated just
; below (label-referenced via fat.asm `jp fac_loop_body`; net-zero -- the tail
; `ds $5FE5 - $` absorbs the shift). See docs/tier2-gdate-spec.md.
                ds      $553C - $, $00      ; pad to the canonical _GDATE entry
gdate_handler:
                ld      hl, $07C0           ; year = 1984
                ld      de, $0101           ; D = month 01, E = day 01
                ld      bc, $0000
                xor     a                   ; A = 0 (Sunday); F = $44 (Z,P/V), as stock
                ld      ($F306), a          ; clear dispatcher re-entrancy flag (stock parity)
                ret

fac_loop_body:                          ; [fac_loop, fac_have_sec) -> falls into fac_have_sec; relocated past $553C
                ld      de, (FAT_WRTMP)
                push    hl
                or      a
                sbc     hl, de
                pop     hl
                jp      nc, fac_full        ; jr->jp: relocated
                push    hl
                ld      a, l
                and     1
                ld      (FAT_PARITY), a
                ld      e, l
                ld      d, h
                srl     d
                rr      e                   ; DE = cluster >> 1
                add     hl, de              ; HL = fatofs = cluster * 3/2
                ld      a, l
                ld      (FAT_BYTEIDX), a
                ld      a, h
                and     1
                ld      (FAT_BYTEIDX + 1), a    ; byteidx = fatofs & $1FF
                ld      a, h
                srl     a                   ; FAT sector offset = fatofs >> 9
                ld      e, a
                ld      d, 0
                ld      hl, (FAT_FATSTART)
                add     hl, de              ; HL = absolute FAT sector
                ld      de, (FAT_WRTMP2)
                push    hl
                or      a
                sbc     hl, de
                pop     hl
                jp      z, fac_have_sec     ; jr->jp: already loaded -> no re-read
                ld      (FAT_WRTMP2), hl    ; remember the new cached sector
                ld      (FAT_FATSEC), hl
                ex      de, hl
                ld      hl, WBUF
                call    read_sector
                jp      c, fac_rderr        ; jr->jp: relocated
                jp      fac_have_sec        ; fall-through preserved

fac_e_odd_body:                         ; [fac_e_odd, fat_write_fat_entry) — ends in ret
                ld      a, (FAT_B1)
                ld      l, a
                ld      h, 0
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                ld      a, (FAT_B0)
                rrca
                rrca
                rrca
                rrca
                and     $0F
                ld      e, a
                ld      d, 0
                add     hl, de
                ex      de, hl
                ret

ffds_nopad_body:                        ; [ffds_nopad, ffds_alloc) -> falls into ffds_alloc
                ld      hl, (BDOS_WRCLUS)
                ld      a, h
                or      l
                jp      z, ffds_alloc       ; jr->jp: no cluster yet -> allocate the first
                ld      a, (BDOS_WRSECIDX)
                ld      hl, FAT_SECPERCLUS
                cp      (hl)
                jp      c, ffds_haveclus    ; jr->jp: room in the current cluster
                jp      ffds_alloc          ; fall-through preserved

fdc_entloop_body:                       ; [fdc_entloop, fdc_useslot); loop; ends jr fdc_secloop
                push    bc
                push    hl
                ld      a, (hl)
                or      a
                jp      z, fdc_useslot      ; jr->jp: $00 end-marker -> free slot here
                cp      $E5
                jp      z, fdc_useslot      ; jr->jp: $E5 deleted -> reusable slot
                ld      de, (FAT_NAMEPTR)
                call    name_cmp
                jp      z, fdc_useslot      ; jr->jp: same-name existing entry
                pop     hl
                ld      de, 32
                add     hl, de
                pop     bc
                djnz    fdc_entloop_body
                ld      hl, (FAT_DIRSEC)
                inc     hl
                ld      (FAT_DIRSEC), hl
                ld      hl, (FAT_DIRREM)
                dec     hl
                ld      (FAT_DIRREM), hl
                jp      fdc_secloop         ; jr->jp: relocated

fdc_useslot_body:                       ; [fdc_useslot, fdc_zero) -> falls into fdc_zero
                pop     hl                  ; HL = dir entry slot in WBUF
                pop     bc
                ld      de, (FAT_DIRSEC)
                ld      (BDOS_DIRSEC), de
                push    hl
                ld      de, WBUF
                or      a
                sbc     hl, de              ; HL = offset within the sector
                ld      (BDOS_DIROFF), hl
                pop     hl
                push    hl
                ex      de, hl              ; DE = dest slot
                ld      hl, (FAT_NAMEPTR)
                ld      bc, 11
                ldir                        ; name -> entry +0..10
                xor     a
                ld      (de), a             ; +11 = $00 (normal file; matches MSX-DOS)
                inc     de
                ld      b, 20               ; +12..+31 is 20 bytes
                jp      fdc_zero            ; fall-through preserved

; ===== Tier-2: COMMAND.COM-load kernel entries — veneer scaffold (milestone 3a) =====
; The relocated MSX-DOS-1 kernel + COMMAND.COM call back into ~21 disk-ROM entry
; points at fixed page-1 addresses (the de-facto-standard shared-kernel ABI;
; spec-diskrom-kernel.md §5). zerobas exposes each as a 3-byte `jp k_XXXX` veneer
; at its canonical address, with the contract body in this free-tail region.
; This 3a pass places the FIVE free-region entries (no relocation needed); $402D
; (in the $4022-$402F pad) is the sixth non-colliding entry, wired above. Bodies
; are register-preserving stubs for now — our ROM does not yet reach the
; COMMAND.COM-load phase — so this scaffold changes no current behaviour; the 14
; entries that collide with active code arrive in the 3b relocation pass, and
; milestone 4 fills each contract. CLEAN-ROOM: exposing ABI entry points + own
; contract code, never shared-kernel bytes — same legitimacy class as the $4010
; BIOS jump table. Veneer safety confirmed by disk_probe_dosboot_veneer.py.
                ds      $5FE5 - $, $00  ; pad to the first free-region kernel entry
                jp      k_5FE5          ; $5FE5
                ds      $607B - $, $00
                jp      k_607B          ; $607B  (BDOS callback; spec §5.2)
                ds      $75A5 - $, $00
                jp      k_75A5          ; $75A5
                ds      $77B8 - $, $00
                jp      k_77B8          ; $77B8
                ds      $782B - $, $00
                jp      k_782B          ; $782B
; --- contract bodies (stubs; filled in milestone 4; added as each veneer lands) ---
k_402D:         ret
k_41FD:         ret
k_4558:         ret
k_46C8:         ret
; k_47B2 — COMMAND.COM loader (Tier-2 M5.4 first cut, fork P; spec tier2-m5.4-spec.md).
; The relocated MSXDOS.SYS loader (~$D821) CALLs $47B2 to load COMMAND.COM (§8.40/
; §8.54); the stock reads it via the disk ROM's own file routines, so we do the same
; through our oracle-validated FCB BDOS: Open "COMMAND.COM", point the DTA at $0100
; (the .COM load address, §5.2/§8.50), and Sequential-Read every 128-byte record
; contiguously into the TPA. We then RET to $D824 — MSXDOS.SYS's existing post-$D824
; transfer runs the now-loaded shell (the ×1 jump to $0100 seen in the §8.54 baseline).
; First cut (diagnostic): does NOT yet reproduce $47B2's return-register state
; (AF=0142/HL=1A00/IY=DC5B, §8.50) — add if the probe shows MSXDOS.SYS needs it.
; CLEAN-ROOM: our own loader over our own file layer; COMMAND.COM is data we copy,
; never disassembled.
k_47B2:         push    de                  ; save entry DE (= kernel work ptr $DC5B) for the IY return
                ld      de, k47b2_fcb       ; FCB naming COMMAND.COM
                ld      c, BDOS_F_OPEN      ; $0F Open
                call    bdos_entry
                inc     a                   ; A=$FF not-found -> 0
                jr      z, k47b2_fail       ; open failed: bail (stays in §8.40 spin)
                ld      hl, $0100           ; .COM load address (§5.2/§8.50)
                ld      (BDOS_DTA), hl
k47b2_rdloop:   ld      de, k47b2_fcb
                ld      c, BDOS_F_SEQRD     ; $14 Sequential Read -> (BDOS_DTA)
                call    bdos_entry
                or      a
                jr      nz, k47b2_done      ; A=$01 EOF -> COMMAND.COM loaded
                ld      hl, (BDOS_DTA)      ; advance DTA one record
                ld      de, RECSIZE         ; 128
                add     hl, de
                ld      (BDOS_DTA), hl
                jr      k47b2_rdloop
; k47b2_done — COMMAND.COM is loaded; reproduce stock $47B2's RETURN contract (§8.50,
; spec §5.1) so MSXDOS.SYS's post-$D824 transfer enters COMMAND.COM at $0100 with the
; environment it expects. Measured at the $0100 entry (same-program ours-vs-stock,
; 2026-06-26): stock HL=BC=$1A00 IX=$F195 IY=$DC5B; ours had HL=0 BC=$0014 IX=$F1AA
; IY=$0314 -> COMMAND.COM jp $0500 and SPUN at $050D (no DOS env). The path $D824->$0100
; (or a; call $F36B; ei; jp $0100) does NOT touch these registers, so they pass straight
; through from here. Contract: HL=BC = the loaded file size (FAT_FILESIZE); IX = the
; drive-A DPB ($F195, == the entry IX, which our BDOS clobbered); IY = the kernel work
; pointer the kernel handed us in DE (== $DC5B). A stays $01 (EOF) so $D824's `or a` keeps
; the load-success path. CLEAN-ROOM: our own loader returning the black-box-observed
; register contract; no stock bytes.
k47b2_done:     ld      ix, DRVA_DPB        ; IX = $F195 drive-A DPB (entry IX, restored)
                ld      bc, (FAT_FILESIZE)  ; BC = COMMAND.COM size ($1A00)
                ld      hl, (FAT_FILESIZE)  ; HL = COMMAND.COM size ($1A00)
                pop     iy                  ; IY = saved entry DE (kernel work ptr $DC5B)
                ret                         ; RET to $D824 -> COMMAND.COM with its env
k47b2_fail:     pop     de                  ; balance the saved entry DE
                xor     a                   ; A=0 = load failed (caller stays in §8.40 spin)
                ret
k47b2_fcb:      db      0                   ; drive = default
                db      "COMMAND COM"       ; 11-byte 8.3 name (FCB+1..+11; dir form)
                ds      24, 0               ; FCB bookkeeping (unread by bdos_entry)
k_4919:         ret
k_4935:         ret
k_498C:         ret
k_49B4:         ret
k_4A39:         ret
k_4B59:         ret
k_4BE5:         ret
k_4C25:         ret
k_4E4B:         ret
k_4EDE:         ret
k_5FE5:         ret
k_607B:         ret
k_75A5:         ret
k_77B8:         ret
k_782B:         ret

; p1_blit_tmpl — clean-room blit routine (§8.35), LDIR'd to P1_BLIT ($E77A) by
; build_resident.  Called from dskio (page-1 ROM) via `call P1_BLIT` when the
; DSKIO transfer destination is in page 1 ($4000-$7FFF): the FDC read was
; redirected to SECTOR_BUF; this copies SECTOR_BUF to the original page-1 target
; by briefly switching page-1 sub-slot from disk ROM (3-1) to RAM (3-0).
;
; Runs from page-3 RAM (always-mapped), so the page-1 sub-slot flip is safe.
; The call return address (a page-1 ROM address) is still on the stack while
; page 1 = RAM; sub-slot 1 is restored BEFORE `ret`, so the RET lands in the ROM.
;
; $FFFF secondary register: write = direct sub-slot IDs (bits [3:2] = page-1
; sub-slot); read = complement of the written value (MSX2 TH §2.4).  We CPL
; after reading to recover the "write" form, mask bits 3:2 to 00 (sub-slot 0 =
; RAM), then write; on return CPL to restore original sub-slot 1.
;
; Source: MSX2 TH §2.4 (expanded-slot secondary register semantics); sub-slot
; layout confirmed by black-box differential (set_ramad / page0_ram_in, same
; host).  Clean-room: never reads the stock $EF95 or any proprietary driver.
; Lives in the free tail (LDIR-relocated; moved here from the cramped pre-$41FD
; region so the wa_seg M5.6 additions fit, §8.58). wa_seg_*_tmpl follows it
; immediately so build_resident copies BOTH with one LDIR (RAM-contiguous).
;   in:  P1_DEST = page-1 target address (word in page-3 scratch)
;   out: 512 bytes from SECTOR_BUF copied to (P1_DEST); page-1 sub-slot restored
p1_blit_tmpl:
                ld      a, ($FFFF)          ; A = inverted sub-slot state (MSX2 TH)
                cpl                         ; A = actual sub-slot write value
                push    af                  ; save original state for restore
                and     $F3                 ; bits 3:2 -> 00: page 1 = sub-slot 0 (RAM)
                ld      ($FFFF), a          ; page 1 now maps to RAM
                ld      hl, SECTOR_BUF      ; source: FDC data was read here
                ld      de, (P1_DEST)       ; dest: original page-1 target (now RAM)
                ld      bc, 512
                ldir
                pop     af                  ; A = original sub-slot write value
                ld      ($FFFF), a          ; page 1 back to disk ROM (sub-slot 1)
                ret
p1_blit_end:

; wa_seg_*_tmpl — clean-room bodies for the $F368/$F36B work-area segment-switch
; hooks (§8.58), LDIR'd to WA_SEG by build_resident and wired into the $F368 table
; by build_wa_table. The relocated kernel CALLs $F368 to map the disk ROM into
; page 1 (so it can run a page-1 disk-ROM routine) and $F36B to map RAM into page 1
; (so it can read its data living UNDER the page-1 ROM). On this expanded slot 3,
; subslot 1 = disk ROM, subslot 0 = RAM (machine config); the page-1 subslot is
; bits [3:2] of the slot-3 secondary register, $04 = subslot 1, $00 = subslot 0.
;
; Contract (measured stock, §8.58): register-TRANSPARENT (entry regs == exit regs);
; only persistent effect = SLTTBL[3] ($FCC8) and the live secondary register
; ($FFFF) set to $04 (rom) / $00 (ram). We read-modify-WRITE only the page-1 bits
; (mask $F3) so the other pages' subslots are preserved, source the current value
; from the SLTTBL mirror (write-form; $FFFF reads back complemented, so the mirror
; is the safe source), update the mirror then the live register, under DI. No EI:
; faithful -- the kernel calls these with interrupts already off (§8.58 trace).
; Bodies run from page-3 RAM (always mapped), so the page-1 flip never unmaps them.
; Lives in the free tail (LDIR-relocated; ROM position must not disturb canonical
; addresses -- the inline-before-$41FD placement overflowed that gap, §M5.6).
;
; Clean-room: our own standard expanded-slot switch (MSX2 TH §2.4 secondary-slot +
; SLTTBL); the stock $DF57/$DF59 bytes are never read. Straight-line + one PC-
; relative jr, so a plain LDIR relocates it verbatim.
;   in:  -            ; out: page-1 subslot of slot 3 set; all registers preserved
wa_seg_rom_tmpl:                            ; $F368 body: map disk ROM into page 1
                push    af
                push    bc                  ; B is our scratch -> preserve (transparent)
                ld      a, $04              ; page-1 bits = subslot 1 (disk ROM)
                jr      wa_seg_set_tmpl     ; (relocatable: PC-relative)
wa_seg_ram_tmpl:                            ; $F36B body: map RAM into page 1
                push    af
                push    bc
                ld      a, $00              ; page-1 bits = subslot 0 (RAM)
wa_seg_set_tmpl:
                di
                ld      b, a                ; B = desired page-1 subslot bits
                ld      a, (SLTTBL3)        ; current slot-3 subslot (write-form mirror)
                and     $F3                 ; clear page-1 bits, keep pages 0/2/3
                or      b                   ; merge new page-1 bits
                ld      (SLTTBL3), a         ; update RAM mirror first
                ld      ($FFFF), a          ; ...then the live secondary-slot register
                pop     bc
                pop     af
                ret
wa_seg_end_tmpl:
WA_SEG_ROM      equ     WA_SEG + (wa_seg_rom_tmpl - wa_seg_rom_tmpl)   ; = WA_SEG
WA_SEG_RAM      equ     WA_SEG + (wa_seg_ram_tmpl - wa_seg_rom_tmpl)

; f365_iord_tmpl — clean-room body for the fixed disk-work-area slot-read stub at
; $F365 (M15 OI-1/§7 pin: unbuilt/FF on ours; §7.1 causally BOUNDS the func-9 STROUT
; output blocker to completing `wa_seg` + this stub). Reads the PPI primary-slot-
; select register (port $A8) and returns; the disk-ROM work area's own per-char
; output loop CALLs this fixed address (observed black-box: reader PC = $F365 itself,
; i.e. an executed 2-instruction stub, never disassembled — see docs/tier2-m15-spec.md
; §7.2). Installed at the FIXED address $F365 (not WA_SEG-relative: the kernel calls
; it by that absolute address, like WA_JMPTAB), by install_f365 below.
; CLEAN-ROOM: IN A,(n) reading port $A8 is the documented i8255 PPI primary-slot-
; select register (MSX2 TH ch.2 / i8255 PPI datasheet, docs/allowed-sources.md class
; A) — our own encoding of a public 2-instruction sequence, not read from the ROM.
;   in: - ; out: A = primary-slot register; other registers preserved
f365_iord_tmpl:
                in      a, ($A8)
                ret
f365_iord_end:

; install_f365 — copies f365_iord_tmpl to the fixed address $F365. Lives in the
; free tail (no budget limit) and is reached by a single 3-byte `call` from
; build_resident's cramped pre-$41FD path (see init.asm) instead of inlining the
; ld/ld/ld/ldir sequence there, which overflows that region's canonical-address
; budget (M15 §7.1/§7.2: verified — an inline second copy there makes 3-pass/
; symbol-table assembly silently emit an empty object file, no error printed).
install_f365:
                ld      hl, f365_iord_tmpl
                ld      de, F365_STUB
                ld      bc, f365_iord_end - f365_iord_tmpl
                ldir
                ret

; res_print_tmpl — clean-room body for the resident $-string print routine, relocated
; to RES_PRINT ($F1C9) by install_res_print (M15 §9.2/§9.3(ii)). The kernel CALLs
; $F1C9 with DE -> a '$'-terminated string. Emits each char via conout_body (the
; proven $5454 CONOUT path func-2/conin_line_body already use) before advancing --
; the M15 root cause was that our first cut consumed the string without emitting it.
; conout_body preserves BC/DE/HL/IX/IY internally, but only across ITS OWN entry
; state; since E is overwritten with the char before the call, DE (the string
; pointer) is saved/restored around the call here. Straight-line + one PC-relative
; jr, so a plain LDIR relocates it verbatim.
; CLEAN-ROOM: derives from the published func-9 STROUT contract ('$'-terminated
; string at DE) + our own conout_body; no stock bytes (never reads $F392/$F2AC/
; $F237/$D88A-region routine bytes, docs/tier2-m15-spec.md §5/§9).
;   in:  DE -> '$'-terminated string ; out: DE past the '$', A=$24, others as Z80 CP
res_print_tmpl:
                ld      a, (de)         ; A = next string byte
                inc     de
                cp      '$'             ; $24 = MS-DOS string terminator
                ret     z               ; done -> return to the kernel
                push    de              ; save the string pointer (E about to change)
                ld      e, a            ; conout_body's ABI: char in E (M10)
                call    conout_body     ; emit via $5454 CONOUT path -> CHPUT
                pop     de              ; restore the string pointer
                jr      res_print_tmpl  ; (relocatable: PC-relative loop)
res_print_end:

; install_res_print — copies res_print_tmpl to RES_PRINT ($F1C9). Lives in the free
; tail (no budget limit) and is reached by a single 3-byte `call` from build_resident's
; cramped pre-$41FD path (init.asm), same rationale as install_f365 (§7.1/§7.2/§9.3).
install_res_print:
                ld      hl, res_print_tmpl
                ld      de, RES_PRINT
                ld      bc, res_print_end - res_print_tmpl
                ldir
                ret

; seldsk_drv_body — the $50D5 kernel SELDSK-time entry (M17; tier2-m17-spec.md).
; The relocated kernel CALLs $50D5 while processing BDOS SELDSK ($0E) to read the
; logical-drive count. Black-box contract (M17 §2.1, readwatch causal pin): read
; $F347 into A, preserve BC/DE/HL/IX/IY. Reached directly from the fixed $50D5 veneer
; (jp seldsk_drv_body) -- lives here in the free tail like conin_line_body/conout_body.
; CLEAN-ROOM: derives from the observed DATA-cell read contract (return [$F347]) +
; our own code; no stock/kernel bytes decoded (only entry/exit regs + the $F347 read).
;   in: -    ; out: A = ($F347) = drive count ; BC/DE/HL/IX/IY preserved
seldsk_drv_body:
                ld      a, (DRVCNT)     ; DRVCNT = $F347 = logical-drive count ($02)
                ret

