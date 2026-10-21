"""Process selection is tested with synthetic snapshots; no processes are stopped."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest


def test_only_verified_old_cli_processes_are_replaced(tmp_path):
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if not shell:
        pytest.skip("PowerShell unavailable")
    helper = Path(__file__).resolve().parents[1] / "scripts/cli_services.ps1"
    script = tmp_path / "select.ps1"
    script.write_text(r'''
. '__HELPER__'
$root = 'D:\fixture\MYATRI'
$old = [datetime]'2026-10-21T10:00:00'
$items = @(
 [pscustomobject]@{ProcessId=1; ParentProcessId=0; ExecutablePath='C:\Windows\pwsh.exe'; CommandLine='pwsh.exe'; CreationDate=$old},
 [pscustomobject]@{ProcessId=2; ParentProcessId=1; ExecutablePath=$root+'\.venv\Scripts\python.exe'; CommandLine='python.exe -m myatri.interfaces.cli --root var/xiaowennuan companion --mode live'; CreationDate=$old},
 [pscustomobject]@{ProcessId=3; ParentProcessId=1; ExecutablePath='D:\other\python.exe'; CommandLine='python.exe -m myatri.interfaces.cli companion'; CreationDate=$old},
 [pscustomobject]@{ProcessId=4; ParentProcessId=1; ExecutablePath=$root+'\.venv\Scripts\python.exe'; CommandLine='python.exe -m pytest tests'; CreationDate=$old},
 [pscustomobject]@{ProcessId=5; ParentProcessId=1; ExecutablePath=$root+'\.venv\Scripts\python.exe'; CommandLine='python.exe -m myatri.companion.monitor'; CreationDate=$old},
 [pscustomobject]@{ProcessId=6; ParentProcessId=1; ExecutablePath=$root+'\.venv\Scripts\python.exe'; CommandLine='python.exe -m myatri.interfaces.cli companion'; CreationDate=[datetime]'2026-10-23T10:00:00'}
)
@(Get-MyatriCliTargets -Processes $items -ProjectDir $root -CurrentProcessId 1 -StartedBefore ([datetime]'2026-10-22T10:00:00') | ForEach-Object { $_.ProcessId }) | ConvertTo-Json -Compress
'''.replace('__HELPER__', str(helper).replace("'", "''")), encoding="utf-8")
    result = subprocess.run([shell, "-NoProfile", "-File", str(script)], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == 2
