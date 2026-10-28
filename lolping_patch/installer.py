"""Backed-up, journaled patch installation with atomic file replacement."""

import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from .asar import AsarArchive
from .platforms import check_fuse, ensure_stopped, sign_macos
from .settings import load_settings, apply_settings, restore_settings
from .transform import MARKER, PATCH_VERSION, patch_main


class InstallError(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data, mode=None):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is None and path.exists():
            mode = path.stat().st_mode & 0o777
        os.chmod(temporary, mode if mode is not None else 0o600)
        os.replace(temporary, path)
        if os.name != 'nt':
            directory = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path, data):
    atomic_write(path, (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


@contextmanager
def exclusive_lock(folder):
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'lock').open('a+b') as handle:
        handle.seek(0)
        handle.write(b'0')
        handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise InstallError('Another patch process is using this installation.') from exc
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class Installer:
    def __init__(self, target, settings, backup_root):
        self.target, self.settings = target, Path(settings).resolve()
        identity = digest(os.path.normcase(str(target.root.resolve())).encode('utf-8'))[:20]
        self.folder = Path(backup_root).expanduser().resolve() / identity
        # A custom backup directory must not create a separate installer lock.
        self.lock_folder = Path(tempfile.gettempdir()) / 'lolping-answer-patch-locks' / identity
        self.journal = self.folder / 'transaction.json'

    def _load(self):
        if not self.journal.exists():
            return None
        data = json.loads(self.journal.read_text(encoding='utf-8'))
        if (data.get('app') != str(self.target.root.resolve())
                or data.get('settings') != str(self.settings) or data.get('patch') != PATCH_VERSION):
            raise InstallError('Backup belongs to another app, settings location or patch version.')
        return data

    def _save(self, data, state):
        data['state'] = state
        write_json(self.journal, data)

    def status(self):
        data = self._load()
        if data is None:
            archive = AsarArchive(self.target.asar.read_bytes())
            package = json.loads(archive.read('package.json'))
            patched = MARKER.encode() in archive.read('out/main/index.js')
            state = 'patched-without-backup' if patched else 'not-installed'
            return {'state': state, 'app_version': package.get('version'), 'app': str(self.target.root),
                    'backup': str(self.folder)}
        state = data['state']
        if state == 'installed' and any(not Path(item['path']).is_file() or
                digest(Path(item['path']).read_bytes()) != item['installed'] for item in data['files']):
            state = 'changed-after-install'
        return {'state': state, 'app': str(self.target.root), 'backup': str(self.folder)}

    def _backup_bytes(self, data):
        contents = []
        allowed = {str(p) for p in self.target.changed_files}
        if {item['path'] for item in data['files']} != allowed:
            raise InstallError('Backup file list does not match this application.')
        for item in data['files']:
            backup = self.folder / 'originals' / item['backup']
            if backup.parent != self.folder / 'originals' or not backup.is_file():
                raise InstallError('Missing or invalid backup file.')
            raw = backup.read_bytes()
            if digest(raw) != item['original']:
                raise InstallError('Backup hash mismatch; no application files were restored.')
            contents.append((item, raw))
        return contents

    def _rollback(self, data):
        originals = self._backup_bytes(data)
        settings = restore_settings(load_settings(self.settings), data['settings_snapshot'])
        for item, raw in originals:
            atomic_write(item['path'], raw, item['mode'])
        write_json(self.settings, settings)

    def apply(self):
        with exclusive_lock(self.lock_folder):
            try:
                self.folder.mkdir(parents=True, exist_ok=True)
                ensure_stopped(self.target)
                previous = self._load()
                if previous and previous['state'] == 'installed':
                    if self.status()['state'] != 'installed':
                        raise InstallError('Application changed after installation; do not overwrite it.')
                    return self.status()
                if previous and previous['state'] not in ('restored', 'rolled-back', 'aborted'):
                    raise InstallError('Interrupted transaction. Inspect status, then use restore --recover.')
                check_fuse(self.target.fuse_binary)
                raw = self.target.asar.read_bytes()
                archive = AsarArchive(raw)
                archive.verify_integrity()
                package = json.loads(archive.read('package.json'))
                if package.get('name') != 'lolping' or package.get('version') != '0.6.0':
                    raise InstallError('Only the official lolPing 0.6.0 build is supported.')
                patched = archive.replace('out/main/index.js', patch_main(
                    archive.read('out/main/index.js').decode('utf-8')).encode('utf-8'))
                AsarArchive(patched).verify_integrity()
                settings, snapshot = apply_settings(load_settings(self.settings))
                if self.target.asar.read_bytes() != raw:
                    raise InstallError('Application changed during preparation; no files were patched.')
                originals = self.folder / 'originals'
                originals.mkdir(exist_ok=True)
                data = {'app': str(self.target.root.resolve()), 'settings': str(self.settings),
                        'patch': PATCH_VERSION, 'files': [], 'settings_snapshot': snapshot,
                        'fuse_hash': digest(self.target.fuse_binary.read_bytes())}
                for index, file in enumerate(self.target.changed_files):
                    if file.is_symlink():
                        raise InstallError('A file to be modified is a symbolic link; refusing it.')
                    content = raw if file == self.target.asar else file.read_bytes()
                    backup_name = str(index) + '.bin'
                    atomic_write(originals / backup_name, content)
                    data['files'].append({'path': str(file), 'backup': backup_name,
                                          'mode': file.stat().st_mode & 0o777, 'original': digest(content),
                                          'installed': digest(patched) if file == self.target.asar else digest(content)})
                # Persist recovery information before the first application mutation.
                self._save(data, 'installing')
                mutation_started = False
                try:
                    ensure_stopped(self.target)
                    if any(digest(Path(item['path']).read_bytes()) != item['original']
                           for item in data['files']):
                        # No mutation has begun. Do not roll back an external update.
                        self._save(data, 'aborted')
                        raise InstallError('Application changed before installation; no files were patched.')
                    if digest(self.target.fuse_binary.read_bytes()) != data['fuse_hash']:
                        self._save(data, 'aborted')
                        raise InstallError('Electron binary changed before installation; no files were patched.')
                    mutation_started = True
                    atomic_write(self.target.asar, patched)
                    if self.target.platform == 'macos':
                        sign_macos(self.target)
                    write_json(self.settings, settings)
                    for item in data['files']:
                        item['installed'] = digest(Path(item['path']).read_bytes())
                    self._save(data, 'installed')
                except BaseException:
                    if mutation_started:
                        self._rollback(data)
                        self._save(data, 'rolled-back')
                    else:
                        self._save(data, 'aborted')
                    raise
                return self.status()
            except (ValueError, OSError) as exc:
                if isinstance(exc, InstallError):
                    raise
                raise InstallError(str(exc)) from exc

    def restore(self, recover=False):
        with exclusive_lock(self.lock_folder):
            try:
                ensure_stopped(self.target)
                data = self._load()
                if not data:
                    raise InstallError('No backup for this application. Restore is unavailable.')
                if data['state'] in ('restored', 'rolled-back'):
                    return self.status()
                if data['state'] != 'installed' and not recover:
                    raise InstallError('Interrupted transaction. Use restore --recover after inspecting status.')
                self._backup_bytes(data)
                # Even recovery must not overwrite an unrelated application update.
                if digest(self.target.fuse_binary.read_bytes()) != data['fuse_hash']:
                    raise InstallError('The Electron executable/framework changed; refusing restore.')
                for item in data['files']:
                    current = digest(Path(item['path']).read_bytes())
                    allowed = {item['installed']}
                    if recover:
                        allowed.add(item['original'])
                    # A crash inside codesign can leave unrecorded outer signature bytes.
                    partial_signature = (recover and data['state'] == 'installing'
                                         and self.target.platform == 'macos'
                                         and item['path'] != str(self.target.asar))
                    if current not in allowed and not partial_signature:
                        raise InstallError('Application files changed; refusing to overwrite a later update.')
                    if partial_signature:
                        item['installed'] = current
                load_settings(self.settings)  # Validate before changing any app file.
                self._save(data, 'restoring')
                self._rollback(data)
                self._save(data, 'restored')
                return self.status()
            except (ValueError, OSError) as exc:
                if isinstance(exc, InstallError):
                    raise
                raise InstallError(str(exc)) from exc
