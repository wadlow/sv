"""Evaluate new V-codes in a newer STIG against an older STIG for duplicate content."""

import shlex
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from AppKit import (
    NSView, NSRect, NSBox, NSSplitView, NSScrollView, NSTableView, NSTableColumn,
    NSButton, NSTextField, NSTextView, NSColor, NSFont, NSPopUpButton,
    NSViewWidthSizable, NSViewHeightSizable,
)
from Foundation import NSObject, NSIndexSet
import objc

from ..models.stig_file import StigFile
from ..models.vuln_code import VulnCode
from .view_helpers import get_view_attrs, get_bounds_size


TAB_LABEL = "New STIG Evaluation"

FILTER_OPTIONS = [
    "All",
    "Rule Title",
    "Check Text",
    "Description",
    "Unmatched",
]

MATCH_RULE_TITLE = "RT"
MATCH_CHECK_TEXT = "CT"
MATCH_DESCRIPTION = "D"


@dataclass
class NewStigEvaluationItem:
    """A new V-code and its exact-content matches in the older STIG."""

    v_code: str
    rule_title: str
    check_text: str
    discussion: str
    severity: str = "medium"
    matched_rule_title: bool = False
    matched_check_text: bool = False
    matched_description: bool = False
    rule_title_matches: List[VulnCode] = field(default_factory=list)
    check_text_matches: List[VulnCode] = field(default_factory=list)
    discussion_matches: List[VulnCode] = field(default_factory=list)


def _index_older_vulns(older_stig: StigFile):
    by_rule_title: Dict[str, List[VulnCode]] = defaultdict(list)
    by_check_text: Dict[str, List[VulnCode]] = defaultdict(list)
    by_discussion: Dict[str, List[VulnCode]] = defaultdict(list)
    for vuln in older_stig.vuln_codes:
        if vuln.rule_title:
            by_rule_title[vuln.rule_title].append(vuln)
        if vuln.check_text:
            by_check_text[vuln.check_text].append(vuln)
        if vuln.discussion:
            by_discussion[vuln.discussion].append(vuln)
    return by_rule_title, by_check_text, by_discussion


def build_new_stig_evaluation(
    older_stig: StigFile,
    newer_stig: StigFile,
    unfiltered_data: Dict[str, List[str]],
) -> List[NewStigEvaluationItem]:
    """Find new V-codes whose content exactly matches something in the older STIG."""
    newer_lookup = {vc.id: vc for vc in newer_stig.vuln_codes}
    by_rule_title, by_check_text, by_discussion = _index_older_vulns(older_stig)
    items: List[NewStigEvaluationItem] = []

    for vcode_id in unfiltered_data.get("in_b_not_a", []):
        newer_vuln = newer_lookup.get(vcode_id)
        if not newer_vuln:
            continue

        rule_title_matches = list(by_rule_title.get(newer_vuln.rule_title, []))
        check_text_matches = list(by_check_text.get(newer_vuln.check_text, []))
        discussion_matches = list(by_discussion.get(newer_vuln.discussion, []))

        items.append(NewStigEvaluationItem(
            v_code=newer_vuln.v_code,
            rule_title=newer_vuln.rule_title,
            check_text=newer_vuln.check_text,
            discussion=newer_vuln.discussion,
            severity=newer_vuln.severity,
            matched_rule_title=bool(rule_title_matches),
            matched_check_text=bool(check_text_matches),
            matched_description=bool(discussion_matches),
            rule_title_matches=rule_title_matches,
            check_text_matches=check_text_matches,
            discussion_matches=discussion_matches,
        ))

    items.sort(key=lambda item: item.v_code)
    return items


def item_has_any_match(item: NewStigEvaluationItem) -> bool:
    """Return True if the new V-code matches any older V-code content."""
    return item.matched_rule_title or item.matched_check_text or item.matched_description


def unmatched_items(items: List[NewStigEvaluationItem]) -> List[NewStigEvaluationItem]:
    """Return new V-codes with no exact match in the older STIG."""
    return [item for item in items if not item_has_any_match(item)]


def severity_subdir(severity: str) -> str:
    """Map STIG severity to OLD/NEW subdirectory name (high, medium, or low)."""
    value = (severity or "medium").lower()
    if value in ("high", "critical"):
        return "high"
    if value == "low":
        return "low"
    return "medium"


def pick_source_vuln(item: NewStigEvaluationItem) -> Optional[VulnCode]:
    """Pick the best older V-code to copy for a matched new V-code."""
    if item.check_text_matches:
        return item.check_text_matches[0]
    if item.rule_title_matches:
        return item.rule_title_matches[0]
    if item.discussion_matches:
        return item.discussion_matches[0]
    return None


SAMPLE_NEW_TEST = """def test_v_261906(ssh, screenshot: false)
  all_pass = true
  messages = ""
  screenshot_content = ""
  shell_prompt = "rhel9-ato# "
  v_code = "V-261906"
  severity = "medium"
  description = "PostgreSQL and associated applications must reserve the use of dynamic code execution for situations that require it."
  all_pass = :na
  messages = "DTRS/Medweb employs PostgreSQL as an internal component, with no network or management access from outside the device.  There is no DB management interface available or needed."
  return [all_pass, messages, v_code, description, severity, screenshot_content]

  command_to_execute = ""
  result = execute_command(ssh, command_to_execute).strip

  if result.empty?
    msg = "FAIL: "
    messages << "  " + msg
    screenshot_content << "# " + msg
    all_pass = false
  else
    msg = "PASS: "
    messages << "  " + msg
    screenshot_content << "# " + msg
    all_pass = true
  end

  [all_pass, messages, v_code, description, severity, screenshot_content]
end"""


def default_new_test_template() -> str:
    """Return a Ruby test template derived from the sample V-261906 test."""
    return (
        SAMPLE_NEW_TEST
        .replace("test_v_261906", "test_v_@VCODE_NUM@")
        .replace("V-261906", "@VCODE@")
        .replace('severity = "medium"', 'severity = "@SEVERITY@"')
        .replace(
            "description = \"PostgreSQL and associated applications must reserve "
            "the use of dynamic code execution for situations that require it.\"",
            'description = "@DESCRIPTION@"',
        )
    )


def generate_copy_script(
    items: List[NewStigEvaluationItem],
    older_stig: StigFile,
    newer_stig: StigFile,
) -> str:
    """Build a bash script to copy old V-code files to new V-code names."""
    lines = [
        "#!/bin/bash",
        "# Copy old V-code files to new names based on STIG evaluation matches.",
        f"# Older STIG: {older_stig.display_name} "
        f"(V{older_stig.stig_version} R{older_stig.stig_release})",
        f"# Newer STIG: {newer_stig.display_name} "
        f"(V{newer_stig.stig_version} R{newer_stig.stig_release})",
        "",
        'OLD="../cpsql"',
        'NEW="."',
        "",
        "# V-code files live under severity subdirectories: high, medium, low.",
        "",
        "set -euo pipefail",
        "",
        'mkdir -p "$NEW/high" "$NEW/medium" "$NEW/low"',
        "",
        "copy_vcode() {",
        '  local old_code="$1"',
        '  local new_code="$2"',
        '  local src_severity="$3"',
        '  local dest_severity="$4"',
        '  local old_num="${old_code#V-}"',
        '  local new_num="${new_code#V-}"',
        '  local src="$OLD/${src_severity}/${old_code}.rb"',
        '  local dest="$NEW/${dest_severity}/${new_code}.rb"',
        '  if [ ! -f "$src" ]; then',
        '    echo "WARNING: no file found: ${src}" >&2',
        "    return 0",
        "  fi",
        '  if [ -e "$dest" ]; then',
        '    echo "SKIP: $dest already exists" >&2',
        "    return 0",
        "  fi",
        '  mkdir -p "$NEW/${dest_severity}"',
        '  sed -e "s|${old_code}|${new_code}|g" \\',
        '      -e "s|test_v_${old_num}|test_v_${new_num}|g" \\',
        '      "$src" > "$dest"',
        '  echo "Created $dest from $src (replaced ${old_code} and test_v_${old_num})"',
        "}",
        "",
    ]

    copy_count = 0
    for item in items:
        source_vuln = pick_source_vuln(item)
        if not source_vuln:
            continue
        src_severity = severity_subdir(source_vuln.severity)
        dest_severity = severity_subdir(item.severity)
        match_codes = format_match_codes(item)
        lines.append(
            f'copy_vcode "{source_vuln.v_code}" "{item.v_code}" '
            f'"{src_severity}" "{dest_severity}"  # {match_codes}'
        )
        copy_count += 1

    unmatched_count = sum(1 for item in items if not item_has_any_match(item))
    lines.extend([
        "",
        f"# Generated {copy_count} copy command(s).",
        f"# {unmatched_count} new V-code(s) have no older match and are not copied.",
    ])
    return "\n".join(lines) + "\n"


def generate_new_script(
    items: List[NewStigEvaluationItem],
    older_stig: StigFile,
    newer_stig: StigFile,
) -> str:
    """Build a bash script to create new V-code tests from a user template."""
    unmatched = unmatched_items(items)
    lines = [
        "#!/bin/bash",
        "# Create new V-code test files from a template for unmatched new V-codes.",
        f"# Older STIG: {older_stig.display_name} "
        f"(V{older_stig.stig_version} R{older_stig.stig_release})",
        f"# Newer STIG: {newer_stig.display_name} "
        f"(V{newer_stig.stig_version} R{newer_stig.stig_release})",
        "",
        'NEW="."',
        'TEMPLATE="./template.rb"',
        "",
        "# Template uses @VCODE@, @VCODE_NUM@, @SEVERITY@, and @DESCRIPTION@ placeholders.",
        "# If template.rb is missing, a default sample test template is created in NEW.",
        "# V-code files are created under severity subdirectories: high, medium, low.",
        "",
        "set -euo pipefail",
        "",
        'mkdir -p "$NEW/high" "$NEW/medium" "$NEW/low"',
        "",
        'if [ ! -f "$TEMPLATE" ]; then',
        '  echo "Creating default template: $TEMPLATE"',
        "  cat > \"$TEMPLATE\" <<'TEMPLATE_EOF'",
        *default_new_test_template().splitlines(),
        "TEMPLATE_EOF",
        "fi",
        "",
        "create_from_template() {",
        '  local vcode="$1"',
        '  local description="$2"',
        '  local dest_severity="$3"',
        '  local vcode_num="${vcode#V-}"',
        '  local dest="$NEW/${dest_severity}/${vcode}.rb"',
        '  if [ -e "$dest" ]; then',
        '    echo "SKIP: $dest already exists" >&2',
        "    return 0",
        "  fi",
        '  mkdir -p "$NEW/${dest_severity}"',
        '  sed -e "s|@VCODE@|${vcode}|g" \\',
        '      -e "s|@VCODE_NUM@|${vcode_num}|g" \\',
        '      -e "s|@SEVERITY@|${dest_severity}|g" \\',
        '      "$TEMPLATE" | awk -v desc="$description" \'{gsub(/@DESCRIPTION@/, desc); print}\' > "$dest"',
        '  echo "Created $dest  # ${description}"',
        "}",
        "",
    ]

    for item in unmatched:
        dest_severity = severity_subdir(item.severity)
        lines.append(
            f"create_from_template {shlex.quote(item.v_code)} "
            f"{shlex.quote(item.rule_title)} {shlex.quote(dest_severity)}"
        )

    lines.extend([
        "",
        f"# Generated {len(unmatched)} new test file command(s) for unmatched V-codes.",
        f"# {len(items) - len(unmatched)} matched V-code(s) are omitted.",
    ])
    return "\n".join(lines) + "\n"


def format_match_codes(item: NewStigEvaluationItem, filter_index: int = 0) -> str:
    """Format match category codes (RT, CT, D)."""
    if filter_index == 1:
        return MATCH_RULE_TITLE if item.matched_rule_title else ""
    if filter_index == 2:
        return MATCH_CHECK_TEXT if item.matched_check_text else ""
    if filter_index == 3:
        return MATCH_DESCRIPTION if item.matched_description else ""
    if filter_index == 4:
        return ""
    codes = []
    if item.matched_rule_title:
        codes.append(MATCH_RULE_TITLE)
    if item.matched_check_text:
        codes.append(MATCH_CHECK_TEXT)
    if item.matched_description:
        codes.append(MATCH_DESCRIPTION)
    return ", ".join(codes)


def item_matches_filter(item: NewStigEvaluationItem, filter_index: int) -> bool:
    """Return True if the item should appear under the given filter index."""
    if filter_index <= 0:
        return True
    if filter_index == 1:
        return item.matched_rule_title
    if filter_index == 2:
        return item.matched_check_text
    if filter_index == 3:
        return item.matched_description
    if filter_index == 4:
        return not item_has_any_match(item)
    return False


def _unique_v_codes(vulns: List[VulnCode]) -> List[str]:
    seen: Set[str] = set()
    result: List[str] = []
    for vuln in vulns:
        if vuln.v_code not in seen:
            seen.add(vuln.v_code)
            result.append(vuln.v_code)
    return sorted(result)


def matching_older_v_codes(item: NewStigEvaluationItem, filter_index: int = 0) -> str:
    """Return a display string of older V-codes that matched."""
    if filter_index == 1:
        return ", ".join(_unique_v_codes(item.rule_title_matches))
    if filter_index == 2:
        return ", ".join(_unique_v_codes(item.check_text_matches))
    if filter_index == 3:
        return ", ".join(_unique_v_codes(item.discussion_matches))
    if filter_index == 4:
        return ""

    matched: Set[str] = set()
    for vuln in item.rule_title_matches + item.check_text_matches + item.discussion_matches:
        matched.add(vuln.v_code)
    return ", ".join(sorted(matched))


def build_detail_content(item: NewStigEvaluationItem, filter_index: int) -> tuple:
    """Return pane title and body text for the selected filter."""
    if filter_index == 1:
        lines = [f"New rule title ({item.v_code}):\n{item.rule_title or '(none)'}"]
        older_codes = _unique_v_codes(item.rule_title_matches)
        if older_codes:
            lines.append(f"\nSame rule title in older STIG: {', '.join(older_codes)}")
        else:
            lines.append("\nNo matching rule title in older STIG.")
        return "Rule Title", "\n".join(lines)

    if filter_index == 2:
        lines = [f"New check text ({item.v_code}):\n{item.check_text or '(none)'}"]
        older_codes = _unique_v_codes(item.check_text_matches)
        if older_codes:
            lines.append(f"\nSame check text in older STIG: {', '.join(older_codes)}")
            if item.check_text_matches:
                sample = item.check_text_matches[0]
                lines.append(f"\nOlder example ({sample.v_code}):\n{sample.check_text}")
        else:
            lines.append("\nNo matching check text in older STIG.")
        return "Check Text", "\n".join(lines)

    if filter_index == 3:
        lines = [f"New description ({item.v_code}):\n{item.discussion or '(none)'}"]
        older_codes = _unique_v_codes(item.discussion_matches)
        if older_codes:
            lines.append(f"\nSame description in older STIG: {', '.join(older_codes)}")
            if item.discussion_matches:
                sample = item.discussion_matches[0]
                lines.append(f"\nOlder example ({sample.v_code}):\n{sample.discussion}")
        else:
            lines.append("\nNo matching description in older STIG.")
        return "Description", "\n".join(lines)

    if filter_index == 4:
        lines = [
            f"{item.v_code}: {item.rule_title}",
            "",
            "This new V-code has no exact rule title, check text, or description match",
            "in the older STIG.",
            "",
            f"Rule Title:\n{item.rule_title or '(none)'}",
            "",
            f"Check Text:\n{item.check_text or '(none)'}",
            "",
            f"Description:\n{item.discussion or '(none)'}",
        ]
        return "Unmatched V-code", "\n".join(lines)

    lines = [
        f"{item.v_code}: {item.rule_title}",
        f"Matches: {format_match_codes(item) or '(none)'}",
        f"Older V-codes with shared content: {matching_older_v_codes(item) or '(none)'}",
        "",
        f"Rule title match: {'yes' if item.matched_rule_title else 'no'}",
        f"Check text match: {'yes' if item.matched_check_text else 'no'}",
        f"Description match: {'yes' if item.matched_description else 'no'}",
        "",
        f"Rule Title:\n{item.rule_title or '(none)'}",
        "",
        f"Check Text:\n{item.check_text or '(none)'}",
        "",
        f"Description:\n{item.discussion or '(none)'}",
    ]
    return "Evaluation Summary", "\n".join(lines)


class NewStigEvaluationDataSource(NSObject):
    """Data source for the new STIG evaluation table."""

    def init(self):
        self = objc.super(NewStigEvaluationDataSource, self).init()
        if self is None:
            return None
        self.items: List[NewStigEvaluationItem] = []
        self.filter_index = 0
        return self

    @objc.python_method
    def set_items(self, items: List[NewStigEvaluationItem]):
        self.items = list(items) if items else []

    @objc.python_method
    def set_filter_index(self, filter_index: int):
        self.filter_index = filter_index

    def numberOfRowsInTableView_(self, table_view):
        return len(self.items)

    def tableView_objectValueForTableColumn_row_(self, table_view, column, row):
        if not (0 <= row < len(self.items)):
            return None
        item = self.items[row]
        col_id = str(column.identifier()) if column.identifier() else ""
        if col_id == "match":
            return format_match_codes(item, self.filter_index)
        if col_id == "vcode":
            return item.v_code
        if col_id == "older":
            return matching_older_v_codes(item, self.filter_index)
        if col_id == "title":
            return item.rule_title
        return None


class NewStigEvaluationDelegate(NSObject):
    """Delegate for evaluation table selection."""

    def init(self):
        self = objc.super(NewStigEvaluationDelegate, self).init()
        if self is None:
            return None
        attrs = get_view_attrs(self)
        attrs["evaluation_view"] = None
        return self

    @objc.python_method
    def set_evaluation_view(self, evaluation_view):
        get_view_attrs(self)["evaluation_view"] = evaluation_view

    def tableViewSelectionDidChange_(self, notification):
        attrs = get_view_attrs(self)
        evaluation_view = attrs.get("evaluation_view")
        if not evaluation_view:
            return
        table_view = notification.object()
        selected_row = table_view.selectedRow()
        data_source = table_view.dataSource()
        if selected_row >= 0 and data_source and 0 <= selected_row < len(data_source.items):
            evaluation_view.show_item(data_source.items[selected_row], data_source.filter_index)
        else:
            evaluation_view.clear_item()


class NewStigEvaluationView(NSView):
    """Tab for evaluating duplicate content in new V-codes."""

    def init(self):
        self = objc.super(NewStigEvaluationView, self).init()
        if self is None:
            return None

        attrs = get_view_attrs(self)
        attrs["older_stig"] = None
        attrs["newer_stig"] = None
        attrs["all_items"] = []
        attrs["main_window"] = None
        attrs["detail_box"] = None
        attrs["detail_scroll"] = None
        attrs["close_btn"] = None
        attrs["generate_copy_script_btn"] = None
        attrs["generate_new_script_btn"] = None
        attrs["copy_script_dialog"] = None
        attrs["new_script_dialog"] = None
        NewStigEvaluationView.createUI(self)
        return self

    @objc.python_method
    def set_evaluation(
        self,
        older_stig: StigFile,
        newer_stig: StigFile,
        items: List[NewStigEvaluationItem],
    ):
        attrs = get_view_attrs(self)
        attrs["older_stig"] = older_stig
        attrs["newer_stig"] = newer_stig
        attrs["all_items"] = items

        summary = attrs.get("summary_label")
        if summary:
            matched_count = sum(
                1 for item in items
                if item.matched_rule_title or item.matched_check_text or item.matched_description
            )
            summary.setStringValue_(
                f"Evaluating {len(items)} new V-codes in "
                f"{newer_stig.display_name} (V{newer_stig.stig_version} R{newer_stig.stig_release}) "
                f"against {older_stig.display_name} "
                f"(V{older_stig.stig_version} R{older_stig.stig_release}). "
                f"{matched_count} share exact rule title, check text, or description with the older STIG."
            )

        filter_popup = attrs.get("filter_popup")
        if filter_popup:
            filter_popup.selectItemAtIndex_(0)
        self._apply_filter()

    def filterChanged_(self, sender):
        from PyObjCTools import AppHelper
        AppHelper.callAfter(self._apply_filter)

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
    def _apply_filter(self):
        attrs = get_view_attrs(self)
        all_items = attrs.get("all_items", [])
        filter_popup = attrs.get("filter_popup")
        data_source = attrs.get("data_source")
        table_view = attrs.get("table_view")
        filter_index = self._selected_filter_index(filter_popup)

        filtered = [item for item in all_items if item_matches_filter(item, filter_index)]
        if data_source:
            data_source.set_filter_index(filter_index)
            data_source.set_items(filtered)
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
        detail_box = attrs.get("detail_box")
        if not detail_box:
            return
        if filter_index == 1:
            detail_box.setTitle_("Rule Title")
        elif filter_index == 2:
            detail_box.setTitle_("Check Text")
        elif filter_index == 3:
            detail_box.setTitle_("Description")
        elif filter_index == 4:
            detail_box.setTitle_("Unmatched V-code")
        else:
            detail_box.setTitle_("Evaluation Detail")

    def generateCopyScript_(self, sender):
        """Show a bash script to copy matched old V-code files to new names."""
        attrs = get_view_attrs(self)
        older_stig = attrs.get("older_stig")
        newer_stig = attrs.get("newer_stig")
        all_items = attrs.get("all_items", [])
        if not older_stig or not newer_stig:
            return

        script_text = generate_copy_script(all_items, older_stig, newer_stig)
        dialog = attrs.get("copy_script_dialog")
        if dialog is None:
            from ..dialogs.generate_script_dialog import GenerateScriptDialog
            dialog = GenerateScriptDialog()
            attrs["copy_script_dialog"] = dialog
        dialog.show(script_text, title="Generated Copy Script")

    def generateNewScript_(self, sender):
        """Show a bash script to create new tests from a template for unmatched V-codes."""
        attrs = get_view_attrs(self)
        older_stig = attrs.get("older_stig")
        newer_stig = attrs.get("newer_stig")
        all_items = attrs.get("all_items", [])
        if not older_stig or not newer_stig:
            return

        script_text = generate_new_script(all_items, older_stig, newer_stig)
        dialog = attrs.get("new_script_dialog")
        if dialog is None:
            from ..dialogs.generate_script_dialog import GenerateScriptDialog
            dialog = GenerateScriptDialog()
            attrs["new_script_dialog"] = dialog
        dialog.show(script_text, title="Generated New Script")

    @objc.python_method
    def show_item(self, item: NewStigEvaluationItem, filter_index=None):
        attrs = get_view_attrs(self)
        detail_text_view = attrs.get("detail_text_view")
        if not detail_text_view:
            return
        if filter_index is None:
            filter_popup = attrs.get("filter_popup")
            filter_index = self._selected_filter_index(filter_popup)
        _, detail_body = build_detail_content(item, filter_index)
        match_line = format_match_codes(item, filter_index)
        content = (
            f"{item.v_code} - {item.rule_title}\n"
            f"Matches: {match_line or '(none)'}\n"
            f"Older V-codes: {matching_older_v_codes(item, filter_index) or '(none)'}\n\n"
            f"{detail_body}"
        )
        detail_text_view.setString_(content)
        self._update_detail_pane_title(filter_index)

    @objc.python_method
    def clear_item(self):
        attrs = get_view_attrs(self)
        detail_text_view = attrs.get("detail_text_view")
        if detail_text_view:
            detail_text_view.setString_("Select a new V-code to view evaluation details.")

    def closeNewStigEvaluationTab_(self, sender):
        attrs = get_view_attrs(self)
        main_window = attrs.get("main_window")
        if main_window:
            main_window.remove_new_stig_evaluation_tab()

    @objc.python_method
    def _layout_bottom_content(self):
        attrs = get_view_attrs(self)
        bottom_box = attrs.get("detail_box")
        detail_scroll = attrs.get("detail_scroll")
        close_btn = attrs.get("close_btn")
        copy_script_btn = attrs.get("generate_copy_script_btn")
        new_script_btn = attrs.get("generate_new_script_btn")
        if not bottom_box or not detail_scroll:
            return

        bottom_content = bottom_box.contentView()
        bottom_width, bottom_height = get_bounds_size(bottom_content.bounds())
        margin = 10
        footer_height = 40

        if close_btn:
            close_btn.setFrame_(NSRect((margin, 8), (100, 28)))
        if copy_script_btn:
            copy_script_btn.setFrame_(NSRect((margin + 110, 8), (160, 28)))
        if new_script_btn:
            new_script_btn.setFrame_(NSRect((margin + 280, 8), (160, 28)))

        scroll_height = max(40, bottom_height - footer_height - margin)
        detail_scroll.setFrame_(
            NSRect((margin, footer_height), (max(100, bottom_width - (2 * margin)), scroll_height))
        )

    def resizeSubviewsWithOldSize_(self, old_size):
        objc.super(NewStigEvaluationView, self).resizeSubviewsWithOldSize_(old_size)
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
        top_box.setTitle_("New V-code Similarity")
        top_box.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        top_content = top_box.contentView()
        top_width, top_box_height = get_bounds_size(top_content.bounds())

        summary = NSTextField.alloc().initWithFrame_(NSRect((10, top_box_height - 28), (top_width - 20, 22)))
        summary.setStringValue_("Compare new V-codes against the older STIG for duplicate content.")
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

        filter_popup = NSPopUpButton.alloc().initWithFrame_(NSRect((70, filter_y - 2), (180, 26)))
        for option in FILTER_OPTIONS:
            filter_popup.addItemWithTitle_(option)
        filter_popup.selectItemAtIndex_(0)
        filter_popup.setAutoresizingMask_(0x08)
        filter_popup.setTarget_(self)
        filter_popup.setAction_("filterChanged:")
        top_content.addSubview_(filter_popup)

        list_height = max(120, top_box_height - 100)
        scroll_view = NSScrollView.alloc().initWithFrame_(NSRect((10, 10), (top_width - 20, list_height)))
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setHasHorizontalScroller_(False)
        scroll_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        scroll_view.setBorderType_(1)

        data_source = NewStigEvaluationDataSource.alloc().init()
        table_view = NSTableView.alloc().initWithFrame_(scroll_view.bounds())
        table_view.setDataSource_(data_source)
        table_view.setAllowsColumnReordering_(False)
        table_view.setUsesAlternatingRowBackgroundColors_(True)
        table_view.setRowHeight_(22)
        table_view.setHeaderView_(None)

        match_column = NSTableColumn.alloc().initWithIdentifier_("match")
        match_column.setWidth_(80)
        match_column.setMinWidth_(60)
        table_view.addTableColumn_(match_column)

        vcode_column = NSTableColumn.alloc().initWithIdentifier_("vcode")
        vcode_column.setWidth_(100)
        vcode_column.setMinWidth_(90)
        table_view.addTableColumn_(vcode_column)

        older_column = NSTableColumn.alloc().initWithIdentifier_("older")
        older_column.setWidth_(140)
        older_column.setMinWidth_(100)
        older_column.setResizingMask_(1)
        table_view.addTableColumn_(older_column)

        title_column = NSTableColumn.alloc().initWithIdentifier_("title")
        title_column.setWidth_(max(200, top_width - 340))
        title_column.setResizingMask_(1)
        table_view.addTableColumn_(title_column)

        delegate = NewStigEvaluationDelegate.alloc().init()
        delegate.set_evaluation_view(self)
        table_view.setDelegate_(delegate)

        scroll_view.setDocumentView_(table_view)
        top_content.addSubview_(scroll_view)
        split_view.addSubview_(top_box)

        bottom_box = NSBox.alloc().initWithFrame_(NSRect((0, 0), (width, bottom_height)))
        bottom_box.setTitlePosition_(2)
        bottom_box.setTitle_("Evaluation Detail")
        bottom_box.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        bottom_content = bottom_box.contentView()
        bottom_width, bottom_box_height = get_bounds_size(bottom_content.bounds())

        detail_footer_height = 40
        detail_margin = 10
        scroll_height = max(40, bottom_box_height - detail_footer_height - detail_margin)

        close_btn = NSButton.alloc().initWithFrame_(NSRect((detail_margin, 8), (100, 28)))
        close_btn.setTitle_("Close Tab")
        close_btn.setTarget_(self)
        close_btn.setAction_("closeNewStigEvaluationTab:")
        close_btn.setAutoresizingMask_(0x04 | 0x08)
        bottom_content.addSubview_(close_btn)

        copy_script_btn = NSButton.alloc().initWithFrame_(NSRect((detail_margin + 110, 8), (160, 28)))
        copy_script_btn.setTitle_("Generate Copy Script")
        copy_script_btn.setTarget_(self)
        copy_script_btn.setAction_("generateCopyScript:")
        copy_script_btn.setAutoresizingMask_(0x04 | 0x08)
        bottom_content.addSubview_(copy_script_btn)

        new_script_btn = NSButton.alloc().initWithFrame_(NSRect((detail_margin + 280, 8), (160, 28)))
        new_script_btn.setTitle_("Generate New Script")
        new_script_btn.setTarget_(self)
        new_script_btn.setAction_("generateNewScript:")
        new_script_btn.setAutoresizingMask_(0x04 | 0x08)
        bottom_content.addSubview_(new_script_btn)

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
        detail_text_view.setString_("Select a new V-code to view evaluation details.")
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
        attrs["summary_label"] = summary
        attrs["filter_popup"] = filter_popup
        attrs["table_view"] = table_view
        attrs["data_source"] = data_source
        attrs["detail_box"] = bottom_box
        attrs["detail_scroll"] = detail_scroll
        attrs["close_btn"] = close_btn
        attrs["generate_copy_script_btn"] = copy_script_btn
        attrs["generate_new_script_btn"] = new_script_btn
        attrs["detail_text_view"] = detail_text_view
