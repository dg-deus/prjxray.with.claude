# coding: utf-8
#
# SPDX-License-Identifier: ISC
"""
Worked example: probe CLB tiles with a CARRY4 carry-in bit.

This mirrors prjxray's 005-tilegrid/clb fuzzer: a CARRY4 is placed in each CLB
and its CI input is tied high (probe) or low (reference).  The single bit that
follows CI is the landmark used to locate the tile.

Copy this file to add your own tile types.  The two things that matter are
:meth:`emit_instance` (the primitive + the toggled feature) and the
``calibration`` (filled in once the deltas are known; see compute.py).
"""

from __future__ import annotations

from ..tiles import ProbeCalibration, TileProbeGenerator, register


@register
class ClbLlLCarry4(TileProbeGenerator):
    tile_type = "CLBLL_L"
    site_type = "SLICEL"
    zero_value = "1'b0"
    one_value = "1'b1"

    # prjxray clb fuzzer uses --dword 0 --dframe 0 (landmark sits on the tile
    # origin); words/frames per the prjxray geometry table.
    calibration = ProbeCalibration(
        dframe=0x0, dword=0, dbit=None, words=2, frames=36, auto_frame=False)

    def emit_instance(self, inst_name: str, value: str) -> str:
        # CARRY4 with CI driven by the toggled constant.  KEEP/DONT_TOUCH stop
        # the optimizer from removing it; LOC is applied from XDC.
        return (
            "  (* KEEP = \"true\", DONT_TOUCH = \"true\" *)\n"
            "  CARRY4 {name} (\n"
            "    .CO(), .O(), .DI(4'b0), .S(4'b1111),\n"
            "    .CI({val}), .CYINIT(1'b0)\n"
            "  );".format(name=inst_name, val=value))
