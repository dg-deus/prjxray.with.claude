#!/usr/bin/env python3
"""
Generate a prjxray-style tileconn.json using only RapidWright APIs.

tileconn.json describes how wires of neighboring tiles are stitched
together into nodes.  Each entry relates a *pair of tile types* at a given
relative grid offset, and lists the wire name pairs that belong to the same
node whenever those two tile types appear at that offset:

    [
        {
            "grid_deltas": [<dx>, <dy>],
            "tile_types": ["<TILE_TYPE1>", "<TILE_TYPE2>"],
            "wire_pairs": [["<wire in tile1>", "<wire in tile2>"], ...]
        },
        ...
    ]

RapidWright already models the full device routing graph (Tile, Wire,
Node), so instead of parsing raw Vivado dumps like
fuzzers/074-dump_all/generate_grid.py does, we can simply walk every node
in the device and record which wire pairs cross tile boundaries.

prjxray stores only the "directly connected" wire pairs of a node (a
spanning tree), not the full clique of all its wires.  This script
approximates that with a minimum spanning tree over the node's wires using
manhattan grid distance as the edge weight, which strongly prefers pairs
in adjacent tiles.  The resulting file reconstructs exactly the same nodes
as the prjxray database, although the particular spanning pairs chosen for
multi-tile nodes may differ from the ones prjxray picked.

Coordinate note: RapidWright's Tile.getColumn()/getRow() match Vivado's
GRID_POINT_X/GRID_POINT_Y tile properties, which are exactly the
grid_x/grid_y used by prjxray's tilegrid.json, so grid_deltas are computed
the same way.

Usage:
    pip install rapidwright
    python3 rapidwright_tileconn.py --part xc7a35t --output tileconn.json

Add --verify to additionally check that every generated (tile pair, wire
pair) rule holds at *every* occurrence of that tile-type pattern in the
grid, i.e. that the file is safe to apply purely by pattern matching.
"""

import argparse
import json


def wire_sort_key(wire):
    tile = wire.getTile()
    return (
        str(tile.getTileTypeEnum().name()),
        str(wire.getWireName()),
        tile.getColumn(),
        tile.getRow(),
    )


def spanning_wire_pairs(node):
    """Yield a minimal set of wire pairs connecting all wires of a node.

    Kruskal's MST with manhattan grid distance as the weight, so wire
    pairs in the same or adjacent tiles are preferred over long-distance
    pairs, mirroring prjxray's "directly connected" pairs.
    """
    wires = list(node.getAllWiresInNode())
    if len(wires) < 2:
        return

    edges = []
    for i, wire1 in enumerate(wires):
        tile1 = wire1.getTile()
        for j in range(i + 1, len(wires)):
            tile2 = wires[j].getTile()
            dist = abs(tile1.getColumn() - tile2.getColumn()) + \
                abs(tile1.getRow() - tile2.getRow())
            edges.append((dist, i, j))
    edges.sort()

    parent = list(range(len(wires)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for _, i, j in edges:
        root_i, root_j = find(i), find(j)
        if root_i != root_j:
            parent[root_i] = root_j
            yield wires[i], wires[j]


def add_pair(tileconn, wire1, wire2):
    # Canonical ordering, same as update_tile_conn() in
    # fuzzers/074-dump_all/generate_grid.py.
    if wire_sort_key(wire1) > wire_sort_key(wire2):
        wire1, wire2 = wire2, wire1

    tile1 = wire1.getTile()
    tile2 = wire2.getTile()
    key = (
        str(tile1.getTileTypeEnum().name()),
        str(tile2.getTileTypeEnum().name()),
        tile2.getColumn() - tile1.getColumn(),
        tile2.getRow() - tile1.getRow(),
    )
    tileconn.setdefault(key, set()).add(
        (str(wire1.getWireName()), str(wire2.getWireName())))


def generate_tileconn(device):
    from com.xilinx.rapidwright.device import Node

    tileconn = {}
    tiles = list(device.getAllTiles())
    for tile_idx, tile in enumerate(tiles):
        if tile_idx % 1000 == 0:
            print('tile {}/{}'.format(tile_idx, len(tiles)))

        for wire_idx in range(tile.getWireCount()):
            node = Node.getNode(tile, wire_idx)
            if node is None:
                continue

            # A node is visible from every wire it contains; only process
            # it from its base wire so each node is handled exactly once.
            if node.getTile() != tile or node.getWireIndex() != wire_idx:
                continue

            for wire1, wire2 in spanning_wire_pairs(node):
                add_pair(tileconn, wire1, wire2)

    entries = []
    for (type1, type2, dx, dy), pairs in sorted(tileconn.items()):
        entries.append(
            {
                'grid_deltas': [dx, dy],
                'tile_types': [type1, type2],
                'wire_pairs': sorted(list(pair) for pair in pairs),
            })

    return entries


def verify_tileconn(device, entries):
    """Check that every rule holds at every matching grid location.

    tileconn.json is applied by pattern matching over the whole grid, so a
    (tile_types, grid_deltas, wire_pair) rule is only sound if the two
    wires are on the same node for *every* occurrence of the pattern.
    """
    from com.xilinx.rapidwright.device import Node

    tiles_by_type = {}
    for tile in device.getAllTiles():
        tiles_by_type.setdefault(
            str(tile.getTileTypeEnum().name()), []).append(tile)

    errors = 0
    for entry in entries:
        type1, type2 = entry['tile_types']
        dx, dy = entry['grid_deltas']

        for tile1 in tiles_by_type[type1]:
            row = tile1.getRow() + dy
            col = tile1.getColumn() + dx
            if not (0 <= row < device.getRows()
                    and 0 <= col < device.getColumns()):
                continue

            tile2 = device.getTile(row, col)
            if tile2 is None or str(tile2.getTileTypeEnum().name()) != type2:
                continue

            for wire1, wire2 in entry['wire_pairs']:
                node1 = Node.getNode(tile1, tile1.getWireIndex(wire1))
                node2 = Node.getNode(tile2, tile2.getWireIndex(wire2))
                if node1 is None or node2 is None or not node1.equals(node2):
                    print(
                        'ERROR: {} {}/{} <-> {}/{} not connected'.format(
                            entry['grid_deltas'], tile1.getName(), wire1,
                            tile2.getName(), wire2))
                    errors += 1

    return errors


def main():
    parser = argparse.ArgumentParser(
        description='Generate a prjxray-style tileconn.json via RapidWright.'
    )
    parser.add_argument(
        '--part', default='xc7a35t', help='Part or device name')
    parser.add_argument('--output', default='tileconn.json')
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Re-check every rule at every grid location (slow)')
    args = parser.parse_args()

    import rapidwright  # noqa: F401 -- starts the JVM
    from com.xilinx.rapidwright.device import Device

    device = Device.getDevice(args.part)
    print('Loaded device {} ({} rows x {} cols)'.format(
        device.getName(), device.getRows(), device.getColumns()))

    entries = generate_tileconn(device)
    print('{} tile type/delta entries'.format(len(entries)))

    with open(args.output, 'w') as f:
        json.dump(entries, f, indent=4, sort_keys=True)
        f.write('\n')

    if args.verify:
        errors = verify_tileconn(device, entries)
        print('verification complete, {} errors'.format(errors))
        if errors:
            exit(1)


if __name__ == '__main__':
    main()
