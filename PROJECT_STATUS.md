## Current Snapshot

Last Updated: 2026-06-02

Project: UnmultBatchTool
Phase: build checkpoint, before UI restyle design

Current state:
- Reconstructed editable Python source from the original PyInstaller executable.
- Added source launcher, dependency file, README updates, and focused unittest coverage.
- Added first interaction fixes: optional drag-and-drop via `tkinterdnd2`, debounced preview updates, preview downsampling, and a more usable export panel placement.

Verification evidence:
- `python -m unittest tests.test_unmult_tool` passed.
- `python -m py_compile unmult_tool.py` passed.
- GUI smoke check created `UnmultApp`, confirmed drag token is available, updated idle tasks, and destroyed the window successfully.
- CLI smoke check processed one generated PNG successfully.

Dirty state:
- Initial repository has no commits yet.
- Next action is to commit the current checkpoint.

Known risks:
- `UnmultBatchTool.exe` is the old binary and has not been rebuilt from the reconstructed source.
- UI restyle is not designed or implemented yet.
