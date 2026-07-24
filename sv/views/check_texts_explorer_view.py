"""Explorer tab listing V-codes and their check text."""

from typing import List, Optional

from AppKit import (
    NSView, NSRect, NSBox, NSSplitView, NSScrollView, NSTextView, NSButton,
    NSTextField, NSViewWidthSizable, NSViewHeightSizable, NSColor, NSFont,
)
from Foundation import NSIndexSet
import objc

from ..models.vuln_code import VulnCode
from .vcode_list_pane import VCodeListPane
from .view_helpers import get_view_attrs, get_bounds_size


TAB_LABEL = "Check Texts Explorer"


class CheckTextsExplorerView(NSView):
    """Tab showing V-codes from selected Explorer STIGs and their check text."""

    def init(self):
        self = objc.super(CheckTextsExplorerView, self).init()
        if self is None:
            return None

        attrs = get_view_attrs(self)
        attrs["main_window"] = None
        attrs["vcode_list_pane"] = None
        attrs["check_text_view"] = None
        attrs["summary_label"] = None
        attrs["close_btn"] = None
        CheckTextsExplorerView.createUI(self)
        return self

    @objc.python_method
    def set_vuln_codes(self, vuln_codes: List[VulnCode]):
        """Load V-codes from the selected Explorer STIGs."""
        attrs = get_view_attrs(self)
        summary = attrs.get("summary_label")
        if summary:
            summary.setStringValue_(
                f"Showing {len(vuln_codes)} V-code(s) from selected Explorer STIGs."
            )

        vcode_list_pane = attrs.get("vcode_list_pane")
        if vcode_list_pane:
            VCodeListPane.set_vuln_codes(vcode_list_pane, vuln_codes)

        if vuln_codes:
            self.show_check_text(vuln_codes[0])
            table_view = get_view_attrs(vcode_list_pane).get("table_view")
            if table_view:
                table_view.selectRowIndexes_byExtendingSelection_(
                    NSIndexSet.indexSetWithIndex_(0), False
                )
        else:
            self.clear_check_text()

    @objc.python_method
    def show_check_text(self, vuln_code: Optional[VulnCode]):
        """Display check text for the selected V-code."""
        attrs = get_view_attrs(self)
        check_text_view = attrs.get("check_text_view")
        if not check_text_view:
            return

        if not vuln_code:
            self.clear_check_text()
            return

        header = (
            f"{vuln_code.v_code}: {vuln_code.rule_title}\n"
            f"Severity: {(vuln_code.severity or 'unknown').upper()}\n\n"
            "Check Text:\n"
        )
        body = vuln_code.check_text or "(No check text available)"
        check_text_view.setString_(header + body)

    @objc.python_method
    def clear_check_text(self):
        attrs = get_view_attrs(self)
        check_text_view = attrs.get("check_text_view")
        if check_text_view:
            check_text_view.setString_("Select a V-code to view its check text.")

    def closeCheckTextsExplorerTab_(self, sender):
        attrs = get_view_attrs(self)
        main_window = attrs.get("main_window")
        if main_window:
            main_window.remove_check_texts_explorer_tab()

    @objc.python_method
    def _on_vcode_selected(self, vuln_code: Optional[VulnCode]):
        self.show_check_text(vuln_code)

    def createUI(self):
        bounds = self.bounds()
        width, height = get_bounds_size(bounds)
        if width == 0 or height == 0:
            width, height = 1200, 800
            self.setFrame_(NSRect((0, 0), (width, height)))

        split_view = NSSplitView.alloc().initWithFrame_(NSRect((0, 0), (width, height)))
        split_view.setVertical_(True)
        split_view.setDividerStyle_(1)
        split_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)

        left_width = int(width * 0.35)
        right_width = width - left_width

        left_box = NSBox.alloc().initWithFrame_(NSRect((0, 0), (left_width, height)))
        left_box.setTitlePosition_(2)
        left_box.setTitle_("V-codes")
        left_box.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        left_content = left_box.contentView()
        left_width, left_height = get_bounds_size(left_content.bounds())

        summary = NSTextField.alloc().initWithFrame_(
            NSRect((10, left_height - 28), (left_width - 20, 22))
        )
        summary.setStringValue_("Select a V-code to view its check text.")
        summary.setBezeled_(False)
        summary.setDrawsBackground_(False)
        summary.setEditable_(False)
        summary.setSelectable_(False)
        summary.setTextColor_(NSColor.whiteColor())
        summary.setAutoresizingMask_(0x08 | 0x02)
        left_content.addSubview_(summary)

        list_height = max(120, left_height - 38)
        vcode_list_pane = VCodeListPane.alloc().init()
        vcode_list_pane.setFrame_(NSRect((0, 10), (left_width, list_height)))
        vcode_list_pane.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        left_content.addSubview_(vcode_list_pane)

        list_attrs = get_view_attrs(vcode_list_pane)
        list_attrs["on_selection_changed"] = self._on_vcode_selected

        right_box = NSBox.alloc().initWithFrame_(NSRect((0, 0), (right_width, height)))
        right_box.setTitlePosition_(2)
        right_box.setTitle_("Check Text")
        right_box.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        right_content = right_box.contentView()
        right_width, right_height = get_bounds_size(right_content.bounds())

        footer_height = 40
        margin = 10
        close_btn = NSButton.alloc().initWithFrame_(NSRect((margin, 8), (100, 28)))
        close_btn.setTitle_("Close Tab")
        close_btn.setTarget_(self)
        close_btn.setAction_("closeCheckTextsExplorerTab:")
        close_btn.setAutoresizingMask_(0x04 | 0x08)
        right_content.addSubview_(close_btn)

        scroll_height = max(40, right_height - footer_height - margin)
        check_scroll = NSScrollView.alloc().initWithFrame_(
            NSRect((margin, footer_height), (max(100, right_width - (2 * margin)), scroll_height))
        )
        check_scroll.setHasVerticalScroller_(True)
        check_scroll.setHasHorizontalScroller_(False)
        check_scroll.setAutoresizingMask_(0x02 | 0x08 | 0x10 | 0x20)
        check_scroll.setBorderType_(1)

        check_text_view = NSTextView.alloc().initWithFrame_(check_scroll.bounds())
        check_text_view.setEditable_(False)
        check_text_view.setSelectable_(True)
        check_text_view.setRichText_(False)
        check_text_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        check_text_view.setString_("Select a V-code to view its check text.")
        check_text_view.setTextColor_(NSColor.whiteColor())
        check_text_view.setBackgroundColor_(NSColor.blackColor())
        check_text_view.setFont_(NSFont.systemFontOfSize_(12))
        check_scroll.setDocumentView_(check_text_view)
        right_content.addSubview_(check_scroll)

        split_view.addSubview_(left_box)
        split_view.addSubview_(right_box)
        split_view.adjustSubviews()
        self.addSubview_(split_view)

        attrs = get_view_attrs(self)
        attrs["summary_label"] = summary
        attrs["vcode_list_pane"] = vcode_list_pane
        attrs["check_text_view"] = check_text_view
        attrs["close_btn"] = close_btn
