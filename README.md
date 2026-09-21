# Wi-Fi QR Code 產生器

Windows 桌面工具：輸入機台 Model Name 與 5 碼 SN，即時產生可供 iOS / Android 掃描的 Wi-Fi QR Code。

## 使用方式

1. 啟動 `WiFiQRCodeGenerator.exe`。
2. 輸入機台型號與 5 碼 SN。SSID 會直接組合為 `Model Name + SN`。
3. 預設密碼會自動隨機產生為 10 碼，也可以按「重新產生」或手動修改，但長度固定為 10 碼。
4. 用手機掃描右側 QR Code，或按「下載 PNG」保存圖片。

Wi-Fi QR payload 使用標準格式：`WIFI:T:WPA;S:<SSID>;P:<Password>;;`，並會自動處理 SSID / 密碼中的特殊字元。

## 建置 EXE

在 Windows PowerShell 執行：

```powershell
.\build_windows.ps1
```

完成後的檔案位於 `dist\WiFiQRCodeGenerator.exe`，可直接複製到其他 Windows 電腦執行。
