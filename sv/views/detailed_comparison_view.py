"""Detailed comparison checklist for implementing tests for a newer STIG."""

from dataclasses import dataclass, field
from typing import Dict, List, Set

from AppKit import (
    NSView, NSRect, NSBox, NSSplitView, NSScrollView, NSTableView, NSTableColumn,
    NSButton, NSButtonCell, NSTextField, NSTextView, NSColor, NSFont, NSPopUpButton,
    NSViewWidthSizable, NSViewHeightSizable
)
from Foundation import NSObject, NSIndexSet
import objc

from ..models.stig_file import StigFile
from ..models.vuln_code import VulnCode
from .view_helpers import get_view_attrs, get_bounds_size


FILTER_OPTIONS = [
    "All",
    "New",
    "New Check Text",
    "New Rule Title",
    "New Severity",
    "New Discussion",
    "New Fix Text",
    "New Rule ID",
    "New Group Title",
    "New V-code Label",
]

RULE_ID_FILTER_OPTION = "New Rule ID"

TYPE_CODE_N = "N"
TYPE_CODE_NCT = "NCT"
TYPE_CODE_NRT = "NRT"
TYPE_CODE_NS = "NS"
TYPE_CODE_ND = "ND"
TYPE_CODE_NFT = "NFT"
TYPE_CODE_NRI = "NRI"
TYPE_CODE_NGT = "NGT"
TYPE_CODE_NVC = "NVC"

FILTER_INDEX_TO_CODE = {
    1: TYPE_CODE_N,
    2: TYPE_CODE_NCT,
    3: TYPE_CODE_NRT,
    4: TYPE_CODE_NS,
    5: TYPE_CODE_ND,
    6: TYPE_CODE_NFT,
    7: TYPE_CODE_NRI,
    8: TYPE_CODE_NGT,
    9: TYPE_CODE_NVC,
}

FILTER_INDEX_TO_DETAIL = {
    0: ("Check Text", "check_text"),
    1: ("Check Text", "check_text"),
    2: ("Check Text", "check_text"),
    3: ("Rule Title", "rule_title"),
    4: ("Severity", "severity"),
    5: ("Discussion", "discussion"),
    6: ("Fix Text", "fix_text"),
    7: ("Rule ID", "rule_id"),
    8: ("Group Title", "group_title"),
    9: ("V-code Label", "v_code"),
}


@dataclass
class ImplementationTestItem:
    """A checklist item for creating or updating a STIG implementation test."""

    v_code: str
    rule_title: str
    change_type: str
    severity: str
    check_text: str
    checked_codes: Set[str] = field(default_factory=set)
    changed_check_text: bool = False
    changed_rule_title: bool = False
    changed_severity: bool = False
    changed_discussion: bool = False
    changed_fix_text: bool = False
    changed_rule_id: bool = False
    changed_group_title: bool = False
    changed_v_code: bool = False


def has_only_rule_id_change(item: ImplementationTestItem) -> bool:
    """Return True if the only change for an updated item is the rule ID."""
    if item.change_type == "New" or not item.changed_rule_id:
        return False
    return not (
        item.changed_check_text
        or item.changed_rule_title
        or item.changed_severity
        or item.changed_discussion
        or item.changed_fix_text
        or item.changed_group_title
        or item.changed_v_code
    )


def item_matches_filter(
    item: ImplementationTestItem,
    filter_index: int,
    eliminate_rule_id: bool = False,
) -> bool:
    """Return True if the item should appear under the given filter index."""
    if eliminate_rule_id and has_only_rule_id_change(item):
        return False
    if filter_index <= 0:
        return True
    if filter_index == 1:
        return item.change_type == "New"
    if filter_index == 2:
        return item.changed_check_text
    if filter_index == 3:
        return item.changed_rule_title
    if filter_index == 4:
        return item.changed_severity
    if filter_index == 5:
        return item.changed_discussion
    if filter_index == 6:
        return item.changed_fix_text
    if filter_index == 7:
        return item.changed_rule_id and not eliminate_rule_id
    if filter_index == 8:
        return item.changed_group_title
    if filter_index == 9:
        return item.changed_v_code
    return False


def item_matches_filter_name(
    item: ImplementationTestItem,
    filter_name: str,
    eliminate_rule_id: bool = False,
) -> bool:
    """Return True if the item should appear under the given filter name."""
    try:
        filter_index = FILTER_OPTIONS.index(filter_name)
    except ValueError:
        return False
    return item_matches_filter(item, filter_index, eliminate_rule_id)


def get_applicable_type_codes(
    item: ImplementationTestItem,
    eliminate_rule_id: bool = False,
) -> List[str]:
    """Return the type codes that apply to a checklist item."""
    if item.change_type == "New":
        return [TYPE_CODE_N]
    codes: List[str] = []
    if item.changed_check_text:
        codes.append(TYPE_CODE_NCT)
    if item.changed_rule_title:
        codes.append(TYPE_CODE_NRT)
    if item.changed_severity:
        codes.append(TYPE_CODE_NS)
    if item.changed_discussion:
        codes.append(TYPE_CODE_ND)
    if item.changed_fix_text:
        codes.append(TYPE_CODE_NFT)
    if item.changed_rule_id and not eliminate_rule_id:
        codes.append(TYPE_CODE_NRI)
    if item.changed_group_title:
        codes.append(TYPE_CODE_NGT)
    if item.changed_v_code:
        codes.append(TYPE_CODE_NVC)
    return codes


def is_fully_checked(item: ImplementationTestItem, eliminate_rule_id: bool = False) -> bool:
    """Return True when every applicable type code has been checked off."""
    return master_checkbox_state(item, eliminate_rule_id) == 1


def master_checkbox_state(item: ImplementationTestItem, eliminate_rule_id: bool = False) -> int:
    """Return master checkbox state: 0=off, 1=on, -1=mixed (partial)."""
    applicable = get_applicable_type_codes(item, eliminate_rule_id)
    if not applicable:
        return 0
    checked_count = sum(1 for code in applicable if code in item.checked_codes)
    if checked_count == 0:
        return 0
    if checked_count == len(applicable):
        return 1
    return -1


def format_type_codes(
    item: ImplementationTestItem,
    eliminate_rule_id: bool = False,
    filter_index: int = 0,
) -> str:
    """Format change category codes for display."""
    codes = get_applicable_type_codes(item, eliminate_rule_id)
    if filter_index > 0:
        code = FILTER_INDEX_TO_CODE.get(filter_index)
        return code if code and code in codes else ""
    return ", ".join(codes)


def _find_vuln_by_v_code(stig: StigFile, v_code: str):
    """Find a VulnCode in a STIG by its display V-code."""
    if not stig:
        return None
    target = v_code.upper()
    for vuln in stig.vuln_codes:
        if vuln.v_code.upper() == target:
            return vuln
    return None


def _lookup_vulns(
    item: ImplementationTestItem,
    older_stig: StigFile,
    newer_stig: StigFile,
):
    """Return older and newer VulnCode records for a checklist item."""
    newer_vuln = _find_vuln_by_v_code(newer_stig, item.v_code)
    older_vuln = None
    if newer_vuln and older_stig:
        older_lookup = {vc.id: vc for vc in older_stig.vuln_codes}
        older_vuln = older_lookup.get(newer_vuln.id)
    if not older_vuln:
        older_vuln = _find_vuln_by_v_code(older_stig, item.v_code)
    return older_vuln, newer_vuln


def _field_value(vuln: VulnCode, field: str, item: ImplementationTestItem) -> str:
    """Get a field value from a VulnCode, falling back to checklist item data."""
    if vuln:
        value = getattr(vuln, field, "")
        if value:
            return str(value)
    fallback = {
        "check_text": item.check_text,
        "rule_title": item.rule_title,
        "severity": item.severity,
        "v_code": item.v_code,
    }
    return str(fallback.get(field, "") or "")


def build_detail_content(
    item: ImplementationTestItem,
    filter_index: int,
    older_stig: StigFile,
    newer_stig: StigFile,
) -> tuple:
    """Return pane title and body text for the selected filter."""
    pane_title, field = FILTER_INDEX_TO_DETAIL.get(filter_index, ("Check Text", "check_text"))
    older_vuln, newer_vuln = _lookup_vulns(item, older_stig, newer_stig)
    newer_val = _field_value(newer_vuln, field, item)

    if filter_index == 0:
        return pane_title, newer_val or "(none)"

    body_parts = [f"{pane_title} (newer):\n{newer_val or '(none)'}"]
    if older_vuln and newer_vuln:
        older_val = getattr(older_vuln, field, "")
        newer_field_val = getattr(newer_vuln, field, "")
        if str(older_val) != str(newer_field_val):
            body_parts.append(f"\n{pane_title} (older):\n{older_val or '(none)'}")
    return pane_title, "\n".join(body_parts)


def build_implementation_checklist(
    older_stig: StigFile,
    newer_stig: StigFile,
    unfiltered_data: Dict[str, List[str]],
) -> List[ImplementationTestItem]:
    """Build checklist items from a STIG comparison."""
    newer_lookup = {vc.id: vc for vc in newer_stig.vuln_codes}
    older_lookup = {vc.id: vc for vc in older_stig.vuln_codes}
    items: List[ImplementationTestItem] = []

    for vcode_id in unfiltered_data.get('in_b_not_a', []):
        vuln = newer_lookup.get(vcode_id)
        if vuln:
            items.append(ImplementationTestItem(
                v_code=vuln.v_code,
                rule_title=vuln.rule_title,
                change_type="New",
                severity=vuln.severity,
                check_text=vuln.check_text,
                changed_check_text=True,
                changed_rule_title=True,
                changed_severity=True,
                changed_discussion=True,
                changed_fix_text=True,
                changed_rule_id=True,
                changed_group_title=True,
                changed_v_code=True,
            ))

    for vcode_id in unfiltered_data.get('different', []):
        newer_vuln = newer_lookup.get(vcode_id)
        older_vuln = older_lookup.get(vcode_id)
        if newer_vuln and older_vuln:
            items.append(ImplementationTestItem(
                v_code=newer_vuln.v_code,
                rule_title=newer_vuln.rule_title,
                change_type="Updated",
                severity=newer_vuln.severity,
                check_text=newer_vuln.check_text,
                changed_check_text=older_vuln.check_text != newer_vuln.check_text,
                changed_rule_title=older_vuln.rule_title != newer_vuln.rule_title,
                changed_severity=older_vuln.severity != newer_vuln.severity,
                changed_discussion=older_vuln.discussion != newer_vuln.discussion,
                changed_fix_text=older_vuln.fix_text != newer_vuln.fix_text,
                changed_rule_id=older_vuln.rule_id != newer_vuln.rule_id,
                changed_group_title=older_vuln.group_title != newer_vuln.group_title,
                changed_v_code=older_vuln.v_code != newer_vuln.v_code,
            ))

    items.sort(key=lambda item: item.v_code)
    return items


class DetailedComparisonDataSource(NSObject):
    """Data source for the implementation test checklist table."""

    def init(self):
        self = objc.super(DetailedComparisonDataSource, self).init()
        if self is None:
            return None
        self.items: List[ImplementationTestItem] = []
        self.eliminate_rule_id = True
        self.filter_index = 0
        return self

    @objc.python_method
    def set_eliminate_rule_id(self, eliminate_rule_id: bool):
        self.eliminate_rule_id = eliminate_rule_id

    @objc.python_method
    def set_filter_index(self, filter_index: int):
        self.filter_index = filter_index

    @objc.python_method
    def set_items(self, items: List[ImplementationTestItem]):
        self.items = list(items) if items else []

    def numberOfRowsInTableView_(self, table_view):
        return len(self.items)

    def tableView_objectValueForTableColumn_row_(self, table_view, column, row):
        if not (0 <= row < len(self.items)):
            return None
        item = self.items[row]
        col_id = str(column.identifier()) if column.identifier() else ""
        if col_id == "checkbox":
            if self.filter_index <= 0:
                return master_checkbox_state(item, self.eliminate_rule_id)
            code = FILTER_INDEX_TO_CODE.get(self.filter_index)
            return 1 if code and code in item.checked_codes else 0
        if col_id == "type":
            return format_type_codes(item, self.eliminate_rule_id, self.filter_index)
        if col_id == "vcode":
            return item.v_code
        if col_id == "title":
            return item.rule_title
        return None

    def tableView_setObjectValue_forTableColumn_row_(self, table_view, value, column, row):
        if not (0 <= row < len(self.items)):
            return
        col_id = str(column.identifier()) if column.identifier() else ""
        if col_id != "checkbox" or self.filter_index <= 0:
            return
        code = FILTER_INDEX_TO_CODE.get(self.filter_index)
        if not code:
            return
        item = self.items[row]
        if bool(value):
            item.checked_codes.add(code)
        else:
            item.checked_codes.discard(code)


class DetailedComparisonDelegate(NSObject):
    """Delegate for checklist table selection."""

    def init(self):
        self = objc.super(DetailedComparisonDelegate, self).init()
        if self is None:
            return None
        attrs = get_view_attrs(self)
        attrs['detail_view'] = None
        return self

    @objc.python_method
    def set_detail_view(self, detail_view):
        attrs = get_view_attrs(self)
        attrs['detail_view'] = detail_view

    def tableViewSelectionDidChange_(self, notification):
        attrs = get_view_attrs(self)
        detail_view = attrs.get('detail_view')
        if not detail_view:
            return
        table_view = notification.object()
        selected_row = table_view.selectedRow()
        data_source = table_view.dataSource()
        if selected_row >= 0 and data_source and 0 <= selected_row < len(data_source.items):
            detail_view.show_item(data_source.items[selected_row], data_source.filter_index)
        else:
            detail_view.clear_item()


class DetailedComparisonView(NSView):
    """Checklist tab for creating tests to implement a newer STIG."""

    def init(self):
        self = objc.super(DetailedComparisonView, self).init()
        if self is None:
            return None

        attrs = get_view_attrs(self)
        attrs['older_stig'] = None
        attrs['newer_stig'] = None
        attrs['all_items'] = []
        attrs['main_window'] = None
        attrs['tab_label'] = ""
        attrs['table_view'] = None
        attrs['data_source'] = None
        attrs['detail_text_view'] = None
        attrs['detail_box'] = None
        attrs['detail_scroll'] = None
        attrs['close_btn'] = None
        attrs['filter_popup'] = None
        attrs['eliminate_rule_id_cb'] = None
        attrs['eliminate_rule_id'] = True
        attrs['checkbox_column'] = None
        DetailedComparisonView.createUI(self)
        return self

    @objc.python_method
    def set_comparison(self, older_stig: StigFile, newer_stig: StigFile, items: List[ImplementationTestItem]):
        """Populate the checklist from a STIG comparison."""
        attrs = get_view_attrs(self)
        attrs['older_stig'] = older_stig
        attrs['newer_stig'] = newer_stig
        attrs['all_items'] = items

        summary = attrs.get('summary_label')
        if summary:
            summary.setStringValue_(
                f"Implement tests for {newer_stig.display_name} "
                f"(V{newer_stig.stig_version} R{newer_stig.stig_release}) "
                f"based on changes from "
                f"{older_stig.display_name} "
                f"(V{older_stig.stig_version} R{older_stig.stig_release})."
            )

        filter_popup = attrs.get('filter_popup')
        eliminate_cb = attrs.get('eliminate_rule_id_cb')
        if filter_popup:
            filter_popup.selectItemAtIndex_(0)
        if eliminate_cb:
            eliminate_cb.setState_(1)
        attrs['eliminate_rule_id'] = True
        self._rebuild_filter_popup(True)
        self._apply_filter()

    def filterChanged_(self, sender):
        """Handle filter popup selection change."""
        from PyObjCTools import AppHelper
        AppHelper.callAfter(self._apply_filter)

    def eliminateRuleIdChanged_(self, sender):
        """Handle Eliminate New Rule ID checkbox change."""
        from PyObjCTools import AppHelper
        AppHelper.callAfter(self._apply_rule_id_setting)

    @objc.python_method
    def _apply_rule_id_setting(self):
        attrs = get_view_attrs(self)
        checkbox = attrs.get('eliminate_rule_id_cb')
        eliminate_rule_id = checkbox.state() == 1 if checkbox else True
        attrs['eliminate_rule_id'] = eliminate_rule_id
        self._rebuild_filter_popup(eliminate_rule_id)
        self._apply_filter()

    @objc.python_method
    def _rebuild_filter_popup(self, eliminate_rule_id: bool):
        """Show or hide the New Rule ID filter option."""
        attrs = get_view_attrs(self)
        filter_popup = attrs.get('filter_popup')
        if not filter_popup:
            return

        selected_title = filter_popup.titleOfSelectedItem()
        filter_popup.removeAllItems()
        for option in FILTER_OPTIONS:
            if eliminate_rule_id and option == RULE_ID_FILTER_OPTION:
                continue
            filter_popup.addItemWithTitle_(option)

        if selected_title:
            for index in range(filter_popup.numberOfItems()):
                if filter_popup.itemTitleAtIndex_(index) == selected_title:
                    filter_popup.selectItemAtIndex_(index)
                    return
        filter_popup.selectItemAtIndex_(0)

    @objc.python_method
    def _selected_filter_index(self, filter_popup) -> int:
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
    def _apply_filter(self, filter_index=None):
        """Filter checklist items and refresh the table."""
        attrs = get_view_attrs(self)
        all_items = attrs.get('all_items', [])
        filter_popup = attrs.get('filter_popup')
        data_source = attrs.get('data_source')
        table_view = attrs.get('table_view')
        eliminate_rule_id = attrs.get('eliminate_rule_id', True)

        if filter_index is None:
            filter_index = self._selected_filter_index(filter_popup)

        filtered = [
            item for item in all_items
            if item_matches_filter(item, filter_index, eliminate_rule_id)
        ]

        if data_source:
            data_source.set_eliminate_rule_id(eliminate_rule_id)
            data_source.set_filter_index(filter_index)
            data_source.set_items(filtered)
        checkbox_column = attrs.get('checkbox_column')
        if checkbox_column:
            checkbox_column.setEditable_(filter_index > 0)
        self._update_detail_pane_title(filter_index)
        if table_view:
            table_view.reloadData()
            if filtered:
                table_view.selectRowIndexes_byExtendingSelection_(NSIndexSet.indexSetWithIndex_(0), False)
                self.show_item(filtered[0], filter_index)
            else:
                table_view.deselectAll_(None)
                self.clear_item()

    @objc.python_method
    def _update_detail_pane_title(self, filter_index: int):
        attrs = get_view_attrs(self)
        detail_box = attrs.get('detail_box')
        if detail_box:
            pane_title, _ = FILTER_INDEX_TO_DETAIL.get(filter_index, ("Check Text", "check_text"))
            detail_box.setTitle_(pane_title)

    @objc.python_method
    def show_item(self, item: ImplementationTestItem, filter_index=None):
        """Show field-appropriate detail text for the selected checklist item."""
        attrs = get_view_attrs(self)
        detail_text_view = attrs.get('detail_text_view')
        if not detail_text_view:
            return
        eliminate_rule_id = attrs.get('eliminate_rule_id', True)
        older_stig = attrs.get('older_stig')
        newer_stig = attrs.get('newer_stig')
        if filter_index is None:
            filter_popup = attrs.get('filter_popup')
            filter_index = self._selected_filter_index(filter_popup)
        type_codes = format_type_codes(item, eliminate_rule_id, filter_index)
        if filter_index > 0 and type_codes:
            type_line = f"Type: {type_codes}"
        else:
            type_line = f"Types: {type_codes or '(none)'}"

        if older_stig and newer_stig:
            _, detail_body = build_detail_content(item, filter_index, older_stig, newer_stig)
        else:
            detail_body = item.check_text

        content = (
            f"{item.v_code} - {item.rule_title}\n"
            f"{type_line}\n"
            f"Severity: {item.severity.upper()}\n\n"
            f"{detail_body}"
        )
        detail_text_view.setString_(content)
        self._update_detail_pane_title(filter_index)

    @objc.python_method
    def clear_item(self):
        attrs = get_view_attrs(self)
        detail_text_view = attrs.get('detail_text_view')
        if detail_text_view:
            detail_text_view.setString_("Select a checklist item to view details.")

    def closeDetailedComparisonTab_(self, sender):
        """Close this detailed comparison tab."""
        attrs = get_view_attrs(self)
        main_window = attrs.get('main_window')
        tab_label = attrs.get('tab_label')
        if main_window and tab_label:
            main_window.remove_detailed_comparison_tab(tab_label)

    @objc.python_method
    def _layout_bottom_content(self):
        """Lay out the detail scroll view and Close Tab button within the bottom pane."""
        attrs = get_view_attrs(self)
        bottom_box = attrs.get('detail_box')
        detail_scroll = attrs.get('detail_scroll')
        close_btn = attrs.get('close_btn')
        if not bottom_box or not detail_scroll:
            return

        bottom_content = bottom_box.contentView()
        bottom_width, bottom_height = get_bounds_size(bottom_content.bounds())
        margin = 10
        footer_height = 40

        if close_btn:
            close_btn.setFrame_(NSRect((margin, 8), (100, 28)))

        scroll_height = max(40, bottom_height - footer_height - margin)
        detail_scroll.setFrame_(
            NSRect((margin, footer_height), (max(100, bottom_width - (2 * margin)), scroll_height))
        )

    def resizeSubviewsWithOldSize_(self, old_size):
        objc.super(DetailedComparisonView, self).resizeSubviewsWithOldSize_(old_size)
        self._layout_bottom_content()

    def viewDidMoveToWindow(self):
        self._layout_bottom_content()

    def createUI(self):
        bounds = self.bounds()
        width, height = get_bounds_size(bounds)
        if width == 0 or height == 0:
            width, height = 1200, 800
            self.setFrame_(NSRect((0, 0), (width, height)))

        split_view = NSSplitView.alloc().initWithFrame_(NSRect((0, 0), (width, height)))
        split_view.setVertical_(False)
        split_view.setDividerStyle_(1)
        split_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)

        top_height = int(height * 0.65)
        bottom_height = height - top_height

        top_box = NSBox.alloc().initWithFrame_(NSRect((0, 0), (width, top_height)))
        top_box.setTitlePosition_(2)
        top_box.setTitle_("Implementation Test Checklist")
        top_box.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        top_content = top_box.contentView()
        top_width, top_box_height = get_bounds_size(top_content.bounds())

        summary = NSTextField.alloc().initWithFrame_(NSRect((10, top_box_height - 28), (top_width - 20, 22)))
        summary.setStringValue_("Select checklist items as tests are created for the newer STIG.")
        summary.setBezeled_(False)
        summary.setDrawsBackground_(False)
        summary.setEditable_(False)
        summary.setSelectable_(False)
        summary.setTextColor_(NSColor.whiteColor())
        summary.setAutoresizingMask_(0x08 | 0x02)
        top_content.addSubview_(summary)

        filter_y = top_box_height - 58
        filter_label = NSTextField.alloc().initWithFrame_(NSRect((10, filter_y), (55, 22)))
        filter_label.setStringValue_("Filter")
        filter_label.setBezeled_(False)
        filter_label.setDrawsBackground_(False)
        filter_label.setEditable_(False)
        filter_label.setSelectable_(False)
        filter_label.setTextColor_(NSColor.whiteColor())
        filter_label.setAutoresizingMask_(0x08 | 0x02)
        top_content.addSubview_(filter_label)

        filter_popup = NSPopUpButton.alloc().initWithFrame_(NSRect((70, filter_y - 2), (165, 26)))
        for option in FILTER_OPTIONS:
            if option == RULE_ID_FILTER_OPTION:
                continue
            filter_popup.addItemWithTitle_(option)
        filter_popup.selectItemAtIndex_(0)
        filter_popup.setAutoresizingMask_(0x08)
        filter_popup.setTarget_(self)
        filter_popup.setAction_("filterChanged:")
        top_content.addSubview_(filter_popup)

        eliminate_cb = NSButton.alloc().initWithFrame_(NSRect((245, filter_y - 1), (220, 24)))
        eliminate_cb.setTitle_("Eliminate New Rule ID")
        eliminate_cb.setButtonType_(3)
        eliminate_cb.setState_(1)
        eliminate_cb.setTarget_(self)
        eliminate_cb.setAction_("eliminateRuleIdChanged:")
        eliminate_cb.setAutoresizingMask_(0x08)
        top_content.addSubview_(eliminate_cb)

        list_height = max(120, top_box_height - 100)
        scroll_view = NSScrollView.alloc().initWithFrame_(NSRect((10, 10), (top_width - 20, list_height)))
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setHasHorizontalScroller_(False)
        scroll_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        scroll_view.setBorderType_(1)

        data_source = DetailedComparisonDataSource.alloc().init()
        table_view = NSTableView.alloc().initWithFrame_(scroll_view.bounds())
        table_view.setDataSource_(data_source)
        table_view.setAllowsColumnReordering_(False)
        table_view.setUsesAlternatingRowBackgroundColors_(True)
        table_view.setRowHeight_(22)
        table_view.setHeaderView_(None)

        checkbox_column = NSTableColumn.alloc().initWithIdentifier_("checkbox")
        checkbox_column.setWidth_(30)
        checkbox_column.setMinWidth_(30)
        checkbox_column.setMaxWidth_(30)
        checkbox_column.setEditable_(True)
        checkbox_cell = NSButtonCell.alloc().init()
        checkbox_cell.setButtonType_(3)
        checkbox_cell.setTitle_("")
        checkbox_cell.setAllowsMixedState_(True)
        checkbox_column.setDataCell_(checkbox_cell)
        checkbox_column.setEditable_(False)
        table_view.addTableColumn_(checkbox_column)

        type_column = NSTableColumn.alloc().initWithIdentifier_("type")
        type_column.setWidth_(160)
        type_column.setMinWidth_(100)
        type_column.setMaxWidth_(220)
        type_column.setResizingMask_(1)
        table_view.addTableColumn_(type_column)

        vcode_column = NSTableColumn.alloc().initWithIdentifier_("vcode")
        vcode_column.setWidth_(100)
        vcode_column.setMinWidth_(90)
        table_view.addTableColumn_(vcode_column)

        title_column = NSTableColumn.alloc().initWithIdentifier_("title")
        title_column.setWidth_(max(200, top_width - 250))
        title_column.setResizingMask_(1)
        table_view.addTableColumn_(title_column)

        delegate = DetailedComparisonDelegate.alloc().init()
        delegate.set_detail_view(self)
        table_view.setDelegate_(delegate)

        scroll_view.setDocumentView_(table_view)
        top_content.addSubview_(scroll_view)
        split_view.addSubview_(top_box)

        bottom_box = NSBox.alloc().initWithFrame_(NSRect((0, 0), (width, bottom_height)))
        bottom_box.setTitlePosition_(2)
        bottom_box.setTitle_("Check Text")
        bottom_box.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        bottom_content = bottom_box.contentView()
        bottom_width, bottom_box_height = get_bounds_size(bottom_content.bounds())

        detail_footer_height = 40
        detail_margin = 10
        scroll_height = max(40, bottom_box_height - detail_footer_height - detail_margin)

        close_btn = NSButton.alloc().initWithFrame_(
            NSRect((detail_margin, 8), (100, 28))
        )
        close_btn.setTitle_("Close Tab")
        close_btn.setTarget_(self)
        close_btn.setAction_("closeDetailedComparisonTab:")
        close_btn.setAutoresizingMask_(0x04 | 0x08)
        bottom_content.addSubview_(close_btn)

        detail_scroll = NSScrollView.alloc().initWithFrame_(
            NSRect(
                (detail_margin, detail_footer_height),
                (max(100, bottom_width - (2 * detail_margin)), scroll_height),
            )
        )
        detail_scroll.setHasVerticalScroller_(True)
        detail_scroll.setHasHorizontalScroller_(False)
        detail_scroll.setAutoresizingMask_(0x02 | 0x08 | 0x10 | 0x20)
        detail_scroll.setBorderType_(1)

        detail_text_view = NSTextView.alloc().initWithFrame_(detail_scroll.bounds())
        detail_text_view.setEditable_(False)
        detail_text_view.setSelectable_(True)
        detail_text_view.setRichText_(False)
        detail_text_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        detail_text_view.setString_("Select a checklist item to view details.")
        detail_text_view.setTextColor_(NSColor.whiteColor())
        detail_text_view.setBackgroundColor_(NSColor.blackColor())
        detail_text_view.setFont_(NSFont.systemFontOfSize_(12))
        detail_scroll.setDocumentView_(detail_text_view)
        bottom_content.addSubview_(detail_scroll)

        split_view.addSubview_(bottom_box)
        split_view.adjustSubviews()
        self.addSubview_(split_view)
        self._layout_bottom_content()

        attrs = get_view_attrs(self)
        attrs['summary_label'] = summary
        attrs['filter_popup'] = filter_popup
        attrs['eliminate_rule_id_cb'] = eliminate_cb
        attrs['checkbox_column'] = checkbox_column
        attrs['table_view'] = table_view
        attrs['data_source'] = data_source
        attrs['detail_box'] = bottom_box
        attrs['detail_scroll'] = detail_scroll
        attrs['close_btn'] = close_btn
        attrs['detail_text_view'] = detail_text_view
