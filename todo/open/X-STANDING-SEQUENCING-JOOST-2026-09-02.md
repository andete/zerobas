- [ ] 🔁 **STANDING SEQUENCING (Joost, 2026-09-02): SPEED MATTERS AND WE SHOULD
      AT LEAST TRY — BUT CORRECTNESS COMES FIRST.** Answers the charter question
      D-INTERPSPEED raised (*does "faithful MSX1 BASIC" include speed?*): **yes**,
      and the 2.5–3.8× measured against the CF-3300 (the band was 2.5–3.1× until
      2026-09-04, when the missing seventh row was measured at 3.81×) is
      therefore a real defect
      and not an accepted property. **It is also NOT the next thing to work on.**
      🎯 **WHAT THIS RE-ORDERS.** Every open DIVERGENCE outranks every speed item.
      A row where zerobas answers differently from the reference is correctness;
      a row where it answers the same thing slower is not, and optimising code
      whose behaviour is still wrong means optimising code that will change.
      ⚠️ **SO THE Z80 REFERENCES ARE PARKED, NOT DECLINED**
      (<https://shiar.nl/calc/z80/optimize>,
      <https://www.smspower.org/Development/Z80ProgrammingTechniques>) — they sit
      on the D-INTERPSPEED item and stay unread until the correctness queue is
      down. Reading them now would invite spending page-1 bytes and review effort
      on the wrong axis.
      ➡️ **AND IT GIVES "DONE" A MEASURE**, which the file did not have before:
      correctness is reached when the open divergence set is EMPTY — the filed
      row sets (`scratchpad/filed_row_sweep.py`), `kwsweep`'s keyword
      denominator and `sysvarsweep`'s cell denominator all read clean, with no
      row parked as NO-ORACLE that a third reference could settle.
      🔴 **WHEN SPEED DOES COME UP, THE BASELINE IS NOT 1.0** — `PAINT`'s filed
      "1.9–2.0× slower" is measured against a zero that does not exist on this
      tree (D-INTERPSPEED §4), and any future speed row has the same problem.
      🙋→🤖 The charter half is ANSWERED; what remains under it is autonomous.
      🔁 STANDING — a ruling of Joost's, kept open so it stays visible. NOT
      pickable work; what it re-orders is marked on the items themselves.
      🔁 **SUPERSEDED IN PART 2026-09-10 BY THE PRIORITY TIERS** (🎚️ legend at the
      top of this section). *"Every open divergence outranks every speed item"*
      no longer holds as written: on-par speed (TIER 4) now outranks exhaustive
      error handling (TIER 5), and "reasonable time" (TIER 2) outranks common
      error handling (TIER 3). What survives unchanged: correctness of the HAPPY
      PATH (TIER 1) still outranks everything, the Z80 optimisation references
      stay parked until TIERS 1–3 are clean, and the speed baseline is still not
      1.0. "Done" is no longer "the divergence set is empty" — it is "every
      keyword is at TIER 4 or better".
      🎚️ STANDING — ruling, SUPERSEDED IN PART 2026-09-10 (see the tail of this block)
