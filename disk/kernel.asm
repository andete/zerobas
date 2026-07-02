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
; --- MSX-DOS-1 kernel SFIRST/SNEXT dir-search entries: $4FB8/$5006 (M19) -------
; While processing BDOS SFIRST ($11) / SNEXT ($12) the relocated kernel CALLs these
; two page-1 disk-ROM entries to walk the root directory for entries matching the
; search FCB's 8.3 pattern. Both are our own $00 pad (inside the $4EE1..$50A9 fill,
; below the $50A9/$50C4/$50D5/$50E0 veneers), so before this the CALL NOP-slid into
; the $50A9 stub tail and returned a bogus "entry found" -> DIR hung (M19 §3). Each
; is inserted as an additional descending ds-anchor in this chain ($4FB8, $5006 slot
; in address order between $4EDE and $50A9), consuming existing pad -> net-zero.
; Black-box entry contract (M19 §2, callseq/capture, no stock CODE decoded): entry
; DE -> the kernel's search-FCB copy (drive byte + 11-byte 8.3 pattern, ?=$3F
; wildcard); the runtime DTA base lives in the fixed work-area cell $F23D (the
; kernel's current-DTA pointer, set via its own SETDTA before the search). Bodies
; (sfirst_body/snext_body/dirscan_match) live in the free tail; clean-room -- our
; own fat_mount/fat_find root-dir walk + published SFIRST/SNEXT contract. See
; docs/tier2-m19-spec.md.
                ds      $4FB8 - $, $00  ; pad up to the pinned $4FB8 SFIRST entry
sfirst:
                jp      sfirst_body     ; -> free-tail: find FIRST matching dir entry (M19)
                ds      $5006 - $, $00  ; pad up to the pinned $5006 SNEXT entry
snext:
                jp      snext_body      ; -> free-tail: find NEXT matching dir entry (M19)
; --- MSX-DOS-1 kernel SETDTA-time entry: $5058 (M19) --------------------------
; While processing BDOS SETDTA ($1A) the relocated kernel CALLs this page-1
; disk-ROM entry to cache the new DTA pointer into the disk work area. Black-box
; contract (M19, callseq/capture/callwatch causal pin, no stock CODE decoded):
; entry DE = the new DTA pointer (=$D403 for DIR; register-identical ours==stock,
; 51 calls each), and stock's routine stores it at the fixed work-area cell $F23D
; (proven: on stock $F23D=$D403 and SFIRST reads it via PCs $4FCC/$4FEF; on ours,
; before this veneer, $F23D was never written -> SFIRST/SNEXT wrote the found entry
; to a stale/garbage DTA -> DIR reported "File not found"). Wiring $5058 to cache
; DE at $F23D makes SFIRST/SNEXT (which read DOS_DTAPTR=$F23D) target the real
; runtime DTA. Same un-wired-$50xx-entry class as M13/M17/M18. Body =
; setdta_cache_body (free tail). CLEAN-ROOM: our own DE->$F23D store + the observed
; entry-register / write-target contract; no stock routine internals decoded.
                ds      $5058 - $, $00  ; pad up to the pinned $5058 SETDTA-cache entry
setdta_cache:
                jp      setdta_cache_body ; -> free-tail: ($F23D) := DE (runtime DTA; M19)
; --- MSX-DOS-1 kernel GETALLOC entry: $505D (M20 REVISION 3; tier2-m20-spec.md) -----
; While processing BDOS GETALLOC ($1B) the relocated kernel CALLs this page-1 disk-ROM
; entry to compute the DIR "nn bytes free" footer. Black-box contract (M20 §2, no stock
; CODE decoded): entry regs byte-identical ours==stock (C=$1B BC=$5D1B DE=$D100
; HL=$C924 IX=$F195); the un-wired $00 pad here made the CALL NOP-slide into the $50A9
; stub tail (garbage exit -> "0 bytes free"). Exit contract (map.grauw.nl _ALLOC):
; A=sectors/cluster, BC=bytes/sector, DE=total data clusters, HL=free clusters.
; REVISION 3 (this span): Revisions 1 (register-only) and 2 (+ resident FAT buffer +
; IY + a per-drive DPB+19 field) were both BUILT and FALSIFIED -- the A/BC/DE/HL scan
; math was correct in both (host-unit-tested + confirmed at getalloc_body's own ret),
; but the DIR footer was wrong regardless, IDENTICALLY so both with and without the
; IY/DPB+19 wiring. Root cause (this span, a narrow read of 20 RAM-KERNEL bytes at the
; shared post-handler exit path $D8AA-$D8BD -- NOT stock ROM/COMMAND.COM code -- to
; answer one question, "what does the branch at $D8AE test"; same technique already
; used to pin $F23D/$F247/$F347/$F306 in prior milestones): the kernel's common BDOS-
; exit path gates HL passthrough on a flag cell, $F306 (set to $01 by the dispatcher on
; every BDOS call, per tier2-gdate-spec.md's earlier pin) -- a handler that leaves
; $F306 set has its HL SILENTLY OVERWRITTEN with H:=B,L:=A (the CP/M single-byte-result
; B:A->HL mirror) instead of passed through. Stock's $505D handler clears it; ours never
; did, so our correct HL was replaced by a mirror of our own A/BC (explaining the exact
; wrong constant observed, `$0202`=514, in both falsified revisions). Causally proven by
; a poke test (forcing $F306:=0 flips the branch and the handler's real HL survives).
; `gdate_handler` below already clears $F306 (previously assumed "harmless stock
; parity" -- it is in fact load-bearing, and the only reason GDATE's HL reaches its
; caller). Revision 3 = Revision 1's register-only body (own FAT scan via read_sector/
; WBUF, reusing fat.asm's fac_entry_from_wbuf unpack -- no new RAM cell, no IY, no
; DPB+19, both proven unnecessary) + one added store: clear $F306 before `ret`, loading
; the final A value AFTER the clear (order matters: A must hold sectors/cluster at
; `ret`; the clear only needs A=0 transiently as the store source).
; CLEAN-ROOM: our own FAT scan (fat_mount + read_sector + fat.asm's fac_entry_from_wbuf,
; all pre-existing oracle-validated primitives) + the published GETALLOC A/BC/DE/HL
; contract (map.grauw.nl) + the black-box-pinned $F306 dispatcher-flag semantics
; (register/memory VALUES + one narrow RAM-kernel byte read, no stock ROM decoded).
                ds      $505D - $, $00  ; pad up to the pinned $505D GETALLOC entry
getalloc:
                jp      getalloc_body   ; -> free-tail: FAT free-cluster scan (M20 rev3)
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
; --- MSX-DOS-1 kernel CURDRV-time entry: $50C4 (M18; tier2-m18-spec.md) ---------
; While processing BDOS CURDRV (func $19) the relocated kernel CALLs this page-1
; disk-ROM entry (register-identical ours==stock at entry: AF=0044 BC=C419 DE=D3FF
; HL=D502 SP=DBFE IY=DC5B, ret=D88A -- a real CALL boundary, M18 §2.1). Black-box
; contract (readwatch causal pin): read the CURRENT-drive index from $F247 into A,
; preserve BC/DE/HL/IX/IY. Our $50B8-$50D4 block is our own $00 padding, so before
; this veneer the CALL NOP-slid and never read the drive -> the kernel's later
; 'A'+drive letter math used a bogus index ($C400 + 2 = 'C>') instead of A>. Body =
; curdrv_body (free tail); clean-room -- the stock routine's internals were never
; read (only its entry/exit registers + a DATA-cell read-watch of $F247).
                ds      $50C4 - $, $00  ; pad up to the pinned $50C4 kernel entry
curdrv:
                jp      curdrv_body     ; -> free-tail: A = ($F247) current drive (M18)
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
; k_47B2 — M21b: generic BDOS RDBLK-via-page1 handler (tier2-m21-spec.md §5.4/
; §5.5; was: a COMMAND.COM-only diagnostic loader, Tier-2 M5.4 first cut).
; The kernel's $27 RDBLK handler ($D887, ret=$C51D) CALLs $47B2 for BOTH the
; boot-time COMMAND.COM self-load (DE=$DC5B) and the runtime typed-command TPA
; load (DE=$DA40) — both hand a fully-formed FCB of the SAME shape (§5.4), and
; by the time this runs the kernel's own preceding FOPEN (page-1 $4462, M21a)
; has already located the file and left FAT_FIRSTCLUS/FAT_FILESIZE seeded for
; it, so no re-search is needed here: just re-prime the iterator and stream.
; Requested count (entry HL) is treated as an upper bound in principle, but
; every observed caller requests far more than any file this ROM handles and
; relies on EOF to stop the transfer — reading straight to EOF is a documented
; simplification, the same shape as bdos_rdblk's own random-record-0-only
; assumption (disk/driver.asm).
;   in:  DE = FCB pointer (kernel work buffer); HL = requested record count
;   out: A = $01 EOF (MSX2 TH; matches stock's observed constant, §0.1/§5.5)
;        HL = BC = total bytes transferred (= the file's full size, since the
;        transfer always runs to EOF); IY = the entry DE (kernel work pointer,
;        §5.4/§8.50); IX = the drive-A DPB (§8.50's original boot contract,
;        extended unconditionally per §5.4 — both callers get the same body).
;        $F306 cleared (Tier-2 dispatcher-flag rule, M20).
; CLEAN-ROOM: our own file layer streaming into the caller's own DTA; COMMAND.COM
; is data we copy, never disassembled.
k_47B2:         push    de                  ; save entry DE (kernel work ptr) for the IY return
                ; Seed OUR internal BDOS_DTA from the kernel's own live DTA pointer
                ; (DOS_DTAPTR, $F23D -- M19) rather than trusting BDOS_DTA itself:
                ; the kernel's real SETDTA writes DOS_DTAPTR only, never our own
                ; mini-BDOS's cell, so BDOS_DTA is stale leftover from whatever
                ; this ROM's own internal loader last used it for (found the hard
                ; way: it read back $1A80, the END of the boot-time COMMAND.COM
                ; load, at the runtime BDOSX.COM call).
                ld      hl, (DOS_DTAPTR)
                ld      (BDOS_DTA), hl
                call    fat_open            ; re-prime the iterator (FAT_FIRSTCLUS already found)
                ld      hl, FAT_FILESIZE
                ld      de, BDOS_BYTESLEFT
                ld      bc, 4
                ldir                        ; BDOS_BYTESLEFT = true file size (fresh read)
                ld      a, RECPERSEC
                ld      (BDOS_RECIDX), a    ; buffer empty -> first read refills
k47b2_rdloop:   call    bdos_seqread        ; A=$00 record delivered / $01 EOF
                or      a
                jr      nz, k47b2_done      ; EOF -> the file is fully transferred
                ld      hl, (BDOS_DTA)      ; advance DTA one record
                ld      de, RECSIZE         ; 128
                add     hl, de
                ld      (BDOS_DTA), hl
                jr      k47b2_rdloop
; k47b2_done — the file is fully transferred; reproduce the pinned return contract
; (§5.5, exact register match at $C51D: AF=$0142 HL=$0480 for the runtime caller;
; §8.50, HL=BC=FAT_FILESIZE IX=DRVA_DPB IY=entry-DE for the boot caller).
k47b2_done:     xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                or      a                   ; clear carry (A=0 already; overwritten by dec next)
                ld      b, 1
                dec     b                   ; B=0; F = Z=1,N=1,C=0 (§5.5's AF=$0142 flag half)
                ld      ix, DRVA_DPB        ; IX = $F195 drive-A DPB (§8.50)
                ld      hl, (FAT_FILESIZE)  ; HL = total bytes transferred (LD: flags unaffected)
                push    hl
                pop     bc                  ; BC = HL (§5.5: "the genuine BDOS $27 returns the
                                             ; count in both")
                pop     iy                  ; IY = saved entry DE (kernel work pointer)
                ld      a, 1                ; A = $01 EOF (LD: flags unaffected) -> AF = $0142
                ret
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

; curdrv_body — the $50C4 kernel CURDRV-time entry (M18; tier2-m18-spec.md).
; The relocated kernel CALLs $50C4 while processing BDOS CURDRV ($19) to read the
; CURRENT-drive index. Black-box contract (M18 §2.1, readwatch causal pin): read
; $F247 into A, preserve BC/DE/HL/IX/IY. Reached directly from the fixed $50C4 veneer
; (jp curdrv_body) -- lives here in the free tail like seldsk_drv_body.
; CLEAN-ROOM: derives from the observed DATA-cell read contract (return [$F247]) +
; our own code; no stock/kernel bytes decoded (only entry/exit regs + the $F247 read).
;   in: -    ; out: A = ($F247) = current drive ; BC/DE/HL/IX/IY preserved
curdrv_body:
                ld      a, (CURDRV_CELL) ; CURDRV_CELL = $F247 = current-drive index ($00)
                ret

; ===== M19: runtime directory search (BDOS SFIRST $11 / SNEXT $12) =============
; sfirst_body / snext_body / dirscan_match / name_cmp_wild — the bodies behind the
; $4FB8 (SFIRST) / $5006 (SNEXT) page-1 kernel entries. They walk our own root
; directory (reusing fat_mount + the fat_find ff_secloop/ff_entloop structure),
; match each 8.3 name against the kernel's search-FCB pattern (with the ? wildcard),
; copy the found entry's drive-byte + 32-byte directory image to the runtime DTA,
; and persist the scan position in BDOS_SRCHIDX so SNEXT resumes where the prior
; call stopped. Return A=$00 found / A=$FF exhausted (published SFIRST/SNEXT
; contract; the flags are irrelevant to the caller — M19 §2.4).
;
; PINNED black-box contract (M19 §2/§4, callseq/capture — NO stock CODE decoded):
;   - entry DE -> the kernel's search-FCB copy: drive byte at +0, 11-byte 8.3 name
;     pattern at +1..+11 (?=$3F matches any single char; DIR issues all-? -> lists
;     every entry). Observed DE=$DA40, [$DA40]=80 3F 3F ... (M19 §2.3/§4.5).
;   - the runtime DTA base is the kernel's current-DTA pointer, the fixed work-area
;     word at DOS_DTAPTR ($F23D) (=$D403 here, set via the kernel's own SETDTA just
;     before the search); read fresh each call (M19 §4.1). It receives one drive
;     byte (current drive + 1) then the 32-byte raw dir entry (observed: DTA=
;     01 <32-byte entry>, M19 §4.4).
;   - NO attribute filter: SFIRST/SNEXT surface EVERY non-$E5, non-$00 entry incl.
;     volume-label ($08) and subdir ($10) entries (stock returned the SandStone
;     volume label as match #1; COMMAND.COM's formatter does the label filtering /
;     "nn files" count, not us — M19 §4.4/§7, verified against test.dsk).
; CLEAN-ROOM: our own dir walk over our own fat_* layer + the published FCB /
; directory-entry / SFIRST-SNEXT contract; the stock routine's internals (108/101
; page-1 PCs) were never decoded — only entry/exit registers, call counts, and
; one-sided DATA reads of OUR OWN memory. See docs/tier2-m19-spec.md.

; setdta_cache_body — the $5058 kernel SETDTA-time entry (M19). Caches the new DTA
; pointer (DE) into the disk work-area cell DOS_DTAPTR ($F23D), so the SFIRST/SNEXT
; bodies can read the runtime DTA from a fixed cell (as stock's SFIRST does, PCs
; $4FCC/$4FEF). Register-transparent (like curdrv_body/wa_seg): preserves A/BC/DE/
; HL/IX/IY. Reached from the fixed $5058 veneer (jp setdta_cache_body).
; CLEAN-ROOM: our own DE->$F23D store + the observed entry DE=DTA / write-$F23D
; contract; no stock routine internals decoded. See docs/tier2-m19-spec.md.
;   in:  DE = new DTA pointer ; out: ($F23D) := DE ; all registers preserved
setdta_cache_body:
                ld      (DOS_DTAPTR), de    ; $F23D := DE (runtime DTA pointer)
                ret

; getalloc_body — the $505D kernel GETALLOC-time entry (M20 REVISION 3;
; tier2-m20-spec.md). BDOS $1B GETALLOC: return the volume's allocation geometry.
;
; Walks clusters 2..(rawTotal-1) sector-by-sector into WBUF (the SAME fatofs/byteidx/
; parity math and the SAME shared fac_entry_from_wbuf unpack that fat_alloc_cluster
; uses -- fat.asm; not modified, not called in place, so the Tier-1 write path stays
; byte-unchanged), counting $000 (free) entries instead of stopping at the first one.
; The cluster/free-counter/loop-bound live on the CPU stack across each
; fac_entry_from_wbuf call (it clobbers AF/BC/DE/HL and preserves nothing -- same
; push/pop-around-the-call idiom as fat.asm's own fac_have_sec).
;
; The FIX (Revision 3, see the $505D veneer comment above for the full root-cause
; writeup): clear the dispatcher's HL-passthrough flag ($F306) before `ret`, loading
; the final A value AFTER the clear. Without this the kernel's common BDOS-exit path
; silently overwrites our correct HL with a mirror of our own A/BC.
;
; Any FDC read error takes the fail-safe exit (A=0 BC=$0200 DE=0 HL=0) -- matches
; fat_total_clusters' own "report no free space" error posture.
;
; CLEAN-ROOM: our own FAT scan (fat_mount + read_sector, reusing fat.asm's existing
; fac_entry_from_wbuf unpack) + the published GETALLOC A/BC/DE/HL contract (map.grauw.nl
; MSX-DOS BDOS functions) + the black-box-pinned $F306 dispatcher-flag semantics (no
; stock CODE decoded).
;   out (success): A=(FAT_SECPERCLUS) BC=$0200 DE=total data clusters
;                  HL=free-cluster count ; ($F306):=$00
;   out (fail-safe): A=0 BC=$0200 DE=0 HL=0
getalloc_body:
                call    fat_mount               ; geometry -> FAT_* scratch (SECTOR_BUF)
                jp      c, ga_fail
                call    fat_total_clusters       ; DE = dataClusters + 2 (rawTotal)
                push    de                       ; stack[0] = rawTotal (stays for the scan)
                ld      hl, $FFFF
                ld      (FAT_WRTMP2), hl         ; no FAT sector cached yet (fat_alloc_
                                                 ; cluster's own init, same convention)
                ld      de, 0                    ; DE = free-cluster counter
                ld      hl, 2                    ; HL = cluster under test
ga_scanloop:
                pop     bc                       ; BC = rawTotal (peek: pop then re-push)
                push    bc
                push    hl                       ; save cluster across the compare
                or      a
                sbc     hl, bc                   ; HL = cluster - rawTotal
                pop     hl                       ; restore cluster
                jp      z, ga_scandone           ; cluster == rawTotal -> scan complete
                ; fatofs = cluster + (cluster>>1)  (== floor(cluster*3/2), the same
                ; math fac_loop_body uses -- Microsoft FAT spec §3.2 12-bit packing)
                push    de                       ; save free counter across the call below
                push    hl                       ; save cluster (need it after the call)
                ld      a, l
                and     1
                ld      (FAT_PARITY), a
                ld      e, l
                ld      d, h
                srl     d
                rr      e                        ; DE = cluster >> 1
                add     hl, de                   ; HL = fatofs
                ld      a, l
                ld      (FAT_BYTEIDX), a
                ld      a, h
                and     1
                ld      (FAT_BYTEIDX + 1), a     ; byteidx = fatofs & $1FF
                ld      a, h
                srl     a                        ; FAT sector offset = fatofs >> 9
                ld      e, a
                ld      d, 0
                ld      hl, (FAT_FATSTART)
                add     hl, de                   ; HL = absolute FAT sector for this cluster
                ld      de, (FAT_WRTMP2)
                push    hl
                or      a
                sbc     hl, de
                pop     hl
                jp      z, ga_havesec            ; already the cached sector -> no re-read
                ld      (FAT_WRTMP2), hl
                ld      (FAT_FATSEC), hl
                ex      de, hl
                ld      hl, WBUF
                call    read_sector
                jp      c, ga_rderr
ga_havesec:
                call    fac_entry_from_wbuf      ; DE = 12-bit entry value (clobbers
                                                 ; AF/BC/DE/HL -- fat.asm's own contract)
                ld      a, d
                or      e
                pop     hl                       ; restore cluster
                pop     de                       ; restore free counter
                jr      nz, ga_notfree
                inc     de                       ; entry == $000 -> free, bump counter
ga_notfree:
                inc     hl                       ; next cluster
                jp      ga_scanloop
ga_rderr:
                pop     hl                       ; discard saved cluster
                pop     de                       ; discard saved free counter
                pop     hl                       ; discard rawTotal
                jp      ga_fail
ga_scandone:
                ex      de, hl                   ; HL := free-cluster count (final)
                pop     de                       ; DE := rawTotal
                dec     de
                dec     de                       ; DE := total data clusters (final)
                xor     a
                ld      ($F306), a               ; clear dispatcher HL-passthrough flag
                                                 ; (M20 REVISION 3 fix -- see $505D veneer)
                ld      bc, $0200                ; BC := bytes/sector (final)
                ld      a, (FAT_SECPERCLUS)      ; A := sectors/cluster (final)
                or      a                        ; Cy = 0 (success)
                ret
ga_fail:
                xor     a
                ld      ($F306), a               ; clear here too (consistent with the
                                                 ; success path; harmless -- A=0 already
                                                 ; forces free_bytes=0 either way)
                ld      bc, $0200                ; BC := 512 (belt-and-braces)
                ld      de, 0
                ld      hl, 0
                ret

; sfirst_body — BDOS SFIRST ($11): find the FIRST matching root-dir entry.
;   in:  DE -> search FCB (name pattern at DE+1) ; out: A=$00 found / $FF none
sfirst_body:
                inc     de                  ; DE -> the 11-byte 8.3 pattern (FCB+1)
                ld      (FAT_NAMEPTR), de   ; dirscan_match compares against this
                call    fat_mount           ; (re)parse BPB -> FAT_FIRSTROOT/FAT_ROOTSECS
                jp      c, ds_none          ; disk error -> no entry
                ld      hl, 0
                ld      (BDOS_SRCHIDX), hl  ; scan cursor := entry 0
                jr      dirscan_match

; snext_body — BDOS SNEXT ($12): resume from BDOS_SRCHIDX, find the NEXT match.
;   in:  DE -> search FCB (name pattern at DE+1) ; out: A=$00 found / $FF exhausted
snext_body:
                inc     de                  ; DE -> the 11-byte 8.3 pattern (FCB+1)
                ld      (FAT_NAMEPTR), de
                call    fat_mount           ; geometry back into scratch (idempotent)
                jp      c, ds_none
                ; fall through: BDOS_SRCHIDX already points at the next entry.

; dirscan_match — walk the root dir from BDOS_SRCHIDX; on the first entry matching
; the pattern (name_cmp_wild) copy its drive-byte + 32-byte image to the DTA, set
; BDOS_SRCHIDX := match-index + 1, return A=$00. On $00 end-mark or all sectors
; scanned, return A=$FF. Reconstructs the sector cursor from BDOS_SRCHIDX alone
; (idx>>4 = sectors to skip; idx&15 = entry-in-sector) so it never persists
; FAT_DIRSEC/FAT_DIRREM across calls (M19 §4.3/§4.4).
dirscan_match:
                ; sectorsToSkip = BDOS_SRCHIDX >> 4  (16 entries per 512-B sector)
                ld      hl, (BDOS_SRCHIDX)
                ld      b, 4
dsm_shr:
                srl     h
                rr      l
                djnz    dsm_shr             ; HL = idx >> 4 = sector offset
                ; FAT_DIRSEC := FAT_FIRSTROOT + sectorOffset
                ld      de, (FAT_FIRSTROOT)
                add     hl, de
                ld      (FAT_DIRSEC), hl
                ; FAT_DIRREM := FAT_ROOTSECS - sectorOffset
                ld      hl, (BDOS_SRCHIDX)
                ld      b, 4
dsm_shr2:
                srl     h
                rr      l
                djnz    dsm_shr2            ; HL = idx >> 4 again (sector offset)
                ex      de, hl              ; DE = sector offset
                ld      hl, (FAT_ROOTSECS)
                or      a
                sbc     hl, de
                jp      z, ds_none          ; already past the last root sector
                jp      c, ds_none          ; (defensive) offset beyond root
                ld      (FAT_DIRREM), hl
dsm_secloop:
                ld      hl, (FAT_DIRREM)
                ld      a, h
                or      l
                jp      z, ds_none          ; scanned every remaining root sector
                ld      de, (FAT_DIRSEC)
                ld      hl, SECTOR_BUF
                call    read_sector
                jp      c, ds_none          ; FDC error -> exhausted (no entry)
                ; start entry-in-sector = BDOS_SRCHIDX & 15
                ld      a, (BDOS_SRCHIDX)
                and     $0F
                ld      c, a                ; C = entry index within this sector
                ; HL = SECTOR_BUF + entry*32
                ld      hl, SECTOR_BUF
                ld      b, a
                or      a
                jr      z, dsm_athl
dsm_addent:
                ld      de, 32
                add     hl, de
                djnz    dsm_addent
dsm_athl:
                ld      a, 16
                sub     c
                ld      b, a                ; B = entries left in THIS sector (16-C)
dsm_entloop:
                ld      a, (hl)
                or      a
                jp      z, ds_none          ; $00 = end of directory -> exhausted
                cp      $E5
                jr      z, dsm_skip         ; deleted entry -> skip (no filter else)
                ld      de, (FAT_NAMEPTR)
                push    hl
                push    bc
                call    name_cmp_wild       ; Z if the 8.3 name matches the pattern
                pop     bc
                pop     hl
                jr      z, dsm_found
dsm_skip:
                ld      de, 32
                add     hl, de              ; next 32-byte directory entry
                call    dsm_bump            ; BDOS_SRCHIDX += 1 (advance past this one)
                djnz    dsm_entloop
                ; sector done: advance FAT_DIRSEC, dec FAT_DIRREM, next sector.
                ld      hl, (FAT_DIRSEC)
                inc     hl
                ld      (FAT_DIRSEC), hl
                ld      hl, (FAT_DIRREM)
                dec     hl
                ld      (FAT_DIRREM), hl
                jr      dsm_secloop
dsm_found:
                ; HL = matched 32-byte directory entry. Build the runtime DTA as the
                ; MSX-DOS SFIRST/SNEXT "found FCB" (drive + unopened FCB), matching
                ; stock byte-for-byte in every field COMMAND.COM's DIR reads (name,
                ; attribute, time, date, first cluster, size). The field layout was
                ; pinned black-box against stock's DTA + a readwatch of the DIR
                ; formatter's DTA reads (M19 §4.4):
                ;   DTA[0]      = drive (current drive + 1)
                ;   DTA[1..11]  = entry[0..10]  (11-byte 8.3 name)
                ;   DTA[12]     = 0  (FCB extent/EX)
                ;   DTA[13]     = entry[11]     (attribute)
                ;   DTA[14..22] = 0  (incl. the computed record-count field DIR
                ;                 never reads; left 0 -- black-box confirmed unread)
                ;   DTA[23..32] = entry[22..31] (time, date, first cluster, size)
                ; The attribute at DTA[13] is what lets DIR filter volume-label /
                ; subdir entries and count "nn files" correctly -- writing a verbatim
                ; raw entry (attr at DTA[12]) mis-set that filter (the alternating-
                ; garbage / wrong-count bug). CLEAN-ROOM: our own field copy from our
                ; own dir walk into the published FCB-result layout; no stock code.
                push    hl                  ; save entry ptr
                ld      de, (DOS_DTAPTR)    ; DE = runtime DTA base
                push    de                  ; save DTA base
                ; zero DTA[0..32] (33 bytes) so all gap/unset fields are $00.
                ld      h, d
                ld      l, e                ; HL = DTA base
                ld      (hl), 0
                push    hl
                pop     de                  ; DE = DTA base
                inc     de                  ; DE = DTA+1
                ld      bc, 32
                ldir                        ; propagate the $00 across DTA[1..32]
                pop     de                  ; DE = DTA base
                pop     hl                  ; HL = matched dir entry
                ; DTA[0] = drive (current drive + 1)
                ld      a, (CURDRV_CELL)
                inc     a
                ld      (de), a
                inc     de                  ; DE = DTA+1
                ; DTA[1..11] = entry[0..10] (name)
                push    hl                  ; keep entry base
                ld      bc, 11
                ldir                        ; -> DTA[1..11]; HL=entry+11, DE=DTA+12
                ; DTA[12] stays 0; DTA[13] = entry[11] (attr)
                inc     de                  ; DE = DTA+13
                ld      a, (hl)             ; entry[11] = attribute
                ld      (de), a
                ; DTA[14..22] stay 0; DTA[23..32] = entry[22..31]
                pop     hl                  ; HL = entry base
                ld      bc, 22
                add     hl, bc              ; HL = entry+22 (time/date/clus/size)
                ld      de, (DOS_DTAPTR)
                ld      a, e
                add     a, 23
                ld      e, a
                jr      nc, dsm_nohc
                inc     d
dsm_nohc:
                ld      bc, 10
                ldir                        ; -> DTA[23..32]
                call    dsm_bump            ; BDOS_SRCHIDX := match-index + 1
                xor     a                   ; A = $00 = found
                ret
ds_none:
                ld      a, $FF              ; A = $FF = no (more) matching entry
                ret

; dsm_bump — BDOS_SRCHIDX += 1 (advance the persistent scan cursor). Preserves all
; registers (HL is the live entry pointer at both call sites).
dsm_bump:
                push    hl
                ld      hl, (BDOS_SRCHIDX)
                inc     hl
                ld      (BDOS_SRCHIDX), hl
                pop     hl
                ret

; name_cmp_wild — compare an 11-byte dir name against the search pattern, with the
; FCB ? wildcard: a pattern byte of $3F matches any single character. Otherwise
; identical to name_cmp (case-insensitive via toupper). (Published CP/M-2.2 /
; MSX-DOS FCB match rule; M19 §4.5 — verified DIR issues an all-? pattern.)
;   in:  HL = directory-entry name, DE = search pattern ; out: Z set if match;
;        trashes A, B, DE, HL (HL/DE advanced 11 bytes; C preserved)
name_cmp_wild:
                ld      b, 11
ncw_loop:
                ld      a, (de)
                cp      $3F                 ; '?' pattern byte matches anything
                jr      z, ncw_next
                ld      a, (de)
                call    toupper
                ld      c, a
                ld      a, (hl)
                call    toupper
                cp      c
                ret     nz                  ; mismatch -> Z clear
ncw_next:
                inc     hl                  ; 16-bit inc: leaves flags intact
                inc     de
                djnz    ncw_loop
                ret                         ; Z set (all 11 positions matched)

