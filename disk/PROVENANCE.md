# Provenance log — zerobas-disk

Every constant, address, data table, and algorithm in zerobas-disk must appear
here with an independent **allowed** source, or be explicitly **quarantined**.
An unexplained magic value blocks release.

- **sourced** — traced to an allowed source (see [`README.md`](../README.md) for
  the list) or to this project's own black-box **oracle observation**.
- **quarantined** — no copied source; derived from the documented format or spec
  and justified by oracle round-trip (or an original algorithm of ours). **Never**
  lifted from a reference ROM or any disk-ROM/MSX-BASIC disassembly.

Allowed sources (the canonical master list + the governing test live in
[`../README.md`](../README.md); each entry below names *what may be taken from it,
and only that*):
- **MSX2 TH** — MSX2 Technical Handbook (Konamiman's English translation, public);
  documented disk-ROM / BDOS *interfaces* (entry addresses, calling conventions,
  work-area layouts) — never reproduced ROM code.
- **MB8877A DS** — Fujitsu MB8877A FDC datasheet (public); the CF-3300's **actual**
  FDC and the **primary** for the FDC register / command / timing interface.
- **WD2793 DS** — WD2793 FDC datasheet (Western Digital, public); the WD179x-family
  **compatible-family** reference the driver was first written against. The MB8877A
  is WD179x-compatible, so its command/status register interface is **identical** —
  every "WD2793 DS" citation below applies verbatim to the MB8877A (and is
  oracle-validated byte-identical to the real CF-3300). openMSX also models the
  CF-3300 FDC under its `<WD2793>` device name.
- **CF-3300 schematic** — open hardware schematic for the National CF-3300; FDC
  wiring / register-window *hardware facts* only. (Exact document still to be
  pinned — see FDC section; until pinned, every register address is cross-checked
  against openMSX + the WD2793 datasheet + oracle.)
- **openMSX source** — openMSX emulator C++ source (GPL); hardware register
  addresses / port maps **only** — facts, never code (GPL stays out of this 0BSD
  tree).
- **Microsoft FAT spec** — Microsoft FAT Filesystem Specification (public);
  FAT12 structures.
- **ECMA-107** — ECMA-107 standard; 3.5" disk geometry.
- **MSX Assembly Page** — MSX Assembly Page BIOS/sysvar reference (public web); the
  *standard* interface it consolidates (corroborate internals against the TH).
- **komkon docs** — `fms.komkon.org/MSX/Docs/` hook / sysvar *address tables*
  (facts) — not RE-derived routine-behaviour text.
- **Nextor Driver Development Guide** — the documented DPB / driver *interface
  contract* only — never Nextor code.
- **C-BIOS** — C-BIOS source (BSD 2-clause); system-variable *addresses* / facts
  (don't copy code/expression without BSD-2 attribution).
- **oracle** — this project's own black-box observation of a real MSX (inputs in,
  outputs out; never reading the reference ROM or any proprietary binary).
- **own design** — algorithm or constant chosen by this project.

NOT allowed (see README): the MSX Wiki / MSX Resource Center and other community
reverse-engineering compilations, and the bytes of any proprietary binary
(reference ROM, MSXDOS.SYS, COMMAND.COM) read as anything but an oracle.

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

## INIT: HPHYD hook install + BDOS entry publication (resolved design)

The disk ROM's INIT routine (called by the boot scan) now does **two** things:

1. **Installs the standard `HPHYD ($FFA7) → DSKIO ($4010)` inter-slot hook** (the
   Phase-1.5 PROVIDER surface), so a real MSX-BASIC / MSX-DOS host that issues
   PHYDIO reaches our sector engine.
2. **Publishes the BDOS entry point** via the SYSTEM ($F37D) sysvar and seeds the
   default DTA (the INTERNAL path zerobas-BASIC drives), then returns.

> **History.** An earlier draft installed `JP phyd_handler`/`JP dskio` into hook
> slots at $FF3E/$FF4B — that code was **removed as oracle-contradicted dead
> code** (the inner box below). The HPHYD install added now is the *correct*
> idiom (RST 30h / CALLF inter-slot patch at the *right* hook address $FFA7),
> matching the National CF-3300 reference's observed integration.

### HPHYD hook install (provider direction)

The 5 hook bytes written at `$FFA7` are an inter-slot `CALLF`:

```
HPHYD ($FFA7): F7 87 10 40 C9   ; RST 30h ; slot $87 (3-1) ; addr $4010 ; RET
```

i.e. `RST 30h` (=`$F7`=CALLF, the BIOS inter-slot-call restart) + slot byte +
2-byte target + `RET`. The target is **our own DSKIO entry ($4010)**; the slot
byte is **this ROM's own slot**. A plain `JP` cannot be used (it cannot cross
slots). Confirmed by black-box readout: after INIT on every
`C-BIOS_MSX1_*_BASIC_DISK` machine, `$FFA7..$FFAB` = `F7 87 10 40 C9`.

**Obtaining this ROM's own slot byte at INIT — the hard sub-problem.** The slot
byte is captured from **register A on INIT entry** (the first thing INIT does:
`LD (HOOK_SLOT),A`), then used as the CALLF operand. Dual-sourced:

* The standard MSX cartridge/disk INIT convention passes the ROM's slot id to
  INIT in a register (MSX2 TH cartridge-ROM INIT convention). This is established
  here purely by **black-box oracle**: a trace of the CF-3300 BIOS calling its
  disk INIT observed **A = C = $87** (= slot 3-1) on entry — no community-wiki
  source is relied on.
* zerobas-BASIC's own slot scan (`basic/initext.asm`) likewise leaves the slot
  byte in **A** at the CALSLT to this INIT: it does `ld a,(SCAN_SLOT)` right
  before loading IY/IX and calling CALSLT, and CALSLT passes AF through to the
  target. **Black-box confirmed:** at our INIT entry A = `$87` on every
  `C-BIOS_MSX1_*_BASIC_DISK` machine (DE high byte and IYh also = $87).

> **Coupling (documented).** Reading the slot from A depends on the caller
> delivering it there. Both the standard BIOS boot scan AND `basic/initext.asm`
> do so (the latter is our own clean-room code; `ld a,(SCAN_SLOT)` is what puts
> the slot in A). Our scan happens to leave C ≠ slot (it does not follow the
> "slot in C" half of the convention), so we read **A**, not C — the register
> confirmed = $87 on both the real BIOS and our scan. If `initext.asm`'s INIT
> calling sequence ever changes the register holding the slot, this read must
> follow. The DISKSLOT sysvar (set by `initext.asm` *after* the CALSLT returns)
> is NOT available *during* INIT, so it cannot be used here.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| HPHYD hook address | $FFA7 | public MSX hook table (fms.komkon.org/MSX/Docs/Hooks.txt); CF-3300 black-box (`disk/docs/expansion-protocol.md` §2) | sourced |
| Hook idiom | `F7 <slot> 10 40 C9` = RST 30h ; slot ; $4010 ; RET | MSX2 TH §2 inter-slot CALLF; CF-3300 black-box trace (expansion-protocol.md §2) | sourced |
| Hook target | $4010 = our DSKIO ($4000 + standard +$10 offset) | MSX2 TH, disk ROM interface | sourced |
| Own slot byte source | register A on INIT entry (`LD (HOOK_SLOT),A` first) = $87 (3-1) | MSX2 TH cartridge-ROM INIT convention; established by black-box oracle (CF-3300 INIT trace A=$87) + our own `basic/initext.asm` scan (oracle-confirmed A=$87); coupling documented above | sourced |
| `HOOK_SLOT` scratch byte | $E55D (1 B) | own choice (free page-3 RAM after FAT_SECPERFAT word $E55B-$E55C, before WBUF $E560) | sourced |
| End-to-end provider read | `CALL $FFA7` (installed hook) → CALLF → our DSKIO reads boot sector byte-identical to disk | own black-box test (C-BIOS_MSX1_EU_BASIC_DISK) | sourced |
| BIOS PHYDIO entry | $0144 | MSX Assembly Page BIOS map (map.grauw.nl/resources/msxbios.php); MSX2 TH BIOS jump table — NOT disassembly | sourced |
| Tier-1 organic provider oracle | real CF-3300 BIOS boot scan installs `H.PHYD = F7 87 10 40 C9`; real BIOS PHYDIO ($0144) routes *through* $FFA7 (BP-hit confirmed) into our DSKIO; sector 0 byte-identical, CY=0; CY=1 write+readback round trip; no probe-injected hook | own black-box test (`National_CF-3300_ZEROBASDISK` + `disk_probe_provider_phydio.py`) | sourced |
| SYSTEM sysvar | $F37D | MSX2 TH, work area; C-BIOS `systemvars.asm` | sourced |
| SYSTEM sysvar write: `LD ($F37D),HL` with HL = bdos_entry | — | own code; reached cross-slot via CALSLT, differentially confirmed (`disk_probe_bdos.py` vs MSX-DOS 1) | sourced |
| Default DTA seed: `LD (BDOS_DTA),HL` with HL = $0080 | — | own code; $0080 = MSX-DOS default DTA (MSX2 TH, BDOS conv.) | sourced |
| BDOS entry dispatcher: A=$FF for unsupported calls | — | own design; A=$FF documented BDOS error | sourced |

> **Hook integration — oracle finding (probe-3 investigation), now actioned.**
> Observing the **National CF-3300** reference in openMSX after boot (RAM only —
> the disk ROM's code was never read), the real disk ROM integrates via the
> CALLF idiom — which is exactly what INIT now installs at HPHYD:
> - It installs **`RST 30h` (CALLF) inter-slot calls** — `$F7`, a slot byte, a
>   2-byte target — at hook-table entries **$FD9F (H.TIMI, timer), $FDEF, $FDF9,
>   $FFA7, $FFAC**, all with slot byte **$87 = expanded slot 3-1** and targets in
>   the disk ROM's page-1 range. A plain `JP` (the old draft's approach) **cannot
>   cross slots**. zerobas-disk now installs the **same CALLF idiom at $FFA7
>   (HPHYD)**, pointing at our DSKIO ($4010) — the load-bearing hook (§2 of the
>   expansion protocol; the other four are not loader-bearing for our scope).
> - The real ROM does **NOT** touch **$FF3E** or **$FF4B** (both still `$C9` after
>   boot). $FF4B is not even 5-byte-aligned in the hook table (`$FF4B − $FD9A =
>   433`, not ÷5), so the old draft's "H.DSKIO = $FF4B" was never a valid slot.
> - **$F37D** holds **$31C3** (a BIOS-ROM, page-0 address) on the reference,
>   because Disk BASIC exposes file I/O through the disk-ROM entry table ($4010…)
>   plus the BASIC expansion/CALLF chain, not an FCB BDOS at a SYSTEM vector.
>
> **Resolution applied.** The mis-addressed `JP` hooks at $FF3E/$FF4B were
> **removed** from `disk/disk.asm` long ago (along with the now-unused
> `phyd_handler` shim, the `install_hook` writer, and the `H_PHYD`/`H_DSKIO`
> equs): they were both wrong (wrong addresses, `JP` can't cross slots) *and*
> dead for the host direction. The **correct** hook — a CALLF at $FFA7 → our
> DSKIO — is now installed for the **provider** direction (a foreign host's
> PHYDIO reaching us). INIT therefore now: (1) installs the HPHYD CALLF, and (2)
> publishes the SYSTEM-vector BDOS entry + DTA default (the internal path
> zerobas-BASIC drives). The internal path stays **differentially
> oracle-confirmed byte-identical vs real MSX-DOS 1** (`disk_probe_bdos.py`), the
> underlying $4010 DSKIO read is differential-confirmed vs the CF-3300
> (`disk_probe_dskio.py`, probe 2), and the new HPHYD→DSKIO route is confirmed
> end-to-end (`CALL $FFA7` reads the boot sector byte-identical to disk).

---

## DPB / GETDPB — real (provider direction)

**`getdpb` ($4016) is now a real DPB builder** (previously a deliberate carry-set
stub). It is the PROVIDER-direction surface: a real MSX-BASIC / MSX-DOS host calls
$4016 to obtain a DPB describing the mounted volume's geometry, and a black-box
trace of `BLOAD`/`SAVE` on the CF-3300 confirmed Disk BASIC **does** call GETDPB,
so a standard provider must answer it. (zerobas's own loader never calls $4016 —
`fat_mount` derives geometry straight from the BPB — but a foreign host driving us
does.) The earlier "not cleanly sourceable" concern (directory mask/shift, total-
cluster encoding) is resolved below: the field formulas come from the **Nextor 2.1
Driver Development Guide §4.5.3** (Konamiman, GitHub — an allowed public MSX ref
that restates the standard GETDPB contract) and the **MSX2 Technical Handbook §3,
Figure 3.11** (DPB structure), and the whole layout is **black-box confirmed
field-for-field against the CF-3300's own GETDPB output** (see the oracle box).

### Calling convention (Nextor §4.5.3 / MSX disk-ROM interface)

```
in:  A  = drive (unit) number (0 = A:)        ; ignored — single-drive machine
     B  = C = media descriptor byte
     HL = DPB base address MINUS ONE          ; GETDPB fills from HL+1 (media)
out: Cy = 0 ok (DPB filled) / Cy = 1 error (boot-sector read failed)
```

The first byte GETDPB writes (media) lands at **HL+1** — black-box confirmed: with
HL = $C0FF the CF-3300 reference wrote the media byte at $C100. The DPB's BASE+0
(drive number) is the caller's, not filled by GETDPB.

### DPB field encoding (per-field source) — 720 KB shown, all BPB-derived

| DPB offset | Field | 720 KB value | Encoding / source |
|------------|-------|--------------|-------------------|
| +0 | drive number | (caller's) | TH Fig 3.11; NOT filled by GETDPB |
| +1 | media ID | $F9 | BPB media byte (boot +21); TH Fig 3.11 |
| +2..3 | sector size (LE) | $0200 (512) | BPB bytes-per-sector (+11); validated 512 at mount |
| +4 | directory mask | $0F (15) | `(sector size / 32) - 1` = 512/32-1 = 15 (Nextor §4.5.3) |
| +5 | directory shift | $04 (4) | one-bits in dir mask = log2(entries/sector) = 4 (Nextor §4.5.3) |
| +6 | cluster mask | $01 | `(sectors per cluster) - 1` = 2-1 = 1 (Nextor §4.5.3); secPerClus from BPB |
| +7 | cluster shift | $02 | `(one-bits in cluster mask) + 1` = 1+1 = 2 (Nextor §4.5.3) |
| +8..9 | top sector of FAT (LE) | 1 | reserved sectors (= FAT_FATSTART, our `fat_mount`); TH Fig 3.11 |
| +10 | number of FATs | 2 | BPB +16 (= FAT_NUMFATS); TH Fig 3.11 |
| +11 | dir entries | $70 (112) | BPB root-entry count low byte (+17); TH Fig 3.11 (max 254) |
| +12..13 | top sector of data (LE) | 14 | first data sector (= FAT_FIRSTDATA, our `fat_mount`); TH Fig 3.11 |
| +14..15 | amount of cluster + 1 (LE) | $02CA (714) | dataClusters + 1 = `fat_total_clusters` (713+2) − 1; TH Fig 3.11; MS FAT spec §3.3 |
| +16 | sectors per FAT | 3 | BPB +22 (= FAT_SECPERFAT); TH Fig 3.11 |
| +17..18 | top sector of dir (LE) | 7 | first root-dir sector (= FAT_FIRSTROOT, our `fat_mount`); TH Fig 3.11 |
| +19..20 | FAT address in memory | (OS field) | filled by the OS, NOT GETDPB; TH Fig 3.11; left untouched |

> **Clean-room DPB differential oracle (validation + encoding-nailing).** Booted
> the real **National CF-3300** (`cf-3300_disk.rom`) in openMSX with a /tmp copy
> of the 720 KB `test720.dsk`, injected a Z80 stub that CALSLTs the reference's
> GETDPB ($4016) with A=0, B=C=$F9, HL=$C0FF (slot byte $87), and read the
> resulting DPB bytes out of RAM. The reference returned **carry=0** and DPB =
> `f9 00 02 0f 04 01 02 01 00 02 70 0e 00 ca 02 03 07 00`. Running the SAME stub
> against `C-BIOS_MSX1_EU_BASIC_DISK` (zerobas-disk in slot 3-1) returned the
> **byte-identical** 18-field result. This is a clean oracle use: only the
> reference's *output bytes* were observed; its code (slot 3-1 $4000-$7FFF) was
> never read or disassembled. The `+14..15 = $02CA` value is what corrected the
> encoding to `dataClusters + 1` (= `fat_total_clusters − 1`), not + 2.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| GETDPB ($4016) builds a real DPB from the BPB | — | MSX2 TH Fig 3.11 + Nextor §4.5.3 field formulas; field-for-field CF-3300 black-box confirmed | sourced |
| GETDPB convention: A=drive, B=C=media, HL=DPB base−1, Cy out | — | Nextor 2.1 Driver Development Guide §4.5.3; media-at-HL+1 black-box confirmed | sourced |
| Disk geometry: tracks / sectors-per-track / sides | 80 / 9 / 2 | ECMA-107, 3.5" DSDD (used by the CHS map, §FDC driver) | sourced |
| Sectors per cluster (720 KB) | 2 | ECMA-107 / MS FAT spec (read from the BPB at mount, not hard-coded) | sourced |
| Total sectors (720 KB) | 1440 (80 × 2 × 9) | derivable from geometry | sourced |

No quarantined items.

---

## FDC driver — MB8877A / WD2793 + CF-3300 register map

> The CF-3300's actual FDC is the Fujitsu **MB8877A**; it is WD179x-family
> compatible, so the WD2793 datasheet ("WD2793 DS") below is a faithful
> compatible-family reference for the identical command/status interface
> (oracle-validated byte-identical to the real CF-3300). openMSX models this FDC
> as a `<WD2793>` device.

### WD2793 / MB8877A register layout (from datasheet)

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
| Write Sector command (single record) | $A0 | WD2793 DS command table | sourced |
| Force Interrupt | $D0 | WD2793 DS command table | sourced |
| WD2793 reset → Track register = 0 | — | openMSX `WD2793.cc` `reset()` (`trackReg = 0`); informs the restore-on-retry recovery | sourced |

> **Write Sector command byte + flag bits (`CMD_WRITE = $A0`).** The WD2793 Type-II
> command word is `1 0 m S E C a0`: bit 7-5 = `100` selects Write Sector, bit 4
> `m` = multiple-record (0 = single record), bit 3 `S` = side-compare enable
> (0 = no side compare — the driver does not compare the side field, exactly as the
> Read path leaves it 0), bit 2 `E` = 15 ms head-settle delay (0), bit 1 `C` =
> side-compare value (don't-care when S=0), bit 0 `a0` = data-address-mark select
> (0 = write a **normal** data mark `$FB`, 1 = a **deleted** data mark `$F8`). The
> driver writes `$A0` = all those flag bits clear: single record, no side compare,
> no settle delay, **normal data mark**. This is the exact write twin of the Read
> Sector `$80` the driver already uses (also all-flags-clear single record). Source:
> WD2793 datasheet, Write Sector command word + flag-bit table.

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

### DSKIO WRITE path (`dskio_write` / `fdc_write_phys` / `fdc_write_data`)

The write direction mirrors the read direction structurally: `dskio_write` loops
the sector count, converts each logical sector → CHS with the same `div9`, and
calls `fdc_write_phys` (the twin of `fdc_read_phys`). `fdc_write_phys` latches
drive A + side + motor via `FDC_CTRL` ($7FBC), Type-I-seeks to the track, then
issues the `$A0` Write Sector command and runs the polled 512-byte transfer
(`fdc_write_data`): poll `FDC_STATUS` ($7FB8) bit 1 (DRQ) and write each byte to
`FDC_DATA` ($7FBB) — the exact write twin of the read loop's DRQ poll. Then it
polls BUSY-clear and checks the result-phase status. One restore+reseek+rewrite
retry recovers a stale Track register, like the read path; a genuine
write-protected disk is reported up front with **no** retry.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| DSKIO write request: Cy=1 on entry → `dskio_write` | — | MSX2 TH, disk ROM interface (DSKIO direction) | sourced |
| Write Sector command issued | $A0 (single record, normal data mark) | WD2793 DS command word (see §command flag bits) | sourced |
| Polled write transfer: on DRQ (status bit 1) write next byte to Data reg ($7FBB) | — | WD2793 DS (Type II DRQ-paced data transfer); IRQ/DRQ not wired to Z80 per `NationalFDC.cc` → status-polled, like the read path | sourced |
| Result-phase status read after BUSY clears | $7FB8 | WD2793 DS (Type II result phase) | sourced |
| Write-protect / write-fault: status bit 6 ($40, `ST_WP`) set → DSKIO error code **0** (write protected) | — | WD2793 DS (Type II bit 6 = Write Fault; Type I bit 6 = Write Protect — same bit, $40) ↔ MSX2 TH DSKIO write-protected code 0 | sourced |
| WP/write-fault reported up front, no restore-retry | — | own design; a protected medium will not be cured by a recalibrate, so retrying is pointless (and could mask the WP) | sourced |
| Write status → DSKIO error mapping (WP/fault→0, NOTRDY→2, RNF→8, CRC→4, LOST→12) | — | own mapping; WD2793 DS Type-II status bits ↔ MSX2 TH DSKIO error codes (identical to the read mapping plus the WP/fault→0 row) | sourced |
| `B` = sectors-not-written on error, like the read path's `dskio_err` | — | MSX2 TH, disk ROM interface (DSKIO output: B = sectors not transferred) | sourced |
| WRITE round-trip + persistence + CF-3300 cross-machine read all byte-identical | — | **differential oracle PASS** (`disk_probe_write.py`): our `dskio_write` writes a distinctive 512-byte pattern to a /tmp scratch image, our read path reads it back identical, a fresh reboot reads it identical (persisted to the image file), and the **genuine National CF-3300's own disk ROM** DSKIO-reads the sector **byte-identical** to what we wrote | oracle-confirmed |

> **Single-drive simplification.** The CF-3300 declares `<drives>1</drives>`; the
> driver always selects drive A (latch bit 0) and ignores the DSKIO drive number
> and media-descriptor byte. **Write support is now implemented** (`dskio_write` /
> `fdc_write_phys` / `fdc_write_data`, rows above): a DSKIO write request performs
> the real WD2793 Write Sector sequence and is differential-confirmed against the
> CF-3300 reference. A genuinely write-protected medium still returns error code 0
> (write protected), which is the same code the old stub returned for the now-real
> WP case. This is the physical sector-write primitive only; FAT12/BDOS write
> logic is a separate, later workstream.

> **FDC registers shadow ROM offsets $3FB8–$3FBF.** Because the WD2793 device
> intercepts reads at $7FB8–$7FBF (ROM offsets $3FB8–$3FBF), those bytes of the
> ROM image are not readable as code/data. They fall inside the zero-padding
> region of this 16 KB ROM, so nothing important is placed there.

No quarantined items.

---

## Boot sector boot code (test image)

The test image's boot sector (sector 0, `tools/make_test_dsk.py`
`_write_boot_code`) must be **cold-boot-safe**: a real MSX1 disk machine reads it
into RAM and *executes* it, so an inert/garbage boot-code area hangs the machine.
This is a **clean-room own-design stub built from the documented MSX2 TH contract**
— NOT a copied reference boot sector.

### Contract (sourced verbatim — MSX2 TH §3, MSX-DOS, boot procedure)

> "Then, the contents of the boot sector (logical sector #0) is transferred to
> C000H to C0FFH. At this time, when 'DRIVE NOT READY' or 'READ ERROR' occurs, or
> when the top of the transferred sector is neither EBH nor E9H, DISK-BASIC is
> invoked. The routine at C01EH is called with CY flag reset. Normally, since code
> 'RET NC' is written to this address, nothing is carried and the execution
> returns. Any boot program written here in assembly language is invoked
> automatically."
> — MSX2 Technical Handbook, Chapter 3 (Konamiman's public English translation).

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Boot sector load address | $C000–$C0FF | MSX2 TH §3 (verbatim above) | sourced |
| Boot-code entry offset | $C01E (sector offset +$1E) | MSX2 TH §3 | sourced |
| Entry mechanism | **CALL** ("the routine at C01EH is called") — stub must RET, not JP | MSX2 TH §3 | sourced |
| Entry flag state (first call) | CY (carry) **reset** | MSX2 TH §3 | sourced |
| First byte must be $EB or $E9 to reach the boot code | $EB (kept) | MSX2 TH §3 ("neither EBH nor E9H → DISK-BASIC") | sourced |
| Documented safe data-disk default at $C01E | `RET NC` (returns with CY reset → falls through to BASIC) | MSX2 TH §3 (verbatim above) | sourced |

### Own-design stub

The stub at sector offset $1E is the single documented "do nothing, return"
instruction, plus one belt-and-braces RET:

| Byte | Offset | Meaning | Status |
|------|--------|---------|--------|
| $D0 | $1E | `RET NC` — the documented data-disk default; CY is reset on the first call (MSX2 TH §3) so it returns to BASIC | own design (= documented default) |
| $C9 | $1F | `RET` — unconditional return; covers any path that enters at $C01F or with CY set, so the area can never run into the $00 NOP slide | own design (defensive) |
| $00 | $20–$1FD | NOP filler; never executed (entry $1E returns) | — |

> **Why this is safe and own-design, not a lift.** The MSX2 TH text states the
> default at $C01E *is* `RET NC`, and that a data disk with no boot program simply
> returns there. Our stub writes exactly that one documented instruction (plus a
> defensive unconditional `RET`). No byte sequence was copied from any real MSX
> boot sector or disk-ROM disassembly — the behaviour is reconstructed from the
> CALL/RET-NC contract. Bytes 0–2 keep `$EB $FE $90` (byte 0 = $EB so the boot
> code is reached at all; bytes 1–2 are the standard x86-style jump-displacement +
> NOP filler of the 3-byte jump field, not executed by the Z80 boot path). Bytes
> 3–29 (OEM + BPB) and the FAT/dir geometry are untouched; only $1E..$1FD change.

> **Oracle-confirmed cold-boot-safe (before vs after).** `disk_probe_boot.py`
> cold-boots the genuine **National CF-3300** reference with the
> image attached as drive A and samples CPU PC after settle. **AFTER (this stub):**
> PC reaches BASIC (ROM/RAM, e.g. $DEC1/$0D68/$10D9; SP healthy ~$C1xx; PC moving =
> live interpreter), screenshot shows the Disk-BASIC "Enter date" prompt — no
> boot-area hang. **BEFORE (the old $1E.. = $00 filler):** the NOP slide runs off
> the rails and wedges the machine — PC frozen at **$002E**, SP corrupted to
> **$0026**. The probe asserts both (the fix is safe; the synthesised filler
> wedges), strictly black-box (attach disk, observe PC; no ROM read).

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
| Open → 17× SeqRead → Close delivers byte-identical records + return codes vs real MSX-DOS 1.03 (cluster-multiple file) | — | **NARROW differential oracle PASS** (`disk_probe_bdos.py`): same `ORACLE.BIN` read on MSX-DOS and on our `bdos_entry` via CALSLT — Open/records/EOF/Close all byte-identical | oracle-confirmed |
| SeqRead EOF bounded by true file size (`FAT_FILESIZE` → `BDOS_BYTESLEFT`): partial final record = n real bytes + (RECSIZE−n) $00 pad, code $00; EOF ($01) on the next read | — | **FULL differential oracle PASS** (`disk_probe_bdos.py`, PART A): a 1500-byte non-cluster-multiple `ORACLE2.BIN` read on MSX-DOS 1.03 and on our `bdos_entry` is byte-identical across all 12 delivered records (incl. the 92-byte partial) and the EOF code | oracle-confirmed |
| Partial-record pad value = **$00 (zero-fill)** | — | **ORACLE OBSERVATION** (`disk_probe_bdos.py` PART A): MSX-DOS 1.03 returns the partial record with its tail beyond the file end set to $00 — confirmed actively zero-filled by pre-loading the DTA with $FF and seeing the tail still read $00 (so not Ctrl-Z/$1A, not stale). Record framing from MSX2 TH FCB sequential I/O / CP/M FCB | oracle-confirmed |
| Single open file: position in FAT iterator + BDOS_RECIDX + BDOS_BYTESLEFT, FCB extent (+12) / current-record (+32) / record-count (+15) / alloc-map (+16..31) fields left at $00 | — | own design simplification (read-only loader subset). **DOCUMENTED INTENTIONAL DIVERGENCE**, not a fidelity gap: `disk_probe_bdos.py` PART B captures these fields on both machines and reports the divergence — MSX-DOS advances them (its internal FCB bookkeeping), zerobas does not. zerobas's only `bdos_entry` callers (BLOAD/LOAD/RUN) read **A + the DTA only, never FCB fields**, so matching this bookkeeping has no functional value. The fields a reasonable FCB caller *does* read — drive (+0) and the 8.3 name (+1..+11) — ARE byte-identical (PART B [MATCH]) | divergence-documented |
| Register save/restore contract for the BLOAD→BDOS call | — | the Open/SeqRead/Close round-trip is exercised by `disk_probe_bdos.py` (CALSLT in, A out) over two files; exact non-A register preservation across CALSLT still not textually sourced | quarantined |

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
> the BPB, searches the root directory for the FCB's 11-byte 8.3 name, and seeds
> `BDOS_BYTESLEFT` from `FAT_FILESIZE`; the sequential reader slices the 512-byte
> sector buffer into 128-byte records into the DTA, refilling from the cluster
> chain on exhaustion, and **bounds the record stream by the true file size**:
> when `BDOS_BYTESLEFT` reaches 0 every read returns EOF ($01), and the final
> partial record is delivered with n = min(128, BYTESLEFT) real bytes followed by
> 128−n bytes of $00 (oracle-observed MSX-DOS padding), code $00. Close is a
> no-op success (read-only). The FCB bookkeeping fields (extent/current-record/
> record-count/alloc-map) are left at $00 — a **documented intentional
> divergence** (no `bdos_entry` caller reads them), characterised field-by-field
> by `disk_probe_bdos.py` PART B; the matched fields (drive, 8.3 name) are
> byte-identical. The whole BDOS read surface is now FULL-differential
> oracle-confirmed byte-identical vs real MSX-DOS 1.03 across a cluster-multiple
> file (narrow) and a 1500-byte sub-record-EOF file (PART A).

### BDOS WRITE interface (Create / Sequential Write / write-flushing Close)

The disk ROM also implements the CP/M-compatible FCB WRITE subset a `SAVE` /
`BSAVE"A:FILE"` path needs: Create a file, append 128-byte records to it, and
make it durable at Close. The single-open-file model of the read side is
preserved (one file open for read OR write at a time); the write position lives
in dedicated scratch (§Scratch RAM), not in the FCB bookkeeping fields (the same
documented divergence as the read side). The whole write surface is
**differential oracle-confirmed vs real MSX-DOS 1** by `disk_probe_fwrite.py`:
functional read-back, cross-machine MSX-DOS read, and a
structural image diff.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| FCB Create call number | $16 | MSX2 TH, MSX-DOS BDOS call table | sourced |
| FCB Sequential Write call number | $15 | MSX2 TH, MSX-DOS BDOS call table | sourced |
| Create: find/make a root-dir slot for the FCB's 8.3 name; write name + attribute + zeroed size/cluster; ready for writing from offset 0 | — | own code composing the FAT12 write-back layer; FCB name offset + Create call number sourced above | sourced |
| Create return value | A = $00 created / $FF error (disk full / write protect / dir full) | MSX2 TH, BDOS conventions | sourced |
| Sequential Write: buffer the next 128-byte record from the DTA (`BDOS_DTA`) into `SECTOR_BUF`; flush a full 512-byte sector to the file, allocating/extending the cluster chain | — | own code; 128-byte record + settable DTA sourced (read side); FAT12 write-back below | sourced |
| Sequential Write return value | A = $00 ok / $01 disk full / $FF not-open | MSX2 TH, BDOS conventions (seq-write disk-full code $01) | sourced |
| Write granularity is the 128-byte record (a file written via Sequential Write is always a 128-byte multiple; no sub-record byte count) | — | CP/M / MSX-DOS FCB sequential-write semantics (MSX2 TH, FCB sequential I/O) | sourced |
| Close (write file): flush the partial final 512-byte sector (zero-padded tail), persist the cluster chain (EOC already linked during allocation), rewrite the dir entry's first cluster (+26) and true byte count (+28) | — | own code; dir-entry field offsets from Microsoft FAT spec §3.4 (below) | sourced |
| Close (write) return value | A = $00 ok / $FF I/O error | MSX2 TH, BDOS conventions | sourced |
| Close (read file) behaviour unchanged (no dirty state → A = $00) | — | preserves the read-side Close | sourced |
| Directory-entry attribute byte (+11) on Create | **$00 (normal file)** | **ORACLE OBSERVATION** (`disk_probe_fwrite.py` PART 3): real MSX-DOS 1 Create writes attribute $00 — it does NOT set the archive bit; we match it byte-for-byte. (An earlier draft used $20/archive; the oracle showed $00.) | oracle-confirmed |
| Create + 11× Sequential Write (1408 B) + Close → our own Open/SeqRead reads it back byte-identical, correct size, correct EOF | — | **FUNCTIONAL PASS** (`disk_probe_fwrite.py` PART 1): exercises a partial final data sector (384 of 512 B), a cluster-chain hop, and the multi-FAT sync | oracle-confirmed |
| The file OUR ROM writes is Opened + Sequentially Read **byte-identical by genuine MSX-DOS 1** (correct data + EOF) | — | **CROSS-MACHINE PASS** (`disk_probe_fwrite.py` PART 2): proves our FAT chain + directory entry are valid to real MSX-DOS, not just to our own reader | oracle-confirmed |
| Same name+content file written by OUR ROM vs by MSX-DOS → identical DATA + identical dir entry **excluding date/time (+22..25) and the free-list-dependent first cluster (+26..27)** | — | **STRUCTURAL PASS** (`disk_probe_fwrite.py` PART 3): each image's data recovered by walking its OWN FAT chain (proving both chains valid); the dir entry matches MSX-DOS apart from the documented timestamp divergence and the cluster pointer (the MSX-DOS image also carries WRITER.COM/AUTOEXEC, so its free list differs) | oracle-confirmed |

> **Date/time stamp — intentional divergence (no fabricated clock).** MSX-DOS
> stamps the directory entry's last-modified date/time (+22..25) from the system
> clock. zerobas has **no RTC / clock source**, so Create/Close write these four
> bytes as **$0000**. This is a deliberate divergence in the SAME spirit as the
> read-side FCB-bookkeeping divergence: the file's NAME, SIZE, FIRST-CLUSTER, FAT
> CHAIN, and DATA all match genuine MSX-DOS byte-for-byte (proven by
> `disk_probe_fwrite.py`); only the timestamp differs. We do **not** invent a
> clock. The structural differential explicitly masks +22..25 and reports the
> observed MSX-DOS value (e.g. `$00002108`) alongside our `$00000000`.

> **Implementation note.** Realised in `disk/disk.asm` as `bdos_create` /
> `bdos_seqwrite` / the write branch of `bdos_close`, on top of a FAT12
> write-back substrate (§FAT12 write-back layer): `fat_dir_create`,
> `fat_alloc_cluster`, `fat_write_fat_entry`, `fat_flush_data_sector`,
> `fat_dir_update`. The file DATA accumulates in `SECTOR_BUF`; the FAT/dir
> METADATA helpers use an independent second buffer `WBUF` so a cluster scan or
> directory stamp never disturbs the in-flight data sector. New write-position
> scratch lives after `BDOS_BYTESLEFT` (§Scratch RAM). Disk-full / write-protect
> surface as $01 / $FF respectively (the underlying DSKIO write-protect code 0 is
> mapped up to a BDOS error).

---

## FAT12 write-back layer

The write twin of the read FAT12 layer (§FAT12 layer), built from the Microsoft
FAT specification. All structures are realised, not lifted; the physical sector
write goes through the already differential-confirmed `dskio` write path.

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Free-cluster allocation: linear scan from cluster 2 to the total-cluster bound, claim the first `$000` entry | — | Microsoft FAT spec §3.2 ($000 = free); total clusters = 2 + (totalSectors − firstData) / secPerClus (§3.3) | sourced |
| Free-cluster scan reads the FAT **sector-by-sector** into `WBUF` (one read per FAT sector, up to 341 12-bit entries tested from RAM), not one disk read per cluster | — | own design (performance); the first free cluster can be hundreds of clusters into a populated disk | sourced |
| Newly allocated cluster marked end-of-chain | `$FFF` (EOC) | Microsoft FAT spec §3.2 ($FF8–$FFF = end-of-chain; we write $FFF) | sourced |
| 12-bit FAT entry **pack** (write) — even cluster: low byte = v[7:0], high nibble of next byte = v[11:8]; odd cluster: low nibble of byte = v[3:0], next byte = v[11:4] | — | Microsoft FAT spec §3.2 — the exact inverse of the read-side `fat_next_cluster` unpack; sector-straddle ($1FF boundary) handled by spilling into the following FAT sector | sourced |
| Chain LINK: point the previous tail cluster's FAT entry at the new cluster | — | own code over the 12-bit pack above (Microsoft FAT spec §3.2) | sourced |
| Multi-FAT sync: every FAT-entry change is written to **all** FAT copies (`BPB_NUMFATS`), copy k's sector = base + k × secPerFAT | — | Microsoft FAT spec §3.1 (NumFATs identical copies); numFATs / secPerFAT cached at mount so the sync needs no boot-sector re-read mid-flush | sourced |
| Directory-entry create: find a free root-dir slot ($00 end-marker or $E5 deleted) or the existing same-named entry; write name (+0..10), attribute (+11), zero +12..31 | — | Microsoft FAT spec §3.4 (dir entry layout, $00/$E5 slot markers) | sourced |
| Directory-entry first-cluster field | +26..27 (word LE) | Microsoft FAT spec §3.4 | sourced |
| Directory-entry file-size field | +28..31 (dword LE) | Microsoft FAT spec §3.4 | sourced |
| Directory-entry date/time fields | +22..25 = $0000 (intentional divergence, no clock — see §BDOS WRITE) | own design (documented divergence) | sourced |
| Data write: buffer record bytes into `SECTOR_BUF`, write full 512-byte sectors at `firstData + (cluster−2)×secPerClus + sectorInCluster`, zero-pad the partial final sector | — | Microsoft FAT spec §3.3 (data-sector math); own buffering | sourced |
| Truncate-if-exists: Create reusing an existing same-named dir slot orphans the old chain (does not free it) | — | own design simplification (loader-create subset); acceptable because the read/round-trip and cross-machine probes confirm the new chain + size are correct | quarantined |
| Whole FAT12 write-back differential-confirmed vs MSX-DOS 1 | — | **oracle PASS** (`disk_probe_fwrite.py`): functional read-back, cross-machine MSX-DOS read, structural image diff — see §BDOS WRITE | oracle-confirmed |

> **Implementation note.** The write-back helpers live in `disk/disk.asm` after
> the read FAT12 layer. They share the read helpers' geometry scratch (`FAT_*`)
> and the 512-byte `WBUF` metadata buffer; the data buffer is `SECTOR_BUF`. The
> 12-bit straddle case (an entry split across a 512-byte FAT-sector boundary, e.g.
> cluster 341/682 on a 720 KB image) is handled symmetrically to the read path —
> the following FAT sector is loaded for the spilling nibble and written back too.

> **Truncate-orphan quarantine.** Re-Creating an existing file reuses its dir
> slot but does NOT walk + free its old cluster chain, so the old chain leaks as
> lost clusters. This is an own-design simplification for the loader's
> create-fresh use; the produced file (new chain, size, data) is correct and
> oracle-confirmed. A full implementation would free the old chain first; that is
> deferred (no current caller re-Creates over a populated file).

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
| BDOS bytes-remaining counter (`BDOS_BYTESLEFT`) | $E542–$E545 (4-byte LE) | own choice (free page-3 RAM past basic-core's `DISK_DTA` buffer $E4C2..$E541, clear of every disk + basic region — see basic/sysvars.inc); seeded from `FAT_FILESIZE` by Open, decremented per record to bound the partial final record + EOF | sourced |
| BDOS/FAT12 WRITE-back scratch | $E546–$E559 (20 bytes) | own choice (free page-3 RAM after `BDOS_BYTESLEFT`, clear of every disk + basic region) | sourced |
| — write mode flag (`BDOS_WRMODE`, 1 = file open for write) | $E546 (1 byte) | own choice | sourced |
| — chain-tail cluster being filled (`BDOS_WRCLUS`) | $E547–$E548 (word) | own choice | sourced |
| — file's first cluster, 0 until allocated (`BDOS_WRFIRST`) | $E549–$E54A (word) | own choice | sourced |
| — sector index within current cluster (`BDOS_WRSECIDX`) | $E54B (1 byte) | own choice | sourced |
| — bytes buffered in SECTOR_BUF (`BDOS_WRBUFLEN`, 0..512) | $E54C–$E54D (word) | own choice | sourced |
| — total bytes written = final file size (`BDOS_WRBYTES`) | $E54E–$E551 (4-byte LE) | own choice | sourced |
| — open file's dir-entry sector (`BDOS_DIRSEC`) | $E552–$E553 (word) | own choice | sourced |
| — open file's dir-entry byte offset (`BDOS_DIROFF`) | $E554–$E555 (word) | own choice | sourced |
| — write-helper transients (`FAT_WRTMP`, `FAT_WRTMP2`) | $E556–$E559 (2 words) | own choice (saved value / free-cluster-scan cached sector) | sourced |
| numFATs / secPerFAT cached at mount (`FAT_NUMFATS`, `FAT_SECPERFAT`) | $E55A–$E55C (3 bytes) | own choice (so multi-FAT sync needs no boot-sector re-read mid-flush) | sourced |
| Write-back FAT/dir metadata buffer (`WBUF`, 512 bytes) | $E560–$E75F | own choice (free page-3 RAM after the write scratch); keeps FAT/dir reads off `SECTOR_BUF` so in-flight write data is undisturbed | sourced |

> **FAT12 geometry is derived, not stored as constants.** `fat_mount` reads the
> boot sector and computes the first-FAT / first-root / root-sector-count /
> first-data sector numbers from the on-disk BPB (Microsoft FAT spec §3.1/§3.3),
> validating only that the sector size is 512 bytes (so the 512-byte
> `SECTOR_BUF` is always large enough). No geometry is hard-coded, so the layer
> serves any FAT12 image the BPB describes. GETDPB (§DPB) reuses these same
> `fat_mount`-derived values to build the DPB it returns to a foreign host.

> These addresses are provisional. Before finalising, verify against both
> zerobas-core's RAM map (PROVENANCE.md §RAM additions) and the C-BIOS system
> variable table to confirm the window is free *at rest* — and against oracle
> probe #3's disturbed-RAM footprint to confirm it is also free *during a disk
> call*. The window is own-choice; the probes only rule out collisions, they do
> not dictate the layout.

---

## Oracle probes owed

Before any code section is declared complete, the following black-box probes
must be run against the CF-3300 in openMSX and added to the probe suite (`probes/disk/`):

1. **FDC register map probe** — ~~confirm the CF-3300 WD2793 base address and
   drive-select latch by writing known patterns and reading status~~ **Resolved
   from an allowed source:** the register addresses and the drive/side/motor
   latch bit map are taken directly from openMSX `src/fdc/NationalFDC.cc`
   (allowed for hardware register maps). **Runtime-confirmed:** probe 2 below now
   reads real sectors through this register map on openMSX, so the map is
   exercised, not just sourced.
2. **DSKIO sector read** — read sector 0 (boot sector) and confirm BPB fields
   match the known test image; validates FAT12 and FDC layers together.
   **DONE — differential oracle PASS.** `probes/disk/disk_probe_dskio.py`
   (in `probes/disk/`) reads the same `disk/test720.dsk` on the real
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
   passes** (`disk_probe_bdos.py`). It reads the same `ORACLE.BIN`
   through Open → 17× SeqRead → Close on real MSX-DOS 1.03 (booted on
   `National_CF-3300` from a DOS system disk, the `.COM` auto-run via AUTOEXEC.BAT)
   and on our `bdos_entry` (via CALSLT), and the Open result, all 16 records, the
   EOF code, and the Close result are **byte-identical**. **FULL differential now
   landed too:** `disk_probe_bdos.py` PART A adds a 1500-byte non-cluster-multiple
   `ORACLE2.BIN` whose last record is partial (92 real bytes), and PART B captures
   the 37-byte FCB on both machines after Open / 2 SeqReads / Close. Result: the
   12 delivered records (incl. the partial) + the EOF code are byte-identical, the
   partial record's pad is **oracle-observed $00 zero-fill** (confirmed by
   pre-filling the DTA with $FF), and the FCB drive + 8.3-name fields match;
   MSX-DOS-internal FCB bookkeeping (extent/current-record/record-count/alloc-map)
   is a reported **documented intentional divergence** (no `bdos_entry` caller
   reads it). The FAT12 read path
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
5. **DSKIO sector WRITE** — prove `dskio_write` produces a real, correctly
   formatted sector, bidirectionally and black-box. **DONE — differential oracle
   PASS.** `probes/disk/disk_probe_write.py` makes a /tmp
   scratch COPY of the test image (never the committed one — openMSX `-diska`
   writes back), then: (a) **round-trip** on `C-BIOS_MSX1_BASIC_DISK` — a stub
   DSKIO-WRITEs a distinctive 512-byte pattern to a high data sector and our
   already-validated read path reads it back **identical**; (b) **persistence** —
   a fresh reboot reads the sector back **identical** (the write reached the image
   file); (c) **cross-machine differential** — the genuine **National CF-3300**'s
   own disk ROM DSKIO-reads that same sector **byte-identical** to what we wrote.
   This proves our WD2793 Write Sector sequence yields a sector the real hardware/
   ROM accepts. Strictly black-box: CALSLT into $4010 (MSX2 TH), only returned
   data + carry/A observed; the reference disk ROM is never read or disassembled.
6. **BDOS FCB WRITE round-trip** — prove the Create / Sequential Write /
   write-flushing Close subset produces a real, MSX-DOS-compatible FAT12 file.
   **DONE — differential oracle PASS.** `probes/disk/disk_probe_fwrite.py`
   operates only on /tmp copies of the seed disk (never a
   committed image): (a) **functional** — on `C-BIOS_MSX1_BASIC_DISK` a stub
   Set-DTA + Create + 11× Sequential Write (a 1408-byte payload: a 128-byte-record
   multiple but not a sector or cluster multiple, so it exercises a partial final
   data sector + a cluster hop + multi-FAT sync) + Close via CALSLT to
   `bdos_entry`, then a fresh boot reads it back through our own bdos_open/seqread
   **byte-identical** with the correct size + EOF; (b) **cross-machine** — genuine
   **MSX-DOS 1** (booted on `National_CF-3300`, an ORACLE.COM auto-run via
   AUTOEXEC.BAT) Opens + Sequentially Reads the file OUR ROM wrote **byte-identical**
   (proving our FAT chain + dir entry are valid to real MSX-DOS); (c) **structural**
   — the same name+content file written by OUR ROM and by an MSX-DOS WRITER.COM on
   separate /tmp images have **byte-identical DATA** (each recovered by walking its
   OWN FAT chain) and an **identical dir entry excluding the date/time bytes
   (+22..25)** and the free-list-dependent first cluster. The date/time divergence
   (zerobas has no clock) is the only intended mismatch; the attribute byte was
   oracle-corrected to $00 to match MSX-DOS. Strictly black-box: BDOS results +
   delivered bytes only; MSXDOS.SYS / COMMAND.COM never read or disassembled.

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
an oracle probe confirming the value. There are no `TBD`/blocked rows: the FDC
register map is sourced from openMSX, the read + write + BDOS-read + BDOS-write
paths are differential-confirmed (§Oracle probes 2, 3, 5 & 6 — the physical WRITE
path's CF-3300 cross-machine read is byte-identical, and the FCB WRITE subset
produces a file MSX-DOS 1 reads byte-identical), and GETDPB is a real DPB builder
field-for-field confirmed against the CF-3300 (§DPB). The two remaining
`quarantined` write-side items are the
truncate-orphan simplification (re-Create leaks the old chain) and the
date/time-stamp divergence (no clock) — both documented and oracle-bounded.
