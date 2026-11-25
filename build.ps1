# สร้าง dist\PimPid.exe (ไฟล์เดียว ใช้ติดตั้งบนเครื่องอื่นได้เลย ไม่ต้องมี Python)
# รัน:  powershell -ExecutionPolicy Bypass -File build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m pip install --quiet pyinstaller pystray pillow

$version = (python -c "from version import VERSION; print(VERSION)").Trim()
$v = ($version.Split(".") + @("0", "0", "0"))[0..3] -join ", "
New-Item -ItemType Directory -Force build | Out-Null
python icon.py build\pimpid.ico

@"
VSVersionInfo(
  ffi=FixedFileInfo(filevers=($v), prodvers=($v)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'PimPid'),
      StringStruct('FileDescription', 'PimPid - Thai/English wrong-layout typing checker'),
      StringStruct('FileVersion', '$version'),
      StringStruct('ProductName', 'PimPid'),
      StringStruct('ProductVersion', '$version'),
      StringStruct('OriginalFilename', 'PimPid.exe')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"@ | Set-Content -Encoding utf8 build\version_info.txt

$b = Join-Path $PSScriptRoot "build"
python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name PimPid `
    --icon "$b\pimpid.ico" `
    --version-file "$b\version_info.txt" `
    --hidden-import pystray._win32 `
    --workpath "$b\pyi" --specpath $b `
    app.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

Write-Host ""
Write-Host "Built: $PSScriptRoot\dist\PimPid.exe  (v$version)"
