# Backward-compatible wrapper — binaries are the same for mainnet and testnet.
# Prefer: ..\mainnet\install-windows.ps1
& (Join-Path $PSScriptRoot "..\mainnet\install-windows.ps1") @args
