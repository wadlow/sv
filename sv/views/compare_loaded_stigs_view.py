"""Compare view for comparing two STIGs already loaded in the viewer."""

from AppKit import (
    NSRect, NSScrollView, NSTableColumn, NSButton, NSTextField,
    NSColor, NSBox, NSAlert
)
from Foundation import NSObject
import objc
import re
from collections import defaultdict
from typing import List, Tuple

from ..models.stig_file import StigFile
from ..utils.stig_repository import _loaded_version_to_repo_format, _parse_version_tuple
from .compare_view import CompareView
from .stigs_pane import TooltipTableView
from .view_helpers import get_view_attrs, get_bounds_size


def _stig_display_label(stig: StigFile) -> str:
    """Format a STIG for display in the selection lists."""
    return stig.display_name


def _normalize_for_family_match(name: str) -> str:
    """Normalize a STIG display name for grouping related product lines."""
    normalized = name.lower().replace('postgresql', 'postgres')
    normalized = re.sub(r'\s+\d+$', '', normalized)
    return ' '.join(normalized.split())


def _stig_family_key(stig: StigFile) -> str:
    """Group STIGs that are the same product under different benchmark titles."""
    return _normalize_for_family_match(stig.display_name)


def _stig_generation_rank(stig: StigFile) -> int:
    """
    Infer product generation from the STIG name.

    Unnumbered names such as "Crunchy Data PostgreSQL" rank lower than names
    that include a major version such as "Crunchy Data Postgres 16".
    """
    name = stig.display_name.lower().replace('postgresql', 'postgres')
    match = re.search(r'postgres\s*(\d+)', name)
    if match:
        return int(match.group(1))
    match = re.search(r'\s(\d+)$', name)
    if match:
        return int(match.group(1))
    return 0


def _stig_newness_key(stig: StigFile) -> Tuple[int, Tuple[int, int]]:
    """Return a sort key where higher values indicate a newer STIG."""
    return (_stig_generation_rank(stig), _stig_version_key(stig))


def _stig_version_key(stig: StigFile) -> Tuple[int, int]:
    """Return a sortable (version, release) tuple for a STIG."""
    repo_fmt = _loaded_version_to_repo_format(stig.stig_version, stig.stig_release)
    if repo_fmt:
        parsed = _parse_version_tuple(repo_fmt)
        if parsed:
            return parsed
    return (0, 0)


def partition_stigs_for_comparison(stig_files: List[StigFile]) -> Tuple[List[StigFile], List[StigFile]]:
    """
    Split loaded STIGs into older and newer lists by product family.

    STIGs that appear only once in a family are excluded from both lists.
    When multiple related STIGs are loaded (including renamed benchmarks such as
    "Crunchy Data PostgreSQL" and "Crunchy Data Postgres 16"), the newest goes
    in newer_stigs and all others go in older_stigs.
    """
    groups = defaultdict(list)
    for stig in stig_files:
        groups[_stig_family_key(stig)].append(stig)

    older_stigs: List[StigFile] = []
    newer_stigs: List[StigFile] = []

    for stigs in groups.values():
        if len(stigs) < 2:
            continue
        sorted_stigs = sorted(stigs, key=_stig_newness_key)
        newer_stigs.append(sorted_stigs[-1])
        older_stigs.extend(sorted_stigs[:-1])

    sort_key = lambda stig: (stig.display_name.lower(), _stig_version_key(stig))
    older_stigs.sort(key=sort_key)
    newer_stigs.sort(key=sort_key)
    return older_stigs, newer_stigs


class LoadedStigPickerDataSource(NSObject):
    """Data source for a loaded-STIG selection table."""

    def init(self):
        self = objc.super(LoadedStigPickerDataSource, self).init()
        if self is None:
            return None
        self.stig_files = []
        return self

    @objc.python_method
    def set_stig_files(self, stig_files: List[StigFile]):
        self.stig_files = list(stig_files) if stig_files else []

    def numberOfRowsInTableView_(self, table_view):
        return len(self.stig_files)

    def tableView_objectValueForTableColumn_row_(self, table_view, table_column, row):
        if 0 <= row < len(self.stig_files):
            return _stig_display_label(self.stig_files[row])
        return ""


class LoadedStigPickerDelegate(NSObject):
    """Delegate for loaded-STIG selection table."""

    def init(self):
        self = objc.super(LoadedStigPickerDelegate, self).init()
        if self is None:
            return None
        attrs = get_view_attrs(self)
        attrs['compare_view'] = None
        attrs['picker_key'] = None  # 'stig_a_index' or 'stig_b_index'
        return self

    @objc.python_method
    def set_compare_view(self, compare_view, picker_key):
        attrs = get_view_attrs(self)
        attrs['compare_view'] = compare_view
        attrs['picker_key'] = picker_key

    def tableViewSelectionDidChange_(self, notification):
        attrs = get_view_attrs(self)
        compare_view = attrs.get('compare_view')
        picker_key = attrs.get('picker_key')
        if not compare_view or not picker_key:
            return

        table_view = notification.object()
        selected_row = table_view.selectedRow()
        view_attrs = get_view_attrs(compare_view)
        if selected_row >= 0:
            view_attrs[picker_key] = selected_row
        else:
            view_attrs[picker_key] = None
        compare_view._update_compare_button_state()


class CompareLoadedStigsView(CompareView):
    """Compare tab that selects STIGs from those already loaded in the viewer."""

    def init(self):
        self = objc.super(CompareView, self).init()
        if self is None:
            return None

        attrs = get_view_attrs(self)
        attrs['stig_a'] = None
        attrs['stig_b'] = None
        attrs['main_window'] = None
        attrs['table_data_sources'] = []
        attrs['table_views'] = []
        attrs['table_delegates'] = []
        attrs['detail_text_views'] = []
        attrs['severity_filters'] = {'high': True, 'medium': True, 'low_other': True}
        attrs['show_rule_id_differences'] = False
        attrs['unfiltered_data'] = {'in_b_not_a': [], 'in_a_not_b': [], 'different': []}
        attrs['loaded_stig_files'] = []
        attrs['older_stigs'] = []
        attrs['newer_stigs'] = []
        attrs['stig_a_index'] = None
        attrs['stig_b_index'] = None
        attrs['compared_stig_a_index'] = None
        attrs['compared_stig_b_index'] = None
        attrs['stig_a'] = None
        attrs['stig_b'] = None
        attrs['unfiltered_data'] = {'in_b_not_a': [], 'in_a_not_b': [], 'different': []}
        CompareView.createLayout(self)
        return self

    @objc.python_method
    def set_stig_files(self, stig_files: List[StigFile]):
        """Set the list of loaded STIGs available for selection."""
        attrs = get_view_attrs(self)
        attrs['loaded_stig_files'] = list(stig_files) if stig_files else []
        older_stigs, newer_stigs = partition_stigs_for_comparison(attrs['loaded_stig_files'])
        attrs['older_stigs'] = older_stigs
        attrs['newer_stigs'] = newer_stigs
        attrs['stig_a_index'] = None
        attrs['stig_b_index'] = None
        attrs['compared_stig_a_index'] = None
        attrs['compared_stig_b_index'] = None
        attrs['stig_a'] = None
        attrs['stig_b'] = None
        attrs['unfiltered_data'] = {'in_b_not_a': [], 'in_a_not_b': [], 'different': []}

        picker_lists = {
            'stig_a': older_stigs,
            'stig_b': newer_stigs,
        }
        for picker_key, stigs in picker_lists.items():
            data_source = attrs.get(f'{picker_key}_data_source')
            table_view = attrs.get(f'{picker_key}_table_view')
            if data_source:
                data_source.set_stig_files(stigs)
            if table_view:
                table_view.deselectAll_(None)
                table_view.reloadData()

        self._update_compare_button_state()
        self._update_detailed_comparison_button_state()
        self._update_evaluate_new_stig_button_state()

    @objc.python_method
    def _run_comparison(self, stig_a, stig_b):
        """Compare STIGs and enable follow-up actions when results are ready."""
        CompareView._run_comparison(self, stig_a, stig_b)
        self._update_detailed_comparison_button_state()
        self._update_evaluate_new_stig_button_state()

    @objc.python_method
    def _has_completed_comparison(self) -> bool:
        attrs = get_view_attrs(self)
        return (
            attrs.get('stig_a') is not None and
            attrs.get('stig_b') is not None and
            attrs.get('compared_stig_a_index') is not None and
            attrs.get('compared_stig_b_index') is not None
        )

    @objc.python_method
    def _update_detailed_comparison_button_state(self):
        """Enable Detailed Comparison only after a comparison has been run."""
        attrs = get_view_attrs(self)
        detailed_btn = attrs.get('detailed_comparison_btn')
        if detailed_btn:
            detailed_btn.setEnabled_(self._has_completed_comparison())

    @objc.python_method
    def _update_evaluate_new_stig_button_state(self):
        """Enable Evaluate New STIG only after a comparison has been run."""
        attrs = get_view_attrs(self)
        evaluate_btn = attrs.get('evaluate_new_stig_btn')
        if evaluate_btn:
            evaluate_btn.setEnabled_(self._has_completed_comparison())

    def detailedComparison_(self, sender):
        """Open a detailed comparison checklist tab for the current comparison."""
        attrs = get_view_attrs(self)
        older_stig = attrs.get('stig_a')
        newer_stig = attrs.get('stig_b')
        unfiltered_data = attrs.get('unfiltered_data', {})
        main_window = attrs.get('main_window')
        if not older_stig or not newer_stig or not main_window:
            return

        from .detailed_comparison_view import (
            DetailedComparisonView,
            build_implementation_checklist,
        )
        items = build_implementation_checklist(older_stig, newer_stig, unfiltered_data)
        detailed_view = DetailedComparisonView.alloc().init()
        detailed_view.set_comparison(older_stig, newer_stig, items)
        main_window.add_detailed_comparison_tab(newer_stig.display_name, detailed_view)

    def evaluateNewStig_(self, sender):
        """Open a tab evaluating duplicate content in new V-codes."""
        attrs = get_view_attrs(self)
        older_stig = attrs.get('stig_a')
        newer_stig = attrs.get('stig_b')
        unfiltered_data = attrs.get('unfiltered_data', {})
        main_window = attrs.get('main_window')
        if not older_stig or not newer_stig or not main_window:
            return

        from .new_stig_evaluation_view import (
            NewStigEvaluationView,
            build_new_stig_evaluation,
        )
        items = build_new_stig_evaluation(older_stig, newer_stig, unfiltered_data)
        evaluation_view = NewStigEvaluationView.alloc().init()
        evaluation_view.set_evaluation(older_stig, newer_stig, items)
        main_window.add_new_stig_evaluation_tab(evaluation_view)

    def closeCompareTab_(self, sender):
        attrs = get_view_attrs(self)
        main_window = attrs.get('main_window')
        if main_window:
            main_window.remove_compare_loaded_tab()

    def compareStigs_(self, sender):
        """Compare the two selected loaded STIGs."""
        attrs = get_view_attrs(self)
        older_stigs = attrs.get('older_stigs', [])
        newer_stigs = attrs.get('newer_stigs', [])
        stig_a_index = attrs.get('stig_a_index')
        stig_b_index = attrs.get('stig_b_index')

        if stig_a_index is None or stig_b_index is None:
            return
        if not (0 <= stig_a_index < len(older_stigs) and 0 <= stig_b_index < len(newer_stigs)):
            return

        stig_a = older_stigs[stig_a_index]
        stig_b = newer_stigs[stig_b_index]

        if _stig_family_key(stig_a) != _stig_family_key(stig_b):
            alert = NSAlert.alloc().init()
            alert.setMessageText_("Select Matching STIGs")
            alert.setInformativeText_(
                "Please select an older and newer version of the same STIG to compare."
            )
            alert.setAlertStyle_(1)
            alert.runModal()
            return

        print(
            f"CompareLoadedStigsView.compareStigs_: Comparing "
            f"{stig_a.display_name} V{stig_a.stig_version} R{stig_a.stig_release} vs "
            f"V{stig_b.stig_version} R{stig_b.stig_release}"
        )
        attrs['compared_stig_a_index'] = stig_a_index
        attrs['compared_stig_b_index'] = stig_b_index
        self._run_comparison(stig_a, stig_b)

    @objc.python_method
    def _update_compare_button_state(self):
        """Enable Compare when matching older/newer STIGs are selected."""
        attrs = get_view_attrs(self)
        stig_a_index = attrs.get('stig_a_index')
        stig_b_index = attrs.get('stig_b_index')
        older_stigs = attrs.get('older_stigs', [])
        newer_stigs = attrs.get('newer_stigs', [])
        compare_btn = attrs.get('compare_btn')

        if compare_btn:
            should_enable = False
            if (
                stig_a_index is not None and
                stig_b_index is not None and
                0 <= stig_a_index < len(older_stigs) and
                0 <= stig_b_index < len(newer_stigs)
            ):
                should_enable = (
                    _stig_family_key(older_stigs[stig_a_index]) ==
                    _stig_family_key(newer_stigs[stig_b_index])
                )
            compare_btn.setEnabled_(should_enable)

        self._update_detailed_comparison_button_state()
        self._update_evaluate_new_stig_button_state()

    def _create_loader_pane(self, frame):
        """Create STIG selection pane with two pickers and a Compare button."""
        width, height = get_bounds_size(frame)

        pane = NSBox.alloc().initWithFrame_(frame)
        pane.setBoxType_(3)
        pane.setBorderType_(1)
        pane.setTitlePosition_(0)
        pane.setAutoresizingMask_(0x02 | 0x10)

        content = pane.contentView()
        content_bounds = content.bounds()
        content_width, content_height = get_bounds_size(content_bounds)

        top_margin = 20
        label_height = 20
        title_to_selector_gap = 6
        selector_to_next_gap = 28
        button_height = 28
        button_gap = 8
        bottom_margin = 10

        button_stack_height = (
            (button_height * 3) + (button_gap * 2) + bottom_margin + selector_to_next_gap
        )
        picker_labels_height = (
            (label_height + title_to_selector_gap) * 2 +
            selector_to_next_gap * 2
        )
        table_height = max(
            60,
            int((content_height - top_margin - button_stack_height - picker_labels_height) / 2),
        )
        y_pos = content_height - top_margin

        label_a = NSTextField.alloc().initWithFrame_(NSRect((10, y_pos - label_height), (content_width - 20, label_height)))
        label_a.setStringValue_("Older STIGs")
        label_a.setBezeled_(False)
        label_a.setDrawsBackground_(False)
        label_a.setEditable_(False)
        label_a.setSelectable_(False)
        label_a.setTextColor_(NSColor.whiteColor())
        label_a.setAutoresizingMask_(0x08 | 0x02)
        content.addSubview_(label_a)
        y_pos -= label_height + title_to_selector_gap

        self._create_stig_picker(content, NSRect((10, y_pos - table_height), (content_width - 20, table_height)), 'stig_a')
        y_pos -= table_height + selector_to_next_gap

        label_b = NSTextField.alloc().initWithFrame_(NSRect((10, y_pos - label_height), (content_width - 20, label_height)))
        label_b.setStringValue_("Newer STIGs")
        label_b.setBezeled_(False)
        label_b.setDrawsBackground_(False)
        label_b.setEditable_(False)
        label_b.setSelectable_(False)
        label_b.setTextColor_(NSColor.whiteColor())
        label_b.setAutoresizingMask_(0x08 | 0x02)
        content.addSubview_(label_b)
        y_pos -= label_height + title_to_selector_gap

        self._create_stig_picker(content, NSRect((10, y_pos - table_height), (content_width - 20, table_height)), 'stig_b')
        y_pos -= table_height + selector_to_next_gap

        compare_y = bottom_margin + (2 * (button_height + button_gap))
        detailed_y = bottom_margin + button_height + button_gap
        evaluate_y = bottom_margin

        compare_btn = NSButton.alloc().initWithFrame_(NSRect((10, compare_y), (content_width - 20, button_height)))
        compare_btn.setTitle_("Compare STIGs")
        compare_btn.setButtonType_(0)
        compare_btn.setBezelStyle_(1)
        compare_btn.setEnabled_(False)
        compare_btn.setAutoresizingMask_(0x08 | 0x02)
        compare_btn.setTarget_(self)
        compare_btn.setAction_("compareStigs:")
        content.addSubview_(compare_btn)

        detailed_btn = NSButton.alloc().initWithFrame_(NSRect((10, detailed_y), (content_width - 20, button_height)))
        detailed_btn.setTitle_("Detailed Comparison")
        detailed_btn.setButtonType_(0)
        detailed_btn.setBezelStyle_(1)
        detailed_btn.setEnabled_(False)
        detailed_btn.setAutoresizingMask_(0x08 | 0x02)
        detailed_btn.setTarget_(self)
        detailed_btn.setAction_("detailedComparison:")
        content.addSubview_(detailed_btn)

        evaluate_btn = NSButton.alloc().initWithFrame_(NSRect((10, evaluate_y), (content_width - 20, button_height)))
        evaluate_btn.setTitle_("Evaluate New STIG")
        evaluate_btn.setButtonType_(0)
        evaluate_btn.setBezelStyle_(1)
        evaluate_btn.setEnabled_(False)
        evaluate_btn.setAutoresizingMask_(0x08 | 0x02)
        evaluate_btn.setTarget_(self)
        evaluate_btn.setAction_("evaluateNewStig:")
        content.addSubview_(evaluate_btn)

        self_attrs = get_view_attrs(self)
        self_attrs['compare_btn'] = compare_btn
        self_attrs['detailed_comparison_btn'] = detailed_btn
        self_attrs['evaluate_new_stig_btn'] = evaluate_btn

        return pane

    @objc.python_method
    def _create_stig_picker(self, parent, frame, picker_key):
        """Create a single-selection table for picking a loaded STIG."""
        width, height = get_bounds_size(frame)

        scroll_view = NSScrollView.alloc().initWithFrame_(frame)
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setHasHorizontalScroller_(False)
        scroll_view.setAutoresizingMask_(0x08 | 0x02)
        scroll_view.setBorderType_(1)

        table_view = TooltipTableView.alloc().initWithFrame_(NSRect((0, 0), (width, height)))
        table_view.setUsesAlternatingRowBackgroundColors_(True)
        table_view.setRowHeight_(20.0)
        table_view.setHeaderView_(None)
        table_view.setAllowsMultipleSelection_(False)

        column = NSTableColumn.alloc().initWithIdentifier_("stig")
        column.setWidth_(width - 20)
        column.setResizingMask_(1)
        table_view.addTableColumn_(column)

        data_source = LoadedStigPickerDataSource.alloc().init()
        table_view.setDataSource_(data_source)

        delegate = LoadedStigPickerDelegate.alloc().init()
        delegate.set_compare_view(self, f'{picker_key}_index')
        table_view.setDelegate_(delegate)

        scroll_view.setDocumentView_(table_view)
        parent.addSubview_(scroll_view)

        attrs = get_view_attrs(self)
        attrs[f'{picker_key}_data_source'] = data_source
        attrs[f'{picker_key}_table_view'] = table_view
        attrs[f'{picker_key}_delegate'] = delegate

        return table_view
