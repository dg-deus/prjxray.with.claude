# coding: utf-8
#
# SPDX-License-Identifier: ISC
"""
``python -m bitgrid.bitsgen`` — ref.bit + probe.bit + index.csv -> bits entries.

Diffs the two bitstreams, attributes each toggled bit to a tile (by matching the
sorted landmark bits to the column's tiles ordered by grid Y), then computes
``{baseaddr, frames, offset, words}`` per tile.

Attribution assumes one landmark bit per tile (the clean single-feature case).
With ``--reverse`` the grid-Y ordering is flipped to match the bit ladder
direction; the tool reports whether the resulting offsets form a clean ladder.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from typing import List, Optional

from .compute import ColumnObservation, compute_column
from .probe import BitLoc, diff_files


def _load_index(path: str):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append(r)
    rows.sort(key=lambda r: int(r["grid_y"]))
    return rows


def _attribute(bitlocs: List[BitLoc], index_rows, reverse: bool):
    tiles = list(index_rows)
    if reverse:
        tiles = list(reversed(tiles))
    if len(bitlocs) != len(tiles):
        print(
            "warning: %d toggled bits but %d tiles — attribution may be off"
            % (len(bitlocs), len(tiles)), file=sys.stderr)
    obs = []
    for tile_row, loc in zip(tiles, bitlocs):
        obs.append(
            ColumnObservation(
                tile=tile_row["tile"], grid_y=int(tile_row["grid_y"]),
                frame=loc.frame, word=loc.word, bit=loc.bit))
    return obs


def _load_part_lookup(part_yaml: Optional[str]):
    if not part_yaml:
        return None
    import yaml
    from ..frame_address import BlockType, FrameAddress
    with open(part_yaml) as f:
        part = yaml.safe_load(f)

    table = {}
    for half, hd in part.get("global_clock_regions", {}).items():
        for row, rd in hd.get("rows", {}).items():
            for bus, bd in rd.get("configuration_buses", {}).items():
                for col, cd in bd.get("configuration_columns", {}).items():
                    fa = FrameAddress(
                        block_type=BlockType[bus],
                        row_half=(0 if half == "top" else 1),
                        row=int(row), column=int(col), minor=0)
                    table[fa.raw] = cd["frame_count"]

    def lookup(baseaddr: int) -> int:
        if baseaddr not in table:
            raise KeyError(baseaddr)
        return table[baseaddr]

    return lookup


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ref", required=True, help="reference PERFRAMECRC .bit")
    p.add_argument("--probe", required=True, help="probe PERFRAMECRC .bit")
    p.add_argument("--index", required=True, help="index.csv from designgen")
    p.add_argument("--part-yaml", help="part.yaml from partgen (clamps frames)")
    p.add_argument("--dframe", type=lambda s: int(s, 16), default=None,
                   help="known frame delta (hex); omit to use 0x80 alignment")
    p.add_argument("--dword", type=int, default=0, help="known word delta")
    p.add_argument("--words", type=int, default=None,
                   help="words/tile; omit to derive from the column ladder")
    p.add_argument("--frames", type=int, default=None, help="frames/column")
    p.add_argument("--reverse", action="store_true",
                   help="flip grid-Y ordering for bit attribution")
    p.add_argument("-o", "--out", default="-", help="output bits json")
    args = p.parse_args(argv)

    bitlocs = diff_files(args.ref, args.probe)
    if not bitlocs:
        print("error: no toggled bits found between ref and probe",
              file=sys.stderr)
        return 1
    print("found %d toggled bits" % len(bitlocs), file=sys.stderr)

    index_rows = _load_index(args.index)
    obs = _attribute(bitlocs, index_rows, args.reverse)

    entries = compute_column(
        obs,
        dframe=args.dframe,
        dword=args.dword,
        words=args.words,
        frames=args.frames,
        auto_frame=(args.dframe is None),
        part_frame_lookup=_load_part_lookup(args.part_yaml),
    )

    result = {tile: e.to_json() for tile, e in entries.items()}
    offsets = sorted(e.offset for e in entries.values())
    print("offset ladder: %s" % offsets, file=sys.stderr)

    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out == "-":
        print(text)
    else:
        with open(args.out, "w") as f:
            f.write(text + "\n")
        print("wrote %s (%d tiles)" % (args.out, len(result)), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
