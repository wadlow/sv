"""Debug utility for conditional printing."""

import os

# Check if debug mode is enabled via environment variable
DEBUG_MODE = os.environ.get('SV_DEBUG_MODE') == '1'


def debug_print(*args, **kwargs):
    """Print debug message only if debug mode is enabled.
    
    Usage:
        from sv.utils.debug import debug_print
        debug_print("This only prints if --d flag is used")
    """
    if DEBUG_MODE:
        print(*args, **kwargs)
