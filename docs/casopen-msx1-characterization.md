<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-CASOPEN — how an MSX1 handles the NAME in `OPEN"CAS:name"`

Measured 2026-08-07 on the **Philips VG-8020** *and* the **National CF-3300**
against zerobas at `6a32356`, by
[`probes/basic/basic_probe_castail.py`](../probes/basic/basic_probe_castail.py)
(`make castail-characterize`). Spec: [spec-basic-casopen.md](spec-basic-casopen.md).

This is the reading the
[cassearch-msx1-characterization.md](cassearch-msx1-characterization.md) §5
residual was blocked on. That slice **found** the divergence — `OPEN"CAS:RT" FOR
INPUT` name-matches on both references and zerobas opens whatever file comes
next — pinned it on both halves, and filed it *without a byte count*, naming
three readings a fix would need and refusing to price the fix before it had
them.

## 0. 🔴 What the pinned row could NOT tell a fix, and what each answer decides

`cas2-open` / `cas2-open:echo` rest on **one** shape: a named `OPEN` on a
two-file tape, matching the second file. From that pair alone, three things a fix
must decide are unknown, and each of them can be got wrong in its own direction:

| # | question the pin could not answer | why it decides the fix |
|---|---|---|
| 1 | Does **bare** `OPEN"CAS:"` (no name) take the next file, as bare `LOAD"CAS:"` does? | A fix that arms name-matching must NOT arm it for the empty name. That arm reaches the match without ever entering the compare loop, so no named row can see it. |
| 2 | Is the compare **case-sensitive**, as it is for `LOAD`/`CLOAD`? | It decides whether the fix may reuse the existing byte-exact capture, or must fold case first. The two cost different amounts and produce different behaviour on `OPEN"CAS:rt"`. |
| 3 | What does **`FOR OUTPUT`** do with a name — is it already correct? | The two arms share one parse. A fix that changes where the name is captured passes through the OUTPUT arm whether it means to or not, and nothing in this tree had ever read what OUTPUT writes. |

Answers: **1 — yes, the next file, exactly like bare `LOAD"CAS:"`**;
**2 — CASE-SENSITIVE, and this is a THIRD face of the divergence that no
existing row could see**; **3 — already correct, on all three sides, named and
bare**.

## 1. The reading, all three sides

Fixtures: the existing two-file $EA ASCII tape (`SK` prints `ZQ8`, then `RT`
prints `ZQ9`) for the INPUT rows, and a fresh **recording** tape
(`cassetteplayer new`) for the OUTPUT rows.

| row | typed | VG-8020 | CF-3300 | zerobas @ `6a32356` |
|---|---|---|---|---|
| `cas2-openbare` | `OPEN"CAS:" FOR INPUT AS #1` | `Found:SK` | `Found:SK` | `Found:SK` |
| `cas2-openbare:echo` 🟢 | (`INPUT#1,A$` / `PRINT A$`) | `10 PRINT"ZQ8"` | `10 PRINT"ZQ8"` | `10 PRINT"ZQ8"` |
| `cas2-opencase` | `OPEN"CAS:rt" FOR INPUT AS #1` | `<load-failed>` | `<load-failed>` | **`<nothing>`** |
| `cas2-opencase:alive` 🟢 | (`PRINT"ZQ6"` after the Ctrl-STOP) | `ZQ6` | `ZQ6` | `ZQ6` |
| `cas-openout` | `OPEN"CAS:WX" FOR OUTPUT AS #1` | `<nothing>` | `<nothing>` | `<nothing>` |
| `cas-openout:alive` 🟢 | (`PRINT"ZQ6"` after the `CLOSE`) | `ZQ6` | `ZQ6` | `ZQ6` |
| `cas-openout:tape` 🟢 | *(the header name, decoded off the recording)* | `'WX    '` | `'WX    '` | `'WX    '` |
| `cas-openout:data` 🟢 | *(the text, decoded off the recording)* | `'ZQ7'` | `'ZQ7'` | `'ZQ7'` |
| `cas-openoutbare` | `OPEN"CAS:" FOR OUTPUT AS #1` | `<nothing>` | `<nothing>` | `<nothing>` |
| `cas-openoutbare:alive` 🟢 | (`PRINT"ZQ6"`) | `ZQ6` | `ZQ6` | `ZQ6` |
| `cas-openoutbare:tape` | *(the header name, decoded)* | `'      '` | `'      '` | `'      '` |
| `cas-openoutbare:data` 🟢 | *(the text, decoded)* | `'ZQ7'` | `'ZQ7'` | `'ZQ7'` |

🟢 = a **positive control**. `<load-failed>` is the one normalisation this
battery applies (`Device I/O error` on both references, zerobas's own lowercase
`load error` — the quarantined wording divergence, `basic/PROVENANCE.md`), and it
fires only when the tail is **exactly** that message.

**The two references agree on all twelve readings**, which is what promotes each
of them from "what a CF-3300 does" to "what an MSX1 does". The VG-8020 is a full
side here for the reason
[castail-msx1-characterization.md](castail-msx1-characterization.md) §0 gives:
every MSX1 has a cassette port.

## 2. R-CO1 — bare `OPEN"CAS:"` takes the NEXT file, and all three sides already agree

`Found:SK` and `10 PRINT"ZQ8"`: no compare happens, the first header on the tape
is taken. That is bare `LOAD"CAS:"`'s reading (`cas2-bare`) verbatim, on a
different verb.

**This row exists to say what a fix must NOT change.** It is the only row that
reaches the match arm without entering the compare loop, so a fix that armed
matching unconditionally — the obvious way to get `cas2-open` green — would break
it and no other row in the battery would notice. It is a **survivor** row, and
knife K-CO3 (spec §5) is what proves it can actually catch that mistake.

## 3. R-CO2 — the compare is CASE-SENSITIVE, and that is a THIRD face of the divergence

`OPEN"CAS:rt"` on a tape whose only candidate is `RT`:

* both references step over `SK`, step over `RT`, run off the end of the tape,
  wait on silence, and answer the operator's Ctrl-STOP with `Device I/O error`;
* zerobas answers **nothing at all**, because it opened `SK` — the name never
  reached the compare, so a name that could not match anything still opened a
  file.

So the byte-exact compare `CAS_WANT` already implements for `LOAD`/`CLOAD`
(CF-3300-confirmed, `docs/spec-cas-tier3-cload.md` A.5) is the **same** rule on
`OPEN`. A fix may therefore reuse the existing capture unchanged; it must not
add case folding, and it must not invent a looser compare for this one verb.

🔴 **The pinned row could not have found this.** `cas2-open` asks a name that
DOES match: it separates "matched the right file" from "took the next file", and
both a case-sensitive and a case-insensitive machine answer it identically. This
row is the only one that separates *compared and missed* from *never compared*,
and it is the reading that says the divergence is about **the name never reaching
the search**, not about which file the search picks.

⚠️ **It is read FILTERED, and that is what makes it scorable.** A machine that
compares and misses prints `Skip :SK / Skip :RT` **and then** its own aborted-load
message. Read unfiltered that tail is not *exactly* the message, the
`<load-failed>` normalisation would not fire, and the row would diverge on the
quarantined **wording** difference instead of on the question it asks. Filtered it
is a clean two-valued discriminator, and its `:alive` half is what says the
Ctrl-STOP returned to a working prompt rather than that the machine stopped
answering.

## 4. R-CO3 — `FOR OUTPUT` is ALREADY CORRECT, and the screen could never have said so

`OPEN"CAS:WX" FOR OUTPUT` prints nothing on any of the three sides — whether it
records the name, records six spaces, or records garbage. The screen is not a
witness here, so the reading is taken **off the tape the machine actually wrote**:
the row runs on a recording tape and
[`probes/lib/cas_decode.py`](../probes/lib/cas_decode.py) turns the WAV back into
bytes. The six bytes after the ten-byte `$EA` run **are** the header name field.

```
EA EA EA EA EA EA EA EA EA EA  57 58 20 20 20 20  5A 51 37 0D 0A 1A 1A …
└──────── the $EA ASCII id ────┘ └── 'WX    ' ──┘ └ 'ZQ7' CR LF ^Z … ┘
```

* **named** — `'WX    '`, space-padded to six, on all three sides;
* **bare** — `'      '`, six spaces, on all three sides.

So `FOR OUTPUT` is **not** part of this divergence, and this reading's job is to
say so *before* a fix touches the shared parse both arms run through. It is also
the OUTPUT arm's first positive evidence of any kind: until this row, nothing in
the tree read what a cassette OPEN writes.

Signal edges only — the decoder observes the recording, no reference ROM is
disassembled, and the same decoder runs on all three sides.

## 5. R-CO4 — what the answers TOGETHER say the defect is

The three answers agree on one story, and it is narrower than "OPEN ignores the
name":

* the name **is** parsed on the OPEN path (OUTPUT writes it into the header);
* the compare rule for cassette names is one rule, shared by five verbs, and it
  is byte-exact;
* the bare form is a separate arm and is already right on both verbs.

What is wrong is exactly one thing: **the parsed name is never handed to the
search on the INPUT arm.** That is a smaller claim than the residual made, and it
is what makes the fix a re-routing of an existing capture rather than a new
compare.

## 6. What is NOT claimed here

* **Whether the reference pads the name to 6 ON SCREEN** — still the non-claim
  [cassearch-msx1-characterization.md](cassearch-msx1-characterization.md) §6
  records. This slice measures padding **in the tape header**, which is a
  different artifact and is decidable: it is six bytes wide by the format.
* **What `OPEN"CAS:name" FOR OUTPUT` does when the name is longer than 6** — not
  measured; the existing capture truncates to six on every verb and no row here
  asks.
* **Whether a reference errors, or waits, when the named file is missing** —
  unchanged from
  [castail-msx1-characterization.md](castail-msx1-characterization.md): a missing
  tape file is not an error on an MSX1 at all, which is why `cas2-opencase` ends
  in a Ctrl-STOP rather than in a message the machine volunteered.
* **`APPEND` / `RANDOM` on a cassette channel** — refused by zerobas, unmeasured
  on the references, out of scope.
* **The wording of the failure message** stays the quarantined divergence,
  normalised per side in every row of the battery.
