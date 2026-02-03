param(
  [string]$ApiKey = "",
  [string]$Project = ""
)
$ErrorActionPreference = "Stop"
function Exec($cmd) {
  $p = Start-Process -FilePath "powershell" -ArgumentList "-NoProfile -Command $cmd" -Wait -PassThru
  if ($p.ExitCode -ne 0) { throw "Command failed: $cmd" }
}
if (-not (Get-Command railway -ErrorAction SilentlyContinue)) {
  Write-Host "Railway CLI not found"
  exit 1
}
if ($ApiKey -ne "") {
  Exec "railway login --token $ApiKey"
}
if ($Project -ne "") {
  Exec "railway link --project $Project"
} else {
  Exec "railway init --service api"
}
Exec "railway up"
Write-Host "Deployment triggered"
