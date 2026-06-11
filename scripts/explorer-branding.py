#!/usr/bin/env python3
"""Rebrand btc-rpc-explorer for Block Zero (testnet or mainnet).

btc-rpc-explorer ships only Bitcoin coin configs and hardcodes "Bitcoin
Explorer" in a few view templates. This patches the in-place coin config and
views for the chosen network. Re-run after every `git pull` of the explorer,
then restart the matching systemd unit.

Usage:
  python3 explorer-branding.py testnet   # TBLOZ, tbz HRP, port 3002 service
  python3 explorer-branding.py mainnet   # BLOZ, bz HRP, port 3003 service
"""
from __future__ import annotations

import argparse
import sys

BASE_BY_NETWORK = {
    "testnet": "/opt/btc-rpc-explorer",
    "mainnet": "/opt/btc-rpc-explorer-mainnet",
}

NETWORKS = {
    "testnet": {
        "service": "blockzero-explorer",
        "coin_name": "Block Zero",
        "ticker": "TBLOZ",
        "ticker_lower": "tbloz",
        "site_title": "Block Zero Testnet Explorer",
        "explorer_label": "Block Zero Testnet Explorer",
        "tagline": "A second chance at Genesis. CPU-mineable. Fair launch.",
        "subtitle": "Open-source explorer for the Block Zero testnet, powered by your own node.",
        "testnet_label": "Block Zero Testnet Explorer",
        "explorer_url": "https://texplorer.bloz.org",
    },
    "mainnet": {
        "service": "blockzero-mainnet-explorer",
        "coin_name": "Block Zero",
        "ticker": "BLOZ",
        "ticker_lower": "bloz",
        "site_title": "Block Zero Explorer",
        "explorer_label": "Block Zero Explorer",
        "tagline": "A second chance at Genesis. CPU-mineable. Fair launch.",
        "subtitle": "Open-source explorer for Block Zero mainnet, powered by your own node.",
        "testnet_label": "Block Zero Explorer",
        "explorer_url": "https://explorer.bloz.org",
    },
}

# ---------------------------------------------------------------------------
# Block Zero theme — same design tokens as bloz.org (void/steel/blue/cyan,
# Orbitron + Rajdhani + Inter) plus the shared cross-site suite nav.
# Loaded AFTER the explorer's own theme css, so overrides win.
# ---------------------------------------------------------------------------
THEME_CSS = """\
/* BLOCK ZERO explorer theme — design tokens shared with bloz.org */
@import url("https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500;600&display=swap");

:root {
\t--bz-void: #05070A;
\t--bz-steel: #11161D;
\t--bz-steel-2: #161d27;
\t--bz-blue: #3FA9FF;
\t--bz-cyan: #6FE7FF;
\t--bz-silver: #BFC7D5;
\t--bz-white: #F5F7FA;
\t--bz-muted: #79849a;
\t--bz-line: rgba(111, 231, 255, 0.14);
}

body { background-color: var(--bz-void) !important; font-family: "Inter", system-ui, sans-serif !important; }
.bg-header-footer { background-color: var(--bz-void) !important; }
nav.navbar.bg-header-footer { border-bottom: 1px solid var(--bz-line); }
footer.bg-header-footer, footer { border-top: 1px solid var(--bz-line); }
.navbar-brand span.fw-light { font-family: "Orbitron", "Rajdhani", sans-serif; font-size: 0.95rem; letter-spacing: 0.1em; color: var(--bz-silver) !important; }

.card { background-color: var(--bz-steel) !important; border: 1px solid var(--bz-line) !important; border-radius: 0 !important; }
.card-header { background-color: var(--bz-steel-2) !important; border-bottom: 1px solid var(--bz-line) !important; font-family: "Rajdhani", sans-serif; letter-spacing: 0.06em; text-transform: uppercase; }
.modal-content { background-color: var(--bz-steel) !important; border: 1px solid var(--bz-line) !important; }

h1, h2, h3, .h1, .h2, .h3 { font-family: "Orbitron", "Rajdhani", sans-serif; letter-spacing: 0.04em; }

a { color: var(--bz-blue); }
a:hover { color: var(--bz-cyan); }

.btn-primary { background-color: rgba(63, 169, 255, 0.10) !important; border-color: var(--bz-blue) !important; color: var(--bz-white) !important; border-radius: 0 !important; }
.btn-primary:hover { background-color: rgba(63, 169, 255, 0.22) !important; box-shadow: 0 0 18px rgba(63, 169, 255, 0.3); }
.form-control, .input-group-text { background-color: var(--bz-steel) !important; border-color: var(--bz-line) !important; color: var(--bz-white) !important; border-radius: 0 !important; }
.dropdown-menu { background-color: var(--bz-steel-2) !important; border: 1px solid var(--bz-line) !important; }
.dropdown-item { color: var(--bz-silver) !important; }
.dropdown-item:hover, .dropdown-item:focus { background-color: rgba(111, 231, 255, 0.08) !important; color: var(--bz-cyan) !important; }
.badge.bg-primary { background-color: rgba(63, 169, 255, 0.18) !important; border: 1px solid var(--bz-blue); color: var(--bz-cyan) !important; }

/* Hide duplicate explorer navbar — suite header from bloz.org is canonical */
nav.navbar.bg-header-footer { display: none !important; }
"""


def suite_nav_pug(explorer_url: str) -> str:
    """Pug markup for the shared suite nav, injected right after the body tag."""
    return (
        '\t\tnav.bz-suite(aria-label="Block Zero sites")\n'
        '\t\t\ta.bz-suite-brand(href="https://bloz.org")\n'
        '\t\t\t\timg(src="https://bloz.org/assets/bloz-mark.png", alt="", width="83", height="83")\n'
        "\t\t\t\tspan BLOCK ZERO\n"
        "\t\t\t.bz-suite-links\n"
        '\t\t\t\ta(href="https://bloz.org") Home\n'
        '\t\t\t\ta(href="https://pool.bloz.org") Pool\n'
        f'\t\t\t\ta.active(href="{explorer_url}") Explorer\n'
        '\t\t\t\ta(href="https://bridge.bloz.org") Bridge\n'
        "\t\t\tspan.bz-suite-live\n"
        "\t\t\t\tspan.dot\n"
        "\t\t\t\tspan#suite-height MAINNET LIVE\n"
    )


def build_patches(base: str, cfg: dict) -> dict[str, list[tuple[str, str, int]]]:
    ticker = cfg["ticker"]
    ticker_lower = cfg["ticker_lower"]
    title = cfg["site_title"]
    label = cfg["explorer_label"]
    tagline = cfg["tagline"]
    subtitle = cfg["subtitle"]
    test_label = cfg["testnet_label"]

    return {
        f"{base}/app/coins/btc.js": [
            ('name:"Bitcoin",', f'name:"{cfg["coin_name"]}",', 1),
            ('ticker:"BTC",', f'ticker:"{ticker}",', 1),
            ('name:"BTC",', f'name:"{ticker}",', 1),
            ('values:["", "btc", "BTC"]', f'values:["", "{ticker_lower}", "{ticker}"]', 1),
            ('"BTC":currencyUnits[0]', f'"{ticker}":currencyUnits[0]', 1),
            ('"test":"Testnet Explorer",', f'"test":"{test_label}",', 1),
        ],
        f"{base}/views/index.pug": [
            ("title Bitcoin Explorer", f"title {title}", 1),
            ("h5 Bitcoin Explorer", f"h5 {title}", 1),
            ("Made for Bitcoiners by Bitcoiners. Enjoy!", tagline, 1),
        ],
        f"{base}/views/layout.pug": [
            ("span.fw-light Bitcoin Explorer", f"span.fw-light {label}", 1),
            ("BitcoinExplorer.org - Open-Source Bitcoin Explorer", label, 1),
            ('content="BTC Explorer"', f'content="{label}"', 0),
            (
                ".btn-primary.btn-sm #{item}",
                f'.btn-primary.btn-sm #{{item == "BTC" ? "{ticker}" : item}}',
                0,
            ),
            (
                "value=${item.toLowerCase()}`) #{item}",
                f'value=${{item.toLowerCase()}}`) #{{item == "BTC" ? "{ticker}" : item}}',
                0,
            ),
            ("title Explorer", f"title {title}", 1),
            (
                "Open-source, easy-to-use, educational Bitcoin explorer whose only dependency is your Bitcoin Core node.",
                subtitle,
                0,
            ),
            ('"BitcoinExplorer.org"', f'"{label}"', 0),
        ],
        f"{base}/views/layout-iframe.pug": [
            ("BitcoinExplorer.org - Open-Source Bitcoin Explorer", label, 1),
            ('content="BTC Explorer"', f'content="{label}"', 0),
        ],
        f"{base}/views/includes/shared-mixins.pug": [
            (".simpleVal} BTC`", ".simpleVal} " + ticker + "`", 0),
        ],
        f"{base}/views/snippets/utxo-set.pug": [
            (
                "The sum of all spendable BTC units across the entire blockchain",
                f"The sum of all spendable {ticker} units across the entire blockchain",
                1,
            ),
        ],
    }


def currency_patches(base: str, cfg: dict) -> dict[str, list[tuple[str, str, int]]]:
    ticker = cfg["ticker"]
    ticker_lower = cfg["ticker_lower"]
    return {
        f"{base}/app/currencies.js": [
            ('name:"BTC",', f'name:"{ticker}",', 1),
            (
                "global.currencySymbols = {",
                f'global.currencyTypes["{ticker_lower}"] = global.currencyTypes["btc"];\n\nglobal.currencySymbols = {{',
                1,
            ),
            ('"btc": "\u20bf",', f'"btc": "\u20bf",\n\t"{ticker_lower}": "\u20bf",', 1),
        ],
    }


def theme_patches(base: str, cfg: dict) -> dict[str, list[tuple[str, str, int]]]:
    """Inject the Block Zero theme css + shared suite nav into layout.pug."""
    css_link = '\t\tlink(rel="stylesheet", href="./style/bloz-theme.css")'
    header_css = '\t\tlink(rel="stylesheet", href="https://bloz.org/assets/bloz-header.css")'
    header_js = '\t\tscript(src="https://bloz.org/assets/bloz-header.js" defer)'
    nav = suite_nav_pug(cfg["explorer_url"])
    return {
        f"{base}/views/layout.pug": [
            ("+themeCss", f"+themeCss\n{css_link}\n{header_css}", 1),
            (
                'href="./style/bloz-theme.css")',
                'href="./style/bloz-theme.css")\n\t\tlink(rel="stylesheet", href="https://bloz.org/assets/bloz-header.css")',
                0,
            ),
            (
                'img(src="https://bloz.org/assets/bloz-mark.png", alt="", width="22", height="22")',
                'img(src="https://bloz.org/assets/bloz-mark.png", alt="", width="83", height="83")',
                0,
            ),
            (
                'img(src="https://bloz.org/assets/bloz-mark.png", alt="", width="55", height="55")',
                'img(src="https://bloz.org/assets/bloz-mark.png", alt="", width="83", height="83")',
                0,
            ),
            (
                '\t\t\t\ta(href="https://bridge.bloz.org") Bridge\n\t\tnav.navbar',
                '\t\t\t\ta(href="https://bridge.bloz.org") Bridge\n\t\t\tspan.bz-suite-live\n\t\t\t\tspan.dot\n\t\t\t\tspan#suite-height MAINNET LIVE\n\t\tnav.navbar',
                0,
            ),
            (
                "\tbody.bg-header-footer\n\t\tnav.navbar",
                f"\tbody.bg-header-footer\n{nav}\t\tnav.navbar",
                1,
            ),
            (
                "\t\tblock endOfBody",
                f"{header_js}\n\n\t\tblock endOfBody",
                1,
            ),
        ],
    }


def write_theme_css(base: str) -> None:
    path = f"{base}/public/style/bloz-theme.css"
    try:
        with open(path, encoding="utf-8") as f:
            if f.read() == THEME_CSS:
                print(f"  theme css up to date: {path}")
                return
    except FileNotFoundError:
        pass
    with open(path, "w", encoding="utf-8") as f:
        f.write(THEME_CSS)
    print(f"  wrote theme css: {path}")


def patch_file(path: str, reps: list[tuple[str, str, int]]) -> None:
    try:
        with open(path, encoding="utf-8") as f:
            s = f.read()
    except FileNotFoundError:
        print(f"  SKIP (missing): {path}")
        return
    changed = False
    for old, new, n in reps:
        if new in s:
            print(f"  already applied in {path}: {new[:60]!r}")
            continue
        if old not in s:
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
    parser = argparse.ArgumentParser(description="Rebrand btc-rpc-explorer for Block Zero")
    parser.add_argument(
        "network",
        choices=sorted(NETWORKS),
        help="testnet (TBLOZ / texplorer.bloz.org) or mainnet (BLOZ / explorer.bloz.org)",
    )
    args = parser.parse_args()
    cfg = NETWORKS[args.network]
    base = BASE_BY_NETWORK[args.network]

    patches = build_patches(base, cfg)
    patches.update(currency_patches(base, cfg))
    patches.update(theme_patches(base, cfg))

    print(f"Branding for {args.network} ({cfg['ticker']}) in {base}...")
    write_theme_css(base)
    for path, reps in patches.items():
        patch_file(path, reps)
    print(f"done; restart with: systemctl restart {cfg['service']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
