#!/usr/bin/env python3
"""
hexmap_io.py
------------
Minimal ESRI shapefile (.shp/.dbf) reader for the Downballot congressional-district
hexmap, plus a TopoJSON county-centroid helper.

Only the shape types the hexmap actually uses are supported: Polygon (5). No GDAL,
shapely, or geopandas dependency — the hexmap is a few hundred convex polygons and
the seat cartogram works on hex-lattice adjacency rather than polygon algebra.

Source data: data/raw/hexmap/ — Congressional District Hexmap v3.1/v3.2 by
Daniel Donner for The Downballot (https://the-db.co/maps), CC BY 4.0.
"""

import struct
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
HEXMAP_DIR = BASE_DIR / "data" / "raw" / "hexmap"


def read_dbf(path):
    """Return a list of dicts, one per record, all values as stripped strings."""
    with open(path, "rb") as f:
        header = f.read(32)
        n_records, header_len, record_len = struct.unpack("<IHH", header[4:12])
        fields = []
        while True:
            desc = f.read(32)
            if desc[0:1] in (b"\r", b""):
                break
            fields.append((desc[:11].rstrip(b"\x00").decode(), desc[16]))
        f.seek(header_len)
        rows = []
        for _ in range(n_records):
            raw = f.read(record_len)
            offset = 1  # first byte is the deletion flag
            row = {}
            for name, length in fields:
                row[name] = raw[offset:offset + length].decode("latin1").strip()
                offset += length
            rows.append(row)
    return rows


def read_shp_polygons(path):
    """Return one list-of-rings per shape record; each ring is a list of (x, y).

    Ring orientation follows the shapefile spec: clockwise = outer, counter-clockwise
    = hole. The hexmap has no holes, so callers can treat every ring as an outer ring.
    """
    data = Path(path).read_bytes()
    shapes = []
    offset = 100  # main file header
    while offset < len(data):
        _, content_len = struct.unpack(">II", data[offset:offset + 8])
        rec = data[offset + 8: offset + 8 + content_len * 2]
        offset += 8 + content_len * 2
        shape_type = struct.unpack("<I", rec[0:4])[0]
        if shape_type == 0:  # null shape
            shapes.append([])
            continue
        if shape_type != 5:
            raise ValueError(f"{path}: unsupported shape type {shape_type}")
        n_parts, n_points = struct.unpack("<II", rec[36:44])
        parts = struct.unpack(f"<{n_parts}I", rec[44:44 + 4 * n_parts])
        pts_start = 44 + 4 * n_parts
        coords = struct.unpack(f"<{2 * n_points}d", rec[pts_start:pts_start + 16 * n_points])
        pts = list(zip(coords[0::2], coords[1::2]))
        bounds = list(parts) + [n_points]
        shapes.append([pts[bounds[i]:bounds[i + 1]] for i in range(n_parts)])
    return shapes


def load_layer(name, shp_stem=None):
    """Load a hexmap layer as a list of (attributes, rings) tuples."""
    folder = HEXMAP_DIR / name
    stem = shp_stem or name
    attrs = read_dbf(folder / f"{stem}.dbf")
    geoms = read_shp_polygons(folder / f"{stem}.shp")
    if len(attrs) != len(geoms):
        raise ValueError(f"{name}: {len(attrs)} dbf records vs {len(geoms)} shapes")
    return list(zip(attrs, geoms))


# ── TopoJSON county centroids ────────────────────────────────────────────────

def county_centroids(topo_path):
    """Map 5-digit county FIPS → (lon, lat) area-weighted centroid.

    Positions are only used to decide which corner of a distorted state hex-blob a
    district sits in, so a ring centroid is accurate enough.
    """
    import json

    topo = json.loads(Path(topo_path).read_text())
    tf = topo["transform"]
    sx, sy = tf["scale"]
    tx, ty = tf["translate"]

    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def ring_points(arc_ids):
        pts = []
        for i in arc_ids:
            seg = arcs[~i][::-1] if i < 0 else arcs[i]
            pts.extend(seg if not pts else seg[1:])
        return pts

    def ring_centroid(pts):
        """Shoelace centroid; falls back to the vertex mean on a degenerate ring."""
        a = cx = cy = 0.0
        for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
            cross = x0 * y1 - x1 * y0
            a += cross
            cx += (x0 + x1) * cross
            cy += (y0 + y1) * cross
        if a == 0:
            n = len(pts)
            return sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n, 0.0
        return cx / (3 * a), cy / (3 * a), abs(a / 2)

    out = {}
    for geom in topo["objects"]["counties"]["geometries"]:
        fips = str(geom.get("id", "")).zfill(5)
        rings = geom.get("arcs") or []
        if geom["type"] == "Polygon":
            rings = [rings]
        elif geom["type"] != "MultiPolygon":
            continue
        parts = []
        for poly in rings:
            if not poly:
                continue
            cx, cy, area = ring_centroid(ring_points(poly[0]))
            parts.append((cx, cy, area))
        if not parts:
            continue
        total = sum(p[2] for p in parts)
        if total > 0:
            out[fips] = (
                sum(p[0] * p[2] for p in parts) / total,
                sum(p[1] * p[2] for p in parts) / total,
            )
        else:
            out[fips] = (parts[0][0], parts[0][1])
    return out
