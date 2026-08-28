# D-NGRAM2 — `req_operand`, one body for six open-coded copies

*2026-08-28. `basic/interp.asm`. Probe `scratchpad/ngram2_probe.py`, knives
`scratchpad/ngram2_knives.py`, ranking `scratchpad/ngram_sweep.py --main`.*

**Cost: −41 B of main page 1 (185 → 226 B free).** Low region unchanged.
**Rows: 18, DIFF 0/18** against both references.

## 1. The candidate, re-measured before it was taken

D-NGRAM filed this and it is still the top-ranked exact repeat in the *scarce*
regions:

    call skip_spaces / or a / jp z,loc_missing / cp COLON / jp z,loc_missing

12 B × 6 sites = 72 B. One 13 B body plus six 3 B calls = 31 B.

The six: LOCATE's argument positions (`missing.asm`), PLAY's voice slot
(`play.asm`), PRINT USING's format and its value list (`printusing.asm` ×2), and
SCREEN's mode and trailing arguments (`screen.asm` ×2).

🔬 **THE SITES WERE ENUMERATED AT INSTRUCTION LEVEL, AND A LINE-BASED GREP FINDS
ONLY FOUR OF SIX.** Four sites have comment lines *inside* the sequence, so an
adjacent-line regex misses them. The check that actually mattered was for an
**interior label** at any site — which would make the span byte-identical
without being *entered* the same way, the dup-span trap. There is none.

## 2. Falsification — and the hazard is not the one you would guess

The risk here is not "the helper is wrong". It is **"one of the six sites was
never rewired"** — a site left open-coded behaves identically, every row stays
green, and the saving silently comes up short. So there is at least one row per
SITE, and the knife's job is to move all of them.

| knife | predicted | measured |
|---|---|---|
| K-NG1 retarget the helper to `stmt_error` | all 11 subject rows move, 7 controls hold | **exactly that** |
| K-NG2 delete the `cp COLON` half | *(first prediction: all 6 colon rows)* | **2 rows** |

🔴 **K-NG2's FIRST PREDICTION WAS TOO WIDE, AND THAT IS THE FINDING.** Only
`PLAY:` and `PRINT USING:` move. At LOCATE and SCREEN the colon rows keep their
ERR 24 through a **second cause**: with the helper's COLON test gone they fall
through to the argument evaluation, and `eval` on a `:` defers ERR 24 of its own
(D-MISSOP, `ev_f_err`). So the helper's COLON half is the *sole* cause of the
verdict at 2 sites and a redundant-but-harmless first responder at the other 4.
That is what makes those four agreeing rows say **why** they agree.
[[a-case-that-agrees-can-agree-for-the-wrong-reason]]

## 3. 🔴 A KNIFE CAN BE SILENTLY INERT BECAUSE THE BUILD DID NOT HAPPEN

Running the knives twice on an unchanged tree gave **two different answers** —
K-NG2 moved 2 rows in one run and 11 in the other. The 11-row output was
byte-identical to K-NG1's: **the probe had measured the previous knife's ROM.**
Writing the source and immediately invoking `make` can leave the old ROM
installed, and the probe then reads the uncut machine — which reports as
*"moved 0 rows"*, i.e. exactly what a knife with nothing to say looks like.

Confirmed rather than assumed: builds ARE deterministic (three consecutive
builds byte-identical) and converge in one pass, so non-determinism is excluded;
and the hash the anomalous run reported as "clean" is K-NG1's ROM.

The runner now records the ROM hash **before and after** planting and refuses to
score a cut whose hash did not move, printing the transition. It also forces
`ZEROBAS_REFCACHE=0`: a knife measures, it never replays
([`spec-refcache.md`](spec-refcache.md) §6).

⚠️ **THIS IS A CLASS, NOT A ONE-OFF.** The repo has 14 knife runners and none of
them checks that its cut reached the machine. Filed.

## 4. The probe's own blind rows

The first cut of the row set used `SCREEN 1,` for the trailing-argument site.
Mode 1 leaves text mode, so the harness captured nothing and the row read
`<NO OUTPUT>` **on all three sides** — three blanks agreeing, scored `SAME`.
That would have left `screen.asm:140`, one of the six sites, with no witness at
all. The rows are mode 0 now, and the probe fails loudly on any row that is
blank on every side. [[an-unnamed-outcome-reads-as-no-outcome]]
