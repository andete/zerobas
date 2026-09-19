<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# zerobas disk expansion protocol — pinned spec (Phase 1.5 research spike)

Status: **research spike output, not yet implemented.** This document pins the
exact standard MSX BASIC↔disk-ROM protocol the zerobas loader verbs
(`BLOAD`/`LOAD`/`RUN`/`SAVE`/`BSAVE` for `"A:"`) must speak so that

* a **foreign / real standard disk ROM** services zerobas-BASIC's loader (the
  *host* direction, 1.5c), and
* a **real MSX-BASIC / MSX-DOS** can drive zerobas-disk (the *provider*
  direction, 1.5b).

Every address/convention below is cited inline to an allowed source:
**MSX2 Technical Handbook** (TH), the **MSX hook table**
(`fms.komkon.org/MSX/Docs/Hooks.txt`), or this spike's **black-box openMSX
observation** of the genuine **National CF-3300** Disk BASIC (BP on documented
hook addresses + register read-out; the reference ROM was never read or
disassembled). No reference-ROM disassembly was used.

---

## 0. Headline finding (the gate result)

**The drive-letter loader path does NOT use the BASIC DEVICE-expansion
mechanism (`$4006` / `DEVICE` work area). It uses the PHYDIO/DSKIO physical
sector interface, with the FAT/directory logic living in the disk ROM (provider)
or in the loader (zerobas).**

Live proof — on the real CF-3300, executing `BLOAD"A:PROG.BIN"`:

* `PROCNM ($FD89, 16 B)` and `DEVICE ($FD99)` stay **all-zero** — the device
  expansion entry was never invoked. (TH §5.7 names these as the expansion-call
  work areas; observed untouched.)
* Control flows through **HPHYD ($FFA7) → DSKIO ($4010)** plus **DSKCHG
  ($4013)** and **GETDPB ($4016)**. The drive-letter `"A:"` is resolved
  *internally* by Disk BASIC (boot-sector/BPB read, FAT walk, root-dir search),
  then the bytes move via the **physical sector** entry.

This is exactly the surface zerobas already drives through its private
`bdos_entry`. The standardization is therefore **not** "learn the DEVICE
protocol" — it is "drive the standard **DSKIO ($4010)** entry of whatever disk
ROM is in the slot, and own the FAT/dir logic in the loader" (Depth A, the
committed plan). See §5 go/no-go.

---

## 1. Extension-ROM header (TH §5.7, *Expanding the BIOS*)

A standard expansion ROM begins with a 16-byte header at its base (`$4000` for a
page-1 ROM):

| Offset | Field      | Meaning                                            |
|--------|------------|----------------------------------------------------|
| +0000  | ID         | `"AB"` (`$41 $42`) — expansion-ROM signature       |
| +0002  | INIT       | initialisation routine address (word)              |
| +0004  | STATEMENT  | `CALL`-statement expansion handler (word; 0 = none)|
| +0006  | DEVICE     | device-expansion handler (word; 0 = none)          |
| +0008  | TEXT       | tokenised-BASIC text pointer (word; 0 = none)      |
| +000A.. | reserved  | `$00`                                              |

zerobas-disk today: `"AB"`, INIT word set, **STATEMENT = 0, DEVICE = 0** — and
per §0 that is *correct* for the loader scope. DEVICE stays 0; the verbs reach
disk via DSKIO, not via the device handler.

The BIOS cold-boot scan walks slots, finds each `"AB"` header, and `CALSLT`s its
INIT (TH §2/§5.7). zerobas-BASIC replicates the remainder of this scan in
`basic/initext.asm` because its own INIT does not return to the BIOS scan.

---

## 2. The HOOK table — the five observed hooks identified

Hook table (RAM, 5 bytes each, default `RET`/`C9`). Names per the MSX hook table
(fms.komkon.org/MSX/Docs/Hooks.txt) and TH Appendix:

| Addr  | Name  | Purpose                              | Loader-bearing? |
|-------|-------|--------------------------------------|-----------------|
| $FD9F | HTIMI | timer-interrupt handler              | No (motor-off / housekeeping; fires ~50–60 Hz) |
| $FDEF | HDSKO | `DSKO$` statement (sector write)     | No (BASIC `DSKO$`, not BLOAD/SAVE) |
| $FDF9 | HSETS | `SET` statement                      | No |
| $FFA7 | HPHYD | **PHYDIO** standard routine (physical disk I/O) | **YES** |
| $FFAC | HFORM | FORMAT standard routine              | No (disk format) |

**Only HPHYD ($FFA7) is load-bearing for the loader verbs.** Live trace: during
both `BLOAD"A:"` and `SAVE"A:"`, HPHYD fires and lands in DSKIO; HDSKO, HSETS,
HFORM never fire. HTIMI fires constantly but carries no file I/O.

### Hook install idiom (observed, RST 30h / CALLF inter-slot patch)

After boot the real CF-3300 disk ROM has overwritten each hook's 5 bytes with an
inter-slot `CALLF`:

```
HPHYD ($FFA7): F7 87 50 60 C9   ; RST 30h ; slot $87 ; addr $6050 ; RET
HDSKO ($FDEF): F7 87 6B 96 C9   ; RST 30h ; slot $87 ; addr $966B ; RET
HTIMI ($FD9F): F7 87 78 2B C9   ; RST 30h ; slot $87 ; addr $782B ; RET
```

* `F7` = `RST 30h` = **CALLF**, the BIOS inter-slot-call restart (TH §2 inter-
  slot calls). Its inline operands are: 1 byte slot id, 2 bytes target address.
* `87` = the **slot byte** for the disk ROM = expanded slot 3-1
  (`F-EXP | sec<<2 | pri` = `$80 | (1<<2) | 3` = `$87`). Matches the prior
  CF-3300 probe finding exactly.
* The target addresses ($6050 etc.) are *inside the disk ROM page* and are an
  internal detail of the reference ROM — **zerobas does not need or use them**;
  it only needs to know the *idiom* (RST 30h + slot byte + addr + RET) to (a)
  install its own hooks when acting as provider, and (b) recognise that a
  foreign ROM has installed them when acting as host.

A `JP` cannot be used here (it cannot cross slots); the earlier `$FF3E/$FF4B`
`JP` hooks were correctly removed from zerobas-disk as dead/wrong code.

---

## 3. DSKIO — the file-I/O contract (TH §5, disk-ROM interface; observed)

Standard disk-ROM jump table (fixed offsets from the ROM base, reached
cross-slot via CALSLT):

| Offset | Entry  | Role                                   |
|--------|--------|----------------------------------------|
| +$10   | DSKIO  | read/write logical sectors             |
| +$13   | DSKCHG | disk-change test (+ re-read of DPB)    |
| +$16   | GETDPB | build Drive Parameter Block from BPB   |
| +$19   | CHOICE | format-choice string                   |
| +$1C   | DSKFMT | format a disk                          |
| +$1F   | MTOFF  | motors off                             |

### DSKIO ($4010) register convention (TH §5 + observed live on CF-3300)

| Reg | In                                        |
|-----|-------------------------------------------|
| A   | drive number (0 = A)                      |
| B   | number of sectors                         |
| C   | media descriptor (`$F9` = 720K observed)  |
| DE  | first logical sector number               |
| HL  | transfer buffer address                   |
| **CY (carry)** | **direction: clear = READ, set = WRITE** |

Out: `CY` set on error with the error code in A and B = sectors not
transferred; `CY` clear on success.

**Observed live (CF-3300):**

`BLOAD"A:PROG.BIN"` — all reads (`CY=0`):
```
DSKIO A=00 CY=0 B=01 C=F9 DE=0000   ; boot/BPB
DSKIO A=00 CY=0 B=03 C=F9 DE=0001   ; FAT
DSKIO A=00 CY=0 B=01 C=F9 DE=0007   ; root dir
... data sectors ...
```

`SAVE"A:Z"` — reads to locate free space, then writes (`CY=1`):
```
DSKIO A=00 CY=0 B=03 C=F9 DE=0001   ; read FAT
DSKIO A=00 CY=0 B=01 C=F9 DE=0007   ; read root dir
DSKIO A=00 CY=1 B=03 C=F9 DE=0001   ; WRITE FAT copy 1
DSKIO A=00 CY=1 B=03 C=F9 DE=0004   ; WRITE FAT copy 2
DSKIO A=00 CY=1 B=01 C=F9 DE=0007   ; WRITE root dir
DSKIO A=00 CY=1 B=01 C=F9 DE=001A   ; WRITE data cluster
```

This is precisely the read/write + FAT-walk sequence zerobas-disk already
implements internally (`fat_mount`/`fat_find`/`fat_read_file_sector` and the
`fat_alloc_cluster`/`fat_write_fat_entry`/`fat_dir_*` write-back substrate). The
difference is *who* drives DSKIO: the loader, not the disk ROM.

---

## 4. The two delegation directions — loader-scoped contract

### 4a. Provider direction (1.5b) — real BASIC/DOS drives zerobas-disk

A real Disk BASIC / MSX-DOS host expects an "AB" disk ROM that, at **INIT**:

1. installs the standard hooks via the **RST 30h / slot-byte / RET** idiom — at
   minimum **HPHYD ($FFA7) → DSKIO** so PHYDIO reaches our sector engine, and
   (for full DOS) **HDSKO ($FDEF)** etc.; and
2. publishes the standard sector interface at the fixed offsets (**DSKIO $4010**,
   **DSKCHG $4013**, **GETDPB $4016** are the loader-bearing three — GETDPB must
   return a real DPB here, unlike zerobas's internal path).

**Minimal provider surface:** make zerobas-disk install the HPHYD hook at INIT
(it already has DSKIO + DSKCHG; GETDPB is currently a stub and must be made real
for the provider direction). The FCB BDOS at `$F37D` is *not* part of the
standard host contract and is not needed for this direction.

### 4b. Host direction (1.5c) — zerobas-BASIC drives a foreign disk ROM

zerobas-BASIC's loader verbs must reach the in-slot disk ROM's **DSKIO ($4010)**
(read & write) and own the FAT12/dir logic themselves:

1. locate the disk ROM slot via the INIT scan (already done — `DISKSLOT`);
2. call **DSKIO ($4010)** cross-slot via **CALSLT ($001C)** with the register
   convention in §3, `CY` selecting read/write;
3. (optionally **GETDPB ($4016)** for geometry, OR keep deriving geometry from
   the BPB as zerobas does today — geometry-agnostic, so DSKIO alone suffices);
4. run the existing FAT12 read/write substrate against DSKIO instead of against
   the private `bdos_entry`.

**Minimal host surface:** a thin shim that swaps the loader's current
`bdos_call` (CALSLT `bdos_entry` at `$F37D`) for `CALSLT $4010` with the DSKIO
register convention. The FAT12/dir engine moves from disk-ROM-side to
loader-side (or is shared) — but it already exists and is oracle-confirmed.

---

## 5. Go / No-go

**GO — clean loader-scoped delegation is feasible**, and is *simpler* than
feared because the loader path is pure PHYDIO/DSKIO, not the DEVICE-expansion
file-channel protocol (which is poorly documented and which the loader verbs do
not touch).

Implementation surface:

* **1.5b provider:** install **HPHYD→DSKIO** at INIT (RST 30h idiom, slot byte
  computed from the INIT slot id); make **GETDPB** real. Small, well-sourced.
* **1.5c host:** retarget the loader's cross-slot call from `bdos_entry` to
  **DSKIO $4010** with the §3 convention; relocate the (already-built) FAT12
  read+write engine to the loader side.

Likely-hard parts:

* **SAVE/write delegation** is the FAT12 write-back sequence (alloc cluster →
  write FAT copies → write dir entry → write data). zerobas-disk already
  implements and oracle-confirms this against MSX-DOS 1; reusing it against a
  foreign ROM's DSKIO `CY=1` path is mechanical, but **multi-FAT-copy sync and
  dir-entry stamping must match what a real host expects** (the SAVE trace shows
  both FAT copies written — DE=0001 and DE=0004).
* **GETDPB** for the provider direction is the one genuinely new clean-room
  item: the DPB field encoding (dir mask/shift, cluster-count encoding) was
  flagged not-cleanly-sourceable in §DPB. It is **not** needed for the host
  direction (DSKIO + BPB suffice), so 1.5c can land without it; only 1.5b needs
  it, and only if a real DOS host calls GETDPB (BLOAD/SAVE on the host side
  showed GETDPB *is* called by Disk BASIC, so the provider must answer it).

No blockers that change the committed Depth-A plan.

---

## 6. Oracle inventory

| Use | Machine / ROM | Status |
|-----|---------------|--------|
| (a) **Observation** of a real standard Disk BASIC | `National_CF-3300` (`cf-3300_disk.rom`, 16 KB, present & ungzipped in `~/.openMSX/share/systemroms/`) | **Available** — used for this spike. WD2793 / National connection style, true MSX1. |
| (b) **Host-direction test** (foreign disk ROM + zerobas-BASIC) | needs a `*_BASIC_DISK` machine whose slot-3-1 ROM is a *foreign* ROM (e.g. `cf-3300_disk.rom`, or `vg8235_disk.rom`/`nms8250_disk.rom`, both present gzipped). | **Gap (small):** the current `C-BIOS_MSX1_BASIC_DISK` machine wires *zerobas's own* `disk.rom`. The install script's `--disk-rom` can point at a foreign ROM to build this variant — straightforward, no new tooling. |
| (c) **Provider-direction test** (real BASIC/DOS + zerobas-disk image) | real MSX-DOS 1.03 on `National_CF-3300` (already used by `disk_probe_bdos.py` / `disk_probe_fwrite.py`); a zerobas-disk-written `.dsk` mounted under it. | **Available** — the existing FCB differential already mounts zerobas-written images under real MSX-DOS. For the *hook/DSKIO* provider contract, the same machine drives PHYDIO once zerobas-disk installs HPHYD. |

**Confirmed:** a foreign standard disk ROM (CF-3300's) can be combined with
zerobas-BASIC for the host-direction test (just rebuild the machine with
`--disk-rom cf-3300_disk.rom`), and a real MSX-DOS host already mounts
zerobas-disk images for the provider-direction test.

---

## 8. The CONTROL-FLOW half of the protocol (measured 2026-09-19)

§§2–3 pin the *transport*: which hooks exist, the install idiom, and DSKIO's
register contract. They do not say **who drives whom**, and that is the half a
faithful re-implementation actually has to match. It is now measured — see
`disk/docs/spec-diskcode-eviction.md` §6.6r/§6.6s (which cells, how often) and
**§6.6u** (who calls whom), from `scratchpad/hookcount_probe.py` and
`scratchpad/loadproto_probe.py`.

The shape of a reference `LOAD`, in one line: **main calls one hook cell once,
and the disk ROM does everything else on its own side.**

* main (page 1) calls the verb cell `$FE67` — once, whatever the file size;
* control crosses to the disk ROM, which runs mount, directory search and the
  **entire sector loop** there: every per-sector entry's caller is in the disk
  ROM, at 3 data sectors and at 29 alike;
* the disk side makes 8 outward inter-slot calls (mount traffic — the count does
  not scale with sectors) and **every one targets its own slot**;
* **no disk→main crossing occurs at either public inter-slot entry** (`$0030`
  CALLF, `$001C` CALSLT) for the whole verb;
* `$FE5D` and `$FE76` are also entered during a `LOAD`, but their callers are in
  MAIN — they are main-side steps in the same statement, not callees of the
  disk-side handler.

⚠️ **Still unmeasured:** the register contract AT the crossing (what main puts
in which register before calling `$FE67`, and what it expects back), and whether
`SAVE`/`MERGE` share the shape. Those are the next things a faithful
implementation needs.

---

## 7. Clean-room statement

All disk-ROM behaviour here was obtained by **black-box observation**: setting
openMSX breakpoints on documented hook addresses and reading the live Z80
register file / system work areas. The reference disk ROM's code bytes (slot 3-1
$4000–$7FFF) were never captured, read, or disassembled. Every address and
register convention is cited to the MSX2 Technical Handbook, the public MSX hook
table, or such observation. No implementation code was written for this spike;
no commit was made.
