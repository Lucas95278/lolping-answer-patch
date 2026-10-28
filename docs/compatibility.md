# Compatibility evidence / 兼容性验证

Checked on 2026-10-28. Patch version 1.0.0 targets upstream v0.6.0, source commit `76812ad5b1cdbe55eb44455b43bac2c51f0618d0`.

| Check | macOS ARM64 | Windows x64 |
| --- | --- | --- |
| Official 0.6.0 main-module fingerprint | Verified | Verified from official NSIS installer |
| Original and rebuilt ASAR entry integrity | Passed | Passed |
| Other packed files unchanged | Passed | Passed |
| 36 answer/stream behavior tests on transformed code | Passed locally | Passed locally using Windows bundle |
| Native installer signing / byte-exact restore | Passed on disposable app copy, isolated settings/backup paths | Automated Windows CLI check is provided in GitHub Actions |
| Manual final-answer desktop interaction | User confirmed on this Mac during the original repair | Not performed |

The disposable Mac copy was never launched. Its real outer signing and deep signature verification ran successfully; all four affected app files restored to their original bytes. The process-running boundary was mocked for that isolated check because the user's working lolPing remained open. Unit tests separately cover the installer logic. A static Windows-bundle test runs JavaScript outside Electron and does not verify global hooks, multi-monitor scaling, screen capture or window focus on a Windows desktop.

## Fingerprints

Both official platforms share the same `out/main/index.js`:

```text
43d1f8835531226f87cdc384664c45878e343e5e86a919c44982e80b63d1035c
```

Official Windows 0.6.0 installer SHA256:

```text
371f2c0544ab7160c8f531438c13e388d431b2cec2deedd3857d2c1b65e47b81
```

Download: [upstream v0.6.0 release](https://github.com/darrenprx/lolPing/releases/tag/v0.6.0).

The original Mac ASAR checked during the repair had SHA256:

```text
93d3ad0ca93f285af4aa7db1a3e1ed4cd074033ca2d7f40db1f40bf3a8aa65ae
```

Both inspected Electron binaries use a v1 fuse wire with EmbeddedAsarIntegrityValidation disabled. The installer inspects that wire on every apply, does not disable it, and refuses an enabled/unknown value. macOS includes ASAR header hash metadata even with the validation fuse disabled; the patch updates that metadata before signing.

## Limits / 限制

Windows still needs manual desktop verification; Intel Mac, Windows ARM64, older/newer lolPing releases and rebuilt packages are unverified. Provider responses are probabilistic; bilingual style and correctness depend on the configured model. Document extraction does not guarantee image coverage. A provider context/output limit can cause a request to fail instead of returning a complete answer.

Windows 尚需人工验证真实桌面操作。没有验证 Intel Mac、Windows ARM64、其他 lolPing 版本或自行重新编译的程序包。双语风格与答案准确性受模型影响；文档提取不保证覆盖嵌入图片；超出模型上下文或输出长度时，可能没有最终答案。
