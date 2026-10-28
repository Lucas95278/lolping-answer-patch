# Cross-platform patch implementation plan

Goal: produce a clean GitHub-ready patch project for installed lolPing 0.6.0.

Architecture: stdlib Python transaction CLI; ASAR and source transformations independent of OS; platform-specific discovery and signing; original files kept outside repository.

1. Test ASAR round-trips, entry integrity, invalid layouts, identity/version/fingerprint refusal and source transformation idempotence. Extract the already verified answer transform into a portable module; keep its 36 behavior/SSE tests running against both official platform bundles where available.
2. Test apply/status/restore on temporary Mac and Windows layouts, selective settings restore, failed signing rollback, repeated application and app-update refusal. Implement platform discovery, process checks, safe backup metadata, atomic writes and launchers.
3. Add README files, licenses, CI, artifact packaging and compatibility report. Run the full test suite, exercise the CLI against disposable application copies only, run a separate review, scan the source archive for private files, and deliver the project and zip.

Review focus: Windows EXE embedded integrity, partial transaction failures, restoring a later app update, preserving unrelated/user-edited settings, leaking private backup data into a release.
