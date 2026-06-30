# coding: utf-8
#
# SPDX-License-Identifier: ISC
"""
Package C step 2: turn observed landmark bits into ``bits`` entries.

For a tile we want the rectangle ``{baseaddr, frames, offset, words}``:

* **baseaddr** — frame address of the column base.  Recovered from any observed
  frame by rounding down to the 0x80 column boundary (``auto_frame``), or by
  subtracting a known frame delta ``dframe``.
* **offset**   — first word the tile uses = observed word minus the known word
  delta ``dword`` of the landmark inside the tile.
* **words**    — words per tile.  Either a frozen constant, or *derived* from
  the column ladder: the common spacing between consecutive tiles' offsets.
* **frames**   — frames per column.  A frozen constant, clamped to the
  authoritative value from ``part.yaml`` (package A) when available.

See the long-form explanation in the project README.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..frame_address import (FRAME_WORD_COUNT, align_down_to_column, dframe_of)


@dataclass
class BitsEntry:
    baseaddr: int
    frames: Optional[int]
    offset: int
    words: Optional[int]

    def to_json(self) -> dict:
        d = {
            "baseaddr": "0x%08X" % self.baseaddr,
            "offset": self.offset,
        }
        if self.frames is not None:
            d["frames"] = self.frames
        if self.words is not None:
            d["words"] = self.words
        return d


def compute_baseaddr(frame: int, dframe: Optional[int] = None,
                     auto_frame: bool = True) -> int:
    """Recover the column base frame from an observed frame address."""
    if auto_frame or dframe is None:
        base = align_down_to_column(frame)
    else:
        base = frame - dframe
    assert base % 0x80 == 0, "unaligned baseaddr 0x%08X" % base
    return base


def compute_offset(word: int, dword: Optional[int] = None) -> int:
    off = word - (dword or 0)
    assert 0 <= off <= FRAME_WORD_COUNT, "offset out of range: %d" % off
    return off


def derive_words_from_ladder(offsets: List[int]) -> int:
    """Most common positive spacing between consecutive sorted offsets.

    Same-type tiles tile the frame contiguously, so consecutive offsets differ
    by ``words``.  The HCLK row introduces a single odd +1 step, so we take the
    mode of the gaps rather than any single difference.
    """
    s = sorted(set(offsets))
    if len(s) < 2:
        raise ValueError("need >= 2 tiles to derive words from the ladder")
    gaps = [b - a for a, b in zip(s, s[1:]) if b - a > 0]
    return Counter(gaps).most_common(1)[0][0]


def validate_entry(entry: BitsEntry, tile_name: str = "") -> None:
    if entry.words is not None:
        assert 1 <= entry.words <= FRAME_WORD_COUNT, (tile_name, entry.words)
        assert entry.offset + entry.words <= FRAME_WORD_COUNT, (
            tile_name, entry.offset, entry.words)


@dataclass
class ColumnObservation:
    """One landmark bit attributed to one tile."""
    tile: str
    grid_y: int
    frame: int
    word: int
    bit: int


def compute_column(observations: List[ColumnObservation],
                   dframe: Optional[int] = None,
                   dword: Optional[int] = None,
                   words: Optional[int] = None,
                   frames: Optional[int] = None,
                   auto_frame: bool = True,
                   part_frame_lookup=None) -> Dict[str, BitsEntry]:
    """Produce a ``{tile_name: BitsEntry}`` map for one probed column.

    ``part_frame_lookup`` is an optional callable ``baseaddr -> frame_count``
    (e.g. from package A's part.yaml) used to clamp ``frames``.
    """
    # Per-tile offset and base address.
    raw_offsets = {o.tile: compute_offset(o.word, dword) for o in observations}

    # Derive words from the offset ladder if not supplied.
    derived_words = words
    if derived_words is None and len(raw_offsets) >= 2:
        try:
            derived_words = derive_words_from_ladder(list(raw_offsets.values()))
        except ValueError:
            derived_words = None

    out: Dict[str, BitsEntry] = {}
    for o in observations:
        base = compute_baseaddr(o.frame, dframe, auto_frame)
        f = frames
        if part_frame_lookup is not None:
            try:
                maxf = part_frame_lookup(base)
                f = maxf if (f is None or f > maxf) else f
            except KeyError:
                pass
        entry = BitsEntry(
            baseaddr=base,
            frames=f,
            offset=raw_offsets[o.tile],
            words=derived_words,
        )
        validate_entry(entry, o.tile)
        out[o.tile] = entry
    return out
