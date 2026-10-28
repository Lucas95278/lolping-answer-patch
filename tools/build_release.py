"""Create a deterministic source-only zip from an explicit file whitelist."""

import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    '.gitignore', '.github/workflows/test.yml', 'README.md', 'README.zh-CN.md',
    'LICENSE', 'NOTICE', 'CHANGELOG.md', 'patch-macos.command', 'patch-windows.cmd',
    'docs/design.md', 'docs/implementation-plan.md', 'docs/compatibility.md',
    'lolping_patch/__init__.py', 'lolping_patch/__main__.py', 'lolping_patch/asar.py',
    'lolping_patch/transform.py', 'lolping_patch/platforms.py', 'lolping_patch/settings.py',
    'lolping_patch/installer.py', 'tools/build_release.py', 'tools/check_bundle.py',
    'tools/fetch_windows_fixture.py', 'tools/smoke_windows.py',
    'tests/test_asar.py', 'tests/test_installer.py', 'tests/test_transform.py', 'tests/test_platforms.py',
    'tests/runtime/answers.test.cjs', 'tests/runtime/streams.test.cjs',
]


def main():
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    archive = output / 'lolping-answer-patch-1.0.0.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
        for name in sorted(FILES):
            info = zipfile.ZipInfo('lolping-answer-patch/' + name, (2026, 10, 28, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if name.endswith('.command') else 0o644
            info.external_attr = (0o100000 | mode) << 16
            zipped.writestr(info, (ROOT / name).read_bytes())
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / 'SHA256SUMS.txt').write_text(checksum + '  ' + archive.name + '\n', encoding='utf-8')
    print(archive)
    print(checksum)


if __name__ == '__main__':
    main()
