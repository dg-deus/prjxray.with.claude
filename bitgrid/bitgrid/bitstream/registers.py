# coding: utf-8
#
# SPDX-License-Identifier: ISC
"""7-series configuration register addresses (UG470, Table 5-23)."""

from __future__ import annotations

from enum import IntEnum


class ConfReg(IntEnum):
    CRC = 0
    FAR = 1          # Frame Address Register
    FDRI = 2         # Frame Data Register, Input
    FDRO = 3         # Frame Data Register, Output
    CMD = 4
    CTL0 = 5
    MASK = 6
    STAT = 7
    LOUT = 8
    COR0 = 9
    MFWR = 10
    CBC = 11
    IDCODE = 12
    AXSS = 13
    COR1 = 14
    WBSTAR = 16
    TIMER = 17
    BOOTSTS = 22
    CTL1 = 24


class Opcode(IntEnum):
    NOP = 0
    READ = 1
    WRITE = 2
    RESERVED = 3


# Word that marks the start of the configuration command stream.
SYNC_WORD = 0xAA995566
