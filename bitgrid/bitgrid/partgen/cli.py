# coding: utf-8
#
# SPDX-License-Identifier: ISC
"""``python -m bitgrid.partgen`` — PERFRAMECRC bitstream -> part.yaml."""

from __future__ import annotations

import argparse
import sys

from ..bitstream.reader import parse_file
from .frames import count_columns
from .part_yaml import dump_part_yaml


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Count frames per column from a PERFRAMECRC bitstream "
        "and emit a prjxray-format part.yaml")
    p.add_argument("bitstream", help="design.perframecrc.bit")
    p.add_argument("-o", "--out", default="-", help="output part.yaml (or -)")
    p.add_argument(
        "--check", action="store_true",
        help="warn about columns with missing/extra minor frames")
    args = p.parse_args(argv)

    parsed = parse_file(args.bitstream)
    if not parsed.far_sequence:
        print(
            "error: no FAR writes found — was BITSTREAM.GENERAL.PERFRAMECRC "
            "set to YES?", file=sys.stderr)
        return 1

    columns = count_columns(parsed.far_sequence)

    if args.check:
        for col in columns:
            for w in col.sanity_check():
                print("warning: " + w, file=sys.stderr)

    text = dump_part_yaml(columns, idcode=parsed.idcode)
    if args.out == "-":
        sys.stdout.write(text)
    else:
        with open(args.out, "w") as f:
            f.write(text)
        print("wrote %s (%d columns)" % (args.out, len(columns)),
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
