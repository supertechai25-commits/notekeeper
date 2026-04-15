# sync_to_drive.ps1 - copies NoteKeeper APK + source to Google Drive
$src  = "C:\Users\Super\.ollama\notekeeper"
$dest = "G:\My Drive\NoteKeeper"

New-Item -ItemType Directory -Force -Path $dest | Out-Null

$apks = Get-ChildItem "$src\bin\*.apk" -ErrorAction SilentlyContinue
if ($apks) {
    foreach ($apk in $apks) {
        Copy-Item $apk.FullName -Destination $dest -Force
        Write-Host "Copied APK: $($apk.Name)"
    }
} else {
    Write-Host "No APK in bin\ yet - run again after build finishes."
}

$files = @("main.py","keep_app.py","buildozer.spec","BUILD_APK.md")
foreach ($f in $files) {
    if (Test-Path "$src\$f") {
        Copy-Item "$src\$f" -Destination $dest -Force
        Write-Host "Copied: $f"
    }
}

Write-Host "Done. Files are in: $dest"
