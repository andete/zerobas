# D-BRKFRAME — the per-statement Ctrl-STOP poll is 0.3%, and the profile that said otherwise was reading the prompt

**Status: REFUTED and CLOSED. No code shipped. The carve that was raised to pay
for it stayed.** 2026-09-11.

## 0. What was claimed

D-SPEEDPROF's entry ended with *"~20 % is BIOS (`BREAKX` per statement, which the
reference pays too)"*, and a later profile of the bare `FOR I=1 TO n:NEXT` loop
put **62.4 %** of it in BIOS/ISR with **40.6** samples at `$11A0` — the keyboard
matrix scan — for every loop iteration. The inference was that `BREAKX` ($00B7)
is the single largest cost in every BASIC program zerobas runs, and that the
reference escapes it because its ISR publishes `INTFLG` ($FC9B) while ours does
not.

Everything in that paragraph is a reading. The CAUSE it names is not.

## 1. The two measurements that ARE sound

Both were made with a write watchpoint / key injection against the real machines,
not inferred.

**INTFLG is dead on this target.** Injecting Ctrl-STOP (`keymatrixdown 6 0x02`
+ `keymatrixdown 7 0x10`) with a watchpoint on `$FC9B`:

| machine | writes to INTFLG | where |
|---|---|---|
| CF-3300 | 12 | `$036A` `$036D` `$03B6` — the ISR maintains it, `$00`/`$FF` |
| zerobas (C-BIOS) | 1 | `$0F24`, at boot, and never again |

Both machines broke out of the program, so the injection reached both. **C-BIOS's
ISR does not maintain INTFLG**, so the reference's own break mechanism is not
available to copy.

**NEWKEY, however, IS maintained — identically on both.** Reading `NEWKEY+6`
(bit 1 = CTRL) and `NEWKEY+7` (bit 4 = STOP) before / during / after the same
injection gives `$FF $FF` → `$FD $EF` → `$FF $FF` on the CF-3300 **and** on
zerobas. So a run loop *could* poll two RAM bytes the ISR has already paid for
instead of calling `BREAKX`, at one-frame granularity — which is the reference's
granularity too, since `INTFLG` is an ISR product.

## 2. The fix was built, and it bought nothing

`rp_exec`'s `call BREAKX` was replaced by

```
                ld      hl,NEWKEY+6         ; row 6: bit 1 = CTRL (ACTIVE LOW)
                bit     1,(hl)
                jr      nz,rp_stopans       ; CTRL up -> NZ -> no break
                inc     hl                  ; row 7: bit 4 = STOP
                bit     4,(hl)
rp_stopans:                                 ; Z set here == Ctrl-STOP is down
                pop     hl
                jr      z,rp_break
```

— one tail, because whichever `bit` runs last already leaves Z meaning "break",
so the `jr c,rp_break` it replaces becomes `jr z` at the same size and reach.
Net **+7 B** of main page 1.

Measured in frames (`TIME` is `JIFFY`), baseline vs the change, same harness:

| loop | before | after | delta |
|---|---|---|---|
| `FOR I=1 TO 4000:NEXT` | 1056 | 1052 | −0.4 % |
| `FOR I=1 TO 2000:X=I:NEXT` | 1096 | 1094 | −0.2 % |
| `FOR I=1 TO 2000:X=I+1:NEXT` | 1419 | 1416 | −0.2 % |
| `FOR I=1 TO 2000:GOSUB 100:NEXT` | 673 | 667 | −0.9 % |

🔴 **And the run-to-run variance of the harness is about the same size**: the
profiler's own `jiffies` line reported **1052** for the baseline build that the
table above measures at **1056**. So the honest statement is not "0.3 % faster",
it is **"at or below the noise floor of the instrument"**.

**7 bytes of a 12-byte page-1 budget for that is a bad trade. REVERTED.**

## 3. Why the profile said 62 %

`$11A0` is the READY prompt's `HALT`. The sample window outlived the program:
`FOR I=1 TO 4000:NEXT` runs 1052 frames ≈ 21 s, and the window was **40 s**. Every
sample after the program ended landed on one address, and one address is exactly
what symbolises as one enormous entry.

The same loop, profiled with a window that fits inside the run:

| | window 40 s (overruns) | window 25 s (fits) |
|---|---|---|
| `$11A0` | 54.6 % of all samples | **absent from the top sixteen** |
| BIOS/ISR total | 68.1 % | **23.6 %** |
| `d10_lp` | 5.5 % | **13.6 %** |
| `wsrc_unpack` | 3.4 % | **8.0 %** |

This is [[a-mechanism-inferred-from-one-observation]] again, and the tell is the
one that file names: the sentence claimed a CAUSE (`BREAKX` is the cost) where the
evidence supported only a READING (samples sit below `$2812`).

## 4. The gate that now stops it

`scratchpad/speedprof_rig.py` refuses to average idle in. Two shapes were tried:

1. **A marker byte POKEd from BASIC for exactly the run's duration.** Rejected —
   the Tcl side never observed it: the marker read `0` for the entire session
   (one `255` at boot, then `0` from t=2.75 s), so the rig reported **0 % in-run
   for a window that plainly overlapped**, an apparatus failing the way the thing
   it replaced failed.
   🔴 **AND MY FIRST EXPLANATION OF THAT WAS WRONG.** I wrote that `POKE &HE21F,1`
   had taken the machine down, on the strength of ONE blank-screen run, and then
   ran it: `10 PRINT"[hiA]":POKE &HE21F,7:PRINT"[hiB";PEEK(&HE21F);"]"` prints
   `[hiA] [hiB 7 ]` on **zerobas and on the CF-3300 alike**, and so does the same
   line against `&HD000`. The write is fine on both. So the failure is on the
   READ side — `debug read memory 0xE21F` in the sampler — and the `0x` address
   form is the suspect. **UNCONFIRMED, and left open rather than asserted**; the
   shipped guard needs no marker, so nothing depends on it.
   [[a-justification-parenthesis-is-an-unrun-claim]]
2. **Trim a constant PC run at either end.** Rejected — idle is not a *constant*
   PC; the prompt cycles several addresses around its HALT, so the trim found
   nothing and the bad table came back unchanged.
3. **SHIPPED: the most-sampled PC, if it is BIOS and holds ≥ 15 %, is the prompt.**
   No executing code holds a share like that — in a window that fits, `$11A0` does
   not reach the top sixteen; in one that overruns by half it is 54.6 % alone. The
   rig drops those samples, prints `⚠️ IDLE DISCARDED` with the percentage, and
   says the window overran by about that much.

Knifed on the bad window: it now recovers `d10_lp` 12.2 % / `wsrc_unpack` 7.5 %
against the good window's 13.6 % / 8.0 %.

## 5. What the corrected profile actually points at

An **empty** `FOR I=1 TO 9000:NEXT` — no arithmetic in the program text at all:

| routine | share |
|---|---|
| `d10_lp` + `d10_skip` | **17.5 %** |
| `wsrc_unpack` + `wu_digloop` + `wsrc_nz` + `wsrc_go` + `wsrc_dexp_ok` + `wu_rev_lp` | **~15 %** |
| `dtw_lp` | 5.7 % |
| BIOS/ISR (genuine, spread over `$19xx` `$24xx` `$0Cxx` `$25xx`) | 23.6 % |
| `nx_have` (`NEXT` itself) | 2.6 % |

The loop variable is a 14-digit BCD double (MSX's default type, and faithful —
see D-MULZERO's `B=7` finding), so every `NEXT` runs the full pack/unpack
pipeline. **That, not the Ctrl-STOP poll, is where a bare loop's time goes**, and
a divide-by-ten loop being the largest single entry in a loop that only ever adds
1 is the next thing to explain.
