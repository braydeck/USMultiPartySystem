#!/usr/bin/env python3
"""Build per-party social-share assets:
  viz/public/og/<CODE>.png   — 1200x630 "you're <Party>" card (for link previews)
  viz/public/r/<CODE>/index.html — tiny stub with per-party OG meta that redirects
                                    humans to /?tab=quiz&result=<CODE>

Pure-static (no edge function); files in public/ deploy verbatim to the site root,
so a shared https://usmultipartysystem.pages.dev/r/<CODE> previews with the party card.
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
SITE = "https://usmultipartysystem.pages.dev"

NAMES = {"CON": "Conservative", "SD": "Social Democrat", "STY": "Solidarity", "POP": "Populist",
         "CUP": "Civic Union Party", "LIB": "Liberal", "NAT": "Nationalist",
         "DSA": "Democratic Socialists", "PRG": "Progressive"}
COLORS = {"PRG": "#1e3a8a", "LIB": "#1d4ed8", "DSA": "#60a5fa", "SD": "#06b6d4", "STY": "#16a34a",
          "CUP": "#a16207", "CON": "#ea580c", "POP": "#dc2626", "NAT": "#7f1d1d"}
TAGLINES = {"PRG": "Climate action, social justice, universal programs",
            "LIB": "Civil liberties, regulated markets, global engagement",
            "DSA": "Worker power, economic equality, public ownership",
            "SD": "Strong safety net, institutional reform, center-left",
            "STY": "Cross-cutting populism, skeptical of both establishments",
            "CUP": "Moderate on economics and culture, institutionalist",
            "CON": "Free markets, traditional values, national sovereignty",
            "POP": "Anti-establishment right, immigration restriction",
            "NAT": "Cultural conservatism, economic nationalism, strong borders"}
CODE_TO_ID = {"CON": "0", "SD": "1", "STY": "2", "NAT": "3", "LIB": "4", "POP": "5", "CUP": "6", "DSA": "8", "PRG": "9"}

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
    ax.text(70, 500, name, fontsize=52, color=color, fontweight="bold")
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


STUB = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
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
<meta http-equiv="refresh" content="0; url=/?tab=quiz&result={code}" />
</head>
<body>
<script>location.replace("/?tab=quiz&result={code}");</script>
<noscript><a href="/?tab=quiz&result={code}">View this result</a></noscript>
</body>
</html>
"""


def stub(code: str):
    d = R_DIR / code
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(STUB.format(name=NAMES[code], tag=TAGLINES[code], code=code, site=SITE))


for code in NAMES:
    card(code)
    stub(code)
print(f"wrote {len(NAMES)} cards to viz/public/og/ and {len(NAMES)} stubs to viz/public/r/")
