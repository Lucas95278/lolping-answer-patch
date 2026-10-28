import argparse
import json
import subprocess
import sys
from pathlib import Path

from .installer import Installer
from .platforms import discover, default_paths


def main(argv=None):
    # Windows redirected output can default to cp1252; bilingual messages must
    # not make an otherwise successful installation exit with an encoding error.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='backslashreplace')
    parser = argparse.ArgumentParser(description='lolPing 0.6.0 final-answer patch / 最终答案补丁')
    parser.add_argument('command', choices=['apply', 'status', 'restore'])
    parser.add_argument('--app', help='lolPing.app, Windows installation directory, or lolPing.exe')
    parser.add_argument('--settings-dir', type=Path, help='Override settings directory (for isolated tests)')
    parser.add_argument('--backup-dir', type=Path, help='Override backup root; retain it for restore')
    parser.add_argument('--recover', action='store_true', help='Recover an interrupted restore/install')
    args = parser.parse_args(argv)
    if args.recover and args.command != 'restore':
        parser.error('--recover can only be used with restore')
    try:
        settings, backups = default_paths()
        target = discover(args.app)
        installer = Installer(target, args.settings_dir / 'settings.json' if args.settings_dir else settings,
                              args.backup_dir or backups)
        if args.command == 'apply':
            result = installer.apply()
        elif args.command == 'restore':
            result = installer.restore(recover=args.recover)
        else:
            result = installer.status()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.command == 'apply' and result['state'] == 'installed':
            print('Patch installed. Restart lolPing. / 补丁已安装，请重新打开 lolPing。')
        if args.command == 'restore' and result['state'] in ('restored', 'rolled-back'):
            print('Original application restored. / 已还原原版程序。')
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print('Error / 错误: ' + str(exc), file=sys.stderr)
        print('See README for permissions, backup recovery and supported builds. / 请查阅 README 的权限、备份与版本说明。', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
