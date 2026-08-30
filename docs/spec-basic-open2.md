# D-OPEN2 — a second disk OPEN raises a SPURIOUS `Syntax error` (the open itself succeeds)

🔴 **CORRECTED 2026-08-30, HOURS AFTER IT WAS FIRST WRITTEN AND COMMITTED. The
first version of this document said "only ONE file may be open at a time" and
that is an OVER-CLAIM.** Multi-channel works: **device+device, device+disk and
disk+device are all fine on both machines**. Every row in the first pass opened
two DISK channels — `A.TXT` and `B.TXT` are disk files too — so a device channel
was never in the comparison, and what read as "every shape" was one shape.
The finding is narrower and sharper: **two DISK channels.**
🎯 The rows below stand exactly as measured; only the CONCLUSION drawn from them
was wrong. [[a-case-that-agrees-can-agree-for-the-wrong-reason]]

*2026-08-30. Probe `scratchpad/open2_probe.py`, 13 rows, National CF-3300 vs the
repack: **9 DIFF**. **Measurement only — no code change.***

## 1. The finding

A second concurrent **disk** `OPEN` answers `Syntax error` on zerobas. The
CF-3300 accepts every shape of it.

| row | CF-3300 | zerobas |
|---|---|---|
| `v.2dev` — two **device** channels | OK | **OK** |
| `v.dev1dsk2` · `v.dsk1dev2` — one device, one disk, either order | OK | **OK** |
| `v.2dsk` — two **disk** channels | OK | **Syntax error** |

🎯 **So the channel machinery is not the subject — the FAT engine's single global
streaming state is.** `basic/sysvars.inc` says so in its own words: *"Because
fat.asm keeps ONE global set of streaming state … only one channel's state is
'live' in those globals at a time"*, swapped by a write-back cache discipline.
A device channel needs none of it, which is why it coexists.

The disk-only rows:

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

- `basic/PROVENANCE.md` §MAXFILES: *"… This **retires the single-channel limit**
  every Phase-2 file verb previously shared."*
- `TODO.md`: *"**`MAXFILES` + the multi-channel table** — DONE."*

⚠️ **AND MY FIRST CORRECTION OF THEM WAS ITSELF TOO BROAD.** Those entries are
**mostly right**: the token work is oracle-locked, the ceiling is honoured, and
multi-channel genuinely works for device channels and for one-disk-plus-device.
What does not work is **two disk channels at once** — exactly the case the FAT
engine's single global streaming state would predict. Both documents now say
that, rather than the blanket refutation the first pass wrote.
[[a-fix-falsifies-the-justification-beside-it]]

⚠️ **Separately measured and NOT the same thing:** `OPEN"LPT:"AS #1` — a device
with no `FOR` clause, i.e. RANDOM mode — is `Syntax error` here and `OK` on the
CF-3300 (`v.devbare`). It is its own divergence, and it **voided a whole
discriminator run** by failing as the baseline of a comparison before anyone
noticed it was red.

## 3a. Where it is raised — narrowed by rows, not by reading

`ERL` names the line, once the handler is armed **after** `MAXFILES` (which
disarms `ON ERROR` on both machines — that cost an earlier probe):

| row | reading |
|---|---|
| `f.two` — second disk open, valid channel | **`ERR 2 AT 40`** — the OPEN itself |
| `f.pin` — second open, channel `#9` | `ERR 52 AT 40` — the readout can name line 40 |
| `f.one` / `g.alone` — one open | OK at line 50 — the handler survives |

🔴 **Two hypotheses refuted on the way, both mine.**

1. *"The open succeeds and corrupts the text cursor, so the NEXT statement is the
   syntax error."* `f.two` says `AT 40`: it is the OPEN.
2. *"It is the `jr c,oo_fail_syn` after `oo_parse_reclen`, the only `Syntax
   error` exit on the disk path after the channel check."* `g.nolen` — the same
   open with **no `LEN=` clause at all**, where `oo_parse_reclen` returns the 256
   default with carry clear and cannot fail — is **also `ERR 2 AT 40`**. So that
   exit is not the site and the enumeration was incomplete.

🎯 **What the rows leave, and it fits every observation:** `fch_claim` is reached
only by a **disk** open, and when a *second* channel is claimed it calls
`fch_save_active` → `fch_flush_active` — the write-back that persists the FIRST
channel's state. **That path executes only when a second disk channel is
claimed.** A device open never calls `fch_claim` at all (it just sets
`FCH_MODES[ch]`), which is exactly why device+disk coexists.

⚠️ **Named as the remaining candidate, not as the cause.** Neither `oo_nodisk`
(`load_error`) nor `oo_fail` (`df_or_loaderr`) maps to ERR 2, so the raise is
either inside that write-back chain or a **deferred `FPERR`=4 surfacing at the
statement boundary** — which would be attributed to line 40 exactly as observed.
Distinguishing those two is the next step, and it wants instrumentation.

## 3b. 🎯 It is not a refusal — the open COMPLETES and the error is spurious

Trapping the `ERR 2`, `RESUME`ing past it and reading the channel table out of
RAM (`FCH_MODES` at `$EA00+ch`, `FCH_ACTIVE` at `$E012`):

| row | `MODES[1]` | `MODES[2]` | `ACTIVE` |
|---|---|---|---|
| `s.two` — the failing second open | **4** | **4** | **2** |
| `s.one` — one open | 4 | 0 | 1 |
| `s.bad` — the `#9` reject | 4 | 0 | 1 |
| `s.none` — nothing open | 0 | 0 | 0 |

**Both channels are marked open and channel 2 is active.** The second `OPEN` did
all of its work — table entry, slot claim, the lot — and the `Syntax error` is
raised *afterwards*. It is a **spurious deferred error**, not a refusal, which is
why `oo_nodisk`/`oo_fail` never matched: neither of them ran.

And the channels are usable afterwards:

| row | result |
|---|---|
| `u.field` — `FIELD` on both channels | **works** |
| `u.put1` / `u.put2` — one `PUT` on each, individually | **both work** |

⚠️ **`u.both` (write through both, read one back) is `<NO OUTPUT>` and is NOT
read here as "two-channel writes fail".** It has three sufficient causes —
D-PUT3's `PUT` counter, two 128-byte `STRING$` temps against the default pool, or
a genuine two-channel write fault — and separating them needs its own row set.
[[a-case-that-agrees-can-agree-for-the-wrong-reason]]

➡️ **So the fix may be small: stop raising the error.** What remains is finding
what sets `FPERR`=4 on this path. Guessing has already cost two refuted
hypotheses (§3a), so the next step is **instrumentation, not another reading** —
the candidate is still `fch_claim` -> `fch_save_active` -> `fch_flush_active`,
the write-back that only runs when a second disk channel is claimed, and whose
CALSLT into the sub-ROM is the kind of path that sets `SH_ERR`.

## 3c. Located to one call, with six hypotheses refuted by rows

Diagnostic knives (cuts made to LOCATE, never proposed as fixes), each rebuilt
and re-run against the ERL rows:

| cut | spurious `ERR 2` |
|---|---|
| `call fch_save_active` in `fch_claim` | **gone** |
| only `fch_flush_active` (the CALSLT flush) | remains |
| only the `ldir` context save | remains |
| clear `SH_ERR` after the tenant call | remains |
| guard `IX` around `fch_claim` | remains |

So the raise is inside `fch_save_active`, in the part that survives cutting both
the flush and the save: **`fch_ctx_addr`**, which asks the string-heap tenant for
the channel's context-block address (op 18) through a CALSLT.

🔴 **SIX HYPOTHESES REFUTED, ALL MINE:** cursor damage after the statement
(`ERL` says `AT 40`); the `oo_parse_reclen` exit (`g.nolen` has no clause and
still fails); the flush; the `ldir`; a stale `SH_ERR`; and an `IX` clobber —
the last despite `fch_ctx_addr`'s own header naming IX, which is what made it
worth testing.

🎯 **AND THE STRUCTURAL FACT THAT EXPLAINS WHY NOTHING CAUGHT THIS.**
`fch_save_active` returns early when `FCH_ACTIVE` is 0, so `fch_ctx_addr` — and
with it op 18 `sh_chan_addr` — **never executes while only one channel is
open**. It runs for the first time exactly when a second disk channel is
claimed. The whole path is untested by construction, and every single-channel
row in this project has always been green.

### What the tenant actually returned (RAM readout, not reasoning)

Dumping the request block in the error handler — `SH_OP` `$E36D`, `SH_LEN`
`$E36E`, `SH_PTR` `$E371`, `SH_ERR` `$E37E`:

| row | `SH_OP` | `SH_LEN` | `SH_PTR` | `SH_ERR` |
|---|---|---|---|---|
| the failing second open | 18 | **1** | **47572 = `$B9D4`** | **0** |
| one channel / none (controls) | 255 | 255 | 65535 | 255 |

🎯 **The controls read as UNINITIALISED**, which is the direct confirmation that
op 18 never runs with a single channel — the structural fact above, measured
rather than argued.

🟢 **And the call SUCCEEDED**: `SH_ERR` = 0, `SH_LEN` = 1 (channel 1 is the one
being saved, which is correct), and the address is plausible. `TXTTAB` = `$8001`,
`HIMEM` = `$F380`; the table is carved below **`TXTMAX`**, not below `HIMEM`, and
`$B9D4` plus a ~200 B pool and two ~562 B contexts lands about where `TXTMAX`
should be. **So the 50-byte context save is not landing in the program**, and the
"stray write corrupts the tokenised text" theory — which would have explained a
`Syntax error` neatly — is not supported.

⚠️ **Noted in passing, not chased:** `VARTAB` (`$F6C2`) and `STREND` (`$F6C6`)
both read **0** — zerobas does not maintain those published MSX cells. A program
that `PEEK`s them gets 0 where a reference gives a real pointer. That is its own
question and does not belong to this item.

⚠️ **NEXT STEP NEEDS A DEBUGGER, NOT ANOTHER READING.** The handler
(`sub/strheap.asm sh_chan_addr`) and its callee chain read correctly for both
channel 1 and channel 2, and BASIC-level bisection has bottomed out. What is
wanted is a breakpoint on the second `fch_ctx_addr` with a register/RAM dump —
guessing further is what produced the six refutations above.

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
