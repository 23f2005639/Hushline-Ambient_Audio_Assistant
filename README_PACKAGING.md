Hushline — Packaging and Windows installer

Overview
- This document shows commands to build a Windows executable and an installer.

Prerequisites
- Windows x64 build machine
- Project virtualenv active
- Install build deps:

```powershell
pip install -r requirements.txt
pip install pyinstaller
```

Build steps (recommended: `--onedir` first)

1) Build with PyInstaller (script provided):

```powershell
# from project root
.\build_pyinstaller.ps1
```

2) Test the build

```powershell
# run the generated exe
dist\Hushline\Hushline.exe
```

3) Create installer with Inno Setup
- Install Inno Setup (https://jrsoftware.org/isinfo.php)
- Build installer:

```powershell
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" Hushline.iss
```

Notes & Troubleshooting
- If Qt plugins fail at runtime, include PySide6 plugin folders with `--add-data` or use `--collect-all PySide6`.
- For media control, ensure `winrt` is available and the target machine has the relevant media APIs.
- Code-sign the final `Hushline-Setup.exe` for distribution.

If you want, I can:
- generate a `pyproject.toml` / `requirements.txt` from your venv
- create a single-file (`--onefile`) spec instead of `--onedir`
- produce a CI script that builds and signs the installer
