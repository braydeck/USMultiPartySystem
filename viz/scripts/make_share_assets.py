#!/usr/bin/env python3
"""Build per-party social-share assets:
  viz/public/og/<CODE>.png   — 1200x630 "you're <Party>" card (for link previews)
  viz/public/r/<CODE>/index.html — tiny stub with per-party OG meta that redirects
                                    humans to /?tab=quiz&result=<CODE>

Pure-static (no edge function); files in public/ deploy verbatim to the site root,
so a shared https://usmultiparty.com/r/<CODE> previews with the party card.
"""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PROFILES = json.loads((ROOT / "viz" / "src" / "data" / "clusterProfiles.json").read_text())
HOUSE = json.loads((ROOT / "viz" / "src" / "data" / "houseSeats.json").read_text())
OG_DIR = ROOT / "viz" / "public" / "og"
R_DIR = ROOT / "viz" / "public" / "r"
SITE = "https://usmultiparty.com"

# Names / colors / taglines mirror viz/src/constants/parties.ts (PARTY_NAMES, PARTY_COLORS,
# PARTY_TAGLINES). Keep in sync if those change. All ten current parties, incl. LBR (formerly
# SD) and OAO.
NAMES = {"CON": "Conservative", "LBR": "Labor", "STY": "Solidarity", "POP": "Populist",
         "CUP": "Civic Union Party", "LIB": "Liberal", "NAT": "Nationalist",
         "DSA": "Democratic Socialists", "PRG": "Progressive",
         "OAO": "Order and Opportunity Party"}
COLORS = {"PRG": "#15803d", "DSA": "#22c55e", "LIB": "#0284c7", "LBR": "#38bdf8", "STY": "#8a70b8",
          "CUP": "#825a27", "CON": "#e68c2c", "POP": "#d34812", "NAT": "#a01d2a", "OAO": "#5b6b8c"}
TAGLINES = {"PRG": "Progressive on taxes, climate, and civil liberties; trusts elections",
            "LIB": "Progressive on economics and climate; backs border enforcement and police",
            "DSA": "Progressive on economics and culture, secular, election-skeptic",
            "LBR": "Safety net, clean energy, and a Dreamer pathway with border enforcement",
            "STY": "Economically progressive and religiously traditional; election-skeptic",
            "CUP": "Centrist on economics and culture; law-and-order institutionalists",
            "CON": "Low-tax, law-and-order; trusts elections and backs background checks",
            "POP": "Immigration-restrictionist and election-skeptic; backs Medicaid expansion",
            "NAT": "Anti-immigration, religiously traditional, low-tax, and election-skeptic",
            "OAO": "Economically progressive and law-and-order; trusts elections"}
CODE_TO_ID = {"CON": "0", "LBR": "1", "STY": "2", "NAT": "3", "LIB": "4",
              "POP": "5", "CUP": "6", "OAO": "7", "DSA": "8", "PRG": "9"}

by_id = {p["id"]: p for p in PROFILES}
seats_by_id = {str(h["party"]): h["national"] for h in HOUSE}


def card(code: str):
    name, color, tag = NAMES[code], COLORS[code], TAGLINES[code]
    cid = CODE_TO_ID[code]
    seats = seats_by_id.get(cid, 0)
    positions = by_id[cid].get("keyPositions", [])[:3]

    fig = plt.figure(figsize=(12, 6.3), dpi=100)
    fig.patch.set_facecolor("#ffffff")
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1200); ax.set_ylim(0, 630); ax.axis("off")

    ax.add_patch(Rectangle((0, 0), 18, 630, facecolor=color))  # left color band
    ax.text(70, 560, "WHICH PARTY ARE YOU?", fontsize=15, color="#94a3b8", fontweight="bold")
    # Shrink the name to fit the card width for long party names (e.g. "Order and Opportunity Party").
    name_fs = max(30, min(52, int(1120 / len(name))))
    ax.text(70, 500, name, fontsize=name_fs, color=color, fontweight="bold")
    ax.text(70, 452, tag, fontsize=19, color="#475569")
    ax.text(70, 410, f"{seats} of 873 House seats under proportional rules", fontsize=15, color="#94a3b8")

    y = 345
    for pos in positions:
        supports = pos.get("direction") == "supports"
        mark, mcol = ("✓", "#16a34a") if supports else ("✗", "#dc2626")
        q = pos["question"]
        if len(q) > 64:
            q = q[:61] + "..."
        ax.text(72, y, mark, fontsize=20, color=mcol, fontweight="bold")
        ax.text(104, y, q, fontsize=17, color="#1c1b1a")
        y -= 46

    ax.text(70, 52, f"Take the quiz  →  {SITE.replace('https://', '')}", fontsize=18,
            color=color, fontweight="bold")

    OG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OG_DIR / f"{code}.png", dpi=100, facecolor="#ffffff")
    plt.close(fig)


# Self-contained landing: renders a visible party statement + "Take the quiz" CTA so the page
# is never blank (works with JS off, or if the redirect fails). JS visitors are sent straight
# into the app's shared-result view via location.replace, which is the richer experience.
STUB = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>I'm {name}. Which party are you?</title>
<meta name="description" content="{tag}" />
<meta property="og:type" content="website" />
<meta property="og:url" content="{site}/r/{code}" />
<meta property="og:title" content="I'm {name}. Which party are you?" />
<meta property="og:description" content="{tag}" />
<meta property="og:image" content="{site}/og/{code}.png" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="I'm {name}. Which party are you?" />
<meta name="twitter:description" content="{tag}" />
<meta name="twitter:image" content="{site}/og/{code}.png" />
<link rel="canonical" href="/?tab=quiz&result={code}" />
</head>
<body style="margin:0;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;background:#f8fafc;color:#1c1b1a;">
<div style="max-width:560px;margin:0 auto;padding:64px 24px;text-align:center;">
  <div style="font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:#94a3b8;font-weight:700;">Which party are you?</div>
  <div style="font-size:40px;font-weight:800;color:{color};margin:12px 0 6px;line-height:1.1;">{name}</div>
  <div style="font-size:17px;color:#475569;margin-bottom:28px;">{tag}</div>
  <p style="font-size:15px;color:#64748b;line-height:1.55;margin:0 auto 28px;max-width:44ch;">Someone shared their result from a simulation of U.S. elections under proportional representation. Take the quiz to find the party that matches your politics.</p>
  <a href="/?tab=quiz&result={code}&utm_source=result_share&utm_medium=share&utm_content={code}" style="display:inline-block;background:{color};color:#fff;font-weight:700;font-size:16px;text-decoration:none;padding:13px 30px;border-radius:9999px;">Take the quiz &rarr;</a>
</div>
<script>location.replace("/?tab=quiz&result={code}&utm_source=result_share&utm_medium=share&utm_content={code}");</script>
</body>
</html>
"""


def stub(code: str):
    d = R_DIR / code
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(
        STUB.format(name=NAMES[code], tag=TAGLINES[code], code=code, site=SITE, color=COLORS[code]))


for code in NAMES:
    card(code)
    stub(code)
print(f"wrote {len(NAMES)} cards to viz/public/og/ and {len(NAMES)} stubs to viz/public/r/")
