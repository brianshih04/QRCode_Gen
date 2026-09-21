$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot

python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --onefile --windowed --name WiFiQRCodeGenerator wifi_qr_generator.py

Write-Host ""
Write-Host "Build complete: $PSScriptRoot\dist\WiFiQRCodeGenerator.exe" -ForegroundColor Green
