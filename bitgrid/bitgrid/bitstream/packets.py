# coding: utf-8
#
# SPDX-License-Identifier: ISC
"""
Low-level 7-series configuration packet parser.

A ``.bit`` file begins with an (optional) variable-length header describing the
design, followed by a stream of 32-bit big-endian configuration words.  After a
sync word (0xAA995566) the words form a sequence of *packets*:

Type 1 packet (header word):
    [31:29] = 0b001              packet type
    [28:27] = opcode             0=NOP, 1=Read, 2=Write
    [26:13] = register address   (14 bits; only low 5 used in practice)
    [12:11] = reserved
    [10:0]  = word count         (up to 2047 payload words)

Type 2 packet (header word), always follows a Type 1 and reuses its register:
    [31:29] = 0b010              packet type
    [28:27] = opcode
    [26:0]  = word count         (large payloads, e.g. the whole FDRI stream)

This module yields decoded packets with their payloads; higher-level meaning
(FAR addresses, frame data) is assembled in :mod:`bitgrid.bitstream.reader`.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Iterator, List

from .registers import ConfReg, Opcode, SYNC_WORD


@dataclass
class Packet:
    ptype: int          # 1 or 2
    opcode: Opcode
    register: int       # raw register address; map to ConfReg when known
    payload: List[int]  # 32-bit words

    @property
    def reg(self):
        try:
            return ConfReg(self.register)
        except ValueError:
            return None


def _words_from_bit(data: bytes) -> List[int]:
    """Return the big-endian 32-bit words of the config stream after sync.

    The ``.bit`` container has a Xilinx header before the raw config words.  We
    locate the sync word by scanning 32-bit big-endian words, which is robust
    regardless of header length.
    """
    # Trim to a multiple of 4 bytes.
    n = len(data) - (len(data) % 4)
    words = list(struct.unpack(">%dI" % (n // 4), data[:n]))

    for i, w in enumerate(words):
        if w == SYNC_WORD:
            return words[i + 1:]
    raise ValueError("sync word 0x%08X not found in bitstream" % SYNC_WORD)


def iter_packets(data: bytes) -> Iterator[Packet]:
    """Parse a raw ``.bit`` byte string into a stream of packets."""
    words = _words_from_bit(data)
    i = 0
    last_register = 0
    while i < len(words):
        hdr = words[i]
        i += 1
        ptype = (hdr >> 29) & 0x7
        opcode = Opcode((hdr >> 27) & 0x3)

        if ptype == 1:
            register = (hdr >> 13) & 0x3FFF
            count = hdr & 0x7FF
            last_register = register
        elif ptype == 2:
            # Type 2 reuses the register of the preceding Type 1.
            register = last_register
            count = hdr & 0x07FFFFFF
        elif ptype == 0 and hdr == 0:
            # Padding / NOP zero word between packets.
            continue
        else:
            # Unknown / reserved header; stop rather than misinterpret.
            break

        payload = words[i:i + count]
        i += count
        yield Packet(ptype=ptype, opcode=opcode, register=register,
                     payload=payload)


def read_bit_file(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()
