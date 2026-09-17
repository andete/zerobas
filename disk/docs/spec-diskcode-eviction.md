<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — evicting the disk code from the main ROM

**Status: written 2026-09-17, no code moved under it yet.**
Ruled by Joost, 2026-09-17: *"There should probably be hardly any disk code left
in the main Rom."*

This is the continuation of
[spec-diskbasic-hook-rearchitecture.md](spec-diskbasic-hook-rearchitecture.md),
which settled the MECHANISM (a verb's hook points at a disk-ROM body) and took it
through phases 0–3. **That document is the mechanism; this one is the
DENOMINATOR.** It does not restate the slot model, the ABI measurement or the
phase-3 blocker; it says how much disk code is in main, what shape it is, what
each piece costs to move, and in what order.

---

## 0. The one-line target

Main keeps the **parse** and the **error raise**. `disk.rom` gets the **work**.
Nothing that only a disk can do should occupy a byte of main page 1.

---

## 1. The denominator, measured 2026-09-17

`tools/carve_scout.py --census` over the six files that are disk code and nothing
else — `basic/fat.asm`, `basic/files.asm`, `basic/field.asm`,
`basic/fatio-body.inc`, `basic/fatiocreate-body.inc`, `basic/randio-body.inc`:

```
215 labels defined, 181 in page 1
**2394 B leaves page 1** if they move
  SHARED (called from outside -- must stay, or become call-backs):  250 B  (22 entries)
  PRIVATE (moves with the verb):                                   2144 B  (159 labels)
```

**Against 69 B free in main page 1 and 32 B in the low region (2026-09-17.)**
So this one direction is worth roughly thirty times everything carving has
produced in this tree, and it is the reason no other budget question needs
answering first.

⚠️ **THE BOUNDARY IS THOSE SIX FILES AND NOT A BYTE MORE.** `basic/save.asm`,
`basic/cload.asm` and the `BLOAD`/`LOAD`/`RUN` loaders are **tape AND disk** —
they dispatch on the device, so they are not disk code that can leave. Whether
their disk arms can be split out is a SEPARATE question and is not priced here.
Quoting 2394 B as "the disk code in main" without that sentence would be
overclaiming by omission.

## 2. What the destination looks like — and it is not 8415 flat bytes

```
disk free (0x00 runs >= 16 B) = 8415 B in 32 runs  (2026-09-17)
  $6ACC-$75A4  2777 B   next pin $75A5
  $5602-$5FE4  2531 B   next pin $5FE5
  $50E3-$53A6   708 B   next pin $53A7
  $75A8-$77B7   528 B   next pin $77B8
  $4EE1-$4FB7   215 B   next pin $4FB8
  $7F35-$7FD0   156 B   next pin $7FD1
```

🔴 **THE SPACE IS FRAGMENTED BY PINNED KERNEL ADDRESSES**, so "8415 B free" is
not a budget a 2144 B body can be dropped into. **2144 B fits the largest hole
(2777 B) with 633 B to spare, and nothing else does.** Any plan that assumes
flat space is wrong; a plan that lands the bulk in `$6ACC` and the leaves in the
smaller runs is the shape that fits. **Re-read `make basic-reloc`'s disk section
before every move** — the runs shift as bodies land, exactly as main's wall does.

## 3. The mechanism, corrected

The hook re-architecture spec has this; the correction below does not, because it
was made after that document was written and **its absence misled a whole slice
of work on 2026-09-17**.

* **Main → disk** is the hook: `ld hl,<cell>` + `call chan_gate`. Unclaimed → ERR
  5, trappable, which is what a diskless machine must answer.
* **Disk → main, page 0** is a plain `call`: `disk.rom` is a PAGE-1 ROM, so while
  it is mapped, page 0 still holds slot 0 and main's **low region is callable by
  absolute address**. Declared in `gen_resident_abi.py`'s CODE list, which is
  ceiling-checked to be below `__MEAS_LOW_END`.
* **Disk → main, page 1** is `calbak` — `ld iy,(EXPTBL-1) / jp CALSLT` — with the
  target in `IX`. 🔴 **IT EXISTS, AT NINETEEN CALL SITES**, reaching six page-1
  targets declared in the CALLBACK list. Its ABI is **measured two-sided**
  (D-XSLOTABI): HL/DE/BC/A cross both ways intact, and CF crosses too.
* **RAM** crosses freely: the work area is mapped throughout. Declared in the RAM
  list.

⚠️ **I TOLD JOOST THIS CALL "HAS NEVER BEEN MADE IN THIS TREE" AND THAT ITS PRICE
GATED THE CHANNEL VERBS. BOTH WERE FALSE**, and I filed the second into TODO
before checking. The source was stale prose: `gen_resident_abi.py`'s own
paragraph said its CALLBACK list was *"Empty today, and that is a statement, not
an oversight"* while the list held six names. **A PLAN BUILT ON A DOCUMENT'S
PROSE INSTEAD OF ITS DATA IS A PLAN BUILT ON WHAT WAS TRUE ONCE.**

## 4. The defect this fixes, which is not a byte count

🔴 **EVERY GATE-ONLY HOOK IS A PRESENCE TEST, AND MAIN REDOES THE WORK AFTER IT.**
Measured on `CVI`/`CVS`/`CVD` (D-CVMOVE): after the hook returned *claimed*, main
ran the entire conversion regardless — so a foreign disk ROM that claimed `H_CVI`
and computed the answer had it **overwritten on the way out**. The same shape
held for `DSKF` and holds for every cell still pointing at `hk_present`.

🎯 So each remaining verb is the **same fix**, not a fresh design: move the work
behind the hook, leave the parse and the raise in main. That is why §6's order is
a queue rather than a research programme.

## 5. Eight rules, each one paid for on 2026-09-17

1. 🔴 **`STRSCR` IS NOT A MARSHALLING BUFFER.** It is where `MKI$`/`MKS$`/`MKD$`
   stage their result, so `CVI(MKI$(258))` hands a body a string whose body IS
   `STRSCR+1`. Staging a pointer there wrote over the value being converted:
   **12 of 32 rows DIFF**, and the 20 that stayed green were the arguments that
   are not staged strings. **A ROUND TRIP IS WHERE A SHARED SCRATCH BUFFER
   ALIASES ITSELF** — and a round trip is the case these verbs exist for.
2. 🎯 **BEFORE MARSHALLING ANYTHING, ASK WHETHER IT IS ALREADY IN RAM OR ALREADY
   BELOW `$4000`.** For the CV trio it was both: the descriptor was in `STRPTR`
   and `pu_deref_body` was at `$28C1`, so the body deref'd it itself and the
   marshalling I wrote first was pure risk.
3. 🟢 **A TRIVIAL PAGE-1 HELPER SHOULD VANISH, NOT MOVE.** `flt_int_result` only
   set `FACTYP := 2`; the body does that inline and a page-1 address stopped
   being a dependency of a routine that runs in another slot. Only a substantial
   helper forces the promote-or-call-back decision.
4. ⚠️ **A REGISTER GUARD MOVES WITH THE WORK IT GUARDS.** `DSKF`'s count used to
   run main-side under its own `push iy`; it runs inside the handler now, so the
   guard had to span the GATE instead. That survives a build and dies in a probe.
5. ⚠️ **AN ARGUMENT IN A REGISTER MUST CROSS IN RAM.** `chan_gate` clobbers `DE`
   building its own return address — the first cut of D-DSKFDRV checked `DE`
   after the gate, tested `cg_back`, and made every `DSKF` answer `Bad drive
   name`, with the TIER 3 row passing because it expects a refusal.
6. 🟢 **ERROR ORDER IS OFTEN FREE.** Moving the checks above the gate is
   unobservable when both paths raise the same error — for the CV trio the
   too-short check and the unclaimed gate both raise ERR 5. **Say which two
   errors coincide**, do not assume they do.
7. ⚠️ **A NEW SECTION HEADER NEEDS A CITATION.** `make basic-reloc` refuses one
   without it. Cite the section that establishes the verb as the disk ROM's, and
   the measurement the body rests on.
8. 🔴 **THE MEASUREMENT MOVES WITH THE CODE IT GUARDS.** `DSKF`'s `drive <= 2`
   bound and the four-points-above / two-below reading that fixed it now live
   beside the check in `disk/kernel.asm`. A bound whose evidence stays behind in
   another ROM is a bound nobody can re-derive.

## 6. The order, and why it is this one

Each step is one slice: move, build, verb probe, knife, `kwsweep`, full battery,
one commit.

| # | what | state |
|---|---|---|
| 1 | `MKI$` | ✅ D-MKINT — the exemption was marshalling, not implementation; +13 B |
| 2 | `CVI` `CVS` `CVD` | ✅ D-CVMOVE — +14 B main, −38 B disk; 0/32 DIFF |
| 3 | `DSKF` | ✅ D-DSKFMOVE — +4 B main, −37 B disk; identical on all six drive points |
| 4 | `LSET` `RSET` `FIELD` | the channel trio — §7 |
| 5 | the FAT layer (`basic/fat.asm` + the two `fatio` bodies) | 🛑 **BLOCKED — §6.1** |
| 6 | the channel engine (`basic/field.asm`, `randio-body.inc`) | last, §7 |

### 6.1 🛑 THE FAT LAYER CANNOT LEAVE UNTIL THE LOADERS DO — measured 2026-09-17

This spec listed the FAT layer as "the bulk" and put it at step 5. **That order
is wrong, and the census is what hid it**: `--census` reports a label as SHARED
by counting callers *outside the six files*, but it does not say WHO, so
"250 B shared" read as a small frontier when part of it is a hard pin.

**Six files outside the six call the FAT I/O layer directly:**

```
basic/bload-body.inc        fat_io_getbyte x8, fat_mount x1
basic/cload.asm             fat_io_open x2, fat_io_getbyte x4, fat_find x2, fat_mount x1
basic/fat-delete-body.inc   fat_find x1, fat_mount x1
basic/fat-prim-body.inc     fat_mount x1
basic/print.asm             fat_io_putbyte x1
basic/sv-diskwr.inc         fat_io_create x1, fat_io_close x1, fat_io_putbyte x1
```

🔴 **THESE ARE THE TAPE/DISK SHARED LOADERS — the exact code §1 and §11 declined
to price.** `LOAD`/`RUN`/`BLOAD`/`SAVE`/`PRINT#` dispatch on the DEVICE, so they
are not disk code that can leave; and while they stream bytes through
`fat_io_getbyte`, the layer they stream through cannot leave either. Moving it
regardless would turn 25 plain `call`s into 25 inter-slot calls on the hot path
of every disk load — at 0.156 ms each (D-XSLOTPRICE) on a machine already ~3×
slower than the reference.

🎯 **SO THE REAL STEP 5 IS A QUESTION, NOT A MOVE:** can each loader's disk arm
be split from its tape arm, so the arm and the layer move together? That is the
prerequisite, it is unpriced, and it is where the next measurement belongs —
**not** in starting a move that ends 25 calls deep in the wrong slot.
⚠️ Until it is answered, the FAT layer is **pinned in main**, and the honest
figure for what can leave today is **§1's 2394 B MINUS the FAT layer and its
frontier**, which this spec does not yet break out.

🎯 **THE SMALL VERBS FIRST IS NOT TIMIDITY.** Each one pays for the next by
freeing main page 1 — 22 B this morning, 69 B now — and each proves one more of
§5's rules against a real probe before the bulk move depends on it.

## 7. The channel trio, and the wall that is not one

`LSET`/`RSET`/`FIELD` need the channel engine: `fch_check` `$7080`,
`fch_mode_class` `$502B`, `fld_lookup` `$73B8`, `var_str_type` `$47A6`,
`req_letter` `$4093` — every one in page 1. **That is what D-VERBCLASS's "STAY
155 B" was measuring.**

🔴 **AND IT IS NOT A WALL, BECAUSE §3'S CORRECTION REMOVES IT.** Those are
call-back targets, and adding one is a single declaration in
`gen_resident_abi.py`'s CALLBACK list — which is exactly how `fat_count_free`
went in for `DSKF`. D-VERBCLASS priced a constraint from the SUB ROM's rule
("no main-page-1 escape"), and `disk.rom` is not bound by it.

### 7.1 🎚️ RULED BY JOOST 2026-09-17: THE FULL MOVE, AND SPEED WAITS

The trio is **PARSE-DOMINATED, and its work has already left main**:
`lrset_store` is a sub-ROM page-0 tenant, so the justified copy went long ago.
What `basic/field.asm`'s 576 B private actually holds is BASIC parsing —
`LSET A$="X"` is `req_letter` → `var_str_type` → `tgt_parse_fld` → `skip_eq` →
`req_operand` → `str_eval`, and `FIELD#1,20 AS N$` is an `eval` for the channel
plus an `eval` and a name resolution per field pair.

So moving the bodies faithfully — the reference's architecture, where the handler
calls back into BASIC for every expression (D-CFARCH: `FILES 5` is ERR 13, not
ERR 2) — costs roughly **five to six call-backs per statement, ~0.8–0.9 ms** at
D-XSLOTPRICE's 0.156 ms, on the verbs whose whole purpose is writing records in a
loop. Two options were put to Joost:

* **A. the full move** — up to 576 B of page 1, at that per-statement cost;
* **B. partial** — move only the non-parse work, keep the parse main-side: no
  speed cost, but the store is already gone so the byte win is small.

🎚️ **HE RULED A, VERBATIM: *"A, lets worry about speed when we reach the next
tiers"*.** That is consistent with the tier ladder — TIER 1 is the happy path
working, TIER 2 reasonable time, TIER 4 on-par speed — and with the charter:
faithful full MSX1 BASIC, which is what the reference's own architecture is.
⚠️ **AND THE COST MUST BE MEASURED, NOT CARRIED AS AN ESTIMATE.** 0.156 ms is
D-XSLOTPRICE's **main→disk** figure; the reverse direction is ASSUMED to match
and has not been measured. Time `LSET` in a loop before and after, and record the
reading — a per-statement price that only ever existed as an estimate is the kind
of figure a later slice quotes as if it had been taken.

⚠️ **WHAT IS STILL OPEN IS PHASE 3'S QUESTION, NOT THIS ONE**: `OPEN`, `CLOSE`,
`INPUT`, `LINE INPUT`, `MERGE` and `MAXFILES` **have no hook cell we have
identified**, and the pattern is *point the verb's hook at a disk-ROM body*. With
no cell to point there is nothing to do. That is an ORACLE measurement — the
`hookid_chan.py` POKE sweep over the unidentified cells of the 35-cell census,
with its two controls — and it gates step 6, not steps 4 and 5.

## 8. What must stay in main, and why

The 250 B frontier is not a residue to be minimised; it is the **interface**.

* **The parse.** `fname_expr`, `pdfcb_resume`, `parse_disk_fcb` — already
  call-back targets, because a filespec is a BASIC expression and only main can
  evaluate one. The reference does the same across slots (D-CFEVAL/D-CFARCH:
  `FILES 5` is ERR 13, not ERR 2).
* **The raise.** `raise_error` is page 1 and a handler must not raise across the
  call: a body returns a status and main raises. `DISKOP_STATUS` is that channel.
* **The channel table's readers.** `fch_check`/`fch_select` serve `EOF`, `LOC`,
  `LOF` — verbs that are not disk-only.
* **`init_filechan`** (30 B) runs at cold boot, before any hook is claimed.

## 9. The diskless obligation

`C-BIOS_MSX1_EU_REPACK_NODISK` is an official target. **Every body that moves
must leave the diskless build answering what the reference answers**, which is
ERR 5 from the hook being unclaimed — not the channel's own error, and not
silence.

⚠️ **D-NODISKGAP IS THE WARNING**: `ex_lfiles` once entered PAST its gate, so a
diskless `LFILES` answered differently from a diskless `FILES`. **A body that
moves must leave exactly ONE entry, and it must be the gate.**
`make nodisk-acceptance` scores it, and its `PINNED` set is a record of
divergence — removing an entry from it is what fixing one looks like.

## 10. How each step is verified

* the verb's own oracle probe **at the byte level** — `kwsweep`'s rows are often
  `LEN`- or value-based and would pass a wrong byte ORDER (`mksd_probe.py` reads
  bytes back with `ASC`, which is what caught §5.1);
* `make kwsweep` — SUPPORTED must not move for a behaviour-preserving change;
* both knife arms re-stamped, ROM hash included;
* `make nodisk-acceptance` for §9;
* the full battery **plus the eight battery-excluded targets**, which include
  `diskbasic-acceptance`, `bdos-acceptance` and `fat-error-acceptance` — the
  three that actually exercise a disk.

## 11. What this spec does NOT claim

* It does not claim the 2394 B is all recoverable: §8's 250 B is interface.
* It does not price the tape/disk shared loaders (§1) — and §6.1 is what that
  omission costs: they PIN the FAT layer in main, so "the bulk" is not available
  until they are priced. **The first version of this spec listed it as step 5
  anyway**, which is a plan asserting availability it had not checked.
* It does not answer where the **FAT walk** should live. `fat_count_free` is a
  13 B stub in main onto the SUB ROM's `fatprim` tenant, so the walk is in
  neither ROM the call crosses between. Whether it belongs in `disk.rom` — which
  has its own FAT for MSX-DOS, deliberately not shared (CALLBACK list, D-DISKVERB2
  note) — is step 5's question and is genuinely open.
* It does not assume the order in §6 survives contact. Each step re-reads the
  walls before it starts.
