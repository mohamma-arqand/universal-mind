; Universal Mind — LITE installer (no cv2/scipy: 185MB unpacked)
; The Lite law: the door stays open; the vision/AI-signal capabilities
; refuse BY NAME with the remedy.

#define MyAppName "Universal Mind Lite"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "Universal Mind"
#define MyAppExe "UniversalMind.cmd"

[Setup]
AppId={{8E1C9A4F-55D3-4B7A-9C2E-UMINDLITE}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\UniversalMindLite
DefaultGroupName=Universal Mind Lite
DisableProgramGroupPage=yes
OutputDir=D:\workspaces\baddanKhoda\build\installer
OutputBaseFilename=UniversalMind-Lite-Setup-1.1.0
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "D:\workspaces\baddanKhoda\build\portable-lite\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\Universal Mind Lite"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{group}\Universal Mind Lite"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"

[Tasks]
Name: "desktopicon"; Description: "Desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "autostart"; Description: "Start with Windows (autostart)"; GroupDescription: "Startup:"

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "Launch Universal Mind Lite now"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "UniversalMindLite"; ValueData: "{app}\{#MyAppExe}"; Flags: uninsdeletevalue; Tasks: autostart

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
