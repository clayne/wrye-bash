; install.nsi
; Installation script for Wrye Bash NSIS installer.

;-------------------------------- The Installation Sections:

    Section "Wrye Bash" Main
        SectionIn RO

        ${If} $CheckState_OB == ${BST_CHECKED}
            ; Install resources:
            ${If} $Path_OB != $Empty
                !insertmacro InstallBashFiles "$Path_OB" "Oblivion Path"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Nehrim == ${BST_CHECKED}
            ; Install resources:
            ${If} $Path_Nehrim != $Empty
                !insertmacro InstallBashFiles "$Path_Nehrim" "Nehrim Path"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Skyrim == ${BST_CHECKED}
            ; Install resources:
            ${If} $Path_Skyrim != $Empty
                !insertmacro InstallBashFiles "$Path_Skyrim" "Skyrim Path"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Fallout4 == ${BST_CHECKED}
            ; Install resources:
            ${If} $Path_Fallout4 != $Empty
                !insertmacro InstallBashFiles "$Path_Fallout4" "Fallout4 Path"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Fallout4VR == ${BST_CHECKED}
            ; Install resources:
            ${If} $Path_Fallout4VR != $Empty
                !insertmacro InstallBashFiles "$Path_Fallout4VR" "Fallout4VR Path"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_SkyrimSE == ${BST_CHECKED}
            ; Install resources:
            ${If} $Path_SkyrimSE != $Empty
                !insertmacro InstallBashFiles "$Path_SkyrimSE" "SkyrimSE Path"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_SkyrimSE_GOG == ${BST_CHECKED}
            ; Install resources:
            ${If} $Path_SkyrimSE_GOG != $Empty
                !insertmacro InstallBashFiles "$Path_SkyrimSE_GOG" "SkyrimSE_GOG Path"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_SkyrimVR == ${BST_CHECKED}
            ; Install resources:
            ${If} $Path_SkyrimVR != $Empty
                !insertmacro InstallBashFiles "$Path_SkyrimVR" "SkyrimVR Path"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Fallout3 == ${BST_CHECKED}
            ; Install resources:
            ${If} $Path_Fallout3 != $Empty
                !insertmacro InstallBashFiles "$Path_Fallout3" "Fallout3 Path"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_FalloutNV == ${BST_CHECKED}
            ; Install resources:
            ${If} $Path_FalloutNV != $Empty
                !insertmacro InstallBashFiles "$Path_FalloutNV" "FalloutNV Path"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Enderal == ${BST_CHECKED}
            ; Install resources:
            ${If} $Path_Enderal != $Empty
                !insertmacro InstallBashFiles "$Path_Enderal" "Enderal Path"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_EnderalSE == ${BST_CHECKED}
            ; Install resources:
            ${If} $Path_EnderalSE != $Empty
                !insertmacro InstallBashFiles "$Path_EnderalSE" "EnderalSE Path"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Ex1 == ${BST_CHECKED}
            ; Install resources:
            ${If} $Path_Ex1 != $Empty
                !insertmacro InstallBashFiles "$Path_Ex1" "Extra Path 1"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Ex2 == ${BST_CHECKED}
            ; Install resources:
            ${If} $Path_Ex2 != $Empty
                !insertmacro InstallBashFiles "$Path_Ex2" "Extra Path 2"
            ${EndIf}
        ${EndIf}

        ; Write the uninstall keys for Windows
        SetOutPath "$COMMONFILES\Wrye Bash"
        WriteRegStr HKLM "SOFTWARE\Wrye Bash" "Installer Path" "$EXEPATH"
        WriteRegStr HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Wrye Bash" "DisplayName" "Wrye Bash"
        WriteRegStr HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Wrye Bash" "UninstallString" '"$COMMONFILES\Wrye Bash\uninstall.exe"'
        WriteRegStr HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Wrye Bash" "URLInfoAbout" 'https://www.github.com/wrye-bash/wrye-bash'
        WriteRegStr HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Wrye Bash" "HelpLink" 'https://www.afkmods.com/index.php?/topic/4966-wrye-bash-all-games/'
        WriteRegStr HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Wrye Bash" "Publisher" 'Wrye & Wrye Bash Development Team'
        WriteRegStr HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Wrye Bash" "DisplayVersion" '${WB_FILEVERSION}'
        WriteRegDWORD HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Wrye Bash" "NoModify" 1
        WriteRegDWORD HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Wrye Bash" "NoRepair" 1
        CreateDirectory "$COMMONFILES\Wrye Bash"
        WriteUninstaller "$COMMONFILES\Wrye Bash\uninstall.exe"
    SectionEnd

    Section "Start Menu Shortcuts" Shortcuts_SM
        CreateDirectory "$SMPROGRAMS\Wrye Bash"
        CreateShortCut "$SMPROGRAMS\Wrye Bash\Uninstall.lnk" "$COMMONFILES\Wrye Bash\uninstall.exe" "" "$COMMONFILES\Wrye Bash\uninstall.exe" 0
        ; Since 310, debug mode has been removed, so delete the debug shortcuts
        Delete "$SMPROGRAMS\Wrye Bash\*(Debug Log).lnk"

        ${If} $CheckState_OB == ${BST_CHECKED}
            ${If} $Path_OB != $Empty
                SetOutPath $Path_OB\Mopy
                CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Oblivion.lnk" "$Path_OB\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Nehrim == ${BST_CHECKED}
            ${If} $Path_Nehrim != $Empty
                SetOutPath $Path_Nehrim\Mopy
                CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Nehrim.lnk" "$Path_Nehrim\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Skyrim == ${BST_CHECKED}
            ${If} $Path_Skyrim != $Empty
                SetOutPath $Path_Skyrim\Mopy
                CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Skyrim.lnk" "$Path_Skyrim\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Fallout4 == ${BST_CHECKED}
            ${If} $Path_Fallout4 != $Empty
                SetOutPath $Path_Fallout4\Mopy
                CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Fallout4.lnk" "$Path_Fallout4\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Fallout4VR == ${BST_CHECKED}
            ${If} $Path_Fallout4VR != $Empty
                SetOutPath $Path_Fallout4VR\Mopy
                CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Fallout4VR.lnk" "$Path_Fallout4VR\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_SkyrimSE == ${BST_CHECKED}
            ${If} $Path_SkyrimSE != $Empty
                SetOutPath $Path_SkyrimSE\Mopy
                CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - SkyrimSE.lnk" "$Path_SkyrimSE\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_SkyrimSE_GOG == ${BST_CHECKED}
            ${If} $Path_SkyrimSE_GOG != $Empty
                SetOutPath $Path_SkyrimSE_GOG\Mopy
                CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - SkyrimSE (GOG).lnk" "$Path_SkyrimSE_GOG\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_SkyrimVR == ${BST_CHECKED}
            ${If} $Path_SkyrimVR != $Empty
                SetOutPath $Path_SkyrimVR\Mopy
                CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - SkyrimVR.lnk" "$Path_SkyrimVR\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Fallout3 == ${BST_CHECKED}
            ${If} $Path_Fallout3 != $Empty
                SetOutPath $Path_Fallout3\Mopy
                CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Fallout3.lnk" "$Path_Fallout3\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_FalloutNV == ${BST_CHECKED}
            ${If} $Path_FalloutNV != $Empty
                SetOutPath $Path_FalloutNV\Mopy
                CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - FalloutNV.lnk" "$Path_FalloutNV\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Enderal == ${BST_CHECKED}
            ${If} $Path_Enderal != $Empty
                SetOutPath $Path_Enderal\Mopy
                CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Enderal.lnk" "$Path_Enderal\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_EnderalSE == ${BST_CHECKED}
            ${If} $Path_EnderalSE != $Empty
                SetOutPath $Path_EnderalSE\Mopy
                CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - EnderalSE.lnk" "$Path_EnderalSE\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Ex1 == ${BST_CHECKED}
            ${If} $Path_Ex1 != $Empty
                SetOutPath $Path_Ex1\Mopy
                CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Extra 1.lnk" "$Path_Ex1\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}

        ${If} $CheckState_Ex2 == ${BST_CHECKED}
            ${If} $Path_Ex2 != $Empty
                SetOutPath $Path_Ex2\Mopy
                CreateShortCut "$SMPROGRAMS\Wrye Bash\Wrye Bash - Extra 2.lnk" "$Path_Ex2\Mopy\Wrye Bash.exe"
            ${EndIf}
        ${EndIf}
    SectionEnd
