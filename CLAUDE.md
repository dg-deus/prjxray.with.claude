# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Project X-Ray documents the bit-stream format of Xilinx 7-series FPGAs (Artix-7,
Kintex-7, Zynq-7, Spartan-7) plus legacy Spartan-6. It is a reverse-engineering
toolchain: it drives Vivado to emit many designs, turns them into bitstreams,
cross-correlates the bits to discover what each bit does, and records the
findings in a **database** of `.db`/`.json`/`.yaml` files. Those tools and the
database let other software (e.g. F4PGA/Yosys flows) read and write 7-series
bitstreams without proprietary tooling.

The deliverable is the database, not an application. Most "development" here is
either improving the fuzzers/tools that build the database, or improving the
Python/C++ libraries that consume it.

## Big-picture architecture

The data flow has two halves that meet at the database:

```
Vivado designs ─▶ fuzzers ─▶ segmaker/segmatch ─▶ database (.db, tilegrid.json, part.yaml, ...)
                                                        │
FASM text ─▶ FasmAssembler ─▶ frame data (.frm) ─▶ xc7frames2bit ─▶ .bit   (assembly)
.bit ─▶ bitread ─▶ frame data ─▶ FasmDisassembler ─▶ FASM text             (disassembly)
```

Three layers cooperate:

1. **Fuzzers** (`fuzzers/`) — numbered, dependency-ordered design generators that
   produce the database. See "Fuzzer conventions" below. This is where the
   reverse-engineering happens.
2. **Python library** (`prjxray/`) — the importable `prjxray` package that models
   a device and translates between bitstreams and FASM. Key modules:
   - `db.py` (`Database`) loads `tilegrid.json`, `tileconn.json`, `tile_type_*.json`
     and `segbits_*.db` for a device.
   - `grid.py`/`grid_types.py` map tile coordinates to frame addresses per block
     type (CLB/IO/CLK, BRAM, CFG).
   - `segmaker.py` (`Segmaker`) is the core fuzzer primitive: given many specimen
     bitstreams with known feature settings, it tags which bits correspond to
     which feature. Fuzzer `generate.py` scripts drive it.
   - `fasm_assembler.py` / `fasm_disassembler.py` convert FASM ⇄ frame data.
   - `tile_segbits.py`, `connections.py`, `node_model.py` parse the DB and model
     the routing fabric.
3. **C++ library + tools** (`lib/`, `tools/`) — performance-critical bitstream I/O.
   `lib/` builds `libprjxray` (frames, configuration packets, segbits readers,
   per-architecture `xc7series`/`spartan6` definitions). `tools/` builds CLI
   binaries: `bitread` (.bit → frames), `bittool`, `segmatch` (the differential
   solver behind database creation), `xc7frames2bit` (.frm → .bit), `xc7patch`,
   `frame_address_decoder`, `gen_part_base_yaml`, `bits2rbt`.

`utils/` holds Python glue scripts used by fuzzers and maintainers: `checkdb.py`
(DB validation), `sort_db.py` (canonical ordering — run after editing `.db`),
`dbfixup.py`, `mergedb.py`, `fasm2frames.py`, `bit2fasm.py`, `segprint.py`,
`update_parts.py`, `roi_all.py`, etc.

## Environment setup (required before almost anything)

The whole toolchain is parameterized by environment variables (`XRAY_*`). You
must select a device family by sourcing a settings script before running
fuzzers, the database make targets, or many utils:

```bash
source settings/artix7.sh   # or kintex7.sh / zynq7.sh / spartan7.sh
```

This sets `XRAY_DATABASE`, `XRAY_PART`, ROI variables, and (via
`utils/environment.sh`) paths like `XRAY_DIR`, `XRAY_TOOLS_DIR`,
`XRAY_DATABASE_DIR`, and tool aliases (`XRAY_BITREAD`, `XRAY_SEGMATCH`,
`XRAY_MERGEDB`, `XRAY_DBFIXUP`, `XRAY_VIVADO`, ...). Fuzzers reference these, not
hardcoded paths.

**Vivado 2017.2 is the only supported version** for running fuzzers (see README,
Issue #14). Point `XRAY_VIVADO_SETTINGS` at its `settings64.sh`; do **not** source
`settings64.sh` directly — `utils/vivado.sh` sources it in an isolated shell so it
doesn't pollute PATH/LD_LIBRARY_PATH. Building tools and using the Python API
against a downloaded database does **not** require Vivado.

## Common commands

```bash
# One-time / build
make build                 # git submodule update + cmake + build C++ tools into build/
make env                   # create Python venv in env/ and install requirements

# Get a prebuilt database (avoids running fuzzers, which take a very long time)
./download-latest-db.sh    # clones prjxray-db into database/

# Prepare static part info needed by fuzzers
make db-prepare-parts                 # all families
make db-prepare-artix7                # one family

# Run the full database build (slow; needs Vivado)
source settings/artix7.sh
cd fuzzers && make -j$(nproc)

# Run a single fuzzer
source settings/artix7.sh
cd fuzzers/010-clb-lutinit && make -j$(nproc) run

# Validate / canonicalize the database after edits
make db-check-artix7
cd database/artix7 && python3 ../../utils/sort_db.py
```

### Tests

```bash
make test          # runs test-py + test-cpp + test-tools
make test-py       # pytest with --doctest-modules (excludes fuzzers/minitests/experiments/docs)
make test-cpp      # configures with -DPRJXRAY_BUILD_TESTING=ON, builds, runs ctest
make test-tools    # Makefile.tools_tests (end-to-end tool tests)
```

C++ tests are not built by default; enable with `-DPRJXRAY_BUILD_TESTING=ON`.
Choose a debug build with `-DCMAKE_BUILD_TYPE=Debug`. Run a single Python test
inside the env, e.g. `. env/bin/activate && pytest utils/test_fasm2frames.py -k name`.
Run a single C++ test from `build/` with `ctest -R <name> --output-on-failure`.

### Formatting (CI enforces these)

```bash
make format            # cpp + py + tcl + docs + trailing whitespace
make format-cpp        # clang-format-5.0, Chromium style, 8-space tabs (.clang-format)
make format-py         # yapf, pep8-based (.style.yapf)
make check-license     # SPDX header + python shebang/coding checks
```

## Fuzzer conventions

Fuzzers live in `fuzzers/NNN-name/` and are wired together in `fuzzers/Makefile`
via `$(eval $(call fuzzer,<dir>,<deps>,<scope>))`, where `<deps>` are fuzzers that
must finish first and `<scope>` is `part` or `all`. Dependencies matter: e.g.
`000-init-db` → `001-part-yaml` → `005-tilegrid` → most others.

A typical fuzzer contains:
- `Makefile` — sets `N` (number of specimens) and includes a shared template.
- `generate.tcl` — the Vivado flow (synth/place/route/write_bitstream, queries).
- `generate.sh` — orchestrates seeding, Vivado, bit extraction per specimen.
- `generate.py` — post-processes `.bits` via `Segmaker` into `segdata_*.txt`.
- optional `top.v`/`top.py`, `bits.dbf` (bit-fixup rules), `tag_groups.txt`.

Shared makefile templates encode the common pipeline — read these before writing
or debugging a fuzzer:
- `fuzzers/fuzzer.mk` — base targets (`run`, `database`, `pushdb`, `clean`) and
  per-specimen generation.
- `fuzzers/clb.mk`, `fuzzers/clb_ext.mk` — CLB fuzzers (run `segmatch`, build masks).
- `fuzzers/pip_loop.mk`, `fuzzers/int_loop.mk` — iterative loops for PIP/interconnect
  fuzzers that repeat until all PIPs are solved.

The per-specimen pipeline is: generate design → Vivado bitstream → `bitread`
(.bit → .bits) → `segmaker` (bits → tagged segdata) → `segmatch` across specimens
→ `dbfixup`/`maskmerge` → `mergedb` into the database. Output `.db` files are
per tile-type and side (e.g. `segbits_clbll_l.db`, `segbits_clbll_r.db`).

## Database format

The database (`database/<family>/...`, populated by `download-latest-db.sh` or
fuzzers) is mostly text and documented under `docs/dev_database/`:
- `segbits_*.db` — `<feature> <bit_list>`; a bit prefixed `!` must be cleared.
- `mask_*.db` — which bits a tile type uses.
- `ppips_*.db` — pseudo-PIPs tagged `always`/`default`/`hint`.
- `tilegrid.json` — every tile with its frame `baseaddr`/`frames`/`offset`/`words`.
- `part.json`/`part.yaml`, `devices.yaml` — device/part/resource definitions.

After hand-editing any `.db`, run `utils/sort_db.py` to keep canonical ordering
(minimizes diffs) and `make db-check-<family>` to validate.

## Conventions and gotchas

- **Do not run as root.** The top-level `Makefile` aborts for uid 0 unless
  `ALLOW_ROOT` is set (CI sets it).
- **SPDX headers required.** Every `.sh`/`.py`/`Makefile`/`.tcl` needs
  `SPDX-License-Identifier: ISC`; `check_license.sh` enforces it (skips
  `third_party`, `database`, `env`, `build`).
- **Python files** must declare `# coding: utf-8`; executable ones need
  `#!/usr/bin/env python3` (`check_python_scripts.sh`).
- **Submodules** (third_party: abseil-cpp, cctz, googletest, gflags, yaml-cpp;
  plus fasm, python-sdf-timing, yosys) are required — `make build` runs
  `git submodule update --init --recursive`.
- The `database/` contents are treated as generated/vendored; don't reformat them
  with the source formatters (use `sort_db.py`).
- DCO sign-off (`git commit -s`) is required on commits to upstream; CONTRIBUTING.md
  is generated from README.md via `.github/scripts/update-contributing.py`.
- CI (`.github/workflows/Pipeline.yml`, `Automerge.yml`) builds tools + env,
  builds/validates the database per family on self-hosted runners with Vivado,
  and runs the format/license checks.
