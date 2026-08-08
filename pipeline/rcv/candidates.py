"""Display names and party labels for candidates in Alaska/Maine RCV contests.

CVR files carry names in raw tabulator form ("Peltola, Mary S.", "Iii King, Angus")
and no party for most contests, so both RCV builders route their candidate lists
through here before writing output.

Party affiliations are as they appeared on the state's own ballot/results:
  https://www.elections.alaska.gov/election-results/
  https://www.maine.gov/sos/cec/elec/results/
"""

# Raw CVR name → (display name, party code). Party of None means unaffiliated /
# not applicable (write-ins).
GENERAL_ELECTION = {
    # Alaska 2022 & 2024 general
    "Peltola, Mary S.":      ("Mary Peltola",      "D"),
    "Palin, Sarah":          ("Sarah Palin",       "R"),
    "Begich, Nick":          ("Nick Begich III",   "R"),
    "Bye, Chris":            ("Chris Bye",         "L"),
    "Murkowski, Lisa":       ("Lisa Murkowski",    "R"),
    "Tshibaka, Kelly C.":    ("Kelly Tshibaka",    "R"),
    "Chesbro, Patricia R.":  ("Pat Chesbro",       "D"),
    "Kelley, Buzz A.":       ("Buzz Kelley",       "R"),
    "Howe, John Wayne":      ("John Wayne Howe",   "AIP"),
    "Hafner, Eric":          ("Eric Hafner",       "D"),
    "Dunleavy/Dahlstrom":    ("Mike Dunleavy",     "R"),
    "Gara/Cook":             ("Les Gara",          "D"),
    "Walker/Drygas":         ("Bill Walker",       "I"),
    "Pierce/Grunwald":       ("Charlie Pierce",    "R"),
    "Trump/Vance":           ("Donald Trump",      "R"),
    "Harris/Walz":           ("Kamala Harris",     "D"),
    "Kennedy/Shanahan":      ("Robert Kennedy Jr.", "I"),
    "Oliver/Maat":           ("Chase Oliver",      "L"),
    "Stein/Ware":            ("Jill Stein",        "G"),
    "West/Abdullah":         ("Cornel West",       "I"),
    "Terry/Broden":          ("Randall Terry",     "I"),
    "Sonski/Onak":           ("Peter Sonski",      "I"),
    # Maine 2018 CD2 general
    "Bruce Poliquin":        ("Bruce Poliquin",    "R"),
    "Jared F. Golden":       ("Jared Golden",      "D"),
    "Tiffany L. Bond":       ("Tiffany Bond",      "I"),
    "William R.S. Hoar":     ("Will Hoar",         "I"),
    # Maine 2022 CD2 general (names as spelled in the SoS summary report)
    "Jared Forrest Golden":  ("Jared Golden",      "D"),
    "Tiffany Bond":          ("Tiffany Bond",      "I"),
    "Write-in":              ("Write-in",          None),
}

# Primary candidates all share the contest's party, so only the display name
# needs fixing where the CVR mangles it.
DISPLAY_FIXES = {
    "Iii King, Angus":       "Angus King III",
    "Owen Z. Mccarthy":      "Owen McCarthy",
    "Dale John Crafts":      "Dale Crafts",
    "Eric L. Brakey":        "Eric Brakey",
    "Lucas R. St. Clair":    "Lucas St. Clair",
    "Craig R. Olson":        "Craig Olson",
    "Jonathan S. Fulford":   "Jonathan Fulford",
    "Janet T. Mills":        "Janet Mills",
    "Adam Roland Cote":      "Adam Cote",
    "Elizabeth A. Sweet":    "Betsy Sweet",
    "Mark W. Eves":          "Mark Eves",
    "Mark N. Dion":          "Mark Dion",
    "Diane Marie Russell":   "Diane Russell",
    "Donna J. Dion":         "Donna Dion",
    "Nirav D. Shah":         "Nirav Shah",
    "Hannah M. Pingree":     "Hannah Pingree",
    "Troy Dale Jackson":     "Troy Jackson",
    "Robert B. Charles":     "Robert Charles",
    "Benjamin T. Midgley":   "Benjamin Midgley",
    "Jonathan J. Bush":      "Jonathan Bush",
    "Garrett Paul Mason":    "Garrett Mason",
    "David J. Jones":        "David Jones",
    "Robert J. Wessels":     "Robert Wessels",
    "James D. Libby":        "James Libby",
    "Joseph M. Baldacci":    "Joseph Baldacci",
    "Matthew G. Dunlap":     "Matt Dunlap",
    "Paige Loud":            "Paige Loud",
}

PRIMARY_PARTY = {"PRIMARY_D": "D", "PRIMARY_R": "R"}


def display_name(raw: str) -> str:
    if raw in GENERAL_ELECTION:
        return GENERAL_ELECTION[raw][0]
    return DISPLAY_FIXES.get(raw, raw)


def party_of(raw: str, contest_type: str) -> str | None:
    if raw == "Write-in":
        return None
    if contest_type in PRIMARY_PARTY:
        return PRIMARY_PARTY[contest_type]
    if raw in GENERAL_ELECTION:
        return GENERAL_ELECTION[raw][1]
    raise KeyError(f"No party recorded for general-election candidate {raw!r}; add it to candidates.py")


def relabel(race: dict) -> dict:
    """Rewrite every candidate name in a race record to its display name and
    attach a name → party map."""
    ctype = race.get("contestType", "GENERAL")
    names = race["candidates"]
    rename = {n: display_name(n) for n in names}
    race["parties"] = {rename[n]: party_of(n, ctype) for n in names}

    def remap_keys(d):
        return {rename.get(k, k): v for k, v in d.items()}

    race["candidates"] = [rename[n] for n in names]
    for key in ("irvWinner", "condorcetWinner", "rankedPairsWinner", "pluralityWinner"):
        if race.get(key):
            race[key] = rename.get(race[key], race[key])
    for rnd in race.get("irvRounds", []):
        rnd["totals"] = remap_keys(rnd["totals"])
        rnd["pcts"] = remap_keys(rnd["pcts"])
        rnd["eliminated"] = [rename.get(c, c) for c in rnd.get("eliminated", [])]
    for key in ("condorcetMatrix", "condorcetCounts"):
        if key in race:
            race[key] = {rename.get(a, a): remap_keys(row) for a, row in race[key].items()}
    if race.get("stvElected"):
        race["stvElected"] = [rename.get(c, c) for c in race["stvElected"]]
    for rnd in race.get("stvRounds", []):
        for k in ("elected", "eliminated"):
            if rnd.get(k):
                rnd[k] = rename.get(rnd[k], rnd[k])
        rnd["counts"] = remap_keys(rnd["counts"])
    return race
