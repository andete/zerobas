- [ ] 🔴 **THE PROGRAM LADDER: WHOLE 1980s-STYLE BASIC PROGRAMS AS INTEGRATION
      TESTS (D-PROGLADDER, Joost's idea 2026-10-28).**
      🎚️ TIER 1 — it finds what a real user hits first, so its findings are
      ranked by the tier they land in, not by this item's tier.
      🤖 **AUTONOMOUS** — write the programs, run them, file what diverges.
      📏 **Why.** Joost: progress on the filed items had slowed, and most of them
      are tier-6 edges or apparatus. Programs of the kind people actually typed in
      exercise the INTERACTIONS (string space under load, nested FOR/GOSUB, PRINT
      USING, files, sprites, music, traps) that one-keyword rows never combine.
      🧰 **Apparatus:** [`run_programs.py`](probes/programs/run_programs.py), gate
      `programs-acceptance`. Each `probes/programs/L<n>_*.bas` is ORIGINAL code
      (never a typed-in listing). It goes on an ASCII tape that autorun loads
      (each machine tokenises it itself), with the `REM @ANSWERS` keys typed once
      it runs. The program LPRINTs numbered checkpoints into openMSX's printer
      logger, which never scroll away; the final screen is compared too (the
      `ZB` prompt reads as `Ok`). The emulated-time ratio is printed beside each
      zerobas row.
      📈 **Ladder:** L1 (guessing, loan with PRINT USING, dice/RND histogram) ·
      L2 (address book with a string sort and search; text adventure with a word
      parser) · L3 (grid spreadsheet; string-GC-heavy report) · L4 (sprite game
      with ON SPRITE / ON INTERVAL / STRIG / PLAY, input made deterministic) ·
      L5 (random-access database with FIELD / GET / PUT, ON ERROR) — disk rungs
      need the NMS 1200 reference.
      ✅ **L1 (2026-10-28): 3 programs, SAME on both zerobas targets**
      ([`progladder_l1.out`](scratchpad/progladder_l1.out)). Time ratios: guess
      x1.02, loan x1.17, **dice x2.13** — 1200 `RND(1)` + array updates; a TIER 5
      reading, filed here only (speed is paused for ROM space).
      🔧 **D-PLANDATA, FIXED 2026-10-29: the gate planner did not see a program.**
      The commit adding L3_editor / L2_hexmon planned ZERO emulator suites
      (tools/pick_gates.py follows Python imports; run_programs.py GLOBS
      `L*.bas`, and `probes/programs` was not even a module dir, so
      gcdi-acceptance's `import run_programs` did not resolve either). Now a
      changed `probes/programs/*.bas` plans every suite whose own script is the
      runner, and a `.bas` a closure names by path (catcopy's) plans that suite;
      `.bas` only, so kwsweep-rig-carry.json does not drag the sweep into every
      plan. Selftest P16 / P16b / P16c; replayed on the real suite set: the two
      programs -> programs-acceptance, a runner edit -> programs + gcdi + catcopy,
      catcopy's data -> catcopy. (Those two programs were run by hand before that
      commit: [`progladder_l7.out`](scratchpad/progladder_l7.out).)
      ✅ **L3_ledger (2026-10-29): SAME** (string DEF FNs for dates, a stable sort,
      PRINT USING `$$` / `**` / `+` / `,` / trailing `-` / `%` overflow, STR$ / VAL
      round trips), apart from `**$`, which it FOUND: D-PUSTARDOL
      ([`progladder_l9.out`](scratchpad/progladder_l9.out)).
      ✅ **L3_wrap + L4_matrix (2026-11-05): SAME after two fixes they FOUND** -- a text
      formatter (MID$= title case, INSTR from a start, wrap and justify, word counts with
      SWAP sorting, HEX$ / OCT$ / BIN$) found D-CONCAT3 (TIER 3), and a double-precision
      Gauss-Jordan solver (ERASE / re-DIM, SWAP rows, CINT / FIX / INT of negatives) found
      D-DBLNORM (TIER 1, a wrong comparison). Values print rounded where the 14th digit of a
      division differs by ruling (numbers.md). Before / after:
      [`progladder_l10.out`](scratchpad/progladder_l10.out).
      ✅ **L4_screen3 + L3_gcload (2026-11-05): SAME** -- SCREEN 3 blocks and SCREEN 2 LINE /
      CIRCLE (ellipse, arc) / PAINT / DRAW with X and =var; substrings, checksummed through
      POINT and VPEEK over both screens; a 100-string word list rewritten under CLEAR 1200
      until the string space gives, FRE("") after each round, ERASE
      ([`progladder_l15.out`](scratchpad/progladder_l15.out),
      [`progladder_l15b.out`](scratchpad/progladder_l15b.out) -- the first run stopped on a
      DRAW error of mine on both machines).
      ✅ **L5_files (2026-11-05, `@DISK`): SAME against the CF-3300** -- two files open at once,
      LOC / LOF on sequential files, LINE INPUT# in an EOF loop, INPUT$(n,#), NAME, KILL,
      FILES, and the file errors trapped (53, 54, 52, 61 and friends); it FOUND D-INPLF (TIER 6),
      and reads 11 bytes now so its INPUT$ does not split a CR LF pair
      ([`progladder_l14.out`](scratchpad/progladder_l14.out)).
      ✅ **L3_hanoi + L4_sieve (2026-11-05): SAME, first run** -- recursion on GOSUB with a
      hand-made frame stack, DEF FN, MID$= board drawing; a 2000-entry integer sieve,
      AND / OR / XOR / NOT, \ and MOD of negatives, &H / &O / &B, HEX$ / BIN$ / OCT$, trapped
      int16 overflow, CINT / FIX / INT at .5 ([`progladder_l13.out`](scratchpad/progladder_l13.out)).
      ✅ **L2_parts + L3_quiz (2026-11-05): SAME after D-PUSTYPE + D-RESNEXTEOL (which
      L2_parts found through a mis-typed `\\` field of mine) and D-LADFAST (which L3_quiz found)**
      -- parallel record arrays with `!` / `%`, insertion sort, PRINT USING string columns,
      delete-and-compact; typed answers into LINE INPUT / INPUT, RESTORE to a line, a
      trim-and-upcase subroutine ([`progladder_l12.out`](scratchpad/progladder_l12.out),
      [`progladder_l12b.out`](scratchpad/progladder_l12b.out)).
      ✅ **L4_rpn + L2_bank (2026-11-05): SAME, first run** -- an RPN calculator (tokenizer
      with INSTR / MID$ / VAL, an array stack, ON GOTO, trapped Division by zero / Overflow
      with RESUME to a line) and a single-precision savings ledger (`!` / `%` suffixes, INT
      cent rounding, PRINT USING with commas, CINT / FIX / INT / STR$)
      ([`progladder_l11.out`](scratchpad/progladder_l11.out)).
      ✅ **L5_chain (2026-11-01, `@DISK`): SAME in printer and screen** -- a program that
      writes three more as text files (PRINT # with CHR$(34) quoting), then `RUN "P2.BAS"`
      (variables cleared: `A` reads 0 in part two), DEFINT / `\` in the loaded part, a
      second `RUN "file"`, and `MERGE` -- which ENDS a running program on both machines.
      Its first draft found that `LLIST` (like LIST) ends a running program on both, so it
      ran 3 printer lines and stopped; restructured with the stopping statements last
      ([`progladder_chain.out`](scratchpad/progladder_chain.out)). Gaps: D-ASAVEDI's class.
      ✅ **L5_house (2026-11-01, `@DISK`): SAME in printer and screen** -- doubles in a
      random file through MKD$ / CVD (exact round trip), COPY, LFILES (whole and `*.DAT`),
      NAME, KILL, DSKF before / after, a tokenised SAVE that carries on and is read back
      (first byte 255, LOF 1207 on both), a trapped KILL of a missing file, FILES with
      none left (ERR 53 on both), and a closing `SAVE ...,A` -- which ENDS a running
      program on both machines (a tokenised SAVE does not). Its gaps found D-ASAVEDI
      (above, KNOWN_GAPS). 🔧 **D-LADSETTLE (apparatus)**: the runner captured the screen
      0.5 s after CURLIN returned to direct mode; after `SAVE ...,A` the CF-3300 prints
      `Ok` ~4.5 s later, so a BASIC-identical run read as a screen divergence
      ([`progladder_house.out`](scratchpad/progladder_house.out)). It now captures once
      the last non-blank row of the 24 is the prompt (`Ok` / `ZB`, character 255 -- the
      cursor -- ignored), at most 15 s on. Three wrong settles first: "two identical
      reads" (the screen is as still during a disk write), the cursor's row read as the
      last row, and width 32 scanning past the name table. All 40 programs re-run with
      it: only L5_house's gaps differ
      ([`ladsettle_programs.out`](scratchpad/ladsettle_programs.out)).
      ✅ **L4_marks (2026-11-01): SAME after two fixes it FOUND** -- DEFSTR (a string DEF FN
      typed by its letter), LET, ERASE + re-DIM + the Redimensioned trap, LPRINT TAB / LPOS
      columns, MID$= / INSTR, a SCREEN 2 chart rubbed out with PRESET and read with POINT,
      `VDP(7)=POINT(..)`, TRON across three lines, STOP. Picked by the keywords NO ladder
      program used (38 of 159 on 2026-11-01). Found D-LPRTAB and D-BRKFRESH
      ([`progladder_marks.out`](scratchpad/progladder_marks.out) ->
      [`progladder_marks3.out`](scratchpad/progladder_marks3.out)).
      ✅ **C8_floats (2026-10-31)**: the float paths D-REREAD batch 7 rewrote, in a
      program -- a 4x4 Gauss-Jordan solve with partial pivoting and its determinant,
      `^` with integer / negative / fractional exponents and negative bases, `/` in
      each precision, SQR, INT / FIX / CINT at the halves, PRINT USING (`##.###`,
      `+`, `^^^^`, `,`, `$$`, `**`, trailing `-`, `&`), divide-by-zero / overflow /
      `(-8)^(1/3)` under ON ERROR, single vs double drift over 1000 adds. First run:
      3 lines differed ONLY in the 14th digit (the determinant -165.99999999999 there,
      -166 here; `16^.25` 1.9999999999998 there, 2 here; `SQR(2)`) -- the classes ruled
      2026-07-13 (correct rounding; D-POWNEG measured them). Those values now print
      through `DEF FNR` to 8 places, as L1_loan rounds to cents; then SAME
      ([`progladder_c8.out`](scratchpad/progladder_c8.out)). TIER 5 reading only:
      72 s against 47 on the VG-8020.
      ✅ **C7_bits (2026-10-31)**: contest-style bit tricks on DEFINT integers --
      popcount by `n AND n-1`, a running XOR, Gray codes through `BIN$`, subsets by
      a bit mask, a prime sieve packed 16 to an integer (bit 15 is the sign:
      `&H8000`), `&H` / `&B` / `&O` literals and `VAL("&H..")`, `HEX$` / `OCT$` /
      `BIN$` of negatives, AND / OR / XOR / NOT / EQV / IMP on negatives, `\` and
      MOD with negative operands, an XOR swap, `n AND -n`. SAME (every answer
      checked by hand). TIER 5 reading only: 80 s against 49 on the VG-8020.
      ✅ **L4_music (2026-10-31)**: a jukebox -- PLAY in one and three voices with
      lengths, dots, rests, `X` substrings and `N` notes, tempo / length / volume
      from variables, an envelope, PLAY(n) while three voices run, an ON INTERVAL
      clock during a tune, a SOUND drum timed by TIME, and a song table played
      bar by bar from DATA, each tune timed against the VG-8020's length. It FOUND
      D-PLAYQUEUE (the bars replaced each other) and D-PLAYRATE (short notes),
      and showed `<` / `>` are ERR 5 on both machines. SAME after D-PLAYQUEUE.
      ✅ **L2_keys (2026-10-30)**: function keys the way a menu program sets them --
      `KEY n,"..."` with CHR$(13), an empty key, a 16-character one cut to 15, the
      row read back by VPEEK with KEY ON and OFF, KEY LIST, an INKEY$ menu loop,
      INPUT$(3) and `INKEY$=""` in a PRINT. It FOUND D-PRSTR2X and D-KEYREPAINT;
      SAME after them.
      ✅ **L3_forms (2026-10-30)**: a data-entry screen drawn with control codes only --
      ESC Y positioning, TAB, cursor left / right / up / down, backspace, home,
      ESC K / ESC J erase, ESC L / ESC M insert and delete line -- then the screen
      VPEEKed back with POS / CSRLIN: SAME. (Predicted a CHPUT divergence: MISS --
      the repack's terminal codes already match.)
      ✅ **L5_journal (2026-10-30, @DISK)**: sequential files the way a diary program
      used them -- OUTPUT / APPEND / INPUT, PRINT# with quoted fields, INPUT# and
      LINE INPUT# with EOF loops, two files open at once, LOF / LOC, NAME, KILL,
      BSAVE / BLOAD with an offset, and the careless program's errors (53 missing,
      54 already open, 59 not open, `WRITE #` Syntax error -- MSX1 has no WRITE):
      SAME as the CF-3300, at about the same speed (56 s against 50).
      ✅ **C6_wordsort (2026-10-30)**: Project Euler 22 and 42 on the first 120 names /
      150 words of their published lists (said in the program): a Shell sort of
      120 strings, letter values by ASC, a score past 32767 in a double, triangle
      tests -- string compare and heap churn under CLEAR 3000. Both answers match
      Python on the same subsets; SAME.
      ✅ **G4_sokoban (2026-10-30)**: a Sokoban level as strings, a 35-move script
      decoded by INSTR and dispatched by `ON K GOSUB`, blocked moves, pushes, a box
      leaving its goal, VPOKEd tiles from custom characters, a VRAM-checksum per
      move, crunched style: all five checkpoints match a Python model of the same
      rules; SAME.
      ✅ **C5_strings (2026-10-30)**: string algorithms contest-style -- KMP with
      its failure table, edit distance and LCS (with the walk back) on 2-D integer
      arrays, run-length encoding, ROT13 by ASC / CHR$ and a hash with XOR, anagram
      groups by sorting characters in place with `MID$(...)=`: all six answers
      match Python; SAME. (My hash first overflowed an integer -- Overflow on all
      three.)
      ✅ **C4_euler (2026-10-30)**: Project Euler 16 (2^100), 25 (50 digits), 48
      (1..100, five digits), 92 (below 1000), 39 (p <= 120), all scaled and said
      so: base-10000 limbs, a Fibonacci pair of limb arrays, modular powers in
      doubles, a memoised chain in an integer array, Euclid's formula for the
      triangles. All five match; SAME. Two of my drafts failed the same way on
      all three machines: 2400 SQRs took 5 minutes on the VG-8020 (P39 now uses
      Euclid's formula), and a FOR whose start was already past its end ran its
      body once, as MSX BASIC does, and indexed past the array.
      ✅ **G3_life (2026-10-30)**: Conway's Life on a 16x12 board in SCREEN 3
      (multicolour: PSET blocks, a LINE frame, POINT read back for a checksum),
      rows as strings with `MID$(...)=` and `MID$` neighbour counts, crunched
      style: all eight populations match a Python simulation, SAME. (My first
      draft numbered an inner-loop line 51 meaning "5 1/2"; BASIC sorts it after
      6 and 7 -- the same wrong run on all three machines.)
      ✅ **G2_runner (2026-10-30)**: a side-scrolling runner in crunched style --
      MID$ windows of a DATA map, a scripted jump table, VPEEK collisions, `VDP(7)`
      border flashes written and read back, PLAY with `X`, a VRAM checksum. It
      FOUND D-POSTTY (the prompt row after SCREEN 0); SAME after it.
      ✅ **C3_euler (2026-10-30)**: Project Euler 3, 17, 24, 40, 63 at full size, 76 for
      60, 21 below 1000, 36 below 500 (said in the program) -- trial division of a
      12-digit double up to its root, number words by string building, the
      factorial number system, Champernowne digits by arithmetic, LOG digit
      counts, a partition DP, an integer-array divisor sieve, STR$ / BIN$
      palindromes. All answers match the independent ones; SAME. The first draft
      took 552 s on the VG-8020 and timed out here; it was cut by MEASURING each
      section first ([`c3_section_times.out`](scratchpad/c3_section_times.out)).
      📏 **TIER 5 (paused), the measurement worth keeping:** per section, zerobas
      against the VG-8020 -- double division 1.6x, STR$ / BIN$ / MID$ 1.7x, string
      building 2.1x, LOG 2.2x, an INTEGER array sieve (`D%(M)=D%(M)+K`) 2.5x, a
      Pascal row in a DOUBLE array 2.8x, the partition DP (`P(K)=P(K)+P(K-M)`)
      3.0x. ARRAY ELEMENT ACCESS is the hotspot, well ahead of the arithmetic.
      And SQR (C4, [`sqr_speed.out`](scratchpad/sqr_speed.out)): 268 ms a call here
      against 134 on the VG-8020, 2.0x, the same for singles and doubles -- slow on
      BOTH machines, so a ladder program avoids it in a loop.
      ✅ **G1_snake and C2_euler (2026-10-30).** G1, the first in the hobbyist
      game-contest style: a self-playing snake in crunched 10-liner form --
      keywords run into names (`IFC=129ORC=128THEND=`, `FXANDNY`, `GOSUB9ELSESOUND8,0`),
      `:`-packed lines, VPOKEd characters and colours, PUT SPRITE, SOUND in the loop,
      a seeded 400-move demo, a VRAM checksum: SAME. C2: Project Euler 1, 2, 5, 6, 9,
      15, 18, 19, 20 and 28 at full size (Joost 2026-10-30: PE 1-100 may be
      published), in doubles where the answers pass 32767 and base-10000 limbs for
      100!: all ten answers match Joost's own solutions on the VG-8020; zerobas
      SAME. 📏 TIER 5: 299 s against 161.
      ✅ **C1_numbers (2026-10-30), THE FIRST CONTEST-STYLE PROGRAM** (Joost: "the kind
      of program competitive programmers write"; series C*, and G* for hobbyist
      game-contest style, both 2026-10-30). Sieve below 2000, GCD / MOD / `\`
      with negatives, modular power through doubles, 30! in base-10000 limbs,
      Fibonacci(80) by string addition, Collatz in doubles, a coin-change DP, an
      O(n log n) LIS: every answer but the seeded LIS was ALSO computed in Python
      first, and the VG-8020 matches all of them; zerobas SAME. The runner globs
      `[LCG]*.bas` now. 📏 Speed (TIER 5, paused): zerobas took 263 s where the
      VG-8020 took 139; the Collatz loop alone in doubles (divide, INT, compare)
      is 1.7x ([`collatz_speed.bas`](scratchpad/collatz_speed.bas): 2698 jiffies
      against 1574 for N = 1..60). The first draft took 561 s on the VG-8020 and
      timed out here; it was trimmed, not left to time out.
      ✅ **L2_survey (2026-10-30)**: INPUT the way people type into it --
      letters for a number, half a pair wrong, one value too many, a quoted name
      with a comma, a missing value, an empty answer, LINE INPUT with a comma,
      `1E2` / `-0` / `&H1F` / padded numbers. It FOUND D-INPUTCONT (and, while
      measuring, D-INPUTCOMMA); SAME after both.
      ✅ **L4_recurse (2026-10-30)**: recursion by GOSUB with arrays as the frame
      stack -- towers of Hanoi (63 moves), a quicksort of 40 seeded-RND values
      (depth 9), a 4-way flood count on a string grid with `MID$(...)=` -- and a
      FRE(0) check that the stack is clean afterwards: SAME. (My first quicksort
      overwrote its second child's bounds and did not sort -- the same wrong
      answer on all three machines.) zerobas took 72 s where the VG-8020 took 46
      (TIER 5, paused).
      ✅ **L3_turtle (2026-10-30).** DRAW with `X` substrings, `=var;` for
      angle / colour / lengths, `S` scale, `N` / `B`, relative `M`, then POINT
      samples and VRAM checksums; PLAY with `=var;` and `X`, and DRAW / PLAY
      errors. It FOUND D-FULLCLASH and D-PLAYEQ; SAME after both.
      ✅ **L2_codebreak and L4_machine (2026-10-29).** A seeded-RND code game
      (`MID$(...)=`, INSTR, ASC / CHR$, STRING$ / SPACE$, `\  \` and `&` USING,
      INPUT validation, ON..GOTO): SAME. Machine code from BASIC (DEFUSR /
      USR0-2 with DAC and VALTYP, VARPTR into a number and a string, a routine
      that calls FILVRM): it FOUND D-USRSTR; SAME after it.
      ✅ **L4_tables (2026-10-29)**: integer `\` / MOD / AND / OR / XOR / NOT,
      HEX$ / OCT$ / BIN$ and back, INT / FIX / CINT, single against double,
      PRINT USING tables of SQR / LOG / EXP / `^^^^`, trig through a DEF FN,
      compound interest with a double DEF FN, SWAP sort, STR$ of huge values,
      an int overflow trapped. It FOUND D-PUTINY; SAME after it.
      ✅ **L3_screen1 and L4_errors (2026-10-29).** SCREEN 1 with VPOKEd characters
      and colours, BASE / VDP / VPEEK checksums: SAME. The error-handling program
      (RESUME / RESUME NEXT / RESUME line, ERROR n, errors inside GOSUB, ON..GOSUB
      out of range, a retry count): SAME on the DISK target and, after D-NODEV, on
      NODISK (D-LATEINT's late interrupts are fixed). It FOUND D-NODEV: `OPEN "NUL:"`
      on the diskless target went to the tape. (My first L3_screen1 had a MOD
      overflow, ERR 6 on both machines.)
      🔧 **D-NODEV, FIXED 2026-10-29 (TIER 3).** With no disk, any name with a `:`
      that is not a known device is ERR 56 on the VG-8020 (`"NUL:"`, `"AB:"`,
      `":X"`, `"FOO:BAR"`, `"ABCDEFGHI:X"`); zerobas tested only a drive's second
      character, so those went to the cassette -- FOR OUTPUT opened it, FOR INPUT
      waited ~4.5 s with interrupts off and gave ERR 19
      ([`nodev_measure.out`](scratchpad/nodev_measure.out)). `nodisk_dev` now scans
      the whole staged name; the scan sits at the low region's END (`ndd_scan`,
      basic/main.asm), past the $3297 pin whose pad was 4 B -- the low region is
      now 1 B free plus that pad's 10 B (reusable, Joost 2026-10-20). Gate
      nodev-acceptance (the diskless target only: the DISK target's reference is
      the CF-3300), knife K-N ([`nodev_knife.out`](scratchpad/nodev_knife.out)).
      ✅ **More rungs (2026-10-29): L3_chart, L2_calendar, L3_editor, L2_hexmon, all
      SAME.** The chart (SCREEN 2, 24 POINT checksums) found D-GCDI4 (CIRCLE's arc
      maths under DI); the calendar found D-CATCOPY (INSTR copied its operands). The
      line editor (insert / delete / replace / `MID$` overtype / find) matches the
      VG-8020 on every line INCLUDING `FRE("")` after each command; the hex monitor
      (POKE / PEEK above a `CLEAR`ed HIMEM, HEX$, `VAL("&H..")`, XOR) matches too
      ([`progladder_l7.out`](scratchpad/progladder_l7.out)).
      ✅ **L5 (2026-10-29): random-access stock file, SAME against the CF-3300**
      (`@DISK`: the CF-3300 and the DISK target, each on a private copy of
      `disk/empty720.dsk`, the boot's `Enter date` answered with RETURN) —
      FIELD / LSET / RSET / MKI$ / MKS$ / CVI / CVS, PUT / GET with and without a
      record number, LOF, a sequential export read back with EOF / LOC / LOF, ON
      ERROR + RESUME on a missing file, KILL; printer and screen identical. Its
      gaps are KNOWN (D-DISKDI). Draft mistakes, all mine and all identical on both
      machines: MAXFILES left at 1 (ERR 52), `WRITE #` (not MSX BASIC: ERR 2), and
      `\ \` string fields, which the CF-3300 does not take (recorded under the
      PRINT USING item). The runner now INJECTS answers into KEYBUF
      (`omsx_repl.key_proc`): openMSX's `type` lost keys on BOTH machines after disk
      I/O.
      ✅ **L4 (2026-10-29): sprite demo, SAME** — sprites, ON SPRITE (2 hits),
      ON INTERVAL, two-voice PLAY, frame-locked; printer log identical. Its 2 gaps
      are KNOWN (D-GCDI3). The first draft's `PLAY "...AB>C"` was ERR 5 on BOTH
      machines (written as O5C now).
      ✅ **L3 (2026-10-29): spreadsheet + sales report, SAME** in output; the
      report's RND gaps are KNOWN (D-GCDI2). Sheet x1.36 time, report x1.44
      ([`progladder_l3.out`](scratchpad/progladder_l3.out)).
      ✅ **L2 (2026-10-28): address book + text adventure, SAME** after D-GCDI
      ([`progladder_gaps.out`](scratchpad/progladder_gaps.out), which also shows 0
      interrupt gaps on all five programs). The address book found D-GCDI: its
      4th `CHOICE?` read `AMAES` -- a typed RETURN lost.
      🔧 **D-GCDI, FIXED 2026-10-28 (TIER 1: typed keys were lost) -- the GC half.**
      Sub-ROM tenants run under `sr_slot`'s DI. Two of them reach a whole string GC:
      the string-heap engine and the arrays engine's string-element store. zerobas
      missed frames for up to 107 ms; `TIME` ran 72% of the clock through a
      `STRING$` loop; keys typed meanwhile were lost. The VG-8020: 0 gaps. Fix:
      `strheap_engine` and `aeng_copy_str` are now `ei / call body / di / ret`
      (the trampoline contract, spec-basic-subrom-trampoline.md §2.2, as `bload`
      does), page-0 tenants whose IRQ takes the $0038 trampoline; page 1 stays
      main, so `htimi_guard` keeps serving PLAY. Not at `ary_engine`'s entry:
      scalar lookups share it and are the hot path (+10 T a NEXT, test_forint I3).
      Gate `gcdi-acceptance` (JIFFY-watchpoint gaps + a line typed during the
      churn; [`gcdi_gate.out`](scratchpad/gcdi_gate.out)); knives K-S / K-A each
      turn their own row red, ROM hashed around each plant
      ([`gcdi_knife.out`](scratchpad/gcdi_knife.out)); before:
      [`gcdi_before.out`](scratchpad/gcdi_before.out). `programs-acceptance` runs
      `--gaps`: more gaps than the reference diverges, except the KNOWN_GAPS
      entries (D-GCDI2), which must STAY gappy until their fix removes them.
      ⚠️ RESIDUAL, NOT MEASURED: the other DI tenants (PRINT USING, READ/DATA,
      LIST's detokeniser, PLAY parse, FILES, ...) -- the ladder's gap watch is the
      instrument.
