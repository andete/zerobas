# D-SCRAPEMODE — the harness diagnosed the fault three times and threw the diagnosis away

*2026-09-02. Guard in [`probes/lib/omsx_repl.py`](../probes/lib/omsx_repl.py); arms in
[`scratchpad/scrapemode_knives.py`](../scratchpad/scrapemode_knives.py).*

## 1. What happened

Adding `National_CF-3000` as a third reference (D-LSETREF) with the reset every
cassette machine in the tree uses — `("NEW",)` — returned `<NO OUTPUT>` on **all
seven rows, both controls included**, and **wrote seven refcache entries**.

A stock MSX1 boots **SCREEN 1**: 32 columns, name table at `$1800`. This module's
scrape assumes SCREEN 0 (`SCR_ADDR = 0x0000`, 40 columns) and its own comment
says so — *"a stock SCREEN-1 machine would need 0x1800/768/32 instead"*. The
CF-3300 side works only because its reset injects `SCREEN 0`. So what came back
from `$0000` was the **pattern generator table**: character bitmaps read as text.

Non-blank, so nothing refused it:

```
capture: '        ~B~B~B    T (D      4R      8T   (| 8T     |    ~BB~BB~ @~H<(~ ...'
```

## 2. 🔴 The diagnosis existed. It was discarded.

Re-running that exact call and printing what the echo oracle concluded:

```
verdicts: ['BLIND/mode', 'BLIND/mode', 'BLIND/mode']
mis_echoed (what the harness ACTS on): []
probe_refcache.storable() says: True
```

`BLIND/mode` is emitted when the oracle reads **SCRMOD out of the machine's own
RAM** and finds it non-zero — *"this scrape is not looking at the text plane"*.
The harness reached that conclusion **three times out of three** and then dropped
all three, because `mis_echoed()` counts only `MANGLED`:

> *"Only MANGLED counts -- a BLIND slot is a refusal to judge, not a finding, and
> treating it as one would re-run most of every suite."*

**That rule is right, and it is not the bug.** A blind *slot* genuinely is a
refusal to judge. But `BLIND/mode` is not a blind spot at all — it is a positive
reading, taken from the machine, that the instrument is aimed at the wrong plane.
Nothing downstream asked for it.

Two guards were each one layer from catching this:

1. `probe_refcache.storable()` refuses the string `<NO OUTPUT>` — but that is
   produced by each probe's `face()` *downstream*. The raw capture it inspects is
   garbage bytes, so its own header promise ("a non-reading is never stored")
   did not hold.
2. The echo oracle, above.

## 3. The guard

```python
def scrape_invalid(echo) -> str | None:
    """A one-line reason iff EVERY judged slot says the scrape was off-plane."""
    verdicts = [v for _, _, _, v, _ in echo]
    if len(verdicts) >= 2 and all(v == "BLIND/mode" for v in verdicts):
        return f"all {len(verdicts)} echo slots read BLIND/mode (SCRMOD != 0) ..."
    return None
```

⚠️ **THE PREDICATE IS `BLIND/mode` SPECIFICALLY, NOT "all blind".** A probe that
CLSes early legitimately produces `BLIND/rewrote` on every slot; refusing on that
would redden correct runs — the failure mode
[[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]] warns about,
where a guard fires on a good tree. Only the mode verdict says the instrument was
aimed wrong.

🎯 **IT REFUSES TO CACHE, NOT TO RUN.** The readings are still returned and
printed; only the *store* is skipped, with a stderr line naming the cause. An
early refusal is how 08-31 buried two real divergences, so the operator still
sees whatever the probe made of the garbage — it simply never becomes permanent.

## 4. Arms — red and green on the same apparatus

Same machine, same probe, **only `reset` differs**, and each arm is scored by
counting cache entries on disk rather than by reading the guard's own message
(which would be the readout agreeing with itself,
[[readout-blind-to-its-own-subject]]):

| arm | `reset` | cache entries | guard spoke | verdict |
|---|---|---|---|---|
| **RED** off-plane | `("NEW",)` | 0 → **0** | yes | ✅ refused |
| **GREEN** on-plane | `("", "SCREEN 0", "NEW")` | 0 → **1** | no | ✅ stored |

The green arm's capture is real text (` Ok … NEW … Ok`); the red arm's is the
pattern table. A guard that only ever refuses is not a guard, which is why the
green arm is half the measurement.

## 5. What is NOT fixed, named rather than implied

* **The scrape is still SCREEN-0-only.** This guard makes an off-plane run
  *refuse to cache*; it does not teach the module to read `$1800`/32 columns. A
  probe wanting a stock SCREEN-1 machine must still put it in SCREEN 0 via
  `reset`, as every disk-machine side already does.
* **`storable()` still tests the wrong layer** for every other way a capture can
  be junk. Only the off-plane case is covered.
* **13 knife runners still lack a ROM-hash guard** (unrelated, filed separately).
