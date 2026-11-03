# D-REFCACHE — do not re-measure a constant

*2026-08-28. `probes/lib/probe_refcache.py`, hooked into `omsx_repl.run_cases`.
Gate: `make refcache-check`.*

## 1. The measurement that motivated it

A differential probe reads three sides. Two of them — the Philips VG-8020 and
the National CF-3300 — are **fixed ROMs**: given the same typed lines they
return the same screen today and in a year. zerobas's side changes on every
build; the references do not change at all.

Measured on D-STRLONG's own 23-row matrix:

| side | cold |
|---|---|
| vg8020 | 14.5s |
| cf3300 | 19.8s |
| **zb** | **11.2s** |
| 3-side total | 45.6s |

**75 % of a differential run is re-measuring constants.** With the references
served from the store, a repeat inside a slice — where zerobas has been rebuilt
and the references have not — drops from **45.6s to 11.2s, 4.1×**. A repeat with
nothing rebuilt at all is **0.0s**.

⚠️ **THESE ARE SECONDS, NOT MINUTES.** When this was proposed the probe cost was
described as far larger than it is; the *fraction* was right and the absolute
size was not. The bigger absolute saving on a working day is D-GATESKIP
([`spec-gateskip.md`](spec-gateskip.md)), not this.

## 2. What is in the key

1. **The machine's actual bytes, not its name.** `machine_identity()` hashes the
   machine XML *and every ROM it references* — by content when the file is on
   disk, by the `<sha1>` the XML declares when openMSX resolves it from its own
   ROM database. 🎯 **This is what makes the cache safe for zerobas too, with no
   "is this a reference?" list for anyone to keep up to date**: zerobas's ROM
   hash moves on every build so its entries always miss, and if a rebuild is
   byte-identical then a hit is *correct*, not lucky. There is no judgement call
   anywhere in the design.
2. Every line typed, verbatim, including the reset and prologue sequences.
3. Every parameter that changes delivery or capture.
4. **A harness fingerprint** — the bytes of `omsx_repl.py` and `omsx_run.py`.
   Change how a line is delivered or a screen is scraped and every stored
   reading was taken by a *different instrument*.
   [[apparatus-is-part-of-the-measurement]]

## 3. Three rules that are not obvious

**ALL-OR-NOTHING PER CALL, NEVER PER CASE.** Under `batch=True` a whole matrix
shares one boot, so serving half of it from cache would change the batch
*composition* of the half that still runs. The harness has a `--boot-per-case`
escape hatch precisely because inter-case leakage is possible — so a composition
change could move an answer for a reason that has nothing to do with staleness,
and the disagreement would look exactly like a stale cache. Probes that already
run boot-per-case get full per-row caching from this rule for free.

**A NON-READING IS NEVER STORED.** `None`, empty, `<NO OUTPUT>`, `<NO CAPTURE>`
are apparatus faults. Storing one freezes a flake into an answer no rerun can
dislodge — the exact opposite of what the serial flake-retry exists to do.

**THE OUT-PARAMETER IS REPLAYED, NOT BYPASSED — and the first cut got this wrong
in a way that looked fine.** `settle_out` is a dict the *caller* reads
afterwards, so a hit that left it empty would make the caller's tally silently
under-count. The safe-looking answer was to bypass the cache for any call
carrying one. 🔴 **Then I counted: 23 of 23 rows of a typical differential probe
are marked.** That rule made the cache exactly **0 % useful** on the entire class
of probe it was built for — installed, green, and inert. The dict now
round-trips with int keys and tuples preserved exactly.

⚠️ **But a replayed provenance is not a measurement of this run.** Those values
are emulated-time instants — when the sentinel fired, or that it did not — and
they are how capture-on-signal is watched for health. A replayed dict carries
`replayed=True` and `probe_signal.Tally` reports it separately, so
*"1344 on signal, 1 fell back"* can never be a recording wearing a live run's
clothes. [[readout-blind-to-its-own-subject]]

## 4. Falsification — `make refcache-check`, 23 arms

Every way a wrong hit could happen, **planted** and shown to miss, each with a
green control beside it:

| arm | plants | requires |
|---|---|---|
| K0 | identical inputs | a HIT — the control that says the misses below mean something |
| K1/K2 | one character of a typed line; one extra line | MISS |
| K3 | each of five delivery parameters | MISS |
| K4 | **one byte of a ROM the machine names** | different identity (+ K4b: restoring it restores the identity) |
| K5 | a changed harness fingerprint | MISS |
| K6 | eight shapes of non-reading | refused (+ K6b: a real reading IS stored) |
| K7 | a settle dict with int keys and tuples | exact round trip |
| K8 | 24 concurrent writers | 0 torn reads |
| K9 | **a deliberate lie in the store, checked against a real machine** | `verify` catches it |

**K9 is the one that matters** — every other arm is arithmetic on keys. It boots
a real VG-8020, requires an actual agreement first (`verify_ok >= 1`, not merely
the absence of a mismatch — *"0 bad"* is also what a verify that never ran
reports), then tampers with the entry and requires the mismatch to be caught.

🔴 **K9 FAILED ON ITS FIRST RUN FOR A REASON WORTH RECORDING.** Run as
`__main__`, this file is *not* the module `omsx_repl` imports — Python binds a
second, independent `probe_refcache`. The selftest was setting `VERIFY` on one
instance while the wrapper read the other, and the arm reported "did not fire",
which would have read as *"the cache cannot be falsified"* when it was really
two copies of the instrument. The arms now bind the imported module explicitly.

## 5. Two more faults the first battery found in it

🔴 **THE FIRST FULL BATTERY UNDER THIS CACHE STORED 3132 ENTRIES AND NOT ONE
UNIT LOG SAID SO.** `report()` existed and nothing called it — a cache whose
hits are invisible is exactly what this module's header says must not exist: a
run that measured nothing reading like a run that measured everything. The
module now registers its own `atexit` reporter, so the chokepoint owns its
visibility the way it owns its key, rather than asking 200 callers to remember.

🔴 **AND THE TALLY WAS SILENT IN THE ONE RUN THAT NEEDED IT.** `summary()`'s
"anything to say?" guard listed `hit`/`miss`/`bypass`/`verify_bad` but not
`verify_ok` — so a `verify` battery in which every entry AGREED printed nothing,
and "no output" was indistinguishable from "verify never ran". The first verify
battery was briefly read as evidence on that silence. It was not evidence of
anything until the guard listed every counter.
[[an-unnamed-outcome-reads-as-no-outcome]]

## 6. 🔴 THE BATTERY MEASURES; IT NEVER REPLAYS

With a warm store, `make graphics-acceptance` on an unchanged tree serves all
315 rows from disk, **boots nothing, and prints `ALL PASS`.** A gate that agrees
because it was told the answer is the purest form of a case agreeing for the
wrong reason.

🎯 **I FOUND IT BY DOING IT TO MYSELF.** A bisect run "passed" without measuring
anything, and the ONLY thing that gave it away was probe_signal's
`⚠️ 321 REPLAYED from the refcache -- not measured on this run`. Without that
marker I would have recorded a false cause in this document.

So `tools/run_gates.py` forces `ZEROBAS_REFCACHE=0` for every unit and says so.
The two mechanisms get **disjoint jobs**: this cache is for ITERATING on a
slice, and D-GATESKIP ([`spec-gateskip.md`](spec-gateskip.md)) is what makes an
unchanged tree cheap for the battery — loudly, with the skip named in the
report. An explicit `ZEROBAS_REFCACHE=verify` is passed through, and caps
`--jobs` at 4: verify re-measures every row with no cache relief, and at J=8 the
tent-pole starved into the stall watchdog.
[[a-case-that-agrees-can-agree-for-the-wrong-reason]]

### 6.1 🟢 D-REFSONLY (2026-11-03): "References only"

Joost, asked whether batteries should use the cache: **"References only"**.
The finding above stands as written: what made `graphics-acceptance` pass
without measuring anything was replaying the **subject**. The VG-8020 and the
CF-3300 are fixed ROMs; replaying *them* replays a constant.

What changed:

- **`ZEROBAS_REFCACHE=refs`**, a new mode. A reference machine is served and
  stored exactly as in mode 1. A zerobas machine is **neither served nor
  stored** — it is booted and measured every time and counted as
  `zerobas reading(s) MEASURED`. Applied at both entry points (`run_cases` and
  `cached_run`), and in `basic_probe_kwram.py`, which keeps its own cache path.
- **"Zerobas" is decided by bytes first** (`probe_refcache.is_subject`): the
  machine XML names a ROM built in this repo, or a repo-built ROM is inserted
  (a cart). The `C-BIOS_MSX1_EU_REPACK*` name is a second check. When the two
  disagree, or the XML cannot be resolved, the machine is treated as **zerobas**:
  a wrong "subject" verdict costs a boot, while a wrong "reference" verdict
  would replay the build under test.
- **`tools/run_gates.py` forces `refs`** for every unit instead of `0`. An
  explicit `=verify` (still capped at `--jobs 4`) or `=0` from the environment
  passes through.
- **A hard stop, not a counter.** Every hit path calls `refuse_subject_hit()`,
  which raises if a zerobas reading is about to be served in `refs` mode. The
  tally line reads `REFS MODE (references replayed, zerobas measured), N
  REFERENCE reading(s) replayed, … M zerobas reading(s) MEASURED, 0 zerobas
  replayed`. probe_signal's marker now says `N REPLAYED … (N REFERENCE, 0
  zerobas)`.

**Why the guarantee still holds.** §6 promises that a battery measures the
subject, not that it boots the references. Every zerobas reading in a battery is
still taken live on that run. Selftest arms KS1–KS9 check this: KS5 shows a
zerobas launch is not served even when a matching entry exists, KS6 is the green
control (a reference launch *is* served), and KS9 does it end to end through
`run_cases` on the real `C-BIOS_MSX1_EU_REPACK_NODISK` with a lie planted under
its exact key. The 14-day expiry and `verify` remain the bound on a bad
*reference* reading.

## 7. A MISATTRIBUTION, RECORDED BECAUSE IT WAS NEARLY SHIPPED AS A FINDING

`graphics-acceptance` stalled three times while this slice was being validated.
`ZEROBAS_REFCACHE=0` still **imports** the module, so it was never a clean
attribution test; removing the module entirely made HEAD pass, and I concluded
*"this is my change, not the host"* — on **one run per side**. The correlation
looked clean across four runs and pointed at a one-line `atexit` reporter.

🔴 **IT WAS COINCIDENCE.** Re-running the supposedly-failing configuration
passed. All three stalls fell in one hour when the host load averages were
7.1–7.5; they stopped when it fell to 2.5. The stall watchdog's own message says
it: *a host-clock deadline cannot separate a frozen emulator from a starved
one.* n=1 per side is not an attribution, however clean the story looks.
[[stall-vs-slow]] [[an-unnamed-outcome-reads-as-no-outcome]]

## 8. Modes

    ZEROBAS_REFCACHE=1        (default) read + write
    ZEROBAS_REFCACHE=0        disabled entirely
    ZEROBAS_REFCACHE=verify   run everything for real, compare, fail on mismatch

⚠️ **THE STORE GROWS.** A single full battery stored **3132 entries / 17 MB**.
Nothing prunes it yet; `rm -rf ~/.cache/zerobas/refcache` is the whole recovery
procedure and costs one cold battery.

⚠️ **RUN `verify` PERIODICALLY.** A well-formed but *wrong* reference reading —
taken while the reference machine was misbehaving for some reason `storable()`
does not catch — would otherwise be frozen forever. The store's whole value is
that it is long-lived, which is also the only thing that makes it dangerous.

## 8. D-REFAGE (2026-08-29) — entries expire, and the store has a readout

The filed residual was *"the store grows and nothing prunes it"*, and it named
its own real complaint: **the hazard was never disk, it was staleness.** A
well-formed but **wrong** reference reading — taken while the reference machine
misbehaved in a way `storable()` does not catch — was frozen **forever**, because
nothing ever re-measured it and nothing scheduled `ZEROBAS_REFCACHE=verify`.
`rm -rf ~/.cache/zerobas/refcache` was the entire recovery procedure.

**An age cap does not detect a bad reading. It bounds how long one can survive**
— and that is what is claimed for it, no more. Past `MAX_AGE_DAYS` (14, override
with `ZEROBAS_REFCACHE_MAX_AGE_DAYS`; 0 disables) an entry reads as a **miss** and
is re-measured against the live machine. Self-healing, no scheduling, no operator
step.

⚠️ **Deliberately not a random re-verify sample.** A probe that re-measures a
different subset on every run makes its own wall-clock unpredictable, and this
cache exists to make repeats cheap.

🟢 **The expiry is NAMED in the tally, not folded into `miss`** — an expired entry
is a reading this run *deliberately refused to reuse*, which is a different fact
from never having had one. [[an-unnamed-outcome-reads-as-no-outcome]]

`make refcache-check` now also runs `--maintain`: it prunes past-cap entries and
prints the store. 🔴 **And that readout can go RED** — after a prune, no entry may
be past the cap; if one is, expiry is not doing what this section claims. A
readout that cannot fail is a print statement.

**Measured 2026-08-29: 5386 entries, 11.2 MB, oldest 0.7 d.** The filed figure
(*3132 entries / 17 MB*) had rotted in **both** directions — more entries, less
disk. Re-run `--maintain`; do not quote this line.

**Ten new arms (KA1–KA10)**, and two of them are the controls that matter: KA1
asserts a **fresh** entry is *not* expired (without it, every arm below would pass
on a store that simply never wrote), and KA9 asserts prune **keeps** a fresh entry
(a prune that deleted everything would pass KA8). KA10 checks the cap-0 escape
hatch actually disables expiry.

## 9. D-REFBYPASS (2026-11-03) — the probes that launch openMSX themselves

`run_cases` was never the only door. Thirty-odd probes build their own Tcl and
spawn openMSX directly (the trap probes, cloadverr, eofcas, keyshift, autorun,
bootkey, resetboot, ctrlkeys …), and `probes/lib/omsx_run.py` is a second
shared door that ten more probes (and the tape probes, and `z80probe`) use as a
subprocess. None of them cached, so every repeat re-booted the VG-8020 and the
CF-3300 for answers that cannot change.

`probe_refcache.cached_run(cmd, outs, run, *, inouts=(), media=(), ok=None)`
caches ONE launch. The caller keeps its own spawn — its `guarded()` Popen, its
watchdog, its kill signal — inside `run`; the cache never spawns anything. The
key (`direct_key`) is the machine's bytes, the argv and every `-script` text
with each per-run path replaced by a placeholder (`<OUTn>`, `<SCRIPTn>`,
`<MEDIAn>`), the sha256 of every input file — **auto-detected**, in argv and in
the Tcl text, so an undeclared tape still keys — the user's `settings.xml` and
`share/scripts/` (read, never written), every `-ext`'s XML, the binary's
identity, and `direct_fingerprint()` (the harness fingerprint plus
`probe_refcache.py` itself). A path that is not a file yet stays in the key
verbatim: an incomplete normalisation costs a **miss**, never a wrong hit.

Never cached (counted `bypassed`, with the reason in the tally): a Tcl that
reads the host — `clock …`, `rand()`, `after realtime`, `exec`, `glob`, `env()`
— or a directory passed as media. The three rules hold unchanged: every
declared output is stored and replayed together; an output that is missing,
empty or a non-reading is never stored, and `ok(value)` lets the caller veto a
watchdog kill; `verify` re-runs and compares byte for byte. Outputs are deleted
before a real run, so a stale file from an earlier call cannot be stored as
this run's reading, and the D-CACHEPRE staleness guard runs on the hit path.

🔴 **A repeat inside one process is a re-measurement.** stop-trap runs every
case `--trials 2` times and asserts the verdict is robust across both; the first
cut served trial 1 from trial 0's just-stored entry (run 1 on an EMPTY store
logged `16 hit, 16 miss`), so the second trial measured nothing. The n-th
identical launch of a process now gets its own key, so every stored reading was
measured once, separately, and a later process replays each trial from its own
measurement (arms KD12, KD12b).

omsx_run.py children report into their parent's tally through
`$ZEROBAS_REFCACHE_TALLY` (the first importer owns it), so a parent that
imports `probe_refcache` prints the children's hits. Selftest arms KD0–KD12b and
KD-R (the REPACK machines name every repo-built ROM by absolute, present path,
so zerobas's key moves with the build). When this section was written the
battery forced the cache OFF; §6.1 replaced that the same day. The battery now
runs `refs`, so the reference side of these launches is replayed there too, and
zerobas is still measured.
