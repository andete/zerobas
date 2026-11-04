# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-REFCACHE — do not re-measure a constant.

A differential probe reads three sides. Two of them, the Philips VG-8020 and the
National CF-3300, are FIXED ROMs: given the same typed lines they return the same
screen today, tomorrow and in a year. zerobas's side changes on every build; the
references do not change at all. On 2026-08-28 D-STRLONG ran its 3-side matrix
FOUR times over rows whose reference answers could not have moved, and roughly
two thirds of every run was re-measuring constants.

This module caches the raw capture of a `run_cases` call so a repeat is served
from disk. It is deliberately paranoid, because the failure it could cause is
the worst one this project has:

  🔴 A CACHE IS ONE SLIP AWAY FROM "A PREDICTION COPIED INTO THE RESULT COLUMN".
  A key that is too loose serves an OLD answer for a NEW question and the run
  reports it as a reading. Every design decision below is about making a wrong
  hit impossible rather than unlikely, and about making a hit VISIBLE so a run
  that measured nothing cannot read like a run that measured everything.

═══ WHAT IS IN THE KEY ═══════════════════════════════════════════════════════

1. THE MACHINE'S ACTUAL BYTES, not its name. `machine_identity()` hashes the
   machine XML *and every ROM it references* (by content when the file is on
   disk, by the `<sha1>` the XML declares when openMSX resolves it from its own
   ROM database). 🎯 THIS IS WHAT MAKES THE CACHE SAFE FOR zerobas TOO, with no
   "is this a reference?" list for anyone to keep up to date: zerobas's ROM hash
   changes on every build, so its entries simply always miss -- and if a rebuild
   happens to be byte-identical, a hit is CORRECT, not lucky.
2. EVERY LINE TYPED, verbatim, including the reset/prologue sequence.
3. EVERY PARAMETER THAT CHANGES DELIVERY OR CAPTURE -- batch, reset, capture,
   holds, hold_secs, prologue, boot, step, cap_gap, timeout, cart, diska,
   verify_delivery, run_gap, sentinel, sentinel_capture.
4. A HARNESS FINGERPRINT: the bytes of omsx_repl.py, omsx_run.py and
   omsx_preflight.py (whose guarded() edits every spawned argv). If HOW a
   line is delivered or a screen is read changes, every stored reading was taken
   by a different instrument and must be discarded. [[apparatus-is-part-of-the-measurement]]

═══ THREE RULES THAT ARE NOT OBVIOUS ═════════════════════════════════════════

🔴 ALL-OR-NOTHING PER CALL, NEVER PER CASE. Under `batch=True` a whole matrix
   shares ONE boot, and serving half of it from cache would change the batch
   COMPOSITION of the half that still runs. The harness has a `--boot-per-case`
   escape hatch precisely because inter-case leakage is possible, so a
   composition change could move an answer for a reason that has nothing to do
   with staleness -- and the disagreement would look like a stale cache. So a
   call is served entirely from cache or not at all. Probes that already run
   boot-per-case (one case per `run_cases` call, e.g. basic_probe_deffn) get
   full per-row caching from this rule for free; batched matrices get
   whole-matrix caching, which is what a re-run needs anyway.

🔴 THE OUT-PARAMETER IS STORED AND REPLAYED, NOT BYPASSED -- AND THE FIRST CUT
   OF THIS MODULE GOT THAT WRONG IN A WAY THAT LOOKED FINE. `settle_out` is a
   dict the CALLER reads afterwards (probe_signal.kwargs wires capture-on-signal
   through it), so leaving it empty on a hit would make the caller's tally
   silently under-count. The safe-looking answer was to bypass the cache for any
   call that passes one. 🎯 THEN I COUNTED: **23 of 23 rows** of a typical
   differential probe are marked, so that rule made the cache exactly 0% useful
   on the entire class of probe it was built for -- installed, green, and inert.
   [[an-unnamed-outcome-reads-as-no-outcome]] [[gateblind-slice]]

   So the dict round-trips (int keys and tuples preserved exactly, see `_enc`).
   ⚠️ BUT A REPLAYED PROVENANCE IS NOT A MEASUREMENT OF THIS RUN. Those values
   are emulated-time instants -- when the sentinel fired, or that it did not --
   and they are how the capture-on-signal apparatus is watched for health. A
   replayed dict therefore carries `replayed=True`, and probe_signal's tally
   reports those separately, so "1344 on signal, 1 fell back" can never be a
   recording of an older run wearing a live run's clothes.
   [[apparatus-is-part-of-the-measurement]] [[readout-blind-to-its-own-subject]]

🔴 A NON-READING IS NEVER STORED. `None`, an empty capture, `<NO OUTPUT>` and
   `<NO CAPTURE>` are apparatus FAULTS. Storing one would freeze a flake into a
   permanent answer that no rerun can dislodge -- the exact opposite of what the
   serial flake-retry exists to do. Misses are cheap; a cached ghost is not.

═══ MODES ════════════════════════════════════════════════════════════════════

  ZEROBAS_REFCACHE=1        (default) read + write
  ZEROBAS_REFCACHE=0        disabled entirely
  ZEROBAS_REFCACHE=verify   🎯 THE FALSIFICATION MODE. Run EVERYTHING for real,
                            then compare against whatever was stored and FAIL
                            LOUDLY on any mismatch. This is what says the cache
                            is telling the truth, rather than the cache being
                            trusted because it is convenient. Run it before
                            trusting a long-lived store.
  ZEROBAS_REFCACHE=refs     D-REFSONLY (Joost 2026-11-03, "References only"),
                            what tools/run_gates.py forces for every unit:
                            REFERENCE machines as in `1`, zerobas machines
                            (is_subject: by ROM bytes, then by name) always
                            measured, never served, never stored.

Store: $ZEROBAS_REFCACHE_DIR, else ~/.cache/zerobas/refcache. NOT under
/tmp/zerobas -- that root is wiped on purpose and the whole point is to persist
across sessions. Entries are one JSON file per key, sharded by the first two hex
characters, written to a temp file in the SAME directory and `os.replace`d into
place: the battery runs 8-wide and a shared path written non-atomically is how
the machine-XML race produced 412 torn reads of 1200. [[machxml-race]]
"""
from __future__ import annotations

import base64
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

import probe_tmp                        # noqa: F401 -- sets tempfile.tempdir
# 🎯 NOT DECORATION. `store()` writes its temp file with an explicit `dir=` (it
# MUST land beside the entry it replaces, or the rename is not atomic), but the
# selftest's scratch dirs have no such constraint and would otherwise escape to
# the system temp. `temp-root-check` caught exactly that. [[one-temp-root]]

_MODE = (os.environ.get("ZEROBAS_REFCACHE") or "1").strip().lower()
ENABLED = _MODE not in ("0", "no", "off", "false")
VERIFY = _MODE in ("verify", "check")
# D-REFSONLY (Joost 2026-11-03, asked whether batteries should use the cache:
# "References only"). In `refs` mode a REFERENCE machine is served and stored
# exactly as in mode 1, and a zerobas machine is NEITHER served NOR stored: it
# is booted and measured every time. tools/run_gates.py forces this mode for
# every unit, so the subject is measured on every battery run and only the
# constants are replayed (docs/spec-refcache.md §6).
REFS = _MODE in ("refs", "references")

ROOT = (os.environ.get("ZEROBAS_REFCACHE_DIR")
        or os.path.join(os.path.expanduser("~"), ".cache", "zerobas", "refcache"))

# a reading that is not a reading -- never stored, never served
NON_READINGS = ("<NO OUTPUT>", "<NO CAPTURE>")

STATS = {"hit": 0, "miss": 0, "store": 0, "bypass": 0, "verify_ok": 0,
         "verify_bad": 0, "refused": 0, "replayed": 0, "expired": 0,
         # D-REFSONLY: zerobas readings taken live under `refs`, and zerobas
         # readings SERVED from the store (any mode). Under `refs` the second
         # one is 0 by construction -- and `refuse_subject_hit` dies if not.
         "subject_measured": 0, "subject_served": 0}

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SUBJECT: dict[str, bool] = {}


def _repo_rom(path: str) -> bool:
    """A ROM file built in THIS repo (build/*.rom and anything else under it)."""
    p = os.path.realpath(path)
    return (p.startswith(os.path.realpath(REPO) + os.sep)
            and p.lower().endswith((".rom", ".bin")))


def is_subject(machine: str, files=()) -> bool:
    """True iff this launch measures ZEROBAS, i.e. must never be replayed in
    `refs` mode.

    🎯 BY BYTES FIRST: the machine XML names a ROM built in this repo (the KD-R
    logic -- the REPACK installer writes build/*.rom by absolute path), or an
    inserted file (`files`: a -cart, a cart= argument) is one. BY NAME SECOND:
    the C-BIOS_MSX1_EU_REPACK* prefix. The two must agree; when they do not,
    the answer is SUBJECT (measure) -- a wrong "reference" verdict replays the
    thing under test, a wrong "subject" verdict only costs a boot. An XML that
    cannot be resolved is a subject for the same reason."""
    by_name = machine.startswith("C-BIOS_MSX1_EU_REPACK")
    if any(f and _repo_rom(str(f)) for f in files):
        return True
    if machine not in _SUBJECT:
        xml = _machine_xml(machine)
        if xml is None:
            by_bytes = True
        else:
            body = open(xml, encoding="utf-8", errors="replace").read()
            names = re.findall(r"<filename>\s*([^<]*?)\s*</filename>", body)
            by_bytes = any(_repo_rom(n) for n in names if os.path.isabs(n))
        _SUBJECT[machine] = by_bytes or by_name
        if by_bytes != by_name and xml is not None:
            sys.stderr.write(
                f"⚠️ refcache: {machine}: name says "
                f"{'zerobas' if by_name else 'reference'}, its ROM bytes say "
                f"{'zerobas' if by_bytes else 'reference'} -- treated as ZEROBAS "
                f"(measured, never replayed)\n")
    return _SUBJECT[machine]


def subject_bypass(machine: str, files=()) -> bool:
    """`refs` mode and a zerobas launch: the caller must run for real and must
    neither load nor store. Counts it, so the tally names what was measured."""
    if REFS and is_subject(machine, files):
        STATS["subject_measured"] += 1
        return True
    return False


def refuse_subject_hit(machine: str, files=()) -> None:
    """THE GUARD, called on every hit path just before a stored reading is
    served. In `refs` mode serving zerobas is the one thing that must not
    happen -- a battery would print ALL PASS for a build it never booted
    (§6) -- so it is not a counter, it is a hard stop."""
    if is_subject(machine, files):
        if REFS:
            raise SystemExit(
                f"🔴 refcache: REFUSING TO SERVE A ZEROBAS READING ({machine}) in "
                f"ZEROBAS_REFCACHE=refs -- the subject must be measured on every "
                f"battery run (docs/spec-refcache.md §6). This is a harness bug.")
        STATS["subject_served"] += 1


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _file_sha(path: str) -> str:
    try:
        with open(path, "rb") as fh:
            return _sha(fh.read())
    except OSError:
        return "ABSENT"


# --- the machine's actual bytes ---------------------------------------------
_MACHINE_ID: dict[str, str] = {}


def _machine_xml(machine: str) -> str | None:
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "tools"))
    try:
        import openmsx_paths as P
    except Exception:
        return None
    cands = []
    try:
        cands.append(os.path.join(P.find_user(), "share", "machines", machine + ".xml"))
    except Exception:
        pass
    for share in getattr(P, "SHARE_CANDIDATES", []):
        cands.append(os.path.join(share, "machines", machine + ".xml"))
    for c in cands:
        if os.path.exists(c):
            return c
    return None


def machine_identity(machine: str) -> str:
    """sha256 over the machine XML AND every ROM it names.

    🎯 CONTENT, NOT NAME. A machine is only "the same machine" if the bytes it
    boots are the same bytes. zerobas's merged ROM moves on every build, so its
    entries expire by construction -- there is no list of "cacheable machines"
    to get wrong, and no judgement call about which side is a reference.
    """
    if machine in _MACHINE_ID:
        return _MACHINE_ID[machine]
    xml = _machine_xml(machine)
    if xml is None:
        # unknown machine -> a per-process unique identity, so nothing is ever
        # served for it. Refusing to cache is always safe; guessing is not.
        ident = "UNRESOLVED:" + _sha(os.urandom(16).hex().encode())
        _MACHINE_ID[machine] = ident
        return ident
    ident = identity_of_xml(xml)
    _MACHINE_ID[machine] = ident
    return ident


def identity_of_xml(xml: str) -> str:
    """The identity computation itself, on an explicit path.

    Split out so `--selftest` can plant a machine and mutate a ROM it names
    WITHOUT writing into openMSX's shared machines tree -- the tree whose
    non-atomic publication produced 412 torn reads of 1200. [[machxml-race]]
    A falsification arm that has to corrupt the real environment to fire is not
    one anybody will run twice.
    """
    with open(xml, "rb") as fh:
        text = fh.read()
    parts = [_sha(text)]
    body = text.decode("utf-8", "replace")
    for tag in ("filename", "sha1"):
        cursor = 0
        while True:
            a = body.find(f"<{tag}>", cursor)
            if a < 0:
                break
            b = body.find(f"</{tag}>", a)
            if b < 0:
                break
            val = body[a + len(tag) + 2:b].strip()
            cursor = b
            if tag == "sha1":
                parts.append("sha1:" + val)        # openMSX resolves it from its
                continue                            # own ROM database by content
            for p in sorted(glob.glob(val)) or [val]:
                parts.append(f"file:{os.path.basename(p)}:{_file_sha(p)}")
    return _sha("\n".join(parts).encode())


# --- the instrument ----------------------------------------------------------
_HARNESS: str | None = None


def harness_fingerprint() -> str:
    """The bytes of the delivery/capture code itself.

    A reading is taken BY something. Change how lines are typed or how the
    screen is scraped and every stored reading was taken by a different
    instrument, whatever the machine and the typed text say.
    """
    global _HARNESS
    if _HARNESS is None:
        here = os.path.dirname(os.path.abspath(__file__))
        # 🔴 AND THE HARNESS SWITCHES THAT CHANGE THE SCHEDULE, NOT ONLY THE
        # FILES. `$ZEROBAS_RUN_GAP` (D-CAPGAP) raises every case's RUN->capture
        # budget from inside `_tcl`, BELOW the point where this key is built --
        # so without this line an A/B "with and without the wider budget"
        # returned the FIRST run's cached capture and reported IDENTICAL ROWS BY
        # CONSTRUCTION. Measured: the second run logged `1 hit`, which is the
        # only reason it was caught. A reading is taken BY something, and a
        # switch that moves the capture instant is part of that something
        # [[a-rule-that-fits-every-row-may-be-fitting-the-instrument]].
        switches = "|".join(f"{k}={os.environ.get(k, '')}"
                            for k in ("ZEROBAS_RUN_GAP",))
        _HARNESS = _sha(b"".join(
            open(os.path.join(here, n), "rb").read()
            # omsx_preflight.py since D-AUTORUN (2026-10-11): its guarded() now
            # ADDS to every spawned argv (no settings save; autorun un-armed on a
            # tape mount), so it is part of HOW a reading is taken
            for n in sorted(("omsx_repl.py", "omsx_run.py", "omsx_preflight.py"))
            if os.path.exists(os.path.join(here, n))) + switches.encode()
            + emulator_identity().encode())
    return _HARNESS


_EMU: str | None = None


def emulator_identity() -> str:
    """The openMSX build the probes launch: `openmsx -v`'s first line (e.g.
    `openMSX 22.0-12-g989fb0b76`). Unreadable -> a random token, so nothing is
    served from a cache whose instrument cannot be named.

    🔴 THE EMULATOR IS PART OF THE INSTRUMENT (2026-10-28). Joost swapped openMSX
    for a 22.0 development build, and the key held nothing of the binary: a
    reading the OLD emulator took would have been replayed as the new one's,
    hiding exactly the change the swap was meant to show. Folded into
    harness_fingerprint(), so a new build expires every entry once.
    """
    global _EMU
    if _EMU is None:
        exe = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
        try:
            out = subprocess.run([exe, "-v"], capture_output=True, text=True, timeout=30).stdout
            _EMU = out.splitlines()[0].strip() if out.strip() else ""
        except (OSError, subprocess.SubprocessError):
            _EMU = ""
        if not _EMU:
            _EMU = "UNREADABLE:" + os.urandom(8).hex()
    return _EMU


MEDIA_PARAMS = ("diska", "diskb", "cassette", "cart")


def _param_key(k, v):
    # 🔴 A MEDIA PARAMETER IS KEYED BY ITS BYTES, NOT ITS PATH (2026-11-03). The
    # disk / tape probes copy their image to a fresh temp file per run, so the
    # path made every run a new key: the first FULL under `refs` stored 718
    # reference readings and the next FULL missed every one of them again.
    # The bytes are what the machine reads; a path is only where they sat.
    if k in MEDIA_PARAMS and isinstance(v, str) and os.path.isfile(v):
        return {"sha256": _file_sha(v)}
    return list(v) if isinstance(v, tuple) else v


def key_for(machine: str, cases, params: dict) -> str:
    # "v" 2 for a call that carries a media file: entries stored before
    # 2026-11-04 hold no post-run media bytes (see media_snapshot), so they
    # must never be served to a caller that reads its disk back.
    has_media = any(params.get(k) for k in MEDIA_PARAMS)
    payload = {
        "v": 2 if has_media else 1,
        "machine_id": machine_identity(machine),
        "harness": harness_fingerprint(),
        "cases": [[c[0], list(c[1])] for c in cases],
        "params": {k: _param_key(k, v) for k, v in sorted(params.items())},
    }
    return _sha(json.dumps(payload, sort_keys=True, default=str).encode())


def _enc(o):
    """JSON cannot hold an int dict key or a tuple, and settle_out is full of
    both (`marks[3] = [(12.5, 255)]`). Round-tripping through plain JSON would
    turn `3` into `"3"` and the tuple into a list -- and the consumer indexes by
    int. So dicts and tuples are tagged rather than flattened."""
    if isinstance(o, dict):
        return {"__d__": [[_enc(k), _enc(v)] for k, v in o.items()]}
    if isinstance(o, tuple):
        return {"__t__": [_enc(x) for x in o]}
    if isinstance(o, list):
        return [_enc(x) for x in o]
    return o


def _dec(o):
    if isinstance(o, dict):
        if "__d__" in o:
            return {_dec(k): _dec(v) for k, v in o["__d__"]}
        if "__t__" in o:
            return tuple(_dec(x) for x in o["__t__"])
    if isinstance(o, list):
        return [_dec(x) for x in o]
    return o


def _path(key: str) -> str:
    return os.path.join(ROOT, key[:2], key + ".json")


# --- D-REFAGE (2026-08-29): entries EXPIRE ----------------------------------
# 🔴 THE HAZARD WAS NEVER DISK, IT WAS STALENESS. A well-formed but WRONG
# reference reading -- taken while the reference machine misbehaved in a way
# `storable()` does not catch -- was frozen FOREVER, because nothing ever
# re-measured it and nothing scheduled `ZEROBAS_REFCACHE=verify`.
# 🎯 AN AGE CAP DOES NOT DETECT A BAD READING; it BOUNDS HOW LONG ONE CAN SURVIVE,
# which is the honest thing to claim for it. After MAX_AGE_DAYS an entry reads as
# a MISS and is re-measured against the live machine -- self-healing, needing no
# scheduling and no operator step. `rm -rf` stops being the recovery procedure.
# ⚠️ Deliberately NOT a random re-verify sample: a probe that re-measures a
# different subset on every run makes its own wall-clock unpredictable, and this
# cache exists to make repeats cheap.
MAX_AGE_DAYS = float(os.environ.get("ZEROBAS_REFCACHE_MAX_AGE_DAYS", "14"))
_MAX_AGE = MAX_AGE_DAYS * 86400.0


def _age(path: str, now: float | None = None) -> float:
    """Seconds since the entry was written. -1 when it cannot be told.

    🔴 `now` IS NOT A TEST HOOK, IT IS THE FIX. Reading the clock afresh per
    call makes every age relative to a DIFFERENT instant, and `maintain` walks
    the store twice -- once to prune, once to report. An entry at cap minus a
    hair survives the prune and is over the cap when the report measures it, so
    the gate fails ITSELF (D-REFRACE, TODO).""" 
    try:
        t = time.time() if now is None else now
        return max(0.0, t - os.path.getmtime(path))
    except OSError:
        return -1.0


def expired(path: str, now: float | None = None) -> bool:
    """An entry older than the cap. A cap of 0 or less disables expiry."""
    if _MAX_AGE <= 0:
        return False
    a = _age(path, now)
    return a >= 0 and a > _MAX_AGE


def load(key: str):
    """-> (result, settle) or (None, None)."""
    path = _path(key)
    if expired(path):
        # Read as a MISS, so the caller re-measures against the live machine.
        STATS["expired"] += 1
        return None, None
    try:
        with open(path, "r") as fh:
            d = json.load(fh)
        return d["result"], _dec(d.get("settle")) if d.get("settle") else None
    except (OSError, ValueError, KeyError):
        return None, None


# 🔴 WHAT THE LAST prune() COULD NOT DELETE, AND WHY THAT NEEDED A NAME.
# `except OSError: kept += 1` counted a FAILED unlink as a kept entry, which is
# indistinguishable from a legitimately young one -- so an over-cap entry that
# cannot be removed makes `maintain()` go red while reporting only "an entry
# survived the prune", with no path, no age and no hint that a delete FAILED.
# D-REFDIAG reproduced exactly that on demand (a read-only parent directory) and
# could not reproduce the failure actually filed, so the deliverable is to make
# the NEXT occurrence explain itself rather than to guess at the last one.
# A list of (path, age_seconds, errno-ish string); reset at the start of a prune.
PRUNE_FAILED: list = []


def prune(max_age_days: float | None = None,
          now: float | None = None) -> tuple[int, int]:
    """Delete every entry past the cap. -> (removed, kept). Disk is the SECOND
    reason this exists; the first is that an expired entry left on disk is a
    stale reading waiting for the cap to be raised.

    Entries that were over the cap and could NOT be unlinked are counted in
    `kept` (the return shape is unchanged) AND recorded in `PRUNE_FAILED`, so
    the caller can say WHICH entry defeated it."""
    limit = _MAX_AGE if max_age_days is None else max_age_days * 86400.0
    removed = kept = 0
    PRUNE_FAILED.clear()
    for dirpath, _dirs, files in os.walk(ROOT):
        for fn in files:
            if not fn.endswith(".json"):
                continue
            fp = os.path.join(dirpath, fn)
            a = _age(fp, now)
            if limit > 0 and a > limit:
                try:
                    os.unlink(fp); removed += 1
                except OSError as e:
                    PRUNE_FAILED.append((fp, a, e.__class__.__name__
                                         + (f"/{e.errno}" if e.errno else "")))
                    kept += 1
            else:
                kept += 1
    return removed, kept


def store_stats(now: float | None = None) -> tuple[int, int, float]:
    """-> (entries, bytes, oldest_age_seconds) over the whole store."""
    n = size = 0
    oldest = 0.0
    for dirpath, _dirs, files in os.walk(ROOT):
        for fn in files:
            if not fn.endswith(".json"):
                continue
            fp = os.path.join(dirpath, fn)
            n += 1
            try:
                size += os.path.getsize(fp)
            except OSError:
                pass
            oldest = max(oldest, _age(fp, now))
    return n, size, oldest


def storable(result) -> bool:
    """Only a COMPLETE set of real readings is worth keeping."""
    if not isinstance(result, list) or not result:
        return False
    for r in result:
        if r is None or not isinstance(r, str) or not r.strip():
            return False
        if any(n in r for n in NON_READINGS):
            return False
    return True


# 🔴 A DISK-WRITING CALL HAS TWO RESULTS, AND A HIT REPLAYED ONLY ONE (2026-11-04).
# run_cases returns the screen; a probe that SAVEs to its diska then reads the
# IMAGE back (savedate, diskfull, putdir, wcache, asave*). Once the media key
# was made content-based those calls began to hit, and six suites reported
# "INSTRUMENT FAULT: the CF-3300 wrote nothing" -- the reference disk was never
# written because nothing ran. So the entry carries every media file the run
# CHANGED, compressed, and a hit writes those bytes back. The key holds the
# pre-run bytes, so replaying the post-run bytes is exact.
def media_snapshot(params: dict) -> dict:
    """{param: (path, sha)} for every media file a call names."""
    out = {}
    for k in MEDIA_PARAMS:
        v = params.get(k)
        if isinstance(v, str) and os.path.isfile(v):
            out[k] = (v, _file_sha(v))
    return out


def media_changes(before: dict) -> dict:
    """{param: base64(zlib(bytes))} for each media file whose bytes changed."""
    import base64
    import zlib
    out = {}
    for k, (path, sha) in before.items():
        if _file_sha(path) != sha:
            with open(path, "rb") as fh:
                out[k] = base64.b64encode(zlib.compress(fh.read(), 9)).decode()
    return out


def load_media(key: str) -> dict:
    try:
        with open(_path(key)) as fh:
            return json.load(fh).get("media") or {}
    except (OSError, ValueError):
        return {}


def replay_media(media: dict, params: dict) -> None:
    import base64
    import zlib
    for k, blob in media.items():
        path = params.get(k)
        if isinstance(path, str):
            with open(path, "wb") as fh:
                fh.write(zlib.decompress(base64.b64decode(blob)))
            STATS["media_replayed"] = STATS.get("media_replayed", 0) + 1


def store(key: str, result, machine: str, settle=None, media=None) -> bool:
    if not storable(result):
        STATS["refused"] += 1
        return False
    d = _path(key)
    os.makedirs(os.path.dirname(d), exist_ok=True)
    # atomic: temp file in the SAME dir, then replace. 8-wide batteries share
    # this tree and a partially-written entry would be read as a short answer.
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(d), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump({"key": key, "machine": machine, "result": result,
                       "settle": _enc(settle) if settle else None,
                       "media": media or None}, fh)
        os.replace(tmp, d)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return False
    STATS["store"] += 1
    return True


def summary() -> str:
    s = _totals()
    # 🔴 THIS GUARD USED TO OMIT verify_ok AND store, WHICH SILENCED THE TALLY IN
    # EXACTLY THE RUN THAT NEEDED IT. A `verify` battery where every entry AGREES
    # increments only verify_ok -- so the report said nothing, and "no output"
    # was indistinguishable from "verify never ran". The first verify battery
    # was read as evidence on that silence; it was not evidence of anything until
    # this line listed every counter.
    if not any(s[k] for k in ("hit", "miss", "bypass", "verify_ok",
                              "verify_bad", "store", "refused", "expired",
                              "subject_measured", "subject_served")):
        return ""
    bits = [f"{s['hit']} hit", f"{s['miss']} miss"]
    if VERIFY:
        bits = [f"VERIFY MODE (nothing served; every row re-measured)"] + bits
    if REFS:
        # D-REFSONLY: every battery log says, in one line, how many REFERENCE
        # readings were replayed and that NO zerobas reading was
        bits = ["REFS MODE (references replayed, zerobas measured)",
                f"{s['hit']} REFERENCE reading(s) replayed",
                f"{s['miss']} reference miss",
                f"{s['subject_measured']} zerobas reading(s) MEASURED",
                f"{s['subject_served']} zerobas replayed"]
    elif s["subject_served"]:
        bits.append(f"{s['subject_served']} of the hits were ZEROBAS readings")
    if s["store"]:
        bits.append(f"{s['store']} stored")
    if s["refused"]:
        bits.append(f"{s['refused']} refused (non-reading)")
    if s["replayed"]:
        bits.append(f"{s['replayed']} replayed provenance")
    if s["bypass"]:
        # D-REFBYPASS: a direct launch is bypassed for a REASON (the Tcl reads
        # the host clock, ...), and the reason is the finding
        why = "; ".join(f"{n}x {w}" for w, n in sorted(_BYPASS_WHY.items()))
        bits.append(f"{s['bypass']} bypassed" + (f" ({why})" if why else ""))
    if s["expired"]:
        # Named, not folded into `miss`: an expired entry is a reading this run
        # DELIBERATELY refused to reuse, and that is a different fact from never
        # having had one. [[an-unnamed-outcome-reads-as-no-outcome]]
        bits.append(f"{s['expired']} EXPIRED past {MAX_AGE_DAYS:g}d "
                    f"(re-measured)")
    if VERIFY:
        bits.append(f"{s['verify_ok']} entries CONFIRMED against a fresh reading"
                    f", {s['verify_bad']} MISMATCH")
    return "refcache: " + ", ".join(bits)


def report() -> None:
    """Print the tally. 🔴 A RUN THAT MEASURED NOTHING MUST NOT READ LIKE A RUN
    THAT MEASURED EVERYTHING -- so this is printed even when every row hit."""
    line = summary()
    if line:
        sys.stderr.write(line + "\n")
    _tally_close()


# 🔴 REGISTERED HERE, NOT ASKED OF 200 CALLERS. The first full battery under
# this cache stored 3132 entries and NOT ONE unit log said so, because `report()`
# existed and nothing called it. A cache whose hits are invisible is precisely
# the thing this module's header says must not exist: a run that measured
# nothing reading exactly like a run that measured everything. The chokepoint
# owns its own visibility, the same way it owns its own key.
# [[an-unnamed-outcome-reads-as-no-outcome]] [[one-temp-root]]
import atexit                                                    # noqa: E402
atexit.register(report)


# ===========================================================================
# --- D-REFBYPASS (2026-11-03): the probes that launch openMSX THEMSELVES ----
# ===========================================================================
# 🔴 THE CHOKEPOINT ABOVE WAS NEVER THE ONLY DOOR. `run_cases` is where most
# probes reach the emulator, but 29+ probes in probes/basic/ build their own Tcl
# and spawn openMSX directly (the trap probes, cloadverr, eofcas, keyshift,
# autorun, bootkey, resetboot, ctrlkeys ...), and the omsx_run.py CLI is a
# second shared door used as a subprocess by ten more. None of them cached, so
# every repeat re-booted the VG-8020 and the CF-3300 for answers that cannot
# change. Joost 2026-11-03: "do it before the sub2 rereads, it'll save time
# every next test run".
#
# `cached_run()` is the same contract as `run_cases` with a different unit:
# ONE openMSX LAUNCH. The caller keeps its own spawn (its guarded() Popen, its
# watchdog, its kill signal) inside the `run` callable it hands over -- the
# cache never spawns anything itself, so every launch still goes through
# omsx_preflight.guarded() at the line tools/check_probe_preflight.py checks.
#
# ═══ THE KEY ═══
#   * machine_identity(the -machine argument): XML + every ROM it names, by
#     content. 🎯 For the REPACK machines the XML names build/*.rom by ABSOLUTE
#     path (tools/install-repack-machine.py), so a rebuild changes the key; the
#     selftest arm KD-R checks that every repo-built filename is absolute and
#     present, because a relative or missing one hashes as "ABSENT" and would
#     make zerobas's key BUILD-INDEPENDENT -- the one wrong hit that matters.
#   * the argv, and the text of every -script, with each per-run path replaced
#     by a placeholder: the declared outputs (<OUTn>), the scripts themselves
#     (<SCRIPTn>), and every input file (<MEDIAn>). Without that every key is
#     unique (mkstemp names, the per-process probe_tmp directory).
#   * sha256 of every input file: every argv token that is an existing file
#     (-diska, -cassetteplayer, -cart, -setting ...) AND every absolute path in
#     the Tcl / -command text that exists before the run (a `cassetteplayer
#     insert {...}`, a `diska {...}`, an `open {...} r`). 🎯 AUTO-DETECTED, not
#     declared: a probe that forgot to declare a tape would otherwise get the
#     OLD tape's answer. A path that is not a file yet (an undeclared output)
#     stays in the key VERBATIM -- so the failure mode of an incomplete
#     normalisation is a key that never repeats, i.e. a MISS, never a wrong hit.
#   * the user's ~/.openMSX/share/settings.xml and share/scripts/ (openMSX reads
#     both at startup; READ for the key, never written), unless -setting names
#     another settings file (then that file is an input like any other).
#   * every -ext NAME's extension XML, by identity_of_xml; an -ext that cannot
#     be resolved makes the run UNCACHEABLE.
#   * direct_fingerprint(): harness_fingerprint() (omsx_repl, omsx_run,
#     omsx_preflight, the emulator build) + THIS file's bytes, because the key
#     and the replay are now part of how a direct reading is taken -- and the
#     identity of the binary argv[0] names when it is not the default one.
#
# ═══ NEVER CACHED (counted as `bypassed`) ═══
#   A Tcl / -command text that reads the HOST: `clock ...`, `rand()`/`srand`,
#   `after realtime` (fires on the wall clock), `exec`, `glob`, `env(`. openMSX
#   is deterministic in EMULATED time; those are the ways a script can make its
#   output depend on something else. A directory passed as media (dir-as-disk)
#   is not hashed and so not cached either.
#
# ═══ THE SAME THREE RULES ═══
#   ALL-OR-NOTHING per launch: every declared output is stored and replayed.
#   A NON-READING IS NEVER STORED: every output must exist and be non-empty,
#   and must not contain <NO OUTPUT>/<NO CAPTURE>; an `ok(value)` predicate
#   lets the caller veto (a watchdog TIMEOUT whose output may be partial).
#   VERIFY runs for real and compares byte-for-byte with the stored outputs.
#   And the D-CACHEPRE staleness guard runs on the HIT path, exactly as in
#   run_cases: a hit never launches, so it never reached guarded().

_NONDET = (
    ("clock", re.compile(r"\bclock\s+(seconds|milliseconds|microseconds|clicks|format|scan)\b")),
    ("rand()", re.compile(r"\bs?rand\s*\(")),
    ("after realtime", re.compile(r"\bafter\s+realtime\b")),
    ("exec", re.compile(r"(^|[\s\[;{])exec\s")),
    ("glob", re.compile(r"(^|[\s\[;{])glob\s")),
    ("env()", re.compile(r"\benv\(")),
)
_PATH_RE = re.compile(r"(/[^\s{}\"'\[\];]+)")
OMSX_USER_SETTINGS = os.path.expanduser("~/.openMSX/share/settings.xml")
OMSX_USER_SCRIPTS = os.path.expanduser("~/.openMSX/share/scripts")
# a direct entry's outputs above this many bytes are not stored (a recorded WAV
# can be tens of MB; the store is JSON)
DIRECT_MAX_BYTES = 16 * 1024 * 1024

_DIRECT_FP: str | None = None


def direct_fingerprint() -> str:
    """harness_fingerprint() plus this file: for a direct launch the key-builder
    and the replay ARE part of the instrument (the D-REFBYPASS brief)."""
    global _DIRECT_FP
    if _DIRECT_FP is None:
        _DIRECT_FP = _sha((harness_fingerprint() + "\n").encode()
                          + open(os.path.abspath(__file__), "rb").read())
    return _DIRECT_FP


_EMU_OF: dict[str, str] = {}


def _emu_of(exe: str) -> str:
    """The identity of argv[0]. The default binary is already in
    harness_fingerprint(); any OTHER one (an --omsx override) gets its own
    `-v`, so a reading taken by a different build can never be served."""
    path = exe if os.path.sep in exe else (shutil.which(exe) or exe)
    real = os.path.realpath(path)
    dflt = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
    if real == os.path.realpath(dflt):
        return "default"
    if real not in _EMU_OF:
        try:
            out = subprocess.run([real, "-v"], capture_output=True, text=True,
                                 timeout=30).stdout
            _EMU_OF[real] = out.splitlines()[0].strip() if out.strip() else ""
        except (OSError, subprocess.SubprocessError):
            _EMU_OF[real] = ""
        if not _EMU_OF[real]:
            _EMU_OF[real] = "UNREADABLE:" + os.urandom(8).hex()
    return _EMU_OF[real]


def _dir_sha(d: str) -> str:
    if not os.path.isdir(d):
        return "ABSENT"
    parts = []
    for dirpath, _dirs, files in sorted(os.walk(d)):
        for fn in sorted(files):
            fp = os.path.join(dirpath, fn)
            parts.append(f"{os.path.relpath(fp, d)}:{_file_sha(fp)}")
    return _sha("\n".join(parts).encode())


def _variants(p: str) -> list[str]:
    """A path as a script may spell it: as given, absolute, and resolved
    (macOS /tmp is /private/tmp)."""
    out = []
    for v in (p, os.path.abspath(p), os.path.realpath(p)):
        if v and v not in out:
            out.append(v)
    return out


def direct_key(cmd, outs, inouts=(), media=()):
    """-> (key, None) or (None, reason-it-is-uncacheable).

    Pure function of the launch's INPUTS (see the section header): it never
    looks at what the run produced."""
    argv = [str(a) for a in cmd]
    if "-machine" not in argv or argv.index("-machine") + 1 >= len(argv):
        return None, "no -machine in argv"
    machine = argv[argv.index("-machine") + 1]
    scripts = [argv[j + 1] for j, a in enumerate(argv)
               if a == "-script" and j + 1 < len(argv)]
    texts = []
    for s in scripts:
        try:
            texts.append(open(s, encoding="utf-8", errors="surrogateescape").read())
        except OSError:
            return None, f"-script {s} unreadable"
    commands = [argv[j + 1] for j, a in enumerate(argv)
                if a == "-command" and j + 1 < len(argv)]
    for t in texts + commands:
        for why, rx in _NONDET:
            if rx.search(t):
                return None, f"the Tcl reads the host ({why})"

    # every per-run path -> a placeholder; inputs also -> their content hash
    subst: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(p, ph):
        for v in _variants(p):
            if v not in seen:
                seen.add(v)
                subst.append((v, ph))

    for i, p in enumerate(outs):
        add(p, f"<OUT{i}>")
    for i, p in enumerate(inouts):
        add(p, f"<INOUT{i}>")
    for i, p in enumerate(scripts):
        add(p, f"<SCRIPT{i}>")
    cands = list(media)
    for j, a in enumerate(argv[1:], 1):
        if argv[j - 1] in ("-script",) or a in seen:
            continue
        if os.path.isdir(a) and argv[j - 1].startswith("-"):
            return None, f"a directory is passed as media ({a}); its content is not hashed"
        if os.path.isfile(a):
            cands.append(a)
    for t in texts + commands:
        cands += [m for m in _PATH_RE.findall(t) if os.path.isfile(m)]
    media_sha = []
    for p in cands:
        if any(v in seen for v in _variants(p)):
            continue
        add(p, f"<MEDIA{len(media_sha)}>")
        media_sha.append(_file_sha(p))
    inout_sha = [_file_sha(p) for p in inouts]
    subst.sort(key=lambda kv: -len(kv[0]))       # longest first: no prefix clash

    def norm(s: str) -> str:
        for v, ph in subst:
            s = s.replace(v, ph)
        return s

    exts = []
    for j, a in enumerate(argv):
        if a == "-ext" and j + 1 < len(argv):
            name = argv[j + 1]
            found = None
            for root in (os.path.expanduser("~/.openMSX/share/extensions"),
                         *[os.path.join(s, "extensions") for s in _share_dirs()]):
                c = os.path.join(root, name + ".xml")
                if os.path.exists(c):
                    found = c
                    break
            if found is None:
                return None, f"-ext {name} does not resolve to an extension XML"
            exts.append(f"{name}:{identity_of_xml(found)}")
    settings = ("given" if "-setting" in argv
                else _file_sha(OMSX_USER_SETTINGS))
    payload = {
        "v": 1, "kind": "direct",
        "machine_id": machine_identity(machine),
        "harness": direct_fingerprint(),
        "emu": _emu_of(argv[0]),
        "argv": [norm(a) for a in argv[1:]],
        "scripts": [norm(t) for t in texts],
        "media": media_sha, "inouts": inout_sha, "ext": exts,
        "settings": settings, "user_scripts": _dir_sha(OMSX_USER_SCRIPTS),
        "outs": len(outs),
    }
    return _sha(json.dumps(payload, sort_keys=True).encode()), None


def _share_dirs() -> list[str]:
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "tools"))
    try:
        import openmsx_paths as P
        return list(getattr(P, "SHARE_CANDIDATES", []))
    except Exception:
        return []


def _read_outs(paths) -> list[bytes] | None:
    got = []
    for p in paths:
        try:
            with open(p, "rb") as fh:
                got.append(fh.read())
        except OSError:
            return None
    return got


def direct_storable(blobs) -> bool:
    """Every declared output exists, is non-empty, holds no non-reading."""
    if blobs is None or not blobs:
        return False
    if sum(len(b) for b in blobs) > DIRECT_MAX_BYTES:
        return False
    for b in blobs:
        if not b.strip():
            return False
        if any(n.encode() in b for n in NON_READINGS):
            return False
    return True


def _direct_load(key: str):
    path = _path(key)
    if expired(path):
        STATS["expired"] += 1
        return None
    try:
        with open(path) as fh:
            d = json.load(fh)
        if d.get("kind") != "direct":
            return None
        return [base64.b64decode(x) for x in d["outs"]]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _direct_store(key: str, blobs, machine: str) -> bool:
    if not direct_storable(blobs):
        STATS["refused"] += 1
        return False
    d = _path(key)
    os.makedirs(os.path.dirname(d), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(d), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump({"key": key, "kind": "direct", "machine": machine,
                       "outs": [base64.b64encode(b).decode() for b in blobs]}, fh)
        os.replace(tmp, d)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return False
    STATS["store"] += 1
    return True


def _hit_preflight(cmd) -> None:
    """D-CACHEPRE on the direct hit path (see run_cases): a hit never launches,
    so it would otherwise never reach guarded()'s stale-ROM refusal. A
    function of its own so the selftest can drive a planted machine."""
    import omsx_preflight
    omsx_preflight.guard_cmd(list(cmd))


def cached_run(cmd, outs, run, *, inouts=(), media=(), ok=None):
    """Run ONE openMSX launch through the reference store.

    cmd     the argv the caller is about to spawn, BEFORE guarded() (guarded's
            own additions are a function of omsx_preflight.py, which is in the
            fingerprint)
    outs    every file the run writes that the caller reads afterwards. They
            are DELETED before a real run, so a stale file from an earlier call
            can never be stored as this run's reading.
    inouts  files that are both an input and an output (a disk the run SAVEs
            onto): hashed BEFORE the run for the key, stored AFTER, never
            deleted
    run     a zero-argument callable doing the real spawn (guarded Popen +
            watchdog); its return value is handed back on a miss
    media   extra input files to hash (inputs are auto-detected too)
    ok      ok(value) -> False vetoes the store (e.g. a watchdog timeout)

    -> (served_from_cache: bool, value). value is None on a hit.
    """
    if not ENABLED:
        return False, run()
    _argv = [str(a) for a in cmd]
    _m = _argv[_argv.index("-machine") + 1] if "-machine" in _argv[:-1] else "?"
    _files = [a for a in _argv[1:] if os.path.isfile(a)] + list(media)
    if subject_bypass(_m, _files):
        # D-REFSONLY: zerobas is measured, never loaded and never stored
        return False, run()
    key, why = direct_key(cmd, outs, inouts, media)
    if key is None:
        STATS["bypass"] += 1
        _BYPASS_WHY.setdefault(why, 0)
        _BYPASS_WHY[why] += 1
        return False, run()
    # 🔴 A REPEAT INSIDE ONE PROCESS IS A DELIBERATE RE-MEASUREMENT, NOT A
    # REPEAT TO SKIP. stop-trap runs every case `--trials 2` times and asserts
    # the verdict is "robust across 2 trials"; the first cut of this function
    # served trial 1 from trial 0's fresh entry (measured: run 1 of
    # stop-trap-acceptance logged `16 hit, 16 miss` on an EMPTY store), so the
    # second trial measured nothing while the log still claimed two. So the
    # n-th identical launch of a process gets its own key: every stored reading
    # was measured once, separately, and a later process replays trial 1 from
    # trial 1's own measurement. [[a-case-that-agrees-can-agree-for-the-wrong-reason]]
    n = _OCCURRENCE.get(key, 0)
    _OCCURRENCE[key] = n + 1
    if n:
        key = _sha(f"{key}#{n}".encode())
    argv = [str(a) for a in cmd]
    machine = argv[argv.index("-machine") + 1]
    stored = _direct_load(key)
    if stored is not None and len(stored) == len(outs) + len(inouts) \
            and not VERIFY:
        refuse_subject_hit(machine, _files)
        _hit_preflight(cmd)
        for p, b in zip(list(outs) + list(inouts), stored):
            with open(p, "wb") as fh:
                fh.write(b)
        STATS["hit"] += 1
        return True, None
    for p in outs:
        try:
            os.unlink(p)
        except OSError:
            pass
    value = run()
    blobs = _read_outs(list(outs) + list(inouts))
    if VERIFY and stored is not None and len(stored) == len(outs) + len(inouts):
        if blobs == stored:
            STATS["verify_ok"] += 1
        else:
            STATS["verify_bad"] += 1
            bad = [i for i in range(len(stored))
                   if blobs is None or i >= len(blobs) or blobs[i] != stored[i]]
            sys.stderr.write(
                f"🔴 refcache VERIFY MISMATCH on {machine} (direct launch): "
                f"output(s) {bad} differ between the stored reading and a fresh "
                f"one. The store is WRONG or the machine moved; key {key[:12]}\n")
    else:
        STATS["miss"] += 1
    if ok is not None and not ok(value):
        STATS["refused"] += 1
        return False, value
    _direct_store(key, blobs, machine)
    return False, value


_BYPASS_WHY: dict[str, int] = {}
_OCCURRENCE: dict[str, int] = {}


# --- the tally of CHILD processes -------------------------------------------
# 🔴 omsx_run.py RUNS AS A SUBPROCESS, so its hits were counted in a process
# whose stderr most callers send to DEVNULL -- a cache whose hits are invisible
# is what this module's header says must not exist. The first process to
# import this module names a tally file in the environment; every descendant
# that imports it appends its counters there at exit, and the owner folds them
# into its own summary. The owner deletes the file; a descendant opens it
# WITHOUT O_CREAT, so one outliving its parent leaks nothing.
_TALLY_ENV = "ZEROBAS_REFCACHE_TALLY"
_TALLY_OWNER = False
if not os.environ.get(_TALLY_ENV):
    try:
        _fd, _tp = tempfile.mkstemp(prefix=f"refcache_tally_{os.getpid()}_",
                                    suffix=".txt")
        os.close(_fd)
        os.environ[_TALLY_ENV] = _tp
        _TALLY_OWNER = True
    except OSError:
        pass


def _totals() -> dict:
    s = dict(STATS)
    if _TALLY_OWNER:
        try:
            with open(os.environ.get(_TALLY_ENV, ""), "r") as fh:
                for ln in fh:
                    try:
                        for k, v in json.loads(ln).items():
                            if k in s:
                                s[k] += int(v)
                    except (ValueError, TypeError, AttributeError):
                        pass
        except OSError:
            pass
    return s


def _tally_close() -> None:
    path = os.environ.get(_TALLY_ENV, "")
    if not path:
        return
    if _TALLY_OWNER:
        try:
            os.unlink(path)
        except OSError:
            pass
        return
    if not any(STATS.values()):
        return
    try:
        fd = os.open(path, os.O_WRONLY | os.O_APPEND)
    except OSError:
        return
    try:
        os.write(fd, (json.dumps(STATS) + "\n").encode())
    finally:
        os.close(fd)


# ===========================================================================
# --- SELFTEST: every way a cache can lie, planted and shown to fail --------
# ===========================================================================
def _selftest() -> int:
    r"""🔴 A CACHE IS TRUSTED ONLY AS FAR AS ITS WRONG-HIT ARMS ACTUALLY FIRE.

    Each arm below PLANTS the difference and asserts a MISS. An arm that passes
    because the two inputs were never really different is not an arm -- so every
    one prints the two keys it compared, and K0 is the green control that says
    identical inputs really do produce a hit on this same apparatus.
    """
    import shutil
    fails = []

    def arm(name, cond, detail=""):
        print(f"{'PASS' if cond else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")
        if not cond:
            fails.append(name)

    M = "Philips_VG_8020"
    CASES = [("direct", ["NEW", 'PRINT "HI"'])]
    P = dict(batch=False, reset=("NEW",), capture="screen", holds=None,
             hold_secs=12.0, prologue=(), boot=8.0, step=8.0, cap_gap=10.0,
             timeout=300.0, omsx=None, cart=None, diska=None,
             verify_delivery=True, run_gap=None, sentinel=None,
             sentinel_capture=False)
    k0 = key_for(M, CASES, P)

    # --- K0 GREEN CONTROL: identical inputs -> the SAME key --------------
    arm("K0 identical inputs give the same key (green control)",
        key_for(M, CASES, P) == k0, k0[:12])

    # --- K1 one character of one typed line ------------------------------
    k = key_for(M, [("direct", ["NEW", 'PRINT "HJ"'])], P)
    arm("K1 one character of a typed line -> MISS", k != k0, f"{k0[:8]} vs {k[:8]}")

    # --- K2 an extra line ------------------------------------------------
    k = key_for(M, [("direct", ["NEW", 'PRINT "HI"', "END"])], P)
    arm("K2 an extra typed line -> MISS", k != k0, f"{k0[:8]} vs {k[:8]}")

    # --- K3 a delivery parameter -----------------------------------------
    for field, val in (("batch", True), ("reset", ("CLS",)), ("boot", 9.0),
                       ("capture", "text"), ("sentinel_capture", True)):
        p2 = dict(P); p2[field] = val
        k = key_for(M, CASES, p2)
        arm(f"K3 param {field!r} -> MISS", k != k0, f"{k0[:8]} vs {k[:8]}")

    # --- K4 THE MACHINE'S BYTES, not its name ----------------------------
    # plant a machine XML naming a ROM, then change ONE BYTE of that ROM.
    tmp = tempfile.mkdtemp(prefix="refcache-selftest-")
    try:
        rom = os.path.join(tmp, "fake.rom")
        open(rom, "wb").write(b"\x00" * 64)
        xml = os.path.join(tmp, "Fake_Machine.xml")
        open(xml, "w").write(
            f"<msxconfig><machine><devices><primary><ROM><rom>"
            f"<filename>{rom}</filename></rom></ROM></primary>"
            f"</devices></machine></msxconfig>")
        a = identity_of_xml(xml)
        open(rom, "wb").write(b"\x00" * 63 + b"\x01")     # ONE byte
        b = identity_of_xml(xml)
        arm("K4 one byte of a ROM the machine names -> different identity",
            a != b, f"{a[:8]} vs {b[:8]}")
        # and the same bytes give the same identity (the control for K4)
        open(rom, "wb").write(b"\x00" * 64)
        arm("K4b restoring the ROM restores the identity (control)",
            identity_of_xml(xml) == a, a[:12])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # --- K5 the instrument -----------------------------------------------
    global _HARNESS
    saved, _HARNESS = _HARNESS, "PRETEND-THE-HARNESS-CHANGED"
    k = key_for(M, CASES, P)
    _HARNESS = saved
    arm("K5 a changed harness fingerprint -> MISS", k != k0, f"{k0[:8]} vs {k[:8]}")
    # K5e the EMULATOR is part of the instrument (2026-10-28): a different openMSX
    # build must change the fingerprint itself, not only a planted one
    global _EMU
    saved_h, saved_e = _HARNESS, _EMU
    _HARNESS = None
    h_real = harness_fingerprint()
    _HARNESS, _EMU = None, "openMSX 0.0-PRETEND-ANOTHER-BUILD"
    h_other = harness_fingerprint()
    _HARNESS, _EMU = saved_h, saved_e
    arm("K5e another openMSX build -> a different harness fingerprint -> MISS",
        h_other != h_real, f"{h_real[:8]} vs {h_other[:8]}")

    # --- K6 a non-reading is never stored --------------------------------
    for bad, why in ((None, "None"), ([], "empty list"), ([None], "[None]"),
                     ([""], "empty string"), (["  "], "blank"),
                     (["x <NO OUTPUT> y"], "<NO OUTPUT>"),
                     (["<NO CAPTURE>"], "<NO CAPTURE>"),
                     (["ok", None], "one good one None")):
        arm(f"K6 refuse to store {why}", not storable(bad))
    arm("K6b a real reading IS storable (control)", storable(["READY", "OK"]))

    # --- K7 round trip ---------------------------------------------------
    global ROOT
    saved_root, ROOT = ROOT, tempfile.mkdtemp(prefix="refcache-rt-")
    try:
        val = ["line one\nline two", "second case"]
        settle = {"sentinel": {0: 56.0, 1: 80.125}, "fallback": {},
                  "marks": {0: [(56.0, 255)]}, "span": {0: (1.5, 9.0)}}
        store("deadbeef" * 8, val, M, settle=settle)
        got, gs = load("deadbeef" * 8)
        arm("K7 store -> load round-trips the result exactly", got == val)
        # 🔴 INT KEYS AND TUPLES, NOT "3" AND [3]. The consumer indexes settle_out
        # by int and unpacks tuples; plain JSON would hand back strings and lists
        # and the tally would read empty while looking fine.
        arm("K7b settle_out round-trips int keys and tuples exactly", gs == settle,
            f"{gs}")
        arm("K7c an unknown key loads as (None, None)", load("f0" * 32) == (None, None))
        # a result stored WITHOUT settle must not be served to a caller that
        # wants one -- otherwise the caller gets an empty dict and under-counts
        store("cafe" * 16, val, M, settle=None)
        arm("K7d a settle-less entry stores no provenance",
            load("cafe" * 16)[1] is None)

        # --- K8 concurrent writers never yield a torn read ---------------
        import threading
        keys = [f"{i:064x}" for i in range(24)]
        payload = ["A" * 4000]
        ths = [threading.Thread(target=store, args=(k, payload, M)) for k in keys]
        for t in ths:
            t.start()
        for t in ths:
            t.join()
        torn = [k for k in keys if load(k)[0] != payload]
        arm("K8 24 concurrent writers, 0 torn reads", not torn,
            f"torn: {torn[:3]}" if torn else "")
    finally:
        shutil.rmtree(ROOT, ignore_errors=True)
        ROOT = saved_root

    # --- K9 THE VERIFY MODE, END TO END ON A REAL MACHINE ----------------
    # 🎯 EVERY ARM ABOVE IS PURE ARITHMETIC ON KEYS. This one plants a WRONG
    # answer in the store and shows that `ZEROBAS_REFCACHE=verify` catches it
    # against a real emulator reading -- which is the only thing that says the
    # store can be trusted after it has been sitting on disk for a month.
    # 🔴 RUN AS `__main__`, THIS FILE IS NOT THE MODULE omsx_repl IMPORTS.
    # `python3 probe_refcache.py --selftest` binds this code as `__main__`, and
    # omsx_repl's `import probe_refcache` then creates a SECOND, independent
    # module object. The first cut of K9 set VERIFY/ROOT on one instance while
    # the wrapper read the other, and the arm reported "did not fire" -- which
    # would have read as "the cache cannot be falsified" when it was really two
    # copies of the instrument. Bind the IMPORTED one explicitly.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import probe_refcache as RC          # the instance omsx_repl will use
    print(f"NOTE  K9 binds the IMPORTED module instance "
          f"({'same object' if RC.STATS is STATS else 'DISTINCT from __main__'})"
          f" -- see the comment above; this is a statement of fact, not an arm.")
    saved_root, RC.ROOT = RC.ROOT, tempfile.mkdtemp(prefix="refcache-verify-")
    saved_verify, RC.VERIFY = RC.VERIFY, True
    # 🔴 AND `ENABLED` TOO. The battery forced ZEROBAS_REFCACHE=0 for every
    # unit (a gate measures, it never replays -- spec-refcache.md §6; `refs`
    # since D-REFSONLY, which leaves ENABLED on), which
    # made this gate's own K9 arms go dark: run_cases bypassed the module
    # entirely, so the tamper could not be caught and the arm reported "did not
    # fire". The suite must drive the module it is testing rather than inherit
    # the environment's opinion of whether that module is switched on.
    saved_enabled, RC.ENABLED = RC.ENABLED, True
    try:
        import omsx_repl
        CASE = [("direct", ["NEW", 'PRINT "REFCACHE"'])]
        KW = dict(batch=False, boot=8.0, step=8.0, cap_gap=10.0, timeout=300.0)
        real = omsx_repl.run_cases(M, CASE, **KW)
        arm("K9a a real reading came back", bool(real and real[0]),
            (real[0][:40] if real and real[0] else "NOTHING"))
        import inspect
        b = inspect.signature(omsx_repl._run_cases_impl).bind(M, CASE, **KW)
        b.apply_defaults()
        a2 = dict(b.arguments); a2.pop("machine"); a2.pop("cases"); a2.pop("settle_out", None)
        k = RC.key_for(M, CASE, a2)
        # 🟢 GREEN CONTROL WITH TEETH: re-run against the entry just stored and
        # require an ACTUAL agreement (verify_ok incremented), not merely the
        # absence of a mismatch -- "0 bad" is also what a VERIFY that never ran
        # would report. [[a-case-that-agrees-can-agree-for-the-wrong-reason]]
        omsx_repl.run_cases(M, CASE, **KW)
        arm("K9b VERIFY agreed with the untampered entry (green control)",
            RC.STATS["verify_ok"] >= 1, f"verify_ok={RC.STATS['verify_ok']}")
        RC.store(k, ["A DELIBERATE LIE"], M)           # tamper
        before = RC.STATS["verify_bad"]
        omsx_repl.run_cases(M, CASE, **KW)
        arm("K9c VERIFY caught a tampered entry (the arm that matters)",
            RC.STATS["verify_bad"] == before + 1,
            f"verify_bad {before} -> {RC.STATS['verify_bad']}")
    except Exception as e:                       # an emulator-less host
        print(f"SKIP  K9 end-to-end verify: {type(e).__name__}: {e}")
    finally:
        RC.VERIFY, RC.ENABLED = saved_verify, saved_enabled
        shutil.rmtree(RC.ROOT, ignore_errors=True)
        RC.ROOT = saved_root

    # --- D-REFAGE: expiry, prune, and the store readout --------------------
    saved_root = RC.ROOT
    RC.ROOT = tempfile.mkdtemp(prefix="refage-")
    try:
        RC.store("a" * 40, ["r1"], "M")
        p_fresh = RC._path("a" * 40)
        arm("KA1 a FRESH entry is not expired (the green control -- without it "
            "every arm below passes on a store that simply never wrote)",
            os.path.exists(p_fresh) and not RC.expired(p_fresh))
        arm("KA2 a fresh entry LOADS", RC.load("a" * 40)[0] == ["r1"])

        old_t = time.time() - (RC.MAX_AGE_DAYS + 1) * 86400
        os.utime(p_fresh, (old_t, old_t))
        arm("KA3 an entry past the cap reads as EXPIRED", RC.expired(p_fresh))
        before = RC.STATS["expired"]
        arm("KA4 🔴 THE ARM THAT MATTERS: an expired entry LOADS AS A MISS, so "
            "the caller re-measures against the live machine",
            RC.load("a" * 40)[0] is None)
        arm("KA5 and the refusal is COUNTED, not silent",
            RC.STATS["expired"] == before + 1)
        arm("KA6 the summary NAMES the expiry rather than folding it into miss",
            "EXPIRED" in RC.summary())

        n, _sz, oldest = RC.store_stats()
        arm("KA7 store_stats sees the entry and its age", n == 1 and oldest > 0)
        removed, kept = RC.prune()
        arm("KA8 prune deletes the expired entry", (removed, kept) == (1, 0))

        RC.store("b" * 40, ["r2"], "M")
        removed, kept = RC.prune()
        arm("KA9 prune KEEPS a fresh entry (negative control -- a prune that "
            "deletes everything would pass KA8)", (removed, kept) == (0, 1))

        saved_max = RC._MAX_AGE
        RC._MAX_AGE = 0
        os.utime(RC._path("b" * 40), (old_t, old_t))
        arm("KA10 a cap of 0 DISABLES expiry (the escape hatch works)",
            not RC.expired(RC._path("b" * 40)))
        RC._MAX_AGE = saved_max

        # --- D-REFRACE: maintain must not race its own post-condition -------
        for fn in os.listdir(RC.ROOT):
            fp = os.path.join(RC.ROOT, fn)
            if os.path.isfile(fp):
                os.unlink(fp)
        RC.store("c" * 40, ["r3"], "M")
        edge = RC._path("c" * 40)
        # plant it a HAIR under the cap: survives a prune taken now, and is
        # over the cap a second later. This is the real store's situation on
        # the day an entry ages out mid-battery.
        t_now = time.time()
        os.utime(edge, (t_now - RC._MAX_AGE + 0.5, t_now - RC._MAX_AGE + 0.5))
        arm("KA11 GREEN CONTROL (and only that): maintain() is green on an "
            "entry under the cap. 🔴 IT PASSES WITH OR WITHOUT THE ONE-CLOCK "
            "FIX -- a mutation reverting `prune(now=now)` left it PASSING -- "
            "because the real gap between the two walks is microseconds and "
            "this fixture plants half a second of margin. Named for what it "
            "is; KA12 is the arm with content.", RC.maintain(now=t_now) == 0)
        arm("KA12 🔴 THE ARM WITH CONTENT: measure the post-condition a second "
            "LATER than the prune -- the shape the code had before D-REFRACE -- "
            "and the SAME store goes RED. That is what makes `maintain` capable "
            "of failing ITSELF on the calendar, and why one clock reading is "
            "now threaded through both walks.",
            RC.maintain(now=t_now, stats_now=t_now + 1.0) == 1)
        arm("KA13 and a genuinely over-cap entry is still PRUNED, so KA11 did "
            "not buy its green by disabling expiry",
            (os.utime(edge, (t_now - RC._MAX_AGE * 3, t_now - RC._MAX_AGE * 3)),
             RC.maintain(now=t_now, stats_now=t_now,
                         ) == 0)[1] and not os.path.exists(edge))
        # --- D-REFDIAG: the one-clock fix finally has a COVERING arm ---------
        # 🔴 KA11 AND KA12 DO NOT COVER IT, AND A MUTATION PROVED THAT. Reverting
        # `prune(now=now)` to `prune()` -- undoing D-REFRACE's entire fix -- left
        # EVERY arm passing: KA11 plants half a second of margin, and KA12 passes
        # `stats_now` by hand so it exercises the SHAPE without ever checking
        # that `maintain` threads its clock into `prune`.
        # This one separates them. Plant an entry 20 days old, then run the whole
        # of `maintain` against a clock 30 days in the PAST. Threading that clock
        # through makes the entry's age NEGATIVE (clamped to 0), so it survives;
        # reading the wall clock inside `prune` makes it 20 days old, so it is
        # deleted. Survival IS the fix.
        for fn in os.listdir(RC.ROOT):
            fp = os.path.join(RC.ROOT, fn)
            if os.path.isfile(fp):
                os.unlink(fp)
        RC.store("e" * 40, ["r5"], "M")
        ent = RC._path("e" * 40)
        t20 = time.time() - 20 * 86400
        os.utime(ent, (t20, t20))
        past = time.time() - 30 * 86400
        RC.maintain(now=past, stats_now=past)
        arm("KA15 🔴 THE ARM THAT COVERS D-REFRACE: maintain() threads ITS clock "
            "into prune(), so an entry that is 'not yet written' at that clock "
            "SURVIVES -- revert `prune(now=now)` and this entry is deleted",
            os.path.exists(ent))
        RC.maintain()
        arm("KA15 NEGATIVE: at the REAL clock the same 20-day entry is pruned, "
            "so KA15 is about the clock and not about expiry being broken",
            not os.path.exists(ent))

        # --- D-REFDIAG: a failed unlink must NAME itself ---------------------
        # 🔴 THE ARM THAT MATTERS HERE. `except OSError: kept += 1` made an
        # entry prune COULD NOT DELETE look exactly like a young one, so the
        # gate went red saying only "an entry survived the prune". Reproduced on
        # demand with a read-only parent directory.
        for fn in os.listdir(RC.ROOT):
            fp = os.path.join(RC.ROOT, fn)
            if os.path.isfile(fp):
                os.unlink(fp)
        RC.store("d" * 40, ["r4"], "M")
        stuck = RC._path("d" * 40)
        way_old = time.time() - RC._MAX_AGE * 2
        os.utime(stuck, (way_old, way_old))
        holder = os.path.dirname(stuck)
        mode = os.stat(holder).st_mode
        os.chmod(holder, 0o555)
        try:
            rc_stuck = RC.maintain()
            failed_named = bool(RC.PRUNE_FAILED) and \
                RC.PRUNE_FAILED[0][0] == stuck
        finally:
            os.chmod(holder, mode)
        arm("KA14 an over-cap entry that CANNOT be unlinked makes maintain red "
            "AND is named in PRUNE_FAILED, so the post-mortem has the path",
            rc_stuck == 1 and failed_named)

        removed2, _kept2 = RC.prune()
        arm("KA14 NEGATIVE: once it IS removable the same entry prunes and "
            "PRUNE_FAILED is EMPTY -- so the list means 'could not delete', "
            "not merely 'an over-cap entry existed'",
            removed2 == 1 and not RC.PRUNE_FAILED)
    finally:
        shutil.rmtree(RC.ROOT, ignore_errors=True)
        RC.ROOT = saved_root

    # --- D-REFBYPASS: the DIRECT-launch key (cached_run) -------------------
    # Pure key arithmetic plus a fake `run` -- no emulator -- except KD-R,
    # which reads the REAL installed REPACK machine XML (never its ROM bytes
    # beyond the hash the identity already takes).
    global _machine_xml, _hit_preflight, VERIFY, ENABLED, REFS
    saved_mx, saved_hp = _machine_xml, _hit_preflight
    saved_root, saved_v, saved_en, saved_refs = ROOT, VERIFY, ENABLED, REFS
    REFS = False                        # the KD arms are about mode 1
    tmp = tempfile.mkdtemp(prefix="refbypass-selftest-")
    try:
        rom = os.path.join(tmp, "fake.rom")
        open(rom, "wb").write(b"\x00" * 64)
        mxml = os.path.join(tmp, "Fake_Direct.xml")
        open(mxml, "w").write(
            f"<msxconfig><machine><devices><primary><ROM><rom>"
            f"<filename>{rom}</filename></rom></ROM></primary>"
            f"</devices></machine></msxconfig>")
        zxml = os.path.join(tmp, "zb_plant.xml")      # NAME says zerobas, bytes don't
        open(zxml, "w").write(open(mxml).read())
        rxml = os.path.join(tmp, "ref_plant.xml")     # BYTES say zerobas, name doesn't
        open(rxml, "w").write(
            f"<msxconfig><filename>{os.path.join(REPO, 'build', 'zerobas-main-eu.rom')}"
            f"</filename></msxconfig>")
        plants = {"Fake_Direct": mxml, "C-BIOS_MSX1_EU_REPACK_PLANT": zxml,
                  "Fake_Ref_With_Repo_Rom": rxml}
        _machine_xml = lambda m: plants.get(m) or saved_mx(m)  # noqa: E731
        _hit_preflight = lambda cmd: None                                   # noqa: E731

        def launch(sub, tcl_body="after time 9 {type \"PRINT 1\\r\"}\n",
                   cas_bytes=b"CAS" * 10, inner_bytes=b"DSK" * 10):
            """write one launch's files under `sub`, as a probe would"""
            d = os.path.join(tmp, sub)
            os.makedirs(d, exist_ok=True)
            out = os.path.join(d, f"cap_{sub}.txt")
            cas = os.path.join(d, f"tape_{sub}.cas")
            inner = os.path.join(d, f"disk_{sub}.dsk")
            tcl = os.path.join(d, f"run_{sub}.tcl")
            open(cas, "wb").write(cas_bytes)
            open(inner, "wb").write(inner_bytes)
            open(tcl, "w").write(f"diska {{{inner}}}\n" + tcl_body
                                 + f"after time 20 {{set f [open {{{out}}} w]; "
                                   f"puts $f x; close $f; exit}}\n")
            cmd = ["openmsx", "-machine", "Fake_Direct", "-cassetteplayer", cas,
                   "-command", "set renderer none; set sound_driver null",
                   "-script", tcl]
            return cmd, out

        _MACHINE_ID.pop("Fake_Direct", None)
        ca, oa = launch("a")
        ka, _ = direct_key(ca, [oa])
        cb, ob = launch("b-another-temp-dir")
        kb, _ = direct_key(cb, [ob])
        arm("KD0 GREEN CONTROL: the same launch from ANOTHER temp dir (out, tcl, "
            "tape and Tcl-named disk all renamed) gives the SAME key",
            ka is not None and ka == kb, f"{(ka or '-')[:8]} vs {(kb or '-')[:8]}")
        c2, o2 = launch("c", cas_bytes=b"CAS" * 9 + b"CAT")
        k2, _ = direct_key(c2, [o2])
        arm("KD1 one byte of an ARGV medium (-cassetteplayer) -> MISS",
            k2 != ka, f"{ka[:8]} vs {(k2 or '-')[:8]}")
        c3, o3 = launch("d", inner_bytes=b"DSK" * 9 + b"DSL")
        k3, _ = direct_key(c3, [o3])
        arm("KD2 one byte of a medium named ONLY in the Tcl text (`diska {...}`) "
            "-> MISS (auto-detected, not declared)",
            k3 != ka, f"{ka[:8]} vs {(k3 or '-')[:8]}")
        c4, o4 = launch("e", tcl_body="after time 9 {type \"PRINT 2\\r\"}\n")
        k4, _ = direct_key(c4, [o4])
        arm("KD3 one character of the Tcl -> MISS", k4 != ka,
            f"{ka[:8]} vs {(k4 or '-')[:8]}")
        open(rom, "wb").write(b"\x00" * 63 + b"\x01")
        _MACHINE_ID.pop("Fake_Direct", None)
        k5, _ = direct_key(ca, [oa])
        open(rom, "wb").write(b"\x00" * 64)
        _MACHINE_ID.pop("Fake_Direct", None)
        k5b, _ = direct_key(ca, [oa])
        arm("KD4 one byte of a ROM the machine names -> MISS, through cached_run's "
            "own key", k5 != ka, f"{ka[:8]} vs {(k5 or '-')[:8]}")
        arm("KD4b restoring the ROM restores the key (control)", k5b == ka)
        for body, why in (("set t [clock seconds]\n", "clock"),
                          ("set r [expr {rand()}]\n", "rand"),
                          ("after realtime 1 {exit}\n", "after realtime"),
                          ("exec ls\n", "exec"), ("set g [glob /tmp/*]\n", "glob"),
                          ("puts $env(HOME)\n", "env")):
            c6, o6 = launch("f", tcl_body=body)
            k6, r6 = direct_key(c6, [o6])
            arm(f"KD5 a Tcl that reads the host ({why}) is UNCACHEABLE",
                k6 is None, r6 or "")
        # KD-R: the REAL zerobas machines. A repo-built ROM named by a relative
        # or missing path hashes as ABSENT -- then zerobas's key would NOT move
        # with the build, and that is the wrong hit this cache must never make.
        repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        for m in ("C-BIOS_MSX1_EU_REPACK_NODISK", "C-BIOS_MSX1_EU_REPACK_DISK"):
            x = saved_mx(m)
            if x is None:
                print(f"SKIP  KD-R {m}: not installed (make repack-machine)")
                continue
            body = open(x, encoding="utf-8", errors="replace").read()
            names = re.findall(r"<filename>\s*([^<]*?)\s*</filename>", body)
            ours = [n for n in names if "zerobas" in n or n.startswith(repo)]
            badn = [n for n in ours if not (os.path.isabs(n) and os.path.isfile(n))]
            arm(f"KD-R {m}: every repo-built ROM it names is ABSOLUTE and PRESENT, "
                f"so its bytes are in the key", bool(ours) and not badn,
                f"{len(ours)} repo ROM(s){'; BAD ' + repr(badn) if badn else ''}")
        # KD6 end to end on a fake run: miss -> store -> hit replays the bytes
        ROOT, VERIFY, ENABLED = tempfile.mkdtemp(prefix="refbypass-rt-"), False, True
        calls = []

        def fake_run(out, data):
            def r():
                calls.append(out)
                if data is not None:
                    open(out, "wb").write(data)
                return "ran"
            return r

        h0 = STATS["hit"]
        _OCCURRENCE.clear()
        s1 = cached_run(ca, [oa], fake_run(oa, b"READING 1\n"))
        open(oa, "wb").write(b"STALE")
        _OCCURRENCE.clear()                  # a NEW process, as far as the key goes
        s2 = cached_run(cb, [ob], fake_run(ob, b"SHOULD NOT RUN\n"))
        arm("KD6 miss -> stored -> the SAME launch from another temp dir is a "
            "HIT, the run is NOT called, and the output is replayed byte-exact",
            s1 == (False, "ran") and s2 == (True, None) and len(calls) == 1
            and open(ob, "rb").read() == b"READING 1\n" and STATS["hit"] == h0 + 1,
            f"{s1} {s2} calls={len(calls)}")
        # KD12: the SAME launch AGAIN in the same process (a --trials repeat)
        # is RE-MEASURED, not served the first trial's reading ...
        s3 = cached_run(cb, [ob], fake_run(ob, b"TRIAL 2\n"))
        arm("KD12 a repeat of an identical launch INSIDE one process is re-measured "
            "(a `--trials` repeat must not be a copy of trial 1)",
            s3 == (False, "ran") and len(calls) == 2, f"{s3} calls={len(calls)}")
        # ... and a later process replays EACH trial from its own measurement
        _OCCURRENCE.clear()
        t1 = cached_run(ca, [oa], fake_run(oa, b"X\n")); r1 = open(oa, "rb").read()
        t2 = cached_run(ca, [oa], fake_run(oa, b"X\n")); r2 = open(oa, "rb").read()
        arm("KD12b a later process serves trial 1 and trial 2 from their OWN entries",
            t1 == t2 == (True, None) and (r1, r2) == (b"READING 1\n", b"TRIAL 2\n")
            and len(calls) == 2, f"{r1!r} {r2!r}")
        cx, ox = launch("g", tcl_body="after time 9 {type \"PRINT 3\\r\"}\n")
        cached_run(cx, [ox], fake_run(ox, b""))
        _OCCURRENCE.clear()   # else the 2nd call misses as a TRIAL, proving nothing
        cached_run(cx, [ox], fake_run(ox, b"later\n"))
        arm("KD7 an EMPTY output is never stored (the next call runs)",
            calls[-2:] == [ox, ox])
        cy, oy = launch("h", tcl_body="after time 9 {type \"PRINT 4\\r\"}\n")
        cached_run(cy, [oy], fake_run(oy, b"partial\n"), ok=lambda v: False)
        _OCCURRENCE.clear()
        cached_run(cy, [oy], fake_run(oy, b"partial\n"))
        arm("KD8 an `ok` veto (a watchdog timeout) is never stored",
            calls[-2:] == [oy, oy])
        open(oa, "wb").write(b"STALE FROM AN EARLIER CALL\n")
        cz, oz = launch("i", tcl_body="after time 9 {type \"PRINT 5\\r\"}\n")
        open(oz, "wb").write(b"STALE FROM AN EARLIER CALL\n")
        cached_run(cz, [oz], fake_run(oz, None))     # the run writes NOTHING
        arm("KD9 a stale output file from an earlier call is DELETED before the "
            "run, so it can never be stored as this run's reading",
            not os.path.exists(oz) and _direct_load(direct_key(cz, [oz])[0]) is None)
        VERIFY = True
        vb = STATS["verify_bad"]; vo = STATS["verify_ok"]
        _OCCURRENCE.clear()
        cached_run(ca, [oa], fake_run(oa, b"READING 1\n"))
        arm("KD10 VERIFY agrees with an untampered entry (green control)",
            STATS["verify_ok"] == vo + 1)
        _OCCURRENCE.clear()
        cached_run(ca, [oa], fake_run(oa, b"A DIFFERENT READING\n"))
        arm("KD11 VERIFY catches a reading that moved (the arm that matters)",
            STATS["verify_bad"] == vb + 1)
        # --- D-REFSONLY: `refs` mode -- references replayed, zerobas measured --
        VERIFY = False
        arm("KS1 the real machines classify: REPACK_NODISK/_DISK are zerobas, "
            "the VG-8020 and CF-3300 are references",
            is_subject("C-BIOS_MSX1_EU_REPACK_NODISK")
            and is_subject("C-BIOS_MSX1_EU_REPACK_DISK")
            and not is_subject("Philips_VG_8020")
            and not is_subject("National_CF-3300"))
        arm("KS2 name and bytes DISAGREE -> zerobas, both ways round (a REPACK "
            "name over foreign ROMs; a reference name over a repo-built ROM)",
            is_subject("C-BIOS_MSX1_EU_REPACK_PLANT")
            and is_subject("Fake_Ref_With_Repo_Rom")
            and not is_subject("Fake_Direct"))
        arm("KS3 a repo-built ROM inserted as a cart makes a REFERENCE machine's "
            "launch a zerobas measurement",
            is_subject("Philips_VG_8020", [os.path.join(REPO, "build", "x.rom")]))
        # a zerobas launch whose entry IS in the store (stored in mode 1) ...
        cz2 = [a.replace("Fake_Direct", "C-BIOS_MSX1_EU_REPACK_PLANT") for a in ca]
        _OCCURRENCE.clear()
        cached_run(cz2, [oa], fake_run(oa, b"OLD ZEROBAS READING\n"))
        kz, _ = direct_key(cz2, [oa])
        arm("KS4 (control) the zerobas entry really is in the store",
            _direct_load(kz) == [b"OLD ZEROBAS READING\n"])
        REFS = True
        n0, sm0 = len(calls), STATS["subject_measured"]
        _OCCURRENCE.clear()
        served = cached_run(cz2, [oa], fake_run(oa, b"NEW ZEROBAS READING\n"))
        arm("KS5 🔴 THE ARM THAT MATTERS: in refs mode a zerobas launch is NEVER "
            "served, even with a matching entry -- it runs, and is counted",
            served == (False, "ran") and len(calls) == n0 + 1
            and open(oa, "rb").read() == b"NEW ZEROBAS READING\n"
            and STATS["subject_measured"] == sm0 + 1, f"{served}")
        arm("KS5b ... and is not STORED either (the old entry is untouched)",
            _direct_load(kz) == [b"OLD ZEROBAS READING\n"])
        _OCCURRENCE.clear()
        n1 = len(calls)
        served = cached_run(ca, [oa], fake_run(oa, b"SHOULD NOT RUN\n"))
        arm("KS6 in refs mode a REFERENCE launch is still served (the green "
            "control: without it KS5 passes on a mode that serves nothing)",
            served == (True, None) and len(calls) == n1)
        try:
            refuse_subject_hit("C-BIOS_MSX1_EU_REPACK_PLANT")
            died = False
        except SystemExit:
            died = True
        arm("KS7 the hit-path guard is a HARD STOP for zerobas in refs mode", died)
        arm("KS8 the tally names both sides", "zerobas reading(s) MEASURED"
            in summary() and "0 zerobas replayed" in summary(), summary())
        REFS = False
    finally:
        _machine_xml, _hit_preflight = saved_mx, saved_hp
        REFS = saved_refs
        if ROOT != saved_root:
            shutil.rmtree(ROOT, ignore_errors=True)
        ROOT, VERIFY, ENABLED = saved_root, saved_v, saved_en
        _MACHINE_ID.pop("Fake_Direct", None)
        shutil.rmtree(tmp, ignore_errors=True)

    # --- KM1 / KM2 a run_cases MEDIA parameter is keyed by its bytes ------
    _md = tempfile.mkdtemp(prefix="refmedia-")
    try:
        pa, pb = os.path.join(_md, "a.dsk"), os.path.join(_md, "b.dsk")
        for p_ in (pa, pb):
            with open(p_, "wb") as fh:
                fh.write(b"\x00" * 64)
        cs = [("direct", ["PRINT 1"])]
        ka = key_for("Fake_Media", cs, {"diska": pa})
        kb = key_for("Fake_Media", cs, {"diska": pb})
        arm("KM1 the same disk bytes at two temp paths give ONE key (the 718-miss bug)",
            ka == kb)
        with open(pb, "wb") as fh:
            fh.write(b"\x00" * 63 + b"\x01")
        arm("KM2 one changed disk byte gives a NEW key",
            key_for("Fake_Media", cs, {"diska": pb}) != ka)
        before = media_snapshot({"diska": pa})
        with open(pa, "wb") as fh:
            fh.write(b"\x00" * 60 + b"SAVE")          # the run "wrote" the disk
        ch = media_changes(before)
        pc = os.path.join(_md, "c.dsk")
        with open(pc, "wb") as fh:
            fh.write(b"\x00" * 64)                    # the next caller's fresh copy
        replay_media(ch, {"diska": pc})
        arm("KM3 a disk the run WROTE is replayed byte for byte on a hit (the "
            "six disk-write suites that read their image back)",
            list(ch) == ["diska"] and open(pc, "rb").read() == b"\x00" * 60 + b"SAVE")
    finally:
        shutil.rmtree(_md, ignore_errors=True)
        _MACHINE_ID.pop("Fake_Media", None)

    # --- KS9 refs mode END TO END through run_cases, on the REAL zerobas ---
    # Plant a LIE under the exact run_cases key of a zerobas reading, switch
    # the imported instance to `refs`, and require a live boot's answer.
    import probe_refcache as RC
    saved = (RC.ROOT, RC.ENABLED, RC.VERIFY, RC.REFS)
    RC.ROOT = tempfile.mkdtemp(prefix="refsonly-")
    RC.ENABLED, RC.VERIFY, RC.REFS = True, False, True
    try:
        import inspect
        import omsx_repl
        ZM = "C-BIOS_MSX1_EU_REPACK_NODISK"
        CASE = [("direct", ["NEW", 'PRINT "REFSONLY"'])]
        KW = dict(batch=False, boot=8.0, step=8.0, cap_gap=10.0, timeout=300.0)
        b = inspect.signature(omsx_repl._run_cases_impl).bind(ZM, CASE, **KW)
        b.apply_defaults()
        a2 = dict(b.arguments); a2.pop("machine"); a2.pop("cases"); a2.pop("settle_out", None)
        RC.store(RC.key_for(ZM, CASE, a2), ["A DELIBERATE LIE"], ZM)
        got = omsx_repl.run_cases(ZM, CASE, **KW)
        arm("KS9 🔴 refs mode, run_cases, the REAL zerobas machine with a LIE "
            "planted under its exact key: the lie is NOT served -- zerobas boots",
            bool(got) and got[0] != "A DELIBERATE LIE" and "REFSONLY" in (got[0] or ""),
            (got[0] or "NOTHING")[:40] if got else "NOTHING")
    except SystemExit as e:
        # Two different exits. omsx_preflight refuses with code 2 when the
        # installed machine does not match the build (the static gate tier does
        # not install it; it went RED there on 2026-11-03 for that reason) --
        # nothing was measured, so it is a SKIP, said out loud. The guard's own
        # exit carries its REFUSING message: that is the failure this arm exists
        # to catch.
        if e.code == 2:
            print("SKIP  KS9 end-to-end refs: openMSX preflight refused the "
                  "zerobas machine (not installed for this build) -- NOT measured")
        else:
            arm("KS9 refs mode end to end", False, f"SystemExit: {e}")
    except Exception as e:                       # an emulator-less host
        print(f"SKIP  KS9 end-to-end refs: {type(e).__name__}: {e}")
    finally:
        shutil.rmtree(RC.ROOT, ignore_errors=True)
        RC.ROOT, RC.ENABLED, RC.VERIFY, RC.REFS = saved

    print()
    print("ALL PASS — refcache falsification suite" if not fails
          else f"🔴 {len(fails)} ARM(S) FAILED: {fails}")
    return 1 if fails else 0


def maintain(now: float | None = None,
             stats_now: float | None = None) -> int:
    """Prune expired entries and print what the store looks like.

    🟢 THE PRUNE HAS TO BE SOMEWHERE THAT ACTUALLY RUNS. An age cap that only
    takes effect on `load` bounds STALENESS but never reclaims disk, and the
    filed item's whole complaint was that `rm -rf` was the entire recovery
    procedure. `make refcache-check` runs every battery, costs nothing, and is
    already the file's gate."""
    # 🔴 ONE CLOCK READING FOR BOTH WALKS. The prune and the post-condition
    # must agree about what time it is, or the check is a race against the gate
    # itself: an entry at cap-epsilon passes the prune and is at cap+delta when
    # the report measures it. That is what made `refcache-check` go red on the
    # CALENDAR and the battery's retry arm call it REAL -- a second run inside
    # one battery is a second run at the same instant, so a retry cannot
    # classify a clock-driven red (D-REFRACE).
    # `stats_now` exists ONLY for the selftest's negative control, which
    # reproduces the old two-readings behaviour and must go red.
    now = time.time() if now is None else now
    removed, kept = prune(now=now)
    n, size, oldest = store_stats(now=now if stats_now is None else stats_now)
    print(f"refcache store: {n} entr(ies), {size / 1e6:.1f} MB, "
          f"oldest {oldest / 86400:.1f}d, cap {MAX_AGE_DAYS:g}d; "
          f"pruned {removed}, kept {kept}")
    # 🔴 A READOUT THAT CANNOT GO RED IS A PRINT STATEMENT. After a prune no
    # entry may be past the cap -- if one is, expiry is not doing what the two
    # sentences above claim.
    if MAX_AGE_DAYS > 0 and oldest > _MAX_AGE:
        # 🔴 SAY WHICH ENTRY AND WHY, NOT JUST THAT ONE EXISTS. The filed red
        # (TODO, apparatus (d)) could not be diagnosed after the fact because
        # this message named nothing: the run that investigated it also REPAIRED
        # it, so the evidence was gone. Everything below is free to compute and
        # is what a post-mortem needs.
        print(f"🔴 an entry survived the prune at {oldest / 86400:.1f}d "
              f"> {MAX_AGE_DAYS:g}d cap")
        if PRUNE_FAILED:
            print(f"   CAUSE: {len(PRUNE_FAILED)} over-cap entr(ies) could NOT "
                  f"be unlinked -- this is the `except OSError` arm, and it is "
                  f"counted in `kept`, which is why it used to look like a "
                  f"young entry:")
            for fp, a, err in PRUNE_FAILED[:5]:
                print(f"     {a / 86400:.2f}d  {err}  {fp}")
        else:
            # No unlink failed, so the survivor was UNDER the cap when the prune
            # looked and OVER it when the report did -- or it appeared between
            # the two walks. Name the offender so the next reader has the datum
            # this gate denied its own investigator.
            worst = None
            for dirpath, _dirs, files in os.walk(ROOT):
                for fn in files:
                    if not fn.endswith(".json"):
                        continue
                    fp = os.path.join(dirpath, fn)
                    ag = _age(fp, now if stats_now is None else stats_now)
                    if worst is None or ag > worst[1]:
                        worst = (fp, ag)
            print("   CAUSE: no unlink failed, so this is NOT the "
                  "`except OSError` arm. The oldest survivor was under the cap "
                  "when prune looked and over it when the report did, or it "
                  "arrived between the two walks.")
            if worst:
                print(f"     oldest survivor: {worst[1] / 86400:.4f}d  "
                      f"{worst[0]}")
                print(f"     margin over cap: "
                      f"{(worst[1] - _MAX_AGE):.3f}s")
        return 1
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    if "--maintain" in sys.argv:
        raise SystemExit(maintain())
    raise SystemExit((print(summary() or "refcache: idle"), 0)[1])
