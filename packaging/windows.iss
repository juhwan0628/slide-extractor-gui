#define AppName "Slide Extractor"
#define AppVersion GetEnv("SLIDE_APP_VERSION")
#define BundleVersion GetEnv("SLIDE_BUNDLE_VERSION")
#if AppVersion == ""
  #error SLIDE_APP_VERSION must be read from slide_core/version.py before packaging
#endif
#if BundleVersion == ""
  #error SLIDE_BUNDLE_VERSION must be read using slide_core/version.py --bundle
#endif
[Setup]
AppId={{D70DD77D-5DAC-4A25-B7B5-1F03D8321744}
AppName={#AppName}
AppVersion={#AppVersion}
VersionInfoVersion={#BundleVersion}
DefaultDirName={localappdata}\Programs\SlideExtractor
DefaultGroupName={#AppName}
OutputBaseFilename=SlideExtractor-v{#AppVersion}-Setup-Windows-x64
OutputDir=..\dist
PrivilegesRequired=lowest
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\SlideExtractor.exe
[Files]
Source: "..\dist\SlideExtractor\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
[Icons]
Name: "{autoprograms}\Slide Extractor"; Filename: "{app}\SlideExtractor.exe"
[Run]
Filename: "{app}\SlideExtractor.exe"; Description: "Run Slide Extractor"; Flags: postinstall nowait skipifsilent
