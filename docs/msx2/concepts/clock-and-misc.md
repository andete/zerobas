<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# The clock, the settings memory and the other sub-ROM calls — shared facts

> **Spec:** DRAFT 0 (2026-11-23), from the published interface; the clock facts the call pages measured ([REDCLK](../sub/REDCLK.md), [WRTCLK](../sub/WRTCLK.md): [xclk.asm](../../../probes/bios/spec/xclk.asm), [scratchpad/AE_xclk_msx2.out](../../../scratchpad/AE_xclk_msx2.out)) are cited here where they bear on a shared fact, as [M xclk]. References: HB-F900, NMS 8250, FS-A1WSX.
>
> Goldfish pass 1 (test writer) 2026-11-23: 2 findings, 1 measured, 0 moved to open.

The concept page for the sub-ROM calls outside the screen, graphics and VRAM regions:
[REDCLK](../sub/REDCLK.md) and [WRTCLK](../sub/WRTCLK.md) (the clock IC),
[BEEP](../sub/BEEP.md) (whose sound is a setting kept in the clock IC),
[NEWPAD](../sub/NEWPAD.md) (mouse, track ball, light pen) and [KNJPRT](../sub/KNJPRT.md) (a kanji on
a bitmap screen). It holds the facts several of them share. Each call's own state, differences and
open items live on its page ([spec method](../../spec-method.md) §1), never here. The full list of
entries is the [inventory](../index.md).

## References, subject, citation tags

- **References** (to be measured): Sony HB-F900 (openMSX `msx2`), Philips NMS 8250 (`msx2_eu`),
  Panasonic FS-A1WSX (`msx2plus`). **Subject:** C-BIOS's MSX2 / MSX2+ builds.
- Tags: **[P A1]** the MSX2 Technical Handbook (Konamiman's English translation) Appendix 1, the
  sub-ROM listing; **[P A1 main]** its main-ROM listing; **[P 2]** Chapter 2's BASIC statement table; **[P 2§2.10]** Chapter 2 §2.10, the SET
  statements; **[P 5§5.4]** Chapter 5 §5.4 and Table 5.5 (GTPAD); **[P 5§6.n]** Chapter 5 §6.n, the clock
  IC; **[P A4]** Appendix 4, the work area; **[P A6]** Appendix 6, the I/O map; **[P MAP]** the MSX
  Assembly Page's compiled sub-ROM list (C / scoped in [allowed-sources.md](../../allowed-sources.md):
  corroborate against the handbook, never alone for a rule); **[A]** assumed.
- Clean room: the RTC, PSG, VDP and work area are READ on the references (ports $B4 / $B5 included);
  a reference ROM's bytes never are.

## The clock IC (RP-5C01)

- The clock IC is an RP-5C01 on I/O ports **$B4** (address latch) and **$B5** (data) [P A6]. Bit 7 of
  the write-only system-control port $F5 enables it [P A6]; whether any reference lets software see
  that bit is [A].
- It holds four **blocks** of 13 four-bit registers (addresses 0-12) and three control registers at
  13-15 that every block shares [P 5§6.2]: **#13 MODE** (read / write), **#14 TEST** and **#15 RESET**
  (write only) [P 5§6.2].
- **MODE (#13):** bits 1-0 select the block (0-3); bit 2 alarm output on; bit 3 the clock counts when 1,
  stops counting seconds when 0 [P 5§6.3]. The standard MSX2 does not use the alarm [P 5§6.3].
- **TEST (#14):** each bit feeds a fast pulse into the day / hour / minute / second counter [P 5§6.4].
- **RESET (#15):** bit 0 resets the alarm registers; bit 1 resets the stage below the seconds; bits 2-3
  control the 16 Hz / 1 Hz pulse outputs, which the MSX2 does not use [P 5§6.5]. The handbook's text and
  its figure disagree on the polarity of bit 2 (one says "1" turns it on, the other "0") [P 5§6.5].
- Bits the handbook marks "." always read 0 and cannot be changed [P 5§6.6].

### Block 0 — the clock; block 1 — the alarm

- Block 0 holds BCD digit pairs, low digit first: seconds (0-1), minutes (2-3), hours (4-5), day of the
  week (6), day (7-8), month (9-10), year (11-12) [P 5§6.6]. Writing a register sets the time; reading
  it gives the current time [P 5§6.6].
- The year is two digits; MSX-BASIC's GET DATE shows it plus an offset of 80 (year registers 0, 0 read
  as "80") [P 5§6.6]. The day of the week is a mod-7 counter whose mapping to real days is undefined
  [P 5§6.6].
- In 12-hour mode, bit 1 of block 0's register 5 is the afternoon flag [P 5§6.6].
- Block 1 holds the alarm (minutes, hours, day of the week, day) [P 5§6.6], plus two settings:
  register 10 bit 0 chooses the 24-hour clock (1) or the 12-hour clock (0); register 11 is a mod-4
  year counter, a leap year when its two bits are 00 [P 5§6.6].

### Block 2 — the BASIC settings

| reg | content [P 5§6.7] |
|---|---|
| 0 | ID: what block 3 holds (below) |
| 1, 2 | display adjust X, Y (-8 to +7) |
| 3 | bit 0 screen mode, bit 1 interlace mode |
| 4, 5 | WIDTH, low then high nibble |
| 6, 7, 8 | foreground, background, border colour |
| 9 | bit 0 function-key display on/off, bit 1 key click, bit 2 printer mode, bit 3 cassette speed |
| 10 | bits 3-2 BEEP tone, bits 1-0 BEEP volume |
| 11 | bits 1-0 title colour |
| 12 | native (country) code |

- `SET ADJUST`, `SET BEEP`, `SET SCREEN` and `SET TITLE`'s colour store here; the system applies them
  at power-on and reset [P 2§2.10]. `SET BEEP` takes a timbre and a volume of 1-4; timbre 1 is the
  MSX1's high beep, 2 a low beep, 3 a two-tone and 4 a three-tone beep [P 2§2.10].
- Which 2-bit code each of the 1-4 values is stored as, whether the 1-bit screen-mode field means
  SCREEN 0 / 1, and whether the unused bits 3-2 of registers 3 and 11 keep what is written, are [A].
- The handbook gives SET ADJUST's range as -7 to 8 [P 2§2.10] and the register's as -8 to +7
  [P 5§6.7]; which one the references accept is [A].

### Block 3 — title, password or prompt

- Block 2's ID chooses what block 3 holds; register 0 of block 3 repeats it [P 5§6.7]. On the references as
  openMSX starts them with empty persistent state (the probe's `--fresh`), block 2's register 0 reads **$A** and
  block 3's register 0 reads 0, on all three [M xclk] — neither an ID the handbook lists (0-2) nor repeated in block 3. Whether
  a reference's boot code reads the ID, and what it does with $A, is CK-1 / CK-2's question:
  - **ID 0, title:** registers 1-12 hold six characters, two nibbles each, low nibble first [P 5§6.7];
  - **ID 1, password:** usage IDs (1-3), a compressed password (4-7), a key-cartridge flag (8) and
    value (9-12) [P 5§6.7];
  - **ID 2, prompt:** six characters, as for the title [P 5§6.7].
- `SET TITLE`, `SET PROMPT` and `SET PASSWORD` share this block: only the last one holds [P 2§2.10].
  A six-character title makes the start-up screen wait for a key [P 2§2.10].
- The handbook's example program writes the prompt with WRTCLK, low nibble of each character first
  (its comments call the nibbles the other way round) [P 5§6.8, List 5.10].

### How the calls address it

- REDCLK / WRTCLK take the address in C as `00MMAAAA`: MM the block, AAAA the register; the caller
  does not set the MODE register itself [P 5§6.8, A1]. What the calls leave in MODE afterwards is the
  central open question of both pages.
- The handbook's Chapter 5 heads REDCLK with address $015F (EXTROM's); Appendix 1 gives $01F5 [P A1,
  5§6.8]. $01F5 is the entry: through EXTROM it returned the named register on every read [M xclk].
- Both calls select the block themselves and leave MODE's bank at MM, TE / AE kept; the details, and the subject's
  fault, are on their pages.

### MSX2+

- No public source consulted describes a change to the clock IC's use on the MSX2+; whether the
  FS-A1WSX stores anything else in blocks 2 / 3 (e.g. for SCREEN 10-12) is [A].

## Other devices the calls in this region reach

- **Light pen:** ports $B8-$BB (Sanyo specification) [P A6]; enabled by bit 6 of $F5 [P A6].
- **Mouse / track ball:** on the joystick ports (PSG), told apart automatically [P 5§5.4 note 2].
- **Kanji ROM:** ports $D8 (low address) and $D9 (high address / data) [P A6]; enabled by bit 0 of
  $F5 [P A6]. Ports $DA / $DB are reserved "for future kanji expansion" [P A6]; that the JIS level-2
  ROM sits there on the references is [A]. Which reference has which kanji ROM is [A] and is recorded
  per machine before KNJPRT's matrix is read.
- Cells several of the calls are assumed to use: FORCLR ($F3E9), ATRBYT ($F3F2), LOGOPR ($FB02),
  GRPACX ($FCB7), GRPACY ($FCB9) [P A4] — which call reads which is [A] on each page.
- The main ROM's BEEP ($00C0) and GTPAD ($00DB) may reach this region on the MSX2: BEEP "always calls the
  sub-ROM" [P A1 main]; GTPAD handing its numbers 8 and up to NEWPAD is given only by [P MAP] — both
  are [A] until measured, and the pages require only equal results, not a hand-over.

## Shared measurement fixtures (for the call pages' matrices)

- **Apparatus.** Probes run under openMSX, on the references and on the subject (C-BIOS's MSX2 /
  MSX2+ configs, `tools/install_cbios_msx2.py`). They may read the RTC, PSG and VDP registers through
  the emulator's debugger as well as through the ports (allowed; ROM bytes are not). Time is measured
  as emulated time (CPU cycles), not frames, so the NMS 8250's 50 Hz and the others' 60 Hz do not
  enter a duration. What openMSX does not model is named on the page that would need it (the RTC's
  TEST register, the light pen); a row that needs it pins nothing there.
- **RTC preset.** All 52 registers cannot hold distinct values: there are 16 nibble values, many
  fields are 1-3 bits wide, and "." bits read 0 [P 5§6.6]. The preset is therefore stated PER
  ADDRESS: for the case's address A, the named block's register A differs from register A of the
  block MODE selects, and from registers A-1 and A+1 of the named block. Where the fields leave no
  room, the case says so. Addresses whose widths constrain this: block 1's 0, 1, 9 and 12 have no bits (always 0), so a
  read of them separates blocks only against a block-2 / 3 register preset non-zero; block 0's and
  block 1's 10 (1 bit), and block 0's 5, 8 and block 1's 5, 8, 11 (2 bits), separate only against a
  register with a set bit outside that width. The matrices therefore point MODE at block 2 or 3
  (full 4-bit registers) for cases naming blocks 0 / 1, and at block 0 for cases naming blocks 2 / 3,
  preset so the two registers differ in the low bits.
  MODE's bank bits name a block other than the case's, TE / AE are a chosen pair. Everything is read
  back after the call, through the ports and the debugger. Block 0 cases stop the clock (TE = 0) so
  the seconds cannot roll over [A: that TE = 0 freezes all digits the call can read].
  The xclk run used a cheaper form of this preset: blocks 2 / 3 := the complement of blocks 0 / 1 by address,
  MODE's bank := the case's block XOR 2, TE / AE := each pair by register (so block 0 was read with TE = 0 on
  half its registers only), and no register frame; the call pages say which of their rules rest on it.
- **Register frame:** A, F, B, C, D, E, H, L, IX, IY, the alternate set set to distinct values (A's
  high nibble never 0, $F or equal to C's); all recorded after the call, with SP and the interrupt
  state, on entry with DI and with EI.
- **Call paths:** every case runs through EXTROM ($015F) and through SUBROM ($015C) — the two must
  give equal results; where a main-ROM entry may reach the call (BEEP $00C0, GTPAD $00DB) it is run too
  and must give equal results. Equal results do not show a hand-over, and no page claims one.
- **Machines:** every case runs on all three references; the FS-A1WSX row is not a single spot check.

## Open (not measured) — this page's own [A]s

| item | case that settles it |
|---|---|
| whether software can see $F5 bit 7 (it is write-only [P A6]) | not planned: no call's rule depends on it |
| the block 2 / 3 encodings of SET SCREEN, SET ADJUST, SET BEEP, SET TITLE (text and colour), SET PROMPT, SET PASSWORD; block 3's nibble order; the 1-bit screen field; the ADJUST range (-7..8 or -8..+7) | **CK-1**: on each reference, run each SET with boundary arguments (ADJUST -8, -7, 7, 8; BEEP 1-4 × 1-4; SCREEN 0 / 1 with WIDTH 1, 32, 40, 80, colours 0 / 15; TITLE / PROMPT of 0, 1, 6, 7 characters incl. codes $00, $7F, $FF; PASSWORD of 1 and 255 characters), dump all four blocks and MODE through the debugger after each |
| what the references show at reset for each CK-1 dump (cells FORCLR / BAKCLR / BDRCLR, LINL40 / LINLEN, CLIKSW, VDP R18 for ADJUST, the prompt) | **CK-2**: reset after each CK-1 row and record those cells and VDP registers — this pins the boot code's reading of the blocks, which WRTCLK's page does not |
| MSX2+ use of blocks 2 / 3 (e.g. SCREEN 10-12) | CK-1 / CK-2 on the FS-A1WSX with SET SCREEN in SCREEN 10-12 |
| RESET bit 2 / 3 polarity (text vs figure [P 5§6.5]) | not needed: the MSX2 does not use the pulse outputs [P 5§6.5], so nothing observable depends on it |

## Related pages

[the inventory](../index.md); the main-ROM entries' concept page ([main/README.md](../main/README.md));
the MSX1 pages [BEEP ($00C0)](../../bios/BEEP.md) and [GTPAD ($00DB)](../../bios/GTPAD.md); the sound
concept page [sound-calls.md](../../concepts/sound-calls.md).
