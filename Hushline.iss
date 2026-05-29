; Inno Setup script for Hushline installer
[Setup]
AppName=Hushline
AppVersion=0.1
DefaultDirName={autopf}\Hushline
DefaultGroupName=Hushline
OutputBaseFilename=Hushline-Setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\Hushline\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "ambient_settings.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Hushline"; Filename: "{app}\Hushline.exe"
Name: "{group}\Uninstall Hushline"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\Hushline.exe"; Description: "Launch Hushline"; Flags: nowait postinstall skipifsilent
