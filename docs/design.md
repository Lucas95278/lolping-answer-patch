# lolPing Answer Patch design

User choice: patch an already installed application, with macOS and Windows entry points, rather than maintain another client.

Target: official lolPing 0.6.0. Preserve the confirmed behavior: no intermediate pings; final answer dialog beside the completion-time cursor; MCQ letters; bilingual FRQ; automatic copy; incomplete responses never become final answers.

Use a Python 3.9+ standard-library CLI with apply/status/restore commands and platform launchers. Share the bundle transformer across platforms. Validate package identity, version, known main-module fingerprints and every replacement anchor. Refuse unsupported or integrity-protected builds rather than bypass protections.

Back up original bundle and macOS signature files outside the project, and snapshot only the answer settings the installer changes. Write files atomically; roll back on install/signing failure. Restore only this patch's files, refuse to roll back an unrelated app update, and retain later edits to settings. Never package personal settings, credentials, history, entire upstream app or Riot assets.

macOS: re-sign locally and describe manual restoration of existing Accessibility and Screen Recording permissions. Windows: leave executable and its signature untouched; discover the per-user/per-machine installation or accept an explicit path. Never kill an application, request elevation automatically, or modify system permissions.

Ship English/Chinese documentation, upstream license notice, code differences, tests, Windows/macOS GitHub Actions matrix, and a deterministic source zip. Local macOS tests and Windows bundle compatibility checks must be distinguished from an actual Windows desktop test.

Current installed application is read-only input and is not an installation target during this project.
