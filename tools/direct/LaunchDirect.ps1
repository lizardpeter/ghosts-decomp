[CmdletBinding(DefaultParameterSetName='Connect')]
param(
    [Parameter(Mandatory=$true)][string]$GameDirectory,
    [Parameter(Mandatory=$true,ParameterSetName='Connect')][string]$Connect,
    [Parameter(Mandatory=$true,ParameterSetName='Host')][string]$HostEndpoint,
    [Parameter(Mandatory=$true,ParameterSetName='Host')][ValidatePattern('^[A-Za-z0-9_]{3,63}$')][string]$Map,
    [Parameter(ParameterSetName='Host')][ValidatePattern('^[A-Za-z0-9_]{1,31}$')][string]$GameType = 'war',
    [Alias('Profile')][ValidatePattern('^[A-Za-z0-9_-]{1,32}$')][string]$ProfileName = 'default',
    [ValidatePattern('^[A-Za-z0-9_\-](?:[A-Za-z0-9_ \-]{0,29}[A-Za-z0-9_\-])?$')][string]$PlayerName
)
$ErrorActionPreference = 'Stop'
$endpoint = if ($PSCmdlet.ParameterSetName -eq 'Host') { $HostEndpoint } else { $Connect }
if ($endpoint -notmatch '^([0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]{1,5}$') { throw 'Use numeric IPv4:port.' }
$parts = $endpoint.Split(':')
$octets = $parts[0].Split('.') | ForEach-Object { [int]$_ }
$wildcard = $PSCmdlet.ParameterSetName -eq 'Host' -and (($octets | Where-Object { $_ -ne 0 }).Count -eq 0)
if (($octets | Where-Object { $_ -gt 255 }).Count -or (!$wildcard -and ($octets[0] -eq 0 -or $octets[0] -ge 224)) -or [int]$parts[1] -lt 1 -or [int]$parts[1] -gt 65535) { throw 'Invalid endpoint.' }
$game = (Resolve-Path -LiteralPath $GameDirectory).Path
$manifest = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'manifest.json') | ConvertFrom-Json
if ($manifest.mode -ne 'direct') { throw 'This is not a direct-mode package.' }
foreach ($item in @(@('iw6mp64_offline.exe',$manifest.exe_sha256),@('recon.dll',$manifest.dll_sha256))) {
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $PSScriptRoot $item[0])).Hash
    if ($hash -ne $item[1]) { throw "Package hash mismatch: $($item[0])" }
}
$data = Join-Path (Join-Path $env:LOCALAPPDATA 'GhostsDirect') $ProfileName
New-Item -ItemType Directory -Force -Path $data | Out-Null
$profilePath = Join-Path $data 'player.json'
if (Test-Path -LiteralPath $profilePath) {
    $playerRecord = Get-Content -Raw -LiteralPath $profilePath | ConvertFrom-Json
    if ($playerRecord.id -isnot [string] -or $playerRecord.name -isnot [string] -or $playerRecord.format -ne 1 -or $playerRecord.id -notmatch '^[0-9a-fA-F]{16}$' -or $playerRecord.id -eq '0000000000000000' -or $playerRecord.name -notmatch '^[A-Za-z0-9_\-](?:[A-Za-z0-9_ \-]{0,29}[A-Za-z0-9_\-])?$') { throw 'Invalid local player profile.' }
} else {
    $bytes = New-Object byte[] 8
    $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { do { $random.GetBytes($bytes); $id = -join ($bytes | ForEach-Object { $_.ToString('x2') }) } while ($id -eq '0000000000000000') } finally { $random.Dispose() }
    $playerRecord = [pscustomobject]@{ format = 1; id = $id; name = 'LocalPlayer' }
}
if ($PlayerName) { $playerRecord.name = $PlayerName }
$temporaryProfile = $profilePath + '.tmp'
[System.IO.File]::WriteAllText($temporaryProfile, ($playerRecord | ConvertTo-Json))
Move-Item -LiteralPath $temporaryProfile -Destination $profilePath -Force
# The ID is self-asserted custom-session identity, not an authenticated account.
if ($game.Contains('"') -or $data.Contains('"')) { throw 'Unsupported quote in path.' }
$arguments = '+set fs_basepath "' + $game + '" +set fs_homepath "' + $data + '" +direct_player ' + $playerRecord.id + ' "' + $playerRecord.name + '" '
if ($PSCmdlet.ParameterSetName -eq 'Host') { $arguments += '+direct_host ' + $endpoint + ' ' + $Map + ' ' + $GameType }
else { $arguments += '+connect ' + $endpoint }
Start-Process -FilePath (Join-Path $PSScriptRoot 'iw6mp64_offline.exe') -WorkingDirectory $game -ArgumentList $arguments -Wait
