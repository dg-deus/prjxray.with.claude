# coding: utf-8
#
# SPDX-License-Identifier: ISC
"""
Package B: per-tile-type probe generators.

To locate a tile's bits we place one primitive in every tile of a column and
toggle a single feature between a *reference* design (value = ``zero_value``)
and a *probe* design (value = ``one_value``).  The one bit that flips is the
landmark we measure in package C.

A :class:`TileProbeGenerator` knows, for one tile type:

* which FPGA **site type** to occupy (so we can pick a site inside each tile),
* how to emit the **Verilog** for one probe instance, and
* the **delta calibration** ``(dframe, dword, dbit)`` of the toggled bit
  relative to the tile origin — plus the tile's ``words``/``frames`` geometry.

The deltas may be left as ``None`` initially; package C can recover the frame
delta via 0x80 alignment and derive ``words`` from the column ladder (see
:mod:`bitgrid.bitsgen.compute`).  Once known, freeze them here.

Users add new tile types by subclassing and registering — see
``tile_lib/clb_carry4.py`` for a worked example and ``tile_lib/_template.py``
for a starting point.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Type


@dataclass
class ProbeCalibration:
    """Known geometry of a tile type (fill in as it is reverse-engineered)."""
    dframe: Optional[int] = None   # frame delta of the landmark bit (base 16)
    dword: Optional[int] = None    # word delta within the frame
    dbit: Optional[int] = None     # bit delta within the word
    words: Optional[int] = None    # words consumed per tile
    frames: Optional[int] = None   # frames per column (clamped to part.yaml)
    auto_frame: bool = True        # recover baseaddr by 0x80 alignment


class TileProbeGenerator:
    """Base class for one tile type's probe design."""

    #: tilegrid tile type, e.g. "CLBLL_L".  Set in subclasses.
    tile_type: str = ""
    #: Vivado site type to occupy inside the tile, e.g. "SLICEL".
    site_type: str = ""
    #: feature values that map to a cleared / set landmark bit.
    zero_value: str = "0"
    one_value: str = "1"

    calibration: ProbeCalibration = ProbeCalibration()

    def emit_instance(self, inst_name: str, value: str) -> str:
        """Return the Verilog for one probe instance set to ``value``.

        Subclasses MUST override.  ``value`` is ``zero_value`` or ``one_value``.
        Place no LOC here — placement is done from XDC using the site chosen by
        the position provider.
        """
        raise NotImplementedError

    def module_preamble(self) -> str:
        """Optional shared Verilog (functions, localparams) emitted once."""
        return ""


# ---- registry -------------------------------------------------------------

_REGISTRY: Dict[str, Type[TileProbeGenerator]] = {}


def register(cls: Type[TileProbeGenerator]) -> Type[TileProbeGenerator]:
    if not cls.tile_type:
        raise ValueError("%s must set tile_type" % cls.__name__)
    _REGISTRY[cls.tile_type] = cls
    return cls


def get_generator(tile_type: str) -> TileProbeGenerator:
    if tile_type not in _REGISTRY:
        raise KeyError(
            "no probe generator registered for tile type %r; add one under "
            "bitgrid/designgen/tile_lib/ and import it" % tile_type)
    return _REGISTRY[tile_type]()


def registered_tile_types() -> List[str]:
    return sorted(_REGISTRY)


def load_builtin_generators() -> None:
    """Import the bundled tile_lib modules so they self-register."""
    from .tile_lib import clb_carry4  # noqa: F401
