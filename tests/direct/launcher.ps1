# Windows CI: execute launcher/profile preparation with process launch intercepted.
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
# Verify the local real-GPU diagnostic parses under Windows PowerShell without
# requiring an elevated CI runner or invoking any firewall or game process.
$probePath = Join-Path $repoRoot 'tools/direct/ProbeStartup.ps1'
$probeTokens = $null
$probeErrors = $null
[System.Management.Automation.Language.Parser]::ParseFile(
    $probePath, [ref]$probeTokens, [ref]$probeErrors) | Out-Null
if ($probeErrors.Count) {
    throw ('Local startup diagnostic PowerShell syntax error: ' +
           ($probeErrors | ForEach-Object { $_.Message } | Out-String))
}
$taskRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('iw6-launcher-' + [guid]::NewGuid().ToString('N'))
$oldLocalAppData = $env:LOCALAPPDATA
$oldStartProcess = Get-Item Function:\Start-Process -ErrorAction SilentlyContinue
$global:Iw6TestLaunches = [System.Collections.Generic.List[object]]::new()
function global:Start-Process {
    param([string]$FilePath,[string]$WorkingDirectory,[string]$ArgumentList,[switch]$Wait)
    $global:Iw6TestLaunches.Add(@{ file=$FilePath; working=$WorkingDirectory; arguments=$ArgumentList; wait=$Wait.IsPresent })
}
try {
    $bundle = Join-Path $taskRoot 'bundle'
    $game = Join-Path $taskRoot 'game with spaces'
    $env:LOCALAPPDATA = Join-Path $taskRoot 'appdata'
    New-Item -ItemType Directory -Force -Path $bundle,$game,$env:LOCALAPPDATA | Out-Null
    $launcher = Join-Path $bundle 'LaunchDirect.ps1'
    Copy-Item -LiteralPath (Join-Path $repoRoot 'tools/direct/LaunchDirect.ps1') -Destination $launcher
    [System.IO.File]::WriteAllText((Join-Path $bundle 'iw6mp64_offline.exe'),'test-exe')
    [System.IO.File]::WriteAllText((Join-Path $bundle 'recon.dll'),'test-dll')
    $manifest = @{ mode='direct'; exe_sha256=(Get-FileHash (Join-Path $bundle 'iw6mp64_offline.exe')).Hash; dll_sha256=(Get-FileHash (Join-Path $bundle 'recon.dll')).Hash }
    [System.IO.File]::WriteAllText((Join-Path $bundle 'manifest.json'),($manifest | ConvertTo-Json))
    & $launcher -GameDirectory $game -Connect '127.0.0.1:27016' -Profile 'one' -PlayerName 'Test Player'
    $profilePath = Join-Path $env:LOCALAPPDATA 'GhostsDirect/one/player.json'
    $first = Get-Content -Raw -LiteralPath $profilePath | ConvertFrom-Json
    if ($first.format -ne 1 -or $first.id -notmatch '^[0-9a-f]{16}$' -or $first.name -ne 'Test Player') { throw 'Profile generation failed.' }
    if ($global:Iw6TestLaunches[0].arguments -notmatch ('\+direct_player ' + $first.id + ' "Test Player" \+connect 127\.0\.0\.1:27016$')) { throw 'Connect argument construction failed.' }
    & $launcher -GameDirectory $game -Connect '127.0.0.1:27016' -Profile 'one'
    $again = Get-Content -Raw -LiteralPath $profilePath | ConvertFrom-Json
    if ($again.id -ne $first.id) { throw 'Profile ID changed across launches.' }
    & $launcher -GameDirectory $game -HostEndpoint '0.0.0.0:27016' -Map 'mp_prison' -GameType 'war' -Profile 'two'
    if ($global:Iw6TestLaunches[2].arguments -notmatch '\+direct_host 0\.0\.0\.0:27016 mp_prison war$') { throw 'Host argument construction failed.' }
    $second = Get-Content -Raw -LiteralPath (Join-Path $env:LOCALAPPDATA 'GhostsDirect/two/player.json') | ConvertFrom-Json
    if ($second.id -eq $first.id) { throw 'Separate profiles reused an ID.' }
    $refused = $false
    try { & $launcher -GameDirectory $game -Connect '127.0.0.1:27016;quit' -Profile 'one' } catch { $refused = $true }
    if (!$refused -or $global:Iw6TestLaunches.Count -ne 3) { throw 'Invalid endpoint was launched.' }
    [System.IO.File]::WriteAllText((Join-Path $bundle 'recon.dll'),'tampered')
    $refused = $false
    try { & $launcher -GameDirectory $game -Connect '127.0.0.1:27016' -Profile 'one' } catch { $refused = $true }
    if (!$refused -or $global:Iw6TestLaunches.Count -ne 3) { throw 'Tampered package was launched.' }
    Write-Output 'PASS: Windows launcher profile persistence, separate profiles, host/connect arguments and refusal paths; game process was not executed'
} finally {
    $env:LOCALAPPDATA = $oldLocalAppData
    Remove-Item Function:\Start-Process -ErrorAction SilentlyContinue
    if ($oldStartProcess) { Set-Item Function:\global:Start-Process $oldStartProcess.ScriptBlock }
    Remove-Variable Iw6TestLaunches -Scope Global -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $taskRoot) { Remove-Item -LiteralPath $taskRoot -Recurse -Force }
}
