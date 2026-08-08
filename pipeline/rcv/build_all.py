#!/usr/bin/env python3
"""
Rebuild every Alaska/Maine RCV race in ``data/outputs/rcv/``.

Alaska races come from Dominion CVR exports on disk (see download_cvrs.sh);
Maine races come from ranked.vote's CVR-derived reports. Only contests that
actually went to a ranked tabulation are included as race cards — Alaska's 2022
Governor and 2024 President races are built too, because the fact that they
ended in the first round is itself reported in the viz.

Usage:
    bash   pipeline/rcv/download_cvrs.sh        # one-time, ~4 GB
    python pipeline/rcv/build_all.py
    cd viz && python3 scripts/prepare_data.py
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
RAW = REPO_ROOT / "data" / "raw" / "rcv"

S22 = "https://www.elections.alaska.gov/results/22SSPG/CVR_Export_20220908084311.zip"
G22 = "https://elections.alaska.gov/results/22GENR/rcv/CVR_Export.zip"
G24 = "https://www.elections.alaska.gov/results/24GENR/CVR_Export_20241130154411.zip"

# cvr dir, contest description, year, office, race name, race id, stv seats, source
ALASKA = [
    ("AK_2022_special", "U.S. Representative (Special General)", 2022, "US_HOUSE",
     "U.S. House, at-large (special)", "AK_2022_US_HOUSE_SPECIAL", 1, S22),
    ("AK_2022_general", "U.S. Representative", 2022, "US_HOUSE",
     "U.S. House, at-large", "AK_2022_US_HOUSE", 1, G22),
    ("AK_2022_general", "U.S. Senator", 2022, "US_SENATE",
     "U.S. Senate", "AK_2022_US_SENATE", None, G22),
    ("AK_2022_general", "Governor / Lieutenant Governor", 2022, "GOVERNOR",
     "Governor", "AK_2022_GOVERNOR", None, G22),
    ("AK_2024_general", "U.S. Representative", 2024, "US_HOUSE",
     "U.S. House, at-large", "AK_2024_US_HOUSE", 1, G24),
    ("AK_2024_general", "U.S. President / Vice President", 2024, "PRESIDENT",
     "President", "AK_2024_PRESIDENT", None, G24),
]


def main() -> None:
    missing = [d for d, *_ in ALASKA if not (RAW / d).is_dir()]
    if missing:
        raise SystemExit(
            "Missing CVR exports: " + ", ".join(sorted(set(missing)))
            + f"\nRun: bash {Path('pipeline/rcv/download_cvrs.sh')}"
        )

    for cvr_dir, contest, year, office, name, race_id, stv, source in ALASKA:
        cmd = [
            sys.executable, str(HERE / "process_dominion_cvr.py"),
            "--cvr-dir", str(RAW / cvr_dir), "--contest", contest,
            "--state", "AK", "--year", str(year), "--office", office,
            "--race-name", name, "--race-id", race_id, "--source", source,
        ]
        if stv:
            cmd += ["--stv-seats", str(stv)]
        subprocess.run(cmd, check=True)

    subprocess.run([sys.executable, str(HERE / "fetch_ranked_vote.py")], check=True)
    subprocess.run([sys.executable, str(HERE / "official_reports.py")], check=True)
    print("\nAll races rebuilt. Next: cd viz && python3 scripts/prepare_data.py")


if __name__ == "__main__":
    main()
