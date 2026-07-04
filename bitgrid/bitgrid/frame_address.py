# coding: utf-8
#
# SPDX-License-Identifier: ISC
"""
7-series Xilinx frame-address codec.

A 7-series configuration *frame address* is the 32-bit value written to the
Frame Address Register (FAR).  Its bit layout (UG470, Table 5-24) is:

    bits [25:23]  block type   (0=CLB_IO_CLK, 1=BLOCK_RAM, 2=CFG_CLB)
    bit  [22]     row half     (0=top, 1=bottom)
    bits [21:17]  row          (clock-region row within the half, 5 bits)
    bits [16:7]   column       (major / configuration column, 10 bits)
    bits [6:0]    minor        (frame index within the column, 7 bits)

This matches prjxray's encoding (``util.get_baseaddress`` /
``util.addr2btype``):

    address = (row << 17) + (column << 7)
              + (1 << 22 if bottom) + (block_type << 23)

The 7-bit ``minor`` field is why a tile's base frame is always a multiple of
0x80 (128): the per-column frames share everything above bit 6 and differ only
in the minor field, and a column never has more than 128 frames.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

# Number of 32-bit words in one 7-series configuration frame.
FRAME_WORD_COUNT = 101
WORD_SIZE_BITS = 32

# A column boundary is aligned to this (minor == 0).
MINOR_ALIGNMENT = 0x80


class BlockType(IntEnum):
    CLB_IO_CLK = 0
    BLOCK_RAM = 1
    CFG_CLB = 2

    @property
    def bus_name(self) -> str:
        """prjxray ``part.yaml`` bus name for this block type."""
        return self.name


class RowHalf(IntEnum):
    TOP = 0
    BOTTOM = 1

    @property
    def yaml_name(self) -> str:
        return "top" if self is RowHalf.TOP else "bottom"


@dataclass(frozen=True, order=True)
class FrameAddress:
    """A decoded 7-series frame address.

    Compares/sorts in raw-address order, which is also column-then-minor order
    within a (block_type, half, row) group.
    """

    block_type: BlockType
    row_half: RowHalf
    row: int
    column: int
    minor: int

    # ---- encoding ---------------------------------------------------------

    @property
    def raw(self) -> int:
        """The 32-bit FAR value."""
        return (
            (int(self.block_type) << 23)
            | (int(self.row_half) << 22)
            | ((self.row & 0x1F) << 17)
            | ((self.column & 0x3FF) << 7)
            | (self.minor & 0x7F))

    @property
    def base_address(self) -> int:
        """Address of minor 0 in this column (the column's base frame)."""
        return self.raw & ~(MINOR_ALIGNMENT - 1)

    @property
    def column_key(self) -> tuple:
        """Identity of the column this frame belongs to (ignores minor)."""
        return (self.block_type, self.row_half, self.row, self.column)

    # ---- decoding ---------------------------------------------------------

    @classmethod
    def from_raw(cls, addr: int) -> "FrameAddress":
        return cls(
            block_type=BlockType((addr >> 23) & 0x7),
            row_half=RowHalf((addr >> 22) & 0x1),
            row=(addr >> 17) & 0x1F,
            column=(addr >> 7) & 0x3FF,
            minor=addr & 0x7F,
        )

    def with_minor(self, minor: int) -> "FrameAddress":
        return FrameAddress(
            self.block_type, self.row_half, self.row, self.column, minor)

    def __str__(self) -> str:
        return "0x%08X" % self.raw


def align_down_to_column(frame_addr: int) -> int:
    """Round any frame address *down* to its column base (minor == 0).

    This is the ``baseaddr`` recovery rule used in package C: a tile's base
    frame is the column boundary, and the leftover ``frame_addr % 0x80`` is the
    DFRAME of whatever bit was observed.
    """
    return frame_addr & ~(MINOR_ALIGNMENT - 1)


def dframe_of(frame_addr: int) -> int:
    """The minor part of an address = its offset past the column base."""
    return frame_addr & (MINOR_ALIGNMENT - 1)
