- [ ] ⚠️ **`build/disk.rom` pad-only damage is invisible ON PURPOSE** — 9543 of
      16384 bytes (58.2 %) are `$00` pad in 252 runs. Closing it needs a whole-image
      digest, which would pin the ROM against every legitimate `disk/*.asm` change.
      Re-open only with an argument that answers that. Detail: line 2577.
      🎚️ APPARATUS — disk.rom pad
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
