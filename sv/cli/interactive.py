"""Interactive command-line interface for STIG Viewer."""

import re
import readline
import shlex
import sys
import threading
from typing import Callable, Dict, List, Optional, TypeVar

from PyObjCTools import AppHelper

from .ui_context import capture_ui_state, explain_checklist_vcode, format_state_summary

COMMANDS = [
    'help', 'summary', 'tab', 'stigs', 'compare', 'vcode', 'explain', 'quit', 'exit',
]

VCODE_PATTERN = re.compile(r'\bV-\d+\b', re.I)

HELP_TEXT = """STIG Viewer interactive commands:
  help              Show this help
  summary           Describe what is currently displayed
  tab               Show the active tab
  stigs             List loaded STIGs
  compare           Show comparison details (if on a Compare tab)
  vcode V-#####       Explain a V-code on the Detailed Comparison checklist
  explain V-#####     Same as vcode
  quit, exit        Quit STIG Viewer

Natural-language examples:
  why is V-214247 in the list?
  why does V-214247 not have a code?
  what tab am I on?
  what is selected?

All CLI output goes to stderr so it stays visible while the app runs.
"""

T = TypeVar('T')


def _run_on_main(func: Callable[[], T], timeout: float = 5.0) -> Optional[T]:
    """Run a callable on the AppKit main thread and return its result."""
    result: Dict[str, object] = {}
    done = threading.Event()

    def run():
        try:
            result['value'] = func()
        except Exception as exc:
            result['error'] = exc
        finally:
            done.set()

    AppHelper.callAfter(run)
    if not done.wait(timeout):
        return None
    if 'error' in result:
        raise result['error']
    return result.get('value')


def _get_snapshot(app_controller, timeout: float = 5.0) -> Optional[dict]:
    return _run_on_main(lambda: capture_ui_state(app_controller), timeout)


def _extract_vcode(line: str) -> Optional[str]:
    match = VCODE_PATTERN.search(line)
    return match.group(0).upper() if match else None


def _wants_vcode_explain(lower: str, vcode: Optional[str]) -> bool:
    if not vcode:
        return False
    if lower.startswith('vcode') or lower.startswith('explain'):
        return True
    keywords = (
        'why', 'code', 'explain', 'in the list', 'checklist', 'not have',
        'no code', 'empty code', 'type code',
    )
    return any(keyword in lower for keyword in keywords)


class InteractiveCLI:
    """Readline-based CLI that queries live UI state."""

    def __init__(self, app_controller):
        self.app_controller = app_controller
        self._running = False

    def start(self):
        """Start the CLI loop in a background thread."""
        if self._running:
            return
        self._running = True
        thread = threading.Thread(target=self._run_loop, name='sv-interactive-cli', daemon=True)
        thread.start()

    def _run_loop(self):
        readline.parse_and_bind('tab: complete')
        readline.set_completer(self._completer)
        print('STIG Viewer interactive CLI (type "help" for commands)', file=sys.stderr)
        print('Tip: on a Detailed Comparison tab, try: vcode V-214247', file=sys.stderr)
        while self._running:
            try:
                line = self._readline().strip()
            except EOFError:
                print(file=sys.stderr)
                self._quit_app()
                break
            except KeyboardInterrupt:
                print('\n(Use "quit" to exit STIG Viewer)', file=sys.stderr)
                continue
            if not line:
                continue
            try:
                self._handle_line(line)
            except Exception as exc:
                print(f'Error: {exc}', file=sys.stderr)

    def _readline(self) -> str:
        sys.stderr.write('sv> ')
        sys.stderr.flush()
        line = sys.stdin.readline()
        if not line:
            raise EOFError
        return line.rstrip('\n')

    def _completer(self, text: str, state_idx: int) -> Optional[str]:
        options = [cmd for cmd in COMMANDS if cmd.startswith(text)]
        if state_idx < len(options):
            return options[state_idx]
        return None

    def _handle_line(self, line: str):
        lower = line.lower()
        if lower in ('quit', 'exit'):
            self._quit_app()
            return

        if lower in ('help', '?'):
            print(HELP_TEXT, file=sys.stderr)
            return

        vcode = _extract_vcode(line)
        if _wants_vcode_explain(lower, vcode):
            explanation = _run_on_main(
                lambda: explain_checklist_vcode(self.app_controller, vcode)
            )
            if explanation is None:
                print('Timed out reading UI state.', file=sys.stderr)
                return
            print(explanation, file=sys.stderr)
            return

        snapshot = _get_snapshot(self.app_controller)
        if snapshot is None:
            print('Timed out reading UI state.', file=sys.stderr)
            return

        if lower in ('summary', 'status', 'what', 'what am i looking at'):
            print(format_state_summary(snapshot), file=sys.stderr)
            return

        if lower in ('tab', 'what tab', 'what tab am i on'):
            print(f"Current tab: {snapshot.get('tab', 'Unknown')}", file=sys.stderr)
            if snapshot.get('view'):
                print(snapshot['view'], file=sys.stderr)
            return

        if lower.startswith('stigs') or 'how many stigs' in lower:
            count = snapshot.get('loaded_stig_count', 0)
            print(f"Loaded STIGs: {count}", file=sys.stderr)
            for stig_line in snapshot.get('loaded_stigs', []):
                print(f"  {stig_line}", file=sys.stderr)
            return

        if lower.startswith('compare') or 'comparison' in lower:
            self._print_compare(snapshot)
            return

        if 'what is selected' in lower or lower == 'selected':
            self._print_selection(snapshot)
            return

        if lower.startswith('help '):
            print(HELP_TEXT, file=sys.stderr)
            return

        try:
            parts = shlex.split(line)
        except ValueError as exc:
            print(f'Could not parse input: {exc}', file=sys.stderr)
            return

        if parts:
            cmd = parts[0].lower()
            if cmd in ('vcode', 'explain'):
                target = parts[1] if len(parts) > 1 else None
                if not target:
                    print('Usage: vcode V-#####', file=sys.stderr)
                    return
                target_vcode = _extract_vcode(target) or target.upper()
                explanation = _run_on_main(
                    lambda: explain_checklist_vcode(self.app_controller, target_vcode)
                )
                if explanation is None:
                    print('Timed out reading UI state.', file=sys.stderr)
                    return
                print(explanation, file=sys.stderr)
            elif cmd == 'summary':
                print(format_state_summary(snapshot), file=sys.stderr)
            elif cmd == 'tab':
                print(f"Current tab: {snapshot.get('tab', 'Unknown')}", file=sys.stderr)
            elif cmd == 'stigs':
                for stig_line in snapshot.get('loaded_stigs', []):
                    print(f"  {stig_line}", file=sys.stderr)
            elif cmd == 'compare':
                self._print_compare(snapshot)
            else:
                print(f'Unknown command: {parts[0]}. Type "help" for commands.', file=sys.stderr)

    def _print_compare(self, snapshot: dict):
        if not snapshot.get('comparison_active') and not snapshot.get('comparing'):
            print('No active comparison on the current tab.', file=sys.stderr)
            if snapshot.get('selected_older_stig') or snapshot.get('selected_newer_stig'):
                if snapshot.get('selected_older_stig'):
                    print(f"Selected older STIG: {snapshot['selected_older_stig']}", file=sys.stderr)
                if snapshot.get('selected_newer_stig'):
                    print(f"Selected newer STIG: {snapshot['selected_newer_stig']}", file=sys.stderr)
            return
        if snapshot.get('comparing'):
            print(f"Comparing: {snapshot['comparing']}", file=sys.stderr)
        for key, label in (
            ('in_newer_not_older', 'In newer, not in older'),
            ('in_older_not_newer', 'In older, not in newer'),
            ('different', 'In both (different)'),
            ('checklist_item_count', 'Checklist items'),
            ('filter', 'Checklist filter'),
        ):
            if key in snapshot:
                print(f"  {label}: {snapshot[key]}", file=sys.stderr)

    def _print_selection(self, snapshot: dict):
        found = False
        for key, label in (
            ('selected_stig', 'Selected STIG'),
            ('selected_vcode', 'Selected V-code'),
            ('selected_older_stig', 'Selected older STIG'),
            ('selected_newer_stig', 'Selected newer STIG'),
            ('selected_checklist_item', 'Selected checklist item'),
        ):
            if key in snapshot:
                print(f"{label}: {snapshot[key]}", file=sys.stderr)
                found = True
        if not found:
            print('Nothing selected on the current tab.', file=sys.stderr)

    def _quit_app(self):
        self._running = False
        from AppKit import NSApplication
        AppHelper.callAfter(lambda: NSApplication.sharedApplication().terminate_(None))


def start_interactive_cli(app_controller):
    """Start the interactive CLI for the running application."""
    cli = InteractiveCLI(app_controller)
    cli.start()
    return cli
