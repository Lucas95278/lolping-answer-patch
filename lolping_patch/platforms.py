"""Installation discovery, process checks and local macOS signing."""

import csv
import hashlib
import io
import os
import plistlib
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

FUSE_MAGIC = b'dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX'


@dataclass
class Target:
    root: Path
    platform: str
    asar: Path
    executable: Path
    fuse_binary: Path
    extra_files: list = field(default_factory=list)

    @property
    def changed_files(self):
        return [self.asar] + self.extra_files


def host_platform():
    if sys.platform == 'darwin':
        return 'macos'
    if sys.platform == 'win32':
        return 'windows'
    raise ValueError('This installer supports macOS and Windows only.')


def discover(path=None):
    platform = host_platform()
    if path:
        root = Path(path).expanduser().resolve()
        if platform == 'windows' and root.suffix.lower() == '.exe':
            root = root.parent
    else:
        if platform == 'macos':
            candidates = [Path('/Applications/lolPing.app'), Path.home() / 'Applications/lolPing.app']
        else:
            candidates = []
            for env, suffix in [('LOCALAPPDATA', 'Programs/lolPing'), ('ProgramFiles', 'lolPing'),
                                ('ProgramFiles(x86)', 'lolPing')]:
                if os.environ.get(env):
                    candidates.append(Path(os.environ[env]) / suffix)
        found = [p.resolve() for p in candidates if p.exists()]
        found = list(dict.fromkeys(found))
        if len(found) != 1:
            raise ValueError('Cannot select one lolPing installation. Use --app with its full path.')
        root = found[0]
    if platform == 'macos':
        info = root / 'Contents/Info.plist'
        with info.open('rb') as handle:
            meta = plistlib.load(handle)
        if (meta.get('CFBundleIdentifier') != 'com.lolping.app'
                or meta.get('CFBundleExecutable') != 'lolPing'):
            raise ValueError('Unrecognized macOS application.')
        exe = root / 'Contents/MacOS' / meta['CFBundleExecutable']
        target = Target(root, platform, root / 'Contents/Resources/app.asar', exe,
                        root / 'Contents/Frameworks/Electron Framework.framework/Electron Framework',
                        [exe, info, root / 'Contents/_CodeSignature/CodeResources'])
    else:
        exe = root / 'lolPing.exe'
        target = Target(root, platform, root / 'resources/app.asar', exe, exe)
    for file in target.changed_files + [target.fuse_binary]:
        if not file.is_file():
            raise ValueError('Required application file is missing: ' + str(file))
    return target


def default_paths():
    if host_platform() == 'macos':
        base = Path.home() / 'Library/Application Support'
        return base / 'lolPing/settings.json', base / 'lolPing-answer-patch/backups'
    if not os.environ.get('APPDATA') or not os.environ.get('LOCALAPPDATA'):
        raise ValueError('Windows APPDATA / LOCALAPPDATA is unavailable.')
    return (Path(os.environ['APPDATA']) / 'lolPing/settings.json',
            Path(os.environ['LOCALAPPDATA']) / 'lolPing-answer-patch/backups')


def check_fuse(path):
    # Electron v1 wire; EmbeddedAsarIntegrityValidation is fuse index 4.
    # Refuse unknown formats rather than disable any executable protection.
    raw = path.read_bytes()
    offsets, start = [], 0
    while True:
        offset = raw.find(FUSE_MAGIC, start)
        if offset < 0:
            break
        offsets.append(offset)
        start = offset + len(FUSE_MAGIC)
    if not offsets:
        raise ValueError('Electron fuse wire not found; this executable has not been verified.')
    for offset in offsets:
        header = raw[offset + len(FUSE_MAGIC):offset + len(FUSE_MAGIC) + 2]
        if len(header) != 2 or header[0] != 1 or not 5 <= header[1] <= 32:
            raise ValueError('Unknown Electron fuse format.')
        flags = raw[offset + len(FUSE_MAGIC) + 2:offset + len(FUSE_MAGIC) + 2 + header[1]]
        if len(flags) != header[1] or any(c not in b'01r' for c in flags) or flags[4] != ord('0'):
            raise ValueError('Embedded ASAR integrity is enabled or unknown. This build is unsupported.')


def ensure_stopped(target):
    if target.platform == 'windows':
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq lolPing.exe', '/FO', 'CSV', '/NH'],
                                check=True, capture_output=True)
        rows = csv.reader(io.StringIO(result.stdout.decode(errors='replace')))
        running = any(row and row[0].lower() == 'lolping.exe' for row in rows)
    else:
        result = subprocess.run(['ps', '-axo', 'comm='], check=True, capture_output=True, text=True)
        running = any('/lolPing.app/Contents/' in line or line.strip() == str(target.executable)
                      for line in result.stdout.splitlines())
    if running:
        raise ValueError('Quit lolPing completely from its tray/menu bar, then try again.')


def sign_macos(target):
    # The official build includes integrity metadata even while its validation
    # fuse is disabled. Keep the metadata consistent without changing any fuse.
    from .asar import AsarArchive
    from .installer import atomic_write
    info = target.root / 'Contents/Info.plist'
    raw = info.read_bytes()
    meta = plistlib.loads(raw)
    archive = AsarArchive(target.asar.read_bytes())
    header_json = archive.raw[16:16 + int.from_bytes(archive.raw[12:16], 'little')]
    meta['ElectronAsarIntegrity'] = {'Resources/app.asar': {
        'algorithm': 'SHA256', 'hash': hashlib.sha256(header_json).hexdigest()}}
    fmt = plistlib.FMT_BINARY if raw.startswith(b'bplist') else plistlib.FMT_XML
    atomic_write(info, plistlib.dumps(meta, fmt=fmt))
    # Sign only the outer bundle; bundled helpers/framework signatures stay intact.
    subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', '--preserve-metadata=entitlements',
                    str(target.root)], check=True, capture_output=True)
    subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(target.root)],
                   check=True, capture_output=True)
