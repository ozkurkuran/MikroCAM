; MikroCAM per-user Windows installer (NSIS 3.12, Unicode).
; Built by release/windows/build.py; every /D value comes from mikrocam/core/identity.py.
; Required defines: APP_NAME APP_VERSION VI_VERSION PUBLISHER COPYRIGHT URL HELP_URL APP_EXE
; UNINSTALLER REG_KEY SOURCE_DIR OUTFILE UNINSTALL_LIST LICENSE_FILE ICON_FILE CONFIG_FILE

Unicode true
ManifestDPIAware true
RequestExecutionLevel user
; zlib keeps the embedded decompressor under the zlib/libpng license (LZMA would add CPL-1.0).
SetCompressor /SOLID zlib

!include "MUI2.nsh"
!include "FileFunc.nsh"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "${OUTFILE}"
InstallDir "$LOCALAPPDATA\Programs\${APP_NAME}"
InstallDirRegKey HKCU "${REG_KEY}" "InstallLocation"
BrandingText "${APP_NAME} ${APP_VERSION}"

VIProductVersion "${VI_VERSION}"
VIAddVersionKey /LANG=1033 "ProductName" "${APP_NAME}"
VIAddVersionKey /LANG=1033 "ProductVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1033 "FileVersion" "${VI_VERSION}"
VIAddVersionKey /LANG=1033 "FileDescription" "${APP_NAME} ${APP_VERSION} Setup"
VIAddVersionKey /LANG=1033 "CompanyName" "${PUBLISHER}"
VIAddVersionKey /LANG=1033 "LegalCopyright" "${COPYRIGHT}"

!define MUI_ICON "${ICON_FILE}"
!define MUI_UNICON "${ICON_FILE}"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_LINK "${URL}"
!define MUI_FINISHPAGE_LINK_LOCATION "${URL}"

!insertmacro MUI_PAGE_LICENSE "${LICENSE_FILE}"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "Turkish"

Section "MikroCAM" SecMain
  SectionIn RO
  SetShellVarContext current
  ; Replace an earlier installation with its own uninstaller so stale files do not remain.
  IfFileExists "$INSTDIR\${UNINSTALLER}" 0 fresh
    ExecWait '"$INSTDIR\${UNINSTALLER}" /S _?=$INSTDIR'
    Delete "$INSTDIR\${UNINSTALLER}"
  fresh:
  SetOutPath "$INSTDIR"
  File /r "${SOURCE_DIR}\*"
  SetOutPath "$INSTDIR\config"
  File "/oname=configuration.txt" "${CONFIG_FILE}"
  SetOutPath "$INSTDIR"
  WriteUninstaller "$INSTDIR\${UNINSTALLER}"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0

  WriteRegStr HKCU "${REG_KEY}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "${REG_KEY}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "${REG_KEY}" "Publisher" "${PUBLISHER}"
  WriteRegStr HKCU "${REG_KEY}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
  WriteRegStr HKCU "${REG_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${REG_KEY}" "UninstallString" '"$INSTDIR\${UNINSTALLER}"'
  WriteRegStr HKCU "${REG_KEY}" "QuietUninstallString" '"$INSTDIR\${UNINSTALLER}" /S'
  WriteRegStr HKCU "${REG_KEY}" "URLInfoAbout" "${URL}"
  WriteRegStr HKCU "${REG_KEY}" "HelpLink" "${HELP_URL}"
  WriteRegDWORD HKCU "${REG_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${REG_KEY}" "NoRepair" 1
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  WriteRegDWORD HKCU "${REG_KEY}" "EstimatedSize" $0
SectionEnd

Section "Uninstall"
  SetShellVarContext current
  Delete "$SMPROGRAMS\${APP_NAME}.lnk"
  ; Generated list: exactly the installed files, then their directories when empty.
  ; User data lives in %APPDATA%\FlatCAM (or in config\ when portable mode was enabled) and is kept.
  !include "${UNINSTALL_LIST}"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "${REG_KEY}"
SectionEnd
