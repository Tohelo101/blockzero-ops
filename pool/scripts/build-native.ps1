# Build native bz-pool-miner.exe (Windows, MSVC)
# Requires: Visual Studio 2022 Build Tools with C++ workload, CMake 3.20+, Git
param(
    [string]$BuildType = "Release",
    [string]$BuildDir = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not $BuildDir) { $BuildDir = Join-Path $Root "build\native" }

Write-Host "Building bz-pool-miner ($BuildType)"
Write-Host "Source: $Root\native"

$cmake = Get-Command cmake -ErrorAction SilentlyContinue
if (-not $cmake) { throw "cmake not found. Install CMake and add to PATH." }

New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
Push-Location $BuildDir
try {
    # Use Ninja (the MSVC env is already active via msvc-dev-cmd) instead of a
    # pinned "Visual Studio 17 2022" generator — the runner image's VS version
    # changes (now VS 18), and a hardcoded VS generator breaks on every bump.
    cmake -G Ninja -DCMAKE_BUILD_TYPE=$BuildType "$Root\native"
    cmake --build . --config $BuildType --target bz-pool-miner -j
    # Ninja (single-config) writes directly into $BuildDir; VS generators use a
    # per-config subdir. Accept either layout.
    $exe = @(
        (Join-Path $BuildDir "bz-pool-miner.exe"),
        (Join-Path $BuildDir "$BuildType\bz-pool-miner.exe"),
        (Join-Path $BuildDir "Release\bz-pool-miner.exe")
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $exe) { throw "Build failed: bz-pool-miner.exe not found" }
    $out = Join-Path $Root "bin\bz-pool-miner.exe"
    New-Item -ItemType Directory -Force -Path (Split-Path $out) | Out-Null
    Copy-Item -Force $exe $out
    . (Join-Path $Root "scripts\copy-openssl-runtime.ps1")
    Copy-OpenSslRuntime -DestDir (Split-Path $out)
    Write-Host "OK: $out"
} finally {
    Pop-Location
}
