- [ ] 🔍 **fp_mul WITH AN INVALID BCD DIGIT (> 9): THE NEW LOOP'S LEFTMOST CELL CAN DIFFER
      FROM THE OLD ONE (D-FPMULBCD, found 2026-10-31 by D-REREAD batch 5).**
      🎚️ TIER 6 — only reachable through `CVD` / `CVS` of arbitrary bytes or a POKE
      into a float variable.
      🤖 **AUTONOMOUS** — measure first: what the VG-8020 prints for a product of a
      double whose mantissa holds a nibble above 9 (`CVD` of a crafted string). Valid
      digits give identical results (the batch-5 model; test_fpdiv_fast). The OLD
      loop could also write one byte BELOW MULPROD in pass 0 with such a digit; the
      new one cannot.
