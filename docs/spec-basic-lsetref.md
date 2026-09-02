# D-LSETREF — the `LSET`/`RSET` no-oracle split is the DISK ROM, not a firmware revision

*Measured 2026-09-02. Probe: [`scratchpad/lsetref_probe.py`](../scratchpad/lsetref_probe.py).*

## 1. The question this closes

`TODO.md` carried `LSET`/`RSET` on a **never-FIELDed** variable as **NO-ORACLE**:

* cassette-only **Philips VG-8020** → `Illegal function call` (ERR 5)
* disk-equipped **National CF-3300** → pads in place (`AB   `)

zerobas targets the disk machine and agrees with it, so nothing was known to be
wrong — but the row could not score either way. The filed open question was
whether the split follows **disk capability** or **firmware revision**, because
that decides whether the CF-3300 is the right oracle for the row at all.

## 2. 🎯 The controlled pair is FREE, and the argument is arithmetic

🟢 **CLEAN-ROOM: NOTHING HERE READS A REFERENCE ROM.** The rule
([`docs/dev-workflow.md`](dev-workflow.md) §2) is that a reference ROM is *only
ever an oracle -- inputs in, observed outputs out, never disassembled or
byte-copied*, and this section honours it. The identity below is **openMSX's own
published configuration metadata**: `National_CF-3000.xml` and
`National_CF-3300.xml` each carry a `<sha1>` sibling to their `<filename>`, and
those two values are equal. No ROM content is read, derived, or quoted -- the
claim is "openMSX names the same image in both configs", which is a fact about
the emulator's config files. Every behavioural row in §3 is black-box: typed
lines in, screen text out.

openMSX's own ROM database resolves the National MSX1 line to these images:

| machine | disk | main BIOS+BASIC sha1 |
|---|---|---|
| National CF-1200 | no  | `c7a2c5baee6a9f0e1c6ee7d76944c0ab1886796c` |
| National CF-2700 | no  | `c7a2c5baee6a9f0e1c6ee7d76944c0ab1886796c` |
| **National CF-3000** | **no** | **`c7a2c5baee6a9f0e1c6ee7d76944c0ab1886796c`** |
| **National CF-3300** | **YES** | **`c7a2c5baee6a9f0e1c6ee7d76944c0ab1886796c`** |

The CF-3000 and the CF-3300 run **the same 32768-byte main BASIC ROM, byte for
byte**. The CF-3300 additionally carries a disk ROM in slot 3-1.

**So for that pair a "firmware revision" explanation is excluded before any
machine boots — there is no revision to differ.** Whatever separates them is the
disk ROM. This is the load-bearing step, and it costs one `shasum`.

## 3. The observation that backs it

Five rows, three sides, `ZEROBAS_REFCACHE=0`:

| row | vg8020 (cassette) | **cf3000 (cassette, ROM ≡ cf3300)** | cf3300 (disk) | zb |
|---|---|---|---|---|
| `A$="12345":LSET A$="AB"` | ERR 5 | **ERR 5** | `AB   \|` | `AB   \|` |
| `A$="12345":RSET A$="AB"` | ERR 5 | **ERR 5** | `   AB\|` | `   AB\|` |
| `A$="12345":LSET A$="ABCDEFGH"` | ERR 5 | **ERR 5** | `ABCDE\|` | `ABCDE\|` |
| `LSET A$="AB"` (unset target) | ERR 5 | **ERR 5** | `\|` | `\|` |
| `LEN(A$)` after `LSET A$="AB"` | ERR 5 | **ERR 5** | `5` | `5` |
| **`ctl.lit`** `"AB"+"CD"` | `ABCD` | `ABCD` | `ABCD` | `ABCD` |
| **`ctl.str`** `A$+"\|"` | `12345\|` | `12345\|` | `12345\|` | `12345\|` |

Both controls touch no `LSET`, no `RSET` and no `FIELD`, so a fixture fault
reddens a control before it reddens a subject
([[a-case-that-agrees-can-agree-for-the-wrong-reason]]).

🔴 **THE `LEN` ROWS ARE NOT DECORATION.** The probe's `face()` collapses
whitespace runs (`" ".join(txt.split())`), so `AB   |` and `AB |` are the SAME
reading and the four value rows **cannot witness the pad WIDTH** — cf3300 and zb
could pad to different lengths and still agree. `LEN(A$)` is a number and cannot
collapse; both read `5`. The agreement is real.

## 4. Verdict

**The split is DISK vs CASSETTE.** A cassette machine refuses the verb outright;
Disk BASIC implements the non-FIELDed store. zerobas ships a disk ROM, so **the
CF-3300 is the correct oracle for every `LSET`/`RSET` row, and the cassette
machines have no vote on them.** `g.lset` / `g.rset` come off the NO-ORACLE list
and score as ordinary agreeing rows.

➡️ **AND THAT PROMOTION HAS A CONSEQUENCE.** `b.lset` (`LSET A$=5`) was parked in
the same bucket as a three-way disagreement (ERR 5 / ERR 13 / ERR 2). Once the
cassette reading is known to be a refusal of the verb rather than an opinion
about the RHS, the row is a plain **divergence against the right oracle** —
zerobas said ERR 2 where the CF-3300 says ERR 13. That is
[`docs/spec-basic-lsettm.md`](spec-basic-lsettm.md), and it shipped.

## 5. Predictions, scored

* **P1 — cf3000 reads ERR 5 like vg8020. ✅ CONFIRMED.** Not a tautology: the
  VG-8020's ROM is a *different image*, so "the main ROM raises IFC" was a
  one-image observation until the CF-3000 ran.
* **P2 — the Spectravideo SVI-738 (a second, unrelated disk lineage) pads like
  the CF-3300. ❌ NOT MEASURED, AND SAYING SO IS THE POINT.** The machine cannot
  be built on this host: its XML requires `svi-738_rs232.rom` at sha1
  `4e9384c9…` and the local dump is `9de525e0…` — a different image. openMSX
  refuses the machine outright (`Fatal error: Couldn't find ROM file`). Sony
  HB-701FD and Gradiente Expert DD Plus, the only other MSX1 disk machines
  openMSX ships configs for, have no local ROMs at all.
  ⚠️ **So the conclusion rests on ONE disk lineage.** It is not weakened — the
  byte-identical pair is what carries §4, and that pair is National-internal —
  but "Disk BASIC pads" is measured on National's disk ROM only. Whether other
  vendors' disk ROMs agree is **open and untested**, and it does not matter for
  zerobas, whose target IS the CF-3300. [[an-unnamed-outcome-reads-as-no-outcome]]
* **P3 — `LSET A$=5` reads the same error on cf3000 as on vg8020. ✅** Both ERR 5.

## 6. 🔴 The apparatus fault this run found, and it is the recurring class

The FIRST cf3000 attempt returned `<NO OUTPUT>` on **all seven rows, controls
included** — a dead machine, not a finding. Cause: a stock MSX1 boots SCREEN 1
(32 columns, name table `$1800`) and `omsx_repl.SCR_ADDR` is `$0000`/40 columns.
The module's own comment predicts it exactly: *"a stock SCREEN-1 machine would
need 0x1800/768/32 instead"*. The CF-3300 side works only because its `reset`
injects `SCREEN 0`; giving the CF-3000 the same reset fixed it.

**But the harness did not notice, and it CACHED the result.** What was read at
`$0000` in SCREEN 1 is the **pattern-generator table** — character bitmaps
rendered as text — so the capture was non-blank, `probe_refcache.storable()`
accepted it, and **seven ghost entries were written** that no rerun would have
dislodged. Two independent guards were one layer away from catching it:

1. `storable()` refuses `<NO OUTPUT>` — but that string is produced by the
   probe's `face()` *downstream*; the raw capture it inspects is garbage bytes,
   not the sentinel. The guard tests the wrong layer.
2. The D-ECHO oracle judged every slot **BLIND**, and `mis_echoed()` counts only
   `MANGLED` — *"a BLIND slot is a refusal to judge, not a finding"*. Correct
   per slot. But **every slot blind, on every case, is not a blind spot; it is a
   dead machine**, and that aggregate is never asked.

The seven entries were purged by hand. The hole is filed in `TODO.md`; the
tell was that seven *different* programs produced byte-identical screens.
[[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]
[[apparatus-is-part-of-the-measurement]]
