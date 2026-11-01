#define MyAppName "RoboChess"
#define MyAppVersion "1.0.0"
[Setup]
AppId={{CA242A77-E361-4161-A18D-5A6FA2C84941}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=SFUbuntu
AppPublisherURL=https://github.com/SFUbuntu/RoboChess
DefaultDirName={localappdata}\Programs\RoboChess
DefaultGroupName=RoboChess
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=outputs
OutputBaseFilename=RoboChess-Instalador-Windows-x64
SetupIconFile=chess_comparator\assets\rook.ico
UninstallDisplayIcon={app}\RoboChess.exe
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; Flags: unchecked
[Files]
Source: "dist\RoboChess\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\RoboChess"; Filename: "{app}\RoboChess.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\RoboChess"; Filename: "{app}\RoboChess.exe"; WorkingDir: "{app}"; Tasks: desktopicon
[Run]
Filename: "{app}\RoboChess.exe"; Description: "Abrir RoboChess"; Flags: nowait postinstall skipifsilent
