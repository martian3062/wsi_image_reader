from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def build_pdf_report(row, output_path: str) -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    y = height - 60
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, "Biotech Fast App - Analysis Report")

    y -= 40
    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"File: {row['filename']}")
    y -= 20
    c.drawString(50, y, f"Pattern: {row['pattern_label']}")
    y -= 20
    c.drawString(50, y, f"Risk Score: {row['risk_score']}")
    y -= 20
    c.drawString(50, y, f"Image Size: {row['width']} x {row['height']}")

    y -= 35
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Feature Breakdown")

    c.setFont("Helvetica", 10)
    fields = [
        ("Average Intensity", row["avg_intensity"]),
        ("Intensity Std", row["intensity_std"]),
        ("Edge Density", row["edge_density"]),
        ("Redness Score", row["redness_score"]),
        ("Saturation Score", row["saturation_score"]),
        ("Tissue Ratio", row["tissue_ratio"]),
    ]

    for label, value in fields:
        y -= 18
        c.drawString(60, y, f"{label}: {value}")

    y -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Summary")
    y -= 20
    c.setFont("Helvetica", 10)

    text = c.beginText(60, y)
    text.setLeading(14)
    for line in str(row["summary"]).split(". "):
        if line.strip():
            text.textLine(line.strip())
    c.drawText(text)

    c.showPage()
    c.save()
    return output_path