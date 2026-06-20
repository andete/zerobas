# Provenance log — zerobas-disk

Every constant, address, data table, and algorithm in zerobas-disk must appear
here with an independent **allowed** source, or be explicitly **quarantined**.
An unexplained magic value blocks release.

- **sourced** — traced to an allowed source (see [`README.md`](../README.md) for
  the list) or to this project's own black-box **oracle observation**.
- **quarantined** — no copied source; derived from the documented format or spec
  and justified by oracle round-trip (or an original algorithm of ours). **Never**
  lifted from a reference ROM or any disk-ROM/MSX-BASIC disassembly.

Allowed sources:
- **MSX2 TH** — MSX2 Technical Handbook (Konamiman's English translation, public)
- **WD2793 DS** — WD2793 FDC datasheet (Western Digital, public)
- **CF-3300 schematic** — open hardware schematics for the National CF-3300
  (National Panasonic MSX1 built-in disk machine; source TBD — see FDC section)
- **openMSX source** — openMSX emulator C++ source (GPL); usable for hardware
  register addresses and port maps
- **Microsoft FAT spec** — Microsoft FAT Filesystem Specification (public)
- **ECMA-107** — ECMA-107 standard for 3.5" disk geometry (public)
- **MSX Assembly Page** — MSX Assembly Page BIOS/sysvar reference (public web)
- **C-BIOS** — C-BIOS source (BSD 2-clause); system variable addresses
- **own design** — algorithm or constant chosen by this project

---

## ROM skeleton

The disk ROM is a standalone 16 KB ROM placed in slot 3-1, page 1 ($4000–$7FFF).
It is **not** an IPS patch: it is a fresh ROM with its own "AB" header, exactly as
a real MSX1 built-in disk machine carries.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Slot placement | slot 3-1, page 1 | MSX2 TH §3, slot architecture | sourced |
| ROM address range | $4000–$7FFF (16 KB) | MSX2 TH, memory map | sourced |
| "AB" identifier | $41 $42 at $4000 | MSX2 TH, cartridge ROM format | sourced |
| INIT vector (word) | $4002 (2-byte address; BIOS CALLs through it) | MSX2 TH, cartridge ROM format (same field as main zerobas ROM) | sourced |
| STATEMENT / DEVICE / TEXT vectors | $4004 / $4006 / $4008 = $0000 (unused) | MSX2 TH, cartridge ROM format | sourced |
| Reserved header bytes | $400A–$400F = $00 | MSX2 TH, cartridge ROM format | sourced |
| Disk entry-point table base | $4010 (immediately after the 16-byte header) | MSX2 TH, disk ROM interface | sourced |
| DSKIO entry | JP at $4010 | MSX2 TH, disk ROM interface (offset +$10 from ROM base) | sourced |
| DSKCHG entry | JP at $4013 | MSX2 TH, disk ROM interface (offset +$13) | sourced |
| GETDPB entry | JP at $4016 | MSX2 TH, disk ROM interface (offset +$16) | sourced |
| CHOICE entry | JP at $4019 | MSX2 TH, disk ROM interface (offset +$19) | sourced |
| DSKFMT entry | JP at $401C | MSX2 TH, disk ROM interface (offset +$1C) | sourced |
| MTOFF entry | JP at $401F | MSX2 TH, disk ROM interface (offset +$1F) | sourced |
| Entry-stub error return | carry set = operation failed | MSX2 TH, disk ROM interface | sourced |
| CHOICE "no choices" return | HL = $0000 (no format-choice string) | MSX2 TH, disk ROM interface | sourced |

> **Header layout correction.** An earlier draft of this table placed INIT as a
> 3-byte `JP` at $4003 with reserved bytes at $4006–$400F. That is not the MSX
> cartridge header: INIT is a 2-byte *address word* at $4002 (the BIOS CALLs
> through it), followed by the STATEMENT/DEVICE/TEXT word vectors, with the 6
> reserved bytes at $400A–$400F. Only this standard 16-byte header puts the disk
> entry-point table at $4010. The implementation (`disk/disk.asm`) and the rows
> above use the corrected, standard layout — matching the main zerobas ROM.

No quarantined items.

---

## INIT: system hook installation

The disk ROM's INIT routine (called by BIOS at boot) currently installs `JP`
instructions into two hook slots and writes the SYSTEM sysvar. **An oracle
observation has since contradicted this design — see the box below.** The hook
area is 5-byte slots in page-3 RAM, 5-byte-aligned from $FD9A.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| H.DSKIO hook address | $FF4B | (claimed MSX2 TH) | **WRONG — oracle-contradicted** |
| H.PHYD hook address | $FF3E | (claimed MSX2 TH) | **WRONG — oracle-contradicted** |
| Hook slot size | 5 bytes | MSX2 TH; oracle (hooks are 5-byte-aligned from $FD9A) | sourced |
| Cross-slot hook mechanism: `RST 30h` (CALLF) + slot byte + dw target | — | **oracle observation** (CF-3300 disk ROM, see box) | sourced |
| `JP nnnn` opcode for hook | $C3 | Z80 instruction set | **WRONG approach — JP can't cross slots** |
| SYSTEM sysvar write: LD ($F37D),HL with HL = bdos_entry | — | own code | **quarantined — oracle-contradicted** |
| INIT does NOT need to identify its own slot | — | own design | **WRONG — cross-slot hooks need the slot byte** |
| BDOS entry stub: A=$FF / RET | — | own design; A=$FF documented BDOS error | sourced |

> **ORACLE FINDING (probe 3 investigation) — the hook/SYSTEM design is wrong and
> must be redesigned.** Observing the **National CF-3300** reference in openMSX
> after boot (RAM only — the disk ROM's code was never read), the real disk ROM
> integrates very differently from what our INIT does:
> - It installs **`RST 30h` (CALLF) inter-slot calls** — `$F7`, a slot byte, a
>   2-byte target — at hook-table entries **$FD9F (H.TIMI, timer), $FDEF, $FDF9,
>   $FFA7, $FFAC**, all with slot byte **$87 = expanded slot 3-1** and targets in
>   the disk ROM's page-1 range. This is the standard MSX cross-slot hook: a
>   plain `JP` (what we install) **cannot cross slots**, so our hooks would only
>   work if slot 3-1 happened to be paged into page 1 at call time.
> - It does **NOT** touch **$FF3E** or **$FF4B** (both still `$C9` after boot).
>   $FF4B is not even 5-byte-aligned in the hook table (`$FF4B − $FD9A = 433`,
>   not ÷5), so our "H.DSKIO = $FF4B" was never a valid hook slot. Our
>   H.PHYD/H.DSKIO addresses are wrong.
> - **$F37D** holds **$31C3** (a BIOS-ROM, page-0 address), not a disk-ROM BDOS
>   entry. The reference does not expose file I/O via an FCB BDOS at a SYSTEM
>   vector in Disk BASIC (that is an MSX-DOS construct); it uses the disk-ROM
>   entry-point table ($4010…) plus the BASIC expansion/CALLF hook chain.
>
> **What is confirmed correct:** the **$4010 entry-point table** (DSKIO etc.)
> reached via an inter-slot call — our DSKIO is byte-identical to the reference
> there (probe 2). **Redesign direction:** because zerobas controls both the
> BASIC ROM and the disk ROM, the simplest robust integration is for
> zerobas-BASIC to locate the disk ROM's slot and call its `$4010` entry table
> (and our FAT12 helpers) via `CALSLT`/`RST 30h`, rather than relying on the
> mis-addressed `JP` hooks + SYSTEM vector. The exact hook names/addresses, if we
> do hook, must be taken from the MSX2 TH hook table (allowed) — not guessed.
> See disk/TODO.md (INIT redesign item).

---

## Drive Parameter Block (DPB) — 720 KB 3.5" drive

MSX2 TH defines the DPB layout that `GETDPB` must fill in. The 720 KB geometry
values follow the FAT12 / ECMA-107 standard for 3.5" DSDD media.

**GETDPB is currently a stub (carry set).** Writing the BPB→DPB computation
requires knowing the exact MSX DPB field encoding, which has two ambiguous
fields (directory mask / directory shift) and one likely-wrong value inherited
from a draft note (total clusters $059E). These are blocked on **oracle probe 2**
(DSKIO sector-read of the boot sector — listed in §Oracle probes). No GETDPB
code will be written until those rows are confirmed or re-sourced from MSX2 TH.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| DPB size | 18 bytes | MSX2 TH, DPB layout | sourced |
| DPB +0: media type byte | $F9 | MSX2 TH (DSDD 3.5" media descriptor); ECMA-107 | sourced |
| DPB +1: sector size (bytes, power-of-2 encoded) | $02 | MSX2 TH DPB layout; interpreted as log2(512/128)=2 (own interpretation — oracle owed) | quarantined |
| DPB +2: directory mask | $0F | MSX2 TH DPB layout; encoding unclear without TH text — own analysis gives $07 for 2 sec/clus, not $0F | **TBD — oracle needed** |
| DPB +3: directory shift | $04 | MSX2 TH DPB layout; inconsistent with 2 sec/clus derivation (gives $05); own analysis gives $04 only for 1 sec/clus | **TBD — oracle needed** |
| DPB +4–5: FAT size (sectors per FAT copy) | $0003 (LE) | MSX2 TH DPB layout; 3 sectors × 512 = 1536 bytes ≥ 713 clusters × 12/8 = 1070 bytes → 3 ✓ | sourced |
| DPB +6: fat_max (FAT copies) | $02 | MSX2 TH DPB layout | sourced |
| DPB +7–8: first dir sector | $0007 (LE) | 1 reserved + 2 × 3 FAT sectors = 7; derivable from BPB | sourced |
| DPB +9–10: first data sector | $000E (LE) | 7 + ceil(112×32/512) = 7+7 = 14; derivable from BPB | sourced |
| DPB +11–12: total clusters | $02C9 (LE) = 713 | (1440−14)/2 = 713 data clusters; own derivation. Draft note had $059E (=1438) which is wrong — 713≠1438 | **quarantined — oracle needed** |
| DPB +13–14: fat_loc (first FAT sector) | $0001 (LE) | sector 1 follows the boot sector; derivable from BPB | sourced |
| DPB +15–16: dir entries | $0070 (LE) = 112 | MSX2 TH DPB layout; ECMA-107 / MS FAT spec | sourced |
| DPB +17: reserved/unused | $00 | MSX2 TH DPB layout | sourced |
| Disk geometry: tracks | 80 | ECMA-107, 3.5" DSDD | sourced |
| Disk geometry: sectors/track | 9 | ECMA-107, 3.5" DSDD | sourced |
| Disk geometry: sides | 2 | ECMA-107, 3.5" DSDD | sourced |
| Sectors per cluster | 2 | ECMA-107 / MS FAT spec for 720 KB; consistent with FAT size = 3 sectors (see +4–5 above) | sourced |
| Total sectors | 1440 (80 × 2 × 9) | derivable from geometry | sourced |

> **DPB value derivation.** Most DPB fields are redundant with the on-disk BPB;
> GETDPB should derive them by reading the BPB from the boot sector and computing
> from it, so the same code works for any FAT12 geometry the BPB describes. The
> fixed constants above are the *expected* values for a 720 KB image and serve
> as oracle-compare targets.

No quarantined items.

---

## FDC driver — WD2793 + CF-3300 register map

### WD2793 register layout (from datasheet)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Status/Command register | +0 (read=status, write=command) | WD2793 DS | sourced |
| Track register | +1 (read/write current track) | WD2793 DS | sourced |
| Sector register | +2 (read/write target sector) | WD2793 DS | sourced |
| Data register | +3 (read/write data byte during transfer) | WD2793 DS | sourced |

### WD2793 status register bits (read)

| Bit | Meaning (Type I) | Meaning (Type II/III) | Source |
|-----|------------------|-----------------------|--------|
| 7 | Not Ready | Not Ready | WD2793 DS |
| 6 | Write Protect | Write Fault | WD2793 DS |
| 5 | Head Loaded | Record Type (0=data, 1=deleted) | WD2793 DS |
| 4 | Seek Error | Record Not Found | WD2793 DS |
| 3 | CRC Error | CRC Error | WD2793 DS |
| 2 | Track 0 | Lost Data | WD2793 DS |
| 1 | Index Pulse | Data Request (DRQ) | WD2793 DS |
| 0 | Busy | Busy | WD2793 DS |

### WD2793 command bytes

| Command | Byte (base) | Type | Source |
|---------|-------------|------|--------|
| Restore (step to track 0) | $00 (+ flag bits) | I | WD2793 DS |
| Seek (go to track in Data reg) | $10 (+ flag bits) | I | WD2793 DS |
| Read Sector | $80 (+ flag bits) | II | WD2793 DS |
| Write Sector | $A0 (+ flag bits) | II | WD2793 DS |
| Force Interrupt | $D0 | IV | WD2793 DS |

### CF-3300 (National connection style) register addresses

> **Source resolved — openMSX `src/fdc/NationalFDC.cc`.** The WD2793 registers
> are memory-mapped into the slot's address space using National Panasonic's
> connection style. openMSX decodes them with `address & 0x3FC7`, giving the
> canonical addresses $7FB8–$7FBC (mirrored across $7F80–$7FBF and into page 2).
> Since zerobas-disk runs from ROM page 1 (slot 3-1, $4000–$7FFF), the driver
> uses the $7FB8 window directly. openMSX is an allowed source for hardware
> register addresses and port maps (see [`README.md`](../README.md) / source list).

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Status/Command register (read=status, write=command) | $7FB8 | openMSX `NationalFDC.cc` (`0x3F80` → `getStatusReg`/`setCommandReg`) | sourced |
| Track register | $7FB9 | openMSX `NationalFDC.cc` (`0x3F81` → `get/setTrackReg`) | sourced |
| Sector register | $7FBA | openMSX `NationalFDC.cc` (`0x3F82` → `get/setSectorReg`) | sourced |
| Data register | $7FBB | openMSX `NationalFDC.cc` (`0x3F83` → `get/setDataReg`) | sourced |
| Drive/side/motor latch (write) + IRQ/DRQ status (read) | $7FBC | openMSX `NationalFDC.cc` (`0x3F84`–`0x3F87`) | sourced |
| Drive-select bit: drive A | latch bit 0 ($01) | openMSX `NationalFDC.cc` writeMem (`value & 3 == 1` → Drive::A) | sourced |
| Drive-select bit: drive B | latch bit 1 ($02) | openMSX `NationalFDC.cc` writeMem (`value & 3 == 2` → Drive::B) | sourced |
| Side-select bit | latch bit 2 ($04) | openMSX `NationalFDC.cc` writeMem (`value & 0x04` → setSide) | sourced |
| Motor-on bit | latch bit 3 ($08) | openMSX `NationalFDC.cc` writeMem (`value & 0x08` → setMotor) | sourced |
| Status-read at $7FBC: INTRQ | bit 7 ($80) | openMSX `NationalFDC.cc` readMem (`getIRQ` → bit 7) | sourced |
| Status-read at $7FBC: DRQ (active-low) | bit 6 ($40), 0 = DRQ active | openMSX `NationalFDC.cc` readMem (`getDTRQ` → clears bit 6) | sourced |
| DRQ/BUSY polling model | poll WD2793 status reg ($7FB8): bit 1 = DRQ, bit 0 = BUSY | WD2793 DS (status register, Type II); IRQ/DRQ lines not wired to Z80 INT per `NationalFDC.cc` comment | sourced |

> **Driver polls the status register, not the $7FBC IRQ/DRQ latch.** openMSX's
> `NationalFDC.cc` notes the IRQ/DRQ lines are *not* connected to the Z80
> interrupt request, so the driver runs fully polled: it reads the WD2793 status
> register at $7FB8 and tests bit 1 (DRQ) and bit 0 (BUSY). This is the standard
> WD179x polled-transfer model from the datasheet and needs no machine-specific
> $7FBC reads.

> **A note on the stale "Philips/NMS" wording in `TODO.md`.** The FDC TODO bullet
> still says "Philips/NMS-style port addresses" from before the CF-3300 reference
> was chosen. The reference machine and this provenance section are National
> connection style (memory-mapped, not I/O-port); the implementation follows the
> CF-3300/National map above.

### WD2793 command flag bits (datasheet)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Type I head-load flag (h) | bit 3 ($08) | WD2793 DS; openMSX `WD2793.cc` `H_FLAG` | sourced |
| Type I verify flag (V) | bit 2 ($04) | WD2793 DS; openMSX `WD2793.cc` `V_FLAG` | sourced |
| Type I step-rate bits | bits 1-0 ($03), 00 = 6 ms @1 MHz | WD2793 DS; openMSX `WD2793.cc` `STEP_SPEED` + `timePerStep` | sourced |
| Restore command (calibrate to track 0) | $0C ($00 + h + V, rate 0) | WD2793 DS command table | sourced |
| Seek command (to track in Data reg) | $1C ($10 + h + V, rate 0) | WD2793 DS command table | sourced |
| Read Sector command (single record) | $80 | WD2793 DS command table | sourced |
| Force Interrupt | $D0 | WD2793 DS command table | sourced |
| WD2793 reset → Track register = 0 | — | openMSX `WD2793.cc` `reset()` (`trackReg = 0`); informs the restore-on-retry recovery | sourced |

### Logical-sector → physical CHS mapping (720 KB)

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| sectors per track | 9 | ECMA-107 / MS FAT spec (BPB) | sourced |
| sides | 2 | ECMA-107 | sourced |
| sector number = (LBA mod 9) + 1 | 1..9 | ECMA-107 CHS layout; standard LBA→CHS | sourced |
| head/side = (LBA / 9) mod 2 | 0/1 | ECMA-107 CHS layout | sourced |
| track = LBA / 18 | 0..79 | ECMA-107 CHS layout | sourced |

### DSKIO register interface and error codes

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| DSKIO input: A=drive, B=#sectors, C=media, DE=start logical sector, HL=buffer | — | MSX2 TH, disk ROM interface (DSKIO) | sourced |
| DSKIO direction: carry reset = read, carry set = write | — | MSX2 TH, disk ROM interface (DSKIO) | sourced |
| DSKIO output: carry set = error, A = error code, B = sectors not transferred | — | MSX2 TH, disk ROM interface (DSKIO) | sourced |
| Error code: write protected | 0 | MSX2 TH, DSKIO error codes | sourced |
| Error code: not ready | 2 | MSX2 TH, DSKIO error codes | sourced |
| Error code: data (CRC) error | 4 | MSX2 TH, DSKIO error codes | sourced |
| Error code: record not found | 8 | MSX2 TH, DSKIO error codes | sourced |
| Error code: other (lost data, etc.) | 12 | MSX2 TH, DSKIO error codes | sourced |
| WD2793 status → DSKIO error mapping (NOTRDY→2, RNF→8, CRC→4, LOST→12) | — | own mapping; WD2793 DS status bits ↔ MSX2 TH error codes | sourced |
| Restore-on-error retry (one retry: restore + reseek + reread) | — | own design; recovers a stale Track register after reset (see WD2793 reset row) | sourced |

> **Single-drive simplification.** The CF-3300 declares `<drives>1</drives>`; the
> driver always selects drive A (latch bit 0) and ignores the DSKIO drive number
> and media-descriptor byte. Write support is deferred: a DSKIO write request
> returns error code 0 (write protected).

> **FDC registers shadow ROM offsets $3FB8–$3FBF.** Because the WD2793 device
> intercepts reads at $7FB8–$7FBF (ROM offsets $3FB8–$3FBF), those bytes of the
> ROM image are not readable as code/data. They fall inside the zero-padding
> region of this 16 KB ROM, so nothing important is placed there.

No quarantined items.

---

## FAT12 layer

### Boot sector / BPB

| Item | Offset in boot sector | Source (allowed) | Status |
|------|-----------------------|------------------|--------|
| Bytes per sector | +11–12 (LE) | Microsoft FAT spec §3.1; ECMA-107 | sourced |
| Sectors per cluster | +13 | Microsoft FAT spec §3.1 | sourced |
| Reserved sectors (incl. boot sector) | +14–15 (LE) | Microsoft FAT spec §3.1 | sourced |
| Number of FATs | +16 | Microsoft FAT spec §3.1 | sourced |
| Max root directory entries | +17–18 (LE) | Microsoft FAT spec §3.1 | sourced |
| Total sectors (16-bit) | +19–20 (LE) | Microsoft FAT spec §3.1 | sourced |
| Media type byte | +21 | Microsoft FAT spec §3.1; ECMA-107 | sourced |
| Sectors per FAT | +22–23 (LE) | Microsoft FAT spec §3.1 | sourced |
| Sectors per track | +24–25 (LE) | Microsoft FAT spec §3.1; ECMA-107 | sourced |
| Number of heads (sides) | +26–27 (LE) | Microsoft FAT spec §3.1; ECMA-107 | sourced |
| Boot sector location | track 0, side 0, sector 1 | ECMA-107 | sourced |

### FAT12 cluster chain

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Cluster 0 entry | media descriptor byte | Microsoft FAT spec §3.2 | sourced |
| Cluster 1 entry | $FFF (end-of-chain) | Microsoft FAT spec §3.2 | sourced |
| First data cluster | 2 | Microsoft FAT spec §3.2 | sourced |
| End-of-chain marker | $FF8–$FFF | Microsoft FAT spec §3.2 | sourced |
| Free cluster marker | $000 | Microsoft FAT spec §3.2 | sourced |
| 12-bit packing: even cluster k | bytes[k*3/2] and low nibble of bytes[k*3/2+1] | Microsoft FAT spec §3.2 | sourced |
| 12-bit packing: odd cluster k | high nibble of bytes[k*3/2] and bytes[k*3/2+1] | Microsoft FAT spec §3.2 | sourced |
| First data sector | reserved_sectors + FAT_count × sectors_per_FAT + ceil(max_dir_entries × 32 / bytes_per_sector) | Microsoft FAT spec §3.3 | sourced |
| Data sector for cluster N | first_data_sector + (N − 2) × sectors_per_cluster | Microsoft FAT spec §3.3 | sourced |

### Root directory entries

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Directory entry size | 32 bytes | Microsoft FAT spec §3.4 | sourced |
| Filename | +0–7 (8 chars, space-padded, uppercase) | Microsoft FAT spec §3.4 | sourced |
| Extension | +8–10 (3 chars, space-padded, uppercase) | Microsoft FAT spec §3.4 | sourced |
| Attributes byte | +11 | Microsoft FAT spec §3.4 | sourced |
| First cluster (low 16 bits) | +26–27 (LE) | Microsoft FAT spec §3.4 | sourced |
| File size (bytes) | +28–31 (LE) | Microsoft FAT spec §3.4 | sourced |
| Deleted entry marker | $E5 at offset 0 | Microsoft FAT spec §3.4 | sourced |
| End-of-directory marker | $00 at offset 0 | Microsoft FAT spec §3.4 | sourced |
| Filename comparison | case-insensitive, space-padding ignored, 8.3 split | Microsoft FAT spec §3.4; own code | sourced |
| Volume-label / subdirectory entries skipped in search | attribute bits $08 / $10 | Microsoft FAT spec §3.4 (attribute byte); own search policy | sourced |

> **Implementation note.** This whole section is now realised in `disk/disk.asm`
> (`fat_mount`, `fat_find` / `name_cmp`, `fat_next_cluster`, `fat_open`,
> `fat_read_file_sector`). Every value above is read from the on-disk BPB / FAT /
> directory at run time — none is hard-coded — so the rows are format
> definitions, not magic constants in the binary. The single straddle case in
> the 12-bit FAT entry (an entry split across a 512-byte sector boundary) is
> handled by reading the following FAT sector for the high byte. A FAT read
> error during chain-walk is not separately reported; it yields a bogus link
> that the end-of-chain test (`>= $0FF8`) treats as EOF.

No quarantined items.

---

## BDOS interface

The disk ROM provides a BDOS-compatible file-access interface callable from
zerobas's `BLOAD` handler. In MSX-BASIC-with-disk (Disk BASIC, **not** MSX-DOS),
the disk ROM's `INIT` installs a BDOS entry point via the `SYSTEM` system
variable; zerobas calls through that vector using CP/M-compatible FCB calls.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| SYSTEM sysvar (BDOS jump target) | $F37D | MSX2 TH, work area; C-BIOS `systemvars.asm` | sourced |
| BDOS calling convention: call number in C, FCB pointer in DE | — | MSX2 TH, MSX-DOS spec; mirrors CP/M BDOS | sourced |
| FCB Open call number | $0F | MSX2 TH, MSX-DOS BDOS call table | sourced |
| FCB Close call number | $10 | MSX2 TH, MSX-DOS BDOS call table | sourced |
| FCB Sequential Read call number | $14 | MSX2 TH, MSX-DOS BDOS call table | sourced |
| Set DTA Address call number (DE = new DTA) | $1A | MSX2 TH, MSX-DOS BDOS call table | sourced |
| BDOS return value on success | A = $00 | MSX2 TH, BDOS call conventions | sourced |
| BDOS return value on error | A = $FF (Open) / $01 (SeqRead end-of-file) | MSX2 TH, BDOS call conventions | sourced |
| Dispatcher: switch on call number in C, A=$FF for unsupported calls | — | own code; call-number-in-C convention sourced above | sourced |
| Open: FCB+1..+11 name → `fat_find`; map found/not-found to A=$00/$FF | — | own code composing the FAT12 layer; FCB name offset + return values sourced above | sourced |
| Sequential Read: deliver SECTOR_BUF in 128-byte records to the **settable** DTA (`BDOS_DTA`), refill via `fat_read_file_sector` at record 4 | — | own code; 128-byte record sourced above; settable DTA via $1A sourced below | sourced |
| Set DTA ($1A): store DE into `BDOS_DTA`; subsequent SeqReads copy to it | — | own code; $1A call number + DE=DTA convention sourced (MSX2 TH / MSX-DOS) | sourced |
| `BDOS_DTA` default | $0080 | MSX2 TH, BDOS conventions (MSX-DOS default); INIT seeds it | sourced |
| Records per sector = 512 / 128 = 4 | $04 | own derivation (sector size ÷ record size) | sourced |
| Open → 17× SeqRead → Close delivers byte-identical records + return codes vs real MSX-DOS 1.03 | — | **NARROW differential oracle PASS** (`disk_probe_bdos.py`, msx-preservation): same `ORACLE.BIN` read on MSX-DOS and on our `bdos_entry` via CALSLT — Open/records/EOF/Close all byte-identical | oracle-confirmed |
| Single open file: position in FAT iterator + BDOS_RECIDX, FCB extent (+12) / current-record (+32) fields unused | — | own design simplification (read-only loader subset); NOT differenced by the narrow oracle — the FULL FCB-field differential is a tracked follow-up | quarantined |
| SeqRead EOF granularity = cluster-chain end (last record may pad past FAT_FILESIZE) | — | own design; CP/M record semantics. The narrow oracle uses an exact-cluster-multiple file so EOF lands clean and this is not exercised; exact sub-record byte-bounding is the FULL-differential follow-up | quarantined |
| Register save/restore contract for the BLOAD→BDOS call | — | the Open/SeqRead/Close round-trip is now exercised by `disk_probe_bdos.py` (CALSLT in, A out); exact non-A register preservation across CALSLT still not textually sourced | quarantined |

### FCB layout

| Item | Offset | Source (allowed) | Status |
|------|--------|------------------|--------|
| Drive number (0=default, 1=A, 2=B) | +0 | MSX2 TH, FCB layout; CP/M standard (public) | sourced |
| Filename (8 chars, space-padded, uppercase) | +1–8 | MSX2 TH, FCB layout | sourced |
| Extension (3 chars, space-padded, uppercase) | +9–11 | MSX2 TH, FCB layout | sourced |
| Extent number | +12 | MSX2 TH, FCB layout | sourced |
| Reserved (S1, S2) | +13–14 | MSX2 TH, FCB layout | sourced |
| Record count in current extent | +15 | MSX2 TH, FCB layout | sourced |
| Allocation map | +16–31 | MSX2 TH, FCB layout | sourced |
| Current sequential record | +32 | MSX2 TH, FCB layout | sourced |
| FCB size | 36 bytes (standard FCB + random record field) | MSX2 TH, FCB layout | sourced |
| Disk Transfer Area (DTA) default location | $0080 in page 0 | MSX2 TH, BDOS conventions | sourced |
| Sequential read block size | 128 bytes per record | MSX2 TH, FCB sequential I/O | sourced |

> **Disk BASIC vs MSX-DOS distinction.** zerobas is a Disk-BASIC-style ROM, not
> an MSX-DOS host. The BDOS interface above is the Disk BASIC FCB subset that
> MSX2 TH documents as available when a disk ROM is present in slot 3-1.
> MSX-DOS extensions (drive mapping, error codes beyond the basic set) are out
> of scope. The oracle probes will confirm which subset the CF-3300 reference
> exposes.

> **Calling convention quarantine (now actioned).** The dispatcher
> (`bdos_entry`) is implemented and reads the call number from C and the FCB
> pointer from DE (sourced). The remaining unsourced piece — the exact register
> save/restore contract the zerobas BLOAD caller must honour around the vector —
> is filed `quarantined` in the table above, pending oracle probe 3 (BDOS FCB
> round-trip). The DTA defaults to the documented $0080 but is now **settable**
> via BDOS $1A: under the combined Disk-BASIC machine page 0 is BIOS ROM, so a
> SeqRead to $0080 silently fails — the BLOAD path issues $1A first to point the
> DTA at a writable page-3 buffer it controls (see disk BLOAD execute in
> basic/PROVENANCE.md). Confirmed end-to-end by `disk_probe_bload_disk.py`.

> **Implementation note.** Realised in `disk/disk.asm` as `bdos_entry` plus
> `bdos_open` / `bdos_seqread` / `bdos_close`, on top of the FAT12 helpers
> (`fat_mount` / `fat_find` / `fat_open` / `fat_read_file_sector`). Open mounts
> the BPB and searches the root directory for the FCB's 11-byte 8.3 name; the
> sequential reader slices the 512-byte sector buffer into four 128-byte records
> into the DTA, refilling from the cluster chain on exhaustion; Close is a no-op
> success (read-only). The two `quarantined` rows above (single-open-file
> position model, cluster-chain EOF granularity) are documented simplifications,
> not copied behaviour. End-to-end validation waits on the openMSX machine
> config + a test `.dsk` + oracle probe 3.

---

## Scratch RAM

zerobas-disk must not collide with zerobas-core's scratch RAM ($E020–$E25F) or
with any system-reserved area. The disk scratch window is chosen from free page-3
RAM outside known regions.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Candidate disk scratch origin | $E260 (first free byte after zerobas-core VARTAB end $E23F + gap) | own choice (free page-3 RAM; no collision with zerobas-core or system sysvars) | sourced |
| FCB work area | $E260–$E287 (36 bytes for FCB) | own choice | sourced |
| DPB work area | $E288–$E299 (18 bytes for DPB copy) | own choice | sourced |
| FDC driver state | $E29A–$E29F (6 bytes) | own choice (gap between DPB and sector buffer) | sourced |
| — remaining sector count | $E29A (1 byte) | own choice | sourced |
| — current logical sector | $E29B–$E29C (word) | own choice | sourced |
| — current transfer address | $E29D–$E29E (word) | own choice | sourced |
| — read attempt counter | $E29F (1 byte) | own choice | sourced |
| Sector buffer (512 bytes) | $E2A0–$E49F | own choice (free page-3 RAM) | sourced |
| FAT12 geometry + iterator state | $E4A0–$E4B1 (18 bytes) | own choice (free page-3 RAM after the sector buffer) | sourced |
| — sectors per cluster | $E4A0 (1 byte) | own choice | sourced |
| — first FAT sector | $E4A1–$E4A2 (word) | own choice | sourced |
| — first root-dir sector | $E4A3–$E4A4 (word) | own choice | sourced |
| — root-dir sector count | $E4A5–$E4A6 (word) | own choice | sourced |
| — first data sector | $E4A7–$E4A8 (word) | own choice | sourced |
| — current cluster (open file) | $E4A9–$E4AA (word) | own choice | sourced |
| — sector index within cluster | $E4AB (1 byte) | own choice | sourced |
| — found file first cluster | $E4AC–$E4AD (word) | own choice | sourced |
| — found file size (bytes) | $E4AE–$E4B1 (4 bytes) | own choice | sourced |
| FAT12 transient work vars | $E4B2–$E4BE (13 bytes) | own choice (parity, byte-index, FAT sector, two FAT bytes, name pointer, dir-scan cursor + remaining) | sourced |
| BDOS sequential-read record index | $E4BF (1 byte) | own choice (free page-3 RAM after FAT scratch; next 128-byte record within SECTOR_BUF, 0..4) | sourced |
| BDOS settable DTA pointer (`BDOS_DTA`) | $E4C0–$E4C1 (word) | own choice (free page-3 RAM after the record index); default $0080, set via BDOS $1A | sourced |

> **FAT12 geometry is derived, not stored as constants.** `fat_mount` reads the
> boot sector and computes the first-FAT / first-root / root-sector-count /
> first-data sector numbers from the on-disk BPB (Microsoft FAT spec §3.1/§3.3),
> validating only that the sector size is 512 bytes (so the 512-byte
> `SECTOR_BUF` is always large enough). No geometry is hard-coded, so the layer
> serves any FAT12 image the BPB describes; the 720 KB DPB values elsewhere in
> this document are oracle-compare targets, not inputs to this code.

> These addresses are provisional. Before finalising, verify against both
> zerobas-core's RAM map (PROVENANCE.md §RAM additions) and the C-BIOS system
> variable table to confirm the window is free *at rest* — and against oracle
> probe #3's disturbed-RAM footprint to confirm it is also free *during a disk
> call*. The window is own-choice; the probes only rule out collisions, they do
> not dictate the layout.

---

## Oracle probes owed

Before any code section is declared complete, the following black-box probes
must be run against the CF-3300 in openMSX and added to `msx-preservation`:

1. **FDC register map probe** — ~~confirm the CF-3300 WD2793 base address and
   drive-select latch by writing known patterns and reading status~~ **Resolved
   from an allowed source:** the register addresses and the drive/side/motor
   latch bit map are taken directly from openMSX `src/fdc/NationalFDC.cc`
   (allowed for hardware register maps). **Runtime-confirmed:** probe 2 below now
   reads real sectors through this register map on openMSX, so the map is
   exercised, not just sourced.
2. **DSKIO sector read** — read sector 0 (boot sector) and confirm BPB fields
   match the known test image; validates FAT12 and FDC layers together.
   **DONE — differential oracle PASS.** `disk-spec/tools/disk_probe_dskio.py`
   (in the `msx-preservation` repo) reads the same `disk/test720.dsk` on the real
   National CF-3300 reference and on our `*_BASIC_DISK` machine by calling the
   standard DSKIO entry ($4010, MSX2 TH) via `CALSLT`, and compares the returned
   bytes + carry/A. Result: zerobas-disk's DSKIO is **byte-identical to the
   CF-3300 reference** (sector 0 and sector 14; both `A=0, Cy=0`, both equal to
   the on-disk bytes). Strictly black-box: only returned data + flags observed,
   the reference disk ROM's code was never read. (A prior functional self-test
   via the FAT12 helpers — `fat_mount`/`fat_find`/`fat_read_file_sector` — also
   passed: geometry derived, file found, records correct across a cluster hop,
   clean EOF.)
3. **BDOS FCB round-trip** — open a known file via FCB, read its first 128-byte
   record, close it; confirms BDOS calling convention and DTA contents. **Also
   capture the disturbed-RAM footprint:** dump page-3 (and page-0 around the DTA)
   before and after the call; the delta is the RAM the BIOS/BDOS call path
   clobbers on its own (DTA, sector buffer, stack growth, disk bookkeeping
   sysvars). zerobas-disk's scratch window must sit clear of that footprint —
   addresses that look "free" at rest can still be trashed mid-call, which a
   static sysvar-map check would miss. (We pick our *own* scratch addresses, so
   this is collision-avoidance, not a layout to copy.)
   **Reframed twice.** First: the CF-3300 *reference disk ROM* has no FCB BDOS —
   probe-3 investigation (observing CF-3300 RAM only) found it runs Disk BASIC,
   which exposes no CP/M FCB BDOS ($F37D points into BIOS ROM, $0005 is not a BDOS
   entry, page 0 is ROM; file I/O goes through the disk-ROM entry table + BASIC
   expansion/CALLF hooks). The FCB BDOS ($0005 / $0080 DTA / FCB) is an **MSX-DOS**
   construct, available only once MSX-DOS is loaded (page 0 = RAM). Second, and the
   current state: the right reference for the FCB layer is therefore **real
   MSX-DOS 1**, not the CF-3300 disk ROM — and that differential now **exists and
   passes** (`disk_probe_bdos.py`, msx-preservation). It reads the same `ORACLE.BIN`
   through Open → 17× SeqRead → Close on real MSX-DOS 1.03 (booted on
   `National_CF-3300` from a DOS system disk, the `.COM` auto-run via AUTOEXEC.BAT)
   and on our `bdos_entry` (via CALSLT), and the Open result, all 16 records, the
   EOF code, and the Close result are **byte-identical** — a passed NARROW
   differential (scope caveat: cluster-multiple file, no FCB-field/sub-record-EOF
   diff; the full differential is a tracked follow-up). The FAT12 read path
   underneath is independently differential-confirmed via probe 2. Probe 4
   (BLOAD end-to-end) remains the *interpreter-glue* check, where the meaningful
   comparison is the loaded file content + exec handoff. Two design
   findings folded in elsewhere: (a) the disk ROM INIT does not run in the
   combined `*_BASIC_DISK` machine (boot-scan ordering); (b) the $0080 DTA assumes
   page-0 RAM, invalid under Disk BASIC — the BLOAD path must supply its own
   buffer.
4. **BLOAD"A:file",R end-to-end** — load a BSAVE binary from disk and confirm
   the BSAVE header parse + load-into-RAM + jump-to-exec path matches the
   cassette path's oracle spec.

> **Functional vs differential.** Probe 2 (DSKIO sector read) is now a *passed
> differential oracle* against the real CF-3300 (see above). The remaining
> validations (BDOS FCB round-trip, BLOAD end-to-end) are so far *functional*
> self-tests on openMSX (our ROM + our `disk/test720.dsk`, built by
> `tools/make_test_dsk.py` from the Microsoft FAT spec + ECMA-107 — allowed
> sources, no disk-ROM bytes); their *differential* counterparts vs the CF-3300
> reference are still owed. All reference use is strictly black-box (observed
> outputs only); the CF-3300 disk ROM is never read or disassembled.

---

## Audit

Before release, every constant and address in `disk/disk.asm` must map to a
`sourced` row above, be `quarantined` with a round-trip justification, or have
an oracle probe confirming the value. The TBD rows in the FDC section are a
**hard blocker** on writing that code.
