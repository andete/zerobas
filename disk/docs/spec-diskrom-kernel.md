<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Behavioural spec: the MSX-DOS-1 disk-ROM kernel ABI

The interface surface a stock `MSXDOS.SYS` depends on from the disk ROM when it
boots — the **in-ROM kernel entry points** it hard-codes, and the **resident RAM
work area** the disk ROM's INIT builds for it. The MSX2 Technical Handbook
documents the six standard disk-ROM BIOS entries (`$4010` DSKIO … `$401F`) but
**omits the `$4022+` kernel region**; this spec is the clean-provenance reference
for that omitted region, which does not exist in any published source.

Derived **entirely from this project's own black-box oracle observation** of real
machines — never from any disk-ROM, `MSXDOS.SYS`, or `COMMAND.COM` disassembly.
Each contract below names the probe (`probes/disk/*.py`) that established it; the
full investigation trail (including refuted hypotheses, omitted here) is the
notebook [`provider-oracle-scope.md`](provider-oracle-scope.md) `§8.x`. This is
the implementer-facing distillation — the settled contracts only — and a
first-class deliverable usable independently of zerobas's code.

> **Scope / status.** Documents the contracts that are **settled** (oracle-
> confirmed, reimplemented in [`../disk.asm`](../disk.asm), regression-green). The
> live frontier — the work-area cells and entries not yet settled — stays in the
> notebook until it settles (see [§ Frontier](#frontier-not-yet-settled)). The
> implementation is gated, on the real-hardware boot path only, behind an
> `$FF`-uninitialised / real-CF-3300 guard; on the C-BIOS hosts (which never boot
> DOS) the gate skips and behaviour is unchanged.

## Clean-room basis: a cross-vendor de-facto-standard ABI

The entries `MSXDOS.SYS` hard-codes are **not** one vendor's private internals.
A PROVENANCE byte-comparison (file **identity only**, never disassembly) of seven
vendors' disk ROMs — National CF-3300, Spectravideo SVI-738, Daewoo DPF-550,
Philips VG-8235 + NMS-8245, Sony HB-F500P, Panasonic FS-4600 — found
(`disk_probe_diskrom_crossvendor.py`; see [`oracle-artifacts.md`](oracle-artifacts.md) →
"Cross-vendor disk-ROM set"):

- the ROMs differ **17–36 %** overall — independent implementations, not copies;
- **~63 % of each ROM is a byte-identical shared block** (largest `$4768–$576F`,
  4104 bytes) — a shared ASCII/Microsoft MSX-DOS-1 kernel, industry-wide;
- **`$4030`, `$50A9`, and `$5454` all fall inside that shared region.**

So these are genuine **cross-vendor de-facto-standard entries**, the same
legitimacy class as the published `$4010` DSKIO / `$4016` GETDPB. Reimplementing
their **contracts** (address + register/side-effect behaviour) with our own code
is clean ABI work; the bytes behind them are never read or copied. The surface is
**bounded** to the shared-kernel entries the kernel actually calls.

---

## 1. Kernel entry points (the disk ROM stays mapped in page 1 throughout boot)

Under MSX-DOS, page 1 (`$4000–$7FFF`) holds the disk ROM (slot 3-1) while the
kernel runs, so these are reachable exactly as the standard `$4010` entry is.

### 1.1 `$4030` — return the resident work-area pointer

| | AF | BC | DE | HL | IX | IY |
|---|---|---|---|---|---|---|
| in  | — | — | — | (ignored) | (ignored) | — |
| out | preserved | preserved | preserved | **work-area base** | preserved | preserved |

- **Contract.** Ignores all inputs (`HL` and `A` swept across seven vectors,
  output invariant — `disk_probe_dosboot_4030.py --sweep`). Returns a **constant
  pointer** in `HL`; preserves `AF/BC/DE/IX/IY`; writes nothing in `$F100–$F3FF`.
  Semantics: "get work area." Implementation is `ld hl,<base> / ret`.
- **The returned value is load-bearing — it places the kernel.** `MSXDOS.SYS`
  relocates its resident kernel so that the kernel **TOP = this pointer** and the
  base sits `$067A` below it (invariant `DE − HL = $067A` on stock and Tier-1 —
  `disk_probe_dosboot_ramtop.py`). It is therefore **`$4030`'s return — not the
  DRVTBL reserved-top field, not HIMEM — that selects kernel placement.** zerobas
  returns `$DD0E` (the stock value) so the kernel lands at `$D606`, clear of our
  high-RAM scratch.

Probes: `disk_probe_dosboot_4030.py`, `disk_probe_dosboot_ramtop.py`.

### 1.2 `$50A9` — drive / work-area setup, returning the work-area pointers

| | AF | BC | DE | HL | IX | IY |
|---|---|---|---|---|---|---|
| in  | — | preserved | `$DC80` | `$D606` (kernel base) | `$F195` | `$C0AB` (FCB) |
| out | **`A=$00`, Z set** (`F=$42`) | preserved | **`$F1AA`** | **`$F359`** | **`$F1AA`** | preserved |

- **Side effect:** one persistent write, `$F242 := $00`. No other non-stack write.
- **Contract.** Returns `A=0`/`Z`; sets `DE = IX = $F1AA` and `HL = $F359` (both
  point into the resident work area: `$F1AA` = drive-B DPB, `$F359` = `DRVTBL+$11`);
  preserves `BC` and `IY`. Returns to the caller (`$D7CE`), which consumes the
  pointers. A minimal faithful body: `sub a` (yields `A=$00`,`F=$42` exactly) /
  store `$00` to `$F242` / load the three return registers / `ret`.

Probe: `disk_probe_dosboot_50a9.py`.

### 1.3 `$5454` — CONOUT (console character output)

- **Contract.** Output the character in **`A`** via the BIOS CHPUT path,
  preserving `BC/DE/HL/IX/IY`. The kernel calls it to emit the MSX-DOS sign-on
  banner (first call `A=$0D`, the leading CR). Black-box call-chain on the stock:
  `$5454 → $408F → $40B1 → $001C` (CALSLT) → resident kernel → `$F38C/$F398` →
  `$00A2` (CHPUT).
- **Baked-in, not relocated.** `CD 54 54` (`CALL $5454`) is present in the
  pristine just-loaded `MSXDOS.SYS` image and unchanged at call time — a hard
  immediate, confirming `$5454` is a fixed entry address, not a relocated vector.
- **zerobas status (§8.39).** The entry is placed at `$5454` (a `ds`-fill in the
  ROM's free tail, like `$4030`/`$50A9`). The current body is a **first cut: a
  register-preserving `RET` that emits nothing** — sufficient to clear the derail,
  which alone collapses the boot's BDOS calls 21→3 (stock parity) and breaks the
  warm-boot loop. Emitting the character (the full contract above, via our CALLF
  console path) is the remaining refinement; until then the banner/prompt produce
  no visible output, so `A>` is confirmed behaviourally, not on screen.

Probes: `disk_probe_dosboot_pctrace.py`, `disk_probe_dosboot_entries.py`,
`disk_probe_dosboot_bdos_contract.py`.

---

## 2. The resident work area (`$F100–$F3FF`) — built by disk-ROM INIT

On a stock machine the disk ROM's INIT populates this always-mapped page-3 RAM
before the boot reads it (stock = ~3 % `$FF`; an un-built clone = ~76 % `$FF` —
`disk_probe_dosboot_workarea.py`). It is a mix of **data** (pointers, per-drive
DPBs) and small **resident routines** the kernel calls at fixed addresses. The
cells below are settled; build them in INIT under the same host-adaptive `$FF`
gate.

### 2.1 `RAMAD0–3` (`$F341–$F344`) — page-3 RAM slot id

After `$4030` the kernel reads `RAMAD` ~84× to page RAM into page 0 (where the
page-0 BIOS ROM was). The base BIOS sets only `EXPTBL`; **filling `RAMAD` is the
disk ROM's INIT job.** Derive the page-3 RAM-slot id (`F000SSPP` form — primary
from `$A8`, expand flag from `EXPTBL`, subslot from `$FFFF`) and write all four
bytes, **gated on `$FF`** so a host that already set them is untouched. Absent
this, page 0 reads `$FF` (unmapped slot) → `RST 38h` slide. Probe:
`disk_probe_dosboot_lowstore.py`.

### 2.2 `$F340` — INIT-complete flag

One byte below `RAMAD0`. The kernel reads it (`LD A,($F340) / AND A / CALL Z,…`)
to branch into normal init; **`$00` = proceed**. The disk ROM clears it; clear it
in INIT (`xor a / ld ($F340),a`). Left `$FF`, the kernel takes the derail branch.
Probe: `disk_probe_dosboot_bdos_contract.py`.

### 2.3 `$F348` DRVTBL — drive table

16-byte structure the disk ROM builds (write-watch: every meaningful write comes
from page 1, the disk ROM — `disk_probe_dosboot_drvtbl.py`). `$95`-low-byte
word layout:

| offset | field | meaning |
|---|---|---|
| `+0`  | `$87` | disk-interface slot id (slot 3-1, expanded form) |
| `+1`  | word  | top-of-reserved-RAM (HIMEM) |
| `+3`  | word  | the `$4030` work-area pointer |
| `+5/+7/+9` | word | driver-routine pointers (DPB-class) |
| `+11` | `$0000` | unused entry |
| `+13` | word  | driver-routine pointer (stock: the drive-A DPB `$F195`) |
| `+15` | `$AA` | sentinel / next-entry head |

Read by a single consumer at PC `$0368`. **Note:** `+1` (reserved-top) is *not*
the kernel-placement lever — `$4030`'s return is (§1.1). zerobas builds the table
with our own slot id and pointers into our own code/work area; the `$EB95–$F195`
high-RAM trampoline bytes are never read.

### 2.4 `$F368–$F37C` — segment-switch jump table

Seven slots the kernel calls as resident RAM-segment-switch hooks. On a memory-
mapper machine they page a segment; on a plain 64K machine (e.g. CF-3300) they are
**register/flag-transparent `RET` no-ops** with zero RAM/FDC/IO side effects
(`disk_probe_dosboot_f368.py`). Of the eight only `$F368`/`$F36B` are ever called.
Build `JP <ret-stub>` into `$F368–$F37A`; **leave `$F37D` = `JP bdos_entry`** (the
SYSTEM entry, already zerobas's). Our own `RET`; the stock's `$DFxx` targets are
never read.

### 2.5 Per-drive DPBs — `$F195` (drive A), `$F1AA` (drive B)

The work area holds a Disk Parameter Block per drive at these fixed addresses
(`$F1AA = $F195 + $15`). `$50A9` (§1.2) hands the kernel `IX=$F1AA`; the boot
handoff (§3) hands it `IX=$F195`. Build the drive-A DPB by calling our own GETDPB
(`$4016`) on the inserted disk's BPB — validated byte-identical to the stock
(`$F195` = `00 f9 00 02 0f 04 01 02 01 00 02 70 0e 00 ca 02 03 07 00`,
`disk_probe_dosboot_dispatch.py`).

### 2.6 `$F1C9` — resident `$`-terminated string-output helper

A resident routine the kernel CALLs to print a `$`-terminated string (`DE` →
string), routing each character through the console primitive (ultimately CONOUT,
§1.3). Absent (left `$FF`), the kernel runs the cell as `RST 38h` and derails.
Install our own clean-room body. Probe: `disk_probe_dosboot_resident.py`.

### 2.7 `$F24E–$F2FD` — `RET` stub table

The disk ROM fills this region with `$C9` (RET) — segment-bank hooks the kernel's
directory/FAT code CALLs around each step (write-watch: filled from page 1 PC
`$57D6`; no real `JP`s written — `disk_probe_dosboot_dispatch.py`). On a 64K
machine they are no-ops. Fill with `$C9` (our own constant, never stock bytes).

---

## 3. Boot handoff — registers at `MSXDOS.SYS` entry (`$0200`)

`MSXDOS.SYS` keeps and dereferences certain registers from the moment the boot
sector hands control to it; the boot path must set them (the boot sector preserves
them to entry, measured — `disk_probe_dosboot_pctrace.py`):

| reg | value | role |
|---|---|---|
| `IX` | drive-A DPB pointer (`$F195`) | dereferenced as the DPB for directory / file reads |
| `BC` | byte count (`$0980` = the `MSXDOS.SYS` file size) | consumed by an init sign-branch at `$024A` |

A wrong `IX` → garbage DPB → the "Insert DOS disk" error path. A zero `BC` → the
`$024A` sign branch goes the wrong way → a derail loop. (`BC` is set by the
loader, not a static handoff — it comes from the RDBLK return, §4.)

Probes: `disk_probe_dosboot_dispatch.py`, `disk_probe_dosboot_bdos_contract.py`.

---

## 4. DSKIO (`$4010`) contract refinements exercised under DOS

The standard `$4010` DSKIO entry is documented (MSX2 TH); these additional
behaviours are what the DOS boot path requires and were oracle-confirmed here:

- **Success returns `B = 0`** ("all sectors transferred"). The kernel checks it.
- **BDOS RDBLK (`$27`) returns the record count in *both* `HL` and `BC`** (stock
  `$0980`). zerobas's `bdos_rdblk` must set `BC = HL` (`disk_probe_dosboot_bdos_contract.py`).
- **Page-1 transfer destinations need a bounce.** When DSKIO's target buffer falls
  in page 1 (`$4000–$7FFF` = the disk ROM under DOS), a direct `ld (hl),a` writes
  to ROM and is lost. Read into a page-3 buffer, then a page-3-resident blit
  briefly remaps page 1's sub-slot to RAM, `LDIR`s the sector to the real target,
  and restores the slot (`disk_probe_dosboot_dskio_exit.py`).
- **FDC transfers must mask interrupts.** The polled-DRQ transfer (and the page-1
  blit) underrun → LOST DATA if a 50 Hz VDP interrupt preempts the tight loop once
  `COMMAND.COM` runs `EI`. Bracket the FDC transfer and the blit with an
  IFF-preserving DI guard (`di` on entry; `ei` on exit only if the caller had
  interrupts enabled). The masked boot phase is unaffected
  (`disk_probe_dosboot_fdc.py`).

---

## Frontier (not yet settled)

Tracked in [`provider-oracle-scope.md`](provider-oracle-scope.md); promoted here
only once each settles (per the settle-gated cadence in
[`../../docs/documentation-deliverable.md`](../../docs/documentation-deliverable.md)):

- **`$5454` CONOUT real output** — the entry is *placed and unblocks the boot*
  (§1.3 status; §8.39), but the first-cut body emits nothing. Promoting the full
  output behaviour waits on the console path settling; the contract itself (§1.3)
  is already settled and documented.
- **Hosting the proprietary COMMAND.COM to `A>` — quantified scope (§8.41): the
  whole 63% shared kernel, not a bounded entry.** The `$4462`/`$544E` ×~24k spin is
  a *downstream symptom* of `$47B2` (the real first divergence: stock `$47B2`=`XOR
  A` runs the load routine; ours bails). But a boundary probe
  (`disk_probe_dosboot_47b2.py`) shows the `$D821→$47B2→$D824` span runs **371,384
  instructions** and **executes COMMAND.COM itself at `$0100`** (sub-entry `$607B`,
  `ra=$0100`) — it is *the entire COMMAND.COM load + shell init*, calling **21
  disk-ROM sub-entries across `$41xx–$77xx`** (12 shared-kernel, 16 colliding with
  our active code `<$50B7`, only `$4010` DSKIO correct). So reaching `A>` this way ⇒
  contract-reimplementing essentially the whole shared MSX-DOS-1 disk kernel at its
  exact internal addresses — a major project, distinct from this spec's settled
  BIOS-ABI work (`$4010–$401F`, GETDPB) and Disk-BASIC. Not walled (each target is a
  black-box contract, the `$5454` playbook ×~12 + code relocation), but the cost is
  now measured. Whether to undertake it is a scope decision, not a settle gate.
  Probes: `disk_probe_dosboot_47b2.py`, `disk_probe_dosboot_entries.py`,
  `disk_probe_dosboot_pctrace.py` (`--arm $D7FA`).
- **The remaining `$F100–$F3FF` cells** the kernel reads to reach a real
  `COMMAND.COM` load and `A>` (`$F100–$F17C` driver-dispatch region, the `$F327`
  routines, the `$F1F0–$F1FF` device table). Each is being characterised and built
  incrementally, re-trapping after each piece.

## Reproducing

Every contract above is reproducible from the named probe under
[`../../probes/disk/`](../../probes/disk/) against the oracle machines (stock
`National_CF-3300`; Tier-1 `National_CF-3300_ZEROBASDISK`; a real MSX-DOS 1 disk).
The probe corpus is part of this deliverable: the contracts are *measurements*, and
the probes are how anyone re-takes them. See
[`../../docs/openmsx-harness.md`](../../docs/openmsx-harness.md) for running them
and [`oracle-artifacts.md`](oracle-artifacts.md) for the validated oracle set.
