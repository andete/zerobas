- [x] ✅ **`ev_f_err`'s OTHER SEVEN JUMP SITES — CLOSED 2026-08-26, D-EVFERR, at
      ZERO BYTES.** [`docs/spec-basic-evferr.md`](docs/spec-basic-evferr.md),
      `scratchpad/evferr_probe.py`, **26 rows x 3 machines, references unanimous
      on all 26, 11 DIFF -> 1.** The filing said EIGHT jump sites; today's tree
      has **SEVEN**, and **two of those are not assembled** (`expr.asm:2032/2037`
      sit inside `IF !G8_RESIDENT` and `sysvars.inc:475` is `G8_RESIDENT equ 1`).
      🔴 **AND EVERY ONE OF THE FIVE ROWS FILED AS "AGREES" AGREED FOR A REASON
      OTHER THAN ITS SITE**, which is the whole finding: `A=VARPTR 5` /
      `A=VARPTR(5)` answer 2 through **`es_noentry`**'s leftover-token layer
      because `ev_f_err` leaves the cursor UNADVANCED; `A=EOF(0)` / `A=LOF(0)`
      answer 59 inside **`fch_check`**, one call before the site; `A=BASE 5` /
      `A=BASE(0)` answer 2 in the RESIDENT `ev_f_base` (`graphics.asm:1292`).
      The separators are one character away and **four of the five sites were
      live divergences wearing a green row**: `A=VARPTR` and `A=VARPTR(`
      COMPLETED SILENTLY (refs 2), and `OPEN"CRT:"FOR OUTPUT AS#1:A=EOF(1)` /
      `A=LOF(1)` COMPLETED SILENTLY where both references say **ERR 5**.
      💰 **ZERO BYTES — all four walls identical (45 / 107 / 2464 / 1622) and
      `basic-reloc.rom` moved `41b8c4ed` -> `6db7c1f0`**: every fix is a `jp`
      whose TARGET changed, the byte-neutral cure `vptr_close` had carried in
      its own comment since the arrays slice. The ~6 B price and the page-1
      carve this item was blocked on were answers to the wrong question.
      🎯 **`ev_f_err` NOW HAS ZERO INCOMING JUMPS** — it is reached only by
      fall-through from `ev_f_defer`, and the three labels that replaced it each
      say ONE thing: `ev_f_missop` (24, a factor was required), `ev_f_empty`
      (2, malformed expression), `ev_f_ifc` (5, the value is out of domain).
      🔴 **AND THIS ITEM'S OWN JUSTIFICATION HAD ROTTED TOO**: *"BASE is
      descoped and carries its own inline `ERRMARK` body"* has been false since
      graphics slice G8 — right conclusion, dead reasoning.
