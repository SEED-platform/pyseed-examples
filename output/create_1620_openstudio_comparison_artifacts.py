from __future__ import annotations

import csv
import json
from pathlib import Path


SRC = Path("output/openstudio_1620/1620_i_street_openstudio_comparison.json")
OUT_DIR = Path("output/openstudio_1620")
CORRECTED = OUT_DIR / "1620_i_street_openstudio_comparison_corrected.json"
CSV_PATH = OUT_DIR / "1620_i_street_monthly_electricity_comparison.csv"
SVG_PATH = OUT_DIR / "1620_i_street_openstudio_vs_real.svg"
J_PER_KBTU = 1_055_055.85262
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def pct(model: float, actual: float) -> float:
    return (model - actual) / actual * 100.0


def main() -> None:
    data = json.loads(SRC.read_text())
    actual_by_month = {row["month"]: row["actual_kbtu"] for row in data["comparison"]["monthly_electricity"]}
    ts = data["mcp"]["electricity_timeseries"]
    model_by_month = {}
    for row in ts["data"]:
        month = MONTHS[int(row["month"]) - 1]
        model_by_month[month] = float(row["value"]) / J_PER_KBTU

    rows = []
    for month in MONTHS:
        actual = actual_by_month[month]
        model = model_by_month[month]
        rows.append(
            {
                "month": month,
                "actual_kbtu": actual,
                "modeled_kbtu": model,
                "difference_kbtu": model - actual,
                "difference_percent": pct(model, actual),
            },
        )

    actual_annual = sum(actual_by_month.values())
    model_annual = sum(model_by_month.values())
    metrics = data["mcp"]["summary_metrics"]["metrics"]
    model_eui = metrics["eui_kBtu_ft2"]
    seed_eui = data["inputs"]["seed_site_eui_kbtu_per_ft2"]
    actual_meter_eui = actual_annual / data["inputs"]["seed_gross_floor_area_ft2"]

    data["comparison"] = {
        "actual_annual_electricity_kbtu": actual_annual,
        "modeled_annual_electricity_kbtu": model_annual,
        "actual_meter_eui_kbtu_per_ft2": actual_meter_eui,
        "seed_reported_site_eui_kbtu_per_ft2": seed_eui,
        "model_site_eui_kbtu_per_ft2": model_eui,
        "model_vs_actual_electricity_percent": pct(model_annual, actual_annual),
        "model_vs_seed_site_eui_percent": pct(model_eui, seed_eui),
        "monthly_electricity": rows,
    }
    CORRECTED.write_text(json.dumps(data, indent=2))

    with CSV_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    max_value = max(max(r["actual_kbtu"], r["modeled_kbtu"]) for r in rows)
    svg_w, svg_h = 1000, 1000
    chart_x, chart_y, chart_w, chart_h = 78, 310, 840, 390
    group_w = chart_w / len(rows)
    bar_w = group_w * 0.32
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}">',
        '<rect width="100%" height="100%" fill="#f7fafc"/>',
        f'<rect x="0" y="0" width="{svg_w}" height="94" fill="#0b94cf"/>',
        f'<rect x="620" y="0" width="{svg_w - 620}" height="94" fill="#087cb2"/>',
        '<text x="56" y="44" font-family="Arial" font-size="28" font-weight="700" fill="white">1620 I Street NW</text>',
        '<text x="56" y="72" font-family="Arial" font-size="16" fill="#eaf7fc">OpenStudio-MCP model vs SEED 2022 electric meter</text>',
        '<text x="740" y="44" font-family="Arial" font-size="24" font-weight="700" fill="white">SEED + OSM</text>',
        '<text x="740" y="70" font-family="Arial" font-size="13" fill="#eaf7fc">Office | 125,367 ft2 | 10 levels</text>',
    ]
    cards = [
        ("Annual electricity", f"{model_annual / 1_000_000:.2f}M vs {actual_annual / 1_000_000:.2f}M kBtu", f"{pct(model_annual, actual_annual):+.2f}%"),
        ("Model site EUI", f"{model_eui:.1f} kBtu/ft2", f"SEED: {seed_eui:.1f}"),
        ("Meter EUI", f"{actual_meter_eui:.1f} kBtu/ft2", "2022 electric meter only"),
    ]
    for i, (title, value, note) in enumerate(cards):
        x = 56 + i * 305
        parts.extend(
            [
                f'<rect x="{x}" y="130" width="270" height="84" rx="4" fill="white" stroke="#d7dee8"/>',
                f'<rect x="{x}" y="130" width="6" height="84" fill="#1b6257"/>',
                f'<text x="{x + 18}" y="156" font-family="Arial" font-size="11" font-weight="700" fill="#52616b">{title.upper()}</text>',
                f'<text x="{x + 18}" y="184" font-family="Arial" font-size="17" font-weight="700" fill="#111827">{value}</text>',
                f'<text x="{x + 18}" y="204" font-family="Arial" font-size="12" fill="#52616b">{note}</text>',
            ],
        )
    parts.extend(
        [
            f'<line x1="{chart_x}" y1="{chart_y + chart_h}" x2="{chart_x + chart_w}" y2="{chart_y + chart_h}" stroke="#334155" stroke-width="1"/>',
            f'<line x1="{chart_x}" y1="{chart_y}" x2="{chart_x}" y2="{chart_y + chart_h}" stroke="#334155" stroke-width="1"/>',
            f'<text x="{chart_x}" y="{chart_y - 24}" font-family="Arial" font-size="21" font-weight="700" fill="#111827">Monthly electricity consumption</text>',
            f'<text x="{chart_x + chart_w - 90}" y="{chart_y - 18}" font-family="Arial" font-size="12" fill="#52616b">kBtu</text>',
        ],
    )
    for i, row in enumerate(rows):
        base_x = chart_x + i * group_w + 10
        actual_h = chart_h * row["actual_kbtu"] / max_value
        model_h = chart_h * row["modeled_kbtu"] / max_value
        parts.extend(
            [
                f'<rect x="{base_x:.1f}" y="{chart_y + chart_h - actual_h:.1f}" width="{bar_w:.1f}" height="{actual_h:.1f}" fill="#183f6d"/>',
                f'<rect x="{base_x + bar_w + 5:.1f}" y="{chart_y + chart_h - model_h:.1f}" width="{bar_w:.1f}" height="{model_h:.1f}" fill="#d9901a"/>',
                f'<text x="{base_x + bar_w:.1f}" y="{chart_y + chart_h + 18}" text-anchor="middle" font-family="Arial" font-size="11" fill="#334155">{row["month"]}</text>',
            ],
        )
    parts.extend(
        [
            '<rect x="78" y="760" width="12" height="12" fill="#183f6d"/>',
            '<text x="98" y="771" font-family="Arial" font-size="14" fill="#334155">Actual SEED meter</text>',
            '<rect x="250" y="760" width="12" height="12" fill="#d9901a"/>',
            '<text x="270" y="771" font-family="Arial" font-size="14" fill="#334155">OpenStudio-MCP model</text>',
            '<text x="78" y="824" font-family="Arial" font-size="13" fill="#52616b">Model uses MCP create_new_building, OSM-derived 10 stories, SEED GFA, Baltimore-Washington TMY3 weather, all-electric assumptions.</text>',
            "</svg>",
        ],
    )
    SVG_PATH.write_text("\n".join(parts))
    print(CORRECTED)
    print(CSV_PATH)
    print(SVG_PATH)


if __name__ == "__main__":
    main()
