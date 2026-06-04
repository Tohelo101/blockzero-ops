# Official Block Zero testnet chain identity (v2).
# Update $OfficialGenesis after mining the testnet genesis - see blockzero-docs/testnet-reset.md

$OfficialGenesis = "7462293eec16a92c54a74362af6825688135e2955250024dcc3668ff4f55cfce"

$OfficialGenesisMessage = "The Times 04/Jun/2026 Block Zero - a second chance at Genesis"
$OfficialGenesisTime = 1780531200   # 2026-06-04T00:00:00Z

# Block 1 is not fixed - it is mined after genesis on the public network.
# Scripts only verify genesis hash, not block 1.
