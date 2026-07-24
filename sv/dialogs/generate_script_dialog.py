"""Dialog for displaying a generated bash script."""

from pathlib import Path

import objc
from AppKit import (
    NSView, NSRect, NSButton, NSScrollView, NSTextView, NSWindow, NSSavePanel,
    NSTitledWindowMask, NSClosableWindowMask, NSMiniaturizableWindowMask,
    NSResizableWindowMask, NSViewWidthSizable, NSViewHeightSizable,
    NSViewMinXMargin, NSFont,
)
from Foundation import NSObject


DEFAULT_FILENAMES = {
    "Generated Copy Script": "copy_vcodes.sh",
    "Generated New Script": "new_vcodes.sh",
}


class GenerateScriptDialogTarget(NSObject):
    """Target object for script dialog button actions."""

    dialog = objc.ivar()

    def initWithDialog_(self, dialog):
        self = objc.super(GenerateScriptDialogTarget, self).init()
        if self is None:
            return None
        self.dialog = dialog
        return self

    def saveFile_(self, sender):
        if self.dialog:
            self.dialog._save_file()


class GenerateScriptDialog:
    """Dialog showing a generated bash script."""

    def __init__(self):
        self.window = None
        self.text_view = None
        self.default_filename = "script.sh"
        self._target = None

    def show(self, script_text: str, title: str = "Generated Script"):
        """Show the dialog with the generated script."""
        if self.window is None:
            self._create_window()
        self.window.setTitle_(title)
        self.default_filename = DEFAULT_FILENAMES.get(title, "script.sh")
        if self.text_view:
            self.text_view.setString_(script_text)
        self.window.makeKeyAndOrderFront_(None)

    def _save_file(self):
        """Prompt for a destination and save the script text."""
        if not self.text_view:
            return

        panel = NSSavePanel.savePanel()
        panel.setTitle_("Save Script")
        panel.setNameFieldStringValue_(self.default_filename)
        panel.setAllowedFileTypes_(["sh", "public.shell-script", "public.plain-text"])

        if panel.runModal() != 1:
            return

        url = panel.URL()
        if not url:
            return

        path = Path(str(url.path()))
        script_text = self.text_view.string()
        path.write_text(script_text, encoding="utf-8")

    def _create_window(self):
        width = 900
        height = 700
        rect = NSRect((100, 100), (width, height))
        style = (
            NSTitledWindowMask | NSClosableWindowMask |
            NSMiniaturizableWindowMask | NSResizableWindowMask
        )
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, style, 2, False
        )
        self.window.setTitle_("Generated Script")
        self.window.setReleasedWhenClosed_(False)
        self.window.setMinSize_((500, 300))

        content_view = NSView.alloc().initWithFrame_(NSRect((0, 0), (width, height)))
        text_frame = NSRect((10, 50), (width - 20, height - 60))
        text_scroll = NSScrollView.alloc().initWithFrame_(text_frame)
        text_scroll.setHasVerticalScroller_(True)
        text_scroll.setHasHorizontalScroller_(True)
        text_scroll.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        text_scroll.setBorderType_(1)

        text_view = NSTextView.alloc().initWithFrame_(text_scroll.bounds())
        text_view.setEditable_(False)
        text_view.setSelectable_(True)
        text_view.setRichText_(False)
        text_view.setFont_(NSFont.monospacedSystemFontOfSize_weight_(12, 0))
        text_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        text_scroll.setDocumentView_(text_view)
        content_view.addSubview_(text_scroll)
        self.text_view = text_view

        self._target = GenerateScriptDialogTarget.alloc().initWithDialog_(self)

        btn_width = 100
        btn_height = 32
        btn_y = 10
        save_btn = NSButton.alloc().initWithFrame_(
            NSRect((width - (2 * btn_width) - 20, btn_y), (btn_width, btn_height))
        )
        save_btn.setTitle_("Save File")
        save_btn.setBezelStyle_(1)
        save_btn.setTarget_(self._target)
        save_btn.setAction_("saveFile:")
        save_btn.setAutoresizingMask_(NSViewMinXMargin)
        content_view.addSubview_(save_btn)

        close_btn = NSButton.alloc().initWithFrame_(
            NSRect((width - btn_width - 10, btn_y), (btn_width, btn_height))
        )
        close_btn.setTitle_("Close")
        close_btn.setBezelStyle_(1)
        close_btn.setTarget_(self.window)
        close_btn.setAction_("close")
        close_btn.setAutoresizingMask_(NSViewMinXMargin)
        content_view.addSubview_(close_btn)

        self.window.setContentView_(content_view)
