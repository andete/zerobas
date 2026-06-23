; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-disk — disk.asm
; ===========================================================================
; A clean-room MSX1 disk-interface ROM. Standalone 16 KB ROM that lives in an
; internal expansion slot (slot 3-1, page 1, $4000-$7FFF) on a built-in-disk
; MSX1. See README.md and disk/PROVENANCE.md.
;
; CLEAN-ROOM DISCIPLINE: every constant, address, and algorithm here traces to
; an allowed source (MSX2 Technical Handbook, the FDC datasheet, Microsoft FAT
; spec, ECMA-107, openMSX/C-BIOS sources, or this project's own black-box
; oracle observations). Nothing is derived from any disk-ROM or MSX-BASIC
; disassembly. See disk/PROVENANCE.md.
;
; FDC NOTE: the CF-3300's actual FDC is the Fujitsu MB8877A; it is WD179x-family
; compatible, so the WD2793 datasheet is a faithful compatible-family reference
; for the identical command/status register interface (oracle-validated
; byte-identical to the real CF-3300). openMSX models this FDC as a WD2793.
; "WD2793" below refers to that compatible interface, not a different chip.
;
; Runtime model: this is an "AB" disk-interface ROM. At boot the BIOS finds the
; header at $4000 and calls INIT, which (1) installs the standard HPHYD ($FFA7)
; -> DSKIO ($4010) inter-slot hook so a real MSX-BASIC / MSX-DOS host can drive
; us via PHYDIO (the Phase-1.5 PROVIDER surface), and (2) publishes the BDOS
; entry point via the SYSTEM ($F37D) sysvar (and seeds the default DTA), then
; returns to the BIOS boot scan. zerobas-BASIC itself reaches the file layer
; through that SYSTEM-vector BDOS entry across slots with CALSLT (the internal
; path) — NOT through the H.* / HPHYD chain; HPHYD exists for FOREIGN hosts. The
; disk subsystem reaches the physical driver through the six fixed-offset entry
; points at $4010..$401F.
;
; STATUS: INIT installs the HPHYD->DSKIO hook (provider direction) and publishes
; the BDOS entry + DTA default (internal direction). The FDC driver is
; implemented (WD2793, National memory-mapped register map, polled sector read
; AND polled sector write — physical write primitive). The FAT12 read layer is
; implemented (BPB parse, cluster-
; chain walk, root-directory 8.3 search, sequential file-sector read) as
; internal helpers. The BDOS/FCB layer is implemented (bdos_entry dispatches
; Open $0F / Sequential Read $14 / Close $10 on top of the FAT12 helpers); it is
; reached through the SYSTEM vector and is the bridge zerobas's BLOAD path
; calls. GETDPB ($4016) is REAL: it builds a Drive Parameter Block from the
; on-disk BPB for a foreign host (provider direction), field-for-field confirmed
; against a black-box CF-3300 GETDPB trace (see getdpb / disk/PROVENANCE.md §DPB).
; End-to-end disk I/O is implemented and the read + BDOS paths are differentially
; oracle-confirmed (disk_probe_dskio / disk_probe_bdos in msx-preservation).
; ===========================================================================

; --- System addresses (disk/PROVENANCE.md §INIT / §BDOS) -------------------
; Sources: MSX2 Technical Handbook, work area.
SYSTEM          equ     $F37D   ; SYSTEM sysvar: BDOS entry-point word
; RAMAD0-3: the RAM slot address for each of the four pages (the standard MSX
; work-area cells the disk ROM's INIT populates so MSX-DOS can re-page RAM into
; page 0). MSX2 TH work area; the disk-ROM-INIT responsibility is confirmed by a
; black-box differential (provider-oracle-scope.md §8.8/§8.16). EXPTBL flags which
; primary slots are expanded. (EXPTBL also in basic/sysvars.inc — same address.)
RAMAD0          equ     $F341   ; RAM-slot id per page ($F341-$F344), MSX2 TH work area
EXPTBL          equ     $FCC1   ; expanded-slot flags, 1 byte/primary, bit 7 = expanded

; --- Standard hook + entry addresses (disk/PROVENANCE.md §INIT) -------------
; HPHYD is the standard PHYDIO hook a disk ROM installs so a host's physical disk
; I/O reaches the in-slot DSKIO. Source: public MSX hook table
; (fms.komkon.org/MSX/Docs/Hooks.txt) + disk/docs/expansion-protocol.md §2
; (CF-3300 black-box trace: after boot $FFA7 held an RST 30h / slot $87 / RET).
HPHYD           equ     $FFA7   ; PHYDIO hook (5 RAM bytes, default C9)
; DSKIO entry: this ROM base ($4000) + standard disk-ROM offset +$10 (MSX2 TH,
; disk ROM interface). The HPHYD CALLF targets it cross-slot.
DSKIO_ENTRY     equ     $4010   ; our DSKIO ($4000 + $10)

; --- Disk scratch RAM (disk/PROVENANCE.md §Scratch RAM) --------------------
; (GETDPB writes the 18-byte DPB into the CALLER's buffer per MSX2 TH, so the disk
; ROM reserves no local DPB area.)
;
; FDC driver state (6 bytes below the sector buffer)
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
; numFATs / secPerFAT cached at mount so the write path can sync every FAT copy
; without re-reading the boot sector (which would clobber SECTOR_BUF mid-flush).
FAT_NUMFATS     equ     $E55A   ; number of FAT copies (byte; from BPB +16)
FAT_SECPERFAT   equ     $E55B   ; sectors per FAT copy (word; from BPB +22)
; This ROM's own slot byte, captured from A at INIT entry (disk/PROVENANCE.md
; §INIT) and used to build the HPHYD CALLF operand. Own-choice free page-3 RAM
; in the $E55D gap (after FAT_SECPERFAT's word $E55B-$E55C, before WBUF $E560).
HOOK_SLOT       equ     $E55D   ; our slot byte for the HPHYD inter-slot hook (1)
; FAT12 working scratch (transient within a single call)
FAT_PARITY      equ     $E4B2   ; 1 = odd cluster, 0 = even (FAT12 nibble pack)
FAT_BYTEIDX     equ     $E4B3   ; byte index within a FAT sector (word, 0..511)
FAT_FATSEC      equ     $E4B5   ; FAT sector currently read (word)
FAT_B0          equ     $E4B7   ; first FAT byte of a 12-bit entry
FAT_B1          equ     $E4B8   ; second FAT byte of a 12-bit entry
FAT_NAMEPTR     equ     $E4B9   ; -> 11-byte search name (word)
FAT_DIRSEC      equ     $E4BB   ; current root-dir sector being scanned (word)
FAT_DIRREM      equ     $E4BD   ; root-dir sectors remaining to scan (word)

; --- BDOS / FCB layer (disk/PROVENANCE.md §BDOS interface) ------------------
; CP/M-compatible FCB file access reached through the SYSTEM-sysvar vector
; INIT installed. Call number in C, FCB pointer in DE; result in A (MSX2 TH,
; MSX-DOS BDOS call conventions). Names in the FCB are an 11-byte 8.3 field at
; +1 (8 name + 3 ext, space-padded, upper-case) — exactly the layout fat_find
; consumes. The DTA defaults to $0080 (page 0) but is settable via BDOS $1A —
; BLOAD points it at a writable page-3 buffer (page 0 is BIOS ROM under Disk
; BASIC, so the $0080 default would silently fail there).
BDOS_F_OPEN     equ     $0F     ; FCB Open           (MSX2 TH, MSX-DOS BDOS table)
BDOS_F_CLOSE    equ     $10     ; FCB Close          (MSX2 TH, MSX-DOS BDOS table)
BDOS_F_SEQRD    equ     $14     ; FCB Sequential Read(MSX2 TH, MSX-DOS BDOS table)
BDOS_F_SEQWR    equ     $15     ; FCB Sequential Write (MSX2 TH, MSX-DOS BDOS table)
BDOS_F_CREATE   equ     $16     ; FCB Create file    (MSX2 TH, MSX-DOS BDOS table)
BDOS_F_SETDTA   equ     $1A     ; Set DTA Address (DE=new DTA) (MSX2 TH, MSX-DOS BDOS table)
BDOS_F_RDBLK    equ     $27     ; Random Block Read (RDBLK) (MSX-DOS BDOS table; the
                                ; MSX-DOS-1 boot loads MSXDOS.SYS through this — a3 §8.9)
DTA_DEFAULT     equ     $0080   ; default Disk Transfer Area (MSX2 TH, BDOS conv.)
RECSIZE         equ     128     ; sequential-read record size (MSX2 TH, FCB seq I/O)
RECPERSEC       equ     4       ; 512 / 128 = records per 512-byte sector (own deriv.)
; BDOS sequential-read position (own choice; free page-3 RAM after FAT scratch).
; Records consumed from SECTOR_BUF so far; RECPERSEC means "buffer exhausted,
; refill on next read". File position otherwise lives in the FAT iterator.
BDOS_RECIDX     equ     $E4BF   ; next 128-byte record within SECTOR_BUF (0..4)
; Settable DTA pointer (BDOS call $1A). Under MSX-DOS the default DTA is page-0
; RAM at $0080; under the combined Disk-BASIC machine page 0 is BIOS ROM, so a
; SeqRead to $0080 silently fails. BDOS $1A lets the caller (BLOAD) point the
; record transfer at a writable buffer it controls. Default preserves MSX-DOS
; compatibility. Own choice for the variable location: free page-3 RAM after the
; BDOS record index. See disk/PROVENANCE.md §BDOS interface.
BDOS_DTA        equ     $E4C0   ; current DTA pointer (word; default DTA_DEFAULT)
; Bytes of the open file still undelivered, seeded from FAT_FILESIZE by Open and
; decremented one record (up to RECSIZE) per Sequential Read. Bounds the partial
; final record and the EOF point by the true file size (own choice for the
; variable location: free page-3 RAM past basic-core's DISK_DTA buffer
; $E4C2..$E541, clear of every other disk and basic region). 4-byte LE.
; See disk/PROVENANCE.md §BDOS interface + §Scratch RAM.
BDOS_BYTESLEFT  equ     $E542   ; bytes of the open file not yet delivered (4-byte LE)

; --- BDOS / FAT12 WRITE-back scratch (disk/PROVENANCE.md §Scratch RAM) -------
; The write side mirrors the read side's "single open file" model: at most one
; file is open for write at a time, and its position lives in these vars (the
; FCB bookkeeping fields are left untouched, as on the read side). All own-choice
; free page-3 RAM after BDOS_BYTESLEFT ($E542..$E545), clear of SECTOR_BUF /
; FAT_* / every basic-core region. See disk/PROVENANCE.md §Scratch RAM.
BDOS_WRMODE     equ     $E546   ; 1 = a file is open for sequential write (byte)
BDOS_WRCLUS     equ     $E547   ; chain-tail cluster currently being filled (word)
BDOS_WRFIRST    equ     $E549   ; file's first cluster, 0 until first allocated (word)
BDOS_WRSECIDX   equ     $E54B   ; sector index within the current cluster (byte)
BDOS_WRBUFLEN   equ     $E54C   ; bytes currently buffered in SECTOR_BUF (word, 0..512)
BDOS_WRBYTES    equ     $E54E   ; total bytes written so far = final file size (4-byte LE)
BDOS_DIRSEC     equ     $E552   ; logical sector holding the open file's dir entry (word)
BDOS_DIROFF     equ     $E554   ; byte offset of that dir entry within its sector (word)
FAT_WRTMP       equ     $E556   ; transient scratch for the FAT12 write helpers (word)
FAT_WRTMP2      equ     $E558   ; second transient (free-cluster scan cached sector)
; A SECOND 512-byte sector buffer used by the WRITE-BACK FAT/dir helpers. The
; data being accumulated for a Sequential Write lives in SECTOR_BUF; allocating a
; cluster (FAT scan) or stamping the directory entry must read/write OTHER sectors
; without disturbing that in-flight data, so the write-back metadata path uses
; this independent buffer. Own-choice free page-3 RAM after the write scratch.
WBUF            equ     $E560   ; write-back FAT/dir sector buffer ($E560..$E75F)

; FCB / directory-entry field offsets (Microsoft FAT spec §3.4; MSX2 TH FCB).
DIRENT_FIRSTCLUS equ    26      ; first-cluster word (LE) within a dir entry
DIRENT_FILESIZE equ     28      ; file-size dword (LE) within a dir entry
EOC             equ     $0FFF   ; end-of-chain marker we write (Microsoft FAT spec §3.2)

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
; ($7FB9 = track register — unused: seeks target the track via the Data register.)
FDC_SECTOR      equ     $7FBA   ; sector register
FDC_DATA        equ     $7FBB   ; data register
FDC_CTRL        equ     $7FBC   ; write = drive/side/motor latch; read = IRQ/!DRQ

; Control-latch write bits (NationalFDC.cc writeMem). Single-drive machine: only
; drive A is selected (drive B would be $02 — never used).
CTRL_DRIVE_A    equ     $01     ; select drive 0 (A)
CTRL_SIDE       equ     $04     ; side select (0 = side 0, 1 = side 1)
CTRL_MOTOR      equ     $08     ; motor on

; WD2793 status-register bits (WD2793 datasheet). BUSY (bit 0) and DRQ (bit 1)
; are polled with literal `bit 0,a` / `bit 1,a` in the transfer loops (a `bit`
; index cannot take a mask), so only the error-mask bits below need symbols.
ST_LOST         equ     $04     ; lost data (Type II)
ST_CRC          equ     $08     ; CRC error
ST_RNF          equ     $10     ; record not found (Type II)
ST_WP           equ     $40     ; write protect / write fault
ST_NOTRDY       equ     $80     ; drive not ready

; WD2793 commands. Type I flags: head-load $08 + verify $04, step-rate 0 = 6 ms.
CMD_RESTORE     equ     $0C     ; restore to track 0  ($00 + headload + verify)
CMD_SEEK        equ     $1C     ; seek to (Data reg)  ($10 + headload + verify)
CMD_READ        equ     $80     ; read sector, single record
CMD_WRITE       equ     $A0     ; write sector, single record (Type II, $A0 base)
; ($D0 = force interrupt / abort — unused: no command is ever aborted mid-flight.)

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

; --- extended disk-ROM kernel entry: $4030 ($4000 + $30) -------------------
; MSXDOS.SYS's resident init CALLs $4030 expecting the disk ROM's "get work area"
; routine. The six standard entries above end at $401F; the $4022-$402F slots are
; further disk-ROM/DOS-kernel entries the MSX-DOS-1 boot does NOT call (a3 §8.11),
; so they are left as $00 fill. $4030 IGNORES its inputs and returns a fixed
; work-area pointer in HL, preserving every other register (black-box oracle, a3
; §8.13: disk_probe_dosboot_4030.py --sweep). Inlined at exactly $4030 (not a JP)
; so it lands on the address the boot CALLs; `ld hl,nn`+`ret` preserves AF too.
                ds      $4030 - $, $00  ; pad the unused $4022-$402F kernel-entry slots
                ld      hl, GETWRK_AREA ; $4030: return our work-area base
                ret                     ; ($4033) HL = work area, all else preserved

; --- INIT -------------------------------------------------------------------
; Called by the BIOS boot scan (or by zerobas-BASIC's slot scan, which finishes
; the scan C-BIOS skips — see basic/initext.asm). INIT does two things:
;
;   1. installs the standard HPHYD ($FFA7) -> DSKIO ($4010) inter-slot hook, so a
;      real MSX-BASIC / MSX-DOS host that issues PHYDIO reaches our sector engine.
;      This is the PROVIDER-direction surface (disk/docs/expansion-protocol.md
;      §4a/§5): the loader path on a standard machine is HPHYD -> DSKIO, and a
;      foreign host drives us through it. The host direction (zerobas-BASIC) does
;      NOT use this hook — it reaches the file layer through the SYSTEM vector
;      below — but installing HPHYD makes zerobas-disk a standard provider.
;
;   2. publishes the BDOS entry-point address into the SYSTEM sysvar ($F37D) and
;      seeds the default DTA (the INTERNAL path: zerobas-BASIC reaches the file
;      layer through this SYSTEM-vector BDOS entry, called across slots with
;      CALSLT — the entry *address* read back from $F37D, the slot from the INIT
;      scan's DISKSLOT capture). This is differentially oracle-confirmed
;      (disk_probe_bdos.py vs real MSX-DOS 1) and is kept alongside the new hook.
;
; HPHYD hook idiom (observed on the National CF-3300, disk/PROVENANCE.md §INIT;
; MSX2 TH §2 inter-slot calls): the 5 hook bytes are an inter-slot CALLF —
;   F7 <slot> <lo> <hi> C9  =  RST 30h ; slot id ; target addr ; RET
; F7 = RST 30h = CALLF, the BIOS inter-slot-call restart (a plain JP cannot cross
; slots). We point it at our own DSKIO entry ($4010) with this ROM's slot byte.
;
; OWN SLOT BYTE (the hard sub-problem). The MSX cartridge/disk INIT convention
; passes the ROM's slot id to INIT in a register (MSX2 TH cartridge-ROM INIT
; convention); established here by black-box oracle — a trace of the CF-3300 BIOS
; calling its disk INIT observed A = C = $87 = slot 3-1. zerobas-BASIC's own slot scan
; (basic/initext.asm) likewise leaves the slot byte in A at the CALSLT to this
; INIT: it does `ld a,(SCAN_SLOT)` immediately before loading IY/IX and calling
; CALSLT, and CALSLT passes AF through to the target — black-box confirmed: at
; our INIT entry A = $87 (slot 3-1) on every C-BIOS_MSX1_*_BASIC_DISK machine.
; So we read the slot byte from A as the FIRST thing INIT does, before anything
; clobbers it. COUPLING: this depends on the caller delivering the slot in A,
; which both the standard BIOS scan and basic/initext.asm do (the latter is our
; own code; the dependence is documented here and in disk/PROVENANCE.md §INIT).
;
; Sources: SYSTEM $F37D — MSX2 TH, work area; C-BIOS systemvars.asm. HPHYD $FFA7,
; CALLF/RST 30h idiom — disk/docs/expansion-protocol.md (CF-3300 black-box trace)
; + MSX2 TH §2. Slot-in-A INIT convention — MSX2 TH + CF-3300/own-scan oracle.
init:
                ; --- capture this ROM's slot byte (A on INIT entry; see header) ---
                ; Do this FIRST, before anything clobbers A.
                ld      (HOOK_SLOT), a      ; HOOK_SLOT = our slot byte (e.g. $87 = 3-1)

                ; --- install HPHYD ($FFA7) -> DSKIO ($4010) inter-slot CALLF ----
                ; Write the 5 hook bytes: F7 <slot> 10 40 C9
                ;   = RST 30h ; slot ; addr-lo ; addr-hi ; RET   (CALLF, MSX2 TH §2)
                ld      a, $F7              ; +0: RST 30h opcode (CALLF)
                ld      (HPHYD + 0), a
                ld      a, (HOOK_SLOT)      ; +1: this ROM's slot byte
                ld      (HPHYD + 1), a
                ld      a, low DSKIO_ENTRY  ; +2: target addr low  ($10)
                ld      (HPHYD + 2), a
                ld      a, high DSKIO_ENTRY ; +3: target addr high ($40)
                ld      (HPHYD + 3), a
                ld      a, $C9              ; +4: RET
                ld      (HPHYD + 4), a

                ; --- publish the BDOS entry as an executable JP vector ---------
                ; $F37D (SYSTEM) is the disk system's BDOS-call jump vector. The
                ; MSX-DOS boot CALLs it to Open/Read MSXDOS.SYS — black-box (a3
                ; §8.9): at step 7 the boot-sector code does `CALL $F37D` with
                ; C=$0F (BDOS Open File) and DE = an FCB in the boot sector. So
                ; $F37D must hold `JP <bdos dispatcher>`, NOT a bare address word:
                ; the boot EXECUTES these bytes (our old raw word `9F 43` ran as
                ; `SBC A,A / LD B,E / RST 38h` -> the $0038 wedge). Our bdos_entry
                ; is an oracle-validated FCB BDOS (Open $0F / SeqRead $14 / Close
                ; $10 / SetDTA $1A), and it is reachable from here even with RAM in
                ; page 0: our ROM stays in page 1 and bdos_entry's scratch is all
                ; page-3 RAM, both mapped throughout boot. zerobas-BASIC's own
                ; loader no longer reads $F37D (Phase 1.5 moved it to DSKIO + own
                ; FAT; see basic/sysvars.inc), so the JP form is free to install.
                ld      a, $C3              ; JP opcode
                ld      (SYSTEM), a
                ld      hl, bdos_entry
                ld      (SYSTEM + 1), hl    ; $F37D = C3 <bdos_entry lo> <hi>
                ; default the settable DTA to the MSX-DOS default ($0080) so a
                ; SeqRead before any $1A behaves as MSX-DOS does.
                ld      hl, DTA_DEFAULT
                ld      (BDOS_DTA), hl
                ; --- populate RAMAD0-3 so MSX-DOS can re-page RAM into page 0 ---
                ; The disk ROM's INIT owns the per-page RAM-slot table (§8.8/§8.16):
                ; MSXDOS.SYS's resident init reads RAMAD0-3 ($F341-4) to map RAM into
                ; page 0 (where the BIOS ROM was), and without it pages an empty slot
                ; ($FF) and wedges at $0038. set_ramad fills RAMAD only when the host
                ; left it uninitialised ($FF), so the C-BIOS hosts (which set their own
                ; RAMAD) are untouched. (provider-oracle-scope.md §8.16)
                call    set_ramad
                ; fall into the DOS-boot bridge (TH ch.3); it returns to the BIOS
                ; boot scan, falling through to BASIC for a non-system disk.
                ; --- intentional fall-through to boot_disk -------------------

; --- DOS-boot bridge (slice 2-Tier2-a1; MSX2 TH ch.3 steps 4-5) ------------
; Read logical sector 0 into the standard boot load address $C000; if it carries
; a boot signature ($EB/$E9 at byte 0) run the "custom boot program" at $C01E
; with CY reset (step 5). A data disk's byte $1E is the documented RET NC stub,
; so this returns and INIT falls through to BASIC unchanged — the regression-safe
; property (the bridge runs in every host's INIT). Steps 6-7 (the page-0 MSX-DOS
; environment + the CY-set $C01E) are slice a2; see provider-oracle-scope.md §8.
; No disk / read error / no signature all return cleanly to BASIC.
BOOT_LOAD       equ     $C000   ; standard boot-sector load address (MSX2 TH ch.3)
BOOT_ENTRY      equ     $C01E   ; custom-boot-program entry (BOOT_LOAD + $1E)
; page-0 RAM-swap scratch (transient, used only during INIT's boot bridge).
BOOT_SV_A8      equ     $E760   ; saved $A8 primary-slot config
BOOT_SV_SEC     equ     $E761   ; saved slot secondary ($FFFF) live value
; step-6 page-0 environment scratch (transient; used only by the $0030 CALLF
; handler and the CALSLT handler during the boot bridge). The $0030 handler must
; deliver A,B,C,DE,HL UNTOUCHED to the DSKIO callee, so it saves them here while
; it reads the inline CALLF operand off the stack. Own-choice free page-3 RAM
; after BOOT_SV_SEC. (provider-oracle-scope.md §8.4)
R30_HL          equ     $E762   ; $0030 handler: saved caller HL (word)
R30_BC          equ     $E764   ; $0030 handler: saved caller BC (word)
R30_DE          equ     $E766   ; $0030 handler: saved caller DE (word)
R30_AF          equ     $E768   ; $0030 handler: saved caller AF incl. carry (word)
CALSLT_HL       equ     $E76A   ; CALSLT handler: HL stash across the call setup (word)
; BDOS $27 (Random Block Read) scratch — transient within one RDBLK call. Own-choice
; free page-3 RAM after the step-6 block. Only the DOS-boot path (on a real-BIOS host)
; calls $27, so this never collides with the zerobas-BASIC host buffers (which use
; the standard DSKIO path, not bdos_entry). (disk/PROVENANCE.md §BDOS interface)
RDBLK_REQ       equ     $E76C   ; records requested (HL on entry) (word)
RDBLK_RECSIZE   equ     $E76E   ; record size from FCB+14 (word)
RDBLK_DONE      equ     $E770   ; records delivered so far (word; = HL on return)
RDBLK_CNT       equ     $E772   ; bytes left in the current record (word)
RDBLK_BUFPOS    equ     $E774   ; byte offset into SECTOR_BUF (word, 0..512)
RDBLK_DST       equ     $E776   ; current DTA write pointer (word; from BDOS_DTA)

; --- MSX-DOS-1 "get work area" return ($4030; a3 §8.13) ---------------------
; MSXDOS.SYS's resident init CALLs disk-ROM entry $4030 and uses the returned HL
; as a work-area base pointer. Black-box oracle (disk_probe_dosboot_4030.py
; --sweep on the genuine CF-3300): $4030 IGNORES its inputs and returns a FIXED
; pointer, preserving AF/BC/DE/IX/IY. We return a pointer to our own reserved
; page-3 RAM; the size + layout MSXDOS.SYS then expects at that pointer is the next
; oracle target.
;
; KERNEL-PLACEMENT LEVER (a3 §8.24). Black-box differential of the BDOS-vector write
; (disk_probe_dosboot_ramtop.py): MSXDOS.SYS places its resident kernel so its TOP
; sits at THIS work-area pointer and its base $067A (the kernel size) below it
; -- stock work area $DD0E -> kernel $D606; our old $E780 -> kernel $E106, straight
; onto our $E29A+ scratch (the §8.19 collision). NOT DRVTBL+1/HIMEM (§8.20/§8.23).
; So we return the STOCK's $DD0E: the kernel lands at $D6xx, below our scratch, and
; the 128-byte work area DOS fills ($DD0E-$DD8E) is clear of both kernel and scratch.
GETWRK_AREA     equ     $DD0E   ; MSX-DOS work-area base returned by $4030 (128 B reserved);
                                ; = the stock value so MSXDOS's kernel lands below our scratch
; --- MSX-DOS-1 kernel continuation entry $50A9 (a3 §8.26/§8.27) -------------
; After publishing its BDOS vector the relocated kernel does `CALL $50A9` (page 1 =
; our disk ROM, so it lands here). Black-box oracle (disk_probe_dosboot_50a9.py
; --stock): the routine IGNORES its register inputs, makes exactly ONE persistent
; memory write ($50A9_WRKB := $00, via its internal CALL $472D), and returns a fixed
; register contract -- A=0 / Z+N (AF=$0042), DE=IX=$F1AA, HL=$F359, BC + IY preserved.
; The returned HL/DE/IX point into the disk work area the kernel/disk-ROM already
; built; this entry only hands them back (it does not populate them). We reproduce the
; observed contract with our own code; the stock's $472D body is never disassembled.
W50A9_WRKB      equ     $F242   ; the one work-area cell $50A9 clears (semantic: black-box)
W50A9_RET_DE    equ     $F1AA   ; DE (= IX) on return: disk work-area pointer
W50A9_RET_HL    equ     $F359   ; HL on return: disk work-area pointer (DRVTBL+$11 region)
; --- $F348 DRVTBL: the disk-driver table MSXDOS.SYS dispatches through (§8.22) ---
; The disk ROM (not MSXDOS) builds this table; MSXDOS reads it to find the disk
; interface's slot, its reserved top-of-RAM, and the driver-routine pointers. The
; four driver pointers are always-mapped page-3 trampolines (the boot/DOS calls them
; while the disk ROM is NOT in any page, so a direct $40xx call won't reach it). We
; synthesise each as the proven H.PHYD form -- a self-contained CALLF stub
; `F7 <slot> <lo> <hi> C9` (RST 30h inter-slot call; MSX2 TH §2) -- into our own
; $4010-region BIOS entries, never the stock's $EF95 kernel bytes. DRV_TRAMP holds
; them in reserved page-3 RAM past the $4030 work area (free, gated DOS path only).
DRV_TRAMP       equ     $E800   ; 4 CALLF trampolines, 5 bytes each ($E800-$E813)
; Reserved top-of-RAM advertised in DRVTBL+1 (the stock's HIMEM value). NOTE: this is
; NOT the kernel-placement lever -- §8.20 ruled out HIMEM, §8.23 ruled out DRVTBL+1,
; and §8.24 proved the lever is DRVTBL+3 (the $4030 work-area pointer, GETWRK_AREA
; above). We still advertise the stock $DF93 here for fidelity (MSXDOS reads it), but
; placement is governed by GETWRK_AREA, not this field.
DOS_RESV_TOP    equ     $DF93   ; top-of-reserved-RAM advertised in DRVTBL+1 (not the lever)
boot_disk:
                xor     a               ; drive A
                ld      b, 1            ; one sector
                ld      c, a            ; media byte (ignored, single-drive)
                ld      de, 0           ; logical sector 0 (the boot sector)
                ld      hl, BOOT_LOAD   ; -> $C000 (page-3 RAM)
                or      a               ; Cy = 0 -> read
                call    dskio
                ret     c               ; no disk / read error -> BASIC
                ld      a, (BOOT_LOAD)  ; first byte = boot signature?
                cp      $EB
                jr      z, boot_sig_ok
                cp      $E9
                ret     nz              ; not a boot disk -> BASIC
boot_sig_ok:
                or      a               ; Cy = 0 -> step-5 "custom boot" call
                call    BOOT_ENTRY      ; step 5 (data-disk default RET NC returns here)
                ; --- step 6: stand up the page-0 MSX-DOS environment ----------
                ; Switch RAM into page 0 (the page-0 BIOS ROM, incl. the inter-slot
                ; primitives, vanishes) and lay the JP-vector set the boot code +
                ; MSXDOS.SYS dereference there (RDSLT/CALSLT/ENASLT/CALLF + the int
                ; vector) as our OWN page-1 handlers. Interrupts stay OFF the whole
                ; time: while page 0 is RAM the $0038 cell is not yet the BIOS
                ; handler. (provider-oracle-scope.md §8.4/§8.6)
                di
                call    page0_ram_in    ; RAM into page 0 (host-adaptive, gap B)
                call    lay_page0_env   ; write the inter-slot vector set into page 0
                ; --- step 7: CY-set $C01E -- "load the system" -----------------
                ; A real DOS disk's boot code now loads MSXDOS.SYS at $0100 and JPs
                ; in (no return). A non-system / data disk's $1E stub (D0 C9) takes
                ; the C9 RET on CY set and returns here, so we MUST tear the env
                ; back down before BASIC: this runs in every host's INIT, incl. the
                ; C-BIOS_*_BASIC_DISK regression on test720.dsk (sig $EB, stub D0 C9).
                scf                     ; Cy = 1 -> "load the system" entry
                call    BOOT_ENTRY      ; DOS disk JPs into MSXDOS.SYS (no return)
                call    page0_ram_out   ; data disk returned: BIOS ROM back in page 0
                ei
                ret                     ; -> BIOS boot scan -> BASIC

; page0_ram_in — map page 3's slot/subslot (always RAM: the stack lives there)
; into page 0, so the boot code/MSXDOS see RAM where the BIOS ROM was. Derives
; the RAM slot from page 3 (gap B: host-adaptive, never hardcoded slot 3-0).
; Caller MUST DI (while page 0 is RAM the $0038 int vector is not the BIOS). Saves
; the originals for page0_ram_out. Clobbers A, C. (provider-oracle-scope.md §8.2)
page0_ram_in:
                in      a, ($A8)            ; primary slot config
                ld      (BOOT_SV_A8), a
                ld      a, ($FFFF)          ; slot secondary reg (reads inverted)
                cpl                         ; -> live value
                ld      (BOOT_SV_SEC), a
                ; page-0 primary := page-3 primary  ($A8 bits 7-6 -> bits 1-0)
                ld      a, (BOOT_SV_A8)
                and     %11000000
                rlca
                rlca
                ld      c, a
                ld      a, (BOOT_SV_A8)
                and     %11111100
                or      c
                out     ($A8), a
                ; page-0 subslot := page-3 subslot  ($FFFF bits 7-6 -> bits 1-0)
                ld      a, (BOOT_SV_SEC)
                and     %11000000
                rlca
                rlca
                ld      c, a
                ld      a, (BOOT_SV_SEC)
                and     %11111100
                or      c
                ld      ($FFFF), a
                ret

; page0_ram_out — restore the original page-0 mapping (BIOS ROM back in page 0).
page0_ram_out:
                ld      a, (BOOT_SV_SEC)
                ld      ($FFFF), a
                ld      a, (BOOT_SV_A8)
                out     ($A8), a
                ret

; set_ramad — populate RAMAD0-3 ($F341-4) with the host's RAM-slot id, so MSX-DOS
; can re-page RAM into page 0. The real CF-3300 main BIOS sets only EXPTBL and
; leaves RAMAD to the disk ROM (black-box differential, §8.8/§8.16); MSXDOS.SYS's
; resident init then reads RAMAD0-3 (84 reads observed on the stock, §8.16) to map
; RAM where the page-0 BIOS ROM was. Without it MSX-DOS pages an empty slot ($FF)
; and the CPU wedges at $0038 ($FF = RST 38h self-loop).
;
; HOST-ADAPTIVE + REGRESSION-SAFE. RAMAD is filled ONLY when the host left it
; uninitialised ($FF) -- the real-CF-3300 case where the disk-ROM job was skipped.
; The C-BIOS hosts set their own RAMAD (observed $C9..), so the $FF gate leaves them
; exactly as they were (and C-BIOS never boots DOS, so nothing reads RAMAD there).
;
; The value is the RAM slot id in standard F000SSPP form, derived from PAGE 3 (always
; RAM: the stack lives there) the same host-adaptive way page0_ram_in derives its
; swap slot -- primary from $A8 bits 15-14, and, if that primary is expanded (EXPTBL
; bit 7), the subslot from $FFFF. All four pages share this slot on the single-RAM-
; slot machines we target (CF-3300: slot 3-0 = $83, matching the stock's RAMAD0).
; Sources: MSX2 TH work area (RAMAD0-3, EXPTBL) + MSX2 TH ch.2 slot handling. No
; disk-ROM/MSX-DOS code is read; the disk-ROM-INIT responsibility + the read are
; black-box oracle observations (§8.8/§8.16).
set_ramad:
                ld      a, (RAMAD0)
                inc     a                   ; $FF -> $00 (Z): RAMAD uninitialised?
                ret     nz                  ; host already set RAMAD -> leave it alone
                ; --- derive the page-3 RAM slot id (F000SSPP) ---
                in      a, ($A8)
                rlca
                rlca
                and     3                   ; A = page-3 primary slot (PP)
                ld      c, a                ; C = PP
                ld      b, 0
                ld      hl, EXPTBL
                add     hl, bc              ; -> EXPTBL[PP]
                bit     7, (hl)             ; primary expanded?
                ld      a, c                ; not expanded: slot id = PP (flags preserved)
                jr      z, sr_store
                ld      a, ($FFFF)          ; expanded: fold in the page-3 subslot
                cpl                         ; $FFFF reads inverted -> live value
                rlca
                rlca
                and     3                   ; page-3 subslot (SS)
                rlca
                rlca                        ; SS << 2 (into bits 3-2)
                or      c                   ; | PP
                or      $80                 ; | expanded flag (bit 7)
sr_store:
                ld      (RAMAD0 + 0), a     ; page 0
                ld      (RAMAD0 + 1), a     ; page 1
                ld      (RAMAD0 + 2), a     ; page 2
                ld      (RAMAD0 + 3), a     ; page 3
                ; fall through to build the $F368 disk-work-area jump table -------
                ; (only reached under the same $FF gate -- the real-CF-3300 DOS host)

; build_wa_table — lay the disk system's resident jump table at $F368-$F37C.
; MSXDOS.SYS's resident init CALLs fixed work-area entries $F368/$F36B (the disk
; system's RAM-segment-switch hooks); on a 64K MSX with no memory mapper these are
; no-ops (one segment), confirmed black-box on the stock CF-3300: the calls are
; register/flag-transparent with NO memory, FDC, or I/O-port effects (§8.18,
; disk_probe_dosboot_f368.py). Absent the table our $F368 reads $FF and the CALL
; slides through $FF as RST 38h (the §8.17 derail). We point the seven slots
; $F368..$F37A at our own RET stub (wa_stub); $F37D (SYSTEM) is already our
; JP bdos_entry from INIT and is left intact (the loop stops at $F37C). The stub
; lives in our page-1 ROM, reachable exactly as int_h/$0038 already is (page 1 stays
; our disk ROM through boot). Clean-room: our own RET; the stock's $DFxx targets are
; never read. Source: MSX2 TH disk work area + MSX-DOS segment-switch hook model.
WA_JMPTAB       equ     $F368   ; disk-work-area resident jump table ($F368-$F37C, 7 slots)
build_wa_table:
                ld      hl, WA_JMPTAB
                ld      b, 7                ; 7 JP slots $F368..$F37A (3 bytes each)
bwt_loop:
                ld      (hl), $C3           ; JP opcode
                inc     hl
                ld      (hl), low wa_stub
                inc     hl
                ld      (hl), high wa_stub
                inc     hl
                djnz    bwt_loop
                ; fall through to build the $F348 DRVTBL (same $FF gate)
; build_drvtbl — synthesise the four CALLF trampolines in page-3 RAM, then lay the
; $F348 DRVTBL pointing at them + our slot + reserved-top + the $4030 work area.
; Mirrors the disk ROM's own build (§8.22 write-watch: stock builds it from page 1);
; clean-room — every pointer aims at our own code, the stock $EF95/$DFxx bytes are
; never read. Runs only under set_ramad's $FF gate (the real-CF-3300 DOS host).
build_drvtbl:
                ; --- four CALLF trampolines: F7 <slot> <target-lo> 40 C9 ---------
                ld      hl, drv_targets ; ROM: low byte of each $40xx driver entry
                ld      de, DRV_TRAMP   ; RAM: where the stubs are laid
                ld      b, DRV_NTRAMP
bdt_tramp:
                ld      a, $F7          ; RST 30h (CALLF) opcode
                ld      (de), a
                inc     de
                ld      a, (HOOK_SLOT)  ; this ROM's slot byte
                ld      (de), a
                inc     de
                ld      a, (hl)         ; target low byte (e.g. $10 = DSKIO)
                ld      (de), a
                inc     de
                ld      a, high DSKIO_ENTRY ; $40: all driver entries are in page 1
                ld      (de), a
                inc     de
                ld      a, $C9          ; RET
                ld      (de), a
                inc     de
                inc     hl
                djnz    bdt_tramp
                ; --- the DRVTBL itself at $F348 ---------------------------------
                ld      a, (HOOK_SLOT)
                ld      (DRVTBL + 0), a             ; +0  slot id
                ld      hl, DOS_RESV_TOP
                ld      (DRVTBL + 1), hl            ; +1  reserved top-of-RAM
                ld      hl, GETWRK_AREA
                ld      (DRVTBL + 3), hl            ; +3  $4030 work-area pointer
                ld      hl, DRV_TRAMP + 0
                ld      (DRVTBL + 5), hl            ; +5  DSKIO  trampoline
                ld      hl, DRV_TRAMP + 5
                ld      (DRVTBL + 7), hl            ; +7  DSKCHG trampoline
                ld      hl, DRV_TRAMP + 10
                ld      (DRVTBL + 9), hl            ; +9  GETDPB trampoline
                ld      hl, 0
                ld      (DRVTBL + 11), hl           ; +11 unused (stock = $0000)
                ld      hl, DRV_TRAMP + 15
                ld      (DRVTBL + 13), hl           ; +13 DSKFMT trampoline (NOTE: stock +13 =
                                                    ; $F195 = the drive-A DPB pointer, not a
                                                    ; trampoline — §8.22's "driver pointers"
                                                    ; reading of +5/+7/+9/+13 needs revisiting;
                                                    ; but +13 is NOT the IX source, §8.30)
                ld      a, $AA
                ld      (DRVTBL + 15), a            ; +15 sentinel (stock = $AA)
                ; fall through to install the resident work-area routines (§8.28)
; build_resident — install the disk system's resident RAM ROUTINES the kernel CALLs
; from fixed work-area addresses (a3 §8.28). After $50A9 the kernel CALLs $F1C9, a
; $-terminated STRING-PRINT helper the genuine disk ROM relocates into the work area
; (stock body: CALL $F36B / LD A,(DE) / CALL $F368 / INC DE / CP '$' / RET Z /
; CALL $53A8 output / loop). Absent it ($FF) the CALL slides through RST 38h. We
; install OUR OWN clean-room body (never the stock bytes) into page-3 RAM (always
; mapped, no slot juggling). FIRST CUT: consume the string to its '$' terminator and
; return -- the kernel's control flow continues; banner output is added by a later
; re-trap if the kernel proves to need it. Runs under the same $FF gate as set_ramad.
build_resident:
                ld      hl, res_print_tmpl
                ld      de, RES_PRINT
                ld      bc, res_print_end - res_print_tmpl
                ldir
                ; --- the $F24E-$F2FD no-op segment-hook stub table (§8.29) ----------
                ; The COMMAND.COM-load dispatch trace (disk_probe_dosboot_dispatch.py,
                ; stock) shows the kernel CALL ~18 fixed entries in $F252-$F2A3 between
                ; $50A9-return and the first real DSKIO. On a plain 64K machine that
                ; whole table is $C9 (RET): they are the disk system's RAM-segment bank
                ; in/out hooks (same no-op class as the $F368/$F36B hooks, §8.18) and do
                ; nothing without a memory mapper. Absent it ($FF) every CALL slides
                ; through RST 38h and the kernel derails (the §8.28a "Insert DOS disk").
                ; We fill it with RET so the no-op hooks return cleanly. Our own bytes
                ; (a constant), never the stock work-area code.
                ld      hl, RES_STUBS
                ld      (hl), $C9               ; RET
                ld      de, RES_STUBS + 1
                ld      bc, RES_STUBS_END - RES_STUBS - 1
                ldir
                ; --- drive-A DPB at $F195 (§8.30) -----------------------------------
                ; The kernel expects a valid drive-A DPB at $F195: $4030's input is
                ; IX=$F195 and the $50A9 contract hands IX back pointing into the work
                ; area; MSXDOS.SYS dereferences that DPB to read the directory +
                ; COMMAND.COM. The disk ROM builds it at boot ($F195 = drive-A id, then
                ; the 18-byte DPB our GETDPB produces byte-identical to the CF-3300,
                ; §8.13). Ours was $FF -> the kernel reads garbage geometry and warm-
                ; boots (§8.29). Lay the drive-A id ($00) at $F195+0 and CALL our own
                ; GETDPB (HL=base; it fills base+1=media onward) to build the DPB from
                ; the inserted disk's BPB -- the same disk boot_disk reads next, and
                ; DSKIO is already callable here. On a boot-sector read error GETDPB
                ; returns Cy=1 having written nothing past the id, so a not-ready disk
                ; cannot leave garbage. Our own code/data; never the stock $F1xx bytes.
                xor     a
                ld      (DRVA_DPB), a           ; $F195 +0 = drive-A id ($00)
                ld      hl, DRVA_DPB            ; GETDPB: HL = DPB base (fills base+1 on)
                call    getdpb
                ret
RES_STUBS       equ     $F24E   ; no-op segment-hook stub table base (§8.29)
RES_STUBS_END   equ     $F2FE   ; one past the last stub ($F2FD)
DRVA_DPB        equ     $F195   ; drive-A DPB base (id byte + 18-byte DPB, §8.30)
DRVTBL          equ     $F348   ; MSX-DOS-1 disk-driver table (§8.22)
RES_PRINT       equ     $F1C9   ; resident $-string print routine the kernel CALLs (§8.28)
DRV_NTRAMP      equ     4       ; number of CALLF trampolines
; drv_targets — low byte of each $40xx driver entry the trampolines call. Order
; matches the stock DRVTBL's non-zero pointer slots (+5/+7/+9/+13): the hot pointer
; is sector I/O (DSKIO), then DSKCHG/GETDPB, then DSKFMT. (Standard disk-ROM jump
; table, MSX2 TH; refined by re-trap if a driver pointer's contract differs.)
drv_targets:
                db      $10     ; DSKIO  ($4010)
                db      $13     ; DSKCHG ($4013)
                db      $16     ; GETDPB ($4016)
                db      $1C     ; DSKFMT ($401C)
; wa_stub — the no-op body for the $F368 segment-switch hooks (RET; see above).
wa_stub:
                ret

; res_print_tmpl — clean-room body for the resident $-string print routine, relocated
; to RES_PRINT ($F1C9) by build_resident (§8.28). The kernel CALLs $F1C9 with DE -> a
; '$'-terminated string. Our first cut CONSUMES the string (advance DE past it) and
; returns; it does not yet emit the characters (the stock routes each char through a
; disk-ROM console primitive). Straight-line + relative-jump only, so a plain LDIR
; relocates it verbatim. Re-trap will show whether the kernel needs real output.
;   in:  DE -> '$'-terminated string ; out: DE past the '$', A=$24, others as Z80 CP
res_print_tmpl:
                ld      a, (de)         ; A = next string byte
                inc     de
                cp      '$'             ; $24 = MS-DOS string terminator
                ret     z               ; done -> return to the kernel
                jr      res_print_tmpl  ; (relocatable: PC-relative loop)
res_print_end:

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

; int_h ($0038) — maskable-interrupt vector while RAM is in page 0. Our boot runs
; DI throughout, so this only fires if MSXDOS.SYS re-enables interrupts before
; installing its own handler. Acknowledge the VDP frame interrupt (reading the
; TMS9918 status port $99 clears it) and return; without the ack the interrupt
; would re-fire immediately. (Documented-shape safe stub; TMS9918 datasheet.)
int_h:
                push    af
                in      a, ($99)        ; read VDP S#0 -> clears the frame-int flag
                pop     af
                ei
                ret

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
                ; issue write-sector and transfer the data
                ld      a, c
                ld      (FDC_SECTOR), a
                ld      hl, (FDC_DEST)  ; reload buffer start each attempt
                ld      a, CMD_WRITE
                ld      (FDC_STATUS), a
                call    fdc_write_data
                ret     nc              ; success: Cy = 0, HL = buffer + 512
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
                ret

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

; getdpb — build the Drive Parameter Block from the BPB ($4016 disk-ROM entry).
;
; Builds a real DPB from the on-disk BPB. This is the PROVIDER-direction surface
; (disk/docs/expansion-protocol.md §4a): a real MSX-BASIC / MSX-DOS host calls
; $4016 to obtain the mounted volume's geometry as a DPB, so the provider must
; answer it (a black-box trace of BLOAD/SAVE on the CF-3300 showed Disk BASIC
; DOES call GETDPB). zerobas's own loader path never calls $4016 — it derives
; geometry straight from the BPB (fat_mount) — but a foreign host driving us does.
;
; Calling convention (MSX disk-ROM interface; Nextor 2.1 Driver Development Guide
; §4.5.3, which restates the standard GETDPB contract):
;   in:  A  = drive (unit) number (0 = A:)  — ignored, single-drive machine
;        B  = C = media descriptor byte
;        HL = DPB base address MINUS ONE (the byte at base+0 is the drive number,
;             which GETDPB does NOT fill; GETDPB fills base+1 = media onward)
;   out: Cy = 0 ok (DPB filled), Cy = 1 = error (could not read the boot sector)
;
; DPB field layout + encodings: MSX2 Technical Handbook §3, Figure 3.11 (DPB
; structure), and the Nextor 2.1 Driver Development Guide §4.5.3 field formulas.
; Each field below cites its source + derivation. The whole layout was confirmed
; FIELD-FOR-FIELD against a black-box GETDPB trace of the National CF-3300
; reference on this same 720 KB image (carry=0, DPB bytes read out of RAM — the
; reference ROM's code was never read). See disk/PROVENANCE.md §DPB.
;
; fat_mount already parses the BPB into scratch (FAT_FATSTART / FAT_FIRSTROOT /
; FAT_FIRSTDATA / FAT_SECPERCLUS / FAT_NUMFATS / FAT_SECPERFAT) and leaves the
; boot sector in SECTOR_BUF, so GETDPB reuses those (our own code) and reads the
; remaining raw BPB fields (media, sector size, root-entry count) from SECTOR_BUF.
getdpb:
                ; HL = DPB base - 1 (Nextor §4.5.3). GETDPB fills from base+1 (media)
                ; onward; base+0 (drive number) is the caller's, not ours. So the
                ; first byte WE write (media) lands at HL+1. (CONFIRMED by the
                ; CF-3300 black-box trace: with HL = $C0FF the reference wrote the
                ; media byte at $C100 = HL+1; see disk/PROVENANCE.md §DPB.)
                inc     hl                  ; HL -> DPB +1 (media ID), = caller HL + 1
                push    hl                  ; keep DPB+1 pointer across fat_mount
                call    fat_mount           ; parse BPB; leaves boot sector in SECTOR_BUF
                pop     hl
                ret     c                   ; boot-sector read failed -> Cy = 1

                ; +1 media ID = BPB media descriptor (boot sector +21). TH Fig 3.11
                ; "media ID"; ECMA-107 / MS FAT spec media byte. (= $F9 on 720 KB.)
                ld      a, (SECTOR_BUF + 21)
                ld      (hl), a
                inc     hl                  ; HL -> DPB +2

                ; +2..3 sector size (LE) = BPB bytes-per-sector. TH Fig 3.11; we
                ; validated $0200 (512) at mount, so copy the BPB word verbatim.
                ld      a, (SECTOR_BUF + BPB_BYTSPERSEC)
                ld      (hl), a
                inc     hl
                ld      a, (SECTOR_BUF + BPB_BYTSPERSEC + 1)
                ld      (hl), a
                inc     hl                  ; HL -> DPB +4

                ; +4 directory mask = (sector size / 32) - 1  (Nextor §4.5.3:
                ; "directory mask = (sector size/32) - 1"). 512/32 - 1 = 15 = $0F.
                ; +5 directory shift = number of one-bits in the directory mask
                ;    (Nextor §4.5.3) = log2(entries per sector) = 4 for 512-byte
                ;    sectors. Sector size is validated = 512 at mount, so these are
                ;    the fixed 512-byte values $0F / $04 (CF-3300 oracle: 0f 04).
                ld      (hl), $0F           ; +4 directory mask
                inc     hl
                ld      (hl), 4             ; +5 directory shift
                inc     hl                  ; HL -> DPB +6

                ; +6 cluster mask = (sectors per cluster) - 1   (Nextor §4.5.3).
                ; +7 cluster shift = (one-bits in cluster mask) + 1 (Nextor §4.5.3);
                ;    for a power-of-two secPerClus this equals log2(secPerClus)+1.
                ;    720 KB: secPerClus = 2 -> mask = 1, shift = 2 (CF-3300: 01 02).
                ld      a, (FAT_SECPERCLUS) ; our own BPB-derived value (fat_mount)
                dec     a
                ld      (hl), a             ; +6 cluster mask = secPerClus - 1
                ld      c, a                ; C = cluster mask (count its one-bits)
                inc     hl                  ; HL -> DPB +7
                ld      b, 1                ; shift starts at 1 (Nextor: +1)
                ld      a, c
                or      a
                jr      z, gdpb_popdone
gdpb_pc_loop:
                srl     c
                jr      nc, gdpb_pc_next
                inc     b                   ; one more set bit -> +1 to the shift
gdpb_pc_next:
                ld      a, c
                or      a
                jr      nz, gdpb_pc_loop
gdpb_popdone:
                ld      (hl), b             ; +7 cluster shift
                inc     hl                  ; HL -> DPB +8

                ; +8..9 top sector of FAT (LE) = first FAT sector = reserved sectors.
                ; TH Fig 3.11 "top sector of FAT"; our FAT_FATSTART (fat_mount).
                ld      de, (FAT_FATSTART)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl                  ; HL -> DPB +10

                ; +10 number of FATs. TH Fig 3.11; our FAT_NUMFATS (BPB +16).
                ld      a, (FAT_NUMFATS)
                ld      (hl), a
                inc     hl                  ; HL -> DPB +11

                ; +11 number of directory entries (max 254). TH Fig 3.11; BPB +17
                ; root-entry count low byte (112 on 720 KB -> $70; high byte is 0).
                ld      a, (SECTOR_BUF + BPB_ROOTENTCNT)
                ld      (hl), a
                inc     hl                  ; HL -> DPB +12

                ; +12..13 top sector of data area (LE) = first data sector.
                ; TH Fig 3.11 "top sector of data area"; our FAT_FIRSTDATA.
                ld      de, (FAT_FIRSTDATA)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl                  ; HL -> DPB +14

                ; +14..15 amount of cluster + 1 (LE). TH Fig 3.11 "amount of cluster
                ; + 1"; = data-cluster count + 1. fat_total_clusters returns
                ; dataClusters + 2 (its highest-cluster-plus-one chain bound), so
                ; the DPB field is that value - 1. (CF-3300 oracle: $02CA = 714 =
                ; dataClusters(713) + 1 on this 720 KB image; fat_total_clusters
                ; returns 715, minus 1 = 714.) Microsoft FAT spec §3.3 cluster count.
                push    hl
                call    fat_total_clusters  ; DE = dataClusters + 2 (reads boot sec into WBUF)
                dec     de                  ; DE = dataClusters + 1 (the DPB encoding)
                pop     hl
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl                  ; HL -> DPB +16

                ; +16 number of sectors per FAT. TH Fig 3.11; our FAT_SECPERFAT
                ; (BPB +22). 720 KB = 3. Single byte (FAT fits < 256 sectors).
                ld      a, (FAT_SECPERFAT)
                ld      (hl), a
                inc     hl                  ; HL -> DPB +17

                ; +17..18 top sector of directory area (LE) = first root-dir sector.
                ; TH Fig 3.11 "top sector of directory area"; our FAT_FIRSTROOT.
                ld      de, (FAT_FIRSTROOT)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                ; +19..20 (FAT address in memory) is filled by the OS, not GETDPB
                ; (TH Fig 3.11) — left untouched, matching the CF-3300 oracle which
                ; left those two bytes unwritten.
                or      a                   ; Cy = 0 success
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
; a 1500-byte file (disk_probe_bdos.py, msx-preservation) — the last record is
; 92 real bytes + 36 bytes of $00 (confirmed by pre-filling the DTA with $FF: the
; tail still returns $00, so MSX-DOS actively zero-fills, not Ctrl-Z/stale data),
; code $00; the following read returns $01. CP/M FCB sequential-I/O record model
; (MSX2 TH, FCB sequential I/O) supplies the record framing.
bdos_seqread:
                ; EOF once every file byte has been delivered (BYTESLEFT == 0).
                ld      hl, (BDOS_BYTESLEFT)        ; low word
                ld      de, (BDOS_BYTESLEFT + 2)    ; high word
                ld      a, h
                or      l
                or      d
                or      e
                jr      z, bsr_eof                  ; no bytes left -> EOF
                ld      a, (BDOS_RECIDX)
                cp      RECPERSEC
                jr      c, bsr_have     ; records still left in SECTOR_BUF
                call    fat_read_file_sector
                jr      c, bsr_eof      ; chain ended early -> EOF (shouldn't, BYTESLEFT>0)
                xor     a
                ld      (BDOS_RECIDX), a    ; back to record 0
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
rdb_recloop:
                ld      hl, (RDBLK_DONE)
                ld      de, (RDBLK_REQ)
                or      a
                sbc     hl, de
                jr      z, rdb_ok           ; delivered every requested record
                ld      hl, (RDBLK_RECSIZE)
                ld      (RDBLK_CNT), hl     ; bytes still to copy for this record
rdb_byteloop:
                ld      hl, (RDBLK_CNT)
                ld      a, h
                or      l
                jr      z, rdb_recdone      ; whole record copied
                ; EOF when every file byte has been delivered (BYTESLEFT == 0)
                ld      hl, (BDOS_BYTESLEFT)
                ld      de, (BDOS_BYTESLEFT + 2)
                ld      a, h
                or      l
                or      d
                or      e
                jr      z, rdb_eof
                call    rdblk_getbyte       ; A = next file byte (advances buffer)
                jr      c, rdb_eof          ; chain ended early (defensive)
                ld      hl, (RDBLK_DST)
                ld      (hl), a
                inc     hl
                ld      (RDBLK_DST), hl
                ld      hl, (RDBLK_CNT)
                dec     hl
                ld      (RDBLK_CNT), hl
                jr      rdb_byteloop
rdb_recdone:
                ld      hl, (RDBLK_DONE)
                inc     hl
                ld      (RDBLK_DONE), hl
                jr      rdb_recloop
rdb_ok:
                xor     a                   ; A = $00 all requested records read
                ld      hl, (RDBLK_DONE)
                ret
rdb_eof:
                ld      a, $01              ; A = $01 EOF before all requested
                ld      hl, (RDBLK_DONE)    ; HL = records actually read
                ret

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

; --- BDOS WRITE calls (disk/PROVENANCE.md §BDOS interface, §FAT12 write-back) -

; bdos_create ($16) — create (or truncate-if-exists) the file named in the FCB,
; ready for sequential writing from offset 0.
;   in:  DE = FCB pointer (FCB+1 = 11-byte 8.3 name)
;   out: A = $00 created / $FF error (disk full / write protect / I/O)
; Mounts the volume, then finds or makes a root-directory slot for the name and
; writes a fresh dir entry (name, attribute $00, first cluster = 0, size = 0,
; timestamps = 0 — see the date/time divergence in disk/PROVENANCE.md). No data
; cluster is allocated yet: the first cluster is allocated lazily on the first
; Sequential Write, so a zero-byte file occupies no clusters (matching MSX-DOS).
bdos_create:
                push    de              ; FCB across fat_mount
                call    fat_mount
                jr      c, bdos_create_failpop
                pop     hl              ; HL = FCB
                inc     hl              ; HL = FCB+1 = 8.3 name
                call    fat_dir_create  ; find/make a dir slot, write the entry
                jr      c, bdos_create_err
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
bdos_create_failpop:
                pop     hl
bdos_create_err:
                xor     a
                ld      (BDOS_WRMODE), a
                ld      a, $FF
                ret

; bdos_seqwrite ($15) — write the next 128-byte record FROM the DTA into the file.
;   out: A = $00 ok / $01 disk full / $FF error (MSX2 TH, BDOS conventions)
; Buffers RECSIZE (128) bytes from BDOS_DTA into SECTOR_BUF at offset BDOS_WRBUFLEN;
; whenever the buffer fills (512 bytes) it is flushed to the file's current data
; sector (allocating/extending the cluster chain as needed) and the buffer resets.
; BDOS_WRBYTES accumulates the true byte count for Close to stamp into the dir
; entry. (CP/M / MSX-DOS sequential write delivers a fixed 128-byte record from
; the DTA — MSX2 TH FCB sequential I/O; record framing as the read side.)
bdos_seqwrite:
                ld      a, (BDOS_WRMODE)
                or      a
                jr      z, bsw_err          ; not open for write
                ; copy RECSIZE bytes DTA -> SECTOR_BUF + BDOS_WRBUFLEN
                ld      hl, (BDOS_WRBUFLEN)
                ld      de, SECTOR_BUF
                add     hl, de              ; HL = dest in SECTOR_BUF
                ex      de, hl              ; DE = dest
                ld      hl, (BDOS_DTA)      ; HL = source record (settable DTA)
                ld      bc, RECSIZE
                ldir                        ; copy 128 bytes into the buffer
                ; advance buffered length and total byte count by RECSIZE.
                ld      hl, (BDOS_WRBUFLEN)
                ld      de, RECSIZE
                add     hl, de
                ld      (BDOS_WRBUFLEN), hl
                call    wrbytes_add_recsize ; BDOS_WRBYTES += RECSIZE (4-byte LE)
                ; if the 512-byte buffer is now full, flush it to the file.
                ld      hl, (BDOS_WRBUFLEN)
                ld      de, 512
                or      a
                sbc     hl, de
                jr      c, bsw_ok           ; buffer not full yet
                call    fat_flush_data_sector
                jr      c, bsw_full         ; disk full / write error
                ld      hl, 0
                ld      (BDOS_WRBUFLEN), hl ; buffer drained
bsw_ok:
                xor     a                   ; A = $00 success
                ret
bsw_full:
                ld      a, $01              ; disk full (MSX-DOS seq-write code)
                ret
bsw_err:
                ld      a, $FF
                ret

; wrbytes_add_recsize — BDOS_WRBYTES += RECSIZE, 4-byte little-endian add.
wrbytes_add_recsize:
                ld      hl, BDOS_WRBYTES
                ld      a, (hl)
                add     a, RECSIZE
                ld      (hl), a
                inc     hl
                ld      b, 3                ; carry through the upper 3 bytes
wba_loop:
                ld      a, (hl)
                adc     a, 0
                ld      (hl), a
                inc     hl
                djnz    wba_loop
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
                ld      (FAT_NUMFATS), a    ; cache for the write path's FAT sync
                ld      b, a
                ld      de, (SECTOR_BUF + BPB_FATSZ16)
                ld      (FAT_SECPERFAT), de ; cache for per-copy sector stride
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

; ===========================================================================
; FAT12 WRITE-BACK substrate (disk/PROVENANCE.md §FAT12 write-back)
; ===========================================================================
; The write twins of the read helpers. All structures (free-cluster scan, 12-bit
; entry pack, multi-FAT sync, directory-entry create/update) are realised from
; the Microsoft FAT specification; the physical sector write goes through the
; already-validated dskio write path. Reached by bdos_create / bdos_seqwrite /
; bdos_close. Buffer discipline: the file DATA being accumulated for a Sequential
; Write lives in SECTOR_BUF (fat_flush_data_sector writes it out); the FAT/dir
; METADATA helpers (alloc/link/dir create/update) use the independent WBUF, so a
; cluster scan or dir stamp never disturbs the in-flight data sector.

; write_sector — write one logical sector from a buffer via the DSKIO core.
;   in:  DE = logical sector number, HL = buffer (512 bytes)
;   out: Cy = 0 ok, Cy = 1 error (A = DSKIO error code)
; The write twin of read_sector: same DSKIO call but with the direction carry set
; (Cy = 1 = write). The caller has already staged the data in the buffer.
write_sector:
                ld      b, 1            ; one sector
                ld      c, $F9          ; media byte (ignored, single drive)
                ld      a, 0            ; drive 0 (ignored)
                scf                     ; Cy = 1 = WRITE direction (MSX2 TH DSKIO)
                jp      dskio           ; tail-call: dskio returns to our caller

; fat_read_fat_sector — read FAT-copy-0 sector that holds cluster N's entry.
;   in:  HL = cluster number
;   out: WBUF holds that FAT sector; (FAT_FATSEC) = its absolute sector;
;        (FAT_BYTEIDX) = byte index of the entry's low byte within the sector;
;        (FAT_PARITY) = cluster & 1; Cy reflects the read.
; Uses the write-back buffer WBUF (NOT SECTOR_BUF), so the in-flight data being
; accumulated for a Sequential Write is never disturbed by a FAT scan. Shared
; offset math with fat_next_cluster: fatofs = cluster*3/2; sector = fatStart +
; fatofs/512; byteidx = fatofs & 511. (Microsoft FAT spec §3.2.)
fat_read_fat_sector:
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
                srl     a                   ; fatofs >> 9 = FAT sector offset
                ld      e, a
                ld      d, 0
                ld      hl, (FAT_FATSTART)
                add     hl, de
                ld      (FAT_FATSEC), hl
                ex      de, hl
                ld      hl, WBUF
                jp      read_sector

; fat_alloc_cluster — find a free ($000) cluster, mark it EOC, sync all FATs.
;   out: Cy = 0 ok, HL = the allocated cluster number; Cy = 1 = disk full / error
; Linear scan from cluster 2 to the last data cluster (total = fat_total_clusters,
; computed ONCE). To keep the scan fast on a populated disk (the first free
; cluster can be hundreds of clusters in), the FAT is read SECTOR-BY-SECTOR into
; WBUF: fat_get_entry is only invoked once a candidate $000 is suspected, so the
; common case reads one FAT sector and tests up to 341 entries from RAM. The first
; $000 entry is claimed: written as EOC ($FFF) into every FAT copy via
; fat_write_fat_entry, so a freshly allocated tail cluster already terminates the
; chain. (Microsoft FAT spec §3.2: $000 = free, $FF8-$FFF = end-of-chain.)
fat_alloc_cluster:
                call    fat_total_clusters  ; DE = total clusters (reads boot sector)
                ld      (FAT_WRTMP), de
                ; FAT_FATSEC tracks which FAT sector is in WBUF; -1 = none loaded.
                ld      hl, $FFFF
                ld      (FAT_WRTMP2), hl    ; cached-sector = none
                ld      hl, 2               ; first data cluster
fac_loop:
                ld      de, (FAT_WRTMP)
                push    hl
                or      a
                sbc     hl, de
                pop     hl
                jr      nc, fac_full        ; cluster >= total -> disk full
                ; which FAT sector + byte index holds cluster HL's entry?
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
                ; is this sector already in WBUF? (cached-sector compare)
                ld      de, (FAT_WRTMP2)
                push    hl
                or      a
                sbc     hl, de
                pop     hl
                jr      z, fac_have_sec     ; already loaded -> no re-read
                ld      (FAT_WRTMP2), hl    ; remember the new cached sector
                ld      (FAT_FATSEC), hl
                ex      de, hl
                ld      hl, WBUF
                call    read_sector
                jr      c, fac_rderr
fac_have_sec:
                ; read the 12-bit entry from WBUF (handles straddle into next sec).
                pop     hl                  ; HL = cluster
                push    hl
                call    fac_entry_from_wbuf ; DE = entry value
                ld      a, d
                or      e
                pop     hl
                jr      z, fac_found        ; $000 -> free
                inc     hl
                jr      fac_loop
fac_rderr:
                pop     hl
                ret                         ; Cy set from read_sector
fac_found:
                ; claim it: write EOC into every FAT copy, return the cluster.
                push    hl
                ld      de, EOC
                call    fat_write_fat_entry ; HL = cluster, DE = value
                pop     hl
                ret     c                   ; write error propagates (Cy set)
                or      a                   ; Cy = 0 success, HL = cluster
                ret
fac_full:
                scf                         ; disk full
                ret

; fac_entry_from_wbuf — unpack cluster (FAT_BYTEIDX/FAT_PARITY already set) from
; the FAT sector currently in WBUF; if the entry straddles the 512-byte boundary
; (byteidx == 511) read the FOLLOWING FAT sector for the high byte (and leave it
; cached, since the scan continues into it).
;   out: DE = 12-bit entry value; preserves nothing but DE
fac_entry_from_wbuf:
                ld      hl, (FAT_BYTEIDX)
                ld      de, WBUF
                add     hl, de
                ld      a, (hl)
                ld      (FAT_B0), a
                ld      hl, (FAT_BYTEIDX)
                ld      de, 511
                or      a
                sbc     hl, de
                jr      z, fac_straddle
                ld      hl, (FAT_BYTEIDX)
                ld      de, WBUF + 1
                add     hl, de
                ld      a, (hl)
                jr      fac_comb
fac_straddle:
                ; read the next FAT sector into WBUF and cache it.
                ld      hl, (FAT_FATSEC)
                inc     hl
                ld      (FAT_FATSEC), hl
                ld      (FAT_WRTMP2), hl
                ex      de, hl
                ld      hl, WBUF
                call    read_sector
                ld      a, (WBUF)
fac_comb:
                ld      (FAT_B1), a
                ld      a, (FAT_PARITY)
                or      a
                jr      nz, fac_e_odd
                ld      a, (FAT_B1)
                and     $0F
                ld      d, a
                ld      a, (FAT_B0)
                ld      e, a
                ret
fac_e_odd:
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

; fat_write_fat_entry — set a cluster's 12-bit value in EVERY FAT copy on disk.
;   in:  HL = cluster, DE = 12-bit value to store
;   out: Cy = 0 ok, Cy = 1 error
; Reads the FAT-copy-0 sector(s) holding the entry, packs the 12 bits into the
; right nibbles (even cluster: low byte = v[7:0], high nibble of next byte =
; v[11:8]; odd cluster: low nibble of byte = v[3:0], next byte = v[11:4] — the
; exact inverse of fat_next_cluster's unpack), then writes the modified sector
; back to the SAME relative sector in all BPB_NUMFATS copies. If the entry
; straddles a 512-byte boundary the following FAT sector is updated too.
; (Microsoft FAT spec §3.2 packing; multi-FAT sync per BPB_NUMFATS.)
fat_write_fat_entry:
                ld      (FAT_WRTMP), de     ; save the value
                push    hl                  ; save cluster
                call    fat_read_fat_sector ; WBUF = FAT sector 0; BYTEIDX/PARITY set
                ; --- pack the low byte / shared nibble into WBUF[byteidx]
                ld      hl, (FAT_BYTEIDX)
                ld      de, WBUF
                add     hl, de
                push    hl                  ; HL = &buf[byteidx]
                ld      de, (FAT_WRTMP)     ; DE = value
                ld      a, (FAT_PARITY)
                or      a
                jr      nz, fwe_odd0
                ; even: buf[byteidx] = value & $FF
                ld      a, e
                ld      (hl), a
                jr      fwe_byte1
fwe_odd0:
                ; odd: buf[byteidx] = (buf[byteidx] & $0F) | ((value & $0F) << 4)
                ld      a, (hl)
                and     $0F
                ld      b, a
                ld      a, e
                and     $0F
                rlca
                rlca
                rlca
                rlca
                or      b
                ld      (hl), a
fwe_byte1:
                pop     hl                  ; HL = &buf[byteidx]
                ; the second byte may live in the next FAT sector.
                ld      bc, (FAT_BYTEIDX)
                ld      a, c
                cp      $FF
                jr      nz, fwe_b1_same     ; byteidx != 511 -> same sector
                ld      a, b
                or      a
                jr      nz, fwe_b1_same     ; (byteidx high != 0; impossible for 512)
                ; straddle: byte1 is buf[0] of the NEXT FAT sector. First persist
                ; this sector to all FATs, then load + patch the next sector. The
                ; saved cluster is still on the stack, so pop it before any early
                ; error return (Cy preserved) to keep the stack balanced.
                call    fat_write_buf_allfats
                jr      c, fwe_err
                ld      hl, (FAT_FATSEC)
                inc     hl
                ld      (FAT_FATSEC), hl    ; advance to the straddle sector
                ex      de, hl
                ld      hl, WBUF
                call    read_sector
                jr      c, fwe_err
                ld      hl, WBUF            ; patch byte 0 of the next sector
                ld      de, (FAT_WRTMP)
                ld      a, (FAT_PARITY)
                or      a
                jr      nz, fwe_str_odd
                ; even straddle: buf[0] = (buf[0] & $F0) | ((value >> 8) & $0F)
                ld      a, (hl)
                and     $F0
                ld      b, a
                ld      a, d
                and     $0F
                or      b
                ld      (hl), a
                jr      fwe_finish
fwe_str_odd:
                ; odd straddle: buf[0] = value[11:4] = (value >> 4) & $FF
                ; compute (value>>4): low nibble from high nibble of E, high nibble
                ; from low nibble of D.
                ld      hl, WBUF
                ld      a, e
                rrca
                rrca
                rrca
                rrca
                and     $0F                 ; high nibble of E -> low nibble of result
                ld      b, a
                ld      a, d
                rlca
                rlca
                rlca
                rlca
                and     $F0                 ; D<<4 -> high nibble of result
                or      b
                ld      (hl), a
                jr      fwe_finish
fwe_b1_same:
                ; second byte is buf[byteidx+1] in the same sector.
                inc     hl                  ; HL = &buf[byteidx+1]
                ld      de, (FAT_WRTMP)
                ld      a, (FAT_PARITY)
                or      a
                jr      nz, fwe_same_odd
                ; even: buf[byteidx+1] = (buf[byteidx+1] & $F0) | ((value>>8)&$0F)
                ld      a, (hl)
                and     $F0
                ld      b, a
                ld      a, d
                and     $0F
                or      b
                ld      (hl), a
                jr      fwe_finish
fwe_same_odd:
                ; odd: buf[byteidx+1] = (value >> 4) & $FF
                ld      a, e
                rrca
                rrca
                rrca
                rrca
                and     $0F
                ld      b, a
                ld      a, d
                rlca
                rlca
                rlca
                rlca
                and     $F0
                or      b
                ld      (hl), a
fwe_finish:
                pop     hl                  ; discard saved cluster
                ; persist the (current) FAT sector to all FAT copies.
                jp      fat_write_buf_allfats
fwe_err:
                pop     hl                  ; discard saved cluster (keep stack sane)
                scf                         ; report the I/O error
                ret

; fat_write_buf_allfats — write WBUF back to (FAT_FATSEC) in every FAT copy.
;   in:  WBUF holds the sector; FAT_FATSEC = its sector in FAT copy 0
;   out: Cy = 0 ok, Cy = 1 error
; The same relative offset in each of the BPB_NUMFATS copies differs by exactly
; secPerFAT sectors, so copy k's sector = FAT_FATSEC + k*secPerFAT. The bytes are
; written from WBUF, which must NOT be disturbed between copies — so the per-copy
; target sector is computed without re-reading. (Microsoft FAT spec §3.1: NumFATs
; identical copies; §3.2: same entry packing in each.)
fat_write_buf_allfats:
                ; numFATs and secPerFAT were cached by fat_mount (FAT_NUMFATS /
                ; FAT_SECPERFAT) precisely so this routine needs no boot-sector
                ; re-read — WBUF here holds the FAT sector we must preserve across
                ; all copies.
                ld      a, (FAT_NUMFATS)
                ld      b, a                ; B = copies to write
                ld      hl, (FAT_FATSEC)    ; copy-0 target sector
fwba_loop:
                push    bc
                push    hl
                ex      de, hl              ; DE = target sector
                ld      hl, WBUF
                call    write_sector
                pop     hl
                pop     bc
                ret     c                   ; write error
                ; advance to the same sector in the next FAT copy.
                ld      de, (FAT_SECPERFAT)
                add     hl, de
                djnz    fwba_loop
                or      a                   ; Cy = 0 success
                ret

; fat_total_clusters — total cluster count of the volume (2 + data clusters).
;   out: DE = total clusters; preserves HL
; dataClusters = (totalSectors - firstData) / secPerClus; we read totalSectors
; from the BPB. Re-reads the boot sector into WBUF (NOT SECTOR_BUF, which may hold
; in-flight write data). (Microsoft FAT spec §3.3.)
fat_total_clusters:
                push    hl
                ld      de, 0
                ld      hl, WBUF
                call    read_sector
                jr      c, ftc_done         ; on error report 2 (no free clusters)
                ld      hl, (WBUF + 19)     ; total sectors 16-bit (BPB +19)
                ld      de, (FAT_FIRSTDATA)
                or      a
                sbc     hl, de              ; HL = data sectors
                ; DE accumulates dataSectors / secPerClus.
                ld      de, 0
                ld      a, (FAT_SECPERCLUS)
                ld      c, a
ftc_div:
                ld      a, l
                or      h
                jr      z, ftc_divdone
                ld      a, l
                sub     c
                ld      l, a
                jr      nc, ftc_nob
                dec     h
ftc_nob:
                inc     de
                jr      ftc_div
ftc_divdone:
                inc     de
                inc     de                  ; + 2 (first data cluster is 2)
ftc_done:
                pop     hl
                ret

; fat_flush_data_sector — write SECTOR_BUF (the current 512-byte data buffer) to
; the file's current data sector, allocating/extending the cluster chain first.
;   out: Cy = 0 ok, Cy = 1 = disk full / write error
; Zero-pads SECTOR_BUF from BDOS_WRBUFLEN..511 (partial final sector), ensures a
; current cluster exists (allocating the first one and recording it in BDOS_WRFIRST,
; or allocating + linking the next when the current cluster is full), then writes
; the absolute data sector = firstData + (cluster-2)*secPerClus + WRSECIDX and
; advances WRSECIDX. (Microsoft FAT spec §3.3 data-sector math.)
fat_flush_data_sector:
                ; zero-pad the unused tail of the buffer (bytes WRBUFLEN..511) so a
                ; partial final sector writes 512 well-defined bytes. pad count =
                ; 512 - WRBUFLEN; dest = SECTOR_BUF + WRBUFLEN.
                ld      hl, 512
                ld      de, (BDOS_WRBUFLEN)
                or      a
                sbc     hl, de              ; HL = 512 - WRBUFLEN (pad count, 0..512)
                jr      z, ffds_nopad       ; buffer already full -> no pad
                jr      c, ffds_nopad       ; (defensive: WRBUFLEN > 512 never happens)
                ld      b, h
                ld      c, l                ; BC = pad count
                ld      hl, SECTOR_BUF
                add     hl, de              ; HL = SECTOR_BUF + WRBUFLEN = first pad byte
ffds_padloop:
                ld      a, b
                or      c
                jr      z, ffds_nopad
                xor     a
                ld      (hl), a
                inc     hl
                dec     bc
                jr      ffds_padloop
ffds_nopad:
                ; ensure we have a data cluster to write into. Allocate when there
                ; is NO cluster yet (WRCLUS == 0, the very first flush) OR the
                ; current cluster is full (WRSECIDX >= secPerClus).
                ld      hl, (BDOS_WRCLUS)
                ld      a, h
                or      l
                jr      z, ffds_alloc       ; no cluster yet -> allocate the first
                ld      a, (BDOS_WRSECIDX)
                ld      hl, FAT_SECPERCLUS
                cp      (hl)
                jr      c, ffds_haveclus    ; room in the current cluster
ffds_alloc:
                ; allocate a new cluster (first one, or chain extension).
                call    fat_alloc_cluster
                ret     c                   ; disk full
                ; HL = new cluster. Link it: if a previous cluster exists, point it
                ; at HL; else record HL as the file's first cluster.
                ld      de, (BDOS_WRCLUS)
                ld      a, d
                or      e
                jr      z, ffds_first       ; no previous cluster -> this is first
                push    hl                  ; save new cluster
                ex      de, hl              ; HL = previous cluster
                pop     de                  ; DE = new cluster (value to link)
                push    de
                call    fat_write_fat_entry ; previous -> new (12-bit link)
                pop     hl                  ; HL = new cluster
                ret     c
                jr      ffds_setclus
ffds_first:
                ld      (BDOS_WRFIRST), hl  ; remember the file's first cluster
ffds_setclus:
                ld      (BDOS_WRCLUS), hl
                xor     a
                ld      (BDOS_WRSECIDX), a  ; start at sector 0 of the new cluster
ffds_haveclus:
                ; absolute sector = firstData + (cluster-2)*secPerClus + WRSECIDX
                ld      hl, (BDOS_WRCLUS)
                ld      de, 2
                or      a
                sbc     hl, de
                ex      de, hl              ; DE = cluster - 2
                ld      hl, 0
                ld      a, (FAT_SECPERCLUS)
                ld      b, a
ffds_mul:
                add     hl, de
                djnz    ffds_mul            ; HL = (cluster-2) * secPerClus
                ld      de, (FAT_FIRSTDATA)
                add     hl, de
                ld      a, (BDOS_WRSECIDX)
                ld      e, a
                ld      d, 0
                add     hl, de              ; HL = absolute logical sector
                ex      de, hl              ; DE = sector
                ld      hl, SECTOR_BUF
                call    write_sector
                ret     c
                ld      a, (BDOS_WRSECIDX)
                inc     a
                ld      (BDOS_WRSECIDX), a
                or      a                   ; Cy = 0 success
                ret

; fat_dir_create — find/make a root-directory slot for an 8.3 name and write a
; fresh entry; record the slot's sector + offset in BDOS_DIRSEC/BDOS_DIROFF.
;   in:  HL = 11-byte 8.3 name field
;   out: Cy = 0 ok, Cy = 1 = directory full / I/O error
; First scans the root directory for an EXISTING entry of the same name (truncate-
; in-place: reuse its slot, which also frees nothing — the old chain is orphaned;
; acceptable for the loader-create subset, see PROVENANCE divergence). Otherwise
; claims the first free slot ($00 end-marker or $E5 deleted). Writes name (+0..10),
; attribute $00 (+11; ORACLE: MSX-DOS Create makes a normal file, archive bit
; clear), zeroes +12..25 incl. the date/time fields (intentional divergence — no
; clock; see disk/PROVENANCE.md), first cluster 0 (+26), size 0 (+28..31), then
; writes the dir sector back. (Microsoft FAT spec §3.4.)
fat_dir_create:
                ld      (FAT_NAMEPTR), hl
                ld      hl, (FAT_FIRSTROOT)
                ld      (FAT_DIRSEC), hl
                ld      hl, (FAT_ROOTSECS)
                ld      (FAT_DIRREM), hl
fdc_secloop:
                ld      hl, (FAT_DIRREM)
                ld      a, h
                or      l
                jr      z, fdc_full         ; no slot in any root sector
                ld      de, (FAT_DIRSEC)
                ld      hl, WBUF
                call    read_sector
                ret     c
                ld      hl, WBUF
                ld      b, 16               ; 16 entries per 512-byte sector
fdc_entloop:
                push    bc
                push    hl
                ld      a, (hl)
                or      a
                jr      z, fdc_useslot      ; $00 end-marker -> free slot here
                cp      $E5
                jr      z, fdc_useslot      ; $E5 deleted -> reusable slot
                ; same-name existing entry? (truncate-in-place)
                ld      de, (FAT_NAMEPTR)
                call    name_cmp
                jr      z, fdc_useslot
                pop     hl
                ld      de, 32
                add     hl, de
                pop     bc
                djnz    fdc_entloop
                ld      hl, (FAT_DIRSEC)
                inc     hl
                ld      (FAT_DIRSEC), hl
                ld      hl, (FAT_DIRREM)
                dec     hl
                ld      (FAT_DIRREM), hl
                jr      fdc_secloop
fdc_useslot:
                pop     hl                  ; HL = dir entry slot in WBUF
                pop     bc
                ; record the slot's sector + byte offset for fat_dir_update.
                ld      de, (FAT_DIRSEC)
                ld      (BDOS_DIRSEC), de
                push    hl
                ld      de, WBUF
                or      a
                sbc     hl, de              ; HL = offset within the sector
                ld      (BDOS_DIROFF), hl
                pop     hl
                ; write the 11-byte name (case already 8.3 upper from the caller).
                push    hl
                ex      de, hl              ; DE = dest slot
                ld      hl, (FAT_NAMEPTR)
                ld      bc, 11
                ldir                        ; name -> entry +0..10
                ; DE now points at +11 (attribute). ORACLE OBSERVATION: real
                ; MSX-DOS 1's Create writes a NORMAL file with attribute $00 (it
                ; does NOT set the archive bit), so we match it byte-for-byte
                ; (disk_probe_fwrite.py PART 3 structural compare). $00 = no
                ; attributes = an ordinary readable/writable file (Microsoft FAT
                ; spec §3.4 attribute byte).
                xor     a
                ld      (de), a             ; +11 = $00 (normal file; matches MSX-DOS)
                inc     de
                ; zero +12..+31 (S1/S2, rec-count, alloc-map, date/time, first
                ; cluster, size). Date/time = 0 is the documented divergence.
                ld      b, 20               ; +12..+31 is 20 bytes
fdc_zero:
                xor     a
                ld      (de), a
                inc     de
                djnz    fdc_zero
                pop     hl                  ; discard slot pointer
                ; write the dir sector back.
                ld      de, (BDOS_DIRSEC)
                ld      hl, WBUF
                call    write_sector
                ret     c
                or      a                   ; Cy = 0 success
                ret
fdc_full:
                scf
                ret

; fat_dir_update — rewrite the open-for-write file's directory entry at Close
; with its true byte count (DIRENT_FILESIZE) and first cluster (DIRENT_FIRSTCLUS).
;   out: Cy = 0 ok, Cy = 1 = I/O error
; Re-reads the dir entry's sector (BDOS_DIRSEC), patches the entry at BDOS_DIROFF:
; first cluster word (+26) from BDOS_WRFIRST, size dword (+28) from BDOS_WRBYTES,
; then writes the sector back. The name + attribute were set at Create and are
; left intact. (Microsoft FAT spec §3.4.)
fat_dir_update:
                ld      de, (BDOS_DIRSEC)
                ld      hl, WBUF
                call    read_sector
                ret     c
                ; HL = &entry = WBUF + DIROFF
                ld      hl, (BDOS_DIROFF)
                ld      de, WBUF
                add     hl, de
                ; +26 first cluster (LE) = BDOS_WRFIRST
                push    hl
                ld      de, DIRENT_FIRSTCLUS
                add     hl, de
                ld      de, (BDOS_WRFIRST)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                pop     hl
                ; +28 file size (4-byte LE) = BDOS_WRBYTES
                ld      de, DIRENT_FILESIZE
                add     hl, de
                ex      de, hl              ; DE = &entry+28
                ld      hl, BDOS_WRBYTES
                ld      bc, 4
                ldir
                ; write the dir sector back.
                ld      de, (BDOS_DIRSEC)
                ld      hl, WBUF
                call    write_sector
                ret     c
                or      a                   ; Cy = 0 success
                ret

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
                ds      $50A9 - $, $00  ; pad up to the kernel's $50A9 call target
                sub     a               ; A=$00, F=$42 (Z+N) -- the exact exit AF
                ld      (W50A9_WRKB), a ; $F242 := $00  (the only persistent write)
                ld      de, W50A9_RET_DE ; DE = $F1AA
                ld      ix, W50A9_RET_DE ; IX = $F1AA (= DE)
                ld      hl, W50A9_RET_HL ; HL = $F359
                ret                     ; AF=$0042, BC/IY untouched

; --- pad to a full 16 KB page ($4000-$7FFF) --------------------------------
                ds      $8000 - $, $00
