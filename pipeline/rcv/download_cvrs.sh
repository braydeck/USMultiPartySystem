#!/usr/bin/env bash
# Download and unpack the Alaska Division of Elections cast vote record exports
# used by pipeline/rcv/build_all.py. ~130 MB compressed, ~4 GB unpacked, and
# gitignored (data/raw/rcv/). Maine's races are fetched over HTTP at build time
# by fetch_ranked_vote.py and need nothing here.
set -euo pipefail

cd "$(dirname "$0")/../.."
DEST="data/raw/rcv"
mkdir -p "$DEST"

fetch() {
  local name="$1" url="$2"
  if [ -d "$DEST/$name" ]; then
    echo "$name already present, skipping"
    return
  fi
  echo "Downloading $name …"
  curl -fL --retry 3 -o "$DEST/$name.zip" "$url"
  unzip -oq "$DEST/$name.zip" -d "$DEST/$name"
  rm "$DEST/$name.zip"
}

fetch AK_2022_special "https://www.elections.alaska.gov/results/22SSPG/CVR_Export_20220908084311.zip"
fetch AK_2022_general "https://elections.alaska.gov/results/22GENR/rcv/CVR_Export.zip"
fetch AK_2024_general "https://www.elections.alaska.gov/results/24GENR/CVR_Export_20241130154411.zip"

echo "Done. Next: python pipeline/rcv/build_all.py"
