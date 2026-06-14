#!/usr/bin/env python3
"""Patch btc-rpc-explorer identifyMiner so the dev-fund output is never shown
as the block's miner payout.

Upstream picks the FIRST coinbase output with value > 0 as the "miner payout".
With the BLOZ Development & Growth Fund split, some miners place the fund output
before their own payout, so the explorer mislabels the fund address as the miner.

Fix: skip the dev-fund address and pick the LARGEST remaining coinbase output
(the miner always receives the majority: 80-90% vs the fund's 10-20%).

Run on the explorer host (mainnet). Idempotent.
"""
from __future__ import annotations

import shutil
import sys

UTILS = "/opt/btc-rpc-explorer-mainnet/app/utils.js"
DEV_FUND_ADDRESS = "bz1qmv7lyweytwy807f6yq78zfvhh5ye5y2y0x2gfl"

OLD = """	if (coinbaseTx.vout && coinbaseTx.vout.length > 0) {
		for (let i = 0; i < coinbaseTx.vout.length; i++) {
			const vout = coinbaseTx.vout[i];

			const voutValue = new Decimal(vout.value);
			if (voutValue > 0) {
				const address = getVoutAddress(vout);

				if (address) {
					return {
						name: address,
						type: "address-only",
						identifiedBy: "payout address " + address,
					};
				}
			}
		}
	}"""

NEW = """	if (coinbaseTx.vout && coinbaseTx.vout.length > 0) {
		// Block Zero: skip the Development & Growth Fund output and pick the
		// largest remaining coinbase output as the miner payout. The fund only
		// receives 10-20% of the subsidy, so the miner is always the largest.
		const BLOZ_DEV_FUND_ADDRESS = "bz1qmv7lyweytwy807f6yq78zfvhh5ye5y2y0x2gfl";
		let bestAddress = null;
		let bestValue = new Decimal(0);
		for (let i = 0; i < coinbaseTx.vout.length; i++) {
			const vout = coinbaseTx.vout[i];
			const voutValue = new Decimal(vout.value);
			const address = getVoutAddress(vout);
			if (!address || address == BLOZ_DEV_FUND_ADDRESS) {
				continue;
			}
			if (voutValue.greaterThan(bestValue)) {
				bestValue = voutValue;
				bestAddress = address;
			}
		}
		if (bestAddress) {
			return {
				name: bestAddress,
				type: "address-only",
				identifiedBy: "payout address " + bestAddress,
			};
		}
	}"""


def main() -> int:
    with open(UTILS, encoding="utf-8") as f:
        src = f.read()

    if "BLOZ_DEV_FUND_ADDRESS" in src:
        print("already patched")
        return 0
    if OLD not in src:
        print("ERROR: target block not found (explorer version changed?)", file=sys.stderr)
        return 1

    shutil.copy2(UTILS, UTILS + ".bak")
    src = src.replace(OLD, NEW, 1)
    with open(UTILS, "w", encoding="utf-8") as f:
        f.write(src)
    print("patched OK (backup at %s.bak)" % UTILS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
