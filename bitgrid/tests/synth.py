# coding: utf-8
#
# SPDX-License-Identifier: ISC
"""Build synthetic PERFRAMECRC-style bitstreams for tests."""

import struct
from typing import Dict, List

from bitgrid.bitstream.registers import ConfReg, Opcode, SYNC_WORD
from bitgrid.frame_address import FRAME_WORD_COUNT


def _type1(opcode: Opcode, reg: ConfReg, count: int) -> int:
    return (1 << 29) | (int(opcode) << 27) | (int(reg) << 13) | count


def build_bitstream(frames: Dict[int, List[int]], idcode: int = None) -> bytes:
    """frames: {raw_frame_address: [101 words]} -> .bit-style bytes."""
    words: List[int] = [0xFFFFFFFF, SYNC_WORD]  # header noise + sync
    if idcode is not None:
        words.append(_type1(Opcode.WRITE, ConfReg.IDCODE, 1))
        words.append(idcode)
    for addr in sorted(frames):
        data = frames[addr]
        assert len(data) == FRAME_WORD_COUNT
        words.append(_type1(Opcode.WRITE, ConfReg.FAR, 1))
        words.append(addr)
        words.append(_type1(Opcode.WRITE, ConfReg.FDRI, FRAME_WORD_COUNT))
        words.extend(data)
    return struct.pack(">%dI" % len(words), *words)
