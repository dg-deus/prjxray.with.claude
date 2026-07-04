# coding: utf-8
#
# SPDX-License-Identifier: ISC
"""
Package B: provide tile name -> grid (X, Y) and a placeable site per tile.

Two providers:

* :class:`RapidWrightProvider` queries a device model through the ``rapidwright``
  Python package (jpype-backed).  Use this when RapidWright is installed.
* :class:`FileProvider` reads a dumped ``tiles.txt`` (the same columnar format
  prjxray's 005-tilegrid produces:
  ``<type> <name> <grid_x> <grid_y> <skip> [<clock_region> <site_type> <site> <prohibited> ...]``).
  Use this when RapidWright is unavailable — dump the file once from Vivado.

Both expose :meth:`tiles_of_type` and :meth:`column_of`, which select the run of
tiles of one type that share a grid column (constant X), sorted bottom-to-top by
grid Y — exactly the column we toggle in one design.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class TilePos:
    name: str
    type: str
    grid_x: int
    grid_y: int
    site: Optional[str] = None       # a placeable site of the wanted site_type
    clock_region: Optional[str] = None


class TilePositionProvider:
    def all_tiles(self) -> List[TilePos]:
        raise NotImplementedError

    def tiles_of_type(self, tile_type: str) -> List[TilePos]:
        return [t for t in self.all_tiles() if t.type == tile_type]

    def column_of(self, tile_type: str, grid_x: int) -> List[TilePos]:
        """Tiles of ``tile_type`` in grid column ``grid_x``, bottom-to-top."""
        col = [t for t in self.tiles_of_type(tile_type) if t.grid_x == grid_x]
        col.sort(key=lambda t: t.grid_y)
        return col

    def columns_for_type(self, tile_type: str) -> List[int]:
        return sorted({t.grid_x for t in self.tiles_of_type(tile_type)})


class FileProvider(TilePositionProvider):
    """Read tiles from a prjxray-style ``tiles.txt`` dump."""

    def __init__(self, path: str, want_site_type: Optional[str] = None):
        self._tiles: List[TilePos] = []
        self._load(path, want_site_type)

    def _load(self, path: str, want_site_type: Optional[str]) -> None:
        with open(path) as f:
            for line in f:
                rec = line.split()
                if len(rec) < 5:
                    continue
                ttype, name, gx, gy, _skip = rec[0:5]
                site = None
                clock_region = None
                if len(rec) >= 6:
                    clock_region = rec[5] if rec[5] != "NA" else None
                    # trailing triples: site_type site_name prohibited
                    for i in range(6, len(rec) - 2, 3):
                        st, sn = rec[i], rec[i + 1]
                        if want_site_type is None or st == want_site_type:
                            site = sn
                            break
                self._tiles.append(
                    TilePos(name=name, type=ttype, grid_x=int(gx),
                            grid_y=int(gy), site=site,
                            clock_region=clock_region))

    def all_tiles(self) -> List[TilePos]:
        return self._tiles


class RapidWrightProvider(TilePositionProvider):
    """Query tile/site positions from RapidWright (lazy import)."""

    def __init__(self, part: str, want_site_type: Optional[str] = None):
        self.part = part
        self.want_site_type = want_site_type
        self._tiles: Optional[List[TilePos]] = None

    def _load(self) -> List[TilePos]:
        try:
            from rapidwright.device import Device  # type: ignore
        except Exception as e:  # pragma: no cover - depends on environment
            raise RuntimeError(
                "RapidWright Python bindings not available (%s). Install the "
                "'rapidwright' package or use FileProvider with a tiles.txt "
                "dump." % e)

        dev = Device.getDevice(self.part)
        tiles: List[TilePos] = []
        for tile in dev.getAllTiles():
            site = None
            for s in tile.getSites():
                st = str(s.getSiteTypeEnum())
                if self.want_site_type is None or st == self.want_site_type:
                    site = s.getName()
                    break
            tiles.append(
                TilePos(
                    name=tile.getName(),
                    type=str(tile.getTileTypeEnum()),
                    grid_x=tile.getColumn(),
                    grid_y=tile.getRow(),
                    site=site,
                ))
        return tiles

    def all_tiles(self) -> List[TilePos]:
        if self._tiles is None:
            self._tiles = self._load()
        return self._tiles
