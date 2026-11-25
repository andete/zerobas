- [ ] 🐛 **`GO TO 100` (ONE SPACE) IS GOTO ON THE VG-8020 AND A SYNTAX ERROR ON ZEROBAS (D-GOTOSPACE, found 2026-11-25 by
      D-KWSPEC's flow region).**
      🎚️ TIER 1 — a valid program that runs on the reference stops on zerobas (programs ported from other BASICs write
      `GO TO`).
      🤖 **AUTONOMOUS** — measured by [`kgosub.py`](../../probes/basic/spec/kgosub.py) ->
      [`KGS_run1.out`](../../scratchpad/KGS_run1.out): KGS FX 7 `GO TO <line>` and FX 28 `IF 1 THEN GO TO <line>` jump
      on the VG-8020, Syntax error (2) on zerobas. The form is NARROW on the reference: `GO  TO` (two spaces, FX 27),
      `GO SUB` (FX 26) and `GO` alone (FX 29) are Syntax error on both machines. So the reference's tokeniser knows
      the one spelled-out form `GO TO`, not spaces inside keywords in general.
      ➡️ When picked up: measure first what the reference STORES for `GO TO` (LIST of a typed `10 GO TO 20`: GOTO's
      token, or the text kept), then teach zerobas's tokeniser (basic/tokenise.inc match_kw / the sub ROM's kwtable,
      whose single copy has a pinned sha256) that one form, and nothing wider.
