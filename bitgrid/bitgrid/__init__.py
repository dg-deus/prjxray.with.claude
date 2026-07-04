# coding: utf-8
#
# SPDX-License-Identifier: ISC
"""bitgrid — independent, Python-only computation of tilegrid ``bits``.

Packages:
  partgen   (A) PERFRAMECRC bitstream -> per-column frame counts -> part.yaml
  designgen (B) generate Verilog/XDC/tcl probe designs per tile column
  bitsgen   (C) diff bitstreams -> toggled bits -> baseaddr/offset/words
  verify    (D) compare computed bits against a reference & drive the pipeline
"""

__version__ = "0.1.0"
