"""File dialogs for opening and saving files."""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from AppKit import NSOpenPanel, NSSavePanel, NSArray
from Foundation import NSURL


def _default_ckl_directory() -> Optional[Path]:
    """Return the preferred CKL directory for the current year."""
    ckl_dir = Path(f"/Users/wadlow/cust/Medweb/CKL-{datetime.now().year}")
    if ckl_dir.is_dir():
        return ckl_dir
    parent = ckl_dir.parent
    if parent.is_dir():
        return parent
    return None


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
    def _open_checklist_files(file_types: List[str], title: str) -> List[Path]:
        """Open dialog for selecting checklist files of the given type(s)."""
        try:
            panel = NSOpenPanel.openPanel()
            panel.setCanChooseFiles_(True)
            panel.setCanChooseDirectories_(False)
            panel.setAllowsMultipleSelection_(True)
            panel.setAllowedFileTypes_(file_types)
            panel.setTitle_(title)

            ckl_dir = _default_ckl_directory()
            if ckl_dir is not None:
                panel.setDirectoryURL_(
                    NSURL.fileURLWithPath_isDirectory_(str(ckl_dir), True)
                )

            if panel.runModal() == 1:  # NSFileHandlingPanelOKButton
                urls = panel.URLs()
                return [Path(str(url.path())) for url in urls if url]
            return []
        except Exception as e:
            print(f"Error in file dialog: {e}")
            return []

    @staticmethod
    def open_ckl_files() -> List[Path]:
        """Open dialog for selecting CKL (XML) files."""
        return FileDialog._open_checklist_files(['ckl'], "Open CKL Files")

    @staticmethod
    def open_cklb_files() -> List[Path]:
        """Open dialog for selecting CKLB (JSON) files."""
        return FileDialog._open_checklist_files(['cklb'], "Open CKLB Files")
    
    @staticmethod
    def open_verify_ckl_file() -> Optional[Path]:
        """Open dialog for selecting a single CKL file to verify."""
        try:
            panel = NSOpenPanel.openPanel()
            panel.setCanChooseFiles_(True)
            panel.setCanChooseDirectories_(False)
            panel.setAllowsMultipleSelection_(False)
            panel.setAllowedFileTypes_(['ckl', 'cklb'])
            panel.setTitle_("Verify CKL")

            ckl_dir = _default_ckl_directory()
            if ckl_dir is not None:
                panel.setDirectoryURL_(
                    NSURL.fileURLWithPath_isDirectory_(str(ckl_dir), True)
                )

            if panel.runModal() == 1:  # NSFileHandlingPanelOKButton
                urls = panel.URLs()
                if urls:
                    return Path(str(urls[0].path()))
            return None
        except Exception as e:
            print(f"Error in verify CKL file dialog: {e}")
            return None

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

    @staticmethod
    def save_cklb_file(default_name: str = "checklist.cklb") -> Optional[Path]:
        """Save dialog for creating a new CKLB (JSON) file."""
        try:
            panel = NSSavePanel.savePanel()
            panel.setAllowedFileTypes_(['cklb'])
            panel.setTitle_("Create CKLB File")
            panel.setNameFieldStringValue_(default_name)

            ckl_dir = _default_ckl_directory()
            if ckl_dir is not None:
                panel.setDirectoryURL_(
                    NSURL.fileURLWithPath_isDirectory_(str(ckl_dir), True)
                )

            if panel.runModal() == 1:  # NSFileHandlingPanelOKButton
                url = panel.URL()
                if url:
                    return Path(str(url.path()))
            return None
        except Exception as e:
            print(f"Error in save CKLB dialog: {e}")
            return None

