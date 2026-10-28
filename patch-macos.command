#!/bin/zsh
cd -- "${0:A:h}" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  print 'Install Python 3.9+ from python.org first. / 请先安装 Python 3.9 或更新版本。'
  read -r '?Press Enter to close / 按回车关闭'
  exit 1
fi
if (( $# == 0 )); then
  print '1) Install / 安装  2) Status / 状态  3) Restore / 还原'
  read -r 'choice?Select / 选择 [1]: '
  case "$choice" in
    2) set -- status ;;
    3) set -- restore ;;
    ''|1) set -- apply ;;
    *) print 'Invalid choice / 选项无效'; exit 1 ;;
  esac
fi
python3 -m lolping_patch "$@"
result=$?
read -r '?Press Enter to close / 按回车关闭'
exit "$result"
