# D-REVJUDGE — the 7 `[REVIEW]` advisory headers: are they 7, and is anything watching?

Slice D-REVJUDGE, 2026-08-06, from `0e66408`. Sixth of the gate-judging arc
(D-ROMJUDGE → D-DSKJUDGE → D-CITEJUDGE → D-DOCJUDGE → D-BYTEJUDGE → **D-REVJUDGE**).

Subject: check 3 of [`tools/audit_citations.py`](../tools/audit_citations.py) — the
**advisory** section-citation rule. It reports a `disk/*.asm` section header
`; --- name ---` that carries no inline citation within
`SECTION_CITE_LOOKAHEAD = 6` comment lines. It prints 7 candidates and has never
affected an exit code.

The filed residual ([`TODO.md`](../TODO.md) §"Open — standing residuals"):

> ⚠️ **The 7 `[REVIEW]` advisory headers are stable but unwatched** — the same 7
> files and names across 575 commits, triaged once (`docs/clean-room-audit.md`,
> 2026-07-04). Advisory is the right call, but a NEW one would land unnoticed in a
> list nobody diffs. The fix is a `deadcode-allow.txt`-style acknowledged list — an
> allowlist that must keep matching is a control; 7 justifications to write.

**Verdict: the control lands, and the filed design would have made things worse.**
Four of the seven are not headers — they are the instrument. Writing the seven
justifications as filed would have frozen a rule defect into an allowlist that
"must keep matching", making the defect permanent and load-bearing. The rule fix
comes first; the acknowledged list is then **3** entries, not 7.

---

## 0. The question

Not *"is check 3 advisory?"* — that is a property of the tooling, and
[[correct-claim-can-be-the-wrong-question]] says such properties are usually true
and usually decide nothing. It is true here: check 3's findings are printed and
discarded, `advisory_total` never reaches the `return 1`.

Three questions that do decide something:

**Q1 — Would an acknowledged list have caught anything, ever?** Walk check 3 over
every commit and get the real series of `(file, header name)` sets. If the set has
never moved, the list catches nothing and the honest answer is a decline. §2.1.

**Q2 — Are they even the right 7?** Measure the denominator: how many section
headers exist, how many each exemption clause removes, and does any exemption — or
any magic number — swallow a header that names real derived behaviour? §1, §2.2.

**Q3 — What would promotion to GATING cost?** Measured, not argued. §2.4.

And the question none of the three asks, which is the one that changed the design:
**what fails if check 3 itself goes blind, and does anything notice?** §2.3.

---

## 1. The denominator

### 1.1 Section headers in the scanned corpus

Check 3 runs only for the `disk` target (`INLINE_CITE_TARGETS = {"disk"}`), over
`disk/*.asm` + `disk/*.inc` — 8 files, 6 of which carry section headers. At
`0e66408`:

| classification | headers | what decided it |
|---|---:|---|
| cited **on the header line** | 28 | `CITATION` matched the `; --- … ---` line |
| cited **in the block below** | 16 | `CITATION` within `SECTION_CITE_LOOKAHEAD = 6` |
| **structural**, exempt | 5 | `STRUCTURAL_HDR` |
| **`[REVIEW]`** | **7** | neither |
| named nothing (bare rule) | 0 | — |
| **total** | **56** | |

### 1.2 The convention is disk-only, and that scoping is measured, not assumed

D-CITEJUDGE found check 1's scan list silently excluding `sub/` because the
directory was created after the list was written ([[readout-blind-to-its-own-subject]]).
Check 3's exclusion is the opposite case — deliberate, documented in the tool's own
docstring, and it holds up when measured. Running the same rule over the other
targets:

| target | files | headers | would be `[REVIEW]` |
|---|---:|---:|---:|
| disk | 8 | 56 | 7 |
| basic | 70 | 431 | **230** |
| sub | 37 | 299 | **118** |
| tape | 1 | 25 | 0 (all 25 are bare rules) |

`basic/` and `sub/` use `; --- name ---` as a **section divider**, not a citation
carrier; they cite per-feature in `PROVENANCE.md`. Widening check 3 to them would
produce **348** advisory findings against 7. The scoping is correct and now has a
number behind it.

### 1.3 Files this slice ADDS, checked against the sweep's own filter

⚠️ D-DOCJUDGE and D-BYTEJUDGE both mispredicted the swept-file count by forgetting
their own deliverables — the second one after writing the warning into its own §1.1.
Enumerated here, by extension, against `SWEEP_EXTS = (".md", ".asm", ".inc", ".py",
".tcl", ".txt", ".bas", ".yml")`:

| file | ext | in `SWEEP_EXTS`? |
|---|---|---|
| `docs/spec-audit-citations-review.md` (this file) | `.md` | **yes** |
| `tools/citations-advisory-allow.txt` | `.txt` | **yes** |

Everything else this slice touches is a **modification**, not an addition:
`tools/audit_citations.py`, `TODO.md`, `docs/clean-room-audit.md`,
`docs/spec-audit-citations-gate.md`. No Makefile change — `audit-citations` is
already a step of `basic-reloc` (D-CITEJUDGE).

⇒ swept files **694 → 696**.

---

## 2. Falsify by measuring

### 2.1 Q1 — walk check 3 over all 980 commits

House method: `git ls-tree -r` + `git cat-file --batch` with a blob cache, today's
rule over each commit's own tree (a fixed rule over a varying subject is the right
instrument for *"has the set moved?"*). The walker was cross-checked against the
shipped tool at `0e66408` — same 7 findings, same files, same names, same lines —
before being trusted.

**980 commits, 10 transitions.** Every one of them falls in `#58`–`#362`
(2026-06-20 → 2026-07-01), the Tier-2 disk build-out:

| # | commit | date | event |
|---:|---|---|---|
| 58 | `d4474aa` | 06-20 | **+** `disk.asm` `'INIT'` |
| 62 | `7510cd7` | 06-21 | **+** `disk.asm` `'write path'` |
| 228 | `5b225cf` | 06-24 | **+** `disk.asm` `'contract bodies …'` |
| 229 | `43d3b69` | 06-24 | *rename only* — the header's own text edited |
| 273 | `ce93452` | 06-25 | **+** `'conout_body …'`, **+** `'shared page-0 … helpers'` |
| 274 | `c51083c` | 06-25 | *move only* — `disk.asm` split into parts, 5 members re-pathed |
| 306 | `164b857` | 06-27 | **+** `runtime.asm` `'dos_handoff …'` |
| 320 | `b3c04fd` | 06-27 | **+** `kernel.asm` `'_GDATE entry …'` |
| 323 | `2ba38dc` | 06-30 | **−** `'conout_body …'` (the M10 fix gave it a citation) |
| 362 | `5225a29` | 07-01 | **+** `kernel.asm` `'SETDTA-time entry …'` |

**Since `5225a29` the set has not moved once: 617 commits.** The filed *"575
commits"* is not wrong so much as measured from the wrong datum — it counts from
the 2026-07-04 triage, three days *after* the set stopped moving.

And the reason it stopped: **`disk/*.asm` and `disk/*.inc` have not been touched in
300 commits.** Last edit `90fc1d1`, 2026-07-09. 30 commits touched them in the last
600; 0 in the last 300. Tier-2 is a concluded arc. The subject is frozen.

⇒ **Q1's answer has two halves.** An acknowledged list installed at the beginning
would have fired 9 times. Installed at the 2026-07-04 triage it would have fired
**0 times in 578 commits**, over a tree nobody edits. *Recall alone does not
justify the list.* §2.3 is what does.

### 2.2 🔴 Q2 — four of the seven are the instrument, not the tree

`SECTION_CITE_LOOKAHEAD = 6` is the same magic number as D-CITEJUDGE's
`HEADER_BLOCK_LINES = 45`, in the same file, one check over. Sweep it:

| lookahead | `[REVIEW]` |
|---:|---:|
| **6** (shipped) | **7** |
| 8 | 6 |
| 10 | 4 |
| 12 | 3 |
| 15 … 200 | **3** |

It converges at 12 and never moves again, because the scan already stops at the
first code line. The distribution of where the citation actually sits, over the
headers that have one below them:

```
offsets: 1 2 3 3 3 3 3 4 4 4 4 4 5 5 5 6 | 7 10 10 11
                                    cap ^
```

The cap lands one line above a real citation. The four it cuts off:

| header | citation | offset |
|---|---|---:|
| `disk/init.asm:51` `'INIT'` | `disk/docs/expansion-protocol.md §4a/§5` | **7** |
| `disk/runtime.asm:8` `'shared page-0 … helpers'` | `documented MSX BIOS ABI (MSX2 TH ch.2/2.4)` | **10** |
| `disk/runtime.asm:539` `'dos_handoff …'` | `(tier2-f338-default-spec.md)` | **10** |
| `disk/kernel.asm:441` `'_GDATE entry …'` | `See docs/tier2-gdate-spec.md.` | **11** |

All four are real document references, in the header's own uninterrupted comment
block, before any code. **They are compliant sections that the rule cannot reach.**

The three that survive are genuine review candidates:

| header | why |
|---|---|
| `disk/driver.asm:87` `'write path'` | 3 comment lines, no citation, then code. Leans on its read-path twin, whose header does cite. |
| `disk/kernel.asm:65` `'SETDTA-time entry: $5058 (M19)'` | 12 comment lines naming finding, probes and method — but in vocabulary `CITATION` does not carry. See §2.5. |
| `disk/kernel.asm:2052` `'contract bodies (stubs …)'` | code on the very next line; a stub table with no provenance to cite. |

**Re-walking the fixed rule over all 980 commits** ([[a-rule-for-two-corpora-must-be-knifed-in-both]]:
when a knife changes the rule, restate every number predicted from the old one):

| | magic 6 | comment block |
|---|---:|---:|
| transitions | 10 | **7** |
| additions of a new uncited header | 8 | **4** |
| removals | 1 | 1 |
| pure churn (rename / file split) | 2 | 2 |
| set size at `0e66408` | 7 | **3** |
| commits with a non-empty set | 922 | 918 |
| set stable since | `5225a29` (617) | `5225a29` (617) |

⇒ **half of everything check 3 has ever reported was the instrument.** Precision
over its whole life: 4 of 8 additions; 3 of 7 today.

### 2.3 🔴 The record says so already, in the human's own voice

`docs/clean-room-audit.md:493` records the 2026-07-04 triage:

> *"7 genuine advisory headers remain (structural headers **whose bodies carry full
> citations** — judged individually, all acceptable)."*

The human looked at each one, **saw the citation in the body**, and wrote that down
— and still called them genuine advisory headers, because the tool said 7 and
nothing invited the question *why is the tool reporting a header whose body carries
a full citation?*

It is sharper than that. The **same commit** fixed the other half of the same
defect. `4c14006`'s message:

> *"`audit_citations.py`'s `CITATION` regex recognised the old `spec-*.md` naming
> but not the current `tier2-*-spec.md` convention, **falsely flagging 4 headers
> that DO cite a spec inline**; added `-spec\.md`/`tier2-`."*

Both halves are one defect — **the rule not reaching the citation**, once by
vocabulary and once by distance. The 2×2 at `4c14006^`, the tree that pass was
looking at:

| | lookahead 6 | comment block |
|---|---:|---:|
| **pre-`4c14006` regex** | **11** | 7 |
| **post-`4c14006` regex** | **7** | **3** |

The pass walked 11 → 7 along the vocabulary axis, stopped, and triaged the
remainder. The distance axis was sitting in the next four lines of the same
function. `_GDATE` needed *both* fixes; `'shared page-0 … helpers'` needed only the
distance one and its citation had been reachable-in-principle since day one.

⇒ this is the ninth-plus instance of [[filed-justification-is-a-claim]] and the
second of the D-CITEJUDGE shape, in the same tool: **a magic line-count constant
manufacturing findings against compliant files, with the "fix" being prose written
into files that needed nothing.**

### 2.4 What actually fails if check 3 goes blind — and Q3's number

D-DSKJUDGE's conversion: not *"who reads this?"* but *"break it on purpose and see
what goes red."*

| cut | today | anything red? |
|---|---|---|
| delete check 3's loop entirely | 7 `[REVIEW]` lines and the `ADVISORY:` summary vanish | **no.** `rc 0`, `make basic-reloc` green |
| `INLINE_CITE_TARGETS = set()` | same | **no.** `rc 0` |
| break `SECTION_HDR` | same | **no.** `rc 0` |
| plant a new uncited header | it prints as advisory #8 | **no.** `rc 0` |

Check 3 is the only check in the tool with **no self-test** — checks 1, 5 and 6 all
have one (10/10, 11/11, 12/12), and `MIN_FILES` counts *files*, not headers scanned
(floor 6, and only 6 of the 8 disk files carry headers at all, so two could vanish
silently). Its green state is *"here are N things, all fine"*, a state that reads
identically whether the rule works or not — the
[[gate-whose-answer-is-an-error-passes-a-dead-subject]] shape, and it is why a
defect survived 617 commits and a deliberate human triage.

**Q3, measured.** Promotion to gating (findings return 1) without an allowlist
would have made `make basic-reloc` **red in 918 of 980 commits (93.7 %)** — the set
is non-empty from `7510cd7` onward. With an allowlist it *is* the design in §3,
differing only in the exit code. Gating also forces the tool to assert *"an uncited
header is a defect"*, a judgement `docs/clean-room-audit.md` reserves for a human
and the tool deliberately declines. **Promotion is declined; the set is pinned
instead.**

### 2.5 A declined widening, measured — `black-box`

`disk/kernel.asm:65` attests richly (*"Black-box contract (M19, callseq/capture/
callwatch causal pin, no stock CODE decoded)"*) in vocabulary `CITATION` does not
carry, though `oracle` — the same hop — is already in it. Adding `black[- ]?box`:

| `CITATION` | `[REVIEW]` (block rule) |
|---|---:|
| as shipped | 3 |
| `+ black[- ]?box` | 2 (`kernel.asm:65` only) |
| `+ black[- ]?box + CLEAN-ROOM` | 2 (no further effect) |

**Declined.** The §2.2 fix is an instrument correction — a document reference exists
and the rule cannot reach it, provable without touching a file. This is a
*judgement* about what counts as a citation, which is exactly what check 3 declines
to make; and `CLEAN-ROOM` in particular is check 2's per-file attestation token,
so carrying it here would exempt every header in every attested file. The 2026-07-04
triage looked at this header and kept it as a review candidate. It stays one, now
acknowledged with that reasoning written down.

**Re-open bar:** a widening that leaves the other two survivors flagged, scores 0
new exemptions across all 980 commits of the disk tree, and is argued from
`docs/clean-room-audit.md`'s chain definition rather than from this one header.

### 2.6 🔴 Found by a knife that did not cut: `CITATION` has no negation window

K3 plants a new uncited section header and expects `rc 2`. It came back **`rc 0`
twice**. Before concluding anything about the design —
[[knife-aimed-at-the-wrong-gate]] — check the knife CUT. It had not: the plant read

> `; --- freshly landed veneer with no provenance at all ---`

and **`PROVENANCE` is a `CITATION` token**. The plant exempted itself with a
sentence saying it had no provenance. Re-worded, K3 cuts cleanly and both runs
return `rc 2`.

That is a defect in the knife, but it names a real property of the rule: check 1
has a `NEGATION` window, **check 3 has none** — any occurrence of a citation token
exempts, in any polarity, in any sense. Measured over the 48 exempt headers, how
many rest on a *weak or negated* match rather than a document reference (`§`,
`spec-`, `tier2-`, `PROVENANCE`, a named handbook / datasheet / standard)?

| | count |
|---|---:|
| exempt headers | 48 |
| exempt on a **strong** citation | 45 |
| **exempt on a weak or negated token only** | **3** |

| header | the match | what it really is |
|---|---|---|
| `runtime.asm:197` `'const_body …'` | `oracle` in *"no oracle bytes"* | negated — but the line also names *"published CONST contract (map.grauw.nl)"* |
| `runtime.asm:222` `'conin_body …'` | `oracle` in *"no oracle bytes"* | negated — block names *"the published BDOS $01 CONIN contract"*, `map.grauw.nl` |
| `runtime.asm:423` `'int_h_body …'` | `VDP` in *"a bare VDP ack is not enough"* | ordinary prose — block names *"the MSX1 standard, BIOS-agnostic"* |

⇒ the mechanism is real; **the class has 0 substantive members today.** All three
name a public source or a standard, so all three *should* be exempt — they are
simply exempt for the wrong reason, and `map.grauw.nl`, the public artifact two of
them actually cite, is not in `CITATION`'s vocabulary at all.

> ✅ **CLOSED 2026-08-06 by D-NEGJUDGE — the negation window is DECLINED and the
> table above is wrong on one row.**
> [`docs/spec-audit-citations-negation.md`](spec-audit-citations-negation.md).
> Walked over all **981** commits: a 3-line negation window adds **38** findings
> the shipped rule does not make and **0 of the 38** lack a document citation
> (precision **0**), while disagreeing with the shipped rule in **760** commits.
> It fails structurally — `CLEAN-ROOM` is a `NEGATION` token *and* the prefix of
> this project's citation convention, so the window discards the citation on every
> header in house style; and `\bno\b` matches inside `NO-OP`.
> 🔴 **The `runtime.asm:423` row above is wrong: that header is NOT substantively
> attested.** It names *"the MSX1 standard"* — a standard, not a document — and had
> been exempt on the word `VDP` in ordinary prose for **708** commits. It is now
> the 4th acknowledged entry. The class had **1** real member, not 0, and the
> negation window **does not catch it** while flagging the two that should stay
> exempt. `map.grauw.nl` was measured: **0** changed verdicts in 981 commits.

**Not fixed here, and the reason is a measurement, not fatigue.** Adding
`map.grauw.nl` would change no count in this tree — a rule with no observable
effect is [[gate-can-be-green-while-measuring-nothing]]. Adding a negation window
is a real rule change whose effect is to **grow** the acknowledged list, so it
needs its own falsification and its own justifications. Filed in `TODO.md` with
that bar. It also means the acknowledged list of 3 is honestly a **lower bound**.

---

## 3. Design

Three changes to `tools/audit_citations.py`, in this order — the order matters,
because landing the list first is what would have frozen the defect.

### 3.1 The rule: the header's own comment BLOCK, not a magic 6

Replace `SECTION_CITE_LOOKAHEAD` with a scan of every line under the header until
the first of:

* a **code** line (non-comment, non-blank) — already the shipped behaviour;
* the **next section header** — new, so a header can never borrow the citation of
  the section below it;
* end of file.

Blank lines do not break the block (a `;` header block is routinely broken by bare
`;` and by empty lines). The longest block this traverses in the tree today is 12
lines, so the scan is bounded in practice by the code that follows, not by a
constant.

The loop moves into a module-level `section_findings(lines)` so the self-test, the
sweep and any future walker all exercise the same code path — the
`listing_runs()` pattern check 5 already uses.

**Effect: advisory 7 → 3, with no `.asm` file edited.** Same shape as D-CITEJUDGE's
`HEADER_BLOCK_LINES` fix, which removed 9 of 24 findings the same way.

### 3.2 The self-test — the control check 3 has never had

Synthetic vectors, one per shape, exercised through `section_findings()` and
returning **2** on any misclassification, beside the other three self-tests.

⚠️ [[a-selftest-vector-can-be-the-forbidden-artifact]] does **not** bind here:
check 3 refuses a *property* (no citation present), not a *kind of text*, so a
positive vector is a header with no citation — which forbids nothing and can be
written down safely. Synthetic is still the right call, because pinning real tree
text would make the vectors rot with every comment edit, and because one vector per
*shape* is cheaper than one per instance.

| # | vector | expect |
|---:|---|---|
| 1 | cite at offset 1 | cited |
| 2 | cite at offset 6 — the old cap's boundary | cited |
| 3 | **cite at offset 7** — the class the old rule missed | cited |
| 4 | **cite at offset 11** — the deepest real case in the tree | cited |
| 5 | blank + bare-`;` lines then a cite at offset 5 | cited |
| 6 | cite on the header line itself | cited |
| 7 | structural header (`ROM skeleton`), no cite anywhere | cited (exempt) |
| 8 | 3 comment lines, no cite, then code | **REVIEW** |
| 9 | code on the very next line | **REVIEW** |
| 10 | next header carries the cite — must not borrow it | **REVIEW** |
| 11 | bare rule `; ------------` (names nothing) | ignored |
| 12 | an ordinary comment line, not a header | ignored |

Vectors 3 and 4 are this slice's regression pin: they are the exact class
`SECTION_CITE_LOOKAHEAD = 6` could not see.

### 3.3 The acknowledged list — `tools/citations-advisory-allow.txt`

Same format and same loader as `citations-listing-allow.txt` /
`citations-dump-allow.txt`: `<path> <digest> <reason>`, a missing reason is a parse
error. Digest = `sha256(f"{path}|{header name}")[:12]` — anchored on the name, never
a line number, because line numbers rot and a path-level entry would blind a whole
file to a second header.

Both directions are checked, and **both exit 2**:

* an entry **no longer produced** → stale, or the rule went blind;
* a finding **not acknowledged** → the advisory set no longer matches what was
  triaged.

Exit **2**, not 1, on purpose: check 3 makes no judgement about whether an uncited
header is a defect, so it cannot claim *"the tree regressed"*. What it can claim is
*"nothing below this was measured against a current triage"* — which is what 2
means everywhere else in this tool.

⚠️ D-BYTEJUDGE's **K3b** found that deleting check 6's allowlist **file** degrades
to `rc 1`, not 2, because a missing file reads as "no entries" and the canary
becomes an ordinary unallowlisted finding. That cannot happen here **because both
directions are checked**: with the file gone, all 3 findings are unacknowledged and
the unacknowledged rule returns 2. Predicted explicitly in §5 (K1c).

**Three entries, not seven.** Each is a real judgement about a real gap:

| header | acknowledged because |
|---|---|
| `driver.asm:87` `'write path'` | the write twin of `dskio_read`; the read path's header carries the `PROVENANCE.md §FDC / §DSKIO` citation both rest on |
| `kernel.asm:65` `'SETDTA-time entry: $5058 (M19)'` | attested by finding + probes + method in vocabulary `CITATION` does not carry; widening measured and declined, §2.5 |
| `kernel.asm:2052` `'contract bodies (stubs …)'` | a `ret` stub table; no derived behaviour, so no provenance to cite |

### 3.4 Two independent controls, and only removing both is silent

* the **self-test** proves the rule still classifies correctly — but it passes
  N/N even if the rule is never applied to the tree (`INLINE_CITE_TARGETS = set()`);
* the **acknowledged list** proves the rule is still being applied to the real
  subject — but it says nothing about text the rule has never seen.

Neither subsumes the other. §5 knifes each alone (both must be loud) and both
together (the only silent state) — the structure D-DOCJUDGE established and
D-BYTEJUDGE confirmed.

### 3.5 The record

Per [[a-recommendation-in-the-record-is-still-a-claim]], the refutation is written
back into the documents that carry the claim: `docs/clean-room-audit.md:493`
(the *"7 genuine advisory headers"* triage) and
`docs/spec-audit-citations-gate.md` §2.5 (*"the same 7 headers … advisory is the
right call and stays"*, measured at two endpoints rather than walked).

---

## 4. Predicted GREEN, at exact values

Written before any change is made. From clean (`rm -rf build` first).

**`make audit-citations`, exit 0:**

| reading | predicted |
|---|---|
| per-target files | 8 / 107 / 1 |
| provenance-bearing | 97 / 181 / 15 |
| rule self-test | 10/10 |
| listing self-test | 11/11 |
| dump self-test | 12/12 |
| **section self-test** | **12/12** |
| **advisory `[REVIEW]`** | **3, all acknowledged** |
| listing sweep | **696** files, 2 allowlisted |
| dump sweep | **696** files, 1 allowlisted |
| gating findings | 0 |

**ROM-neutral — this slice touches no `.asm`, so all four images must be
byte-identical to `0e66408`:**

| image | sha256 |
|---|---|
| `build/disk.rom` | `2c630d3dfeec727b5ec87c3c3140cfa5fdedc6b6a144d346467e6142b6e33c27` |
| `build/sub.rom` | `b2935188963eda429d61fc6ded6350a8067f1ccc09b5d4a9edc4713da2697e5e` |
| `build/basic-reloc.rom` | `3f1cd5866314270e3ae325b56f8707e62f26b7d65210f1c1d64510b7c48594af` |
| `build/zerobas-main-eu.rom` | `d061cd58ad4cede795221fef1c0b0c9ae2c0d0c7a090f6a2b8fcef1154d9e28e` |

**Walls:** low **23 B**, page 1 **356 B**, sub p0 **3869 B**, sub p1 **2324 B**.
**Closure:** abi 122+4, `--page0` 718+15, `--page1` 522+41. **kwtable** 1041 B.

**Dead code: main 1551 spans / 285 seeds → 0; sub 1451 / 102 → 0 (+1 allowlisted).**
⚠️ This slice writes prose into `tools/audit_citations.py`, a `check_dead_code.py`
`external_names` root that is read *including comments*. The new
`tools/citations-advisory-allow.txt` is **not** read — `external_names` takes only
`.asm`/`.inc`/`.py`. Any movement in 285/102 is a finding about this slice's own
prose.

**Corpus: 19/19 green**, sequential, each log captured whole.

---

## 5. Predicted RED, with knives

Every knife run **twice**. Restore point is a scratchpad snapshot taken before the
first cut, never `git checkout --` ([[knife-cleanup-restores-from-head]]); the
runner refuses to start unless its subject is green, and is written in Python so
the zsh word-splitting trap ([[zsh-make-var-word-split]]) cannot apply.

| id | cut | predicted |
|---|---|---|
| **K0** | delete check 3's loop **at `0e66408`, before the change** | `rc 0`, "clean", 7 advisory lines gone, `basic-reloc` green — *the measurement that says check 3 has no control today* |
| **K0c** | control: restore | `rc 0`, 7 advisory |
| **K1a** | regress the rule to a 6-line cap | **`rc 2`** — section self-test misclassifies vectors 3 and 4 |
| **K1b** | K1a **+** delete vectors 3 and 4 | **`rc 2`** — self-test passes 10/10; 4 findings unacknowledged |
| **K1c** | K1b **+** delete the allowlist **file** | **`rc 2`** — 7 unacknowledged (⚠️ *not* K3b's `rc 1`: both directions are checked) |
| **K1d** | K1c **+** remove the acknowledged-set check | **`rc 0`, silent** — the only silent state, and it is today's behaviour |
| **K2** | `INLINE_CITE_TARGETS = set()` | **`rc 2`** — self-test still 12/12; 3 stale entries |
| **K2c** | control: restore | `rc 0` |
| **K3** | plant a new uncited section header in `disk/driver.asm` | **`rc 2`** — 1 unacknowledged |
| **K3c** | the same plant against the **pre-change** tool | **`rc 0`** — prints as advisory #8 and gates nothing |
| **K4** | give `driver.asm:87` a citation | **`rc 2`** — 1 stale entry |
| **K5** | break `SECTION_HDR` | **`rc 2`** — section self-test, vectors 1–10 |
| **K6** | drop the reason from an allowlist line | **`rc 2`** — parse error |
| **K7** | `make basic-reloc` with the tool red, **twice** | fails both times (PHONY, so re-running does not defeat it) |

K3/K3c is the pair that decides whether the change is load-bearing: same plant, two
tools, `rc 2` vs `rc 0`.

---

## 6. As-built

### 6.1 Predictions, scored

Every §4 value hit:

| reading | predicted | measured |
|---|---|---|
| per-target files / provenance-bearing | 8/107/1, 97/181/15 | **same** |
| rule / listing / dump self-test | 10/10, 11/11, 12/12 | **same** |
| **section self-test** | 12/12 | **12/12** |
| **advisory** | 3, all acknowledged | **3, all acknowledged** |
| **files swept** | **696** | **696** |
| walls low / p1 / sub p0 / sub p1 | 23 / 356 / 3869 / 2324 | **same** |
| closure abi / p0 / p1 | 122+4 / 718+15 / 522+41 | **same** |
| dead code main / sub | 1551·285→0 / 1451·102→0 (+1) | **same** |
| kwtable | 1041 B | **same** |
| all four ROM sha256 | unchanged from `0e66408` | **unchanged** |

**ROM-neutral, proved by hash.** This slice touches no `.asm`; `disk.rom`,
`sub.rom`, `basic-reloc.rom` and `zerobas-main-eu.rom` are byte-identical to
`0e66408`.

**Dead-code seeds did not move (285 / 102)** despite ~150 lines of new prose in
`tools/audit_citations.py`, an `external_names` root read including comments. The
new `tools/citations-advisory-allow.txt` is invisible to that sweep by extension —
predicted in §4 and confirmed.

One incidental confirmation that the digest anchoring works: check 6's allowlisted
canary moved from `tools/audit_citations.py:421` to `:428` as this slice's
insertions pushed it down, and matched anyway — the entry is anchored on content,
not on a line number.

### 6.2 Knives — 13 rows, each run twice, 26 runs

All as predicted **after one knife was corrected** (§2.6). Highlights:

* **K0 / K0c** — deleting check 3 outright from the pre-change tool: `rc 0`,
  advisory **0**, `basic-reloc` green. The control leaves advisory **7**, also
  `rc 0`. *This is the measurement that says check 3 had no control at all.*
* **K3c / K3** — the decisive pair. The same planted uncited header gives
  **`rc 0`, advisory 8** on the pre-change tool and **`rc 2`** on the new one.
  That is the filed risk, reproduced and then closed.
* **K1c** — deleting the allowlist **file** gives **`rc 2`**, not D-BYTEJUDGE's
  `rc 1`, because both directions are checked. Predicted correctly this time.
* **K1d** — self-test vectors gone *and* the acknowledged-set check gone is the
  **only** silent state (`rc 0`, "clean"). Neither control alone is silent:
  K1b (list only) and K2 (self-test only, `INLINE_CITE_TARGETS` emptied) both
  exit 2. §3.4's independence claim holds.
* **K7** — `make basic-reloc` fails **both** times with the tool red; PHONY, so
  re-running does not defeat it.

🔴 **The one miss was mine, and it found something.** K3's first plant read
*"with no provenance at all"* and came back green twice — it had not cut, because
`PROVENANCE` is a `CITATION` token and the plant exempted itself. Checking the cut
before believing the reading ([[knife-aimed-at-the-wrong-gate]]) turned a
false green into §2.6's measurement and a filed residual.

### 6.3 Corpus — 19/19, sequential, each log captured whole

`basic-reloc` · `repack-machine` · `unit-test` (**58** files) · `audit-citations`
(rc 0) · `preflight-check` · `injector-check` · `latch-check` · `dexp5-pin` ·
`linemax-acceptance` · `lnblank-acceptance REPEAT=2` · `subrom-acceptance` ·
`subrom-inttest` · `graphics-floor-acceptance` · `graphics-acceptance` · `probe` ·
`fat-error-acceptance` · `diskbasic-acceptance` (**34/34** verbs converged) ·
`bdos-acceptance` (**12/12** gated differentials, 1 screen skipped) ·
`lof-acceptance` (**45 cases, 0 unfiled divergence, 0 oracle drift, 0 mangled**).

⚠️ **`lof-acceptance` sighting 3 has now failed to occur in EIGHT consecutive
slices.** Whole log captured (`> file 2>&1`, 59 lines), not tailed.

⚠️ One process note worth carrying: the first launch of the historical walk
crashed on a missing `git` argv[0] and the wrapper **reported exit 0**, because
the command ended in `; echo "rc=$?"`. Same family as
[[deadcode-gate]]'s *"a pipeline's exit code is the last command's"* — the status
read must be the status of the thing being measured.

### 6.4 What this slice did NOT do

* **Did not widen `CITATION` with `black-box`** — measured (§2.5), 3 → 2, and
  declined as a judgement the tool does not make. Re-open bar written.
* **Did not add a negation window to check 3** — measured (§2.6), 3 of 48
  exemptions rest on a weak or negated token, all 3 substantively attested, so the
  class has 0 real members. Filed in `TODO.md`; its effect is to *grow* the
  acknowledged list, so it needs its own falsification.
* **Did not promote check 3 to gating** — measured (§2.4): red in 918 of 980
  commits, and it would force a judgement `docs/clean-room-audit.md` reserves for a
  human.
* **Did not widen check 3 beyond `disk`** — measured (§1.2): 348 findings against
  disk's 3, because `basic`/`sub` use the same syntax for a different purpose.
* **Did not re-triage the three survivors.** Their acknowledgements record the
  2026-07-04 human judgement and the reasoning behind it; the tool still does not
  claim any of them is a defect.
