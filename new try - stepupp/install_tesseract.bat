@echo off
echo ========================================================
echo Installing Tesseract OCR for Student Marks Management...
echo ========================================================
echo.
if exist "%~dp0tesseract-installer.exe" (
    echo Launching Tesseract installer...
    echo Please follow the on-screen installer prompts and accept the Windows prompt.
    echo Default installation path: C:\Program Files\Tesseract-OCR
    start "" "%~dp0tesseract-installer.exe"
) else (
    echo Installing via Windows Package Manager (winget)...
    winget install UB-Mannheim.TesseractOCR --accept-source-agreements --accept-package-agreements
)
echo.
echo When the installation is finished, re-upload your marks sheet in the portal.
pause
