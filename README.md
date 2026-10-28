# lolPing Answer Patch

[English](README.md) · [简体中文](README.zh-CN.md)

An unofficial, reversible patch for an **already installed lolPing 0.6.0** on macOS and Windows. Keep the ask wheel, hide intermediate AI pings, and show the completed answer in lolPing's own dialog beside your cursor. The answer is also copied to your clipboard.

This is a local patch tool, not an official lolPing plugin API or a replacement client. Install [the original lolPing](https://github.com/darrenprx/lolPing/releases/tag/v0.6.0) separately.

## What changes

| Action | Result |
| --- | --- |
| MCQ: top wheel slice (`danger`) | Option letter(s), with question numbers when needed |
| FRQ: lower-right slice (`allin`) | English followed by Chinese for each subpart; everyday English around IELTS Writing 5.5 |
| While waiting | No receipt ping, step markers, emotes, progress bubble or automatic intermediate card |
| After a successful answer | One final answer dialog near the cursor's **current position**, without taking keyboard focus; automatic clipboard copy |
| Cancelled, superseded or incomplete response | No partial answer published or copied |

The patch uses the full document text that lolPing can extract, with a 600,000-character context cap and explicit coverage limitations. It cannot recover inaccessible pages or images omitted by the document extractor. Your provider's context limits still apply. All local AI asks use the quiet final-answer flow, including asks outside the two renamed slices. Remote visitors retain the upstream display flow, but share the changed prompt and stream validation.

## Supported versions

- **macOS 13+, Apple Silicon**, official lolPing 0.6.0 ARM64 build.
- **Windows 11 x64**, official lolPing 0.6.0 x64 build.
- **Python 3.9+**, using only its standard library. No pip packages or Node.js are needed to install the patch.
- An existing, working AI profile in lolPing. Your provider, model, API key, ask key and unrelated preferences are preserved.

Other versions, unofficial/rebuilt main modules, enabled Electron embedded ASAR validation and unknown fuse formats are refused. Intel Mac and Windows ARM64 have not been verified. See [compatibility and evidence](docs/compatibility.md); Windows desktop interaction has not been manually tested.

## Install on macOS

1. Install lolPing 0.6.0, launch it once, and configure an AI profile. Make sure a normal ask works first.
2. Download this repository with **Code → Download ZIP**, or get the source package from [Releases](https://github.com/Lucas95278/lolping-answer-patch/releases). Extract it into a writable folder.
3. Quit lolPing from its menu bar icon; closing the settings window is insufficient.
4. Double-click `patch-macos.command` and choose **1**. If the downloaded file has no executable permission, use the Terminal commands below.
5. Reopen lolPing. Hold your configured ask key (normally Command on Mac), drag to **MCQ** or **FRQ**, and release. The final answer appears beside the cursor when complete.

From Terminal, open the extracted project folder and run:

```sh
python3 -m lolping_patch apply
# Explicit path when auto-discovery cannot select one installation:
python3 -m lolping_patch apply --app "/Applications/lolPing.app"
```

The installer updates the ASAR header metadata in `Info.plist` and locally ad-hoc signs the outer app bundle. It does not re-sign bundled frameworks/helpers or change Electron fuses. This local signature is not Apple notarization. macOS may invalidate **existing** Accessibility or Screen Recording permission records after signing. If the ask gesture or screenshot stops working, open **System Settings → Privacy & Security**, restore lolPing's existing entries in those two panels yourself, and restart lolPing. The patch does not change system permissions, disable Gatekeeper or require you to share your password.

If installation reports a write-permission error, use a lolPing installation writable by your account; this tool does not elevate itself. If macOS blocks the downloaded launcher, run the Python command in Terminal after reviewing the source.

## Install on Windows

1. Install the official lolPing 0.6.0 x64 build, configure an AI profile, then fully quit its tray icon.
2. Install [Python](https://www.python.org/downloads/windows/) 3.9 or later. Enable its command-line launcher / PATH option.
3. Extract this project, double-click `patch-windows.cmd`, and choose **1**.
4. Reopen lolPing and use your existing ask key to choose **MCQ** or **FRQ**. The upstream Windows default ask key is Win; your configured key is not changed.

PowerShell or Command Prompt from the extracted project folder:

```powershell
py -3 -m lolping_patch apply
# For a custom installation location:
py -3 -m lolping_patch apply --app "D:\Apps\lolPing"
```

The tool checks the actual `lolPing.exe` fuse wire before changing `resources/app.asar`. It leaves the EXE and its signature byte-for-byte unchanged. System-wide installations can require write access; the usual per-user installation avoids elevation.

## Status, backup and restore

Quit lolPing before installing or restoring. Use the same `--app`, settings and backup locations used for installation.

```sh
python3 -m lolping_patch status
python3 -m lolping_patch restore
```

On Windows, replace `python3` with `py -3`. Both launchers also offer status and restore menu choices.

Backups are stored **outside the project**, under an installation-specific ID:

| Platform | Backup root | Settings file |
| --- | --- | --- |
| macOS | `~/Library/Application Support/lolPing-answer-patch/backups/` | `~/Library/Application Support/lolPing/settings.json` |
| Windows | `%LOCALAPPDATA%\lolPing-answer-patch\backups\` | `%APPDATA%\lolPing\settings.json` |

Keep the backup folder. It contains the original ASAR, the macOS outer signature files when applicable, hashes, transaction state and the previous values of the eight settings fields changed by this patch. It does not copy API keys, profiles or conversation history into a backup. Previous custom MCQ/FRQ instructions can contain your own text; do not upload backups.

Restore verifies every backed-up file and every affected installed file before writing. It refuses to overwrite an unrelated app update. Settings are restored field by field **only if their current value still equals the value this patch installed**; your later edits are kept. Reapplying a successfully installed patch is a no-op.

Ordinary installation/signing failures roll back automatically. After a forced process termination, inspect `status`. If it reports `installing` or `restoring`, quit lolPing and run:

```sh
python3 -m lolping_patch restore --recover
```

Recovery accepts the recorded original/patched states and, after an interrupted Mac signing operation, partial outer signature changes while the framework and known ASAR still match. Use it only for an interrupted transaction, not after updating lolPing. Recovery after power loss or storage failure is not guaranteed, especially on Windows. If files no longer match, keep your backup and reinstall the official app instead of forcing this tool. After restoring, you can update normally; a new app version requires a separately verified patch.

## Troubleshooting

- **No final answer:** first check provider/model connectivity and usage limits, then macOS permissions if relevant. Failed or truncated requests deliberately leave the clipboard unchanged and show no intermediate progress. Ask again with readable material or a longer provider output limit.
- **An older custom patch is already installed:** an unknown main-module fingerprint is refused. Use its original backup or reinstall official 0.6.0 before using this public tool. This tool cannot reconstruct missing originals.
- **Missing settings:** launch and configure the original app once before applying. Malformed JSON is refused, not replaced with defaults.
- **No backup:** the app may have been moved, patched from another account or patched with a different backup directory. Use the original locations. Never use a backup from another app version.
- **Short or incomplete document:** the prompt can request more readable file content, but cannot guarantee that every provider can accept the full context or see embedded images.

The patch adds no server, telemetry or upload step. AI requests still go through the provider configured in lolPing and follow its existing capture/history settings. Automatic copy overwrites the clipboard when an answer succeeds.

## Development and verification

```sh
python3 -m unittest discover -s tests -v
# Optional: Node.js 22+ and your own official app.asar, outside the repository:
python3 tools/check_bundle.py /path/to/original/app.asar
# Optional source diff for review:
python3 tools/check_bundle.py /path/to/original/app.asar --diff /tmp/lolping-answer.patch
python3 tools/build_release.py
```

`check_bundle.py` runs 36 answer/stream tests on the actual transformed module and verifies that all other packed ASAR entries remain unchanged. The Python suite tests archive integrity, installer rollback, selective settings restore, repeated application, app-update refusal and interrupted recovery. GitHub Actions runs unit tests on macOS/Windows with Python 3.9/3.13, plus a Windows official-bundle transform and CLI apply/restore check. It never launches lolPing or sends an AI request.

Code layout: `asar.py` reads/rebuilds the archive; `transform.py` contains the exact guarded JS changes; `platforms.py` discovers installations and handles signing; `installer.py` handles backup/transactions; `settings.py` applies the eight targeted preferences. `--settings-dir` and `--backup-dir` are available for isolated checks. A second app copy otherwise uses the same upstream settings location, so never test one without those overrides.

The release builder uses an explicit source-file whitelist and generates a source ZIP plus SHA256 checksum. It excludes installed apps, full compiled bundles, upstream artwork, private settings and backups.

## License and credits

MIT; see [LICENSE](LICENSE) and [NOTICE](NOTICE). Based on [darrenprx/lolPing v0.6.0](https://github.com/darrenprx/lolPing/tree/v0.6.0), copyright 2026 Danrui Meng. This project is unofficial and is not affiliated with lolPing or Riot Games. Riot icons/sounds and the original application are not distributed here. Electron fuse behavior is documented in the [official Electron guide](https://www.electronjs.org/docs/latest/tutorial/fuses).
