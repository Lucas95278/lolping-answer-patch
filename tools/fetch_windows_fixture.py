"""Download and unpack the official Windows fixture for maintainer checks only."""

import hashlib
from pathlib import Path
import shutil
import subprocess
import urllib.request

URL = 'https://github.com/darrenprx/lolPing/releases/download/v0.6.0/lolPing-Setup-0.6.0.exe'
SHA256 = '371f2c0544ab7160c8f531438c13e388d431b2cec2deedd3857d2c1b65e47b81'


def main():
    root = Path('fixtures/windows').resolve()
    root.mkdir(parents=True, exist_ok=True)
    installer = root / 'installer.exe'
    urllib.request.urlretrieve(URL, installer)
    if hashlib.sha256(installer.read_bytes()).hexdigest() != SHA256:
        raise ValueError('Official installer checksum mismatch')
    seven = shutil.which('7z') or shutil.which('7zz')
    if not seven:
        raise ValueError('7-Zip is required only for this maintainer fixture download')
    subprocess.run([seven, 'x', '-y', '-o' + str(root / 'nsis'), str(installer),
                    '$PLUGINSDIR/app-64.7z'], check=True, stdout=subprocess.DEVNULL)
    subprocess.run([seven, 'x', '-y', '-o' + str(root / 'app'),
                    str(root / 'nsis/$PLUGINSDIR/app-64.7z')], check=True, stdout=subprocess.DEVNULL)
    print(root / 'app/resources/app.asar')


if __name__ == '__main__':
    main()
