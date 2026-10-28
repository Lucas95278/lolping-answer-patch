import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_asar import archive_fixture
from lolping_patch.installer import Installer, InstallError, exclusive_lock, write_json
from lolping_patch.platforms import Target, FUSE_MAGIC, check_fuse


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = self.root / 'lolPing'
        (self.app / 'resources').mkdir(parents=True)
        self.asar = self.app / 'resources/app.asar'
        self.original = archive_fixture()
        self.asar.write_bytes(self.original)
        self.exe = self.app / 'lolPing.exe'
        self.exe.write_bytes(b'MZ' + FUSE_MAGIC + bytes([1, 9]) + b'101100011')
        self.settings = self.root / 'settings.json'
        self.settings.write_text(json.dumps({'teammate': {'profiles': [{'id': 'keep'}]}, 'other': 42}))
        self.target = Target(self.app, 'windows', self.asar, self.exe, self.exe)
        self.installer = Installer(self.target, self.settings, self.root / 'backups')
        self.addCleanup(patch.stopall)
        patch('lolping_patch.installer.ensure_stopped').start()
        patch('lolping_patch.installer.patch_main', side_effect=lambda s: s + '\n// lolping-answer-patch:1.0.0\n').start()

    def test_apply_status_restore_preserves_exe_and_later_settings(self):
        exe = self.exe.read_bytes()
        self.installer.apply()
        self.assertEqual(self.installer.status()['state'], 'installed')
        self.assertEqual(self.exe.read_bytes(), exe)
        settings = json.loads(self.settings.read_text())
        settings['teammate']['intents']['danger']['label'] = 'My MCQ'
        settings['other'] = 43
        self.settings.write_text(json.dumps(settings))
        self.installer.restore()
        self.assertEqual(self.asar.read_bytes(), self.original)
        self.assertEqual(self.exe.read_bytes(), exe)
        settings = json.loads(self.settings.read_text())
        self.assertEqual(settings['other'], 43)
        self.assertEqual(settings['teammate']['profiles'], [{'id': 'keep'}])
        self.assertEqual(settings['teammate']['intents']['danger'], {'label': 'My MCQ'})

    def test_second_apply_is_noop_and_backup_stays_original(self):
        self.installer.apply()
        first = self.asar.read_bytes()
        self.installer.apply()
        self.assertEqual(self.asar.read_bytes(), first)
        self.installer.restore()
        self.assertEqual(self.asar.read_bytes(), self.original)

    def test_restore_keeps_preexisting_empty_settings_objects(self):
        original = {'teammate': {'intents': {}}, 'other': 42}
        self.settings.write_text(json.dumps(original))
        self.installer.apply()
        self.installer.restore()
        self.assertEqual(json.loads(self.settings.read_text()), original)

    def test_refuses_app_update_and_corrupt_backup(self):
        self.installer.apply()
        self.asar.write_bytes(b'new app update')
        with self.assertRaises(InstallError):
            self.installer.restore()
        self.assertEqual(self.asar.read_bytes(), b'new app update')

    def test_signing_failure_rolls_back_all_bytes_and_settings(self):
        self.target.platform = 'macos'
        self.target.extra_files = [self.exe]
        before = self.settings.read_bytes()
        original_exe = self.exe.read_bytes()
        def fail(target):
            self.exe.write_bytes(b'partially signed executable')
            raise InstallError('signing failed')
        with patch('lolping_patch.installer.sign_macos', side_effect=fail):
            with self.assertRaises(InstallError):
                self.installer.apply()
        self.assertEqual(self.asar.read_bytes(), self.original)
        self.assertEqual(self.exe.read_bytes(), original_exe)
        self.assertEqual(json.loads(self.settings.read_text()), json.loads(before))

    def test_invalid_settings_are_never_replaced(self):
        self.settings.write_text('{invalid')
        with self.assertRaises(InstallError):
            self.installer.apply()
        self.assertEqual(self.asar.read_bytes(), self.original)
        self.assertEqual(self.settings.read_text(), '{invalid')

    def test_unrelated_signature_change_prevents_restore(self):
        self.target.platform = 'macos'
        self.target.extra_files = [self.exe]
        with patch('lolping_patch.installer.sign_macos'):
            self.installer.apply()
        self.exe.write_bytes(b'updated executable')
        with self.assertRaises(InstallError):
            self.installer.restore()

    def test_corrupt_backup_prevents_any_restore_write(self):
        self.installer.apply()
        before = self.asar.read_bytes()
        next((self.installer.folder / 'originals').iterdir()).write_bytes(b'corrupted')
        with self.assertRaises(InstallError):
            self.installer.restore()
        self.assertEqual(self.asar.read_bytes(), before)

    def test_unknown_version_is_rejected(self):
        self.asar.write_bytes(archive_fixture({'package.json': b'{"name":"lolping","version":"0.7.0"}', 'out/main/index.js': b'original main'}))
        with self.assertRaises(InstallError):
            self.installer.apply()

    def test_enabled_or_unknown_fuse_is_refused(self):
        for wire in (b'101110011', b'1011?0011'):
            self.exe.write_bytes(FUSE_MAGIC + bytes([1, 9]) + wire)
            with self.assertRaises(InstallError):
                self.installer.apply()
        self.assertEqual(self.asar.read_bytes(), self.original)

    def test_interrupted_install_requires_explicit_recovery(self):
        self.installer.apply()
        journal = json.loads(self.installer.journal.read_text())
        journal['state'] = 'installing'
        self.installer.journal.write_text(json.dumps(journal))
        with self.assertRaises(InstallError):
            self.installer.apply()
        with self.assertRaises(InstallError):
            self.installer.restore()
        self.installer.restore(recover=True)
        self.assertEqual(self.asar.read_bytes(), self.original)

    def test_fuse_missing_or_malformed_is_refused(self):
        for raw in (b'MZ', FUSE_MAGIC + b'\x02\x09' + b'101100011', FUSE_MAGIC + b'\x01\x09'):
            self.exe.write_bytes(raw)
            with self.assertRaises(ValueError):
                check_fuse(self.exe)

    def test_another_installer_cannot_mutate_a_locked_target(self):
        with exclusive_lock(self.installer.lock_folder):
            with self.assertRaises(InstallError):
                self.installer.apply()
        self.assertEqual(self.asar.read_bytes(), self.original)

    def test_custom_backup_root_does_not_bypass_installation_lock(self):
        other = Installer(self.target, self.settings, self.root / 'different-backups')
        with exclusive_lock(self.installer.lock_folder):
            with self.assertRaises(InstallError):
                other.apply()
        self.assertEqual(self.asar.read_bytes(), self.original)

    def test_external_update_during_preparation_is_not_backed_up_or_overwritten(self):
        from lolping_patch.settings import apply_settings
        updated = archive_fixture({'package.json': b'{"name":"lolping","version":"0.6.0"}',
                                   'out/main/index.js': b'external update'})
        def change_app(settings):
            self.asar.write_bytes(updated)
            return apply_settings(settings)
        with patch('lolping_patch.installer.apply_settings', side_effect=change_app):
            with self.assertRaises(InstallError):
                self.installer.apply()
        self.assertEqual(self.asar.read_bytes(), updated)

    def test_external_update_after_backup_is_not_rolled_back(self):
        calls = []
        updated = b'external app update after backup'
        def check_process(target):
            calls.append(True)
            if len(calls) == 2:
                self.asar.write_bytes(updated)
        with patch('lolping_patch.installer.ensure_stopped', side_effect=check_process):
            with self.assertRaises(InstallError):
                self.installer.apply()
        self.assertEqual(self.asar.read_bytes(), updated)

    def test_asar_backup_uses_the_same_snapshot_as_transformation(self):
        from lolping_patch.installer import digest
        executable = self.exe.read_bytes()
        updated = b'external update between validation and backup'
        changed = []
        def change_before_backup(raw):
            if raw == executable and not changed:
                changed.append(True)
                self.asar.write_bytes(updated)
            return digest(raw)
        with patch('lolping_patch.installer.digest', side_effect=change_before_backup):
            with self.assertRaises(InstallError):
                self.installer.apply()
        self.assertEqual(self.asar.read_bytes(), updated)

    def test_settings_write_failure_rolls_back_app_and_preserves_provider(self):
        failures = []
        def write_once_fail(path, data):
            if Path(path).resolve() == self.settings.resolve() and not failures:
                failures.append(True)
                raise OSError('disk write failed')
            return write_json(path, data)
        before = json.loads(self.settings.read_text())
        with patch('lolping_patch.installer.write_json', side_effect=write_once_fail):
            with self.assertRaises(InstallError):
                self.installer.apply()
        self.assertEqual(self.asar.read_bytes(), self.original)
        self.assertEqual(json.loads(self.settings.read_text()), before)
