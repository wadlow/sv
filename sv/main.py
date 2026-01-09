"""Main entry point for the STIG Viewer application."""

import sys
import signal
import os
from AppKit import NSApplication, NSTimer
from Foundation import NSObject
from PyObjCTools import AppHelper

from .app_delegate import AppDelegate

# Global flag for termination
_terminate_flag = False

# Global flag for debug mode (populate with fake data instead of real STIGs)
DEBUG_MODE = os.environ.get('SV_DEBUG_MODE') == '1'


def signal_handler(signum, frame):
    """Handle interrupt signal (Ctrl-C)."""
    global _terminate_flag
    print("\nReceived interrupt signal. Terminating application...")
    _terminate_flag = True
    # Use os._exit to force immediate termination
    os._exit(0)


class TerminationChecker(NSObject):
    """Helper class to check for termination."""
    
    def checkTermination_(self, timer):
        """Check if we should terminate."""
        global _terminate_flag
        if _terminate_flag:
            app = NSApplication.sharedApplication()
            app.terminate_(None)
        else:
            # Schedule next check
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                0.1, self, 'checkTermination:', None, False
            )


def main():
    """Launch the application."""
    # Set up signal handler for Ctrl-C
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Set the application name to "STIG Viewer" instead of "Python"
        from Foundation import NSProcessInfo
        processInfo = NSProcessInfo.processInfo()
        processInfo.setProcessName_("STIG Viewer")
        
        app = NSApplication.sharedApplication()
        delegate = AppDelegate.alloc().init()
        app.setDelegate_(delegate)
        
        # Activate the app
        app.activateIgnoringOtherApps_(True)
        
        # Set up a timer to periodically check for termination
        # This allows Ctrl-C to work even during the blocking event loop
        checker = TerminationChecker.alloc().init()
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.1, checker, 'checkTermination:', None, False
        )
        
        # Run the event loop
        AppHelper.runEventLoop()
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt. Terminating application...")
        app = NSApplication.sharedApplication()
        app.terminate_(None)
    except Exception as e:
        import traceback
        print(f"Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

