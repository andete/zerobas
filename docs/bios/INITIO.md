<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# `INITIO` ($003B) — initialise the sound chip and PLAY's state

> **Spec:** FINAL (2026-11-18), the core rule: ten test-writer reviews, each answered by measuring.
> The tenth found only new combinations of measured rules, which are in the open list, and §7's
> small-call stop applies (Joost, 2026-11-18). Measured on the Philips VG-8020: 31 states over seven
> rounds, built so that "kept" and "written" give different answers:
> - the PSG pattern, all $00 and all $FF included;
> - port $AA;
> - PLAY's queue descriptors, the voice control blocks and MUSICF / PLYCNT, each seeded with garbage
>   independently;
> - entry F $00 / $FF, and interrupts on and off;
> - two full sets of entry registers (entry A $A7 / $00), the shadow registers and I included;
> - PLAY's parse cells seeded;
> - QUEUES moved to two other tables, each seeded with garbage and read before any interrupt;
> - the first call after boot;
> - a read window with a witness (JIFFY). Round 7 retries until the window is clean on both machines;
>   rounds 5-6 record which calls were clean.

## Summary

`INITIO` puts the sound chip (PSG) and PLAY's queues back in their starting state. On the PSG:
- the three amplitudes become 0, and the mixer (R7) $B8: tone enabled on all three channels (its bits are
  active-low), noise disabled, port A input, port B output. With the amplitudes 0 the chip is silent;
- R11 becomes $0B and R15 $CF;
- the tone and noise periods (R0-R6) and the envelope period (R12, R13) are left as they were.

PLAY's state goes back to its start: the three voice queues are emptied (their descriptors are
written into the table QUEUES ($F3F3) points to, $F959 as the boot leaves it; the buffer addresses in
them are fixed), MUSICF / PLYCNT cleared,
and the three voice control blocks rewritten: bytes 15-19 of each become $04 $04 $78 $88 $FF
(in the published layout these are octave 4, length 4, tempo 120, the volume byte and the envelope
period's low byte; no case plays a note to show it), every other byte 0.
The fourth (RS-232) queue, QUEUES itself, PLAY's parse cells and the PPI's port $AA (the CAPS lamp,
the click, the cassette motor, the keyboard row) are not touched. It returns A = $FF, F = $54, E = $0B and
interrupts enabled; BC, HL, IX, IY, D, I and the shadow registers are kept.

zerobas does all of it the same (the descriptors where QUEUES points since D-INITIOQUEUES, 2026-11-19),
apart from the voice control blocks, which it does not rewrite (D-INITIOVCB). It writes only 0 into
voice 0's tempo byte ($FB52). Already at a cartridge's INIT, during boot, its blocks hold 0 and the
VG-8020's the defaults.

Whether a PLAY after INITIO sounds the same on both is not measured here.

## The specification

Reference: the Philips VG-8020's main BIOS. Ours: the C-BIOS repack, whose INITIO writes R15 and R11 and
then runs GICINI's teardown (cbios-repack/initio.patch, initio-gicini.patch).

**Evidence.** **[XI7 n]**: case `n` of round 7's XINITIO7 probe, run 1,
[`scratchpad/XINITIO7_run1.out`](../../scratchpad/XINITIO7_run1.out). `probes/bios/spec/xinitio7.asm` makes
every recorded call clean on BOTH machines. It re-seeds and retries a case, up to 8 tries, until
JIFFY is unchanged across the call, and records the tries (one was enough everywhere). It enters
INITIO with interrupts on (XI7 1 / 2) and off (XI7 3 / 4). It sets the PSG all $00 or all $FF, and
seeds the voice control blocks all $FF or with $CC - k, the complement of rounds 2-3's pattern.

**[XI6 n]**: case `n` of round 6's XINITIO6 probe, run 4,
[`scratchpad/XINITIO6_run4.out`](../../scratchpad/XINITIO6_run4.out). `probes/bios/spec/xinitio6.asm` sets the
PSG all $00 before every call, reads R7 / R11 / R15 after it, and runs five cases in round 5's window:
- the first call after boot;
- QUEUES := $9EB7, and QUEUES := $A123;
- QUEUES left at $F959 with that table seeded;
- the same with MUSICF $FF.

The window is usually clean, not always: INITIO and the reads take a few thousand T-states of a
70,000-T frame. XI6 4 took no interrupt in run 2 and one in run 3, and XI5 1 none in XINITIO5's run 2
and one in its run 4. The JIFFY witness says which. The rules do not read it, since it is each
machine's own time and a slower but correct implementation would take more interrupts; it is
declared UNSTABLE. On the VG-8020 it was unchanged in XI5 2 / 3 (run 4), in all five XI6 cases
(run 4), and in all four XI7 cases at the first try, on both machines: the "INITIO itself" rules rest
on those.

In the moved cases both QUEUES' 28-byte table and $F959.. are seeded with garbage. Everything is read
before the call and again after it, before any `ei`; JIFFY is the witness.

**[XI5 n]**: case `n` of round 5's XINITIO5 probe, run 4,
[`scratchpad/XINITIO5_run4.out`](../../scratchpad/XINITIO5_run4.out). `probes/bios/spec/xinitio5.asm` runs
every case with interrupts off and round 4's window. JIFFY ($FC9E) is read just before the call and
again after the reads, as the window's witness. It seeds QUEUES ($F3F3) := $9EB7 in XI5 1 / 2, where
XI5 3 inherits it, and reads $9EB7.. and QUETAB again after one more interrupt.

**Rounds 1-3 ran with an interrupt pending.** Their probes kept interrupts off for more than a frame
(the 3200-byte copy and compare), so the VDP's interrupt was pending at the call. It ran at INITIO's
own EI in the interrupts-off cases, and at the probe's `ei` just before the call in the interrupts-on
cases. So the interrupts-off cases describe INITIO followed by one interrupt, and the interrupts-on
cases one interrupt and then INITIO. Rounds 5 and 6 remove it, with
JIFFY as the witness, and every rule the interrupt could have explained holds there too. In rounds
1-3's interrupts-off cases MUSICF was garbage before the call and R8-R10 still read 0 after it. That
fits INITIO clearing MUSICF before it enables interrupts; the state at that interrupt is not recorded.
(MUSICF was garbage before the call in XI 1 / 2 / 5, XI2 1 / 4 and XI3 4 / 5; in XI2 5 and XI3 1 / 2 it
was 0.)

**Round 4's window has no witness.** It reads the VDP status just before the call and runs `di` right
after it. In XI4 2, entered with interrupts on, the interrupt left pending by the snapshot ran
between the probe's `ei` and that status read: port $AA was written $C3 and read $CA. XI5 1 shows an
interrupt can still be taken after INITIO's EI. No round-4 rule depends on the window: R-IO-AA4
witnesses itself through $AA's low nibble, and XI4 2 is checked on the high nibble only.

**[XI4 n]**: case `n` of round 4's XINITIO4 probe, run 1,
[`scratchpad/XINITIO4_run1.out`](../../scratchpad/XINITIO4_run1.out). `probes/bios/spec/xinitio4.asm` adds
PLAY's parse cells ($FB35-$FB3E) to the seeds and sets the I register. It reads the VDP status just
before the call, so no interrupt is pending, and makes `di` the first instruction after it, so no
interrupt runs before the reads; its IFF2 bit therefore reads that `di`, not INITIO.

**[XI3 n]**: case `n` of round 3's XINITIO3 probe, run 1,
[`scratchpad/XINITIO3_run1.out`](../../scratchpad/XINITIO3_run1.out). `probes/bios/spec/xinitio3.asm` keeps
XINITIO2's record and sets each seed independently: the queue descriptors / QUEBAK, the voice control
blocks, and MUSICF / PLYCNT written with chosen values. That includes MUSICF 0 with garbage elsewhere,
so the blocks' rewrite is seen with interrupts on. Port $AA's whole byte is written, and case 1 is the
first call after boot.

**[XI2 n]**: case `n` of round 2's XINITIO2 probe, run 2,
[`scratchpad/XINITIO2_run2.out`](../../scratchpad/XINITIO2_run2.out). `probes/bios/spec/xinitio2.asm` adds a
second register set (entry A $00) and the shadow registers, and seeds PLAY in three modes:
- none;
- all of it with interrupts off, the voice control blocks ($FB41-$FBAF) included;
- the queue descriptors and QUEBAK only, with MUSICF / PLYCNT left 0, so that interrupts can stay on.

It records the voice control blocks whole after the call, and skips STATFL / TRGFLG ($F3E7-$F3E8): the
interrupt writes them.

**[XI n]**: case `n` of the XINITIO probe, run 3,
[`scratchpad/XINITIO_run3.out`](../../scratchpad/XINITIO_run3.out). `probes/bios/spec/xinitio.asm` lists the
five cases and the 105-byte record:
- The PSG's 16 registers are set to a pattern (register k := base + k × step), R7's top two bits
  included, and read back through the PSG's own ports, not through RDPSG.
- Port $AA's high nibble is set, its low nibble (the keyboard row) kept.
- In the three cases with interrupts off, QUETAB / QUEBAK ($F959-$F974) and MUSICF / PLYCNT
  ($FB3F-$FB40) get garbage first. With interrupts on they are left as the boot set them: an
  interrupt would otherwise play from the garbage.
- The whole work area $F380-$FFFF is copied just before the call and compared after it, skipping the
  interrupt's own cells (SCNCNT, the key matrices, JIFFY).
- Every register is garbage on entry; each record ends in a sentinel byte the decoder requires.

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/bios/spec/xinitio_rules.py -- do not edit; `python3 tools/spec_rules.py probes/bios/spec/xinitio_rules.py --write` -->

**33 rules; 33 hold on the reference. Of the 4515 recorded outputs (each case's cursor, cells, A, table entries ...): 4459 read by a rule's check, 56 declared NOT evidence (below), 0 unread.**

#### 1. INITIO ($003B)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-IO-PSG** The PSG: R7 := $B8 (the mixer bits are active-low: tone ENABLED on A / B / C, noise disabled, port A input, port B output -- the silence comes from the amplitudes), R8 / R9 / R10 := 0 (the three amplitudes), R11 := $0B, R15 := $CF; R0-R6, R12 and R13 are left as found -- for five patterns, all $00 and all $FF included. | 5 | ✓ | ✓ |
| **R-IO-AA** Port $AA's high nibble (the PPI's port C: the CAPS lamp, the click, the cassette motor and output) is left as found -- 0, 5, A, C and F. (Its low nibble, the keyboard row, is the interrupt's: it may run an interrupt between the return and the read; R-IO-AA4 closes that window.) | 5 | ✓ | ✓ |
| **R-IO-PLAY** PLAY's state is reset: the three voice queues' descriptors -- in the table QUEUES points to, $F959-$F96A as the boot leaves it (R-IO-QUEUES) -- to put / get / backup 0, size $7F and their buffers $F975, $F9F5, $FA75; MUSICF ($FB3F) and PLYCNT ($FB40) to 0. The fourth (RS-232) queue's descriptor and QUEBAK ($F96B-$F974) are left, from garbage; no other cell of the work area $F380-$FFFF changes (cells not seeded held what the boot or the previous case left: R-IO-SEED seeds more). | 3 | ✓ | ✓ |
| **R-IO-QUIET** A second call, from the state the previous INITIO left (PLAY idle), changes nothing in the work area (R-IO-BOOT: the first call after boot). | 2 | ✓ | ✓ |
| **R-IO-REGS** On return A = $FF and F = $54 whatever the flags on entry ($00 / $FF); D is kept and E is $0B; BC, HL, IX and IY are kept. | 5 | ✓ | ✓ |
| **R-IO-EI** It returns with interrupts ENABLED, also when entered with them disabled. | 5 | ✓ | ✓ |

#### 2. Round 2: a second register set and the shadow registers; the reset with interrupts ON; the voice control blocks (XINITIO2)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-IO-REGS2** Whatever A was on entry ($A7 or $00), A = $FF and F = $54 on return; D is kept ($9B and $64 measured) and E is $0B; BC, HL, IX, IY and the shadow registers AF' / BC' / DE' / HL' are kept -- two full sets of entry values. | 5 | ✓ | ✓ |
| **R-IO-PSG2** R-IO-PSG and R-IO-AA hold here too, with interrupts on and off and both register sets. | 5 | ✓ | ✓ |
| **R-IO-PLAYEI** Entered with interrupts ON (MUSICF 0, so the interrupt plays nothing), INITIO resets the three voice descriptors (QUEUES at $F959) the same way, from garbage; the RS-232 descriptor and QUEBAK stay. | 2 | ✓ | ✓ |
| **R-IO-VCB** The three voice control blocks (37 B each at $FB41, $FB66, $FB8B) are rewritten: offsets 15-19 = 04 04 78 88 FF, every other byte 0 -- from garbage in XI2 1 / 4; in the other cases the blocks already held these values. | 5 | ✓ | ✗ 5: XI2 1, XI2 2, XI2 3, XI2 4, XI2 5 |
| **R-IO-SEED** With PLAY's state, QUEBAK and the voice control blocks all garbage, exactly the cells R-IO-PLAY and R-IO-VCB name change, no other; with nothing seeded, nothing changes. | 3 | ✓ | ✗ 2: XI2 1, XI2 4 |

#### 3. Round 3: each seed independent, MUSICF / PLYCNT values, the first call after boot (XINITIO3)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-IO-VCB3** The voice control blocks are rewritten to R-IO-VCB's values whatever else holds: with interrupts ON and MUSICF 0 (XI3 3), with the blocks seeded and only PLYCNT besides (XI3 6), and already at a cartridge's INIT during boot (XI3 1, the first call: nothing to change). | 6 | ✓ | ✗ 6: XI3 1, XI3 2, XI3 3, XI3 4, XI3 5, XI3 6 |
| **R-IO-MP** MUSICF and PLYCNT become 0 whatever they held -- 0 / $5A, $FF / 0 (MUSICF alone), $5A / $FF, 0 / $33 (XI3 2 / 4 / 5 / 6; XI3 3 seeds 0 / 0) -- and exactly the seeded cells the reset gives another value change, no other. | 5 | ✓ | ✗ 4: XI3 2, XI3 3, XI3 5, XI3 6 |
| **R-IO-BOOT** The first call after boot, nothing seeded, changes no cell of the work area. (That the boot already left the voice control blocks at INITIO's values is R-IO-VCB3's read of XI3 1.) | 1 | ✓ | ✓ |
| **R-IO-REGS3** R-IO-REGS2 and R-IO-PSG2 hold here too: A $FF, F $54, E $0B, the rest and the shadow registers kept; the PSG; port $AA's high nibble (CAPS, click, motor, cassette out) as found; interrupts on. | 6 | ✓ | ✓ |

#### 4. Round 4: the parse cells, the I register, and a read window no interrupt can enter (XINITIO4: the VDP status read just before the call, `di` the first instruction after it)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-IO-I** The I register is kept ($5A, $A5, $00). | 3 | ✓ | ✓ |
| **R-IO-PARSE** PLAY's parse cells $FB35-$FB3E (VOICEN, MCLPTR, QUEUEN ...) are left, from garbage: the changed cells are exactly R-IO-PLAY's / R-IO-VCB's / R-IO-MP's. | 3 | ✓ | ✗ 1: XI4 3 |
| **R-IO-AA4** With interrupts off on entry and no interrupt after the return, port $AA is left WHOLE, the keyboard-row nibble included ($35, $96); R15 still reads $CF, so INITIO wrote it, not an interrupt. | 2 | ✓ | ✓ |
| **R-IO-REGS4** R-IO-REGS3's registers, the PSG and port $AA's high nibble hold here too. | 3 | ✓ | ✓ |
| **R-IO-VCB4** R-IO-VCB holds here too. | 3 | ✓ | ✗ 3: XI4 1, XI4 2, XI4 3 |

#### 5. Round 5: under the clean window, with JIFFY as the witness; QUEUES moved (XINITIO5: QUEUES ($F3F3) := $9EB7 in XI5 1 / 2, left so for XI5 3)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-IO-CLEAN** In XI5 2 and 3, where the witness shows no interrupt in the window (the evidence note), R7 / R8-R10 / R11 / R15 are as R-IO-PSG says with the PSG all $FF and a pattern: INITIO wrote them. | 2 | ✓ | ✓ |
| **R-IO-QUEUES** With QUEUES = $9EB7, the 18 bytes there hold R-IO-PLAY's descriptors (0, 0, 0, $7F, $F975 / $F9F5 / $FA75) after the call and one more interrupt, and the $F959.. table keeps its garbage, its bytes +18..+27 (QUEBAK, the RS-232 descriptor) included. $9EB7 was not seeded here, so this round does not show the WRITE: R-IO-QUEUES6 does. QUEUES itself is left (it is in no case's changed cells). As the boot leaves QUEUES ($F959), rounds 1-4 saw the reset at $F959. | 3 | ✓ | ✗ 3: XI5 1, XI5 2, XI5 3 |
| **R-IO-MP5** MUSICF / PLYCNT become 0 ($FF / 0, 0 / $5A, $5A / $FF), the voice control blocks R-IO-VCB's values, and exactly those seeded cells change. (XI5 1 took an interrupt in the window; the witnessed cases are XI5 2 / 3, and MUSICF $FF with no interrupt is R-IO-MPFF.) | 3 | ✓ | ✗ 3: XI5 1, XI5 2, XI5 3 |
| **R-IO-REGS5** The registers, I and the PSG (all $00, all $FF and a pattern) as R-IO-REGS3 / R-IO-I / R-IO-PSG say; port $AA WHOLE in the clean cases ($96, $C3), its high nibble in XI5 1, where the interrupt that slipped in scanned the keyboard ($35 read as $3A). | 3 | ✓ | ✓ |

#### 6. Round 6: QUEUES and its table read BEFORE any interrupt can run (XINITIO6: the clean window, JIFFY as the witness, the reads before any `ei`)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-IO-QBOOT** At the first call after boot QUEUES is $F959 and its table already holds R-IO-PLAY's descriptors, the RS-232 descriptor and QUEBAK 0; the call changes none of it. | 1 | ✓ | ✓ |
| **R-IO-QUEUES6** INITIO ITSELF writes the descriptors where QUEUES points: with QUEUES $9EB7 or $A123 and its 28-byte table garbage, the table's first 18 bytes become R-IO-PLAY's descriptors (the buffer addresses $F975 / $F9F5 / $FA75 whatever QUEUES is), its bytes +18..+27 keep their garbage, $F959.. ($F96B-$F974 included) keeps its own, and QUEUES is kept -- in a witnessed window (the evidence note). | 2 | ✓ | ✗ 2: XI6 2, XI6 3 |
| **R-IO-QF959** With QUEUES at the boot's $F959 and that table garbage, the descriptors are written there: the first 18 bytes become R-IO-PLAY's, bytes +18..+27 keep their garbage. | 1 | ✓ | ✓ |
| **R-IO-MPFF** With MUSICF $FF (every bit), in a witnessed window, INITIO itself clears MUSICF -- and writes the descriptors at $F959 as R-IO-QF959. | 1 | ✓ | ✓ |
| **R-IO-PSG0** With the PSG all $00 before the call and a witnessed window (run 4), R7 = $B8, R11 = $0B and R15 = $CF after it. From $00 this rules out an AND of the old value; R-IO-PSG7 (from $FF) rules out an OR. | 5 | ✓ | ✓ |

#### 7. Round 7: every call witnessed clean on BOTH machines (XINITIO7 re-seeds and retries until JIFFY is unchanged across the call), interrupts on and off at entry, the PSG all $00 / all $FF, the voice control blocks all $FF and $CC - k

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-IO-PSG7** R7 = $B8, R11 = $0B and R15 = $CF from the PSG all $FF (XI7 1 / 3 / 4) and all $00 (XI7 2): with R-IO-PSG0 neither an AND nor an OR of the old value fits -- they are written whole. | 4 | ✓ | ✓ |
| **R-IO-VCB7** The voice control blocks become R-IO-VCB's values from all $FF (XI7 2 / 3) and from $CC - k (XI7 1 / 4, the complement of rounds 2-3's pattern): every bit of every byte was seen both ways. | 4 | ✓ | ✗ 4: XI7 1, XI7 2, XI7 3, XI7 4 |
| **R-IO-EI7** Entered with interrupts ON (XI7 1 / 2), in the clean window, INITIO itself does the same: MUSICF ($FF, $5A) becomes 0, and the descriptors are written where QUEUES points ($F959, $9EB7). | 2 | ✓ | ✗ 1: XI7 2 |
| **R-IO-Q7** Entered with interrupts off (XI7 3 / 4): the descriptors are written where QUEUES points ($F959, $A123), as R-IO-QUEUES6 / R-IO-QF959; MUSICF is 0 after (cleared from $FF in XI7 3; XI7 4 seeds 0). | 2 | ✓ | ✗ 1: XI7 4 |

Declared NOT evidence (16 cases: XI 1, XI 2, XI 3, XI 4 … (+12)): r14 — R14 is the PSG's INPUT port A: it reads the joystick lines, not anything INITIO writes

Declared NOT evidence (3 cases: XI4 1, XI4 2, XI4 3): r14, iff — R14 is the PSG's input port; IFF2 reads the probe's own `di` (the first instruction after the return: round 4's read window)

Declared NOT evidence (3 cases: XI5 1, XI5 2, XI5 3): r14, iff — R14 is the PSG's input port; IFF2 reads the probe's own `di` (round 5's read window)

Declared UNSTABLE on the reference itself (3 cases: XI5 1, XI5 2, XI5 3): jifb, jifa — the read window's witness, each machine's own time -- the same case took no interrupt in scratchpad/XINITIO5_run2.out and one in scratchpad/XINITIO5_run4.out (XI5 1); the evidence note states the witnessed values

Declared UNSTABLE on the reference itself (5 cases: XI6 1, XI6 2, XI6 3, XI6 4 … (+1)): jifb, jifa — the read window's witness, each machine's own time -- XI6 4 took no interrupt in scratchpad/XINITIO6_run2.out and one in scratchpad/XINITIO6_run3.out; run 4's are all unchanged (the evidence note)

Declared UNSTABLE on the reference itself (4 cases: XI7 1, XI7 2, XI7 3, XI7 4): jifb, jifa, tries — the read window's witness, each machine's own time: the probe retries until JIFFY is unchanged (XINITIO7_run1.out: one try everywhere, on both machines). No rule reads it: a correct but slower INITIO would need more tries -- the evidence note states the witnessed values

<!-- RULES END -->

## Differences from the reference

| TODO item | rules zerobas fails |
|---|---|
| **D-INITIOVCB** (the voice control blocks are not rewritten; they hold 0 after boot) | R-IO-VCB, R-IO-SEED, R-IO-VCB3, R-IO-VCB4, R-IO-VCB7, R-IO-MP / R-IO-PARSE / R-IO-MP5 (through the blocks' cells) |

## Open (not measured)

- **[A]** INITIO's duration: it decides how often an interrupt lands in a probe's window. The rules
  require no timing; round 7's witness needed one try per case on both machines.
- **[A]** Round 7 (the clean interrupts-on cases) does not record PLYCNT, R0-R6 / R8-R10 / R12 / R13,
  the registers, port $AA or a work-area diff. Their interrupts-on evidence is rounds 1-3, where an
  interrupt ran before INITIO, and PLYCNT's clear is witnessed with interrupts off only (XI5 2 / 3).
- **[A]** The queue descriptors from every bit pattern: the moved tables were seeded with incrementing
  values only (voice A's put byte $20, $40, $5A, $60, $C0), so "written whole" is not separated from a
  mask that keeps a bit those seeds never set. R-IO-VCB7 covers the voice control blocks only.
- **[A]** The witnesses' own assumptions: that every interrupt in a window moves JIFFY, and (round 4)
  that every interrupt rewrites port $AA's keyboard-row nibble.
- **[A]** Whether INITIO, entered with interrupts on, disables them during its reset: round 7's clean
  windows show the result, not the moment.
- **[A]** Where A = $FF, F = $54 and E = $0B come from. F has Z, H and P/V set, which looks like a test
  result; a dependence on an unseeded cell would not show.
- **[A]** The bytes around a moved QUEUES table: writes before its +0 or after its +27 were not read.
- **[A]** Where INITIO's values come from. The block defaults, the buffer addresses, size $7F and R7 /
  R11 / R15 were each seen written over garbage. The cells that could hold a copy of them were not:
  the whole work area was never filled with garbage before a call.
- **[A]** A PLAY after INITIO, with other O / L / T / V / M settings before it: what it sounds like,
  and the voice control blocks after it.
- **[A]** Whether INITIO writes R14, port A's output latch: a read returns the joystick lines (declared
  not evidence), so it matters only if port A is later made an output.
- **[A]** QUEBAK with QUEUES moved: both $F971-$F974 and the moved table's +24..+27 kept their garbage,
  so whether QUEBAK is fixed or relative to QUEUES is not separated.
- **[A]** QUEUES pointing at a table that overlaps INITIO's other targets (MUSICF / PLYCNT, the voice
  control blocks, the voice buffers) or at memory that is not RAM.
- **[A]** Port $AA's keyboard-row bit 3: every clean case that reads the whole byte has it 0 ($35, $96,
  $C3), so "the low nibble is kept" and "bit 3 is cleared" both fit.
- **[A]** The disk machine (every run is the diskless row): whether the disk ROM hooks INITIO, and
  what it does to the disk ROM's work area.
- **[A]** The rest of the work area from garbage. Only PLAY's cells were seeded; every other cell held
  what the boot or the previous case left, so a write of that same value is invisible. The interrupt's
  own cells are not compared: SCNCNT / REPCNT ($F3F6-$F3F7), the key matrices ($FBDA-$FBEF), JIFFY,
  INTVAL and INTCNT's low byte ($FC9E-$FCA2), and from round 2 on STATFL / TRGFLG ($F3E7-$F3E8). RAM below $F380, VRAM, and the ports other
  than $A0-$A2 and $AA are not read.
- **[A]** The RS-232 queue's buffer and the voice buffers' contents ($F975..) from garbage.
- **[A]** When inside the call interrupts come back on. Rounds 1-3's pending interrupt ran right after
  it, with R8-R10 still 0 afterwards (see the evidence note), but no probe records the PSG writes or
  the PLAY state at that moment.
- **[A]** "Left as found" for R0-R6, R12 and R13 is read back, not traced. A rewrite with the same
  value would look the same. That matters for R13, whose write restarts the envelope.
- **[A]** The PSG's unimplemented bits (the high bits of R1 / R3 / R5 / R13, R6 and R8-R10) read back
  as written here. That depends on the emulated chip model; a test should compare the implemented bits only.
- **[A]** Port $AA during the call (a click or a motor pulse), and the printer port: whether INITIO
  strobes or resets it.
- **[A]** The interrupt mode, and IFF1: LD A,I reads IFF2 only, and IM was not read.
- **[A]** How far below SP INITIO writes the stack; brief writes to R7-R11 / R15 during the call (an
  amplitude raised before the mixer is cleared); VDP register writes.
- **[A]** INITIO called while PLAY is really running (queues filled by a PLAY, interrupts on), its real
  use.
- **[A]** Whether INITIO calls a hook (none was planted), and which PSG register it leaves latched on
  $A0.
- **[A]** The CF-3300 (the second reference): an earlier probe through BASIC
  ([`initio_cf.out`](../../scratchpad/initio_cf.out)) read R7 $B8, R8-R10 0, R11 $0B, R15 $CF, A $FF,
  F $54 and E $0B after the call, plus BC $1234, D $56 and HL $9ABC, and an unlabelled 'A' $5A. The
  file does not hold the entry values or a "before" pattern for the PSG, so it shows the values after
  the call, not what INITIO wrote or kept.

## Related pages

[The interrupts-and-traps concept page](../concepts/interrupts-and-traps.md) (the system region),
[GICINI](index.md) ($0090), the shared-state map ([shared-state.md](shared-state.md)).

## Tests that cover it

**`spec-live`** ([tools/spec_live.py](../../tools/spec_live.py), in every gate): every rule above, run live on zerobas against these cases' measured reference values. It fails if a rule fails that *Differences from the reference* does not name, or a named one holds ([docs/spec-method.md](../spec-method.md) §8).

Also `initio-acceptance` (probes/basic/basic_probe_initio.py: R11 / R15, port $AA through BASIC).
