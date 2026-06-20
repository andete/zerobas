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
| INIT vector (JP) | 3 bytes at $4003 | MSX2 TH, cartridge ROM format (same field as main zerobas ROM) | sourced |
| Reserved header bytes | $4006–$400F = $00 | MSX2 TH, cartridge ROM format | sourced |
| Disk entry-point table base | $4010 | MSX2 TH, disk ROM interface | sourced |
| DSKIO entry | JP at $4010 | MSX2 TH, disk ROM interface (offset +$10 from ROM base) | sourced |
| DSKCHG entry | JP at $4013 | MSX2 TH, disk ROM interface (offset +$13) | sourced |
| GETDPB entry | JP at $4016 | MSX2 TH, disk ROM interface (offset +$16) | sourced |
| CHOICE entry | JP at $4019 | MSX2 TH, disk ROM interface (offset +$19) | sourced |
| DSKFMT entry | JP at $401C | MSX2 TH, disk ROM interface (offset +$1C) | sourced |
| MTOFF entry | JP at $401F | MSX2 TH, disk ROM interface (offset +$1F) | sourced |

No quarantined items.

---

## INIT: system hook installation

The disk ROM's INIT routine (called by BIOS at boot) installs JP instructions
into the system hook slots. The hook area is 5-byte slots in page-3 RAM; the
BIOS initialises each to `RST $30` (5 bytes = `$FF $FF $FF $FF $FF` or a formal
no-op sequence); INIT overwrites with `JP nnnn` ($C3 + 2-byte address) + 2 padding
bytes.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| H.DSKIO hook address | $FF4B | MSX2 TH, work area / hook table | sourced |
| H.PHYD hook address | $FF3E | MSX2 TH, work area / hook table | sourced |
| Hook slot size | 5 bytes | MSX2 TH (all H.* hooks are 5-byte; called with `CALL` so they may also `RET`) | sourced |
| `JP nnnn` opcode | $C3 | Z80 instruction set (public) | sourced |
| INIT calls BIOS to identify slot self | — | MSX2 TH RDSLT/CALSLT protocol; own code | sourced |

> **H.PHYD vs H.DSKIO.** MSX2 TH distinguishes two disk-I/O hooks:
> `H.PHYD` ($FF3E) intercepts the BIOS PHYDIO entry (physical sector I/O at the
> BIOS level), and `H.DSKIO` ($FF4B) intercepts the disk-BASIC DSKIO call
> (logical I/O from file-access code). Both are installed by INIT; the FDC
> driver lives behind `H.PHYD`.

No quarantined items.

---

## Drive Parameter Block (DPB) — 720 KB 3.5" drive

MSX2 TH defines the DPB layout that `GETDPB` must fill in. The 720 KB geometry
values follow the FAT12 / ECMA-107 standard for 3.5" DSDD media.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| DPB size | 18 bytes | MSX2 TH, DPB layout | sourced |
| DPB +0: media type byte | $F9 | MSX2 TH (DSDD 3.5" media descriptor); ECMA-107 | sourced |
| DPB +1: sector size (bytes, power-of-2 encoded) | $02 (= 512) | MSX2 TH DPB layout | sourced |
| DPB +2: directory mask | $0F (= cluster_size − 1, 1 sector/cluster) | MSX2 TH DPB layout | sourced |
| DPB +3: directory shift | $04 (= log2(sectors_per_cluster) + log2(512/32)) | MSX2 TH DPB layout | sourced |
| DPB +4–5: FAT size (sectors per FAT copy) | $03 (3 sectors) | MSX2 TH DPB layout; FAT12 for 720 KB = 3 sectors | sourced |
| DPB +6: fat_max (last usable FAT sector entry) | $02 (2 FAT copies) | MSX2 TH DPB layout | sourced |
| DPB +7–8: first dir sector | $07 (= 1 reserved + 2 × 3 FAT sectors) | MSX2 TH DPB layout; derivable from BPB | sourced |
| DPB +9–10: first data sector | $0E (= first_dir + 112×32/512 = 7+7) | MSX2 TH DPB layout; derivable from BPB | sourced |
| DPB +11–12: total clusters (max cluster − 1) | $059E (= 713, total data clusters − 1) | MSX2 TH DPB layout; 720 KB geometry | sourced |
| DPB +13–14: fat_loc (first FAT sector) | $0001 | MSX2 TH DPB layout; always sector 1 for FAT12 | sourced |
| DPB +15–16: dir entries | $0070 (= 112) | MSX2 TH DPB layout; ECMA-107 / MS FAT spec | sourced |
| DPB +17: reserved/unused | $00 | MSX2 TH DPB layout | sourced |
| Disk geometry: tracks | 80 | ECMA-107, 3.5" DSDD | sourced |
| Disk geometry: sectors/track | 9 | ECMA-107, 3.5" DSDD | sourced |
| Disk geometry: sides | 2 | ECMA-107, 3.5" DSDD | sourced |
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

> **Source gap — TBD.** The WD2793 registers are memory-mapped into the slot's
> address space on the CF-3300 using National Panasonic's connection style. The
> exact base address within the $4000–$BFFF window must come from an open
> hardware source (CF-3300 schematics or openMSX source code). These addresses
> are **not yet sourced**; no FDC driver code will be written until this row is
> filled in.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| FDC register base address (memory-mapped) | TBD | CF-3300 schematic or openMSX source (GPL) | **TBD** |
| Drive-select / side-select latch address | TBD | CF-3300 schematic or openMSX source (GPL) | **TBD** |
| Drive-select bit assignment (drive A / B) | TBD | CF-3300 schematic or openMSX source (GPL) | **TBD** |
| Side-select bit assignment (side 0 / 1) | TBD | CF-3300 schematic or openMSX source (GPL) | **TBD** |
| Motor-on bit / latch | TBD | CF-3300 schematic or openMSX source (GPL) | **TBD** |
| Interrupt / DRQ polling vs interrupt line | TBD | CF-3300 schematic or openMSX source (GPL) | **TBD** |

> Until the TBD rows above are resolved from an open source, the FDC driver
> section of the code cannot be written. The oracle probe that reads / writes a
> sector will serve as the round-trip validation once addresses are in.

No quarantined items yet (pending TBD resolution).

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
| BDOS return value on success | A = $00 | MSX2 TH, BDOS call conventions | sourced |
| BDOS return value on error | A = $FF (Open) / $01 (SeqRead end-of-file) | MSX2 TH, BDOS call conventions | sourced |

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

> **Calling convention quarantine (potential).** The exact register state the
> zerobas BLOAD caller must set up before invoking the BDOS vector (DMA address,
> register save/restore contract) will be oracle-confirmed before code is written.
> Rows that turn out to have no independent textual source will be re-filed as
> quarantined with a round-trip justification.

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
| Sector buffer (512 bytes) | $E2A0–$E4A0 | own choice (free page-3 RAM) | sourced |

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

1. **FDC register map probe** — confirm the CF-3300 WD2793 base address and
   drive-select latch by writing known patterns and reading status; fills in
   the TBD rows in the FDC section.
2. **DSKIO sector read** — read sector 0 (boot sector) and confirm BPB fields
   match the known test image; validates FAT12 and FDC layers together.
3. **BDOS FCB round-trip** — open a known file via FCB, read its first 128-byte
   record, close it; confirms BDOS calling convention and DTA contents. **Also
   capture the disturbed-RAM footprint:** dump page-3 (and page-0 around the DTA)
   before and after the call; the delta is the RAM the BIOS/BDOS call path
   clobbers on its own (DTA, sector buffer, stack growth, disk bookkeeping
   sysvars). zerobas-disk's scratch window must sit clear of that footprint —
   addresses that look "free" at rest can still be trashed mid-call, which a
   static sysvar-map check would miss. (We pick our *own* scratch addresses, so
   this is collision-avoidance, not a layout to copy.)
4. **BLOAD"A:file",R end-to-end** — load a BSAVE binary from disk and confirm
   the BSAVE header parse + load-into-RAM + jump-to-exec path matches the
   cassette path's oracle spec.

---

## Audit

Before release, every constant and address in `disk/disk.asm` must map to a
`sourced` row above, be `quarantined` with a round-trip justification, or have
an oracle probe confirming the value. The TBD rows in the FDC section are a
**hard blocker** on writing that code.
