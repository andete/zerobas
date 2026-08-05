# D-INJSINK — emitted or matched against, and the hole the false positive was hiding

Apparatus slice. **Touches no `basic/`, no `sub/`, no `disk/`, no `tape/` source**
— one checker, one library helper, one host test — so no sign-off gate applies.
Written up as a slice anyway, with predicted RED/GREEN sets fixed at exact values
before the change.

Closes the one item [`docs/latch2-window-characterization.md`](latch2-window-characterization.md)
§10.1 filed:

> **`make injector-check` CLASSIFIES ITS OWN DETECTOR AS AN INJECTOR.** … Closed
> for now as a fourth named structural exemption … **The open question is whether
> the classifier should distinguish a literal that is EMITTED from one that is
> MATCHED AGAINST**; it fails closed today, which is the right direction, but
> every future assertion-about-injectors file will need an exemption.

Companion: [`docs/spec-probe-lastinj.md`](spec-probe-lastinj.md) §3.4 (the gate's
design), [`docs/spec-probe-latch2.md`](spec-probe-latch2.md) (the host test).

---

## 1. The filed item, and what it actually is

`make injector-check` proves the tree holds exactly ONE type-ahead injector. A
`.py` under `probes/`, `tools/` or `tests/` offends when its **string literals**
contain `debug write memory` **and** the file names a type-ahead cursor. 257
files, 253 CLEAN, 4 EXEMPT, 0 offenders.

D-LATCH2's corpus turned it red on `tests/test_key_drain_guard.py` — a host test
that boots nothing and emits no Tcl. Its `debug write memory` is the **needle of
a regex** asserting that `key_proc()` does *not* write `GETPNT`. It was closed as
a fourth named structural exemption, with the reasoning that the alternative —
renaming the needle — would leave the next reader unable to tell evasion from
innocence.

The filed item carries **two claims**, and this slice checks both before building
on either [[filed-justification-is-a-claim]]:

* **Claim A** — the host test cannot be written so it does not trip the
  classifier without becoming evasive.
* **Claim B** — the useful question is *emitted vs matched against*, and the cost
  of not answering it is an exemption list that grows once per assertion file.

---

## 2. What was measured before designing

### 2.1 🔴 Claim A is FALSE — and the non-evasive rewrite is a one-line move

The host test restates the injector's **wire format** (`debug write memory <addr>`)
in order to assert about it. That format is not the test's to own: it is
`probes/lib/omsx_repl.py`'s, the module that writes it, and that module is
exempt by construction and forever.

Measured, by classifying the rewritten source: with `writes()` replaced by a call
to a predicate living in `omsx_repl`, the host test classifies

    CLEAN   emits no 'debug write memory'

with **zero** residual occurrences of the literal. No renaming, no splitting, no
obfuscation — the next reader sees `omsx_repl.tcl_writes(key, GETPNT)` and can
read what it means. So the exemption was not forced. Fourth filed justification
running to be wrong, and again in the direction that deferred work.

### 2.2 🔴 And the false positive was hiding a FALSE NEGATIVE of exactly the shape the gate exists to catch

Making that move sanctions a pattern — *the write vocabulary lives in one module
and other files name it* — so the obvious next question is what else can cross a
module boundary. Measured against the shipped classifier:

| # | body | verdict today |
|---|---|---|
| **H1** | `from latch_check import OLD_KEY` … `return OLD_KEY % {…}` | **CLEAN** |
| **H2** | `import latch_check` … `return latch_check.OLD_KEY` | **CLEAN** |
| **H4** | control: `FROZEN_FAULT` verbatim | **COMPOSES** |

`latch_check.OLD_KEY` is **the pre-D-LATCH injector, frozen** — the exact body
`make latch-check` row A forces onto the `$1197` trigger and requires to MANGLE,
sixteen boots a run. A probe can emit it verbatim, ship the D-LATCH delivery
race, and pass `injector-check`. This is not an evasion shape: "the frozen body
is already written down, import it" is what a careful author does. The tree
already imports `latch_check` from a test, so the path is live and idiomatic.

**The gate is blind to values that cross a module boundary.** The false positive
was the visible half of that blindness; the false negative is the half that
matters.

### 2.3 The emit/match discrimination, knifed rather than argued

A whitelist form was built and run: a WRITE-bearing literal whose immediate
context is a regex sink (`re.search`/`match`/`compile`/…) or a membership /
equality comparison does not count as emission.

Measured on the host test, the two WRITE-bearing literal nodes are:

| line | literal | AST context |
|---|---|---|
| 53 | `'debug write memory\s+'` | `JoinedStr` → **`Call(re.search)`** → `Call` → `Return` |
| 51 | `'True if this Tcl body has a \`debug write mem…'` | `Expr` → `FunctionDef` → `Module` — **a docstring** |

The whitelist clears line 53 and **cannot** clear line 51: the host test still
classifies `COMPOSES`. Line 51 is *prose*, and this tree explains the injector
mechanism in prose constantly — which is why the classifier counts every literal
and walks the AST in the first place. To clear prose, the rule has to become
"every literal that is not in an emitting position is excused", i.e. an all-uses
dataflow rule. That rule's hole is measured too:

    from latch_check import OLD_KEY
    def build(parts): return "".join(parts)
    def build_tcl():  return build(["set throttle off\n", OLD_KEY])

— laundered through an ordinary local call, which no AST pass here can follow.
**CLEAN today, and CLEAN under the all-uses rule.** That is not an evasion shape
either; it is how half the probes in this tree assemble Tcl.

🔴 **A prototype defect, recorded rather than quietly fixed.** The first
whitelist run reported `FROZEN_FAULT → CLEAN`, which would have been a
spectacular finding. It was a bug in the *prototype*: it re-implemented the
cursor-hit computation and dropped the `getpnt`/`putpnt` substring rule, so the
frozen fault's `_GETPNT` did not count. Re-run against the classifier's own
`_named`/`CURSORS` logic, the control is `COMPOSES` as it must be
[[knife-that-refutes-its-own-control]].

### 2.4 The denominator for the new rule

A **module-level name bound to an expression whose string literals contain
`debug write memory`** is a *frozen-body symbol*. Measured over the same 257
files:

| symbol | defined in |
|---|---|
| `latch_check.OLD_KEY` | `probes/lib/latch_check.py` |
| `latch_check.GETPNT_KEY` | `probes/lib/latch_check.py` |
| `check_probe_injectors.WRITE` | `tools/check_probe_injectors.py` |
| `check_probe_injectors.FROZEN_FAULT` | `tools/check_probe_injectors.py` |
| `check_probe_injectors.FROZEN_CLEAN` | `tools/check_probe_injectors.py` |

**5 symbols, 2 modules, and no module-basename collision anywhere in the 257** —
so `import M` / `from M import N` resolves unambiguously by basename, which is
how `probes/lib` is on `sys.path` at run time anyway.

Files naming a frozen-body symbol **from outside its defining module: exactly
one** — `tests/test_key_drain_guard.py`, which already holds an exemption.

---

## 3. The design

### 3.1 The answer to the filed question, stated plainly

**No general emitted-vs-matched rule.** §2.3 measures why: the discrimination
that is cheap (per-literal sink whitelist) does not clear the file it was for,
because prose is a literal too; and the discrimination that would clear it
(all-uses dataflow) cannot see through a one-line local call, which is an
ordinary probe shape rather than an evasion. A rule with that hole would be worse
than the exemption it replaced, because an exemption is a *reviewed* line in a
file and a hole is not.

What replaces it is three narrower things, each measurable:

### 3.2 The wire format gets an owner (closes §2.1, and stops the growth)

`omsx_repl.tcl_writes(body, addr) -> bool` — "does this Tcl body carry a
`debug write memory` aimed at `addr`". It is a **predicate**, not a string: it
returns `bool`, so nothing can compose Tcl out of it, which is what makes it a
safe thing for other files to name. `tests/test_key_drain_guard.py` calls it and
stops restating the format.

This is the growth-stopper: an assertion-about-the-injector file that does not
touch a frozen body now needs **no exemption at all**.

### 3.3 Frozen bodies are SEQUESTERED (closes §2.2)

New rule, alongside the existing one and independent of it:

> A file offends when it **names a frozen-body symbol defined in another module**.

No use analysis, nothing to fool: the offence is reaching for the body, not what
you do with it afterwards. H1 and H2 both offend. The registry is **generated**
from the tree on every run, the way `injector-check` replaced a hand-maintained
list in the first place [[lastinj-slice]].

⚠️ **A generated registry can go empty and take the rule with it.** So the
registry is *pinned*: `latch_check.OLD_KEY`, `latch_check.GETPNT_KEY` and
`check_probe_injectors.FROZEN_FAULT` are known-by-construction and their absence
is `CANNOT JUDGE`, not a clean walk — the same reasoning as "0 files scanned is
not a clean tree, it is a broken walk".

### 3.4 The exemption list gets classes, and one class is MACHINE-CHECKED

Every entry now states which of three things the file is:

| class | meaning | today |
|---|---|---|
| `SHIPS` | this file **is** the one injector | `probes/lib/omsx_repl.py` |
| `HOLDS` | this file **defines** a frozen fault body as a control | `probes/lib/latch_check.py`, `tools/check_probe_injectors.py` |
| `HANDLES` | this file **names** a frozen body defined elsewhere, to assert about it | `tests/test_key_drain_guard.py` |

🎯 **A `HANDLES` entry is a NARROW claim and the gate checks it**: the file must
carry **no `debug write memory` literal of its own**. Claim more than that and the
exemption stops covering you. This is what makes the list safe to grow — §5 states
the review rule — and it is why §3.2 is load-bearing rather than cosmetic: the
host test could not make the `HANDLES` claim today.

### 3.5 The self-test gains a POSITIVE for the new rule

The existing two-sided frozen self-test is untouched. Two rows are added, also
two-sided, so the new rule cannot be vacuous either:

* `FROZEN_LAUNDER` — H2's body, importing a frozen body and returning it — must
  classify **HANDLES**;
* `FROZEN_IMPORT_OK` — the same shape importing a **non**-frozen symbol from the
  same module — must classify **CLEAN**, so "flag every importer" fails as loudly
  as "flag none".

The self-test runs against a **frozen registry**, not the tree's, so it stays
hermetic.

### 3.6 What does NOT change

`key_proc()` itself and every byte of Tcl it emits; `latch_check`'s frozen
bodies; the existing classifier rule; `CURSORS`; both delivery oracles;
`MAX_DIRECT`. No `basic/`, `sub/`, `disk/` or `tape/` source; no ROM rebuilt.

---

## 4. Predicted RED and GREEN sets — fixed before the change

Baseline `07e9c0a`, tree clean, `make -q build/zerobas-main-eu.rom` **exit 0**.
Measured baseline: `injector-check` 257 files / 253 CLEAN / 4 EXEMPT / 0
offenders, exit 0; `unit-test` **58/58**. No two emulator gates concurrently.

### 4.1 The green set

| # | run | predicted |
|---|---|---|
| **G1** | `make injector-check` | `257` files, `253` CLEAN, `4` EXEMPT, **0** offenders, **0** UNPARSEABLE, exit 0 |
| **G2** | its self-test banner | **4** frozen rows pass: FAULT→COMPOSES, CLEAN→CLEAN, LAUNDER→HANDLES, IMPORT_OK→CLEAN |
| **G3** | the registry line | **5 symbols across 2 modules**, and all 3 pinned symbols present |
| **G4** | `make injector-check LIST=1`, the 4 EXEMPT rows | `omsx_repl.py` **SHIPS**; `latch_check.py` **HOLDS**; `check_probe_injectors.py` **HOLDS**; `test_key_drain_guard.py` **HANDLES**, and its `HANDLES` claim **validates** (no WRITE literal of its own) |
| **G5** | `tests/test_key_drain_guard.py` classified with its exemption removed | **CLEAN** on the literal rule, **HANDLES** on the registry rule — i.e. §3.2 really did remove the first reason |
| **G6** | `make unit-test` | **58/58** |
| **G7** | `make preflight-check` | **0 unguarded** (no new spawn site) |
| **G8** | `make latch-check` | **16/16**, exit 0 — `key_proc`'s emitted Tcl is byte-identical, so its subject cannot have moved |
| **G9** | `make diskbasic-acceptance` | **34/34 verbs converged**, exit 0 |
| **G10** | `make -q build/zerobas-main-eu.rom` | **exit 0** throughout |
| **G11** | `omsx_repl.key_proc()` before vs after | **byte-identical** — the helper is additive |

### 4.2 The red set — the knives

| knife | cut | predicted RED | predicted GREEN control |
|---|---|---|---|
| **K1** | the registry pre-pass gutted to return `{}` | 🎯 **`CANNOT JUDGE`, exit 2** — the pin trips first (`FROZEN_LAUNDER` classifies CLEAN, and the 3 pinned symbols are missing) | G1/G2/G3 unmodified, exit 0 |
| **K2** | **K2-shaped**: registry built, walk run, report printed — only the *judgement* gutted (registry hits never marked) | `FROZEN_LAUNDER` classifies **CLEAN** → **`CANNOT JUDGE`, exit 2**. The tally would have been `0 offenders` [[coverage-gate-cannot-see-a-gutted-guard]] | K1 in the same session |
| **K3** | H2 planted as a real file, `probes/disk/disk_probe_launder.py` | **1 offender**, exit 1, named `HANDLES … latch_check.OLD_KEY` | the same run with the plant removed: **0 offenders**, exit 0 |
| **K3b** | 🔴 the *pre-change* classifier on the same plant | **0 offenders, exit 0** — a green gate over a tree that ships the frozen fault verbatim. This is the finding, not the fix | K3 after the change: 1 offender |
| **K4** | `omsx_repl.tcl_writes` gutted to `return False` | `make unit-test` **FAILS** on `test_key_drain_guard.py`, row **R4** (`OLD_KEY writes GETPNT` → `False`, want `True`) — the moved predicate is still knifed by the test that uses it | G6 unmodified: 58/58 |
| **K5** | the `HANDLES` validation removed, and a `debug write memory` literal planted in `tests/test_key_drain_guard.py` | with validation **in place**: the planted file is reported (its `HANDLES` claim no longer covers it), exit non-zero. With it removed: `0 offenders`, exit 0 | the unplanted tree: exit 0 either way |
| **K6** | the existing frozen pair (`FROZEN_FAULT`, `FROZEN_CLEAN`) re-scored under the new classifier | unchanged: **COMPOSES** / **CLEAN**. A new discrimination that let either move would have widened the hole it narrowed | — |

### 4.3 Corpus

Sequential, no two emulator gates at once: `unit-test` · `injector-check` ·
`preflight-check` · `latch-check` · `diskbasic-acceptance` · `deadcode`.
`make -q build/zerobas-main-eu.rom` exit 0 throughout.

⚠️ Blast radius: `probes/lib/omsx_repl.py` is imported by every probe, so the
additive helper is priced by G8/G9/G11 rather than assumed.

---

## 4bis. What landed, and what it measured

`probes/lib/omsx_repl.py` (+ `tcl_writes`, additive), `tools/check_probe_injectors.py`
(rule (b), the generated registry, the pin, exemption classes and the `HANDLES`
validation) and `tests/test_key_drain_guard.py` (stops restating the wire format).
**No `basic/`, `sub/`, `disk/` or `tape/` source touched; `make -q build/zerobas-main-eu.rom`
exit 0 throughout, so no ROM was rebuilt.**

### 4bis.1 🔴 The gate shipped at `07e9c0a` certifies a tree that ships the frozen fault

K3b is the finding. `probes/disk/disk_probe_launder.py` — nine lines, `import
latch_check`, `return "set throttle off\n" + latch_check.OLD_KEY` — planted in
the tree and scored by the **shipped** classifier:

    files scanned : 258
      compose their own injector : 0
    ALL PASS -- one injector in the tree, and it is the one `make latch-check` scores.
    rc = 0

`OLD_KEY` is the pre-D-LATCH injector verbatim: the body `make latch-check` row A
forces onto `$1197` and requires to MANGLE, and the body D-LASTINJ proved was
character-identical to the last copy it re-pointed. The gate whose whole purpose
is "there is ONE injector in this tree" reported ALL PASS over two. The same
plant under the new classifier: **1 offender, exit 1**, named
`HANDLES … latch_check.OLD_KEY`; with the plant removed, **0 offenders, exit 0**.

### 4bis.2 The green set hit exactly

G1 `257 / 253 CLEAN / 4 EXEMPT / 0 offenders`, G2 rows A–D, G3 `5 symbols across
2 modules, all 3 pinned present`, G4 the four classes as predicted, G6 `58/58`,
G7 `0 unguarded / 95 guarded`, G8 **`latch-check 16/16`**, G9 **`diskbasic-acceptance
34/34`**, G10 exit 0, `deadcode` 0/0.

**G11 is the one that prices the blast radius**: `key_proc()` emits **730 bytes,
sha256 `f936ab2a…`, byte-identical before and after** — so `omsx_repl`'s new
helper cannot have moved any probe's delivery alignment, which is the property
D-LATCH §4.3 warns is at stake whenever that module is touched.

**G5 is the one that shows §3.2 was load-bearing rather than cosmetic.** With its
exemption removed, `tests/test_key_drain_guard.py` now classifies **`CLEAN` on
rule (a)** and `HANDLES` on rule (b) — the first of its two reasons for needing an
exemption is gone, and what remains is the narrow claim the gate checks.

### 4bis.3 The knives, scored

| knife | measured |
|---|---|
| K1 | registry pre-pass gutted → **`CANNOT JUDGE`, rc 2**, naming all three pinned symbols |
| K2 | rule (b)'s judgement gutted, walk + report intact → **`CANNOT JUDGE`, rc 2** on self-test **row C** |
| K3 | plant present → **1 offender, rc 1**; plant removed → **0, rc 0** |
| K3b | the same plant, **pre-change** classifier → **ALL PASS, rc 0** (§4bis.1) |
| K4 | `tcl_writes` → `return False` → `test_key_drain_guard` **rc 1**, rows **R1** and **R4** FAIL |
| K5 | a `debug write memory` literal planted back into the host test → **`BAD EXEMPTION`, rc 1**; with the validation removed, the identical plant scores **`0 offenders, rc 0`** |
| K6 | `FROZEN_FAULT` still **COMPOSES**, `FROZEN_CLEAN` still **CLEAN** — the new discrimination widened nothing |

A GREEN control was run in the same session immediately before and after every
knife: `rc 0`, `0 offenders`, `all rows passed`.

🔴 **K1's prediction was wrong in its mechanism, and it is recorded rather than
rewritten.** It predicted the self-test would trip ("`FROZEN_LAUNDER` classifies
CLEAN") *and* the pin. Only the pin trips: the self-test judges against
`FROZEN_REGISTRY`, which is hermetic by design (§3.5), so gutting the *tree's*
pre-pass leaves row C passing. That is the pin's entire reason for existing, and
without it K1 would have been a silent green — the same shape as
[[coverage-gate-cannot-see-a-gutted-guard]], one layer further out. The two
devices are not redundant: K2 shows the self-test catches a gutted judgement, K1
shows only the pin catches a gutted input.

### 4bis.4 🔴 A prototype defect, in the measurement rather than the tree

§2.3's first whitelist run reported `FROZEN_FAULT → CLEAN`, which would have been
a headline. It was the prototype: it re-implemented the cursor-hit computation
and dropped the `getpnt`/`putpnt` substring rule, so `_GETPNT` did not count.
Re-run against the classifier's own `_named`/`CURSORS`, the control is `COMPOSES`.
The knife that refutes its own control is refuting the apparatus
[[knife-that-refutes-its-own-control]] — and this one was caught only because the
control was scored in the same run as the subject.

---

## 5. What makes the exemption list safe to grow

🔴 **The count does NOT drop. It stops growing for the general case, and the one
class that can still grow is one that must be reviewed anyway.** Stated exactly,
because the alternative was to claim a drop the measurements do not support:

* An assertion-about-the-injector file that inspects `key_proc()`'s output needs
  **no** entry — §3.2 removed the reason.
* A file that reaches for a **frozen fault body** needs a `HANDLES` entry. That
  is correct: handling a live fault body is a reviewed act, not a formality.
* A `HANDLES` entry must state **which symbols** it names and **why they cannot
  reach the machine**, and the gate checks the narrow half of that claim (no
  WRITE literal of the file's own). The wide half — "cannot reach the machine" —
  is the reviewer's, and the reviewer is whoever signs the slice that adds it.
* `SHIPS` is one file and is not expected to grow. `HOLDS` grows only when a new
  era freezes a new fault body, which is a slice-sized event with its own gate.

---

## 6. Coverage limits, stated in advance

* **The classifier is still a text classifier.** A split literal
  (`"debug write" + " memory"`) passes, as it did before; so does a frozen body
  laundered through a local call (§2.3). Neither is narrowed here, and neither is
  a careless-author shape — but both are stated rather than implied.
* **The registry is module-basename-resolved.** Measured collision-free over 257
  files today; a future duplicate basename would resolve to both, which is the
  eager direction.
* **`from M import *`** is handled by flagging any frozen-body symbol in `M`.
  Eager, and there are no star-imports in the tree today.
* **`HANDLES` validation checks the file, not the intent.** It proves the file
  restates no write format of its own; it cannot prove the file does not boot a
  machine. `preflight-check` is the gate that prices that, separately.
