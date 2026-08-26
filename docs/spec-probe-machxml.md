<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-MACHXML — the machine config was published by TRUNCATING it, and 112 targets read it

Status: **✅ FIXED.** 2026-08-26, on `26e1d7e`. One-line publish change in
`tools/install-repack-machine.py`, no ROM byte moved.

---

## 1. It named itself, which is the whole point of the 2026-08-25 work

The D-ONLIST battery went 38/38 with one *"recovered flake (green on serial
retry)"* on `error-trap-acceptance`. The row was:

    FAIL  ERROR      1 -> zb ERR None ref ERR '1'

`ERR None` is a **missing capture**, not a wrong answer, and
`omsx_repl._why_missing()` spent the evidence the run already held
(the battery's own `error-trap-acceptance` log — `scratchpad/gate_logs/` is a
per-run directory `run_gates.py` deletes at the start of every battery, so the
quoted text below is the record, not the file):

> *openMSX terminated ON ITS OWN (exit 1) after 0s wall, before its scheduled
> capture; the run wrote 0 line(s). emulator said: Fatal error: …Loading of
> hardware configuration failed: `C-BIOS_MSX1_EU_REPACK_DISK.xml`: Document
> doesn't contain mandatory root Element*

🎯 **BEFORE THAT WORK THIS ROW PRINTED A BARE `<NO CAPTURE>`, THE RUNNER RETRIED
IT INTO GREEN, AND IT WAS A FLAKE FOREVER.** `docs/spec-probe-omsx-settings.md`
closed with *"NOT 'the flake is solved' — 'this flake is'. Another cause would
now NAME ITSELF instead of printing nothing, which is the durable part."* This
is that sentence being cashed.

---

## 2. The mechanism, read from the source

`tools/install-repack-machine.py` published with:

```python
open(out, "w").write(cfg)
```

`open(out, "w")` **truncates the moment it is called** and only then writes. For
the duration of that gap the shared path holds an **empty file** — and openMSX
reads its machine config at start, so an emulator launching inside the window
dies before executing one instruction.

**The exposure is not incidental: `repack-machine` is a prerequisite of 112
Makefile targets**, and `make gates` runs its units in parallel. Every unit can
re-publish the file every other unit is about to read.

⚠️ **THIS IS THE `settings.xml` RACE'S SIBLING ON A DIFFERENT FILE.** That one
was cured by giving each run its **own copy** via openMSX's `-setting`. **That
cure is unavailable here** — openMSX resolves a machine by NAME out of the
shared user tree, so there is no per-run copy to hand it. The other cure applies
instead: make the publish **atomic**, and the window stops existing.

---

## 3. 🔬 Falsified by driving the mechanism, not by counting flakes

`scratchpad/machxml_repro.py` — the shape `scratchpad/flake/repro.py`
established: **a flake count is not causal evidence.** Two arms, same readers and
writers, differing only in how the publish lands. 400 rounds × 3 writers ×
3 readers, **both arms against a copy under `/tmp/zerobas`** so the user's real
machine tree is never opened for writing.

| arm | publish | reads that saw a document that was NOT WHOLE |
|---|---|---|
| **SHARED** | `open(out,"w").write(cfg)` | **412 / 1200 (34.3 %)** |
| **ATOMIC** | sibling temp + `os.replace` | **0 / 1200** |

The red arm is the control that proves the apparatus can detect tearing at all;
without it a 0-vs-0 result would be the ALL-CONVERGED shape rather than a pass,
and the script **exits 2 and says so** if the shared arm ever comes back clean.

---

## 4. The fix

```python
tmp = f"{out}.{os.getpid()}.tmp"
with open(tmp, "w") as f:
    f.write(cfg); f.flush(); os.fsync(f.fileno())
os.replace(tmp, out)
```

`os.replace` is atomic on POSIX within a filesystem, and the temp sits in the
**same directory** so it always is one. The pid keeps two concurrent installers
from sharing a temp — they may both write, and whichever lands last wins with a
**whole** file, which is all any reader needs. Verified: `make repack-machine`
from clean publishes a file that parses, and leaves **no `.tmp` behind**.

---

## 5. The siblings — measured off the hot path, not assumed

`tools/install-openmsx-machine.py` has **five** writes of the same shape into the
same shared tree. They are **not** fixed here, and the reason is a measurement
rather than a judgement: they are reached only from `machines` /
`machines-oracle`, and the Makefile says of that target, in its own comment,
*"`machines` is the RELEASE-INSTALL path, **not a gate path**"*. Nothing runs
them 112-deep in parallel. Filed.

---

## 6. What this does NOT establish

* **It does not say this was the only cause of that battery's flake**, only that
  it was the cause of *that row on that run* — which the emulator itself stated.
* The repro's reader is `ElementTree`, not openMSX. The claim under test is
  about the **file**, and a parser is the honest detector for *"a reader saw a
  document that was not whole"*; it is not a claim about openMSX's parser.
* **No gate covers this.** A future non-atomic publish into the shared tree
  would reintroduce the window silently, and the only thing that would notice is
  another named `<NO CAPTURE>`. A checker is not proposed here; the residual is.
