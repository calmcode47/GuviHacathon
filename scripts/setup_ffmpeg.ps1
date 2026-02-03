# PowerShell script to install FFmpeg on Windows development machines

Write-Host "Checking for FFmpeg installation..." -ForegroundColor Cyan

# Check if FFmpeg is already installed
$ffmpegPath = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($ffmpegPath) {
    Write-Host "FFmpeg is already installed:" -ForegroundColor Green
    ffmpeg -version | Select-Object -First 1
    exit 0
}

Write-Host "FFmpeg not found. Attempting to install..." -ForegroundColor Yellow

# Check for Chocolatey
if (Get-Command choco -ErrorAction SilentlyContinue) {
    Write-Host "Installing FFmpeg via Chocolatey..." -ForegroundColor Cyan
    choco install ffmpeg -y
    if ($LASTEXITCODE -eq 0) {
        Write-Host "FFmpeg successfully installed via Chocolatey" -ForegroundColor Green
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        exit 0
    }
}

# Check for winget
if (Get-Command winget -ErrorAction SilentlyContinue) {
    Write-Host "Installing FFmpeg via winget..." -ForegroundColor Cyan
    winget install --id=Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -eq 0) {
        Write-Host "FFmpeg successfully installed via winget" -ForegroundColor Green
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        exit 0
    }
}

# Manual installation instructions
Write-Host "`nAutomatic installation failed. Please install FFmpeg manually:" -ForegroundColor Yellow
Write-Host "1. Download from https://ffmpeg.org/download.html" -ForegroundColor White
Write-Host "2. Extract to a folder (e.g., C:\ffmpeg)" -ForegroundColor White
Write-Host "3. Add the bin folder to your PATH environment variable" -ForegroundColor White
Write-Host "4. Restart your terminal/PowerShell" -ForegroundColor White
Write-Host "`nOr install Chocolatey first: https://chocolatey.org/install" -ForegroundColor Cyan

exit 1
