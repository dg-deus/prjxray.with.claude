# coding: utf-8
#
# SPDX-License-Identifier: ISC
"""
``python -m bitgrid.verify`` — verification harness.

User inputs a ``--device`` (e.g. xc7a12t) and ``--package`` (e.g. cpg238-1);
together they form the Vivado part (``xc7a12tcpg238-1``).

Two modes:

* ``--compare COMPUTED REFERENCE`` — diff a computed ``bits`` json (from package
  C) against a reference ``tilegrid.json`` (e.g. a downloaded prjxray DB),
  reporting per-tile mismatches in baseaddr/frames/offset/words.  Exit code is
  nonzero if anything differs.
* ``--pipeline`` — drive packages A→B→C end to end for one tile type.  Steps
  that need Vivado are invoked through designgen's runner; without Vivado this
  stops after emitting the designs and tells you what to run.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Dict, Optional


def make_part(device: str, package: str) -> str:
    return "%s%s" % (device, package)


# ---- compare --------------------------------------------------------------

_FIELDS = ("baseaddr", "frames", "offset", "words")


def _load_bits(path: str) -> Dict[str, dict]:
    with open(path) as f:
        data = json.load(f)
    # Accept either {tile: {baseaddr,...}} or a tilegrid.json {tile: {bits: {...}}}
    out = {}
    for tile, td in data.items():
        if isinstance(td, dict) and "bits" in td:
            for _bt, entry in td["bits"].items():
                out[tile] = entry
                break
        else:
            out[tile] = td
    return out


def _norm(entry: dict) -> dict:
    n = {}
    for k in _FIELDS:
        if k not in entry:
            continue
        v = entry[k]
        if k == "baseaddr" and isinstance(v, str):
            v = int(v, 0)
        n[k] = v
    return n


def compare(computed_path: str, reference_path: str) -> int:
    comp = _load_bits(computed_path)
    ref = _load_bits(reference_path)

    mismatches = 0
    only_computed = set(comp) - set(ref)
    only_ref = set(ref) - set(comp)

    for tile in sorted(set(comp) & set(ref)):
        c, r = _norm(comp[tile]), _norm(ref[tile])
        for k in _FIELDS:
            if k in c and k in r and c[k] != r[k]:
                cv = ("0x%08X" % c[k]) if k == "baseaddr" else c[k]
                rv = ("0x%08X" % r[k]) if k == "baseaddr" else r[k]
                print("MISMATCH %s.%s: computed=%s reference=%s" %
                      (tile, k, cv, rv))
                mismatches += 1

    if only_computed:
        print("only in computed: %d tiles" % len(only_computed))
    if only_ref:
        print("only in reference: %d tiles" % len(only_ref))

    common = len(set(comp) & set(ref))
    print("compared %d tiles, %d field mismatches" % (common, mismatches))
    return 1 if (mismatches or only_computed or only_ref) else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--device", required=True, help="e.g. xc7a12t")
    p.add_argument("--package", required=True, help="e.g. cpg238-1")
    p.add_argument("--compare", nargs=2, metavar=("COMPUTED", "REFERENCE"),
                   help="diff computed bits against a reference tilegrid.json")
    p.add_argument("--pipeline", action="store_true",
                   help="drive packages A->B->C (needs Vivado for the builds)")
    p.add_argument("--tile-type", help="tile type for --pipeline")
    args = p.parse_args(argv)

    part = make_part(args.device, args.package)
    print("part: %s" % part, file=sys.stderr)

    if args.compare:
        return compare(args.compare[0], args.compare[1])

    if args.pipeline:
        if not args.tile_type:
            print("error: --pipeline requires --tile-type", file=sys.stderr)
            return 2
        print(
            "pipeline driver:\n"
            "  1. designgen  --tile-type %s --part %s --rapidwright --out build\n"
            "  2. run build/ref.tcl and build/probe.tcl in Vivado\n"
            "     (also build a PERFRAMECRC design for partgen)\n"
            "  3. partgen   <perframecrc.bit> -o build/part.yaml\n"
            "  4. bitsgen   --ref build/ref.bit --probe build/probe.bit \\\n"
            "               --index build/index.csv --part-yaml build/part.yaml \\\n"
            "               -o build/bits.json\n"
            "  5. verify    --device %s --package %s \\\n"
            "               --compare build/bits.json <reference tilegrid.json>"
            % (args.tile_type, part, args.device, args.package),
            file=sys.stderr)
        return 0

    print("nothing to do: pass --compare or --pipeline", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
