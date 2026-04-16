param(
    [switch]$InstallDependencies,
    [ValidateSet("stdio", "streamable-http")]
    [string]$Transport = "streamable-http",
    [int]$Port = 8001
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvDir = Join-Path $repoRoot ".runtime\.venv"
$pythonExe = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "Creating runtime virtual environment..."
    python -m venv $venvDir
}

if ($InstallDependencies) {
    Write-Host "Installing runtime dependencies..."
    & $pythonExe -m pip install --upgrade pip
    & $pythonExe -m pip install -r (Join-Path $repoRoot "runtime\api\requirements.txt")
}

Write-Host "Compiling skill runtime tables..."
& $pythonExe (Join-Path $repoRoot "scripts\compile_skill_runtime.py")

$mcpCommand = @(
    "`$env:SKILL_RUNTIME_MCP_TRANSPORT='$Transport'",
    "`$env:SKILL_RUNTIME_MCP_PORT='$Port'",
    "`$env:SKILL_RUNTIME_MCP_STATELESS='true'",
    "Set-Location '$repoRoot'",
    "& '$pythonExe' -m runtime.api.app.mcp_server"
) -join "; "

Write-Host "Starting Skill Runtime MCP server..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", $mcpCommand | Out-Null

if ($Transport -eq "streamable-http") {
    Write-Host "MCP endpoint: http://127.0.0.1:$Port/mcp"
} else {
    Write-Host "MCP stdio command: $pythonExe -m runtime.api.app.mcp_server"
}
