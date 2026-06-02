#!/usr/bin/env python3
"""Rebrand btc-rpc-explorer for the Block Zero testnet.

btc-rpc-explorer ships only Bitcoin coin configs and hardcodes "Bitcoin
Explorer" in a few view templates. This patches the in-place coin config and
views so the explorer shows "Block Zero" / "TBLOZ". Re-run after every
`git pull` of the explorer, then: systemctl restart blockzero-explorer
"""
import sys

BASE = "/opt/btc-rpc-explorer"

# file -> list of (old, new, max_count). max_count <= 0 means "replace all".
PATCHES = {
    f"{BASE}/app/coins/btc.js": [
        ('name:"Bitcoin",', 'name:"Block Zero",', 1),
        ('ticker:"BTC",', 'ticker:"TBLOZ",', 1),
        ('name:"BTC",', 'name:"TBLOZ",', 1),          # currencyUnits[0] native unit
        ('values:["", "btc", "BTC"]', 'values:["", "tbloz", "TBLOZ"]', 1),
        ('"BTC":currencyUnits[0]', '"TBLOZ":currencyUnits[0]', 1),
        ('"test":"Testnet Explorer",', '"test":"Block Zero Testnet Explorer",', 1),
    ],
    f"{BASE}/views/index.pug": [
        ('title Bitcoin Explorer', 'title Block Zero Testnet Explorer', 1),
        ('h5 Bitcoin Explorer', 'h5 Block Zero Testnet Explorer', 1),
        ('Made for Bitcoiners by Bitcoiners. Enjoy!',
         'A second chance at Genesis. CPU-mineable. Fair launch.', 1),
    ],
    f"{BASE}/views/layout.pug": [
        ('span.fw-light Bitcoin Explorer', 'span.fw-light Block Zero Explorer', 1),
        ('BitcoinExplorer.org - Open-Source Bitcoin Explorer',
         'Block Zero Testnet Explorer', 1),
        ('content="BTC Explorer"', 'content="Block Zero Explorer"', 0),
        # Display-currency toggle: keep the internal value "btc" but label it TBLOZ.
        ('.btn-primary.btn-sm #{item}',
         '.btn-primary.btn-sm #{item == "BTC" ? "TBLOZ" : item}', 0),
        ('value=${item.toLowerCase()}`) #{item}',
         'value=${item.toLowerCase()}`) #{item == "BTC" ? "TBLOZ" : item}', 0),
        # Default <title> in the layout (used when a page sets no headContent title)
        ('title Explorer', 'title Block Zero Testnet Explorer', 1),
        ('Open-source, easy-to-use, educational Bitcoin explorer whose only dependency is your Bitcoin Core node.',
         'Open-source explorer for the Block Zero testnet, powered by your own node.', 0),
        ('"BitcoinExplorer.org"', '"Block Zero Testnet Explorer"', 0),
    ],
    f"{BASE}/views/layout-iframe.pug": [
        ('BitcoinExplorer.org - Open-Source Bitcoin Explorer',
         'Block Zero Testnet Explorer', 1),
        ('content="BTC Explorer"', 'content="Block Zero Explorer"', 0),
    ],
    # The actual amount unit ("... BTC") comes from this global table, NOT the
    # coin config. Rename the native unit's display name to TBLOZ and add a
    # "tbloz" alias key: some views re-look-up the type by the unit's (now
    # "tbloz") lowercased name, e.g. currencyTypes[parts.currencyUnit.toLowerCase()].
    f"{BASE}/app/currencies.js": [
        ('name:"BTC",', 'name:"TBLOZ",', 1),
        ('global.currencySymbols = {',
         'global.currencyTypes["tbloz"] = global.currencyTypes["btc"];\n\nglobal.currencySymbols = {',
         1),
        ('"btc": "\u20bf",', '"btc": "\u20bf",\n\t"tbloz": "\u20bf",', 1),
    ],
    # Amount tooltips hardcode " BTC" as the unit suffix on every page that
    # renders a value. Replace all occurrences so amounts read "... TBLOZ".
    f"{BASE}/views/includes/shared-mixins.pug": [
        ('.simpleVal} BTC`', '.simpleVal} TBLOZ`', 0),
    ],
    f"{BASE}/views/snippets/utxo-set.pug": [
        ('The sum of all spendable BTC units across the entire blockchain',
         'The sum of all spendable TBLOZ units across the entire blockchain', 1),
    ],
}


def patch_file(path, reps):
    try:
        with open(path, encoding="utf-8") as f:
            s = f.read()
    except FileNotFoundError:
        print(f"  SKIP (missing): {path}")
        return
    changed = False
    for old, new, n in reps:
        if old not in s:
            if new in s:
                print(f"  already applied in {path}: {new!r}")
            else:
                print(f"  WARN not found in {path}: {old!r}")
            continue
        count = s.count(old)
        if n <= 0:
            s = s.replace(old, new)
            print(f"  patched {path} ({count}x): {old!r} -> {new!r}")
        else:
            s = s.replace(old, new, n)
            print(f"  patched {path}: {old!r} -> {new!r}")
        changed = True
    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.write(s)


def main() -> int:
    for path, reps in PATCHES.items():
        patch_file(path, reps)
    print("done; restart with: systemctl restart blockzero-explorer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
