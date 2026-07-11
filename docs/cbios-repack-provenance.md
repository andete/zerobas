<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# C-BIOS repack — provenance firewall for the merged main-ROM patch

The cbios-repack arc ([`spec-cbios-repack-tooling.md`](spec-cbios-repack-tooling.md))
ships one new deliverable that the rest of zerobas does not: a **merged 32 KB main
ROM** ([`../zerobas-main-eu.ips`](../zerobas-main-eu.ips) / [`.bps`](../zerobas-main-eu.bps))
that combines a *repacked C-BIOS* base with zerobas's own relocated BASIC and tape
layers. Because that image is built **on top of** C-BIOS bytes, it needs an explicit
provenance argument that the shipped patch still carries **zero C-BIOS bytes** — the
same firewall the rest of the repo holds ([`../PROVENANCE.md`](../PROVENANCE.md),
[`clean-room-audit.md`](clean-room-audit.md)). This is that write-up.

The claim has two independent halves — the *source* firewall and the *output*
firewall — and both are checkable.

## 1. Source firewall — no C-BIOS bytes enter the repo (decision D1)

The repack edits C-BIOS *source*, and we hold that edit as **our own 0BSD patch
against a pinned upstream tag**, never as vendored bytes:

- [`../cbios-repack/eu-drop-statements.patch`](../cbios-repack/eu-drop-statements.patch)
  is a unified diff — a *description* of one edit (comment out `include
  "statements.asm"`) to C-BIOS's BSD-2-clause source at tag `v0.29-3-gb5ad9cb`. A
  diff is not a merge; it contains our text, not upstream code bytes.
- The build applies that patch to the **user's own** `~/projects/cbios` checkout
  ([`../tools/build_repacked_cbios.py`](../tools/build_repacked_cbios.py)), rebuilds,
  and pins both results by sha1 (pristine `baf2e9c6…`, repacked `edb08440…`). No ROM
  bytes — pristine or repacked — are stored in the repo; they are reproduced on demand.

So nothing under version control contains C-BIOS code. That is the same rule the
whole project runs on; the repack does not weaken it.

## 2. Output firewall — the merged IPS/BPS carries only our bytes or `$00`

The merged main ROM *does* contain C-BIOS bytes at runtime (the whole BIOS lives in
page 0 below `$2812`). The shipped artifact, though, is **not** the ROM — it is a
**patch diffed against the pristine stock built from the same pinned tag**
([`../tools/build_patches.py`](../tools/build_patches.py) `--main`). An IPS/BPS only
records the offsets where target ≠ source. Everywhere the merged image still equals
stock — i.e. every retained C-BIOS byte — the patch is **silent**. So the payload can
only contain bytes at offsets we *changed*, and by construction of the merge
([`../tools/build_mainrom.py`](../tools/build_mainrom.py)) those come from exactly
three of our own sources:

| Region | Source of the changed bytes | Provenance |
|---|---|---|
| `$00A5–$00A7`, `$00E2–$00F5` | tape page-0 vectors (`tape/tape.asm`) | ours |
| `$2812–$7FFF` | relocated BASIC (`basic/main-reloc.asm`) — all of it since the 2026-07-11 D5 revision (tape bodies now at `$09EE–tape_end`, gap-1 fill) | ours |
| dropped dead-code holes | zeroed by the repack → `$00` in the diff | not a C-BIOS byte |

No retained BIOS byte can appear in the payload, because at those offsets the diff
emits nothing.

### The proof (reproducible, in-repo, no external build)

Parsing the committed [`../zerobas-main-eu.ips`](../zerobas-main-eu.ips) and
classifying every payload byte:

- **6 records, 17 223 changed bytes**, offset span `$00A6–$7FFF`.
- **16 411 non-zero** bytes — **0** of them fall outside a zerobas-owned region
  (tape vectors or `$2812–$7FFF`).
- **0** changed offsets below `$2812` are anything other than a tape vector.
- The remaining **812** payload bytes are `$00` — the dropped dead-code holes.

Grounding those "owned" bytes as *literally ours*, not a coincidental match:

- `IPS(pristine)` reconstructs the merged image **byte-for-byte** (patch integrity).
- `merged[$2812:$8000]` equals `basic-reloc.rom` everywhere **except** (pre-D5-revision layouts) `$3A72–$3C42`,
  and those exception offsets are `$00` in `basic-reloc.rom` — i.e. the only
  non-BASIC bytes in the BASIC window are the tape bodies dropped into BASIC's
  reserved `$00` hole. Every window byte therefore traces to `basic/` or `tape/`.

The BPS is the same diff in a CRC-locked container (it additionally pins the pristine
source CRC32), so the identical argument holds.

## 3. Verify on demand

```sh
# Output firewall — parse the shipped IPS, assert no non-$00 byte outside our regions:
python3 - <<'PY'
data=open("zerobas-main-eu.ips","rb").read(); i=5; recs=[]
while data[i:i+3]!=b"EOF":
    off=int.from_bytes(data[i:i+3],"big"); i+=3
    size=int.from_bytes(data[i:i+2],"big"); i+=2
    if size==0:
        n=int.from_bytes(data[i:i+2],"big"); i+=2; v=data[i]; i+=1; recs.append((off,bytes([v])*n))
    else:
        recs.append((off,data[i:i+size])); i+=size
owned=lambda a: a in set(range(0xA5,0xA8))|set(range(0xE2,0xF6)) or 0x2812<=a<=0x7FFF
leaks=[(off+k,b) for off,p in recs for k,b in enumerate(p) if b and not owned(off+k)]
print("C-BIOS leak bytes:", len(leaks))   # -> 0
PY

# Source firewall — reproduce the pinned repacked ROM from the tracked patch:
#   see ../cbios-repack/README.md ("Reproduce").
```

Both checks are cheap and repo-local; the source firewall's reproduction needs the
user's C-BIOS checkout (by design — that is where the only C-BIOS bytes ever live).
