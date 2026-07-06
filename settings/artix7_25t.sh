# Copyright (C) 2017-2026  The Project X-Ray Authors.
#
# Use of this source code is governed by a ISC-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/ISC
#
# SPDX-License-Identifier: ISC
export XRAY_DATABASE="artix7"
# The xc7a25t die is shared with the capacity-capped xc7a12t (see
# settings/artix7/devices.yaml).  Fuzz the fabric on the uncapped 25t;
# 12t parts only need the per-part fuzzers (000/001/075).
export XRAY_PART="xc7a25tcsg325-1"
export XRAY_ROI_FRAMES="0x00000000:0xffffffff"

# All CLB's in part, all BRAM's in part, all DSP's in part.
# tcl queries IOB => don't bother adding
export XRAY_ROI_TILEGRID="SLICE_X0Y0:SLICE_X41Y49 SLICE_X0Y50:SLICE_X17Y74 SLICE_X24Y50:SLICE_X33Y74 SLICE_X0Y75:SLICE_X33Y99 RAMB18_X0Y0:RAMB18_X2Y19 RAMB18_X0Y20:RAMB18_X0Y29 RAMB18_X0Y30:RAMB18_X1Y39 RAMB36_X0Y0:RAMB36_X2Y9 RAMB36_X0Y10:RAMB36_X0Y14 RAMB36_X0Y15:RAMB36_X1Y19 DSP48_X0Y0:DSP48_X1Y39"

export XRAY_EXCLUDE_ROI_TILEGRID=""

# This is used by fuzzers/005-tilegrid/generate_full.py
# (special handling for frame addresses of certain IOIs -- see the script for details).
# This needs to be changed for any new device!
# If you have a FASM mismatch or unknown bits in IOIs, CHECK THIS FIRST.
#
# TODO(verify): placeholder pattern based on other artix7 parts (the low-Y
# anomalous tile of each IO column).  Find the IO column coordinates with:
#   link_design -part xc7a25tcsg325-1
#   puts [lsort [get_tiles -filter {TYPE==LIOI3}]]
#   puts [lsort [get_tiles -filter {TYPE==RIOI3}]]
# then confirm against measured frame addresses after the first 005 run.
export XRAY_IOI3_TILES="LIOI3_X0Y9"

source $(dirname ${BASH_SOURCE[0]})/../utils/environment.sh

env=$(python3 ${XRAY_UTILS_DIR}/create_environment.py)
ENV_RET=$?
if [[ $ENV_RET != 0 ]] ; then
	return $ENV_RET
fi
eval $env
