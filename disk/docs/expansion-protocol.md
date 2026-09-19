<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# zerobas disk expansion protocol — pinned spec (Phase 1.5 research spike)

Status: **research spike output, not yet implemented.** §§1–6 are the Phase-1.5
spike (the TRANSPORT: header, hooks, DSKIO). **§8 is a later and separate body of
work (2026-09-19): the CONTROL FLOW** — who calls whom, with what, and what comes
back — consolidated from eleven measured sections of
`disk/docs/spec-diskcode-eviction.md`. Read §8 for how `LOAD` actually works.

This document pins the
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

## 8. How `LOAD` actually works on the reference — the consolidated protocol

**Status: synthesis, 2026-09-19.** §§1–3 pin the *transport* — the extension-ROM
header, which hooks exist, the install idiom, DSKIO's register convention. They
do not say **who drives whom**, and that is the half a faithful re-implementation
has to match. This section is the answer, consolidated from eleven working
sections of `disk/docs/spec-diskcode-eviction.md` (§6.6r–§6.6aa) written as the
measurements were made, several of them correcting earlier ones.

> 🔴 **HOW TO READ THIS.** Claims are separated into **measured**, **inferred**
> and **not measured**, and the measured ones name their instrument and the
> control that makes them believable. A claim with no control named is not one
> you should build on. §8.7 lists the retractions that are still live, so nothing
> here re-imports a corrected claim.

It is placed before §7 deliberately: the clean-room statement closes the document.

---

### 8.1 A hook cell is only a crossing if it is CLAIMED

A claimed cell holds `F7 <slot> <lo> <hi> C9` (§2); an unclaimed one holds a bare
`C9`, and BASIC calls it anyway — it returns and **nothing crosses**. After boot,
**35 of the 118 published slots are claimed**, identical across every case
measured.

🔴 **An entry counter cannot tell the two apart.** An offered extension point
nobody took and a real inter-slot handover are both "entered once". Four of the
cells this project's analysis had been built on are bare `RET`s: `$FE67`, `$FE6C`
and both per-sector cells. Read a cell's five bytes before calling it an entry,
a boundary or a crossing.

*Measured: §6.6v, `scratchpad/crossabi_probe.py`. Control: the claim state is
read directly, and independently corroborated by an entry/exit asymmetry — an
unclaimed cell shows entries and no exits, because its `C9` at offset 0 returns
before offset 4 is reached.*

### 8.2 The crossing is `$FE5D`, and it carries a MODE, not a verb

Main calls the claimed cell `$FE5D` — once per file operation, whatever the file
size. It is the cell every file verb enters and the only one that pairs entry
with exit. The register contract at that instant:

| register | what it carries |
|---|---|
| `DE` | the **MSX open-mode code**, all four classic values measured (§6.6ab): `$0001` INPUT (`LOAD`, `MERGE`, `BLOAD`, `OPEN…FOR INPUT`) · `$0002` OUTPUT (`OPEN…FOR OUTPUT`, `BSAVE`, `SAVE"…",A`) · `$0004` RANDOM (`OPEN "f" AS #n`) · `$0008` APPEND · and `$0080` for **tokenised `SAVE` and nothing else** |
| `HL` | the **file buffer** — `$DC65` for every program verb, `$DD6E` for every `OPEN` channel (ten verbs, §6.6ab) |
| `BC` | `$F871` — one past the end of the file-name block at `$F864..$F870`; for `BSAVE` it is the START ADDRESS as typed (§6.6ab) |
| `AF` | invariant across every verb |
| `IX`, `IY` | vary; no interpretation this measurement supports |

🔴 **There is no verb selector.** `LOAD`, `MERGE` and `BLOAD` arrive with the same
cell, the same `DE` and the same `HL`. The reference opens file buffer 0 in a
mode; verb-level difference is carried by *which other claimed cell* is entered
and by what main does around the call.

⚠️ `$F41F` holds the statement's BASIC token at this instant (`$B5` `LOAD`, `$B6`
`MERGE`, `$BA` `SAVE`, `$B0` `OPEN`) and is **not** the selector — 13 reads, all
from main, none inside the crossing. It is main's own bookkeeping.

*Measured: §6.6v, §6.6w, `scratchpad/crossabi_probe.py` and
`scratchpad/selector_probe.py`. Controls: a timing arm proving the capture
happens before the crossing runs; a read watchpoint proving who consumes
`$F41F`; a determinism arm proving two runs of one case are byte-identical.*

### 8.3 The disk ROM owns everything from there

Control crosses and the disk ROM runs mount, directory search and the **entire
sector loop** on its own side. Every per-sector entry's caller is in the disk
ROM — **16 of 16** at 3 data sectors, **68 of 68** at 29 — each at a stack depth
below the verb entry.

The disk side makes **8** outward inter-slot calls, every one to its own slot,
and the count does **not** scale with sectors (8 at 3, 8 at 29), so they are
mount traffic.

**There is no hand-back.** Across the crossing the page-1 selection changes
exactly three times — `0-0` → `3-1` → `0-0` — with **zero**
`DISK → elsewhere → DISK` excursions. The disk ROM is paged in once and stays.
⚠️ That is a claim about which ROM is *visible*; an inter-slot trampoline
switches slots too, so visibility and execution are different statements.

*Measured: §6.6u (`scratchpad/loadproto_probe.py`) and §6.6aa
(`scratchpad/slotswitch_probe.py`). Controls: a caller whose region is known a
priori (`H.TIMI`'s is main page 0, 2244/2244); and a known-answer pair — page 1
must read MAIN at the crossing's entry and DISK somewhere inside it.*

### 8.4 The shared work area — the interface surface

**What the disk side reads.** 38 distinct cells during a `LOAD`, 36 during a
`SAVE`, **36 of them shared**; `LOAD` adds exactly two and `SAVE` adds none. Both
make **480** disk-side reads in the band.

**What the disk side writes.** 22 cells during a `LOAD` and 16 during a `SAVE`,
**each exactly once**. What main *sees changed* on return is 34 and 11 — a
different set, because some cells are written and restored and others are changed
by another region.

**Two 13-byte name blocks, an input/output pair.** Both are drive byte + 8.3 name
+ one trailing byte:

* `$F864..$F870` — the name main supplies. `BC` points one past it.
* `$F568..$F574` — the name the disk side publishes. It reads `.S       BAS`
  after `LOAD"S.BAS"` and `.T       BAS` after `SAVE"T.BAS"`.

The rest is small and hot: `$FB21..$FB22`, `$FB29`, `$FCC4`, `$FCC8`, and the
word at `$FD73..$FD74`.

`$FC9E` (the documented JIFFY timer) and `$FCA2` change in both verbs and are
written only from main page 0 — the 60 Hz interrupt, which runs throughout.

⚠️ **Scope.** This is the shared work area `$F380..$FFFF` only. The disk ROM's
private RAM below `$F380` is excluded by design — internal state, not interface.

*Measured: §6.6x (`scratchpad/diskreads_probe.py`) and §6.6y
(`scratchpad/diskwrites_probe.py`). Controls: SP lies outside the watched band,
so these are work-area accesses and not push/pop traffic; the log ceiling was not
reached, so each set is complete rather than a prefix; and **every changed cell
has a recorded writer** — an orphan would mean the watchpoint is blind and every
"the disk side does not write this" reading unfounded.*

### 8.5 Part of the protocol executes from RAM

Five clusters of code run from RAM during the crossing, **all below `$F380`** —
which is why the work-area probes could report a writer "in region RAM" and not
say where it lived:

| range | span | fetches |
|---|---|---|
| `$F1D9..$F1E1` | 9 B | 582 |
| `$F1F4` | 1 B | 2 |
| **`$F255..$F2A3`** | **79 B** | 45 |
| `$F365..$F36B` | 7 B | 196 |
| `$F38C..$F399` | 14 B | 520 |

The last matches the stub `scratchpad/cf_trace.py` located empirically and
labelled CLPRIM — and 🔑 **it is the one cluster with NO disk-side writer**
(§6.6ac), which two independent routes agree on. ⚠️ Clusters bridge gaps of up to
16 B — operands are fetched as data and a `jr` skips forward — so the spans are an
upper bound on extent, not a measured routine size.

➡️ **The DISK ROM installs four of the five, ~96 B of span** (9 + 1 + 79 + 7).
Every one is written well before the first file operation — the latest write to
any cluster is t≈14.00 against a crossing at t≈164.03 — and none is rebuilt per
call. ⚠️ Two are written more than once during boot, so "installed at INIT" is
too narrow: the disk side touches them again later in the boot sequence.

🔑 **The disk ROM installs the 79-byte block at boot.** Writes to `$F255..$F2A3`
come from main page 0 at t≈0.372, main page 1 at t≈1.191 and **the disk ROM at
t≈3.798**; the crossing itself is at t≈164.03. Every write precedes the crossing
by ~160 emulated seconds, so the block is installed once and is **not** rebuilt
per call.

*Measured: §6.6z (`scratchpad/ramcode_probe.py`). Control: an execution detector
(`wp_last_address == PC` selects opcode fetches) validated by a known-answer pair
— `$FE5D` holds `F7` and must appear; the read-only name block at `$F864..$F870`
must not.*

### 8.6 A `LOAD`, end to end

1. Main executes the tokenised `LOAD`. `$F41F` holds the statement token — main's
   own record, never read by the disk side.
2. Main places the file name in FCB form at `$F864..$F870` and sets `BC` one past
   it, `HL` to the file buffer, `DE` to the open mode (`$0001`, a read).
3. Main calls `$FE5D`. Page 1 is main at this instant.
4. The cell's `F7 <slot> <lo> <hi> C9` crosses; page 1 becomes the disk ROM.
5. The disk ROM does mount, directory search and the whole sector loop on its own
   side, reading 38 shared work-area cells (480 reads) and making 8 outward
   inter-slot calls to its own slot. Code in five RAM clusters installed at boot
   runs alongside it.
6. The disk side writes 22 work-area cells, each once, publishing the resolved
   name at `$F568..$F574`.
7. Control returns through the cell's trailing `C9`; page 1 returns to main. Main
   sees 34 cells changed.
8. **After** the crossing closes, main enters `$FE76` — claimed, one-way, and
   specific to the binary-format program path: tokenised `LOAD` enters it; ASCII
   `LOAD`, `MERGE`, `SAVE` and `BLOAD` do not.

### 8.7 Live retractions — do not re-import these

| claim | status |
|---|---|
| "`$FE67` is the shared verb entry" (§6.6s) | 🔴 **retracted** by §6.6v — `$FE67` is a bare `RET` |
| "main hands `LOAD` over at `$FE67`" (§6.6u) | 🔴 **cell corrected** to `$FE5D` by §6.6v; the shape was right |
| "its sector loop is driven from outside the hook" (§6.6r) | 🔴 **retracted** by its own author; answered by §6.6u — the loop is inside the disk ROM |
| "per-sector largely dissolves the buffer-aliasing hazard" (§6.6r) | 🔴 **withdrawn** — premised on main keeping the loop, which it does not |
| "`$FE76` is entered between `$FE5D`'s entry and exit" (§6.6v) | 🔴 **retracted** by §6.6aa — an artefact of a probe printing entries and exits by category rather than in time order |
| "H.BINL is `BLOAD`'s cell" (public name) | 🔴 **refuted**, then **refined** — it marks the binary-FORMAT path |

### 8.8 Inferred, not measured

* That the two 13-byte blocks are FCB-style **drive byte + 8.3 + one trailing
  byte** is read off their contents and their size, not from any specification.
* That main page-0 activity during the crossing is the 60 Hz interrupt is
  strongly supported (`$FC9E` is the documented JIFFY) but was not isolated by
  disabling interrupts.

### 8.9 Not measured

* 🟢 **PARTLY ANSWERED (§6.6ab).** `DE` is the MSX open-mode code and all four
  classic values are measured (1/2/4/8). `$0080` is not "a write" (three other
  writes use `$0002`), not "binary" (`BSAVE` uses `$0002`) and not "not-ASCII"
  (`BLOAD` uses `$0001`): among ten operations it is used by **exactly one**, the
  tokenised program `SAVE`. ⚠️ What it MEANS is still not determined.
* What `IX` carries at the crossing (`IY` reads `$0000` for `BLOAD` and every
  `OPEN`, and `$00D0` for `BSAVE"…",&HD000,…`, but that is not enough to name it).
* 🟢 **ANSWERED (§6.6ac):** four of the five clusters are written by the disk
  ROM (~96 B of span); the fifth, `$F38C..$F399`, has no disk-side writer and is
  the BIOS's inter-slot stub.
* What any of the RAM-resident code **does**. 🔴 And it must stay that way: code
  sitting in RAM is reference ROM content that has merely been relocated, so
  reading its bytes would be reading the reference. Range, size, installer region
  and install time only.
* Whether `SAVE` and `MERGE` share the whole shape, or only the crossing.

### 8.10 What a faithful implementation inherits

* **One claimed cell** carrying a mode byte, not a verb dispatch — cheaper than
  the selector this project had planned for.
* **The whole loop below the boundary**: the disk side owns mount, directory and
  sector transfer for the duration of one call.
* **A shared work-area contract of ~38 cells**, nearly all common to read and
  write paths, with an input name block and an output name block.
* 🔴 **RAM-resident code installed at boot** — a *new kind* of cost. No design in
  this project has assumed it, and `wall-assertion-check` covers ROM only, so
  nothing here would have caught its absence.
* 🔴 **And the buffer-aliasing hazard is the price of the faithful shape**, not an
  argument against it: a disk side that owns the loop holds buffer state across
  the whole transfer while a BASIC statement is live.

---

## 7. Clean-room statement

All disk-ROM behaviour here was obtained by **black-box observation**: setting
openMSX breakpoints on documented hook addresses and reading the live Z80
register file / system work areas. The reference disk ROM's code bytes (slot 3-1
$4000–$7FFF) were never captured, read, or disassembled. Every address and
register convention is cited to the MSX2 Technical Handbook, the public MSX hook
table, or such observation. No implementation code was written for the Phase-1.5
spike (§§1–6); no commit was made for it.

🔴 **AND THE SAME LINE, RESTATED FOR §8'S MEASUREMENTS (2026-09-19).** They read
registers, RAM addresses, work-area RAM CONTENTS, I/O port values and the
slot-select state, at breakpoints and watchpoints on RAM addresses in the
published hook table. No ROM byte was read, no hook cell's `<lo> <hi>` was
followed, nothing was single-stepped into ROM, and nothing was disassembled.
Two further restrictions were adopted as §8's measurements got closer to the ROM:

* a register holding an address in page 0 or 1 is reported as a **region**, never
  as an address, and a slot that was not sampled is never named;
* 🔴 **the bytes of the RAM-resident code (§8.5) were never read.** Code sitting
  in RAM is reference ROM content that has merely been RELOCATED, so reading it
  would be reading the reference. Its address range, size, installer region and
  install time are measured; its contents are not.
