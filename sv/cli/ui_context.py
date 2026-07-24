"""Capture a snapshot of the current STIG Viewer UI state."""

from typing import Any, Dict, List, Optional

from ..models.stig_file import StigFile
from ..models.vuln_code import VulnCode
from ..views.view_helpers import get_view_attrs
from ..views.detailed_comparison_view import (
    ImplementationTestItem,
    TYPE_CODE_NFT,
    format_type_codes,
    get_applicable_type_codes,
    has_only_rule_id_change,
    master_checkbox_state,
    item_matches_filter_name,
)


def _stig_summary(stig: StigFile) -> str:
    return (
        f"{stig.display_name} "
        f"(V{stig.stig_version} R{stig.stig_release}, {len(stig.vuln_codes)} V-codes)"
    )


def _vuln_summary(vuln: VulnCode) -> str:
    title = vuln.rule_title
    if len(title) > 80:
        title = title[:77] + "..."
    return f"{vuln.v_code} [{vuln.severity}]: {title}"


def _find_vuln_by_display_code(stig: Optional[StigFile], vcode: str) -> Optional[VulnCode]:
    if not stig:
        return None
    target = vcode.upper()
    for vuln in stig.vuln_codes:
        if vuln.v_code.upper() == target:
            return vuln
    return None


def _find_checklist_item(items: List[ImplementationTestItem], vcode: str) -> Optional[ImplementationTestItem]:
    target = vcode.upper()
    for item in items:
        if item.v_code.upper() == target:
            return item
    return None


def _changed_field_labels(older_vuln: VulnCode, newer_vuln: VulnCode) -> List[str]:
    labels: List[str] = []
    for attr, label in (
        ('v_code', 'V-code label'),
        ('rule_id', 'Rule ID'),
        ('severity', 'Severity'),
        ('group_title', 'Group title'),
        ('rule_title', 'Rule title'),
        ('discussion', 'Discussion'),
        ('check_text', 'Check text'),
        ('fix_text', 'Fix text'),
    ):
        if getattr(older_vuln, attr) != getattr(newer_vuln, attr):
            labels.append(label)
    return labels


def _implementation_type_labels(
    item: ImplementationTestItem,
    eliminate_rule_id: bool = False,
) -> List[str]:
    """Human-readable labels for fields that drive type codes."""
    labels: List[str] = []
    if item.changed_check_text:
        labels.append('check text (NCT)')
    if item.changed_rule_title:
        labels.append('rule title (NRT)')
    if item.changed_severity:
        labels.append('severity (NS)')
    if item.changed_discussion:
        labels.append('discussion (ND)')
    if item.changed_fix_text:
        labels.append(f'fix text ({TYPE_CODE_NFT})')
    if item.changed_rule_id and not eliminate_rule_id:
        labels.append('rule ID (NRI)')
    if item.changed_group_title:
        labels.append('group title (NGT)')
    if item.changed_v_code:
        labels.append('V-code label (NVC)')
    return labels


def explain_checklist_vcode(app_controller, vcode: str) -> str:
    """Explain why a V-code appears on the active Detailed Comparison checklist."""
    main_window = app_controller.main_window
    if not main_window or not main_window.tab_view:
        return 'Main window is not available.'

    selected_item = main_window.tab_view.selectedTabViewItem()
    if not selected_item:
        return 'No tab is selected.'

    tab_label = str(selected_item.label())
    if not tab_label.startswith('Detailed Comparison:'):
        return (
            f"Current tab is '{tab_label}'. "
            f"Switch to a Detailed Comparison tab, then ask again about {vcode}."
        )

    view = selected_item.view()
    attrs = get_view_attrs(view)
    all_items: List[ImplementationTestItem] = attrs.get('all_items', [])
    item = _find_checklist_item(all_items, vcode)
    if not item:
        return f"{vcode} is not in this Detailed Comparison checklist."

    older_stig = attrs.get('older_stig')
    newer_stig = attrs.get('newer_stig')
    eliminate_rule_id = attrs.get('eliminate_rule_id', True)
    filter_popup = attrs.get('filter_popup')
    filter_name = filter_popup.titleOfSelectedItem() if filter_popup else 'All'
    filter_index = 0
    if filter_popup:
        title = filter_popup.titleOfSelectedItem()
        if title:
            from ..views.detailed_comparison_view import FILTER_OPTIONS
            try:
                filter_index = FILTER_OPTIONS.index(title)
            except ValueError:
                filter_index = 0
    data_source = attrs.get('data_source')
    visible_items = data_source.items if data_source else []
    visible = _find_checklist_item(visible_items, vcode) is not None

    if eliminate_rule_id and has_only_rule_id_change(item):
        lines = [
            f"{item.v_code}: {item.rule_title}",
            f"Category: {item.change_type}",
            '',
            f"{vcode} is in the checklist but hidden because only the rule ID changed.",
            'Uncheck "Eliminate New Rule ID" to show rule-ID-only items and NRI codes.',
        ]
        return '\n'.join(lines)

    lines = [
        f"{item.v_code}: {item.rule_title}",
        f"Category: {item.change_type}",
    ]

    newer_vuln = _find_vuln_by_display_code(newer_stig, vcode)
    older_vuln = None
    if newer_vuln and older_stig:
        older_lookup = {vc.id: vc for vc in older_stig.vuln_codes}
        older_vuln = older_lookup.get(newer_vuln.id)
    if not older_vuln:
        older_vuln = _find_vuln_by_display_code(older_stig, vcode)

    derived_item = item
    if item.change_type == 'Updated' and older_vuln and newer_vuln:
        derived_item = ImplementationTestItem(
            v_code=item.v_code,
            rule_title=item.rule_title,
            change_type=item.change_type,
            severity=item.severity,
            check_text=item.check_text,
            changed_check_text=older_vuln.check_text != newer_vuln.check_text,
            changed_rule_title=older_vuln.rule_title != newer_vuln.rule_title,
            changed_severity=older_vuln.severity != newer_vuln.severity,
            changed_discussion=older_vuln.discussion != newer_vuln.discussion,
            changed_fix_text=older_vuln.fix_text != newer_vuln.fix_text,
            changed_rule_id=older_vuln.rule_id != newer_vuln.rule_id,
            changed_group_title=older_vuln.group_title != newer_vuln.group_title,
            changed_v_code=older_vuln.v_code != newer_vuln.v_code,
        )

    lines.append(
        f"Type codes: {format_type_codes(derived_item, eliminate_rule_id, filter_index) or '(none)'}"
    )
    applicable = get_applicable_type_codes(derived_item, eliminate_rule_id)
    if applicable:
        checked = sorted(derived_item.checked_codes & set(applicable))
        lines.append(
            f"Checked off: {', '.join(checked) if checked else '(none)'} "
            f"of {', '.join(applicable)}"
        )
        if filter_index <= 0:
            state = master_checkbox_state(derived_item, eliminate_rule_id)
            if state == 1:
                master_label = 'yes (all type codes checked)'
            elif state == -1:
                master_label = 'partial (some type codes checked)'
            else:
                master_label = 'no'
            lines.append(f"Master complete: {master_label}")

    if item.change_type == 'New':
        lines.append('')
        lines.append(
            f"{vcode} is in the list because it exists only in the newer STIG "
            f"({ _stig_summary(newer_stig) if newer_stig else 'newer version' })."
        )
        lines.append('Type code N means this is a new implementation test to create.')
        if not visible and filter_name != 'All':
            lines.append(
                f"Note: hidden by the current filter ({filter_name}). "
                f"Choose 'All' or 'New' to see it in the table."
            )
        return '\n'.join(lines)

    lines.append('')
    lines.append(
        f"{vcode} is in the list because it exists in both STIG versions with differences."
    )
    if older_stig and newer_stig:
        lines.append(f"Older: {_stig_summary(older_stig)}")
        lines.append(f"Newer: {_stig_summary(newer_stig)}")

    if older_vuln and newer_vuln:
        changed = _changed_field_labels(older_vuln, newer_vuln)
        if changed:
            lines.append(f"Changed fields: {', '.join(changed)}")
        impl_labels = _implementation_type_labels(derived_item, eliminate_rule_id)
        if impl_labels:
            lines.append(f"Type codes reflect: {', '.join(impl_labels)}")
        else:
            lines.append('No type codes apply because no tracked fields differ.')

        if not format_type_codes(derived_item, eliminate_rule_id):
            lines.append('')
            lines.append(
                'This item had no type code because only fields outside NCT/NRT/NS '
                'were tracked previously. Discussion/fix/group-title changes now use '
                'ND, NFT, NGT, etc.'
            )
    else:
        lines.append('Could not load both V-code records for a field-by-field comparison.')

    if not visible and filter_name != 'All':
        matches = item_matches_filter_name(item, filter_name, eliminate_rule_id)
        if not matches:
            lines.append('')
            lines.append(
                f"Note: hidden by the current filter ({filter_name}). "
                f"Choose 'All' or a matching filter to see it in the table."
            )

    return '\n'.join(lines)


def capture_ui_state(app_controller) -> Dict[str, Any]:
    """Build a read-only snapshot of what the app is currently showing."""
    state: Dict[str, Any] = {
        'tab': 'Unknown',
        'loaded_stig_count': len(app_controller.stig_files),
        'loaded_stigs': [_stig_summary(s) for s in app_controller.stig_files],
    }

    main_window = app_controller.main_window
    if not main_window or not main_window.tab_view:
        return state

    selected_item = main_window.tab_view.selectedTabViewItem()
    if not selected_item:
        return state

    tab_label = str(selected_item.label())
    state['tab'] = tab_label
    view = selected_item.view()

    if tab_label == 'Explorer':
        _capture_explorer_state(app_controller, state)
    elif tab_label == 'Compare Loaded STIGs':
        _capture_compare_loaded_state(view, state)
    elif tab_label == 'Compare':
        _capture_compare_file_state(view, state)
    elif tab_label.startswith('Detailed Comparison:'):
        _capture_detailed_comparison_state(view, state)
    elif tab_label == 'Check for STIGs':
        state['view'] = 'Check for STIGs tab — lists loaded STIGs for update checks.'
    elif tab_label == 'Compare CKLs':
        state['view'] = 'Compare CKLs tab — compare checklist files.'
    elif view:
        state['view'] = f'Checklist tab: {tab_label}'

    return state


def _capture_explorer_state(app_controller, state: Dict[str, Any]):
    explorer = app_controller.main_window.get_explorer_view()
    if not explorer:
        return

    explorer_attrs = get_view_attrs(explorer)
    stigs_pane = explorer_attrs.get('stigs_pane')
    vcode_list_pane = explorer_attrs.get('vcode_list_pane')

    state['view'] = 'Explorer — browse loaded STIGs and V-codes.'

    if stigs_pane:
        from ..views.stigs_pane import StigsPane
        selected = StigsPane.get_selected_stigs(stigs_pane)
        checked = StigsPane.get_checked_stigs(stigs_pane)
        if selected:
            state['selected_stig'] = _stig_summary(selected[0])
        if checked:
            state['checked_stig_count'] = len(checked)

    if vcode_list_pane:
        pane_attrs = get_view_attrs(vcode_list_pane)
        table_view = pane_attrs.get('table_view')
        data_source = pane_attrs.get('data_source')
        if table_view and data_source and hasattr(data_source, 'vuln_codes'):
            state['visible_vcode_count'] = len(data_source.vuln_codes)
            selected_row = table_view.selectedRow()
            if 0 <= selected_row < len(data_source.vuln_codes):
                state['selected_vcode'] = _vuln_summary(data_source.vuln_codes[selected_row])


def _capture_compare_loaded_state(view, state: Dict[str, Any]):
    attrs = get_view_attrs(view)
    state['view'] = 'Compare Loaded STIGs — compare two loaded STIG versions.'

    older_stigs = attrs.get('older_stigs', [])
    newer_stigs = attrs.get('newer_stigs', [])
    state['older_stig_options'] = [_stig_summary(s) for s in older_stigs]
    state['newer_stig_options'] = [_stig_summary(s) for s in newer_stigs]

    stig_a_index = attrs.get('stig_a_index')
    stig_b_index = attrs.get('stig_b_index')
    if stig_a_index is not None and 0 <= stig_a_index < len(older_stigs):
        state['selected_older_stig'] = _stig_summary(older_stigs[stig_a_index])
    if stig_b_index is not None and 0 <= stig_b_index < len(newer_stigs):
        state['selected_newer_stig'] = _stig_summary(newer_stigs[stig_b_index])

    stig_a = attrs.get('stig_a')
    stig_b = attrs.get('stig_b')
    if stig_a and stig_b:
        state['comparison_active'] = True
        state['comparing'] = f"{_stig_summary(stig_a)} vs {_stig_summary(stig_b)}"
        unfiltered = attrs.get('unfiltered_data', {})
        state['in_newer_not_older'] = len(unfiltered.get('in_b_not_a', []))
        state['in_older_not_newer'] = len(unfiltered.get('in_a_not_b', []))
        state['different'] = len(unfiltered.get('different', []))
    else:
        state['comparison_active'] = False


def _capture_compare_file_state(view, state: Dict[str, Any]):
    attrs = get_view_attrs(view)
    state['view'] = 'Compare tab — compare STIGs loaded from files.'
    stig_a = attrs.get('stig_a')
    stig_b = attrs.get('stig_b')
    if stig_a and stig_b:
        state['comparison_active'] = True
        state['comparing'] = f"{_stig_summary(stig_a)} vs {_stig_summary(stig_b)}"
        unfiltered = attrs.get('unfiltered_data', {})
        state['in_newer_not_older'] = len(unfiltered.get('in_b_not_a', []))
        state['in_older_not_newer'] = len(unfiltered.get('in_a_not_b', []))
        state['different'] = len(unfiltered.get('different', []))
    else:
        state['comparison_active'] = False
        state['stig_a_file'] = attrs.get('stig_a_path', '(not loaded)')
        state['stig_b_file'] = attrs.get('stig_b_path', '(not loaded)')


def _capture_detailed_comparison_state(view, state: Dict[str, Any]):
    attrs = get_view_attrs(view)
    state['view'] = 'Detailed Comparison — implementation test checklist.'
    older = attrs.get('older_stig')
    newer = attrs.get('newer_stig')
    if older and newer:
        state['comparing'] = f"{_stig_summary(older)} vs {_stig_summary(newer)}"
    all_items = attrs.get('all_items', [])
    state['checklist_item_count'] = len(all_items)
    filter_popup = attrs.get('filter_popup')
    if filter_popup:
        state['filter'] = filter_popup.titleOfSelectedItem() or 'All'
    state['eliminate_rule_id'] = attrs.get('eliminate_rule_id', True)
    eliminate_rule_id = state['eliminate_rule_id']
    filter_index = 0
    if state.get('filter'):
        from ..views.detailed_comparison_view import FILTER_OPTIONS
        try:
            filter_index = FILTER_OPTIONS.index(state['filter'])
        except ValueError:
            filter_index = 0
    data_source = attrs.get('data_source')
    if data_source and data_source.items:
        state['visible_checklist_item_count'] = len(data_source.items)
        selected_row = attrs.get('table_view')
        if selected_row:
            row = selected_row.selectedRow()
            if 0 <= row < len(data_source.items):
                item = data_source.items[row]
                state['selected_checklist_item'] = (
                    f"{item.v_code} [{format_type_codes(item, eliminate_rule_id, filter_index)}]: "
                    f"{item.rule_title[:60]}"
                )


def format_state_summary(state: Dict[str, Any]) -> str:
    """Format UI state as human-readable text for CLI output."""
    lines = [f"Current tab: {state.get('tab', 'Unknown')}"]

    if state.get('view'):
        lines.append(state['view'])

    lines.append(f"Loaded STIGs: {state.get('loaded_stig_count', 0)}")
    if state.get('loaded_stigs'):
        for stig_line in state['loaded_stigs'][:10]:
            lines.append(f"  - {stig_line}")
        if len(state['loaded_stigs']) > 10:
            lines.append(f"  ... and {len(state['loaded_stigs']) - 10} more")

    for key, label in (
        ('selected_stig', 'Selected STIG'),
        ('selected_vcode', 'Selected V-code'),
        ('visible_vcode_count', 'Visible V-codes'),
        ('checked_stig_count', 'Checked STIGs'),
        ('selected_older_stig', 'Selected older STIG'),
        ('selected_newer_stig', 'Selected newer STIG'),
        ('comparing', 'Comparison'),
        ('comparison_active', 'Comparison active'),
        ('in_newer_not_older', 'In newer, not older'),
        ('in_older_not_newer', 'In older, not newer'),
        ('different', 'In both (different)'),
        ('filter', 'Checklist filter'),
        ('eliminate_rule_id', 'Eliminate New Rule ID'),
        ('checklist_item_count', 'Checklist items'),
        ('visible_checklist_item_count', 'Visible checklist items'),
        ('selected_checklist_item', 'Selected checklist item'),
        ('stig_a_file', 'STIG A file'),
        ('stig_b_file', 'STIG B file'),
    ):
        if key in state:
            lines.append(f"{label}: {state[key]}")

    lines.append('')
    lines.append('Ask about a checklist V-code, e.g.: vcode V-214247')
    return '\n'.join(lines)
