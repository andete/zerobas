; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; Part of zerobas-disk, included by disk.asm (build with `pasmo -I disk`).
; the disk driver: DSKIO/DSKCHG/GETDPB/DSKFMT + WD2793 FDC primitives
; CLEAN-ROOM: every constant, address and algorithm here traces to a public source
; or a black-box oracle probe; nothing is derived from disassembly. See disk/PROVENANCE.md.

; --- Disk entry-point handlers ---------------------------------------------

; dskio — physical sector read/write (disk-ROM entry +$10; also the H.DSKIO
; hook target). MSX2 TH disk ROM interface:
;   in:  Cy = 0 read / 1 write; A = drive; B = sector count; C = media byte;
;        DE = start logical sector; HL = transfer address
;   out: Cy = 0 ok; Cy = 1 error with A = error code, B = sectors not done
; Single-drive machine: drive number and media byte are ignored (always drive
; A). Both directions are implemented: read via fdc_read_phys, write via
; fdc_write_phys. See PROVENANCE.md §FDC / §DSKIO interface.
dskio:
                jr      c, dskio_write
                ; --- read path ---
                ld      a, b
                or      a
                jr      z, dskio_ok     ; zero sectors -> nothing to do
                ld      (FDC_CNT), a
                ld      (FDC_LSEC), de
                ld      (FDC_DEST), hl
dskio_next:
                ld      a, (FDC_CNT)
                or      a
                jr      z, dskio_ok
                ; logical sector -> CHS (track/side/sector)
                ld      hl, (FDC_LSEC)
                call    div9            ; B = track*2+head, L = sector-1 (H=0)
                ld      a, l
                inc     a
                ld      c, a            ; C = sector (1..9)
                ld      a, b
                and     1
                ld      e, a            ; E = side (0/1)
                srl     b
                ld      d, b            ; D = track (0..79)
                ld      hl, (FDC_DEST)
                ; page-1 bounce: if destination in $4000-$7FFF (page 1 = our disk
                ; ROM under DOS) read into SECTOR_BUF then blit to the real target
                ; with page 1 remapped to RAM (a3 §8.35 / p1_blit_tmpl below).
                ld      a, h
                and     $C0
                cp      $40             ; $4000-$7FFF: bit7=0, bit6=1
                jr      nz, dskio_rd    ; not page 1 -> direct path
                ld      (P1_DEST), hl   ; save real page-1 destination
                ld      hl, SECTOR_BUF
                ld      (FDC_DEST), hl  ; redirect FDC to bounce buffer
                call    fdc_read_phys
                jr      c, dskio_err
                call    fdc_di_save     ; a3 §8.36: mask across the page-1 blit too
                call    P1_BLIT         ; copy SECTOR_BUF -> P1_DEST with page1=RAM
                call    fdc_io_done     ; restore caller IFF after the blit
                ld      hl, (P1_DEST)
                ld      de, 512
                add     hl, de
                ld      (FDC_DEST), hl  ; advance real destination by 512
                jr      dskio_adv
dskio_rd:
                call    fdc_read_phys
                jr      c, dskio_err
                ld      (FDC_DEST), hl  ; HL = buf+512, advance for next sector
dskio_adv:
                ld      hl, (FDC_LSEC)
                inc     hl
                ld      (FDC_LSEC), hl
                ld      a, (FDC_CNT)
                dec     a
                ld      (FDC_CNT), a
                jr      dskio_next
dskio_ok:
                call    mtoff           ; spin the motor down
                ld      b, 0            ; B = 0: all sectors done (DSKIO success contract)
                or      a               ; Cy = 0
                ret
dskio_err:
                push    af              ; save error code + carry
                call    mtoff
                ld      a, (FDC_CNT)
                ld      b, a            ; B = sectors not transferred
                pop     af
                ret                     ; Cy still set, A = error code
; --- write path -------------------------------------------------------------
; Mirrors the read loop's structure exactly: loop the sector count, convert each
; logical sector -> CHS via div9, and call fdc_write_phys (the write twin of
; fdc_read_phys). On entry Cy = 1 (write direction); registers as for read.
dskio_write:
                ld      a, b
                or      a
                jr      z, dskio_ok     ; zero sectors -> nothing to do
                ld      (FDC_CNT), a
                ld      (FDC_LSEC), de
                ld      (FDC_DEST), hl
dskio_wnext:
                ld      a, (FDC_CNT)
                or      a
                jr      z, dskio_ok
                ; logical sector -> CHS (track/side/sector), same as the read path
                ld      hl, (FDC_LSEC)
                call    div9            ; B = track*2+head, L = sector-1 (H=0)
                ld      a, l
                inc     a
                ld      c, a            ; C = sector (1..9)
                ld      a, b
                and     1
                ld      e, a            ; E = side (0/1)
                srl     b
                ld      d, b            ; D = track (0..79)
                ld      hl, (FDC_DEST)
                call    fdc_write_phys
                jr      c, dskio_err
                ld      (FDC_DEST), hl  ; HL advanced by 512 on success
                ld      hl, (FDC_LSEC)
                inc     hl
                ld      (FDC_LSEC), hl
                ld      a, (FDC_CNT)
                dec     a
                ld      (FDC_CNT), a
                jr      dskio_wnext

; fdc_read_phys — read one physical sector into (HL).
;   in:  D = track, E = side (0/1), C = sector (1..9), HL = buffer
;   out: Cy = 0 ok, HL advanced 512; Cy = 1 error, A = DSKIO error code
; Selects drive A + side + motor, then seeks and reads, retrying once via a
; restore if the first attempt fails (recovers a stale Track register).
fdc_read_phys:
                call    fdc_di_save     ; mask interrupts across the transfer
                ld      a, CTRL_DRIVE_A + CTRL_MOTOR
                bit     0, e
                jr      z, fdc_rp_nos
                or      CTRL_SIDE
fdc_rp_nos:
                ld      (FDC_CTRL), a
                call    fdc_settle      ; motor spin-up / head settle
                ld      a, 2
                ld      (FDC_TRY), a    ; up to two attempts
fdc_rp_attempt:
                ; seek to target track (track number via Data register)
                ld      a, d
                ld      (FDC_DATA), a
                ld      a, CMD_SEEK
                ld      (FDC_STATUS), a
                call    fdc_wait_ready
                ; issue read-sector and transfer the data
                ld      a, c
                ld      (FDC_SECTOR), a
                ld      hl, (FDC_DEST)  ; reload buffer start each attempt
                ld      a, CMD_READ
                ld      (FDC_STATUS), a
                call    fdc_read_data
                jp      nc, fdc_io_done ; success: Cy = 0, HL = buffer + 512
                ; failure: A = error code, Cy = 1
                push    af
                ld      a, (FDC_TRY)
                dec     a
                ld      (FDC_TRY), a
                jr      z, fdc_rp_fail
                pop     af
                call    fdc_restore     ; recalibrate, then retry
                jr      fdc_rp_attempt
fdc_rp_fail:
                pop     af              ; restore error code + carry
                jp      fdc_io_done

; fdc_read_data — transfer 512 bytes of a read-sector command into (HL).
;   in:  HL = buffer; a READ command has just been written
;   out: Cy = 0 ok, HL += 512; Cy = 1 error with A = DSKIO error code
; Polled transfer: 512 = 2 x 256 (E = block counter, B = byte counter), so the
; sector (C) and track (D) registers survive for a possible retry.
; RELOCATED (M26, tier2-m26-spec.md): this 74-byte body used to live here
; in full, but 56 bytes in (the fdc_rd_n1/fdc_rd_n2 status-decode tail) it
; collided with the real kernel's canonical $17 FREN dispatch entry, $4392
; (confirmed via trace --resync: stock's real disk ROM jumps to its own
; FREN body from that exact address; ours fell through into this unrelated
; FDC code instead -- the same address-collision shape as M21's $4462 and
; M24's $456F). Only ONE caller (`call fdc_read_data` in fdc_rp_attempt
; above), self-contained, no external refs into its middle -- so it
; relocates cleanly. Real body now fdc_read_data_body (kernel.asm free
; tail); this span is net-zero pad with the fren_body veneer planted at
; the pinned offset so fdc_write_phys below stays at its exact address.
fdc_read_data:
                jp      fdc_read_data_body
                ds      $436C - $, $00      ; pad remainder up to the pinned canonical entry
k_436C:
                jp      fdel_body           ; $436C: BDOS $13 FDEL canonical entry (M26)
                                            ; (re-characterised 2026-07-03: this address used
                                            ; to sit mid-body inside fdc_read_data's OLD span;
                                            ; landing FREN's relocation above turned it into
                                            ; dead pad -- but before this fix, the un-wired
                                            ; FDEL call NOP-slid straight through into
                                            ; fren_body with FDEL's own FCB, corrupting the
                                            ; target directory entry. See tier2-m26-spec.md
                                            ; sec 2.2.)
                ds      $4392 - $, $00      ; pad remainder up to the next canonical entry
k_4392:
                jp      fren_body           ; $4392: BDOS $17 FREN canonical entry (M26)
                ds      $43A4 - $, $00      ; net-zero: fdc_write_phys stays at $43A4

; fdc_write_phys — write one physical sector from (HL).
;   in:  D = track, E = side (0/1), C = sector (1..9), HL = buffer
;   out: Cy = 0 ok, HL advanced 512; Cy = 1 error, A = DSKIO error code
; The write twin of fdc_read_phys: selects drive A + side + motor, seeks to the
; target track, then issues the WD2793 Write Sector command (CMD_WRITE = $A0,
; single record) and feeds the 512-byte payload to the data register on DRQ.
; Retries once via a restore if the first attempt fails (recovers a stale Track
; register after a reset), exactly like the read path. A genuine write-protected
; disk is reported up front (no retry) by fdc_write_data's status check.
fdc_write_phys:
                call    fdc_di_save     ; mask interrupts across the transfer
                ld      a, CTRL_DRIVE_A + CTRL_MOTOR
                bit     0, e
                jr      z, fdc_wp_nos
                or      CTRL_SIDE
fdc_wp_nos:
                ld      (FDC_CTRL), a
                call    fdc_settle      ; motor spin-up / head settle
                ld      a, 2
                ld      (FDC_TRY), a    ; up to two attempts
fdc_wp_attempt:
                ; seek to target track (track number via Data register)
                ld      a, d
                ld      (FDC_DATA), a
                ld      a, CMD_SEEK
                ld      (FDC_STATUS), a
                call    fdc_wait_ready
                ; D-DISKERR (docs/spec-basic-diskerr.md): an EMPTY drive must fail a
                ; write the way it fails a read -- the seek's type-I status carries
                ; NOT READY; the body is in the kernel's corridor (this span has 7 B
                ; before the $4462 pin).
                call    fdc_wp_chkrdy   ; CY, A=2 when the drive is not ready
                jp      c, fdc_wp_fail
                ; issue write-sector and transfer the data
                ld      a, c
                ld      (FDC_SECTOR), a
                ld      hl, (FDC_DEST)  ; reload buffer start each attempt
                ld      a, CMD_WRITE
                ld      (FDC_STATUS), a
                call    fdc_write_data
                jp      nc, fdc_io_done ; success: Cy = 0, HL = buffer + 512
                ; failure: A = error code, Cy = 1
                cp      0               ; error code 0 = write protected -> no retry
                jr      z, fdc_wp_fail
                push    af
                ld      a, (FDC_TRY)
                dec     a
                ld      (FDC_TRY), a
                jr      z, fdc_wp_fail2
                pop     af
                call    fdc_restore     ; recalibrate, then retry
                jr      fdc_wp_attempt
fdc_wp_fail2:
                pop     af              ; restore error code + carry
fdc_wp_fail:
                jp      fdc_io_done

; fdc_write_data — transfer 512 bytes from (HL) to a write-sector command.
;   in:  HL = buffer; a WRITE command has just been written
;   out: Cy = 0 ok, HL += 512; Cy = 1 error with A = DSKIO error code
; Polled transfer, the exact write twin of fdc_read_data: 512 = 2 x 256
; (E = block counter, B = byte counter), so the sector (C) and track (D)
; registers survive for a possible retry. The WD2793 asserts DRQ when it is ready
; for the next data byte; the driver polls the status register at $7FB8 and writes
; each byte to the data register. After the last byte it polls for BUSY-clear and
; reads the result-phase status: bit 6 ($40) on a Type-II write is WRITE FAULT /
; write-protect -> DSKIO write-protected (code 0); RNF/CRC/LOST/NOTRDY map exactly
; as the read path does.  (WD2793 DS: Write Sector, status register Type II.)
fdc_write_data:
                ld      e, 2            ; two 256-byte halves
fdc_wr_blk:
                ld      b, 0            ; djnz 0 -> 256 iterations
fdc_wr_wait:
                ld      a, (FDC_STATUS)
                bit     1, a            ; DRQ?
                jr      nz, fdc_wr_byte
                bit     0, a            ; BUSY?
                jr      nz, fdc_wr_wait
                jr      fdc_wr_status   ; finished with no DRQ -> short/error
fdc_wr_byte:
                ld      a, (hl)
                ld      (FDC_DATA), a
                inc     hl
                djnz    fdc_wr_wait
                dec     e
                jr      nz, fdc_wr_blk
fdc_wr_drain:
                ld      a, (FDC_STATUS) ; all 512 written; wait for command end
                bit     0, a
                jr      nz, fdc_wr_drain
fdc_wr_status:
                ld      a, (FDC_STATUS)
                ; write-protect / write-fault (bit 6, $40) -> DSKIO code 0 first,
                ; so a protected disk reports write-protected rather than retrying.
                and     ST_WP
                jr      z, fdc_wr_chk
                xor     a               ; A = 0 = write protected
                scf
                ret
fdc_wr_chk:
                ld      a, (FDC_STATUS)
                and     ST_NOTRDY + ST_RNF + ST_CRC + ST_LOST
                jr      z, fdc_wr_ok
                ld      b, a            ; keep the error bits
                and     ST_NOTRDY
                jr      z, fdc_wr_n1
                ld      a, 2            ; not ready
                scf
                ret
fdc_wr_n1:
                ld      a, b
                and     ST_RNF
                jr      z, fdc_wr_n2
                ld      a, 8            ; record not found
                scf
                ret
fdc_wr_n2:
                ld      a, b
                and     ST_CRC
                jr      z, fdc_wr_n3
                ld      a, 4            ; CRC / data error
                scf
                ret
fdc_wr_n3:
                ld      a, 12           ; lost data / other
                scf
                ret
fdc_wr_ok:
                or      a               ; A = 0, Cy = 0
                ret

; fdc_restore — recalibrate the head to track 0 (Type I restore).
fdc_restore:
                ld      a, CMD_RESTORE
                ld      (FDC_STATUS), a
                ; fall through to fdc_wait_ready

; fdc_wait_ready — wait for the WD2793 to finish (BUSY clear).
fdc_wait_ready:
                call    fdc_settle      ; let BUSY assert before polling
fdc_wr_loop:
                ld      a, (FDC_STATUS)
                bit     0, a            ; BUSY?
                jr      nz, fdc_wr_loop
                ret

; fdc_settle — short busy-wait (~0.9 ms) for command latency / motor spin-up.
fdc_settle:
                push    bc
                ld      b, 0            ; 256 iterations
fdc_st_loop:
                djnz    fdc_st_loop
                pop     bc
                ret

; fdc_di_save/fdc_io_done/div9/dskchg/getdpb relocated to disk/fat.asm's free
; tail (M21a, disk/docs/tier2-m21-spec.md §5.3): $4462 — a byte inside the old
; fdc_di_save body — collided with the kernel's FOPEN dir-fill entry point
; (RC-1). Vacating this span lets a real veneer sit exactly at $4462; every
; caller of the moved routines resolves by symbol (grep-confirmed, §5.3), so
; no repoint is needed anywhere but here.
                ds      $4462 - $, $00      ; pad to the collision point
                jp      fopen_fill_body     ; M21a: real FOPEN dir-fill (disk/fat.asm)
                ds      $44F4 - $, $00      ; pad the rest of the vacated span (net-zero)

; choice — format-choice string (CHOICE entry point).
; Return HL = 0 (no format-choice string): we support only one fixed 720 KB
; geometry (MSX2 TH, disk ROM interface: HL = 0 means no choices offered).
choice:
                ld      hl, 0
                ret

; dskfmt — format disk (write support deferred indefinitely; not a loader need).
dskfmt:
                scf
                ret

; mtoff — turn off disk motor(s).
; Clear the National control latch: deselect the drive and drop the motor line.
; MSX2 TH: MTOFF has no error-return convention; the BIOS ignores the return state.
mtoff:
                xor     a
                ld      (FDC_CTRL), a
                ret

; bdos_entry — BDOS dispatcher (written into the SYSTEM sysvar by INIT).
; CP/M-compatible calling convention (MSX2 TH, MSX-DOS BDOS conventions):
;   in:  C = call number, DE = FCB pointer (for FCB calls)
;   out: A = result
; Implements the read-only FCB subset zerobas's BLOAD path needs: Open ($0F),
; Sequential Read ($14), Close ($10). Any other call returns A=$FF.
;
; Position model (own design / simplification): only one file is open at a time.
; The open file's chain position lives in the FAT iterator (fat_open / fat_read_
; file_sector); BDOS_RECIDX tracks which 128-byte record of the current 512-byte
; SECTOR_BUF the next read delivers; BDOS_BYTESLEFT (seeded from FAT_FILESIZE by
; Open) bounds the partial final record and the EOF point by the true file size.
; The FCB extent (+12) / current-record (+32) / record-count (+15) / alloc-map
; (+16..31) bookkeeping fields are left untouched — a DOCUMENTED INTENTIONAL
; DIVERGENCE from MSX-DOS (no bdos_entry caller reads them; differential-
; characterised by disk_probe_bdos.py PART B). The drive (+0) and 8.3-name
; (+1..+11) fields a reasonable caller reads stay byte-identical to MSX-DOS.
; See disk/PROVENANCE.md §BDOS interface.
bdos_entry:
                ld      a, c
                cp      BDOS_F_OPEN
                jr      z, bdos_open
                cp      BDOS_F_SEQRD
                jp      z, bdos_seqread
                cp      BDOS_F_CLOSE
                jp      z, bdos_close
                cp      BDOS_F_SETDTA
                jr      z, bdos_setdta
                cp      BDOS_F_CREATE
                jp      z, bdos_create
                cp      BDOS_F_SEQWR
                jp      z, bdos_seqwrite
                cp      BDOS_F_RDBLK
                jp      z, bdos_rdblk
                ld      a, $FF          ; unsupported call
                ret

; bdos_setdta ($1A) — set the Disk Transfer Area address.
;   in:  DE = new DTA pointer
;   out: (no documented result; A undefined per MSX-DOS) — we leave A as-is
; Stores DE into BDOS_DTA; subsequent SeqReads copy each 128-byte record there
; instead of the $0080 default. (MSX2 TH / MSX-DOS BDOS call table.)
bdos_setdta:
                ld      (BDOS_DTA), de
                ret

; bdos_open ($0F) — open the file named in the FCB.
; Mounts the volume (BPB), searches the root directory for the FCB's 11-byte 8.3
; name (+1..+11), and primes the sequential iterator.
;   in:  DE = FCB pointer
;   out: A = $00 opened / $FF not found or I/O error (MSX2 TH, BDOS conventions)
bdos_open:
                xor     a
                ld      (BDOS_WRMODE), a    ; an Open is a READ open; clear write state
                push    de              ; save FCB pointer across fat_mount
                call    fat_mount
                jr      c, bdos_open_failpop
                pop     hl              ; HL = FCB
                inc     hl              ; HL = FCB+1 = 11-byte 8.3 name field
                call    fat_find
                jr      c, bdos_open_err
                call    fat_open
                ld      a, RECPERSEC    ; buffer empty -> first read refills
                ld      (BDOS_RECIDX), a
                ; Seed the bytes-remaining counter from the true file size so
                ; Sequential Read can bound the partial final record + EOF.
                ld      hl, FAT_FILESIZE
                ld      de, BDOS_BYTESLEFT
                ld      bc, 4
                ldir                    ; BDOS_BYTESLEFT = FAT_FILESIZE (4-byte LE)
                xor     a               ; A = $00 success
                ret
bdos_open_failpop:
                pop     hl              ; discard saved FCB pointer
bdos_open_err:
                ld      a, $FF
                ret

; bdos_seqread ($14) — read the next 128-byte record into the DTA (BDOS_DTA).
; The record stream is bounded by the true file size in BDOS_BYTESLEFT (seeded
; from FAT_FILESIZE by Open, decremented per record): once it reaches 0 every
; further read returns EOF, and the final partial record is delivered with only
; n = min(RECSIZE, BYTESLEFT) real bytes followed by RECSIZE-n zero bytes, the
; whole record returned with code $00; EOF ($01) comes on the NEXT read.
;   out: A = $00 record delivered / $01 end-of-file (MSX2 TH, BDOS conventions)
; Partial-record zero-fill provenance: ORACLE OBSERVATION of real MSX-DOS 1.03 on
; a 1500-byte file (probes/disk/disk_probe_bdos.py) — the last record is
; 92 real bytes + 36 bytes of $00 (confirmed by pre-filling the DTA with $FF: the
; tail still returns $00, so MSX-DOS actively zero-fills, not Ctrl-Z/stale data),
; code $00; the following read returns $01. CP/M FCB sequential-I/O record model
; (MSX2 TH, FCB sequential I/O) supplies the record framing.
bdos_seqread:
                jp      bdos_seqread_body   ; Tier-2 3b: divert; veneer fills the gap
                ds      $4558 - $, $00      ; anchor the canonical address
                jp      k_4558              ; $4558: COMMAND.COM-load kernel veneer
; --- MSX-DOS-1 kernel FCLOSE-finaliser entry: $456F (M24 slice A;
; tier2-m24-fclose-multicluster-spec.md) --------------------------------------
; The RAM kernel implements the FCB write tier (FMAKE/WRSEQ/FCLOSE) itself and
; CALLs three page-1 canonical worker entries for it; pre-M24 all three were
; un-wired. This one ($456F, the FCLOSE finaliser) fell on a lone $00 pad byte
; that NOP-slid into bsr_have (the Sequential-Read record copier): with the
; ambient BDOS_BYTESLEFT left at 0 after a completed .COM load, bsr_have's
; n := min(RECSIZE, BYTESLEFT) computed 0, and its LDIR ran with BC=0 -- a
; 65536-byte block move that sprayed the whole RAM map, crashing every write-mode
; Close of a file needing real flush/FAT/dir work (BDOSX3 record 10 exposed
; it; earlier FCLOSE calls survived only by luck, hitting this fall-in with a
; nonzero ambient BYTESLEFT that made the same LDIR a harmless copy).
; Reproduces stock's finaliser contract with OUR already-proven bdos_close
; (BDOS_WRMODE-gated: cheap no-op for a read-close, flush + fat_dir_update for
; a dirty write-close) -- no stock algorithm decoded, only the call-target
; address pinned black-box (ret=$D88A dispatcher class, DE=IY=$DA40 kernel FCB
; pointer). bsr_have is NOT itself a canonical address (only $4558/$456F are);
; shifting it by 2 bytes here is safe (M15 SS7.3 free-fall convention).
                ds      $456F - $, $00      ; pad up to the pinned $456F FCLOSE-finaliser entry
k_456F:
                jp      bdos_close          ; $456F: BDOS $10 FCLOSE canonical entry (M24 slice A)
bsr_have:
                ; n = real bytes this record = min(RECSIZE, BYTESLEFT).
                ; BYTESLEFT is nonzero here; if the high word is set or low word
                ; >= RECSIZE then a full RECSIZE record; otherwise n = low byte.
                ld      hl, (BDOS_BYTESLEFT + 2)    ; high word
                ld      a, h
                or      l
                jr      nz, bsr_full                ; >= 65536 left -> full record
                ld      hl, (BDOS_BYTESLEFT)        ; low word
                ld      a, h
                or      a
                jr      nz, bsr_full                ; >= 256 left -> full record
                ld      a, l                        ; < 256 bytes left
                cp      RECSIZE
                jr      c, bsr_partial              ; < 128 -> partial record
bsr_full:
                ld      a, RECSIZE                  ; full 128-byte record
bsr_partial:
                ; A = n (real bytes, 1..128). Compute source in SECTOR_BUF.
                push    af                          ; save n
                ld      a, (BDOS_RECIDX)
                ld      h, 0
                ld      l, a
                add     hl, hl          ; *2
                add     hl, hl          ; *4
                add     hl, hl          ; *8
                add     hl, hl          ; *16
                add     hl, hl          ; *32
                add     hl, hl          ; *64
                add     hl, hl          ; HL = RECIDX * 128
                ld      de, SECTOR_BUF
                add     hl, de          ; HL = source record in SECTOR_BUF
                ld      de, (BDOS_DTA)  ; settable DTA (BDOS $1A); default $0080
                pop     af              ; A = n
                push    af              ; keep n for the decrement
                ld      c, a
                ld      b, 0            ; BC = n real bytes
                ldir                    ; copy n real bytes to the DTA
                ; zero-fill the remaining RECSIZE - n bytes of the record (DE now
                ; points just past the real bytes in the DTA).
                pop     af              ; A = n
                push    af              ; keep n for the decrement
                neg
                add     a, RECSIZE      ; A = RECSIZE - n (pad count, 0..127)
                jr      z, bsr_nopad
                ld      b, a            ; B = pad byte count
bsr_padloop:
                xor     a
                ld      (de), a         ; zero-fill (oracle: MSX-DOS pads with $00)
                inc     de
                djnz    bsr_padloop
bsr_nopad:
                ; BYTESLEFT -= n (n in A on stack); 4-byte LE subtract.
                pop     af              ; A = n
                ld      hl, BDOS_BYTESLEFT
                ld      c, a
                ld      a, (hl)
                sub     c
                ld      (hl), a
                inc     hl
                ld      b, 3            ; propagate borrow through the upper 3 bytes
bsr_borrow:
                ld      a, (hl)
                sbc     a, 0
                ld      (hl), a
                inc     hl
                djnz    bsr_borrow
                ld      a, (BDOS_RECIDX)
                inc     a
                ld      (BDOS_RECIDX), a
                xor     a               ; A = $00 success
                ret
bsr_eof:
                ld      a, $01          ; end-of-file
                ret

; bdos_rdblk ($27) — Random Block Read (RDBLK). The MSX-DOS-1 boot loads
; MSXDOS.SYS through this (a3 §8.9): after Open + SetDTA it issues $27 with a huge
; record count to pull the whole file in.
;   in:  DE = FCB (already Open'd), HL = number of records to read
;        record size  = FCB +14..15 (word; 0 -> default 128)
;        start record = FCB +33..35 — SUPPORTED ONLY AS 0 (read from file start);
;                       the boot always passes 0. A non-zero random seek is a
;                       documented simplification (no boot path uses it).
;        DTA          = BDOS_DTA (set by the preceding $1A); records land at
;                       DTA, DTA+recsize, … within this one call (BDOS_DTA itself
;                       is left unchanged for later calls).
;   out: A  = $00 all requested records read / $01 EOF before all (partial)
;        HL = number of records actually read
;        BC = HL (the genuine BDOS $27 returns the count in both; MSXDOS.SYS
;             init reads BC at its $024A sign branch — §8.32/§8.33)
; Re-primes the file iterator to the start each call (idempotent random-record-0
; semantics) and streams bytes from SECTOR_BUF, refilling via fat_read_file_sector.
; Bounded by the true file size in BDOS_BYTESLEFT (reseeded from FAT_FILESIZE here).
; See disk/PROVENANCE.md §BDOS interface.
bdos_rdblk:
                ld      (RDBLK_REQ), hl     ; save requested record count
                ; record size <- FCB+14..15 (DE = FCB)
                ld      hl, 14
                add     hl, de
                ld      a, (hl)
                ld      (RDBLK_RECSIZE), a
                inc     hl
                ld      a, (hl)
                ld      (RDBLK_RECSIZE + 1), a
                ld      hl, (RDBLK_RECSIZE) ; 0 -> default 128 (MSX-DOS block I/O)
                ld      a, h
                or      l
                jr      nz, rdb_rs_ok
                ld      hl, RECSIZE
                ld      (RDBLK_RECSIZE), hl
rdb_rs_ok:
                ; re-prime the read position to the file start (random record 0)
                call    fat_open            ; iterator -> FAT_FIRSTCLUS, clussec 0
                ld      hl, FAT_FILESIZE    ; BDOS_BYTESLEFT = true file size
                ld      de, BDOS_BYTESLEFT
                ld      bc, 4
                ldir
                ld      hl, 512
                ld      (RDBLK_BUFPOS), hl  ; force a sector refill on the first byte
                ld      hl, 0
                ld      (RDBLK_DONE), hl    ; no records delivered yet
                ld      hl, (BDOS_DTA)
                ld      (RDBLK_DST), hl     ; local write pointer (BDOS_DTA preserved)
                jp      rdb_recloop_body    ; Tier-2 3b: divert; veneer fills the gap (M24 slice B)
; --- MSX-DOS-1 kernel FMAKE-worker entry: $461D (M24 slice B;
; tier2-m24-fclose-multicluster-spec.md) --------------------------------------
; The RAM kernel's BDOS $16 FMAKE handling CALLs this page-1 entry with the
; same convention our own bdos_create already expects (DE = FCB pointer,
; FCB+1 = 11-byte 8.3 name; pinned black-box, ret=$D88A dispatcher class,
; DE=IY=$DA40 kernel FCB pointer) -- so the body is a direct tail-call, no
; wrapper needed. Pre-M24 this fell on a byte inside rdb_byteloop's
; predecessor instruction (the M21b RDBLK loop), producing the harmless-but-
; wrong A=$01 exit (the "n=37" register oddity) instead of ever creating a
; file. rdb_recloop..rdb_eof (unchanged, M21b) are relocated below to make
; room -- position-free, reached only by label from bdos_rdblk's own
; `jp rdb_recloop_body` fall-through above.
                ds      $461D - $, $00      ; pad up to the pinned $461D FMAKE-worker entry
k_461D:
                jp      bdos_create         ; $461D: BDOS $16 FMAKE canonical entry (M24 slice B)

; rdblk_getbyte — deliver the next byte of the open file in A, refilling
; SECTOR_BUF from the cluster chain when exhausted and decrementing BDOS_BYTESLEFT.
;   out: Cy = 0 ok (A = byte) / Cy = 1 chain ended (caller guards with BYTESLEFT).
; Uses RDBLK_BUFPOS (0..512). Clobbers A + flags only (works through HL/DE/C via the
; helper, which the caller does not rely on across the call).
rdblk_getbyte:
                ld      hl, (RDBLK_BUFPOS)
                ld      de, 512
                or      a
                sbc     hl, de
                jr      c, rgb_have         ; BUFPOS < 512 -> a byte is buffered
                call    fat_read_file_sector ; refill SECTOR_BUF with the next sector
                ret     c                   ; chain ended -> Cy = 1
                ld      hl, 0
                ld      (RDBLK_BUFPOS), hl
rgb_have:
                ld      hl, (RDBLK_BUFPOS)
                inc     hl
                ld      (RDBLK_BUFPOS), hl  ; advance for next time
                dec     hl                  ; HL = the byte's index
                ld      de, SECTOR_BUF
                add     hl, de
                ld      c, (hl)             ; C = the file byte
                ; BDOS_BYTESLEFT -= 1 (4-byte LE)
                ld      hl, BDOS_BYTESLEFT
                ld      a, (hl)
                sub     1
                ld      (hl), a
                inc     hl
                ld      a, (hl)
                sbc     a, 0
                ld      (hl), a
                inc     hl
                ld      a, (hl)
                sbc     a, 0
                ld      (hl), a
                inc     hl
                ld      a, (hl)
                sbc     a, 0
                ld      (hl), a
                ld      a, c                ; A = the byte
                or      a                   ; Cy = 0 success
                ret

; bdos_close ($10) — close the file.
;   out: A = $00 ok / $FF error (MSX2 TH, BDOS conventions)
; For a READ-opened file there is no dirty state -> success (the historical
; behaviour). For a WRITE-opened file (BDOS_WRMODE = 1) this is where the file
; is made durable: flush the partial final 512-byte sector, persist the cluster
; chain's end-of-chain marker (already linked as each cluster was allocated), and
; rewrite the directory entry with the true byte count (DIRENT_FILESIZE) and the
; first cluster (DIRENT_FIRSTCLUS). On any I/O failure return $FF.
bdos_close:
                ld      a, (BDOS_WRMODE)
                or      a
                jr      nz, bdos_close_write
                xor     a               ; read close: nothing to flush
                ret
bdos_close_write:
                xor     a
                ld      (BDOS_WRMODE), a    ; the file is no longer open for write
                ; flush any buffered partial sector (BDOS_WRBUFLEN > 0).
                ld      hl, (BDOS_WRBUFLEN)
                ld      a, h
                or      l
                jr      z, bdos_close_dir   ; nothing buffered
                call    fat_flush_data_sector
                jr      c, bdos_close_err
bdos_close_dir:
                call    fat_dir_update      ; write true size + first cluster
                jr      c, bdos_close_err
                xor     a                   ; A = $00 success
                ret
bdos_close_err:
                ld      a, $FF
                ret

