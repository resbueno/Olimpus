Dim sh, fso, root, ret
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)

' Roda o bat de setup completamente oculto e aguarda terminar
ret = sh.Run("cmd /c """ & root & "\iniciar.bat""", 0, True)

If ret <> 0 Then
    MsgBox "Olimpus encontrou um erro ao iniciar." & vbCrLf & _
           "Verifique o arquivo olimpus_erro.log na pasta do app.", _
           vbCritical, "Olimpus"
End If
