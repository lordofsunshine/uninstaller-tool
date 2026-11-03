#define AppName "Uninstaller Tool"
#define AppExeName "UninstallerTool.exe"
#define AppPublisher "Uninstaller Tool"
#define AppId "{{6C1A4E7A-6F2B-4D2A-9E4A-2B0E1C7D3A51}"
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion={#AppVersion}
VersionInfoProductVersion={#AppVersion}
VersionInfoDescription={#AppName} Setup
VersionInfoCompany={#AppPublisher}
DefaultDirName={localappdata}\Programs\Uninstaller Tool
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=UninstallerTool-Setup-{#AppVersion}-Windows7-8-8.1
SetupIconFile=..\assets\app_icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
MinVersion=6.1sp1
CloseApplications=no
RestartApplications=no
LicenseFile=..\LICENSE
ShowLanguageDialog=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function IsDotNet461OrLater: Boolean;
var
  Release: Cardinal;
begin
  Result := False;
  if IsWin64 then
  begin
    if RegQueryDWordValue(HKLM64, 'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full', 'Release', Release) then
      Result := Release >= 394254;
  end
  else
  begin
    if RegQueryDWordValue(HKLM, 'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full', 'Release', Release) then
      Result := Release >= 394254;
  end;
end;

function InitializeSetup: Boolean;
begin
  Result := IsDotNet461OrLater;
  if not Result then
    MsgBox('Uninstaller Tool requires Microsoft .NET Framework 4.6.1 or later.' + #13#10 + #13#10 +
           'It supports Windows 7 SP1, Windows 8, Windows 8.1, Windows 10 and Windows 11.' + #13#10 + #13#10 +
           'Install it from the official Microsoft page:' + #13#10 +
           'https://www.microsoft.com/en-us/download/details.aspx?id=49982', mbError, MB_OK);
end;
