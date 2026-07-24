"""Explorer tab listing V-codes and their check text."""

from pathlib import Path
from typing import List, Optional, Set

from AppKit import (
    NSView, NSRect, NSBox, NSSplitView, NSScrollView, NSTextView, NSButton,
    NSTextField, NSPopUpButton, NSViewWidthSizable, NSViewHeightSizable,
    NSColor, NSFont,
)
from Foundation import NSIndexSet
import objc

from ..models.vuln_code import VulnCode
from ..utils.check_json_export import export_check_json
from ..utils.check_text_diff import (
    build_mismatch_attributed_text,
    check_texts_mismatch,
    load_json_check_text,
)
from .vcode_list_pane import VCodeListPane
from .view_helpers import get_view_attrs, get_bounds_size


TAB_LABEL = "Check Texts Explorer"
CHECKS_DIR = Path(__file__).resolve().parent.parent / "checks"

FILTER_OPTIONS = [
    "All",
    "With JSON",
    "Without JSON",
    "Mismatched",
]
FILTER_WITHOUT_JSON = 2
FILTER_MISMATCHED = 3


def load_json_v_codes(checks_dir: Path = CHECKS_DIR) -> Set[str]:
    """Return V-codes that have a JSON file in the checks directory."""
    if not checks_dir.is_dir():
        return set()
    return {path.stem for path in checks_dir.glob("*.json")}


def _vcode_sort_key(vuln_code: VulnCode):
    try:
        return int(vuln_code.v_code.replace("V-", "").replace("v-", ""))
    except (ValueError, AttributeError):
        return 999999999


def dedupe_vuln_codes_for_explorer(
    vuln_codes: List[VulnCode],
    checks_dir: Path = CHECKS_DIR,
) -> List[VulnCode]:
    """Collapse duplicate V-codes from multiple checked STIGs into one entry."""
    from collections import defaultdict

    grouped: dict[str, List[VulnCode]] = defaultdict(list)
    for vuln_code in vuln_codes:
        grouped[vuln_code.v_code].append(vuln_code)

    deduped: List[VulnCode] = []
    for v_code in sorted(grouped.keys(), key=lambda code: _vcode_sort_key(
        grouped[code][0]
    )):
        variants = grouped[v_code]
        if len(variants) == 1:
            deduped.append(variants[0])
            continue

        json_check_text = load_json_check_text(v_code, checks_dir)
        if json_check_text is not None:
            matching = [
                variant for variant in variants
                if not check_texts_mismatch(variant.check_text, json_check_text)
            ]
            if matching:
                deduped.append(matching[0])
                continue

        deduped.append(max(variants, key=lambda variant: len(variant.check_text or "")))

    return deduped


def item_matches_json_filter(
    vuln_code: VulnCode,
    filter_index: int,
    json_v_codes: Set[str],
    checks_dir: Path = CHECKS_DIR,
) -> bool:
    """Return True if the V-code should appear for the selected JSON filter."""
    if filter_index <= 0:
        return True
    has_json = vuln_code.v_code in json_v_codes
    if filter_index == 1:
        return has_json
    if filter_index == 2:
        return not has_json
    if filter_index == 3:
        if not has_json:
            return False
        json_check_text = load_json_check_text(vuln_code.v_code, checks_dir)
        return check_texts_mismatch(vuln_code.check_text, json_check_text)
    return True


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
        attrs["filter_label"] = None
        attrs["filter_popup"] = None
        attrs["close_btn"] = None
        attrs["export_btn"] = None
        attrs["export_queue"] = []
        attrs["export_in_progress"] = False
        attrs["left_box"] = None
        attrs["right_content"] = None
        attrs["check_scroll"] = None
        attrs["all_vuln_codes"] = []
        attrs["json_v_codes"] = load_json_v_codes()
        CheckTextsExplorerView.createUI(self)
        return self

    @objc.python_method
    def set_vuln_codes(self, vuln_codes: List[VulnCode]):
        """Load V-codes from the selected Explorer STIGs."""
        attrs = get_view_attrs(self)
        raw_vuln_codes = list(vuln_codes) if vuln_codes else []
        attrs["all_vuln_codes"] = dedupe_vuln_codes_for_explorer(raw_vuln_codes)
        attrs["json_v_codes"] = load_json_v_codes()

        filter_popup = attrs.get("filter_popup")
        if filter_popup:
            filter_popup.selectItemAtIndex_(0)
        self._apply_filter()

    def filterChanged_(self, sender):
        from PyObjCTools import AppHelper
        AppHelper.callAfter(self._apply_filter)

    @objc.python_method
    def _selected_filter_index(self) -> int:
        attrs = get_view_attrs(self)
        filter_popup = attrs.get("filter_popup")
        if not filter_popup:
            return 0
        title = filter_popup.titleOfSelectedItem()
        if not title:
            return 0
        try:
            return FILTER_OPTIONS.index(title)
        except ValueError:
            return 0

    @objc.python_method
    def _apply_filter(self):
        attrs = get_view_attrs(self)
        attrs["json_v_codes"] = load_json_v_codes()
        all_vuln_codes = attrs.get("all_vuln_codes", [])
        json_v_codes = attrs.get("json_v_codes", set())
        filter_index = self._selected_filter_index()
        filtered = [
            item for item in all_vuln_codes
            if item_matches_json_filter(item, filter_index, json_v_codes)
        ]

        summary = attrs.get("summary_label")
        if summary:
            if filter_index == 0:
                summary.setStringValue_(
                    f"Showing {len(filtered)} V-code(s) from selected Explorer STIGs."
                )
            else:
                filter_name = FILTER_OPTIONS[filter_index]
                summary.setStringValue_(
                    f"Showing {len(filtered)} of {len(all_vuln_codes)} V-code(s) ({filter_name})."
                )

        vcode_list_pane = attrs.get("vcode_list_pane")
        if vcode_list_pane:
            VCodeListPane.set_vuln_codes(vcode_list_pane, filtered)
            table_view = get_view_attrs(vcode_list_pane).get("table_view")
            if table_view:
                table_view.reloadData()

        if filtered:
            self.show_check_text(filtered[0])
            if vcode_list_pane:
                table_view = get_view_attrs(vcode_list_pane).get("table_view")
                if table_view:
                    table_view.selectRowIndexes_byExtendingSelection_(
                        NSIndexSet.indexSetWithIndex_(0), False
                    )
        else:
            self.clear_check_text()
            if vcode_list_pane:
                table_view = get_view_attrs(vcode_list_pane).get("table_view")
                if table_view:
                    table_view.deselectAll_(None)

        self._update_export_button_state()
        self.setNeedsDisplay_(True)

    @objc.python_method
    def _filtered_vuln_codes(self) -> List[VulnCode]:
        attrs = get_view_attrs(self)
        all_vuln_codes = attrs.get("all_vuln_codes", [])
        json_v_codes = attrs.get("json_v_codes", set())
        filter_index = self._selected_filter_index()
        return [
            item for item in all_vuln_codes
            if item_matches_json_filter(item, filter_index, json_v_codes)
        ]

    @objc.python_method
    def _export_enabled_for_filter(self) -> bool:
        return self._selected_filter_index() in (
            FILTER_WITHOUT_JSON,
            FILTER_MISMATCHED,
        )

    @objc.python_method
    def _update_export_button_state(self):
        attrs = get_view_attrs(self)
        export_btn = attrs.get("export_btn")
        if not export_btn:
            return
        if attrs.get("export_in_progress"):
            export_btn.setEnabled_(False)
            return
        enabled = (
            self._export_enabled_for_filter()
            and bool(self._filtered_vuln_codes())
        )
        export_btn.setEnabled_(enabled)

    def exportCheckTexts_(self, sender):
        from PyObjCTools import AppHelper
        AppHelper.callAfter(self._start_export_check_texts)

    @objc.python_method
    def _start_export_check_texts(self):
        """Export STIG check text as JSON for all V-codes in the current filter."""
        if not self._export_enabled_for_filter():
            return

        attrs = get_view_attrs(self)
        to_export = list(self._filtered_vuln_codes())
        if not to_export:
            self._update_export_button_state()
            return

        attrs["export_in_progress"] = True
        attrs["export_queue"] = to_export
        self._update_export_button_state()
        self._export_next_check_text()

    @objc.python_method
    def _export_next_check_text(self):
        from PyObjCTools import AppHelper

        attrs = get_view_attrs(self)
        queue = attrs.get("export_queue", [])
        if not queue:
            attrs["export_in_progress"] = False
            attrs["export_queue"] = []
            AppHelper.callAfter(self._apply_filter)
            AppHelper.callAfter(self._update_export_button_state)
            return

        vuln = queue.pop(0)
        attrs["export_queue"] = queue
        try:
            # Always build JSON from the loaded STIG VulnCode, overwriting any
            # existing check JSON file (including for the Mismatched filter).
            export_check_json(vuln, CHECKS_DIR)
        except Exception as exc:
            attrs["export_in_progress"] = False
            attrs["export_queue"] = []
            self._update_export_button_state()
            self._show_export_error(str(exc))
            return

        def after_write():
            self._apply_filter()
            self._export_next_check_text()

        AppHelper.callAfter(after_write)

    @objc.python_method
    def _show_export_error(self, message: str):
        from AppKit import NSAlert
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Export Check Texts failed")
        alert.setInformativeText_(message)
        alert.runModal()

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

        filter_index = self._selected_filter_index()
        if filter_index == FILTER_MISMATCHED:
            json_check_text = load_json_check_text(vuln_code.v_code, CHECKS_DIR)
            if json_check_text is not None and check_texts_mismatch(
                vuln_code.check_text, json_check_text
            ):
                check_text_view.setRichText_(True)
                attributed = build_mismatch_attributed_text(
                    vuln_code.v_code,
                    vuln_code.rule_title,
                    vuln_code.severity,
                    vuln_code.check_text or "",
                    json_check_text,
                )
                check_text_view.textStorage().setAttributedString_(attributed)
                return

        check_text_view.setRichText_(False)
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
            check_text_view.setRichText_(False)
            check_text_view.setString_("Select a V-code to view its check text.")

    def closeCheckTextsExplorerTab_(self, sender):
        attrs = get_view_attrs(self)
        main_window = attrs.get("main_window")
        if main_window:
            main_window.remove_check_texts_explorer_tab()

    @objc.python_method
    def _on_vcode_selected(self, vuln_code: Optional[VulnCode]):
        self.show_check_text(vuln_code)

    @objc.python_method
    def _layout_panes(self):
        attrs = get_view_attrs(self)
        left_box = attrs.get("left_box")
        check_scroll = attrs.get("check_scroll")
        vcode_list_pane = attrs.get("vcode_list_pane")
        summary = attrs.get("summary_label")
        filter_label = attrs.get("filter_label")
        filter_popup = attrs.get("filter_popup")
        close_btn = attrs.get("close_btn")
        export_btn = attrs.get("export_btn")
        if not left_box:
            return

        left_content = left_box.contentView()
        left_width, left_height = get_bounds_size(left_content.bounds())
        margin = 10
        footer_height = 40
        summary_height = 22
        filter_height = 26
        top_margin = 10

        summary_y = left_height - top_margin - summary_height
        filter_y = summary_y - 6 - filter_height

        if summary:
            summary.setFrame_(
                NSRect((margin, summary_y), (left_width - (2 * margin), summary_height))
            )
        if filter_label:
            filter_label.setFrame_(NSRect((margin, filter_y + 2), (45, 22)))
        if filter_popup:
            filter_popup.setFrame_(
                NSRect((margin + 50, filter_y), (max(150, left_width - margin - 60), filter_height))
            )
        if close_btn:
            close_btn.setFrame_(NSRect((margin, 8), (100, 28)))
        if export_btn:
            export_btn.setFrame_(NSRect((margin + 110, 8), (150, 28)))
        if vcode_list_pane:
            list_bottom = footer_height + margin
            list_height = max(80, filter_y - margin - list_bottom)
            vcode_list_pane.setFrame_(
                NSRect((0, list_bottom), (left_width, list_height))
            )

        if check_scroll:
            right_content = attrs.get("right_content")
            if right_content:
                right_width, right_height = get_bounds_size(right_content.bounds())
                check_scroll.setFrame_(
                    NSRect(
                        (margin, margin),
                        (max(100, right_width - (2 * margin)), max(40, right_height - (2 * margin))),
                    )
                )

    def resizeSubviewsWithOldSize_(self, old_size):
        objc.super(CheckTextsExplorerView, self).resizeSubviewsWithOldSize_(old_size)
        self._layout_panes()

    def viewDidMoveToWindow(self):
        self._layout_panes()

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

        summary = NSTextField.alloc().initWithFrame_(NSRect((10, left_height - 28), (left_width - 20, 22)))
        summary.setStringValue_("Select a V-code to view its check text.")
        summary.setBezeled_(False)
        summary.setDrawsBackground_(False)
        summary.setEditable_(False)
        summary.setSelectable_(False)
        summary.setTextColor_(NSColor.whiteColor())
        summary.setAutoresizingMask_(0x08 | 0x02)
        left_content.addSubview_(summary)

        filter_label = NSTextField.alloc().initWithFrame_(NSRect((10, left_height - 58), (45, 22)))
        filter_label.setStringValue_("Filter")
        filter_label.setBezeled_(False)
        filter_label.setDrawsBackground_(False)
        filter_label.setEditable_(False)
        filter_label.setSelectable_(False)
        filter_label.setTextColor_(NSColor.whiteColor())
        filter_label.setAutoresizingMask_(0x08 | 0x02)
        left_content.addSubview_(filter_label)

        filter_popup = NSPopUpButton.alloc().initWithFrame_(
            NSRect((60, left_height - 60), (max(160, left_width - 70), 26))
        )
        for option in FILTER_OPTIONS:
            filter_popup.addItemWithTitle_(option)
        filter_popup.selectItemAtIndex_(0)
        filter_popup.setTarget_(self)
        filter_popup.setAction_("filterChanged:")
        filter_popup.setAutoresizingMask_(0x08 | 0x02)
        left_content.addSubview_(filter_popup)

        footer_height = 40
        list_height = max(120, left_height - 90)
        vcode_list_pane = VCodeListPane.alloc().init()
        vcode_list_pane.setFrame_(NSRect((0, footer_height), (left_width, list_height)))
        vcode_list_pane.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        left_content.addSubview_(vcode_list_pane)

        list_attrs = get_view_attrs(vcode_list_pane)
        list_attrs["on_selection_changed"] = self._on_vcode_selected

        close_btn = NSButton.alloc().initWithFrame_(NSRect((10, 8), (100, 28)))
        close_btn.setTitle_("Close Tab")
        close_btn.setTarget_(self)
        close_btn.setAction_("closeCheckTextsExplorerTab:")
        close_btn.setAutoresizingMask_(0x04 | 0x08)
        left_content.addSubview_(close_btn)

        export_btn = NSButton.alloc().initWithFrame_(NSRect((120, 8), (150, 28)))
        export_btn.setTitle_("Export Check Texts")
        export_btn.setTarget_(self)
        export_btn.setAction_("exportCheckTexts:")
        export_btn.setEnabled_(False)
        export_btn.setAutoresizingMask_(0x04 | 0x08)
        left_content.addSubview_(export_btn)

        right_box = NSBox.alloc().initWithFrame_(NSRect((0, 0), (right_width, height)))
        right_box.setTitlePosition_(2)
        right_box.setTitle_("Check Text")
        right_box.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        right_content = right_box.contentView()
        right_width, right_height = get_bounds_size(right_content.bounds())

        margin = 10
        check_scroll = NSScrollView.alloc().initWithFrame_(
            NSRect((margin, margin), (max(100, right_width - (2 * margin)), max(40, right_height - (2 * margin))))
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
        self._layout_panes()

        attrs = get_view_attrs(self)
        attrs["summary_label"] = summary
        attrs["filter_label"] = filter_label
        attrs["filter_popup"] = filter_popup
        attrs["vcode_list_pane"] = vcode_list_pane
        attrs["check_text_view"] = check_text_view
        attrs["close_btn"] = close_btn
        attrs["export_btn"] = export_btn
        attrs["left_box"] = left_box
        attrs["right_content"] = right_content
        attrs["check_scroll"] = check_scroll
