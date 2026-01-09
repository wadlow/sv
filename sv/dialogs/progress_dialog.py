"""Progress dialog for long-running operations."""

from AppKit import (
    NSWindow, NSRect, NSView, NSTextField, NSProgressIndicator,
    NSWindowStyleMask, NSBackingStoreBuffered
)
from Foundation import NSObject
from PyObjCTools import AppHelper


class ProgressDialog:
    """Progress dialog window."""
    
    def __init__(self, title="Processing...", message="Please wait"):
        """Initialize the progress dialog."""
        self.window = None
        self.progress_indicator = None
        self.message_field = None
        self.counter_field = None
        self.title = title
        self.message = message
        self._create_window()
    
    def _create_window(self):
        """Create the progress window."""
        # Create window - taller to accommodate multi-line messages
        window_frame = NSRect((100, 100), (450, 150))
        style_mask = 1 | 2  # NSTitledWindowMask | NSClosableWindowMask
        
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            window_frame,
            style_mask,
            2,  # NSBackingStoreBuffered
            False
        )
        self.window.setTitle_(self.title)
        self.window.setReleasedWhenClosed_(False)
        self.window.setLevel_(10)  # NSFloatingWindowLevel - keep on top
        
        # Create content view
        content_view = self.window.contentView()
        bounds = content_view.bounds()
        
        # Message field - for filename
        message_frame = NSRect((20, 100), (410, 30))
        self.message_field = NSTextField.alloc().initWithFrame_(message_frame)
        self.message_field.setStringValue_(self.message)
        self.message_field.setBordered_(False)
        self.message_field.setDrawsBackground_(False)
        self.message_field.setEditable_(False)
        self.message_field.setSelectable_(False)
        self.message_field.setAutoresizingMask_(0x12)  # NSViewWidthSizable | NSViewHeightSizable
        content_view.addSubview_(self.message_field)
        
        # Counter field - for progress counter
        counter_frame = NSRect((20, 70), (410, 25))
        self.counter_field = NSTextField.alloc().initWithFrame_(counter_frame)
        self.counter_field.setStringValue_("")
        self.counter_field.setBordered_(False)
        self.counter_field.setDrawsBackground_(False)
        self.counter_field.setEditable_(False)
        self.counter_field.setSelectable_(False)
        # Make counter text bold
        from AppKit import NSFont
        bold_font = NSFont.boldSystemFontOfSize_(12)
        self.counter_field.setFont_(bold_font)
        self.counter_field.setAutoresizingMask_(0x12)  # NSViewWidthSizable | NSViewHeightSizable
        content_view.addSubview_(self.counter_field)
        
        # Progress indicator
        progress_frame = NSRect((20, 30), (360, 20))
        self.progress_indicator = NSProgressIndicator.alloc().initWithFrame_(progress_frame)
        self.progress_indicator.setStyle_(1)  # NSProgressIndicatorBarStyle
        self.progress_indicator.setIndeterminate_(True)
        self.progress_indicator.setAutoresizingMask_(0x12)  # NSViewWidthSizable | NSViewHeightSizable
        self.progress_indicator.startAnimation_(None)
        content_view.addSubview_(self.progress_indicator)
    
    def show(self):
        """Show the progress window."""
        if self.window:
            self.window.center()
            self.window.makeKeyAndOrderFront_(None)
            self.window.orderFrontRegardless()
            # Process events to ensure window appears
            from AppKit import NSApplication
            app = NSApplication.sharedApplication()
            app.updateWindows()
    
    def set_message(self, message: str):
        """Update the progress message."""
        print(f"ProgressDialog.set_message called with: {repr(message)}")  # Debug
        
        # Split message on newline to separate filename from counter
        lines = message.split('\n', 1)
        
        if self.message_field:
            print(f"Setting message field to: {repr(lines[0])}")  # Debug
            self.message_field.setStringValue_(lines[0])
            self.message_field.setNeedsDisplay_(True)
        
        if self.counter_field and len(lines) > 1:
            print(f"Setting counter field to: {repr(lines[1])}")  # Debug
            self.counter_field.setStringValue_(lines[1])
            self.counter_field.setNeedsDisplay_(True)
        elif self.counter_field:
            # Clear counter if no second line
            self.counter_field.setStringValue_("")
        
        # Process events to update display
        from AppKit import NSApplication, NSDate, NSDefaultRunLoopMode
        app = NSApplication.sharedApplication()
        app.updateWindows()
        # Process pending events to keep UI responsive
        date = NSDate.dateWithTimeIntervalSinceNow_(0.01)
        app.nextEventMatchingMask_untilDate_inMode_dequeue_(
            0xFFFFFFFF,  # NSAnyEventMask
            date,
            NSDefaultRunLoopMode,
            False
        )
        print("ProgressDialog.set_message: Display updated")  # Debug
    
    def close(self):
        """Close the progress window."""
        if self.window:
            self.window.close()
            self.window = None

