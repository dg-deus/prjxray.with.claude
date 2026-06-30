# coding: utf-8
#
# SPDX-License-Identifier: ISC

import yaml

from bitgrid.bitstream.reader import parse
from bitgrid.frame_address import FRAME_WORD_COUNT, BlockType, FrameAddress, RowHalf
from bitgrid.partgen.frames import count_columns
from bitgrid.partgen.part_yaml import build_part_dict
from synth import build_bitstream


def _column(block_type, half, row, col, n_frames):
    frames = {}
    for minor in range(n_frames):
        fa = FrameAddress(block_type, half, row, col, minor)
        frames[fa.raw] = [0] * FRAME_WORD_COUNT
    return frames


def test_count_and_part_yaml():
    frames = {}
    # CLB-ish column with 36 frames and a BRAM content column with 128.
    frames.update(_column(BlockType.CLB_IO_CLK, RowHalf.TOP, 0, 0, 36))
    frames.update(_column(BlockType.CLB_IO_CLK, RowHalf.TOP, 0, 1, 30))
    frames.update(_column(BlockType.BLOCK_RAM, RowHalf.TOP, 0, 0, 128))

    parsed = parse(build_bitstream(frames, idcode=0x0362D093))
    assert parsed.idcode == 0x0362D093
    assert len(parsed.far_sequence) == 36 + 30 + 128

    cols = count_columns(parsed.far_sequence)
    counts = {(c.block_type, c.column): c.frame_count for c in cols}
    assert counts[(BlockType.CLB_IO_CLK, 0)] == 36
    assert counts[(BlockType.CLB_IO_CLK, 1)] == 30
    assert counts[(BlockType.BLOCK_RAM, 0)] == 128

    part = build_part_dict(cols, idcode=parsed.idcode)
    cc = part["global_clock_regions"]["top"]["rows"][0][
        "configuration_buses"]["CLB_IO_CLK"]["configuration_columns"]
    assert cc[0]["frame_count"] == 36
    # round-trips through yaml
    assert yaml.safe_load(yaml.safe_dump(part)) == part
