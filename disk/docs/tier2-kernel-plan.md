<!--
SPDX-License-Identifier: 0BSD
Copyright (c) 2026 Joost Yervante Damad
-->
# Tier-2 kernel phase — the plan to host COMMAND.COM to `A>`

**Status.** GREEN-LIT 2026-06-24 (user: *"we want the full work in the end. The
guidance stands, but we continue."*). This is the forward plan for the phase the
spec [§5](spec-diskrom-kernel.md#5-the-commandcom-load-phase--kerneldisk-rom-call-surface-characterised-reimplementation-deferred)
recorded as *characterised but paused*. It supersedes the "paused" status with a
roadmap; **no asm is written until the architecture fork below is signed off**
(spec-before-implementation).

This plan is itself a documentation deliverable. The provenance trail lives in the
notebook ([`provider-oracle-scope.md`](provider-oracle-scope.md) §8.40–8.46); each
milestone, once settled, distils into [`spec-diskrom-kernel.md`](spec-diskrom-kernel.md) §5.

## Working discipline (standing, restated because this phase is the riskiest)

- **One milestone per session; user reviews between steps.** Opus-driven — no
  sub-agent delegation for judgement on this sub-track.
- **Spec/scope before code.** This doc is that scope; the per-milestone contract is
  characterised and written *before* its asm.
- **Commit each finished milestone** (notebook + spec + probe), no need to ask.
- **Clean-room firewall — the load-bearing rule.** `COMMAND.COM` and `MSXDOS.SYS`
  are **only ever oracles**: identical inputs in, observed outputs out. They are
  **never disassembled or byte-copied** — not their loader bytes, not the page-0
  slot helper, not the `$DDxx` kernel. Every new address / constant / algorithm is
  cited inline to an allowed source (MSX2 TH, map.grauw.nl, hardware datasheets,
  C-BIOS, or our own black-box observation). The one provenance breach this project
  ever had (§8.37) came from a brief that omitted this rule; if any asm is ever
  delegated, the firewall goes in the brief verbatim. `make audit-citations` +
  a human paper-trail pass gate every milestone.
- **No regression.** The unified ROM must keep Disk-BASIC byte-identical: after
  every milestone, `make unit-test`, DSKIO == CF-3300, and the file read/write/dir
  differentials stay green. The cluster lives inside active code, so the M3
  net-zero relocation discipline holds.
- **Scope ceiling.** MSX-DOS **1** only (DOS2 / Nextor is a separate future axis).

## Architecture — what the black box actually requires

§8.45 + §8.46 reframed §8.41's "reproduce the 63 % kernel". There are **two
distinct service surfaces**, not one monolith:

1. **COMMAND.COM's own interface** — what the proprietary shell at `$0100` actually
   calls: its BDOS path (which COMMAND.COM installs at `$0005` itself — `$0005=$00`
   at entry, §8.45) plus the fixed page-1 cluster entries it reaches (e.g. `$607B`
   from `ra=$0100`, §8.41). **This is the surface we must satisfy.**
2. **The page-0 vector table + `$DDxx/$DExx` high-RAM kernel** — §8.46 showed these
   are called only by disk-ROM and high-RAM-kernel PCs, **never by COMMAND.COM**.
   They are the stock's *internal* inter-slot bridge between its page-1 disk ROM and
   the kernel it relocates into high RAM — an artifact of *that* architecture, not a
   contract COMMAND.COM depends on.

### The fork — DECIDED: (a) faithful relocation (user, 2026-06-24)

The two models that were on the table:

- **(a) Faithful relocation model — CHOSEN.** Reproduce the stock's "relocate the
  resident kernel into high RAM + page-0 inter-slot vector table" *structure*: our
  own resident kernel relocated into a high-RAM band, reached through the page-0
  vectors and the inter-slot helper, mirroring the original's internal shape. Maximum
  fidelity to the stock's internal architecture. The user chose maximum fidelity
  over the smaller surface.
- **(b) Minimal page-1 host (not chosen)** — would have kept DOS logic in the page-1
  ROM, reused `bdos_entry`, and satisfied only COMMAND.COM's observable interface.
  Recorded here for provenance; superseded by (a).

**What (a) means under the clean-room rule — read this twice.** "Faithful" is at the
level of *structure and contracts observed black-box*, **never bytes**. We build our
**own** resident-kernel code and relocate it to high RAM; we provide the page-0
vector table with our own targets and an inter-slot helper written from the public
slot-select spec (MSX2 TH / map.grauw.nl). We do **not** copy the stock's relocated
kernel, its loader, its slot helper, or its internal algorithms out of a
disassembly — `MSXDOS.SYS`/`COMMAND.COM` stay pure oracles (inputs in, observed
outputs out). High-RAM addresses are our choice except where a black-box observation
shows COMMAND.COM or a fixed cluster entry depends on a specific value. Because (a)
reproduces internal shape, the temptation to disassemble is highest here — the §8.37
breach is the cautionary tale; the firewall above is non-negotiable.

## Measured scope (the scan, §8.48 — do this before the entry-by-entry grind)

A single coverage pass over the `$D821→$47B2→$D824` span
(`disk_probe_dosboot_scope.py`) sizes the whole job up front. The *executed* code on
the path to `A>` is far smaller than the "63 % / ~10 KB shared kernel" ROM figure —
that was the kernel's size, not what runs:

Definitive footprint of the whole `$D821 → A> idle` phase (§8.52, scan 5 — merges
the load span + tail, stops auto-detected at idle):

| region | size | ranges | what |
|--------|------|--------|------|
| TPA / COMMAND.COM | 1,488 B | 11 | proprietary — we **load + run**, never reimplement |
| **disk-ROM (page 1)** | **3,680 B** | 23 | the cluster bodies we fill behind the veneers (M5.6…N) |
| **high-RAM kernel** | **1,920 B** | 15 | the relocation surface (a) mirrors (M5.2/M5.4) |
| **code we must build** | **5,600 B** | | between §8.41's ~10.4 KB worst case and §8.48's ~2.9 KB optimism — now measured |

The 15 high-RAM regions (M5.2 blueprint): `$C200-C27F` `$CB90-CBDF` `$CE50-D00F`
`$D070-D08F` `$D600-D60F` `$D820-D8BF` `$DDA0-DDEF` `$DE50-DF6F` `$EF90-F05F` (hot
loop) `$F0F0-F17F` `$F1C0-F1FF` `$F250-F2BF` `$F360-F39F` `$FD90-FDCF` `$FFC0-FFDF`.

**Offset:** the 3,680 B disk-ROM cluster largely *overlaps routines zerobas already
has* (DSKIO `$4010`, the FAT/dir code, `bdos_entry`), so genuinely *new* code is less
than 5,600 B — much of M5.6…N is wiring existing routines to the observed veneer
contracts, not writing afresh.

> **Correction (§8.53).** The **1,920 B high-RAM is an over-count of "our" work** —
> MSXDOS.SYS (the DOS kernel) relocates *itself* into high RAM (~`$D300-$DC7F`), so
> the `$D6xx/$D8xx` code (~176 B) is *loaded* MSXDOS.SYS and the `$DDxx/$DExx`
> handlers (~368 B) are MSXDOS.SYS-*installed* — **not code we write** (like
> COMMAND.COM). The `$C2xx-$D0xx` regions (~688 B) are probably MSXDOS.SYS
> buffers/data too. Our real high-RAM job is the **disk-ROM-built work area**
> (`$F100-$F3FF`: the `$F2xx` CALSLT table, `$F368` table, DPBs — partly built in the
> §8.18-8.30 a3 work) plus `$EF9x`/`$FD9x` (TBD). So fork-(a) "faithful relocation"
> of the *kernel* is done by loading MSXDOS.SYS — we don't rewrite the `$DExx`
> kernel; our work is the plumbing + work area. **Net high-RAM to build: < 1,920 B
> (likely ~600-1,200 B); exact split is an M5.2 task.** Total "to build" is therefore
> **< 5,600 B.**

The 8 high-RAM regions: `$DDA0-$DDEF` (RST-38 / `$DDAE`), `$DE50-$DF1F`
(`$DE54`/`$DE9B` vector targets), **`$EF90-$F05F` (one hot wait/copy loop — ~94 % of
all span instructions; reimplement its *contract*, not its iteration count)**,
`$F0F0-$F17F` (= `$F100-$F17C` driver dispatch, §2), `$F250-$F2AF`, `$F360-$F39F`
(= `$F368`/`$F37D` BDOS-vector area, §8.9/§8.18), `$FD90-$FDAF` (= `$FDA0`, §8.46),
`$FFC0-$FFDF` (near `$FFFF`). Several are already characterised work-area structures.

**Caveat:** coverage = this one canonical boot; paths COMMAND.COM doesn't take here
are out of scope (acceptable — the goal is hosting *this* disk to `A>`). The
interactive command loop after `$D824` is a separate small scan, run before
M5.final.

### Kernel decomposition (scans 2+3, §8.49/§8.50)

The call-edge + contract scans resolved the (a) high-RAM kernel into five parts —
the M5.2/M5.4 blueprint, with register contracts already captured:

1. **`$F252-$F2A3` — inter-slot trampoline table (~13 stubs).** One stub per page-1
   cluster entry; register-transparent (stub entry-regs == target entry-regs), using
   the standard **`CALSLT` convention** (`IX=target`, `IYh=slot 3`). Build once as a
   parameterised mechanism from the public inter-slot spec — *not* 13 routines.
2. **Page-0 vector handlers** — `$0038→$DDAE` (interrupt), `$001C→$DE54`,
   `$0024→$DE9B`, and the `$0054` slot-helper return into `$DF0C/$DE97`.
3. **`$EF95/$EF9B` hot copy/wait loop** (the `$EF90-$F05F` region, ~94 % of span
   instructions) — reimplement the contract, not the iteration count.
4. **COMMAND.COM service gateway** — `$FD9A/$FD9F/$FDA3` (+ `$F38C/$F392/$F397`),
   the entries COMMAND.COM's own code calls (never `$0005`, never page-1 directly);
   chains to worker `$782B`.
5. **Disk-read dispatch** — `$F365→$4010` DSKIO; the COMMAND.COM load itself is a
   **single DSKIO call, B=13 sectors → `$0100`** (= 6656 B, COMMAND.COM's size) =
   the core of `k_47B2`.

Scanning phase complete (scans 1-5, §8.48-8.52): footprint, call graph, per-entry
register contracts, and the definitive `$D821 → A> idle` sizing are all captured.

**What "scans complete" does and does not mean.** The scans delivered the *map* —
where every routine is, who calls it, and its register calling convention — plus a
*bounded sizing* (~5.6 KB, ~38 regions, ~40 % reuse/mechanical). They did **not**
pre-characterise behavior: for the **C** regions the register I/O is only a skeleton;
the real data contract (memory read/written, the algorithm-as-contract) still has to
be characterised **per region** by deeper black-box probing — and that is the
*characterise* half of each milestone, inherently per-routine, not front-loadable.
R+M are fully specified by the scans; r needs one confirming probe each. So the
expensive work (behavioral characterisation + implementation of the C set) is still
ahead — region by region, one per session — exactly the "major multi-session
project" §8.41 anticipated.

The next step is **M5.4** (stand up the trampoline table + page-0 vectors, validated
standalone), the first asm — an R+M region, so fully spec'd already.

## Progress ledger (update at every step)

Denominator = the §8.52 measured footprint of code **we must build** for the
COMMAND.COM-load→`A>` phase: **5,600 B** (disk-ROM cluster 3,680 B + high-RAM kernel
1,920 B; COMMAND.COM's own 1,488 B is proprietary load+run, not counted). A region
is **done** only when its contract is implemented *and* validated by the progress
probe. "Reuse" = an existing zerobas routine the body will wire to (faster than
greenfield, but not *done* until wired + validated).

Legend: **✅ done** (implemented + validated → counts as covered) · **🟨 veneer**
(M3 scaffold placed, body is a `ret` stub — contract not yet filled) · **⬜ todo**
(no scaffold yet).

Prefill class (where grounded front-loading is safe — *guessing is not used*):
**R** reuse-ready (wire to an existing validated routine now) · **M** mechanical
(build once from public spec) · **r** reuse-likely (our FAT/BDOS family — confirm the
captured contract before wiring) · **C** characterise (orchestration / hot path /
relocated-kernel code; needs the full characterise→implement→validate loop).
Front-loadable now = **R+M (400 B)**; after a contract-confirm = **r (1,744 B)**;
**C (3,280 B)** must follow the boot in order.

Bar chars: `█` done · `▒` veneer · `░` todo.

> *(scans complete + §8.53 sizing correction, pre-M5.4)*
> ```
> TOTAL     █▒▒▒▒▒▒▒▒▒▒░░░░░░░░░  ✅  176 · 🟨2,544 · ⬜2,336  / 5,056 B  (3.5% done)
> disk-ROM  █▒▒▒▒▒▒▒▒▒▒▒▒▒░░░░░  ✅  176 · 🟨2,544 · ⬜  960  / 3,680 B
> hi-RAM    ░░░░░░░░░░░░░░░░░░░░  ✅    0 · 🟨    0 · ⬜1,376  / 1,376 B
> ```
> §8.53: 544 B of high-RAM is **loaded MSXDOS.SYS, not ours** (excluded above); a
> further ~688 B (`$C2xx-$D0xx`) is likely loaded too → total may drop toward
> **~4,368 B** once M5.2 confirms. Covered unchanged (176 B); only the denominator moved.

| disk-ROM range | B | st | cls | hi-RAM range | B | st | cls |
|---|---|---|---|---|---|---|---|
| `4010-40BF` | 176 | ✅ | R DSKIO (done) | `C200-C27F` | 128 | ⬜ | C kernel COMMAND-exec |
| `4170-418F` | 32 | ⬜ | C | `CB90-CBDF` | 80 | ⬜ | C |
| `41F0-436F` | 384 | 🟨 | r `k_41FD` fat/dir | `CE50-D00F` | 448 | ⬜ | C |
| `4400-446F` | 112 | ⬜ | C | `D070-D08F` | 32 | ⬜ | C |
| `44D0-456F` | 160 | 🟨 | r `k_4558` | `D600-D60F` | 16 | ⬜ | C |
| `4600-461F` | 32 | ⬜ | C | `D820-D8BF` | 160 | ⬜ | C COMMAND-exec |
| `46A0-46EF` | 80 | 🟨 | r `k_46C8` | `DDA0-DDEF` | 80 | ⬜ | C RST-38/`$DDAE` |
| `4740-474F` | 16 | ⬜ | C | `DE50-DF6F` | 288 | ⬜ | C vector handlers |
| `47B0-47DF` | 48 | 🟨 | C `k_47B2` loader† | `EF90-F05F` | 208 | ⬜ | C hot loop |
| `4840-49BF` | 384 | 🟨 | r `k_4919/4935/498C/49B4` | `F0F0-F17F` | 144 | ⬜ | r driver dispatch |
| `4A30-4A7F` | 80 | 🟨 | r `k_4A39` | `F1C0-F1FF` | 64 | ⬜ | r work area |
| `4B20-4C4F` | 304 | 🟨 | r `k_4B59/4BE5/4C25` | `F250-F2BF` | 112 | ⬜ | M CALSLT table |
| `4E40-4EFF` | 192 | 🟨 | C `k_4E4B/4EDE` | `F360-F39F` | 64 | ⬜ | r BDOS vec (`$F37D`) |
| `50E0-510F` | 48 | ⬜ | C | `FD90-FDCF` | 64 | ⬜ | C COMMAND gateway |
| `53A0-544F` | 176 | ⬜ | C | `FFC0-FFDF` | 32 | ⬜ | M subslot |
| `54C0-559F` | 224 | ⬜ | C | | | | |
| `5600-569F` | 160 | ⬜ | C | | | | |
| `5FA0-609F` | 256 | 🟨 | R `k_5FE5/607B` → DSKIO/bdos_entry | | | | |
| `6370-637F` | 16 | ⬜ | C | | | | |
| `7490-74DF` | 80 | ⬜ | C | | | | |
| `7580-77BF` | 576 | 🟨 | C `k_75A5/77B8` hot | | | | |
| `7820-786F` | 80 | 🟨 | r `k_782B` | | | | |
| `7940-797F` | 64 | ⬜ | C | | | | |

† `k_47B2` is the COMMAND.COM loader — class C only in that it's bespoke
orchestration, but it is **grounded, not guessed**: read 13 sectors → `$0100` via
our DSKIO, lay the §5.2 page-0 env, set the register contract, transfer in.

## Milestones (each: characterise on stock → implement → re-probe progress)

Sequenced for the **(a) faithful relocation** build; sized by the scan above.

- **M5.1 — COMMAND.COM service-interface map.** Black-box on stock: trace the
  outbound CALL targets COMMAND.COM (`$0100-$1FFF`) invokes, how/when it installs
  `$0005`, and which page-1 cluster entries it reaches. Deliverable: the
  COMMAND.COM→DOS contract list.
- **M5.2 — high-RAM kernel + page-0 vector structure map.** Black-box on stock:
  characterise the structure (a) must mirror — the relocated-kernel band's extent and
  entry points, the contract of each of the six page-0 vectors
  (`$000C/$0014/$001C/$0024/$0030/$0038`), and the inter-slot mechanism. Observed
  shape only; no disassembly. Deliverable: the relocation blueprint (our own
  addresses/code, structurally faithful).
- **M5.3 — BDOS path + gap list.** How COMMAND.COM calls each BDOS function; map onto
  `bdos_entry` (the resident BDOS, now relocated per (a)); list + implement gaps (cf.
  Random-Block-Read, §8.9), validated via `disk_probe_bdos.py` cases.
- **M5.4 — stand up the relocated kernel band + page-0 vector table.** Build our own
  resident kernel into the high-RAM band, lay the page-0 vector table (our targets) +
  the inter-slot helper (from public spec), and wire the disk-ROM↔kernel calls
  through them. Validate in isolation (paging + vector round-trips) before COMMAND.COM
  is involved — the hang-prone part, per the §8.2/§8.4 lessons.
- **M5.5 — `k_47B2` loader body.** Read COMMAND.COM via our CF-3300-identical file
  layer to `$0100`; lay the full page-0 env (§5.2) atop the M5.4 vectors; set the
  register contract; `jp $0100`. Validate: COMMAND.COM's own code runs at `$0200`
  (first proprietary COMMAND.COM code on zerobas) — a new incremental **progress
  probe**.
- **M5.6 … M5.N — fill the page-1 cluster contracts** in the order COMMAND.COM/the
  kernel hit them (the `$5454` playbook ×~N): characterise each on stock, implement
  behind its existing veneer, re-run the progress probe, repeat. One per session.
- **M5.final — reach + validate `A>`.** Pin the `A>` screen
  (`disk_probe_provider_dosboot.py`) against the stock CF-3300 (byte/behaviour), and
  round-trip a `DIR` / file op through the live shell.

## Validation strategy

- **Incremental progress probe** after every milestone: "how far does COMMAND.COM
  get" (PC high-water / last cluster entry reached / screen state) — the single
  metric that says a milestone advanced the boot.
- **Regression gates stay green throughout** (unit-test, DSKIO==CF-3300, file
  diffs) — the unified ROM must never regress Disk-BASIC.
- **Oracle:** `msxdos103-cmd111.dsk` (SHA256 `666cbc6d…`), always on a `/tmp` copy
  (openMSX can write back); `git status` + original-hash check after each run.

## Effort projection (rough — high variance, read the caveat)

A horizon for a fresh session, in **one-hour work-days** (the unit the user is pacing
at). Derived from the observed git pace, **not** a commitment.

*Spent so far:* the sub-track ran 2026-06-22→24 over 3 *dense* calendar days (~60
commits) = roughly **~20–30 one-hour days** of compressed effort — almost all of it
the hard part (understanding + sizing + finding the mechanism), now largely done.

*Remaining:*

| phase | est. 1-hr days |
|---|---|
| M5.4 foundation (R+M: trampoline table + page-0 vectors, validate paging) | 2–4 |
| M5.5 `k_47B2` loader body | 1–3 |
| **r** set (~10 regions: confirm-probe + wire + validate) | 6–12 |
| **C** set (~18 regions: deep characterise + implement + validate) | 12–22 |
| M5.final — integration to `A>` + validation | 4–8 |
| **total** | **~25–50** |

Single-number guess: **~35 one-hour days (≈ 6–10 weeks at 1/day)**.

**Caveat — variance is high and skewed long.** The scans bounded the *size* but not
the *difficulty per region*, and this work's history is a chain of "each fix revealed
the next blocker" (§8.16 refuted, §8.25 falsified, the §8.31–8.40 re-root-causing).
The last-mile integration to `A>` is the wildcard: it could click in a few sessions
or a stubborn paging/timing issue could eat a week. Mitigants vs. the exploratory
phase: a bounded backlog, clean stubs (divergences stay obvious), ~40 % reuse/
mechanical. Re-estimate as the ledger fills — actual days-per-region will quickly
calibrate this.

## Open questions (resolved as milestones land)

- The exact BDOS-call mechanism COMMAND.COM uses (M5.1/M5.3) — `$0005` JP it
  installs, vs. a cluster entry.
- The high-RAM band's placement under (a): which addresses are free to choose vs.
  pinned by a black-box-observed dependency (resolved in M5.2).
- The paging/inter-slot hazard (M5.4) — the historically hang-prone step (§8.2/§8.4);
  validate the relocated band + vectors standalone before COMMAND.COM runs.
