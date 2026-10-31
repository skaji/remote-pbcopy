#!/usr/bin/env python3
"""Manual macOS clipboard checks; see clipboard-check.md for instructions."""

import base64
import json
import os
import shlex
import shutil
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve()
REPO = SCRIPT.parent.parent
WORKER = len(sys.argv) > 1 and sys.argv[1] == '--child'
ROOT = Path(sys.argv[4]).parent if WORKER else None
TMUX = os.environ.get('TMUX_BIN', shutil.which('tmux') or '/opt/homebrew/opt/tmux/bin/tmux')
SCREEN = os.environ.get('SCREEN_BIN', '/usr/bin/screen')
SOCKET = ROOT / 'clipboard.sock' if WORKER else None

def clipboard_request(operation, data=b''):
    with socket.socket(socket.AF_UNIX) as client:
        client.connect(str(SOCKET))
        client.sendall(json.dumps({'operation': operation, 'data': base64.b64encode(data).decode()}).encode() + b'\n')
        with client.makefile('rb') as response:
            return base64.b64decode(json.loads(response.readline())['data'])

def clipboard():
    if SOCKET is not None and SOCKET.exists():
        return clipboard_request('read')
    return subprocess.check_output(['/usr/bin/pbpaste'])

def reset_clipboard():
    if SOCKET is not None and SOCKET.exists():
        clipboard_request('write', b'pbcopy-check sentinel')
    else:
        subprocess.run(['/usr/bin/pbcopy'], input=b'pbcopy-check sentinel', check=True)

class ClipboardHandler(socketserver.StreamRequestHandler):
    def handle(self):
        request = json.loads(self.rfile.readline())
        if request['operation'] == 'write':
            subprocess.run(['/usr/bin/pbcopy'], input=base64.b64decode(request['data']), check=True)
            data = b''
        else:
            data = subprocess.check_output(['/usr/bin/pbpaste'])
        self.wfile.write(json.dumps({'data': base64.b64encode(data).decode()}).encode() + b'\n')

def check_cases(label, mode):
    results = []
    commands = [('Perl', ['perl', str(REPO / 'pbcopy')]),
                ('Python', [sys.executable, str(REPO / 'pbcopy.py')]),
                ('Go', [str(ROOT / 'pbcopy-go')])]
    for name, command in commands:
        for size in ('short', 'long'):
            expected = (f'pbcopy-check {label} {mode} {name} ' + ('日本語' * 80 if size == 'long' else '日本語')).encode()
            reset_clipboard()
            output = subprocess.check_output(command, input=expected + b'\n')
            sys.stdout.buffer.write(output)
            sys.stdout.buffer.flush()
            passed = False
            for _ in range(15):
                if clipboard() == expected:
                    passed = True
                    break
                time.sleep(0.1)
            results.append({'implementation': name, 'size': size, 'passed': passed})
    if mode == 'plain':
        for selection in ('', 'c'):
            expected = f'pbcopy-check {label} selector={selection or "empty"}'.encode()
            reset_clipboard()
            sys.stdout.buffer.write(b'\x1b]52;' + selection.encode() + b';' + base64.b64encode(expected) + b'\x1b\\')
            sys.stdout.buffer.flush()
            passed = False
            for _ in range(15):
                if clipboard() == expected:
                    passed = True
                    break
                time.sleep(0.1)
            results.append({'implementation': 'OSC52 selector=' + (selection or 'empty'), 'passed': passed})
    return results

def main():
    global ROOT, SOCKET
    if len(sys.argv) > 1 and sys.argv[1] == '--child':
        _, _, label, mode, output = sys.argv
        results = check_cases(label, mode)
        Path(output).write_text(json.dumps(results))
        return
    if len(sys.argv) != 2 or sys.argv[1] in ('-h', '--help'):
        print('Usage: python3 misc/check-clipboard.py TERMINAL_LABEL')
        print('Run in a plain local macOS terminal, outside tmux, screen, and Herdr.')
        print('Override TMUX_BIN or SCREEN_BIN to select their executables.')
        return
    if sys.platform != 'darwin' or not sys.stdout.isatty():
        raise SystemExit('Run this script in an actual macOS terminal tab.')
    if any(os.environ.get(key) for key in ('TMUX', 'STY', 'HERDR_ENV')):
        raise SystemExit('Start in a plain terminal, outside a multiplexer.')
    for executable in ('perl', 'go', TMUX, SCREEN):
        if not shutil.which(executable):
            raise SystemExit('Executable not found: ' + executable)
    label = sys.argv[1]
    ROOT = Path(tempfile.mkdtemp(prefix='pbcopy-check-', dir='/tmp')).resolve()
    SOCKET = ROOT / 'clipboard.sock'
    subprocess.run(['go', 'build', '-o', str(ROOT / 'pbcopy-go'), './cmd/pbcopy'],
                   cwd=REPO, check=True)
    print('Results directory: ' + str(ROOT), flush=True)
    original = clipboard()
    server = socketserver.UnixStreamServer(str(SOCKET), ClipboardHandler)
    os.chmod(SOCKET, 0o600)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    results = {}
    try:
        results['plain'] = check_cases(label, 'plain')
        for mode in ('tmux-default', 'tmux-passthrough', 'screen'):
            output = ROOT / f'{mode}.json'
            if output.exists():
                output.unlink()
            child = shlex.join([sys.executable, str(SCRIPT), '--child', label, mode, str(output)])
            env = dict(os.environ)
            env.pop('TMUX', None)
            if mode.startswith('tmux'):
                config = ROOT / f'{mode}.conf'
                config.write_text('set -g allow-passthrough on\n' if mode.endswith('passthrough') else '')
                socket_name = 'pbcopy-check-' + str(os.getpid()) + '-' + mode
                command = [TMUX, '-L', socket_name, '-f', str(config), 'new-session', '-s', 'check', child]
            else:
                config = ROOT / 'screen.conf'
                config.write_text('startup_message off\n')
                command = [SCREEN, '-c', str(config), '-S', 'pbcopy-check-' + str(os.getpid()), sys.executable, str(SCRIPT), '--child', label, mode, str(output)]
            try:
                completed = subprocess.run(command, env=env, timeout=40)
                results[mode] = json.loads(output.read_text()) if output.exists() else {'error': 'No results', 'exit_code': completed.returncode}
            except subprocess.TimeoutExpired:
                results[mode] = {'error': 'Timed out'}
            finally:
                # Only clean up the isolated server/session created above.
                if mode.startswith('tmux'):
                    subprocess.run([TMUX, '-L', socket_name, 'kill-server'], capture_output=True)
                else:
                    subprocess.run([SCREEN, '-S', 'pbcopy-check-' + str(os.getpid()), '-X', 'quit'], capture_output=True)
    finally:
        server.shutdown()
        server.server_close()
        SOCKET.unlink()
        subprocess.run(['/usr/bin/pbcopy'], input=original, check=True)
    output = ROOT / 'results.json'
    output.write_text(json.dumps({'terminal': label, 'results': results}, indent=2))
    print('\nClipboard test results:')
    for mode, rows in results.items():
        if isinstance(rows, dict):
            print(mode + ': ' + str(rows))
        else:
            for row in rows:
                print(mode + ' / ' + row['implementation'] + ' / ' + row.get('size', '') + ': ' + ('PASS' if row['passed'] else 'FAIL'))
    print('Saved to ' + str(output))

if __name__ == '__main__':
    main()
