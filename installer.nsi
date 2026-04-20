!define APP_NAME "JuzzyAI"
!define APP_VERSION "1.0.2"
!define APP_EXE "juzzyai.exe"
!define PUBLISHER "Zhussup"
!define REGKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\JuzzyAI"

!include "MUI2.nsh"
!include "WinMessages.nsh"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "JuzzyAI-Setup.exe"
InstallDir "$PROGRAMFILES64\JuzzyAI"
InstallDirRegKey HKLM "${REGKEY}" "InstallLocation"
RequestExecutionLevel admin
Unicode True

; MUI Settings
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE "Welcome to JuzzyAI Setup"
!define MUI_WELCOMEPAGE_TEXT "AI-powered coding assistant for your terminal.$\r$\n$\r$\nAfter installation, run from any terminal:$\r$\n  juzzyai"
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch JuzzyAI now"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; ── INSTALL ──────────────────────────────────────────────────────────────────

Section "Install"
    SetOutPath "$INSTDIR"
    File "dist\${APP_EXE}"

    ; Add to system PATH
    ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path"
    WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path" "$0;$INSTDIR"

    ; Notify system - PATH applies without reboot
    SendMessage ${HWND_BROADCAST} ${WM_WININICHANGE} 0 "STR:Environment" /TIMEOUT=1000

    ; Shortcuts
    CreateShortcut "$DESKTOP\JuzzyAI.lnk" "$INSTDIR\${APP_EXE}"
    CreateDirectory "$SMPROGRAMS\JuzzyAI"
    CreateShortcut "$SMPROGRAMS\JuzzyAI\JuzzyAI.lnk" "$INSTDIR\${APP_EXE}"
    CreateShortcut "$SMPROGRAMS\JuzzyAI\Uninstall JuzzyAI.lnk" "$INSTDIR\Uninstall.exe"

    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Registry for "Programs and Features"
    WriteRegStr   HKLM "${REGKEY}" "DisplayName"     "${APP_NAME}"
    WriteRegStr   HKLM "${REGKEY}" "UninstallString"  "$INSTDIR\Uninstall.exe"
    WriteRegStr   HKLM "${REGKEY}" "InstallLocation"  "$INSTDIR"
    WriteRegStr   HKLM "${REGKEY}" "DisplayVersion"   "${APP_VERSION}"
    WriteRegStr   HKLM "${REGKEY}" "Publisher"        "${PUBLISHER}"
    WriteRegStr   HKLM "${REGKEY}" "DisplayIcon"      "$INSTDIR\${APP_EXE}"
    WriteRegDWORD HKLM "${REGKEY}" "NoModify"         1
    WriteRegDWORD HKLM "${REGKEY}" "NoRepair"         1
SectionEnd

; ── UNINSTALL ────────────────────────────────────────────────────────────────

Section "Uninstall"
    Delete "$INSTDIR\${APP_EXE}"
    Delete "$INSTDIR\Uninstall.exe"
    Delete "$DESKTOP\JuzzyAI.lnk"
    Delete "$SMPROGRAMS\JuzzyAI\JuzzyAI.lnk"
    Delete "$SMPROGRAMS\JuzzyAI\Uninstall JuzzyAI.lnk"
    RMDir  "$SMPROGRAMS\JuzzyAI"
    RMDir /r "$INSTDIR"

    ; Remove INSTDIR from PATH
    ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path"
    Push "$0"
    Push ";$INSTDIR"
    Push ""
    Call un.StrRep
    Pop $1
    WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path" "$1"

    SendMessage ${HWND_BROADCAST} ${WM_WININICHANGE} 0 "STR:Environment" /TIMEOUT=1000

    DeleteRegKey HKLM "${REGKEY}"
SectionEnd

; ── Helper: StrRep (uninstall only) ──────────────────────────────────────────
Function un.StrRep
    ; Stack: string, old, new  →  result
    Exch $R0   ; new
    Exch
    Exch $R1   ; old
    Exch 2
    Exch $R2   ; string
    Push $R3
    Push $R4
    Push $R5
    Push $R6
    StrLen $R3 $R1
    StrCpy $R4 ""
    loop:
        StrLen $R5 $R2
        IntCmp $R5 0 done
        StrCpy $R6 $R2 $R3
        StrCmp $R6 $R1 replace
        StrCpy $R6 $R2 1
        StrCpy $R4 "$R4$R6"
        StrCpy $R2 $R2 "" 1
        Goto loop
    replace:
        StrCpy $R4 "$R4$R0"
        StrCpy $R2 $R2 "" $R3
        Goto loop
    done:
        StrCpy $R0 $R4
    Pop $R6
    Pop $R5
    Pop $R4
    Pop $R3
    Exch $R2
    Exch 2
    Exch $R1
    Exch
    Exch $R0
FunctionEnd
