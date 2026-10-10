; Compile through scripts/build_installer_windows.ps1: only its audited snapshot is input.
; This identity belongs to Studium permanently. Never regenerate it for an upgrade.
#if VER < EncodeVer(6, 3, 0)
  #error Inno Setup 6.3 or newer is required
#endif
#ifndef AppVersion
  #error AppVersion must be supplied by the build script
#endif
#ifndef PayloadInclude
  #error PayloadInclude must be supplied by the build script
#endif
#ifdef SyntheticTestRoot
  #error Synthetic roots are only allowed in the separate regression fixture
#endif

[Setup]
AppId={{B724B6D6-9F24-49D0-9A0B-49BF455BE744}
AppName=Studium
AppVersion={#AppVersion}
AppVerName=Studium {#AppVersion}
AppPublisher=COLOSSAL-maksik
AppPublisherURL=https://github.com/COLOSSAL-maksik/Studium-public
VersionInfoVersion={#AppVersion}
VersionInfoProductName=Studium
VersionInfoProductVersion={#AppVersion}
VersionInfoCompany=COLOSSAL-maksik
DefaultDirName={localappdata}\Programs\Studium
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DefaultGroupName=Studium
DisableProgramGroupPage=yes
DisableDirPage=auto
UninstallDisplayName=Studium
UninstallDisplayIcon={app}\Studium.exe
OutputBaseFilename=Studium-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LanguageDetectionMethod=none
ShowLanguageDialog=yes
CloseApplications=no
RestartApplications=no
SetupLogging=yes
; Future signing can use Inno's SignTool directives. No credentials or keys belong here.

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Exact per-file entries, generated after validation; no checkout-wide wildcard.
#include PayloadInclude

[Icons]
Name: "{userprograms}\Studium"; Filename: "{app}\Studium.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\Studium"; Filename: "{app}\Studium.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Studium.exe"; Description: "{cm:LaunchProgram,Studium}"; Flags: nowait postinstall skipifsilent

[Code]
const
  OwnershipKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{B724B6D6-9F24-49D0-9A0B-49BF455BE744}_is1';

function GuardDataRoot(): String;
begin
  Result := ExpandConstant('{localappdata}\Studium');
end;

function GuardAppVersion(): String;
begin
  Result := '{#AppVersion}';
end;

#include "InstallSafety.iss"
