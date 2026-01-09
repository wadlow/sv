"""STIGs pane for displaying STIG files checklist."""

from AppKit import (
    NSView, NSRect, NSScrollView, NSTableView, NSTableColumn, NSButton,
    NSViewWidthSizable, NSViewHeightSizable
)
from Foundation import NSObject
import objc
import os
from typing import List

from ..models.stig_file import StigFile
from .view_helpers import get_view_attrs, get_bounds_size

# Check if verbose CKL debug logging is enabled
_CKL_DEBUG = os.environ.get('SV_CKL_DEBUG') == '1'


class StigsTableDataSource(NSObject):
    """Data source for the STIGs table view."""
    
    def init(self):
        """Initialize the data source."""
        self = objc.super(StigsTableDataSource, self).init()
        if self is None:
            return None
        self.stig_files = []
        self.on_selection_changed = None  # Called when checkbox changes
        self.on_row_selection_changed = None  # Called when row selection changes
        return self
    
    @objc.python_method
    def set_stig_files(self, stig_files):
        """Set the STIG files to display."""
        self.stig_files = stig_files
        print(f"StigsTableDataSource.set_stig_files: Set {len(stig_files)} files")  # Debug
    
    @objc.python_method
    def set_selection_callback(self, callback):
        """Set the callback for checkbox changes."""
        self.on_selection_changed = callback
        print(f"StigsTableDataSource.set_selection_callback: Set callback to {callback}")  # Debug
    
    @objc.python_method
    def set_row_selection_callback(self, callback):
        """Set the callback for row selection changes."""
        self.on_row_selection_changed = callback
        print(f"StigsTableDataSource.set_row_selection_callback: Set callback to {callback}")  # Debug
    
    # NSTableViewDataSource methods
    def numberOfRowsInTableView_(self, tableView):
        """Return the number of rows."""
        count = len(self.stig_files)
        if _CKL_DEBUG:
            print(f"StigsTableDataSource.numberOfRowsInTableView_: Returning {count} rows")  # Debug
        return count
    
    def tableView_objectValueForTableColumn_row_(self, tableView, column, row):
        """Return the value for a cell."""
        if row < len(self.stig_files):
            stig_file = self.stig_files[row]
            if column.identifier() == "checkbox":
                return stig_file.is_checked
            elif column.identifier() == "name":
                return stig_file.display_name
        return None
    
    def tableView_setObjectValue_forTableColumn_row_(self, tableView, value, column, row):
        """Handle changes to cell values (checkbox clicks)."""
        print(f"StigsTableDataSource.tableView_setObjectValue_forTableColumn_row_: row={row}, value={value}")  # Debug
        if row < len(self.stig_files) and column.identifier() == "checkbox":
            self.stig_files[row].is_checked = bool(value)
            print(f"StigsTableDataSource: STIG {self.stig_files[row].display_name} is_checked={self.stig_files[row].is_checked}")  # Debug
            # Notify that checkbox changed
            if self.on_selection_changed:
                print(f"StigsTableDataSource: Calling checkbox callback: {self.on_selection_changed}")  # Debug
                self.on_selection_changed()
            else:
                print("StigsTableDataSource: WARNING - No checkbox callback set!")  # Debug
    
    def tableViewSelectionDidChange_(self, notification):
        """Handle row selection changes."""
        table_view = notification.object()
        selected_row = table_view.selectedRow()
        print(f"StigsTableDataSource.tableViewSelectionDidChange_: selected_row={selected_row}")  # Debug
        # Notify that row selection changed
        if self.on_row_selection_changed:
            print(f"StigsTableDataSource: Calling row selection callback")  # Debug
            self.on_row_selection_changed()
        else:
            print("StigsTableDataSource: WARNING - No row selection callback set!")  # Debug


class StigsPane(NSView):
    """Pane showing checklist of STIG files."""
    
    def init(self):
        """Initialize the STIGS pane."""
        self = NSView.alloc().init()
        if self is None:
            return None
        
        attrs = get_view_attrs(self)
        attrs['stig_files'] = []
        attrs['table_view'] = None
        attrs['scroll_view'] = None
        attrs['data_source'] = None
        attrs['on_selection_changed'] = None
        StigsPane.createUI(self)
        return self
    
    def createUI(self):
        """Create the UI with a table view."""
        print("StigsPane.createUI: Starting...")  # Debug
        bounds = self.bounds()
        width, height = get_bounds_size(bounds)
        
        # If bounds are zero, use default size
        if width == 0 or height == 0:
            width, height = 300, 400
            bounds = NSRect((0, 0), (width, height))
            self.setFrame_(bounds)
            print(f"StigsPane.createUI: Set default frame {width}x{height}")  # Debug
        
        # Create data source
        data_source = StigsTableDataSource.alloc().init()
        
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
        table_view.setUsesAlternatingRowBackgroundColors_(True)
        table_view.setRowHeight_(28)
        table_view.setHeaderView_(None)  # Hide column headers
        
        # Checkbox column (narrow)
        checkbox_column = NSTableColumn.alloc().initWithIdentifier_("checkbox")
        checkbox_column.setWidth_(30)
        checkbox_column.setMinWidth_(30)
        checkbox_column.setMaxWidth_(30)
        checkbox_column.setEditable_(True)
        # Use NSButtonCell for checkbox
        from AppKit import NSButtonCell
        checkbox_cell = NSButtonCell.alloc().init()
        checkbox_cell.setButtonType_(3)  # NSSwitchButton (checkbox)
        checkbox_cell.setTitle_("")
        checkbox_cell.setAllowsMixedState_(False)
        checkbox_column.setDataCell_(checkbox_cell)
        table_view.addTableColumn_(checkbox_column)
        
        # Name column
        name_column = NSTableColumn.alloc().initWithIdentifier_("name")
        name_column.setWidth_(width - 50)
        name_column.setMinWidth_(200)
        name_column.setResizingMask_(1)  # NSTableColumnAutoresizingMask
        table_view.addTableColumn_(name_column)
        
        scroll_view.setDocumentView_(table_view)
        self.addSubview_(scroll_view)
        
        attrs = get_view_attrs(self)
        attrs['table_view'] = table_view
        attrs['scroll_view'] = scroll_view
        attrs['data_source'] = data_source
        
        print(f"StigsPane.createUI: Complete - created table view with checkboxes")  # Debug
    
    def set_stig_files(self, stig_files: List[StigFile]):
        """Set the STIG files to display."""
        print(f"StigsPane.set_stig_files: Called with {len(stig_files)} files")  # Debug
        attrs = get_view_attrs(self)
        attrs['stig_files'] = stig_files
        
        data_source = attrs.get('data_source')
        table_view = attrs.get('table_view')
        
        if data_source:
            print("StigsPane.set_stig_files: Setting files on data source...")  # Debug
            data_source.set_stig_files(stig_files)
            
            # Set the checkbox callback on the data source
            on_selection_changed = attrs.get('on_selection_changed')
            print(f"StigsPane.set_stig_files: on_selection_changed from attrs = {on_selection_changed}")  # Debug
            if on_selection_changed:
                print(f"StigsPane.set_stig_files: Setting checkbox callback on data_source: {on_selection_changed}")  # Debug
                data_source.set_selection_callback(on_selection_changed)
            else:
                print("StigsPane.set_stig_files: WARNING - No on_selection_changed callback in attrs!")  # Debug
            
            # Set the row selection callback on the data source
            on_row_selection_changed = attrs.get('on_row_selection_changed')
            print(f"StigsPane.set_stig_files: on_row_selection_changed from attrs = {on_row_selection_changed}")  # Debug
            if on_row_selection_changed:
                print(f"StigsPane.set_stig_files: Setting row selection callback on data_source: {on_row_selection_changed}")  # Debug
                data_source.set_row_selection_callback(on_row_selection_changed)
            else:
                print("StigsPane.set_stig_files: WARNING - No on_row_selection_changed callback in attrs!")  # Debug
        
        if table_view:
            print("StigsPane.set_stig_files: Reloading table view...")  # Debug
            table_view.reloadData()
            print("StigsPane.set_stig_files: Table reloaded")  # Debug
        else:
            print("StigsPane.set_stig_files: WARNING - No table view!")  # Debug
    
    def get_checked_stigs(self) -> List[StigFile]:
        """Get the list of checked STIG files."""
        attrs = get_view_attrs(self)
        stig_files = attrs.get('stig_files', [])
        print(f"StigsPane.get_checked_stigs: Total {len(stig_files)} STIGs")  # Debug
        for i, sf in enumerate(stig_files):
            print(f"  STIG {i}: {sf.display_name}, is_checked={sf.is_checked}")  # Debug
        checked = [sf for sf in stig_files if sf.is_checked]
        print(f"StigsPane.get_checked_stigs: Returning {len(checked)} checked STIGs")  # Debug
        return checked
    
    def has_selected_row(self) -> bool:
        """Check if any row is selected (highlighted)."""
        attrs = get_view_attrs(self)
        table_view = attrs.get('table_view')
        if table_view:
            selected_row = table_view.selectedRow()
            has_selection = selected_row >= 0
            print(f"StigsPane.has_selected_row: selected_row={selected_row}, has_selection={has_selection}")  # Debug
            return has_selection
        return False
    
    def get_selected_stigs(self) -> List[StigFile]:
        """Get the list of selected (highlighted) STIG files."""
        attrs = get_view_attrs(self)
        table_view = attrs.get('table_view')
        stig_files = attrs.get('stig_files', [])
        
        if table_view:
            selected_row = table_view.selectedRow()
            print(f"StigsPane.get_selected_stigs: selected_row={selected_row}")  # Debug
            if selected_row >= 0 and selected_row < len(stig_files):
                selected = [stig_files[selected_row]]
                print(f"StigsPane.get_selected_stigs: Returning {len(selected)} selected STIGs: {selected[0].display_name}")  # Debug
                return selected
        print(f"StigsPane.get_selected_stigs: Returning 0 selected STIGs")  # Debug
        return []
