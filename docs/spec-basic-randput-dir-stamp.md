# D-RNDDIR — when does a RANDOM `PUT` reach the DIRECTORY?

**Status: ✅ MEASURED AND DECIDED 2026-07-31. Outcome (A) — see §8. Zero ROM
bytes; the whole slice is apparatus + documentation, which is what the filed item
asked for.**
Owner item: [`TODO.md`](../TODO.md) — *"A RANDOM `PUT` stamps the on-disk
directory size immediately; the reference does not."*
Gate: [`probes/disk/diskbasic_probe_lof.py`](../probes/disk/diskbasic_probe_lof.py),
`make lof-acceptance`. Prior art:
[`lof-cf3300-characterization.md`](lof-cf3300-characterization.md) §1, §3, §5.

## 1. What is actually known, and what is not

Measured, and already in the battery ([characterization §1](lof-cf3300-characterization.md)):

```
OPEN "ZQ.DAT" AS #1 : FIELD #1,10 AS A$ : LSET A$="X" : PUT #1,1 : PRINT LOF(1)
   reference   LOF = 256   directory = 0
   zerobas     LOF = 256   directory = 256
```

The `LOF` columns AGREE. The machines separate on the **directory only**, which
is why this row is also the `dir` instrument's own falsification — a directory
comparison that stayed green here would be measuring nothing.

⚠️ **The row stops at the moment before `CLOSE`.** Every reading in the table
was taken from a machine that exited with the channel still open. So the filed
sentence — *"the reference does not stamp"* — is only licensed as *"the
reference has not stamped it YET"*. **Nobody has typed a `CLOSE`.** Three
different worlds all reproduce the measurement exactly:

* **(W1) Timing only.** The reference stamps at `CLOSE`; zerobas stamps early
  *and* at `CLOSE`; a well-formed program sees identical disks. The divergence
  is then invisible from BASIC and costs a real user nothing.
* **(W2) Value.** Both stamp, with **different numbers**. A later program's
  `LOF` then disagrees — user-visible, a defect.
* **(W3) Neither.** The reference never stamps a RANDOM write into the directory
  at all, so its `PUT` data is unreachable afterwards while zerobas's is not.

W1 and W2 and W3 are not distinguishable by anything on record. This slice types
the missing rows.

## 2. And a second thing the record cannot tell apart

The characterization states the rule as *"a RANDOM `PUT` grows it to
`recno × reclen`"*. The only evidence for that formula is the **256** above —
and `OPEN … AS #1` with no `LEN=` clause defaults to reclen **256**
([`basic/files.asm:583`](../basic/files.asm:583)), so `1 × 256 = 256`. But a
256-byte sector is also **256**. 🔴 **The single measured cell agrees with two
different rules and cannot separate them** — the recurring failure this project
has now hit ~21× (memory: `apparatus-is-part-of-the-measurement`; "a case that
AGREES can agree for the WRONG REASON"). A fix aimed with the wrong rule would
reproduce the one measured cell perfectly and be wrong everywhere else
(memory: `err21-no-resume-slice`).

There is a third undetermined term. `grows` presumes `max(old, new)`. Nothing
measured says the reference does not simply **assign**. If zerobas assigns *and*
stamps early, then a `PUT #1,1` into an existing 2048-byte file rewrites its
directory entry to 256 and **1792 bytes become unreachable** — that is data
loss, not a cosmetic. That row has never been typed either.

## 3. The measurement — four new rows

All four go in [`diskbasic_probe_lof.py`](../probes/disk/diskbasic_probe_lof.py)'s
`CASES`, reusing its apparatus wholesale (14.0 s cadence, `echo_missing` guard
anchored on the per-side prompt, `scrmod`-measured geometry, a `/tmp` copy of
[`disk/test720.dsk`](../disk/test720.dsk) per case, the `dir` column read out of
that copy after the machine exits). Every row is ≤ 5 typed lines and ≤ 29
characters per line, so nothing scrolls off and no echo wraps past three rows.

| label | typed | `dir` name | what it can refute |
|---|---|---|---|
| `rnd_put_cl` | `OPEN "ZQ.DAT" AS #1` / `FIELD #1,10 AS A$` / `LSET A$="X":PUT #1,1:CLOSE` / `PRINT LOF(1)` | `ZQ      DAT` | **W1 vs W3.** Does the reference stamp AT CLOSE, and with what number? |
| `rnd_put_rt` | …the same three lines, then `OPEN "ZQ.DAT" AS #1` / `PRINT LOF(1)` | `ZQ      DAT` | **W1 vs W2.** The USER-VISIBLE round trip: what a later program actually reads. |
| `rnd_put_len` | `OPEN "ZQ.DAT" AS #1 LEN=16` / `FIELD #1,16 AS A$` / `LSET A$="X":PUT #1,1` / `PRINT LOF(1)` | `ZQ      DAT` | **`recno × reclen` vs "one sector".** Predicts **16** under the first rule and **256** under the second. §2. |
| `rnd_put_big` | `OPEN "TEST.BIN" AS #1` / `FIELD #1,10 AS A$` / `LSET A$="X":PUT #1,1` / `PRINT LOF(1)` | `TEST    BIN` | **assign vs grow, and DATA LOSS.** A 2048-byte existing file. `2048` = grow; `256` = assign. The `dir` column says whether zerobas's early stamp TRUNCATES it. |

Notes on the design, each load-bearing:

* **`rnd_put_cl` prints `LOF(1)` after the `CLOSE` on purpose.** Its subject is
  the `dir` column, but a row whose only reading is `dir` cannot tell *"CLOSE
  ran and stamped 0"* from *"the CLOSE line never arrived"* — the two states
  produce the same number. The trailing `PRINT LOF(1)` must read `FNO`
  (`File not open`), which is an independent witness that the channel really
  closed. A sentinel that also means "no reading" is not a measurement
  (memory: `appmiss-slice`).
* **`rnd_put_rt` re-opens RANDOM, not `FOR INPUT`.** `rand_exist` already pins
  that a RANDOM open of an existing file seeds `LOF` from the directory (26 for
  `HI.TXT`, both machines), so this row's `LOF` **is** the directory read
  through BASIC — the user-visible half of the same instrument.
* **The attribution control already exists and is GREEN:** `roundtrip`
  (sequential write → `CLOSE` → re-open → **8** on both machines). It says
  `CLOSE`-stamping works on both machines on the *sequential* path, so a red
  `rnd_put_rt` is attributable to the **RANDOM** path and not to `CLOSE` in
  general. Named here so it is a control rather than a coincidence.
* **`LEN=16`, not `LEN=10`.** zerobas requires a power-of-two reclen
  ([`basic/files.asm:256`](../basic/files.asm:256)); `LEN=10` would be refused
  on the zb side and the row would measure the `LEN=` parser instead of the
  size rule. (Whether the reference accepts a non-power-of-two `LEN=` is a
  *different* question and is NOT opened here.)
* **`rnd_put_big` mutates `TEST.BIN`.** Safe: every case runs on its own `/tmp`
  copy; the committed image is never mounted (`run_case`).

## 4. Oracle locks

Each new row gets a `REF_EXPECT` entry and (all four name a directory) a
`DIR_EXPECT` entry, **filled from the first measured reference run**, not
predicted here. The probe's oracle-completeness control already fails `--gate`
on a row with no recorded oracle, so a row added and left unlocked is loud.

⚠️ The oracle is the **reference column only**. A zerobas reading is never
written into `REF_EXPECT`/`DIR_EXPECT` — that is how `disk_probe_closelist.py`
came to encode zerobas's own bug as an oracle (D-BADFNUM §7.1).

## 5. The decision rule — written BEFORE the numbers are in

Phase 2 is chosen by the measurement, and the choice is pre-committed here so it
is not rationalised afterwards:

* **(A) W1 confirmed, no data loss.** `rnd_put_rt` agrees on both machines *and*
  `rnd_put_big` shows zerobas does not truncate an existing entry. Then the
  divergence is a pre-`CLOSE` timing difference that no BASIC program can
  observe, and it does **not** buy ROM bytes at a 23 B low wall.
  → **No ROM change.** Record the measurement in the characterization, retire
  the TODO item as MEASURED-AND-DECLINED, and rewrite `DIR_DIVERGE["rand_put"]`
  from *"filed, open"* to *"decided, permanent"* **with the round-trip rows
  named as the evidence**. The entry stays; only its justification changes, and
  it stays a control that must keep matching.
* **(B) W2, or data loss.** The round trips disagree, or zerobas's early stamp
  shrinks `TEST.BIN`'s entry. Then it is a real defect. → a Phase-2 spec with a
  design, a byte cost, and knives, signed off separately before any `basic/`
  edit. `DIR_DIVERGE["rand_put"]` is then **deleted, not updated**, when it
  lands.
* **(C) W3.** The reference never stamps. → measurement stands, and the
  follow-up question ("is the reference's own `PUT` data reachable at all?")
  is FILED rather than answered here; it is a different subject.

In (A) and (C) this session ships **apparatus + documentation only** and zero
ROM bytes. That is a legitimate outcome for an item whose TODO entry says in as
many words that it "starts as a measurement" — and the four rows are permanent
gate coverage of a path that had exactly one, ambiguous, pre-`CLOSE` row.

## 6. Gates

Phase 1 (probe-only, no `basic/` or `sub/` change — the ROM is untouched, so no
rebuild and no wall measurement is due):

* `make lof-characterize` — the full battery, to take the four readings.
* `make lof-acceptance` — **41 → 45 cases**, 0 unfiled, 0 oracle drift, 0
  mangled, 0 without an oracle lock. `KNOWN_DIVERGE` stays **EMPTY**;
  `DIR_DIVERGE` gains no new entry unless a new row diverges, in which case it
  is filed WITH its measurement per the probe's own rule.
* `make chancost-characterize` is **not** re-run: nothing this phase touches is
  in it. ⚠️ Never two emulator gates at once.

Phase 2 gates are specified with Phase 2, if there is one.

## 7. Knives

A measurement-only phase still needs its instrument shown to CUT, or "the four
rows agree" is unfalsifiable:

* **K1 — the `dir` column must be able to go red on the NEW rows.** Force
  `DIR_EXPECT` for one new row to a wrong value and confirm that row alone
  reports `DIR ORACLE DRIFT` while the other three stay green. Without this,
  four rows that happen to agree prove nothing about the column being live on
  them.
* **K2 — the `CLOSE` really executes.** `rnd_put_cl`'s trailing `PRINT LOF(1)`
  must read `FNO`. If it reads a number, the `CLOSE` did not run and the row's
  `dir` reading is about something else entirely. This is a pass/fail on the
  measured screen, not a code change.

If Phase 2 happens, its own knives are specified there.

## 8. MEASURED — 2026-07-31

`make lof-characterize`, then `make lof-acceptance`. Both machines, the probe's
own apparatus unchanged, **0 mangled rows** on every run.

| row | ref LOF | ref dir | zb LOF | zb dir | |
|---|---|---|---|---|---|
| `rnd_put_cl` | `File not open` | **256** | `File not open` | 256 | agree |
| `rnd_put_rt` | **256** | 256 | 256 | 256 | agree |
| `rnd_put_len` | **16** | 0 | 16 | **16** | diverges (`dir`) |
| `rnd_put_big` | 2048 | 2048 | 2048 | 2048 | agree |

**W1 confirmed; W2 and W3 refuted.** The reference stamps the root-directory
entry **at `CLOSE`**, with the same value zerobas writes, and a later program
re-opening the file reads the same 256 on both machines. The difference is
*when*, and no BASIC program can see it.

**§2's two undetermined terms are now determined.** `LEN=16` reads **16**, so the
rule is `recno × reclen` and sector-granularity is out — the 256 that "confirmed"
the formula had been agreeing with both rules at once. And `rnd_put_big` reads
2048 in all four columns: **no truncation, no data loss**, on either machine.
`max()` is pinned by the PAIR (`rand_put` grows 0 → 256; `rnd_put_big` does not
shrink), not by either row alone. zerobas's `frnd_update_size`
([`basic/randio-body.inc:381`](../basic/randio-body.inc:381)) is a genuine
`max()` — `ret c` / `ret z` before the store — which is *why* it could not
shrink.

**Mechanism, both sides:** zerobas's `fat_rand_put` tails into
`jp fat_dir_update` ([`basic/randio-body.inc:373`](../basic/randio-body.inc:373)),
stamping on every `PUT`; the reference defers to `CLOSE`.

### Knives

* **K1 — CUT.** `DIR_EXPECT["rnd_put_cl"]` forced to `999`: that row alone
  reported `DIR ORACLE DRIFT (recorded 999)` and the gate exited non-zero, while
  `rnd_put_rt` / `rnd_put_big` stayed `agree` and `rnd_put_len` stayed
  `diverges (FILED: dir)`. The `dir` column is live **on these rows**, not merely
  in principle. Reverted.
* **K2 — PASS.** `rnd_put_cl`'s trailing `PRINT LOF(1)` reads `File not open` on
  both machines, so the `CLOSE` executed and the row's `dir` reading is about the
  state a `CLOSE` leaves.
* **Free repeatability check.** The K1 run re-boots every row independently and
  reproduced all four reference readings exactly (256 / 256 / 16 / 2048).

### What landed

Per §5(A): **no ROM change.** Four permanent rows on a path that previously had
one ambiguous pre-`CLOSE` row; `make lof-acceptance` **41 → 45 cases, 0 unfiled,
0 oracle drift, 0 mangled**. `KNOWN_DIVERGE` stays **EMPTY**. `DIR_DIVERGE` holds
`rand_put` **and** `rnd_put_len` — rewritten from "filed, open item" to
"**decided, permanent**", with the round-trip rows named in the probe as the
evidence, so the entries stay controls that must keep matching rather than
suppression.

⚠️ `rnd_put_len` GREW the allowlist. That is allowed only loudly, with a
measurement and an attribution control, and it has both: it is the same
divergence as `rand_put` at a different value, and it is *load-bearing* — it is
what shows the early stamp follows `recno × reclen` rather than the sector size.

### Residual, FILED not answered

A machine reset *between* the `PUT` and the `CLOSE` leaves the two disks
different: the reference loses the write entirely, while zerobas's entry is
already stamped and points at a chain whose FAT state at that instant nothing
here examined. Measuring it needs a reset-mid-program harness this probe does not
have, and it is a robustness question rather than a parity one. Filed in
[`TODO.md`](../TODO.md).

### The lesson

🔴 **A ROW THAT STOPS ONE STATEMENT SHORT LICENSES A WEAKER CLAIM THAN THE ONE IT
GETS WRITTEN UP AS.** `rand_put` measured "the entry is 0 *at this instant*" and
was carried for an arc as "the reference does not stamp the directory". The
missing statement was `CLOSE` — four characters, never typed, and the difference
between a defect and a timing detail.
