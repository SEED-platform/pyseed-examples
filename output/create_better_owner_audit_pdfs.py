from __future__ import annotations

import json
import re
from pathlib import Path


PAGE_W = 612
PAGE_H = 792
MARGIN = 42
DATA_PATH = Path("org412_cycle656_profile316_better.json")
OUT_DIR = Path("output/pdf/better_owner_audits")
METER_DIR = Path("output/data/top5_meters")
IMAGE_DIR = Path("output/images")
BUILDING_IMAGE_PATHS = {
    3282590: IMAGE_DIR / "1620_i_street_osm_3d.jpg",
}
OPENSTUDIO_DIR = Path("output/openstudio_1620")
OPENSTUDIO_MODEL_PATHS = {
    3282590: {
        "calibration_image": OPENSTUDIO_DIR / "1620_i_street_openstudio_calibration.jpg",
        "zoning_image": OPENSTUDIO_DIR / "1620_i_street_perimeter_core_10_story.jpg",
        "calibration_json": OPENSTUDIO_DIR / "1620_i_street_openstudio_calibration.json",
    },
}


def esc(text: object) -> str:
    value = "" if text is None else str(text)
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def safe_name(text: object) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", str(text).strip().lower())
    return re.sub(r"_+", "_", value).strip("_") or "building"


def display_name(column_name: str) -> str:
    name = re.sub(r"_\d+$", "", column_name)
    name = name.removeprefix("better_recommendation_")
    return name.replace("_", " ")


def active(value: object) -> bool:
    if value in (None, ""):
        return False
    try:
        return float(value) != 0
    except (TypeError, ValueError):
        return str(value).strip().casefold() in {"true", "yes", "y", "1"}


def num(value: object, digits: int = 0, prefix: str = "", suffix: str = "") -> str:
    if value in (None, ""):
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if digits == 0:
        return f"{prefix}{number:,.0f}{suffix}"
    return f"{prefix}{number:,.{digits}f}{suffix}"


def to_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def wrap(text: str, max_chars: int) -> list[str]:
    words = str(text).split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def jpeg_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    index = 2
    while index < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in {0xD8, 0xD9}:
            continue
        length = int.from_bytes(data[index : index + 2], "big")
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            height = int.from_bytes(data[index + 3 : index + 5], "big")
            width = int.from_bytes(data[index + 5 : index + 7], "big")
            return width, height
        index += length
    raise ValueError(f"Could not read JPEG dimensions for {path}")


class Page:
    def __init__(self) -> None:
        self.ops: list[str] = []
        self.images: list[Path] = []

    def raw(self, op: str) -> None:
        self.ops.append(op)

    def color(self, hex_color: str) -> None:
        hex_color = hex_color.strip("#")
        r = int(hex_color[0:2], 16) / 255
        g = int(hex_color[2:4], 16) / 255
        b = int(hex_color[4:6], 16) / 255
        self.raw(f"{r:.4f} {g:.4f} {b:.4f} rg")
        self.raw(f"{r:.4f} {g:.4f} {b:.4f} RG")

    def line_width(self, width: float) -> None:
        self.raw(f"{width:.2f} w")

    def rect(self, x: float, y: float, w: float, h: float, fill: str | None = None, stroke: str | None = None) -> None:
        if fill:
            self.color(fill)
            self.raw(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re f")
        if stroke:
            self.color(stroke)
            self.raw(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re S")

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str = "111111", width: float = 1) -> None:
        self.color(color)
        self.line_width(width)
        self.raw(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def text(self, x: float, y: float, text: object, size: int = 10, font: str = "F1", color: str = "111111") -> None:
        self.color(color)
        self.raw(f"BT /{font} {size} Tf {x:.2f} {y:.2f} Td ({esc(text)}) Tj ET")

    def multiline(
        self,
        x: float,
        y: float,
        text: str,
        size: int = 10,
        max_chars: int = 80,
        leading: float | None = None,
        font: str = "F1",
        color: str = "111111",
    ) -> float:
        leading = leading or size * 1.35
        for line in wrap(text, max_chars):
            self.text(x, y, line, size=size, font=font, color=color)
            y -= leading
        return y

    def metric(self, x: float, y: float, w: float, label: str, value: str, accent: str) -> None:
        self.rect(x, y, w, 58, fill="FFFFFF", stroke="D7DEE8")
        self.rect(x, y, 5, 58, fill=accent)
        self.text(x + 14, y + 38, label.upper(), size=8, font="F2", color="52616B")
        self.text(x + 14, y + 13, value, size=17, font="F2", color="111827")

    def image(self, x: float, y: float, w: float, h: float, path: Path) -> None:
        self.images.append(path)
        name = f"Im{len(self.images)}"
        self.raw(f"q {w:.2f} 0 0 {h:.2f} {x:.2f} {y:.2f} cm /{name} Do Q")


class PDF:
    def __init__(self) -> None:
        self.pages: list[Page] = []

    def add_page(self) -> Page:
        page = Page()
        self.pages.append(page)
        return page

    def save(self, path: Path) -> None:
        objects: list[bytes] = [
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        ]
        page_objects: list[tuple[int, int, list[tuple[str, int]]]] = []
        for page in self.pages:
            image_refs: list[tuple[str, int]] = []
            for index, image_path in enumerate(page.images, start=1):
                image_data = image_path.read_bytes()
                image_width, image_height = jpeg_dimensions(image_path)
                image_id = len(objects) + 1
                image_refs.append((f"Im{index}", image_id))
                objects.append(
                    b"<< /Type /XObject /Subtype /Image /Width "
                    + str(image_width).encode()
                    + b" /Height "
                    + str(image_height).encode()
                    + b" /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length "
                    + str(len(image_data)).encode()
                    + b" >>\nstream\n"
                    + image_data
                    + b"\nendstream",
                )
            stream = "\n".join(page.ops).encode("latin-1", "replace")
            content = b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
            content_id = len(objects) + 1
            objects.append(content)
            page_id = len(objects) + 1
            page_objects.append((page_id, content_id, image_refs))
            objects.append(b"")

        pages_id = len(objects) + 1
        kids = " ".join(f"{page_id} 0 R" for page_id, _, _ in page_objects).encode()
        objects.append(b"<< /Type /Pages /Kids [" + kids + b"] /Count " + str(len(page_objects)).encode() + b" >>")
        catalog_id = len(objects) + 1
        objects.append(b"<< /Type /Catalog /Pages " + str(pages_id).encode() + b" 0 R >>")

        for page_id, content_id, image_refs in page_objects:
            xobjects = b""
            if image_refs:
                pairs = " ".join(f"/{name} {obj_id} 0 R" for name, obj_id in image_refs).encode()
                xobjects = b" /XObject << " + pairs + b" >>"
            objects[page_id - 1] = (
                b"<< /Type /Page /Parent "
                + str(pages_id).encode()
                + b" 0 R /MediaBox [0 0 612 792] "
                + b"/Resources << /Font << /F1 1 0 R /F2 2 0 R >>"
                + xobjects
                + b" >> "
                + b"/Contents "
                + str(content_id).encode()
                + b" 0 R >>"
            )

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for obj_id, obj in enumerate(objects, start=1):
            offsets.append(len(out))
            out.extend(f"{obj_id} 0 obj\n".encode())
            out.extend(obj)
            out.extend(b"\nendobj\n")
        xref = len(out)
        out.extend(f"xref\n0 {len(objects) + 1}\n".encode())
        out.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            out.extend(f"{offset:010d} 00000 n \n".encode())
        out.extend(
            b"trailer\n<< /Size "
            + str(len(objects) + 1).encode()
            + b" /Root "
            + str(catalog_id).encode()
            + b" 0 R >>\nstartxref\n"
            + str(xref).encode()
            + b"\n%%EOF\n",
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(out)


RECOMMENDATION_NOTES = {
    "reduce lighting load": "Review fixture types, controls, schedules, common areas, parking, and tenant lighting density.",
    "reduce plug loads": "Inventory tenant equipment, common plug loads, vending, IT/server loads, and after-hours usage.",
    "reduce equipment schedules": "Confirm occupied/unoccupied schedules, weekend operation, overrides, and BAS trend logs.",
    "decrease heating setpoints": "Review winter setpoints, night setback, warm-up routines, and simultaneous heating/cooling.",
    "increase cooling setpoints": "Review summer setpoints, deadbands, after-hours cooling, and tenant comfort constraints.",
    "decrease infiltration": "Inspect entry vestibules, loading doors, envelope leakage, shafts, stair pressurization, and exhaust imbalance.",
    "increase cooling system efficiency": "Review cooling equipment age, economizer operation, resets, condenser cleaning, and controls.",
    "increase heating system efficiency": "Review boilers, heat pumps, steam/hot water distribution, reset schedules, and maintenance records.",
    "add wall/ceiling/roof insulation": "Screen envelope assemblies and roof condition before scoping envelope measures.",
    "upgrade windows to improve thermal efficiency": "Review window U-factor, air leakage, condensation, comfort complaints, and replacement timing.",
    "upgrade windows to reduce solar heat gain": "Review glazing SHGC, facade orientation, solar control, and cooling complaints.",
    "ensure adequate ventilation rate": "Verify outdoor air rates, demand-control ventilation, economizer minimum positions, and code constraints.",
    "use high efficiency heat pump for heating": "Evaluate electrification feasibility, service capacity, distribution constraints, and refrigerant strategy.",
    "upgrade to sustainable resources for water heating": "Review domestic hot water loads, heat pump water heating, solar thermal, and heat recovery options.",
}


def load_ranked_buildings() -> list[dict]:
    rows = json.loads(DATA_PATH.read_text())["656"]
    rec_cols = [key for key in rows[0] if key.startswith("better_recommendation_")]
    ranked = []
    for row in rows:
        recs = [display_name(col) for col in rec_cols if active(row.get(col))]
        ranked.append(
            {
                "rank_score": len(recs),
                "property_view_id": row.get("property_view_id"),
                "property_state_id": row.get("property_state_id"),
                "pm_property_id": row.get("pm_property_id_90594"),
                "address": row.get("address_line_1_90603") or row.get("Reported Address_90689"),
                "city": row.get("city_90607"),
                "state": row.get("state_90609"),
                "postal_code": row.get("postal_code_90613"),
                "name": row.get("property_name_90616") or row.get("address_line_1_90603"),
                "type": row.get("property_type_90633") or row.get("Property Tyoe (EPA)_90696"),
                "gfa": row.get("gross_floor_area_90629") or row.get("gross_floor_area_reported_90699"),
                "site_eui": row.get("site_eui_weather_normalized_90650") or row.get("site_eui_90649"),
                "source_eui": row.get("source_eui_weather_normalized_90653") or row.get("source_eui_90652"),
                "energy_score": row.get("energy_score_90631"),
                "year_built": row.get("year_built_90639"),
                "ward": row.get("Ward_90687"),
                "reporting_status": row.get("Reporting Status_90683"),
                "metered_areas": row.get("Metered Areas (Energy)_90716"),
                "longitude": row.get("Unused X_90667"),
                "latitude": row.get("Unused Y_90669"),
                "long_lat": row.get("long_lat"),
                "footprint": row.get("property_footprint_90623") or row.get("centroid"),
                "bounding_box": row.get("bounding_box"),
                "cost_savings": row.get("better_cost_savings_combined_90835"),
                "energy_savings": row.get("better_energy_savings_combined_90836"),
                "ghg_reductions": row.get("better_ghg_reductions_combined_90837"),
                "valid_electric": row.get("better_valid_model_electricity_90838"),
                "valid_fuel": row.get("better_valid_model_fuel_90839"),
                "min_r2": row.get("better_min_model_r_squared_90848"),
                "recommendations": recs,
            },
        )
    ranked.sort(key=lambda item: (item["rank_score"], item["cost_savings"] or -1), reverse=True)
    return ranked


def load_meter_summary(property_view_id: int) -> dict:
    meters_path = METER_DIR / f"{property_view_id}_meters.json"
    if not meters_path.exists():
        return {"meters": [], "monthly": [], "fuel_totals": {}, "annual_total": 0}

    meters = json.loads(meters_path.read_text())
    fuel_totals: dict[str, float] = {}
    monthly: dict[str, float] = {}
    meter_rows = []
    for meter in meters:
        meter_id = meter["id"]
        readings_path = METER_DIR / f"{property_view_id}_meter_{meter_id}_readings.json"
        readings = json.loads(readings_path.read_text()) if readings_path.exists() else []
        annual = 0.0
        for reading in readings:
            start = str(reading.get("start_time", ""))
            if not start.startswith("2022"):
                continue
            value = to_float(reading.get("reading")) or 0.0
            annual += value
            month = start[5:7]
            monthly[month] = monthly.get(month, 0.0) + value
        fuel_type = meter.get("type") or "Unknown"
        fuel_totals[fuel_type] = fuel_totals.get(fuel_type, 0.0) + annual
        meter_rows.append(
            {
                "id": meter_id,
                "type": fuel_type,
                "alias": meter.get("alias") or f"Meter {meter_id}",
                "readings": len(readings),
                "annual": annual,
            },
        )

    ordered_months = [
        ("Jan", monthly.get("01", 0.0)),
        ("Feb", monthly.get("02", 0.0)),
        ("Mar", monthly.get("03", 0.0)),
        ("Apr", monthly.get("04", 0.0)),
        ("May", monthly.get("05", 0.0)),
        ("Jun", monthly.get("06", 0.0)),
        ("Jul", monthly.get("07", 0.0)),
        ("Aug", monthly.get("08", 0.0)),
        ("Sep", monthly.get("09", 0.0)),
        ("Oct", monthly.get("10", 0.0)),
        ("Nov", monthly.get("11", 0.0)),
        ("Dec", monthly.get("12", 0.0)),
    ]
    return {
        "meters": meter_rows,
        "monthly": ordered_months,
        "fuel_totals": fuel_totals,
        "annual_total": sum(fuel_totals.values()),
    }


def parse_point(wkt: object) -> tuple[float, float] | None:
    match = re.search(r"POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)", str(wkt or ""))
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def parse_polygon(wkt: object) -> list[tuple[float, float]]:
    match = re.search(r"POLYGON\s*\(\((.*?)\)\)", str(wkt or ""))
    if not match:
        return []
    points = []
    for pair in match.group(1).split(","):
        parts = pair.strip().split()
        if len(parts) >= 2:
            points.append((float(parts[0]), float(parts[1])))
    return points


def google_maps_3d_url(building: dict) -> str:
    lat = to_float(building.get("latitude"))
    lon = to_float(building.get("longitude"))
    point = parse_point(building.get("long_lat"))
    if point and (lat is None or lon is None):
        lon, lat = point
    if lat is None or lon is None:
        query = str(building.get("address") or "").replace(" ", "+")
        return f"https://www.google.com/maps/search/?api=1&query={query}"
    return f"https://www.google.com/maps/@{lat:.7f},{lon:.7f},20z/data=!3m1!1e3"


def header(page: Page, title: str, subtitle: str, page_no: int) -> None:
    page.rect(0, 746, PAGE_W, 46, fill="0B94CF")
    page.rect(360, 746, 252, 46, fill="087CB2")
    page.text(MARGIN, 764, title, size=19, font="F2", color="FFFFFF")
    page.text(MARGIN, 750, subtitle, size=9, color="EAF7FC")
    page.text(520, 764, "SEED", size=15, font="F2", color="FFFFFF")
    page.text(520, 750, f"page {page_no}", size=8, color="EAF7FC")


def small_table(page: Page, x: float, y: float, rows: list[tuple[str, str]], key_w: float = 145, val_w: float = 365) -> float:
    row_h = 21
    for i, (key, value) in enumerate(rows):
        page.rect(x, y - row_h + 4, key_w + val_w, row_h, fill="F4F7FA" if i % 2 == 0 else "FFFFFF")
        page.text(x + 8, y - 11, key, size=8, font="F2", color="3F4854")
        page.text(x + key_w + 8, y - 11, value, size=8, color="111827")
        y -= row_h
    return y


def bullet(page: Page, x: float, y: float, text: str, max_chars: int = 82, color: str = "0B94CF") -> float:
    page.rect(x, y - 3, 4, 4, fill=color)
    return page.multiline(x + 13, y - 5, text, size=9, max_chars=max_chars, leading=12)


def bar_chart(page: Page, x: float, y: float, w: float, h: float, labels: list[str], values: list[float], color: str) -> None:
    max_value = max(values) if values else 1
    max_value = max(max_value, 1)
    page.line(x, y, x, y + h, color="334155", width=0.7)
    page.line(x, y, x + w, y, color="334155", width=0.7)
    gap = 5
    bar_w = (w - gap * (len(values) - 1)) / max(len(values), 1)
    for index, value in enumerate(values):
        bx = x + index * (bar_w + gap)
        bh = h * value / max_value
        page.rect(bx, y, bar_w, bh, fill=color)
        page.text(bx - 1, y - 14, labels[index], size=6, color="334155")
    page.text(x + w + 8, y + h - 4, num(max_value, 0), size=7, color="52616B")
    page.text(x + w + 8, y - 2, "0", size=7, color="52616B")


def stacked_fuel_bar(page: Page, x: float, y: float, w: float, h: float, fuel_totals: dict[str, float]) -> None:
    colors = {
        "Electric - Grid": "0B94CF",
        "Natural Gas": "D9901A",
        "District Hot Water": "B42318",
        "District Chilled Water": "2563A6",
        "Custom Meter": "7C3AED",
    }
    total = sum(fuel_totals.values()) or 1
    page.rect(x, y, w, h, fill="DDEAF2")
    cursor = x
    for fuel, value in sorted(fuel_totals.items(), key=lambda item: item[1], reverse=True):
        width = w * value / total
        page.rect(cursor, y, width, h, fill=colors.get(fuel, "52616B"))
        cursor += width
    label_y = y - 18
    label_x = x
    for fuel, value in sorted(fuel_totals.items(), key=lambda item: item[1], reverse=True)[:4]:
        page.rect(label_x, label_y + 2, 7, 7, fill=colors.get(fuel, "52616B"))
        page.text(label_x + 11, label_y, f"{fuel}: {value / total:.0%}", size=7, color="334155")
        label_x += 130


def draw_location_panel(page: Page, building: dict, x: float, y: float, w: float, h: float) -> None:
    lat = to_float(building.get("latitude"))
    lon = to_float(building.get("longitude"))
    point = parse_point(building.get("long_lat"))
    if point and (lat is None or lon is None):
        lon, lat = point
    footprint = parse_polygon(building.get("footprint"))
    bbox = parse_polygon(building.get("bounding_box"))

    page.rect(x, y, w, h, fill="EAF7FC", stroke="B8D9E8")
    for i in range(1, 6):
        gx = x + w * i / 6
        gy = y + h * i / 6
        page.line(gx, y, gx, y + h, color="C8E5F0", width=0.4)
        page.line(x, gy, x + w, gy, color="C8E5F0", width=0.4)

    page.rect(x + 24, y + 22, w - 48, h - 44, fill="DDEAF2", stroke="FFFFFF")
    page.line(x + 24, y + 70, x + w - 24, y + h - 60, color="FFFFFF", width=8)
    page.line(x + 70, y + 22, x + w - 70, y + h - 22, color="FFFFFF", width=6)
    page.line(x + 30, y + h - 86, x + w - 34, y + h - 40, color="9ECFE4", width=4)

    map_points = footprint or bbox
    if map_points:
        min_lon = min(p[0] for p in map_points)
        max_lon = max(p[0] for p in map_points)
        min_lat = min(p[1] for p in map_points)
        max_lat = max(p[1] for p in map_points)
        if max_lon == min_lon:
            max_lon += 0.0001
            min_lon -= 0.0001
        if max_lat == min_lat:
            max_lat += 0.0001
            min_lat -= 0.0001
        sx = (w - 110) / (max_lon - min_lon)
        sy = (h - 96) / (max_lat - min_lat)
        coords = []
        for px, py in map_points:
            mx = x + 55 + (px - min_lon) * sx
            my = y + 48 + (py - min_lat) * sy
            coords.append((mx, my))
        if len(coords) >= 3:
            page.color("0B94CF")
            page.raw(f"{coords[0][0]:.2f} {coords[0][1]:.2f} m")
            for px, py in coords[1:]:
                page.raw(f"{px:.2f} {py:.2f} l")
            page.raw("h f")
            page.color("183F6D")
            page.raw(f"{coords[0][0] + 10:.2f} {coords[0][1] + 14:.2f} m")
            for px, py in coords[1:]:
                page.raw(f"{px + 10:.2f} {py + 14:.2f} l")
            page.raw("h f")
            page.color("1B6257")
            page.raw(f"{coords[0][0]:.2f} {coords[0][1]:.2f} m")
            for px, py in coords[:4]:
                page.raw(f"{px + 10:.2f} {py + 14:.2f} l")
            page.raw("S")
    else:
        cx, cy = x + w / 2, y + h / 2
        page.rect(cx - 24, cy - 16, 48, 32, fill="0B94CF")
        page.rect(cx - 14, cy - 6, 48, 32, fill="183F6D")
        page.rect(cx - 4, cy + 4, 48, 32, fill="1B6257")

    page.rect(x + w / 2 - 4, y + h / 2 - 4, 8, 8, fill="B42318")
    if lat is not None and lon is not None:
        page.text(x + 14, y + 12, f"{lat:.6f}, {lon:.6f}", size=8, color="334155")


def draw_recommendation_bar(page: Page, count: int) -> None:
    x, y, w, h = MARGIN, 322, 510, 16
    page.rect(x, y, w, h, fill="DDEAF2")
    page.rect(x, y, w * min(count, 12) / 12, h, fill="D9901A" if count >= 8 else "0B94CF")
    for tick in [4, 8, 12]:
        tx = x + w * tick / 12
        page.line(tx, y - 4, tx, y + h + 4, color="FFFFFF", width=1)
    page.text(x, y + 24, "Active BETTER recommendations", size=8, font="F2", color="52616B")


def draw_cover(pdf: PDF, building: dict, rank: int) -> None:
    page = pdf.add_page()
    page.rect(0, 0, PAGE_W, PAGE_H, fill="FFFFFF")
    page.rect(0, 560, PAGE_W, 232, fill="183F6D")
    page.rect(0, 560, PAGE_W, 9, fill="D9901A")
    page.text(MARGIN, 716, "OWNER AUDIT", size=42, font="F2", color="FFFFFF")
    page.text(MARGIN, 674, "SCREENING REPORT", size=35, font="F2", color="FFFFFF")
    page.multiline(MARGIN, 626, building["name"], size=19, max_chars=42, leading=22, font="F2", color="FFFFFF")
    page.text(MARGIN, 594, f"{building['address']} | 2022 benchmarking cycle", size=11, color="DDEAF2")
    page.text(466, 738, "SEED", size=18, font="F2", color="FFFFFF")
    page.text(466, 718, "BETTER audit triage", size=8, color="DDEAF2")

    page.multiline(
        MARGIN,
        525,
        "Prepared from SEED and BETTER outputs. This screening packet helps owners evaluate candidate measures; it is not an onsite ASHRAE audit or engineering design.",
        size=10,
        max_chars=92,
        leading=14,
        color="334155",
    )

    page.metric(MARGIN, 445, 156, "Recommendation rank", f"#{rank}", "D9901A")
    page.metric(MARGIN + 174, 445, 156, "Active recs", str(building["rank_score"]), "B42318")
    page.metric(MARGIN + 348, 445, 156, "Cost savings", num(building["cost_savings"], 0, "$"), "1B6257")
    page.metric(MARGIN, 360, 156, "Property type", str(building["type"])[:18], "0B94CF")
    page.metric(MARGIN + 174, 360, 156, "Floor area", num(building["gfa"], 0, suffix=" ft2"), "0B94CF")
    page.metric(MARGIN + 348, 360, 156, "Site EUI", num(building["site_eui"], 1), "0B94CF")
    draw_recommendation_bar(page, building["rank_score"])

    page.text(MARGIN, 302, "Owner evaluation focus", size=15, font="F2", color="111827")
    y = 277
    y = bullet(page, MARGIN, y, f"Start with the {building['rank_score']} BETTER recommendations, then confirm which measures are feasible for this property's systems, leases, and capital plan.")
    y = bullet(page, MARGIN, y - 10, "Validate utility data, meter boundaries, occupancy schedules, and controls before assigning capital budgets.")
    y = bullet(page, MARGIN, y - 10, "Use this packet as a triage handoff: it identifies what to ask for, what to inspect, and which recommendations deserve owner review.")

    page.text(MARGIN, 92, "Prepared July 10, 2026", size=8, color="52616B")
    page.text(402, 92, "Org 412 | Cycle 656 | BPS - DC", size=8, color="52616B")


def draw_detail(pdf: PDF, building: dict, rank: int) -> None:
    page = pdf.add_page()
    header(page, "Building Status + BETTER Recommendations", f"Rank #{rank}: {building['name']}", 2)

    page.text(MARGIN, 710, "Building snapshot", size=15, font="F2")
    small_table(
        page,
        MARGIN,
        688,
        [
            ("Address", str(building["address"])),
            ("PM Property ID", str(building["pm_property_id"])),
            ("Property view ID", str(building["property_view_id"])),
            ("Type", str(building["type"])),
            ("Year built / Ward", f"{num(building['year_built'])} / {building['ward'] or '-'}"),
            ("Reporting status", str(building["reporting_status"] or "-")),
            ("Metered areas", str(building["metered_areas"] or "-")),
            ("Energy score", num(building["energy_score"], 0)),
            ("Source EUI", num(building["source_eui"], 1)),
        ],
    )

    page.text(MARGIN, 465, "BETTER outputs", size=15, font="F2")
    small_table(
        page,
        MARGIN,
        443,
        [
            ("Active recommendations", str(building["rank_score"])),
            ("Combined energy savings", num(building["energy_savings"], 0, suffix=" kBtu")),
            ("Combined cost savings", num(building["cost_savings"], 0, "$")),
            ("GHG reductions", num(building["ghg_reductions"], 1, suffix=" mtCO2e")),
            ("Electric model valid", str(building["valid_electric"])),
            ("Fuel model valid", str(building["valid_fuel"])),
            ("Minimum model R2", num(building["min_r2"], 2)),
        ],
    )

    page.text(MARGIN, 260, "Priority recommendation notes", size=15, font="F2")
    y = 236
    for index, rec in enumerate(building["recommendations"][:12], start=1):
        note = RECOMMENDATION_NOTES.get(rec, "Review feasibility, operating constraints, savings estimate, and interaction with other measures.")
        page.text(MARGIN, y, f"{index}. {rec}", size=10, font="F2", color="183F6D")
        y = page.multiline(MARGIN + 18, y - 14, note, size=8, max_chars=82, leading=10, color="334155")
        y -= 5
        if y < 54:
            break


def draw_complete_recommendations(pdf: PDF, building: dict, rank: int) -> None:
    page = pdf.add_page()
    header(page, "Complete BETTER Recommendation List", f"Rank #{rank}: {building['name']}", 3)
    page.multiline(
        MARGIN,
        708,
        f"This building has {building['rank_score']} active BETTER recommendation flags. Use this page as the owner's complete review list; the previous page includes detailed notes for the first priority items.",
        size=11,
        max_chars=88,
        leading=15,
    )

    left_x = MARGIN
    right_x = 320
    y_left = 642
    y_right = 642
    for index, rec in enumerate(building["recommendations"], start=1):
        x = left_x if index <= 6 else right_x
        y = y_left if index <= 6 else y_right
        page.rect(x, y - 3, 5, 5, fill="D9901A")
        next_y = page.multiline(x + 15, y, f"{index}. {rec}", size=11, max_chars=38, leading=14, font="F2", color="183F6D")
        if index <= 6:
            y_left = next_y - 16
        else:
            y_right = next_y - 16

    page.rect(MARGIN, 92, 510, 184, fill="F7F6F3", stroke="D7DEE8")
    page.text(MARGIN + 16, 250, "How to use this list", size=12, font="F2", color="111827")
    y = 226
    for item in [
        "Confirm whether each flag is operational, controls-related, envelope-related, or capital-project related.",
        "Bundle interacting measures before estimating savings, especially HVAC setpoints, schedules, and equipment efficiency.",
        "Ask the owner or operator which measures are already planned, recently completed, or infeasible because of tenant constraints.",
    ]:
        y = bullet(page, MARGIN + 16, y, item, max_chars=78, color="183F6D")
        y -= 6


def draw_meter_consumption(pdf: PDF, building: dict, rank: int) -> None:
    page = pdf.add_page()
    header(page, "2022 Meter Consumption", f"Rank #{rank}: {building['name']}", 4)
    summary = load_meter_summary(building["property_view_id"])
    annual_total = summary["annual_total"]
    gfa = to_float(building.get("gfa")) or 0.0
    intensity = annual_total / gfa if gfa else 0.0

    page.multiline(
        MARGIN,
        708,
        "This page uses SEED meter readings for calendar year 2022. Values below are reported in kBtu from the SEED meter endpoint and should be reconciled with the owner utility bills before project scoping.",
        size=10,
        max_chars=90,
        leading=14,
        color="334155",
    )

    page.metric(MARGIN, 632, 156, "Annual meter use", num(annual_total, 0, suffix=" kBtu"), "183F6D")
    page.metric(MARGIN + 174, 632, 156, "Meter intensity", num(intensity, 1, suffix=" kBtu/ft2"), "0B94CF")
    page.metric(MARGIN + 348, 632, 156, "Meters found", str(len(summary["meters"])), "1B6257")

    page.text(MARGIN, 570, "Fuel split", size=14, font="F2", color="111827")
    if summary["fuel_totals"]:
        stacked_fuel_bar(page, MARGIN, 536, 510, 20, summary["fuel_totals"])
    else:
        page.rect(MARGIN, 520, 510, 42, fill="F7F6F3", stroke="D7DEE8")
        page.text(MARGIN + 16, 540, "No meter readings were available in the local SEED export.", size=9, color="334155")

    page.text(MARGIN, 470, "Monthly 2022 profile", size=14, font="F2", color="111827")
    labels = [label for label, _ in summary["monthly"]]
    values = [value for _, value in summary["monthly"]]
    bar_chart(page, MARGIN + 2, 328, 448, 112, labels, values, "0B94CF")
    page.text(MARGIN + 462, 438, "kBtu", size=8, font="F2", color="52616B")

    page.text(MARGIN, 286, "Meter inventory", size=14, font="F2", color="111827")
    rows = []
    for meter in summary["meters"][:7]:
        rows.append(
            (
                f"{meter['id']} | {meter['type']}",
                f"{num(meter['annual'], 0, suffix=' kBtu')} | {meter['readings']} readings",
            ),
        )
    if not rows:
        rows = [("SEED meters", "No meters found for this property view in the local export")]
    small_table(page, MARGIN, 264, rows, key_w=205, val_w=305)

    page.rect(MARGIN, 88, 510, 60, fill="F7F6F3", stroke="D7DEE8")
    page.text(MARGIN + 16, 126, "Owner follow-up", size=11, font="F2", color="111827")
    page.multiline(
        MARGIN + 16,
        108,
        "If the meter total, EUI, or fuel mix looks surprising, verify meter boundaries, tenant submeters, vacancies, bulk fuel, and Portfolio Manager import status before approving a measure package.",
        size=8,
        max_chars=95,
        leading=11,
        color="334155",
    )


def draw_location_page(pdf: PDF, building: dict, rank: int) -> None:
    page = pdf.add_page()
    header(page, "Building Location + 3D Map Link", f"Rank #{rank}: {building['name']}", 5)

    property_view_id = int(building["property_view_id"])
    image_path = BUILDING_IMAGE_PATHS.get(property_view_id)
    has_building_image = image_path is not None and image_path.exists()

    page.multiline(
        MARGIN,
        708,
        "The image below uses open building and street geometry where available. The Google Maps link opens the same location in satellite/3D-capable map view for owner review.",
        size=10,
        max_chars=90,
        leading=14,
        color="334155",
    )

    lat = to_float(building.get("latitude"))
    lon = to_float(building.get("longitude"))
    point = parse_point(building.get("long_lat"))
    if point and (lat is None or lon is None):
        lon, lat = point
    maps_url = google_maps_3d_url(building)

    if has_building_image:
        page.rect(70, 186, 472, 472, fill="FFFFFF", stroke="D7DEE8")
        page.image(72, 188, 468, 468, image_path)
        page.rect(70, 186, 472, 472, stroke="183F6D")

        page.rect(MARGIN, 78, 510, 86, fill="F7F6F3", stroke="D7DEE8")
        page.text(MARGIN + 16, 140, "Image source and owner review link", size=11, font="F2", color="111827")
        page.multiline(
            MARGIN + 16,
            122,
            f"{building['address']} | {lat:.7f}, {lon:.7f}. Image rendered from OpenStreetMap geometry; map data (C) OpenStreetMap contributors. Google Maps 3D link: {maps_url}",
            size=8,
            max_chars=98,
            leading=11,
            color="334155",
        )
        return

    draw_location_panel(page, building, MARGIN, 386, 510, 260)

    page.text(MARGIN, 350, "Location details", size=14, font="F2", color="111827")
    y = small_table(
        page,
        MARGIN,
        328,
        [
            ("Address", str(building["address"])),
            ("City / state", f"{building.get('city') or 'Washington'} / {building.get('state') or 'DC'}"),
            ("Latitude / longitude", f"{lat:.7f}, {lon:.7f}" if lat is not None and lon is not None else "-"),
            ("SEED footprint", "Available" if parse_polygon(building.get("footprint")) else "Not available in this export"),
        ],
    )

    page.text(MARGIN, y - 8, "Google Maps 3D / satellite link", size=12, font="F2", color="183F6D")
    page.rect(MARGIN, y - 76, 510, 48, fill="EAF7FC", stroke="B8D9E8")
    page.multiline(MARGIN + 14, y - 46, maps_url, size=8, max_chars=82, leading=10, color="183F6D")

    page.rect(MARGIN, 88, 510, 70, fill="F7F6F3", stroke="D7DEE8")
    page.text(MARGIN + 16, 132, "Map note", size=11, font="F2", color="111827")
    page.multiline(
        MARGIN + 16,
        114,
        "Google map tiles are not embedded in this PDF. Embedding them directly requires a Google Maps API key and a use case that fits Google Maps Platform terms. The link above is included for the owner-facing 3D review workflow.",
        size=8,
        max_chars=96,
        leading=11,
        color="334155",
    )


def draw_openstudio_calibration_page(pdf: PDF, building: dict, rank: int, page_no: int) -> None:
    page = pdf.add_page()
    header(page, "OpenStudio-MCP Electricity Calibration", f"Rank #{rank}: {building['name']}", page_no)
    assets = OPENSTUDIO_MODEL_PATHS[int(building["property_view_id"])]
    calibration = json.loads(assets["calibration_json"].read_text())
    metrics = calibration["metrics"]

    page.multiline(
        MARGIN,
        708,
        "This page compares the OpenStudio-MCP EnergyPlus baseline with the building's real 2022 SEED electric meter profile. A transparent monthly meter-calibration factor is included for audit screening so the owner can evaluate modeled recommendations against measured seasonality.",
        size=10,
        max_chars=92,
        leading=14,
        color="334155",
    )
    page.image(91, 210, 430, 430, assets["calibration_image"])

    page.metric(MARGIN, 132, 156, "Annual baseline error", num(metrics["baseline_annual_difference_percent"], 1, suffix="%"), "1B6257")
    page.metric(MARGIN + 174, 132, 156, "Monthly CVRMSE", f"{metrics['baseline_cvrmse_percent']:.1f}% -> 0.0%", "183F6D")
    page.metric(MARGIN + 348, 132, 156, "EUI check", f"{metrics['model_site_eui_kbtu_per_ft2']:.1f} vs {metrics['actual_meter_eui_kbtu_per_ft2']:.1f}", "D9901A")

    page.rect(MARGIN, 24, 510, 78, fill="F7F6F3", stroke="D7DEE8")
    page.text(MARGIN + 16, 78, "Interpretation", size=11, font="F2", color="111827")
    page.multiline(
        MARGIN + 16,
        60,
        "The annual electricity match is already close. The adjustment improves monthly fit by aligning the model output to the actual 2022 meter; it should be validated against schedules, plug loads, HVAC controls, and tenant operating patterns before using it for investment decisions.",
        size=8,
        max_chars=96,
        leading=11,
        color="334155",
    )


def draw_openstudio_zoning_page(pdf: PDF, building: dict, rank: int, page_no: int) -> None:
    page = pdf.add_page()
    header(page, "10-Story Perimeter/Core Model Visual", f"Rank #{rank}: {building['name']}", page_no)
    assets = OPENSTUDIO_MODEL_PATHS[int(building["property_view_id"])]

    page.multiline(
        MARGIN,
        708,
        "The audit model is represented as a ten-story large office with perimeter zones around a central core. This matches the requested OpenStudio geometry intent and gives the owner a quick visual for how the model separates facade-driven loads from interior office loads.",
        size=10,
        max_chars=92,
        leading=14,
        color="334155",
    )
    page.image(66, 178, 480, 480, assets["zoning_image"])

    page.rect(MARGIN, 82, 510, 70, fill="F7F6F3", stroke="D7DEE8")
    page.text(MARGIN + 16, 126, "Modeling note", size=11, font="F2", color="111827")
    page.multiline(
        MARGIN + 16,
        108,
        "This is a schematic audit visual, not a facade survey. The perimeter/core split is useful for evaluating envelope, lighting, plug-load, schedule, and HVAC control recommendations against real building operation.",
        size=8,
        max_chars=96,
        leading=11,
        color="334155",
    )


def draw_owner_checklist(pdf: PDF, building: dict, rank: int, page_no: int = 6) -> None:
    page = pdf.add_page()
    header(page, "Owner Review Checklist", f"Rank #{rank}: {building['name']}", page_no)
    page.multiline(
        MARGIN,
        708,
        "Use this checklist to decide whether the BETTER recommendations are actionable and what information is needed before scoping projects.",
        size=11,
        max_chars=88,
        leading=15,
    )

    sections = [
        (
            "Data to validate",
            [
                "Confirm 2022 utility bills, meter IDs, whole-building coverage, and whether shared meters or tenant meters exist.",
                "Confirm gross floor area, property type, occupancy, operating hours, and major tenant uses.",
                "Check whether the reported Site EUI and ENERGY STAR score match the owner's Portfolio Manager record.",
            ],
        ),
        (
            "Systems to inspect",
            [
                "Lighting controls, fixture schedules, tenant plug-load density, and after-hours equipment operation.",
                "Heating/cooling equipment age, controls, reset schedules, economizer operation, and simultaneous heating/cooling.",
                "Envelope leakage, doors, windows, roof/wall insulation, and comfort complaints that line up with BETTER flags.",
            ],
        ),
        (
            "Decision questions",
            [
                "Which recommendations are low-disruption operational changes versus capital projects?",
                "Which measures are blocked by leases, tenant controls, historic constraints, or upcoming renovations?",
                "Which measures should be bundled so savings are not double-counted?",
            ],
        ),
    ]
    y = 650
    for title, items in sections:
        page.text(MARGIN, y, title, size=14, font="F2", color="183F6D")
        y -= 24
        for item in items:
            y = bullet(page, MARGIN, y, item)
            y -= 10
        y -= 10

    page.rect(MARGIN, 92, 510, 62, fill="F7F6F3", stroke="D7DEE8")
    page.text(MARGIN + 16, 130, "Screening conclusion", size=11, font="F2", color="111827")
    page.multiline(
        MARGIN + 16,
        112,
        "The owner should treat this as a prioritized audit intake sheet. Confirm the data and system context first, then translate the highest-confidence BETTER flags into scoped measures.",
        size=9,
        max_chars=86,
        leading=12,
        color="334155",
    )


def build_pdf(building: dict, rank: int) -> PDF:
    pdf = PDF()
    draw_cover(pdf, building, rank)
    draw_detail(pdf, building, rank)
    draw_complete_recommendations(pdf, building, rank)
    draw_meter_consumption(pdf, building, rank)
    draw_location_page(pdf, building, rank)
    next_page = 6
    if int(building["property_view_id"]) in OPENSTUDIO_MODEL_PATHS:
        draw_openstudio_calibration_page(pdf, building, rank, next_page)
        next_page += 1
        draw_openstudio_zoning_page(pdf, building, rank, next_page)
        next_page += 1
    draw_owner_checklist(pdf, building, rank, next_page)
    return pdf


def write_index(top: list[dict], paths: list[Path]) -> None:
    lines = [
        "# BETTER Owner Audit PDFs",
        "",
        "Org 412 BPS - DC, cycle 2022. Ranked by active BETTER recommendation count; ties sorted by combined BETTER cost savings.",
        "",
        "| Rank | Building | Address | Active recs | PDF |",
        "|---:|---|---|---:|---|",
    ]
    for rank, (building, path) in enumerate(zip(top, paths), start=1):
        lines.append(
            f"| {rank} | {building['name']} | {building['address']} | {building['rank_score']} | [{path.name}]({path.name}) |",
        )
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    top = load_ranked_buildings()[:5]
    paths: list[Path] = []
    packet = PDF()
    for rank, building in enumerate(top, start=1):
        path = OUT_DIR / f"{rank:02d}_{safe_name(building['address'])}_owner_audit_screening.pdf"
        pdf = build_pdf(building, rank)
        pdf.save(path)
        paths.append(path)
        packet.pages.extend(pdf.pages)
    packet_path = OUT_DIR / "top5_better_owner_audit_packet.pdf"
    packet.save(packet_path)
    write_index(top, paths)
    print(packet_path)
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
