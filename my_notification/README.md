# Installation
```powershell
& 'C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\makeappx.exe' pack /o /d my_identity_package /nv /p MyIdentityPackage.msix
& 'C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\SignTool.exe' sign /fd SHA256 /n "common name me" .\MyIdentityPackage.msix
Add-AppxPackage -Path '.\MyIdentityPackage.msix' -ExternalLocation 'C:\Users\pc\Documents\my_notification\dist\my_notification\'
pyinstaller.exe -y --clean --manifest .\my_notification.exe.manifest .\my_notification.py
```
# Uninstallation
`Get-AppxPackage`でpacakge_full_nameを確認
```powershell
Remove-AppxPackage -Package <pacakge_full_name>
```

# Run
```powershell
.\dist\my_notification\my_notification.exe .\notification_processor.py
```
