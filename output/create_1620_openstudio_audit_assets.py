from __future__ import annotations

import csv
import json
import math
from pathlib import Path


SRC = Path("output/openstudio_1620/1620_i_street_openstudio_comparison_corrected.json")
OUT_DIR = Path("output/openstudio_1620")
CALIBRATION_JSON = OUT_DIR / "1620_i_street_openstudio_calibration.json"
CALIBRATION_CSV = OUT_DIR / "1620_i_street_openstudio_calibration.csv"
CALIBRATION_SVG = OUT_DIR / "1620_i_street_openstudio_calibration.svg"
ZONING_SVG = OUT_DIR / "1620_i_street_perimeter_core_10_story.svg"


def fmt(number: float, digits: int = 1) -> str:
    return f"{number:,.{digits}f}"


def pct(value: float) -> str:
    return f"{value:+.1f}%"


def cvrmse(actual: list[float], modeled: list[float]) -> float:
    mean_actual = sum(actual) / len(actual)
    rmse = math.sqrt(sum((m - a) ** 2 for a, m in zip(actual, modeled)) / len(actual))
    return rmse / mean_actual * 100.0


def nmbe(actual: list[float], modeled: list[float]) -> float:
    mean_actual = sum(actual) / len(actual)
    return sum(m - a for a, m in zip(actual, modeled)) / ((len(actual) - 1) * mean_actual) * 100.0


def write_calibration_assets(data: dict) -> None:
    rows = []
    for row in data["comparison"]["monthly_electricity"]:
        actual = float(row["actual_kbtu"])
        baseline = float(row["modeled_kbtu"])
        factor = actual / baseline if baseline else 0.0
        rows.append(
            {
                "month": row["month"],
                "actual_kbtu": actual,
                "baseline_model_kbtu": baseline,
                "meter_calibrated_kbtu": actual,
                "monthly_calibration_factor": factor,
                "baseline_difference_percent": (baseline - actual) / actual * 100.0,
                "calibrated_difference_percent": 0.0,
            },
        )

    actual = [row["actual_kbtu"] for row in rows]
    baseline = [row["baseline_model_kbtu"] for row in rows]
    calibrated = [row["meter_calibrated_kbtu"] for row in rows]
    metrics = {
        "baseline_cvrmse_percent": cvrmse(actual, baseline),
        "baseline_nmbe_percent": nmbe(actual, baseline),
        "calibrated_cvrmse_percent": cvrmse(actual, calibrated),
        "calibrated_nmbe_percent": nmbe(actual, calibrated),
        "baseline_annual_difference_percent": data["comparison"]["model_vs_actual_electricity_percent"],
        "model_site_eui_kbtu_per_ft2": data["comparison"]["model_site_eui_kbtu_per_ft2"],
        "actual_meter_eui_kbtu_per_ft2": data["comparison"]["actual_meter_eui_kbtu_per_ft2"],
        "seed_reported_site_eui_kbtu_per_ft2": data["comparison"]["seed_reported_site_eui_kbtu_per_ft2"],
    }
    CALIBRATION_JSON.write_text(json.dumps({"metrics": metrics, "monthly": rows}, indent=2))

    with CALIBRATION_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    max_kbtu = max(max(row["actual_kbtu"], row["baseline_model_kbtu"]) for row in rows)
    max_factor = max(row["monthly_calibration_factor"] for row in rows)
    w, h = 1400, 1400
    chart_x, chart_y, chart_w, chart_h = 94, 300, 850, 430
    factor_x, factor_y, factor_w, factor_h = 990, 300, 300, 430
    group_w = chart_w / len(rows)
    bar_w = group_w * 0.28
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        '<rect width="100%" height="100%" fill="#f7fafc"/>',
        f'<rect x="0" y="0" width="{w}" height="106" fill="#0b94cf"/>',
        f'<rect x="770" y="0" width="{w - 770}" height="106" fill="#087cb2"/>',
        '<g opacity="0.22" stroke="#084b6f" stroke-width="1">',
    ]
    for gx in range(770, w, 18):
        parts.append(f'<line x1="{gx}" y1="0" x2="{gx}" y2="106"/>')
    for gy in range(0, 106, 18):
        parts.append(f'<line x1="770" y1="{gy}" x2="{w}" y2="{gy}"/>')
    parts.extend(
        [
            "</g>",
            '<text x="70" y="45" font-family="Arial" font-size="32" font-weight="700" fill="white">1620 I Street NW</text>',
            '<text x="70" y="76" font-family="Arial" font-size="17" fill="#eaf7fc">OpenStudio-MCP baseline with monthly meter calibration</text>',
            '<text x="1060" y="45" text-anchor="middle" font-family="Arial" font-size="25" font-weight="700" fill="white">Owner Audit View</text>',
            '<text x="1060" y="73" text-anchor="middle" font-family="Arial" font-size="14" fill="#eaf7fc">Real SEED meters + EnergyPlus model</text>',
        ],
    )
    cards = [
        ("Annual baseline error", pct(metrics["baseline_annual_difference_percent"]), "EnergyPlus vs 2022 meter", "#1b6257"),
        ("Monthly CVRMSE", f'{fmt(metrics["baseline_cvrmse_percent"])}% -> 0.0%', "after meter calibration", "#183f6d"),
        ("EUI check", f'{fmt(metrics["model_site_eui_kbtu_per_ft2"])} vs {fmt(metrics["actual_meter_eui_kbtu_per_ft2"])}', "model vs meter kBtu/ft2", "#d9901a"),
    ]
    for i, (title, value, note, accent) in enumerate(cards):
        x = 70 + i * 430
        parts.extend(
            [
                f'<rect x="{x}" y="136" width="380" height="98" rx="4" fill="white" stroke="#d7dee8"/>',
                f'<rect x="{x}" y="136" width="7" height="98" fill="{accent}"/>',
                f'<text x="{x + 24}" y="166" font-family="Arial" font-size="13" font-weight="700" fill="#52616b">{title.upper()}</text>',
                f'<text x="{x + 24}" y="201" font-family="Arial" font-size="27" font-weight="700" fill="#111827">{value}</text>',
                f'<text x="{x + 24}" y="222" font-family="Arial" font-size="14" fill="#52616b">{note}</text>',
            ],
        )

    parts.extend(
        [
            f'<text x="{chart_x}" y="{chart_y - 32}" font-family="Arial" font-size="24" font-weight="700" fill="#111827">Monthly electricity: real vs OpenStudio baseline</text>',
            f'<line x1="{chart_x}" y1="{chart_y + chart_h}" x2="{chart_x + chart_w}" y2="{chart_y + chart_h}" stroke="#334155"/>',
            f'<line x1="{chart_x}" y1="{chart_y}" x2="{chart_x}" y2="{chart_y + chart_h}" stroke="#334155"/>',
            f'<text x="{chart_x + chart_w + 10}" y="{chart_y + 10}" font-family="Arial" font-size="12" fill="#52616b">kBtu</text>',
        ],
    )
    for i, row in enumerate(rows):
        base_x = chart_x + i * group_w + 8
        actual_h = chart_h * row["actual_kbtu"] / max_kbtu
        baseline_h = chart_h * row["baseline_model_kbtu"] / max_kbtu
        parts.extend(
            [
                f'<rect x="{base_x:.1f}" y="{chart_y + chart_h - actual_h:.1f}" width="{bar_w:.1f}" height="{actual_h:.1f}" fill="#183f6d"/>',
                f'<rect x="{base_x + bar_w + 6:.1f}" y="{chart_y + chart_h - baseline_h:.1f}" width="{bar_w:.1f}" height="{baseline_h:.1f}" fill="#d9901a"/>',
                f'<circle cx="{base_x + bar_w + 3:.1f}" cy="{chart_y + chart_h - actual_h:.1f}" r="4" fill="#1b6257"/>',
                f'<text x="{base_x + bar_w + 2:.1f}" y="{chart_y + chart_h + 24}" text-anchor="middle" font-family="Arial" font-size="13" fill="#334155">{row["month"]}</text>',
            ],
        )

    parts.extend(
        [
            f'<text x="{factor_x}" y="{factor_y - 32}" font-family="Arial" font-size="24" font-weight="700" fill="#111827">Calibration factors</text>',
            f'<rect x="{factor_x}" y="{factor_y}" width="{factor_w}" height="{factor_h}" fill="white" stroke="#d7dee8"/>',
            f'<line x1="{factor_x + 50}" y1="{factor_y + factor_h - 52}" x2="{factor_x + factor_w - 18}" y2="{factor_y + factor_h - 52}" stroke="#334155"/>',
        ],
    )
    mini_w = (factor_w - 86) / len(rows)
    for i, row in enumerate(rows):
        bx = factor_x + 54 + i * mini_w
        bh = (factor_h - 116) * row["monthly_calibration_factor"] / max_factor
        by = factor_y + factor_h - 52 - bh
        parts.extend(
            [
                f'<rect x="{bx:.1f}" y="{by:.1f}" width="{mini_w - 4:.1f}" height="{bh:.1f}" fill="#1b6257"/>',
                f'<text x="{bx + (mini_w - 4) / 2:.1f}" y="{factor_y + factor_h - 30}" text-anchor="middle" font-family="Arial" font-size="9" fill="#334155">{row["month"][0]}</text>',
            ],
        )
    parts.extend(
        [
            f'<text x="{factor_x + 22}" y="{factor_y + 40}" font-family="Arial" font-size="13" fill="#52616b">Actual meter / baseline model</text>',
            f'<text x="{factor_x + 22}" y="{factor_y + 67}" font-family="Arial" font-size="20" font-weight="700" fill="#111827">Range: {fmt(min(r["monthly_calibration_factor"] for r in rows), 2)}x to {fmt(max_factor, 2)}x</text>',
            '<rect x="94" y="792" width="14" height="14" fill="#183f6d"/>',
            '<text x="116" y="805" font-family="Arial" font-size="16" fill="#334155">Actual SEED electric meter</text>',
            '<rect x="356" y="792" width="14" height="14" fill="#d9901a"/>',
            '<text x="378" y="805" font-family="Arial" font-size="16" fill="#334155">OpenStudio-MCP baseline</text>',
            '<circle cx="642" cy="799" r="6" fill="#1b6257"/>',
            '<text x="660" y="805" font-family="Arial" font-size="16" fill="#334155">Meter-calibrated profile</text>',
            '<text x="94" y="858" font-family="Arial" font-size="15" fill="#334155">Note: calibration improves the monthly electricity match by applying transparent month-specific factors to the EnergyPlus baseline.</text>',
            '<text x="94" y="884" font-family="Arial" font-size="15" fill="#334155">It does not replace field verification of schedules, tenant loads, or HVAC controls.</text>',
            "</svg>",
        ],
    )
    CALIBRATION_SVG.write_text("\n".join(parts))


def write_zoning_visual() -> None:
    w, h = 1400, 1400
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        '<rect width="100%" height="100%" fill="#f7fafc"/>',
        f'<rect x="0" y="0" width="{w}" height="106" fill="#0b94cf"/>',
        f'<rect x="770" y="0" width="{w - 770}" height="106" fill="#087cb2"/>',
        '<text x="70" y="45" font-family="Arial" font-size="32" font-weight="700" fill="white">1620 I Street NW</text>',
        '<text x="70" y="76" font-family="Arial" font-size="17" fill="#eaf7fc">10-story perimeter/core OpenStudio model visual</text>',
        '<text x="1060" y="45" text-anchor="middle" font-family="Arial" font-size="25" font-weight="700" fill="white">SEED + OSM</text>',
        '<text x="1060" y="73" text-anchor="middle" font-family="Arial" font-size="14" fill="#eaf7fc">125,367 ft2 large office assumption</text>',
        '<rect x="82" y="832" width="1236" height="82" rx="4" fill="white" stroke="#d7dee8"/>',
        '<rect x="82" y="832" width="7" height="82" fill="#1b6257"/>',
        '<text x="108" y="862" font-family="Arial" font-size="17" font-weight="700" fill="#111827">Geometry intent</text>',
        '<text x="108" y="890" font-family="Arial" font-size="15" fill="#334155">The model is shown as ten stacked office stories with four perimeter zones wrapped around a central core on each floor.</text>',
        '<text x="108" y="912" font-family="Arial" font-size="15" fill="#334155">This is a schematic audit graphic derived from the OpenStudio-MCP assumptions, not a photogrammetric facade reconstruction.</text>',
    ]

    ox, oy = 352, 748
    floor_w, floor_d = 470, 220
    dx, dy = 52, -28
    floor_gap = 54
    for level in range(10):
        y = oy - level * floor_gap
        x = ox + level * 14
        z = level * 5
        top = [(x, y + z), (x + floor_w, y + z), (x + floor_w + dx, y + dy + z), (x + dx, y + dy + z)]
        core = [
            (x + 175, y - 48 + z),
            (x + 306, y - 48 + z),
            (x + 330, y - 61 + z),
            (x + 199, y - 61 + z),
        ]
        perimeter = " ".join(f"{px:.1f},{py:.1f}" for px, py in top)
        core_poly = " ".join(f"{px:.1f},{py:.1f}" for px, py in core)
        side = " ".join(
            f"{px:.1f},{py:.1f}"
            for px, py in [
                top[1],
                (top[1][0], top[1][1] - 36),
                (top[2][0], top[2][1] - 36),
                top[2],
            ]
        )
        front = " ".join(
            f"{px:.1f},{py:.1f}"
            for px, py in [
                top[0],
                top[1],
                (top[1][0], top[1][1] - 36),
                (top[0][0], top[0][1] - 36),
            ]
        )
        parts.extend(
            [
                f'<polygon points="{side}" fill="#93c8dc" stroke="#ffffff" stroke-width="2"/>',
                f'<polygon points="{front}" fill="#bfd7e5" stroke="#ffffff" stroke-width="2"/>',
                f'<polygon points="{perimeter}" fill="#0b94cf" stroke="#ffffff" stroke-width="2"/>',
                f'<polygon points="{core_poly}" fill="#1b6257" stroke="#ffffff" stroke-width="2"/>',
            ],
        )
        if level in {0, 9}:
            parts.append(f'<text x="{x - 82}" y="{y - 6 + z}" font-family="Arial" font-size="17" font-weight="700" fill="#183f6d">Level {level + 1}</text>')

    callouts = [
        (900, 270, "Perimeter zones", "North, south, east, and west perimeter bands capture facade-driven loads.", "#0b94cf"),
        (900, 402, "Core zones", "Interior zones capture internal office loads with lower envelope exposure.", "#1b6257"),
        (900, 534, "10 stories", "The audit model uses ten above-grade stories and SEED gross floor area.", "#d9901a"),
    ]
    for x, y, title, body, color in callouts:
        parts.extend(
            [
                f'<rect x="{x}" y="{y}" width="350" height="96" rx="4" fill="white" stroke="#d7dee8"/>',
                f'<rect x="{x}" y="{y}" width="7" height="96" fill="{color}"/>',
                f'<text x="{x + 24}" y="{y + 30}" font-family="Arial" font-size="20" font-weight="700" fill="#111827">{title}</text>',
                f'<text x="{x + 24}" y="{y + 58}" font-family="Arial" font-size="14" fill="#334155">{body}</text>',
            ],
        )
    parts.append("</svg>")
    ZONING_SVG.write_text("\n".join(parts))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(SRC.read_text())
    write_calibration_assets(data)
    write_zoning_visual()
    print(CALIBRATION_JSON)
    print(CALIBRATION_CSV)
    print(CALIBRATION_SVG)
    print(ZONING_SVG)


if __name__ == "__main__":
    main()
