# coding: utf-8
#
# SPDX-License-Identifier: ISC
"""
Package A core: count frames per configuration column.

Given the FAR address list extracted from a PERFRAMECRC bitstream, every column
is identified by ``(block_type, row_half, row, column)`` and its ``frame_count``
is the number of distinct ``minor`` values observed in it.  Because Vivado
enumerates every real frame in a PERFRAMECRC stream, ``max(minor) + 1`` equals
the true per-column frame count (the same number prjxray stores in part.yaml,
e.g. CLB=36, INT/DSP/BRAM-routing=28/30/42, BRAM content=128).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List

from ..frame_address import BlockType, FrameAddress, RowHalf


@dataclass
class ColumnInfo:
    block_type: BlockType
    row_half: RowHalf
    row: int
    column: int
    frame_count: int
    minors: List[int]

    def sanity_check(self) -> List[str]:
        """Return human-readable warnings about an irregular column."""
        warns = []
        expected = set(range(self.frame_count))
        seen = set(self.minors)
        if seen != expected:
            missing = sorted(expected - seen)
            extra = sorted(seen - expected)
            if missing:
                warns.append(
                    "column %s row %d/%s col %d: missing minors %s" %
                    (self.block_type.name, self.row, self.row_half.yaml_name,
                     self.column, missing))
            if extra:
                warns.append(
                    "column %s row %d/%s col %d: minors above count %s" %
                    (self.block_type.name, self.row, self.row_half.yaml_name,
                     self.column, extra))
        return warns


def count_columns(far_raw: Iterable[int]) -> List[ColumnInfo]:
    """Group FAR addresses into columns and count their frames."""
    minors: Dict[tuple, set] = defaultdict(set)
    for raw in far_raw:
        fa = FrameAddress.from_raw(raw)
        minors[fa.column_key].add(fa.minor)

    cols: List[ColumnInfo] = []
    for (block_type, row_half, row, column), seen in minors.items():
        cols.append(
            ColumnInfo(
                block_type=block_type,
                row_half=row_half,
                row=row,
                column=column,
                frame_count=max(seen) + 1,
                minors=sorted(seen),
            ))
    cols.sort(key=lambda c: (c.row_half, c.row, c.block_type, c.column))
    return cols
