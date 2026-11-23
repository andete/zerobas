- [ ] ⚠️ **`PLAY(n)` READ IMMEDIATELY AFTER `PLAY` SEES A REFERENCE TRANSIENT THAT
      zerobas DOES NOT REPRODUCE.** Filed 2026-08-28 by D-PLAYFN,
      [`docs/spec-basic-playfn.md`](../../docs/spec-basic-playfn.md).
      `10 PLAY"L1CDEFGAB" : 20 PRINT PLAY(0);PLAY(1);PLAY(2);PLAY(3)` with NO delay
      between the two lines gives **vg8020 `-1 -1 -1 0`** — voice 2 reading active
      although only one MML string was supplied — against zerobas's `-1 -1 0 0`.
      Insert ANY delay (a `CLS`, `FOR I=1 TO 200:NEXT`) and both sides agree
      exactly, on that row and on the voice-2 and voice-3 rows.
      🎯 So the reference marks something active during PLAY's own start-up window
      and zerobas settles instantly. **Unmeasured: what exactly, and for how long.**
      Reproducer varies ONLY the delay and prints both columns:
      [`scratchpad/playfn_fixture_probe.py`](../../scratchpad/playfn_fixture_probe.py).
      ⚠️ Whether it is worth reproducing is a real question — a BASIC program cannot
      easily observe a window a `CLS` closes — but it is a measured difference and
      the gate rows are written AROUND it (`SETTLE`), which is the kind of
      accommodation that should be visible rather than silent.
      ✅ **BOTH OPEN QUESTIONS MEASURED 2026-09-02 (D-PLAYWIN), AND THE FILED
      FRAMING IS WRONG IN TWO WAYS.**
      ⏱ **WIDTH: THE WINDOW CLOSES WITHIN ONE STATEMENT.** Not "a CLS suffices" —
      `FOR I=1 TO 1:NEXT` suffices, and so does every longer delay tried (5, 20,
      50, 200). So **no BASIC program that does anything at all between the `PLAY`
      and the read can observe it**; only a read on the very next statement can.
      🔴 **SHAPE: IT IS NOT "VOICE 2 IS MARKED", AND THE FILED ROW IS A SPECIAL
      CASE READ AS THE RULE.** Playing only voice 2 gives the reference
      `-1 -1 -1 0` and only voice 3 gives `-1 -1 0 -1` — in BOTH the extra voice
      is **VOICE 1**, not voice 2:

          supplied        reference (no delay)   settled
          v1 only         -1 -1 -1 0             -1 -1 0 0    extra: v2
          v2 only         -1 -1 -1 0             -1 0 -1 0    extra: v1
          v3 only         -1 -1 0 -1             -1 0 0 -1    extra: v1
          v1+v2           -1 -1 -1 0             (agrees)     extra: none
          v1+v2+v3        -1 -1 -1 -1            (agrees)     extra: none

      The one-string row this item was filed on is the ONLY case where the extra
      voice is v2. The precise rule is still unnamed — but it is not the one
      written above, and any fix aimed at "stop marking voice 2" would be aimed
      at the wrong thing. [[two-rules-that-coincide-on-every-row-you-have]]
      🔴 **AND ZEROBAS HAS A WINDOW TOO — the item says it "settles instantly"
      and that is false.** `PLAY""` reads `-1 0 0 0` on the reference and
      `-1 -1 0 0` here, and **both settle to `0 0 0 0`**. So this is not
      "reference has a transient, zerobas does not"; it is **two transients of
      different shape**, which is a different fix and a different risk.
      🟢 `no PLAY at all` reads `0 0 0 0` on both — the resting state is shared,
      so every row above is read against a real zero.
      🔬 **THE RULE, NAMED AT LAST (D-PLAYBACK, 2026-09-24,
      [`scratchpad/playmusicf_probe.py`](../../scratchpad/playmusicf_probe.py), two
      byte-identical runs, refcache OFF).** Read MUSICF (`PEEK(&HFB3F)`, a
      documented work-area cell) on the statement right after `PLAY`:
      | program | vg8020 `MUSICF PLAY(0)` | zerobas |
      |---|---|---|
      | `PLAY""` | **`7 -1`** | `0 0` |
      | `PLAY"L1C"` (one voice) | **`7 -1`** | `1 -1` |
      | no PLAY | `0 0` | `0 0` |
      🎯 **THE REFERENCE MARKS ALL THREE VOICES AT EVERY `PLAY`** — even for a
      string with no notes, even for one voice — and its interrupt then clears
      the idle ones over the next ticks; zerobas marks only the voices it was
      given. Every row in the table above fits *"all three marked, idle voices
      cleared highest-first"*: v1-only keeps v2 a moment longer than v3, v3-only
      keeps v1 longer than v2. ⚠️ That clearing ORDER is a candidate read off
      five rows, not a measured mechanism.
      🔴 **AND IT SHOWS D-PLAYEMPTY (2026-09-11) MOVED ZEROBAS THE OTHER WAY.**
      Its premise — *"the reference's MUSICF reads 0 right after `PLAY""`"*
      (gicini `m.empty`) — is a reading taken AFTER the reference's interrupt had
      already cleared all three bits; one statement earlier it reads 7. So the
      fix that dropped an empty voice from the commit mask made zerobas mark
      FEWER voices where the reference marks MORE. Both readings are points on
      one transient, which is why they could look contradictory.
      [[two-rules-that-coincide-on-every-row-you-have]]
      ➕ **`empty string, no delay` JOINS THIS ITEM'S PINNED ROWS** (Joost,
      2026-09-24) — the fourth member of the class, pinned at its measured face
      `ref -1 0 0 0` / `zb 0 0 0 0`.
      🎚️ TIER 6 — `PLAY(n)` transient
      🔁 **PARKED (Joost, 2026-09-10): every TIER 5 item waits until TIERS 1–4 are clean, and
      *"when we get to TIER 5, we'll have to do a prioritization together"* —
      the TIER 5 order is a joint pass, not the loop's pick.
      ~~🙋 **NEEDS-JOOST~~ — and the measurement argues for DECLINING.** The window is
      unobservable to any program that executes one statement first; the gate rows
      already accommodate it explicitly (`SETTLE`); and reproducing it means
      matching a transient whose rule is still unnamed, in `playsvc.asm`'s
      interrupt servicer. **Worth-it is the question, and it is yours** — the
      measuring the item asked for is done.
      🏗️ **RULED BY JOOST 2026-09-27 (his "ask me in detail" pass): DECLINE.** The start-up transient is not reproduced; a STATED
      DIVERGENCE, and the gate rows' `SETTLE` stays as the visible accommodation.
      🔁 **STANDING** — kept OPEN only so its two pins (`playfn_fixture_probe`,
      `playmusicf_probe`) stay cited and swept: a declined divergence with live
      pins is standing, not closed (closing it orphaned them — `filed-pin-check`).
