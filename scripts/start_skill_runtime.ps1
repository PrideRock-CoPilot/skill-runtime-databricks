param(
    [switch]$InstallDependencies
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvDir = Join-Path $repoRoot ".runtime\.venv"
$pythonExe = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "Creating runtime virtual environment..."
    python -m venv $venvDir
}

if ($InstallDependencies) {
    Write-Host "Installing backend dependencies..."
    & $pythonExe -m pip install --upgrade pip
    & $pythonExe -m pip install -r (Join-Path $repoRoot "runtime\api\requirements.txt")

    Write-Host "Installing frontend dependencies..."
    Push-Location (Join-Path $repoRoot "runtime\web")
    npm install
    Pop-Location
}

Write-Host "Compiling skill runtime tables..."
& $pythonExe (Join-Path $repoRoot "scripts\compile_skill_runtime.py")

$apiCommand = "Set-Location '$repoRoot'; & '$pythonExe' -m uvicorn runtime.api.app.main:app --reload --app-dir ."
$webCommand = "Set-Location '$repoRoot\runtime\web'; npm run dev"

Write-Host "Starting API window..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", $apiCommand | Out-Null

Write-Host "Starting web window..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", $webCommand | Out-Null

Write-Host "Skill runtime started."
Write-Host "API: http://localhost:8000"
Write-Host "Web: http://localhost:5173"
Write-Host "MCP (stdio command): $pythonExe -m runtime.api.app.mcp_server"
