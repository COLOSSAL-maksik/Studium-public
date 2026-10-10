; Never distribute this fixture. No application is launched and no real data root is used.
#ifndef SyntheticTestRoot
  #error Supply the unique synthetic data root
#endif
#ifndef PayloadInclude
  #error Supply the audited synthetic payload include
#endif

[Setup]
AppId={{F6C8A96D-0143-4591-9451-95B516F1446B}
AppName=Studium Synthetic Installer Test
AppVersion={#AppVersion}
AppPublisher=Studium Synthetic Test
DefaultDirName={tmp}\Studium-Synthetic-Program
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
OutputBaseFilename=Studium-Synthetic-Setup-{#AppVersion}
Compression=zip
SetupLogging=yes

[Files]
#include PayloadInclude

[Code]
const
  OwnershipKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{F6C8A96D-0143-4591-9451-95B516F1446B}_is1';

function GuardDataRoot(): String;
begin
  Result := '{#SyntheticTestRoot}';
end;

function GuardAppVersion(): String;
begin
  Result := '{#AppVersion}';
end;

#include "..\InstallSafety.iss"
