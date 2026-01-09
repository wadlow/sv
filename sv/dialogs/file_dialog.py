"""File dialogs for opening and saving files."""

from pathlib import Path
from typing import List, Optional
from AppKit import NSOpenPanel, NSSavePanel, NSArray


class FileDialog:
    """Wrapper for file dialogs."""
    
    @staticmethod
    def open_stig_files() -> List[Path]:
        """Open dialog for selecting STIG files (ZIP or XML)."""
        try:
            panel = NSOpenPanel.openPanel()
            panel.setCanChooseFiles_(True)
            panel.setCanChooseDirectories_(False)
            panel.setAllowsMultipleSelection_(True)
            panel.setAllowedFileTypes_(['zip', 'xml'])
            panel.setTitle_("Import STIG Files")
            
            # NSFileHandlingPanelOKButton is 1, NSFileHandlingPanelCancelButton is 0
            result = panel.runModal()
            print(f"File dialog result: {result}")  # Debug output
            if result == 1:  # NSFileHandlingPanelOKButton
                urls = panel.URLs()
                file_paths = [Path(str(url.path())) for url in urls if url]
                print(f"Selected {len(file_paths)} file(s)")  # Debug output
                return file_paths
            print("File dialog cancelled")  # Debug output
            return []
        except Exception as e:
            import traceback
            print(f"Error in file dialog: {e}")
            traceback.print_exc()
            return []
    
    @staticmethod
    def open_ckl_files() -> List[Path]:
        """Open dialog for selecting CKL files."""
        try:
            panel = NSOpenPanel.openPanel()
            panel.setCanChooseFiles_(True)
            panel.setCanChooseDirectories_(False)
            panel.setAllowsMultipleSelection_(True)
            panel.setAllowedFileTypes_(['ckl'])
            panel.setTitle_("Open Checklist Files")
            
            if panel.runModal() == 1:  # NSFileHandlingPanelOKButton
                urls = panel.URLs()
                return [Path(str(url.path())) for url in urls if url]
            return []
        except Exception as e:
            print(f"Error in file dialog: {e}")
            return []
    
    @staticmethod
    def save_ckl_file(default_name: str = "checklist.ckl") -> Optional[Path]:
        """Save dialog for creating a new CKL file."""
        try:
            panel = NSSavePanel.savePanel()
            panel.setAllowedFileTypes_(['ckl'])
            panel.setTitle_("Create Checklist File")
            panel.setNameFieldStringValue_(default_name)
            
            if panel.runModal() == 1:  # NSFileHandlingPanelOKButton
                url = panel.URL()
                if url:
                    return Path(str(url.path()))
            return None
        except Exception as e:
            print(f"Error in save dialog: {e}")
            return None

