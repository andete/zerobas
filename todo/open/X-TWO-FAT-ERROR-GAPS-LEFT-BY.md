- [ ] ⚠️ **Two `fat-error` gaps left by the 8-of-8 closure** — (1) no knife
      separates `bload-alive`, `open-alive` or `append-alive` from the shared
      `fat_io_getbyte` layer, so each is shown to see its READ PATH die but not
      proven verb-specific; (2) `merge-alive`, `append-alive` and `kill-alive`
      lean on a SECOND verb (`SAVE",A"`, OPEN/OUTPUT+INPUT, FILES), so a break
      elsewhere can mark their row NOT MEASURED — loud, but not their own verb.
      Detail:
      [`docs/spec-fat-error-verb-control.md`](docs/spec-fat-error-verb-control.md) §8.6.
      *(Item (3), `run-missing`'s second message, is CLOSED — see D-RUNTAIL
      below.)*
      ✅ **GAP (1) CLOSED and GAP (2) DEMONSTRATED, 2026-09-05 (D-FATVERB,
      `scratchpad/fatverb_knives.py`) — knives 4/4 exact.**
      • **K-FE2 / K-FE3 / K-FE4 each cut code only ONE verb executes** — BLOAD's
      own `cp BSAVE_DISK_ID` marker compare, `oo_input`'s own `mode = INPUT`
      store, and `fat_io_append`'s own re-use of the existing chain — and each
      moves its own `*-alive` row. That is precisely what gap (1) said was
      missing: the rows are now proven VERB-specific, not merely "the read path
      died".
      • **K-FE1 is the other half of the claim, and nobody had run it**: cutting
      the shared `fat_io_getbyte` moves **all six** byte-reading controls
      (load/run/bload/open/append/merge) while the DIRECTORY ones — `fat-alive`
      (FILES), `kill-alive`, `name-alive` — correctly hold. Those greens are what
      say the cut breaks the read layer and not the disk.
      • 🎯 **GAP (2) IS VISIBLE IN K-FE3's OWN RESULT**: breaking `OPEN FOR
      INPUT` moves `append-alive` too, because `append-alive` reads its data back
      through an `OPEN FOR INPUT`. The prediction SAYS so rather than discovering
      it, since a prediction omitting it would score the arm as a miss. Gap (2)
      is therefore no longer a suspicion — it is a measured coupling with a named
      mechanism.
      🔴 **AND THE MATRIX'S FIRST RUN REPORTED TWO FALSE MISSES — the READOUT,
      not the knives.** `append-alive` is printed TWICE (`FAIL append-alive …`
      and later `PASS append-alive (directory) …`, a second check under the same
      leading name), and a `name -> verdict` dict keeps the LAST, so a failing row
      read as passing. A row is FAILing if ANY of its lines says so
      [[readout-blind-to-its-own-subject]]. With that fixed, K-FE1 and K-FE4 were
      exact all along.
      ⚠️ **Gap (2) is DEMONSTRATED, not fixed**: `merge-alive`/`append-alive`
      still lean on a second verb. Rebuilding them to stand alone is separate
      work and is not done here.
      ✅ **`append-alive` NOW HAS A SECOND WITNESS THAT NEEDS NO SECOND VERB —
      D-FATSIZE, 2026-09-10.** The FAT12 root entry carries the file LENGTH 32
      bytes from the sector `dir_names` was already walking, so `dir_sizes()`
      reads it for nothing, and `append-alive` asserts **9**.
      🎯 **AND THE NUMBER IS DISCRIMINATING, NOT DECORATIVE**: `AA\r\n` +
      `BB\r\n` + the `$1A` EOF marker is 9, where an APPEND that behaved like
      OUTPUT would have truncated to `BB\r\n` + EOF = **5**. The size separates
      the two outcomes by itself, from the directory — which is exactly what gap
      (2) said the row lacked, since its readback goes through `OPEN FOR INPUT`.
      ⚠️ **MEASURED, NOT DERIVED — reasoning it out gives 8.** The EOF byte is
      easy to forget, so the witness was wired OBSERVE-ONLY first, the probe
      printed `dir size 9`, and the pin was written from that reading.
      🔬 **TEETH SHOWN**: mutating the pin to 5 — the truncating-APPEND value —
      gives `rc=2` and `FAIL append-alive … dir size 9 (want 5)` **while the
      screen witness still reads `AABB`**. So the size caught what the readback
      could not, which is the case for keeping BOTH rather than swapping one for
      the other.
      🔴 **`merge-alive` GETS NO SUCH WITNESS, AND THE REASON IS STRUCTURAL.** Its
      file is 12 bytes — but that 12 is `SAVE",A"`'s OUTPUT, so the size cannot
      witness MERGE at all; it witnesses the verb the row is trying not to depend
      on. Decoupling it needs an ASCII-saved `.BAS` **on the fixture image**
      (`MERGE"A:PROG.BAS"` was already refused during D-FATVERB's scouting — the
      fixture's copy is TOKENISED and MERGE raises `Syntax error`), and that is a
      `tools/make_test_dsk.py` change touching every disk probe. Named with its
      blast radius rather than left as "separate work".
      📏 `fat-error-acceptance` is battery-EXCLUDED, so it was re-run BY HAND
      three times here — observe-only, pinned, and knifed — **20 rows printed, 11
      scored, ALL PASS** on the pinned run.
      🎚️ APPARATUS — fat-error knife gaps
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
