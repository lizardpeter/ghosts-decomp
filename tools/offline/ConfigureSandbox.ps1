param([Parameter(Mandatory=$true)][string]$GameDirectory)
$ErrorActionPreference = 'Stop'
$game = (Resolve-Path -LiteralPath $GameDirectory).Path
$bundle = $PSScriptRoot
if (!(Test-Path -LiteralPath (Join-Path $game 'iw6mp64_MSStore_ship.exe'))) { throw 'Select the original game directory.' }
function Escape([string]$text) { [System.Security.SecurityElement]::Escape($text) }
$xml = @"
<Configuration>
  <Networking>Disable</Networking>
  <MappedFolders>
    <MappedFolder><HostFolder>$(Escape $game)</HostFolder><SandboxFolder>C:\GhostsGame</SandboxFolder><ReadOnly>true</ReadOnly></MappedFolder>
    <MappedFolder><HostFolder>$(Escape $bundle)</HostFolder><SandboxFolder>C:\GhostsBundle</SandboxFolder><ReadOnly>true</ReadOnly></MappedFolder>
  </MappedFolders>
  <LogonCommand><Command>powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\GhostsBundle\LaunchSandbox.ps1</Command></LogonCommand>
</Configuration>
"@
$destination = Join-Path $bundle 'Offline.wsb'
[System.IO.File]::WriteAllText($destination, $xml)
Write-Output "Created $destination. Open it on a Windows host with Windows Sandbox enabled."
