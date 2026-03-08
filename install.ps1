# claude-guardian installer — pure stdlib, no venv needed

$ErrorActionPreference = "Stop"

$guardianDir = Join-Path $env:USERPROFILE ".claude\guardian"

Write-Host "Installing claude-guardian..." -ForegroundColor Cyan
Write-Host ""

# Create data directory
if (-not (Test-Path $guardianDir)) {
    New-Item -ItemType Directory -Path $guardianDir -Force | Out-Null
    Write-Host "  Created $guardianDir"
}

# Initialize state if not exists
$stateFile = Join-Path $guardianDir "state.json"
if (-not (Test-Path $stateFile)) {
    '{"session_count": 0, "phase": "OBSERVE", "last_analysis_ts": 0, "project_sessions": {}}' | Out-File -FilePath $stateFile -Encoding UTF8
    Write-Host "  Created $stateFile"
}

Write-Host ""
Write-Host "Done! claude-guardian is ready." -ForegroundColor Green
Write-Host ""
Write-Host "Phases:"
Write-Host "  Sessions 1-5:   OBSERVE  - learns your patterns silently"
Write-Host "  Sessions 6-10:  SUGGEST  - warns about violations"
Write-Host "  Sessions 11+:   ENFORCE  - blocks violations"
Write-Host ""
Write-Host "Data stored at: $guardianDir\"
Write-Host "Add a .guardianignore file to skip enforcement on specific files."
