"""Main application controller."""

from AppKit import NSApplication, NSObject, NSAlert
from pathlib import Path
from typing import List, Optional
import json
import pickle

from ..models.stig_file import StigFile
from ..models.ckl_file import CklFile
from ..models.vuln_code import VulnCode
from ..parsers.stig_parser import StigParser, StigParserError
from ..parsers.ckl_parser import CklParser, CklParserError
from ..parsers.ckl_writer import CklWriter
from ..dialogs.file_dialog import FileDialog
from ..dialogs.exit_dialog import ExitDialog
from ..dialogs.preferences_dialog import PreferencesDialog
from ..dialogs.progress_dialog import ProgressDialog
from ..controllers.menu_controller import MenuController
from ..views.main_window import MainWindow
from ..views.ckl_view import CklView
from ..views.explorer_view import ExplorerView
from ..views.view_helpers import get_view_attrs
import os


class AppController:
    """Main application controller."""
    
    # Path to store persistent STIG file paths
    PERSIST_FILE = Path.home() / '.sv_stig_files.json'
    
    def __init__(self):
        """Initialize the app controller."""
        self.stig_files = []
        self.ckl_files = []
        self.main_window = None
        self.menu_controller = None
        self.preferences_dialog = None
    
    def setup_application(self):
        """Set up the application."""
        # Create menu controller
        self.menu_controller = MenuController.alloc().init()
        # Use direct attribute access since it's a Python method, not Objective-C
        MenuController.set_app_controller(self.menu_controller, self)
        
        # Create main window
        self.main_window = MainWindow()
        self.main_window.show()
        
        # Create preferences dialog (but don't show it yet)
        self.preferences_dialog = PreferencesDialog()
        
        # Set up explorer view callbacks BEFORE loading persistent STIGs
        # This ensures callbacks are in place when V-codes are populated
        explorer_view = self.main_window.get_explorer_view()
        if explorer_view:
            # Wire up selection callbacks
            explorer_attrs = get_view_attrs(explorer_view)
            
            # Wire up V-code selection callback
            vcode_list_pane = explorer_attrs.get('vcode_list_pane')
            if vcode_list_pane:
                vcode_list_attrs = get_view_attrs(vcode_list_pane)
                vcode_list_attrs['on_selection_changed'] = self._on_vcode_selected
                print(f"AppController: Wired up V-code selection callback BEFORE loading STIGs")  # Debug
            
            # Wire up STIG selection callback on ExplorerView (not directly on stigs_pane)
            # The ExplorerView will handle wiring it to the stigs_pane internally
            explorer_attrs['on_stig_selection_changed'] = self._update_vcode_list
            print(f"AppController: Wired up STIG selection callback: {self._update_vcode_list}")  # Debug
            
            # Wire up delete STIG callback
            explorer_attrs['on_delete_stig'] = self._on_delete_stig
        
        # Load persistent STIG files AFTER setting up callbacks
        self._load_persistent_stigs()
        
        # In debug mode, populate with fake data
        if os.environ.get('SV_DEBUG_MODE') == '1':
            self._populate_fake_data()
    
    def compare_stigs(self):
        """Open the Compare STIGs tab."""
        print("AppController.compare_stigs: Called")  # Debug
        try:
            # Create a new Compare tab
            print("AppController.compare_stigs: Importing CompareView...")  # Debug
            from ..views.compare_view import CompareView
            print("AppController.compare_stigs: Creating CompareView instance...")  # Debug
            compare_view = CompareView.alloc().init()
            print(f"AppController.compare_stigs: Created view: {compare_view}")  # Debug
            print("AppController.compare_stigs: Adding tab...")  # Debug
            self.main_window.add_compare_tab(compare_view)
            print("AppController.compare_stigs: Tab added successfully")  # Debug
        except Exception as e:
            import traceback
            print(f"AppController.compare_stigs: ERROR - {e}")  # Debug
            traceback.print_exc()
            self._show_error(f"Error opening Compare tab: {e}")
    
    def import_stig_files(self):
        """Import STIG files."""
        print("import_stig_files called")  # Debug output
        file_paths = FileDialog.open_stig_files()
        print(f"Got {len(file_paths)} file path(s) from dialog")  # Debug output
        
        if not file_paths:
            print("No files selected, returning")  # Debug output
            return
        
        # Show progress dialog for large files
        progress = None
        try:
            if len(file_paths) > 0:
                try:
                    total_size = sum(f.stat().st_size for f in file_paths if f.exists())
                    # Show progress if total size > 1MB or multiple files
                    if total_size > 1024 * 1024 or len(file_paths) > 1:
                        progress = ProgressDialog(
                            title="Importing STIG Files",
                            message=f"Processing {len(file_paths)} file(s)..."
                        )
                        progress.show()
                except Exception as e:
                    print(f"Error calculating file sizes: {e}")
                    # Show progress anyway for multiple files
                    if len(file_paths) > 1:
                        progress = ProgressDialog(
                            title="Importing STIG Files",
                            message=f"Processing {len(file_paths)} file(s)..."
                        )
                        progress.show()
            
            imported_count = 0
            for i, file_path in enumerate(file_paths):
                print(f"Processing file {i+1}/{len(file_paths)}: {file_path}")  # Debug output
                if progress:
                    progress.set_message(f"Processing {file_path.name} ({i+1}/{len(file_paths)})...")
                    # Process events to update UI
                    from AppKit import NSApplication
                    app = NSApplication.sharedApplication()
                    app.updateWindows()
                
                try:
                    # Parse with progress callback
                    def update_progress(current, total):
                        print(f"Progress callback: {current} of {total}")  # Debug
                        if progress:
                            msg = f"Processing {file_path.name}\nImported {current} of {total} vulnerability records"
                            print(f"Setting progress message: {repr(msg)}")  # Debug - use repr to see \n
                            progress.set_message(msg)
                    
                    print(f"Starting parse with progress callback for {file_path.name}")  # Debug
                    stig_file = StigParser.parse(file_path, progress_callback=update_progress)
                    print(f"Parse complete, got {len(stig_file.vuln_codes)} V-codes")  # Debug
                    self.stig_files.append(stig_file)
                    imported_count += 1
                    print(f"Successfully imported {file_path.name} with {len(stig_file.vuln_codes)} V-codes")  # Debug output
                except StigParserError as e:
                    print(f"StigParserError: {e}")  # Debug output
                    self._show_error(f"Error parsing STIG file {file_path.name}: {e}")
                except Exception as e:
                    import traceback
                    print(f"Exception parsing {file_path.name}: {e}")  # Debug output
                    traceback.print_exc()
                    self._show_error(f"Unexpected error loading {file_path.name}: {e}")
            
            print(f"Imported {imported_count} file(s), updating view...")  # Debug output
            # Update explorer view on main thread
            from PyObjCTools import AppHelper
            from AppKit import NSApplication
            
            def update_ui():
                print("update_ui: Starting UI update on main thread...")  # Debug
                self._update_explorer_view()
                print("update_ui: UI update complete")  # Debug
                
                # Close progress dialog
                if progress:
                    print("update_ui: Closing progress dialog...")  # Debug
                    progress.close()
                    print("update_ui: Progress dialog closed")  # Debug
            
            # Update UI directly
            if imported_count > 0:
                if progress:
                    progress.set_message(f"Successfully imported {imported_count} file(s)")
                print(f"Calling update_ui directly for {imported_count} file(s)...")  # Debug
                update_ui()  # Call directly instead of scheduling
                # Save persistent STIG paths
                self._save_persistent_stigs()
                print(f"Import complete: {imported_count} file(s) imported")  # Debug output
            else:
                if progress:
                    progress.close()
                self._show_error("No files were successfully imported.")
        except Exception as e:
            import traceback
            print(f"Error in import_stig_files: {e}")  # Debug output
            traceback.print_exc()
            if progress:
                progress.close()
            self._show_error(f"Error importing files: {e}")
        finally:
            if progress:
                # Close progress dialog after a short delay if not already closed
                from PyObjCTools import AppHelper
                AppHelper.callAfter(1.0, lambda: progress.close() if progress else None)
    
    def open_checklist_files(self):
        """Open CKL checklist files."""
        file_paths = FileDialog.open_ckl_files()
        if not file_paths:
            return
        
        for file_path in file_paths:
            try:
                ckl_file = CklParser.parse(file_path)
                self.ckl_files.append(ckl_file)
                
                # Create CKL view and add tab
                ckl_view = CklView.alloc().init()
                CklView.set_ckl_file(ckl_view, ckl_file)
                self.main_window.add_ckl_tab(ckl_file, ckl_view)
            except CklParserError as e:
                self._show_error(f"Error parsing CKL file {file_path.name}: {e}")
            except Exception as e:
                self._show_error(f"Unexpected error loading {file_path.name}: {e}")
    
    def create_checklist(self):
        """Create a new checklist from selected STIGs."""
        # Get checked STIGs from explorer view
        explorer_view = self.main_window.get_explorer_view()
        if not explorer_view:
            return
        
        from ..views.explorer_view import ExplorerView
        checked_stigs = ExplorerView.get_checked_stigs(explorer_view)
        if not checked_stigs:
            self._show_error("Please select at least one STIG file.")
            return
        
        # Show save dialog
        file_path = FileDialog.save_ckl_file()
        if not file_path:
            return
        
        try:
            ckl_file = CklWriter.create_from_stigs(file_path, checked_stigs)
            self.ckl_files.append(ckl_file)
            
            # Create CKL view and add tab
            ckl_view = CklView.alloc().init()
            CklView.set_ckl_file(ckl_view, ckl_file)
            self.main_window.add_ckl_tab(ckl_file, ckl_view)
        except Exception as e:
            self._show_error(f"Error creating checklist: {e}")
    
    def create_ckl_file(self):
        """Create a CKL file from selected STIGs and save it."""
        # Get checked STIGs from explorer view
        explorer_view = self.main_window.get_explorer_view()
        if not explorer_view:
            return
        
        from ..views.explorer_view import ExplorerView
        checked_stigs = ExplorerView.get_checked_stigs(explorer_view)
        if not checked_stigs:
            self._show_error("Please select at least one STIG file from the Explorer tab.")
            return
        
        # Show save dialog
        file_path = FileDialog.save_ckl_file()
        if not file_path:
            return
        
        try:
            # Create and write the CKL file
            ckl_file = CklWriter.create_from_stigs(file_path, checked_stigs)
            
            # Show success message
            alert = NSAlert.alloc().init()
            alert.setMessageText_("CKL File Created")
            alert.setInformativeText_(f"Successfully created CKL file:\n{file_path}")
            alert.setAlertStyle_(1)  # NSAlertStyleInformational
            alert.runModal()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._show_error(f"Error creating CKL file: {e}")
    
    def is_explorer_tab_active(self):
        """Check if the Explorer tab is currently active."""
        if not self.main_window:
            return False
        return self.main_window.is_explorer_tab_active()
    
    def has_stigs_loaded(self):
        """Check if any STIG files have been loaded."""
        return len(self.stig_files) > 0
    
    def delete_stig(self, stig_file):
        """Delete a STIG file from the loaded list."""
        if stig_file in self.stig_files:
            self.stig_files.remove(stig_file)
            self._save_persistent_stigs()
            self._update_explorer_view()
    
    def _load_persistent_stigs(self):
        """Load persistent STIG files from disk."""
        if not self.PERSIST_FILE.exists():
            return
        
        try:
            with open(self.PERSIST_FILE, 'r') as f:
                stig_paths = json.load(f)
            
            print(f"Loading {len(stig_paths)} persistent STIG files...")  # Debug
            for path_str in stig_paths:
                path = Path(path_str)
                if path.exists():
                    try:
                        print(f"Parsing {path}...")  # Debug
                        stig_file = StigParser.parse(path)
                        self.stig_files.append(stig_file)
                        print(f"Successfully loaded {path.name}")  # Debug
                    except Exception as e:
                        print(f"Error loading {path}: {e}")  # Debug
                else:
                    print(f"Skipping non-existent file: {path}")  # Debug
            
            # Update explorer view with loaded files
            if len(self.stig_files) > 0:
                self._update_explorer_view()
        except Exception as e:
            print(f"Error loading persistent STIGs: {e}")  # Debug
    
    def _save_persistent_stigs(self):
        """Save persistent STIG file paths to disk."""
        try:
            # Save only the file paths as strings
            stig_paths = [str(stig.file_path) for stig in self.stig_files]
            with open(self.PERSIST_FILE, 'w') as f:
                json.dump(stig_paths, f)
            print(f"Saved {len(stig_paths)} STIG paths to {self.PERSIST_FILE}")  # Debug
        except Exception as e:
            print(f"Error saving persistent STIGs: {e}")  # Debug
    
    def exit_application(self):
        """Handle exit application request."""
        if ExitDialog.show():
            app = NSApplication.sharedApplication()
            app.terminate_(None)
    
    def show_preferences(self):
        """Show preferences dialog."""
        if self.preferences_dialog:
            self.preferences_dialog.show()
    
    def should_terminate(self):
        """Called when application is about to terminate."""
        # Return True to allow termination
        return True
    
    def will_terminate(self):
        """Called when application is terminating."""
        pass
    
    def _update_explorer_view(self):
        """Update the explorer view with current STIG files."""
        try:
            print("_update_explorer_view: Getting explorer view...")  # Debug
            explorer_view = self.main_window.get_explorer_view()
            print(f"_update_explorer_view: Got explorer_view: {explorer_view}")  # Debug
            if explorer_view:
                print(f"_update_explorer_view: Setting {len(self.stig_files)} STIG files...")  # Debug
                # Call the method using the class, passing instance as first arg
                from ..views.explorer_view import ExplorerView
                ExplorerView.set_stig_files(explorer_view, self.stig_files)
                print("_update_explorer_view: STIG files set, updating V-code list...")  # Debug
                self._update_vcode_list()
                print("_update_explorer_view: Complete")  # Debug
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._show_error(f"Error updating explorer view: {e}")
    
    def _update_vcode_list(self):
        """Update the V-code list based on checked STIGs and search."""
        try:
            print("_update_vcode_list: Starting...")  # Debug
            explorer_view = self.main_window.get_explorer_view()
            if not explorer_view:
                print("_update_vcode_list: No explorer_view, returning")  # Debug
                return
            
            # Get checked STIGs
            print("_update_vcode_list: Getting checked STIGs...")  # Debug
            from ..views.explorer_view import ExplorerView
            checked_stigs = ExplorerView.get_checked_stigs(explorer_view)
            print(f"_update_vcode_list: Got {len(checked_stigs)} checked STIGs")  # Debug
            
            # If no STIGs are checked, clear the V-code list and detail pane
            if len(checked_stigs) == 0:
                print("_update_vcode_list: No STIGs checked, clearing V-codes")  # Debug
                ExplorerView.set_vcode_list(explorer_view, [])
                ExplorerView.set_selected_vcode(explorer_view, None)
                return
            
            # Collect all V-codes from checked STIGs
            all_vuln_codes = []
            for stig_file in checked_stigs:
                all_vuln_codes.extend(stig_file.vuln_codes)
            print(f"_update_vcode_list: Collected {len(all_vuln_codes)} V-codes")  # Debug
            
            # Apply severity filter
            print("_update_vcode_list: Getting enabled severities...")  # Debug
            from ..views.view_helpers import get_view_attrs
            search_pane = ExplorerView.get_search_pane(explorer_view)
            search_pane_attrs = get_view_attrs(search_pane)
            from ..views.search_pane import SearchPane
            enabled_severities = SearchPane.get_enabled_severities(search_pane)
            print(f"_update_vcode_list: {len(enabled_severities)} severities enabled: {enabled_severities}")  # Debug
            
            filtered_vuln_codes = []
            for vc in all_vuln_codes:
                severity = vc.severity.lower() if vc.severity else "low"
                # Map critical to high for filtering
                if severity == "critical":
                    severity = "high"
                if severity in enabled_severities:
                    filtered_vuln_codes.append(vc)
            
            print(f"_update_vcode_list: After severity filter: {len(filtered_vuln_codes)} V-codes")  # Debug
            all_vuln_codes = filtered_vuln_codes
            
            # Apply search filter (currently not implemented, but placeholder)
            filtered_vuln_codes = all_vuln_codes
            
            # Sort V-codes by numeric value (V-214277 -> 214277)
            def vcode_sort_key(vc):
                """Extract numeric part from V-code for sorting."""
                try:
                    # Remove 'V-' prefix and convert to int
                    return int(vc.v_code.replace('V-', '').replace('v-', ''))
                except (ValueError, AttributeError):
                    return 999999999  # Put invalid V-codes at the end
            
            filtered_vuln_codes.sort(key=vcode_sort_key)
            print(f"_update_vcode_list: Sorted {len(filtered_vuln_codes)} V-codes by number")  # Debug
            
            # Update the list
            print(f"_update_vcode_list: Setting {len(filtered_vuln_codes)} V-codes in list...")  # Debug
            ExplorerView.set_vcode_list(explorer_view, filtered_vuln_codes)
            print("_update_vcode_list: Complete")  # Debug
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._show_error(f"Error updating V-code list: {e}")
    
    def _on_vcode_selected(self, vuln_code: Optional[VulnCode]):
        """Handle V-code selection change."""
        print(f"AppController._on_vcode_selected: Called with {vuln_code.v_code if vuln_code else 'None'}")  # Debug
        explorer_view = self.main_window.get_explorer_view()
        if explorer_view:
            from ..views.explorer_view import ExplorerView
            print(f"AppController._on_vcode_selected: Setting selected vcode in explorer view")  # Debug
            ExplorerView.set_selected_vcode(explorer_view, vuln_code)
            print(f"AppController._on_vcode_selected: Complete")  # Debug
        else:
            print("AppController._on_vcode_selected: WARNING - No explorer view!")  # Debug
    
    def _on_delete_stig(self):
        """Handle delete STIG request."""
        print("AppController._on_delete_stig: Called")  # Debug
        explorer_view = self.main_window.get_explorer_view()
        if not explorer_view:
            print("AppController._on_delete_stig: No explorer view")  # Debug
            return
        
        from ..views.explorer_view import ExplorerView
        selected_stigs = ExplorerView.get_selected_stigs(explorer_view)
        
        if not selected_stigs:
            self._show_error("Please select at least one STIG to delete.")
            return
        
        # Confirm deletion
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Delete STIG Files")
        alert.setInformativeText_(f"Are you sure you want to delete {len(selected_stigs)} STIG file(s) from the Explorer?\n\nThis will remove them from the list but not delete the actual files from disk.")
        alert.addButtonWithTitle_("Delete")
        alert.addButtonWithTitle_("Cancel")
        alert.setAlertStyle_(2)  # NSAlertStyleWarning
        
        response = alert.runModal()
        if response == 1000:  # First button (Delete)
            for stig in selected_stigs:
                self.delete_stig(stig)
            print(f"AppController._on_delete_stig: Deleted {len(selected_stigs)} STIG(s)")  # Debug
    
    def _show_error(self, message: str):
        """Show an error alert."""
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Error")
        alert.setInformativeText_(message)
        alert.setAlertStyle_(2)  # NSAlertStyleCritical
        alert.runModal()
    
    def _populate_fake_data(self):
        """Populate the explorer view with fake STIG data in debug mode."""
        try:
            print("DEBUG MODE: Populating with fake STIG data...")  # Debug
            from ..utils.fake_data import generate_fake_stig
            
            fake_stig = generate_fake_stig()
            self.stig_files.append(fake_stig)
            
            print(f"DEBUG MODE: Generated fake STIG with {len(fake_stig.vuln_codes)} V-codes")  # Debug
            print(f"DEBUG MODE: STIG name: {fake_stig.display_name}")  # Debug
            print(f"DEBUG MODE: Total STIG files: {len(self.stig_files)}")  # Debug
            
            # Update the explorer view immediately (we're already on the main thread during setup)
            print("DEBUG MODE: Updating explorer view...")  # Debug
            self._update_explorer_view()
            print("DEBUG MODE: Fake data populated successfully")  # Debug
        except Exception as e:
            import traceback
            print(f"DEBUG MODE: Error populating fake data: {e}")  # Debug
            traceback.print_exc()

