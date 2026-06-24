# Tier-2 DOS-boot oracle — artifact identity & provenance

The Tier-2 provider-oracle work (`provider-oracle-scope.md` §8) calibrates
zerobas-disk against a *genuine* MSX-DOS 1 booting on a *genuine* National
CF-3300. The validity of every black-box contract we capture depends on those
reference artifacts being authentic. This file pins each one by hash so a future
swap (different disk, patched system file) is detectable — the same guarantee
openMSX already gives the BIOS.

## The machine ROMs — known-good (openMSX ROM database)

Oracle machine: **`National_CF-3300`** (openMSX built-in). openMSX validates
these against its ROM database on load, so they are authentic by construction:

| ROM | SHA1 |
|-----|------|
| CF-3300 Main BIOS | `c7a2c5baee6a9f0e1c6ee7d76944c0ab1886796c` |
| CF-3300 Disk ROM  | `f1525de4e0b60a6687156c2a96f8a8b2044b6c56` |

(Source: `share/machines/National_CF-3300.xml` in the openMSX install.)

## Cross-vendor disk-ROM set (shared-kernel evidence)

The CF-3300 is not the only disk ROM we hold. The local openMSX system-ROM stash
(`~/Documents/msx/share/systemroms/*_disk.rom.gz`) gives a **multi-vendor oracle
set** — useful because a contract that reproduces *byte-identically across several
independent vendors* is a de-facto MSX standard worth reimplementing, whereas a
vendor-only quirk is suspect (cross-source validation, not a single source of truth).

| Vendor / model | Disk ROM SHA1 (uncompressed 16 KB) |
|----------------|------------------------------------|
| National CF-3300        | `f1525de4e0b60a6687156c2a96f8a8b2044b6c56` |
| Spectravideo SVI-738    | `17b2810545e55d3fa5821d74d8b5ab5475165fba` |
| Daewoo DPF-550          | `c1d83c559e1e6a6da961eafa55aab105681c634c` |
| Philips VG-8235         | `1bf0696816b242081e1041a16e5ff73710792865` |
| Sony HB-F500P           | `1566532146fcfc28c707753777c66585dc12418a` |
| Philips NMS-8245        | `c3f3ca454d66a0bc791f1d4b60e6857b44eb8755` |
| Panasonic FS-4600       | `073feb8bb645d935e099afaf61e6f04f52adee42` |

**Finding (provenance byte-comparison, identity only — never disassembly).** These
ROMs differ **17–36 % of their bytes** overall (genuinely independent implementations,
not copies), **yet ~63 % of each is byte-identical across all of them** — large shared
blocks, the biggest `$4768–$576F` (4104 B), plus `$402F–$44EA`, `$65DF–$6DD0`,
`$6DD2–$7404`. This is the MSX disk-ROM architecture: a **shared ASCII/Microsoft
MSX-DOS-1 kernel (~2/3, identical industry-wide)** plus a **vendor-specific third**
(FDC hardware driver + Disk-BASIC, where per-chip differences belong).

**Why it matters for provenance.** The fixed disk-ROM addresses this MSX-DOS-1
`MSXDOS.SYS` hard-codes — `$4030` (GETWRK), `$50A9`, `$5454` (CONOUT) — are all
byte-identical across the 7 vendors, i.e. they live in the shared kernel. So they are
genuine **cross-vendor de-facto-standard entries**, the same legitimacy class as the
documented `$4010–$401F` interface (DSKIO/GETDPB/…). zerobas-disk reimplements their
observed **contracts** in its own clean-room code (as it already does for `$4030` and
`$50A9`) — it **never copies the shared block's bytes**, exactly the discipline behind
the byte-identical-*output* GETDPB. The shared region's verbatim bytes are an oracle to
observe, not source to lift. (Full detail in `provider-oracle-scope.md` §8.38;
reproduce with `probes/disk/disk_probe_diskrom_crossvendor.py`, which checks each
ROM against the SHA1s above and verifies every hard-coded entry lies in the shared
kernel.)

## The DOS system files — identified here (no upstream hash DB covers them)

The MSX-DOS kernel + shell come from the test disk, **not** from openMSX, so they
are *not* hash-validated by any database (openMSX's `softwaredb.xml` indexes
software *titles*, not the DOS system files; msx.org's per-version checksum
tables 403 every automated fetch). We therefore identify them ourselves.

Oracle disk: `~/Documents/msx/msx/disks/test.dsk`
(720 KB FAT12 — see [[msxdos-oracle-disk]])
SHA256 `847a28f9f0767fa879066756deba78d65ffbb58d2e481a9e1a8ff4caa6ed466c`

Extracted system files (read-only FAT12 walk; no disk mutation):

| file | version | size | SHA1 |
|------|---------|------|------|
| `MSXDOS.SYS`  | 1.03         | 2432 | `61cd9b4a8c06d750be90b85ed09d4b21871490c4` |
| `COMMAND.COM` | 1.08 *(old)* | 6528 | `d78498d59c30d82d4fb5d2fcb1e6d66e0221df74` |
| `COMMAND.COM` | **1.11 *(preferred)*** | 6656 | `af5f2ef3eac4062638f5d8069515e6bcee788e7d` |

(MSXDOS.SYS MD5 `dadede17…` SHA256 `f65e3ac2…`; COMMAND 1.08 MD5 `4c108a4c…`
SHA256 `d2bf0a2b…`.)

### Genuineness assessment

Strong evidence these are authentic Microsoft/ASCII MSX-DOS 1 binaries, not
homebrew or patched:

- `MSXDOS.SYS` embeds `"MSX-DOS version 1.03"` and `"Copyright 1984 by
  Microsoft"` — a homebrew clone would not carry the genuine MS copyright.
  **1.03 is a documented DOS-1 release** (the DOS-1 line is 0.26 / 1.00 / 1.01 /
  1.03; 1.03 is the last MSX-DOS 1).
- `COMMAND.COM` embeds `"COMMAND version 1.08"`. COMMAND.COM versioned
  independently of the kernel under DOS 1; 1.08 is a real (earlier) build — the
  more commonly mirrored pairing is 1.03 + COMMAND 1.11, so ours is a *valid but
  less-common* COMMAND.
- It boots to `A>` on the genuine CF-3300 BIOS and loads byte-perfect into RAM
  (provider-oracle-scope.md slice-3), so the bytes are intact (no bit-rot /
  truncation).

### Caveat — `test.dsk` is a community/collection disk, not a pristine distro

The root directory is full of homebrew (OPENMSX1.MBK, IDEFDISK.COM, KANJI/game
BASICs, SPLIT*.COM …) and has VFAT-style junk entries (`attr=0x0F`, size
`0xFFFFFFFF`) that MSX-DOS 1 never writes. So someone copied the system files
onto a random disk; that's exactly why the *files* (not the disk) had to be
identified independently. The files themselves test clean (above).

### Cross-source validation (done)

Scanning the whole local disk collection (130 `.dsk`, read-only FAT12 walk) gives
strong independent corroboration — the system files are byte-identical across many
*separately-collected* disks, so they are not a one-off artifact of `test.dsk`:

- **MSXDOS.SYS 1.03 (`61cd9b4a…`)** — identical on **6 disks**: `test`, `compass`,
  `daivas5`, `elite`, `Livingst`, `roxyplay`.
- **COMMAND 1.11 (`af5f2ef3…`)** — identical on **4 disks**: `daivas5`, `Livingst`,
  `roxyplay`, `tribal`.
- COMMAND 1.08 (`d78498d5…`) — `test`, `compass`.
- msxhub's `MSXDOS1` package independently lists the canonical DOS-1 release as
  **1.03** (no per-file hashes published there, so no exact external SHA1 anchor;
  the multi-disk agreement is the stronger evidence). Optional future step: download
  msxhub's binaries and confirm byte-identity for a fully external anchor.
- Avoid `tribal`'s MSXDOS.SYS (`c33f02da…`, claims "version 1.8") and `bombaman`
  (DOS **2.2**) — different/patched kernels.

## Preferred oracle: `msxdos103-cmd111.dsk` (1.03 + COMMAND 1.11)

You requested COMMAND **1.11** over 1.08 (1.11 is the more common, later DOS-1
shell). All local 1.11 disks are *game* disks that auto-run, so we built a clean
one: a copy of the proven-bootable `test.dsk` with COMMAND.COM swapped to 1.11.
1.08 (6528 B) and 1.11 (6656 B) both occupy 7 clusters, so the FAT chain is
unchanged — only the file bytes + the directory size field were rewritten.

- Disk: `~/Documents/msx/msx/disks/msxdos103-cmd111.dsk`
  SHA256 `666cbc6dd1d8311ddd829deaa764d9cf7d2ae1e95090dca4b58f7f63723531d3`
- Contents verified: MSXDOS.SYS 1.03 (`61cd9b4a…`) + COMMAND.COM 1.11 (`af5f2ef3…`).
- **Boots clean to `A>` on the stock CF-3300** — prints "COMMAND version 1.11"
  (vs `test.dsk`'s "COMMAND version 1.08").

**Note for the §8 Tier-2 boot work:** the *kernel* (MSXDOS.SYS 1.03) is byte-
identical between the two disks, so every kernel-phase contract (`$4030`/`$50A9`/
the work area / the `IX=$4034` bug, §8.24–8.30) is **unaffected** by the COMMAND
switch — COMMAND.COM only matters once the boot reaches the final shell-load
stage. Use `msxdos103-cmd111.dsk` as `--dos-disk` going forward; `test.dsk` (still
the historical reference for §8.x captures) stays valid for the kernel phase.

### Note on the legacy disk

`test.dsk` itself is still fine for kernel-phase work, but it carries COMMAND 1.08
and the community-disk junk above; prefer `msxdos103-cmd111.dsk` for new captures.

## How to re-verify

Read-only FAT12 walk of the boot sector BPB → FAT → root dir → cluster chains;
hash each file. (No tool dependency; mtools is not required.) The script lives in
the session history; rerun it against any candidate `test.dsk` and compare to the
table above.
