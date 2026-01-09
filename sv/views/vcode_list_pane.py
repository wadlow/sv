"""V-code list pane."""

from AppKit import (
    NSView, NSRect, NSScrollView, NSTableView, NSTableColumn, NSTextField, NSButton,
    NSViewWidthSizable, NSViewHeightSizable
)
from Foundation import NSObject
import objc
import os
from typing import List, Optional

from ..models.vuln_code import VulnCode
from .view_helpers import get_view_attrs, get_bounds_size

# Check if verbose CKL debug logging is enabled
_CKL_DEBUG = os.environ.get('SV_CKL_DEBUG') == '1'


class VCodeTableDataSource(NSObject):
    """Data source for the V-code table view."""
    
    def init(self):
        """Initialize the data source."""
        self = objc.super(VCodeTableDataSource, self).init()
        if self is None:
            return None
        self.vuln_codes = []
        self.on_selection_changed = None
        self.vuln_code_to_ckl_vuln = {}  # For status-based coloring in CKL view
        return self
    
    @objc.python_method
    def set_vuln_codes(self, vuln_codes, vuln_code_to_ckl_vuln=None):
        """Set the vulnerability codes to display."""
        self.vuln_codes = vuln_codes
        self.vuln_code_to_ckl_vuln = vuln_code_to_ckl_vuln or {}
        print(f"VCodeTableDataSource.set_vuln_codes: Set {len(vuln_codes)} codes")  # Debug
    
    @objc.python_method
    def set_selection_callback(self, callback):
        """Set the callback for selection changes."""
        self.on_selection_changed = callback
        print(f"VCodeTableDataSource.set_selection_callback: Set callback {callback}")  # Debug
    
    # NSTableViewDataSource methods
    def numberOfRowsInTableView_(self, tableView):
        """Return the number of rows."""
        count = len(self.vuln_codes)
        if _CKL_DEBUG:
            print(f"VCodeTableDataSource.numberOfRowsInTableView_: Returning {count} rows")  # Debug
        return count
    
    def tableView_objectValueForTableColumn_row_(self, tableView, column, row):
        """Return the value for a cell."""
        if _CKL_DEBUG:
            print(f"VCodeTableDataSource.tableView_objectValueForTableColumn_row_: row={row}")  # Debug
        if row < len(self.vuln_codes):
            vuln_code = self.vuln_codes[row]
            result = f"{vuln_code.v_code}: {vuln_code.rule_title}"
            if _CKL_DEBUG:
                print(f"VCodeTableDataSource: Returning '{result[:60]}...'")  # Debug
            return result
        return ""
    
    # NSTableViewDelegate methods
    def tableViewSelectionDidChange_(self, notification):
        """Handle selection change."""
        print("VCodeTableDataSource.tableViewSelectionDidChange_: Called")  # Debug
        print(f"VCodeTableDataSource: on_selection_changed callback = {self.on_selection_changed}")  # Debug
        tableView = notification.object()
        selected_row = tableView.selectedRow()
        print(f"VCodeTableDataSource: Selected row {selected_row}")  # Debug
        
        if selected_row >= 0 and selected_row < len(self.vuln_codes):
            vuln_code = self.vuln_codes[selected_row]
            print(f"VCodeTableDataSource: Selected {vuln_code.v_code}")  # Debug
            if self.on_selection_changed:
                print(f"VCodeTableDataSource: Calling selection callback with {vuln_code.v_code}")  # Debug
                self.on_selection_changed(vuln_code)
                print("VCodeTableDataSource: Callback complete")  # Debug
            else:
                print("VCodeTableDataSource: WARNING - No callback set!")  # Debug
        else:
            print("VCodeTableDataSource: No valid selection")  # Debug
            if self.on_selection_changed:
                self.on_selection_changed(None)
    


class VCodeListPane(NSView):
    """Pane showing list of V-codes in a table view."""
    
    def init(self):
        """Initialize the V-code list pane."""
        self = NSView.alloc().init()
        if self is None:
            return None
        
        attrs = get_view_attrs(self)
        attrs['vuln_codes'] = []
        attrs['selected_vuln_code'] = None
        attrs['on_selection_changed'] = None
        attrs['table_view'] = None
        attrs['scroll_view'] = None
        attrs['data_source'] = None
        VCodeListPane.createUI(self)
        return self
    
    def createUI(self):
        """Create the UI with a proper table view."""
        print("VCodeListPane.createUI: Starting...")  # Debug
        bounds = self.bounds()
        width, height = get_bounds_size(bounds)
        
        # If bounds are zero, use default size
        if width == 0 or height == 0:
            width, height = 300, 400
            bounds = NSRect((0, 0), (width, height))
            self.setFrame_(bounds)
            print(f"VCodeListPane.createUI: Set default frame {width}x{height}")  # Debug
        
        # Create data source
        data_source = VCodeTableDataSource.alloc().init()
        
        # Create scroll view
        scroll_view = NSScrollView.alloc().initWithFrame_(bounds)
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setHasHorizontalScroller_(False)
        scroll_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        scroll_view.setBorderType_(1)  # NSBezelBorder
        
        # Create table view
        table_view = NSTableView.alloc().initWithFrame_(bounds)
        table_view.setDataSource_(data_source)
        table_view.setDelegate_(data_source)
        table_view.setAllowsColumnReordering_(False)
        table_view.setAllowsColumnResizing_(True)
        table_view.setUsesAlternatingRowBackgroundColors_(False)  # Disable to allow custom colors
        table_view.setRowHeight_(20)  # Reduced from 28 for tighter spacing
        table_view.setHeaderView_(None)  # Hide column headers
        
        # Single column for V-code and title
        from AppKit import NSTextFieldCell
        column = NSTableColumn.alloc().initWithIdentifier_("vcode")
        column.setWidth_(width - 20)
        column.setMinWidth_(200)
        column.setResizingMask_(1)  # NSTableColumnAutoresizingMask
        
        # Create and configure a data cell for the column
        cell = NSTextFieldCell.alloc().init()
        cell.setEditable_(False)
        cell.setLineBreakMode_(0)  # NSLineBreakByWordWrapping
        column.setDataCell_(cell)
        
        table_view.addTableColumn_(column)
        print(f"VCodeListPane.createUI: Created column with cell {cell}")  # Debug
        
        scroll_view.setDocumentView_(table_view)
        self.addSubview_(scroll_view)
        
        attrs = get_view_attrs(self)
        attrs['table_view'] = table_view
        attrs['scroll_view'] = scroll_view
        attrs['data_source'] = data_source
        
        print(f"VCodeListPane.createUI: Complete - created table view with data source")  # Debug
    
    def set_vuln_codes(self, vuln_codes: List[VulnCode], vuln_code_to_ckl_vuln=None):
        """Set the V-codes to display."""
        print(f"VCodeListPane.set_vuln_codes: Called with {len(vuln_codes)} codes")  # Debug
        attrs = get_view_attrs(self)
        attrs['vuln_codes'] = vuln_codes
        
        data_source = attrs.get('data_source')
        table_view = attrs.get('table_view')
        
        if data_source:
            print("VCodeListPane.set_vuln_codes: Setting codes on data source...")  # Debug
            data_source.set_vuln_codes(vuln_codes, vuln_code_to_ckl_vuln)
            
            # Set the selection callback on the data source
            on_selection_changed = attrs.get('on_selection_changed')
            print(f"VCodeListPane.set_vuln_codes: on_selection_changed = {on_selection_changed}")  # Debug
            if on_selection_changed:
                print(f"VCodeListPane.set_vuln_codes: Setting callback on data_source")  # Debug
                data_source.set_selection_callback(on_selection_changed)
            else:
                print("VCodeListPane.set_vuln_codes: WARNING - No on_selection_changed in attrs!")  # Debug
        
        if table_view:
            print("VCodeListPane.set_vuln_codes: Reloading table view...")  # Debug
            table_view.reloadData()
            print("VCodeListPane.set_vuln_codes: Table reloaded")  # Debug
        else:
            print("VCodeListPane.set_vuln_codes: WARNING - No table view!")  # Debug
        
        # Update count callback if set
        on_count_changed = attrs.get('on_count_changed')
        if on_count_changed:
            print(f"VCodeListPane.set_vuln_codes: Calling count changed callback with {len(vuln_codes)}")  # Debug
            on_count_changed(len(vuln_codes))
        else:
            print("VCodeListPane.set_vuln_codes: No count changed callback set")  # Debug
    
    def get_selected_vcode(self) -> Optional[VulnCode]:
        """Get the currently selected V-code."""
        attrs = get_view_attrs(self)
        return attrs.get('selected_vuln_code')
