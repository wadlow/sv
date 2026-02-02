"""Dialog for displaying Check Text comparison results."""

from AppKit import (
    NSWindow, NSView, NSRect, NSButton, NSScrollView, NSTextView,
    NSTitledWindowMask, NSClosableWindowMask, NSMiniaturizableWindowMask,
    NSViewWidthSizable, NSViewHeightSizable, NSColor, NSFont
)
from Foundation import NSObject
import objc


class CompareCheckTextDialog:
    """Dialog showing comparison between Finding Details and Check Text."""
    
    def __init__(self):
        """Initialize the dialog."""
        self.window = None
        self.text_view = None
    
    def show(self, v_code: str, comparison_result: str):
        """Show the dialog with comparison results.
        
        Args:
            v_code: The V-code being compared
            comparison_result: The analysis text to display
        """
        if self.window is None:
            self._create_window()
        
        # Set the title
        self.window.setTitle_(f"Check Text Comparison - {v_code}")
        
        # Set the comparison result text
        if self.text_view:
            self.text_view.setString_(comparison_result)
        
        # Show the window
        self.window.makeKeyAndOrderFront_(None)
        print(f"CompareCheckTextDialog.show: Showing dialog for {v_code}")  # Debug
    
    def _create_window(self):
        """Create the dialog window."""
        # Window dimensions - taller window
        width = 800
        height = 900
        
        # Create window with resizable style
        from AppKit import NSResizableWindowMask
        style = NSTitledWindowMask | NSClosableWindowMask | NSMiniaturizableWindowMask | NSResizableWindowMask
        rect = NSRect((100, 100), (width, height))
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, style, 2, False  # 2 = NSBackingStoreBuffered
        )
        self.window.setTitle_("Check Text Comparison")
        self.window.setReleasedWhenClosed_(False)
        # Set minimum window size
        self.window.setMinSize_((400, 300))
        
        # Create content view
        content_view = NSView.alloc().initWithFrame_(NSRect((0, 0), (width, height)))
        
        # Create text scroll view (takes most of the space)
        text_height = height - 60  # Leave space for button
        text_frame = NSRect((10, 50), (width - 20, text_height))
        text_scroll = NSScrollView.alloc().initWithFrame_(text_frame)
        text_scroll.setHasVerticalScroller_(True)
        text_scroll.setHasHorizontalScroller_(False)
        text_scroll.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        text_scroll.setBorderType_(1)  # NSBezelBorder
        
        # Create text view
        text_view = NSTextView.alloc().initWithFrame_(text_frame)
        text_view.setEditable_(False)
        text_view.setSelectable_(True)
        text_view.setRichText_(False)
        text_view.setFont_(NSFont.systemFontOfSize_(13))
        text_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        text_scroll.setDocumentView_(text_view)
        content_view.addSubview_(text_scroll)
        self.text_view = text_view
        
        # Create Close button
        btn_width = 100
        btn_height = 32
        btn_x = (width - btn_width) // 2
        close_btn_frame = NSRect((btn_x, 10), (btn_width, btn_height))
        close_btn = NSButton.alloc().initWithFrame_(close_btn_frame)
        close_btn.setTitle_("Close")
        close_btn.setBezelStyle_(1)  # NSRoundedBezelStyle
        close_btn.setTarget_(self.window)
        close_btn.setAction_("close")
        # Keep button centered horizontally when window resizes
        from AppKit import NSViewMinXMargin, NSViewMaxXMargin
        close_btn.setAutoresizingMask_(NSViewMinXMargin | NSViewMaxXMargin)
        content_view.addSubview_(close_btn)
        
        # Set content view
        self.window.setContentView_(content_view)
        
        print("CompareCheckTextDialog._create_window: Window created")  # Debug
