# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Cross-platform discovery of openMSX locations and the stock C-BIOS ROM.

Single source of truth for the host-specific paths the build tooling needs:

  * the openMSX *share* dir (its bundled machines/ + ROMs),
  * the openMSX *user* dir (where machine configs get installed),
  * the `openmsx` *binary* (for the probes),
  * the stock *C-BIOS main ROM* the patch build stamps + verifies against.

These used to be hardcoded to macOS paths in several places independently (the two
build-patches shell scripts, the machine installer), which is exactly why the build
failed off macOS. Centralising the candidate lists here keeps Linux / Windows /
macOS support in one place and stops the copies from drifting.

Everything is best-effort auto-detection with an explicit override always winning;
nothing here launches openMSX or reads a ROM.
"""
from __future__ import annotations

import glob
import os
import shutil
import sys

_WIN = os.name == "nt"


def _windows_share_dirs() -> list[str]:
    """openMSX on Windows installs `share/` under its program folder."""
    out = []
    for env in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        base = os.environ.get(env)
        if base:
            out.append(os.path.join(base, "openMSX", "share"))
    return out


def _share_candidates() -> list[str]:
    return [
        "/Applications/openMSX.app/Contents/Resources/share",      # macOS .app
        "/opt/homebrew/share/openmsx", "/usr/local/share/openmsx",  # Homebrew
        "/usr/share/openmsx", "/usr/local/share/openMSX",          # Linux
        *_windows_share_dirs(),                                     # Windows
    ]


def _user_candidates() -> list[str]:
    out = []
    appdata = os.environ.get("APPDATA")
    if appdata:                                                    # Windows
        out.append(os.path.join(appdata, "openMSX"))
    out += [
        os.path.expanduser("~/.openMSX"),                          # Linux / macOS
        os.path.expanduser("~/Documents/openMSX"),                 # some installs
    ]
    return out


def _binary_candidates() -> list[str]:
    out = [
        "/opt/homebrew/bin/openmsx", "/usr/local/bin/openmsx",     # Homebrew
        "/Applications/openMSX.app/Contents/MacOS/openmsx",        # macOS .app
        "/usr/bin/openmsx",                                        # Linux
    ]
    for share_parent in _windows_share_dirs():                     # Windows
        out.append(os.path.join(os.path.dirname(share_parent), "openmsx.exe"))
    return out


# Public candidate lists (importers may extend / inspect these).
SHARE_CANDIDATES = _share_candidates()
USER_CANDIDATES = _user_candidates()


def first_existing(paths, what: str) -> str:
    """First path in `paths` that is an existing directory, or exit with help."""
    for p in paths:
        if p and os.path.isdir(p):
            return p
    sys.exit(f"error: could not auto-detect {what}; pass it explicitly "
             f"(looked in: {', '.join(p for p in paths if p)})")


def find_share(explicit: str | None = None) -> str:
    return explicit or first_existing(SHARE_CANDIDATES, "openMSX share dir")


def find_user(explicit: str | None = None) -> str:
    return explicit or first_existing(USER_CANDIDATES, "openMSX user dir")


def find_openmsx_binary(explicit: str | None = None) -> str:
    """Resolve the openMSX executable, PATH-first.

    Order: explicit arg, $OPENMSX, then PATH (`openmsx`/`openmsx.exe`), then the
    per-platform install defaults. Falls back to the bare name `openmsx` so the OS
    can resolve it (or fail with a clear "command not found")."""
    for cand in (explicit, os.environ.get("OPENMSX")):
        if cand:
            return cand
    on_path = shutil.which("openmsx") or shutil.which("openmsx.exe")
    if on_path:
        return on_path
    for cand in _binary_candidates():
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return "openmsx"


def find_cbios_rom(names, explicit: str | None = None) -> str | None:
    """Locate a stock C-BIOS main ROM by exact filename(s).

    `names` is a filename or ordered list of filenames (e.g. "cbios_main_msx1.rom");
    each is looked for under every share dir's `machines/` folder, in order, so the
    result is deterministic — important because the BPS patch is CRC-locked to one
    exact stock ROM. Returns the first hit, or None if nothing matched."""
    if explicit:
        return explicit
    if isinstance(names, str):
        names = [names]
    for share in SHARE_CANDIDATES:
        machines = os.path.join(share, "machines")
        for name in names:
            cand = os.path.join(machines, name)
            if os.path.isfile(cand):
                return cand
            # tolerate minor packaging variants (e.g. a version suffix)
            hits = sorted(glob.glob(os.path.join(machines, name.replace(".rom", "*.rom"))))
            if hits:
                return hits[0]
    return None


# --- publishing into the shared tree ----------------------------------------
# 🔴 `open(out, "w")` TRUNCATES THE MOMENT IT IS CALLED and only then writes, so
# for the duration of that gap the shared path holds an EMPTY file. openMSX
# reads its machine config at start, so an emulator launching inside the window
# dies before executing one instruction. D-MACHXML measured it at
# **412 / 1200 (34.3 %) of concurrent reads torn** against 0 / 1200 atomic
# (`scratchpad/machxml_repro.py`), and `repack-machine` is a prerequisite of 112
# Makefile targets that `make gates` runs in parallel.
#
# The cure lives HERE, beside `find_user()`, because the module that knows where
# the shared tree is, is the one that should know how to write into it. That is
# also what gives a checker something to name: writes into the tree go through
# `publish()`, and a bare `open(..., "w")` on a path derived from `find_user()`
# is the finding.
def publish(out: str, text: str) -> None:
    """Write `text` to `out` so no reader can ever see a partial file.

    `os.replace` is atomic on POSIX within a filesystem, and the temp sits in
    the SAME directory so it always is one. The pid keeps two concurrent
    installers from sharing a temp -- they may both write, and whichever lands
    last wins with a WHOLE file, which is all any reader needs.
    """
    tmp = f"{out}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, out)
