<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `INIT32` ($006F) — set up the 32-column text screen (SCREEN 1)

> **Spec:** FINAL (2026-11-18), the core rule, with INITXT. Stated on [INITXT's page](INITXT.md), together
> with INITXT: the two calls differ only in values.

## Summary

`INIT32` switches the screen to 32-column text (SCREEN 1). It:
- programs the VDP from T32NAM .. T32PAT, with the border from BDRCLR;
- sets the width from LINL32, as it is;
- fills the colour table from FORCLR / BAKCLR;
- parks the 32 sprites (Y 209, colour FORCLR);
- clears the screen and homes the cursor;
- draws the function-key line on row CRTCNT when it is on.

The rules are on [INITXT's page](INITXT.md), sections "2. INIT32" and "3. Both".

## Differences from the reference

As INITXT's (its page's Differences): **D-INITEDGES**, and the ruled font.

## On the turbo R

- With the key line on at width 255, row 13 holds "key0" only -- no "key1" at column 34, which every earlier machine writes; at width 0 the name table's sum differs from the FS-A1WSX's. FS-A1GT = FS-A1ST, 2026-11-23 (D-TRSPEC) [M]: [AE_trall/xinit.out](../../scratchpad/AE_trall/xinit.out), [AE_trall/xinit4.out](../../scratchpad/AE_trall/xinit4.out); the details are on [INITXT's page](INITXT.md).
