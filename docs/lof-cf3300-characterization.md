# `LOF(#n)` on the CF-3300 — what the size field is, and when it is live

Measured 2026-07-31 with [`probes/disk/diskbasic_probe_lof.py`](../probes/disk/diskbasic_probe_lof.py)
(`make lof-characterize`), differentially against a real National CF-3300 Disk
BASIC and the zerobas repack machine, both booted per case on a `/tmp` copy of
[`disk/test720.dsk`](../disk/test720.dsk).

Written because [`TODO.md`](../TODO.md) carried ONE filed row —
`OPEN "ZQ.DAT" FOR OUTPUT AS #1 : PRINT LOF(1)` → **0** reference, **−1** zerobas
([`chancost-cf3300-characterization.md`](chancost-cf3300-characterization.md) §7.1)
— and that row can neither say WHY nor say HOW MANY paths are affected.

Clean-room: black-box only. Typed BASIC in; the screen, two documented sysvars
(`SCRMOD`/`LINL32`) and the machine's OWN scratch disk image out. No reference
ROM is read or disassembled.

## 0. The apparatus, and the two ways it lied first

Two instruments, deliberately:

* **`LOF` itself**, read off the screen.
* **The DIRECTORY**, read straight out of the `/tmp` disk image after the machine
  exits (the `dir` column). This is the second instrument, and §3 shows it is the
  only thing in the battery that could answer the "which rule?" question.

⚠️ **The apparatus was wrong twice before the subject was wrong once**, both times
in a way that reads as a finding:

1. **Dropped keystrokes.** At `diskbasic_probe_chancost.py`'s 4.5 s cadence the
   CF-3300 ate whole chunks of any line typed after a line that touched the disk:
   `PRINT LOF(1)` arrived as `PRO)`, and `OPEN "ZQ.DAT" FOR INPUT AS #1` as
   `OZQ R INPUT AS #1`. The machine answered both with a **completely real
   `Syntax error`**, and the first full run duly reported `exist_out` and
   `roundtrip` as reference divergences. They were nothing of the kind. At 9.0 s
   the drops stopped and zerobas started **doubling** the first character after a
   create instead (`PRINT LOF(1)` → `PPRINT LOF(1)`), reproducibly, on both
   `stale_*` rows. 14.0 s clears both machines across the whole battery.
2. **The echo guard's own two wrong versions.** The fix for (1) is not a longer
   delay — a delay makes mangling rare, it cannot make it visible — it is an
   ECHO GUARD that fails the row when a typed line is not on screen. Version one
   compared against the full 32-cell name-table rows and flagged **10 of 16 rows,
   most with perfect screens**: Disk BASIC boots SCREEN 1 at `linlen=$1d` = **29
   columns**, so a 30-character line WRAPS and the unused cells land between the
   halves of the echo. Version two sliced rows to `linlen` instead and flagged
   the same rows: the reference also indents SCREEN 1 by a **left margin of 2**
   (C-BIOS uses 1 — [`lean-retire-s2-switch`]), so `r[:29]` cuts the last two
   characters off every full-width line. The guard only became right when it
   stopped assuming a geometry at all and matched with whitespace removed.

⚠️ **And the guard that "worked" still passed a mangled row.** With whitespace
squeezed out, `ZBPPRINT LOF(1)` *contains* `PRINTLOF(1)`, so the doubled-character
screens sailed through a plain substring test — a guard against DROPPED text is
not a guard against INSERTED text. It is anchored on the machine's prompt now
(`""` reference, `"ZB"` zerobas) and must match exactly. Both halves were
falsified before being believed: the guard goes RED on the two doubled-character
captures and GREEN on five clean ones, including wrapped reference echoes.

A mangled row returns `MANGLED`, which is **fatal whether or not `--gate` is
passed** — two mangled sides compare equal and would otherwise print `agree`.

## 1. The battery, measured

zerobas column = the repack build at `761341a` (before any fix).

| case | typed | ref LOF | ref dir | zb LOF | zb dir | |
|---|---|---|---|---|---|---|
| `ctl_syntax` | `OPEM "HI.TXT" …` | `Syntax error` | — | `syntax error` | — | control ✓ |
| `new_out` | `OPEN "ZQ.DAT" FOR OUTPUT AS #1` | **0** | 0 | **−1** | 0 | 🔴 the filed row |
| `new_out_wr` | …then `PRINT #1,"ABCDE"` | **0** | 0 | **−1** | 0 | 🔴 |
| `stale_prev` | `HI.TXT` INPUT → `CLOSE` → new OUTPUT | **0** | — | **26** | — | 🔴 |
| `stale_big` | `TEST.BIN` INPUT → `CLOSE` → new OUTPUT | **0** | — | **2048** | — | 🔴 |
| `exist_out` | `OPEN "HI.TXT" FOR OUTPUT AS #1` | **0** | 0 | **−1** | 0 | 🔴 |
| `exist_out_wr` | …then `PRINT #1,"ABCDE"` | **0** | 0 | **−1** | 0 | 🔴 |
| `append_new` | `OPEN "ZQ.DAT" FOR APPEND AS #1` | `File not found`, then ERR 59 | **absent** | **−1** | 0 | 🔴 §4 |
| `append_exist` | `OPEN "HI.TXT" FOR APPEND AS #1` | 26 | 26 | 26 | 26 | agree |
| `rand_new` | `OPEN "ZQ.DAT" AS #1` | **0** | 0 | **−1** | 0 | 🔴 |
| `rand_exist` | `OPEN "HI.TXT" AS #1` | 26 | 26 | 26 | 26 | agree |
| `rand_put` | …`FIELD`/`LSET`/`PUT #1,1` | **256** | **0** | **−1** | 256 | 🔴 §3, §5 |
| `lof_input` | `OPEN "HI.TXT" FOR INPUT AS #1` | 26 | 26 | 26 | 26 | control ✓ |
| `lof_bin` | `OPEN "TEST.BIN" FOR INPUT AS #1` | 2048 | 2048 | 2048 | 2048 | control ✓ |
| `lof_closed` | `PRINT LOF(1)`, nothing open | ERR 59 | — | ERR 59 | — | control ✓ |
| `roundtrip` | write → `CLOSE` → re-open INPUT | 8 | 8 | 8 | 8 | control ✓ |

Five controls agree, on two distinct known sizes and on both error rows, so the
red rows are attributable to the subject.

## 2. The −1 is a STALE READING, not a constant — and this could have refuted the fix

`stale_prev` and `stale_big` open a known-size file, `CLOSE` it, then create a
new file on the same channel:

| previous file | its size | zerobas's `LOF` on the NEW file |
|---|---|---|
| `HI.TXT` | 26 | **26** |
| `TEST.BIN` | 2048 | **2048** |

Two different previous sizes, reported back exactly. So the create path does not
*write* anything wrong — it never writes the size field at all, and `LOF` returns
whatever the previous tenant of the channel state left there. The famous −1
(`$FFFF`) is simply what that cell holds after a cold boot; it is not a sentinel
and nothing stores it.

**This pair is what makes the diagnosis falsifiable rather than plausible.** Had
either row also printed −1, "the field is never initialised" would have been
*wrong* and something would have to be actively storing `$FFFF`. They were
written before the fix, and they are the reason it is aimed rather than guessed.

## 3. `LOF` does NOT read the directory — and the row that proves it is not the one designed to

The filed row cannot distinguish two rules that both predict 0:

* **(a)** the size field is initialised at OPEN and frozen until CLOSE;
* **(b)** `LOF` computes from the on-disk directory entry, which a just-created
  file has at 0.

`exist_out` was written to separate them — open an EXISTING 26-byte file FOR
OUTPUT and ask whether `LOF` still says 26. **It failed to separate anything:**
the reference truncates the directory entry at OPEN too, so `ref LOF = 0` *and*
`ref dir = 0`, and rule (b) survives.

The separator turned out to be `rand_put`, a row added for the DENOMINATOR, not
for this question:

```
OPEN "ZQ.DAT" AS #1 : FIELD #1,10 AS A$ : LSET A$="X" : PUT #1,1 : PRINT LOF(1)
        reference:  LOF = 256      directory = 0
```

The reference reports **256 while the directory still says 0**. Rule (b) is
refuted: `LOF` reads an in-RAM size field. Rule (a) needs one amendment — the
field is not frozen; a RANDOM `PUT` **moves it live**, while a sequential
`PRINT #` does not (`new_out_wr`, `exist_out_wr`: still 0 after a write).

**The measured rule:**

> `LOF(#n)` reports an in-RAM per-channel size field. It is seeded at OPEN — from
> the directory for an existing file, to **0** for a created one — sequential
> writes do not move it, and a RANDOM `PUT` grows it to `recno × reclen`.

## 4. Incidental (found by the denominator rows, not aimed at)

**`OPEN … FOR APPEND` on a MISSING file: the reference REFUSES, zerobas CREATES.**
The reference raises `File not found`, the channel stays closed (the following
`LOF(1)` reports ERR 59) and the directory readout confirms **no entry was made**.
zerobas creates the file and opens the channel.
[`basic/fat.asm:270`](../basic/fat.asm:270) states the opposite as settled
behaviour — *"A missing file is created (append == create)"* — and cites
`disk_probe_append.py` for CF-3300 parity; that probe appends to an **existing**
file, so it never covered this case. A separate item: it is an `OPEN` semantics
defect, not a `LOF` one. Filed in [`TODO.md`](../TODO.md).

## 5. What this licenses

* zerobas must **zero the size field on every create path**, not only the one the
  filed row walks: `fat_io_create` (OUTPUT, and APPEND-of-missing, which jumps
  into it) and `fat_rand_open`'s `fro_create` (RANDOM-of-missing).
* zerobas must **grow the size field on a RANDOM `PUT`**, alongside the
  `FWR_BYTES` growth `frnd_update_size` already does.
* zerobas must **not** grow it on a sequential `PRINT #` (it already does not).
* The directory is stamped from `FWR_BYTES` at CLOSE
  ([`basic/fat-prim-body.inc:1247`](../basic/fat-prim-body.inc:1247)), never from
  the `LOF` field, so none of this can reach the disk — `roundtrip` is the
  two-sided row that holds that claim.

Design and byte cost: [`spec-basic-lof-size-field.md`](spec-basic-lof-size-field.md).
