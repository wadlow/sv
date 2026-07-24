#!/bin/bash
# Launcher script for STIG Viewer
cd "$(dirname "$0")"

show_help() {
    cat <<'EOF'
Usage: ./run.sh [options]

Options:
  --d       Enable debug mode (show debug messages on the console)
  --ckl     Enable CKL-specific debugging
  --cls     Open Compare Loaded STIGs tab on startup
  --i       Start interactive CLI (sv> prompt on stderr)
  -h, --help
            Show this help message and exit

Notes:
  Without --d, debug messages are suppressed. Errors still go to stderr.
  Combine flags as needed, for example: ./run.sh --i --cls
EOF
}

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Parse command line flags
DEBUG_MODE=0
INTERACTIVE_MODE=0
for arg in "$@"; do
    case $arg in
        -h|--help)
            show_help
            exit 0
            ;;
        --d)
            export SV_DEBUG_MODE=1
            DEBUG_MODE=1
            ;;
        --ckl)
            export SV_CKL_DEBUG=1
            ;;
        --cls)
            export SV_COMPARE_LOADED_STIGS=1
            ;;
        --i)
            export SV_INTERACTIVE=1
            INTERACTIVE_MODE=1
            ;;
    esac
done

# Run with or without debug output
if [ "$DEBUG_MODE" -eq 1 ] || [ "$INTERACTIVE_MODE" -eq 1 ]; then
    # Debug or interactive mode: keep stdout/stderr for CLI and debug messages
    python3 -m sv.main
else
    # Normal mode: suppress stdout (debug messages), keep stderr (errors)
    python3 -m sv.main >/dev/null
fi

