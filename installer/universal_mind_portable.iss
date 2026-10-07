; Universal Mind — FULL portable installer (Inno Setup 6)
; Everything this session built: 346 modules, 31 real capabilities,
; the compiled volctl.exe, the Persian door, autostart, shortcut,
; full uninstall. ONE double-click on a target desktop.

#define MyAppName "Universal Mind"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "Universal Mind"
#define MyAppExe "UniversalMind.cmd"

[Setup]
AppId={{8E1C9A4F-55D3-4B7A-9C2E-UMIND1000}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\UniversalMind
DefaultGroupName=Universal Mind
DisableProgramGroupPage=yes
OutputDir=D:\workspaces\baddanKhoda\build\installer
OutputBaseFilename=UniversalMind-Setup-1.1.0
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "D:\workspaces\baddanKhoda\build\portable\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\Universal Mind"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{group}\Universal Mind"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"

[Tasks]
Name: "desktopicon"; Description: "Desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "autostart"; Description: "Start with Windows (autostart)"; GroupDescription: "Startup:"

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "Launch Universal Mind now"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "UniversalMind"; ValueData: "{app}\{#MyAppExe}"; Flags: uninsdeletevalue; Tasks: autostart

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
