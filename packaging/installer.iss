#if VER != EncodeVer(6, 7, 3)
  #error Use the locked Inno Setup 6.7.3 compiler
#endif

#ifndef BundleDir
  #error BundleDir must point to the PyInstaller SukunaPet directory
#endif
#ifndef ReleaseDir
  #error ReleaseDir must point to the release directory
#endif
#ifndef AppVersion
  #error AppVersion must match pyproject.toml
#endif

[Setup]
AppId={{04B576E4-248B-4D31-978B-86783245D204}
AppName=宿傩桌宠
AppVersion={#AppVersion}
AppPublisher=skip-pet
AppPublisherURL=https://github.com/xyd-0811/skip-pet
DefaultDirName={localappdata}\Programs\SukunaPet
DefaultGroupName=宿傩桌宠
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir={#ReleaseDir}
OutputBaseFilename=Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\SukunaPet.exe
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\宿傩桌宠\宿傩桌宠"; Filename: "{app}\SukunaPet.exe"; WorkingDir: "{app}"
Name: "{userprograms}\宿傩桌宠\卸载宿傩桌宠"; Filename: "{uninstallexe}"
Name: "{userdesktop}\宿傩桌宠"; Filename: "{app}\SukunaPet.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\SukunaPet.exe"; Description: "Launch 宿傩桌宠"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeUninstall(): Boolean;
var
  CleanupCode: Integer;
  ProgramPath: String;
begin
  Result := True;
  ProgramPath := ExpandConstant('{app}\SukunaPet.exe');
  if FileExists(ProgramPath) then
  begin
    if not Exec(ProgramPath, '--uninstall-cleanup', ExpandConstant('{app}'),
      SW_HIDE, ewWaitUntilTerminated, CleanupCode) then
      Result := False
    else
      Result := CleanupCode = 0;
    if not Result then
      MsgBox('Bridge cleanup failed. Application files were kept. See ' +
        ExpandConstant('{localappdata}\sukuna-pet\uninstall-cleanup.log'), mbError, MB_OK);
  end;
end;
