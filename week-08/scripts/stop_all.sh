#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

"$SCRIPT_DIR/stop_services.sh"
"$SCRIPT_DIR/stop_dashboard.sh"
