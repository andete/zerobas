<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# M32 characterisation — BDOS `$24` SETRND (National CF-3300, MSX-DOS-1)

**Status:** ✅ CHARACTERISED (black-box) 2026-07-05 · implementation **NOT** started
(a design fork — reproduce-the-quirk vs implement-correctly — is a hard-stop pending
user sign-off; see §5).

This is the "own black-box characterisation first" that the M31 resolution
([tier2-review-queue.md](tier2-review-queue.md)) flagged as required before any `$24`
implementation, because the stock contract was known to be *anomalous* ("leaves RR = 1
constant, ≠ the DOS-2 `EX×128+CR` formula"). It is fully pinned now.

Tooling (committed, reusable, clean-room): [setrnd_char.asm](../../probes/disk/setrnd_char.asm)
(the `SETRND.COM` exerciser) + [disk_probe_setrnd_char.py](../../probes/disk/disk_probe_setrnd_char.py)
(the runner, one-sided `capture` dumps on both machines).

---

## 1. Question

`$24` SETRND is *documented* (CP/M func 36 lineage) to convert the current **sequential**
file position into the **random-record** field `FCB+33..35` (r0/r1/r2), so a program can
switch from sequential to random access. We do **not** assume that formula — we drive the
position to a known place and read what stock actually writes.

## 2. Method (clean-room, black-box)

`SETRND.COM` runs **identically** on OURS (C-BIOS + zerobas-disk) and STOCK (National
CF-3300) via the real BDOS at `$0005`, then self-loops at `done`:

    fill FCB (name RDTEST.BIN) → FOPEN → SETDTA(scratch) → K× RDSEQ($14)
      → [optionally set FCB+14..15 := rs] → [optionally $24 SETRND] → snapshot FCB → done

The runner patches a `$0102` param block per case (`nreads` K, `rs`, `do-setrnd`), injects
`SETRND.COM` + a 20000-byte position-varying `RDTEST.BIN` (~156 records, so K can cross the
extent-0/1 boundary at record 128) into a **/tmp copy** of the real MSX-DOS-1 oracle
`test.dsk` (md5 `86e840b8…`, untouched), and dumps the FCB (or the EX/S2/CR/RR cells) at
`done` on each machine. Stock ROM **code is never read/disassembled** — only the RAM RESULT
stock's SETRND wrote is observed (the allowed class: registers + DATA memory).

## 3. Evidence

### 3a. Position sweep (rs=0, i.e. FCB+14 left as FOPEN set it = 0)

    K    STOCK                                  OURS
    0    EX=00 CR=00 RR=000001(=1)              EX=00 CR=00 RR=0
    1    EX=00 CR=01 RR=000001(=1)              EX=00 CR=00 RR=0
    3    EX=00 CR=03 RR=000001(=1)              EX=00 CR=00 RR=0
    5    EX=00 CR=05 RR=000001(=1)              EX=00 CR=00 RR=0
    127  EX=00 CR=7F RR=000001(=1)              EX=00 CR=00 RR=0
    128  EX=01 CR=00 RR=000001(=1)              EX=00 CR=00 RR=0   <- extent rolled
    129  EX=01 CR=01 RR=000001(=1)              EX=00 CR=00 RR=0
    130  EX=01 CR=02 RR=000001(=1)              EX=00 CR=00 RR=0

Stock: **RR = 1 for every position** — across CR 0→127 and an extent roll to EX=1. EX/CR do
**not** enter the result.

### 3b. Isolation — full FCB, with vs without the `$24` call (K=3, stock)

    +offset ...                              12 13 14 15 ... 32 33 34 35
    WITHOUT $24 (FOPEN+3 reads):             00 00 00 80 ... 03 00 00 00
    WITH    $24:                             00 00 00 80 ... 03 01 00 00

The **only** byte `$24` changes anywhere in the 37-byte FCB is `+33: 00→01`. So `$24` itself
writes it (not FOPEN/RDSEQ), and its entire effect is `FCB+33 := 1`.

### 3c. What field it *does* read — record-size (FCB+14 = S2) poked before `$24` (K=3, stock)

    rs poked → FCB+14(S2)      resulting RR (r0 r1 r2)
    0            00            01 00 00     (RR=1)
    64           40            01 00 20     (r2 = 40>>1 = 20)
    128          80            01 00 40     (r2 = 80>>1 = 40)
    512          00            01 00 00     (FCB+14 low byte = 0)

Decoded rule: **r0 (FCB+33) := 1, r1 (FCB+34) := 0, r2 (FCB+35) := FCB+14 >> 1.** EX and CR
are never read; the only input is the S2 byte, right-shifted into the overflow byte.

## 4. Derived contract

**Stock `$24` SETRND (CF-3300 MSX-DOS-1) is a broken/stub function.** It does **not** perform
the CP/M position→random-record computation. Its complete, position-independent contract is:

> `FCB+33 := 1` · `FCB+34 := 0` · `FCB+35 := (FCB+14) >> 1`

Under **normal** conditions a program does not pre-poke the reserved S2 byte (FCB+14 = 0 after
FOPEN), so this collapses to **`RR := 1`, constant**. (r1-carry for an *odd* S2 was not probed —
gate-irrelevant; S2 is 0 in every real path.)

**Ours today:** `$24` is a **no-op** — the `$50C8` kernel hook is un-wired `$00` pad (NOP-slide),
so `RR` stays 0. Gap confirmed.

**Second, separate gap surfaced here:** ours' **sequential read** (`$14` RDSEQ) never advances
the *user* FCB position — after K reads ours shows EX=00/CR=00 and unadvanced internal pointers,
where stock shows EX/CR/pointers stepped (K=130: stock EX=01 CR=02 +28=`60` +30=`10`; ours all
`00`). This is the review-queue's "FCB-copy **CR bookkeeping**" item — real, and independent of
`$24`. (FCB+25 dirloc also differs = the M22a accepted-cosmetic class.)

## 5. Gate implication + the decision fork (HARD-STOP)

BDOSX (the acceptance gate, [bdosx.asm](../../probes/disk/bdosx.asm):72/80) calls `$24`
**before** it sets the record size, so stock's SETRND sees FCB+14 = 0 → **`RR := 1`**. To match
stock in the gate, ours' `$24` must write `FCB+33 := 1` (the r2-leak never fires there).

Reproducing this is ~3 bytes of ROM. But it means **deliberately reimplementing a broken stock
function** (constant `RR := 1`). That is a faithfulness-philosophy fork — the user's call, not
mine:

- **(A) Reproduce the quirk** — `RR := 1` (maximally faithful: `+35 := FCB+14>>1`). Byte-identical
  to the CF-3300 oracle; contributes to greening BDOSX. Matches the project's "byte-identical to
  oracle" mission and the clean-room "reproduce the observable contract, bugs included" stance.
- **(B) Implement SETRND correctly** — real `EX×128+CR` position→record. A **documented divergence**
  from the oracle (allowlist class, cf. F3); does NOT green the gate; "more correct" than stock.
- **(C) Defer** — leave `$24` a no-op; BDOSX stays RED on the `$24`/CR-bookkeeping bytes.

Also open regardless of A/B/C: whether to fix the **sequential CR-bookkeeping** gap (§4), which is
likely the larger contributor to BDOSX's remaining unexcused bytes and is a bigger change than `$24`.

## 6. Clean-room provenance

Our own exerciser; calls only the published BDOS `$0F/$1A/$14/$24` contract entries. The CF-3300
is a black box we run and whose **RAM result** we read — never its ROM code. Test disk is a /tmp
copy; the oracle image is untouched (md5 unchanged). No stock bytes decoded.
