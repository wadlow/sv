#!/bin/bash
# Launcher script for STIG Viewer
cd "$(dirname "$0")"

# Parse command line flags
DEBUG_MODE=0
for arg in "$@"; do
    case $arg in
        --d)
            export SV_DEBUG_MODE=1
            DEBUG_MODE=1
            ;;
        --ckl)
            export SV_CKL_DEBUG=1
            ;;
    esac
done

# Run with or without debug output
if [ "$DEBUG_MODE" -eq 1 ]; then
    # Debug mode: show all output
    python3 -m sv.main
else
    # Normal mode: suppress stdout (debug messages), keep stderr (errors)
    python3 -m sv.main >/dev/null
fi

