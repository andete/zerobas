# D-STRADDLE — predictions, written BEFORE the spanning code

## The subject

`fat_rand_put` / `fat_rand_get` overlay a record with ONE `ldir` into
`FWBUF + GP_WITHIN`. With `within + reclen > 512` that runs past the 512-byte
buffer — record 6 at `r=100` has `within=500`, so 88 bytes land beyond `FWBUF`
($E7C0..$E9BF), i.e. in whatever follows it. `oo_parse_reclen`'s power-of-two
rule exists to make that unreachable.

## Why a HOST test and not emulator rows

The item records both blindnesses of the last attempt:

  * a round-trip cannot see a wrong offset, because `PUT` and `GET` share it;
  * `mul_reclen`'s shift put record 6 at within=320, so the row that was meant
    to straddle never straddled.

The second is fixed (D-MULREC). The first is structural, and the answer is to
build the expected sector image INDEPENDENTLY in Python and compare bytes —
which needs no emulator, no disk, and cannot be fooled by a shared offset.
`read_sector` / `write_sector` / `frnd_locate` are all sub-local symbols, so the
harness can trap them exactly as `test_fat_alloc_cluster.py` does.

## Predictions for the test BEFORE any engine change

| case | prediction |
|---|---|
| `r=256 rec=1,2,3` — the tiling anchor | PASS: sector image matches the independent model |
| `r=100 rec=1` — non-tiling, no straddle (within=0) | PASS |
| `r=100 rec=5` — within=400, ends exactly at 500 | PASS |
| **`r=100 rec=6` — within=500, STRADDLES** | 🔴 **FAIL**, two ways: sector 1 never written, and 88 bytes appear ABOVE `FWBUF+512` |
| `r=100 rec=7` — within=88 of sector 1 | PASS on its own sector, but only if rec 6 did not already corrupt it |

⚠️ The overrun row is the one that matters and the one a round trip cannot see:
the damage lands in memory nobody asked about. The test asserts the bytes ABOVE
`FWBUF+512` are untouched, which is a claim about the ENGINE, not about the disk.

## After the spanning change

Every row PASSes, including `r=100 rec=6` writing BOTH sectors, and the
neighbours (records 5 and 7) surviving intact — the adjacency property that
`docs/spec-basic-put3.md` §2 measured on the CF-3300.

## What this tick does NOT do

`oo_parse_reclen` stays as it is. The engine may be straddle-correct before the
validator opens; shipping the validator needs the emulator rows too, and those
come after.
