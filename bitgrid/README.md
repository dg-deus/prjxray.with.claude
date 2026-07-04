# bitgrid

An independent, **Python-only** reimplementation of the logic that computes the
`bits` block (`baseaddr`, `frames`, `offset`, `words`) of `tilegrid.json` for
Xilinx 7-series FPGAs — the part of Project X-Ray's `005-tilegrid` /
`001-part-yaml` fuzzers, rebuilt as a small standalone library.

It depends only on `pyyaml` (plus optional `rapidwright`). Vivado is only needed
to *generate* the input bitstreams; all parsing and computation is pure Python.

## The idea in one picture

Every configurable tile owns a rectangle of the bitstream:

```
   frame baseaddr ──┐         101 words per frame
                    v       offset ┐   ┌ offset+words
   baseaddr      →  ┌─────────────[xx]──────────────┐
   ...              │             [xx]               │  words = rectangle height
   baseaddr+frames-1└─────────────[xx]──────────────┘
                     frames = rectangle width (consecutive frame addresses)
```

* `baseaddr` — column base frame (always a multiple of `0x80`)
* `frames`   — number of consecutive frames in the column
* `offset`   — first 32-bit word the tile uses inside each frame
* `words`    — number of words the tile uses

## Packages

| Pkg | Module | Role |
|-----|--------|------|
| A | `bitgrid.partgen`  | Parse a **PERFRAMECRC** bitstream, count frames per configuration column, emit a prjxray-format `part.yaml`. |
| B | `bitgrid.designgen`| Generate `top.v` + `.xdc` + Vivado `.tcl` that place one probe primitive per tile in a column (reference vs probe). |
| C | `bitgrid.bitsgen`  | Diff the reference/probe bitstreams, attribute each toggled bit to a tile, and compute `{baseaddr, frames, offset, words}`. |
| D | `bitgrid.verify`   | Build the part string from `--device`/`--package`, compare computed bits against a reference `tilegrid.json`, and print the pipeline. |

### How each field is found

* **`frames`** (package A): a PERFRAMECRC bitstream writes every frame preceded
  by an explicit Frame Address Register (FAR) write. We collect all FAR values,
  group them by `(block_type, half, row, column)`, and take `max(minor)+1`.
* **`baseaddr`** (package C): round any observed frame address down to the
  nearest `0x80` (the column boundary). The remainder is the landmark's frame
  delta.
* **`offset`** (package C): observed word minus the landmark's known word delta
  (`dword`); per-tile offsets form a contiguous ladder down the column.
* **`words`** (package C): either a frozen per-tile-type constant, or *derived*
  as the most common spacing between consecutive offsets in the ladder (the lone
  HCLK `+1` step is ignored by taking the mode).

The frame address bit layout (`block[25:23] | half[22] | row[21:17] |
column[16:7] | minor[6:0]`) lives in `bitgrid/frame_address.py`.

## End-to-end usage

```bash
pip install -e .           # or: PYTHONPATH=. for in-place use

# B) emit reference + probe designs for one column of a tile type
python -m bitgrid.designgen --tile-type CLBLL_L --part xc7a12tcpg238-1 \
    --rapidwright --out build               # or --tiles-file tiles.txt

# (run build/ref.tcl, build/probe.tcl, and a PERFRAMECRC design in Vivado)

# A) frames per column -> part.yaml
python -m bitgrid.partgen build/perframecrc.bit -o build/part.yaml --check

# C) compute the bits entries
python -m bitgrid.bitsgen --ref build/ref.bit --probe build/probe.bit \
    --index build/index.csv --part-yaml build/part.yaml -o build/bits.json

# D) compare against a reference tilegrid.json
python -m bitgrid.verify --device xc7a12t --package cpg238-1 \
    --compare build/bits.json /path/to/prjxray-db/artix7/tilegrid.json
```

## Adding a tile type (package B)

Probe generators are pluggable. Copy `bitgrid/designgen/tile_lib/_template.py`,
set `tile_type` / `site_type`, implement `emit_instance` with a primitive that
has one clearly toggled feature, and (once known) freeze the
`(dframe, dword, dbit, words, frames)` calibration. See `clb_carry4.py` for a
worked CLB/CARRY4 example mirroring prjxray's `005-tilegrid/clb` fuzzer.

## Status / limitations

* Implemented and unit-tested: frame-address codec, packet/FAR/FDRI parser,
  frame counting → `part.yaml`, bit diffing, baseaddr/offset/words computation,
  and the verify comparator (`pytest tests/`).
* Stubbed (need external tools, untested here): the Vivado runner
  (`designgen/vivado.py`) and the RapidWright position provider
  (`designgen/tile_positions.py:RapidWrightProvider`). A `FileProvider` reading a
  prjxray-style `tiles.txt` works without RapidWright.
* The "regular column" model (shared frames, word-offset ladder) covers
  CLB/INT/BRAM/DSP-style columns. Irregular tiles (BRAM's second `BLOCK_RAM`
  rectangle, IOB/IOI `_SING` half-tiles, REBUF, HCLK aliases) need the same
  per-type special-casing prjxray's `generate_full.py` applies — not yet ported.

## Tests

```bash
PYTHONPATH=.:tests python -m pytest tests/ -q
```
