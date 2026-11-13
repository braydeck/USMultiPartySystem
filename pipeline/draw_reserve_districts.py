#!/usr/bin/env python3
"""draw_reserve_districts.py: retired 2026-11-11. The reserve maps are drawn with the base maps by
draw_geographic_districts.py, which now writes each map's district apportionment, county map and
ZIP-area splits together, sizing every district from the people it holds. This entry point runs
that drawer for the two reserve maps so an old command still produces the current map.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_geographic_districts import main  # noqa: E402

if __name__ == "__main__":
    main(["reserve", "triple_reserve"])
