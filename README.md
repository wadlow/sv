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

## Features

- Import and view STIG files (XCCDF XML format, supports ZIP archives)
- Open and edit CKL checklist files
- Create new CKL files from selected STIGs
- Advanced search functionality
- Status pie charts for checklist files
- Multi-tab interface for multiple checklists

