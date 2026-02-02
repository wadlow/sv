# SV - STIG Viewer

A macOS application for viewing and managing STIG (Security Technical Implementation Guide) files and CKL (Checklist) files.

## Requirements

- macOS 10.13 or later
- Python 3.8 or later
- PyObjC

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Run from the project root directory:

```bash
python3 -m sv.main
```

Or use the launcher script:

```bash
./run.sh
```

### Command Line Options

- `--d`: Enable debug mode (shows debugging messages on the console)
- `--ckl`: Enable CKL-specific debugging (shows detailed checklist debugging messages)

**Note**: When running without `--d`, debug messages are suppressed. Error messages will still be displayed.

Example:

```bash
# Run without debug output (clean)
./run.sh

# Run with full debug output
./run.sh --d

# Run with CKL-specific debug output
./run.sh --ckl
```

## Features

- Import and view STIG files (XCCDF XML format, supports ZIP archives)
- Open and edit CKL checklist files
- Create new CKL files from selected STIGs
- Advanced search functionality
- Status pie charts for checklist files
- Multi-tab interface for multiple checklists

