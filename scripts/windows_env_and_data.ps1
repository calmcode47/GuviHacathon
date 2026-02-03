param(
  [string]$FfmpegBin = "",
  [string]$HfToken = "",
  [string]$PythonExe = ".venv\\Scripts\\python.exe",
  [string]$InputDir = "",
  [string]$Language = "",
  [string]$SpeakerId = "user",
  [int]$MaxPerLanguage = 60
)
if ($FfmpegBin -ne "") {
  $env:PATH = "$env:PATH;$FfmpegBin"
  $env:FFMPEG_BINARY = Join-Path $FfmpegBin "ffmpeg.exe"
  $env:FFPROBE_BINARY = Join-Path $FfmpegBin "ffprobe.exe"
}
if ($HfToken -ne "") {
  $env:HF_TOKEN = $HfToken
}
$repo = (Resolve-Path ".").Path
$py = if (Test-Path $PythonExe) { $PythonExe } else { "python" }
& $py "$repo\\dataset\\download_open_datasets.py" --base-dir "$repo\\data" --max-per-language $MaxPerLanguage
if ($InputDir -ne "") {
  $argsList = @("--input-dir", $InputDir, "--speaker-id", $SpeakerId, "--base-dir", "$repo\\data")
  if ($Language -ne "") { $argsList += @("--language", $Language) }
  & $py "$repo\\dataset\\normalize_human_samples.py" $argsList
}
