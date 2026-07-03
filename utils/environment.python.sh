# Copyright (C) 2017-2020  The Project X-Ray Authors.
#
# Use of this source code is governed by a ISC-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/ISC
#
# SPDX-License-Identifier: ISC

# Suppress the following warnings;
# - env/lib/python3.7/distutils/__init__.py:4: DeprecationWarning: the imp module is deprecated in favour of importlib; see the module's documentation for alternative uses
export PYTHONWARNINGS=ignore::DeprecationWarning:distutils

# Scripts import top-level repo packages (utils, prjxray) directly, e.g.
# fuzzers/run_fuzzer.py does "from utils.create_environment import ...".
# Older pip exposed the repo root via the "-e ." editable install; modern
# pip (PEP 660) only exposes the declared "prjxray" package, so put the
# repo root on PYTHONPATH explicitly.
case ":${PYTHONPATH:-}:" in
    *":${XRAY_DIR}:"*) ;;
    *) export PYTHONPATH="${XRAY_DIR}${PYTHONPATH:+:${PYTHONPATH}}" ;;
esac
