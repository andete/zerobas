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

## The DOS system files — identified here (no upstream hash DB covers them)

The MSX-DOS kernel + shell come from the test disk, **not** from openMSX, so they
are *not* hash-validated by any database (openMSX's `softwaredb.xml` indexes
software *titles*, not the DOS system files; msx.org's per-version checksum
tables 403 every automated fetch). We therefore identify them ourselves.

Oracle disk: `~/Documents/msx/msx/disks/test.dsk`
(720 KB FAT12 — see [[msxdos-oracle-disk]])
SHA256 `847a28f9f0767fa879066756deba78d65ffbb58d2e481a9e1a8ff4caa6ed466c`

Extracted system files (read-only FAT12 walk; no disk mutation):

| file | size | MD5 | SHA1 | SHA256 |
|------|------|-----|------|--------|
| `MSXDOS.SYS`  | 2432 | `dadede17aaeb6852d83a33030027edb1` | `61cd9b4a8c06d750be90b85ed09d4b21871490c4` | `f65e3ac22f0c8eb842e1863fa885aeb8cef4e0ace02efff92e2bb311db2de469` |
| `COMMAND.COM` | 6528 | `4c108a4c9490383b67231028cd95f46f` | `d78498d59c30d82d4fb5d2fcb1e6d66e0221df74` | `d2bf0a2bbc025554c331bb149bbd47c07ed814b5520924b0118c584062bcd8d7` |

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

### Open follow-up (optional, for BIOS-grade certainty)

To match the BIOS's "validated against a trusted DB" standard, cross-check the
two SHA1s above against an **independently sourced** MSX-DOS 1.03 / COMMAND 1.08
copy (e.g. an official disk image or a community checksum table). Until then the
genuineness rests on the embedded MS strings + clean boot, which is strong but
self-referential.

## How to re-verify

Read-only FAT12 walk of the boot sector BPB → FAT → root dir → cluster chains;
hash each file. (No tool dependency; mtools is not required.) The script lives in
the session history; rerun it against any candidate `test.dsk` and compare to the
table above.
