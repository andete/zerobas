# The `CALL` device-name scan — MSX1 characterization (D-CNAME)

*Measurement. Spec: [`docs/spec-basic-cname.md`](spec-basic-cname.md).
Probe: [`probes/basic/basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py),
batteries `cnm` (stored bytes) and `cnmd` (`--say`).*

Every row here is oracle-locked on **two** references — a Philips VG-8020 and a
National CF-3300 — at `--repeat 2`, past the echo guard, before zerobas was run
on any of them. Readout is `("stored_line", TXTTAB)`: the exact bytes of the
stored line, link word dropped. The two references **agree on every row**.

---

## 0. Why this battery exists

D-LNLIST filed this defect three times over, and **not one of the three rows was
designed to measure it**. Each was written to ask whether `CALL` clears
line-number mode, and each had its digit eaten by the name scan first
([`lnlist-msx1-characterization.md`](lnlist-msx1-characterization.md) §4):

```
lnl-under   20 IF A THEN _X 5       ref -> <8B> A <DA> _X 5        zb -> <8B> A <DA> _X <16>
lnl-call    20 IF A THEN CALL X 5   ref -> <8B> A <DA> <CA> X 5    zb -> <8B> A <DA> <CA> X <16>
lnl-callp   20 IF A THEN CALL X+5   ref -> <8B> A <DA> <CA> X5     zb -> <8B> A <DA> <CA> X<F1><16>
```

Two facts came out of them: the reference keeps a trailing digit as **verbatim
ASCII** across a blank, and for `X+5` it **drops the `+` outright**. Four rules
fit both:

| | rule |
|---|---|
| **N** (name) | copy identifier chars (upcased), STOP at the first other character. **zerobas today** — `is_ident_cont` is letter-or-digit, so not even `.` continues. |
| **S** (skip) | copy identifier chars and blanks, **drop** everything else, run on to some terminator. |
| **P** (plus-only) | rule N, except `+` specifically is swallowed. |
| **V** (verbatim) | copy everything to a terminator. **Already refuted** — the `+` is not in the stored line at all. |

🔴 **S AND P PREDICT THE SAME BYTES FOR ALL THREE FILED ROWS.** One row proves a
defect exists; it does not say what the rule is. So the battery drops the
`IF A THEN` — that question is answered and carrying it would put a second
candidate cause in every payload, the `lnl-colon` mistake one slice later — and
walks the character space instead of sampling it.

---

## 1. Round 1 — the walk, and **both S and P are refuted**

`20 CALL X<c>5`, one character at a time. Under N every row stores `<CA> X` plus
the ordinary tokenisation of `<c>5`; under S every row stores `<CA> X5`; under P
only the `+` row does.

**None of those is what the machine does.** The characters split into three
classes, and the split is not the one any of the four rules predicted:

```
DROPPED -- the character is gone and the scan CONTINUES

  20 CALL X!5   <CA> X5      20 CALL X)5   <CA> X5      20 CALL X,5   <CA> X5
  20 CALL X"5"  <CA> X5      20 CALL X*5   <CA> X5      20 CALL X-5   <CA> X5
  20 CALL X#5   <CA> X5      20 CALL X+5   <CA> X5      20 CALL X.5   <CA> X5
  20 CALL X$5   <CA> X5      20 CALL X%5   <CA> X5      20 CALL X/5   <CA> X5
  20 CALL X&5   <CA> X5      20 CALL X'5   <CA> X5

KEPT -- stored verbatim, and the scan CONTINUES (the 5 stays ASCII)

  20 CALL X 5   <CA> X 5     20 CALL X>5   <CA> X>5     20 CALL X\5   <CA> X\5
  20 CALL X;5   <CA> X;5     20 CALL X?5   <CA> X?5     20 CALL X^5   <CA> X^5
  20 CALL X<5   <CA> X<5     20 CALL X@5   <CA> X@5
  20 CALL X=5   <CA> X=5

TERMINATES -- the scan ends and the ordinary crunch takes the rest

  20 CALL X(5)  <CA> X(<16>)
  20 CALL X:5   <CA> X:<16>
```

---

## 2. 🔴 The boundary is the NUMERIC RANGE — and the operators land on **both** sides

`+ - * /` are **dropped**. `^ \ = < >` are **kept**. All nine are arithmetic or
relational operators with adjacent token bytes, so *"it is an operator"* explains
nothing — this is D-LNLIST's interleaving shape again, where `\` ($FC) kept the
mode and `MOD` ($FB) cleared it with no threshold between them.

Sorted by **ASCII code** the classes are contiguous, and the walk covered the
whole of the decisive range:

| code | characters | class |
|---|---|---|
| `$20` | blank | **KEPT** |
| `$21`–`$2F` | `!` `"` `#` `$` `%` `&` `'` `)` `*` `+` `,` `-` `.` `/` | **DROPPED** — 14 of 15 |
| `$28` | `(` | **TERMINATES** — the one exception inside that range |
| `$30`–`$39` | `0`–`9` | **KEPT** (identifier characters) |
| `$3A` | `:` | **TERMINATES** |
| `$3B`–`$7E` | everything tested — see §3 | **KEPT** |

**The predicate is `' ' < c < '0'`.** Once end-of-line, `:` and `(` are taken
out, a character is discarded if and only if it lies in `$21`..`$2F`. Fifteen
characters, fourteen dropped and one terminating — **the range is a denominator,
not a sample.**

Two rows say the classes compose the way a single loop would, rather than each
being a special case of its own:

```
cnm-plpar   20 CALL X+(5)      <CA> X(<16>)        drop, then terminate
cnm-mix     20 CALL A+B C(1)   <CA> AB C(<12>)     drop, keep a blank, terminate
```

---

## 3. Round 2 — the KEEP side walked, and **three characters that cannot be delivered**

Round 1 read the keep side at `$3B`..`$40`, `$5C` and `$5E` — eight of the
~20 non-identifier characters at or above `$3B`. That is a sample, and D-LNLIST's
whole lesson is that a sampled class can be interleaved. Round 2 read every
remaining printable one:

```
20 CALL X[5   <CA> X[5      $5B          20 CALL X_5   <CA> X_5      $5F
20 CALL X]5   <CA> X]5      $5D          20 CALL X`5   <CA> X`5      $60
20 CALL X~5   <CA> X~5      $7E
```

All kept. **`_` is kept too** ($5F) — the character that *is* the `CALL`
abbreviation is an ordinary name character once a scan is running, not a
terminator.

### 🔴 `{`, `|` and `}` are NOT MEASURABLE, and one of them produced a perfect fake

Rows for `$7B`, `$7C` and `$7D` were written, run and **deleted**. `{` and `|`
returned `<NO CAPTURE>` on both references. `}` did something worse:

```
cnm-rbrc    typed `20 CALL X}5`    BOTH references -> line 20 | <CA> X{5}
```

A stored line containing a `{` **and** a `}` from a payload that had neither —
stable across two boots, agreeing on both machines, and entirely plausible next
to its neighbours. **The echo guard is the only reason this is known**, and it
caught all three before the measurement pass was read as a finding. Recorded in
§7 as not measured rather than kept as rows that cannot be delivered
([[apparatus-is-part-of-the-measurement]]).

### 🔴 A deterministic mangle that `--repeat 2` did NOT catch

`cnm-lower` (`20 CALL abc`) came back `REFUSED (empty program)` from zerobas in
the batched run — a payload with nothing unusual in it, sitting between
`cnm-digit1` and `cnm-lowmix`, which both read fine. Re-run **alone at
`--repeat 2`** on the same installed build it reads `<CA> ABC`, agreeing with
both references.

⚠️ **BOTH BOOTS OF THE BATCHED `--repeat 2` REPRODUCED THE REFUSAL IDENTICALLY**,
so the run reported no `UNSTABLE` and the row looked like a finding. openMSX is
deterministic: a harness race reproduces exactly, and repetition cannot separate
it from a behaviour ([[deterministic-mangle-is-still-a-mangle]]). Alone ✅ +
batch ❌ is a **delivery** failure. Taken at face value it would have been
written up as zerobas rejecting a lower-case device name.

⚠️ **IT CAME BACK TWICE MORE, AND THE ROW IS THEREFORE FLAGGED RATHER THAN
TRUSTED.** The same `REFUSED` appeared under knives **K1** and **K4**, neither of
which can reach a payload with no `$21..$2F` character and no `:`
([`spec-basic-cname.md`](spec-basic-cname.md) §7.3) — and under **K5**, where the
row reddens for a genuine reason, it produced an ordinary reading. It did **not**
recur in the landing gate, where all three sides read `<CA> ABC`. So the flake is
**intermittent between runs but deterministic within one**, which is the worst
combination for a `--repeat` guard: repetition sees it as stable either way. If
this row ever fails a future gate, **re-run it alone before reading it as a
divergence.**

### The fix: a SELF-HEAL pass, ported from `run_differential`

`omsx_repl.run_differential` already re-runs any disagreeing case boot-per-case so
its verdicts "equal a full boot-per-case run". This probe compares **three** sides,
so it drives `run_cases` per side and never inherited that. It does now
([`basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py) `main`): every
row that is `is_bad` on any side, or whose sides disagree, is re-measured
boot-per-case **before anything is read as a finding**.

This is not retry-until-pass. It re-measures under the *stronger* delivery, and it
ships with a falsifier: the seven INFORMATIONAL rows (`ref-list`, `ref-delete`,
`ref-auto`, `ref-renum`, `ref-else`, `dec-eol`, `dec-eolctl`) diverge for measured
reasons, are healed on **every** run, and **must still diverge**. If one comes back
agreeing the probe exits 1 with `SELF-HEAL FAILURE`. Measured 2026-08-01: 114/114
gating rows agree, 7 rows healed, all 7 still divergent.

⚠️ **THE HEAL IS ASYMMETRIC AND IS NOT A SUBSTITUTE FOR `--repeat`.** It only
touches rows that already look wrong, so it can turn a false FAIL into a pass and
can never catch a false PASS. In the ORACLE-LOCK direction a mangle is a false pass
forever, and `--repeat 2` remains the only guard for that.

⚠️ **And the echo guard on the zerobas side is CLEAN for all 56 `cnm` payloads**
(run 2026-08-01; the earlier echo pass covered only the two references). So the
payload does arrive and `cnm-lower` is not a reproducible typing failure — which
means the mechanism is still undiagnosed, and the heal is a containment, not a
diagnosis.

⚠️ Another apparatus limit, found the same way: the echo guard matches whole
**screen rows**, so any payload longer than the display width wraps and can never
match. `cnm-long`'s first cut was 43 characters and read `MANGLED` on both
references identically — the signature of a geometry limit, not a machine
transform. Shortened to 34, which still puts 26 characters of name far past
MSX's 16-byte `PROCNM` device-name buffer.

---

## 4. Blanks, case, keywords, length

```
cnm-blk      20 CALL X 5        <CA> X 5       a blank is kept and the scan RUNS ON
cnm-blk2     20 CALL X  5       <CA> X  5      ...for a whole RUN of blanks
cnm-blkpre   20 CALL  X 5       <CA>  X 5      ...including before the first name char
cnm-twoword  20 CALL X Y        <CA> X Y       two words are ONE name
cnm-digit1   20 CALL 5X         <CA> 5X        a DIGIT may start the name

cnm-lower    20 CALL abc        <CA> ABC       upcased
cnm-lowmix   20 CALL aB3d       <CA> AB3D      ...through a digit, mid-name
cnm-lowplus  20 CALL x+y        <CA> XY        ...and across a DROPPED character

cnm-kw       20 CALL PRINT      <CA> PRINT     NOT crunched to $91
cnm-kwmid    20 CALL XFORY      <CA> XFORY     ...nor a keyword buried inside
cnm-format   20 CALL FORMAT     <CA> FORMAT    THE SHIPPED ORACLE: not FOR+MAT

cnm-long     20 CALL ABCDEFGHIJKLMNOPQRSTUVWXYZ
                                <CA> ABCDEFGHIJKLMNOPQRSTUVWXYZ    no bound at 26
```

`cnm-format` is the cell this slice must not move. `call format` →
`CA 20 46 4F 52 4D 41 54` is shipped behaviour, and
[`basic/format.asm:48`](../basic/format.asm:48) `ex_call` reads exactly those
bytes back.

---

## 5. `_` is the same scan

Every `CALL` row that was mirrored on `_` read the same way:

```
cnm-uctl^      20 _X            _X              cnm-ublk       20 _X 5       _X 5
cnm-upar^      20 _X(5)         _X(<16>)        cnm-ulow       20 _abc       _ABC
cnm-uplus      20 _X+5          _X5             cnm-ucolon     20 _X:5       _X:<16>
cnm-uminus     20 _X-5          _X5             cnm-ucolstmt   20 _X:PRINT 5 _X:<91> <16>
cnm-usemi      20 _X;5          _X;5
```

The `_` itself is stored as the literal `$5F`, not as the `CALL` token `$CA` —
zerobas already agrees, and `cnm-uctl`/`cnm-upar` are the two-sided controls that
say so.

---

## 6. What the bytes MEAN — the `cnmd` say battery

⚠️ **THE FIRST THREE ROWS CANNOT SEPARATE THE RULES, AND SAYING SO IS THE
FINDING.** An unknown device raises `Syntax error` whether its name came out `X`,
`X5` or `X 5`:

```
cnmd-ctl^    10 CALL X    : RUN : PRINT"[";ERR;"]"     vg8020 2   cf3300 2   zb 2
cnmd-blk     10 CALL X 5  : RUN : PRINT"[";ERR;"]"     vg8020 2   cf3300 2   zb 2
cnmd-plus    10 CALL X+5  : RUN : PRINT"[";ERR;"]"     vg8020 2   cf3300 2   zb 2
```

They pin that the fix must not change the error **class**; they measure nothing
about the name. The honest reason is §7: the only extended statement that exists
on either reference is `CALL FORMAT`, which writes a disk, so no row can reach a
live handler.

⚠️ **The brackets are on a LATER line on purpose.** The payload aborts, so a
`PRINT"[...]"` on the payload line would never reach its own `]` and `<none>` on
every side compares EQUAL
([`namedot-msx1-characterization.md`](namedot-msx1-characterization.md) §4).
`ERR` is asked in direct mode, where it prints its brackets either way.

The one semantic question that *is* reachable is whether `:` still ends the
statement — `ON ERROR` + `RESUME NEXT` resumes at the **next statement**, so `A`
reads 7 only if `A=7` is a statement of its own:

```
cnmd-colstmt   10 ON ERROR GOTO 100 / 20 CALL X:A=7 / 30 PRINT"[";A;ERR;"]"
               100 RESUME NEXT / RUN         vg8020 ` 7  0 `  cf3300 ` 7  0 `  zb ` 7  0 `
cnmd-colctl^   ...with `20 A=0:A=7` instead  vg8020 ` 7  0 `  cf3300 ` 7  0 `  zb ` 7  0 `
```

`A` reads **7** on all three sides: `:` ends the name scan and `A=7` is a
statement of its own. That is a **must-not-move** cell, not a red row — a widened
scan that swallowed the `:` would make line 20 one statement, `RESUME NEXT` would
skip to line 30, and `A` would read 0.

⚠️ **`ERR` reads 0, not 2, and the control reads the same as the subject.**
`RESUME` clears the error, so this row cannot witness that `CALL X` failed at all
— it witnesses only *where execution resumed*. `cnmd-colctl` is a positive
control for the readout, not a contrast, and `cnmd-ctl` is what pins ERR=2. Said
here rather than left for a reader to assume the pair is stronger than it is.

---

## 7. What was NOT measured

* **`{` `|` `}` (`$7B`–`$7D`)** — not deliverable through this harness (§3). The
  keep class is walked completely *except* for these three.
* **`$7F` and codes `$80`+** — MSX graphic and kana characters. No delivery path.
* **A live extended statement.** The rules are measured on the STORED BYTES only.
  `CALL FORMAT` is the sole handler that exists on either reference and invoking
  it writes a disk; `diskbasic-acceptance` is what runs it, against `cnm-format`
  pinning its bytes.
* **A name longer than 26 characters**, and therefore any bound above that — the
  echo guard's payload ceiling is the display width (§3).
* **A trailing blank at end of line.** Still not measurable through the keyboard
  (D-LNBLANK's standing limitation), so "does a trailing blank run get stored"
  cannot be asked here either.
* **`CALL` inside `DATA` or `REM`.** Both keep the rest of the line verbatim
  before the name scan can run, so there is nothing to ask.
