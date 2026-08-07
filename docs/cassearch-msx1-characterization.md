<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-CASSEARCH — what an MSX1 prints WHILE the tape search runs

Measured 2026-08-07 on the **Philips VG-8020** *and* the **National CF-3300**
against zerobas at `cc1e20e`, by
[`probes/basic/basic_probe_castail.py`](../probes/basic/basic_probe_castail.py)
(`make castail-characterize`). Spec: [spec-basic-cassearch.md](spec-basic-cassearch.md).

This is the reading the
[castail-msx1-characterization.md](castail-msx1-characterization.md) §5 residual
was blocked on. That slice **found** the divergence — zerobas prints no
`Found:` / `Skip :` progress row — by building the cassette instrument, pinned
it, and filed it. What it never measured is everything a fix needs to know:
*which* arms print, *which verbs* print, and *what the name looks like*.

## 0. 🔴 The residual asked ONE question; the fix needs FOUR answers

[castail-msx1-characterization.md](castail-msx1-characterization.md) §5 rests on
a single row — `cas-load-plain:search`, one verb, one file on the tape, a match
on the first header. From that row alone, four things a fix must decide are
simply unknown, and each of them can be got wrong in a different direction:

| # | question the residual could not answer | why it decides the fix |
|---|---|---|
| 1 | Does `Skip :` appear at all, once **per** stepped-over file, carrying the **skipped** file's name? | A one-file tape can only ever produce a `Found:`. The skip arm is a **different** branch of the match loop. |
| 2 | Does `CLOAD` — the **tokenised** search — print the same rows? | A `$D3` fixture hangs the `LOAD"CAS:"` search (§6 there), so the existing battery could not ask. |
| 3 | 🔴 Do the **other callers** of the same search engine print it? | `MERGE"CAS:"` and `OPEN"CAS:" FOR INPUT` share `cas_open_match`. A print sited in the shared engine prints for them too — so if a reference is **silent** there, that siting would close one divergence by opening two. |
| 4 | Is the name **space-padded to 6** on screen? | It decides whether the emit is a fixed 6-char run or a trimmed one. |

Answers: **1 yes** (per file, the skipped name), **2 yes** (identical rows),
**3 yes — all of them**, **4 not decidable, and it does not matter** (§4).

## 1. The reading, all three sides

Two new fixtures, because the existing one-file tape structurally cannot produce
a skip:

* **`two`** — an $EA ASCII tape holding `SK` (prints `ZQ8`) then `RT` (prints
  `ZQ9`), so a named search must step over one file to reach the other;
* **`twot`** — the tokenised (`$D3`) twin, for `CLOAD`.

Every subject row below is the **search line read UNFILTERED** — the whole tail
between its echo and the next prompt. The `:listing` / `:echo` halves are the
positive controls, and they are controls of the **SKIP**, not merely of the
mount: the first file prints `ZQ8` and the second `ZQ9`, so a machine that took
the wrong file reads `ZQ8` and is caught.

| row | typed | VG-8020 | CF-3300 | zerobas @ `cc1e20e` |
|---|---|---|---|---|
| `cas2-load` | `LOAD"CAS:RT"` | `Skip :SK / Found:RT` | `Skip :SK / Found:RT` | `<nothing>` |
| `cas2-load:listing` 🟢 | (`LIST` after it) | `10 PRINT"ZQ9"` | `10 PRINT"ZQ9"` | `10 PRINT"ZQ9"` |
| `cas2-merge` | `MERGE"CAS:RT"` | `Skip :SK / Found:RT` | `Skip :SK / Found:RT` | `<nothing>` |
| `cas2-merge:listing` 🟢 | (`LIST` after it) | `10 PRINT"ZQ9" / 20 PRINT"ZQ1"` | *(same)* | *(same)* |
| `cas2-cload` | `CLOAD"RT"` (tokenised tape) | `Skip :SK / Found:RT` | `Skip :SK / Found:RT` | `<nothing>` |
| `cas2-cload:listing` 🟢 | (`LIST` after it) | `10 PRINT"ZQ9"` | `10 PRINT"ZQ9"` | `10 PRINT"ZQ9"` |
| `cas2-bare` | `LOAD"CAS:"` (no name) | `Found:SK` | `Found:SK` | `<nothing>` |
| `cas2-bare:listing` 🟢 | (`LIST` after it) | `10 PRINT"ZQ8"` | `10 PRINT"ZQ8"` | `10 PRINT"ZQ8"` |
| `cas2-open` 📌 | `OPEN"CAS:RT" FOR INPUT AS #1` | `Skip :SK / Found:RT` | `Skip :SK / Found:RT` | `<nothing>` |
| `cas2-open:echo` 📌 | (`INPUT#1,A$` / `PRINT A$`) | `10 PRINT"ZQ9"` | `10 PRINT"ZQ9"` | **`10 PRINT"ZQ8"`** |

🟢 = a **positive control**. 📌 = a **pinned divergence**, §5 — and it is not
the one this slice is about.

**The two references agree row for row on all ten readings**, which is what
promotes each of them from "what a CF-3300 does" to "what an MSX1 does". The
VG-8020 is a full side here for the reason
[castail-msx1-characterization.md](castail-msx1-characterization.md) §0 gives:
`RUN"CAS:x"` needs a cassette port, which every MSX1 has.

## 2. R-CS1 — `Skip :` is real, it is PER FILE, and it names the SKIPPED file

`cas2-load` reads `Skip :SK / Found:RT`: two rows, in tape order, the first
naming the file that was **stepped over** and the second the file that was
**taken**. So the progress row is emitted at each decision point of the search
loop, not once at the end, and the name it carries is the **header just read**,
not the name the user asked for.

That is the whole shape a fix needs: one emit at the match arm, one at the miss
arm, both printing the header name the loop has in hand.

## 3. R-CS2 — every verb that searches, prints — including the two the residual never named

🔴 **This is the answer that decided where the fix goes**, and it is the one that
could most easily have gone the other way.

`cas_open_match` (the resident shim over the sub-ROM tenant) has **three**
callers in zerobas: `do_tape_prog` (`CLOAD` / `LOAD"CAS:"` / `RUN"CAS:"`),
`merge_cas` and `oo_dev_cas` (`basic/files.asm`). The residual named only the
first. Measured, **all four verbs print the identical two rows** on both
references:

* `LOAD"CAS:RT"` → `Skip :SK / Found:RT`
* `MERGE"CAS:RT"` → `Skip :SK / Found:RT`
* `CLOAD"RT"` (tokenised) → `Skip :SK / Found:RT`
* `OPEN"CAS:RT" FOR INPUT` → `Skip :SK / Found:RT`

So the progress row belongs to the **search**, not to any verb — which makes the
shared engine the correct and only site. Had any one of them been silent, a
print inside `cas_open_match` would have **closed one divergence by opening
one**, and no amount of reading the code could have said which.

## 4. R-CS3 — the bare form prints `Found:` too, and it is a SEPARATE arm

`LOAD"CAS:"` with no name takes the first file on the tape without comparing
anything: `CAS_WANT_ON = 0` jumps **straight to the match arm**, never through
the compare loop. Both references print `Found:SK` — one row, no skip.

It gets its own row (`cas2-bare`) because no other row here reaches the match arm
by that path, and because it is the one row that must **hold** when the skip arm
is knifed (spec §5, K-SKIP): a form that never skips cannot see a broken skip.

## 5. 📌 R-CS4 — a SECOND divergence, and it is NOT the progress line: `OPEN"CAS:name"` ignores the name

`cas2-open:echo` reads back the text of the file that was opened. Both
references read `10 PRINT"ZQ9"` — file `RT`, the one named. **zerobas reads
`10 PRINT"ZQ8"` — file `SK`, the first one on the tape.**

zerobas does this **deliberately and says so in the source**
([`basic/files.asm`](../basic/files.asm) `oo_dev_cas`):

> `OPEN"CAS:" opens the NEXT file (name-matching is Item A's CLOAD/LOAD/RUN/MERGE
> scope, not OPEN)` — followed by `xor a` / `ld (CAS_WANT_ON),a`.

That scoping decision is now **measured to be wrong**: an MSX1 name-matches on
`OPEN` exactly as it does on the other four verbs. The consequence is visible
twice — the search prints one `Found:SK` instead of `Skip :SK / Found:RT`, and
the channel then delivers the **wrong file's bytes**.

⚠️ **It is pinned and filed, not fixed here.** It is a defect of the OPEN verb's
name handling, in a different file (`basic/files.asm`, main page 1), and closing
it needs its own reference battery — bare `OPEN"CAS:"`, case sensitivity, and
the `FOR OUTPUT` naming half are all unmeasured. Folding it in would be the
[[a-rule-can-claim-more-than-its-evidence]] mistake with the evidence pointing
the right way, which is the easy version to make.

🟢 **The pin is also that row's positive evidence.** A per-side EXACT value is
strictly stronger than the containment controls the other rows use: a dead
machine reads `<nothing>` on both halves and **rots** the pin.

## 6. R-CS5 — the name padding is NOT decidable from a screen, and it does not matter

The tape header holds the name **space-padded to 6**. Read unstripped, both
references show:

```
vg8020  row 7: '  Skip :SK                              '
        row 8: '  Found:RT                              '
cf3300  row 4: ' Skip :SK                               '
        row 5: ' Found:RT                               '
```

(The differing leading margin is the machines' own SCREEN 0 `WIDTH`, not part of
the message — it differs *between* the two references, so it cannot be.)

After `SK` come blanks to the end of the row, and **a trailing pad space is
indistinguishable from unwritten screen**. A CR/LF follows the name, so nothing
can ever land beside it to reveal the cursor column. This battery therefore
**cannot** answer whether the reference emits 6 characters or 2, and neither can
any screen-scraping battery.

It is recorded as a **non-claim** rather than measured badly: emitting the 6
header bytes verbatim and emitting the trimmed name produce a byte-identical
screen. zerobas emits all six, because that is what the loop already has in RAM
and it costs less code than trimming.

## 7. What is NOT claimed here

* **The `OPEN"CAS:name"` name-match defect is not fixed** — §5, pinned and filed.
* **`SAVE"CAS:"` / `CSAVE` / `OPEN"CAS:" FOR OUTPUT` are not measured.** They
  write; they never run the search, so `cas_open_match` is not on their path and
  nothing this slice changes can reach them.
* **`MERGE`'s and `OPEN`'s own tails are not measured**, only their search rows
  and one positive control each. Their after-the-load behaviour is the
  D-CASTAIL question, and it was asked only of `LOAD`/`RUN`.
* **The wording of the failure message** stays the quarantined divergence
  (`basic/PROVENANCE.md`), normalised per side in every row of the battery.
