# Loop restart — paste-ready state (written 2026-09-12)

A `ScheduleWakeup` loop is SESSION-LOCAL and dies with the session. This file is
the durable half: paste the command in `## The command` below into a fresh
session and the loop resumes exactly where it stopped.

## 🟢 STATE AS OF 2026-09-24 EVENING — THIS IS THE CURRENT ONE. EVERYTHING BELOW IS HISTORY.

**Tree CLEAN, all pushed, head `02eac1ba`.** Since the afternoon hand-off
`6b6d7b49` (SHAs from `git log`): `a49d233f` D-KWUNTIME · `fd27aa59` D-VDPIE
closed · `6f2a1fe5` the shared-buffer audit · `6e1722b7` **D-BUFMERGE** ·
`0ce73534` D-CONTROW · `396a45cb` D-KWTDISK · `119294a5` D-KWTLONG ·
`a4e1c3ff` D-KWTRIG · `2ff996ce` D-RAMFOOT · `d7189a99` its naming + *"All 29"* ·
`9dcd8147` the D-ADDR29 spec · `3dee4024` **D-ADDR29 S1** + D-KNIFENOREAD ·
`04d5e412`/`02eac1ba` PLAY X stack reading (+ the repair of that commit).
**Walls, read from a clean tree at the hand-off: main page 1 8 B + low 5 B = 13 B;
sub p0 434, sub p1 706, disk 7264.** Every ROM-growing slice needs a CARVE first.
**T2: 120 keywords** (`make tiers-md`); the 22 still `T2—` are listed by reason on
the D-KWPROVEN item — most END or REPLACE the run, and CURLIN is measured to be a
DIFFERENT event per machine for them (`listkw` 239×), so no end signal is
symmetric. Treat that group as closed-by-measurement unless a new signal appears.

### 🏗️ JOOST'S RULINGS, 2026-09-24 EVENING — DO NOT RE-ASK

| subject | ruling |
|---|---|
| shared buffer | *"(b) One shared buffer"*, then *"Merge; BDOS out of scope"* — SHIPPED (D-BUFMERGE) |
| RAM addresses | *"All 29"* (D-RAMFOOT's published variables), scratch included |
| D-ADDR29's ✋ | `DAC` FULL (ints at DAC+2, USR reads DAC) · `TEMPST` pool → 10 · `RNDX` now, `ARG` later · N set observable-first — `docs/spec-basic-addr29.md` §4.1 |
| PLAY X shape | *"Tenant walks the chain"* — the MML tenant reads the variable chain in RAM itself (spec-basic-audio-play §7.12); main ~0 B, no carve needed |
| the rig | Joost's RP2040-Zero is **CONNECTED to the laptop since 2026-09-25** (`/dev/cu.usbmodem1101`, running firmware, not BOOTSEL; seen read-only, nothing flashed). **UN-PARKED 2026-09-26 and FLASHED with `tools/rigfw/rigfw.ino`:** headless joystick WORKS (bind `msxjoystick1_config` to `joy1`, which this install leaves EMPTY); headless mouse does NOT reach PAD/PDL. Next: STICK/STRIG rows — the rig item in TODO |

### 🌙 LOOP 2026-09-30 EVENING → 10-01 — READ THIS FIRST (the sections below are older)

**Commits after the day section:** `639e3778` **D-ENGROW0** (the disk ROM stopped
reserving the engine table's unused row 0: +50 B disk boot FRE; the OPEN `s.case`
remainder priced at 165 B and put to Joost) · `e4e46bbf` **D-EOFCAS** (TIER 1: EOF()
on a TAPE opened for input answered Illegal function call; found from Joost's
question "are channels only disk or also tape?") + **D-EOFMODE** (EOF on a disk
channel not open for input is 61) + gate `eofcas-acceptance` · `7c488429`
**D-INPQUOTE** (quoted INPUT fields, funded by four zero-behaviour carves:
D-VDPCB, D-RETTAIL, D-TAILMERGE, D-DEMOTE) + D-INPQUOTE2 filed + **D-PKILL** · then
**D-PKILLGATE** (`make hostkill-check`).
**Walls (`make basic-reloc`, 2026-10-01 ~00:30): main page 1 2 B, low 0 B; sub
p0 18 B, sub p1 376 B.** Main is FULL again — carve before any main-byte item.
🙋 **NEW FOR JOOST:** the OPEN same-file `s.case` row: spend 165 B of disk-machine
RAM on the verbatim-name rule, or pin it as a divergence (TODO, the OPEN item).
🔌 **The rig drops off USB intermittently** (seen twice on 09-30). Board-less runs
CARRY its five rows (Joost 09-26); the last board-backed pin is `7c488429`'s.
➡️ **NEXT, AUTONOMOUS — STEP 10, WHICH NOW HAS A MEASURED INTERFACE AND A DESIGN.**
- `e0e55d70` **D-CHANHOOK** (spec §6.6bb): the CF-3300's channel verbs cross
  at EIGHT claimed cells, the data PER BYTE (`$FE85` out, `$FE8A` in). zerobas
  claims only `$FE5D`.
- §6.6bc is the design that dissolves the old RAM blocker. The channel is a
  37 B MSX-DOS FCB in the disk work area (`disk.rom` already has a BDOS FCB
  layer), and its buffer is the BASIC FCB's 256 B record (D-FCBSHAPE made it).
- If it holds: +195 B of disk RAM, s.case for free, ~800 B of main code out.
- **S10.0 is ANSWERED:** the channel is a record-size-1 MSX-DOS FCB moved by
  256 B block I/O. It changes only at record boundaries, and header +6 is the
  byte position. **Next: S10.A**, now a PROOF, not a rewrite (spec §6.6bc):
  the kernel's canonical WRBLK/RDRND/WRRND re-locate the file from the FCB
  every call, so they are multi-file already. Only `driver.asm`'s BLOAD mini
  layer is single-file. Add a BDOSX case alternating two FCBs, and check which
  create/close/RDBLK entries exist at canonical depth. Then OPEN/PRINT#/CLOSE.
- ✅ **D-WRBLKRS FIXED (WRBLK is a byte transfer; gate `wrblkalt-acceptance`).
  S10.A's write side is done.**
- ✅ **D-RDBLKMULTI FIXED (`73a434d2`) and D-RDRNDMULTI FIXED (next commit):**
  RDBLK and RDRND/WRRND re-find the file by the FCB's name every call;
  `wrblkalt-acceptance` runs `--read --rnd --end 150`. S10.A is DONE.
  ✅ **D-RDBLKSEEK's read side FIXED: 147× → 3.1×** (`k47b2_seek`, FCB-resident
  positioning from +26/+28/+30). D-FOPENRC fixed on the way (`4022a78a`).
  ✅ **D-WRBLKSEEK (a): the 32 KB write went 59× → 8.8×** (`wrblk_seek`,
  `wrblk_fcb_keep`, FMAKE clears +16..31).
  ✅ **D-WRBLKSEEK (b): every FCB dump byte-identical to the CF-3300's.**
  🏗️ **Joost 2026-10-01 "Stamp as 3300":** files are dated 0821h (1984-01-01),
  time 0, as the CF-3300 (gate `savedate-acceptance`).
  A WRITE dates a file too, and COPY carries the source's date (both measured).
  📏 D-DOSDATE and D-CLOSESTAMP MEASURED (`make dosdate-acceptance`, a failing
  row excluded with its reason): the CF-3300's FCLOSE re-dates a written file,
  and its SDATE moves GDATE and the stamps.
  ✅ D-CLOSESTAMP fixed (`close_read`).
  🧱 **disk.rom holes:** the one after `$75A5` is FULL (~43 B left). New
  routines go before `$5FE5` (~1.9 KB), or `$47C1` (1.1 KB). The build says
  "EMPTY" when a region overruns: look for the label past its pin in disk.sym.
  ➡️ **NEXT, by tier: D-DOSDATE (find the SDATE ROM entry first), then S10.B
  (TIER 2).** D-BLKIOPERCALL is TIER 5.
- (was) 🔴 **THE PROOF FOUND D-WRBLKRS (TODO):** our WRBLK is only right at a record
  size of 128. At RS = 1 it allocates 32 clusters for 256 B, while the
  CF-3300 is exact. Fix it first: a byte-offset transfer looping per sector.
  The acceptance test is `disk_probe_wrblk_alt.py` (it needs
  ZEROBAS_BASIC_MACHINE=C-BIOS_MSX1_EU_REPACK_DISK). The roundtrip probe's six
  rs=128 cases must stay byte-identical.
- 🔴 D-CFWSTALL was MY capture timing: the capture fires `step` after RUN, and
  `cap_gap` never moves it, `run_gap` does. omsx_repl documents it; I raised
  `cap_gap` twice and bisected a phantom.
- Main bytes are at 2 + 0; the n-gram TAIL list still has a few 4–6 B pairs.
🔴 **LESSONS TONIGHT:**
• **A GATE MUST NOT KILL WHAT IT DID NOT START.** A `pkill -9 openmsx` copied
from a scratchpad rig into a gate killed the pool's emulators; kwtime read 51/32
rows HANG, and I blamed LOAD in a commit message. Unit COUNT and unit TIMES
across batteries found it. Memory: `a-gate-must-not-kill-what-it-did-not-start`.
• **A BOUNDARY CASE MUST WITNESS ITS OWN GEOMETRY.** D-EOFCAS's first boundary
tape agreed on every cell because LINE INPUT refused the line on BOTH machines;
the second put the LF at byte 253, not 255. Only a `len` slot and a byte dump of
the built tape made the case real.
• **A FILED RULE's LAST CLAUSE IS OFTEN THE UNRUN ONE.** D-INPQUOTE's "the rest of
the field is consumed" was never measured past quote-then-CR; three edges differ.

### ☀️ LOOP 2026-09-30 DAY — READ THIS FIRST (the sections below are older)

**Commits after the night section (`git log eaa63e58..`):** `c5f876fd`
**D-FCBSHAPE S1+S2** (a channel is the reference's 265 B FCB; MAXFILES charges
267 on both machines; disk-engine state in `DSK_ENGTAB` under a boot-lowered
HIMEM) · `c3bf6ed6` **D-CIRCANGLE** (CIRCLE refuses |angle| ≥ 6.283245; the
boundary is not 2π) · `d74789c4` **kwram — the T4 row type** (Joost's ruling of
09-30 in the table above; T4 reads 0 of 159 because (b) fails everywhere on the
same documented cells, which ranks the D-ADDR29 re-homing) · `00ee880b`
**D-ONTRAPMERGE** (ON KEY runs on ON STRIG's loop: main page 1 +35 B) +
**D-VARPTRCH** (`VARPTR(#n)` answers the FCB address; VARPTR level 0 → 3, **no
keyword is at level 0 now**) + D-X5LOG (the excluded five keep a failing log).
**Walls (`make basic-reloc`, 2026-09-30 ~17:30): main page 1 15 B, low 3 B; sub
p0 18 B, sub p1 440 B; disk 6517 B.** Recount before quoting.
🔴 **`bdos-acceptance` exited 2 once in `00ee880b`'s FULL run with NO log (the
runner dropped it), then 12/12 three times alone.** Cause unknown. D-X5LOG keeps
the log now: if it goes red again, read `gate_flakes/x5-bdos-acceptance.log`.
➡️ **NEXT, AUTONOMOUS, by tier:** TIER 2 **STEP 10** (OPEN + channel I/O into
`disk.rom`, approved 2026-09-22; its RAM lever, PAINT's span stack, SHIPPED as
D-PAINTSP) — a DESIGN + PRICING slice first, from a clean tree; it is also the
funding route for main bytes (D-INPQUOTE's note). Then TIER 3 D-INPQUOTE (~30-40
B main) and D-ERRKEEP2's rest, TIER 4 D-FCBSHAPE's LEFT list (FCB #0, header
fields, FILTAB geometry) and the D-ADDR29 re-homing kwram ranks.
🔭 kwram costs ~28 min of battery wall (it sets gates-fast's wall too) — the
reference-replay question is filed under the T4 item.
🔴 **LESSONS TODAY:**
• **A SCANNER THAT MATCHES EXACT SEQUENCES CANNOT SEE TWO LOOPS THAT DIFFER IN
IMMEDIATES.** ngram_sweep priced the ON KEY/STRIG pair at 11 B; merged with the
constants in a register it was 35. Read the top candidates' SURROUNDINGS.
• **A `jr` WITH NO SLACK IS A WALL INSIDE A ROUTINE.** Inserting any byte between
LOF's dispatch `jr` and its target broke the build twice; put new tests AHEAD of
a jr chain.
• **A MEASURED DENOMINATOR IS ONLY AS WIDE AS THE FAULTS ITS BATCH TRIED.** Batch 9
gave VARPTR(#) {13, 52}; a negative channel and a bare `#` add 5 and 2 on both
references.

### 🌃 LOOP 2026-09-29 NIGHT → 09-30 — READ THIS FIRST (the sections below are older)

**Commits after the evening section:** the D-FCBSHAPE S1+S2 DESIGN (spec §7: every
machine accepts `CLEAR 200,&HF380`, so the disk-engine table takes the reference's
shape, HIMEM lowered at boot, table at `TXTMAX − 800`) · **D-INPNUM** (TIER 1:
`INPUT #1,X` was Type mismatch for EVERY number; console `INPUT A` took only int16,
40000 → -25536 silently — both now VAL's parser, strheap op 19) · **D-CHANSWITCH**
(TIER 1: (1) my own D-INPNUM left the blank+CR after a number unread → `1 0 2 0`,
fixed in the seqio tenant with a PEEK; (2) a channel switch inside FOR/GOSUB wrote
the 306 B context OVER the frame — `sh_chan_addr` used varceil's CSP clamp, now
`strheap_chantab`) · **D-INPSTR** (TIER 1: a string field's leading blanks are not
data). Filed: **D-INPQUOTE** (TIER 3, quoted fields, ~30–40 B main).
**Walls (`make basic-reloc`, 2026-09-30 ~04:00): main page 1 12 B, low 3 B; sub p0
18 B, sub p1 524 B.** Recount before quoting.
🔴 **ALL THREE TIER 1 BUGS WERE FOUND BY ACCIDENT, testing D-FCBSHAPE's frame
hypothesis** — a probe for one thing that could not read its own answer. The class:
[[a-reader-is-tested-by-what-it-leaves]] (new memory).
➡️ **NEXT, AUTONOMOUS:** main is scarce again, so **a carve by S0's pattern** (move
pure copy/compute main code into sub page 1 behind a tenant op; the n-gram scout
finds nothing in main), then **D-FCBSHAPE S1+S2** (~23 B main: boot `HIMEM =
min(HIMEM,TXTMAX)` ~8 B — disk init runs BEFORE main's store, so without it the
lowered HIMEM is overwritten — and `VARPTR(#n)` ~15 B), then D-INPQUOTE.
🙋 **Still Joost's:** D-DIMRESERVE's evaluator rewrite · D-MKIREUSE's rule conflict ·
the older list in TODO.

### 🌆 LOOP 2026-09-29 AFTERNOON → EVENING (older)

**Commits (`git log 83bdfe74..`):** `ac9ca210` D-NOASTOFOLD + **D-KNIFET3** (the knife took
`PROVES-T3:` error rows as connectedness witnesses — 9 keywords, BSAVE BLIND) · `8f900589`
**D-DIMRESERVE measured** (the DIM-edge gap is the EVALUATOR's stack: 147 B a statement here
vs 79 B on the VG-8020, 36 B per expression entry walking all 12 precedence levels) ·
`673271c4` **D-CPY18** (sub page 1 **1 → 699 B**: the math tenants' 162 record copies folded
into entry points; fp_atan's private copy of the copy routine gone; bit-identical A/B) ·
`0bfea44f` **D-FCBSHAPE S0** (channel save/load bodies into the FAT tenant; main page 1
**0 → 41 B**) · then **D-OPENSAME** (a file open on another channel is 54, as on the
CF-3300 in every mode; main 41 → 29 B).
**Walls (`make basic-reloc`, 2026-09-29 evening): main page 1 29 B, low 1 B; sub p0 9 B,
sub p1 648 B; disk 6522 B (largest hole 2046).** Recount before quoting.
🙋 **NEW FOR JOOST (in TODO, both 🙋):** (1) **D-DIMRESERVE** — rewrite `eval`'s precedence
levels as a climber (the per-statement stack economy, also a T5 speed lever; main code);
(2) **D-MKIREUSE** — its filed fix puts the rule's part 2 (TIER 6 spends no main bytes)
against part 3 (no private copies); which yields?
➡️ **NEXT, AUTONOMOUS:** TIER 4 **D-FCBSHAPE S1+S2 together** (`docs/spec-fcbshape.md` §6:
the DISK and NODISK machines share images, so the layout is ONE runtime design —
265 B blocks, `FILTAB`, header fields, the disk-engine state's fixed table behind the +1
pointer; VARPTR(#n) needs main bytes, 29 exist) → TIER 5 → TIER 6 → apparatus.
🔴 **LESSONS, EACH COST A MISS TODAY:**
• **A SKIP THAT NAMES ONE TAG MISSES ITS SIBLING TAG.** The knife's error-row skip named
`PROVES-T6:`; `PROVES-T3:` rows then became witnesses (third site of the same class).
• **A SCANNER'S COUNT IS A CLAIM — MAKE THE EDIT REFUSE ON IT, AND CROSS-CHECK IT.** D-CPY18's
first scan missed four sites; the edit script refused, an independent awk pass agreed with
the script to the site. Alias the buffers by ADDRESS (HORNER_G = SQRT_X was missed once).
• **A STORED ROW's LINE NUMBERS ARE THE PACKING's, NOT THE STATEMENT COUNT** (`as_stored`
packs ≤34 chars): `ON ERROR GOTO 60` read `Undefined line number` on BOTH machines —
SUPPORTED for the wrong reason.

### 🌙 LOOP 2026-09-28 ~15:00 → 09-29 — READ THIS FIRST (the sections below are older)

🏗️ **JOOST'S RULINGS 2026-09-29 — DO NOT RE-ASK:**
| subject | ruling |
|---|---|
| VARPTR(#n) | *"agree, go with (c)"* — built with the TIER 4 RAM re-layout of channel storage, never standalone; the item is ⛔ BLOCKED on it |
| T3 rung | *"go with (a), then real T3 rows for the 24"* — T6✓ implies T3✓ (`tier_table.proven_rungs`); level 3 32 → 121, level 2 113 → 24; the 24 get real `PROVES-T3:` rows next |
| T3 for REM END STOP CLS LLIST | *"go with (A)"* — declared not applicable (`tier_table.T3_NA`, rendered `T3∅`); level 2 is empty, level 3 = 145 |
| T4 row type (09-30) | *"agree with all three recommendations, build it"* — (b) STRICT (same documented-cell set + final values), (c) economy SHOWN never ticked, the reference's undocumented cells REPORTED not ticked; the reference side is CACHED (*"once we know what memory reference uses, we don't need to measure that again"*). `make kwram` |
| error checks | *"yes, record the rule"* — (1) at a SHARED chokepoint or FILED WITH ITS PRICE, never per-command; (2) TIER 6 spends NO main bytes; (3) no private copy of an existing routine to dodge a wall. Two cleanups filed under it: D-MKIREUSE, D-NOASTOFOLD. Memory: `error-checks-at-shared-chokepoints` |


**All pushed, head `3146e8d6`.** Commits (`git log 780d1b66..`): `e7d13dcd` D-COPYWILD
corrected · `2b4ecd16`/`7813db7c` **T6 batches 9–10 (105 → 116)** · `370ce54b` D-WAITMASK ·
`f0b3a7c3` **D-NEWARG** (`20 NEW 1` ERASED the program) · `295b767b`/`10ff2ad3`/`b46bf8ca`
**the type-ahead T2 method** (D-KWT2TA/RESP/RIG: UNTIMEABLE 498 → 6) · `00c76337` **D-SETTLEKEY**
(a boot-per-case `run_cases` piled every case's marks under key 0) · `ca76bbeb`
**D-CASRELOCK + D-CLOADPROG** (TIER 1 ×2: a second file on a real tape would not load;
CLOAD in a program ran on at a stale cursor) · `11981839` D-VARPTRFCB measured ·
`6a78195d` **D-CASSAYPROG** · `4b0b1266` **D-DSKFSLOW** + D-KWTRATCHET filed · `3146e8d6`
**D-COPYWILD** autonomous half.
🎯 **JOOST'S 09-28 PRIORITY IS MET AS FAR AS IT CAN GO WITHOUT HIM: LEVEL 1 IS EMPTY.**
Level 0 = VARPTR (🙋 D-VARPTRFCB: `VARPTR(#n)` is a 265-byte-stride FCB layout on both
references — re-lay channel storage, which is TIER 4 work, or nothing) + the N/A
keywords. Every other keyword is at level 2+.
**Walls (`make basic-reloc`, 2026-09-29): main low 1 B + page 1 0 B; sub p0 9, sub p1
1; disk 6892 (largest hole 2531).** 🔴 **Main and sub p1 are FULL** — the last three
fixes were placed in `disk.rom` on purpose (zero main bytes); anything that must
live in main needs a carve first (`scratchpad/jr_mapper.py` found only 3 on 09-28).
🙋 **OPEN FOR JOOST:** D-VARPTRFCB (above) · D-COPYWILD's multi-match (5 today; the
reference never returns) · everything older still listed in TODO.
➡️ **NEXT, AUTONOMOUS, by tier:** TIER 3 D-DISKERRS' remainder (D-ERRKEEP2's LOAD/MERGE/
ASCII-LOAD hooks — the witness needs a READ failure while the open file's sector still
reads, i.e. a crafted image; OPEN's 54 is main bytes) → TIER 4/5 → the 27 TIER 6
items → apparatus (D-KWTRATCHET is new and cheap: only 2 of 825 OK rows sit above 6×).
🔴 **LESSONS, EACH COST A MISS TODAY:**
• **A WITHDRAWAL IS A CLAIM TOO.** D-CLOADSKIP was withdrawn on "the fixture was
unfaithful" and its replacement was taken as faithful on the word of OUR writer
(`save.asm`). CSAVE writes the end-link + SEVEN `$00` on all three machines; nobody had
read the reference's tape. Two TIER 1 bugs hid behind it.
• **A ONE-SIDED TIMING IS A BEHAVIOUR QUESTION BEFORE A HARNESS ONE.** I widened kwtime's
pass 2 for CLOAD's REF-ONLY-MISSING; the raw readings showed zerobas had REACHED its END
mark — a real path difference (D-CLOADPROG). The widening was reverted unused.
• **A FILED CAUSE CAN BE RIGHT IN SPIRIT AND WRONG IN MECHANISM.** D-DSKFSLOW said "the
disk is touched before the argument is checked"; the bad-DRIVE check was always first —
the slow two were the evaluator's DEFERRED errors (FPERR). Time the controls first.
• **A per-half steadiness test cannot work at 2–4 counts a half** (openMSX's leader):
any compare shifts the next edge. D-CASRELOCK's fix is the lean edge count, longer.

### ☀️ LOOP 2026-09-28 ~01:00 → ~15:00 — READ THIS FIRST (the sections below are older)

**All pushed, head `94e0e612`.** Commits (`git log 5fbeb280..`): `f91f72ea` D-DRVNAME
+ D-NAMEEXIST · `6918e1bb` D-SEQEOF filed · `8212cb58` **D-KILLOPEN** + **D-ERRKEEP** ·
`5da5c0ae` **D-SAVECOLON** (SAVE/BSAVE/BLOAD ended their LINE; `SAVE"X":PRINT` never
saved) · `3f478c37` **D-PADWIN** (Joost's ruling below) · `2ef751fc` **D-COPYNAMEOPEN** ·
`084a714f` D-CARVESEQ (main 11 → 42 B) · `17576a9e` **D-SEQEOF** (Ctrl-Z / LF / 55; the
`IF EOF(1)` loop read one line too many) · `6b24106a` **D-WPROTECT** + **D-SAVEOPEN** (no
disk WRITE error ever reached BASIC — one `cp 0` in our driver; and SAVE with a file
open wrote NOTHING) + gate `wprotect-acceptance` · `ea50a6fe` D-COPYWILD measured ·
`94e0e612` its correction (see lessons).
**T1 140 → 145, T6 102 → 105.** **Walls (built 2026-09-28 ~15:00): main low 6 B +
page 1 2 B; sub p0 9, sub p1 5 (the seqio tenant took 127), disk 7055.** Main AND
sub p1 are nearly full again — carve before any growing slice.
🏗️ **JOOST'S RULING 2026-09-28 — DO NOT RE-ASK:** *"as pad is very much a leaf
command it makes sense to have a stored verdict, having it go invalid on any rom
change seems harsh"* — PAD's switch carries its windowed verdict
(`scratchpad/kwsweep-window-carry.json`, `NEEDS-WINDOW:` rows), warning only when
`gtpad`'s instructions change.
➡️ **NEXT, by tier:** D-COPYWILD's autonomous half (single-match copy + no-match 53;
the multi-match HANG is a question for Joost, in the item) · D-ERRKEEP2's rest (LOAD /
MERGE / ASCII-LOAD / DSKF hooks with a file open — needs an error source that is not
write protect, e.g. an eject mid-program) · OPEN of a busy channel / of an already-open
file (54: MAIN code, ~19 B, needs a carve) · D-FORFAST (TIER 5, main bytes) · more T6
enumeration.
🔴 **FIVE LESSONS FROM TODAY:**
• **A NEVER-COMPLETING REFERENCE IS A FINDING, NOT A TIMING BUG** — wildcard COPY of 2+
  files: no reading at 20/90/240 s and a blank screen; ask a longer window ONCE, then
  dump the raw screen before assuming capture timing.
• **THE COMMIT WENT IN BESIDE ITS VERDICT** — `ea50a6fe` was sent in the same parallel
  tool batch as the read of its gate result, and pushed RED claiming green. Never batch
  an irreversible act with the check that gates it (memory
  `never-batch-the-commit-with-the-verdict`).
• **A PROBE'S "want" CAN BE AN UNASKED ASSUMPTION** — `disk_probe_eof.py` Case B wanted
  EOF -1 after a second LINE INPUT past the end; the CF-3300 says `Input past end`. Its
  reference half had only ever run Case A.
• **FOLLOW A SWALLOWED ERROR UP WITH BREAKPOINTS ON OUR OWN ROM** — `wptrace_probe.py`
  found the `cp 0` in three rounds (driver sees ST_WP → DSKIO returns Cy=0 → the
  offending instruction), and the third round exposed D-SAVEOPEN by showing NO write
  reached the drive at all.
• **A kwsweep row can be pushed out of the reference's capture window by rows AHEAD
  of it** — `t8namerenameopen` (four file ops) read the bare function-key bar after four
  new rows were inserted before it; make disk rows short.

### 🌙 LOOP 2026-09-27 EVENING → 09-28 ~01:00 — READ THIS FIRST (the day section below is older)

**Tree clean, all pushed, head `4dbb6dfb`.** Eight TIER 1 fixes and T6 75 → **102
of 159**. Commits (SHAs from `git log 3ba7e2de..`): `2f19bed0` D-PAINTSP ·
`d5ce46ef` GOSUB 8→7 priced (back to Joost) · `ba67fdea` D-CARVEFP (sub p1 0 →
266) + `docs/reference-stack-frames.md` (Joost's GOSUB study) · `bbee4856`
D-DIMRESERVE bisected · `601a44c9` **D-STACKFLOOR** (the evaluator had no stack
floor: a nested formula overwrote an array DIM'd to the edge) + **D-SNDVAR**
(`SOUND 8,V` wrote the wrong register) + **D-PADTRACE** (the touchpad, traced on
the VG-8020's PORTS with Joost's rp2040-zero, windowed) · `755a2bf3`
**D-FORFLOAT** (FOR/NEXT was int16: `STEP .5` never ended) funded by D-CARVECAS
(the cassette ASCII reader became the `casget` tenant, +112 B page 1) ·
`f5040021` **D-CAS4BLK** (the tape motor never stopped between blocks; its probe
is a gate now) · `8ab5e977` **D-GFXERRMSG** (an error in SCREEN 2 printed into
the bitmap) + T6 batch 7 · `324f36df` T6 7b · `4dbb6dfb` **D-RUNCLOSE** (RUN
never closed open files) + T6 batch 8.
**Walls (clean build 2026-09-28): main page 1 8 B, low 2 B, sub p0 9 B, sub p1
158 B, disk 7264.** Carves found tonight: `ngram_sweep --main` still pays in
small pieces (D-NEGDE: an open-coded negate at 5 sites, +12 B); `evict_scout.py`
named the cassette reader.
➡️ **NEXT, by tier:** D-DISKERRS (TIER 3 — KILL of an open file, NAME onto an
existing file, re-OPEN of a busy channel, `Q:` accepted, Input past end never
raised; the disk handlers live in `disk.rom`, 7264 B free) · D-FORFAST (TIER 5 —
NEXT 2.37× since D-FORFLOAT; the int fast path needs ~20 B, a carve first) ·
D-DIMRESERVE (TIER 4, now economy only) · the T6 divergences (D-CIRCANGLE and
friends, TIER 6) · more T6 enumeration (57 keywords left; RUN, editor commands
and keyboard-blocking forms need other shapes).
🔴 **FOUR PROCESS LESSONS FROM TONIGHT, all written down where they bite:**
• a check for "is it running" that greps the TYPED command line reads a live
  job as dead on this Mac — memory `a-liveness-check-that-greps-the-command-line`;
  a bare-`&` knife chain survived and overlapped a second one;
• a NEW disk batch is run PER CASE on both machines before its rows join the
  batched sweep, and only agreeing pairs become rows — a wrong row poisons its
  neighbours (that is how D-RUNCLOSE was found);
• a new FOR fix slowed the default loop and broke kwsweep delay rows by TIME,
  not by logic — delays in rows are `%` loops now;
• kwknife has THREE witness enumerators; all three skip PROVES-T6 rows now.

### ☀️ LOOP 2026-09-27, DAY (after the rulings) — READ THIS FIRST

**T6 is BUILT and 75 of 159 keywords prove it** (D-KWT6: `tools/kwerrset.py` =
the denominator, kwsweep `PROVES-T6:<code>` rows, `scratchpad/t6enum_probe.py
--batch=1..6` = the enumeration; each batch's `.out` is the provenance).
Commits: `be4becc2` S1 · `c013ffcc` b1 · `0bbb86be` b2 · `eb6f4940` b3 (disk
functions on the CF-3300) · `d42bfc78` b4 (+ S36z: rows attributed by declared
SUBJECT) · `f5073b4d` b5 · `8b622667` **D-LETNUM** (`LET 5=1` corrupted and
rebooted zerobas; + kwknife never takes a T6 error row as its witness) ·
`94c45b58` **D-CLEARFIT** (`CLEAR 30000` HUNG zerobas) funded by **D-CARVEFO**
(`fopen_cross`, +26 B) + b6.
🔴 **THE ENUMERATION IS A BUG FINDER:** 16 divergences filed today as TIER 6
items (D-STRINGEMPTY D-TANBIG D-MKIRANGE D-MKEXTRA D-DSKFRANGE D-MIDEXTRA
D-READOVF D-ERRORARG D-BAREEXTRA D-POSDUMMY D-IFGOTOBARE D-CLEAR3ARG); two
were machine-damaging and are FIXED (LET, CLEAR).
⚠️ Not enumerable by the trap probe: VAL/FRE (forms are argument content),
RESUME (untrappable), WAIT (blocks), WIDTH (SCREEN 1 reading). Disk-only
keywords use `--batch=3`'s CF-3300 pairing.
**Walls (2026-09-27, after D-CLEARFIT): main page 1 8 B, low 5 B, sub p0 16 B,
sub p1 0 B.** ➡️ NEXT by tier: TIER 3 PAINT span stack (ruled: grow below SP —
needs a sub carve), TIER 4 GOSUB frame 8 → 7, then the TIER 6 fixes (most need
a few bytes; `scratchpad/ngram_sweep.py --main` found today's carve).

### 🏗️ JOOST'S RULINGS 2026-09-27 (morning, his "ask me in detail" pass) — READ THIS FIRST, DO NOT RE-ASK

The queue the night loop stopped on is OPEN again: every 🙋 in TIERS 1–6 is ruled.

| item | ruling |
|---|---|
| D-FCBSHAPE §4 | **(a) the fixed disk table** — disk build pays ~800 B boot `FRE(0)` |
| duplicate `OPEN` of one file | **fold into D-FCBSHAPE** — refuse like the reference once the FCB holds the name |
| RAM frame economy | **shrink ours only** → GOSUB 8 → 7 B (FOR and FN are already smaller; the question wrongly listed FN) |
| PAINT span stack | **re-architect: grow below SP** — frees the 360 B array; unblocks step 10's RAM |
| `PUT` directory stamp | **faithful: stamp at CLOSE** — knowingly gives up D-PUTCUT's crash safety |
| T6 rung | **the reference's errors, per documented form** (code AND line) |
| `OPEN"f"AS 1` / `NAME..AS 5` | **fix it**, carve first |
| DATA literal strings | **point at program text** (copy out before edit/NEW/load) |
| DEF FN actual scope | **the pool route** — re-run 503-vs-505 on today's ROM first |
| `String too long` precedence | **the ownership refactor** |
| `CONT` in a program | **add the line** in-program; keep the prompt's `print_msg` |
| FIELD `e.val` | **keep ours** (stated divergence, closed) |
| `LOAD"CAS:"` tokenised tape | **keep the feature** (stated divergence, closed) |
| `PLAY(n)` transient | **decline** (closed) · VALTYP at cold boot: **keep declined** (closed) |
| PAD touchpad | **"I'll tell you when"** — wait for him to plug the board in and say go |

Four TIER 2 🙋 markers were STALE when read (step 9/10's, the `$FE5D` one —
closed as superseded — the RAM map's, and the hook-FAT hazard's); re-marked.
⚠️ Almost every ruled item needs ROM bytes, and the walls are main page 1 5 B,
low 5 B, sub p0 16 B, sub p1 0 B (clean build 2026-09-27): **carve first**,
lowest tier first — T6's row type (TIER 1) and GOSUB's frame (TIER 4) lead.

### 🌙 LOOP 2026-09-27, 02:00 → (after the section below) — READ THIS FIRST

Shipped: `2c8343ad` rigcap/cf3300_arch headless + the sweep refuses a windowed
launch · `acbe7b2d` **D-S2BHEAP** (TIER 4: the string heap's edge is given back;
strtemp DIFF 4/8 → 1/8, the one left is zerobas holding LESS) · `33bac256` two
stale markers (PUT's retracted 24 s; PAINT's stack is already a filed 🙋) ·
`bf0f03e7` **D-SAYBLIND** (a `--say` row with no reading anywhere is refused;
`<NO ECHO>` is in `BAD`) · `10bcb617` strtemp's pin follows D-S2BHEAP ·
`2a794a76` **D-KNIFEBASE** (the knife deletes all four built ROMs first).
🔴 **`2a794a76`'s body says "+ the excluded five" and they had NOT run** — FULL
came from the every-5th rule, which does not add them. They were run straight
after on the unchanged tree: all five exit 0. Not amended (pushed history).
**Walls (clean build 2026-09-27): main page 1 5 B, low 5 B, sub p0 16 B, sub p1
0 B.** Every ROM slice needs a carve first.
➡️ **QUEUE:** TIERS 1–5 hold nothing autonomous without a carve or a ruling —
PUT's write-through cache needs a carve in main p1 AND sub p1; the sub-side
`sh_pop_top` reclaim (comparisons, concat operands) needs ~20 B of sub p0 and
has no separating row yet. What is left 🤖 is APPARATUS.
**Later the same night (apparatus):** `92668b33` **D-CASCUT** + `6a2881ca`
**D-SSTROW** — all four sites the D-DUPSPAN2 alias audit named are now reached
by knife-proven rows or gone; `6a2881ca` also **D-PLANCHILD** (the gate planner
follows child probes run by path — it had planned 0 suites for a
`basic_probe_string.py` edit) · `4e22c989` DEF FN knife roster 12 → 14 (K-RK1
moved 0 of 73 and falsified two comments) · `680da6b4` the predecessor-walk
item priced at 0 bytes.
🛑 **LOOP STOPPED 2026-09-27 ~06:30 — THE AUTONOMOUS QUEUE IS EMPTY IN PRACTICE.**
What remains 🤖 is a COST decision (`--say` widening, six synthesised refusal
checks), a wide-blast fixture change (an ASCII `.BAS` on the test image for
`merge-alive`), evidence-waiting (`refcache-check`'s calendar red), or priced
at ~0 (the 24 undecidable ENDIF spans). None is worth doing unattended.
🙋 **FOR JOOST:** D-FCBSHAPE §4 · the RAM frame economy (FOR 25 vs 11 B) ·
PAINT's span stack · PUT's directory-stamp trade · T6 · the PAD touchpad fix
(needs the rig plugged in + a window).

### 🌙 LOOP 2026-09-26 → 27 (after the day section below) — READ THIS FIRST

Shipped by the loop: `a4528b25` D-HOMEKEY (C-BIOS patch #4; island 1 now at
`$1ADB`) · `e5857ecf` D-INSBOTTOM · `45791719` the msxtest temp-name flake ·
`8639d4a0` D-FASTPIN (a red post-check re-runs after a recovered retry) ·
`9d550bd4` RAM control-flow economy measured (FOR 25 vs 11 B, GOSUB 7 vs 8, FN
14 vs 13 — 🙋 filed) · `290f765e`/`39eefeae`/`5adf2a67` D-FCBSHAPE measured +
designed (🙋 the disk build's engine-state home, spec §4) · `95f28720` division
loop −3.5% (SQR is ~4× FASTER than the VG-8020; DIVISION is 3.9× slower) ·
`8af1762d` PAINT mask table (flood 2.10× → 1.96×).
⚠️ **Walls (clean build 2026-09-26): sub page 1 was 0 B, sub page 0 40 B, main
page 1 26 B, main low 5 B.** Anything sub-side needs a carve first.
➡️ **QUEUE:** TIERS 1–3 hold nothing autonomous (PAD needs the board; the rest
🙋). TIER 4: D-FCBSHAPE and the frame economy wait on Joost. TIER 5: the
structural speed levers (packed BCD for division, the FOR/GOTO working form,
PAINT's read cache) all need a carve or a design. What is left 🤖 is
APPARATUS.

### ☀️ DAY 2026-09-26 (INTERACTIVE, JOOST PRESENT) — READ THIS FIRST

Shipped, all measured against the VG-8020 and pushed: the RP2040-Zero rig
(`68482841` firmware, `d02f5777` STICK/STRIG rows — both NO KNOWN GAP),
`df970b0a` windowed PAD findings, `57c1476f` **D-TYPEBLIND** (keys lost while
tokenising), `8c743e78` **D-CURSORBLOCK** (the block cursor), `598c51f0`
**D-SCR1PROMPT** (the prompt keeps SCREEN 1), `3422ff3f` **D-KEYWIDTH** (key row
follows WIDTH), `d88e5e3c` rig rows CARRY their verdict, `e2079884`
**D-INSMODE** (INS/DEL/BS shift; C-BIOS patch #3 for the INS/DEL key codes).
🔌 **THE RIG IS UNPLUGGED AND STAYS SO** — it crashes a game of Joost's. Rig rows
carry from `scratchpad/kwsweep-rig-carry.json`; ASK before any run that needs
the board (windowed PAD work, STICK/STRIG changes), and say when he may unplug.
⚠️ **Walls (clean build 2026-09-26): sub page 1 was 11 B free** — the next sub
page-1 slice needs a carve first.
➡️ **OPEN, TIER 1:** D-HOMEKEY (HOME is CLS on C-BIOS), the PAD touchpad
switch/coordinates (needs the rig + a window). TIER 3: D-INSBOTTOM.

### 🌙 NIGHT 2026-09-25 → 26 — READ THIS FIRST, IT SUPERSEDES EVERYTHING BELOW

Joost ruled three questions on 2026-09-25 (recorded in TODO): **drop DETOKBUF**
(done), **boot HIMEM = TXTMAX, truthful** (done), **stop the D-ADDR29 N set at
the observable cells** (done — the evaluator scratch is a stated divergence).
Shipped since midday: the RAM-address arc (VARTAB/ARYTAB/STREND, ATRBYT,
TTYPOS/FNKSWI, RNDX, TEMPST/TEMPPT + D-TEMPPOL, DAC/USR + FAC at DAC, HIMEM)
and **D-DETOKBUF S1–S3** (`b891e117`, `f1c4bde7`, `364e3fb4`): LIST renders
through a 96 B window with token resumption, the GC sorts in the free variable
area, `TXTMAX` = `$E000`. **`FRE(0)` gap to the VG-8020: −4750 in every state
(was −6030); vs the CF-3300 the disk build now LEADS.**
**Walls (clean build 2026-09-26): main page 1 105 B, low 5 B; sub p0 292 B.**
🔴 LESSONS: a derived equate (`PU_NUM = DETOKBUF+256`) is a user no grep of
code finds — the assembler did; re-rendering per window was quadratic (the
battery's `linemax` caught >8 s); a comment edit mid-knife voids the run.
The RP2040-Zero is connected (`/dev/cu.usbmodem1101`) and flashed as the rig (2026-09-26).

➡️ **SHIPPED LATER THAT NIGHT:** `b2b5ad38` D-KEYCLS (the key line survives
CLS/SCREEN/WIDTH; the SHIFT→F6..F10 inference REFUTED) · `43758524` D-KEYSCR1
(the key line in SCREEN 1) · `d8b1365e` D-SLICEOOM (slices of a scalar
allocate only the result) · then its ARRAY half (offset temps, 0/13).
**Walls (clean build 2026-09-26, before the array half): main page 1 61 B, low
1 B; sub p0 175 B — the array half then spent 110 B of sub p0.**
➡️ **QUEUE, lowest tier first:** (1) TIER 4 — S2b's heap half (a released
temp body at FRETOP is not returned), low observable value; (2) TIER 5 speed —
what remains is STRUCTURAL (a working form across chained expressions; the
float suites must hold it). TIER 6 stays parked.

### ☀️ MIDDAY 2026-09-25 — READ THIS FIRST, IT SUPERSEDES THE NIGHT BELOW

Since `cc30d988`: `1de440df` lever A designed · `8cb5d21b` **CHRGTR at `RST
10h`** (50 sites) · the next commit **OUTDO at `RST 18h`** (14 sites; C-BIOS's
boot patched so H.OUTD is a RET — it was C-BIOS's OUTPUT, hook + `pchar` would
print twice). **LEVER A IS DONE AS SCOPED** (SYNCHR deferred, DCOMPR no idiom).
**Walls (clean build 2026-09-25): main page 1 261 B, low 8 B; `$0160` island
129 B free, font island 75 B free.** USR stubs calling `rst $10`/`$18` match
the VG-8020 5/5 (`scratchpad/rstvec_probe.py`).
🔴 **TWO APPARATUS LESSONS, BOTH FIXED:** (a) the unit harness never boots, so
hooks were `$00` — `tests/msxtest.py` `_seed_hooks`; (b) **D-KNIFESTALE**:
`make basic-reloc` refreshes the `.sym` but NOT the merged ROM, and the knife
planted a fresh `stmt_error` into a stale ROM — a whole pin of false verdicts
that LOOKED healthy. kwknife now rebuilds first. `rst` is now a call edge in
`check_tenant_closure.py` AND `check_dead_code.py` (fix 13).

📏 **THE 6030 B, SCOUTED** (`scratchpad/ramlayout_probe.py`): it is mostly a
DISKLESS story — zerobas's layout is the same in both builds, so against the
CF-3300 the gap is only **645 B**. zerobas's 6778 B above its free area =
workspace 4992 + `DETOKBUF` 1280 + channels 306 + strings 200. 🙋 Levers priced
for Joost in TODO §"COMPARE RAM *USAGE*" (drop `DETOKBUF` +1280 B both builds;
NODISK re-layout ~942 B; shrink tenants; accept). And a defect: **D-HIMEMLIE**
— `HIMEM` reads `$F380` while zerobas occupies `$DB00..$F37F`.

D-HIMEMLIE measured (`scratchpad/himem_probe.py`): `CLEAR`'s address rule
already MATCHES (DIFF 0/12; both references allow up to `$F380`); what is left
is the boot VALUE (true `$DB00` vs the VG-8020's `$F380`) — 🙋 Joost's.

✅ **D-ADDR29 S2 SHIPPED** — `VARTAB`/`ARYTAB`/`STREND` published (0/9 vs the
VG-8020; main 3 B, sub 3 B); `FRETOP`/`MEMSIZ` split out as S2b.
**Walls (clean build 2026-09-25): main page 1 261 B, low 5 B; sub p0 431 B.**

✅ **S2b measured** (the 12 B = zerobas copies literal arguments into the heap
and keeps released temporaries — a string-engine policy, not an equate) and
✅ **S3 `ATRBYT` shipped** (6 B; `COLOR` sets it, 9/9). S3 found **D-KEYBOOT**:
zerobas BOOTS with the function-key line hidden (VG-8020 shows it).

✅ **D-KEYBOOT FIXED** — zerobas boots with the function-key line shown
(`scratchpad/keyboot_probe.py`, 0/6 on both builds vs the VG-8020; 22 B).
**Walls (clean build 2026-09-25): main page 1 233 B, low 5 B.**

✅ Since then: the N set (`TTYPOS`/`FNKSWI`, `b7501cd2`), `RNDX` (`a7d46493`),
`TEMPST` measured and reverted (`910966d0`), D-TEMPPOL part 1 (`9caa9383`).

✅ **D-TEMPPOL part 2 + `TEMPST` → 10 shipped** — the pool is the published
TEMPST, 0/51 vs the VG-8020. **Walls: main page 1 190 B, low 5 B; sub p0 400 B.**

➡️ **QUEUE, lowest tier first:** (1) `DAC` full (spec §4.1 — ints at `DAC+2`,
USR reads DAC; the biggest remaining D-ADDR29 item, measure first); (2) S2b's
heap half; (3) D-STOPTAP's 1-frame tap. 🙋 Two questions for Joost stand
(the 6030 B lever; D-HIMEMLIE's boot value). 🙋 **TWO QUESTIONS FOR JOOST** when the autonomous queue empties:
the 6030 B lever, and D-HIMEMLIE's boot value. Re-scan TODO markers first.

### 🌅 NIGHT 2026-09-25 — READ THIS FIRST, IT SUPERSEDES THE QUEUE BELOW

Head `cc30d988`, tree clean, all pushed. Since `a6d0da85`: `9e939cb5` goal (a)
measured (a constant **6030 B** less free memory; economy byte-identical) ·
`582fa8e2`/`fc86b2c1`/`d4ee80bf` the filed-row triage · `f2df6d3f`/`d496b4ab`
D-STOPTAP measured + pinned · `c94153c5`/`664bc47f`/`e99793b4` MAKING ROOM
(Joost: *"Clearly reference fits everything in 32k"*; ruled **B first, then A**)
· `84e69227` + `cc30d988` lever B's first tenants · `888b8d47` **D-STOPTAP
FIXED** (16/16 fine steps) and the **triage DONE**.
**Walls (clean build 2026-09-25): main page 1 140 B, low 0 B; the font island
(`$1ACF`) 165/240 used; the `$0160` island (160 B) EMPTY.**
🔴 **LEVER B'S BLAST RADIUS, LEARNED:** pasmo's image now starts at `$1ACF`; any
tool that assembles `basic/main.asm` ITSELF must read the base from the image
length (`tests/msxtest.py`) or cut it with `tools/split_islands.split()`
(`tests/test_msgenc.py`, `tools/check_switch_builds.py` — the FULL battery found
the last one). A new `basic/*.asm` needs a clean-room attestation and a DEPS entry.

➡️ **QUEUE, lowest tier first:** (1) MAKING ROOM lever A — the `RST 08h..28h`
vectors honouring the published `SYNCHR`/`CHRGTR`/`OUTDO`/`DCOMPR`/`GETYPR`
contracts; a DESIGN first (which of our sites' flag uses fit each contract);
(2) more island tenants for `$0160`; (3) TIER 4: scout the 6030 B (Joost: scout
first), then D-ADDR29 S2 (the pointer chain) with the bytes lever B freed.

### 🌙 LATE EVENING 2026-09-24 → 25 (after the hand-off above was written)

`ef8be6cd` PLAY X shape ruled · `b7864309` **D-PLAYX12 — PLAY X SHIPS** (main
0 B; 13/13 rows match; ERR 7 on self-reference; PLAY level 0 → 2, 10/10 forms) ·
`9316425d` **D-OKSTORE** (no prompt after a stored line / deleted line / empty
Enter, as the reference; 2/5 → 5/5), funded by 9 `jp`→`jr` + promoting
`skipsp_test` into the low region.
🔴 **MAIN IS FULL: page 1 1 B, low 0 B** (clean build, 2026-09-25). Routes left
(`scratchpad/pair_scout.py`, `evict_scout.py`, `jr_mapper.py` — re-run them): D
is ~0 now, pairs ~2 B; the only BIG route is evicting a HOT leaf to sub page 1
(423 B free after PLAY X), which costs speed — **Joost's call, not asked yet.**

### ➡️ THE QUEUE NOW (re-scan; lowest tier first)

* ~~**TIER 1 `PLAY` `X<var>;` — BUILD IT**~~ SHIPPED (`b7864309`).
* 🏗️ **MAKING ROOM — RULED 2026-09-25: no eviction (*"Clearly reference fits
  everything in 32k, we should be able to fit things better"*); build lever B
  (zerobas code islands in C-BIOS's ~400 B of padding) FIRST, then lever A
  (the `RST 08h..28h` vectors honouring the published contracts, ~420 B).**
  TODO §"MAKING ROOM IN MAIN". D-STOPTAP (pinned: re-fire after 41 frames,
  then every 3) and D-ADDR29 wait on it. 🙋 also open: the 6030 B free-memory
  gap — Joost said SCOUT WHERE IT GOES first (TODO §"COMPARE RAM *USAGE*").
* **TIER 4 D-ADDR29**, spec §5 order: S1 ✅ · **S2 the pointer chain**
  (VARTAB/ARYTAB/STREND + FRETOP/MEMSIZ, moved TOGETHER — D-REHOME's group
  argument) · S3 CNSDFG/ATRBYT writes · then DAC-full, TEMPST→10, RNDX, the N set.
  S2+ all cost ROM → carve first. S1's W follow-ups (STR$ trailing space,
  integers in NUMBUF, FBUFFR+0) are filed on the item.
* **APPARATUS last:** the 9-probe filed-row triage.

### 🔴 LESSONS PAID FOR THIS EVENING

* **`ls` BEFORE ANY WRITE INTO `scratchpad/` — `cp` and `mv` too, not only
  heredocs** — a `cp` overwrote D-PLAYXREC's tracked probe, which had ASKED THE
  VERY QUESTION being measured. **Grep TODO/specs for the QUESTION before
  measuring it.**
* **Build `git add` lists from `git diff --name-only`, never from `git status
  --short`** — an awk filter over it matched `??` files and committed 11 strays.
* **Closing an item is a CODE change for the static gates** — a checkbox flip
  after the battery changed tier-status AND orphaned a filed pin; re-run
  `make gates-scoped`, and gate the commit on its rc (`&&`), never `;`.
* **A knife cut with NO reading is not proof** (D-KNIFENOREAD): diff a knife
  run's verdict column against the last healthy one — a uniform column is the tell.
* **An equate move is only E if the CONTENT matches** — FBUFFR was `+1`, and
  three differences became W items. Measure the content first.

## 🟢 STATE AS OF 2026-09-24 AFTERNOON — superseded above.

**Tree CLEAN, all pushed, head `b41d9548`.** SHAs from `git log`, after the
morning hand-off `98513bcc`: `79167b21` D-KWTIME · `b21a86aa` D-KWT5ALONE ·
`cf1a0339` D-WIDTHKEEP · `aca68404` D-GATESCOPE · `91793588` D-KWT5FORM ·
`4204890d` D-BOOTWIDTH + D-ZBCRLF (+D-PSGLATCH) · `a22c1af2` D-KWPAINT2 ·
`b6a373b4` D-PAINTHANG WITHDRAWN · `b41d9548` D-CURLIN.

### 🏗️ MORE OF JOOST'S RULINGS, 2026-09-24 AFTERNOON — DO NOT RE-ASK

| subject | ruling |
|---|---|
| **T2 vs T5 measurement** | option (c): **whole program for T2, keyword ALONE for T5** (a twin without the keyword's statement) |
| **per-form timing** | *"a classic case of two very different effects of one keyword WIDTH … both need a time measurement"* → T5 is PER FORM; a row that sets up with its own keyword declares the timed one (`TIMED:<n>`) |
| **batteries** | **scoped, FULL on risk, and at least every 5th commit** — `make gates-plan` / `make gates-scoped`, `HANDOFF=1` at a session end |
| **the `ZB` prompt** | text stays `ZB`, but it **ends its row with CR/LF like `Ok`** (D-ZBCRLF, shipped) |
| **CURLIN** | *"Yes, maintain CURLIN"* — shipped (D-CURLIN) |
| **boot width** | a presentational split (VG-8020 37, CF-3300 39) → zerobas boots at 37 (the 09-04 rule), disk rows compare at the CF-3300's 39 |
| **shared buffer** | *"(b) One shared buffer"*, then *"Merge; BDOS out of scope"* — shipped as D-BUFMERGE (`6e1722b7`) |
| **the ✋ of D-ADDR29** | all as recommended: `DAC` FULL (ints at DAC+2, USR reads DAC); `TEMPST` pool shrinks to 10; `RNDX` now / `ARG` later; N set observable-first — `docs/spec-basic-addr29.md` §4.1 |
| **RAM addresses** | *"All 29"* — every published work-area variable the VG-8020 writes and zerobas does not (D-RAMFOOT) is to be maintained at the published address, scratch included; reopens D-REHOME's FRETOP/ARYTAB rejections. Arc D-ADDR29, TODO §"COMPARE RAM *USAGE*" |

### ➡️ THE QUEUE NOW

* **TIER 1 D-KWPROVEN remainder:** the **37 UNTIMEABLE rows** (they END before
  the end mark). CURLIN is now the SYMMETRIC end signal ("becomes `$FFFF`") on
  both machines → kwtime needs a **second watchpoint** (`$F41D`, value `$FF`)
  beside the `$E000` start mark — a `probes/lib/omsx_repl.py` change, so FULL —
  then a BIAS check on rows both shapes can time.
* **TIER 3 D-VDPIE** — a measurement first (does the reference re-enable VDP
  interrupts after a program leaves R1 bit 5 clear, and where?).
* **TIER 4 the RAM map** (whole map vs the VG-8020; free memory, addresses,
  economy) — measuring autonomous, ADJUSTMENTS to Joost.
* **💰 BUDGET: 13 B left in main (page 1 8 + low 5).** The next ROM-growing
  item needs a carve first — read [[carve-routes-measured-shut]].

### 🔴 LESSONS PAID FOR THIS AFTERNOON

* **`cap_gap` DOES NOT DELAY THE CAPTURE AFTER `RUN`; `run_gap` DOES.** It cost a
  false TIER 1 "PAINT hangs", filed, committed and withdrawn the same day. A slow
  side reading `<NO MARKER>` is a BUDGET question before it is a defect.
* **Tcl `after time T` is ABSOLUTE emulated time from power-on** — introspection
  at 20 s sampled a program still being TYPED. And never reuse the harness's
  Tcl names (`__f`) in a prologue.
* **After changing kwsweep's rows, re-run kwtime too** before `make tiers-md` —
  it times those same rows (a stale kwtime pin reddened tiers-md-check).
* **The PSG latch race:** the reference's interrupt SELECTS R14; any
  `OUT&HA0`→`INP(&HA2)` read is racy there. All 11 PSG rows sync to a TIME tick
  first (`T9`/`J9` loop). Fixing ONE row moved the race to the next.
* **A generated file is not an input** (the disk ABI) and **a keyword named in
  a shared library's comment is not a dependency** — both found by REPLAYING a
  real diff through `pick_gates` before trusting it.

## 🟢 STATE AS OF 2026-09-24 MORNING — superseded above.

**Tree CLEAN, all pushed, head `3eb2e3f2`.** No ROM has changed since
2026-09-23 evening (battery hashes `ea1e4b98 b188cd31 491644a1 b8453c76`), so
the knife pin is still valid. SHAs below read back from `git log`:
`bfb75bd4` the rulings · `08ebb914` D-TIERSWAP · `12d5453b` D-KWLADDER ·
`3eb2e3f2` D-PLAYBACK closed. Overnight (09-23→24): D-CAPGAP closed, D-MARKERWORD,
D-FILEDROT re-run, and the filed-row triage down to **9 probes**.

### 🔴 TWO "WAITING ON JOOST" BLOCKERS RODE THE WHOLE NIGHT AND WERE ALREADY ANSWERED

The overnight prompt listed the TIER 4 speed charter and the RAM-usage
comparison as Joost's. **Both had been ruled on 2026-09-22** and sat in their
own TODO items; the hand-off copied the list forward without re-reading them,
and Joost was asked the speed question a second time (same answer).
🎯 **RULE: a hand-off's "waiting on Joost" list is a WALL READING — before
carrying one forward, open each item and read its LATEST ruling.** The list
below was built that way on 2026-09-24, each block read to its end with struck
markers excluded — and a first scan that did NOT exclude `~~🙋…~~` reported
two ruled items as 🙋. Scan by BLOCK, and strike-aware.

### 🏗️ JOOST'S RULINGS, 2026-09-24 — DO NOT RE-ASK ANY OF THESE

| subject | ruling |
|---|---|
| **tier ORDER** | **SWAPPED: TIER 4 = RAM USAGE, TIER 5 = ON-PAR SPEED.** 1 happy path · 2 reasonable time · 3 common errors · 4 RAM · 5 speed · 6 every error. Prose dated before 09-24 uses the old numbers; only the `🎚️` tags are live |
| **speed** | in the charter (*"Yes, match the reference"*, first *"yes but that is tier 4"* on 09-22) — now at TIER 5 |
| **RAM rung** | secures **all three**: same free memory, same ADDRESSES (undocumented cells too), same economy. **Target: the VG-8020** when references diverge (*"prefer the vg8020"*); disk-only cells take the CF-3300. A free-memory vs address conflict goes to Joost. Proof = **the whole RAM map**; per-keyword T4 is DERIVED from it |
| **LADDER** | a keyword's LEVEL is its highest UNBROKEN run of proven rungs from T1 (`T1✓ T2— T3✓` = level 1). `tools/tier_table.py` prints it |
| **T2** | the keyword's test program completes within **10× the VG-8020's time** (*"use 10x, it will be slow, but it finishes"*) |
| **T5** | *"Track the ratio, set no bar yet"* — show the RATIO, never a tick |
| **T6** | **NOT ruled** — its own 🙋 item (the only rung still undefined) |
| **the rig** (STICK/STRIG/PAD) | *"Park it."* → ⛔ BLOCKED. `tools/rigstick.swift` stays, untouched |
| **D-PLAYBACK** | ran; the 09-10 agreement was a RACE zerobas won. *"Re-pin under D-PLAYWIN"* — done |

### 🤖 THE QUEUE, IN TIER ORDER — RE-SCAN IT, DO NOT TRUST THIS LIST

➡️ **TIER 1, FIRST: D-KWPROVEN — BUILD THE T2/T5 ROW TYPE** (TODO §"WHAT
PROVES A RUNG?"). **T2 and T5 are ONE measurement**: zerobas ÷ VG-8020 time
for the same program, with a completion watchdog. T2 ticks at ≤ 10×; T5 SHOWS
the ratio and never ticks. The kwsweep rows ARE the per-keyword test programs,
so the obvious shape is timing them on both sides — ⚠️ but `TIME` quantises
(±1 jiffy on small counts; the `width: TIME` rows read 2 vs 5), so a short row
needs a repeat loop to be a ratio at all, and a row that is fast on both sides
should not be scored on noise. **Design it, state the rule for "too short to
time", plant a NEGATIVE arm (a keyword made artificially 20× slower must NOT
tick), and flip `S36e` deliberately** — that arm exists so a proving row type
cannot arrive as a side effect.
📋 **TIER 1, THEN: the keyword-completeness remainder** (TODO §"Keyword-
completeness gaps", 🤖 at its end).
📋 **TIER 2: the same-address question** (TODO §"SHOULD MAIN AND `disk.rom` USE
THE SAME ADDRESS…", 🤖).
📋 **TIER 4: the RAM rung** (TODO §"TIER 4 … MATCHES THE REFERENCE'S RAM
USAGE", §"COMPARE RAM *USAGE*", both 🤖) — the whole-map comparison vs the
VG-8020, all three goals. Measuring is autonomous; ANY ADJUSTMENT goes to Joost.
Score his *"very economical"* hunch as a PREDICTION, including a miss.
📋 **TIER 5: speed** — the interpreter band, `PAINT`, `PUT` (all 🤖).
📋 **APPARATUS (below every tier): the filed-row triage is DONE** (2026-09-25; clrtrapstk_stop measures clean after D-STOPTAP) —
`cf3300_files`, `clrtrapstk_stop`, `loadrun`, `mergeshape`, `mergewin`,
`playmml`, `playnote`, `playpsg`, `playx`. The `play*` ones are likely REAL
holes (they compare and cannot say so) needing a channel, not a declaration.
Method, traps and the D-RECLENV channel shape: the 09-23 section below.

### 🙋 STILL JOOST'S — READ EACH ITEM'S LATEST RULING BEFORE BELIEVING THIS

* **T6** — what bounds "the exhaustive error set" (its own item, split today).
* **`wip/saveport` / "THERE IS NO SINGLE RAM MAP"** — 🙋 *only on WHEN*.
* **"SLIM THE FILE-CHANNEL CONTEXT"** (the *"Gap (small)"* entry) — retire/delete.
* **`LOAD`'s cells (step 9/10)** and the disk-code-eviction constraints — 🙋.
* **Every TIER 6 item** — PARKED since 09-10 (*"when we get to TIER 6"*, then
  numbered 5, *"we'll have to do a prioritization together"*).
* One cosmetic offer: split `⚫ N/A` into "particle" and "composite-only".

### 🔴 LESSONS PAID FOR ON 2026-09-24 — CARRY THEM

* **🏗️ BATTERIES ARE SCOPED NOW (Joost, 2026-09-24, D-GATESCOPE).** `make
  gates-plan` says which tier a change needs; `make gates-scoped` runs it. FULL
  on shared code, an unknown blast radius, every 5th commit since the last full
  green (the runner now records the sha), and every hand-off. Replayed on
  D-WIDTHKEEP's diff it picks 23 suites, not 90 — after two faults the replay
  found: a regenerated `disk/basic-resident-abi.inc` made EVERY commit full, and
  a keyword match over the IMPORT CLOSURE had 81 of 90 suites "mention WIDTH"
  through `omsx_repl.py`'s comments.

* **NOTHING RUNS IN THE REPO WHILE A BATTERY DOES — NOT EVEN A "READ-ONLY"
  CHECK.** I ran `tools/check_selftests.py` mid-battery to answer a question;
  its selftests plant into tracked files and restore CONTENT but not MTIME, so
  `make -q` called the ROMs stale and `lineerr#8/8` REFUSED (rc 2, retry "REAL",
  nothing measured). The runner's POOL WRITE guard caught it.
* **ONLY FIVE OF THE "EIGHT EXCLUDED" ARE REAL.** `diskdep-selftest` and
  `layout-invariant-selftest` run every battery inside `selftest-check`, and
  `citation-check` inside `basic-reloc`. Run the five `*-acceptance` suites only
  when something THEY READ moved — `grep` their scripts for the changed module
  before deciding (today: none reads `tier_table`/`kwforms`).
* **A ROW THAT AGREES CAN AGREE BECAUSE IT WON A RACE.** `empty string, no
  delay` was de-pinned on 09-10 as "no longer diverging"; zerobas's `-1` was a
  MUSICF bit not yet cleared by the next tick. The 3-arm worktree differential
  (09-10 ROM + 09-10 probe / 09-10 ROM + today's probe / today's ROM knifed)
  separated harness from ROM in ~15 min. **And a fix built on a transient
  reading (D-PLAYEMPTY) can move the machine AWAY from the reference** —
  MUSICF reads 7 on the reference one statement earlier than its row sampled.
* **A KNIFE SHOULD CHANGE ONE BYTE WHEN IT CAN** — `jr nz`→`jr` kept every
  address in place; `cmp -l` proved the plant was exactly that byte.
* **PREDICTIONS TODAY: 1 hit, 1 miss** (the D-PLAYEMPTY knife). Score them.

## 📦 STATE AS OF 2026-09-23 — superseded above, kept for its lessons.

**Tree CLEAN, all pushed, head `70ab3095`.** Today shipped SIX commits, every
sha read back from `git log` rather than from memory (this arc has already put a
wrong one in prose once):
`c59a427b` D-ALIASBITE read side · `43d8b5b5` D-ALIASWCELL write side ·
`875e3bbd` the rig measured · `07b7e324` `rigstick` written ·
`9c621cb5` D-LOADPLAIN · `70ab3095` D-KWSTATUS.

### 🟢 D-ALIASBITE IS CLOSED, BOTH SIDES

A disk verb inside an open channel no longer corrupts it. **0 of 7** interposed
statements damage a channel being read, **0 of 8** judged verbs damage a file
being written, **0 of 5** random-file verbs damage it. `LFILES` still REFUSES
(it blocks with no printer and never reaches `CLOSE`) and a refusal is not a
finding.
🔬 **THE FOUR SURVIVORS FAILED FOR THREE DIFFERENT REASONS**, and the lesson is
that a set failing together is not a set failing alike:
1. `chan_gate` re-staged the SECTOR and not the CURSORS THAT ADDRESS IT. It now
   takes `fch_save_active`/`fch_load_ctx` (the whole channel-switch pair), not
   `fch_flush_active`/`fch_restage` (the buffer half).
2. `DSKI$`/`DSKO$` do their work OUTSIDE the gate via `dirverb_op`, and marshal
   their sector number through `FWR_DIRSEC` -- the open channel's own directory
   pointer. They take a second restore, and it only works because the gate saved
   BEFORE the parse. **That ordering is load-bearing and the source says so.**
3. `DSKBUF_PTR` named `FSECTOR_BUF`. With 1 and 2 in place `DSKO$ 0,0` wrote the
   open file's records over SECTOR 0 and the disk lost its boot record --
   strictly worse than the bug being fixed. It points at `FWBUF` now, which is
   the tier the CF-3300 puts raw sectors on (`$EB95`, disjoint from its
   file-data buffer at `$ED95`).
⚠️ **`FIELD`/`LSET`/`RSET` TAKE `chan_gate_bare`** -- the crossing WITHOUT the
bookkeeping. `hk_lrset` writes the channel's record ON PURPOSE, so the full
gate's restore undid it and reddened five suites. A verb added there must do NO
sector I/O; when in doubt take the full gate.
💰 main page 1 **44 → 29 B free**, low region **32 → 26 B**, `disk.rom`
unchanged at 7264 B. (Dated 2026-09-23, from a clean tree. **RE-RUN
`make basic-reloc`, never quote this.**)

### 🟢 D-KWSTATUS: A KEYWORD HAS A STATUS, NEVER A TIER

Joost: *"I have a feeling this TIER ranking is confusing. Can we come up with a
better mechanism?"* One ordinal scale was carrying three jobs. **`TIER n` now
means ONLY an item's priority.** `docs/tier-status.md` reads
`🟢 COVERED / 🟡 PARTIAL / 🔴 GAP / ⚪ UNPROVEN / ⚫ N/A` with evidence columns
(`knife ✓ · 2/2 forms · 4 open, worst TIER 2`).
⚠️ **`reached_group` IS UNTOUCHED** -- the change is presentation, so nothing was
reclassified. COVERED is 139, the same number the old "TIER 1 — REACHED" had.
🔴 **TWO NEGATIVE CONTROLS PIN IT:** no cell may read `| TIER 0 |`, and the
string `no open item` may not appear at all. If either fires, the sheet has
started scoring keywords on the ITEM priority scale again.

### 🔴 …AND JOOST CAUGHT A REGRESSION IN IT THE SAME HOUR — D-KWPROVEN (`b0206cc8`)

*"the old scoring system, while complicated, at least required building up tests
and evidence to reach next tiers for a keyword"* and *"lack of items at a tier
for a command does not actually mean there are no defects"*. **Both correct.**
D-KWSTATUS fixed a labelling contradiction and DELETED THE LADDER in the same
stroke; those were not the same problem. The status column measures the ABSENCE
of filed items and I had given it a green tick reading `COVERED`, which rewards
SILENCE — the exact inverse of what the old scheme demanded.
📏 **THE LOSS, MEASURED:** **32 keywords carry a scored `PROVES-T3:` row and the
new sheet rendered that ZERO times.** `kwsweep_t3` was intact throughout; only
the rendering dropped it.
✅ **FIXED: TWO ORTHOGONAL COLUMNS.** `🟢 COVERED` → `🟢 NO KNOWN GAP` (the
phrase the old text emitter used, which I had deleted), plus a **PROVEN** column
`T1✓ T2— T3✓ T4— T5— T6—`. **A rung is ticked only by a DECLARED, SCORED row,
never by silence**, and T1 also requires knife-proven CONNECTEDNESS — so `LOF`
reads `1/1 forms` and `T1—`.
🎯 **T1 139/159 · T3 32/159 · T2, T4, T5, T6 ALL 0/159 — NO PROVING ROW TYPE
EXISTS FOR THEM.** Nothing here has shown that ANY keyword runs in reasonable
time, at on-par speed, within the reference's RAM, or handles its exhaustive
error set. 🙋 **Designing those row types is JOOST'S** (a rung's definition is
charter-level), and T4's cannot even be specified until the charter question is
answered.
⚠️ **`S36e` PINS THE FOUR ZEROES.** If it fires, someone added a proving row
type — which must be deliberate, with its own definition of what the row proves.
🔴 **THE LESSON, AND IT IS THE SHARPEST OF THE DAY: I MADE AN INSTRUMENT LESS
DEMANDING WHILE MAKING IT CLEARER, AND ONLY THE CLARITY WAS ASKED FOR.** When a
rework replaces a scale, ask what the old scale REQUIRED of the thing it
measured, not just what it said. Simplifying a measure is a way of lowering it.

### 🤖 WHAT IS ACTUALLY AUTONOMOUS TONIGHT — RE-SCAN, DO NOT TRUST THIS LIST

🔴 **`tools/tier_table.py --all` PRINTS THE *TIER LINE'S* MARKER, NOT THE
ITEM'S LAST ONE.** The queue rule is the LAST work-bucket marker in the block,
so an item shown `🤖` there can be `🙋` by its end. **TIER 4 speed is the known
case**: `PAINT`, `PUT` and the interpreter band all print `🤖` and are all
gated on Joost's unanswered charter question (*does faithful include speed?*).
**Read each block to its END before starting it.**

➡️ **TONIGHT'S FIRST ITEM — D-CAPGAP's TWO FAULTY SUITES, and Joost already
approved the work**: *"yes, if a suite is faulty it needs to be fixed
obviously"*. `kwsweep` and `deffn-acceptance` capture rows EARLY. `deffn`'s
`b.recurse` scores "NOT MEASURED" but reads `ERR 7 AT 60` correctly once given a
real budget; `kwsweep` changes four reference values and gains a `MISSING cload`
row. ⚠️ **BOTH CHANGE GATE ROWS AND ONE IS A DENOMINATOR** -- so the change is
the BUDGET, and every moved row needs its own before/after stated.
📋 **THEN the four UNRUN `cap_gap` sites**: `trapsvc-acceptance` (9.0),
`input-devices-acceptance` (10.0), `nodisk-acceptance` (2.0), and
`probe_refcache.py`'s own site. ⚠️ **THE RATIO DOES NOT PREDICT A FINDING**
(`deffn` is 1.2× and moves, `ramfree` is 4.8× and does not), so each needs its
own A/B. 🔬 The control: `ZEROBAS_RUN_GAP=90 make <target>`, diff against a
plain run, **and check `refcache` reports 0 hits on the wide run** -- the first
cut of this control was served from cache and agreed BY CONSTRUCTION.
📋 **THEN** the APPARATUS bucket, which is deep (~35 items) and nearly all
`🤖`: citation tooling, knife roster, filed-face rot, probes that exit 0 on a
divergence, the error-message alphabet, temp-root literals.
📋 **AND the keyword-completeness remainder** (TIER 1, `🤖`, ~TODO.md:22086).

### 🙋 JOOST'S — DO NOT START ANY OF THESE

* **The STICK/STRIG/PAD rig.** He ruled the Apple Developer route and will
  request the `com.apple.developer.hid.virtual.device` capability
  (`https://developer.apple.com/contact/request/system-extension/`). The tool is
  WRITTEN (`tools/rigstick.swift`, `make rigstick-selftest`) and every local
  escape hatch is MEASURED SHUT: unsigned → nil · ad-hoc signed claiming it →
  SIGKILL before `main` · **root (uid=0) → nil** · injecting SDL's
  `SDL_JoystickAttachVirtual` → shut twice (SDL is linked STATICALLY and openMSX
  runs under HARDENED RUNTIME). **No free tool exists** -- Karabiner ships the
  one signed virtual-HID driver on macOS and it is keyboard + pointer only.
  Fallback he will check himself: an Arduino with NATIVE USB (Leonardo/Micro/Pro
  Micro, SAMD/ARM, RP2040 -- an Uno/Nano CANNOT).
  🔬 **The cheapest unrun measurement is neither route: BORROW ANY USB GAMEPAD**
  and answer whether `joystick1` appears, `plug joyporta joystick1` succeeds and
  `STICK(1)` reads it. Nothing on the Mac is on the Generic Desktop page today.
* **The TIER 4 charter question** -- *does faithful include speed?* It gates all
  remaining TIERED work.
* **The RAM-usage comparison** (*"not something for now"*), **step 10 `OPEN`**,
  the *"Gap (small)"* entry in `expansion-protocol.md` §6, the merged remote
  branch `wip/saveport`, the **TIER 1 keyword tier re-ask**.
* **The buffer GEOMETRY question**, which survives D-ALIASWCELL: should main's
  two sector buffers be disjoint from disk's ANYWAY, for the CLASS rather than
  the routes? Nothing this tree can measure reaches the buffer now, so it buys
  robustness against FUTURE code, not a fix. It belongs with the RAM comparison.
* **One cosmetic offer he has not answered:** whether `⚫ N/A` should be split
  into "particle" and "composite-only", which are different facts.

### 🔴 THREE TIMES TODAY A GATE ANSWERED ABOUT A WORLD THAT NO LONGER EXISTED

Different mechanisms, one shape: **the instrument outlived its input.**
1. `ram-map-check` computed its verdict from a **STALE `.sym`** and I nearly
   deleted a LIVE pin on its say-so. The rebuild is what revealed it.
2. `make tiers-md` read the **kwsweep pin written by the battery that ran
   against the BROKEN intermediate ROM**, and demoted `LSET`, `FIELD` and
   `OPEN` to TIER 0. A pin is a measurement of ONE ROM and keeps its answer
   after that ROM is gone.
3. **A FLAKE WITH A SCHEDULE, and I introduced it.** Putting a form count in a
   keyword row made `fmt_markdown` read `build/kwsweep-verdicts.json` -- and
   **`make gates` DELETES `build/` in its build step**. So `selftest-check`
   passed at the prompt and FAILED in the battery, on byte-identical source:
   backwards, since the battery is the verdict that gets trusted. ⚠️ The file
   had ALREADY been fixed for this (*"`evidence`/`t3` are INJECTABLE because S14
   was not hermetic"*) and I re-entered through a new door by adding a FOURTH
   dependency to the same function.
🎯 **THE RULE: when a gate disagrees with a hand run on IDENTICAL BYTES, the
difference is the ENVIRONMENT, and `build/` not existing is the first thing to
try.** Move the artefact aside and re-run rather than reasoning about it.

### 🔴 OTHER LESSONS PAID FOR TODAY — CARRY THEM

* **A POSITIVE CONTROL THE SUBJECT CAN REPAIR IS NOT A CONTROL.** `KILL` was the
  positive control in two write sweeps; the moment the fix landed the guard
  fired on the FIX and both probes returned rc=2 with every row clean and
  nothing judged. `truncate!` (re-`OPEN` FOR OUTPUT) damages by construction and
  survives every future fix. **Check every probe you touch for this shape.**
* **A PRIVILEGE TEST THAT DOES NOT REPORT ITS OWN PRIVILEGE IS NOT ONE.** The
  first root run came back `uid=501` -- not root -- and would have been filed as
  "root refuses" had the tool not printed `getuid()` in its own message.
* **A WHOLE-LINE MATCH ON A BINARY IS NOT AN ABSENCE.** `grep -x` scored
  `No such pluggable` at 0 in a binary that demonstrably emits it.
* **A STALE JUSTIFICATION OUTLIVES THE THING THAT JUSTIFIED IT.** Plain `LOAD`
  had no row because a note said the instrument could not reach it. True when
  written, stale from D-KWLOG four months later. **Joost remembered; the file
  did not.** When an item says "cannot", check the date against the machinery.
* **A BUCKET LABEL IS NOT A BLOCKER.** `VARPTR` printed UNPROVEN beside its own
  evidence reading `knife ✓ · 1/2 forms`, because I mapped the bucket instead of
  asking what the blocker was -- the same mistake the labels I was replacing had
  made one level up.

## 🔴 STATE AS OF 2026-09-21 — READ THIS BEFORE THE FIRING PROMPT

⚠️ **THE 09-16 BLOCK BELOW IS SUPERSEDED IN ITS HEADLINE AND STILL GOOD IN ITS
LESSONS.** Read this section for WHERE the work is; read that one for HOW it
goes wrong. In particular its *"the autonomous queue is EMPTY except TIER 4"* is
no longer true — Joost's 09-20 ruling on the disk-code eviction (*"I think the
answer to Two is obvious: we do as the reference does"*) opened a TIER 2 arc that
is still running.

### The live arc: `disk/docs/spec-diskcode-eviction.md` §6.2, steps 9–14

Under his governing frame — *"a clear understanding of how the communication
between main rom and disk rom fully works"* — the FAT engine and the loader's
sector loop move OUT of main and INTO `disk.rom`, reached through the claimed
hook cell `$FE5D`.

**Shipped:** step 9 LOAD (`e458032b`) · step 11 MERGE + ASCII LOAD (`35eeafb7`) ·
step 12 SAVE (`3b8e1b57`) · and **step 13 COMPLETE**, all four slices —
`174bf887` D-NAMESTAMP, `407298e0` D-KILLLOCAL, `c9238e5a` D-COPYLOCAL,
`285b80e9` D-FILESLOCAL.

⚠️ **THOSE SHAS ARE READ BACK FROM `git log`, AND THE REASON THAT IS WORTH A
LINE:** the D-FILESLOCAL sha was first written into a hand-off as `c9238e5a`'s
neighbour from memory rather than from the log, and it was wrong. A sha is
exactly the kind of fact that looks checkable and is not, once it is in prose.

**Step 13 is NOT a 1895 B relocation** (that filing was wrong, §6.6av): the ported
disk verbs each made a three-ROM round trip — `hk_*` called BACK into main just
so main could marshal on to `sub.rom`'s `dirverb_tenant`, whose body ran FAT
primitives `disk.rom` has had since steps 9/11/12. Each slice deletes one.

🔴 **THE TIERED AUTONOMOUS QUEUE IS EMPTY AT *EVERY* TIER (re-checked 2026-09-21,
D-RETRYSUBJ) — AND "BELOW TIER 4" WAS THE WRONG BOUND.** Scanning every OPEN
item for its LAST work-bucket marker leaves **three** whose last marker is
`🤖 AUTONOMOUS`: the RAM-usage comparison (TIER 2 — **Joost's**, *"not
something for now"*), `refcache-check` (APPARATUS), and `ex_stop`'s missing edge
seed (TIER 5). **TIER 4 speed is NOT autonomous**: its LAST marker is
`🙋 NEEDS-JOOST` on the charter question (*does faithful include speed?*), and
the item says plainly that optimising is only worth starting once that is
answered — §5's autonomous half is already refuted.
🛑 **AND AS OF 2026-09-22 THE AUTONOMOUS QUEUE IS EXHAUSTED — THE LOOP WAS
STOPPED, NOT ABANDONED.** `ex_stop`'s edge-seed item closed (D-STOPSEED,
`348a6dba`). Re-running the marker scan leaves TWO open items whose last marker
is `🤖 AUTONOMOUS`, and **neither is actionable**:
* the **RAM-usage comparison** (TIER 2) — Joost's, *"This is not something for
  now"*;
* **`refcache-check`** (APPARATUS) — its actionable half shipped as D-RETRYSUBJ
  (`2c46d1e1`); the ROOT CAUSE is waiting on a **recurrence** of a red that has
  not happened again, so there is nothing to do until it does.

🙋 **WHAT THE NEXT SESSION SHOULD DO IS ASK JOOST**, not pick something. The
rulings that would re-open real work, in the order they unblock the most:
1. **Does faithful include SPEED?** (the TIER 4 charter question) — this gates
   the interpreter's 2.5–3.8× band, `PAINT` and `PUT`, i.e. all remaining
   TIERED work. The item says optimising is only worth starting once it is
   answered.
2. **Step 10 `OPEN`** — the PAINT span-stack RAM lever.
3. **The same-address question** — D-COPYLOCAL answered it only in miniature
   (cells with ONE consumer); `SECTOR_BUF`/`FSECTOR_BUF` and `WBUF`/`FWBUF` have
   two consumers each and 416 B of accidental overlap.
4. **The TIER 1 keyword tier re-ask** — the unattributed list is now 0, which
   the item itself named as the moment to re-ask.
5. The **RAM-usage comparison**, whenever he wants it.

⚠️ **RESTARTING THE LOOP WITHOUT ONE OF THOSE ANSWERS WILL SPIN.** The honest
move was to stop and say so.
⚠️ **THE RENAME RESIDUAL IS DECLINED, MEASURED** (§6.6ba): `dirverb_tenant` /
`dirverb_op` / `SUBROM_IDX_DIRVERB` are ~96 refs across **12 code + 11 doc**
files, and the docs are the eviction's HISTORICAL RECORD — renaming them would
falsify it, so no mechanical sed, and no gate would catch a
consistent-but-wrong rename. Document, do not half-change.
🔴 **CHECK THE CHECKBOX BEFORE THE BODY.** A `DSKF` blocker reading *"8 B free
on 2026-09-13"* looked like a prime stale blocker; the item is `- [x]` DONE
(D-DSKFDRV) and that text is its original, kept for the record. Several closed
items carry *"(the original item, for the record:)"* blocks that read exactly
like live work.

📜 **SUPERSEDED, kept for its own record — the earlier reading:**
`tools/tier_table.py --keywords` reports the unattributed keyword list at **0**,
so the TIER 1 keyword-completeness item has no concrete target left and its own
text says the tier re-ask goes to Joost at exactly this point. TIER 2's two
autonomous items are step 13 (closed) and the RAM-usage comparison (Joost's,
*"not something for now"*). What is left autonomous is TIER 4 speed (`PAINT`,
`PUT`, the interpreter band) and the APPARATUS/BUDGET buckets.
⚠️ **`VARPTR` LOOKS LIKE A TIER 1 TARGET AND IS NOT:** its second authored
form is `file-channel` (`VARPTR(#n)`), which is Joost's filed stride ruling.
Re-verifying that blocker is what stopped a wasted tick.

📜 **HISTORICAL, kept because the lesson outlived the slice — `FILES`/`LFILES`
and SCOUT IT BEFORE PRICING IT:** This arc has now
had to correct the same over-confident sentence twice — *"`KILL`, `COPY` and
`FILES` are the same shape"* was measured on `KILL` alone and was false for
`COPY`, and then `COPY`'s own scout over-priced it by 17 B because it priced a
cell's home before grepping its consumers. `tnt_files` emits through
`CHPUT`/`LPTOUT` and spells `FSECTOR_BUF` in CODE at two sites
(`sub/dirverb.asm:196`, `:301`), which in `disk.rom` is MAIN's buffer at `$E5C0`.
After it, `dirverb_tenant` holds `DSKO$`/`DSKI$` only — both called from MAIN, so
it does not empty.

🙋 **JOOST'S, FILED, DO NOT START:** the RAM-usage comparison against the
reference (`12cbc6fe` — *"not something for now"*, plus *"I have a hunch
reference is very economical with RAM"*) · the same-address question (`9d4f94b2`)
· step 10 `OPEN` (the PAINT span-stack RAM lever) · the *"Gap (small)"* entry in
`expansion-protocol.md` §6 · the merged remote branch `wip/saveport`.
⚠️ §6.6q's hazard is NOT retired in general: `PAINT` then `LOAD` is still
ungated and `GFX_PSTK` still sits in disk's `SECTOR_BUF` window.

### 🔴 STATE AS OF 2026-09-22 — THE DISK SIDE-TRACK IS CLEAR, GO TO THE
### SAME-ADDRESS QUESTION

Joost's order, in his words: *"do the same-address question first; we want to
finish the disk side-track first"*, then *"take the hang first"*. **The hang is
finished** — and it was never a hang.

**`b43e19ef` D-TWOFILE IS WITHDRAWN: THERE WAS NO DEFECT.** Writing two files and
reading one back works and always did. Four headlines — a hang, a silent abort,
dead screen output, a slow `OPEN` — were all wrong. The probe passed
`cap_gap=70.0` to buy a 4.4-second program room; **`cap_gap` is the gap AFTER the
capture**, so the capture fired at RUN+`step` = 3.0 s and read a half-drawn
screen. `run_gap` is the knob. Pinned by `tests/test_capture_budget.py`
(emulator-free, 8 rows + a knife) and stated on `_run_cases_impl`'s docstring.

✅ **THE SAME-ADDRESS QUESTION IS ANSWERED AS FAR AS MEASUREMENT CAN TAKE IT
(`2fef4b0e`), AND IT TURNED UP A TIER 1 DEFECT.** `aliasbite_probe.py` only ever
needed a `run_gap`; with one it says **BITES**. A disk verb between two reads of
an open channel truncates it: `('ABCD','EFGH')` becomes `('ABCD','')`, silently.
`aliasscope_probe.py` measured the mechanism — `KILL` writes **416 B** into
`$E5C0..$E75F` (exactly the overlap's width) and zero above; `NAME` writes 832
there and 192 into `$E760..$E7BF`.
🔴 **BUT AN A/B AT `174bf887` REPRODUCES IT IDENTICALLY**, before any local mount
existed — **the overlap is NOT the cause and fixing it would not close the item.**
Main's own engine already reuses `FSECTOR_BUF` for every file operation. §6.6q's
*"has not bitten yet"* is inverted in place, its analysis kept.
🙋 **THE REMEDY IS JOOST'S** — (a) same address, (b) one shared buffer, or the
new **(c) make them DISJOINT** (no mutual-exclusion argument, cheaper than (a),
forfeits the shared-body prize). All three are his.

✅ **D-ALIASBITE'S EXTENT IS SWEPT (`e5ffa6fa`) AND IT REFUTED A CLAIM FILED IN
`2fef4b0e`.** Seven interposed statements: **`KILL`, `NAME` and `DSKF` truncate;
a second `OPEN` (in or out), a `PRINT#` on another channel, and a no-disk arm are
all CLEAN.** So *"main's own engine reuses `FSECTOR_BUF` for any file operation"*
is FALSE — ordinary channel I/O is fine. ⚠️ `DSKF` is READ-ONLY and truncates.
🔴 **AND THE FOOTPRINT DOES NOT PREDICT THE OUTCOME:** `OPEN…FOR INPUT AS#2`
writes the SAME 832/192 as `NAME` and the channel SURVIVES. A watchpoint count
says what a verb TOUCHES, never whether anything breaks — the two probes are two
instruments, not one. [[a-footprint-does-not-predict-an-outcome]]
🎯 **LEADING HYPOTHESIS, FROM OUR OWN SOURCE** (`basic/sysvars.inc`, "Phase 2:
MAXFILES per-channel context blocks"): the buffer is a CACHE, flushed on switch
away and re-read on switch back via `fch_restage`. **A channel switch restages; a
disk-ROM verb is not a channel switch.** NOT established as the cause.

✅ **"WHY EMPTY AND NOT GARBAGE" IS ANSWERED (`72326acd`) — IT WAS GARBAGE, AND
THE GARBAGE WAS INVISIBLE.** `LEN(B$)`/`ASC(B$)` read out of RAM: **4 characters
in every arm**, first byte `$45` (correct) in the control, `$00` after
`KILL`/`DSKF`, `$20` after `NAME`. **NOTHING IS TRUNCATED** — the wrong BYTES are
delivered and `CHPUT` paints a NUL as nothing. The item headline, its table and
two commit messages said "truncates" and were all reading that screen.
🔴 **AND IT IS WORSE THAN A TRUNCATION:** a short read is detectable by a
program, four bytes of wrong data are not.
✅ **THE MECHANISM IS MEASURED, NOT HYPOTHESISED** (`scratchpad/aliascell_probe.py`):
**NOT ONE ENGINE CELL MOVES** across the verb — `FREAD_OFF`, `FREAD_LEFT`, the
whole `FCH_STATE0` span, `FCH_NUM`/`FCH_MODE` all unchanged. Only the BUFFER
(`$E5C0..$E5CF`: `ABCD…` → all `$00`) and 3 bytes of the `DISKOP` block. Main's
bookkeeping is intact and its data is not — a stale cache serving the last
writer's leftovers, confirmed by the content FOLLOWING the verb.

🔴 **THE WRITE SIDE IS DATA LOSS ON THE MEDIUM (`bbd68eb5`) — THE ITEM IS NOW
MORE SERIOUS THAN WHEN JOOST WAS ASKED TO RULE ON IT.** `OPEN FOR OUTPUT` ·
`PRINT#` · *[verb]* · `PRINT#` · `CLOSE`, file read back off the HOST-PARSED FAT
chain: control correct; **`KILL` → first 18 bytes `$00`**; **`NAME` → the file is
EMPTY**; **`DSKF` → 37 bytes of `$09`**. The write stream buffers into the SAME
`FSECTOR_BUF`, so `CLOSE` flushes the verb's leftovers to disk. ⚠️ **`DSKF` is a
READ-ONLY query and it destroys a file being written.**

✅ **THE VERB SWEEP IS DONE (`450cd501`): 7 OF 8 JUDGED VERBS DAMAGE THE OPEN
FILE.** `KILL`, `NAME`, `DSKF`, `COPY`, `DSKI$`, `DSKO$`, `SAVE`.
`NAME`/`DSKI$`/`DSKO$` leave it EMPTY, `KILL` NUL-fills the first record,
`COPY`/`SAVE` leave a DIRECTORY ENTRY (`PROG    BAS`) in it, `DSKF` leaves 37
bytes of `$09`.
🟢 **AND `FILES` IS CLEAN — byte-identical to the control.**
⚠️ `LFILES` is NOT evidence either way: its arm never reached `CLOSE` (it blocks
with no printer) and the probe REFUSES it. **A refusal is not a finding.**
⚠️ **EACH ARM NOW POKES A COMPLETION MARKER AFTER ITS `CLOSE`** — an empty file
is what a wiped file AND an unfinished program both look like, and without the
marker four arms were uninterpretable.

✅ **`FILES` IS EXPLAINED (`064b0755`): IT NEVER TOUCHES MAIN'S BUFFER.** Across
the verb it moves THREE cell-bytes — its own `FILES_ENTIDX` (`$E0FC`) and two of
the `DISKOP` block — and **none in `$E5C0..$E7BF`**, against 19–25 for the
corrupting verbs. It is clean on the READ side too (`$45`, `E`).
🎯 **SO THE RULE IS NOT "IT MOUNTS" — IT IS "IT REFILLS MAIN'S STAGED SECTOR".**
A disk-ROM verb can mount, walk the whole root directory and emit every entry
without disturbing a byte.
🔴 **AND THAT REFINED THE REMEDY ADVICE — DO NOT QUOTE THE OLD LINE.** *"Changing
the addresses would not close it"* is true of the defect CLASS and was TOO STRONG
about the shipped ROM. `174bf887`'s route (the sub-ROM tenant using main's own
buffer BY NAME) **no longer exists**; every damaging verb measured today reaches
the buffer through disk's `WBUF` ALIASING it. **So (c) DISJOINT would remove
every route this tree can measure** — a ROUTE fix, not a CLASS fix. That is a
real choice, not "none of them helps". ⚠️ Unmeasured: whether (c) is affordable,
and whether any path outside these nine verbs reaches the buffer.

✅ **THE RANDOM VERBS ARE ALL CLEAN (`3f814149`): `FIELD`, `LSET`, `PUT`, `GET`.**
`PUT`/`GET` being clean STRENGTHENS the rule — they are CHANNEL SWITCHES, and a
channel switch restages. Every clean row measured is a channel switch or touches
no buffer; every damaged row is a disk-ROM verb that refills it.
🔴 **AND `$D000` IS NOT A PRIVATE CELL — IT FABRICATED A FINDING.** The machine
writes it **32 times** per disk program (15/240 alternating); `CLEAR` does not
stop it; every `$xx00` boundary is the same; **`$CFFE` is quiet**. The first run
reported `ERR 15` in EVERY arm including the no-disk control.
⚠️ **SCOPE — 3 of 4 probes survive, each for a stated reason** (see the
D-CELLPRIV item): `aliaswrite` sound (marker VALUE 9 never collides),
`aliascell` sound (SNAPSHOTS tagged by value), `aliasbite` sound (no marker).
🔴 **`aliasscope_probe.py` IS AFFECTED: its counts are LOWER BOUNDS**, because a
spurious write closes its gate early. Directions survive; **do NOT quote *"416
is exactly the overlap width"*** until it is re-run on `$CFFE`. 🟢 `FILES`'s zero
footprint does NOT rest on it — that came from `aliascell`'s snapshot diff.

✅ **`aliasscope` RE-RUN ON `$CFFE` (`360cf469`) — EVERY FIGURE IDENTICAL.**
`KILL` 416/0 · `NAME` 832/192 · `DSKF` 1664/384 · `OPEN-IN` 832/192 · control
0/0, with a per-run guard that refuses on any foreign phase value. **The counts
were NEVER lower bounds and *"416 is exactly the width of the overlap"* is
quotable again.**
🔴 **AND D-CELLPRIV'S OWN HEADLINE WAS CORRECTED — IT WAS MINE AND TOO STRONG.**
`$D000`'s 32 writes are **BOOT-TIME RAM SIZING** (`15`/`240` at every `$xx00`),
timestamped at **t=0.00–0.03** against the program's marker at **t=20.04**, with
ZERO after it. **The cell is safe once a program runs.** The fault was reading
the WHOLE watchpoint log, which begins at power-on — **a log is not a window.**
✅ **THE `$xx00` SWEEP CAME BACK EMPTY IN THE DIRECTION THAT MATTERS:** the four
tracked battery probes that count in `$D000` (`stop_trap`, `key_trap`,
`strig_trap`, `interval_trap`) are FINE — boot is over before their programs
start. 🟢 What survives is worth keeping: the probes now sit on `$CFFE` with the
claim RE-VERIFIED every run rather than assumed.

⚙️ **OPERATING NOTE, 2026-09-23 — DO NOT RUN THE EIGHT BATTERY-EXCLUDED TARGETS
UNCONDITIONALLY.** They sit outside `make gates`'s collection so they never get
`inert_against_last_green`, and running them after every commit cost ~10 min a
tick for nothing. Joost: *"why are you running a battery when there has been no
changes?"* **Apply the same inertness reasoning:** run them when a ROM, a
`probes/`/`tools/`/`tests/` source, a fixture or the installed machine moved;
SKIP them (and say so) for a change confined to `TODO.md`, `docs/` and
`scratchpad/`. ⚠️ `citation-check` is cheap, static and reads the docs, so a docs
change does warrant that one. ⚠️ `make gates` itself is NOT the waste — its
static tier checks citations, the tier table and the markers, and it skips the
emulator tier on its own.

✅ **AND THE REFERENCE HAS ANSWERED THE ARCHITECTURE QUESTION (`d2849fab`).**
`National_CF-3300` has its OWN `cf-3300_disk.rom` and has been this tree's disk
oracle all along — the earlier *"there is no booted disk oracle here"* was FALSE.
**On the reference, `KILL`/`NAME`/`DSKF`/`COPY` all leave an open file
BYTE-IDENTICAL.** So *"we do as the reference does"* settles the direction: a
disk verb must not disturb an open channel. ⚠️ And the reference is **(b) PLUS A
DISCIPLINE** — one shared buffer (267 B/channel, less than a sector) AND a
restage. We already restage on a CHANNEL SWITCH; we do not across a DISK-ROM
CROSSING. **So (b) alone would not close it — the RESTAGE is the load-bearing
change**, and (a)/(b)/(c) only decide what we buy alongside it.

🛑 **THE AUTONOMOUS QUEUE IS EMPTY (2026-09-23, `4ab3f665`). THE NEXT MOVE IS
JOOST'S — DO NOT INVENT WORK.** Three things are waiting on him:

  1. 🔴 **D-ALIASBITE's REMEDY, waiting since `2fef4b0e` and TWICE more serious
     since.** A disk verb inside an open channel corrupts it: a READ hands back
     4 bytes of the wrong data, and a WRITE commits them TO DISK. 7 of 8 judged
     verbs damage the file; `DSKF`/`DSKI$` are READ-ONLY and still destroy a file
     being written. His three options: (a) same address, (b) one shared buffer,
     (c) **DISJOINT** — and (c) would remove every route this tree can measure
     (a ROUTE fix, not a CLASS fix). ⚠️ **The old line *"none of them closes it"*
     is superseded; do not quote it.**
  2. 🔴 **D-CAPGAP's REMEDY:** `kwsweep` and `deffn-acceptance` capture rows
     early. Giving either a `run_gap` CHANGES GATE ROWS and one is a denominator.
  3. 🙋 The standing list: the RAM-usage comparison (TIER 5), step 10 `OPEN`,
     the *"Gap (small)"* entry, `wip/saveport`, the TIER 1 keyword tier re-ask,
     the TIER 4 charter question.

📋 **IF MORE AUTONOMOUS WORK IS WANTED, THE HONEST REMAINDER IS SMALL:** four of
the twelve `cap_gap` sites are UNRUN — `trapsvc-acceptance` (9.0),
`input-devices-acceptance` (10.0), `nodisk-acceptance` (2.0) and
`probe_refcache.py`'s own site — and the two highest remaining ratios are among
them. ⚠️ **The ratio does NOT predict a finding** (`deffn` is 1.2× and moves,
`ramfree` is 4.8× and does not), so each needs its own A/B.
🔬 **THE CONTROL IS BUILT:** `ZEROBAS_RUN_GAP=90 make <target>`, diff the rows
against a plain run, and **check `refcache` reports 0 hits on the wide run** —
the first cut of this control was served from cache and reported identical rows
BY CONSTRUCTION.

➡️ ~~**THE NEXT ITEM — AND IT IS THE LAST ONE: the 12 `cap_gap > step` sites**~~
(`scratchpad/gapscan.py --tracked`, TIER 2 🔭). `settle_n` is the instrument and
was never pointed at this. **Advisory, not a gate** — a wide `cap_gap` is
legitimate inter-case spacing, so a hit has two meanings and the verdict has to
be per-ROW.
🔴 **AFTER THAT THE QUEUE IS EMPTY — GO TO JOOST.** The remedy has waited since
`2fef4b0e`; the write side is DATA LOSS, and **(c) DISJOINT would remove every
route this tree can measure**, which is materially better than when it was filed.
⚠️ **THE SUPERSEDED LINE BELOW ASKED FOR THE `aliasscope` RE-RUN** — done.

➡️ ~~**THE NEXT ITEM: RE-RUN `aliasscope_probe.py` ON `$CFFE`**~~ (with
`CLEAR 200,&HBFFF`) so its counts are exact, and sweep the tree for other probes
poking a `$xx00` marker. ⚠️ **Verify the replacement rather than trusting it** —
`$CFFE` is quiet in ONE measured program.
📋 **THEN** the 12 `cap_gap > step` sites (TIER 2 🔭).
🔴 **AFTER THOSE THE QUEUE IS EMPTY — GO TO JOOST.** The remedy has waited since
`2fef4b0e`; the write side is data loss, and (c) DISJOINT now looks materially
better than when it was filed.
⚠️ **THE SUPERSEDED LINE BELOW ASKED FOR THE `FIELD`/`LSET` SWEEP** — done.

➡️ ~~**THE NEXT ITEM: `FIELD`/`LSET`, WHICH NEED THEIR OWN SWEEP.**~~ They require a
RANDOM channel (`OPEN … AS #n LEN=`) that the current control does not have, so
they need their own control rather than being bolted onto `aliaswrite_probe.py`.
Pure measurement, no ruling.
📋 **THEN** the 12 `cap_gap > step` sites (`scratchpad/gapscan.py --tracked`,
TIER 2 🔭, `settle_n` is the instrument, advisory not a gate).
🔴 **AFTER THOSE TWO THE QUEUE IS EMPTY — GO TO JOOST.** The remedy has waited
since `2fef4b0e` and the item has grown twice since: the write side is data loss,
and (c) now looks materially better than when it was filed.
⚠️ **THE SUPERSEDED LINE BELOW ASKED WHY `FILES` IS CLEAN** — answered.

➡️ ~~**THE NEXT ITEM: WHY IS `FILES` CLEAN?**~~ `LFILES` is the SAME directory walk
differing only in where the characters go, so *"it mounts, therefore it
corrupts"* is NOT the rule. Point `aliasscope_probe.py` (footprint) at `FILES`
and compare with `COPY`/`KILL`: does `FILES` write into `$E5C0..$E7BF` at all?
⚠️ **REMEMBER THE FOOTPRINT DOES NOT PREDICT THE OUTCOME** — `OPEN…FOR INPUT`
wrote `NAME`'s exact footprint and survived — so a zero footprint would be
informative and a matching one would NOT settle it.
📋 **ALSO OPEN:** `FIELD`/`LSET` need their OWN sweep against their own control
(a RANDOM channel the current control does not have). 📋 **THEN** the 12
`cap_gap > step` sites (TIER 2 🔭). ⚠️ **THE SUPERSEDED LINE BELOW ASKED FOR THE
VERB SWEEP** — done.

➡️ ~~**THE NEXT ITEM: THE REMAINING VERBS — and the write probe UNBLOCKS THEM.**~~
`FILES`/`LFILES` were skipped because a listing scrolls the screen the fence is
read from; `scratchpad/aliaswrite_probe.py` scores off the IMAGE, so a printing
verb is now testable. Sweep `FILES`, `LFILES`, `COPY`, `FIELD`, `LSET`,
`DSKI$`/`DSKO$`, `SAVE`, `LOAD` through it. Pure measurement, no ruling.
📋 **THEN** the 12 `cap_gap > step` sites (`scratchpad/gapscan.py --tracked`,
TIER 2 🔭, `settle_n` is the instrument).
🙋 **AND THE REMEDY IS STILL JOOST'S** — (a) same address, (b) one shared
buffer, (c) DISJOINT. ⚠️ None of them adds a restage, and the defect reproduces
at `174bf887` with no aliasing anywhere, so **none of the three closes it.**
⚠️ **THE SUPERSEDED LINE BELOW ASKED ABOUT THE WRITE PATH** — answered.

➡️ ~~**THE NEXT ITEM: DOES THE WRITE PATH LOSE DATA TOO? — pure measurement.**~~ The
read side is done. `FWR_*` streams through the SAME `FSECTOR_BUF`, so
`OPEN FOR OUTPUT` · `PRINT#1` · *[disk verb]* · `PRINT#1` · `CLOSE` may commit
the verb's leftovers TO DISK. That would be data loss on the medium rather than a
bad read, and it is strictly worse. Read the file back in the same program AND
parse the image on the host. ⚠️ **A WRITE-SIDE ARM MUST NOT SCORE OFF THE SCREEN**
— take lengths and bytes out of RAM or off the host-parsed image.
📋 **ALSO OPEN:** the untested verbs (`FILES`/`LFILES`, `COPY`, `FIELD`, `LSET`,
`DSKI$`/`DSKO$`, `SAVE`/`LOAD`) — lower value now the mechanism is known, but
they are the denominator. 📋 **THEN** the 12 `cap_gap > step` sites (TIER 2 🔭).
⚠️ **THE SUPERSEDED LINE BELOW ASKED "WHY EMPTY"** — answered; do not re-run it.

➡️ ~~**THE NEXT ITEM: WHY EMPTY AND NOT GARBAGE.**~~ An overwritten-but-believed
buffer should return the WRONG BYTES, not none. `FREAD_OFF`/`FREAD_LEFT`
(`$E9E6`/`$E9E8`) and the `FCH_STATE0` span (`$E9C9..$E9FA`) are all OUTSIDE the
clobbered window, so **the counter that reaches zero is not identified.** Point
the `aliasscope` watchpoint method at those cells across the verb. Pure
measurement, no ruling.
📋 **ALSO OPEN:** the untested verbs — `FILES`/`LFILES`, `COPY`, `FIELD`, `LSET`,
`DSKI$`/`DSKO$`, `SAVE`/`LOAD`. ⚠️ A LISTING verb needs a readout that is NOT the
screen the fence is read from. 📋 **THEN** the 12 `cap_gap > step` sites (TIER 2 🔭).
⚠️ **THE SUPERSEDED LINE BELOW SAID THE EXTENT SWEEP WAS NEXT** — it is done.

➡️ ~~**THE NEXT ITEM IS D-ALIASBITE'S EXTENT — pure measurement, no ruling.**~~ The
filed item says so itself: *"THE VERB LIST IS TWO, NOT A CLASS."* Does every
mounting verb do it? Does it need a disk VERB at all, or does any second file
operation (a second `OPEN`, a `PRINT#` on another channel) do it? Each answer
widens or narrows a TIER 1 defect and none of it needs Joost.
📋 **THEN:** the 12 `cap_gap > step` probe sites (TIER 2 🔭, `settle_n` is the
instrument). ⚠️ **THE SUPERSEDED LINE BELOW SAID THE SAME-ADDRESS QUESTION WAS
NEXT** — it is done; do not re-run it.

➡️ ~~**THE NEXT ITEM IS THE SAME-ADDRESS QUESTION**~~ (*"should main and `disk.rom`
use the same address for the same thing?"*), which Joost approved
(*"3.: yes, this one as well"*) and which is TIER 2.
🟢 **AND ITS BLOCKER IS NOW EXPLAINED:** `scratchpad/aliasbite_probe.py` REFUSED
to issue a verdict because its CONTROL would not run. **The control was fine and
the probe needs a `run_gap`** — chasing that control is what produced D-TWOFILE.
Give it one and re-run before touching anything else.
⚠️ **§6.6q's overlap is a NEIGHBOUR again, not a suspect** — it was promoted to
suspect by the withdrawn screen headline.
📋 **Filed out of it, TIER 2 🔭 SCOUT-THEN-ASK:** do the **12 probe sites** that
pass `cap_gap > step` with no `run_gap` (`scratchpad/gapscan.py --tracked`)
actually capture their cases in time? Two say in their own comments that
`cap_gap` covers the run. `settle_n` is the instrument and was never pointed at
it. **Advisory, not a gate** — a wide `cap_gap` is legitimate inter-case spacing.

🔴 **WHAT THIS COST AND THE RULE IT EARNED:** five diagnoses of the ROM, each
refuted by measurement, before the apparatus was ever a candidate. **When two or
more hypotheses about the SUBJECT are each refuted, promote the INSTRUMENT to
first suspect** — do not reach for a third about the subject. And a six-row table
fit perfectly because all six rows shared the one instrument bug: **ask what the
rows SHARE before asking what separates them.**
[[a-rule-that-fits-every-row-may-be-fitting-the-instrument]]
[[a-fact-documented-where-the-caller-never-looks]]

### What this arc keeps re-learning

* **`DISKOP_STATUS` IS A SHARED CHANNEL — WRITE IT ONCE, LAST.** Main's FAT
  primitives marshal their own disposition through the same cell, so a handler
  that pre-sets it and lets later paths overwrite reads whatever they left.
  Measured: `NAME "A.BAS" AS "B.BAS"` at an EMPTY DRIVE answered `Syntax error`
  instead of `Disk offline`. A moved body should RETURN its status in `A`.
* **`FAT_DBUF`/`FAT_MBUF`, NEVER `FSECTOR_BUF`/`FWBUF`, in anything shared.**
  `disk.rom` binds them to `$E2A0`/`$E560`; main binds them to `$E5C0`/`$E7C0`.
  The wrong spelling ASSEMBLES CLEAN and reads a buffer nobody filled. It is a
  gate now (`make shared-body-check` rule 2) but only over `*-body.inc`.
* **A LOCAL `fat_find`'s RESULT MUST SURVIVE A CALL-BACK, OR THERE MUST BE NO
  CALL-BACK IN THE WINDOW.** `KILL` had one name so the question never arose;
  `NAME` sidesteps it by ORDER; `COPY` answers it with a main sysvar that has one
  consumer. §6.6av — the general question — is still open.
* **A ROM CHANGE INVALIDATES THE KNIFE PIN.** `tier_table.py` REFUSES until
  `scratchpad/kwknife.py --all` AND `--allfn` are re-run (~15 min, and they must
  not overlap another emulator probe). A comment-only `.inc` edit leaves the
  hashes identical and needs neither.

## 📦 STATE AS OF 2026-09-16 — superseded above, kept for its lessons

⚠️ **THE CRON PROMPT IS STALE AND HAS BEEN ALL SESSION.** It still says *"NEXT
VERBS: NAME, then COPY, then FILES/LFILES"* and *"DO NOT rely on CF across
CALSLT — it was never measured"*. All three verbs shipped; CF is measured
two-sided. **This file is the durable half — believe it over the prompt.**

### The autonomous queue is EMPTY except TIER 4

Every tiered 🤖 item below TIER 4 is closed. What is left:
* **TIER 4 speed** — the interpreter's 2.5–3.8× band, `PAINT` 1.9–2.0×, `PUT`.
  Large, open-ended, and the only tiered autonomous work remaining.
* 🙋 **THREE RULINGS WAIT ON JOOST, and none should be taken alone:**
  1. **`VARPTR(#n)`** — the references stride **265** (MSX's FCB: 256-byte record
     + 9 header), ours would be **306** (`FCH_STATESZ` 50 + `FCH_RECMAX` 256).
     The ADDRESS cannot agree between machines, so a row must read a DELTA — and
     ours cannot match. Implement anyway and document the divergence, or leave it
     deferred and score `VARPTR` 1/2 by design?
     ([`varptrn_probe.py`](varptrn_probe.py))
  2. **The channel-verb CLUSTER MOVE** — `$FE5D` is recovered (it is the cell
     BOTH `OPEN` and `MERGE` arrive through), but `ex_open` has **40** page-1
     call sites with **18 inside loops** against ~3 and none for the FAT-light
     four. The channel HELPERS must travel WITH the bodies; that is a slice shape
     phase 3 has not done. ([`xslot_chanprice.py`](xslot_chanprice.py))
  3. **`LOAD"CAS:"`** — bug-for-bug fidelity costs a working feature and the
     faithful behaviour is a HANG no row can carry.

### What the disk-verb carve bought, and it is the session's through-line

`make basic-reloc` on 2026-09-16: **main page 1 61 B free, low region 36 B,
`disk.rom` 8490 B** — from **3 B and 0 B**. Moving the FAT-light four into
`disk.rom` (`0f15a873` KILL · `b26857de` NAME · `3f6a6099` COPY · `e1bbf7e5`
FILES/LFILES) paid for **six** items that had been diagnosed, priced and parked
on bytes that did not exist:

| item | cost | what was actually wrong |
|---|---|---|
| `FIELD`/`LSET`/`RSET` gate | 20 B | genuinely blocked on bytes |
| `INPUT$` console form | 21 B | genuinely missing code |
| `SCREEN` key click | 9 B | *"no cell any row can read"* — **false** |
| `LOCATE` cursor switch | 10 B | a declined deviation whose premise was about the wrong side |
| `DSKF` drive range | 16 B | *"blocked on the same 8 bytes"* |
| `SWAP` type order | 10 B | *"priced at ten bytes, which had eight"* |

Plus `D-STOPEDGE`, which cost no bytes and turned out to be a hole in **shared
trap machinery** rather than in `STOP`.

📏 **`kwsweep` reads `SUPPORTED=362` — zero MISSING, zero scored DIVERGENT** (only
`csrlin`, WEAK-excluded by its own row note). **150 of 163** statements at TIER 1.
No keyword is unreachable by the knife. **Recount all of it; never quote it.**

### 🔴 What this session kept re-learning

* **RE-VERIFY THE BLOCKER BEFORE READING THE ITEM.** Fifteen re-verified, **fourteen
  stale**. Two were blocked by a SENTENCE, not by the machine. The one that
  survived (`VARPTR(#n)`) had NO stated reason at all until it was measured.
* **AN AGREEING ROW BESIDE EVERY ERROR ROW.** `DSKF`'s first cut made EVERY call
  answer `Bad drive name` — and the TIER 3 row PASSED, because a refusal is what
  it asserts. Only the happy-path row dissented.
* **A BATCHED SUITE'S RESET MUST RESTORE EVERY GLOBAL ITS CASES MOVE**, or a row
  measures its predecessors. Making `CSRSW` live broke three suites at once, and
  `missing-acceptance` reported the damage as *"good news about the tree"*.
* **A FIX THAT CHANGES NOTHING IS A QUESTION ABOUT THE MECHANISM.** D-STOPEDGE's
  first patch moved no reading because `STOP OFF` had already destroyed the bit
  it tested.
* **CORRECT CODE IN THE WRONG PLACE IN A CONTROL-FLOW GRAPH** is invisible in a
  diff: a block dropped into a fallthrough gap (`sea_click`), a shared RAM
  channel written too early (`DISKOP_STATUS`). Both caught by suites, neither by
  the probe written for the feature.
* **AN ITEM'S MARKER CAN BE SUPERSEDED INSIDE ITS OWN BLOCK** — take the LAST,
  not the first. Taking the first reported 🙋 work as autonomous AND hid a TIER 1
  item.
* **A MESSAGE CAN ASSERT A PROPERTY IT NEVER TESTED** and send you after useless
  work (`tier_table`'s nested-checkbox warning, D-KWBACKTICK).

## 🔴 CURRENT ORDER (2026-09-15, Joost): FINISH THE DISK KEYWORDS, THEN THE TODO

He ruled the mechanism proven once phase 2 shipped: *"the mechanism is proven I
guess ... continue with the disk keywords and afterwards back to the generic
todo"*.

The arc is [`spec-diskbasic-hook-rearchitecture.md`](../disk/docs/spec-diskbasic-hook-rearchitecture.md).
Shipped, do not redo: `f3188146` the spec · `7ad4f4ef` 0a cross-ROM dead code ·
`0d18d3d1` 0b the inter-slot call priced · `8a79c2b5` 0c htimi_guard ·
`cee9ce9b` 1 the ABI · `0f15a873` 2 KILL's body moved.

**The pattern phase 2 established, to copy verb by verb.** Main keeps the cursor
hand-off and the status decode; the body becomes an `hk_*` in `disk/kernel.asm`;
`hook_tab` points the hook at it; `chan_gate`'s presence test and `diskslot_test`
VANISH rather than move — that is where most of the saving is. The cursor crosses
in `FN_RESUME`, because `chan_gate` needs HL for the hook cell and clobbers DE.
Call-back targets go in `REQUIRED_DISK_CALLBACK`, 7 B a site, 0.156 ms a call.
**Measured ABI: HL/DE/BC/A cross BOTH ways intact**; IX/IY are the ABI's own; a
callee may RAISE and never return, so do nothing after a call-back that an abort
would skip. **CF crosses too** — measured two-sided in the NAME slice, a callee
that SETS carry comes back set and one that CLEARS it comes back clear, so a
disposition may be read from it (the earlier "never measured, do not rely on it"
is superseded).
🔴 **BUT `DISKOP_STATUS` IS A SHARED CHANNEL, NOT THE HANDLER'S.** Main's FAT
primitives are `ld a,DISKOP_SEL_* / jr fatprim_bounce` shims that marshal their
own disposition through that same cell, so a handler may only write it **once,
LAST**. Pre-setting it and letting later paths overwrite is what made `NAME ...
AS ...` answer `Syntax error` at an empty drive — and it passed the happy-path
row, because success rewrites the cell on the way out.
🔴 **AND `disk.rom` HAS ITS OWN FAT** (`disk/fat.asm`, for MSX-DOS). Importing
main's collides; NAME imports them aliased (`main_fat_mount=fat_mount`) because
main's `fat_find` writes the entry location the dirverb tenant reads. Which FAT a
disk verb should use is phase 4's question.

**Shipped so far in phase 3**: `0f15a873` KILL · `b26857de` NAME · `3f6a6099`
COPY (both halves, and it freed LOW-REGION bytes) · FILES/LFILES in flight.
⚠️ **CHECK EVERY VERB'S ROWS BY NAME.** `diskbasic-acceptance` says 34/34 and has
**no COPY row and no LFILES row**. COPY's gate is `copy-acceptance` (8 rows, with
byte-for-byte content checks); LFILES's is `lptverb-acceptance` (46 rows, and it
names the sides it cannot measure).

⚠️ **A ROM CHANGE COSTS THREE RE-RUNS**, and until they happen `selftest-check`
and `tiers-md-check` are red as ONE fact reported twice: `kwknife.py --all` AND
`--allfn`, then full `make kwsweep`, then `make tiers-md`.
⚠️ **A NEW SECTION HEADER NEEDS AN INLINE CITATION** or the clean-room audit
fails the battery in WARM-UP (rc=2) before a single unit runs.

## Where things stand (rewritten 2026-09-15)

🏗️ **JOOST RULED 2026-09-15 — READ THIS BEFORE PICKING ANYTHING UP. Five
decisions, and they set the order of the next slices. Do not re-ask.**

0. 🛑 **PARKED THE SAME DAY IT WAS APPROVED — READ BOTH RULINGS.** Joost
   approved rung 3 on 2026-09-15 (*"D-VERBPART — option 3 is priced ->
   approved"*) against **256 B**, then ruled *"Park it — carve somewhere else"*
   once D-VERBCLASS measured the realisable relief at **36 B** (a 258 B span is
   STAY 155 / TENANT 67 / MOVE 36). ⛔ **NO BYTES MOVE; RUNGS 3, 3b AND 4 DO NOT
   RE-OPEN WITHOUT A NEW RULING.** The carve must come from elsewhere — Route D
   (`jp`→`jr`, which RENEWS on every insertion) first, then the instruction-pair
   ngram sweep, then ruling 5's sub-ROM carve for tape. What needs the bytes: the
   three diskless gates (`FIELD $FE2B`, `LSET $FE21`, `RSET $FE26`), 16-24 B
   against main page 1's 3 B free (2026-09-15).
   *(The superseded approval, for the record:)* the relocation was unblocked at
   its cheapest rung: `COPY`, `FILES`/`LFILES`, `KILL`, `NAME` move to `disk.rom`, **256 B** of
   main page 1. ⚠️ **RUNG 3 AND NOTHING ELSE** — 3b (1231 B), 4 (2315 B),
   `field.asm` and the 975 B channel machinery are NOT approved by it.
   🔴 **AND THE FIRST STEP IS NOT A MOVE**: the `$4004` consumer slot-walk does
   not exist (`disk/init.asm:18` is `dw 0`, an unknown statement falls to
   `stmt_error`), so that INTERPRETER change lands on its own slice first. Then the
   verbs; then `kwknife.py --all` AND `--allfn`, because a relocation moves code
   between REGIONS and the one-run re-stamp is not enough. Spec:
   [`disk/docs/spec-diskbasic-relocation-seam.md`](../disk/docs/spec-diskbasic-relocation-seam.md).
   **This is ruling 2's prerequisite carve** — the four code forms land after it.
1. **`SAVE"x",A` — SPEND THE 3 B.** The ASCII save must END the run.
2. **The four code forms (LOCATE cursor switch, SCREEN key click, `VARPTR(#n)`,
   `INPUT$` console form) — CARVE FIRST, THEN ALL FOUR TOGETHER.** A carve slice
   is the prerequisite; do not dribble them into the leftover bytes.
   🟢 **THE CARVE IS NAMED AND APPROVED: ruling 0's option 3, 256 B.**
3. ✅ **DONE (D-KWRUNFILE): `PROG3.BAS` = `10 PRINT"[3h]"`, appended last.**
   `RUN` 3/3; `LOAD` 1/2 (its plain form cannot get a row here). The disk group's
   `step` went 5.0 → 8.0 in the same slice — a case slower than `step` has its
   successor typed into a still-running program, and `open_c` blanked twice before
   the fix moved from the row to the GROUP.
   *(original ruling: ADD A SECOND `.BAS`, LEAVE `PROG.BAS` ALONE.)* It must
   PRINT a marker; that is what makes `RUN"<file>"` and `LOAD` observable. Nothing
   existing changes its bytes, so every suite mounting `disk/test720.dsk` keeps
   reading what it read.
4. **The unreachable forms — BUILD A RIG, not an exemption.** `KEY`'s display
   forms, `PAD`'s switch, `STICK`/`STRIG`'s joystick halves keep counting against
   us until a rig drives openMSX's HOST-side joystick and reads the key line where
   it actually sits.
5. 📍 **PLACEMENT: DISK CODE BELONGS IN THE DISK ROM as much as possible; TAPE
   CODE IS A GOOD CANDIDATE FOR THE SUB ROM.** This is the carve's FIRST lever,
   ahead of any instruction-level shaving: main page 1 has **8 B** free and the
   low region **0**, against **~8820 B in `disk.rom`** (32 runs, largest usable
   hole 3182 B) and 505 B in sub page 0. `ascii_save` is disk code sitting in the
   main image and is a migration candidate in its own right.

Recount everything — never quote a number from this file. `make tiers-md` then
read `docs/tier-status.md`; the headline is in its **STATEMENT — 163** paragraph.

* 🎯 **THE WORK IS TIER 1 OVER THE STATEMENT DENOMINATOR.** TWO denominators:
  TOKEN **159** (`basic/kwtable.inc`, guarded by selftest S20, never to be
  weakened) and STATEMENT **163** = 144 keywords with a bare statement form plus
  the 19 composite and channel statements. As of 2026-09-15 the second reads
  **140** — it was 121 at the start of that night's run.
* 🎚️ **TIER 1 = CONNECTED + every AUTHORED FORM covered by an agreeing row +
  no open TIER **1** item** (tier n blocks tier n ONLY — Joost confirmed
  2026-09-14, `blocks_tier1()`, selftest S34). N is authored per statement in
  `tools/kwforms.py` **from the REFERENCE's syntax, never from our handler**. No
  entry ⇒ UNRATED, never satisfied. **A FORM IS A DISTINCT BEHAVIOUR, NOT A
  DISTINCT INPUT.**
* 🔧 **SEVEN RIGS NOW, AND THE LAST TWO ARE THE NEW ONES.** `NEEDS-DISK:`,
  `NEEDS-PRINTER:`, `NEEDS-LOG:`, `NEEDS-TAPE:`, `NEEDS-BLANKTAPE:`, and then
  **`NEEDS-HOLD:<row>,<mask>`** (holds one KEY-MATRIX bit down for a case's whole
  RUN — row 8 bit 0 is SPACE, bits 4/5/6/7 are left/up/down/right, row 6 $20/$40
  are F1/F2) and **`NEEDS-PLUG:<port>,<device>`** (openMSX `plug joyport<port>
  <device>`). Both take an ARGUMENT, which is part of the capture group key.
  `strig_hold` is the matrix rig's CONTROL and is in the sweep for good: if it
  ever reads `[1w 0 ]` the matrix is not being reached and nothing that depends on
  it may be believed.
* ⛔ **WHAT IS LEFT, AND WHY — and not one of them is "nobody looked".** Recount
  the number; the KINDS are stable. **Blocked on CODE, priced, Joost's call:**
  `SAVE` (the ASCII-save tail ends the run on the reference, +3 B against 8 B free
  in main page 1), `LOCATE` (cursor switch), `SCREEN` (key click), `VARPTR` (`#n`),
  `INPUT$` (console form). **Blocked on the INSTRUMENT, measured:** `KEY` (the
  function-key line's layout differs — LINLEN 37 vs 39), `PAD` (no host button),
  `STICK`/`STRIG` (openMSX drives a joystick from the HOST, which the emulated key
  matrix cannot reach), `RUN"file"`/`LOAD` (the loaded program REPLACES ours so
  nothing can print afterwards — `PROG.BAS` POKEs a landmark instead of PRINTING
  one, and changing the fixture touches every suite that mounts it), `AUTO` (the
  increment needs a multi-line direct interaction this harness has no shape for),
  `CONT` (two-phase delivery). **A bar the tree is genuinely far from:** `DRAW`
  1/10, `PLAY` 0/11, both authored from the tree's own specs. **No happy path
  reachable here:** `CALL`, `MAX` — reservedness only.
* 🔴 **`DELETE` AND `RENUM` ARE MEASURED SHUT FOR THIS INSTRUMENT** and should
  not be re-opened with rows: `DELETE 20` inside a running program stops it
  cleanly on BOTH machines (so every range form has the same observable) and
  `RENUM 100` answers `Undefined line 100 in 20` on BOTH (its only reading is an
  error). `scratchpad/mdr_probe.py`.
* 📏 **THE MEASURED CADENCE**, so a fresh session can plan: a full battery is
  **~910 s** and `make gates-fast` **~70 s**; `make kwsweep` alone is ~120 s.
  One battery per slice, and batch several statements into each.

## Twelve blockers re-verified, twelve stale

Not one survived contact with a measurement. `INKEY$` was the last and the most
convincing: filed as needing a HARNESS change to time a keystroke against
D-LATCH/D-LATCH2 — all true, and beside the point, because **a key does not have
to be TYPED to be waiting.** The BIOS type-ahead buffer is ordinary work area and
BASIC can POKE it.

➡️ **A blocker is written down at the moment of most confusion about a problem,
and then never re-read against what was learned afterwards.** Re-verifying has
been cheaper than the work it was hiding every single time.

## What the tape arc cost, and the rule it earned

Four slices went into the WAVEFORM — duty cycle, tone periods, leader lengths,
three refuted hypotheses — when the actual defect was **seven missing `$00`
bytes** at the end of the data block. The oracle had been sitting in
`cas_encode.build_cas_basic` the whole time: our own encoder already encoded the
right answer and no probe had ever diffed the WRITER against it.

➡️ **WHEN A CONSUMER HANGS, DIFF THE BYTES BEFORE THEORISING ABOUT TIMING.** A
format is finite and checkable; timing is an open-ended space that will always
absorb one more hypothesis. Both causes produce the identical symptom, and I
ranked them by which was more interesting rather than which was cheaper to check.

🔴 **AND TWO OF MY OWN REFUTATIONS WERE RETRACTED IN THE SAME ARC**: "leader
length is dead" had been measured on a DIFFERENT build (the lopsided writer,
where the leader was not the binding constraint), and the between-tone-outlier
histogram never predicted the outcome — the cleanest recording ever produced read
the WORST. **A refutation is only as general as the build it was measured on.**

## The next slice — keep taking TIER 1 over the 163

THE LOOP: handler first (if any) → rows + `tools/kwforms.py` in ONE edit pass →
`make kwsweep ONLY=a,b,c` → **READ EACH READING ONE AT A TIME** → knife
(`--fn` for functions) → `make repack-machine` → `check_todo_citations.py --fix`
→ `make kwsweep && make tiers-md` → `make gates-fast` → stage → ONE full battery
plus the five excluded targets → ONE commit naming every statement.

🚩 **THE FIVE APPARATUS FAULTS THIS ARC KEEPS REPEATING**, every one of which
produced a row that agreed while proving nothing:
1. **A ROW CAN AGREE ON AN ERROR.** `fnkw` scored SUPPORTED on `Illegal direct`
   from both machines because `DEF FN` is illegal in direct mode. Read the VALUE,
   not the verdict.
2. **A ROW CAN AGREE ON FURNITURE THAT DIFFERS.** The `KEY ON`/`OFF` rows read a
   fixed VRAM offset and scored SUPPORTED on a BLANK CELL, because the key line
   sits somewhere else on the reference (LINLEN 37 vs 39).
3. **A ROW CAN AGREE ON A CONSTANT.** `pdlkw` read 255 — the IDLE line of an
   EMPTY port — which a PDL answering 255 to everything passes. `motor` printed
   `[ok]`. Plug something in; mask to the bit that moves.
4. **INTERPRETER SPEED LEAKS IN.** The `ON KEY` rows came back `?noecho` on the
   REFERENCE only: it finishes ~3x sooner, so it collected far more function-key
   auto-repeats and scrolled the marker away. And a row that waits 120 frames for
   something that must NOT happen is still waiting when the capture is taken —
   30 frames, and count FRAMES (`TIME`) not iterations.
5. **THE KNIFE REPORTING BLIND IS A FINDING, NOT A NUISANCE.** `DATA`'s cut moved
   nothing because the `DATA` sat after the `END` and was never executed. Putting
   it on the execution path turned up a SHIPPED DEFECT.

⚠️ **Rows with NUMBERED LINE TARGETS are fragile under `as_stored`'s greedy
≤34-char packing — VERIFY WITH `omsx_repl.as_stored` FIRST**, pad with long
ASSIGNMENTS, never `REM` (it swallows the rest of its line). **And an `IF` must END
ITS LINE**: a FALSE condition skips the REST OF THE LINE, not just the `THEN`.

## Five ways a kwsweep row can pass while seeing NOTHING

Every one of these SHIPPED a green row before being caught, and mode 1 nearly
shipped again this session as `CSAVE`:

1. **A readback that never moves** — `KEY` via CRTCNT read 24 with `KEY OFF` and
   24 without. `scratchpad/kwdrain_discrim.py`.
2. **A predicate true of ZERO** — an absent keyword parses as an undefined array
   and reads 0, so `INP(&HA8)>=0` passed exactly like the real answer. The same
   trap hides in an ARGUMENT: `BASE(0)` and `DSKF(0)` are honestly 0.
3. **A crunch that names no keyword** — `tier_table`'s WORD regex keeps a
   trailing `$`, so `sprite$(0)=…` credited nothing while reporting SUPPORTED.
4. **An audit that re-implements the consumer's parser** — IMPORT
   `tier_table.kwtable_keywords()`; expect exactly ONE row crediting nothing.
5. **A row that leaves the machine in a MODE THAT EATS THE NEXT CASE** — `AUTO`
   scored itself correctly and took 21 unrelated rows down with it. After adding
   any row, read the WHOLE sweep summary, not just the new verdict.

🔴 **6. A ROW WHOSE READING IS AN ERROR CANNOT TELL A WORKING FEATURE FROM A
DIFFERENTLY-FAILING ONE.** Added 2026-09-13 from `PAD`, and it is general. Modes
1–5 are ways two machines agree about NOTHING; this is a way they agree about the
WRONG THING. `PRINT PAD(9)` is out of range, so a real `PAD` errors while an
absent one auto-dims an array and prints 0 — which discriminates TOKENISED from
NOT. Cut `PAD`'s dispatch and the word is still tokenised, the fallback still
errors, and the row sees no difference. **Prefer a VALUE reading over an ERROR
reading wherever the reference offers one**: a cut turns a number into an error,
which no error-reading row can see. ⚠️ And check the value is not 0 on both sides,
or you have merely traded this mode for mode 2 — `PAD(0..7)` reads 0 on both
machines even with openMSX's touchpad plugged, because an untouched pad correctly
reports nothing.


Plus: **a FIX silently un-attributes its own keyword** — attribution comes from
OPEN items, so leave a row behind when closing a defect.

## 🔴 AN EDIT SCRIPT NEVER SHARES A BACKGROUNDED COMMAND WITH A BATTERY

Learned 2026-09-13, and it cost two silent failures. Batteries are backgrounded
because they are slow; an edit script is foregrounded because **its output is the
only proof it worked**. Bundled together, the script's `AssertionError` scrolled
past under a green battery tail and TWO TODO.md filings were reported as landed
when neither had — the D-TIER0 ruling-and-lesson block and the D-KWKNIFE block.
The second was a cascade: its anchor was text the first would have created.

⚠️ **The anchor that failed was self-inflicted too**: that block had been
DE-INDENTED for the legend section and the later anchor still carried the item
indentation. An anchor copied from what you MEANT to write is not an anchor.

➡️ **Run the edit, READ its output, and only then start the battery.** After any
filing, `grep` the file for the text you think you added: the assert proves the
anchor matched, the grep proves the write landed. (This very rule needed two
attempts — its own first anchor matched TWICE, because the file embeds the whole
restart command and every heading appears in both halves.)


## 🔴 Re-verify every blocker before believing it

**TEN FOR TEN**, plus the two retractions above. The display verbs' "cannot take a
row", the multi-line words', the CF-3300 NO-ORACLE claim, the disk fixture,
`SCREEN`'s mode, `KEY`'s missing constant, `USR`'s "machine code to call",
`WAIT`'s port, and the printer log `LPOS`/`LPRINT`. Re-verifying has been cheaper
than the work it was hiding every single time.

⚠️ **A WAITER THAT MATCHES ITSELF**: `until ! pgrep -f run_gates.py; do sleep;
done` in the background NEVER EXITS — the waiter's own command line contains the
pattern. Use the background task's completion notification.

## Two staging traps

* **After any `basic/`, `sub/` or `tape/` change the build refreshes the patch
  pairs** — stage them WITH that commit; `patch-freshness-check` can only see the
  omission ONE COMMIT LATER, and it names the exact `make` target.
* **`check_todo_citations.py --fix` rewrites EVERY document citing a moved TODO
  block**, five files beyond TODO.md every time. It compares the WORKING TREE, so
  it is green before and after while a stale citation ships in HEAD.

## Open for Joost — do not pick up

* The `CONT` item (TIER 5): inside a program zerobas prints `Can't CONTINUE`
  where the reference prints `Can't CONTINUE in 10`. A DELIBERATE choice recorded
  at `basic/program.asm:1188`.
* Ranking the remaining apparatus blockers (AUTO's line-entry mode, keystroke
  injection, step (c)).

## The command` below into a fresh
session and the loop resumes exactly where it stopped.

## Where things stand

* Tree CLEAN and pushed at `ad7334af`. Recount everything — never quote a number
  from this file.
* 🟢 **EVERY TIER 1 THE DRAIN PRODUCED IS CLOSED** (`NEW` `FILES` `LFILES`
  `MERGE`, plus `LOAD` which only the MERGE sweep could have found), and **the
  whole kwsweep is clean: `DIVERGENT=0`.**
* 🟢 **THE LAST TIER 1 IS UNBLOCKED.** The "Keyword-completeness gaps" umbrella
  item was ⛔ on a fixture that had existed all along; it is now 🤖 AUTONOMOUS,
  its stale counts are replaced by the two COMMANDS that compute them, and its
  exit criterion is runnable: **DONE = the "no known gap" list is EMPTY.**

## What shipped this session

* **D-KWDISK** (`89f43985`) mount the test image on both sides · **D-KWRIG**
  (`0579b2f8`) the printer rig · **D-KWTAPE** (`59937b12`) a filed defect instead
  of a row · **D-DFEND** (`c0bd895e`) `FILES`+`LFILES` were ONE tail, −8 B sub
  page 1 · **D-MERGERET** (`631157c0`) `MERGE` *and* `LOAD`, +4 B main page 1 ·
  **D-KWUMB** (`b4177c61`) the umbrella item · **D-KWLOG** (`ca271f77`)
  `NEEDS-LOG:`, the third rig — a CAPTURE rather than a device — and `LLIST` ·
  **D-KWGET** (`a7dbb7d4`) `GET` (a random-file read, not a keyboard verb) and
  `CALL` (reservedness only, with the shortfall named) · **D-KWINP** (`c6215324`)
  `INPUT`'s FILE form and `RENUM` · **D-KWAUTO** (`21481b1a`) `AUTO`, placed LAST
  with a kwsweep-local tail rule · **the D-KWTAPE retraction** (`1a777438`).
* 🔴 **TWICE NOW A WORD WAS IN THE LIST FOR ITS NAME**: `GET` (a random-file read)
  and `INPUT` (`INPUT #n` reads a file), each filed next to a word with a real
  blocker and inheriting it by adjacency. Check the shape before the blocker.

## Where things stand — JOOST RULED, and the oracle work found a TIER 1

Joost answered the 🙋 item with **"make the 3 missing oracles"**. The first one
paid immediately and not as expected: building it exposed a TIER 1 defect and
retired the 🙋 blocker for `CLOAD` entirely.

* 🟢 **`CLOAD`'s oracle is DONE.** `omsx_repl.run_cases` takes `cassette=` (the
  `-cassetteplayer` seam every cas probe used and none could reach through the
  harness). The VG-8020 reads a clean-room `.cas` — the earlier "no oracle" was a
  FIXTURE that was itself the defect. A `NEEDS-TAPE:` kwsweep rig is now small.
* 🔴 **NEW TIER 1: a tape zerobas writes cannot be read by a real MSX.** Filed with
  the full matrix; `CSAVE`'s kwsweep row should wait for the fix, because the
  defect IS its subject.
* `INKEY$` is untouched — still the injector's timing, still the one to do last.

## The next slice — the tape-writer COMPENSATION, and it is well specified

**MECHANISM CONFIRMED**: the per-bit loop overhead lands inside the LAST
half-period of every bit.

| bit | VG-8020 | zerobas |
|---|---|---|
| `0` (one low-tone cycle) | `18 19` | `18` **`20`** |
| `1` (two high-tone cycles) | `9 9 9 9` | `9 9 9` **`11`** |

Inside a `1` bit the FIRST cycle is clean, so it is the BIT boundary, not
`cas_cycle` (a tight `djnz` pair, constant by construction). The stretch is ~2
samples ≈ 160 T-states ≈ 12 `djnz` iterations against `CAS_HHALF` = 50 — about a
quarter of a short half, enough to push `9` to `11`, above the midpoint between the
tones and unclassifiable by a threshold derived from the leader.

➡️ **THE FIX**: shorten the trailing low half of each bit by the per-bit overhead
so the total stays correct — a `cas_cycle_last` variant taking a reduced count,
with the leader loop keeping the uncompensated one (the leader measures clean).
⚠️ **Byte cost unmeasured** — the tape ROM is its own region; price it first.
⚠️ **FOUR HYPOTHESES ARE ALREADY DEAD** and are in the item: leader length (rebuilt
to the reference's own), inter-block silence (spliced), leading silence (spliced),
mount form. Do not re-run them.
🎯 **THE TEST IS DECISIVE AND WRITTEN**: `scratchpad/kwdrain_wavread.py` (the VG
reads a tape zerobas wrote, with a prompt witness) and
`scratchpad/kwdrain_wavhist.py`, which must come back CLEANLY BIMODAL — nothing
between the tones, which is what the reference produces.

## 🔴 Two staging traps, both paid for on 2026-09-12/13

* **After any `basic/` or `sub/` change the build refreshes
  `zerobas-main-eu.ips`/`.bps`** — stage them WITH that commit.
  `patch-freshness-check` can only see the omission ONE COMMIT LATER.
* **`check_todo_citations.py --fix` rewrites EVERY document that cites a moved
  TODO block**, not just TODO.md. `todo-citation-check` compares the WORKING TREE,
  so it is green before and after and a stale citation ships in HEAD with nothing
  red. Read `git status --short` as a LIST, not a glance.

## Five ways a kwsweep row can pass while seeing NOTHING

Every one of these SHIPPED a green row this session before being caught:

1. **A readback that never moves** — `KEY` via CRTCNT read 24 with `KEY OFF` and
   24 without, on both machines. `scratchpad/kwdrain_discrim.py`.
2. **A predicate true of ZERO** — an absent keyword parses as an undefined array
   and reads 0, so `INP(&HA8)>=0` passed as -1 exactly like the real answer. The
   same trap hides in an ARGUMENT: `BASE(0)` and `DSKF(0)` are honestly 0.
   `scratchpad/kwdrain_boolcheck.py`.
3. **A crunch that names no keyword** — `tier_table`'s WORD regex keeps a
   trailing `$`, so `sprite$(0)=…` credited nothing while reporting SUPPORTED.
4. **An audit that re-implements the consumer's parser** — my ad-hoc regex
   admitted `A` as a keyword and hid a real miss. IMPORT
   `tier_table.kwtable_keywords()`; expect exactly ONE row crediting nothing,
   `swapctl` stmt `a=1`, the intentional bare-assign control.
5. **A row that leaves the machine in a MODE THAT EATS THE NEXT CASE** — `AUTO`
   scored itself correctly and took 21 unrelated rows down with it. After adding
   any row, read the WHOLE sweep summary, not just the new verdict.

Plus: **a FIX silently un-attributes its own keyword**, because attribution comes
from OPEN items — leave a row behind when closing a defect.

## 🔴 Re-verify every blocker before believing it

**TEN FOR TEN this session.** The display verbs' "cannot take a kwsweep row", the
multi-line words' "cannot be expressed in one row", the CF-3300 NO-ORACLE claim,
the disk fixture, `SCREEN`'s mode ("SCREEN 1 is 32 columns" — nothing makes the
row STAY in the mode, and `SCRMOD` IS declared), `KEY`'s missing constant
(`KEY LIST` prints to the SCREEN and needs none), `USR`'s "machine code to call"
(one POKEd `$C9` is machine code), `WAIT`'s port (measure `INP`, then choose the
mask), and the printer log `LPOS`/`LPRINT` never needed (the head COLUMN reaches
the screen; only the printed TEXT needs the log). Re-verifying has been cheaper
than the work it was hiding every single time.

⚠️ **AND A SIXTH SILENT-FAILURE MODE, FOUND THE HARD WAY: A WAITER THAT MATCHES
ITSELF.** `until ! pgrep -f run_gates.py; do sleep; done` run in the background
NEVER EXITS — the waiter's own command line contains `run_gates.py`, so seven of
them sat waiting on each other while the battery they were watching had long
finished. Use the background task's own completion notification; do not poll with
a pattern that appears in the polling command.

## Open for Joost — do not pick up

* The `CONT` item (TIER 5): inside a program zerobas prints `Can't CONTINUE`
  where the reference prints `Can't CONTINUE in 10`. The cause is a DELIBERATE
  `print_msg`-instead-of-`raise_error` choice recorded at `basic/program.asm:1188`.
* Ranking the remaining apparatus blockers (printer log + its LSTOUT hang hazard,
  AUTO's line-entry mode, keystroke injection, step (c)).

## The command

Paste this into a fresh session. ⚠️ **A loop prompt is fixed when it is armed
and cannot learn** — so it points HERE and this file carries the state.

    /loop continue autonomously on zerobas — 🔴 READ scratchpad/LOOP-RESTART.md FIRST (its 2026-09-24 section is current) and BELIEVE IT OVER THIS PROMPT; then the item's own block in TODO.md to its END. 🏗️ JOOST'S RULINGS OF 2026-09-24 ARE IN THAT SECTION'S TABLE — tier order is now 1 happy path · 2 reasonable time · 3 common errors · 4 RAM USAGE (VG-8020) · 5 ON-PAR SPEED · 6 every error; a keyword's LEVEL is its unbroken run of proven rungs; T2 = within 10× the VG-8020's time; T5 = a ratio, never a tick; T6 is NOT ruled. DO NOT RE-ASK ANY OF THEM. ➡️ FIRST ITEM: TIER 1 D-KWPROVEN — build the T2/T5 row type (ONE measurement: zerobas ÷ VG-8020 time + a completion watchdog), with a "too short to time" rule and a NEGATIVE arm, and flip S36e DELIBERATELY. Then the queue in that section, lowest tier first, APPARATUS (the 9-probe filed-row triage) last. 📊 BEFORE CARRYING ANY "WAITING ON JOOST" CLAIM, OPEN THE ITEM AND READ ITS LATEST RULING — two stale blockers rode a whole night on 09-23. Scan markers by BLOCK, strike-aware, and take the LAST live one. Never quote a count or a wall — recount (`python3 tools/tier_table.py --all`, `make basic-reloc` from a CLEAN tree). 🔴 CLEAN ROOM: registers, RAM addresses, work-area RAM contents, I/O ports and slot state are READABLE; never read a ROM byte, follow a hook target, single-step into ROM or disassemble; NEVER read the bytes of the reference's RAM-resident code (§8.5). THE LOOP: implement → `make gates-fast` → `check_todo_citations.py --fix` to a FIXED POINT → `make tiers-md` → stage EXPLICIT paths (`git add -A` banned; a cited scratchpad path must be added BEFORE the gates) → `make gates-plan` (READ its tier and why), then ONE `make gates-scoped` — STATIC for docs, SCOPED for a probe/tool or handler-local ROM change, FULL (+ the five excluded) for shared code, an unknown blast radius, the 5th commit since the last full green, and EVERY hand-off (`make gates-scoped HANDOFF=1` before ending a session) — and TOUCH NOTHING IN THE REPO WHILE IT RUNS (a selftest is not read-only) → ONE commit, message to a FILE stating the GATE TIER that ran, `git commit -F`, check `--stat` and body → PUSH, without asking. Never commit red; READ THE LOG BEFORE BELIEVING ANY RED (today's was mine). A ROM change invalidates the knife pin (`scratchpad/kwknife.py --all` then `--allfn`). NEVER run two emulator probes at once; never `kill -9` a probe's python parent; `set renderer none; set sound_driver null` + a subprocess timeout; `python3 -u`. `ls` the path AS ITS OWN COMMAND before any `cat >` heredoc. Edit scripts to a FILE, anchored on TEXT, refusing on a missing or non-unique anchor; READ their output. State a prediction before every run and SCORE it, misses included. `timeout` does not exist on this host. MEMORY.md breaches at 16 KB — new pointers go to link-index.md. Attribution: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. 🔴 WHEN THE AUTONOMOUS QUEUE EMPTIES, SAY SO PLAINLY AND STOP THE LOOP RATHER THAN INVENTING WORK.
