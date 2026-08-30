# D-OPEN2 — only ONE file may be open at a time, and two documents say otherwise

*2026-08-30. Probe `scratchpad/open2_probe.py`, 13 rows, National CF-3300 vs the
repack: **9 DIFF**. **Measurement only — no code change.***

## 1. The finding

A **second concurrent `OPEN`** answers `Syntax error` on zerobas. The CF-3300
accepts every shape of it.

| row | CF-3300 | zerobas |
|---|---|---|
| `b.1then2` · `c.2then1` — two random channels, either order | OK | **Syntax error** |
| `t.seq2` — two **sequential** channels | OK | **Syntax error** |
| `t.seq1rnd2` · `t.rnd1seq2` — one of each, either order | OK | **Syntax error** |
| `t.seqwrite` — two sequential, then `PRINT#1` and `PRINT#2` | OK | **Syntax error** |
| `g.nolen2` — no `LEN=` on the second | OK | **Syntax error** |
| `h.mf3` — `MAXFILES=3` | OK | **Syntax error** |
| `e.same2` — the **same file** on two channels | **`File already open`** | **Syntax error** |

🎯 **The ceiling is honoured; concurrency is not.** `a.ch2only` opens channel
**#2 on its own** after `MAXFILES=2` and passes on both sides — so the channel
table does raise the ceiling and channel 2 is reachable. What fails is having two
channels open **at the same time**.

⚠️ **The face is wrong as well as the behaviour.** For the same-file case the
reference gives a real diagnosis, `File already open`; zerobas gives
`Syntax error`, which names the parser for a condition the parser is not in.

## 2. Every candidate cause has its own row

Nothing here is argued — the channel **number** (`a.ch2only`, `c.2then1`), the
**filename** (`d.ts2ch1`), the file **mode** (`t.seq2` / `t.seq1rnd2` /
`t.rnd1seq2`), the **`LEN=`** clause (`g.nolen2`) and the **`MAXFILES` value**
(`h.mf3`) are each isolated, and none of them is it.

🟢 **Four controls.** Three one-channel shapes pass on both sides, and
`n.nomaxf` — the same two opens with **no** `MAXFILES` — reads `Bad file number`
on **both**, which is what says the default ceiling of 1 is being enforced
correctly and the fixture is sound. Without that row, "two opens fail" would have
had a second sufficient cause.

## 3. 🔴 Two recorded claims are falsified by this

- `basic/PROVENANCE.md` §MAXFILES: *"`MAXFILES = n` sets how many sequential file
  channels may be open at once … This **retires the single-channel limit** every
  Phase-2 file verb previously shared."*
- `TODO.md`: *"**`MAXFILES` + the multi-channel table** — DONE."*

The **token** work those entries describe is real and oracle-locked
(`MAXFILES` = `MAX`+`FILES`, byte-identical on a VG-8020), and so is the ceiling.
**The concurrency is not.** Both are corrected in place — conclusion inverted,
analysis kept. [[a-fix-falsifies-the-justification-beside-it]]

## 4. How it was found, and what it blocks

Looking for something else: D-PUT3 left open *"is the third-`PUT` counter
per-channel or global?"*, whose row needs two channels. **The two-channel fixture
kept failing and I blamed the fixture three times** — first a missing `MAXFILES`,
then `MAXFILES` itself (measured `OK` alone on both sides, so not that), then an
unisolated `Syntax error`. A line-by-line bisect against **both** machines is
what turned it from a fixture story into a finding.
[[a-case-that-agrees-can-agree-for-the-wrong-reason]]

➡️ **D-PUT3's per-channel question cannot be asked until this is fixed** — the
row it needs is unwritable on this machine.

⚠️ **ONE REFERENCE:** Disk BASIC; a diskless VG-8020 cannot express these rows.
