# D-LOF — `LOF(#n)`'s size field is never initialised on a create path

**Status:** ✅ **LANDED 2026-07-31.** +6 B main page 1 (page 1 26 B → **20 B**
free; low region unchanged at 23 B), dead-code 0/0 both builds. `make
lof-acceptance` 16/16 (`append_new` filed, §8); `make chancost-characterize` 39
cases / **0** filed. F1–F3 all falsified with the knives verified to have cut.
**Owner item:** [`TODO.md`](../TODO.md)
*"`LOF(#n)` reads −1 on a freshly-created OUTPUT channel"* (~line 2731).
**Measurement:** [`lof-cf3300-characterization.md`](lof-cf3300-characterization.md).
**Baseline walls (clean `make basic-reloc`, `761341a`):** low **23 B**, page 1
**26 B**.

## 1. The defect

`FAT_FILESIZE` ($E9CE, 4-byte LE) is the per-channel size field
[`basic/sysvars.inc:2513`](../basic/sysvars.inc:2513), inside the 50-byte
`FCH_STATE0` span that `fch_save_active`/`fch_load_ctx` swap per channel. It is
the *only* thing `ev_ff_lof` reads
([`basic/expr.asm:1084`](../basic/expr.asm:1084)):

```
ev_ff_lof:      …  call fch_select
                ld      de,(FAT_FILESIZE)
                ret
```

`fat_find` writes it on every path that OPENS AN EXISTING FILE
([`basic/fat-prim-body.inc:250`](../basic/fat-prim-body.inc:250)). **No create
path writes it at all.** `fat_io_create` zeroes `FWR_SECIDX`/`FWR_CLUS`/
`FWR_FIRST`/`FWR_BUFLEN`/`FWR_BYTES` and stops
([`basic/fatiocreate-body.inc:31`](../basic/fatiocreate-body.inc:31)); so does
`fro_create` ([`basic/randio-body.inc:82`](../basic/randio-body.inc:82)). `LOF`
therefore returns whatever the previous tenant of the channel state left behind —
**measured at 26 and at 2048** (characterization §2). The famous −1 is just what
that cell holds after a cold boot. It is not a sentinel and nothing writes it.

## 2. The measured rule (characterization §3)

> `LOF(#n)` reports an in-RAM per-channel size field, seeded at OPEN — from the
> directory for an existing file, to **0** for a created one. A sequential
> `PRINT #` does not move it; a RANDOM `PUT` grows it to `recno × reclen`.

The "reads the directory" alternative is REFUTED, by `rand_put`: the reference
prints **256 while the on-disk directory entry still holds 0**.

## 3. The denominator — every site that makes the field live

Enumerated from the source, not from the probe's path:

| # | site | today | change |
|---|---|---|---|
| 1 | `fat_io_open` — OPEN FOR INPUT | `fat_find` sets it | ✅ none |
| 2 | `fat_io_append` on an EXISTING file | `fat_find` sets it | ✅ none |
| 3 | `fat_rand_open` on an EXISTING file | `fat_find` sets it | ✅ none |
| 4 | **`fat_io_create`** — OPEN FOR OUTPUT, and APPEND-of-missing which `jp`s into it | 🔴 never set | **zero it** |
| 5 | **`fro_create`** — RANDOM open of a missing file | 🔴 never set | **zero it** |
| 6 | **`frnd_update_size`** — RANDOM `PUT` | 🔴 grows `FWR_BYTES` only | **mirror it** |
| 7 | device / cassette channels (LPT/CRT/CAS) | rejected by `fch_mode_class` (then `ev_chan_hasfile`) | ✅ none |
| 8 | a closed channel | ERR 59 (`lof_closed` agrees) | ✅ none |
| 9 | `fch_save_active`/`fch_load_ctx` | carry it per channel | ✅ none |

⚠️ **Both bodies with two homes are covered by editing the body once.**
`fatiocreate-body.inc` is included by [`basic/fat.asm:262`](../basic/fat.asm:262)
(resident) and [`sub/save.asm:119`](../sub/save.asm:119) (sub tenant);
`randio-body.inc` is **sub-only** ([`sub/randio.asm:47`](../sub/randio.asm:47)),
so sites 5 and 6 cost **no main ROM at all**. The disk ROM (`disk/fat.asm`) has
no `fat_io_create` and no `LOF` — out of scope.

## 4. The change

Three edits, all "store a real 0/size where a stale value is currently left".

**(a) `basic/fatiocreate-body.inc`** — after the existing `ld hl,0` block:

```
                ld      (FAT_FILESIZE), hl      ; LOF reads this; a created file
                ld      (FAT_FILESIZE + 2), hl  ; is 0 bytes until CLOSE stamps it
```

**(b) `basic/randio-body.inc`, `fro_create`** — the same two stores beside the
existing `FWR_FIRST`/`FWR_BYTES` zeroing.

**(c) `basic/randio-body.inc`, `frnd_update_size`** — keep the field in step with
the `FWR_BYTES` growth it already performs:

```
                ld      (FWR_BYTES),hl
                ld      (FAT_FILESIZE),hl       ; …and LOF's view of the size
                ld      hl,0
                ld      (FWR_BYTES+2),hl
                ld      (FAT_FILESIZE+2),hl
```

All four bytes are zeroed, not just the 16 `LOF` returns: it is a size field, and
a half-initialised one is the same defect one reader away.

### Byte cost

| build | Δ |
|---|---|
| **main page 1** | **+6 B** (a only) → 26 B free becomes **20 B** |
| main low region | **0** |
| sub | +18 B (a, b, c) — not scarce |

No carve or promotion needed; this is the "may well fit as-is" case.

## 5. Why this cannot reach the disk

`fat_dir_update` stamps the directory from **`FWR_BYTES`**, never from
`FAT_FILESIZE` ([`basic/fat-prim-body.inc:1266`](../basic/fat-prim-body.inc:1266)),
so zeroing the `LOF` field cannot truncate a file. `roundtrip` (write → `CLOSE` →
re-open FOR INPUT → 8 on both machines) is the two-sided row that holds that
claim, and it must stay green.

## 6. Gate

New target **`make lof-characterize`** / **`make lof-acceptance`** (`--gate`) over
[`probes/disk/diskbasic_probe_lof.py`](../probes/disk/diskbasic_probe_lof.py),
16 cases, oracle-locked to the reference column recorded in the characterization.

Required after the change — **9 divergences → 1**:

| case | before | after |
|---|---|---|
| `new_out`, `new_out_wr` | −1 | **0** |
| `stale_prev`, `stale_big` | 26 / 2048 | **0** |
| `exist_out`, `exist_out_wr` | −1 | **0** |
| `rand_new` | −1 | **0** |
| `rand_put` | −1 | **256** |
| `append_new` | −1 | stays divergent — **§8**, allowlisted with its owner |
| the 5 controls | agree | agree |

And `make chancost-characterize` must go **39/1 → 40/0** (`lof_new` is the same
row as `new_out`).

## 7. Falsification — RUN, not planned

Each knife paired with a green control, and each knife checked that it CUT (the
D-ERR21 lesson: a green falsification is a claim about the patch first — verify
the emitted bytes actually changed before scoring a deletion as unnecessary).

| id | do | must go RED | must stay GREEN |
|---|---|---|---|
| **F1** | delete edit (a) | `new_out`, `stale_prev`, `stale_big`, `exist_out` | `lof_input`, `lof_bin`, `roundtrip` |
| **F2** | delete edit (b) | `rand_new` | `rand_exist`, `lof_input` |
| **F3** | delete edit (c) | `rand_put` | `rand_new`, `roundtrip` |
| **F4** | keep all three; assert `roundtrip` = 8 and the on-disk `dir` = 8 | — | the fix does not reach the disk (§5) |

**Result — every knife verified to have CUT before its row was believed:**

| id | knife cut? | red rows | green controls |
|---|---|---|---|
| F1 | page 1 free 20 B → **26 B** (the 6 bytes gone) | `new_out` −1, `stale_prev` **26**, `stale_big` **2048**, `exist_out` −1 | `rand_new`, `lof_input`, `lof_bin`, `roundtrip` |
| F2 | `fro_fill` moved $60BE → $60B8 (−6, sub) | `rand_new` −1 | `new_out`, `rand_exist`, `rand_put`, `lof_input`, `roundtrip` |
| F3 | `fat_rand_get` moved $6291 → $628B (−6, sub) | `rand_put` **0** | `new_out`, `rand_new`, `rand_exist`, `roundtrip` |
| F4 | — | — | `roundtrip` 8 on both machines, on-disk `dir` 8 on both |

Two things the falsification showed that the plan did not predict:

* **Each edit is independently load-bearing.** Deleting one left the other two
  rows GREEN in every case — no edit was covering for another, and none was the
  no-op that D-ERR21's F6 turned out to be.
* **F3's `rand_put` fell to 0, not to −1.** That is the shape that proves (b) and
  (c) are separate facts: the create-path zeroing was still in place and working,
  so what F3 removed was specifically the LIVE GROWTH, not the initialisation.

## 8. Deliberately NOT in this slice

**`OPEN … FOR APPEND` on a missing file creates it; the reference raises
`File not found` and creates nothing** (characterization §4). Found by this
battery's denominator rows. It is an `OPEN` semantics defect, not a `LOF` one —
and [`basic/fat.asm:270`](../basic/fat.asm:270) documents the current behaviour as
deliberate, citing a probe that only ever appended to an *existing* file. Filed as
its own `TODO.md` item; `append_new` is allowlisted in the gate naming that item,
per the `KNOWN_DIVERGE` discipline.

**The chancost probe has no echo guard.** Its rows are short `PRINT FRE(0)` reads
and it has been stable, but it is exposed to the same mangling this battery hit
(characterization §0). Noted in `TODO.md`, not changed here.

## 9. Sign-off — answered 2026-07-31

1. **`append_new` stays a SEPARATE item** (§8), filed in `TODO.md` with its
   measurement and allowlisted in the gate naming it. It changes `OPEN`
   semantics, and the comment it contradicts
   ([`basic/fat.asm:270`](../basic/fat.asm:270)) deserves its own slice.
2. **Both targets**: `make lof-characterize` and `make lof-acceptance`, wired into
   the standing set beside `chancost-characterize`.

## 10. Gates run

`unit-test` 55/55 · `lof-acceptance` **16/16** · `chancost-characterize` 39
cases / **0** filed · `diskbasic-acceptance` 34/34 · `bdos-acceptance` 12/12 ·
`fat-error-acceptance` 7/7 · `error-trap-acceptance` ALL PASS ·
`abort-acceptance` 49/49 · `stop-trap-acceptance` ALL PASS ·
`linemax-acceptance` 60/60 · `arrdim-acceptance` 73/73 · `clearpool-acceptance`
52/52 · `array-acceptance` 149/151 — the two failures are the standing
capitalisation-only rows `ifc.instr.zero` and `ifc.instr.neg`, confirmed BY NAME.
Clean `make basic-reloc`: dead-code **0 dead in BOTH builds**.
