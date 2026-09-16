# Spec — zerobas BASIC audio: `SOUND` + `PLAY` (PSG, MSX1)

**Status: SIGNED OFF (2026-07-21). Slice 1 (`SOUND`) + Slice 2a (`PLAY` parser,
`IDX_PLAY_PARSE`) LANDED 2026-07-21.** Slice 2a detail + gates live in
[spec-basic-audio-play-slice2a.md](spec-basic-audio-play-slice2a.md); its VG-8020
differential corrected §2.2 (`&` tie is NOT MSX1 MML → ERR 5; a voice is a required
string expression — bare comma → Syntax error). Slice 1: the empirical VG-8020 pass
corrected §2.1 (reg 14/15 raise ERR 5, not silently masked). NEXT = Slice 3 (the
live interrupt servicer + `H.TIMI` seam).
Greenfield at spec time: no
audio token, handler, PSG access, or queue exists today (surveyed — see §1). This
spec scopes the whole MSX1 audio surface (`SOUND` direct-write + `PLAY` MML music).
The heavy MML **parser** lands as a **page-1 sub-ROM tenant**; the small live
**queue servicer** stays **resident in the main-ROM page-0 window** (reached from
the interrupt path by a near `JP`, never an inter-slot call).

### Sign-off decisions (2026-07-21)

- **Servicer is resident main-ROM page-0, not a tenant** (supersedes the earlier
  "servicer as page-1 tenant" draft). The reference drains the queue *internally*
  in the BIOS `$0038` ISR — it is not an `H.TIMI` extension. Our ISR is C-BIOS's,
  so `H.TIMI` is our *seam* into it, but the servicer *code* is page-0-resident,
  so the seam is a near `JP` and there is **no inter-slot call in the ISR path**.
  This dissolves the §4.3 reentrancy hazard. Premise: the servicer is small
  (~100–200 B est.) — confirm against the page-0 window budget.
- **Q2 RAM faithfulness: YES** — place the program-visible work-area variables at
  their documented reference addresses (§2.4). More probing, better compatibility.
- **Q3 staging: confirmed** (`SOUND` → parser → live servicer).
- **Q4 PSG access: direct `OUT`** (slot-independent ports).
- **Q5 MML subset: confirmed, MSX1/PSG only**, no MSX-MUSIC/FM.
- **Q6 (`X` substring exec): IN SCOPE as Slice 2b** — land the linear MML grammar
  in 2a, add nested `X` + its resume-stack in 2b (§5).

**Charter fit:** `PLAY`/`SOUND` are core MSX1 BASIC statements, so they are in
scope under the faithful-full-MSX1-BASIC charter ([memory: charter]). MSX1 audio
is **PSG (AY-3-8910) only** — no MSX-MUSIC/FM/PCM (those are MSX2+ / cartridge
extensions, out of charter).

**One-line goal:** parse MML once in a page-1 tenant, drain the music queue live
in a page-1 tenant driven by a tiny resident H.TIMI hook, and write the PSG
directly — so a byte-full main ROM ([memory: basic-rom-space-and-growth]) spends
only a small resident hook + a few RAM cells on a large feature.

---

## 0. Provenance boundary (read first)

Everything in §2 is **contract-level, clean-provenance** fact: BIOS entry-point
register contracts, documented work-area addresses, published MML/`SOUND` syntax
(sources in Appendix A). We do **not** derive the internal queue-drain algorithm
by decoding the stock ROM's music player ([memory: no-reference-rom-disasm]).

The *behavior* of the live servicer (packet format, per-frame drain order,
duration accounting, `MUSICF` transition timing) is therefore an **own-design**
built to the documented contract and **verified empirically** on the openMSX
harness against a real machine (black-box), not lifted from ROM code. §3 marks
each such item `[BLACK-BOX]`. This matters because the recurring arc lesson is
that green builds hide interrupt/init-order bugs — the empirical boot-per-case
differential is load-bearing here ([memory: error-handling-arc]).

---

## 1. Current state (surveyed 2026-07-21)

- **No audio anywhere:** no `PLAY`/`SOUND` token in [`basic/kwtable.inc`](../basic/kwtable.inc),
  no handler, no PSG/`WRTPSG`/`GICINI` access, no queue, no audio doc.
- **The mechanism this rides already exists:**
  - The EI-capable page-0 `$0038` trampoline — [`basic/subromcall.asm:89`](../basic/subromcall.asm)
    (relevant only to §4's reentrancy discussion; the audio tenants are page-1).
  - The append-only sub-ROM tenant ABI — dispatcher [`subrom_call`](../basic/subromcall.asm),
    index tables [`sub/equates.inc:14`](../sub/equates.inc) + main mirror
    [`basic/sysvars.inc:3616`](../basic/sysvars.inc). Highest index today = **13**
    (`IDX_DIRVERB`). Audio takes **14+**.
  - Page-1 entry base `SUBROM_ENTRY_BASE_P1 = $4010`; page-1 tenants keep page 0
    (BIOS + real `$0038` ISR) resident — the property that makes an ISR-time
    CALSLT into them safe without the trampoline.

---

## 2. The real-MSX contract (clean-provenance)

### 2.1 `SOUND reg, value` — direct PSG write

- Syntax: `SOUND register, value`. **`register` 0–13**, `value` 0–255.
- **Register domain (empirically corrected 2026-07-21).** This draft originally
  said registers 14/15 are "silently masked". **The VG-8020 does NOT mask them —
  it raises Illegal function call (ERR 5).** Black-box capture (scratchpad/
  spike_sound_edges.py): `SOUND 14,0`→ERR5, `SOUND 15,0`→ERR5, `SOUND 16,0`→ERR5,
  `SOUND 255,0`→ERR5. So the writable register set is **0–13**; **14–255 →
  Illegal function call (ERR 5)**. (14/15 ARE the PSG I/O ports — joystick/
  cassette — hence rejected, not written.) Register/value coercion follows the
  D-F2-2 byte domain: `>int16` → Overflow (ERR 6); in-int16 but `>255` or negative
  → ERR 5.
- **Register 7 (mixer) top-bit mask (empirically confirmed).** The **top two bits
  of register 7** (the I/O-direction bits) are **not settable** — a faithful
  `SOUND 7,v` writes `R7' = (curR7 & $C0) | (v & $3F)`. Confirmed by reading the
  PSG back after the write: `SOUND 7,255`→R7=`$BF`, `SOUND 7,192`→R7=`$80` (value
  bits 6–7 dropped; BIOS I/O bits preserved). Registers 0–6, 8–13 store the whole
  value byte.
- No interrupt involvement — `SOUND` is a synchronous single register write.

### 2.2 `PLAY "mml"[,"mml"[,"mml"]]` — MML music, up to 3 PSG voices

- Up to three MML strings, one per PSG tone channel. String-var forms allowed
  (`PLAY A$,B$,C$`). A missing voice string = that channel unchanged.
- MML subset for PSG (published, MSX Wiki PLAY / MML refs):
  - `A`–`G` notes with optional `#`/`+`/`-` accidental and optional length digits;
    `N n` (note number, **1–96, one-based**); `R` rest; `O n` octave (1–8).
  - `L n` default length (1–64); `.` dotted; `T n` tempo (32–255); `V n` volume
    (0–15); `S n` envelope shape; `M n` envelope period.
  - **`&` tie, `>` and `<` octave shift: NOT MSX1 PLAY MML** — every one of the
    three raises Illegal function call on **both** references. `&` was measured in
    Slice 2a; `>` and `<` were measured 2026-09-15 (D-KWPLAY, three spellings each
    — `>C`, ` > C`, `O5<C` — on the VG-8020 **and** the CF-3300). This list drew all
    three from a broader MML reference that is not MSX1's, and zerobas **shipped**
    `>`/`<` until that measurement: an OVER-acceptance, removed to match.
  - **`N n` is ONE-BASED against the same period table the letter notes index from
    zero** — `N1` sounds C#1 and `N96` sounds C9, a semitone above the letter range
    `O1 C`…`O8 B`, so the table needs a 97th entry no letter note can reach.
    Measured on both references 2026-09-15; zerobas was a semitone flat for every
    `N n` until then.
  - `X var;` substring execution — **Q6 ANSWERED 2026-09-15: IN SCOPE.** Both
    references run `A$="O7L1C":PLAY"XA$;"` and sound O7 C (tone period 53), in all
    three spellings tried (`XA$;`, `X A$;`, a two-letter name). zerobas raises
    ERR 5: **not implemented**, and that is the one remaining MML gap.
- **Live/asynchronous semantics (the crux):** each string is parsed by the
  interpreter into a queue of data packets terminated by an end byte; the *drain*
  — dequeue packet, decode, set PSG — happens in the **timer-interrupt handler**,
  so `PLAY` returns immediately and music continues under the program. (Source:
  MSX2 Technical Handbook Ch.5 / work-area appendix.)

### 2.3 BIOS entry-point contracts (register-level, published)

| Entry | Addr | Contract |
|---|---|---|
| `GICINI` | `$0090` | Init PSG + the `PLAY` work area/static data. No in/out. |
| `WRTPSG` | `$0093` | Write PSG: `A`=reg, `E`=data. |
| `RDPSG`  | `$0096` | Read PSG: `A`=reg → `A`=data. |
| `CHGSND` | `$0135` | Key-click on/off (not music). |

PSG I/O ports: address-latch `$A0`, data-write `$A1`, data-read `$A2` — **slot-
independent**, so a tenant may `OUT` the PSG directly. (Source: MSX BIOS list,
map.grauw.nl.)

### 2.4 Reference work-area addresses (MSX2 TH work-area appendix)

Documented *reference* layout — zerobas is clean-room and owns its own RAM map,
so these inform **faithfulness** (programs that `PEEK`/`POKE` them), not a
mandate. See Q2.

| Addr | Name | Meaning |
|---|---|---|
| `FB3FH` | `MUSICF` | interrupt flag: which of the 3 queues are active |
| `FB40H` | `PLYCNT` | number of `PLAY` statements queued |
| `FB38H` | `VOICEN` | voice currently being interpreted |
| `FB3EH` | `QUEUEN` | PLAY internal |
| `FB41H` | `VCBA` | static data, voice 0 |
| `F959H` | `QUETAB` | queue table (4 queues: 3 PLAY + 1 RS-232), 6-byte blocks |
| `FD9AH` | `H.KEYI` | keyboard-interrupt hook (5-byte) |
| `FD9FH` | `H.TIMI` | **timer-interrupt hook (5-byte)** — our servicer entry point |

**Note on `H.TIMI` (corrected):** on a real MSX the queue-drain is *internal* to
the BIOS `$0038` ISR — the music player is **not** an `H.TIMI` extension (that
5-byte hook exists for *external* ROMs, e.g. the disk ROM). In zerobas the ISR
belongs to C-BIOS, not our ROM, so `H.TIMI` is our **seam into** that ISR — but
the servicer *code* is resident in our main-ROM page-0 window, so the seam is a
near `JP servicer`, **not** an inter-slot `CALSLT`. See §3.B.

---

## 3. Architecture — where each piece lives

Audio splits into **one-shot heavy** (a page-1 tenant) and **live light** (a
small resident routine):

```
  PLAY "…"  ──► [resident stub] marshal string ptr(s)
                     │
                     ▼   (page-1 tenant, one CALSLT, synchronous)
             IDX_PLAY_PARSE ── parse MML ─► fill voice queues in RAM ─► set MUSICF
                     │  returns immediately
   ── BASIC continues ──
        each VBLANK:  C-BIOS $0038 ISR ─► H.TIMI seam = JP play_service (near)
                             │  if MUSICF==0: ret            (common idle case)
                             │  else: save regs ▼ NO interslot call — resident
                     play_service ── drain queues 1 frame ─► OUT PSG ─► restore; ret
  SOUND r,v ──► [resident leaf] mask r/v ─► OUT PSG          (no interrupt, no tenant)
```

**A. `IDX_PLAY_PARSE` (page-1 sub-ROM tenant, index 14) — the only sub-ROM code.**
The big code chunk. Parses each MML voice string into its RAM packet queue and
sets `MUSICF`. Pure synchronous leaf like `IDX_FORMAT`/`IDX_FATPRIM` — one
`CALSLT`, RAM in / RAM out, returns. `[BLACK-BOX]` the packet encoding — with Q2
RAM-faithfulness we additionally aim to match the reference `QUETAB`-block layout
so a program that inspects the queue sees compatible bytes (probing scope, §3.1).

**B. `play_service` (RESIDENT, main-ROM page-0 window) — the "play live" part.**
One frame's work: for each active voice, decrement the running note's duration;
on expiry pull the next packet and program the PSG (tone period, amplitude/
envelope, that channel's mixer bit in R7); clear the voice's `MUSICF` bit at
end-of-queue. Reached from the ISR via the `H.TIMI` seam as a **near `JP`** — it
is always mapped (page 0 stays resident during page-1 tenant CALSLTs and after
the page-0 trampoline), so **no inter-slot call ever occurs in the ISR path**.
Must be **register-transparent** (save/restore everything it touches) and
**non-reentrant**. `[BLACK-BOX]` the exact per-frame drain order + duration
accounting — matched to a real machine on the harness. **Sizing is the load-
bearing assumption:** this must fit the page-0 window as a small routine.

**C. `H.TIMI` seam (RESIDENT, tiny).** Installed at boot next to
[`sub_int_install`](../basic/subromcall.asm) (from
[`initext.asm`](../basic/initext.asm)): point `H.TIMI` (`FD9FH`) at `JP
play_service`. `play_service` itself does the `MUSICF==0 → ret` fast-out, so the
seam is a bare jump. (If another `H.TIMI` client must chain, preserve the prior
hook — check whether C-BIOS/disk already own it.)

**D. `SOUND` (resident leaf). ✅ LANDED (Slice 1, 2026-07-21).** Coerce `reg` and
`value` (0–255) per the D-F2-2 byte-arg idiom ([memory: df2-2-intarg-coercion-arc]),
range-check `reg ≤ 13` (else ERR 5 per §2.1's empirical correction), preserve R7's
top 2 bits on a register-7 write, `OUT` the PSG directly (`$A0` latch / `$A1`
data). No tenant, no interrupt. Implementation: [`basic/sound.asm`](../basic/sound.asm)
(`ex_sound`); dispatched from [`interp.asm`](../basic/interp.asm); token `$C4`
([`sysvars.inc`](../basic/sysvars.inc), `SOUND_TOKEN`). Resident in **page 1** (the
disk/file eviction freed ~1.1 KB there; the reclaimed page-0 low region is full),
repack-only (whole body under `IF ROM_BASE < $4000`; lean ROM byte-identical). Cost
~72 B. Gate: `make sound-acceptance` (13/13 error surface + 7/7 PSG bytes, VG-8020
differential) + `tests/test_sound.py` (fast host layer, 10/10).

**E. `GICINI`-equivalent init. — DEFERRED to Slice 2.** Slice 1 needs no init of
ours: C-BIOS's own boot `GICINI` already leaves the PSG quiet (amplitudes 0), so a
fresh `SOUND` works, and there are no `PLAY` queues / `MUSICF` to zero yet. On cold
start / first `PLAY` (Slice 2): silence the three tone channels, zero the queues,
clear `MUSICF`. Small resident routine.

### 3.1 RAM faithfulness (Q2 = yes) — probing scope

Place the **program-visible** work-area variables at their documented addresses
(§2.4): `MUSICF FB3FH`, `PLYCNT FB40H`, `VOICEN FB38H`, `QUEUEN FB3EH`,
`VCBA FB41H`, and the `QUETAB F959H` queue table. Two depths:

- **Variable-level (required):** `MUSICF` bit semantics + address, `PLYCNT`,
  `VOICEN`, and the `QUETAB` block structure — so programs that `PEEK MUSICF` to
  detect "music finished" or drive the queue behave correctly.
- **Byte-exact packet encoding inside the queue buffers (stretch):** match the
  reference so a program that dumps the queue sees identical bytes. Needs black-
  box queue snapshots on the harness; scope it inside Slice 2's characterization,
  don't block Slice 1/core on it.

This trades more probing for compatibility, per the sign-off decision. It must not
collide with zerobas's existing [`sysvars.inc`](../basic/sysvars.inc) RAM map —
**audit `FB35H–FB41H`, `F959H+`, `FD9FH` for conflicts before Slice 1** and record
the reconciliation.

**RAM audit — reconciliation (done 2026-07-21, pre-Slice-1). NO CONFLICTS.**
Across the whole `$F800–$FBFF` range zerobas allocates exactly one cell, `EXBRSA`
`$FAF8` (`< $FB35`), and its own scratch lives in pages `$E0–$E3` (nowhere near
`F959`); it installs **no** `H.TIMI` hook (C-BIOS owns `$0038` and services
`H.TIMI` itself — see [`subromcall.asm`](../basic/subromcall.asm)). Therefore
`FB35–FB41` (PLAY work area), `F959+` (QUETAB), and `FD9F` (H.TIMI) are all free
for the reference-faithful layout, and the Slice-3 servicer seam. (Slice 1 uses
none of these — `SOUND` is a stateless direct write.)

### 3.2 Resident footprint (the budget to hold the line on)

Resident main-ROM cost: `PLAY`/`SOUND` tokens + dispatch stubs; **`play_service`
+ the `H.TIMI` seam** (the new resident item vs the v1 plan); the `SOUND` leaf;
the init routine; the RAM work-area cells. Only the MML **grammar** is sub-ROM.
**Target: keep net main-ROM growth (page-0 window + page-1) under a stated byte
budget (fill in at sign-off). If `play_service` overruns the page-0 window, fall
back to the page-1-tenant servicer of the v1 draft (re-accepting §4.3) — but the
resident form is strongly preferred.** `SOUND`-only Slice 1 lands regardless.

---

## 4. The hard parts (where this goes wrong if unspecified)

1. **Interrupt transparency.** The servicer runs inside the ISR; it must preserve
   every register and not disturb `JIFFY`/keyboard servicing (H.TIMI is called
   *after* the BIOS did its own work — confirm ordering `[BLACK-BOX]`).
2. **Non-reentrancy.** A slow frame must not re-enter the servicer. Guard: a
   "servicer busy" flag or rely on H.TIMI being non-reentrant by ISR DI. Specify.
3. **Reentrancy vs an in-progress page-1 tenant CALSLT — DISSOLVED by §3.B.**
   The earlier hazard was: run `PLAY` then evaluate `SIN(x)` (a page-1 math
   tenant); the CPU is *inside* a page-1 CALSLT when VBLANK fires. With the
   servicer as a page-1 *tenant* that would mean a nested same-slot CALSLT with
   shared-scratch corruption risk. Making `play_service` **resident page-0** code
   removes it: page 0 is mapped throughout a page-1 tenant call, so the ISR reaches
   the servicer by a plain near call — no nested CALSLT, no shared marshalling
   scratch. Residual (small): the servicer reads queues the parser wrote, so the
   parser must set `MUSICF` **last/atomically**, after the queues are committed,
   so a VBLANK mid-parse never drains a half-built queue. Still verify on the
   empirical differential — this is the class of bug it exists to catch.
4. **PSG mixer discipline.** Voices share PSG register 7 (mixer) and the volume
   registers; the servicer and `SOUND` must read-modify-write R7 per channel and
   never clobber the R7 I/O-direction bits or R14/15. Same masking contract as
   §2.1.

---

## 5. Decisions (resolved 2026-07-21) + the one open item

- **Q1 — Servicer placement: RESOLVED → resident main-ROM page-0** (`play_service`,
  §3.B). Not a tenant. Fallback to a page-1 tenant only if it overruns the window.
- **Q2 — RAM faithfulness: RESOLVED → yes** (§3.1). Documented addresses for the
  program-visible variables; byte-exact queue encoding a Slice-2 stretch. Accepts
  extra probing for compatibility.
- **Q3 — Risk staging: RESOLVED → confirmed.** Slice 1 = `SOUND` + PSG init +
  mixer masking (synchronous). Slice 2 = `IDX_PLAY_PARSE` (MML→queue, no live
  drain; validate statically). Slice 3 = `play_service` + `H.TIMI` seam (the
  interrupt part, gated by the empirical differential).
- **Q4 — PSG access: RESOLVED → direct `OUT $A0/$A1`** from both the tenant and
  resident code (slot-independent; no `WRTPSG` CALSLT).
- **Q5 — MML subset: RESOLVED → §2.2 PSG subset, MSX1 only**; MSX-MUSIC/FM/PCM
  explicitly out of charter.

### Q6 — `X` (substring execution): what it is, so you can decide

`X` is MML's "execute another string" command — MML's macro/subroutine call.
Syntax `X<string-var>;` (the `;` terminates the variable name). Mid-parse it
suspends the current string, fetches the *named BASIC string variable*, parses its
MML contents, then resumes. Example:

```basic
10 A$="O4 CDEG"
20 PLAY "T120 XA$; XA$; O5 C"      ' plays A$ twice, then a high C
```

It exists to factor out repeated phrases (choruses, riffs) without duplicating
MML text, and it **nests** (an `X`-invoked string may itself contain `X`).

**Cost:** it's the parser's hardest feature. It forces the MML parser to (a) look
up a BASIC string variable *by name* from inside the tenant (reach into the
variable table / VARPTR machinery — [memory: varptr-factyp-bug] territory), and
(b) maintain a **parse-resume stack** for nesting, with a depth cap and a
"string too complex"/overflow error to match. Everything else in §2.2 is a linear
single-pass scan; `X` is the one recursive, variable-coupled piece.

**Faithfulness view:** `X` **is** standard MSX `PLAY` MML, so under the faithful-
full-MSX1 charter ([memory: charter]) omitting it is a real gap, not a clean cut.

**Recommendation:** keep it **in scope**, but isolate it as **Slice 2b** — land
the linear grammar (notes/octave/length/tempo/volume/rest/tie/envelope) in Slice
2a first, add `X` + its resume-stack in 2b. That way the recursion/variable-lookup
risk is staged behind a working core, consistent with the risk-staging norm.
**RESOLVED (2026-07-21): in scope as Slice 2b.**

## 6. Gates (Definition of Done per slice)

- New `make audio-acceptance` corpus (openMSX, boot-per-case differential vs
  Philips VG-8020 [memory: probe-machine-philips]) — the load-bearing empirical
  pass, not just a green build. (Slice 1 ships this as `make sound-acceptance`;
  a `play-acceptance`/`audio-acceptance` umbrella follows with Slice 2/3.)
- Slice 1: ✅ **DONE (2026-07-21).** `make sound-acceptance` — VG-8020 differential,
  two halves: **13/13 error surface** (`reg` 0–13 domain; 14–255 → ERR 5; byte
  coercion ERR 5/6) + **7/7 PSG register bytes** (`SOUND reg,value` → read the
  openMSX "PSG regs" debuggable; register-7 top-2-bit I/O mask included). Fast
  host layer: [`tests/test_sound.py`](../tests/test_sound.py) (10/10, captures the
  OUT sequence + R7 read-modify-write). Token crunch byte-identity ($C4) added to
  `basic_probe_crunch.py`. **The empirical differential corrected the spec**: reg
  14/15 are ERR 5, not silently masked (§2.1).
- Slice 2: parsed queue bytes for representative MML match our own decoder's
  expectation (host unit-test); `PLAY` returns without hanging; `MUSICF`/`QUETAB`
  land at the §2.4 addresses (RAM-faithfulness variable-level check). Slice 2b
  adds nested `X` substring exec with a depth-cap overflow error (if in scope).
- Slice 3: differential — for a set of MML tunes, the **PSG register write trace
  over N frames** matches the reference machine within tolerance; `MUSICF` clears
  at end-of-queue; the `PLAY`-then-`SIN`-loop case (former §4.3 hazard) produces
  no corruption; a VBLANK landing mid-parse never drains a half-built queue
  (`MUSICF`-set-last ordering, §4.3 residual).
- Byte budget respected: report page-0-window bytes for `play_service` + seam and
  page-1 bytes for the parser tenant; state the funder if `PLAY` needs one. If
  `play_service` overruns the window, invoke the §3.2 page-1-tenant fallback.

---

## 7. `X<var>;` substring execution — the design (D-PLAYX, 2026-09-16)

⚠️ **PROVENANCE**: every behavioural statement below is this project's own
black-box measurement of a Philips VG-8020 (13 rows,
[`scratchpad/playx_probe.py`](../scratchpad/playx_probe.py)), each row carrying a
control written WITHOUT `X`. No disassembly; §0's boundary is unchanged.

### 7.1 What it does (measured, not assumed)

| | behaviour |
|---|---|
| resumption | **A CALL, NOT A JUMP** — the outer string continues after the substring |
| scope | **NONE** — `O7` set inside the substring is still in force outside it |
| nesting | **YES**, at least one level (`A$="XB$;"`); deeper is UNMEASURED |
| terminator | `;` is **MANDATORY** — without it, ERR 5 |
| undefined var | silently **EMPTY**, and the outer string continues |
| numeric var | **ERR 13** Type mismatch (not ERR 5) |
| case | insensitive (`x` works) |

🎯 **"NO SCOPE" IS THE LOAD-BEARING ONE.** It means the re-entry needs a SOURCE
CURSOR STACK and **no VCB state save/restore at all** — parse state is simply
shared. That is what makes this affordable.

### 7.2 Where it cannot live, and why the obvious shapes are all shut

The MML parser is `play_parse_tenant`, a **sub-ROM PAGE-1 tenant**
(`sub/playparse.asm`), and the resolve it needs — `var_find_typed $4853`,
`str_eval $49EE` — is **main page 1**. Three routes were considered and two are
measured shut:

* ❌ **Resolve in the tenant via an inter-slot call**, the way `disk.rom` now
  calls main page 1 (D-XSLOTPRICE, 7 B a site). Shut: `sub/deffn.asm`'s header
  records it MEASURED — no sub tenant in this tree calls main page 1, and there
  is no import mechanism (`sub/basic-resident-abi.inc` is generated for page-1
  tenants calling main's LOW region). The disk ROM's mechanism is the disk ROM's.
* ❌ **Flatten the string main-side before handing it over** — expand every
  `X<var>;` into a scratch buffer so the tenant never sees an `X`. Semantically
  exact (there is no scope), but it spends MAIN PAGE 1, the scarce region, on a
  scan-resolve-copy loop plus a buffer.
* ✅ **A SERVICER, on `sub/deffn.asm`'s precedent** — the one shape this tree has
  already built for exactly this problem.

### 7.3 The servicer protocol

⚠️ **A CALSLT IS NOT RESUMABLE** (`sub/deffn.asm`). The tenant is re-entered AT
ITS TOP once per bounce and recovers its phase from RAM plus the entry register;
**there are no locals**, because the Z80 stack belongs to the resident servicer
and anything pushed is gone by the next entry. DEF FN carries BOTH directions of
its protocol in one byte by giving the two directions DISJOINT ALPHABETS, and the
same trick applies here.

    tenant -> main   1  resolve the variable named in PLY_XNAME; give me (ptr,len)
    main   -> tenant  0  nothing asked yet (a fresh PLAY)
                     $81 resolved -- (ptr,len) are in PLY_XPTR/PLY_XLEN
                     $82 undefined -- treat as the EMPTY string (NOT an error)
                      13 raise Type mismatch (the name was numeric)

`$82` is a separate answer from `$81` with length 0 only because the two are
worth telling apart in the source; both resume the parse.

### 7.4 The state that must move to RAM

The parse today keeps its cursor in `MCLPTR` (RAM) but its **byte count in `B`**
and its **queue write pointer in `DE`** — registers, which a non-resumable
re-entry destroys. So:

| cell | width | why |
|---|---|---|
| `PLY_XLEFT` | 1 | the outer `B`, bytes remaining |
| `PLY_XPUT` | 2 | the outer `DE`, queue write pointer |
| `PLY_XNAME` | 2 | the variable name being resolved (name0, name1) |
| `PLY_XPTR` / `PLY_XLEN` | 3 | the servicer's answer |
| `PLY_XSTK` | 3 x d | the source-cursor stack: (ptr:2, left:1) per level |
| `PLY_XDEP` | 1 | current depth |

🔴 **RAM HAS NO GATE** — walk `scratchpad/rammap_sweep.py` and then ASK THE
MACHINE (`ramfree_probe.py`) before claiming any of these; a delta between two
names is not free space. `QUEBAK $F971-$F974` is already fully spent
(`PLY_LASTDUR`, `PLY_BUFEND`), so this needs its own home.

### 7.5 The three open questions — ANSWERED (D-PLAYX2, 2026-09-16)

[`scratchpad/playx2_probe.py`](../scratchpad/playx2_probe.py) (12 rows) and
[`scratchpad/playxdepth_probe.py`](../scratchpad/playxdepth_probe.py) (chains to
24). Controls `O7 C` = 53/0 and `O4 C` = 172/1 read identically on both machines,
and they are DIFFERENT from each other — which is what lets the inheritance row
below say anything at all.

**1. 🔴 NESTING HAS NO CEILING THIS TREE CAN FIND.** 2, 3, 4, 5, 6, 8, 10, 12,
16, 20 and **24** levels all sound the note on the VG-8020. Not "deep enough" —
*no limit observed*, which is the shape of a Z80-stack recursion rather than of a
table. **THIS IS THE ONE ANSWER THAT MOVES THE DESIGN** (see §7.6).

**2. ✅ THE SUBSTRING INHERITS THE OUTER STATE.** `A$="L1C"` with `PLAY"O7XA$;"`
sounds **O7** C (53/0); the same `A$` with `PLAY"XA$;"` sounds the default **O4**
C (172/1). Taken with D-PLAYX's measurement that state also LEAKS OUT, the rule
is: **one shared parse state, no scope in either direction** — which is what
licenses the design's "no VCB save/restore".

**3. The name and terminator corners.**

| | VG-8020 |
|---|---|
| `A$="O7L1C" : PLAY"XA;"` (no `$`) | **ERR 13** — a sigil-less name is NUMERIC and is a type fault even when `A$` exists |
| `PLAY"XZ$;"` (undefined, nothing after) | **silence, NO error** (0/0) |
| `A$="" : PLAY"XA$;O7L1C"` (empty substring) | the outer continues — 53/0 |

So the name rule is the ordinary MSX one: the type lives in the sigil, and `X`
requires a STRING. `ERR 13` is not about the VALUE being numeric, it is about the
NAME being a numeric name.

### 7.6 What the depth answer costs, and the shape it re-opens

§7.3's servicer keeps a **fixed source-cursor stack in RAM** — 3 B a level — and
the stack must be RAM rather than the Z80 stack precisely because a CALSLT is not
resumable and the tenant has no locals. With no observable ceiling on the
reference, **any depth N we pick is a divergence a probe can find**: N=8 is 24 B,
N=24 is 72 B, and neither is "the same as the reference".

⚖️ **THAT RE-PRICES THE FLATTENING SHAPE §7.2 DECLINED.** It was declined on cost
while the depth question was open; the answer changes the comparison, because
flattening has NO depth table at all — main expands every `X<var>;` in place and
the tenant never sees one. Its bound is the EXPANDED LENGTH, not the nesting
depth. Semantically it is still exact (there is no scope), so this is purely
about where the bytes go:

| | servicer + stack (§7.3) | flatten main-side |
|---|---|---|
| main page 1 (61 B free) | small: decode + one resolve | a scan-resolve-copy loop |
| sub page 1 (87 B free) | the `X` scan, the stack walk, the resume | nothing |
| RAM | 3 B x N, plus the outer `B`/`DE` | a flat buffer |
| divergence | a DEPTH limit the reference does not have | a LENGTH limit the reference does not have |

🔴 **AND WRITING THAT TABLE OUT SHOWS IT IS NOT A FORK.** The row that looked
decisive — "RAM: 3 B x N" against "a flat buffer" — is not a trade at all:
**flattening needs RAM TOO**, and a buffer big enough for an expansion is not
obviously smaller than 24 B. So it is not scarce-ROM-versus-RAM; flattening
spends the SCARCE region (main page 1) *and* RAM, to buy a divergence of a
different shape rather than no divergence. That is strictly worse, and the depth
answer did not rescue it.

✅ **DECIDED: THE SERVICER, WITH `N = 8`.** 24 B of RAM table. The reference
manages 24+ levels and any N is a divergence, so N is chosen to be far past
anything real MML does (measured nesting in the wild is 1–3) and the limit is
DOCUMENTED rather than hidden — the same way this tree records every other bound
it cannot match. What must NOT happen is a silent wrong answer: level N+1 raises,
it does not truncate.
⚠️ **THE DIVERGENCE IS FILED, NOT FORGOTTEN**: `X` nested deeper than 8 raises
where both references keep going. A row should pin it, so the day the cap moves
the row moves with it.

### 7.7 Where the RAM would come from — CANDIDATES, not a claim

🔴 **RAM HAS NO GATE** (`make wall-assertion-check` polices ROM only), and
`scratchpad/rammap_sweep.py`'s own caveat is that a delta is *"the cell at the low
address PLUS whatever follows"*, never free space. Its window is `[E000,F380)` and
does not even cover the PLAY work area. So, to be READ and then asked of the
machine, never assumed:

* **The VCB tail.** `VCB_STRIDE` is 37 and the highest offset this tree uses is
  `VCX_FRAMES` at 20 (2 B). Offsets 22..36 are unused HERE — but they are real
  MSX2-TH VCB fields, so this is space borrowed from a layout we have only
  partly implemented, and it must be recorded as such rather than treated as
  spare.
* ❌ **NOT a disk buffer.** `AUDIO_VMASK equ DISKOP_OP` is the standing precedent
  for audio/disk aliasing, but that is a transient PARAMETER cell. `SECTOR_BUF`
  and `BDOS_SEQREC` hold LIVE state for an open channel, and `PLAY` in a program
  with a file open is ordinary. The precedent does not extend to buffers.
* `QUEBAK $F971-$F974` is already fully spent (`PLY_LASTDUR`, `PLY_BUFEND`).

🔴 **AND THE MSX WORK AREA HAS NO CONTIGUOUS ROOM FOR IT — WALKED 2026-09-16,
`$FB00`–`$FD00`:**

| | |
|---|---|
| `VOICEN $FB38` → `MCLPTR $FB3C` | 4 B, of which 3 unnamed |
| `VCBA $FB41` / `VCBB $FB66` / `VCBC $FB8B` | stride 37, offsets 22..36 unused here — **15 B each, NOT contiguous** |
| `VCBC` end `$FBAF` → `LINTTB $FBB2` | **2 B** |

So a single 24 B table does not fit beside the PLAY block, and the VCB tails are
45 B in three separate 15 B pieces. 🎯 **ONE STACK IS ENOUGH, NOT THREE** — the
three voices are parsed SEQUENTIALLY (`pt_vloop`), so a voice's stack is empty
before the next one starts; per-voice storage would be paying three times for a
thing that is only ever used once at a time. That argues for a single block in
this tree's OWN RAM region rather than three VCB tails.
⚠️ **AND `rammap_sweep.py`'S WINDOW `[E000,F380)` DOES NOT COVER ANY OF THIS** —
the walk above is of `basic/sysvars.inc`'s `$FB00`+ names directly. A candidate
in the tree's own region still has to be READ (a delta is the cell at the low
address PLUS whatever follows) and then ASKED OF THE MACHINE.

### 7.8 Which MECHANISM the reference uses — partly answered (D-PLAYXREC)

[`scratchpad/playxrec_probe.py`](../scratchpad/playxrec_probe.py), VG-8020,
2026-09-16. ⚠️ **READ 7.8.1 BEFORE ANY ROW HERE**: this probe was wrong TWICE and
one row is still not scoreable.

| row | reading | |
|---|---|---|
| `c0` plain note | 53/0 | control — the rig works |
| `c1` one level of `X` | 53/0 | control — a terminating `X` |
| `c4` chain of **6**, top level | 53/0 | control — the subject of `c5`, unnested |
| `c2`/`c3` `A$="XA$;"` (self-reference) | **no output in 25 s** | see below |
| `c5` chain of 6, **80 `GOSUB`s deep** | **ERR 5** | 🔴 NOT SCOREABLE — its control is unreadable |
| `c9` the same 80 `GOSUB`s, no `X` | no reading | the control that would make `c5` mean something |

🟡 **SELF-REFERENCE PRODUCES NOTHING, REPEATEDLY — AND THAT IS NOT "IT HANGS".**
An empty capture is the window closing. It is consistent with an unguarded
infinite recursion and equally consistent with a very slow one; nothing here
distinguishes them, and the row is recorded as what it is.

🔴 **`c5` IS THE INTERESTING ONE AND IT CANNOT BE SCORED.** A chain that plays at
top level raising ERR 5 at 80 `GOSUB`s deep would be strong evidence that `X`'s
return points share the BASIC stack — but `c9`, the same nesting WITHOUT any `X`,
produced no reading, so the 80 `GOSUB`s themselves are not cleared of causing it.
**A subject that moves while its control is blind is not a measurement.**

🎯 **AND IT DOES NOT CHANGE THE DESIGN EITHER WAY.** §7.6 chose a fixed 8-entry
RAM table because **a CALSLT is not resumable and the tenant has no locals**, so
the Z80 stack is unavailable to us whatever the reference does. Confirming
recursion would only confirm that the depth divergence is unavoidable — which
§7.6 already says. This subsection exists so the question is not re-opened as
though it were load-bearing.

#### 7.8.1 The probe was wrong twice, in two different ways

1. **Hand-counted line numbers.** `ON ERROR GOTO` and `GOSUB` targets were
   derived by counting list positions, and the recursion body was skipped
   entirely. Both B rows read silence — subject AND control — which is the only
   reason it was caught. Targets are now RESOLVED from labels, and an unresolved
   `@name` refuses.
2. 🔴 **A LABEL THAT RESOLVED PERFECTLY WELL, POINTING AT THE WRONG LINE.** The
   settle loop was labelled on `T=TIME` rather than on the `IF`, so it jumped
   back and re-read its own start time every iteration and never exited. Every
   row that reached the settle hung; the ONE row that raised BEFORE reaching it
   was the only reading in that run — **a broken instrument still emitting
   something that looks like data.** The refusal in (1) cannot catch this: it
   checks that a label RESOLVES, not that it resolves to the right line.

## Appendix A — Sources (clean-provenance, contract-level)

- MSX Wiki, **PLAY** — https://www.msx.org/wiki/PLAY (MML syntax, per-voice strings).
- MSX Wiki, **SOUND** / **PSG Registers** — `SOUND` reg/value ranges + the 14/15
  and R7-top-bit masking; PSG register semantics.
- **MSX BIOS calls**, map.grauw.nl/resources/msxbios.php — `GICINI $0090`,
  `WRTPSG $0093`, `RDPSG $0096`, `CHGSND $0135` register contracts; PSG ports.
- **MSX2 Technical Handbook**, work-area appendix (konamiman.com/msx/msx2th) —
  work-area addresses `MUSICF FB3FH`, `PLYCNT FB40H`, `VOICEN FB38H`,
  `QUETAB F959H`, `H.KEYI FD9AH`, `H.TIMI FD9FH`; the "interpreter fills queues,
  timer-interrupt drains them" division of labor.
- MSX Wiki, **System variables and work area** — queue-table description.

> Provenance note: the above are **published contracts + documented addresses**.
> The internal music-player *algorithm* (packet format, drain order, duration
> accounting) is **own-design, verified black-box** on our harness — never lifted
> from stock-ROM code ([memory: no-reference-rom-disasm], [memory: clean-room-audit-checks]).
