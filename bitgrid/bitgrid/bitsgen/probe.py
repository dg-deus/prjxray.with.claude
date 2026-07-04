# coding: utf-8
#
# SPDX-License-Identifier: ISC
"""
Package C step 1: find toggled bits by diffing two PERFRAMECRC bitstreams.

Given a reference bitstream (feature cleared in every tile) and a probe
bitstream (feature set in every tile), the bits that differ are the landmarks.
Each landmark is reported as ``(frame_address, word_index, bit_index)`` — the
same coordinate system prjxray's ``bitread`` emits as ``FRAME_WORD_BIT``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from ..bitstream.reader import ParsedBitstream, parse_file
from ..frame_address import WORD_SIZE_BITS


@dataclass(frozen=True, order=True)
class BitLoc:
    frame: int      # raw frame address
    word: int       # word index within the frame (0..100)
    bit: int        # bit index within the word (0..31)

    def __str__(self) -> str:
        return "%08X_%03d_%02d" % (self.frame, self.word, self.bit)


def diff(ref: ParsedBitstream, probe: ParsedBitstream) -> List[BitLoc]:
    """Return every bit that is set differently between ref and probe."""
    locs: List[BitLoc] = []
    frames = set(ref.frames) | set(probe.frames)
    for fa in frames:
        rw = ref.frames.get(fa)
        pw = probe.frames.get(fa)
        if rw is None or pw is None:
            # Frame present in only one stream — treat the present one vs zero.
            rw = rw or [0] * len(pw)
            pw = pw or [0] * len(rw)
        for widx, (a, b) in enumerate(zip(rw, pw)):
            x = a ^ b
            while x:
                bit = (x & -x).bit_length() - 1
                locs.append(BitLoc(frame=fa, word=widx, bit=bit))
                x &= x - 1
    locs.sort()
    return locs


def diff_files(ref_path: str, probe_path: str) -> List[BitLoc]:
    return diff(parse_file(ref_path), parse_file(probe_path))
