# Copyright (C) 2017-2026  The Project X-Ray Authors.
#
# Use of this source code is governed by a ISC-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/ISC
#
# SPDX-License-Identifier: ISC
#
# Per-part settings for the xc7a12t (csg325 package).
#
# IMPORTANT: the xc7a12t is the capacity-capped twin of the xc7a25t
# (same die, see settings/artix7/devices.yaml).  The fabric database
# CANNOT be fuzzed with this part: Vivado caps synthesis at 20 block
# RAMs, so the 005-tilegrid specimens (one RAMB18 per grid site, 45+
# instances) fail with Synth 8-5833.  Fuzz the fabric with
# settings/artix7_25t.sh instead; this device shares that database
# through the devices.yaml fabric mapping.
#
# Use this file only for the per-part fuzzers:
#   source settings/artix7_12t.sh
#   make -C fuzzers roi_only    # 000-init-db, 001-part-yaml, 075-pins
#
# Do NOT use the `all` or `part_only` targets with this file -- both
# include fuzzers (005, 074) that must run on the uncapped 25t part.
export XRAY_DATABASE="artix7"
export XRAY_PART="xc7a12tcsg325-3"
export XRAY_ROI_FRAMES="0x00000000:0xffffffff"

source $(dirname ${BASH_SOURCE[0]})/../utils/environment.sh

env=$(python3 ${XRAY_UTILS_DIR}/create_environment.py)
ENV_RET=$?
if [[ $ENV_RET != 0 ]] ; then
	return $ENV_RET
fi
eval $env
