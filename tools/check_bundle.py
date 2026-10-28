"""Verify a user-supplied official bundle without launching or modifying the app."""

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lolping_patch.asar import AsarArchive
from lolping_patch.transform import patch_main


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('asar', type=Path)
    parser.add_argument('--node', default='node')
    parser.add_argument('--diff', type=Path, help='Write a source diff outside release files')
    args = parser.parse_args()
    archive = AsarArchive(args.asar.read_bytes())
    archive.verify_integrity()
    package = json.loads(archive.read('package.json'))
    assert package['name'] == 'lolping' and package['version'] == '0.6.0', 'Unsupported package'
    original = archive.read('out/main/index.js').decode('utf-8')
    patched = patch_main(original)
    rebuilt = AsarArchive(archive.replace('out/main/index.js', patched.encode('utf-8')))
    rebuilt.verify_integrity()
    assert all(archive.read(name) == rebuilt.read(name) for name, entry in archive.entries.items()
               if name != 'out/main/index.js' and not entry.get('unpacked') and 'link' not in entry)
    if args.diff:
        args.diff.write_text(''.join(difflib.unified_diff(original.splitlines(True), patched.splitlines(True),
                                  fromfile='a/out/main/index.js', tofile='b/out/main/index.js')), encoding='utf-8')
    helpers = [name for name in archive.entries if name.startswith('out/main/chunks/_commonjsHelpers-')]
    assert len(helpers) == 1, 'Unexpected common helper module layout'
    with tempfile.TemporaryDirectory(prefix='lolping-answer-tests-') as temporary:
        folder = Path(temporary)
        source, tools = folder / 'index.js', folder / 'tools.cjs'
        source.write_text(patched, encoding='utf-8')
        tools.write_bytes(archive.read(helpers[0]))
        env = dict(os.environ, LOLPING_SOURCE=str(source), LOLPING_TOOLS=str(tools))
        tests = sorted((Path(__file__).resolve().parents[1] / 'tests/runtime').glob('*.test.cjs'))
        subprocess.run([args.node, '--test', *map(str, tests)], check=True, env=env)
    print('Verified main SHA256:', hashlib.sha256(original.encode()).hexdigest())
    print('All other packed entries unchanged; rebuilt ASAR integrity verified.')


if __name__ == '__main__':
    main()
