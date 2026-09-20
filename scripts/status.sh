#!/usr/bin/bash
# Back-compat shim: older panel builds called status.sh.
exec /usr/bin/python3 -I "$(cd "$(dirname "$0")" && pwd)/status.py"
