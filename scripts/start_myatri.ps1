param(
    [switch]$CheckOnly,
    [string]$Root = "var/myatri-main",
    [string]$Agent = "atri",
    [string]$PersonaFile = "",
    [string]$DisplayName = "",
    [ValidateSet("", "xiaowennuan")]
    [string]$Character = ""
)

$ErrorActionPreference = "Stop"
if ($Character -eq "xiaowennuan") {
    if (-not $PSBoundParameters.ContainsKey("Root")) { $Root = "var/xiaowennuan" }
    if (-not $PSBoundParameters.ContainsKey("Agent")) { $Agent = "atri" }
    if (-not $PSBoundParameters.ContainsKey("PersonaFile")) { $PersonaFile = "config/personas/xiaowennuan/persona.md" }
    if (-not $PSBoundParameters.ContainsKey("DisplayName")) {
        $DisplayName = -join @([char]0x5c0f, [char]0x6e29, [char]0x6696)
    }
}
$projectDir = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectDir
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding

try {
    $uvCommand = Get-Command uv -ErrorAction SilentlyContinue
    $uvPath = if ($uvCommand) { $uvCommand.Source } else { Join-Path $env:USERPROFILE ".local\bin\uv.exe" }
    if (-not (Test-Path -LiteralPath $uvPath -PathType Leaf)) {
        throw "uv was not found. Install uv, then open this launcher again."
    }
    Write-Host "[1/3] Checking the locked Python environment..."
    & $uvPath sync --frozen --extra neural
    if ($LASTEXITCODE -ne 0) { throw "Environment setup failed (exit $LASTEXITCODE)." }

    $pythonPath = Join-Path $projectDir ".venv\Scripts\python.exe"
    $launchArgs = @((Join-Path $PSScriptRoot "start_myatri.py"), "--root", $Root, "--agent", $Agent)
    if ($PersonaFile) { $launchArgs += @("--persona-file", $PersonaFile) }
    if ($DisplayName) { $launchArgs += @("--display-name", $DisplayName) }
    if ($CheckOnly) { $launchArgs += "--check-only" }
    & $pythonPath @launchArgs
    exit $LASTEXITCODE
}
catch {
    Write-Host ("MYATRI startup failed: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
