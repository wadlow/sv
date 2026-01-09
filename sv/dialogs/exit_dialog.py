"""Exit confirmation dialog."""

from AppKit import NSAlert


class ExitDialog:
    """Exit confirmation dialog."""
    
    @staticmethod
    def show() -> bool:
        """
        Show exit confirmation dialog.
        
        Returns:
            True if user wants to exit, False otherwise
        """
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Are you sure you want to exit?")
        alert.setInformativeText_("Any unsaved changes will be lost.")
        alert.addButtonWithTitle_("Yes")
        alert.addButtonWithTitle_("No")
        alert.setAlertStyle_(1)  # NSAlertStyleWarning
        
        result = alert.runModal()
        # NSAlertFirstButtonReturn is 1000, NSAlertSecondButtonReturn is 1001
        # First button (Yes) returns 1000, second button (No) returns 1001
        # Using numeric value since constants may not be directly accessible
        return result == 1000  # First button (Yes) was clicked

