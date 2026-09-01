# The disk ROM's layout, and where its free space actually is

**2026-09-01.** `zerobas-disk` is a **pinned-address** ROM. It is a Tier-2
provider: its entry points must land on the addresses the real disk system calls,
so `disk/*.asm` carries **68 `ds $XXXX - $, $00` pads** that push each region up
to the next canonical entry. That layout is deliberate and load-bearing — and it
means the ROM does not behave like a ROM with "space at the end".

## The thing that catches you

**The appendable tail is 2 bytes.** The image ends at `$7FFD`.

Every usable byte is *interior*, held in those pads. Adding code anywhere before
a pad shrinks that pad; adding code where there is no pad below you drives the
next `ds` count **negative**, and pasmo runs past 64 KB and emits nothing.

That failure is loud, which is the one piece of luck: `tools/pad_rom.py` refuses
to pad an empty image rather than shipping one, so a mistake here cannot reach a
built machine. Three attempts to add ~25 bytes to `init` hit exactly this.

🔴 **AND THE OBVIOUS MEASUREMENT LIES.** Reading the built ROM for long runs of
`$00` finds a 3464-byte run and invites the conclusion "there is plenty of room".
There is — but not where you can *reach* it by appending, and the run's address is
not where a naive offset-vs-address slip will tell you it is. Both errors were
made in one session before this document existed.

## How to find the room

```bash
make diskmap
```

It reads the **built ROM** every time, so there is no figure here to rot. It
prints each pad, its size, and the `file:line` where the `ds` is written, largest
first — plus the appendable tail, so the number you must not spend is on screen
next to the numbers you may.

As measured on 2026-09-01: **9328 B of 16384 (56.9 %) sits in pads**, the largest
being 3464 B ending at `$75A5` (`disk/kernel.asm:2046`) and 2531 B ending at
`$5FE5` (`disk/kernel.asm:573`).

⚠️ **STATED LIMIT:** a pad is measured as the `$00` run ending at its pinned
target, so a preceding body whose final bytes are genuinely `$00` inflates that
pad's figure. Every number is an **upper bound**.

## How to use a hole

Put the code **immediately before the `ds` that creates the pad**. The pad
shrinks by exactly what you add, and every pinned address after it stays put.

The disk banner is the worked example: `disk_show_banner` and its string sit just
above `disk/kernel.asm:2046`'s `ds $75A5 - $, $00`, and the ROM's pinned entries
are unmoved.

## Reaching it from outside

`$4022`–`$402C` are unused kernel-entry slots. A `jp` planted at one of them is a
normal disk-ROM entry the main ROM can `CALSLT`, which is how the banner is
called — see `basic/interp.asm`'s `init`, and the note there on why it cannot be
called from the disk ROM's own `INIT`.
