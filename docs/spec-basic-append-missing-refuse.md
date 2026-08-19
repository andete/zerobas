# D-APPMISS — `OPEN … FOR APPEND` on a MISSING file must REFUSE, not create

Status: **✅ LANDED 2026-07-31.** Signed off, implemented, falsified and gated;
§7 and §8 record what was RUN. ⚠️ Three of this spec's own claims were corrected
by the measurements — §5(a), §5(c) and §7 — and the corrections are left in place
rather than edited out, because each one is the finding.
Measured by [`docs/lof-cf3300-characterization.md`](lof-cf3300-characterization.md) §4,
found by D-LOF's denominator rows and not aimed at. Filed in
[`TODO.md`](../TODO.md); gated today as an allowlisted divergence in
[`probes/disk/diskbasic_probe_lof.py`](../probes/disk/diskbasic_probe_lof.py)
case `append_new`.

## 1. The defect (measured — carried forward, not re-derived)

On the National CF-3300, `OPEN "ZQ.DAT" FOR APPEND AS #1` on a file that does not
exist:

* raises **`File not found`**,
* leaves the channel **CLOSED** — the following `LOF(1)` reports ERR 59
  `File not open`,
* and **makes no directory entry at all** — the probe parses the machine's OWN
  `/tmp` disk image after it exits and the `dir` column reads **`absent`**.

zerobas creates the file and opens the channel, because
[`basic/fat.asm:282`](../basic/fat.asm:282) does `jp c,fat_io_create` on a
`fat_find` miss.

⚠️ **A COMMENT STATES THE DEFECT AS SETTLED PARITY, AND ITS CITATION CANNOT
REACH THE CASE.** [`basic/fat.asm:266`](../basic/fat.asm:266) says *"A missing
file is created (append == create)"* and the paragraph cites
`disk_probe_append.py` for CF-3300 parity. **Verified myself before writing this
spec:** that probe's sequence is
`OPEN "AP.TXT" FOR OUTPUT … CLOSE` **then** `OPEN "AP.TXT" FOR APPEND …`
([`probes/disk/disk_probe_append.py:9`](../probes/disk/disk_probe_append.py:9)) —
it creates the file with OUTPUT first and only ever appends to an **existing**
one. The parity claim is TRUE for the Ctrl-Z resume rule it measured and simply
does not reach the missing-file case. [`basic/PROVENANCE.md:2588`](../basic/PROVENANCE.md:2588)
repeats it (*"a missing file tail-calls `fat_io_create`"*); both must be fixed.

## 2. The error CLASS — TRACED, because that is the load-bearing question

The TODO asks the fix to confirm the class rather than assume it. The trace:

```
fat_io_append   fat_find miss -> Cy=1 -> (this slice) ret c
  files.asm:304   call fat_io_append
  files.asm:311   oo_done: pop de / pop hl   (neither touches flags)
  files.asm:314   jr c,oo_fail
  files.asm:335   oo_fail: FCH_MODES[ch]=0, FCH_MODE=0, FCH_ACTIVE=0
  files.asm:430   jp load_error
  bload.asm:162   load_error: TAPIOF, ERRMARK=$EE, print err_io = "load error"
```

**So the class is zerobas's `load error` — NOT the string `File not found`.** That
is correct and is not a divergence introduced here: `load error` is zerobas's
pinned rendering of the reference's whole file/channel error family
([`basic/PROVENANCE.md:74`](../basic/PROVENANCE.md:74) — own wording, never the
reference's verbatim strings; the mapping is documented in
[`probes/disk/disk_probe_fat_error_disposition.py:23`](../probes/disk/disk_probe_fat_error_disposition.py:23)).
The identical routine, message and disposition are what
`OPEN"A:NOSUCH.DAT" FOR INPUT AS #1` already reaches — that case is gated TODAY
as `open-missing` in `fat-error-acceptance`. **This slice makes APPEND-of-missing
land on the same class as INPUT-of-missing, and §6 gates exactly that**, rather
than trusting the shape of the code.

Two consequences, both PRE-EXISTING and deliberately unchanged:

* `load_error` is a `ret`-based print path, not a numbered `raise_error` code, so
  APPEND-of-missing will **not** fire an armed `ON ERROR GOTO` — exactly as
  INPUT-of-missing does not. The `load error` family's trappability is the
  standing item in [`docs/spec-basic-error-handling.md`](spec-basic-error-handling.md)
  (code 19 row), not this slice.
* `load_error` calls `TAPIOF` and stamps `ERRMARK=$EE` (a cassette marker) on a
  disk path. Every disk error path already does; no new behaviour.

## 3. The denominator — every site that turns "not found" into "created"

`fat_find` has seven call sites. Five raise on a miss; **two create**, and only
one of those two is wrong.

| # | site | on a `fat_find` miss | measured reference | verdict |
|---|---|---|---|---|
| 1 | [`fatio-body.inc:30`](../basic/fatio-body.inc:30) `fat_io_open` (OPEN FOR INPUT, LOAD, RUN, MERGE, BLOAD) | Cy=1 → error | refuses | ✅ correct |
| 2 | [`fat-delete-body.inc:33`](../basic/fat-delete-body.inc:33) `KILL` | Cy=1 → error | refuses | ✅ correct |
| 3 | [`files.asm:1331`](../basic/files.asm:1331) `NAME`'s old file | Cy=1 → error | refuses | ✅ correct |
| 4 | [`cload.asm:1068`](../basic/cload.asm:1068) cassette-side find | Cy=1 → error | — | ✅ correct |
| 5 | [`sub/fatprim.asm:148`](../sub/fatprim.asm:148) tenant dispatch | marshals Cy back | — | ✅ transport, not policy |
| 6 | [`randio-body.inc:72`](../basic/randio-body.inc:72) `fat_rand_open` → `fro_create` | **creates** | `rand_new`: ref `dir` = **0**, i.e. the reference CREATES | ✅ **intentional** |
| 7 | [`fat.asm:282`](../basic/fat.asm:282) `fat_io_append` | **creates** | `append_new`: ref `dir` = **absent** | 🔴 **the defect** |

The other `fat_io_create` callers do not consult a miss at all and are creates by
definition: `oo_create` (OPEN FOR OUTPUT, [`files.asm:301`](../basic/files.asm:301))
and `disk_write_begin` (SAVE / BSAVE, [`sv-diskwr.inc:35`](../basic/sv-diskwr.inc:35)).
`pch_disk` ([`print.asm:480`](../basic/print.asm:480)) calls `fat_io_putbyte`, not
create — it is not a create site despite the comment in
[`fatiocreate-body.inc:11`](../basic/fatiocreate-body.inc:11) listing it as a
resident consumer.

**So the denominator is 2 create-on-miss sites, and exactly 1 is wrong.** Site 6
is not collateral: the reference genuinely creates on a RANDOM open of a missing
file, so the two sites must stay DIFFERENT and a "make miss = error everywhere"
sweep would be a regression.

`fat_io_append` itself has ONE caller, `oo_append` ([`files.asm:304`](../basic/files.asm:304)).
The body edit is in `fat.asm`'s own text, not in `fatiocreate-body.inc` (which has
two homes, `basic/fat.asm` + `sub/save.asm`), so this lands in the resident main
ROM only.

## 4. The change

**[`basic/fat.asm:282`](../basic/fat.asm:282)** — one instruction:

```asm
                call    fat_find
-               jp      c,fat_io_create     ; not found -> append == create from scratch
+               ret     c                   ; not found -> REFUSE (oo_fail -> load error)
```

Cy=1 propagates unchanged through `oo_done`'s two `pop`s (neither affects flags)
to `jr c,oo_fail`, which releases the claimed channel slot and clears
`FCH_MODES[ch]` / `FCH_MODE` / `FCH_ACTIVE` before `jp load_error`. That is the
same disposition `fat_mount` failure already takes two lines above
([`fat.asm:279`](../basic/fat.asm:279) `ret c`), so no new state is left dirty.

**[`basic/fat.asm:266`](../basic/fat.asm:266)** — the comment, rewritten to state
the measured rule and to say what the cited probe actually covers:

> A MISSING file is REFUSED (Cy=1 → `oo_fail` → `load error`), matching the
> CF-3300, which raises `File not found`, opens no channel and writes no
> directory entry (lof-cf3300-characterization §4). ⚠️ `disk_probe_append.py`'s
> parity claim below covers the Ctrl-Z resume rule on an EXISTING file only — it
> creates its file with OUTPUT first and never appends to a missing one.

**[`basic/PROVENANCE.md:2588`](../basic/PROVENANCE.md:2588)** — *"a missing file
tail-calls `fat_io_create`"* corrected to the refusal, with the same
scope-of-citation note, plus a line in the section's Divergences paragraph.

**[`docs/lof-cf3300-characterization.md`](lof-cf3300-characterization.md) §4** —
marked ✅ FIXED with a pointer here (the characterization keeps its measurement;
only its "filed, not fixed" status changes).

### Byte cost

`jp c,nn` (3 B) → `ret c` (1 B) = **−2 B in main page 1** (`fat_io_append` links
at `$6337`). Baseline measured clean at `224d03f`: low **23 B**, page 1 **20 B**.
Expected after: low **23 B** (unchanged), page 1 **22 B**. This slice FUNDS the
tighter wall rather than spending it; the numbers are re-measured from a clean
`rm -rf build && make basic-reloc` and reported in §8, not asserted here.

## 5. The gate's blind spot, and how it is closed

⚠️ **`append_new` alone cannot tell "the channel was not opened" from "the channel
was opened but `LOF` is broken", and after the fix it AGREES for a reason it
cannot see.** The probe's reading is the LAST error class on screen:

* reference: `File not found` … then `File not open` → value **`FNO`**;
* zerobas after the fix: `load error` (which `err_class` does not classify, by
  design — §2's pinned wording) … then `file not open` → value **`FNO`**.

The two sides agree, and the agreement carries NO information about the OPEN
error class — a fix that raised `syntax error` at OPEN would read `FNO` too. So
three separate instruments are added, each answering a different half:

**(a) A row that tests the channel with a DIFFERENT VERB.** New case
`append_new_wr`, next to `append_new`:

```
OPEN "ZQ.DAT" FOR APPEND AS #1
PRINT #1,"X"
```

with no `LOF` at all. Its value is the last error, which is now the `PRINT #1`
rejection — so a value of `FNO`/`BFN` means **the write was refused**, attributed
to the channel state rather than to `LOF`. Today's zerobas prints no error here at
all (value `None`), so the row is RED pre-fix. Its `REF_EXPECT` entry is recorded
from the first measured run, per the probe's own rule (`None` = not yet recorded);
it is **not** guessed in this spec. **Measured: ref = `FNO`, dir = `absent`** — so
the reference answers a `PRINT #` into the unopened channel with ERR 59, not
ERR 52.

⚠️ **CORRECTION — this row could not fail as first written, and fixing it reverses
§10 Q2's signed-off answer.** With `load error` unclassified, `err_class` returned
`None` for it — and `None` is also what a row reads when **nothing went wrong**.
Pre-fix the row read `None` because the write was SILENTLY ACCEPTED; post-fix it
read `None` because the write was REFUSED. Two opposite outcomes, one value: a
regression back to silent acceptance would not have moved it. A `LOADERR` class
was added to `ERR_CLASSES` to split them. Q2's answer ("don't teach the lof probe
about `load error`") was correct for `append_new`, whose last error is `FNO`
either way, and wrong for a row that did not exist when the question was asked.

⚠️ **And the row found a SECOND defect, one layer below this slice.** Post-fix it
reads ref `FNO` vs zb `LOADERR`: zerobas refuses the write, but with `load error`
where the reference raises ERR 59 `File not OPEN` — while `lof_closed` shows `LOF`
on the very same closed channel AGREEING at ERR 59, so zerobas *has* the code and
it is `PRINT#`/`INPUT#`'s own disposition. **Attributed by measurement, not by
argument:** a control row `ctl_prwr_closed` types the same `PRINT #1,"X"` with no
`OPEN` at all and diverges IDENTICALLY. Both rows are allowlisted under one new
`TODO.md` item and leave together when it lands.

**(b) The `dir` column becomes part of the verdict.** The second instrument is
printed today but **never compared** — `run_case` returns `dsz` and `main` prints
it, while the verdict is computed from the LOF value only. The central claim of
this slice ("no directory entry at all") is therefore invisible to the gate as it
stands. Added: a `DIR_EXPECT` oracle lock (same discipline as `REF_EXPECT`) and a
`DIR_DIVERGE` allowlist, with the row's verdict requiring BOTH columns to match.

⚠️ **This surfaces one NEW divergence, and that is the point** — `rand_put` reads
ref `dir` = **0** while zb `dir` = **256** (already visible in characterization §1,
never gated). A RANDOM `PUT` stamps the on-disk directory size immediately on
zerobas and not on the reference. It is **not** fixed here: it is allowlisted in
`DIR_DIVERGE` naming a NEW `TODO.md` item, and it doubles as the proof that the
new dir gate CUTS (§7 F4) — a row where the LOF column agrees and only `dir`
separates the machines.

**(c) The error CLASS is asserted where zerobas's wording is pinned.** A new case
`append-missing` (`OPEN"A:NOSUCH.DAT" FOR APPEND AS #1`) in
[`probes/disk/disk_probe_fat_error_disposition.py`](../probes/disk/disk_probe_fat_error_disposition.py),
directly beside the existing `open-missing`. That probe is a self-check against
zerobas's own `load error` for exactly the reason §2 gives, so it is the right
home: 7 → **8 cases**, and `append-missing` failing while `open-missing` passes
would say the APPEND path reaches a different class.

⚠️ **CORRECTION — as first added, this row was GREEN OVER A PROVABLY BROKEN
SUBJECT, and only the knife found it.** With the fix reverted (F5), the row still
PASSED. The cause: `fat-error-acceptance` invokes the probe with **no `--diska`,
i.e. an empty drive**, so all seven pre-existing cases fail inside `fat_mount` and
never reach `fat_find` at all — the docstring claims the find miss, the probe
measured the mount miss, and the two are **indistinguishable by their answer**
(`load error` either way). Re-run on the same knife build with a disk mounted,
`append-missing` goes RED (silent — APPEND created the file, so nothing was
raised) while the other seven stay green.

The probe now makes its own **/tmp COPY** of `disk/test720.dsk` when no `--diska`
is given. That is not tidiness: a build where APPEND still creates **writes
`NOSUCH.DAT` into the mounted image** — measured, and the reason the committed
image must never be mounted here. A directory readout was added alongside, so the
row is two-sided like the lof battery's: a build that printed `load error` and
created the entry anyway cannot pass. The seven pre-existing rows all still pass
with a disk mounted, so the probe now measures what it always claimed to.

**The allowlist entry is DELETED, not updated.** `KNOWN_DIVERGE["append_new"]`
goes away entirely; `make lof-acceptance` must read 16 rows + the new one = **17
cases with `append_new` AGREEING**.

## 6. Two-sided controls that must NOT move

* `append_exist` — APPEND onto an EXISTING file: **26 / 26**, unchanged. This is
  the row that catches a fix that refuses too much.
* `python3 probes/disk/disk_probe_append.py` — the Ctrl-Z round trip
  (`"first\r\nsecond\r\n\x1a"`, byte-identical to the CF-3300) must still pass.
* `roundtrip`, `lof_input`, `lof_bin`, `lof_closed`, `ctl_syntax` — the battery's
  five standing controls.
* `fat-error-acceptance`'s existing seven cases, `open-missing` in particular.
* The echo guard is not touched. A `MANGLED` row stays fatal with or without
  `--gate`.

## 7. Falsification — RUN

Every row below was executed. The knife was applied to the **landed patch**
(`ret c` reverted to `jp c,fat_io_create`, clean rebuild, machine reinstalled),
not merely to the pre-fix history, and it was **verified to CUT** before anything
was scored: `fia_walk` moved $6361 ↔ $6363, `fia_walked` $6374 ↔ $6376 and page-1
free moved 22 ↔ 20 B, so the emitted bytes really did change.

| | result |
|---|---|
| **F1** | 🔴 as required — `append_new` ref `(FNO, absent)` vs zb `(0, 0)`, RED on **both** instruments; `append_new_wr` ref `(FNO, absent)` vs zb `(None, 0)` |
| **F2** | ✅ green control — `append_exist` 26/26 `agree`, `roundtrip` 8/8, and `disk_probe_append.py` byte-identical (`b'first\r\nsecond\r\n\x1a'`) on both machines |
| **F3** | 🔴 as required — `append_new_wr` on the unfixed build reads `None`: **no error at all**, the write silently accepted. This is the reading that exposed the `None`-conflation in §5(a) |
| **F4** | ✅ the dir gate CUTS — `rand_put` has **agreeing** LOF columns (256/256) and separates only on `dir` (0 vs 256): a row the old single-column verdict called `agree` |
| **F5** | ⚠️ **FAILED FIRST, and that was the finding** — see §5(c). The row stayed GREEN with the subject broken because the drive was empty. After the probe was given a disk: 🔴 RED on both instruments (silent screen **and** `NOSUCH DAT` created), seven green controls beside it |

⚠️ F5 is the slice's sharpest lesson: **a red falsification row is not the only
way a knife pays — a GREEN one is a claim about the APPARATUS, and here it was
right.** Had F5 been skipped as "obviously fine, the class trace is clear", the
class assertion this item was filed to make would have shipped measuring nothing.

## 7b. Falsification — as planned (kept for comparison with §7)

| | experiment | must show |
|---|---|---|
| **F1** | **Delete the code under test**: restore `jp c,fat_io_create`, rebuild, and **verify the knife CUT** by diffing `build/basic-reloc.sym` (`fia_walk`/`fia_walked` must shift by 2 B and page-1 free must return to 20) | `append_new` **and** `append_new_wr` go RED on BOTH instruments |
| **F2** | the GREEN control alongside F1 | `append_exist` stays 26/26 and `disk_probe_append.py` stays byte-identical — so F1's red is attributable to the miss path, not to APPEND generally |
| **F3** | run `append_new_wr` against the UNFIXED build | RED with value `None` (no error at all) — proving the row can distinguish "channel opened" from "channel refused" without consulting `LOF` |
| **F4** | the dir gate | `rand_put` (LOF columns agree, `dir` 0 vs 256) must be the row the new dir comparison flags — a gate that flagged nothing would be measuring nothing |
| **F5** | `fat-error-acceptance` with F1's build | `append-missing` RED while `open-missing` stays GREEN |

⚠️ F1 and F5 are RED-expected rows and each is paired with a GREEN control (F2,
and `open-missing` inside F5), because a red falsification row on its own reads as
success when the apparatus is simply broken.

## 8. Gates — RUN

Clean `rm -rf build && make basic-reloc`, then `make repack-machine`, then the
standing set. No two emulator gates ran concurrently; no rebuild while a
differential was running.

| gate | result |
|---|---|
| clean `basic-reloc` | low **23 B** (unchanged), page 1 **20 → 22 B**; **dead-code 0 dead in BOTH builds** |
| `unit-test` | **55/55** |
| `lof-acceptance` | **18 cases, 0 unfiled divergences, 0 oracle drift, 0 mangled** — `append_new` AGREES on both instruments, its `KNOWN_DIVERGE` entry DELETED |
| `fat-error-acceptance` | **8/8 + directory check**, ALL PASS |
| `chancost-characterize` | **39 cases, 0 filed** — allowlist still EMPTY |
| `diskbasic-acceptance` | **34/34** |
| `bdos-acceptance` | **12/12** |
| `abort-acceptance` | **49/49** |
| `linemax-acceptance` | **60/60** |
| `arrdim-acceptance` | **73/73** |
| `clearpool-acceptance` | **52/52** |
| `error-trap-acceptance` / `stop-trap-acceptance` | PASS |
| `array-acceptance` | **149/151** — the two standing rows confirmed BY NAME: `ifc.instr.zero`, `ifc.instr.neg`, capitalisation-only |
| `disk_probe_append.py` | functional PASS + differential PASS, byte-identical |

⚠️ `disk_probe_append.py` needs `ZEROBAS_BASIC_MACHINE` set explicitly — it
refuses to default (`lean-retire-s1-explicit-machine`).

## 9. Deliberately NOT in this slice

* **`fat_rand_open` keeps creating on a miss** — §3 site 6, measured-correct.
* **The `load error` wording and its non-trappability** — §2; the pinned
  divergence family, owned by `spec-basic-error-handling.md`.
* **`rand_put`'s directory divergence** (ref `dir` 0, zb 256) — newly surfaced by
  §5(b), allowlisted and filed as its own `TODO.md` item.
* **`diskbasic_probe_chancost.py`'s missing echo guard** — its own filed item.

## 10. Sign-off — answered 2026-07-31

1. **Gate the `dir` column across the WHOLE battery** (§5b), accepting one new
   allowlist entry for `rand_put` + a new filed TODO item — or gate `dir` only on
   the two `append_*` rows? *Recommendation: the whole column.* The claim under
   test is a directory claim, the column is already measured and printed, and
   scoping the gate to "the rows I currently care about" is how a second
   instrument stays decorative.
2. **Assert the error class in `fat-error-acceptance`** (§5c) rather than teaching
   `diskbasic_probe_lof.py`'s `err_class` about `load error`? *Recommendation:
   yes.* Adding `load error` to the lof probe's class table would change nothing
   for `append_new` (the last error is `FNO` either way) and would put zerobas's
   pinned wording into a table whose stated purpose is machine-independent
   classes.
3. Confirm that the **`ON ERROR` non-trappability** of `load error` on this path
   (§2) stays out of scope, matching `OPEN … FOR INPUT` of a missing file.

**Answers.** Q1 → **whole battery** (signed off). Q2 → **`fat-error-acceptance`**
(signed off) — but the *reason given* for it was later falsified in part: see the
§5(a) correction, which required adding `LOADERR` to the lof probe's classes after
all, because a row that did not exist when Q2 was asked could not otherwise fail.
The chosen HOME for the class assertion was and remains `fat-error-acceptance`.
Q3 → out of scope, proceeded on that basis; `PRINT#`'s ERR 59 gap found along the
way is filed as its own item rather than folded in (ONE TODO item per session).
