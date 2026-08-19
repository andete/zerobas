# SPEC — R1: ROM region rebalance, step 1 (carve 122 B, spend 80 B on the hard wall)

Status: ✅ **LANDED 2026-07-30.** Signed off with §6 Q1 = page-1 tail, Q2 = leave the
RAM hole (both as recommended). Outcome and the two forced deviations in §7 below.
Parent review: [`rom-region-structure-review.md`](rom-region-structure-review.md).
Baseline: `19e8bfd`, clean build, low **0 B** free / page 1 **7 B** free.

⚠️ **Byte-identity is NOT the gate for this slice** (unlike lean-retire S3). This
change is *expected* to move bytes. **The gate is the two wall numbers.**

---

## 1. What R1 does, and why in this order

Two independent parts, deliberately coupled so the second is paid for by the first.

### §1.1 Part A — delete 122 B of unreachable page-1 code

| # | delete | file | region | bytes |
|---|---|---|---|---|
| A1 | `var_find`, `vf_lp`, `vf_test`, `vf_next`, `vf_hit`, `vf_free`, `vf_full`, `var_get_key`, `vgk_zero`, `var_set_key`, `vsk_new`, `vsk_store` | [`basic/vars.asm:464-265`](../basic/vars.asm:464) | page 1 `$4760-$47B0` | **80** |
| A2 | `div_de_bc`, `mod_de_bc`, `div_zero` | [`basic/expr.asm:2003-1918`](../basic/expr.asm:2003) | page 1 `$523C-$5256` | **26** |
| A3 | `disk_putword` | [`basic/sv-diskwr.inc:41`](../basic/sv-diskwr.inc:41) | page 1 `$6B63-$6B73` | **16** |
| A4 | `VARTAB`, `VARENTSZ`, `VARSLOTS` equates | [`basic/sysvars.inc`](../basic/sysvars.inc) | RAM `$E1C0-$E240` | 0 ROM, **128 B RAM** |

🔴 **A3 AND A4 AS WRITTEN ABOVE ARE BOTH WRONG — see §7.1 and §7.2.** Left here
unedited because the deviations are the finding. A3 is a `IF SUB_BUILD` **gate**, not
a deletion (`disk_putword` is live in the sub build). A4 frees **0 B of RAM**, not
128 — the span was already spent by three later slices.

⚠️ **`VAREND` STAYS.** Cells above it are placed relative to it; removing it moves
the whole RAM map. A4 removes only the three symbols that describe the dead pool.
🔴 **Also wrong — §7.2.** Nothing references `VAREND` outside A1's dead block, and
`STRTAB`, the constraint that claim rested on, is retired. It went with the rest.

⚠️ **`udiv16` STAYS** — it sits immediately below A2 and is live (other callers).
A2 ends at `udiv16`, exclusive.

⚠️ **`var_find_typed` STAYS** — the live F3 typed store, immediately below A1. A1
ends at `var_find_typed`, exclusive. The two are easy to confuse:
[`vars.asm:539`](../basic/vars.asm:539)'s own comment distinguishes them.

### §1.2 Part B — promote the 80 B message pool from low to page 1

Move the block from `err_linebuf_overflow` to `__MEAS_LOW_END` (`$3FB0-$4000`, 80 B)
out of the low region and into main page 1: the two overlapping message strings,
`rerr_sparse`/`rsp_go`, `oo_fail_bfn`, `err_notopen_raise`, `err_bad_filenum`,
`err_file_notopen`.

Placement: **at the end of page 1**, after `basic/missing.asm`'s include and before
the `$8000` overflow guard. Rationale — it is data plus three tiny leaves with no
ordering constraint, and putting it at the tail keeps the diff to a move rather than
a renumbering of the include list.

⚠️ **THE TWO STRINGS OVERLAP AND THAT IS LOAD-BEARING.** `err_overflow` is a pointer
12 bytes into `err_linebuf_overflow` — 23 B (now 21 B after D-MSGENC's baked CRLF)
instead of 34. **Move the block verbatim; do not re-word, re-split, or reorder
either string.** [`main.asm`](../basic/main.asm)'s comment on the block spells out
why, and `err_overflow` has two readers that are nowhere near it.

⚠️ **One byte may come back.** `raise_error`'s range test currently pays a `jp`
instead of a `jr` specifically because `rerr_sparse` is far away
([`main.asm`](../basic/main.asm): "page 1 pays exactly ONE byte for this"). After
the move it may fit a `jr` again. **Do not hand-optimise it — let the build tell
you**, and if it does shrink, the measured page-1 free will read 50 B not 49 B.
Report whichever the build says.

---

## 2. Feasibility — why Part B is legal

Three checks, all already measured in the review, restated as the preconditions this
slice must not violate:

1. **Not contract-forced.** 0 of the block's 9 labels are in the forced-low set
   (review §2) — neither the resident-ABI closure nor the `$0038` ISR closure
   reaches it. So no page-1 sub-ROM tenant and no interrupt can be executing it
   while page 1 is switched out.
2. **Zero sub-ROM references.** Verified for all 8 named symbols: `sub/` mentions
   none of them. Nothing sub-side can be reading the block at all.
3. **Every reader is already main page 1** — `err_msgtab`
   ([`interp.asm:899`](../basic/interp.asm:899),
   [`:949`](../basic/interp.asm:949)), `dl_overflow`
   ([`program.asm:114`](../basic/program.asm:114),
   [`:118`](../basic/program.asm:118)), and files.asm's six OPEN reject sites. A
   page-0 tenant would still reach it (main page 1 stays mapped during a page-0
   call), so the move is strictly safer than the status quo, not merely neutral.

---

## 3. Expected walls

| | before | after A | after A+B |
|---|---|---|---|
| main low `$2812-$3FFF` free | **0 B** | 0 B | **80 B** |
| main page 1 `$4000-$7FFF` free | **7 B** | 129 B | **49 B** (50 B if the `jr` returns, §1.2) |

Both walls off zero for the first time in the arc. **These two numbers are the
gate.** If `make basic-reloc` prints anything else, the slice is wrong — stop and
find out why rather than adjusting the expectation.

---

## 4. Gates

Run from clean (`rm -rf build` first — a warm `build/` has misreported a wall by
69 B before, [[measure-the-wall-from-clean]]), and `make repack-machine` after the
`basic/` change before any probe/acceptance run.

| gate | expected |
|---|---|
| `rm -rf build && make basic-reloc` | **low 80 B free, page 1 49 B free** (§3) |
| `make unit-test` | 54/54 |
| `make diskbasic-acceptance` | 34/34 |
| `make bdos-acceptance` | 12/12 |
| `make fat-error-acceptance` | 7/7 |
| `make abort-acceptance` | 31/31 |
| `make error-trap-acceptance` | all pass |
| `make chancost-characterize` | 39/1 |
| `make probe` | OK |
| `make machines` | OK |
| the three closure walks + `check_resident_abi` + `check_kwtable_identity` | OK (run by `basic-reloc`) |
| `build/sub.rom` | **byte-identical** — R1 touches no `sub/` source, and the resident-ABI addresses A1–A3 shift are not in the import list. If `sub.rom` changes, something crossed the ABI and must be explained. |

### 4.1 Gates with teeth for THIS change

The standing suite is necessary but does not by itself prove the carve was safe —
deleting unreachable code is invisible to every behavioural test, which is exactly
why it *looks* free. Two rows carry the weight:

* **ERR 25 and ERR 6 must still print correctly, and so must ERR 52/59.** Part B
  moves the strings that back them and the raisers for 52/59. `error-trap-acceptance`
  covers the trap decision; the *wording* of the two overlapping strings needs the
  D-LINEMAX and S-FCH-2 rows specifically. **Name the rows in the implementation
  report — do not report "suite green" for this.**
* ⚠️ **A falsification row, WITH A GREEN CONTROL** (S3's lesson: a red row reads as
  success, and mine went red for the wrong reason twice). Required pair:
  * **red row** — re-word `err_overflow`'s tail alone and confirm ERR 25's text
    breaks, proving the overlap is really load-bearing and really under test;
  * **green control** — a comment-only edit to the same block, confirming the
    harness reports unchanged. Without the control, the red row proves nothing.

---

## 5. What R1 explicitly does NOT do

* No eviction, no de-eviction (review §3 refuted de-eviction: 35–155 B *loss* per
  tenant).
* No touching the 457 B of contract-forced duplication (review §3.1).
* No promotion of `input.asm` (446 B — needs page-1 room R1 does not create).
* No change to the tenant tables, the resident ABI, or the three closure gates
  (review §6: leave them alone).
* `README.md`'s stale "Limitations (this slice)" section stays a separate TODO item.

---

## 6. Open question for sign-off

**Q1 — where should the promoted block land in page 1?** §1.2 proposes the page-1
tail (after `missing.asm`, before the `$8000` guard), which keeps the diff a clean
move. The alternative is beside its readers in `interp.asm`/`program.asm`, which
reads better but interleaves the diff with live code and risks the overlap being
"tidied". **Recommendation: the tail**, on the S3 principle that a mechanical move
should stay mechanically checkable. Confirm or override.

**Q2 — take A4's 128 B of freed RAM now, or leave the hole?** The 128 B at
`$E1C0..$E240` becomes unowned. Taking it means re-siting cells and re-measuring
the RAM map; leaving it costs nothing today and keeps R1's diff small.
**Recommendation: leave the hole**, note it in TODO.md as available RAM, and spend
it when something needs RAM — R1's gate is the two ROM walls, and a RAM re-site
would put unrelated risk inside it.

---

## 7. OUTCOME — ✅ landed 2026-07-30

**The gate, measured from clean (`rm -rf build && make basic-reloc`):**

| | before | after | specced |
|---|---|---|---|
| main low `$2812-$3FFF` free | 0 B | **80 B** | 80 B ✅ |
| main page 1 `$4000-$7FFF` free | 7 B | **49 B** | 49 B ✅ |
| `build/sub.rom` | `1dbbfe2f…` | **`1dbbfe2f…` byte-identical** | required ✅ |

§1.2's "one byte may come back" **did not** happen — page 1 reads 49 B, not 50, so
`raise_error`'s range test still pays its `jp`. Reported as the build says it.

`sub.rom` was checked against a build of `HEAD` in a throwaway worktree, not merely
assumed from the ABI-regen check passing. Both hashes `1dbbfe2f87b8ca81…`.

### 7.1 Deviation 1 — A3 became a GATE, not a deletion 🔴

**`disk_putword` is not dead code.** Deleting it stopped the assembly with
`ERROR: Symbol 'disk_putword' is undefined on line 36 of file basic/sv-bsvdisk.inc`.

Cause: [`basic/sv-diskwr.inc`](../basic/sv-diskwr.inc) is assembled into **both**
ROMs, and `disk_putword`'s only caller lives in
[`basic/sv-bsvdisk.inc`](../basic/sv-bsvdisk.inc), which **only `sub/save.asm`
includes** — the BSAVE/SAVE write engine is a page-1 tenant. The review's transitive
sweep walked `basic/main.asm`'s include closure, which does not contain that file, so
the caller was outside the analysed set entirely. The routine is genuinely dead in the
main build and genuinely live in the sub build.

Fix: `IF SUB_BUILD` around the body — the **second** such gate in the tree, and
exactly the use `sub/sub.asm` sanctions for "body .inc files that genuinely differ by
side". Same 16 B off main page 1; `sub.rom` unchanged.

⚠️ **This is the one error in the whole review that the review's own apparatus could
not have caught.** Controls and asserts caught the other three (review §0.1); this
one took building the change. Recorded there as error 4.

### 7.2 Deviation 2 — A4 freed ZERO RAM, not 128 B 🔴

The TODO carried forward "its 128-byte span `$E1C0..$E240` is freed RAM". **It was
already spent**, by three slices that each described themselves as homing in "the
freed VARTAB window": `ARYTAB` `$E1C0`, `DIRECTF` `$E1C2`, `SAVSTK` `$E1C3` +
`SAVTXT`, `ZTRAP` `$E1D1..$E207`. `sysvars.inc`'s own comment block still claimed the
span was free — **corrected in place**, with the current tenants listed low-to-high so
the next reader does not chase it again.

Also stale: "`VAREND` must stay — cells above it are placed relative to it". Nothing in
any build references `VAREND` outside A1's dead block, and `STRTAB` — the constraint
that comment named — is itself retired. All four equates deleted (they emit no bytes;
this is hygiene, not a carve). §6 Q2's "leave the RAM hole" was answered by there
being no hole.

### 7.3 Gates

unit **54/54** · diskbasic **34/34** · bdos **12/12** · fat-error **7/7** · abort
**31/31** · error-trap ALL PASS · chancost **39/1** · probe ALL PASS · machines OK ·
the three closure walks + `check_resident_abi` + `check_kwtable_identity` OK. Also run
because ERR 25's string moved: linemax **60/60**.

**§4.1's rows with teeth, named:** `tests/test_msgenc.py` decodes all 27 message
strings out of the ROM — including `err_linebuf_overflow` ("Line buffer overflow"),
`err_overflow` ("overflow"), `err_bad_filenum` ("bad file number") and
`err_file_notopen` ("file not open") — plus a dedicated `overlap` row asserting
`err_overflow == err_linebuf_overflow + 12`. `chancost-characterize`'s `err_badchan`
(BFN == BFN) and `err_notopen` (59 == 59) drive the two **moved raisers** end-to-end
against the reference machine.

**§4.1's falsification pair, delivered as three rows:**

| row | edit | result |
|---|---|---|
| **green control** | comment-only edit inside the moved block | all 27 messages PASS ✅ |
| **red 1** | re-word `err_overflow`'s tail alone | **both** messages break — `err_linebuf_overflow` → 'Line buffer spilled' ✅ the overlap is load-bearing *and* gated |
| **red 2** | split the two strings into independent `db`s | the dedicated overlap row fires: "the err_linebuf_overflow -> err_overflow overlap is broken" ✅ |

Two reds for two *distinct* reasons, one green control. That is what S3's
"a red row reads as success" lesson asks for.
