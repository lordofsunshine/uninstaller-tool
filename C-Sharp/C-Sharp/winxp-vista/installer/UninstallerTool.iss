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
OutputBaseFilename=UninstallerTool-Setup-{#AppVersion}-WindowsXP-Vista
SetupIconFile=..\assets\app_icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
MinVersion=5.1sp3
ArchitecturesAllowed=x86 x64
LicenseFile=..\LICENSE
ShowLanguageDialog=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function IsDotNet40OrLater: Boolean;
var
  Install: Cardinal;
  Release: Cardinal;
begin
  Result := False;
  if IsWin64 then
  begin
    if RegQueryDWordValue(HKLM64, 'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full', 'Install', Install) and (Install = 1) then
      Result := True
    else if RegQueryDWordValue(HKLM64, 'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full', 'Release', Release) then
      Result := Release >= 378389;
  end
  else
  begin
    if RegQueryDWordValue(HKLM, 'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full', 'Install', Install) and (Install = 1) then
      Result := True
    else if RegQueryDWordValue(HKLM, 'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full', 'Release', Release) then
      Result := Release >= 378389;
  end;
end;

function InitializeSetup: Boolean;
var
  Version: TWindowsVersion;
begin
  GetWindowsVersionEx(Version);

  if (Version.Major = 6) and (Version.Minor = 0) and (Version.ServicePackMajor < 1) then
  begin
    MsgBox('Uninstaller Tool requires Windows Vista Service Pack 1 or later.' + #13#10 + #13#10 +
           'Windows XP requires Service Pack 3.', mbError, MB_OK);
    Result := False;
    Exit;
  end;

  Result := IsDotNet40OrLater;
  if not Result then
    MsgBox('Uninstaller Tool requires Microsoft .NET Framework 4.0 or later.' + #13#10 + #13#10 +
           'Install it from the official Microsoft page:' + #13#10 +
           'https://www.microsoft.com/en-us/download/details.aspx?id=17718', mbError, MB_OK);
end;
