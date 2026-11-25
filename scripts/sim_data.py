"""
sim_data.py
-----------
Shared loaders for the generated reference docs (docs/AGENT_SUMMARY.md, PARTY_PROFILES.md).

Every number these docs print is read here from the payloads the site renders
(viz/src/data/*.json, viz/public/data/*.json) or from pipeline/party_codes.py. Nothing is typed
by hand: rerun the build scripts after the pipeline and the docs follow.

The app defaults (depth, turnout stop, magnitude, field, vote model) are parsed out of the tab
sources' useUrlState(...) calls, so a change to a default in the app moves the docs with it.
"""

from __future__ import annotations

import json
import math
import re
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DATA = ROOT / "viz" / "src" / "data"
PUB_DATA = ROOT / "viz" / "public" / "data"
TABS = ROOT / "viz" / "src" / "tabs"
PARTIES_TS = ROOT / "viz" / "src" / "constants" / "parties.ts"

sys.path.insert(0, str(ROOT / "pipeline"))
from party_codes import LEFT_RIGHT, PARTY_TO_CLUSTER  # noqa: E402

FACTORS = ["F4", "F1", "F5", "F2"]  # re-sorted by η² at load time; this is only the key set


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


@lru_cache(maxsize=None)
def load(path: Path):
    with open(path) as f:
        return json.load(f)


def src(name: str) -> Path:
    return SRC_DATA / name


def pub(name: str) -> Path:
    return PUB_DATA / name


# ── App defaults, parsed from the tab sources ────────────────────────────────

def _url_defaults(param: str) -> set[str]:
    pat = re.compile(r"useUrlState<[^>]*>\(\s*'" + re.escape(param) + r"'\s*,\s*'([^']*)'")
    found = set()
    for f in TABS.glob("*.tsx"):
        found.update(pat.findall(f.read_text()))
    return found


def app_defaults() -> dict:
    out = {}
    for key, param in [("depth", "depth"), ("stop", "part"), ("magnitude", "wyoming"),
                       ("field", "scenario"), ("voteModel", "voteModel"), ("senateMethod", "method")]:
        vals = _url_defaults(param)
        if len(vals) != 1:
            raise SystemExit(f"app default for '{param}' is not unique across tabs: {sorted(vals)}")
        out[key] = vals.pop()
    stops = set()
    for f in TABS.glob("*.tsx"):
        for m in re.finditer(r"useUrlState<string>\('part',\s*'[^']*',\s*\{\s*allowed:\s*\[([^\]]*)\]", f.read_text()):
            stops.add(tuple(re.findall(r"'(\d+)'", m.group(1))))
    if len(stops) != 1:
        raise SystemExit(f"turnout stop list differs across tabs: {stops}")
    out["stops"] = list(stops.pop())
    return out


def stop_suffix(stop: str) -> str:
    """Payload suffix for a turnout stop: gap 0 is the plain *Turnout file, the rest *TurnoutLNN."""
    return "Turnout" if stop == "0" else f"TurnoutL{stop}"


# ── Party copy, read from the app constants ──────────────────────────────────

def _ts_record(name: str) -> dict[str, str]:
    text = PARTIES_TS.read_text()
    m = re.search(r"export const " + name + r": Record<string, string> = \{(.*?)\n\};", text, re.S)
    if not m:
        raise SystemExit(f"{name} not found in {rel(PARTIES_TS)}")
    out = {}
    for km in re.finditer(r"^\s*([A-Z]+):\s*'((?:[^'\\]|\\.)*)',?\s*$", m.group(1), re.M):
        out[km.group(1)] = km.group(2).replace("\\'", "'")
    return out


def taglines() -> dict[str, str]:
    return _ts_record("PARTY_TAGLINES")


def blurbs() -> dict[str, str]:
    return _ts_record("PARTY_BLURBS")


def party_names() -> dict[str, str]:
    return _ts_record("PARTY_NAMES")


# ── Core tables ──────────────────────────────────────────────────────────────

def parties() -> list[str]:
    return list(LEFT_RIGHT)


def factor_meta() -> list[dict]:
    """Factors sorted by η², strongest first."""
    rows = load(src("factorLoadings.json"))
    return sorted(rows, key=lambda r: -r["eta"])


def cluster_profiles() -> dict[str, dict]:
    return {c["party"]: c for c in load(src("clusterProfiles.json"))}


def population() -> dict[str, dict]:
    return {r["party"]: r for r in load(src("partyPopulation.json"))}


def n_respondents() -> int:
    return load(src("crossPartyAffinity.json"))["nVoters"]


def house(depth: str, mag: str, stop: str) -> dict:
    """STV and party-list national seats as the House tab shows them at a ranked depth."""
    return load(src("houseDepthNational.json"))[depth][mag][stop]["national"]


def mmp(mag: str, stop: str) -> dict:
    return load(src("houseMmpNational.json"))[mag][stop]


def general(depth: str, stop: str) -> dict:
    return load(pub("generalDepth.json"))[depth][stop]


def primary(depth: str, stop: str) -> dict:
    return load(pub("primaryDepth.json"))[depth]["primary"][stop]


def top_two(depth: str, stop: str) -> dict:
    return load(pub("topTwo.json"))[depth][stop]


def senate(method: str, stop: str) -> list[dict]:
    name = "Condorcet" if method == "cond" else "IRV"
    return load(src(f"pureMultiSenate{name}{stop_suffix(stop)}.json"))


def uncertainty(stop: str) -> dict:
    return load(src(f"uncertainty{stop_suffix(stop)}.json"))


def ec_weights() -> dict[str, int]:
    """Electors per state: House seats at double magnitude plus two (ecAllocation.ts ecWeights)."""
    return {fips: e["totalSeats"] + 2 for fips, e in load(src("houseStateMap.json")).items()}


def bills() -> list[dict]:
    return load(src("candidateVoteModel.json"))


# ── Ports of the app's client-side calculations ──────────────────────────────
# These mirror TypeScript the site runs in the browser, so the doc shows what the page shows.

def largest_remainder(shares: dict[str, float], seats: int) -> dict[str, int]:
    """viz/src/lib/ecAllocation.ts largestRemainder."""
    total = sum(shares.values())
    if total <= 0 or seats <= 0:
        return {}
    exact = {c: s / total * seats for c, s in shares.items()}
    out = {c: int(v // 1) for c, v in exact.items()}
    left = seats - sum(out.values())
    order = sorted(exact, key=lambda c: (-(exact[c] - int(exact[c] // 1)), c))
    for c in order:
        if left <= 0:
            break
        out[c] += 1
        left -= 1
    return out


def plurality_winner(shares: dict[str, float]) -> str | None:
    if not shares:
        return None
    return sorted(shares, key=lambda c: (-shares[c], c))[0]


def allocate_ec(state_winners: dict, weights: dict[str, int], method: str) -> dict:
    """viz/src/lib/ecAllocation.ts allocateEC. method ∈ prop | fptp | irv | condorcet."""
    totals: dict[str, int] = {}
    for fips, sw in state_winners.items():
        ev = weights.get(fips)
        if not ev:
            continue
        if method == "prop":
            electors = largest_remainder(sw["shares"], ev)
        else:
            carry = {"fptp": plurality_winner(sw["shares"]), "irv": sw["winner"],
                     "condorcet": sw["condorcetWinner"]}[method]
            electors = {carry: ev} if carry else {}
        for c, n in electors.items():
            totals[c] = totals.get(c, 0) + n
    total = sum(totals.values())
    majority = total // 2 + 1
    winner = next((c for c, n in sorted(totals.items(), key=lambda kv: (-kv[1], kv[0])) if n >= majority), None)
    return {"byParty": totals, "total": total, "majority": majority, "winner": winner}


def national_first_choice(rounds: list[dict]) -> dict[str, float]:
    first = rounds[0]["candidates"]
    tot = sum(c["votes"] for c in first)
    return {c["code"]: c["votes"] / tot * 100 for c in first}


def agreement_matrices(order: list[str]) -> tuple[dict, dict]:
    """viz/src/components/legislation/PartyAgreement.tsx: free vote (position) and whipped (same side)."""
    position: dict = {}
    binary: dict = {}
    for a in order:
        position[a], binary[a] = {}, {}
        for c in order:
            gap = same = n = 0
            for b in bills():
                va = b["parties"].get(a, {}).get("observedPct")
                vc = b["parties"].get(c, {}).get("observedPct")
                if va is None or vc is None:
                    continue
                gap += abs(va - vc)
                same += (va > 50) == (vc > 50)
                n += 1
            position[a][c] = 100 - gap / n if n else float("nan")
            binary[a][c] = same / n * 100 if n else float("nan")
    return position, binary


def budget_rows() -> list[dict]:
    """The CES state-spending items (pipeline/build_budget_priorities.py), kept out of bills()."""
    return load(src("budgetPriorities.json"))


def coalition_segments_whipped(bill: dict, seats: dict[str, int], order: list[str]) -> dict:
    """voteBloc.ts coalitionSegments(bill, seats, 'whipped'): every seat to the side the party's
    majority favors, each side ordered by support (stable, so ties keep the left-right order); on a
    pass the pivotal party is the yes party whose seats carry the running total to half the chamber."""
    supp = lambda p: bill["parties"][p].get("observedPct") or 0  # noqa: E731
    ps = [p for p in order if p in bill["parties"] and seats.get(p, 0) > 0]
    total = sum(seats[p] for p in ps)
    yes = sorted([p for p in ps if supp(p) > 50], key=lambda p: -supp(p))
    no = sorted([p for p in ps if supp(p) <= 50], key=lambda p: -supp(p))
    total_yes = sum(seats[p] for p in yes)
    passed = total_yes > total / 2
    pivotal, cum = None, 0
    if passed:
        for p in yes:
            cum += seats[p]
            if cum >= total / 2:
                pivotal = p
                break
    return {"yes": yes, "no": no, "total": total, "totalYes": total_yes, "pass": passed, "pivotal": pivotal}


def domain_coalitions(items: list[dict], seats: dict[str, int], order: list[str]) -> list[dict]:
    """voteBloc.ts domainCoalitions: per domain, each party's share of items on the winning side
    and share that pass only with its seats (needed), the most common winning side (ties to more
    seats, then first met) and the items that fail."""
    by: dict[str, list] = {}
    for b in items:
        by.setdefault(b["domain"], []).append(b)
    seated = [p for p in order if seats.get(p, 0) > 0]
    out = []
    for dom, rows in by.items():
        won = {p: 0 for p in seated}
        need = {p: 0 for p in seated}
        sets: dict[str, dict] = {}
        failed, passed = [], 0
        for b in rows:
            c = coalition_segments_whipped(b, seats, order)
            passed += c["pass"]
            if not c["pass"]:
                failed.append(b)
            winners = c["yes"] if c["pass"] else c["no"]
            for p in winners:
                won[p] += 1
            if c["pass"]:
                for p in winners:
                    if c["totalYes"] - seats[p] <= c["total"] / 2:
                        need[p] += 1
            ordered = [p for p in order if p in winners]
            key = ("Y:" if c["pass"] else "N:") + ",".join(ordered)
            if key in sets:
                sets[key]["count"] += 1
            else:
                sets[key] = {"parties": ordered, "pass": c["pass"], "count": 1,
                             "seats": sum(seats.get(p, 0) for p in ordered)}
        typical = {"parties": [], "pass": True, "count": 0, "seats": -1}
        for v in sets.values():
            if v["count"] > typical["count"] or (v["count"] == typical["count"] and v["seats"] > typical["seats"]):
                typical = v
        n = len(rows)
        out.append({"domain": dom, "bills": rows, "passed": passed, "failed": failed,
                    "membership": {p: won[p] / n for p in seated}, "needed": {p: need[p] / n for p in seated},
                    "typical": typical})
    return out


def _normal_cdf(x: float) -> float:
    """Abramowitz & Stegun 26.2.17, as voteBloc.ts normalCdf."""
    if x > 6:
        return 1.0
    if x < -6:
        return 0.0
    t = 1 / (1 + 0.2316419 * abs(x))
    d = 0.3989422803 * math.exp(-0.5 * x * x)
    tail = d * t * (0.3193815 + t * (-0.3565638 + t * (1.7814779 + t * (-1.821256 + t * 1.3302744))))
    return tail if x < 0 else 1 - tail


def pass_probability(bill: dict, seats: dict[str, int], order: list[str]) -> float | None:
    """voteBloc.ts passProbability: members vote independently at their party's observed support."""
    mu = var = total = 0.0
    for p in order:
        s = seats.get(p, 0)
        if not s:
            continue
        total += s
        q = (bill["parties"].get(p, {}).get("observedPct") or 0) / 100
        mu += s * q
        var += s * q * (1 - q)
    if not total:
        return None
    need = math.floor(total / 2) + 1
    return 1 - _normal_cdf((need - 0.5 - mu) / (math.sqrt(var) if var > 0 else 1e-6))


# ── Markdown helpers ─────────────────────────────────────────────────────────

def table(headers: list[str], rows: list[list], align: str | None = None) -> str:
    align = align or ("l" + "r" * (len(headers) - 1))
    sep = ["---:" if a == "r" else ":---:" if a == "c" else "---" for a in align]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(sep) + " |"]
    for r in rows:
        lines.append("| " + " | ".join("" if v is None else str(v) for v in r) + " |")
    return "\n".join(lines)


def f1(x) -> str:
    return f"{x:.1f}"


def f2(x) -> str:
    return f"{x:+.2f}"


def party_of(code: str) -> str:
    return code.split("_")[0]


# ── Senate delegations (port of viz/src/lib/senateDelegations.ts) ────────────

DELEGATIONS_TS = ROOT / "viz" / "src" / "lib" / "senateDelegations.ts"


def split_threshold_pp() -> float:
    m = re.search(r"export const SPLIT_THRESHOLD_PP\s*=\s*([\d.]+)", DELEGATIONS_TS.read_text())
    if not m:
        raise SystemExit(f"SPLIT_THRESHOLD_PP not found in {rel(DELEGATIONS_TS)}")
    return float(m.group(1))


def delegations(states: dict) -> dict[str, dict]:
    """Two senators per state: the resample leader twice, or leader + runner-up when the gap
    between their resample win shares is within SPLIT_THRESHOLD_PP."""
    thr = split_threshold_pp()
    out = {}
    for fips in sorted(states):
        st = states[fips]
        ranked = sorted(st["dist"].items(), key=lambda kv: -kv[1])
        top, top_p = ranked[0] if ranked else (st["modal"], 1.0)
        runner = ranked[1] if len(ranked) > 1 else None
        gap = (top_p - runner[1]) * 100 if runner else float("inf")
        split = gap <= thr + 1e-9
        out[fips] = {"seats": [top, runner[0]] if split and runner else [top, top], "split": split,
                     "top": top, "topPct": top_p * 100,
                     "runner": runner[0] if runner else None, "runnerPct": runner[1] * 100 if runner else None}
    return out


def delegation_seats(states: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for d in delegations(states).values():
        for p in d["seats"]:
            out[p] = out.get(p, 0) + 1
    return out
