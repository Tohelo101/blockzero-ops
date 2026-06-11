# Download Block Zero Windows binaries (bitcoind, bitcoin-cli, bitcoin-qt).
# Used for MAINNET and pool mining. Testnet uses the same exes with -testnet.
#
# Usage:
#   .\install-windows.ps1
#   .\install-windows.ps1 -Force
#
# Then:
#   .\mine-mainnet.ps1 -Pool          # pool mine (recommended)
#   .\mine-mainnet.ps1                 # solo mine

param(
    [string]$Version = "latest",
    [string]$InstallDir = "$env:LOCALAPPDATA\BlockZero",
    [string]$Repo = "Rexemre/blockzero-core",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$BinDir = Join-Path $InstallDir "bin"
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

function Stop-BitcoindIfRunning {
    $procs = Get-Process bitcoind -ErrorAction SilentlyContinue
    if (-not $procs) { return }
    Write-Host "Stopping running bitcoind (required before updating binaries)..."
    $cli = Join-Path $BinDir "bitcoin-cli.exe"
    if (Test-Path $cli) {
        try { & $cli -datadir="$env:LOCALAPPDATA\BlockZeroMainnet" -rpcport=8332 stop 2>$null | Out-Null } catch {}
        try { & $cli -testnet -datadir="$InstallDir" -rpcport=18211 stop 2>$null | Out-Null } catch {}
        Start-Sleep -Seconds 5
    }
    Get-Process bitcoind -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Process bitcoind -ErrorAction SilentlyContinue) -and (Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 2
    }
}

function Get-ReleaseAssetUrl {
    param([string]$Ver)
    if ($Ver -eq "latest") {
        $rel = Invoke-RestMethod "https://api.github.com/repos/$Repo/releases/latest"
    } else {
        $rel = Invoke-RestMethod "https://api.github.com/repos/$Repo/releases/tags/$Ver"
    }
    $zips = $rel.assets | Where-Object { $_.name -match "windows-x64.*\.zip$" }
    $asset = ($zips | Where-Object { $_.name -notmatch "-cli\.zip$" } | Select-Object -First 1)
    if (-not $asset) { $asset = ($zips | Select-Object -First 1) }
    if (-not $asset) {
        throw "No windows-x64 release zip found in $Repo"
    }
    return @{ Url = $asset.browser_download_url; Name = $asset.name; Tag = $rel.tag_name }
}

Write-Host "Block Zero Windows installer"
Write-Host "Install dir: $BinDir"
Write-Host ""

if ((Test-Path (Join-Path $BinDir "bitcoind.exe")) -and (Test-Path (Join-Path $BinDir "bitcoin-cli.exe")) -and -not $Force) {
    Write-Host "Binaries already present."
    Write-Host "Use -Force to re-download."
} else {
    Stop-BitcoindIfRunning
    $info = Get-ReleaseAssetUrl -Ver $Version
    Write-Host "Downloading $($info.Name) ($($info.Tag))..."
    $zip = Join-Path $env:TEMP $info.Name
    Invoke-WebRequest -Uri $info.Url -OutFile $zip -UseBasicParsing
    Expand-Archive -Path $zip -DestinationPath $InstallDir -Force
    Remove-Item $zip -Force
    Get-ChildItem $InstallDir -Directory -Filter "blockzero-*-windows-x64*" | ForEach-Object {
        $srcBin = Join-Path $_.FullName "bin"
        if (Test-Path $srcBin) {
            Get-ChildItem $srcBin -Filter "*.exe" | ForEach-Object {
                Copy-Item $_.FullName $BinDir -Force
            }
        }
    }
    Write-Host "Installed to $BinDir"
}

Write-Host ""
Write-Host "Next steps (mainnet):"
Write-Host "  .\mine-mainnet.ps1 -Pool          # pool mine (recommended)"
Write-Host "  .\mine-mainnet.ps1 -Pool -Threads 4"
Write-Host "  .\mine-mainnet.ps1 -Status        # check wallet / node"
Write-Host ""
Write-Host "Testnet (optional): ..\testnet\mine-testnet.ps1"
Write-Host ""
