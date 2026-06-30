# coding: utf-8
#
# SPDX-License-Identifier: ISC

from bitgrid.frame_address import (BlockType, FrameAddress, RowHalf,
                                    align_down_to_column, dframe_of)


def test_roundtrip():
    fa = FrameAddress(BlockType.CLB_IO_CLK, RowHalf.BOTTOM, row=3, column=5,
                      minor=7)
    assert FrameAddress.from_raw(fa.raw) == fa


def test_field_layout_matches_prjxray():
    # prjxray: address = (row<<17)+(column<<7)+(1<<22 if bottom)+(bt<<23)
    fa = FrameAddress(BlockType.BLOCK_RAM, RowHalf.BOTTOM, row=2, column=9,
                      minor=0)
    expected = (2 << 17) + (9 << 7) + (1 << 22) + (1 << 23)
    assert fa.raw == expected


def test_alignment():
    fa = FrameAddress(BlockType.CLB_IO_CLK, RowHalf.TOP, row=1, column=4,
                      minor=0x27)
    assert align_down_to_column(fa.raw) == fa.base_address
    assert fa.base_address % 0x80 == 0
    assert dframe_of(fa.raw) == 0x27


def test_block_type_decode():
    raw = (2 << 23)  # CFG_CLB
    assert FrameAddress.from_raw(raw).block_type == BlockType.CFG_CLB
