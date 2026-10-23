# Run only by Offline.wsb. A second check refuses launch with any active adapter.
$ErrorActionPreference = 'Stop'
try {
    if (@(Get-NetAdapter -IncludeHidden -ErrorAction Stop | Where-Object { $_.Status -eq 'Up' }).Count -ne 0) {
        throw 'An active network adapter is present; refusing to launch.'
    }
    $manifest = Get-Content -Raw -LiteralPath 'C:\GhostsBundle\manifest.json' | ConvertFrom-Json
    foreach ($item in @(@('iw6mp64_offline.exe', $manifest.exe_sha256), @('recon.dll', $manifest.dll_sha256))) {
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path 'C:\GhostsBundle' $item[0])).Hash
        if ($hash -ne $item[1]) { throw "Package hash mismatch: $($item[0])" }
    }
    New-Item -ItemType Directory -Force -Path 'C:\GhostsData' | Out-Null
    # The package is read-only. Game assets and auxiliary DLLs resolve from the original directory.
    $process = Start-Process -FilePath 'C:\GhostsBundle\iw6mp64_offline.exe' -WorkingDirectory 'C:\GhostsGame' -ArgumentList '+set fs_basepath C:\GhostsGame +set fs_homepath C:\GhostsData' -PassThru -Wait
    Write-Host "Game exit code: $($process.ExitCode)"
} catch {
    Write-Host $_ -ForegroundColor Red
}
Read-Host 'Press Enter to close'
