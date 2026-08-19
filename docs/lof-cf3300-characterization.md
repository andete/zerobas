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

⚠️ **Except the four `rnd_put_*` rows, which did not exist then.** They were added
2026-07-31 by D-RNDDIR ([`spec-basic-randput-dir-stamp.md`](spec-basic-randput-dir-stamp.md))
and their zerobas column is the CURRENT build, i.e. **after** D-LOF fixed the −1.
Mixing two builds in one column would be a trap, so it is said here rather than
left for a reader to infer from the absence of a `−1`.

| case | typed | ref LOF | ref dir | zb LOF | zb dir | |
|---|---|---|---|---|---|---|
| `ctl_syntax` | `OPEM "HI.TXT" …` | `Syntax error` | — | `syntax error` | — | control ✓ |
| `new_out` | `OPEN "ZQ.DAT" FOR OUTPUT AS #1` | **0** | 0 | **−1** | 0 | 🔴 the filed row |
| `new_out_wr` | …then `PRINT #1,"ABCDE"` | **0** | 0 | **−1** | 0 | 🔴 |
| `stale_prev` | `HI.TXT` INPUT → `CLOSE` → new OUTPUT | **0** | — | **26** | — | 🔴 |
| `stale_big` | `TEST.BIN` INPUT → `CLOSE` → new OUTPUT | **0** | — | **2048** | — | 🔴 |
| `exist_out` | `OPEN "HI.TXT" FOR OUTPUT AS #1` | **0** | 0 | **−1** | 0 | 🔴 |
| `exist_out_wr` | …then `PRINT #1,"ABCDE"` | **0** | 0 | **−1** | 0 | 🔴 |
| `append_new` | `OPEN "ZQ.DAT" FOR APPEND AS #1` | `File not found`, then ERR 59 | **absent** | **−1** | 0 | 🔴 §4 — ✅ fixed |
| `append_exist` | `OPEN "HI.TXT" FOR APPEND AS #1` | 26 | 26 | 26 | 26 | agree |
| `rand_new` | `OPEN "ZQ.DAT" AS #1` | **0** | 0 | **−1** | 0 | 🔴 |
| `rand_exist` | `OPEN "HI.TXT" AS #1` | 26 | 26 | 26 | 26 | agree |
| `rand_put` | …`FIELD`/`LSET`/`PUT #1,1` | **256** | **0** | **−1** | 256 | 🔴 §3, §3a, §5 |
| `rnd_put_cl` | …`PUT #1,1` then **`CLOSE`** | `File not open` | **256** | `File not open` | 256 | §3a |
| `rnd_put_rt` | …`CLOSE`, re-open RANDOM | 256 | 256 | 256 | 256 | §3a |
| `rnd_put_len` | `LEN=16`, `PUT #1,1`, no `CLOSE` | **16** | **0** | 16 | 16 | §3a |
| `rnd_put_big` | `PUT #1,1` into 2048-byte `TEST.BIN` | 2048 | 2048 | 2048 | 2048 | §3a |
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

## 3a. …and the directory IS stamped — at `CLOSE`. What §3 measured was a WHEN

Measured 2026-07-31, D-RNDDIR
([`spec-basic-randput-dir-stamp.md`](spec-basic-randput-dir-stamp.md)).

§3 above reads `ref dir = 0` after a RANDOM `PUT` and that reading is correct.
The *sentence* it was carried forward as — "the reference does not stamp the
directory" — is not. 🔴 **`rand_put` exits with the channel STILL OPEN, so all it
ever licensed was "has not stamped it YET". Nobody had typed a `CLOSE`.** Three
worlds reproduce that row identically: the reference stamps at `CLOSE` and
zerobas merely does it early; both stamp *different numbers*; or the reference
never stamps at all and its `PUT` data is unreachable. Typed:

| | ref LOF | ref dir | zb LOF | zb dir |
|---|---|---|---|---|
| `PUT #1,1` then **`CLOSE`** | `File not open` | **256** | `File not open` | 256 |
| …then re-open RANDOM and `LOF` | **256** | 256 | **256** | 256 |

The reference **does** stamp the root-directory entry, at `CLOSE`, with the same
value zerobas writes. **The round trip agrees, so no BASIC program can observe
the difference.** It is a *when*, not a *what*.

The `File not open` in the first row is not decoration: it is the witness that
the `CLOSE` actually ran. A row whose only reading is `dir` cannot tell "the
`CLOSE` ran and stamped 0" from "the `CLOSE` line never arrived" — both produce
the same number.

**The mechanism, both sides.** zerobas's `fat_rand_put` tails into
`jp fat_dir_update` ([`basic/randio-body.inc:373`](../basic/randio-body.inc:373)),
so it rewrites the entry on *every* `PUT`; the reference defers it to `CLOSE`.

**And §3's formula needed separating, not just stating.** The rule was written up
as `recno × reclen` on the strength of the single **256** — but `OPEN … AS #1`
with no `LEN=` defaults reclen to 256 ([`basic/files.asm:583`](../basic/files.asm:583)),
so `1 × 256 = 256` *and* a 256-byte sector is 256. 🔴 **One cell, two rules, no
way to tell them apart.** `rnd_put_len` (`LEN=16`) reads **16** on both machines:
`recno × reclen` holds, sector-granularity is refuted. Its `dir` column reads
0 / 16, which also shows zerobas's early stamp follows the same formula rather
than being a 256-shaped coincidence.

**`max()`, and the pair that pins it.** "Grows" presumes `max(old, new)`; a plain
assign fits §3's evidence just as well, and an assign that also stamps early
would rewrite an existing 2048-byte entry down to 256 and strand 1792 bytes.
`rnd_put_big` puts a 256-byte record into `TEST.BIN` and reads **2048** on both
machines and in both columns — **no truncation, no data loss.** ⚠️ Neither row
pins `max()` alone: `rand_put` shows it GROWS (0 → 256) and `rnd_put_big` shows
it does NOT SHRINK. The pair is the rule. (zerobas's `frnd_update_size` is
`ret c` / `ret z` before the store — a real `max()`, which is why it could not
shrink.)

**Decided, not deferred.** At a 23 B low-region wall a difference no program can
observe buys no ROM bytes, so the two pre-`CLOSE` rows stay in the probe's
`DIR_DIVERGE` **permanently and with this measurement attached**, rather than as
an item waiting to be built.

⚠️ **Residual, explicitly UNMEASURED:** a machine reset *between* the `PUT` and
the `CLOSE` leaves the two disks different — the reference loses the write, and
zerobas's entry points at a chain whose FAT state at that instant is unexamined.
No probe here can reset mid-program. Filed in [`TODO.md`](../TODO.md), not
claimed in either direction.

## 4. Incidental (found by the denominator rows, not aimed at)

**✅ FIXED 2026-07-31 — D-APPMISS, [`spec-basic-append-missing-refuse.md`](spec-basic-append-missing-refuse.md)**
(−2 B; `append_new` now AGREES on both instruments). The measurement below stands
as taken; only its status changed. The row added to prove the fix
(`append_new_wr`) found a SECOND defect one layer down — `PRINT #` into an
unopened channel raises `load error`, not ERR 59 — filed separately.

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
* The directory is stamped from `FWR_BYTES`, never from the `LOF` field, so none
  of this can reach the disk — `roundtrip` is the two-sided row that holds that
  claim.
  ⚠️ **Corrected 2026-07-31 (§3a):** this bullet used to say the stamp happens
  "at CLOSE", citing
  [`basic/fat-prim-body.inc:1247`](../basic/fat-prim-body.inc:1247). True on the
  SEQUENTIAL path and incomplete on the RANDOM one — `fat_rand_put` tails into
  `jp fat_dir_update` ([`basic/randio-body.inc:373`](../basic/randio-body.inc:373))
  and stamps on every `PUT`. The conclusion the bullet draws is unaffected (the
  stamp reads `FWR_BYTES` either way), but the *when* was wrong, and it is the
  exact `when` §3a had to go and measure.

Design and byte cost: [`spec-basic-lof-size-field.md`](spec-basic-lof-size-field.md).
