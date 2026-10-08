"""View for verifying CKL file metadata."""

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from AppKit import (
    NSView, NSRect, NSBox, NSScrollView, NSTextView, NSButton,
    NSViewWidthSizable, NSViewHeightSizable, NSColor, NSFont,
    NSBackgroundColorAttributeName, NSFontAttributeName, NSForegroundColorAttributeName,
)
from Foundation import NSAttributedString, NSMutableAttributedString
import objc

from ..models.checklist_status import ChecklistStatus
from ..models.ckl_file import CklFile
from ..utils.check_stigs_runner import (
    evaluate_ckl_stigs,
    parse_check_stigs_output,
    run_check_stigs,
    status_label,
    StigVersionStatus,
)
from .view_helpers import get_view_attrs, get_bounds_size


TAB_LABEL_PREFIX = "Verify CKL"

STATUS_DISPLAY_ORDER = (
    ChecklistStatus.OPEN,
    ChecklistStatus.NOT_A_FINDING,
    ChecklistStatus.NOT_APPLICABLE,
    ChecklistStatus.NOT_REVIEWED,
)


def _format_file_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} bytes"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.2f} MB"


def _format_generated_date(file_path: Path) -> str:
    stat = file_path.stat()
    generated = datetime.fromtimestamp(stat.st_mtime)
    return generated.strftime("%B %d, %Y at %I:%M %p")


def is_ckl_populated(ckl_file: CklFile) -> bool:
    """Return True when the CKL has at least one reviewed result."""
    return any(v.status != ChecklistStatus.NOT_REVIEWED for v in ckl_file.vulns)


def _status_distribution_text(counts: Counter) -> str:
    parts = [
        f"{status.display_name} {counts[status]}"
        for status in STATUS_DISPLAY_ORDER
        if counts.get(status, 0)
    ]
    return ", ".join(parts)


def _stig_vuln_stats(ckl_file: CklFile, stig_id: str) -> tuple[int, Counter]:
    vulns = [v for v in ckl_file.vulns if v.stig_info.stig_id == stig_id]
    return len(vulns), Counter(v.status for v in vulns)


def _append_line(
    storage,
    text: str,
    font,
    text_color,
    background_color=None,
) -> None:
    if not text:
        return
    attrs = {
        NSFontAttributeName: font,
        NSForegroundColorAttributeName: text_color,
    }
    if background_color is not None:
        attrs[NSBackgroundColorAttributeName] = background_color
    storage.appendAttributedString_(
        NSAttributedString.alloc().initWithString_attributes_(text, attrs)
    )


def _stig_entry_colors(status: Optional[StigVersionStatus]):
    normal = NSColor.whiteColor()
    muted = NSColor.colorWithCalibratedWhite_alpha_(0.45, 1.0)
    highlight_text = NSColor.whiteColor()
    highlight_bg = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.45, 0.12, 0.12, 1.0)

    if status is None or status.status == "unknown":
        return normal, None
    if status.status == "current":
        return muted, None
    if status.status == "out_of_date":
        return highlight_text, highlight_bg
    return normal, None


def _build_summary_attributed_text(
    ckl_file: CklFile,
    stig_statuses: Optional[List[StigVersionStatus]] = None,
    *,
    check_message: Optional[str] = None,
    check_error: Optional[str] = None,
):
    file_path = ckl_file.file_path
    stat = file_path.stat()
    font = NSFont.systemFontOfSize_(13)
    normal = NSColor.whiteColor()
    storage = NSMutableAttributedString.alloc().init()

    _append_line(storage, f"File: {ckl_file.file_name}\n", font, normal)
    _append_line(storage, f"Generated: {_format_generated_date(file_path)}\n", font, normal)
    _append_line(storage, f"Size: {_format_file_size(stat.st_size)}\n\n", font, normal)

    if check_message:
        _append_line(storage, f"{check_message}\n\n", font, normal)
    if check_error:
        _append_line(storage, f"STIG version check failed: {check_error}\n\n", font, normal)

    _append_line(storage, f"STIG Files ({len(ckl_file.stigs)}):\n", font, normal)
    populated = is_ckl_populated(ckl_file)

    if ckl_file.stigs:
        for index, stig in enumerate(ckl_file.stigs, start=1):
            status = (
                stig_statuses[index - 1]
                if stig_statuses and index - 1 < len(stig_statuses)
                else None
            )
            text_color, background_color = _stig_entry_colors(status)
            title = stig.title or stig.stig_id
            if status and status.status != "unknown":
                title = f"{title} {status_label(status.status)}"
            elif status:
                title = f"{title} {status_label('unknown')}"

            block_lines = [f"{index}. {title}\n"]
            if stig.filename:
                block_lines.append(f"   STIG file: {stig.filename}\n")
            if status and status.ckl_version:
                block_lines.append(f"   CKL version: {status.ckl_version.label()}\n")
            if status and status.current_version:
                block_lines.append(f"   Current version: {status.current_version.label()}\n")
            if populated:
                vcode_count, status_counts = _stig_vuln_stats(ckl_file, stig.stig_id)
                block_lines.append(f"   V-codes: {vcode_count}\n")
                distribution = _status_distribution_text(status_counts)
                if distribution:
                    block_lines.append(f"   Results: {distribution}\n")
            version_parts = []
            if stig.version:
                version_parts.append(f"Version {stig.version}")
            if stig.release_info:
                version_parts.append(stig.release_info)
            if version_parts:
                block_lines.append(f"   {' | '.join(version_parts)}\n")
            if stig.benchmark_date:
                block_lines.append(f"   Benchmark date: {stig.benchmark_date}\n")
            block_lines.append("\n")

            for line in block_lines:
                _append_line(storage, line, font, text_color, background_color)
    else:
        _append_line(storage, "   (No STIG information found in this CKL file)\n", font, normal)

    return storage


def _set_summary_content(summary_view, ckl_file: CklFile, **kwargs) -> None:
    summary_view.setRichText_(True)
    attributed = _build_summary_attributed_text(ckl_file, **kwargs)
    summary_view.textStorage().setAttributedString_(attributed)


class VerifyCklView(NSView):
    """Tab showing metadata for a CKL file."""

    def init(self):
        self = objc.super(VerifyCklView, self).init()
        if self is None:
            return None

        attrs = get_view_attrs(self)
        attrs["main_window"] = None
        attrs["ckl_file"] = None
        attrs["summary_view"] = None
        attrs["close_btn"] = None
        VerifyCklView.createUI(self)
        return self

    @objc.python_method
    def set_ckl_file(self, ckl_file: CklFile):
        """Display verification details for a CKL file."""
        attrs = get_view_attrs(self)
        attrs["ckl_file"] = ckl_file
        summary_view = attrs.get("summary_view")
        if summary_view:
            _set_summary_content(
                summary_view,
                ckl_file,
                check_message="Checking STIG versions with check-stigs...",
            )
        self._run_version_check()

    @objc.python_method
    def _run_version_check(self):
        import threading
        from PyObjCTools import AppHelper

        attrs = get_view_attrs(self)
        ckl_file = attrs.get("ckl_file")
        if not ckl_file:
            return

        def worker():
            kwargs = {}
            try:
                output = run_check_stigs()
                current_entries = parse_check_stigs_output(output)
                kwargs["stig_statuses"] = evaluate_ckl_stigs(ckl_file, current_entries)
            except Exception as exc:
                kwargs["check_error"] = str(exc)

            def update_view():
                summary_view = get_view_attrs(self).get("summary_view")
                if summary_view:
                    _set_summary_content(summary_view, ckl_file, **kwargs)

            AppHelper.callAfter(update_view)

        threading.Thread(target=worker, daemon=True).start()

    def closeVerifyCklTab_(self, sender):
        attrs = get_view_attrs(self)
        main_window = attrs.get("main_window")
        ckl_file = attrs.get("ckl_file")
        if main_window and ckl_file:
            main_window.remove_verify_ckl_tab(ckl_file.file_path)

    @objc.python_method
    def _layout_content(self):
        attrs = get_view_attrs(self)
        width, height = get_bounds_size(self.bounds())
        margin = 12
        footer_height = 36

        content_box = attrs.get("content_box")
        if content_box:
            content_box.setFrame_(NSRect((margin, footer_height + margin), (
                max(200, width - (2 * margin)),
                max(120, height - footer_height - (2 * margin)),
            )))

        close_btn = attrs.get("close_btn")
        if close_btn:
            close_btn.setFrame_(NSRect((margin, margin), (100, 28)))

    def resizeSubviewsWithOldSize_(self, old_size):
        objc.super(VerifyCklView, self).resizeSubviewsWithOldSize_(old_size)
        self._layout_content()

    @objc.python_method
    def createUI(self):
        bounds = self.bounds()
        width, height = get_bounds_size(bounds)
        if width == 0 or height == 0:
            width, height = 900, 600
        self.setFrame_(NSRect((0, 0), (width, height)))

        margin = 12
        footer_height = 36
        attrs = get_view_attrs(self)

        content_box = NSBox.alloc().initWithFrame_(NSRect(
            (margin, footer_height + margin),
            (max(200, width - (2 * margin)), max(120, height - footer_height - (2 * margin))),
        ))
        content_box.setTitlePosition_(2)
        content_box.setTitle_("CKL Verification")
        content_box.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        content_view = content_box.contentView()
        content_width, content_height = get_bounds_size(content_view.bounds())
        inner_margin = 10

        scroll_view = NSScrollView.alloc().initWithFrame_(NSRect(
            (inner_margin, inner_margin),
            (max(100, content_width - (2 * inner_margin)), max(80, content_height - (2 * inner_margin))),
        ))
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setHasHorizontalScroller_(False)
        scroll_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        scroll_view.setBorderType_(1)

        summary_view = NSTextView.alloc().initWithFrame_(scroll_view.bounds())
        summary_view.setEditable_(False)
        summary_view.setSelectable_(True)
        summary_view.setRichText_(True)
        summary_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        summary_view.setString_("Select a CKL file to verify.")
        summary_view.setTextColor_(NSColor.whiteColor())
        summary_view.setBackgroundColor_(NSColor.blackColor())
        summary_view.setFont_(NSFont.systemFontOfSize_(13))
        scroll_view.setDocumentView_(summary_view)
        content_view.addSubview_(scroll_view)
        self.addSubview_(content_box)

        close_btn = NSButton.alloc().initWithFrame_(NSRect((margin, margin), (100, 28)))
        close_btn.setTitle_("Close Tab")
        close_btn.setTarget_(self)
        close_btn.setAction_("closeVerifyCklTab:")
        close_btn.setAutoresizingMask_(0x04 | 0x08)
        self.addSubview_(close_btn)

        attrs["content_box"] = content_box
        attrs["summary_view"] = summary_view
        attrs["close_btn"] = close_btn
