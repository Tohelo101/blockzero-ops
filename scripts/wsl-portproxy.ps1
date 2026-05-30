# Block Zero: refresh the Windows->WSL port-proxy for the testnet P2P port (18210).
# WSL2 gets a new NAT IP on each boot, so the proxy must be re-pointed.
# Run as Administrator (e.g. from a scheduled task at logon/startup).

$distro = "Ubuntu-22.04"
$port = 18210

# Ensure WSL (and its systemd services, incl. the node) is started.
wsl -d $distro -- bash -lc "true" | Out-Null

# Get the current WSL eth0 IPv4 address.
$wslIp = (wsl -d $distro -- bash -lc "hostname -I" ).Trim().Split(" ")[0]
if (-not $wslIp) { Write-Error "Could not determine WSL IP"; exit 1 }

# Recreate the portproxy mapping.
netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 2>$null | Out-Null
netsh interface portproxy add v4tov4 listenport=$port listenaddress=0.0.0.0 connectport=$port connectaddress=$wslIp | Out-Null

Write-Host "Port-proxy set: 0.0.0.0:$port -> ${wslIp}:$port"
netsh interface portproxy show v4tov4
