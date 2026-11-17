<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# `INIT32` ($006F) — set up the 32-column text screen (SCREEN 1)

> **Spec:** DRAFT 2 (2026-11-17). Stated on [INITXT's page](INITXT.md), together
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

As INITXT's (its page's Differences): **D-KEYLINESHIFT**, **D-INITEDGES**, **D-LINTTBVAL**, and the
ruled font.
