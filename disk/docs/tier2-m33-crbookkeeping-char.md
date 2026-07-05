<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# M33 characterisation — RDSEQ FCB position write-back ("CR bookkeeping")

**Status:** ✅ CHARACTERISED (black-box + own-source) 2026-07-05 · fix **NOT** started
(a scope fork — documented-fields-only vs full-byte-identity vs defer — is pending user
sign-off; see §5).

The separate gap surfaced during the M32 `$24` SETRND characterisation
([tier2-m32-setrnd-char.md](tier2-m32-setrnd-char.md) §4): ours' sequential read `$14`
RDSEQ never advances the **user FCB** position fields, where stock steps them every record.
Likely the larger contributor to BDOSX's remaining unexcused FCB bytes.

Tooling reused (no new probe): [setrnd_char.asm](../../probes/disk/setrnd_char.asm) +
[disk_probe_setrnd_char.py](../../probes/disk/disk_probe_setrnd_char.py) `--full-fcb --no-setrnd`
(FOPEN → K× RDSEQ → dump the 37-byte FCB on both machines).

---

## 1. Evidence — stock steps the FCB every read; ours never does

`FCB` offsets: `+12`=EX `+14`=S2 `+15`=RC `+16..31`=DOS internal (CP/M alloc-map region,
repurposed for FAT position) `+25`=dirloc `+32`=CR. K = sequential reads before the dump.

    K     STOCK  EX +28/29(clus) +30(idx) CR      OURS  EX +28/29 +30 CR
    0         00   0150            00      00           00  0150   00  00
    5         00   0150            00      05           00  0150   00  00
    127       00   015F            0F      7F           00  0150   00  00
    128       01   015F            0F      00           00  0150   00  00
    129       01   0160            10      01           00  0150   00  00

- **CR (+32) = K mod 128; EX (+12) = K div 128** — stock steps them from the first read; the
  extent rolls (CR 7F→00, EX 0→1) exactly at record 128.
- **Internal FAT pointer**: `+26/27` = first cluster (`0150` = 336, constant); `+28/29` =
  **current** cluster; `+30` = cluster index within file. Steps as reads cross the 1 KB
  cluster boundary (matches at K=5, diverged by K=127). RC (`+15`) stays `80` (full extent).
- **Ours: EX/CR/+28/+30 never move** — the user FCB stays at its post-FOPEN values for every K.
- **At K=0 ours == stock except `+25` (dirloc)** — our FOPEN sets the whole internal region up
  *identically*; the ONLY growing divergence is the missing write-back. (`+25` dirloc is the
  pre-existing M22a accepted-cosmetic class, not part of this gap.)

Divergence surface (excluding dirloc): `+12` EX and `+32` CR from read #1; `+28/+30` once reads
cross a cluster boundary.

## 2. Root cause (our own source — allowed)

The RAM kernel CALLs the ONE page-1 disk-ROM worker `$477D` (`wrseq_body`, kernel.asm:2322) for
every sequential record — RDSEQ and WRSEQ share it; direction is our `BDOS_WRMODE` cell; the read
side falls into `bdos_seqread_body` ([kernel.asm:346](disk/kernel.asm:346)). That body delivers a
128-byte record purely from our **global** iterator state — `BDOS_BYTESLEFT`, `BDOS_RECIDX`,
`FAT_CURCLUS`/`FAT_CLUSSEC` — and **never writes the FCB copy** at `DE = IY = $DA40`. The kernel
then copies that (unadvanced) FCB copy back to the user FCB → the user sees post-open values
forever. Stock's worker advances the copy's position fields, so the kernel copies back the stepped
values.

The FCB-copy pointer `DE=$DA40` **is already live at the worker entry** (kernel.asm:2316), so the
fix has the pointer in hand. What ours lacks is an absolute record counter: it tracks
record-in-sector (`BDOS_RECIDX` 0..3) and bytes-left, not the absolute record number (CR) / extent
(EX). A small per-open counter (or a byte-consumed → record derivation) supplies CR = n mod 128,
EX = n div 128.

## 3. Feasibility + fix shape (if we do it)

After each record `bdos_seqread_body` delivers, write into the FCB copy at `$DA40`:

- **`copy+32 := CR`, `copy+12 := EX`** (documented fields) — small, self-contained; needs the new
  record counter. Makes EX/CR byte-identical to stock.
- **`copy+28/29 := FAT_CURCLUS`, `copy+30 := cluster-index`** (internal FAT pointer) — for FULL
  byte-identity. Ours already holds the current cluster in `FAT_CURCLUS`; this mirrors it into the
  FCB copy in stock's encoding (`+28/29` = current cluster, `+30` = index-from-first). Needs the
  remaining `+16..31` bytes (`+16/17/24/31`) confirmed byte-for-byte before claiming identity.

Placement follows the 3b idiom if the body outgrows its span. No canonical address moves.

## 4. Coupling to M32 `$24` SETRND (important)

The user chose to implement `$24` SETRND **correctly** (`rr = s2·4096 + ex·128 + cr`, a documented
divergence from stock's `RR:=1` stub). But a correct SETRND reads EX/CR **from the FCB** — which,
without this CR-bookkeeping fix, are stuck at 0, so `$24` would compute `rr=0` and be useless. So:

- If CR-bookkeeping is fixed (copy+12/+32 stepped), a correct `$24` reading the FCB works directly.
- If not, a correct `$24` must instead compute the position from OUR internal iterator state
  (single-open-file), not the FCB fields.

**⇒ The M32 SETRND spec's approach depends on this scope decision.** Recommend deciding
CR-bookkeeping first, then speccing `$24`.

## 5. Scope fork (HARD-STOP, pending user)

- **(A) Documented fields only** — step `copy+12` (EX) + `copy+32` (CR); allowlist the internal
  `+16..31` FAT-pointer divergence (no program reads those reserved bytes). Small, unblocks a
  correct FCB-based `$24`. BDOSX may keep a few internal-region bytes RED (allowlisted).
- **(B) Full byte-identity** — also reproduce `+28/+30` (and confirm `+16/17/24/31`) so the whole
  FCB matches stock. More work; needs the rest of the internal region decoded; greens those gate
  bytes outright.
- **(C) Defer** — leave RDSEQ write-back as-is; `$24` (if implemented correctly) reads our internal
  state instead of the FCB.

## 6. Clean-room provenance

Stock behaviour from black-box FCB RAM dumps only (no stock ROM code read; oracle `test.dsk` md5
`86e840b8…` untouched, /tmp copies). Root cause + fix shape from OUR OWN source. The `+16..31`
encoding is inferred from observed RAM values (allowed), not from decoding stock code.
