# coding: utf-8
#
# SPDX-License-Identifier: ISC
"""
``python -m bitgrid.designgen`` — emit reference+probe designs for one column.

Produces, under an output directory:
    ref.v / probe.v   — Verilog with the feature cleared / set in every tile
    probe.xdc         — LOC constraints (shared by both)
    index.csv         — instance -> tile/site/value map (for package C)
    ref.tcl / probe.tcl  — Vivado build scripts (PERFRAMECRC)

Then either run the .tcl yourself, or pass --run to invoke Vivado.
"""

from __future__ import annotations

import argparse
import os
import sys

from .tile_positions import FileProvider, RapidWrightProvider
from .tiles import get_generator, load_builtin_generators, registered_tile_types
from .verilog import build_top_verilog
from .vivado import build_tcl, run_vivado
from .xdc import build_index_csv, build_xdc


def main(argv=None) -> int:
    load_builtin_generators()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tile-type", required=True,
                   help="tile type to probe (registered: %s)" %
                   ", ".join(registered_tile_types()) or "<none>")
    p.add_argument("--part", required=True, help="e.g. xc7a35tcpg236-1")
    p.add_argument("--out", default="build", help="output directory")
    p.add_argument("--grid-x", type=int, default=None,
                   help="grid column to probe (default: first column found)")

    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--tiles-file", help="prjxray-style tiles.txt dump")
    src.add_argument("--rapidwright", action="store_true",
                     help="query positions from RapidWright")

    p.add_argument("--run", action="store_true", help="invoke Vivado on the tcl")
    p.add_argument("--vivado", default="vivado", help="Vivado executable")
    args = p.parse_args(argv)

    gen = get_generator(args.tile_type)

    if args.tiles_file:
        provider = FileProvider(args.tiles_file, want_site_type=gen.site_type)
    else:
        provider = RapidWrightProvider(args.part, want_site_type=gen.site_type)

    cols = provider.columns_for_type(args.tile_type)
    if not cols:
        print("error: no tiles of type %s found" % args.tile_type,
              file=sys.stderr)
        return 1
    grid_x = args.grid_x if args.grid_x is not None else cols[0]
    column = provider.column_of(args.tile_type, grid_x)
    print("probing %d %s tiles in grid column x=%d" %
          (len(column), args.tile_type, grid_x), file=sys.stderr)

    ref_vals = [gen.zero_value] * len(column)
    probe_vals = [gen.one_value] * len(column)

    os.makedirs(args.out, exist_ok=True)

    def w(name, text):
        path = os.path.join(args.out, name)
        with open(path, "w") as f:
            f.write(text)
        return path

    ref_v = w("ref.v", build_top_verilog(gen, column, ref_vals))
    probe_v = w("probe.v", build_top_verilog(gen, column, probe_vals))
    xdc = w("probe.xdc", build_xdc(column))
    w("index.csv", build_index_csv(column, probe_vals))
    ref_tcl = w("ref.tcl", build_tcl(args.part, ref_v, xdc,
                                     os.path.join(args.out, "ref.bit")))
    probe_tcl = w("probe.tcl", build_tcl(args.part, probe_v, xdc,
                                         os.path.join(args.out, "probe.bit")))

    if args.run:
        for tcl in (ref_tcl, probe_tcl):
            rc = run_vivado(tcl, vivado=args.vivado, cwd=args.out)
            if rc != 0:
                print("error: Vivado failed on %s" % tcl, file=sys.stderr)
                return rc
    else:
        print("wrote designs to %s/ — run ref.tcl and probe.tcl in Vivado"
              % args.out, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
