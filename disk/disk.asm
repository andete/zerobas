; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: BSD-2-Clause

; zerobas-disk — disk.asm
; ===========================================================================
; A clean-room MSX1 disk-interface ROM. Standalone 16 KB ROM that lives in an
; internal expansion slot (slot 3-1, page 1, $4000-$7FFF) on a built-in-disk
; MSX1. See README.md and disk/PROVENANCE.md.
;
; CLEAN-ROOM DISCIPLINE: every constant, address, and algorithm here traces to
; an allowed source (MSX2 Technical Handbook, WD2793 datasheet, Microsoft FAT
; spec, ECMA-107, openMSX/C-BIOS sources, or this project's own black-box
; oracle observations). Nothing is derived from any disk-ROM or MSX-BASIC
; disassembly. See disk/PROVENANCE.md.
;
; Runtime model: this is an "AB" disk-interface ROM. At boot the BIOS finds the
; header at $4000 and calls INIT, which installs the H.DSKIO / H.PHYD hooks and
; the SYSTEM (BDOS) vector, then returns to the BIOS boot scan. The BIOS disk
; subsystem reaches the driver through the six fixed-offset entry points at
; $4010..$401F.
;
; STATUS: INIT installs hooks and SYSTEM vector. The FDC read driver is
; implemented (WD2793, National memory-mapped register map, polled sector read;
; writes deferred). The FAT12 read layer is implemented (BPB parse, cluster-
; chain walk, root-directory 8.3 search, sequential file-sector read) as
; internal helpers; the BDOS/FCB layer that wires them to BLOAD is the next
; item. GETDPB is a stub pending the DSKIO oracle probe that will confirm the
; exact MSX DPB field encoding.
; ===========================================================================

; --- System addresses (disk/PROVENANCE.md §INIT / §BDOS) -------------------
; Sources: MSX2 Technical Handbook, work area / hook table.
H_PHYD          equ     $FF3E   ; H.PHYD: physical disk I/O hook (5 bytes)
H_DSKIO         equ     $FF4B   ; H.DSKIO: disk-BASIC disk I/O hook (5 bytes)
SYSTEM          equ     $F37D   ; SYSTEM sysvar: BDOS entry-point word

; --- Disk scratch RAM (disk/PROVENANCE.md §Scratch RAM) --------------------
DPB_AREA        equ     $E288   ; DPB work area (DPB_SIZE bytes)
DPB_SIZE        equ     18      ; DPB is 18 bytes (MSX2 TH, DPB layout)

; FDC driver state (6 bytes in the gap between the DPB and the sector buffer)
FDC_CNT         equ     $E29A   ; remaining sector count
FDC_LSEC        equ     $E29B   ; current logical sector (word)
FDC_DEST        equ     $E29D   ; current transfer address (word)
FDC_TRY         equ     $E29F   ; read attempt counter

; Sector buffer (512 bytes) — DSKIO reads land here for FAT12 parsing.
SECTOR_BUF      equ     $E2A0   ; 512-byte sector buffer ($E2A0-$E49F)

; --- FAT12 geometry + iterator state (disk/PROVENANCE.md §Scratch RAM) ------
; Filled by fat_mount from the on-disk BPB; the file iterator walks the cluster
; chain using them. All own-choice free page-3 RAM after the sector buffer.
FAT_SECPERCLUS  equ     $E4A0   ; sectors per cluster (byte)
FAT_FATSTART    equ     $E4A1   ; first FAT sector (= reserved sectors) (word)
FAT_FIRSTROOT   equ     $E4A3   ; first root-directory sector (word)
FAT_ROOTSECS    equ     $E4A5   ; number of root-directory sectors (word)
FAT_FIRSTDATA   equ     $E4A7   ; first data sector (word)
FAT_CURCLUS     equ     $E4A9   ; current cluster in the open file's chain (word)
FAT_CLUSSEC     equ     $E4AB   ; sector index within current cluster (byte)
FAT_FIRSTCLUS   equ     $E4AC   ; first cluster of the found file (word)
FAT_FILESIZE    equ     $E4AE   ; file size in bytes (4-byte LE)
; FAT12 working scratch (transient within a single call)
FAT_PARITY      equ     $E4B2   ; 1 = odd cluster, 0 = even (FAT12 nibble pack)
FAT_BYTEIDX     equ     $E4B3   ; byte index within a FAT sector (word, 0..511)
FAT_FATSEC      equ     $E4B5   ; FAT sector currently read (word)
FAT_B0          equ     $E4B7   ; first FAT byte of a 12-bit entry
FAT_B1          equ     $E4B8   ; second FAT byte of a 12-bit entry
FAT_NAMEPTR     equ     $E4B9   ; -> 11-byte search name (word)
FAT_DIRSEC      equ     $E4BB   ; current root-dir sector being scanned (word)
FAT_DIRREM      equ     $E4BD   ; root-dir sectors remaining to scan (word)

; --- BPB field offsets within the boot sector (Microsoft FAT spec §3.1) -----
BPB_BYTSPERSEC  equ     11      ; bytes per sector (word LE)
BPB_SECPERCLUS  equ     13      ; sectors per cluster (byte)
BPB_RSVDSECCNT  equ     14      ; reserved sectors incl. boot (word LE)
BPB_NUMFATS     equ     16      ; number of FAT copies (byte)
BPB_ROOTENTCNT  equ     17      ; max root-directory entries (word LE)
BPB_FATSZ16     equ     22      ; sectors per FAT copy (word LE)

; --- FDC: National-style memory-mapped WD2793 (disk/PROVENANCE.md §FDC) -----
; Register addresses + drive-latch bit map: openMSX src/fdc/NationalFDC.cc (GPL,
; allowed for hardware register maps). Status/command bits: WD2793 datasheet.
; The registers are memory-mapped into ROM page 1 at the canonical $7FB8 window;
; the driver runs here (slot 3-1, $4000-$7FFF) and addresses them directly.
FDC_STATUS      equ     $7FB8   ; read = status, write = command
FDC_TRACK       equ     $7FB9   ; track register
FDC_SECTOR      equ     $7FBA   ; sector register
FDC_DATA        equ     $7FBB   ; data register
FDC_CTRL        equ     $7FBC   ; write = drive/side/motor latch; read = IRQ/!DRQ

; Control-latch write bits (NationalFDC.cc writeMem)
CTRL_DRIVE_A    equ     $01     ; select drive 0 (A)
CTRL_DRIVE_B    equ     $02     ; select drive 1 (B)
CTRL_SIDE       equ     $04     ; side select (0 = side 0, 1 = side 1)
CTRL_MOTOR      equ     $08     ; motor on

; WD2793 status-register bits (WD2793 datasheet)
ST_BUSY         equ     $01     ; command in progress
ST_DRQ          equ     $02     ; data request (byte ready, Type II)
ST_LOST         equ     $04     ; lost data (Type II)
ST_CRC          equ     $08     ; CRC error
ST_RNF          equ     $10     ; record not found (Type II)
ST_WP           equ     $40     ; write protect / write fault
ST_NOTRDY       equ     $80     ; drive not ready

; WD2793 commands. Type I flags: head-load $08 + verify $04, step-rate 0 = 6 ms.
CMD_RESTORE     equ     $0C     ; restore to track 0  ($00 + headload + verify)
CMD_SEEK        equ     $1C     ; seek to (Data reg)  ($10 + headload + verify)
CMD_READ        equ     $80     ; read sector, single record
CMD_FORCEINT    equ     $D0     ; force interrupt (abort)

; --- ROM skeleton -----------------------------------------------------------
                org     $4000

; --- MSX cartridge / disk-ROM header ---------------------------------------
; Standard 16-byte cartridge header (MSX2 TH, cartridge ROM format), identical
; in shape to the main zerobas ROM: ID, INIT, STATEMENT, DEVICE, TEXT, then 6
; reserved bytes. INIT is a *word* at $4002 (the BIOS CALLs through it); the
; header is exactly 16 bytes, so the disk entry-point table begins at $4010.
                db      "AB"            ; ROM signature              ($4000)
                dw      init            ; INIT entry point           ($4002)
                dw      0               ; STATEMENT expansion (none) ($4004)
                dw      0               ; DEVICE expansion (none)    ($4006)
                dw      0               ; TEXT / BASIC program (none)($4008)
                dw      0,0,0           ; reserved                   ($400A-$400F)

; --- Disk-ROM entry-point table (MSX2 TH, disk ROM interface) --------------
; Six JP instructions at fixed offsets from the ROM base. The BIOS disk
; subsystem CALLs these; each is 3 bytes, so they land exactly on the +$10,
; +$13, +$16, +$19, +$1C, +$1F boundaries. The `ds` guard is a compile-time
; assert that the header above is exactly 16 bytes (pasmo errors if $ > $4010).
                ds      $4010 - $, $00
                jp      dskio           ; +$10  sector read/write    ($4010)
                jp      dskchg          ; +$13  disk-change status   ($4013)
                jp      getdpb          ; +$16  build DPB from BPB   ($4016)
                jp      choice          ; +$19  format-choice string ($4019)
                jp      dskfmt          ; +$1C  format disk          ($401C)
                jp      mtoff           ; +$1F  motors off           ($401F)

; --- INIT -------------------------------------------------------------------
; Called by the BIOS boot scan. Installs H.PHYD and H.DSKIO hooks in the system
; hook RAM (5-byte slots at $FF3E and $FF4B), and writes the BDOS entry-point
; address into the SYSTEM sysvar ($F37D). Then returns cleanly so the BIOS
; continues its boot sequence.
;
; Hook slot layout (MSX2 TH, hook table): a 5-byte slot patched with
; JP nn ($C3, addr_lo, addr_hi) + 2 padding bytes. The BIOS calls the slot with
; CALL; our JP redirects to the handler, and the handler's RET returns to the
; original CALL site (the BIOS's own return address is already on the stack).
;
; Source: H.PHYD $FF3E, H.DSKIO $FF4B — MSX2 TH, work area / hook table.
;         SYSTEM $F37D — MSX2 TH, work area; C-BIOS systemvars.asm.
;         JP opcode $C3, hook slot 5 bytes — MSX2 TH (all H.* hooks are 5-byte).
init:
                ld      hl, H_PHYD
                ld      de, phyd_handler
                call    install_hook
                ld      hl, H_DSKIO
                ld      de, dskio
                call    install_hook
                ld      hl, bdos_entry
                ld      (SYSTEM), hl
                ret

; install_hook: write a JP instruction into a 5-byte hook slot.
; in:  HL = hook address in page-3 RAM, DE = target handler address
; out: (HL)..(HL+4) = $C3, target_lo, target_hi, $00, $00
; trashes: A, HL
install_hook:
                ld      (hl), $C3       ; Z80 JP opcode
                inc     hl
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl
                ld      (hl), $00       ; padding (hook slots are 5 bytes)
                inc     hl
                ld      (hl), $00
                ret

; --- Disk entry-point handlers ---------------------------------------------

; dskio — physical sector read/write (disk-ROM entry +$10; also the H.DSKIO
; hook target). MSX2 TH disk ROM interface:
;   in:  Cy = 0 read / 1 write; A = drive; B = sector count; C = media byte;
;        DE = start logical sector; HL = transfer address
;   out: Cy = 0 ok; Cy = 1 error with A = error code, B = sectors not done
; Single-drive machine: drive number and media byte are ignored (always drive
; A). Writes are deferred (return write-protected). See PROVENANCE.md §FDC /
; §DSKIO interface.
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
                call    fdc_read_phys
                jr      c, dskio_err
                ld      (FDC_DEST), hl  ; HL advanced by 512 on success
                ld      hl, (FDC_LSEC)
                inc     hl
                ld      (FDC_LSEC), hl
                ld      a, (FDC_CNT)
                dec     a
                ld      (FDC_CNT), a
                jr      dskio_next
dskio_ok:
                call    mtoff           ; spin the motor down
                or      a               ; Cy = 0 (success)
                ret
dskio_err:
                push    af              ; save error code + carry
                call    mtoff
                ld      a, (FDC_CNT)
                ld      b, a            ; B = sectors not transferred
                pop     af
                ret                     ; Cy still set, A = error code
dskio_write:
                ; write support deferred: report write-protected
                ld      a, 0            ; error code 0 = write protected
                ld      b, 0
                scf
                ret

; fdc_read_phys — read one physical sector into (HL).
;   in:  D = track, E = side (0/1), C = sector (1..9), HL = buffer
;   out: Cy = 0 ok, HL advanced 512; Cy = 1 error, A = DSKIO error code
; Selects drive A + side + motor, then seeks and reads, retrying once via a
; restore if the first attempt fails (recovers a stale Track register).
fdc_read_phys:
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
                ret     nc              ; success: Cy = 0, HL = buffer + 512
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
                ret

; fdc_read_data — transfer 512 bytes of a read-sector command into (HL).
;   in:  HL = buffer; a READ command has just been written
;   out: Cy = 0 ok, HL += 512; Cy = 1 error with A = DSKIO error code
; Polled transfer: 512 = 2 x 256 (E = block counter, B = byte counter), so the
; sector (C) and track (D) registers survive for a possible retry.
fdc_read_data:
                ld      e, 2            ; two 256-byte halves
fdc_rd_blk:
                ld      b, 0            ; djnz 0 -> 256 iterations
fdc_rd_wait:
                ld      a, (FDC_STATUS)
                bit     1, a            ; DRQ?
                jr      nz, fdc_rd_byte
                bit     0, a            ; BUSY?
                jr      nz, fdc_rd_wait
                jr      fdc_rd_status   ; finished with no DRQ -> short/error
fdc_rd_byte:
                ld      a, (FDC_DATA)
                ld      (hl), a
                inc     hl
                djnz    fdc_rd_wait
                dec     e
                jr      nz, fdc_rd_blk
fdc_rd_drain:
                ld      a, (FDC_STATUS) ; all 512 read; wait for command end
                bit     0, a
                jr      nz, fdc_rd_drain
fdc_rd_status:
                ld      a, (FDC_STATUS)
                and     ST_NOTRDY + ST_RNF + ST_CRC + ST_LOST
                jr      z, fdc_rd_ok
                ld      b, a            ; keep the error bits
                and     ST_NOTRDY
                jr      z, fdc_rd_n1
                ld      a, 2            ; not ready
                scf
                ret
fdc_rd_n1:
                ld      a, b
                and     ST_RNF
                jr      z, fdc_rd_n2
                ld      a, 8            ; record not found
                scf
                ret
fdc_rd_n2:
                ld      a, b
                and     ST_CRC
                jr      z, fdc_rd_n3
                ld      a, 4            ; CRC / data error
                scf
                ret
fdc_rd_n3:
                ld      a, 12           ; lost data / other
                scf
                ret
fdc_rd_ok:
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

; div9 — divide HL by 9 (logical sector -> track*2+head, sector-1).
;   in:  HL = logical sector (0..1439)
;   out: B = quotient (HL / 9), L = remainder (0..8), H = 0; A trashed
div9:
                ld      b, 0
fdc_div_loop:
                ld      a, h
                or      a
                jr      nz, fdc_div_sub ; HL >= 256 -> definitely >= 9
                ld      a, l
                cp      9
                jr      c, fdc_div_done ; HL < 9 -> remainder in L
fdc_div_sub:
                ld      a, l
                sub     9
                ld      l, a
                jr      nc, fdc_div_nob
                dec     h
fdc_div_nob:
                inc     b
                jr      fdc_div_loop
fdc_div_done:
                ret

; dskchg — disk-change status inquiry.
; Fail with carry set until FDC driver lands.
dskchg:
                scf
                ret

; getdpb — build the Drive Parameter Block from the BPB.
; Called by the BIOS after reading the boot sector; HL points to the BPB.
; Must fill the 18-byte DPB at DPB_AREA and return with HL = DPB_AREA.
;
; STUB: DPB field encoding (directory mask, directory shift, total-clusters
; encoding) needs the MSX2 TH DPB layout chapter and the DSKIO oracle probe
; (see disk/PROVENANCE.md §Oracle probes, probe 2) before the BPB-to-DPB
; computation can be written correctly. Returns carry set (error) for now.
getdpb:
                scf
                ret

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

; phyd_handler — physical disk I/O (behind the H.PHYD hook).
; The BIOS PHYDIO entry uses the same register convention as DSKIO; for this
; single FAT12 drive the physical and logical sector paths coincide, so route
; it straight to the DSKIO read core.
phyd_handler:
                jp      dskio

; bdos_entry — BDOS entry point (written into SYSTEM sysvar by INIT).
; FAT12 / FCB layer not yet implemented. BDOS Open ($0F) returns A=$FF (error)
; per MSX2 TH BDOS conventions; used here as a general "not supported" stub.
bdos_entry:
                ld      a, $FF
                ret

; --- FAT12 layer (disk/PROVENANCE.md §FAT12 layer) -------------------------
; Read-only FAT12 on top of the DSKIO sector reader. Sources: Microsoft FAT
; filesystem specification (BPB, FAT, directory) and ECMA-107 (geometry).
; Assumes 512-byte sectors (validated at mount); the on-disk BPB supplies every
; other geometry value, so the same code serves any FAT12 image the BPB
; describes. These routines are internal helpers; the BDOS/FCB layer (next TODO
; item) wires them to zerobas's BLOAD path. End-to-end validation waits on the
; openMSX machine config + oracle probe 2 (DSKIO boot-sector read).

; read_sector — read one logical sector into a buffer via the DSKIO core.
;   in:  DE = logical sector number, HL = buffer
;   out: Cy = 0 ok, Cy = 1 error (A = DSKIO error code)
read_sector:
                xor     a               ; drive 0 (ignored); also Cy = 0 = read
                ld      b, 1            ; one sector
                ld      c, $F9          ; media byte (ignored, single drive)
                jp      dskio           ; tail-call: dskio returns to our caller

; fat_mount — read the boot sector and derive FAT12 geometry into scratch.
;   out: Cy = 0 ok (geometry valid), Cy = 1 error (FDC error / not 512 B per sec)
fat_mount:
                ld      de, 0           ; boot sector = logical sector 0
                ld      hl, SECTOR_BUF
                call    read_sector
                ret     c
                ; require 512 bytes per sector ($0200 LE) — matches SECTOR_BUF
                ld      a, (SECTOR_BUF + BPB_BYTSPERSEC)
                or      a
                jr      nz, fat_mount_bad   ; low byte must be 0
                ld      a, (SECTOR_BUF + BPB_BYTSPERSEC + 1)
                cp      2
                jr      nz, fat_mount_bad   ; high byte must be 2 ($0200 = 512)
                ld      a, (SECTOR_BUF + BPB_SECPERCLUS)
                ld      (FAT_SECPERCLUS), a
                ld      hl, (SECTOR_BUF + BPB_RSVDSECCNT)
                ld      (FAT_FATSTART), hl  ; first FAT sector = reserved sectors
                ; first root sector = reserved + numFATs * secPerFAT
                ld      a, (SECTOR_BUF + BPB_NUMFATS)
                ld      b, a
                ld      de, (SECTOR_BUF + BPB_FATSZ16)
                ld      hl, 0
fm_fatacc:
                add     hl, de
                djnz    fm_fatacc           ; HL = numFATs * secPerFAT
                ld      de, (FAT_FATSTART)
                add     hl, de
                ld      (FAT_FIRSTROOT), hl
                ; root sectors = (rootEnts*32 + 511) / 512  (512 B per sector)
                ld      hl, (SECTOR_BUF + BPB_ROOTENTCNT)
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl              ; HL = rootEnts * 32
                ld      de, 511
                add     hl, de
                ld      a, h
                srl     a                   ; HL >> 9  (== H >> 1, result < 256)
                ld      l, a
                ld      h, 0
                ld      (FAT_ROOTSECS), hl
                ; first data sector = firstRoot + rootSecs
                ld      de, (FAT_FIRSTROOT)
                add     hl, de
                ld      (FAT_FIRSTDATA), hl
                or      a                   ; Cy = 0 success
                ret
fat_mount_bad:
                scf
                ret

; fat_find — search the root directory for an 8.3 file name.
;   in:  HL = pointer to an 11-byte name field (8 name + 3 ext, space-padded)
;   out: Cy = 0 found  -> FAT_FIRSTCLUS, FAT_FILESIZE set; Cy = 1 not found / error
; Compare is case-insensitive; FAT directories store upper-case 8.3 names.
fat_find:
                ld      (FAT_NAMEPTR), hl
                ld      hl, (FAT_FIRSTROOT)
                ld      (FAT_DIRSEC), hl
                ld      hl, (FAT_ROOTSECS)
                ld      (FAT_DIRREM), hl
ff_secloop:
                ld      hl, (FAT_DIRREM)
                ld      a, h
                or      l
                jr      z, ff_notfound      ; scanned every root sector
                ld      de, (FAT_DIRSEC)
                ld      hl, SECTOR_BUF
                call    read_sector
                ret     c                   ; propagate FDC error
                ld      hl, SECTOR_BUF
                ld      b, 16               ; 512 / 32 entries per sector
ff_entloop:
                push    bc
                push    hl
                ld      a, (hl)
                or      a
                jr      z, ff_endmark       ; $00 = end of directory
                cp      $E5
                jr      z, ff_skip          ; deleted entry
                push    hl
                ld      de, 11
                add     hl, de
                ld      a, (hl)             ; attribute byte (+11)
                pop     hl
                and     $18                 ; volume-label | directory -> skip
                jr      nz, ff_skip
                ld      de, (FAT_NAMEPTR)
                call    name_cmp
                jr      z, ff_found
ff_skip:
                pop     hl
                ld      de, 32
                add     hl, de              ; next 32-byte directory entry
                pop     bc
                djnz    ff_entloop
                ld      hl, (FAT_DIRSEC)
                inc     hl
                ld      (FAT_DIRSEC), hl
                ld      hl, (FAT_DIRREM)
                dec     hl
                ld      (FAT_DIRREM), hl
                jr      ff_secloop
ff_endmark:
                pop     hl
                pop     bc
ff_notfound:
                scf
                ret
ff_found:
                pop     hl                  ; HL = directory entry
                pop     bc
                push    hl
                ld      de, 26
                add     hl, de
                ld      a, (hl)             ; first cluster low (+26)
                inc     hl
                ld      h, (hl)             ; first cluster high (+27)
                ld      l, a
                ld      (FAT_FIRSTCLUS), hl
                pop     hl
                push    hl
                ld      de, 28
                add     hl, de
                ld      de, FAT_FILESIZE
                ld      bc, 4
                ldir                        ; file size (+28..31, LE)
                pop     hl
                or      a                   ; Cy = 0 found
                ret

; name_cmp — compare two 11-byte 8.3 name fields, case-insensitive.
;   in:  HL = directory entry name, DE = search name
;   out: Z set if equal; trashes A, BC, DE, HL
name_cmp:
                ld      b, 11
nc_loop:
                ld      a, (de)
                call    toupper
                ld      c, a
                ld      a, (hl)
                call    toupper
                cp      c
                ret     nz
                inc     hl                  ; 16-bit inc: leaves flags intact
                inc     de
                djnz    nc_loop             ; djnz leaves flags intact
                ret                         ; Z set from the final cp

; toupper — fold a..z to A..Z; all other bytes unchanged.
;   in: A, out: A
toupper:
                cp      $61                 ; 'a'
                ret     c
                cp      $7B                 ; 'z' + 1
                ret     nc
                sub     $20
                ret

; fat_open — start sequential reading of the file found by fat_find.
fat_open:
                ld      hl, (FAT_FIRSTCLUS)
                ld      (FAT_CURCLUS), hl
                xor     a
                ld      (FAT_CLUSSEC), a
                ret

; fat_advance — step the iterator to the next cluster in the chain.
fat_advance:
                ld      hl, (FAT_CURCLUS)
                call    fat_next_cluster
                ld      (FAT_CURCLUS), hl
                xor     a
                ld      (FAT_CLUSSEC), a
                ret

; fat_next_cluster — follow the FAT12 chain one link.
;   in:  HL = current cluster
;   out: HL = next cluster (12-bit; >= $0FF8 means end-of-chain)
; FAT12 packs 1.5 bytes per entry, so an entry can straddle a 512-byte sector
; boundary (e.g. cluster 682 on a full 720 KB image); the high byte is then read
; from the following FAT sector. A read error here is not separately reported —
; it yields a bogus link that the caller's end-of-chain test treats as EOF.
fat_next_cluster:
                ld      a, l
                and     1
                ld      (FAT_PARITY), a     ; cluster parity selects the nibbles
                ; fatofs = cluster + cluster/2  (= cluster * 3/2)
                ld      e, l
                ld      d, h
                srl     d
                rr      e                   ; DE = cluster >> 1
                add     hl, de              ; HL = fatofs
                ld      a, l
                ld      (FAT_BYTEIDX), a
                ld      a, h
                and     1
                ld      (FAT_BYTEIDX + 1), a    ; byteidx = fatofs & $1FF
                ld      a, h
                srl     a                   ; fatofs >> 9 = FAT sector offset
                ld      e, a
                ld      d, 0
                ld      hl, (FAT_FATSTART)
                add     hl, de
                ld      (FAT_FATSEC), hl
                ex      de, hl
                ld      hl, SECTOR_BUF
                call    read_sector
                ; byte0 = buf[byteidx]
                ld      hl, (FAT_BYTEIDX)
                ld      de, SECTOR_BUF
                add     hl, de
                ld      a, (hl)
                ld      (FAT_B0), a
                ; byte1 = buf[byteidx+1], possibly in the next FAT sector
                ld      hl, (FAT_BYTEIDX)
                ld      de, 511
                or      a
                sbc     hl, de
                jr      z, fnc_straddle
                ld      hl, (FAT_BYTEIDX)
                ld      de, SECTOR_BUF + 1
                add     hl, de
                ld      a, (hl)
                jr      fnc_combine
fnc_straddle:
                ld      hl, (FAT_FATSEC)
                inc     hl
                ex      de, hl
                ld      hl, SECTOR_BUF
                call    read_sector
                ld      a, (SECTOR_BUF)
fnc_combine:
                ld      (FAT_B1), a
                ld      a, (FAT_PARITY)
                or      a
                jr      nz, fnc_odd
                ; even cluster: next = B0 | ((B1 & $0F) << 8)
                ld      a, (FAT_B1)
                and     $0F
                ld      h, a
                ld      a, (FAT_B0)
                ld      l, a
                ret
fnc_odd:
                ; odd cluster: next = (B1 << 4) | (B0 >> 4)
                ld      a, (FAT_B1)
                ld      l, a
                ld      h, 0
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl              ; HL = B1 << 4
                ld      a, (FAT_B0)
                rrca
                rrca
                rrca
                rrca
                and     $0F                 ; A = B0 >> 4
                ld      e, a
                ld      d, 0
                add     hl, de
                ret

; fat_read_file_sector — read the open file's next data sector into SECTOR_BUF.
;   out: Cy = 0 ok (SECTOR_BUF holds 512 bytes), Cy = 1 end-of-file / error
; The caller bounds the true end of file with FAT_FILESIZE; this returns Cy = 1
; once the cluster chain reaches an end-of-chain marker.
fat_read_file_sector:
                ld      a, (FAT_CLUSSEC)
                ld      hl, FAT_SECPERCLUS
                cp      (hl)
                jr      c, frs_incluster
                call    fat_advance         ; current cluster exhausted -> next
frs_incluster:
                ld      hl, (FAT_CURCLUS)
                ld      de, 2
                or      a
                sbc     hl, de
                jr      c, frs_eof          ; cluster < 2 (free / empty file)
                ld      hl, (FAT_CURCLUS)
                ld      de, $0FF8
                or      a
                sbc     hl, de
                jr      nc, frs_eof         ; cluster >= $0FF8 = end-of-chain
                ; sector = firstData + (cluster-2)*secPerClus + clussec
                ld      hl, (FAT_CURCLUS)
                ld      de, 2
                or      a
                sbc     hl, de
                ex      de, hl              ; DE = cluster - 2
                ld      hl, 0
                ld      a, (FAT_SECPERCLUS)
                ld      b, a
frs_mul:
                add     hl, de
                djnz    frs_mul             ; HL = (cluster-2) * secPerClus
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
frs_eof:
                scf
                ret

; --- pad to a full 16 KB page ($4000-$7FFF) --------------------------------
                ds      $8000 - $, $00
