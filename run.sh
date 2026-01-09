#!/bin/bash
# Launcher script for STIG Viewer
cd "$(dirname "$0")"

# Parse command line flags
for arg in "$@"; do
    case $arg in
        --d)
            export SV_DEBUG_MODE=1
            ;;
        --ckl)
            export SV_CKL_DEBUG=1
            ;;
    esac
done

python3 -m sv.main

