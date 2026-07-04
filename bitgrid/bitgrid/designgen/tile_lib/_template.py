# coding: utf-8
#
# SPDX-License-Identifier: ISC
"""
Template for a new tile-type probe generator.

1. Copy this file to ``my_tile.py``.
2. Set ``tile_type`` (tilegrid name) and ``site_type`` (Vivado site).
3. Implement ``emit_instance`` with a primitive that has ONE clearly toggled
   feature controlled by ``value``.
4. Leave ``calibration`` mostly ``None`` at first; run package C with
   ``--derive`` to recover dframe (0x80 alignment) and words (column ladder),
   then freeze the numbers here.
5. Import it from ``tiles.load_builtin_generators`` (or pass --tile-module).
"""

from __future__ import annotations

from ..tiles import ProbeCalibration, TileProbeGenerator, register


@register
class MyTile(TileProbeGenerator):
    tile_type = "MY_TILE_TYPE"      # e.g. "CLBLM_R", "BRAM_L", "DSP_R"
    site_type = "MY_SITE_TYPE"      # e.g. "SLICEM", "RAMB36", "DSP48E1"
    zero_value = "1'b0"
    one_value = "1'b1"

    calibration = ProbeCalibration(auto_frame=True)  # fill in once known

    def emit_instance(self, inst_name: str, value: str) -> str:
        raise NotImplementedError("describe the probe primitive here")
