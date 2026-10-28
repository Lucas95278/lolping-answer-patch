"""Exercise the real Windows CLI against an unpacked official app; never launch it."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    app = Path(sys.argv[1]).resolve()
    files = [app / 'lolPing.exe', app / 'resources/app.asar']
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    with tempfile.TemporaryDirectory(prefix='lolping-cli-smoke-') as temporary:
        folder = Path(temporary)
        settings = folder / 'settings'
        settings.mkdir()
        original_settings = {'teammate': {'profiles': []}, 'unrelated': 'preserve'}
        (settings / 'settings.json').write_text(json.dumps(original_settings), encoding='utf-8')
        args = ['--app', str(app), '--settings-dir', str(settings), '--backup-dir', str(folder / 'backups')]
        for action in ['apply', 'status', 'restore']:
            subprocess.run([sys.executable, '-m', 'lolping_patch', action, *args], check=True)
            assert hashlib.sha256(files[0].read_bytes()).hexdigest() == before[str(files[0])]
        assert json.loads((settings / 'settings.json').read_text(encoding='utf-8')) == original_settings
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == before[str(p)] for p in files)
    print('Official Windows app restored byte-for-byte; EXE unchanged throughout.')


if __name__ == '__main__':
    main()
