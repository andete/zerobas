# D-KNIFEROM — a knife that did not reach the ROM must say so

*2026-08-28. `scratchpad/knife_guard.py`, `tools/check_knife_guard.py`, gate
`make knife-guard-check`.*

## 1. 🔴 THE FILING THIS SLICE STARTED FROM WAS WRONG

Filed this morning by D-NGRAM2: *"none of the 14 knife runners checks that its
cut reached the machine"*. Run before building on it, as the standing rule
requires — and **it is wrong in both the count and the direction**:

| | filed | measured |
|---|---|---|
| runners lacking any ROM evidence | 13 of 14 | **5 of 41** |
| the convention | *"does not exist"* | **already established; 36 of 41 follow it** |

`circmiss_knives.py` is the canonical shape — a `hashes()` over the built images
*and* a `rm -rf build` so the rebuild cannot be skipped — and several specs
already distinguish *"the cut reached the artifact and reddened nothing"* (a
finding) from *"the cut never happened"*. One even records *"K-PM3 reddened
NOTHING, **with the ROM provably moved**"*.

🎯 **AND FOUR OF THE FIVE GAPS ARE RUNNERS I WROTE IN THE LAST 48 HOURS.** The
convention existed; I did not inherit it, and then filed its absence as a
project-wide defect. The real defect is narrower and more embarrassing: **there
was no gate, so a new runner could omit it and nobody would see.**

## 2. What shipped

- **`scratchpad/knife_guard.py`** — one implementation: `hashes()` over the four
  built images, `build(log, before)` returning `(moved, after, rc)`, and
  `report()` whose inert wording names the risk. 9 falsification arms.
  ⚠️ `moved(None, x)` is **False**: a caller that forgets a baseline gets no free
  pass, because the absence of evidence is not evidence.
- The five unguarded runners wired to it, and my two inline copies replaced, so
  there is **one** implementation of mine rather than three.
- **`make knife-guard-check`** — a knife runner must either import
  `knife_guard` or hash the images itself.

⚠️ **THE GATE POLICES THE PRESENCE OF EVIDENCE, NOT ITS CORRECT USE.** A runner
can hash and never compare; ten of the 41 appear to print rather than assert.
Reading whether all of them compare correctly is a separate audit, **filed
rather than claimed** — do not read this gate's green as *"every knife is
guarded"*.

## 3. The detector took three tries, and the middle one was the dangerous one

| rule | live result | verdict |
|---|---|---|
| "invokes `repack-machine`" | reddened `machxml_repro.py` | **false positive** — a race reproducer that rebuilds but cuts nothing |
| "…and matches a write-back shape" | 0 violations, **14 real runners silently excused** | **false negative — worse** |
| "…and cuts a `basic/`/`sub/` path, or is named `*knife*`" | 46 policed, 3 correctly excluded | ✅ |

🔴 **THE SECOND RULE WAS THE ONE TO BE FRIGHTENED OF.** It was green, and green
for the wrong reason: knife runners restore in at least four different ways
(`open(src,"w").write`, `p.write_text`, `src.write_text`, …), so keying on the
syntax that touches the file excused everything that touched it differently. A
false positive argues with you; a false negative does not.
**Key on the SUBJECT — what a knife cuts — not on the syntax.**

## 4. Falsification

`--selftest`, 5 arms, on planted fixtures: a runner importing the guard is green;
one hashing on its own is green; **one with no evidence is RED**; a file that
never builds is not policed; a file that builds but cuts nothing is not RED.

And against the **live tree**: stripping the guard from one real runner
(`strlong_knives.py`) turns the gate RED and names that file; restoring it
returns rc=0. A gate only ever run on a clean tree has never been shown to fire.

## 5. An instrument fault found while measuring the denominator

The first audit scored *"does it assert the ROM moved?"* with a regex over
before/after word pairs. It reported `strlong_knives.py` at **5 assertions**
when that file had **none** — matching unrelated prose. A readout blind to its
own subject, in the readout built to size this very slice. The factual column
(does the file contain `hashlib`/`getsize` at all) is what the numbers above
rest on. [[readout-blind-to-its-own-subject]]
