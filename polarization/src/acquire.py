"""Acquire authoritative cross-national datasets for the polarization analysis.

Idempotent: skips any file already present in data/raw/. Each source is a stable,
openly-downloadable URL; if a download fails the script prints a manual-download
instruction rather than failing silently.

Sources
-------
- V-Dem (Varieties of Democracy) full dataset, via the `vdemdata` R package mirror.
  Provides the polarization variable itself (v2cacamps, used to validate the merge),
  the electoral-democracy index (v2x_polyarchy), lower-chamber electoral system
  (v2elparlel), bicameralism (v2lgbicam), regime type (v2x_regime), and executive
  structure variables. On first run the ~4600-column .RData is read once with pyreadr
  and a slim column subset is cached to vdem_slim.parquet.
- QoG Standard time-series (Jan 2025): government system (chga_hinst, Cheibub DD),
  colonial heritage (ht_colonial), and a democracy-score cross-check (vdem_polyarchy).
- QoG Standard cross-section (Jan 2022): La Porta legal origin (lp_legor), which was
  dropped from later QoG releases. Legal origin is time-invariant, so a single
  cross-section is sufficient.
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

SOURCES = {
    "vdem.RData": (
        "https://raw.githubusercontent.com/vdeminstitute/vdemdata/master/data/vdem.RData"
    ),
    "qog_std_ts_jan25.csv": "https://www.qogdata.pol.gu.se/data/qog_std_ts_jan25.csv",
    "qog_std_cs_jan22.csv": "https://www.qogdata.pol.gu.se/data/qog_std_cs_jan22.csv",
}

VDEM_SLIM = RAW / "vdem_slim.parquet"
VDEM_KEEP = [
    "country_name", "country_text_id", "country_id", "year",
    "v2cacamps", "v2cacamps_ord",        # political polarization (validation)
    "v2x_polyarchy", "v2x_regime",        # democracy score + regime type
    "v2elparlel",                          # lower-chamber electoral system
    "v2lgbicam",                           # bicameralism
    "v2exhoshog", "v2ex_elechos", "v2exaphogp",  # executive structure (cross-check)
]


def download(name: str, url: str) -> None:
    dest = RAW / name
    if dest.exists():
        print(f"[skip] {name} already present ({dest.stat().st_size/1e6:.1f} MB)")
        return
    print(f"[get ] {name} <- {url}")
    try:
        urllib.request.urlretrieve(url, dest)
        print(f"[ok  ] {name} ({dest.stat().st_size/1e6:.1f} MB)")
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] {name}: {exc}\n"
              f"       Download manually from {url} and place it at {dest}", file=sys.stderr)


def build_vdem_slim() -> None:
    if VDEM_SLIM.exists():
        print(f"[skip] vdem_slim.parquet already present")
        return
    import pyreadr
    print("[proc] reading vdem.RData (large; one-time) ...")
    vdem = pyreadr.read_r(str(RAW / "vdem.RData"))["vdem"]
    slim = vdem[VDEM_KEEP].copy()
    slim = slim[slim["year"] >= 1900]
    slim.to_parquet(VDEM_SLIM, index=False)
    print(f"[ok  ] vdem_slim.parquet {slim.shape}")


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        download(name, url)
    build_vdem_slim()
    print("\nAcquire complete. Files in", RAW)


if __name__ == "__main__":
    main()
