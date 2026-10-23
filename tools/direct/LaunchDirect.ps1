param(
    [Parameter(Mandatory=$true)][string]$GameDirectory,
    [Parameter(Mandatory=$true)][string]$Connect
)
$ErrorActionPreference = 'Stop'
# Pass a numeric endpoint as one engine argument. Never evaluate command text.
if ($Connect -notmatch '^([0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]{1,5}$') { throw 'Use connect IPv4:port.' }
$parts = $Connect.Split(':')
$octets = $parts[0].Split('.') | ForEach-Object { [int]$_ }
if (($octets | Where-Object { $_ -gt 255 }).Count -or $octets[0] -eq 0 -or $octets[0] -ge 224 -or [int]$parts[1] -lt 1 -or [int]$parts[1] -gt 65535) { throw 'Invalid server endpoint.' }
$game = (Resolve-Path -LiteralPath $GameDirectory).Path
$manifest = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'manifest.json') | ConvertFrom-Json
if ($manifest.mode -ne 'direct') { throw 'This is not a direct-mode package.' }
foreach ($item in @(@('iw6mp64_offline.exe',$manifest.exe_sha256),@('recon.dll',$manifest.dll_sha256))) {
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $PSScriptRoot $item[0])).Hash
    if ($hash -ne $item[1]) { throw "Package hash mismatch: $($item[0])" }
}
$data = Join-Path $env:LOCALAPPDATA 'GhostsDirect'
New-Item -ItemType Directory -Force -Path $data | Out-Null
# Numeric endpoint has no command separators; filesystem dvar arguments are quoted.
if ($game.Contains('"') -or $data.Contains('"')) { throw 'Unsupported quote in path.' }
$arguments = '+set fs_basepath "' + $game + '" +set fs_homepath "' + $data + '" +connect ' + $Connect
Start-Process -FilePath (Join-Path $PSScriptRoot 'iw6mp64_offline.exe') -WorkingDirectory $game -ArgumentList $arguments -Wait
