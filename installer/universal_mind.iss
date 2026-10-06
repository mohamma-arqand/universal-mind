; ═══════════════════════════════════════════════════════════════
; Universal Mind — the one-file Windows installer (Inno Setup)
; A product must install like a first-class citizen. This .iss
; compiles with ISCC (Inno Setup 6) into UniversalMind-Setup.exe:
;   * extracts everything into {app}
;   * creates the private venv + installs pinned requirements
;   * registers Task Scheduler autostart (the ONE admin ask)
;   * drops a Start-Menu icon + a Desktop shortcut
;   * UNINSTALL removes every trace (venv, shortcut, task, files)
;
; Build: ISCC installer\universal_mind.iss   (after setup.cmd)
; ═══════════════════════════════════════════════════════════════
#define MyAppName "Universal Mind"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Universal Mind"
#define MyAppExeName "universal_mind.cmd"
#define MyAppURL "https://github.com/UniversalMind/release"

[Setup]
AppId={{B4DDA70E-3E86-4E4E-8B0C-9F3A9C77D221}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\build\installer
OutputBaseFilename=UniversalMind-Setup-{#MyAppVersion}
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\build\bundle\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "یک آیکون روی دسکتاپ بگذار"; GroupDescription: "میانبرها:"

[Run]
Filename: "{app}\install.cmd"; Description: "نصب اولیه (auto-start + محیط)"; Flags: runhidden waituntilterminated postinstall

[UninstallRun]
Filename: "schtasks"; Parameters: "/delete /tn UniversalMind /f"; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}\.venv"
Type: filesandordirs; Name: "{app}"

