# P0031: opt-in, bounded, read-only startup diagnostic on a REAL Windows PC.
# The only system change is an outbound firewall block for this custom EXE,
# always removed in finally. No Microsoft services are disabled or modified.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$GameDirectory,
    [string]$PackageDirectory = $PSScriptRoot,
    [string]$OutputDirectory,
    [ValidateRange(10,300)][int]$Seconds = 120,
    [switch]$Screenshot
)

$ErrorActionPreference = 'Stop'
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $PackageDirectory 'local-diagnostics' }
$game = (Resolve-Path -LiteralPath $GameDirectory).Path
$package = (Resolve-Path -LiteralPath $PackageDirectory).Path
$exe = (Resolve-Path -LiteralPath (Join-Path $package 'iw6mp64_offline.exe')).Path
$observer = (Resolve-Path -LiteralPath (Join-Path $package 'native_smoke.py')).Path
$manifest = Get-Content -Raw -LiteralPath (Join-Path $package 'manifest.json') | ConvertFrom-Json
if ($manifest.mode -ne 'direct' -or $manifest.build -ne 'iw6mp64_MSStore_ship') {
    throw 'Only the pinned custom Store multiplayer direct-mode package is supported.'
}
foreach ($name in @('iw6mp64_offline.exe','recon.dll')) {
    $expected = if ($name -eq 'recon.dll') { $manifest.dll_sha256 } else { $manifest.exe_sha256 }
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $package $name)).Hash
    if ($actual -ne $expected) { throw "Package integrity mismatch: $name" }
}
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this diagnostic from an elevated PowerShell terminal; it installs and removes a temporary executable-only outbound firewall rule.'
}
if ((Get-Service MpsSvc).Status -ne 'Running') { throw 'Windows Firewall service must be running.' }
foreach ($firewallProfile in Get-NetFirewallProfile -PolicyStore ActiveStore) {
    if (!$firewallProfile.Enabled) { throw 'Active firewall profiles must be enabled.' }
}
$python = Get-Command python -ErrorAction Stop
& $python.Source -c 'import sys; assert sys.version_info >= (3, 9) and sys.maxsize > 2**32'
if ($LASTEXITCODE -ne 0) { throw '64-bit Python 3.9+ is required.' }

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$out = (Resolve-Path -LiteralPath $OutputDirectory).Path
$profile = Join-Path $out 'profile'
New-Item -ItemType Directory -Force -Path $profile | Out-Null
# A complete, legitimately installed Ghosts game directory must provide
# original asset files and the original local game runtime dependencies.
# Never fetch/download or forge content. Never overwrite package DLLs.
$copied = [System.Collections.Generic.List[string]]::new()
$rule = 'Iw6LocalStartup-' + [guid]::NewGuid().ToString('N')
try {
    foreach ($name in @('amd_ags64.dll','bink2w64.dll')) {
        $source = Join-Path $game $name
        $destination = Join-Path $package $name
        if (!(Test-Path -LiteralPath $destination) -and (Test-Path -LiteralPath $source)) {
            Copy-Item -LiteralPath $source -Destination $destination
            $copied.Add($destination)
        }
    }
    New-NetFirewallRule -Name $rule -DisplayName $rule -Direction Outbound -Program $exe -Action Block -Profile Any | Out-Null
    $argsForObserver = @(
        $observer, '--exe', $exe, '--cwd', $game, '--firewall-rule', $rule,
        '--seconds', [string]$Seconds, '--output', (Join-Path $out 'game.json'),
        '--pending-zones', '--loader-flags'
    )
    if ($Screenshot) {
        # This captures the whole desktop. Opt-in only; review before sharing.
        $argsForObserver += @('--screenshot', (Join-Path $out 'desktop.png'))
    }
    $argsForObserver += @(
        '--', '+set', 'fs_basepath', $game, '+set', 'fs_homepath', $profile,
        '+set', 'logfile', '2', '+set', 'r_fullscreen', '0',
        '+direct_player', '0000000000000001', 'LocalProbe'
    )
    & $python.Source @argsForObserver | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Native process observation failed.' }
} finally {
    Remove-NetFirewallRule -Name $rule -ErrorAction SilentlyContinue
    foreach ($path in $copied) { Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue }
}

$result = Get-Content -Raw -LiteralPath (Join-Path $out 'game.json') | ConvertFrom-Json
$messages = @($result.events | Where-Object { $_.event -eq 8 -and $_.text -like 'IW6D:*' } | ForEach-Object { $_.text })
$lastState = @($result.loader_state) | Select-Object -Last 1
$modules = @($result.events | Where-Object { $_.event -eq 6 -and $_.path } |
    ForEach-Object { [System.IO.Path]::GetFileName($_.path).ToLowerInvariant() })
$forbidden = @('xgameruntime.dll','xcurl.dll','xboxliveapi.dll','xboxservices.dll','gamingservices.dll')
$unexpected = @($modules | Where-Object { $forbidden -contains $_ } | Select-Object -Unique)
$gpu = @(Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,Status)
$summary = [pscustomobject]@{
    completed = $true
    exit_code = $result.exit_code
    observation_seconds = $Seconds
    timed_out = $result.timed_out
    direct_milestones = $messages
    last_loader_state = $lastState
    requested_zone_names = $result.pending_zone_names
    unexpected_vendor_modules = $unexpected
    display_adapters = $gpu
    playable_game_verified = $false
    whole_process_egress_verified = $false
}
$summary | ConvertTo-Json -Depth 9 | Set-Content -LiteralPath (Join-Path $out 'summary.json')
$summary | Format-List | Out-Host
Write-Host "Private local diagnostic saved under: $out"
Write-Host 'Keep game.json and any optional desktop screenshot private until you review them.'
Write-Host 'Firewall rule removed. This is an offline startup diagnostic, not a playable join test.'
