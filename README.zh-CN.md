# lolPing 最终答案补丁

[English](README.md) · [简体中文](README.zh-CN.md)

给**已经安装的 lolPing 0.6.0**使用的非官方补丁，包含 Mac 和 Windows 入口。保留原来的提问轮盘，隐藏 AI 回答过程中的彩色打点；回答完成后，在**鼠标当前所在位置旁边**显示 lolPing 自带的答案对话框，同时自动复制答案。

这是本机补丁工具，不是 lolPing 官方提供的插件接口，也不需要维护另一套客户端。请先单独安装[官方 lolPing 0.6.0](https://github.com/darrenprx/lolPing/releases/tag/v0.6.0)。

## 使用效果

| 操作 | 结果 |
| --- | --- |
| MCQ：轮盘上方（`danger`） | 输出选项字母；多道题保留题号 |
| FRQ：轮盘右下方（`allin`） | 每个小问先英文、后中文；英文使用约雅思写作 5.5 的常用表达 |
| 等待回答 | 不显示接收提示、步骤打点、表情、进度气泡或中途自动弹出的卡片 |
| 回答成功 | 鼠标完成时的位置旁边出现最终答案框，不抢键盘焦点；答案自动复制 |
| 请求被取消、被新问题替代或回答被截断 | 不弹出、不复制不完整答案 |

补丁会使用 lolPing 能提取到的完整文档文字，上限为 600,000 个字符，并标明提取范围的限制。它无法补出没有读到的页面或提取器遗漏的图片，也受模型上下文长度限制。所有本机 AI 提问都会使用安静的最终答案流程，除了两个改名的入口，其他本机入口也会受影响。远程访客保留原有显示流程，但共用修改后的提示词和回答完整性检查。

## 支持范围

- **Mac：macOS 13 或更新版本、Apple Silicon**，官方 lolPing 0.6.0 ARM64 程序包。
- **Windows：Windows 11 x64**，官方 lolPing 0.6.0 x64 程序包。
- **Python 3.9 或更新版本**，仅使用标准库；安装补丁不需要 pip 依赖或 Node.js。
- lolPing 中已经配置了可用的 AI 服务。补丁保留服务商、模型、密钥、提问按键及其他无关设置。

不支持其他版本、重新编译或不认识的主程序代码、启用了 Electron 内嵌 ASAR 校验的构建，以及无法识别的保护开关格式。Intel Mac 和 Windows ARM64 尚未验证。[验证记录](docs/compatibility.md)中区分了程序包检查与真实桌面测试；目前没有人工完成 Windows 桌面交互测试。

## Mac 安装

1. 安装官方 0.6.0，启动一次并配置 AI，先确认原版提问可用。
2. 在本仓库点击 **Code → Download ZIP**，或从 [Releases](https://github.com/Lucas95278/lolping-answer-patch/releases) 下载源码补丁包，解压到自己可写入的文件夹。
3. 从菜单栏图标**完全退出** lolPing。只关闭设置窗口不够。
4. 双击 `patch-macos.command`，选择 **1**。如果下载后文件没有执行权限，使用下方的终端命令。
5. 重新打开 lolPing，按住原有提问键（Mac 通常是 Command），拖到 **MCQ** 或 **FRQ** 后松开。回答完成后，答案框会出现在鼠标旁边。

在解压后的项目文件夹打开终端，执行：

```sh
python3 -m lolping_patch apply
# 有多个安装位置，或自动查找失败时：
python3 -m lolping_patch apply --app "/Applications/lolPing.app"
```

补丁会更新 `Info.plist` 中的 ASAR 头部校验信息，并在本机为最外层应用重新签名。不会重签内置框架或辅助程序，也不会修改 Electron 的保护开关。本机临时签名不等同于 Apple 公证。重签名后，macOS 可能让**原有**辅助功能或屏幕录制授权失效；如果提问手势或截图异常，请自行到**系统设置 → 隐私与安全性**，恢复这两个面板中 lolPing 原来的授权记录，再重启应用。工具不会自动修改系统权限、关闭 Gatekeeper，也不需要你在聊天或项目中提供密码。

如果提示无写入权限，请使用当前账户有权写入的 lolPing 安装位置；工具不会自行提权。如果 macOS 阻止下载的启动脚本，请在检查源码后，通过终端运行 Python 命令。

## Windows 安装

1. 安装官方 lolPing 0.6.0 x64，配置 AI，然后从托盘图标完全退出。
2. 安装 [Python 3.9 或更新版本](https://www.python.org/downloads/windows/)，启用命令行启动器或 PATH 选项。
3. 解压本项目，双击 `patch-windows.cmd`，选择 **1**。
4. 重新打开 lolPing，使用原来的提问键选择 **MCQ** 或 **FRQ**。原版 Windows 默认提问键是 Win；补丁不会改变你的按键设置。

也可以在项目文件夹打开 PowerShell 或命令提示符：

```powershell
py -3 -m lolping_patch apply
# 自定义安装位置：
py -3 -m lolping_patch apply --app "D:\Apps\lolPing"
```

工具会检查实际 `lolPing.exe` 中的 Electron 保护开关，再修改 `resources/app.asar`。EXE 及其中的签名保持逐字节不变。安装在系统目录的程序可能需要写入权限；通常使用原版的当前用户安装即可。

## 查看状态、备份和还原

安装和还原前都要退出 lolPing，并使用安装时相同的应用路径、设置目录和备份目录。

```sh
python3 -m lolping_patch status
python3 -m lolping_patch restore
```

Windows 把 `python3` 换成 `py -3`。两个启动脚本也提供查看状态和还原菜单。

备份放在**项目文件夹之外**，按应用安装路径生成独立编号：

| 系统 | 备份根目录 | 设置文件 |
| --- | --- | --- |
| Mac | `~/Library/Application Support/lolPing-answer-patch/backups/` | `~/Library/Application Support/lolPing/settings.json` |
| Windows | `%LOCALAPPDATA%\lolPing-answer-patch\backups\` | `%APPDATA%\lolPing\settings.json` |

请保留备份。它包含原版 ASAR、Mac 外层签名相关文件、文件校验值、安装状态，以及本补丁修改的八个设置字段原值。不会把 API 密钥、服务配置或聊天记录复制进备份。原有的 MCQ/FRQ 自定义说明可能包含你自己的文字，请勿上传备份目录。

还原前会检查所有备份文件和所有受影响的应用文件；如果程序已经更新，不会覆盖新版本。设置按字段恢复：**只有当前值仍等于本补丁写入的值时，才恢复旧值**，保留你安装后做的修改。对成功安装的补丁重复执行安装，不会叠加修改。

普通安装或签名失败会自动回滚。如果补丁进程被强制结束，先执行 `status`；若状态为 `installing` 或 `restoring`，退出 lolPing 后执行：

```sh
python3 -m lolping_patch restore --recover
```

恢复模式接受记录中的原版或补丁状态；Mac 签名中断时，还会在框架和已知 ASAR 仍匹配的前提下，处理未完成的外层签名。仅用于安装中断，不要在 lolPing 更新后使用。断电或存储设备故障后的恢复不作保证，Windows 尤其如此。如果文件已经不匹配，请保留备份并重装官方软件，不要强行覆盖。需要更新 lolPing 时，先还原；新版本需单独验证补丁。

## 常见问题

- **没有最终答案：**先检查服务商、模型连接和用量，再检查 Mac 权限。失败或被截断的请求会保留原有剪贴板，不显示中间进度；提供可读材料，或提高服务商输出长度后重试。
- **此前安装过自定义补丁：**无法识别的主程序指纹会被拒绝。先使用旧补丁备份，或重装官方 0.6.0。工具不能凭空还原丢失的原文件。
- **找不到设置文件：**先启动原版并配置 AI。设置 JSON 损坏时会停止，不会用默认值覆盖。
- **找不到备份：**检查应用是否换了位置、是否由另一账户安装，或是否使用过自定义备份目录。不要混用不同版本的备份。
- **文档内容不完整：**补丁可以要求继续读取可用文件，但不能保证模型能容纳全文，也不能保证嵌入图片被提取。

补丁不增加服务器、遥测或上传环节。AI 请求仍交给 lolPing 中配置的服务商，并遵循原有的截屏和历史设置。回答成功后自动复制，会覆盖当前剪贴板。

## 开发与验证

```sh
python3 -m unittest discover -s tests -v
# 可选：使用 Node.js 22+ 与仓库外自己的官方 app.asar
python3 tools/check_bundle.py /path/to/original/app.asar
# 可选：生成供审阅的源码差异
python3 tools/check_bundle.py /path/to/original/app.asar --diff /tmp/lolping-answer.patch
python3 tools/build_release.py
```

`check_bundle.py` 对实际改写后的模块运行 36 项答案及流式完整性测试，同时验证其他 ASAR 内置文件保持不变。Python 测试覆盖归档校验、失败回滚、设置选择性恢复、重复安装、拒绝覆盖新版本和中断恢复。GitHub Actions 在 Mac/Windows、Python 3.9/3.13 上运行单元测试，并对官方 Windows 程序包执行转换、命令行安装和还原验证；不会启动 lolPing 或发送 AI 请求。

源码构成：`asar.py` 处理程序归档，`transform.py` 保存带版本检查的 JS 修改，`platforms.py` 负责查找应用和 Mac 签名，`installer.py` 管理备份与安装状态，`settings.py` 修改八项指定设置。隔离测试可使用 `--settings-dir` 和 `--backup-dir`；原版不同应用副本默认仍共用同一设置目录，测试副本时必须覆盖目录。

发布打包器只包含明确列出的源码文件，生成源码 ZIP 和 SHA256 校验文件，不会打包已安装的软件、完整编译代码、上游图标音效、个人设置或备份。

## 许可与来源

使用 MIT 许可，详见 [LICENSE](LICENSE) 和 [NOTICE](NOTICE)。基于 [darrenprx/lolPing v0.6.0](https://github.com/darrenprx/lolPing/tree/v0.6.0)，原作者版权为 2026 Danrui Meng。本项目非官方，与 lolPing 或 Riot Games 无隶属关系；不分发 Riot 图标、音效或原版应用。Electron 保护开关见[官方文档](https://www.electronjs.org/docs/latest/tutorial/fuses)。
