- [ ] 🔴 **`err_verify` AND `brk_msg` ARE THE LAST TWO MAIN-RESIDENT MESSAGES,
      AND THEY ARE BLOCKED FOR TWO DIFFERENT REASONS.** Filed 2026-08-02 by
      D-MSGMIGRATE §6.2/§6.3, which measured both and declined both.
      * `err_verify` (8 B): `verify_error` ([`basic/cload.asm:580`](basic/cload.asm:580))
        is `ld hl,err_verify / jp print_msg` with **no `ld (ERRFLG),a`**. Adding
        one costs 5 B to save 8 -- a net 3 B not worth taking blind, because it
        also makes `PRINT ERR` read 20 after a `CLOAD?` mismatch, which is an
        **observable change with no oracle reading behind it**. ⚠️ Exactly the
        shape D-MSGMIGRATE's own §6.4 turned out to be, and there the reading
        (both refs read 6) is what made the fix correct AND free -- so TAKE THE
        READING FIRST. The CAS: harness is the cost; `Verify error` is still
        `<not-measured>` in the msgexact denominator for the same reason.
      * `brk_msg` (6 B): printed by `call print_string`, and **`print_string` has
        no escape decoder at all** -- a `MSGESC_SUB` byte there is `pchar`'d as a
        literal $06. And `Break` is not an error, so ERRFLG is stale. Two
        independent blockers; this one needs a PRINTER change, not a key.
      🎚️ BUDGET — main-resident messages
      🤖 AUTONOMOUS — 🏗️ **RULED BY JOOST 2026-10-27**: *"Measure first, then decide"* -- take the CLOAD? reading (ERR after a Verify error) on the VG-8020; move `Verify error` only if it matches; `Break` stays.
      📏 **MEASURED 2026-10-28** ([`cloadverr_probe.py`](scratchpad/cloadverr_probe.py) -> [`cloadverr_run.out`](scratchpad/cloadverr_run.out)): after a CLOAD? mismatch the
      VG-8020 prints `Verify error` and `PRINT ERR` reads **20**; zerobas read 0. 🔮 Both HIT. So
      it IS an error there, and raising it matches: sub2/tapeprog.asm's ctp_verify_error is now
      `ld a,20 / jp p0_raise_error` -- the same text (err_msgtab[20] = err_verify), ERR / ERL set
      ([`cloadverr_after.out`](scratchpad/cloadverr_after.out)). Gate: cloadverr-acceptance ([`basic_probe_cloadverr.py`](probes/basic/basic_probe_cloadverr.py): our own program and
      tape, both machines, `Verify error | E 20`; [`cloadverr_gate.out`](scratchpad/cloadverr_gate.out)) -- NOT
      basic_probe_cas_verify, whose `pkill -9 openmsx` would kill a parallel battery. 🔪 K-CV1
      ([`cloadverr_knife.py`](scratchpad/cloadverr_knife.py)): tapeprog.asm back to HEAD -> ZB `E 0`, DIVERGES, all five restored
      ([`cloadverr_knife.out`](scratchpad/cloadverr_knife.out)). Docs: CLOAD.md. ➡️ What remains of the item: the 8 B `err_verify` TEXT
      is still in main -- now ONLY as err_msgtab[20]'s target, the shape the other sub-hosted
      messages already have (D-MSGSUB), so it can move to the sub-hosted table with them.
