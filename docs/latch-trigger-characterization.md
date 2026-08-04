# Delivery-race trigger characterisation — every reading, D-LATCH

Companion to [`docs/spec-probe-latch.md`](spec-probe-latch.md). Everything below
was measured on `121b05b` (tree clean, `make -q build/zerobas-main-eu.rom` exit 0,
`make repack-machine` run first). Reference `Philips_VG_8020`, subject
`C-BIOS_MSX1_EU_REPACK_DISK`.

---

## 1. The instrument, and why it cannot disturb what it measures

`__key` is the only place the harness touches `KEYBUF`/`GETPNT`/`PUTPNT`. An
openMSX `after time` callback is atomic with respect to the emulated CPU
(D-DELIVER §8.1), so at the **top** of `__key`, before a byte is written, the
machine is in exactly the state the injection is about to interrupt.

Reading `reg pc`, `reg hl`, `reg de`, `[debug read memory GETPNT]`, `PUTPNT` and
the opcode at PC there costs **zero emulated time**, so it cannot move the
alignment it exists to measure [[apparatus-is-part-of-the-measurement]]. The
instrument is a string-replacement into the generated Tcl, applied at the top of
`__key`; the rest of the timeline is byte-identical to an ordinary run, which is
the property the whole experiment rests on.

## 2. 🔴 The mangled slot is the only slot in 245 whose PC is `$1197`

Phase O (`SPRITE_BEHAV`, reset `("NEW","CLS")`), the batch D-ECHO used. 245
injection slots, one mangle — case 22, slot 156, `10 ON ERROR GOTO 40` echoed as
`N ERROR GOTO 40`.

PC at injection, all 245 slots:

| PC | slots |
|---|---|
| `$11A0` | **230** |
| `$19A3`, `$199C` | 2 each |
| `$18ED`, `$18EE`, `$18EF`, `$1963`, `$1997`, `$199D`, `$19A2`, `$119F`, `$1194` | 1 each |
| **`$1197`** | **1 — slot 156, the mangled one** |

```
slot   PC     opcode  HL      DE      GETPNT  PUTPNT
154   $11A0   $18    $FBF4   $FBF4   $FBF4   $FBF4
155   $11A0   $18    $FBF4   $FBF4   $FBF4   $FBF4
156   $1197   $ED    $FBF4   $FBF4   $FBF4   $FBF4     <-- mangled
157   $11A0   $18    $FC04   $FC04   $FC04   $FC04
```

`$FBF4` is `KEYBUF + 4`, and the preceding injection was `CLS` + CR — 4 bytes.

## 3. The address map

`$009F` (`CHGET`, published MSX BIOS jump table) holds `C3 8F 11`. Twenty-four
bytes read from `$118F` on the subject machine:

```
cdc2fde5d52afaf3ed5bf8f3e72004fb7618f27ef5237dfe
```

which decodes, one instruction for one, onto the `chget` routine in C-BIOS's own
**source** — BSD-2 source this repo already carries patches against
(`cbios-repack/`, pinned `v0.29-3-gb5ad9cb`). No reference ROM was disassembled
[[no-reference-rom-disasm]].

```
$118F  chget        CD C2 FD      call H_CHGE
$1192               E5            push hl
$1193               D5            push de
$1194  chget_wait   2A FA F3      ld hl,(GETPNT)
$1197               ED 5B F8 F3   ld de,(PUTPNT)     <-- THE TRIGGER
$119B               E7            rst $20            (DCOMPR: HL vs DE)
$119C               20 04         jr nz,chget_char
$119E               FB            ei
$119F               76            halt
$11A0               18 F2         jr chget_wait
$11A2  chget_char   7E            ld a,(hl)
```

`$11A0` — the instruction *after* `halt` — is where openMSX parks PC while the
CPU is halted, which is why 230 of 245 slots read it. The CPU is idle in
`chget`'s wait loop for essentially the whole `step`.

## 4. The predictions, scored

Phase O above is the **discovery** run and is not counted as a prediction.
Everything in this table was written into
[`docs/spec-probe-latch.md`](spec-probe-latch.md) §4.1 before it was run.

| # | run | predicted | measured |
|---|---|---|---|
| **P1** | phase Q2, zb | exactly 2 slots at `$1197`, being cases 12 and 22 | ✅ slots **88** and **156**; `mis_echoed` = case 12 slot 88, case 22 slot 156; `mis_delivered` = 12 lost line 30, 22 lost line 10 |
| **P2** | phase O, reset `CLS:CLS` | 1 slot, `HL = $FBF8`, swallow 8 | ✅ slot 156, `$FBF8`, echo `ZBROR GOTO 40` |
| **P3** | phase O, reset `CLS:REM123456` | 1 slot, `HL = $FBFE`, swallow 14 | ✅ slot 156, `$FBFE`, echo `ZBTO 40` |
| **P4** | phase O, reset `CLS:REM123456789012345678` (D-ECHO: "delivered clean") | **zero** slots at `$1197` | 🔴 **WRONG — see §4.1** |
| **P5** | phase O + Q2, reference | zero mangles | ✅ 0 and 0, 652 slots |
| **P6** | every slot | drained; at a fatal slot `HL == GETPNT`, swallow `== GETPNT - KEYBUF` | ✅ **2039/2039** drained; `HL == GETPNT` at **6/6** fatal slots |

P1's slot 88 is the sharpest single number in the slice. The swallowed line is
`30 SCREEN0:PRINT"ZK";A:END`; its predecessor is `20 SCREEN0:A=BASE(10)`, which
is 21 characters and **22** with its CR — and `HL` read `$FC06`, which is
`KEYBUF + 22`.

**Across all seven instrumented batches: 2039 slots, 6 at `$1197`, 6
mis-deliveries, and not one mis-delivery at any other slot.** The biconditional
holds in both directions.

### 4.1 🔴 P4 was wrong, and it corrects a reading in D-ECHO

The 26-byte predecessor **does** hit the trigger — slot 156, `HL = $FC0A`
(`KEYBUF + 26`). What it does not do is produce a *visible* mangle:

| oracle | verdict |
|---|---|
| echo | clean |
| **stored** | 🔴 case 22 stored **`0, 10, 20, 30, 40`** — a spurious line **0** |

The payload `10 ON ERROR GOTO 40` is 20 bytes with its CR, and 26 > 20. So the
read starts *past* the payload, consumes whatever the 40-byte circular buffer
still held from an earlier, longer injection, **wraps**, and then delivers the
real line intact after that garbage. The line the probe wanted arrives; a line
`0` arrives with it.

D-ECHO's §5 table records this row as *"(the batch delivered clean)"*. That
reading was taken from the echo oracle alone — the reproduction snippet in that
slice prints `mis_echoed` and nothing else — and the echo oracle is structurally
unable to see this case, because the typed text **is** on the screen. The stored
oracle sees it immediately. Two oracles, and the one that was asked was the blind
one [[readout-blind-to-its-own-subject]].

It is also the cleanest demonstration that the trigger is *not* the same thing as
the damage. Every fatal slot swallows `N`; whether that is visible, invisible, or
visible only to the other oracle depends on how `N` compares with the payload.

## 5. The mechanism

At `$1197` the CPU holds, in `HL`, the `GETPNT` it read one instruction earlier.
The buffer was drained, so that value is where the predecessor left it. The
injection then writes the payload at `KEYBUF`, sets `GETPNT = KEYBUF` and
`PUTPNT = KEYBUF + n`. The CPU resumes:

* `ld de,(PUTPNT)` → the **new** `PUTPNT`;
* `rst $20` → compares the **stale** `HL` against it → unequal → "a key waits";
* `ld a,(hl)` → reads `KEYBUF + N`.

Every neighbouring boundary is safe for a reason, and §6 measures each of them:

| PC | why harmless |
|---|---|
| `$1194` | `HL` is loaded *after* the write |
| `$119B`, `$119C`, `$119E` | `HL` and `DE` are both stale and **equal** → Z → `halt` → `jr` → both reloaded |
| `$119F`, `$11A0` | halted / re-entering the loop → both reloaded |

🔴 **The hypothesis on file was inverted.** D-ECHO §5 and `TODO.md` proposed *"the
ROM saves a `GETPNT` past the previous line and later restores it"*. C-BIOS
writes `GETPNT` in exactly three places — power-on init, `chget`'s post-read
increment, and nowhere else (`kilbuf` writes `PUTPNT`). **Nothing is saved and
nothing is restored.** What survives the injection is a *register copy*, one
instruction ahead of the compare that would have invalidated it. The hypothesis
predicted the right arithmetic from the wrong object, which is the same shape
D-DELIVER §8.2 recorded: a right conclusion from a wrong model still has to be
re-derived, because the fix each one implies is different. A "restore" story
leads you to look for a save site that does not exist; the latch story tells you
exactly which write to stop making.

## 6. Forced reproduction — the knives that turn correlation into cause

One observation in 245 slots is a correlation. A CPU breakpoint at a chosen
address makes the callback land on that boundary **by construction**:
`debug set_bp <addr> {} { fire }`, where `fire` performs the injection and
removes itself. Target line `10 PRINT"ABCDEFG"` (17 characters); the predecessor
is the previous injected line, whose length is the knob.

### K1 — forced at `$1197`

| predecessor | length + CR | HL at the hit | echoed | stored chain |
|---|---|---|---|---|
| `CLS` | 4 | `$FBF4` | `ZBRINT"ABCDEFG"` | `''` (rejected) |
| `CLS:CLS` | 8 | `$FBF8` | `ZB"ABCDEFG"` | `''` |
| `CLS:REM1` | 9 | `$FBF9` | `ZBABCDEFG"` | `''` |
| `CLS:REM123456` | 14 | `$FBFE` | `ZBFG"` | `''` |

`10 PRINT"ABCDEFG"` with 4, 8, 9 and 14 characters removed from the front is
exactly `RINT"ABCDEFG"`, `"ABCDEFG"`, `ABCDEFG"`, `FG"`. **Four for four**, and
deterministic — the race that fires once in 245 slots now fires every time.

### K2–K4 — the neighbouring boundaries, identical in every other respect

| knife | breakpoint | predecessor | stored chain |
|---|---|---|---|
| **K2** | `$1194` `ld hl,(GETPNT)` | `CLS:REM123456` | **`10`** — delivered |
| **K3** | `$119B` `rst $20` | `CLS:REM123456` | **`10`** — delivered |
| **K4** | `$11A0` `jr chget_wait` | `CLS:REM123456` | **`10`** — delivered |

Same machine, same batch shape, same predecessor, same payload, same injector.
**One instruction apart, and the outcome inverts.** That is the causal claim.

## 7. The fix, and its knives

`key_proc` writes the payload at the **current `GETPNT`**, wrapping at
`KEYBUF + 40`, and moves only `PUTPNT`. A latched `HL` then points at the first
byte of the new payload, because C-BIOS only holds a stale `GETPNT` in `HL`
while it still equals its in-memory value.

| knife | cut (verified) | predicted | measured |
|---|---|---|---|
| **K5** | the fix, forced at `$1197`, four predecessors | zero mangles | **4/4 delivered** (`chain = 10`), `HL` walking the buffer `$FBF8 → $FBFC → $FBFD → $FC02` as the append semantics require |
| **K5 ctrl** | the OLD injector, same session, same boundary | mangles | **`ZBFG"`, chain `''`** — the fault reproduced in the same run [[knife-runner-false-negatives]] |
| **K6** | the plausible half-fix: write at `KEYBUF`, leave `GETPNT` alone | still mangles — **both** halves are load-bearing | **`ZBFG"`, chain `''`** |
| **K7** | the fix on the three safe boundaries | still delivered — the fix must not break what was never broken | **3/3 delivered** |

K6 is the one worth keeping. "Do not write `GETPNT`" *sounds* like the whole
fix; it is half of it, and the half that does nothing on its own. Writing at
`KEYBUF` while the CPU is looking at `KEYBUF + 14` loses the same 14 bytes.

### 7.1 Post-fix, on the batches that used to mangle

| batch | machine | before | after |
|---|---|---|---|
| phase O, reset `CLS` | zb | 1 mis-delivery | **0** |
| phase Q2, reset `CLS` | zb | 2 | **0** |
| phase O, reset `CLS:CLS` | zb | 1 | **0** |
| phase O, reset `CLS:REM123456` | zb | 1 | **0** |
| phase O, reset `CLS:REM…678` | zb | 1 (stored oracle only, §4.1) | **0** |
| phase O, phase Q2 | ref | 0, 0 | **0, 0** (zero-RED, unmoved) |

Every capture present, every case count unchanged.

## 8. The gate, and why it had to exist

Fixing the race silences the only positive control the two delivery oracles ever
had. D-ECHO §3.5 says so outright: a batch of identical cases does not reproduce
the race, so cross-oracle disagreement was the standing check — and it fires
exactly when the race does. Removing the fault without replacing that control is
[[gate-can-be-green-while-measuring-nothing]] with the serial numbers filed off.

`make latch-check` ([`probes/lib/latch_check.py`](../probes/lib/latch_check.py))
therefore does not wait for the race, it forces it — nine boots, ~40 s:

```
latch-check: chget $118F  chget_wait $1194  trigger $1197
  PASS  A  old injector, forced, predecessor  4 B  -> MANGLED (HL $FBF4)
  PASS  A  old injector, forced, predecessor  8 B  -> MANGLED (HL $FBF8)
  PASS  A  old injector, forced, predecessor 14 B  -> MANGLED (HL $FBFE)
  PASS  B  key_proc,     forced, predecessor  4 B  -> DELIVERED
  PASS  B  key_proc,     forced, predecessor  8 B  -> DELIVERED
  PASS  B  key_proc,     forced, predecessor 14 B  -> DELIVERED
  PASS  C  key_proc,     forced at $1194 (ld hl,(GETPNT))   -> DELIVERED
  PASS  C  key_proc,     forced at $119B (rst $20)   -> DELIVERED
  PASS  C  key_proc,     forced at $11A0 (jr chget_wait)   -> DELIVERED
latch-check: 9/9 rows
```

Row **A** is the anti-vacuity clause: it runs the frozen pre-D-LATCH injector and
requires it to **still fail**. If the experiment ever stops reproducing — a
different C-BIOS, a different openMSX scheduling model — row A goes green and the
gate goes **red**, instead of quietly certifying nothing. Row **B** imports
`key_proc` from `omsx_repl` rather than copying it, so the thing scored cannot
drift from the thing shipped [[coverage-gate-cannot-see-a-gutted-guard]].

### 8.1 Knives on the gate itself

| knife | cut | predicted | measured |
|---|---|---|---|
| **K8** | `key_proc` monkeypatched back to the old body | the three **B** rows red, exit 1 | **6/9, exit 1** — and the three **C** rows stayed green, because those boundaries were never fatal for *either* injector |
| **K9** | row A's frozen body replaced with `key_proc` | the three **A** rows red, exit 1 — the control must notice it has no subject | **6/9, exit 1** |
| **K10** | the `chget_wait` byte signature changed to a value that cannot match | **refuse to judge**, non-zero | `latch-check: CANNOT JUDGE -- chget_wait (0x1194) reads '2afaf3ed5bf8f3', not the 'deadbeef…' this gate was written against` [[guard-that-cannot-judge-must-say-so]] |

K9 is the K2-shaped knife: emission and call site both intact, judgement intact,
and only the **subject** removed. It is the failure mode a coverage check cannot
see, and the reason row A is scored rather than merely run.

## 8.2 One corpus row that did not reproduce

`lof-acceptance` exited 2 in the corpus run on a single `ORACLE DRIFT` row —
`wm_app_put`, recorded oracle 61, live reading `None` — with 0 unfiled
divergences and 0 mangled. Attribution, not assumption:

| run | injector | result |
|---|---|---|
| corpus | D-LATCH | 1 oracle drift, exit 2 |
| A1 | D-LATCH | **0 drift, exit 0** |
| A2 | D-LATCH | **0 drift, exit 0** |
| B | `HEAD`'s (pre-D-LATCH), restored and `cmp`-checked back | **0 drift, exit 0** |

Three subsequent runs clean, two of them on the changed tree. So it is a flake
and it is **not** attributed to the fix — and equally it is not written off,
because run B proves nothing on its own: an experiment where the subject never
occurred reads exactly like an exoneration [[knife-runner-false-negatives]]. What
carries the attribution is A1 and A2: the changed tree, twice, clean.

## 9. Open

* **The second window is not closed** (spec §2.5). A CPU inside `chget_char`
  holds an `HL` it is about to write back to `GETPNT`; that needs a non-drained
  buffer, measured absent before **2039/2039** injections here and 490/490 in
  D-DELIVER, but it is a hole and both oracles stay armed because of it.
* **The reference is an outcome control only.** Locating the same boundary in a
  Philips VG-8020 would need a disassembly this project does not do
  [[no-reference-rom-disasm]]. That it mis-delivers zero with either injector is
  all this slice claims about it.
* **One probe still composes its own injector.** Six did: the five trap probes
  each held a **byte-identical** copy of the old `__key`, and each now calls
  `key_proc()` — their five gates were re-run green. `probes/disk/disk_probe_getput.py`
  keeps its copy on purpose: no Makefile target runs it, so the edit could not
  have been scored. `basic_probe_printusing.py` turned out **not** to be in this
  class at all — it drives openMSX `type`, not KEYBUF. D-ECHO §6 filed this as a
  coverage limit; for the copies it is a *correctness* limit.
* **`$1197` is not a stable number.** It is derived per run by `latch-check` and
  vouched for by a byte signature; a C-BIOS bump moves it, and the gate says so
  rather than scoring the wrong address.
