# D-FREGAP — where zerobas's missing 8.6 KB of BASIC memory is

**2026-09-01.** Asked while reviewing the boot banner: the reference prints
`23430 Bytes free` — what would zerobas print? **14767.** This is the accounting
for the difference. Nothing is leaked; all of it is *reserved*, and most of it is
reserved for nothing that uses it.

## The readings

| | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|
| `FRE(0)` | 28733 | 23348 | **14767** |
| `TXTTAB` | `$8001` | `$8001` | `$8001` |
| `HIMEM` | `$F380` | `$DE77` | `$F380` |

🔴 **THE SHAPE THAT SAYS IT IS NOT A LEAK:** zerobas's HIMEM is *higher* than the
CF-3300's and its free figure is far lower, so the two cannot both be measuring
the same span. They are not. It is **not** the file buffers either — `MAXFILES=0`
recovers **41 bytes**.

On the reference the figures reconcile: `STKTOP − STREND = 23346` against
`FRE(0) = 23348`. On zerobas they cannot be compared at all, because
`VARTAB`/`ARYTAB`/`STREND` (`$F6C2/4/6`) **read 0** — zerobas keeps its own tables
at its own addresses (`ARYTAB $E1C0`), which `make sysvarsweep` already records.

## The real ceiling is TXTMAX, not HIMEM

`basic/sysvars.inc:2001`:

```
TXTMAX          equ     $BB00   ; repack: text ceiling, 1280 B below the $C000 BLOAD
DETOKBUF        equ     $BB00   ; repack: 1280 B one-shot detok output buffer.
```

`$BB00 − $8001 = 15103 B`, and `FRE(0) = 14767`. **That is the whole figure.**
Everything above `$BB00` is invisible to BASIC.

## What occupies the 14464 B above the ceiling

Walked with `scratchpad/rammap_sweep.py` plus a sweep for every `equ` in the span
— *not* read off a comment, because RAM figures have no gate:

| span | size | what is actually there |
|---|---|---|
| `$BB00`–`$C000` | 1280 B | **`DETOKBUF`** — a one-shot detokenise output buffer |
| `$C000`–`$E000` | 8192 B | the BLOAD / boot-sector load region — **two bytes allocated in all of it** (`GFX_DJ` `$C120`, `GFX_BAD` `$C121`) |
| `$E000`–`$F380` | 5000 B | the real workspace: **502 named cells** |

🎯 **SO THE GAP IS ONE BUFFER AND ONE CONVENTION.** The workspace is dense and
earns its space. `DETOKBUF` is a real 1280-byte cost. The other **8192 bytes are
reserved by convention** — `$C000` is where a boot sector loads and where BLOAD
targets are expected — and hold two graphics scratch bytes.

## What the source already knew, and what it did not

`sysvars.inc` states the near lever and bounds it honestly:

> The rise is BOUNDED BY DETOKBUF, not by the freed RAM: at 1280 B it does not
> fit in the 1024 B window, so `$BB00` is the ceiling until it is dealt with.

That is correct and it is **small**: dealing with `DETOKBUF` moves the ceiling to
about `$BE00`, worth ~768 B — under a tenth of the gap.

⚠️ **THE BIG NUMBER IS THE ONE NOBODY WROTE DOWN.** The `$C000`–`$E000`
reservation is 8192 B, is not mentioned as a cost anywhere, and its only
occupants are two bytes at `$C120` — themselves oddly sited, stranded above a
boundary everything else respects. The reference does not reserve it: the CF-3300
runs BASIC up to `HIMEM $DE77` and expects a program that BLOADs high to lower
`HIMEM`/`CLEAR` first, which is what those verbs are for.

## Disposition

**No change made.** Raising the ceiling over `$C000` changes where a BLOAD or a
boot sector may safely land, and that is a design decision with a real failure
mode (a silently overwritten program), not a measurement. What this settles is
the *size* and *shape* of the prize:

* ~768 B behind `DETOKBUF` — bounded, already documented, cheap to argue about;
* **~8192 B behind the `$C000` convention** — the actual gap, undocumented until
  now, holding 2 allocated bytes;
* the 5000 B workspace is not a target.

🟢 And it answers the question that started it: a `Bytes free` banner line would
print **14767**, and the number is honest — it is what `PRINT FRE(0)` says. It is
low because of a ceiling, not because of waste in the workspace.
