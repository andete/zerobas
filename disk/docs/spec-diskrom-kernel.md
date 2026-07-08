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

> **Scope / status.** §1–4 document the kernel-entry / work-area / handoff /
> DSKIO contracts; §5 documents the **`COMMAND.COM` load phase**, which is now
> **implemented** — MSX-DOS 1 boots to a visible `A>` on zerobas-disk with full
> BDOS parity (goal MET 2026-07-03). §6 documents the **BDOS-in-ROM function
> surface** the running shell then drives. All settled contracts are reimplemented
> in [`../disk.asm`](../disk.asm) (+ `fat.asm`/`kernel.asm`/`runtime.asm`/
> `driver.asm`) and guarded by standing gates (`make bdos-acceptance`,
> `diskbasic-acceptance`, `bdos-cbios-selfcheck`, `unit-test`). The DOS-path
> implementation is gated, on the real-hardware boot path only, behind an
> `$FF`-uninitialised / real-CF-3300 guard; on the C-BIOS hosts (which never boot
> DOS) the gate skips and behaviour is unchanged.
>
> This document was assembled by a **notebook → product-spec harvest** (the
> [`../../docs/documentation-deliverable.md`](../../docs/documentation-deliverable.md)
> settle-gated cadence): §1–5 are the boot-path ABI; §6 the BDOS surface; §7 the
> work-area construction; §8 the C-BIOS seam rules; §9 the Tier-C boundary
> behaviours. See [§ Frontier / harvest status](#frontier--harvest-status) for the
> little that is still notebook-only and the go-forward cadence.

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

- **Contract.** Output the character in **`E`** via the BIOS CHPUT path,
  preserving `BC/DE/HL/IX/IY` (the MSX-DOS BDOS CONOUT, func 2, char-in-E ABI).
  Black-box call-chain on the stock: `$5454 → $408F → $40B1 → $001C` (CALSLT) →
  resident kernel → `$F38C/$F398` → `$00A2` (CHPUT).
- **Char register = E, not A (M10/§8.80, corrected 2026-06-30).** Two callers were
  observed at the veneer entry (`callseq --log 0x7922`): the early MSXDOS.SYS sign-on
  (caller `$0320`) passes the char in **both `A` and `E`** (first char `$0D`, the
  leading CR), while the relocated kernel's per-char console output (caller `$D88A`,
  the COMMAND.COM banner / date / `A>` prompt) passes it in **`E` with `A=$00`**. So
  `E` is the register common to both — register `E` spells `MSX-DOS version 1.03`
  (early) and `Sun 84-01-01` / `A>` (kernel). A veneer reading `A` therefore emits
  `$00`/garbage for ALL kernel-phase output while *appearing* to work for the early
  sign-on — the original "char in A" reading was an early-phase coincidence.
  `$5454` is the low-level CONOUT primitive; the shell's per-character output routes
  through the `$53A7` CONOUT worker (TAB-expansion + the `$F237` column cell, M22b)
  which drives `$5454`. Both now render **byte-identical to stock** across the full
  sign-on, date prompt, `A>`, and `DIR` — the earlier "open residual" is closed; see
  [§6 console tier](#61-console--misc-tier).
- **Baked-in, not relocated.** The call to `$5454` is present in the pristine
  just-loaded `MSXDOS.SYS` image and unchanged at call time — a hard immediate,
  confirming `$5454` is a fixed entry address, not a relocated vector.
- **zerobas status (§8.80, IMPLEMENTED + RENDERING).** The entry is placed at `$5454`
  (a `ds`-fill in the ROM's free tail, like `$4030`/`$50A9`) as `jp conout_body`. The
  body (`conout_body`, free tail) pages the main BIOS ROM into page 0 via the portable
  `pg0_mainrom_in` (EXPTBL[0]), `call $00A2` (CHPUT) with the char from **`E`**, restores
  page 0, EI, returns. Real ASCII now renders: `screen --machine ours --settle 12` shows
  `MSX-DOS version 1.03` / `Copyright 1984 by Microsoft` / `Sun 84-01-01` + the boot logo.
  (Evolution: §8.39 first-cut RET → §8.67/§8.68 emit-via-CHPUT, char-in-A → §8.80 char-in-E
  fix, the milestone that made output visible.)

Probes: `disk_probe_diff.py` (the differential harness — `screen` / `iowrite` / `callseq
--log 0x7922`); legacy `disk_probe_dosboot_pctrace.py`, `disk_probe_dosboot_entries.py`.

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

One byte below `RAMAD0`. The kernel reads it at PC `$0246` and branches into normal
init only when it is `$00`; **`$00` = proceed**. The disk ROM clears it; clear it
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
- **The FDC register window mirrors ×8 across `$7F80–$7FBF` — keep code out of it.**
  On the National CF-3300 the WD2793 FDC registers are decoded incompletely, so they
  appear **mirrored eight times** across the whole `$7F80–$7FBF` range (not only the
  nominal `$7FB8–$7FBF`). Any ROM *code or data* placed in that range is not a normal
  ROM read at runtime — a fetch there hits the FDC and a store is swallowed — so a
  routine that drifts into it silently fails to persist (this class caused a
  create/write P0: a handler body had drifted into the window ~M27 and file creation
  didn't stick). The window must be left as dead `$00` pad; put a build-time guard on
  its base (`FDC_WINDOW_INTRUSION` assert at `$7F80`) so nothing can reoccupy it.
- **FAT12 FAT-entry writes must split at the correct nibble/byte boundary.** A FAT12
  entry is 12 bits, so every *other* entry straddles a byte boundary; the write path
  must mask/merge the two halves at the boundary that matches the entry's parity.
  An off-by-one in the straddle boundary corrupts entries only at the clusters whose
  FAT bytes cross a *sector* edge (clusters 170/341/682 → byte index 255/511 on a
  720 KB disk) — invisible to a small-disk happy-path probe. Verified byte-exact
  against a corpus of real stock disks (`disk_fat_straddle_oracle.py`; the
  read-only-artifact oracle, [oracle-artifacts.md](oracle-artifacts.md)).

---

## 5. The COMMAND.COM load phase — kernel→disk-ROM call surface (IMPLEMENTED)

> **Genre note.** This section documents the phase that carries the boot from
> `MSXDOS.SYS` init through to the visible `A>` prompt. It is now **settled and
> reimplemented** (goal MET 2026-07-03): the loader pivot `$47B2` is our own
> `k_47B2` and the whole surface below boots byte-identical to stock, guarded by
> `make bdos-acceptance`. The material below is both the clean-provenance *map* of
> the loader's call surface and the contract our reimplementation satisfies. The
> milestone detail lives in [`tier2-m21-spec.md`](tier2-m21-spec.md) (`$4462`/
> `$47B2`) and [`tier2-m31-rdblk-randrecord-spec.md`](tier2-m31-rdblk-randrecord-spec.md)
> (RDBLK random-record); the BDOS functions the shell then drives are §6.

Once `MSXDOS.SYS`'s own init completes (the §1–3 entries + work area all
satisfied), the relocated kernel runs the **`COMMAND.COM` loader** from high RAM
(around `$D7xx`). That loader, and `COMMAND.COM` itself, drive a further cluster of
in-ROM kernel entries — the phase that ends at the `A>` prompt.

### 5.1 The pivot entry `$47B2` — "load + start `COMMAND.COM`"

The loader at `$D821` does `CALL $47B2`. On stock this call target is *the entire
`COMMAND.COM` load + shell startup*, not a discrete subroutine: a boundary probe
(`disk_probe_dosboot_47b2.py`, breakpoints on the `$D821` call and the `$D824`
return) measures the whole `$D821→$47B2→$D824` span at **371,384 instructions**, and
one of its sub-entries is `$607B` **called with `ra=$0100`** — i.e. `COMMAND.COM`
executes at `$0100` *inside* this span and calls back into the disk ROM.

- **zerobas reimplementation (`k_47B2`, [`../kernel.asm`](../kernel.asm)).** Our
  `$47B2` is a clean-room **`_RDBLK` (BDOS `$27`) body** written to the published
  `map.grauw.nl` contract (M21b landed it; M31 un-simplified it to honour the FCB
  random-record field + true count — see §6). It positions to record RR, transfers
  up to `HL` records of the FCB record size, zero-pads a final partial record, and
  reports the true count. The boot loaders that reach it pass RR=0 / record-size 1,
  so the loader contract (`HL=BC=`bytes transferred, `A=1`) falls out for them while
  a running program gets a faithful random block read.
- **Entry/exit contract (oracle-measured).** Entry (stock): `AF=$0044 BC=$FFFA
  DE=$DC5B HL=$D500 IX=$F195 IY=$EC55`; returns to `$D824` with `AF=$0142 HL=$1A00
  IY=$DC5B`, stack balanced. Ours reproduces the exit registers byte-identically
  (`capture --at 0xC51D`: zero diffs).

### 5.2 The COMMAND.COM entry environment — the loader's page-0 OUTPUT contract

`$47B2` reads `COMMAND.COM` to `$0100` and transfers control there with a
specific page-0 environment laid down. Characterising that environment is the
loader's **output contract**; it was captured black-box at the first execution of
`$0100` (`disk_probe_dosboot_page0.py`: breakpoint at `$0100`, read all 256 bytes
of page 0, decode pointers only — `COMMAND.COM` is never disassembled). The capture
is **reproducible** (register set byte-identical across two independent runs).

Registers handed to `COMMAND.COM`:

| AF | BC | DE | HL | IX | IY | SP |
|----|----|----|----|----|----|----|
| `0142` | `0980` | `0000` | `0980` | `F195` | `C0AB` | `F51F` |

`BC = HL = $0980 = 2432` is exactly the `MSXDOS.SYS` resident size — the loader
passes the kernel size, not a don't-care.

Page-0 layout at `$0100` entry — three parts:

1. **No CP/M low vectors.** `$0000-$000B` are all `$00`: there is **no warm-boot
   `JP` at `$0000` and no `JP BDOS` at `$0005`**. MSX-DOS 1 does not lay the
   CP/M-style `$0005` entry at `COMMAND.COM`'s *own* entry; `COMMAND.COM` installs
   those itself before it exec's a transient program. The default FCB (`$005C`) and
   DMA / command-tail (`$0080`) are likewise `$00` (no command line parsed yet).
2. **A 6-entry JP vector table into the relocated high-RAM kernel:**

   | addr | target | addr | target |
   |------|--------|------|--------|
   | `$000C` | `JP $DDF3` | `$0024` | `JP $DE9B` |
   | `$0014` | `JP $DE14` | `$0030` | `JP $DE42` |
   | `$001C` | `JP $DE54` | `$0038` | `JP $DDAE` (RST 38h) |

   Every target lands in the kernel's relocated `$DDxx/$DExx` band — these are the
   page-0 hooks `COMMAND.COM` calls through.
3. **A RAM-resident inter-slot helper at `$003B-$0054`** — functionally the
   standard MSX slot-select sequence (primary-slot `OUT ($A8)` + expanded-subslot
   read/write via `$FFFF`, then `RET`; pattern per MSX2 TH ch.2 / `map.grauw.nl`).
   It lives in page-0 RAM because, once RAM is paged into page 0, the page-0 BIOS
   inter-slot routines are gone (§4 / the boot-bridge paging note). A
   reimplementation writes its own from the public spec — it does not copy these
   bytes.

**Consequence for reimplementation.** This contract shows `k_47B2` is *not* a
self-contained "read `COMMAND.COM` → lay page 0 → `jp $0100`": the environment it
must hand over is six live `JP`s into the relocated kernel plus the slot helper, and
`COMMAND.COM` immediately calls *through* `$0030` / `$0038` / the BDOS path into the
`$DDxx/$DExx` kernel band. Filling the loader body is therefore gated on first
standing up those high-RAM kernel entry points — the §5.5 deferral, seen from the
environment side. Probe: `disk_probe_dosboot_page0.py`.

### 5.3 The call surface — a cluster of shared-kernel entries

Within that span the loader/shell reaches **21 distinct disk-ROM entry points
spread across `$41xx–$77xx`**:

```
$41FD $4558 $46C8 $47B2 $4919 $4935 $498C $49B4 $4A39 $4B59 $4BE5
$4C25 $4E4B $4EDE $4010 $5FE5 $607B $75A5 $77B8 $782B $402D
```

Provenance check (file identity only, `disk_probe_diskrom_crossvendor.py`-class):
**12 of the 21 are shared-kernel** (byte-identical across the seven vendors) —
de-facto-standard, the same legitimacy class as §1. The externally-reached ones
of note: `$4010` (the standard DSKIO, the *one* our ROM already provides
correctly), and `$607B` (reached from `ra=$0100` — `COMMAND.COM`'s own callback
into the disk ROM). The per-entry contracts the shell actually drives are the BDOS
functions in §6; what §5.3 settles is the surface *shape*: a bounded,
mostly-shared-kernel cluster.

### 5.4 What the reimplementation satisfies

Reaching `A>` *through the proprietary `COMMAND.COM`* is **not** a matter of cloning
the loader's internal plumbing. The page-0 vector table + `$DDxx` high-RAM kernel
(§5.2) are the stock's *internal* inter-slot plumbing, **not** COMMAND.COM's
interface (only disk-ROM/kernel PCs call them). A faithful host therefore satisfies
what COMMAND.COM *actually* calls — its `$0005` BDOS path (the §6 function surface)
plus the fixed page-1 cluster — not the kernel's internal `$DDxx` layout. zerobas
builds this under the **faithful relocation model** (mirror the stock's
relocate-kernel-to-high-RAM + page-0 vector structure, with our own code and
contracts — never copied bytes). The boot is byte-identical to stock through the
full BDOS call sequence and the visible `A>`; the settled §1–4 ABI and the
Disk-BASIC deliverable stay regression-green throughout. Probes:
`disk_probe_dosboot_47b2.py`, `disk_probe_diff.py`.

---

## 6. The BDOS-in-ROM function surface

Once `COMMAND.COM` (or any transient `.COM`) is running, it drives MSX-DOS via the
CP/M-style `CALL $0005` with the **function number in `C`**. Under MSX-DOS 1 that
path reaches the relocated high-RAM kernel, which dispatches each call through a
**per-function table** — `($D8BE + 3·C)` → `{segment, handler}` — into a page-1
disk-ROM handler at a **fixed canonical entry address**. Those entry addresses are
the surface this section documents: they are the in-ROM BDOS the MSX2 Technical
Handbook omits entirely, and — like §1 — they fall inside the cross-vendor
shared-kernel region (byte-identical across the seven vendors surveyed in
[oracle-artifacts.md](oracle-artifacts.md)), so they are genuine de-facto-standard
entries, not one vendor's private internals.

**Clean-room basis.** Each contract below is the published function contract
(`map.grauw.nl` MSX-DOS / CP/M BDOS reference) reconciled with a **black-box
characterisation** — the canonical entry *address* is found by watching which
page-1 PC the kernel CALLs for a given `C` (`disk_probe_diff.py callseq --log
0x0005`), and the register/side-effect behaviour is measured against the CF-3300
oracle (the `BDOSX*.COM` exercisers). The body at each entry is our own code; stock
bytes are never read or copied. The whole surface is a standing gate:
`make bdos-acceptance` (11 differentials) + `make bdos-cbios-selfcheck` (C-BIOS
self-consistency, 10) + host unit tests where they exist.

Register conventions below: `C` = the BDOS function number; "entry" = the canonical
page-1 handler address; contracts name the input/output registers that matter.
Functions with no single canonical page-1 address (served through the console
primitives or a data cell) are marked `—`.

### 6.1 Console / misc tier

Proven byte-identical via `BDOSX2.COM`/`BDOSX0.COM` (M22a/M22b/M23).

| `C` | fn | entry | contract |
|---|---|---|---|
| `$00` | TERM0 | — | terminate program; never returns; control falls back to the `A>` shell |
| `$01` | CONIN | `$5445` | read one char (CHGET) **and echo** it via `conout_body` |
| `$02` | CONOUT | `$5454` | output the char in **`E`** via CHPUT (§1.3). The shell's per-char output actually enters the `$53A7` CONOUT worker, which adds TAB-expansion + the `$F237` output-column cell, then drives `$5454` |
| `$06` | DIRIO | `$5454` (branch) | direct console I/O: `E=$FF` → input (no echo), else output; discriminated by `ret=$D88A`+`C=$06`+`E=$FF` |
| `$07` | DIRIN | `$5462` | raw console input; identical to INNOE at this granularity |
| `$08` | INNOE | `$544E` | read one char (CHGET), **no echo** |
| `$09` | STROUT | — | output a `$`-terminated string, each char through the CONOUT path (§2.6, `$F1C9`) |
| `$0A` | BUFIN | — | buffered line input (edited line into the caller's buffer) |
| `$0B` | CONST | `$543C` | console status (CHSNS) normalised to `A=$FF` ready / `A=$00` not |
| `$0C` | CPMVER | `$41EF` | return the CP/M version constant: `A=$22`, `B=$00` |
| `$0D` | DSKRST | `$509F` | disk reset; side effect: DTA pointer → `$0080` |
| `$18` | LOGIN | `$504E` | return the logged-in-drive vector `(1<<DRVCNT)−1`; `C` preserved. **BIOS-seam-sensitive** — see §8 (`DRVCNT`/`$F347` must be seeded above the `$FF` gate) |
| `$2E` | VERIFY | `$55FF` | store the verify flag: `A:=E` (the write-verify *effect* is deliberately not coupled in — a faithful accepted simplification) |

### 6.2 Drive select, allocation, date/time

Boot-path functions (`$0E/$19/$1B/$2A/$2B`) are proven by the 27/27 boot `callseq`;
`$2C/$2D` by `BDOSX2`.

| `C` | fn | entry | contract |
|---|---|---|---|
| `$0E` | SELDSK | `$50D5` | select disk; returns the drive count (`ld a,(DRVCNT)`) |
| `$19` | CURDRV | `$50C4` | return the current drive (`ld a,(CURDRV)`) |
| `$1B` | GETALLOC | `$505D` | free-space scan: `A=`sectors/cluster, `BC=$0200`, `DE=`total data clusters, `HL=`free-cluster count. **Must clear the `$F306` dispatcher flag before `ret`** (§6.5) or the exit path clobbers `HL` |
| `$2A` | GDATE | `$553C` | get date; returns the `1984-01-01` default; format defaults in `$F30D/$F30E` |
| `$2B` | SDATE | — | set date (accepts a typed date; screen-verified) |
| `$2C` | GTIME | `$55DB` | get time; an all-zero constant (not fed by STIME) |
| `$2D` | STIME | `$55E6` | set time: `A:=0`, `B:=H`, `C:=L`, `DE` passthrough (range validation not implemented) |

### 6.3 File / FCB tier — open, read, write, close, rename, delete

Proven by the `BDOSX*.COM` exercisers (0-byte-diff vs the oracle) and, for the write
paths, by **disk-artifact round-trip** against the CF-3300 (the RAM-only gate is
blind to disk writes).

| `C` | fn | entry | contract |
|---|---|---|---|
| `$0F` | FOPEN | `$4462` | open by FCB; fill `FCB+14..31` (record count, size, date/time, device id, first cluster) from the found directory entry; miss → `A=$FF` |
| `$10` | FCLOSE | `$461D`/`$477D`/`$456F` | close; flush a multi-cluster file's final state to the directory + FAT |
| `$13` | FDEL | `$436C` | delete: free the FAT12 chain (`fat_next_cluster`/`fat_write_fat_entry`) and stamp the dir entry `$E5` |
| `$14` | RDSEQ | (via `$477D`) | sequential record read; writes the advanced position back to the FCB |
| `$15` | WRSEQ | `$477D` | sequential record write; allocates a new cluster when the file crosses a cluster boundary |
| `$16` | FMAKE | `$461D` | create / truncate the directory entry |
| `$17` | FREN | `$4392` | rename the directory entry in place (`fat_mount`/`fat_find`/`write_sector`) |
| `$1A` | SETDTA | — | set the DTA pointer (kernel cell `DOS_DTAPTR` = `$F23D`) |
| `$21` | RDRND | `rrnd_position`→`rdrnd_body` | random-record read; positions via the record-in-sector helper |
| `$22` | WRRND | `rrnd_position`→`wrrnd_body` | random-record read-modify-write |
| `$23` | FSIZE | `$501E` | get file size: set `FCB+33..35 = ceil(size/128)` (24-bit LE); `A=L=0` found / `A=L=$FF` not found |
| `$24` | SETRND | `$50C8` | set the random-record field from the current sequential position |
| `$26` | WRBLK | `$47BE` | random **block** write: 24-bit RR positioning, transfer `(HL·RS)` bytes, past-EOF contiguous extend, `RR += HL`. On **shrink** (HL=0, RR<EOF) ours does the FCLOSE-consistent thing — sets size, frees the tail chain, EOC-marks — an intentional signed-off divergence from stock (§9) |
| `$27` | RDBLK | `$47B2` | random **block** read (`k_47B2`): position to record RR, transfer up to `HL` records of the FCB record size, zero-pad a final partial record, report the true count (M31 un-simplification; boot loaders pass RR=0/RS=1 so the loader contract `HL=BC=`bytes, `A=1` falls out) |

### 6.4 Absolute sector I/O

Proven by `BDOSX3` records 22-23.

| `C` | fn | entry | contract |
|---|---|---|---|
| `$2F` | RDABS | `$46BA` | read an arbitrary sector count via DSKIO directly into the runtime DTA |
| `$30` | WRABS | `$4720` | write an arbitrary sector count via DSKIO from the runtime DTA |

### 6.5 Load-bearing general rules for handlers

These are not per-function facts; they govern *every* page-1 handler and were each
the root cause of a real bug:

1. **Clear `$F306` before `ret` if you return a value in `HL`.** The RAM kernel's
   common BDOS-exit path (`$D8AA–$D8BD`) overwrites a handler's `HL` with `H:=B,
   L:=A` **unless** the handler first clears the dispatcher flag `$F306`. Any
   `HL`-returning handler (GETALLOC, and any future one) must clear it (M20).
2. **CONOUT takes the char in `E`, never `A`** (§1.3; M10). A veneer reading `A`
   emits garbage for all kernel-phase output while *appearing* to work for the early
   sign-on.
3. **The internal `BDOS_DTA` and the kernel `DOS_DTAPTR` (`$F23D`) are separate
   cells.** SETDTA writes only `DOS_DTAPTR`; any handler that streams via
   `bdos_seqread`/`bdos_seqwrite` for a caller other than our own boot loader must
   reseed `BDOS_DTA` from `DOS_DTAPTR` at entry, or it targets a stale address (M21b).
4. **DOS-only default cells must be seeded at handoff.** Some kernel/`COMMAND.COM`
   behaviour reads work-area cells that must hold a specific value at DOS entry —
   `$F338` (=0), `$F23B` (printer-echo, =0, else DIR mis-parses list-device state),
   `$F30D/$F30E` (date format). These are laid down in `dos_handoff` (§7).

### 6.6 Not applicable / delegated

- `$03` AUXIN, `$04` AUXOUT — no serial device on this single-drive MSX1 target.
- `$05` LSTOUT — its page-1 dispatch `$5465` **is wired** (`k_5465: jp lstout_body`,
  kernel.asm) and reads the char from `E`, delegating to the main-BIOS `$00A5` LPTOUT
  (characterised in [tier2-lstout-characterisation.md](tier2-lstout-characterisation.md)).
  The delegation is a no-op on the C-BIOS stub target and becomes real when C-BIOS grows
  LPTOUT — a two-interface delegation, not an unimplemented entry. (Contract-audit
  2026-07-08 corrected an earlier "un-wired" note here.) See
  [tier2-m27-lstout-spec.md](tier2-m27-lstout-spec.md).

---

## 7. Work-area construction — how disk-ROM INIT builds `$F100–$F3FF`

§2 documents the settled *cells* the kernel reads; this section documents how the
disk ROM's INIT **builds** the whole area at boot. It matters because the region is
not just data: the relocated `MSXDOS.SYS` kernel and `COMMAND.COM` read `$F100–$F3FF`
directly and CALL routines *inside* it, so a partially-built area derails the shell
long before any file operation. On a clone that leaves it `$FF`, ~460 of the 768
bytes differ from stock and the boot fails (`disk_probe_dosboot_wadiff.py`).

**The build runs in four time-phases** (last-writer-per-byte watch of stock's boot,
`disk_probe_dosboot_wabuild`; ~96 distinct writer routines):

| phase | builds | regions |
|---|---|---|
| 1 — clear / default | zero pass + `$C9`-fill of the hook-stub table | `$F24F–$F2B7` (§2.7) |
| 2 — structural | drive-A DPB + drive table; the segment-switch jump table; the drive-DPB pointer block | `$F195–$F1BC`, `$F368–$F37F` (§2.3/§2.4/§2.5), `$F34D–$F352` |
| 3 — resident code + FCB | the resident routines the kernel CALLs; the resident `COMMAND COM` FCB + its DPB; the device-name table `PRN LST NUL AUX CON` | `$F100–$F17C`, `$F1C9–$F236` (§2.6), `$F21C`, `$F2B8` |
| 4 — final cells | the last cells set exactly at `COMMAND.COM` entry | scattered |

zerobas reimplements the phases that its target actually needs (the CF-3300 is a
plain-64K machine, so the segment-switch table is `RET`-stubs, §2.4). The structural
data reuses existing code — the DPB comes from our own GETDPB (§2.5); the device
table and resident-FCB are static; the resident code blocks are clean-room bodies.

### 7.1 DOS-only default cells — seeded at handoff

Beyond the structural build, several work-area cells must hold a **specific value at
DOS entry** because the kernel or `COMMAND.COM` reads them directly and branches on
them. They are laid down in `dos_handoff` (`../runtime.asm`), each the root cause of
a real derail when left unset:

| cell | value | why |
|---|---|---|
| `$F338` | `$00` | `COMMAND.COM` does `ld a,($F338)` at startup and derails on non-zero (the finding that first exposed the whole unbuilt area) |
| `$F23B` | `$00` | printer-echo state; non-zero makes `COMMAND.COM`'s DIR line-end / prompt cycle believe a list device is attached (the M27 LSTOUT DIR oddity) |
| `$F30D/$F30E` | date-format defaults | consumed by GDATE (§6.2) |
| `$F247` (CURDRV), `$F347` (DRVCNT) | `$00`, drive count | read by CURDRV / LOGIN (§6.2/§6.1); **seeded unconditionally above the `$FF` gate — see §8** |

---

## 8. C-BIOS seam rules — the two interfaces and the seed-above-the-gate rule

zerobas-disk's prime target is **C-BIOS**; the CF-3300 is only the behavioural
oracle. A genuine MSX disk ROM sits between **two interfaces with opposite
portability rules**, and conflating them is the classic source of over-fitting to the
oracle's proprietary BIOS:

- **Interface A — disk-ROM ↔ `MSXDOS.SYS`/`COMMAND.COM` (layout-fixed, BIOS-
  independent).** The DOS image hard-codes specific disk-ROM addresses (the §1/§5/§6
  entries) and reads the work area at fixed offsets. We always load the same DOS
  image, so this interface is identical regardless of main BIOS: **match the
  layout/contract; reimplement contracts, never the proprietary bytes.**
- **Interface B — disk-ROM ↔ main BIOS (must be BIOS-agnostic).** To do its job the
  disk ROM calls main-BIOS services — CHPUT (`$00A2`), KEYINT, the inter-slot
  primitives, the slot work area (EXPTBL `$FCC1` …). Reach them **only** through
  documented, BIOS-agnostic entries and the slot work area — never a hardcoded slot,
  a fixed BIOS address, or an "it's already mapped" assumption. The `EXPTBL[0]`-driven
  page-in used by `conout_body` (§1.3) is the template for every Interface-B call.

### 8.1 The seed-above-the-gate rule (Interface-B, proven twice)

INIT's work-area build is **gated** so a host that already provisioned the area is not
overwritten — `set_ramad` returns early unless `RAMAD0` (`$F341`) reads `$FF`
(uninitialised):

```asm
        ld   a,(RAMAD0)      ; $F341
        inc  a
        ret  nz             ; already set -> skip the whole build
```

On the CF-3300 uninitialised page-3 RAM reads `$FF`, so the gate opens and the build
runs. **On C-BIOS, page-3 RAM is pre-filled with `$C9`** (`RET`), which is *not*
`$FF`, so the gate slams shut and the entire build — RAMAD fill, DRVTBL, resident
code, **and the DRVCNT/CURDRV seeds** — is skipped, leaving those cells at `$C9`.

The consequence: any DOS work-area cell **the kernel reads directly** must be seeded
**above** the gate (unconditionally), not inside the gated build. Proven twice:

| cell | symptom when gated out on C-BIOS | fix |
|---|---|---|
| `$F340` (INIT-complete flag, §2.2) | left `$C9` → kernel takes the derail branch; DOS never boots | clear `$F340` unconditionally before the gate |
| `$F347` (DRVCNT) | left `$C9` → LOGIN builds `(1<<$C9)−1` → returns `$FF` (8 phantom drives) instead of `$03` | seed DRVCNT/CURDRV unconditionally before the gate |

This **falsifies the naïve reading** of the two-interface rule ("disk-ROM↔main-BIOS
is fully BIOS-agnostic") for *seed cells specifically*: they are BIOS-sensitive
because the gate's `$FF` sentinel is a main-BIOS-dependent assumption. The standing
guard is `make bdos-cbios-selfcheck`, which re-captures the BDOS anchors on the
C-BIOS target and asserts byte-identity with the CF-3300 (it is what caught the
LOGIN bug — the CF-3300-only `bdos-acceptance` differential could not).

---

## 9. Boundary / adversarial behaviours (Tier-C)

The happy-path differentials converge on a small disk; the corners — disk-full,
dir-full, cluster-boundary EOF, past-EOF random writes, rename collisions — are a
separate class, and each corner's **expected behaviour is whatever the CF-3300 does**
(observed, not posited from a spec or from our own code). The suite anchors each case
either to a **read-only artifact oracle** (behaviour visible in the bytes a stock
write leaves — FAT chain length, dir layout — read from real stock disks per the
public FAT12 spec) or to a **live differential** (a `BDOSX`-family exerciser driving
the error path on both machines from an identical crafted fixture, asserting
0-byte-diff). Settled cases:

| case | corner | settled behaviour |
|---|---|---|
| 1 | cluster-boundary EOF | byte-identical to stock |
| 2 | disk-full write onset (WRSEQ) | byte-identical (the disk-full error surfaces on the same write, M34) |
| 3 | directory-full (FMAKE) | byte-identical (no fix needed) |
| 4 | WRRND past EOF (M36) | file **size grows** to `(RR+1)·RS` and the new size **persists to the directory entry** — matched to stock byte-for-byte (an FCB-only bump would have been vacuous; stock persists the size to the dirent, so ours does too) |
| 5 | FREN onto an existing name (M35) | **rejected** — `A=$FF`, source file survives, no duplicate dir entry (ours previously renamed anyway; now matches stock's refusal) |

### 9.1 One intentional, signed-off divergence — WRBLK shrink

WRBLK (`$26`, §6.3) **shrink** (HL=0, RR<EOF) is the single place ours *deliberately*
differs from stock: ours does the FCLOSE-consistent thing — set the new size, free
the tail FAT chain, EOC-mark — so the following FCLOSE succeeds on a 1-cluster
consistent chain. Stock corrupts the FAT here (it leaks the tail chain, and the
subsequent FCLOSE fails). This is **not a regression**: ours is correct where stock
is broken, and it is recorded as an accepted divergence rather than a parity target
(disk-artifact round-trip verified, `disk_probe_wrblk_roundtrip.py`).

---

## Frontier / harvest status

The two items this section previously tracked as unsettled — `$5454` CONOUT real
output and hosting `COMMAND.COM` to `A>` — **both landed** (goal MET 2026-07-03) and
are now documented as settled contracts (§1.3, §5). The MSX-DOS-1 disk-ROM track is
**concluded**; the disk ROM is full-verify CLEAN.

What remained after the boot goal was met was a **documentation harvest**, not an
implementation frontier: a body of already-settled behaviour that lived only in the
`tier2-*.md` milestone notebook. That harvest is now largely discharged — the
settled contracts have been promoted section by section (per the settle-gated cadence
in [`../../docs/documentation-deliverable.md`](../../docs/documentation-deliverable.md)):

- **§6** — the BDOS-in-ROM function surface (the ~40 functions the shell drives via
  `$0005`; M13→M36). *Promoted.*
- **§7** — work-area *construction* (the `$F100–$F3FF` build phases + the DOS-default
  cells beyond the §2 subset). *Promoted.*
- **§8** — the C-BIOS seam rules (two-interface rule + seed-above-the-`$FF`-gate,
  proven at `$F340` + `$F347`). *Promoted.*
- **§4 / §9** — the FDC-window ×8 mirror + FAT12 straddle-write remediations (§4) and
  the Tier-C boundary behaviours (§9). *Promoted.*

The **Disk-BASIC verb surface** (FILES/LOAD/SAVE/BLOAD/BSAVE/OPEN/PRINT#/GET/PUT/
EOF/LOF/DSKF/FORMAT) — a distinct layer *above* this kernel ABI — has now also been
promoted, to its own product spec
[`spec-diskbasic-verbs.md`](spec-diskbasic-verbs.md) (distilled from the
[file-channel-protocol.md](file-channel-protocol.md) spike + the
[diskbasic-verb-coverage.md](diskbasic-verb-coverage.md) scoreboard).

Going forward both specs ride the settle-gated cadence: any new settled contract is
promoted from its `tier2-*.md` notebook the moment it settles.

## Reproducing

Every contract above is reproducible from the named probe under
[`../../probes/disk/`](../../probes/disk/) against the oracle machines (stock
`National_CF-3300`; Tier-1 `National_CF-3300_ZEROBASDISK`; a real MSX-DOS 1 disk).
The probe corpus is part of this deliverable: the contracts are *measurements*, and
the probes are how anyone re-takes them. See
[`../../docs/openmsx-harness.md`](../../docs/openmsx-harness.md) for running them
and [`oracle-artifacts.md`](oracle-artifacts.md) for the validated oracle set.
