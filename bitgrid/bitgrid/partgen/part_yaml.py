# coding: utf-8
#
# SPDX-License-Identifier: ISC
"""
Package A core: build a prjxray-format ``part.yaml`` from counted columns.

The structure consumed by prjxray's tilegrid step is::

    global_clock_regions:
      <top|bottom>:
        rows:
          <row>:
            configuration_buses:
              <CLB_IO_CLK|BLOCK_RAM>:
                configuration_columns:
                  <column>: {frame_count: <n>}

We reproduce that tree so the output drops into the same downstream tooling.
``idcode`` is included when it was present in the bitstream.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import yaml

from ..frame_address import BlockType
from .frames import ColumnInfo


def build_part_dict(columns: List[ColumnInfo],
                    idcode: Optional[int] = None) -> dict:
    gcr: Dict[str, dict] = {}
    for col in columns:
        half = gcr.setdefault(col.row_half.yaml_name, {"rows": {}})
        row = half["rows"].setdefault(col.row, {"configuration_buses": {}})
        bus = row["configuration_buses"].setdefault(
            col.block_type.bus_name, {"configuration_columns": {}})
        bus["configuration_columns"][col.column] = {
            "frame_count": col.frame_count
        }

    part: dict = {"global_clock_regions": gcr}
    if idcode is not None:
        part["idcode"] = idcode
    return part


def dump_part_yaml(columns: List[ColumnInfo],
                   idcode: Optional[int] = None) -> str:
    return yaml.safe_dump(
        build_part_dict(columns, idcode),
        default_flow_style=False,
        sort_keys=True)
