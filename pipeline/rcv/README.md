# RCV Pipeline — Alaska & Maine Cast Vote Records

## Data Sources

### Alaska Division of Elections
Election records: https://www.elections.alaska.gov/results/

Download CVR files (CSV format) for:

| Race | File to download | `--race` prefix |
|------|-----------------|-----------------|
| 2022 US House Special (Aug) | RCV results from August 2022 special election | `"US Representative"` |
| 2022 US House General (Nov) | RCV results from November 2022 general | `"US Representative"` |
| 2022 US Senate | November 2022 general election | `"United States Senator"` |
| 2022 Governor | November 2022 general election | `"Governor"` |
| 2024 US House | November 2024 general election | `"US Representative"` |

Save files to `data/raw/rcv/` with names like:
- `AK_2022_house_special.csv`
- `AK_2022_house_general.csv`
- `AK_2022_senate.csv`
- `AK_2022_governor.csv`
- `AK_2024_house.csv`

### Maine Secretary of State
Election records: https://www.maine.gov/sos/cec/elec/results/

Download CVR files for:

| Race | File | `--race` prefix |
|------|------|-----------------|
| 2018 US House CD2 | 2018 general election | `"Representative to Congress"` |
| 2022 US House CD2 | 2022 general election | `"Representative to Congress"` |
| 2024 US House CD2 | 2024 general election | `"Representative to Congress"` |

Save files to `data/raw/rcv/` with names like:
- `ME_2018_house_cd2.csv`
- `ME_2022_house_cd2.csv`
- `ME_2024_house_cd2.csv`

## Running the Pipeline

Run once per race file. From the project root:

```bash
# Alaska 2022 House General
python pipeline/rcv/process_rcv.py \
  --cvr data/raw/rcv/AK_2022_house_general.csv \
  --race "US Representative" \
  --state AK --year 2022 --office US_HOUSE --seats 2

# Alaska 2022 Senate
python pipeline/rcv/process_rcv.py \
  --cvr data/raw/rcv/AK_2022_senate.csv \
  --race "United States Senator" \
  --state AK --year 2022 --office US_SENATE

# Alaska 2022 Governor
python pipeline/rcv/process_rcv.py \
  --cvr data/raw/rcv/AK_2022_governor.csv \
  --race "Governor" \
  --state AK --year 2022 --office GOVERNOR

# Alaska 2024 House
python pipeline/rcv/process_rcv.py \
  --cvr data/raw/rcv/AK_2024_house.csv \
  --race "US Representative" \
  --state AK --year 2024 --office US_HOUSE --seats 2

# Maine 2018 CD2
python pipeline/rcv/process_rcv.py \
  --cvr data/raw/rcv/ME_2018_house_cd2.csv \
  --race "Representative to Congress" \
  --state ME --year 2018 --office US_HOUSE --seats 4

# Maine 2022 CD2
python pipeline/rcv/process_rcv.py \
  --cvr data/raw/rcv/ME_2022_house_cd2.csv \
  --race "Representative to Congress" \
  --state ME --year 2022 --office US_HOUSE --seats 4

# Maine 2024 CD2
python pipeline/rcv/process_rcv.py \
  --cvr data/raw/rcv/ME_2024_house_cd2.csv \
  --race "Representative to Congress" \
  --state ME --year 2024 --office US_HOUSE --seats 4
```

After running all races, regenerate the viz JSON:

```bash
cd viz && python3 scripts/prepare_data.py
```

## CVR Format Notes

- AK CVRs use rank columns like `"US Representative 1st Choice"`, `"US Representative 2nd Choice"`, etc.
- ME CVRs use rank columns like `"Representative to Congress - District 2 1st Choice"`, etc.
- Blank ranks, "overvote", and "undervote" are treated as exhausted preferences.

## USDA RUCC Codes (for County Tier Map)

Download `rucc2013.xlsx` from USDA ERS:
https://www.ers.usda.gov/data-products/rural-urban-continuum-codes/

Save as `data/raw/rucc2013.csv` (export from Excel). Columns needed: `FIPS`, `RUCC_2013`.

Tier mapping:
- RUCC 1–3 → URBAN (metropolitan counties)
- RUCC 4–5 → SUBURBAN (micropolitan + adjacent nonmetro)
- RUCC 6–9 → RURAL (small town + open country)
