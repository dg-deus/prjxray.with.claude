# coding: utf-8
#
# SPDX-License-Identifier: ISC

from bitgrid.bitsgen.compute import (ColumnObservation, compute_baseaddr,
                                     compute_column, compute_offset,
                                     derive_words_from_ladder)
from bitgrid.bitsgen.probe import diff
from bitgrid.bitstream.reader import parse
from bitgrid.frame_address import FRAME_WORD_COUNT, BlockType, FrameAddress, RowHalf
from synth import build_bitstream


def test_baseaddr_and_offset():
    fa = FrameAddress(BlockType.CLB_IO_CLK, RowHalf.TOP, 1, 4, minor=0x27)
    assert compute_baseaddr(fa.raw, auto_frame=True) == fa.base_address
    # explicit dframe form
    assert compute_baseaddr(fa.raw, dframe=0x27, auto_frame=False) == fa.base_address
    assert compute_offset(7, dword=1) == 6


def test_derive_words_ladder_with_hclk_gap():
    # 0,2,4,6, then +1 HCLK jump to 7, 9, 11  -> words should be 2
    assert derive_words_from_ladder([0, 2, 4, 6, 7, 9, 11]) == 2


def test_diff_and_compute_column():
    base = FrameAddress(BlockType.CLB_IO_CLK, RowHalf.TOP, 0, 5, minor=0)
    # Three tiles stacked by word offset 0,2,4; landmark at dword=0,bit=3.
    ref_frames = {base.raw: [0] * FRAME_WORD_COUNT}
    probe_frames = {base.raw: [0] * FRAME_WORD_COUNT}
    tiles = [("TILE_Y0", 0, 0), ("TILE_Y1", 1, 2), ("TILE_Y2", 2, 4)]
    for _name, _gy, word in tiles:
        probe_frames[base.raw][word] |= (1 << 3)

    locs = diff(parse(build_bitstream(ref_frames)),
                parse(build_bitstream(probe_frames)))
    assert len(locs) == 3
    assert [l.word for l in locs] == [0, 2, 4]

    obs = [ColumnObservation(tile=n, grid_y=gy, frame=base.raw, word=w, bit=3)
           for (n, gy, w) in tiles]
    entries = compute_column(obs, dword=0, auto_frame=True)
    assert entries["TILE_Y0"].baseaddr == base.base_address
    assert entries["TILE_Y0"].offset == 0
    assert entries["TILE_Y2"].offset == 4
    # words derived from the 0,2,4 ladder
    assert entries["TILE_Y0"].words == 2
