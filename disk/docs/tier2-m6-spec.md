<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 milestone M6 — build the DOS work area (incremental `$607B` slice)

**Status: DRAFT — awaiting sign-off. No asm until approved. Approach (B, incremental)
chosen by the user; this spec also surfaces a scope escalation found while
characterising (read §5 before approving).** Evidence: notebook §8.59-8.64.

## 1. Problem

The COMMAND.COM-load hang (`$DA23` wrong-path loop) is rooted in a stubbed canonical
entry `$607B` (§8.62): the disk ROM's buffered-transfer / work-area service, which
MSXDOS.SYS calls ~15× during init to build the DOS work area. Our `k_607B` is a bare
`ret`, so the work area is never built. Characterising `$607B`'s `$F2B8` build (§8.64)
showed it threads through ~20 disk-ROM subroutines reading the drive-A DPB (`$F195`)
and writing linked structures — re-implementing its *algorithm* is large, but every
field it produces is **derived from the DPB**, which our `getdpb` already builds
byte-identical to the CF-3300 (§8.13).

## 2. Build target (measured, `memsnap` diff at `$D7CE`, §8.64)

390 work-area cells are populated on stock but stale (`$FF`/clobbered) on ours.
Grouped into logical structures:

| region | size | what it is | ours builds it? |
|--------|------|------------|-----------------|
| `$F1A8-$F241` | 154 B | DPB-chain / drive-parameter block (BPB-derived) | no |
| `$F243-$F24C` | 10 B | work-area pointers (`95 F1` = `$F195`…) | no |
| `$F2B8-$F2FD` | 70 B | `07 "MSXDOS  SYS"` system-file name + DPB/param block | **clobbered** (fixed §8.61; now `$FF`) |
| `$F2FF-$F33F` | ~60 B | resident code stubs (`$F327`=`LD A,$1A;RET`) + flags | partial |
| `$F345-$F37F` | ~60 B | `$F368` jump table + buffer pointers (`$EF95/$ED95/$EB95`) | partial (`$F368`/`$F36B`→wa_seg) |
| `$F3DC`,`$F3F6` | 2 B | flags (`04`,`01`) | no |
| `$DC80-$DCB2` | 50 B | **MSXDOS.SYS's own** buffer (downstream symptom) | not ours — kernel fills it once the above exist |

## 3. Approach (incremental, clean-room)

Build the disk-ROM-owned structures (everything except `$DC80`, which is the
kernel's) during OUR disk-ROM init — the same place we already lay
`DRVTBL`/`$F195`-DPB/`RES_STUBS`/the `$F368` table — **deriving each field**, never
copying stock's bytes:

- DPB-derived fields (`$F1A8` block, the `$F2DE` param block): compute from the
  inserted disk's BPB via the existing `getdpb`, exactly as we build the `$F195` DPB.
- Constants (`$F2B8` = `"MSXDOS  SYS"`, the `07` prefix, the `$F327` `LD A,$1A;RET`
  stub, the flag bytes): our own `db`, justified from the contract (the system-file
  name is public; the stub is our own RET-class body).
- Pointers (`$F34D`→buffer ptrs, `$F369`→hook bodies): point at OUR addresses/buffers,
  not stock's (`$EF95/$DF57` are stock-layout; ours differ).

`k_607B` stays a `ret` for now (it already returns to `HL` via the `ra==HL`
convention); we only add inline behaviour if the trace shows MSXDOS.SYS needs
`$607B`'s return value, not just the pre-built memory.

## 4. Validation (the cheap experiment first)

1. Build the two highest-value structures first — `$F2B8` (filename, trivial constant)
   and the `$F1A8` DPB-chain — and re-probe (`disk_probe_dosboot_progress.py` /
   `_hang.py`). **Hypothesis:** the `$DA23` hang clears or moves to a new blocker.
   - If it advances: the pre-build approach is validated → add the remaining
     structures one at a time, re-probing after each (true incremental).
   - If not: continue the lockstep memory-diff past `$D7CE` to find the *exact* stale
     cell the derail reads, and build just that.
2. Regression after every step: `make unit-test` (18/18), DSKIO/FILES==CF-3300,
   BLOAD `,R`/plain. The build runs only under the existing DOS `$FF` gate, so Tier-1
   stays untouched.
3. Exact byte-set per structure captured from the oracle at implementation time (the
   `$D7CE` memsnap already has it; derive, don't copy).

## 5. Scope escalation — please read before approving

The incremental slice is bigger than "fill one veneer": it is effectively
**reimplementing the disk ROM's DOS work-area initialisation** (~340 disk-ROM-owned
cells across ~6 structures, with derived fields, our-own code stubs, and pointers
into our layout). Realistically a **multi-session sub-track**, done structure-by-
structure with a re-probe gate after each. It is clean-room-feasible (everything
derives from the DPB or is our own constant/stub) and low-risk to Tier-1 (DOS-gated,
additive). But it is the deepest Tier-2 work so far.

**Decision for you:** (a) approve this incremental plan and I proceed structure-by-
structure under span mode (re-probing after each, queueing decisions); (b) approve
but want a tighter first milestone (just the `$F2B8`+`$F1A8` experiment, then re-sync
on results before continuing); (c) reprioritise — bank the diagnosis and spend effort
elsewhere. My recommendation: **(b)** — do the cheap two-structure experiment, prove
or disprove the pre-build hypothesis, and re-sync on the result before committing to
the whole work-area build.
