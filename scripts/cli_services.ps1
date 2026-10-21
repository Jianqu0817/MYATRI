# Only the current checkout's older CLI launchers/runtimes may be replaced.
function Get-MyatriCliTargets {
    param([object[]]$Processes, [string]$ProjectDir, [int]$CurrentProcessId, [datetime]$StartedBefore)
    $root = [IO.Path]::GetFullPath($ProjectDir).Replace('/', '\').TrimEnd('\')
    $python = $root + '\.venv\Scripts\python.exe'
    $entries = @($root + '\scripts\start_myatri.py', $root + '\scripts\start_myatri.ps1')
    $byId = @{}; $ancestors = @{}
    foreach ($item in $Processes) { $byId[[int]$item.ProcessId] = $item }
    $cursor = $CurrentProcessId
    while ($byId.ContainsKey($cursor) -and -not $ancestors.ContainsKey($cursor)) {
        $ancestors[$cursor] = $true
        $cursor = [int]$byId[$cursor].ParentProcessId
    }
    foreach ($item in $Processes) {
        if (-not $item.ExecutablePath -or -not $item.CommandLine -or -not $item.CreationDate) { continue }
        if ($ancestors.ContainsKey([int]$item.ProcessId) -or [datetime]$item.CreationDate -ge $StartedBefore) { continue }
        $exe = $item.ExecutablePath.Replace('/', '\')
        $parent = $byId[[int]$item.ParentProcessId]
        $parentExe = if ($parent -and $parent.ExecutablePath) { $parent.ExecutablePath.Replace('/', '\') } else { '' }
        $tokens = @([regex]::Matches($item.CommandLine.Replace('/', '\'), '"[^"\r\n]*"|[^\s]+') | ForEach-Object { $_.Value.Trim('"') })
        $index = 1
        while ($index -lt $tokens.Count -and $tokens[$index] -in @('-u','-B','-E','-s','-X','utf8')) { $index++ }
        $ownPython = ($exe -eq $python -or $parentExe -eq $python)
        $runtime = $ownPython -and $index+1 -lt $tokens.Count -and $tokens[$index] -eq '-m' -and $tokens[$index+1] -eq 'myatri.interfaces.cli' -and $tokens -contains 'companion'
        $launcher = ($ownPython -and $index -lt $tokens.Count -and $tokens[$index] -eq $entries[0])
        $psLauncher = $exe -match '\\(?:powershell|pwsh)\.exe$' -and $tokens -contains '-File' -and $tokens -contains $entries[1]
        if ($runtime -or $launcher -or $psLauncher) { $item }
    }
}

function Stop-MyatriPreviousCli {
    param([string]$ProjectDir, [datetime]$StartedBefore)
    $targets = @(Get-MyatriCliTargets -Processes @(Get-CimInstance Win32_Process) -ProjectDir $ProjectDir -CurrentProcessId $PID -StartedBefore $StartedBefore)
    foreach ($target in $targets) {
        $current = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $target.ProcessId) -ErrorAction SilentlyContinue
        if (-not $current) { continue }
        if ($current.CreationDate -ne $target.CreationDate -or $current.ExecutablePath -ne $target.ExecutablePath -or $current.CommandLine -ne $target.CommandLine) { throw 'CLI process identity changed; no replacement attempted.' }
        Write-Host ('Stopping previous CLI process ' + $target.ProcessId)
        & "$env:SystemRoot\System32\taskkill.exe" /PID $target.ProcessId /T /F | Out-Null
        if ($LASTEXITCODE -ne 0 -and (Get-CimInstance Win32_Process -Filter ('ProcessId=' + $target.ProcessId) -ErrorAction SilentlyContinue)) { throw 'Previous CLI could not be stopped.' }
    }
}
