from __future__ import annotations

import math
from pathlib import Path


PAGE_W = 612
PAGE_H = 792
MARGIN = 42


def esc(text: object) -> str:
    value = str(text)
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def fmt_num(value: float, digits: int = 0) -> str:
    if value is None:
        return "-"
    if digits == 0:
        return f"{value:,.0f}"
    return f"{value:,.{digits}f}"


def wrap(text: str, max_chars: int) -> list[str]:
    words = text.split()
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


class Page:
    def __init__(self) -> None:
        self.ops: list[str] = []

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

    def pill(self, x: float, y: float, w: float, h: float, label: str, value: str, fill: str, accent: str) -> None:
        self.rect(x, y, w, h, fill=fill)
        self.rect(x, y, 5, h, fill=accent)
        self.text(x + 14, y + h - 20, label.upper(), size=8, font="F2", color="5B6470")
        self.text(x + 14, y + 15, value, size=18, font="F2", color="111111")


class PDF:
    def __init__(self) -> None:
        self.pages: list[Page] = []

    def add_page(self) -> Page:
        page = Page()
        self.pages.append(page)
        return page

    def save(self, path: Path) -> None:
        objects: list[bytes] = []
        font1 = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
        font2 = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"
        objects.append(font1)
        objects.append(font2)
        page_objects: list[tuple[int, int]] = []
        for page in self.pages:
            stream = "\n".join(page.ops).encode("latin-1", "replace")
            content = b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
            content_id = len(objects) + 1
            objects.append(content)
            page_id = len(objects) + 1
            page_objects.append((page_id, content_id))
            objects.append(b"")

        pages_id = len(objects) + 1
        kids = " ".join(f"{page_id} 0 R" for page_id, _content_id in page_objects).encode()
        objects.append(b"<< /Type /Pages /Kids [" + kids + b"] /Count " + str(len(page_objects)).encode() + b" >>")
        catalog_id = len(objects) + 1
        objects.append(b"<< /Type /Catalog /Pages " + str(pages_id).encode() + b" 0 R >>")

        for index, (page_id, content_id) in enumerate(page_objects):
            objects[page_id - 1] = (
                b"<< /Type /Page /Parent "
                + str(pages_id).encode()
                + b" 0 R /MediaBox [0 0 612 792] "
                + b"/Resources << /Font << /F1 1 0 R /F2 2 0 R >> >> "
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
        path.write_bytes(out)


def header(page: Page, title: str, page_no: int) -> None:
    page.line(MARGIN, 748, 210, 748, color="111111", width=3)
    page.text(MARGIN, 724, title, size=28, font="F2")
    page.text(470, 748, "SEED benchmarking", size=10, font="F2", color="256FA6")
    page.text(560, 34, page_no, size=12, font="F2")


def table(page: Page, x: float, y: float, rows: list[tuple[str, str]], widths: tuple[float, float] = (180, 320)) -> float:
    row_h = 21
    for i, (key, value) in enumerate(rows):
        fill = "F4F7FA" if i % 2 == 0 else "FFFFFF"
        page.rect(x, y - row_h + 4, sum(widths), row_h, fill=fill)
        page.text(x + 8, y - 11, key, size=9, font="F2", color="3F4854")
        page.text(x + widths[0] + 8, y - 11, value, size=9, color="111111")
        y -= row_h
    return y


def bar_chart(page: Page, x: float, y: float, w: float, h: float, labels: list[str], values: list[float], color: str) -> None:
    max_value = max(values) if values else 1
    page.line(x, y, x, y + h, color="222222", width=0.8)
    page.line(x, y, x + w, y, color="222222", width=0.8)
    bar_gap = 5
    bar_w = (w - bar_gap * (len(values) - 1)) / max(len(values), 1)
    for i, value in enumerate(values):
        bh = 0 if max_value == 0 else (value / max_value) * h
        bx = x + i * (bar_w + bar_gap)
        page.rect(bx, y, bar_w, bh, fill=color)
        page.text(bx - 2, y - 16, labels[i], size=7, color="333333")
    for frac in [0.25, 0.5, 0.75, 1.0]:
        gy = y + h * frac
        page.line(x, gy, x + w, gy, color="D3D9DF", width=0.4)
        page.text(x + w + 6, gy - 3, fmt_num(max_value * frac), size=7, color="666666")


def benchmark_axis(page: Page, x: float, y: float, w: float) -> None:
    points = [
        ("Median", 51.2, "5A6C7D"),
        ("p75", 70.0, "5A6C7D"),
        ("p95", 117.4, "E2A12B"),
        ("Target", 4192.8, "C3362B"),
    ]
    label_offsets = {
        "Median": (-26, 24, -26, -24),
        "p75": (-5, 47, -5, -41),
        "p95": (14, 24, 14, -24),
        "Target": (-18, 24, -18, -24),
    }
    max_axis = 4500
    page.line(x, y, x + w, y, color="222222", width=1)
    for label, value, color in points:
        px = x + (value / max_axis) * w
        page.line(px, y - 8, px, y + 20, color=color, width=2.2)
        if label == "p75":
            continue
        label_dx, label_dy, value_dx, value_dy = label_offsets[label]
        page.text(px + label_dx, y + label_dy, label, size=8, font="F2", color=color)
        page.text(px + value_dx, y + value_dy, fmt_num(value, 1), size=8, color=color)
    page.text(x, y - 44, "Site EUI scale, kBtu/ft2/year. Target building is far right because it is the maximum observed value.", size=8, color="555555")


def bullet(page: Page, x: float, y: float, text: str, max_chars: int = 82) -> float:
    page.rect(x, y - 2, 4, 4, fill="256FA6")
    return page.multiline(x + 14, y - 4, text, size=10, max_chars=max_chars, leading=14)


def build_report() -> PDF:
    pdf = PDF()

    monthly = [
        ("Jan", 1921.79, 9272393.5),
        ("Feb", 1845.10, 8375065.1),
        ("Mar", 2596.74, 9272393.5),
        ("Apr", 3837.13, 8973284.04),
        ("May", 5330.18, 9272393.5),
        ("Jun", 4086.74, 8973284.04),
        ("Jul", 2551.17, 9272393.5),
        ("Aug", 2519.33, 9272393.5),
        ("Sep", 3027.92, 8973284.04),
        ("Oct", 3152.20, 9272393.5),
        ("Nov", 4705.63, 8973284.04),
        ("Dec", 4715.19, 8973284.04),
    ]
    electric_kwh = sum(row[1] for row in monthly)
    electric_kbtu = electric_kwh * 3.412141633
    hot_kbtu = sum(row[2] for row in monthly)
    total_kbtu = electric_kbtu + hot_kbtu
    reported_area = 26000
    seed_area = 28050

    page = pdf.add_page()
    page.rect(0, 0, PAGE_W, PAGE_H, fill="F7F9FB")
    page.rect(0, 560, PAGE_W, 232, fill="184D73")
    page.rect(0, 560, PAGE_W, 10, fill="E2A12B")
    page.text(MARGIN, 705, "ENERGY AUDIT", size=44, font="F2", color="FFFFFF")
    page.text(MARGIN, 660, "SCREENING REPORT", size=38, font="F2", color="FFFFFF")
    page.text(MARGIN, 620, "2258 25TH PLACE NE", size=21, font="F2", color="FFFFFF")
    page.text(MARGIN, 596, "Washington, DC 20018 | 2022 benchmarking cycle", size=12, color="DDEAF2")
    page.text(420, 740, "SEED", size=18, font="F2", color="FFFFFF")
    page.text(420, 720, "benchmarking analysis", size=9, color="DDEAF2")
    page.multiline(MARGIN, 520, "Prepared from SEED property, benchmarking, and meter data. This is a screening audit, not an onsite ASHRAE audit.", size=11, max_chars=96, leading=15, color="333333")
    page.pill(MARGIN, 445, 156, 58, "Reported Site EUI", "4,192.8", "FFFFFF", "C3362B")
    page.pill(MARGIN + 174, 445, 156, 58, "p95 Site EUI", "117.4", "FFFFFF", "E2A12B")
    page.pill(MARGIN + 348, 445, 156, 58, "Rank", "1 of 2,750", "FFFFFF", "256FA6")
    page.pill(MARGIN, 360, 156, 58, "Property type", "Warehouse", "FFFFFF", "256FA6")
    page.pill(MARGIN + 174, 360, 156, 58, "Year built", "1950", "FFFFFF", "256FA6")
    page.pill(MARGIN + 348, 360, 156, 58, "Ward", "5", "FFFFFF", "256FA6")
    page.text(MARGIN, 260, "Primary issue to investigate", size=16, font="F2")
    page.multiline(MARGIN, 235, "District hot water dominates the reported energy use. The meter records show about 108.9 million kBtu of district hot water and only about 40,289 kWh of electric use. This pattern is unusual for a non-refrigerated warehouse and should be reconciled before any capital work is scoped.", size=12, max_chars=78, leading=17)
    page.text(MARGIN, 84, "Prepared July 8, 2026", size=9, color="555555")
    page.text(420, 84, "Org 412 | Cycle 656", size=9, color="555555")

    page = pdf.add_page()
    header(page, "Executive Summary", 1)
    page.multiline(MARGIN, 675, "2258 25th Place NE is the highest Site EUI property in the 2022 DC benchmarking cycle among properties with non-null Site EUI. Its reported Site EUI is 4,192.8 kBtu/ft2/year, compared with a cycle median of 51.2 and a 95th percentile threshold of 117.4.", size=12, max_chars=83, leading=17)
    y = 595
    y = bullet(page, MARGIN, y, "The property is listed as a Non-Refrigerated Warehouse, 28,050 ft2 in SEED, with a separate reported gross floor area of 26,000 ft2 in imported extra data.")
    y = bullet(page, MARGIN, y - 12, "Reported status is Data Under Review by DOEE; ENERGY STAR score, story count, and onsite system details are not available in SEED.")
    y = bullet(page, MARGIN, y - 12, "The meter data includes Electric - Grid and District Hot Water. District hot water accounts for roughly 99.9% of meter-derived site energy.")
    y = bullet(page, MARGIN, y - 12, "Using the reported 26,000 ft2 area, meter-derived site energy reconciles to about 4,193 kBtu/ft2/year. Using the SEED canonical 28,050 ft2 area, it is about 3,886 kBtu/ft2/year.")
    page.text(MARGIN, 365, "Key Quantities", size=15, font="F2")
    table(page, MARGIN, 340, [
        ("PM Property ID", "PM26961358"),
        ("Property view ID", "3285534"),
        ("Reported Site EUI", "4,192.8 kBtu/ft2/year"),
        ("Source EUI", "5,052.6 kBtu/ft2/year"),
        ("Total GHG emissions", "7,241.2 mtCO2e"),
        ("Annual district hot water", f"{fmt_num(hot_kbtu)} kBtu"),
        ("Annual electricity", f"{fmt_num(electric_kwh)} kWh"),
        ("Meter-derived total site energy", f"{fmt_num(total_kbtu)} kBtu"),
    ])

    page = pdf.add_page()
    header(page, "Building Profile", 2)
    table(page, MARGIN, 675, [
        ("Property name", "De Paris Enterprises Inc"),
        ("Address", "2258 25TH PLACE NE, Washington, DC 20018"),
        ("Owner", "DEPARIS REBECCA C"),
        ("Property type", "Non-Refrigerated Warehouse"),
        ("Year built", "1950"),
        ("Ward / census tract", "Ward 5 / 11001011100"),
        ("Latitude / longitude", "38.92138514 / -76.97164794"),
        ("SEED gross floor area", "28,050 ft2"),
        ("Reported gross floor area", "26,000 ft2"),
        ("Metered areas, energy", "Whole Property"),
        ("Water use", "114.9"),
        ("Disadvantaged community flag", "False"),
        ("Low income flag", "False"),
    ])
    page.text(MARGIN, 350, "Benchmark Context", size=15, font="F2")
    page.multiline(MARGIN, 326, "Comparison set: 2,750 properties in the 2022 cycle with non-null Site EUI. The building is the maximum observed Site EUI in that set. Because the source record is under review, this should be treated as a priority data and meter-boundary investigation.", size=10, max_chars=88, leading=14)
    benchmark_axis(page, MARGIN, 245, 500)
    page.pill(MARGIN, 115, 156, 58, "Median", "51.2", "F4F7FA", "5A6C7D")
    page.pill(MARGIN + 174, 115, 156, 58, "p95", "117.4", "F4F7FA", "E2A12B")
    page.pill(MARGIN + 348, 115, 156, 58, "Building", "4,192.8", "F4F7FA", "C3362B")

    page = pdf.add_page()
    header(page, "Meter Analysis", 3)
    page.text(MARGIN, 675, "Meters Found", size=15, font="F2")
    table(page, MARGIN, 650, [
        ("18966", "Electric - Grid | Manual Entry | PM26961358"),
        ("18967", "District Hot Water | Manual Entry | PM26961358"),
    ])
    page.text(MARGIN, 570, "Annual Fuel Mix", size=15, font="F2")
    mix_x, mix_y = MARGIN, 525
    page.rect(mix_x, mix_y, 500, 28, fill="DDEAF2")
    elec_w = max(3, 500 * electric_kbtu / total_kbtu)
    page.rect(mix_x, mix_y, elec_w, 28, fill="2F80ED")
    page.rect(mix_x + elec_w, mix_y, 500 - elec_w, 28, fill="F2B13F")
    page.text(mix_x, mix_y - 18, "Electricity: 0.13% of site energy after kWh-to-kBtu conversion", size=8, color="2F80ED")
    page.text(mix_x + 270, mix_y - 18, "District hot water: 99.87%", size=8, color="9B660F")
    page.text(MARGIN, 470, "Monthly Electricity Use (kWh)", size=12, font="F2")
    bar_chart(page, MARGIN + 15, 315, 430, 130, [m[0] for m in monthly], [m[1] for m in monthly], "2F80ED")
    page.text(MARGIN, 275, "Monthly District Hot Water (kBtu)", size=12, font="F2")
    bar_chart(page, MARGIN + 15, 120, 430, 130, [m[0] for m in monthly], [m[2] for m in monthly], "F2B13F")
    page.multiline(MARGIN, 78, "The district hot water profile is nearly flat and extremely large month to month. That points first to meter mapping, units, service boundary, or area normalization review; operational heating diagnostics come after the data is reconciled.", size=9, max_chars=92, leading=12)

    page = pdf.add_page()
    header(page, "Preliminary Measures", 4)
    page.multiline(MARGIN, 675, "These measures are screening recommendations based on SEED and meter data only. They should be confirmed through utility bills, meter configuration, operator interviews, drawings, and an onsite walkthrough.", size=11, max_chars=86, leading=15)
    y = 610
    measures = [
        ("1. Reconcile data before scoping retrofits", "Verify district hot water units, meter ownership, service boundary, and whether the meter serves only this property. Confirm whether 26,000 ft2 or 28,050 ft2 should be used for benchmarking."),
        ("2. Investigate district hot water load", "The dominant load is district hot water, not electric use. Review heat exchanger controls, valve leakage, simultaneous heating/cooling, domestic hot water recirculation, and any process or tenant loads."),
        ("3. Review schedules and setpoints", "If the hot water load is legitimate, check occupied/unoccupied schedules, temperature reset, night setback, and weekend operation for warehouse spaces."),
        ("4. Envelope and loading-door leakage", "For warehouse use, inspect overhead doors, vestibules, dock seals, roof insulation, and uncontrolled infiltration paths that can drive heating demand."),
        ("5. Lighting and plug/process loads", "Electricity is small relative to thermal energy, but LED lighting, controls, and tenant process-load review remain practical low-disruption measures."),
        ("6. Add submetering or meter QA workflow", "A single unusually large thermal stream deserves ongoing meter QA, especially if the property remains under review in the benchmarking program."),
    ]
    for title, body in measures:
        page.text(MARGIN, y, title, size=12, font="F2", color="184D73")
        y = page.multiline(MARGIN + 18, y - 18, body, size=10, max_chars=82, leading=14)
        y -= 16

    page = pdf.add_page()
    header(page, "Data Gaps", 5)
    page.text(MARGIN, 675, "Available in SEED", size=15, font="F2")
    y = 645
    for item in [
        "Address, location, owner, ward, parcel/lot, property type, year built, floor area, reporting status.",
        "Reported Site EUI, weather-normalized Site EUI, Source EUI, total GHG emissions, and water use extra data.",
        "Monthly imported meter records for Electric - Grid and District Hot Water for calendar year 2022.",
    ]:
        y = bullet(page, MARGIN, y, item)
        y -= 8
    page.text(MARGIN, 520, "Not available in SEED for this property", size=15, font="F2")
    y = 490
    for item in [
        "ENERGY STAR score, number of stories, building count, conditioned floor area, building systems, equipment age, controls sequences, and operating schedules.",
        "Audit photos, onsite observations, utility tariff costs, comfort/maintenance complaints, and capital cost estimates.",
        "A confirmed explanation for why the canonical gross floor area and reported gross floor area differ.",
    ]:
        y = bullet(page, MARGIN, y, item)
        y -= 8
    page.text(MARGIN, 365, "Recommended Next Steps", size=15, font="F2")
    table(page, MARGIN, 340, [
        ("1", "Pull original utility bills or Portfolio Manager export for PM26961358."),
        ("2", "Confirm whether the district hot water meter is whole-property, shared, or misassigned."),
        ("3", "Confirm the correct gross floor area and update SEED if needed."),
        ("4", "Perform a focused walkthrough of thermal systems, controls, and warehouse envelope conditions."),
        ("5", "After data reconciliation, estimate savings and costs for the highest-confidence measures."),
    ], widths=(35, 465))
    page.multiline(MARGIN, 145, "Screening conclusion: this property is less a normal high-EUI case than a data-reconciliation and thermal-meter-boundary case. If the district hot water readings are valid and assigned correctly, the building warrants a focused thermal systems audit.", size=11, max_chars=88, leading=15)

    return pdf


if __name__ == "__main__":
    out = Path("output/pdf/2258_25th_place_ne_energy_audit_screening_report.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    build_report().save(out)
    print(out)
