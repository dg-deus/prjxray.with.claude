# coding: utf-8
#
# SPDX-License-Identifier: ISC
"""
High-level reader: turn a packet stream into frame data keyed by frame address.

Two bitstream flavours are supported:

* **PERFRAMECRC** (recommended for this toolchain): Vivado writes each frame
  preceded by its own FAR write, so every frame's address is explicit:

      FAR <addr> ; FDRI <101 words> ; CRC ... ; FAR <addr> ; FDRI <101 words> ...

  Parsing is unambiguous and needs no part geometry.  Generate designs with
  ``set_property BITSTREAM.GENERAL.PERFRAMECRC YES`` so this path is taken.

* **Normal**: a single FAR write followed by one big FDRI stream covering every
  frame in hardware auto-increment order.  Reconstructing per-frame addresses
  then requires the column geometry (the part.yaml from package A).  We support
  the explicit-FAR case fully and expose the raw FDRI words for the normal case.

The IDCODE register write (if present) is also captured, for ``part.yaml``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..frame_address import FRAME_WORD_COUNT, FrameAddress
from .packets import Packet, iter_packets, read_bit_file
from .registers import ConfReg, Opcode


@dataclass
class ParsedBitstream:
    idcode: Optional[int] = None
    # Ordered list of frame addresses as they appeared in FAR writes.
    far_sequence: List[int] = field(default_factory=list)
    # frame address (raw int) -> 101 data words.  Populated when frames can be
    # paired with an explicit FAR (PERFRAMECRC) write.
    frames: Dict[int, List[int]] = field(default_factory=dict)
    # Raw concatenated FDRI words that could not be paired with a FAR (normal
    # single-FDRI bitstreams).  Empty for PERFRAMECRC streams.
    unpaired_fdri: List[int] = field(default_factory=list)

    def decoded_far(self) -> List[FrameAddress]:
        return [FrameAddress.from_raw(a) for a in self.far_sequence]


def parse(data: bytes) -> ParsedBitstream:
    out = ParsedBitstream()
    pending_far: Optional[int] = None

    for pkt in iter_packets(data):
        if pkt.opcode != Opcode.WRITE:
            continue
        reg = pkt.reg

        if reg == ConfReg.IDCODE and pkt.payload:
            out.idcode = pkt.payload[-1]

        elif reg == ConfReg.FAR and pkt.payload:
            pending_far = pkt.payload[-1]
            out.far_sequence.append(pending_far)

        elif reg == ConfReg.FDRI and pkt.payload:
            words = pkt.payload
            # PERFRAMECRC: payload is exactly one frame and we have a FAR.
            if pending_far is not None and len(words) == FRAME_WORD_COUNT:
                out.frames[pending_far] = list(words)
                # FAR auto-increments to the next frame after a write.
                pending_far = None
            elif (pending_far is not None
                  and len(words) % FRAME_WORD_COUNT == 0
                  and len(words) // FRAME_WORD_COUNT <= 4):
                # A small multi-frame FDRI burst that still started at a known
                # FAR: split it across consecutive minors of the same column.
                base = FrameAddress.from_raw(pending_far)
                for k in range(len(words) // FRAME_WORD_COUNT):
                    fa = base.with_minor(base.minor + k).raw
                    out.frames[fa] = list(
                        words[k * FRAME_WORD_COUNT:(k + 1) * FRAME_WORD_COUNT])
                pending_far = None
            else:
                # Big single-FDRI (normal) bitstream: cannot pair without
                # geometry; hand back the raw words.
                out.unpaired_fdri.extend(words)

    return out


def parse_file(path: str) -> ParsedBitstream:
    return parse(read_bit_file(path))
