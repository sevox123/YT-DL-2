#define MyAppName "ClipFlow"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

[Setup]
AppId={{B7C2F5A1-3D4E-4F6A-9C1B-2E8A5D7F9013}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppName}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\Output
OutputBaseFilename=ClipFlow-Setup-{#MyAppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\ClipFlow.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; the PyInstaller output
Source: "..\dist\ClipFlow\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; helper tools downloaded by the GitHub workflow (ffmpeg for merging/cutting/mp3, deno for YouTube)
Source: "..\bin\ffmpeg.exe";  DestDir: "{app}"; Flags: ignoreversion
Source: "..\bin\ffprobe.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\bin\deno.exe";    DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\ClipFlow.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\ClipFlow.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ClipFlow.exe"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
