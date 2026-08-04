# Echo-delivery characterisation — every reading, D-ECHO

Companion to [`docs/spec-probe-echo.md`](spec-probe-echo.md). Everything below
was measured on `5c96a0a` (tree clean, `make -q build/zerobas-main-eu.rom` exit 0,
`make repack-machine` run first). Reference `Philips_VG_8020`, subject
`C-BIOS_MSX1_EU_REPACK_DISK`.

---

## 1. 🔴 The two machines do not share screen geometry

Injecting through the real `_tcl` timeline and reading `SCRMOD` (`$FCAF`),
`LINLEN` (`$F3B0`) and the SCREEN-0 name table after every slot:

| | `Philips_VG_8020` | `C-BIOS_MSX1_EU_REPACK_DISK` |
|---|---|---|
| left margin of every row | **2** | **1** |
| `LINLEN` | **37** | **39** |
| columns used | 2..38 | 1..39 |
| prompt | `Ok`, on its own row | `ZB`, prefixing the echo row |

```
VG8020    row 0 |  Ok                                    |
          row 1 |  PRINT"[";1+1;"]"                      |
          row 2 |  [ 2 ]                                 |

zerobas   row 0 | ZBPRINT"[";1+1;"]"                     |
          row 1 | [ 2 ]                                  |
          row 2 | ZB                                     |
```

A comparator with either number hard-coded is wrong on one machine — and wrong
in the direction that reports the *subject* as mangled. The margin is measured
per capture, the width is read from the machine.

⚠️ The last row of the reference carries the function-key line
(`color auto goto list run`) permanently, and the cursor is a live cell in the
name table that decodes to a blank. Both matter below.

## 2. The echo is contiguous, and it survives the next injection

A 43-character line (`_tcl` chunks it into 38 + 5) wraps and **resumes at the
margin of the next row**, on both machines:

```
row 0 | ZBA$="012345678901234567890123456789012|
row 1 | 3456789012"                            |
```

So `"".join(row[margin : margin+LINLEN])` rejoins what wrapping split, and a
wrapped echo is a plain substring of that stream. Measured on both machines.

An echo also survives the following injections — the dump at `t + 0.8·step`
sees it — until something clears or scrolls the screen.

## 3. The direct-mode positive control

Phase O re-expressed in `direct` mode: the line numbers and the final `RUN`
written out by hand, so the injected bytes and every `after time` slot are
**identical** to the stored-mode run.

| run | independent oracle (`__lines`) | echo oracle |
|---|---|---|
| phase O, stored, zb | case 22 stored `20,30,40` | case 22, `10 ON ERROR GOTO 40` |
| **phase O, direct, zb** | case 22 stored `20,30,40` | **case 22, `10 ON ERROR GOTO 40`** |
| phase O, direct, ref | — | **none** |

🎯 **The race is in the DELIVERY path, not the store path.** `mode` selects only
which branch of `_tcl` composes the text. This is what lets one oracle cover
both, and it is why the class was never a stored-mode curiosity.

(The `__lines` walk is available here only because these payloads happen to be
storable program lines. A real `direct`-mode probe has no such oracle — that is
the entire gap.)

## 4. Agreement with the stored oracle, on the real phases

| phase | machine | stored oracle | echo oracle | verdict |
|---|---|---|---|---|
| O | zb | case 22 | case 22, `10 ON ERROR GOTO 40` | **AGREE** |
| O | ref | — | — | AGREE |
| Q2 | zb | case 12, case 22 | case 12 `30 SCREEN0:PRINT"ZK";A:END`, case 22 `10 ON ERROR GOTO 40` | **AGREE** |
| Q2 | ref | — | — | AGREE |

The echo oracle names not just the case but the **line**, and it is the same
line the stored oracle says never entered. Slot coverage on phase O/zb: 169 `OK`,
68 `BLIND/rewrote`, 7 `BLIND/mode`, 1 `MANGLED` of 245.

The seven `BLIND/mode` slots are the whole of case **23**: case 22's untrapped
error leaves the machine in SCREEN 2, so the next case is typed where this scrape
cannot see it. The stored oracle reads case 23's chain regardless — the clearest
single instance of why both are kept (spec §5).

## 5. 🔴 The swallow count is the length of the preceding injection

D-DELIVER recorded that four characters were swallowed and that four is also the
length of the preceding injection (`CLS`+CR), *"suggestive and NOT established"*.
It is established now. Varying only the reset's last line on the phase-O batch:

| preceding injection | its length with CR | swallowed | typed → echoed |
|---|---|---|---|
| `CLS` | 4 | **4** | `10 ON ERROR GOTO 40` → `N ERROR GOTO 40` |
| `CLS:REM1` | 9 | **9** | → `OR GOTO 40` |
| `CLS:CLS` | 8 | **8** | → `ROR GOTO 40` |
| `CLS:REM123456` | 14 | **14** | → `TO 40` |
| `CLS:CLS:CLS:CLS` | 16 | **16** | → ` 40` |
| `CLS:REM123456789012345678` | 26 | — | (the batch delivered clean) |

The last three rows were **stated as predictions before the run**. Five
predecessor lengths, five exact hits.

A sixth confirmation arrived unbidden, from a suite nobody designed for it:
`time-acceptance` mangles `30 PRINTCHR$(67);CHR$(35):END`, whose predecessor is
`20 SWAP TIME,A` — 14 characters, **15** with its CR — and exactly **15** were
swallowed.

⚠️ **What this is NOT.** It is a *rule*, not a mechanism. A story that fits — the
ROM restores a `GETPNT` it saved past the previous line, so the harness's fresh
buffer is read from offset N — is consistent with D-DELIVER's finding that
`GETPNT == KEYBUF` immediately *after* every injection, because that reading was
taken after the harness wrote the pointer and not after the ROM restored one.
**That is a hypothesis and it is not measured here.** What is measured is the
count, six times, exactly.

It also does not explain the *floor*: why the race fires on some slots and not
others. `CLS:REM123456789012345678` shifts the alignment and nothing mangles at
all. [`docs/spec-probe-delivery.md`](spec-probe-delivery.md) §9.1 stands.

## 6. 🔴 Four false-positive classes, all found by MEASUREMENT

Every one of these passed inspection and failed the corpus. Each is now a row in
[`tests/test_echo_oracle.py`](../tests/test_echo_oracle.py) that cannot go silent.

| # | control that failed | payload that broke it | damage |
|---|---|---|---|
| 1 | "the typed text is absent" | every case — all are preceded by a `CLS` reset that erases its own echo | would have fired on every case in every suite |
| 2 | "…and the screen GREW" | `linemax`: a 254-character line then `LIST` — the listing **scrolls** the `LIST` echo off the top while leaving *more* rows than before | **60/60 → exit 2** |
| 3 | "…and the screen LOST NOTHING" | `missing`: `WIDTH 40:CLS:PRINT "AB";CHR$(35)` — clears, then prints. The previous screen held only `Ok` and the permanent function-key row, and a clear brings **both back**, so nothing was "lost" | **59 fires in one suite, exit 2** |
| 4 | "…and a proper SUFFIX is on screen" | `lnblank`: `2\t0 REMX` — the ROM **renders** the tab as blanks, so the typed text can never be a substring while ` REMX` is | 4 fires, and see below |

🔴 **Class 4 was caught by the ZERO-RED control, not by inspection.** It fired on
`Philips_VG_8020`, which D-DELIVER measured mis-delivering 0 in 30. A guard that
reddens the reference is measuring something other than the race
[[knife-that-reddens-nothing-is-the-finding]]. Nothing in the verdict itself
looked wrong; the machine it fired on is what gave it away.

The surviving rule takes its positive evidence from the **mechanism** (§5) rather
than from the shape of the screen: the race swallows a prefix, so a real mangled
echo is a proper suffix of what was typed. A wiped echo leaves no suffix; a
truncated one always does.

## 7. What the corpus found — six real mis-deliveries, four of them invisible before

| suite | mode | typed | echoed | swallowed | stored oracle |
|---|---|---|---|---|---|
| `array` c20 | stored | `10 DIM C(1,1,1,1):C(1,1,1,1)=6` | `IM C(...)=6` | 4 | **also fired** |
| `graphics` ×4 | stored | (D-DELIVER's four) | — | 4 | **also fired** |
| `input-devices` | stored | — | — | — | **also fired** |
| `error-trap` c13 | **direct** | `10 ON ERROR GOTO 100` | `N ERROR GOTO 100` | 4 | blind |
| `logicops` c44 | **direct** | `PRINT "[";(0 AND 0) IMP 0;"]"` | `T "[";(0 AND 0) IMP 0;"]"` | 4 | blind |
| `float` | **direct** | `print "[";fix(-2.5#);"]"` | `t "[";fix(-2.5#);"]"` | 4 | blind |
| `math` | **direct** | `print "[";2--3.5;"]"` | `t "[";2--3.5;"]"` | 4 | blind |
| `str-domain` | **direct** | `PRINT "[";LEN(RIGHT$(A$,256));"]"` | `T "[";LEN(...)` | 4 | blind |
| `time` | **direct** | `30 PRINTCHR$(67);CHR$(35):END` | `);CHR$(35):END` | **15** | blind |

🎯 **Six standing corpus suites were mis-delivering a case each, every run, and
were green.** `logicops`, `float`, `math`, `str-domain`, `time` and `error-trap`
are all `direct`-mode, so nothing in the tree could see it. They were green
because `run_differential` self-heals any case where the two machines disagree —
so the *outcome* was usually rescued, at the price of a boot-per-case pair
nobody could attribute, and with no protection at all for a mangle that happens
to leave a plausible value both sides agree on (`graphics`' `wr_v255fr` is what
that looks like when you can see it, D-DELIVER §7.3).

## 8. Knives

Every cut was verified to have *cut* before its verdict was read, and every knife
that silences the guard is paired with a control proving the fault **reproduced
in that same run** [[knife-runner-false-negatives]]. The module was restored and
`cmp`-checked byte-identical after each.

| knife | cut (verified) | predicted | measured |
|---|---|---|---|
| **K1** | `ZEROBAS_ECHOGUARD=off` | guard silent; the fault still there | **0 fires**, and the stored oracle still flagged case 22 **in that run**. Direct mode: `0` from *both* oracles — the pre-slice state, exactly |
| **K2** | `echo_verdicts` gutted to `return []`, emission and call site both verified still present | same silence — coverage is not efficacy | **0 fires**, stored oracle still flagged case 22 in that run [[coverage-gate-cannot-see-a-gutted-guard]] |
| **K3** | the re-run replaced by `pass` | announced, not repaired | `MIS-ECHOED case 22` still on stderr exactly once, no re-run |
| **K4** | positive control, armed, **direct** mode | fires exactly once, case 22, naming the line | `[22]`, `'10 ON ERROR GOTO 40'` — and the stored oracle saw **nothing**, because direct mode emits no chain |
| **K5** | zero-RED: the reference, phases O and Q2, both modes | zero | **0, 0, 0, 0** — with the zb half of Q2 firing `[12, 22]` as its control |
| **K6** | the margin hard-coded to the reference's `2` | the zerobas side floods with MANGLED | 🔴 **PREDICTION WRONG — see below** |

### 🔴 K6 did not redden, and that is the finding

Hard-coding the margin produces **zero** false fires on zerobas. It moves the
verdicts instead:

```
armed   OK 169   BLIND/rewrote 68   BLIND/mode 7   MANGLED 1
cut     OK 167   BLIND/rewrote 71   BLIND/mode 7   MANGLED 0
```

Two reasons, both worth carrying:

* A margin too large by one only eats the **prompt**, not the payload — zerobas
  echoes as `ZB10 ON ERROR GOTO 40`, so slicing from column 2 still leaves
  `B10 ON ERROR GOTO 40`, and the typed text is still a substring. The margin is
  load-bearing **only for a WRAPPED echo**, where it decides where the join is.
* Where it does bite, the suffix requirement makes it fail **safe**: the
  reconstructed stream loses the wrapped tail, no suffix matches, and the slot
  goes `BLIND/noecho`. **A geometry error degrades this guard to blindness, not
  to noise** — which is the failure mode nothing downstream can notice
  [[knife-that-reddens-nothing-is-the-finding]].

So the geometry has **no emulator knife**. Its instrument is the host unit test,
and that one does catch it — under the same cut,
[`tests/test_echo_oracle.py`](../tests/test_echo_oracle.py) exits 1 on four rows:

```
FAIL  head-swallowed line is MANGLED                 ['BLIND/rewrote', 'BLIND/rewrote']
FAIL  intact line is OK on zerobas margin 1/width 39 ['BLIND/rewrote', 'BLIND/rewrote']
FAIL  wrapped 38-char echo is OK on zerobas          ['BLIND/rewrote', 'BLIND/rewrote']
FAIL  mis_echoed names (case, slot, typed)           []
```

That is the strongest argument for the unit test existing: the gates cannot score
this, and would have stayed green while the guard quietly stopped working.

## 9. Open

* ~~**The floor of the race**~~ · ~~**the mechanism behind §5**~~ — 🎯 **BOTH
  CLOSED 2026-08-04 BY D-LATCH**
  ([`docs/latch-trigger-characterization.md`](latch-trigger-characterization.md)).
  The trigger is one instruction boundary, `$1197` in C-BIOS `chget`; the
  mechanism is a **latched `HL`**, not a saved-and-restored pointer — §5's
  hypothesis was inverted. ⚠️ And §5's last table row, `CLS:REM123456789012345678`
  → *"the batch delivered clean"*, is a **partial reading**: it hits the trigger
  too, but the swallow (26) exceeds the payload (20), so the line arrives after
  garbage and only the *stored* oracle sees it — a spurious line `0`. That row
  was read from `mis_echoed` alone.
* **Probes with their own `build_tcl`** (every `probes/disk/*`,
  `basic_probe_printusing.py`) bypass `omsx_repl._tcl` and are uncovered.
* **A trailing blank** is still not distinguishable by a substring search
  [[decblank-echo-guard-blind]]; the per-probe guards remain the instrument.
* **A mangle that swallows a line entire** leaves no suffix and is invisible.
