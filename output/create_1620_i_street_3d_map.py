from __future__ import annotations

import html
import json
import math
from pathlib import Path


DATA_PATH = Path("output/data/1620_i_street_osm.json")
OUT_DIR = Path("output/images")
TARGET_WAY_ID = 55326896
TARGET_LAT = 38.9010865
TARGET_LON = -77.0375014


def mercator_meters(lat: float, lon: float) -> tuple[float, float]:
    radius = 6378137.0
    x = math.radians(lon) * radius
    y = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * radius
    return x, y


def project(lat: float, lon: float, center: tuple[float, float], scale: float, width: int, height: int) -> tuple[float, float]:
    x, y = mercator_meters(lat, lon)
    dx = x - center[0]
    dy = y - center[1]

    # Rotate the map so I Street reads diagonally, closer to a Google Earth oblique view.
    angle = math.radians(-27)
    rx = dx * math.cos(angle) - dy * math.sin(angle)
    ry = dx * math.sin(angle) + dy * math.cos(angle)

    sx = width / 2 + rx * scale
    sy = height / 2 - ry * scale
    return sx, sy


def polygon_points(geometry: list[dict], center: tuple[float, float], scale: float, width: int, height: int) -> list[tuple[float, float]]:
    return [project(point["lat"], point["lon"], center, scale, width, height) for point in geometry]


def poly_to_svg(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
    if not points:
        return 0, 0
    return sum(x for x, _ in points) / len(points), sum(y for _, y in points) / len(points)


def path_from_points(points: list[tuple[float, float]]) -> str:
    if not points:
        return ""
    head, *tail = points
    parts = [f"M {head[0]:.1f} {head[1]:.1f}"]
    parts.extend(f"L {x:.1f} {y:.1f}" for x, y in tail)
    return " ".join(parts)


def draw_road(element: dict, points: list[tuple[float, float]]) -> str:
    highway = element.get("tags", {}).get("highway", "")
    name = element.get("tags", {}).get("name")
    if highway in {"footway", "path", "steps", "pedestrian"}:
        width = 3
        color = "#e8eef0"
        casing = "#cbd8de"
    elif highway in {"primary", "trunk", "secondary"}:
        width = 18
        color = "#b56f62" if name and "I Street" in name else "#d7dad8"
        casing = "#f8faf8"
    elif highway in {"tertiary", "living_street", "service"}:
        width = 10
        color = "#d1d8d7"
        casing = "#f8faf8"
    else:
        width = 7
        color = "#d8dfde"
        casing = "#f8faf8"

    d = path_from_points(points)
    if not d:
        return ""
    out = [
        f'<path d="{d}" fill="none" stroke="{casing}" stroke-width="{width + 5}" stroke-linecap="round" stroke-linejoin="round"/>',
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>',
    ]
    if name and ("I Street" in name or "16th Street" in name or "17th Street" in name):
        x, y = points[len(points) // 2]
        out.append(
            f'<text x="{x:.1f}" y="{y - width:.1f}" class="road-label" transform="rotate(-27 {x:.1f} {y - width:.1f})">{html.escape(name.replace("Northwest", "NW"))}</text>',
        )
    return "\n".join(out)


def draw_building(element: dict, points: list[tuple[float, float]]) -> str:
    tags = element.get("tags", {})
    is_target = element["id"] == TARGET_WAY_ID
    levels = float(tags.get("building:levels", 10 if is_target else 5))
    height = min(76, max(16, levels * 5.6))
    dx = height * 0.30
    dy = -height * 0.52

    roof = poly_to_svg(points)
    elevated = [(x + dx, y + dy) for x, y in points]
    elevated_svg = poly_to_svg(elevated)

    sides = []
    for i in range(len(points) - 1):
        p1 = points[i]
        p2 = points[i + 1]
        q2 = elevated[i + 1]
        q1 = elevated[i]
        avg_y = (p1[1] + p2[1]) / 2
        shade = "#718495" if avg_y > centroid(points)[1] else "#566878"
        if is_target:
            shade = "#8193a0" if avg_y > centroid(points)[1] else "#5e707d"
        sides.append(
            f'<polygon points="{poly_to_svg([p1, p2, q2, q1])}" fill="{shade}" stroke="#42505c" stroke-width="0.7"/>',
        )

    cx, cy = centroid(elevated)
    roof_fill = "#d7d1c5" if is_target else "#c6cfd2"
    roof_stroke = "#4c5964" if is_target else "#8b99a0"
    shadow = f'<polygon points="{poly_to_svg([(x + 18, y + 28) for x, y in points])}" fill="#1f2937" opacity="0.18"/>'
    out = [shadow, *sides, f'<polygon points="{elevated_svg}" fill="{roof_fill}" stroke="{roof_stroke}" stroke-width="{2.2 if is_target else 1.0}"/>']

    if is_target:
        # Rooftop mechanical penthouses, drawn schematically so the target has visual depth.
        out.extend(
            [
                f'<rect x="{cx - 64:.1f}" y="{cy - 45:.1f}" width="112" height="34" rx="2" fill="#f2f5f6" stroke="#acb6bd" transform="rotate(-27 {cx - 8:.1f} {cy - 28:.1f})"/>',
                f'<rect x="{cx - 24:.1f}" y="{cy + 4:.1f}" width="92" height="30" rx="2" fill="#eef2f4" stroke="#acb6bd" transform="rotate(-27 {cx + 22:.1f} {cy + 19:.1f})"/>',
                f'<rect x="{cx - 110:.1f}" y="{cy - 4:.1f}" width="46" height="18" fill="#a6b0b5" opacity="0.62" transform="rotate(-27 {cx - 87:.1f} {cy + 5:.1f})"/>',
                f'<text x="{cx - 18:.1f}" y="{cy + 88:.1f}" class="pin-label">1620 I STREET NW</text>',
                f'<circle cx="{cx - 30:.1f}" cy="{cy + 61:.1f}" r="10" fill="#f97316" stroke="#ffffff" stroke-width="3"/>',
            ],
        )
    elif tags.get("name"):
        out.append(f'<text x="{cx:.1f}" y="{cy:.1f}" class="place-label">{html.escape(tags["name"])}</text>')
    return "\n".join(out)


def main() -> None:
    data = json.loads(DATA_PATH.read_text())
    width, height = 1000, 760
    center = mercator_meters(TARGET_LAT, TARGET_LON)
    scale = 2.85

    roads = []
    buildings = []
    for element in data["elements"]:
        geometry = element.get("geometry") or []
        if len(geometry) < 2:
            continue
        points = polygon_points(geometry, center, scale, width, height)
        tags = element.get("tags", {})
        if tags.get("highway"):
            roads.append((element, points))
        elif tags.get("building") and len(points) >= 4:
            buildings.append((element, points))

    buildings.sort(key=lambda item: (item[0]["id"] == TARGET_WAY_ID, centroid(item[1])[1]))

    road_svg = "\n".join(draw_road(element, points) for element, points in roads)
    building_svg = "\n".join(draw_building(element, points) for element, points in buildings)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <linearGradient id="sky" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="#eef6f7"/>
      <stop offset="1" stop-color="#d6e6ea"/>
    </linearGradient>
    <filter id="soft-shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="8" dy="13" stdDeviation="8" flood-color="#26323c" flood-opacity="0.24"/>
    </filter>
  </defs>
  <style>
    .road-label {{ font: 600 18px Arial, Helvetica, sans-serif; fill: #ffffff; stroke: #45545f; stroke-width: 3px; paint-order: stroke; }}
    .place-label {{ font: 600 13px Arial, Helvetica, sans-serif; fill: #34404a; stroke: #ffffff; stroke-width: 3px; paint-order: stroke; text-anchor: middle; opacity: 0.82; }}
    .pin-label {{ font: 700 22px Arial, Helvetica, sans-serif; fill: #172033; stroke: #ffffff; stroke-width: 5px; paint-order: stroke; text-anchor: middle; }}
    .caption {{ font: 13px Arial, Helvetica, sans-serif; fill: #34404a; }}
    .title {{ font: 700 30px Arial, Helvetica, sans-serif; fill: #142033; }}
  </style>
  <rect width="100%" height="100%" fill="url(#sky)"/>
  <g opacity="0.55">
    <path d="M-60 595 C190 510 385 455 625 382 S890 250 1060 186" fill="none" stroke="#eef8fb" stroke-width="52"/>
    <path d="M-40 610 C210 525 400 470 635 398 S900 266 1060 202" fill="none" stroke="#c2d7dd" stroke-width="2"/>
  </g>
  <g>{road_svg}</g>
  <g filter="url(#soft-shadow)">{building_svg}</g>
  <g>
    <rect x="28" y="28" width="360" height="88" rx="6" fill="#ffffff" opacity="0.88"/>
    <text x="50" y="66" class="title">1620 I Street NW</text>
    <text x="50" y="94" class="caption">OSM building footprint rendered as an oblique 3D owner-audit locator</text>
    <text x="50" y="724" class="caption">Map data © OpenStreetMap contributors; building geometry source includes DCGIS tags in OSM.</text>
  </g>
</svg>
'''
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "1620_i_street_osm_3d.svg").write_text(svg)
    print(OUT_DIR / "1620_i_street_osm_3d.svg")


if __name__ == "__main__":
    main()
