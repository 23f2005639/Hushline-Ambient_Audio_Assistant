; Inno Setup script for HushLine installer

[Setup]
AppName=HushLine
AppVersion=0.1.0-beta
AppPublisher=Your Name
AppPublisherURL=https://github.com/ShyamMishra-Lab/Hushline-Ambient_Audio_Assistant
AppSupportURL=https://github.com/ShyamMishra-Lab/Hushline-Ambient_Audio_Assistant/issues
AppUpdatesURL=https://github.com/ShyamMishra-Lab/Hushline-Ambient_Audio_Assistant/releases
DefaultDirName={autopf}\HushLine
DefaultGroupName=HushLine
OutputBaseFilename=HushLine-Setup-v0.1.0-beta
SetupIconFile=assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Files]
Source: "dist\Hushline.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "ambient_settings.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\HushLine"; Filename: "{app}\Hushline.exe"; IconFilename: "{app}\assets\icon.ico"
Name: "{userdesktop}\HushLine"; Filename: "{app}\Hushline.exe"; IconFilename: "{app}\assets\icon.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons"
Name: "startupentry"; Description: "Start HushLine when Windows starts"; GroupDescription: "Startup"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
ValueType: string; ValueName: "HushLine"; \
ValueData: "{app}\Hushline.exe"; \
Flags: uninsdeletevalue; Tasks: startupentry

[Run]
Filename: "{app}\Hushline.exe"; Description: "Launch HushLine"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/F /IM Hushline.exe"; Flags: runhidden; RunOnceId: "KillHushLine"