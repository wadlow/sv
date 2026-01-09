"""Preferences dialog window."""

from AppKit import NSWindow, NSWindowStyleMask, NSRect, NSView, NSTextField, NSButton, NSLayoutConstraint, NSLayoutAttributeLeading, NSLayoutAttributeTop, NSLayoutAttributeTrailing, NSLayoutAttributeBottom, NSLayoutRelationEqual


class PreferencesDialog:
    """Preferences dialog window."""
    
    def __init__(self):
        """Initialize the preferences dialog."""
        self.window = None
        self._create_window()
    
    def _create_window(self):
        """Create the preferences window."""
        # Create window
        frame = NSRect((100, 100), (400, 300))
        style_mask = 1 | 2  # NSTitledWindowMask | NSClosableWindowMask
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            style_mask,
            2,  # NSBackingStoreBuffered
            False
        )
        self.window.setTitle_("Preferences")
        self.window.setReleasedWhenClosed_(False)
        
        # Create content view
        content_view = NSView.alloc().initWithFrame_(frame)
        self.window.setContentView_(content_view)
        
        # Add a simple label for now (basic implementation)
        label = NSTextField.alloc().initWithFrame_(NSRect((20, 250), (360, 30)))
        label.setStringValue_("Preferences")
        label.setBordered_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        content_view.addSubview_(label)
    
    def show(self):
        """Show the preferences window."""
        if self.window:
            self.window.center()
            self.window.makeKeyAndOrderFront_(None)
    
    def close(self):
        """Close the preferences window."""
        if self.window:
            self.window.close()

