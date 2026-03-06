"""Check for STIGs view - compare loaded STIGs with cyber.mil and download updates."""

from AppKit import (
    NSView, NSRect, NSBox, NSSplitView, NSScrollView, NSTableView, NSTableColumn,
    NSButton, NSButtonCell, NSTextField, NSTextView, NSViewWidthSizable,
    NSViewHeightSizable, NSViewMinXMargin, NSViewMinYMargin
)
from Foundation import NSObject
import objc
from typing import List

from ..models.stig_file import StigFile
from .view_helpers import get_view_attrs, get_bounds_size


class CheckForStigsDataSource(NSObject):
    """Data source for the Check for STIGs table. Uses same pattern as StigsTableDataSource."""

    def init(self):
        self = objc.super(CheckForStigsDataSource, self).init()
        if self is None:
            return None
        self.stig_files = []
        return self

    @objc.python_method
    def set_stig_files(self, stig_files: List[StigFile]):
        self.stig_files = list(stig_files) if stig_files else []

    def numberOfRowsInTableView_(self, tableView):
        return len(self.stig_files)

    def tableView_objectValueForTableColumn_row_(self, tableView, column, row):
        if 0 <= row < len(self.stig_files):
            stig = self.stig_files[row]
            col_id = str(column.identifier()) if column.identifier() else ""
            if col_id == "checkbox":
                return stig.is_checked
            elif col_id == "name":
                return stig.display_name
        return None

    def tableView_setObjectValue_forTableColumn_row_(self, tableView, value, column, row):
        if 0 <= row < len(self.stig_files):
            col_id = str(column.identifier()) if column.identifier() else ""
            if col_id == "checkbox":
                self.stig_files[row].is_checked = bool(value)


class CheckForStigsView(NSView):
    """View for checking STIG versions and downloading updates."""

    def init(self):
        self = objc.super(CheckForStigsView, self).init()
        if self is None:
            return None

        attrs = get_view_attrs(self)
        attrs['stig_files'] = []
        attrs['table_view'] = None
        attrs['scroll_view'] = None
        attrs['data_source'] = None
        attrs['check_button'] = None
        attrs['download_button'] = None
        attrs['app_controller'] = None
        attrs['empty_label'] = None
        attrs['log_text_view'] = None
        CheckForStigsView.createUI(self)
        return self

    def createUI(self):
        bounds = self.bounds()
        width, height = get_bounds_size(bounds)
        if width == 0 or height == 0:
            width, height = 900, 600
        frame = NSRect((0, 0), (width, height))
        self.setFrame_(frame)
        self.setFlipped_(True)  # Origin top-left so panes align at top

        # STIGs = 1/3 width, Log = 2/3 width, with adjustable divider
        left_width = int(width / 3)
        right_width = width - left_width

        split_view = NSSplitView.alloc().initWithFrame_(frame)
        split_view.setFlipped_(True)
        split_view.setVertical_(True)
        split_view.setDividerStyle_(1)  # Thin, draggable divider
        split_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)

        # Left pane (1/3): NSBox with STIG list + buttons
        left_box = NSBox.alloc().initWithFrame_(NSRect((0, 0), (left_width, height)))
        left_box.setTitlePosition_(2)  # NSAtTop
        left_box.setTitle_("STIGs")
        left_box.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        left_content = left_box.contentView()
        left_content.setFlipped_(True)  # Origin top-left for easier layout
        lw, lh = get_bounds_size(left_content.bounds())

        # STIG list scroll view: top of left pane, minimal gap (NSBox title ~20px)
        list_height = max(200, lh - 45)
        list_rect = NSRect((0, 5), (lw, list_height))  # y=5 from top
        scroll_view = NSScrollView.alloc().initWithFrame_(list_rect)
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setHasHorizontalScroller_(False)
        scroll_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        scroll_view.setBorderType_(1)

        data_source = CheckForStigsDataSource.alloc().init()
        table_view = NSTableView.alloc().initWithFrame_(list_rect)
        table_view.setDataSource_(data_source)
        table_view.setDelegate_(data_source)
        table_view.setAllowsColumnReordering_(False)
        table_view.setAllowsColumnResizing_(True)
        table_view.setUsesAlternatingRowBackgroundColors_(True)
        table_view.setRowHeight_(28)
        table_view.setHeaderView_(None)

        checkbox_column = NSTableColumn.alloc().initWithIdentifier_("checkbox")
        checkbox_column.setWidth_(30)
        checkbox_column.setMinWidth_(30)
        checkbox_column.setMaxWidth_(30)
        checkbox_column.setEditable_(True)
        checkbox_cell = NSButtonCell.alloc().init()
        checkbox_cell.setButtonType_(3)
        checkbox_cell.setTitle_("")
        checkbox_cell.setAllowsMixedState_(False)
        checkbox_column.setDataCell_(checkbox_cell)
        table_view.addTableColumn_(checkbox_column)

        name_column = NSTableColumn.alloc().initWithIdentifier_("name")
        name_column.setWidth_(max(200, lw - 50))
        name_column.setMinWidth_(200)
        name_column.setResizingMask_(1)
        table_view.addTableColumn_(name_column)

        scroll_view.setDocumentView_(table_view)
        left_content.addSubview_(scroll_view)

        # Empty state placeholder (centered in list area)
        empty_label = NSTextField.alloc().initWithFrame_(NSRect((20, 5 + list_height // 2 - 30), (lw - 40, 60)))
        empty_label.setStringValue_("No STIGs loaded.\nUse File → Import STIG to load STIG files.")
        empty_label.setEditable_(False)
        empty_label.setSelectable_(False)
        empty_label.setBordered_(False)
        empty_label.setDrawsBackground_(False)
        empty_label.setAlignment_(1)
        empty_label.setAutoresizingMask_(NSViewWidthSizable)
        left_content.addSubview_(empty_label)

        # Buttons at bottom of left pane (flipped: y=0 is top, so bottom = lh - 38)
        btn_y = max(10, lh - 38)
        check_btn = NSButton.alloc().initWithFrame_(NSRect((20, btn_y), (70, 28)))
        check_btn.setTitle_("Check")
        check_btn.setButtonType_(1)
        check_btn.setTarget_(self)
        check_btn.setAction_("checkVersions:")
        check_btn.setAutoresizingMask_(NSViewMinXMargin | NSViewMinYMargin)
        left_content.addSubview_(check_btn)

        download_btn = NSButton.alloc().initWithFrame_(NSRect((100, btn_y), (80, 28)))
        download_btn.setTitle_("Download")
        download_btn.setButtonType_(1)
        download_btn.setTarget_(self)
        download_btn.setAction_("downloadChecked:")
        download_btn.setAutoresizingMask_(NSViewMinXMargin | NSViewMinYMargin)
        left_content.addSubview_(download_btn)

        split_view.addSubview_(left_box)

        # Right pane (2/3): NSBox with log pane
        right_box = NSBox.alloc().initWithFrame_(NSRect((0, 0), (right_width, height)))
        right_box.setTitlePosition_(2)
        right_box.setTitle_("Log")
        right_box.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        right_content = right_box.contentView()
        right_content.setFlipped_(True)
        rw, rh = get_bounds_size(right_content.bounds())

        log_scroll = NSScrollView.alloc().initWithFrame_(right_content.bounds())
        log_scroll.setHasVerticalScroller_(True)
        log_scroll.setHasHorizontalScroller_(False)
        log_scroll.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        log_scroll.setBorderType_(1)
        log_text = NSTextView.alloc().initWithFrame_(right_content.bounds())
        log_text.setEditable_(False)
        log_text.setSelectable_(True)
        log_text.setRichText_(False)
        log_text.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        log_scroll.setDocumentView_(log_text)
        right_content.addSubview_(log_scroll)

        split_view.addSubview_(right_box)
        split_view.adjustSubviews()
        split_view.setPosition_ofDividerAtIndex_(left_width, 0)

        self.addSubview_(split_view)

        attrs = get_view_attrs(self)
        attrs['table_view'] = table_view
        attrs['scroll_view'] = scroll_view
        attrs['data_source'] = data_source
        attrs['check_button'] = check_btn
        attrs['download_button'] = download_btn
        attrs['empty_label'] = empty_label
        attrs['log_text_view'] = log_text

    def appendLogMessage_(self, message):
        """Append message to log pane. Called on main thread via performSelectorOnMainThread."""
        log_text = get_view_attrs(self).get('log_text_view')
        if log_text and message:
            msg = str(message)
            text = log_text.string() or ""
            log_text.setString_(text + msg + "\n")
            log_text.scrollToEndOfDocument_(None)

    @objc.python_method
    def _log(self, message: str):
        """Append message to the log pane. Safe to call from any thread."""
        msg = str(message)
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "appendLogMessage:", msg, False
        )

    @objc.python_method
    def set_stig_files(self, stig_files: List[StigFile]):
        """Set STIG files to display. All start checked."""
        attrs = get_view_attrs(self)
        for sf in stig_files:
            sf.is_checked = True
        attrs['stig_files'] = list(stig_files)
        ds = attrs.get('data_source')
        tv = attrs.get('table_view')
        empty_label = attrs.get('empty_label')
        if ds:
            ds.set_stig_files(stig_files)
        if tv:
            tv.reloadData()
        if empty_label:
            empty_label.setHidden_(len(stig_files) > 0)

    @objc.python_method
    def set_app_controller(self, app_controller):
        attrs = get_view_attrs(self)
        attrs['app_controller'] = app_controller

    def checkVersions_(self, sender):
        """Check versions against cyber.mil - uncheck if current."""
        attrs = get_view_attrs(self)
        app_controller = attrs.get('app_controller')
        stig_files = attrs.get('stig_files', [])
        if not app_controller or not stig_files:
            return
        from PyObjCTools import AppHelper
        from ..utils.stig_repository import fetch_repository, find_repo_benchmark

        # Immediate test text (runs on main thread)
        self.appendLogMessage_("Check button clicked.")
        self.appendLogMessage_("=== Check for updates ===")

        def do_check():
            try:
                self._log("Fetching content repository...")
                repo = fetch_repository()
                self._log(f"Found {len(repo)} benchmarks in repository.")
                checked_count = sum(1 for sf in stig_files if sf.is_checked)
                self._log(f"Checking {checked_count} selected STIG(s)...")
                changed = False
                for sf in stig_files:
                    if not sf.is_checked:
                        continue
                    result = find_repo_benchmark(
                        repo, sf.stig_name, sf.stig_version, sf.stig_release
                    )
                    if result is None:
                        self._log(f"  {sf.display_name}: not found in repository")
                        continue
                    rb, is_newer = result
                    if is_newer:
                        self._log(f"  {sf.display_name}: newer version available ({rb.version}) - left checked")
                    else:
                        self._log(f"  {sf.display_name}: current (v{rb.version}) - unchecked")
                        sf.is_checked = False
                        changed = True
                self._log("Check complete.")
                if changed:
                    AppHelper.callAfter(0, lambda: self._reload_table())
            except Exception as e:
                self._log(f"Error: {e}")
                AppHelper.callAfter(0, lambda: self._show_error(str(e)))

        import threading
        threading.Thread(target=do_check, daemon=True).start()

    def _reload_table(self):
        attrs = get_view_attrs(self)
        tv = attrs.get('table_view')
        if tv:
            tv.reloadData()

    def _show_error(self, message: str):
        from AppKit import NSAlert
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Error")
        alert.setInformativeText_(message)
        alert.setAlertStyle_(2)
        alert.runModal()

    def downloadChecked_(self, sender):
        """Download all checked STIGs to Downloads folder."""
        attrs = get_view_attrs(self)
        app_controller = attrs.get('app_controller')
        stig_files = attrs.get('stig_files', [])
        if not app_controller or not stig_files:
            return
        checked = [sf for sf in stig_files if sf.is_checked]
        if not checked:
            from AppKit import NSAlert
            alert = NSAlert.alloc().init()
            alert.setMessageText_("No STIGs Selected")
            alert.setInformativeText_("Please select at least one STIG to download.")
            alert.setAlertStyle_(1)
            alert.runModal()
            return

        from PyObjCTools import AppHelper
        from ..utils.stig_repository import fetch_repository, find_repo_benchmark
        from pathlib import Path
        from urllib.request import urlopen, Request

        downloads_dir = Path.home() / "Downloads"

        def do_download():
            try:
                self._log("=== Download ===")
                self._log(f"Fetching content repository...")
                repo = fetch_repository()
                self._log(f"Downloading {len(checked)} STIG(s) to {downloads_dir}...")
                downloaded = []
                errors = []
                for sf in checked:
                    result = find_repo_benchmark(
                        repo, sf.stig_name, sf.stig_version, sf.stig_release
                    )
                    if result is None:
                        err = f"{sf.display_name}: not found in repository"
                        errors.append(err)
                        self._log(f"  {err}")
                        continue
                    rb, _ = result
                    out_path = downloads_dir / rb.content_id
                    try:
                        self._log(f"  Downloading {rb.content_id}...")
                        req = Request(rb.download_url, headers={"User-Agent": "STIG-Viewer/1.0"})
                        with urlopen(req, timeout=120) as resp:
                            data = resp.read()
                        out_path.write_bytes(data)
                        downloaded.append(str(out_path))
                        self._log(f"    Saved to {out_path}")
                    except Exception as e:
                        err = f"{sf.display_name}: {e}"
                        errors.append(err)
                        self._log(f"    Error: {e}")

                self._log(f"Download complete. {len(downloaded)} file(s) saved.")
                if errors:
                    self._log(f"Errors: {len(errors)}")

                def show_result():
                    if downloaded:
                        msg = f"Downloaded {len(downloaded)} file(s) to Downloads:\n" + "\n".join(downloaded[:5])
                        if len(downloaded) > 5:
                            msg += f"\n... and {len(downloaded) - 5} more"
                        if errors:
                            msg += "\n\nErrors:\n" + "\n".join(errors[:3])
                            if len(errors) > 3:
                                msg += f"\n... and {len(errors) - 3} more"
                    else:
                        msg = "No files downloaded.\n" + "\n".join(errors[:5])
                    from AppKit import NSAlert
                    alert = NSAlert.alloc().init()
                    alert.setMessageText_("Download Complete" if downloaded else "Download Failed")
                    alert.setInformativeText_(msg)
                    alert.setAlertStyle_(1 if downloaded else 2)
                    alert.runModal()

                AppHelper.callAfter(0, show_result)
            except Exception as e:
                AppHelper.callAfter(0, lambda: self._show_error(str(e)))

        import threading
        threading.Thread(target=do_download, daemon=True).start()
