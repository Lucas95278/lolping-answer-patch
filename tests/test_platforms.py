import plistlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from lolping_patch.platforms import discover, ensure_stopped


class PlatformTests(unittest.TestCase):
    def test_bilingual_cli_help_works_with_legacy_output_encoding(self):
        result = subprocess.run([sys.executable, '-m', 'lolping_patch', '--help'],
                                capture_output=True, env=dict(os.environ, PYTHONIOENCODING='cp1252'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('最终答案补丁', result.stdout.decode('utf-8'))

    def test_bilingual_cli_errors_works_with_legacy_output_encoding(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run([sys.executable, '-m', 'lolping_patch', 'status', '--app',
                                     str(Path(temporary) / 'missing-lolPing')], capture_output=True,
                                    env=dict(os.environ, PYTHONIOENCODING='cp1252'))
        self.assertEqual(result.returncode, 1)
        self.assertIn('错误', result.stderr.decode('utf-8'))

    def test_official_mac_layout_accepts_inactive_integrity_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = Path(temporary) / 'lolPing.app'
            contents = app / 'Contents'
            files = ['MacOS/lolPing', 'Resources/app.asar', '_CodeSignature/CodeResources',
                     'Frameworks/Electron Framework.framework/Electron Framework']
            for name in files:
                file = contents / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(b'fixture')
            info = {'CFBundleIdentifier': 'com.lolping.app', 'CFBundleExecutable': 'lolPing',
                    'ElectronAsarIntegrity': {'Resources/app.asar': {'hash': 'old-header'}}}
            (contents / 'Info.plist').write_bytes(plistlib.dumps(info))
            with patch('lolping_patch.platforms.host_platform', return_value='macos'):
                target = discover(str(app))
            self.assertEqual(len(target.changed_files), 4)
            self.assertEqual(target.fuse_binary.name, 'Electron Framework')

    def test_windows_exe_path_resolves_to_installation(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = Path(temporary)
            (app / 'resources').mkdir()
            (app / 'resources/app.asar').write_bytes(b'fixture')
            (app / 'lolPing.exe').write_bytes(b'fixture')
            with patch('lolping_patch.platforms.host_platform', return_value='windows'):
                self.assertEqual(discover(str(app / 'lolPing.exe')).root, app.resolve())

    def test_windows_process_detection_uses_csv_image_name(self):
        for output, running in [(b'"lolPing.exe","123","Console","1","1,234 K"\r\n', True),
                                (b'INFO: No tasks are running which match the specified criteria.\r\n', False)]:
            with patch('lolping_patch.platforms.subprocess.run', return_value=SimpleNamespace(stdout=output)):
                if running:
                    with self.assertRaises(ValueError):
                        ensure_stopped(SimpleNamespace(platform='windows'))
                else:
                    ensure_stopped(SimpleNamespace(platform='windows'))

    def test_mac_process_detection_refuses_running_application(self):
        target = SimpleNamespace(platform='macos', executable=Path('/Applications/lolPing.app/Contents/MacOS/lolPing'))
        with patch('lolping_patch.platforms.subprocess.run', return_value=SimpleNamespace(stdout=str(target.executable))):
            with self.assertRaises(ValueError):
                ensure_stopped(target)
