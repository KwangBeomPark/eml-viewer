#define MyAppName "EML Viewer"
#define MyAppPublisher "KwangBeomPark"
#define MyAppExeName "EmlViewer.exe"
#define MyAppIcon "..\..\assets\app.ico"
#ifndef MyAppVersion
#define MyAppVersion "0.1.7"
#endif

[Setup]
AppId={{A9D9B7C3-04B8-4D2F-B28C-5B18C01C9CE1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppMutex=EmlViewerMutex
CloseApplications=yes
DefaultDirName={localappdata}\Programs\EML Viewer
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\..\installer
OutputBaseFilename=EmlViewerSetup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile={#MyAppIcon}
WizardStyle=modern
ChangesAssociations=yes

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "associateeml"; Description: ".eml/.msg 파일을 EML Viewer로 열기"; GroupDescription: "파일 연결:"; Flags: checkedonce

[Files]
Source: "..\..\dist\EmlViewer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Classes\.eml"; ValueType: string; ValueName: ""; ValueData: "EMLViewer.eml"; Flags: uninsdeletevalue; Tasks: associateeml
Root: HKCU; Subkey: "Software\Classes\EMLViewer.eml"; ValueType: string; ValueName: ""; ValueData: "EML Email File"; Flags: uninsdeletekey; Tasks: associateeml
Root: HKCU; Subkey: "Software\Classes\EMLViewer.eml\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: associateeml
Root: HKCU; Subkey: "Software\Classes\EMLViewer.eml\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: associateeml
Root: HKCU; Subkey: "Software\Classes\.msg"; ValueType: string; ValueName: ""; ValueData: "EMLViewer.msg"; Flags: uninsdeletevalue; Tasks: associateeml
Root: HKCU; Subkey: "Software\Classes\EMLViewer.msg"; ValueType: string; ValueName: ""; ValueData: "Outlook MSG Email File"; Flags: uninsdeletekey; Tasks: associateeml
Root: HKCU; Subkey: "Software\Classes\EMLViewer.msg\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: associateeml
Root: HKCU; Subkey: "Software\Classes\EMLViewer.msg\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: associateeml
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: associateeml

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  PreviousAssociation: string;
begin
  if (CurStep = ssInstall) and WizardIsTaskSelected('associateeml') then
  begin
    if RegQueryStringValue(HKCU, 'Software\Classes\.eml', '', PreviousAssociation) then
    begin
      RegWriteStringValue(HKCU, 'Software\EMLViewer', 'PreviousEmlAssociation', PreviousAssociation);
    end;
    if RegQueryStringValue(HKCU, 'Software\Classes\.msg', '', PreviousAssociation) then
    begin
      RegWriteStringValue(HKCU, 'Software\EMLViewer', 'PreviousMsgAssociation', PreviousAssociation);
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  PreviousAssociation: string;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if RegQueryStringValue(HKCU, 'Software\EMLViewer', 'PreviousEmlAssociation', PreviousAssociation) then
    begin
      RegWriteStringValue(HKCU, 'Software\Classes\.eml', '', PreviousAssociation);
    end;
    if RegQueryStringValue(HKCU, 'Software\EMLViewer', 'PreviousMsgAssociation', PreviousAssociation) then
    begin
      RegWriteStringValue(HKCU, 'Software\Classes\.msg', '', PreviousAssociation);
    end;
    RegDeleteKeyIncludingSubkeys(HKCU, 'Software\EMLViewer');
  end;
end;
