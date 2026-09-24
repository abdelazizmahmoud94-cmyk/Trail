"""Multi-format Report Exporter."""

import json
from pathlib import Path
from typing import Dict, Optional

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    )
    from reportlab.lib.styles import getSampleStyleSheet
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


class ReportExporter:
    def __init__(self, output_dir: str = "reports_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_json(self, report: Dict, filename: str) -> Path:
        p = self.output_dir / f"{filename}.json"
        p.write_text(json.dumps(report, indent=2, default=str),
                       encoding="utf-8")
        return p

    def export_csv(self, report: Dict, filename: str) -> Path:
        p = self.output_dir / f"{filename}.csv"
        lines = []
        lines.append(f"# {report.get('report_type', 'report')}")
        lines.append(f"# Generated: {report.get('generated_at', '')}")
        lines.append("")
        for s in report.get("sections", []):
            lines.append(f"## {s['title']}")
            if s["type"] == "table":
                headers = s["content"].get("headers", [])
                rows = s["content"].get("rows", [])
                lines.append(",".join(str(h) for h in headers))
                for r in rows:
                    lines.append(",".join(str(v) for v in r))
            elif s["type"] == "text":
                lines.append(str(s["content"]))
            lines.append("")
        p.write_text("\n".join(lines), encoding="utf-8")
        return p

    def export_html(self, report: Dict, filename: str) -> Path:
        p = self.output_dir / f"{filename}.html"
        parts = [
            "<!DOCTYPE html><html><head><meta charset='utf-8'>",
            f"<title>{report.get('report_type', 'Report')}</title>",
            "<style>",
            "body{font-family:sans-serif;max-width:1000px;margin:40px auto;",
            "background:#0f172a;color:#e2e8f0;padding:20px;}",
            "h1{color:#38bdf8;}h2{color:#38bdf8;margin-top:30px;",
            "border-bottom:1px solid #334155;padding-bottom:6px;}",
            "table{width:100%;border-collapse:collapse;margin:10px 0;",
            "background:#1e293b;border-radius:4px;}",
            "th{background:#0c4a6e;padding:10px;text-align:left;color:#bae6fd;}",
            "td{padding:8px 10px;border-bottom:1px solid #334155;}",
            "</style></head><body>",
            f"<h1>{report.get('report_type', 'Report')}</h1>",
            f"<p style='color:#94a3b8;'>Generated: "
            f"{report.get('generated_at', '')}</p>"]
        for s in report.get("sections", []):
            parts.append(f"<h2>{s['title']}</h2>")
            if s["type"] == "text":
                parts.append(f"<p>{s['content']}</p>")
            elif s["type"] == "table":
                headers = s["content"].get("headers", [])
                rows = s["content"].get("rows", [])
                parts.append("<table><thead><tr>")
                for h in headers:
                    parts.append(f"<th>{h}</th>")
                parts.append("</tr></thead><tbody>")
                for r in rows:
                    parts.append("<tr>")
                    for v in r:
                        parts.append(f"<td>{v}</td>")
                    parts.append("</tr>")
                parts.append("</tbody></table>")
        parts.append("</body></html>")
        p.write_text("".join(parts), encoding="utf-8")
        return p

    def export_pdf(self, report: Dict, filename: str) -> Optional[Path]:
        if not PDF_AVAILABLE:
            return self.export_html(report, filename)
        p = self.output_dir / f"{filename}.pdf"
        doc = SimpleDocTemplate(str(p), pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        title = report.get("report_type", "Report").title()
        elements.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
        elements.append(Paragraph(
            f"Generated: {report.get('generated_at', '')}",
            styles["Normal"]))
        elements.append(Spacer(1, 20))
        for s in report.get("sections", []):
            elements.append(Paragraph(
                f"<b>{s['title']}</b>", styles["Heading2"]))
            if s["type"] == "text":
                elements.append(Paragraph(str(s["content"]),
                                            styles["Normal"]))
            elif s["type"] == "table":
                data = [s["content"].get("headers", [])]
                for r in s["content"].get("rows", []):
                    data.append([str(v) for v in r])
                if len(data) > 1:
                    tbl = Table(data, repeatRows=1)
                    tbl.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0),
                         colors.HexColor("#0c4a6e")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                        ("GRID", (0, 0), (-1, -1), 0.5,
                         colors.HexColor("#334155")),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                         [colors.white, colors.HexColor("#e2e8f0")]),
                    ]))
                    elements.append(tbl)
            elements.append(Spacer(1, 15))
        doc.build(elements)
        return p

    def export_all(self, report: Dict,
                     base_filename: str) -> Dict[str, Path]:
        outputs = {}
        outputs["json"] = self.export_json(report, base_filename)
        outputs["csv"] = self.export_csv(report, base_filename)
        outputs["html"] = self.export_html(report, base_filename)
        pdf = self.export_pdf(report, base_filename)
        if pdf:
            outputs["pdf"] = pdf
        return outputs
