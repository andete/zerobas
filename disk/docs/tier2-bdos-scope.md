<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 BDOS scope — sizing fork A (per-address) vs fork B (intercept at $0005)

**Status:** characterisation complete 2026-06-26 (review-queue "scope reframe" entry, commit
86addb8). This doc is the deliverable of the user-chosen option **C — map the scope first**. It
sizes the two ways to make genuine MSX-DOS 1 reach the `A>` prompt, and recommends one.

## 1. The architecture finding (why "one more veneer" is wrong)

Post-`$47B2`, our disk ROM loads MSXDOS.SYS, prints the banner **byte-identically**, and enters
COMMAND.COM with **byte-identical** registers. The boot then spins because COMMAND.COM's startup
opens `AUTOEXEC.BAT` and the kernel's FOPEN returns the wrong code (`$21` vs stock `$FF`), so
COMMAND.COM never takes the "no AUTOEXEC → show prompt" branch (it loops on its prompt forever;
BUFIN never blocks). See `tier2-review-queue.md` (newest entry) and probes
`disk_probe_dosboot_{entry0100seq,conoutstream,bdosseq,fopenresult,fopenromcalls}.py`.

The reason is structural: **the file-ops BDOS (FOPEN, directory search, file read/write) is
implemented inside the disk ROM** — the shared MSX-DOS-1 kernel that is ~2/3 of every MSX disk
ROM (see memory `msx-diskrom-shared-kernel`). The chain is:

```
COMMAND.COM:  call $0005
$0005      =  JP $D606            (page-0 RAM vector, set by MSXDOS.SYS; identical ours/stock)
$D606      =  JP $D831            (relocated kernel BDOS dispatcher, high RAM, identical)
$D831…     =  dispatch on C; for file ops -> page in the disk ROM -> CALL canonical $44xx/$56xx/$77xx
```

So MSXDOS.SYS is only the thin loader/relocator; the actual BDOS file machinery lives at fixed
**page-1 disk-ROM addresses**. Our 14 Tier-2 veneers reproduce only the **COMMAND.COM-LOAD**
subset of those. Operating DOS (this FOPEN, and everything after `A>`) calls the rest.

## 2. Measured scope of the FOPEN path (not-found case)

The kernel FOPEN of `AUTOEXEC.BAT` (absent) makes a **144-entry, 23-distinct-address** directory
search in the disk ROM (probe `fopenromcalls`, stock). Coverage of those 23 in our ROM today:

| coverage in ours | n | addresses |
|---|---|---|
| real & working (standard jump table) | 2 | `$4010` DSKIO, `$4013` DSKCHG |
| collides with our FDC/DSKIO code (no contract) | 9 | `$4252 $425D $42BF $42F9 $431A $434B $4411 $4462 $44DE` |
| veneer/jump → **bare-`ret` stub** | 7 | `$4558 $46C8 $4935 $5FE5 $607B $77B8 $782B` |
| lands in `ds` padding | 5 | `$5604 $760E $764D $77BB $77BC` |

**21 of 23 need work for FOPEN-not-found alone.** The blocker is the first one, `$4462` (our ROM
has `ld ($E299),a; ret` there — unrelated FDC code). Successful open, file read, directory
listing, `CHKDSK`/`DIR`-style operations, and writes will each reveal more canonical addresses
(this is one path of the full BDOS).

## 3. Fork A — reproduce each canonical disk-ROM address

Place a net-zero veneer at every canonical address the kernel calls ($4462 + its chain), each
redirecting to a relocated body that reproduces that routine's black-box contract.

- **Faithfulness:** highest to the layout-fixed Interface A (the de-facto vendor disk-ROM layout).
- **Size:** open-ended and large. 21 for FOPEN-not-found; the full BDOS surface is many dozens of
  fine-grained internal helpers (e.g. `$5FE5/$607B/$782B` sit thousands of bytes apart — distinct
  routines, each a separate contract to characterise + reproduce). Each new DOS operation
  enumerates more.
- **Clean-room cost:** to reproduce the *exact internal call structure* of the proprietary shared
  kernel (which routine lives at which fixed address, and its precise register/flag contract) is a
  great deal of black-box reverse-engineering of that kernel's architecture — defensible only if
  every contract is derived purely from oracle observation, but it is a lot of it, and it mirrors
  the proprietary internal decomposition rather than a public boundary.

## 4. Fork B — intercept the BDOS at $0005 (the public ABI boundary)

Re-point the page-0 `$0005` vector (set by MSXDOS.SYS) to our own BDOS — a small page-0 RAM
trampoline that pages in the disk ROM and calls our `bdos_entry` — so application BDOS calls
(COMMAND.COM and user programs) dispatch to **our** implementation instead of the kernel's.

- **Boundary:** `$0005` + function-number-in-C is the **fully documented** CP/M / MSX-DOS BDOS
  ABI (MSX2 Technical Handbook, CP/M references). No knowledge of the proprietary kernel's
  internal `$44xx` layout is needed — the textbook clean-room boundary ("reimplement contracts,
  never bytes", at the right granularity).
- **Size:** bounded and known — the BDOS function set is finite (~40 functions; COMMAND.COM
  startup uses ~8: `$02 CONOUT, $06 DIRIO, $09 STROUT, $0A BUFIN, $0E SELDSK, $0F FOPEN,
  $19 CURDRV, $2A SDATE`). We already implement the hard disk half (`bdos_open`/`bdos_seqread`/
  `fat_find`/FAT) — and our `bdos_open` already returns `$FF` for not-found, which is the exact
  value this blocker needs. Console functions delegate to BIOS (CHPUT/keyboard).
- **Risks to manage:**
  1. **DOS work-area state sharing.** Our BDOS must read/write the same documented work-area
     cells the kernel/COMMAND.COM use (DTA pointer, current drive, drive table at $F1xx/$F2xx).
     FCB-based calls are self-contained (FCB at DE), which limits exposure.
  2. **The $0005 redirect / page-in trampoline** (our BDOS is in page-1 ROM; the vector is in
     page-0 RAM): a few bytes of page-0 RAM trampoline, like the existing CONOUT slot-switch.
  3. **Internal kernel BDOS use.** The relocated kernel calls its BDOS via $D606 directly during
     MSXDOS.SYS init (already complete before COMMAND.COM runs), so a $0005 redirect that catches
     only application calls is sufficient — but this must be verified, not assumed.
  4. **Completeness.** A working shell needs the full function set COMMAND.COM/programs exercise,
     not just the 8 startup calls — but each is a documented contract and many already exist.

## 5. Recommendation

**Fork B (intercept at $0005).** It is the cleaner clean-room boundary (documented BDOS ABI vs
reverse-engineering the proprietary kernel's internal address layout), it is bounded and
finite where A is open-ended, it reuses the disk BDOS we already have (and our `bdos_open`
already produces the `$FF` this blocker needs), and it matches the project's stated discipline of
reimplementing public contracts. Fork A remains the most byte-faithful to one vendor's internal
layout, but at a cost (size + clean-room exposure) that B avoids.

**Proposed first step under B (spec before code, per discipline):** write `tier2-bdos-spec.md` —
(i) confirm by probe that the relocated kernel does NOT route its own internal BDOS use through
`$0005` (so an application-level redirect is safe); (ii) specify the `$0005` trampoline + page-in;
(iii) specify the function table our BDOS must cover for COMMAND.COM startup (the 8 above) and the
work-area cells it shares; (iv) validate by re-running `bdosseq`/`fopenresult` — FOPEN must return
`$FF` and COMMAND.COM must leave the prompt-spin. Sign-off before any asm.

## 6. Provenance / how to reproduce

All findings are black-box oracle observation (two boots of the same proprietary DOS, diff the
state); no disassembly of the disk ROM or of MSXDOS.SYS/COMMAND.COM. Probes in
`probes/disk/disk_probe_dosboot_*.py`; oracle disk
`~/Documents/msx/msx/disks/msxdos103-cmd111.dsk` (MSX-DOS 1.03 + COMMAND.COM 1.11, md5
`7bf624375473e76c9eddb683da174faa`), always run on a `/tmp` copy.
