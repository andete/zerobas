# D-WALLIT — a wall figure hardcoded outside `TODO.md` is unpoliced by design

**2026-08-27.** Closes the open class filed 2026-08-22 by D-DUPSPAN2 §5.2.
New gate: `make wall-literal-check` ([`tools/check_wall_literals.py`](../tools/check_wall_literals.py)).

## 1. The filed claim, run before it was built on

Both halves check out.

* [`tools/gen_resident_abi.py:86`](../tools/gen_resident_abi.py:86) now reads
  `syms.get("__MEAS_LOW_END", LOW_CEILING_FALLBACK)`. The `0x3FE5` is gone; only
  a `0x4000` page-1 fallback remains, and it is documented as always-fatal.
* [`tools/wall_assertion_check.py`](../tools/wall_assertion_check.py) states its
  scope in the docstring — "only `- [ ]` items in TODO.md" — so the class
  genuinely has no gate outside that file.

## 2. The rule, and why the obvious version is unusable

The defect is a **hand copy of a value the build already resolves**. The
assembler writes both sym files on every run; a literal beside a name in that
table is a second, unmaintained source of truth.

The first cut asked "is there a number near a word that is a build symbol?"
That gave **8284 (literal, name) pairs, 8108 of them disagreeing** — any
four-letter identifier crossed with any integer on the line. Useless.

What makes it tractable is requiring a **binding**, not proximity:

| rule | shape | denominator |
|---|---|---|
| **A** PY-BINDING | `NAME = <literal>` in `tools/`, `probes/`, NAME a build symbol | **93 anchored of 626** assignments |
| **B** ASM-COMMENT | `NAME equ <expr>   ; $XXXX…` — the house convention | **64** annotated `equ` rows |

Rule B takes only a **leading** `$XXXX`. Over the 888 commented `equ` rows the
loose form ([`scratchpad/wall_comment_sweep.py`](../scratchpad/wall_comment_sweep.py))
gave 16 DIFFER of which **12 were a value or a neighbour's address**
(`; $0001 (+1) or $FFFF (-1)`, `; -> ends $E15A`). The tight form gives 65 rows
and one — a *span*, `; $E9C9..$E9FA inclusive = 50 bytes` — excluded by a `..`
test. That gap is the difference between a gate people believe and one they
learn to ignore.

⚠️ **The scout's denominator is not the gate's.**
[`scratchpad/wall_literal_sweep.py`](../scratchpad/wall_literal_sweep.py) reports
`960 anchored of 1464` for a wider rule (asm rows too, and an anchor allowed to
be a symbol *named in the comment*). Quoting that figure in the gate would
describe a rule the gate does not run — the same shape as the defect being fixed.

## 3. The class was not empty — three live defects

### 3.1 A probe reading 243 B past its subject, failing, and unread

[`probes/basic/basic_probe_cas_verbs.py`](../probes/basic/basic_probe_cas_verbs.py)
bound `STRSCR = 0xE360`. The build resolves `STRSCR` to **`$E26D`**
([`basic/sysvars.inc:1570`](../basic/sysvars.inc:1570), `RVDESC + 3`); `$E360` was
its address before the string-engine S3 low-region re-layout (`17b9878`), and the
hand copy never followed. `$E26D..$E36D` is the buffer, so the probe was reading
**243 bytes into it** instead of at its `[len][bytes]` header.

Both STRSCR cases had been **failing**, reading all-`$FF`:

```
[FAIL] LINE INPUT#1 read back "HELLOWORLD" … expect 0a48454c4c4f574f524c44, got ffffffffffffffffffffff
[FAIL] 2nd LINE INPUT# at Ctrl-Z EOF …       expect 00, got ff
```

The address alone was the cause. Corrected to `$E26D`, on the same apparatus,
same session, nothing else touched:

```
[PASS] LINE INPUT#1 read back "HELLOWORLD" (len 10) byte-identically
[PASS] 2nd LINE INPUT# at Ctrl-Z EOF yields an empty string (STRSCR len 0)
CAS-verbs: PASS            (6/6; the four non-STRSCR cases passed BOTH times — the control)
```

🎯 **The BASIC was correct the whole time.** `OPEN"CAS:"` round-trip and Ctrl-Z
EOF both worked; only the readout was blind. This is
[[readout-blind-to-its-own-subject]] failing by *disagreeing* rather than agreeing.

🔴 **Why it survived: the probe is README-listed but in NO battery.** It returns
a correct `rc=1`, and nothing ever read it. An honest exit code nobody collects is
not an oracle.

### 3.2 Four of six sysvars pointing at the wrong cell, two of them dead

[`probes/basic/basic_probe_clear.py`](../probes/basic/basic_probe_clear.py)'s
Case 3 (informational) compared six work-area cells across machines and printed
**six `SAME` rows**, two of them `ref='0000' zb='0000'` — agreement manufactured
by two zeroes.

Measured on a VG-8020 with the ceiling moved (`CLEAR 200,&HD000` vs `&HC000`),
[`scratchpad/sysvar_addr_probe.py`](../scratchpad/sysvar_addr_probe.py):

| addr | `&HD000` | `&HC000` | verdict |
|---|---|---|---|
| `$F691` | `$0000` | `$0000` | **DEAD** — was "FRETOP" |
| `$F693` | `$0000` | `$0000` | **DEAD** — was "STREND" |
| `$FC4C` | `$0000` | `$0000` | **DEAD** — was "STKTOP" |
| `$FC48` | `$8000` | `$8000` | live but **ceiling-independent** — not "highest available RAM" |
| `$F672` | `$CDE8` | `$BDE8` | tracks the ceiling (−4096) = **MEMSIZ** |
| `$F674` | `$CD20` | `$BD20` | tracks the ceiling (−4096) = **STKTOP** |
| `$F69B` | `$CDE9` | `$BDE9` | tracks the ceiling (−4096) = **FRETOP** |
| `$FC4A` | `$D000` | `$C000` | tracks the ceiling = **HIMEM** ✅ was right |
| `$F676` | `$8001` | `$8001` | BASIC text base = **TXTTAB** ✅ was right |

🎯 **The correct addresses were already written down in this repo.**
[`basic/sysvars.inc:1528`](../basic/sysvars.inc:1528) and
[`docs/sysvar-rehoming-decisions.md:210`](sysvar-rehoming-decisions.md:210) both
name `MEMSIZ $F672` / `STKTOP $F674` / `FRETOP $F69B`, and
[`:918`](../basic/sysvars.inc:918) gives the chain `… ARYTAB $F6C4 <= STREND $F6C6`.
Nothing compared the probe's copies to them. The probe's own prose block
disagreed even with the code beside it — it said `STREND $F692` above
`STREND = 0xF693`.

Corrected, the informational case stops being vacuous and reports real
divergences, which match the documented REJECT/DEFER rehoming decisions
(zerobas does not publish these):

```
SAME  HIMEM  $FC4A   ref='00d0'  zb='00d0'
DIFF  MEMSIZ $F672   ref='e8cd'  zb='0000'
DIFF  STKTOP $F674   ref='20cd'  zb='80f3'
DIFF  FRETOP $F69B   ref='e9cd'  zb='0000'
DIFF  STREND $F6C6   ref='0380'  zb='0000'
SAME  TXTTAB $F676   ref='0180'  zb='0180'
```

⚠️ **Only one of my two discriminators did any work.** I planned "holds a
plausible RAM address" *and* "moves when the argument that should move it moves".
The first run varied string-space size (`CLEAR 200` vs `CLEAR 1000`) and **nothing
moved at all**, including the live cells — that arm separated nothing and I had to
re-run against the ceiling instead. The live/dead split carried the finding.

### 3.3 A source RAM map wrong about its own addresses

[`basic/sysvars.inc`](../basic/sysvars.inc): the `GFX_SPATN … GFX_SFLAGS` chain
annotated addresses **2 B high**. `GFX_SC` is correctly `$E417`; the very next
row, `GFX_SPATN equ GFX_SC + 2`, claimed `$E41B` — as if `GFX_SC` were four bytes
wide, while its own comment says `(2)`. Three downstream rows inherited it.

| row | comment claimed | assembler resolved |
|---|---|---|
| `GFX_SPATN` | `$E41B` | `$E419` |
| `GFX_SSIZE` | `$E41D` | `$E41B` |
| `GFX_SARGN` | `$E41E` | `$E41C` |
| `GFX_SFLAGS` | `$E41F` | `$E41D` |

And [`:2615`](../basic/sysvars.inc:2615) told a reader siting a host buffer that
basic-core RAM "tops out at STRSCR `$E360..$E380`" — **wrong twice**: `STRSCR` is
`$E26D..$E36D` per [`:1481`](../basic/sysvars.inc:1481) *in the same file*, and it
is not the top; the `GFX_PSTK`/`GFX_D*` block above runs to `$E55F`, 512 B higher.
The real cap is `$E560`, and it is build-enforced (`IF GFX_G8V + 2 > $E560`).
Another [[two-sections-of-one-doc-disagreed]].

All 3.3 edits are comment-only. **All three ROM hashes are unchanged across the
rebuild** — identical before and after:

| image | md5 |
|---|---|
| `build/basic-reloc.rom` | `5d208678fae73fc3a85af5eccffbe8e7` |
| `build/sub.rom` | `129aced38fb33cec8feb8d03ad8d007f` |
| `build/zerobas-main-eu.rom` | `f6349c204f00ffaf2c3c9900d43c0b5c` |

## 4. Exemptions are mechanical, not a convenience list

Rule A's five remaining disagreements are all shapes where **both values are
correct**. Three are decided by the tool with no list at all:

* **PER-BUILD** — the two sym tables disagree, so there is no single value to
  check (`SUB_BUILD` is 1 in `sub`, 0 in `basic`).
* **CONDITIONAL** — the asm source defines the name more than once under an
  assembler `IF`; the text carries both arms and one is live (`FPERR_STROOM`,
  `FPERR_MISSOP` under `IF CLEARPOOL`). 32 names qualify.
* **PUBLISHED** — a probe means the published MSX work-area address while the ROM
  has an internal label of the same name. **No mechanical test separates this**,
  so the two cases are pinned by name in
  [`tools/wall-literal-allow.txt`](../tools/wall-literal-allow.txt) with reasons
  — and both were *measured* on the reference (§3.2's table) rather than accepted.
  This is the two-namespaces hazard already filed separately in `TODO.md`.

## 5. Falsification

`--selftest` plants a drift for **each** rule against the real tree and requires
the tree to be green first (a plant proves nothing on an already-red tree):

```
[rule A] planted drift in probes/basic/basic_probe_clear.py: RED (correct)
[rule B] planted drift in basic/sysvars.inc:                 RED (correct)
[control] tree restored:                                     GREEN (correct)
```

Writes are restored via `try/finally` **and** an `atexit` handler, per the
knife-guard rule from D-KNIFEGUARD — a runner that exits between the write and the
restore leaves the tree cut and invisible to the ROM-hash guard.

## 6. What this does NOT catch

* **Prose.** A free-space sentence in a `tools/` docstring is not a binding and is
  not checked. `wall-assertion-check` covers that shape inside `TODO.md` only; it
  remains uncovered elsewhere, and §3.3's `$E360..$E380` was found by *reading*,
  not by either gate.
* **A literal with no name the build knows.** `PROG_LOAD = 0xC000` anchors on
  nothing; only names in a sym file are comparable.
* **RAM the ROM never labels.** Unchanged from the standing note: RAM has no gate.
* **Whether a pinned entry is still correct.** A pin is believed once written; the
  measurement behind each is recorded here and in the allow file, not re-run.
