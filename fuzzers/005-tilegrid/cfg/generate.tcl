# Copyright (C) 2017-2026  The Project X-Ray Authors
#
# Use of this source code is governed by a ISC-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/ISC
#
# SPDX-License-Identifier: ISC
source "$::env(XRAY_DIR)/utils/utils.tcl"

# Same flow as utils.tcl generate_top, with one addition: this fuzzer
# locates the CFG_CENTER frame address by toggling JTAG_CHAIN on a
# BSCANE2 pinned to BSCAN_X0Y0.  Vivado 2020.2 enforces that the
# JTAG_CHAIN value matches the BSCAN site row (DRC PDRC-2); 2017.2 did
# not.  The mismatch is intentional here, so demote the check before
# bitgen (fall back to disabling it if the severity is locked).
create_project -force -part $::env(XRAY_PART) design design
read_verilog top.v
synth_design -top top

set_property CFGBVS VCCO [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property BITSTREAM.GENERAL.PERFRAMECRC YES [current_design]

place_design
route_design

write_checkpoint -force design.dcp

if { [catch { set_property SEVERITY {Warning} [get_drc_checks PDRC-2] } err] } {
    puts "WARNING: could not demote PDRC-2 ($err), disabling it instead"
    set_property IS_ENABLED 0 [get_drc_checks PDRC-2]
}
write_bitstream -force design.bit
