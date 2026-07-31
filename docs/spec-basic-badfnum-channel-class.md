# D-BADFNUM — a REJECTED channel number must answer the reference's error class

Status: ✅ **LANDED 2026-07-31.** Net **−14 B**: page 1 49 → **63 B** free, low
region **unchanged at 23 B**. Gate: `make badfnum-acceptance`, **93 cases, 0
unfiled divergence, 0 oracle drift, 0 mangled, 0 without an oracle lock**.
`diskbasic_probe_lof.py`'s `KNOWN_DIVERGE` is now **EMPTY**.
Filed: TODO.md ~2942, 2026-07-31, by D-NOTOPEN (spec §2b, §7.2).
Related: [`docs/spec-basic-chan-notopen-err59.md`](spec-basic-chan-notopen-err59.md),
[`docs/spec-basic-gpfi-notopen-err59.md`](spec-basic-gpfi-notopen-err59.md).
Memories: `gpfi-wrongmode-grid-slice`, `notopen-chan-err59-slice`, `appmiss-slice`,
`apparatus-is-part-of-the-measurement`.

---

## 1. What was filed, and why it was only a corner

TODO.md files **three rows**:

| typed | reference | zerobas |
|---|---|---|
| `PRINT #2,"X"` | ERR 52 `bad file number` | `load error` |
| `INPUT #2,A$` | ERR 52 | `load error` |
| `PRINT #0,"X"` | ERR 59 `file not open` | `load error` |

and warns that it does not generalise, because channel `0` and channel `2` earn
**different** reference codes. That warning is right and it is the smaller half.

A static read of `basic/` says `fch_valid` has **NINE call sites routing their
reject to SIX different places** — so the filed rows walk 2 of 9 sites and 1 of 6
dispositions:

| site | verb | today's disposition | class printed |
|---|---|---|---|
| [`print.asm:42`](../basic/print.asm:42) | `PRINT#`, `PRINT# USING` | `load_error` | `load error` |
| [`files.asm:695`](../basic/files.asm:695) | `INPUT#`, `LINE INPUT#` | `load_error` | `load error` |
| [`files.asm:832`](../basic/files.asm:832) | `CLOSE#` | `dc_done` | **nothing at all** |
| [`files.asm:1054`](../basic/files.asm:1054) | `OPEN … AS #n` | `oo_fail_bfn` | ERR 52 |
| [`field.asm:153`](../basic/field.asm:153) | `FIELD` | `stmt_error` | ERR 2 |
| [`field.asm:513`](../basic/field.asm:513) | `GET`, `PUT` | `stmt_error` | ERR 2 |
| [`strvar.asm:178`](../basic/strvar.asm:178) | `INPUT$(n,#f)` | `str_eval_no` | ERR 2 |
| [`expr.asm:985`](../basic/expr.asm:985) | `EOF()` | `ev_f_err` | **nothing at all** |
| [`expr.asm:1007`](../basic/expr.asm:1007) | `LOF()` | `ev_f_err` | **nothing at all** |

## 2. The DENOMINATOR — MEASURED, swept, not sampled

`fch_valid`'s reject domain is exactly two inputs (`0` and `> MAXF`), so the core
grid is **12 channel-taking verbs × 5 channel classes = 60 cells**, every one
typed on both machines. Scratch battery: `badfnum_battery.py` (session
scratchpad), apparatus inherited wholesale from
[`probes/disk/diskbasic_probe_lof.py`](../probes/disk/diskbasic_probe_lof.py) —
measured screen geometry, the 14.0 s cadence, and the echo guard. **0 mangled
rows across all 72 cases; `ctl_syntax` green on both sides.**

🔴 **BATTERY 1 SAMPLED THE LAST THREE CLASSES ON THREE VERBS AND READ A PERFECTLY
UNIFORM RULE. THE SWEEP REFUTED IT.** `prw`/`get`/`lof` all answer `BFN` at `#16`
and `IFC` at `#256`/`#-1`, which reads as settled — but the one verb already known
to follow a different rule at `#0` (`OPEN`, which answers **52** where the other
eleven answer **59**) was not among the three sampled, and it is the one that
breaks the pattern: `OPEN … AS #256` is **IFC** on the reference and **BFN** on
zerobas. Sampling would have shipped that cell wrong and called the grid closed.
At 14 s for 37 boots there was never a reason to sample (memory:
`gpfi-wrongmode-grid-slice`).

### 2a. THE REFERENCE RULE (CF-3300), complete

| channel | reference | exceptions |
|---|---|---|
| `#256`, `#-1` (high byte set / negative) | **ERR 5** `Illegal function call` | **none — all 12 verbs, `OPEN` included** |
| `#0` | **ERR 59** `File not OPEN` | `CLOSE #0` = silent no-op; `OPEN … AS #0` = **ERR 52** |
| `1 … MAXF` | proceeds to the mode checks | — |
| `#2`, `#16` (> `MAXF`) | **ERR 52** `Bad file number` | **none — all 12 verbs, `CLOSE` included** |

`ctl_mf2_ch2` is the row that pins the boundary to `MAXF` rather than to the
constant 2: `MAXFILES=2 : PRINT #2,"X"` answers **59** (in range, merely not open),
not 52 — on both machines. Without it "channel 2 is bad" and "channel 2 is beyond
the ceiling" are the same reading.

### 2b. THE MEASURED GRID — 63 of 72 rows diverge

`FNO` = `file not open` (59) · `BFN` = `bad file number` (52) · `IFC` = `illegal
function call` (5) · `SYNTAX` = ERR 2 · `LOADERR` = zerobas's own `load error` ·
**`0` / `7` = NO ERROR WAS RAISED AT ALL** (`7` is the `:PRINT 7` sentinel, so
"no error" is a positive reading and not an absent one — memory: `appmiss-slice`).

| verb | `#0` ref / zb | `#2` ref / zb | `#16` ref / zb | `#256` ref / zb | `#-1` ref / zb |
|---|---|---|---|---|---|
| `PRINT #n,"X"` | FNO / **LOADERR** | BFN / **LOADERR** | BFN / **LOADERR** | IFC / **LOADERR** | IFC / **LOADERR** |
| `PRINT #n,USING` | FNO / **LOADERR** | BFN / **LOADERR** | BFN / **LOADERR** | IFC / **LOADERR** | IFC / **LOADERR** |
| `INPUT #n,A$` | FNO / **LOADERR** | BFN / **LOADERR** | BFN / **LOADERR** | IFC / **LOADERR** | IFC / **LOADERR** |
| `LINE INPUT #n,A$` | FNO / **LOADERR** | BFN / **LOADERR** | BFN / **LOADERR** | IFC / **LOADERR** | IFC / **LOADERR** |
| `CLOSE #n` | 7 / 7 ✅ | BFN / **7** | BFN / **7** | IFC / **7** | IFC / **7** |
| `OPEN … AS #n` | BFN / BFN ✅ | BFN / BFN ✅ | BFN / BFN ✅ | IFC / **BFN** | IFC / **BFN** |
| `FIELD #n,10 AS A$` | FNO / **SYNTAX** | BFN / **SYNTAX** | BFN / **SYNTAX** | IFC / **SYNTAX** | IFC / **SYNTAX** |
| `GET #n,1` | FNO / **SYNTAX** | BFN / **SYNTAX** | BFN / **SYNTAX** | IFC / **SYNTAX** | IFC / **SYNTAX** |
| `PUT #n,1` | FNO / **SYNTAX** | BFN / **SYNTAX** | BFN / **SYNTAX** | IFC / **SYNTAX** | IFC / **SYNTAX** |
| `A$=INPUT$(3,#n)` | FNO / **SYNTAX** | BFN / **SYNTAX** | BFN / **SYNTAX** | IFC / **SYNTAX** | IFC / **SYNTAX** |
| `PRINT EOF(n)` | FNO / **0** | BFN / **0** | BFN / **0** | IFC / **0** | IFC / **0** |
| `PRINT LOF(n)` | FNO / **0** | BFN / **0** | BFN / **0** | IFC / **0** | IFC / **0** |

🔴 **`EOF`/`LOF` RAISE NOTHING AND RETURN A NUMBER.** `PRINT LOF(0)` prints `0` —
not an error, an *answer*, and a plausible-looking one. Screen, verbatim:

```
ZBPRINT LOF(0)
 0
ZB
```

`ev_f_err` sets `ERRMARK` and returns `DE = 0`, and on this path nothing reads
`ERRMARK` — so a program asking the size of a channel it never opened is handed a
silently wrong number. That is the same shape as D-NOTOPEN2's silently-accepted
`FIELD`, one layer earlier, and it is the severe half of this item. **It is not in
the filed rows.**

🔴 **`CLOSE #2` / `#16` / `#256` / `#-1` SILENTLY NO-OP** where the reference
raises. `dc_done` is documented as a "lenient no-op"; the reference is lenient
only about channel **0**.

### 2c. TRAPPABILITY — the semantics half

`10 ON ERROR GOTO 100 / 20 <stmt> / 100 PRINT ERR / RUN`. The handler prints the
code, so `0` reads as **no error was raised at all** and "trapped", "not trapped"
and "nothing happened" stay three distinct readings.

| row | subject | reference | zerobas today |
|---|---|---|---|
| `trap_prw0` | `PRINT #0,"X"` | **59** | `load error`, handler did NOT run |
| `trap_prw2` | `PRINT #2,"X"` | **52** | `load error`, handler did NOT run |
| `trap_prw256` | `PRINT #256,"X"` | **5** | `load error`, handler did NOT run |
| `trap_get2` | `GET #2,1` | **52** | **2** (traps, wrong code) |
| `trap_clo2` | `CLOSE #2` | **52** | **0** — nothing raised |
| `trap_lof0` | `A=LOF(0)` | **59** | **0** — nothing raised |
| `trap_lof2` | `A=LOF(2)` | **52** | **0** — nothing raised |
| `trap_lof1` | `A=LOF(1)` — **GREEN CONTROL** | **59** | **59** ✅ |

`trap_lof1` is green today (`fch_mode_class` raises it) and is what makes the
three red `trap_lof*` rows attributable: without it, `trap_lof0` reading `0` could
not tell "nothing was raised" from "this probe cannot read a trap".

### 2d. The EDGE cells the change touches that nothing had typed

A fix must not move a cell whose reference value is unknown, so these were
measured before the design was fixed, not after:

| typed | reference | zerobas | verdict |
|---|---|---|---|
| `PRINT #1.7,"X"` | FNO | FNO | ✅ agrees — float channel truncates to 1 |
| `PRINT LOF(1.7)` | FNO | FNO | ✅ agrees |
| `PRINT #99999*99999,"X"` | `Overflow` | `overflow` | ✅ agrees — `eval_chan` raises **before** the channel check |
| `PRINT #255,"X"` | BFN | LOADERR | ❌ same defect as `#16` |
| `MAXFILES=2 : CLOSE #2` | 7 | 7 | ✅ agrees |
| `MAXFILES=2 : PRINT LOF(2)` | FNO | FNO | ✅ agrees |
| `PRINT LOF(A$)` | `Type mismatch` | `type mismatch` | ✅ agrees |
| **`PRINT #A$,"X"`** | **`Type mismatch`** | `load error` | ❌ §6 |
| **`INPUT #A$,B$`** | **`Type mismatch`** | `load error` | ❌ §6 |

⚠️ The four `Type mismatch` / `Overflow` rows first read as `None` — the battery's
class table had no entry for either, and **`None` also means "nothing went
wrong"**. They were resolved by reading the screens, not by trusting the sentinel;
the permanent gate (§5) carries both classes so the row can never be silently
ambiguous again. Same trap as `appmiss-slice`, caught by looking.

## 3. The change — ONE shared checker, and it is a NET SAVING

The reference rule is uniform enough to be *one routine*, with two extra entry
points for the only two verbs that treat channel `0` specially. New in
[`basic/files.asm`](../basic/files.asm), replacing `fch_valid` in place:

```
; fch_check_d — D != 0 (>255 or negative) -> ERR 5. Else A = E and Z <=> ch 0.
fch_check_d:
                ld      a,d
                or      a
                jr      nz,fchk_ifc
                ld      a,e
                or      a
                ret
fchk_ifc:
                ld      a,5                 ; illegal function call
                jp      raise_error
; fch_check — the full measured rule: D!=0 -> 5, 0 -> 59, > MAXF -> 52.
fch_check:
                call    fch_check_d
                jp      z,err_notopen_raise
; fch_check_nz — channel 0 already disposed of by the caller: CLOSE no-ops on it,
; OPEN answers 52. Everything else reaches here through fch_check above.
fch_check_nz:
                ld      b,a
                ld      a,(MAXF)
                cp      b                   ; CF set iff ch > MAXF
                jp      c,oo_fail_bfn       ; -> ERR 52
                ld      a,b
                ret
```

Seven of the nine sites collapse to a single `call fch_check`. `CLOSE` and `OPEN`
keep one extra line each for their channel-`0` exception.

### Byte accounting — measured from the instruction encodings, per site

| site | today | after | Δ |
|---|---|---|---|
| `print.asm` `PRINT#` | `ld a,e`+`call`+`jp nc` = 7 | `call fch_check` = 3 | **−4** |
| `files.asm` `INPUT#`/`LINE INPUT#` | 7 | 3 | **−4** |
| `files.asm` `CLOSE#` | `ld a,e`+`call`+`jr nc` = 6 | `call fch_check_d`+`jr z,dc_done`+`call fch_check_nz` = 8 | **+2** |
| `files.asm` `OPEN` | `ld a,d`+`or a`+`jp nz`+`ld a,e`+`call`+`jp nc`+`ret` = 13 | `call fch_check_d`+`jp z,oo_fail_bfn`+`jp fch_check_nz` = 9 | **−4** |
| `field.asm` `FIELD` | 12 | 3 | **−9** |
| `field.asm` `GET`/`PUT` | 12 | 3 | **−9** |
| `strvar.asm` `INPUT$` | 7 | 3 | **−4** |
| `expr.asm` `EOF` | 7 | 3 | **−4** |
| `expr.asm` `LOF` | 7 | 3 | **−4** |
| | **78** | **38** | **−40** |

* new routine (7 + 5 + 6 + 10) **+28**
* `fch_valid` has **no callers left** and is DELETED **−9**
  (the hard dead-code gate would fail the build otherwise — memory: `deadcode-gate`)
* **+7** — the `TMISMATCH` test at the head of `fch_check_d`, which §5.1 below
  explains was NOT in this spec when it was signed off and had to be added

**NET −14 B, entirely page 1. The low region is not touched.** No funding carve was
needed; this slice *pays into* the wall rather than out of it.
**Predicted −21 B → page 1 70 B; MEASURED 70 B exactly** on the first clean build,
before §5.1's +7 took it to the shipped **63 B**. Low **23 B**, unchanged, as
predicted. The prediction landing to the byte is what says the accounting above is
understood rather than merely plausible.

## 5.1 🔴 WHAT THE SPEC GOT WRONG — a control row went red, one axis over

The signed-off design shipped a **regression**, and the row that caught it was one
this spec had listed in §2d as a ✅ **agreeing** cell:

```
edge_tm_lof   PRINT LOF(A$)   ref TMIS   zb FNO   DIVERGE (UNFILED)
```

`PRINT LOF(A$)` was `type mismatch` on **both** machines before this slice. A type
mismatch **hard-zeroes the channel expression to 0** — so the moment `fch_check`
started answering ERR 59 to channel 0, it answered ERR 59 to a string channel too,
and got there before the evaluator's own type check ever ran.

🔴 **I SAMPLED THE TYPE-MISMATCH AXIS ON 3 OF 12 VERBS — INSIDE THE SPEC WHOSE §2
IS AN ARGUMENT AGAINST SAMPLING.** §2d typed `PRINT #A$`, `INPUT #A$` and
`LOF(A$)` as three "edge cells" rather than as what they are: a **sixth channel
class**, with twelve rows like every other class. Sweeping it found the reference
is uniform — `Type mismatch`, **all twelve verbs, no exceptions** — and that
zerobas diverged on **eight** of them, only two of which were regressions
(`EOF`/`LOF`); the other six had been wrong all along and merely changed shape.

The fix is 7 B at the head of `fch_check_d`, ahead of everything else:

```
                ld      a,(TMISMATCH)
                or      a
                jp      nz,type_mismatch_error
```

⚠️ **§6's 0-byte `eval_chan` change does NOT cover this**, and that is the point of
knife **K5**: only four of the twelve verbs reach `eval_chan` at all. The other
eight call plain `eval` and had no type check anywhere on their path.

**The lesson is not "sweep the grid" — the spec already said that. It is that the
axis you are sweeping deliberately is not the only axis, and a cell listed as a
CONTROL BECAUSE IT AGREES is exactly what finds the one you missed.** `edge_tm_lof`
was in the gate only because §2d wanted the untouched cells pinned. It went red on
the first run and paid for the whole apparatus.

### Contract checks — each read off the source, none assumed

* **Clobbers A and B.** Identical to `fch_valid`'s documented contract
  (`; A = channel. Clobbers A, B.`), which all nine sites already tolerate. ✅
* **Preserves E, DE, HL.** The new code never writes them. `PRINT#`/`INPUT#` do
  `ld a,e / call fch_select` afterwards; `CLOSE` reads `E`; `OPEN` returns `DE`. ✅
* **Reads `D`.** Every site has `DE` = channel from `eval`/`eval_chan`, so `D` is
  meaningful at all nine — three sites already test it explicitly, and the other
  six were silently truncating to `E`, which IS the `#256` defect. ✅
* **Raising is safe at every site.** All nine already reach a raiser within a few
  instructions (`fch_mode_class` → `err_notopen_raise`), and `raise_error` resets
  `SP` from `SAVSTK` on **both** the trap and the abort arm — the same
  depth-independence `LOF` has relied on since S-FCH-2. `CLOSE`'s `push hl` and
  `FIELD`'s guarded cursor need no `pop`. ✅
* **`oo_fail_bfn` clears `FCH_MODE`, and that is harmless for the eight new
  callers.** `FCH_MODE` is a *mirror* re-stamped by `fch_select`
  ([`files.asm:1148`](../basic/files.asm:1148)), and **every one of its three
  readers** ([`print.asm:75`](../basic/print.asm:75),
  [`files.asm:720`](../basic/files.asm:720),
  [`files.asm:1135`](../basic/files.asm:1135)) is immediately preceded by a
  `call fch_select`. Verified by reading all three, not by inference from the name. ✅
* **ERR 5 prints the right text.** `err_msgtab[5]` → `err_illegal_fn_arr`
  ([`interp.asm:933`](../basic/interp.asm:933)); `field.asm`'s `exf_dev` already
  raises 5 exactly this way and `wm_lpt_fld` pins it green. ✅
* **`INPUT$`'s reject stops being a parse fallback.** `str_eval_no` means "not a
  string operand" (CF clear); after this it raises. That is the reference's
  behaviour (measured FNO/BFN/IFC, never `Syntax error`) and the site is already
  past its closing `)` with `fch_mode_class` two lines below. ✅
* **`MAXF` is a byte at `$E011`**, so `ld a,(MAXF)` is 3 B. ✅

## 4. Behaviour that CHANGES, stated plainly

1. All 63 diverging cells in §2b answer the reference's class.
2. **`EOF`/`LOF` on a rejected channel stop returning a number.** They now raise.
   A program that did `IF LOF(0)=0 THEN …` and silently got `0` will now error.
   This is the reference's behaviour and is the point of the slice.
3. **`CLOSE` on an out-of-range channel stops being a no-op** and raises 52 / 5.
   `CLOSE #0` and bare `CLOSE` are unchanged.
4. `PRINT#`/`INPUT#`/`LINE INPUT#` **halt or trap** instead of printing
   `load error` and continuing. Every probe was checked for a mid-program
   out-of-range channel op — there are none (§7).
5. All of these now fire an armed `ON ERROR GOTO` with `ERR` = 5 / 52 / 59.

## 5. The gate

A NEW probe, `probes/disk/diskbasic_probe_badfnum.py`, target
`make badfnum-acceptance`, carrying **the whole measured grid** — the 60 core
cells, the 4 controls, the 8 trappability rows and the 9 edge cells of §2d — each
with its own `REF_EXPECT` oracle lock, so an oracle change fails the run on its
own rather than reading as a zerobas result.

Controls that must stay green (so a red row elsewhere is attributable):
`ctl_syntax`, `ctl_ch1_open`, `ctl_pr1_closed`, `ctl_mf2_ch2`, `trap_lof1`, and
the six ✅ rows of §2d.

**The class table carries `Type mismatch` and `Overflow`** from the start, so
neither can classify as `None` — which also reads as "nothing went wrong".

### The existing `lof` gate's allowlist

`KNOWN_DIVERGE["closed_ch2"]` is **DELETED, not updated**; the `closed_ch2` row
stays and must read `BFN` on both. ⚠️ That empties `KNOWN_DIVERGE`. Per
`deadcode-gate` an allowlist that only suppresses is rot, so the emptiness is made
**explicit and asserted** — the same state `chancost` already ships in — rather
than left as a dict that silently matches nothing. `DIR_DIVERGE` still holds
`rand_put` and is unaffected.

## 6. IN SCOPE OR NOT — the `TMISMATCH` channel, decided by measurement

`PRINT #A$,"X"` hard-zeroes the channel to 0 and derails to `load error`
([`float-arith.asm:1291`](../basic/float-arith.asm:1291) — `eval_chan` skips the
int coercion on a type mismatch, deliberately). The reference answers **`Type
mismatch`**.

🔴 **THIS SLICE MOVES THAT CELL WHETHER OR NOT IT IS FIXED.** With `fch_check` in
place, channel 0 raises ERR 59 — so `PRINT #A$` would go from one wrong answer
(`load error`) to a *differently* wrong answer (`file not open`), which is worse:
it is confidently wrong instead of obviously wrong.

The fix is **0 bytes and one token**: `eval_chan`'s tail

```
evc_check:      jp      check_fperr_only    ->    jp      check_expr_errors
```

`check_expr_errors` is the same routine with the `TMISMATCH` test *in front*
([`interp.asm:1170`](../basic/interp.asm:1170) — `check_fperr_only` is documented
as its fall-in entry point, "adds no bytes"). On the non-mismatch path `TMISMATCH`
is 0, so that arm is bit-identical to today. The tail-`jp` shape that makes the
abort chain SP-clean is unchanged, because both entry points pop the same
`eval_chan`-caller resume address.

**Recommendation: take it.** It is free, it is measured, and leaving it out means
knowingly shipping a cell this slice made worse. Rows `tm_prw` / `tm_inp` /
`tm_lof` go in the gate either way.

## 7. Blast radius

`grep`ped `probes/`, `tests/` and `disk/` for a mid-program channel operation on an
out-of-range or type-mismatched channel — the behaviour change in §4 only bites
where one exists. **RUN BEFORE THE FIRST EDIT. Two hits, both benign:**

* [`disk_probe_maxfiles.py:13`](../probes/disk/disk_probe_maxfiles.py:13) — types
  `MAXFILES=2` before touching `#2`, so the channel is in range.
* [`disk_probe_open_device.py:69`](../probes/disk/disk_probe_open_device.py:69) —
  the same, with the comment already saying so ("`#2` needs the ceiling raised
  from the default 1").

Nothing else in the tree operates on a channel this slice re-dispositions.
**Blast radius: zero.**

## 7.1 🔴 A THIRD PROBE ENCODED THE OLD BEHAVIOUR AS AN ORACLE

`make diskbasic-acceptance` went **red** on `CLOSE(list)` — and the blast-radius
grep in §7 could not have found it, because the grep looked for out-of-range
channels and this probe's program is
[`disk_probe_closelist.py`](../probes/disk/disk_probe_closelist.py)'s
`CLOSE#1,#2,#3` **at the default `MAXFILES=1`**, where #2/#3 are out of range only
if you already know what `MAXF` is. Its docstring called that a "lenient no-op".

⚠️ **THAT WAS A ZEROBAS-ONLY FUNCTIONAL ORACLE WITH NO REFERENCE COLUMN — an
assumption promoted to an expectation.** Typed on the CF-3300 rather than argued
about:

| typed (`MAXFILES=1`) | reference | zerobas after |
|---|---|---|
| `OPEN…AS #1 : PRINT #1,"HELLO" : CLOSE #1,#2,#3` | **ERR 52**, dir **8** | **ERR 52**, dir **8** |
| the same at `MAXFILES=3` | no error, dir 8 | no error, dir 8 |
| `CLOSE #1` alone | no error, dir 8 | no error, dir 8 |

The reference raises — **and still flushes #1 first**, which the directory column
proves and a screen reading alone would not. So the new behaviour is right and the
probe's premise was wrong. Line `5 MAXFILES=3` was added so the probe keeps
testing what it exists to test (the **list parser** consuming the whole comma list
instead of stopping after `#1`) without resting on a leniency the reference does
not have.

## 8. Falsification plan — knives, each paired with a GREEN control

Every knife is aimed at code **downstream** of the edit, and every red row is
paired with a green one, so "the row moved" cannot be confused with "the build
broke" (memory: `notopen-chan-err59-slice`).

* **K1 — delete the `jp c,oo_fail_bfn` in `fch_check_nz`.** Every `#2`/`#16` row
  must go red; every `#0` row and `trap_lof1` must stay GREEN. Separates the
  `> MAXF` arm from the `= 0` arm.
* **K2 — delete `fch_check_d`'s `jr nz,fchk_ifc`.** Every `#256`/`#-1` row red;
  every `#0`/`#2`/`#16` row GREEN. Proves the ERR 5 arm is reached and is not
  being answered by one of the other two.
* **K3 — revert `expr.asm`'s two sites only.** The four `eof`/`lof` rows red, the
  other 56 GREEN. Proves the silent-`0` half is fixed by *those* hunks and not as
  a side effect of the shared routine landing.
* **K4 — revert `files.asm`'s `CLOSE` hunk only.** The four `clo_c*` rows red,
  `clo_c0` GREEN. `CLOSE` is the one verb that gains an error where it had none.
* **K0 — aimed at §3's own justification, not at the code.** The claim "clearing
  `FCH_MODE` from `oo_fail_bfn` is harmless for the eight new callers" rests on
  every reader being preceded by `fch_select`. Knife: under an armed handler, trap
  a `PRINT #2` **between** a successful `OPEN … FOR OUTPUT AS #1` and a
  `PRINT #1,"X"`, and check the write still lands. If the byte does not reach the
  file, the contract check in §3 is wrong and the design needs its own 52 raiser
  (+5 B). D-NOTOPEN2's K0′ refuted exactly this kind of already-written-down
  argument.
* **K5 — added after §5.1, and the sharpest of the set.** Cut the `TMISMATCH` test
  in `fch_check_d`. Without it, "§6 is a real layer" and "§6 is decoration
  subsumed by `fch_check`" are indistinguishable, because both leave the gate green.

### RESULTS — all six RUN, on the shipping build

| knife | expected RED | expected GREEN | result |
|---|---|---|---|
| **K1** cut `jp c,oo_fail_bfn` | the 4 `> MAXF` rows | `c0` rows, `ctm`, `ctl_mf2_ch2`, `trap_lof1` | ✅ 4 red **in four different ways** (FNO / 7 / 7 / 0 — each verb falls through to its own downstream behaviour), 5 green |
| **K2** cut `jr nz,fchk_ifc` | the 4 `D != 0` rows | `c0`/`c2`/`c16`, `trap_lof1` | ✅ 4 red, 4 green — and `opn_c256` fell back to **BFN**, reproducing the exact cell the sweep found |
| **K3** revert `expr.asm` only | the 4 `eof`/`lof` rows | `prw`, `fld`, `lof_ctm`, `trap_lof1` | ✅ 4 red **back to the silent `0`**, 5 green |
| **K4** revert the `CLOSE` hunk | `clo_c2`, `clo_c16` | `clo_c0`, `clo_c256`, `clo_ctm`, `prw_c2` | ✅ 2 red, 6 green — the knife cut `fch_check_nz` only, so **only** the `> MAXF` rows moved |
| **K5** cut the `TMISMATCH` test | the 8 verbs on plain `eval` | the 4 that reach `eval_chan` | ✅ **exactly** `prw`/`pru`/`inp`/`lin` green, all others red — §6 is load-bearing |
| **K0** the justification | — | `k0_trapped` 52 / dir 7, `k0_control` 0 / dir 7 | ✅ **the argument HELD** — no extra raiser needed |

⚠️ **K0's FIRST CUT WAS NOT A MEASUREMENT AND THE SCREEN SAID SO.** It read `DIR=7`
on subject *and* control and looked like a clean pass — but both rows also printed
`RESUME without error`, because the program had no `END` and fell into its own
handler. "7 on both" could not separate *"the trap fired and the write survived"*
from *"line 20 did nothing at all"*. The handler now records the code and the
program ends, so each row reads **two** facts. Both K0 rows are permanent gate
rows, with the directory column in the verdict.

## 9. Gates — ALL RUN, ALL GREEN

Clean `rm -rf build && make basic-reloc`: **low 23 B, page 1 63 B, dead-code
0/0 in BOTH builds** · `make unit-test` **55/55** · the new
`make badfnum-acceptance` **93 cases / 0 unfiled / 0 drift / 0 mangled / 0
unlocked** · `make lof-acceptance` **41 cases / 0 unfiled, `KNOWN_DIVERGE` now
EMPTY** · `make chancost-characterize` **39 / 0** · `make diskbasic-acceptance`
**34/34** (red first — §7.1) · `make bdos-acceptance` **12/12** ·
`make fat-error-acceptance` **8/8 + dir** · `make error-trap-acceptance` **PASS** ·
`make abort-acceptance` **49/49** · `make stop-trap-acceptance` **PASS** ·
`make linemax-acceptance` **60/60** · `make arrdim-acceptance` **73/73** ·
`make clearpool-acceptance` **52/52** · `make array-acceptance` **149/151**, the
two standing rows confirmed BY NAME (`ifc.instr.zero`, `ifc.instr.neg` — the
pre-existing capitalisation divergence).

The original list, for reference:
`make repack-machine`, then clean `rm -rf build && make basic-reloc` (dead-code
gate, 0 dead in BOTH builds), then `make unit-test` 55/55 · the new
`make badfnum-acceptance` · `make lof-acceptance` 41 cases / 0 unfiled ·
`make chancost-characterize` 39 / allowlist empty · `make diskbasic-acceptance`
34/34 · `make bdos-acceptance` 12/12 · `make fat-error-acceptance` 8/8 + dir ·
`make error-trap-acceptance` · `make abort-acceptance` 49/49 ·
`make stop-trap-acceptance` · `make linemax-acceptance` 60/60 ·
`make arrdim-acceptance` 73/73 · `make clearpool-acceptance` 52/52 ·
`make array-acceptance` 149/151 (the two standing rows confirmed BY NAME:
`ifc.instr.zero`, `ifc.instr.neg`).

⚠️ Order: clean measure → `make repack-machine` → probe. `rm -rf build &&
make basic-reloc` rebuilds neither `build/disk.rom` nor
`build/zerobas-main-eu.rom`, and the machine XML names both by absolute path.
