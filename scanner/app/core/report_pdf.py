"""Build a detailed PDF pentest report from the structured report dict.

Uses reportlab (pure-Python, no system dependencies) so it works identically on
Windows dev machines and Linux containers.
"""
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

SEVERITY_COLORS = {
    "critical": colors.HexColor("#b91c1c"),
    "high":     colors.HexColor("#c2410c"),
    "medium":   colors.HexColor("#a16207"),
    "low":      colors.HexColor("#15803d"),
    "info":     colors.HexColor("#2563eb"),
}


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="H1x", fontSize=20, leading=24, spaceAfter=4,
                              textColor=colors.HexColor("#0f172a"), fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Sub", fontSize=9, leading=12, textColor=colors.HexColor("#64748b"),
                              fontName="Helvetica"))
    styles.add(ParagraphStyle(name="H2x", fontSize=13, leading=16, spaceBefore=14, spaceAfter=6,
                              textColor=colors.HexColor("#1e293b"), fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Body", fontSize=9, leading=13, textColor=colors.HexColor("#334155")))
    styles.add(ParagraphStyle(name="Mono", fontSize=8, leading=11, fontName="Courier",
                              textColor=colors.HexColor("#334155")))
    styles.add(ParagraphStyle(name="Cell", fontSize=7.5, leading=9.5, fontName="Helvetica",
                              textColor=colors.HexColor("#334155")))
    return styles


def _esc(text: str) -> str:
    """Escape characters that reportlab's Paragraph parser treats as markup."""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build_report_pdf(report: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=16 * mm,
        title=f"Rapport de scan — {report.get('target', {}).get('value', '')}",
    )
    st = _styles()
    story = []

    target = report.get("target", {})
    summary = report.get("summary", {})

    # ── Header ──────────────────────────────────────────────
    story.append(Paragraph("Rapport de sécurité", st["H1x"]))
    story.append(Paragraph(
        f"Cible : <b>{target.get('value', '?')}</b> &nbsp;·&nbsp; Type : {target.get('type', '?')} "
        f"&nbsp;·&nbsp; Généré : {report.get('generated_at', '')}",
        st["Sub"],
    ))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))

    # ── Summary metrics ─────────────────────────────────────
    story.append(Paragraph("Résumé", st["H2x"]))
    sb = summary.get("severity_breakdown", {})
    summary_data = [
        ["Sous-domaines", "Endpoints", "Ports ouverts", "Vulnérabilités"],
        [
            str(summary.get("subdomains", 0)),
            str(summary.get("endpoints", 0)),
            str(summary.get("ports", 0)),
            str(summary.get("vulnerabilities", 0)),
        ],
    ]
    t = Table(summary_data, colWidths=[42 * mm] * 4)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#475569")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, 1), 16),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 1), (-1, 1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))

    # Severity breakdown line
    if sb:
        chips = " &nbsp; ".join(
            f'<font color="{SEVERITY_COLORS.get(k, colors.grey).hexval()}"><b>{v}</b> {k}</font>'
            for k, v in sb.items() if v
        )
        if chips:
            story.append(Paragraph(chips, st["Body"]))

    # ── Open ports ──────────────────────────────────────────
    ports = report.get("open_ports", [])
    if ports:
        story.append(Paragraph(f"Ports ouverts ({len(ports)})", st["H2x"]))
        rows = [["Port", "Proto", "Service", "Produit / Version"]]
        for p in ports:
            rows.append([
                str(p.get("port", "")), p.get("protocol", ""),
                p.get("service", "") or "",
                f"{p.get('product','') or ''} {p.get('version','') or ''}".strip(),
            ])
        story.append(_grid(rows, [18 * mm, 18 * mm, 40 * mm, 78 * mm]))

    cell = st["Cell"]

    # ── Live endpoints ──────────────────────────────────────
    endpoints = report.get("live_endpoints", [])
    if endpoints:
        story.append(Paragraph(f"Endpoints actifs ({len(endpoints)})", st["H2x"]))
        rows = [["Code", "URL", "Titre / Technologies"]]
        for e in endpoints[:60]:
            tech = ", ".join(e.get("tech", []) or [])
            rows.append([
                str(e.get("status_code", "")),
                Paragraph(_esc(e.get("url", "") or ""), cell),
                Paragraph(_esc(e.get("title") or tech or ""), cell),
            ])
        story.append(_grid(rows, [16 * mm, 80 * mm, 58 * mm]))

    # ── Subdomains ──────────────────────────────────────────
    subs = report.get("subdomains", [])
    if subs:
        story.append(Paragraph(f"Sous-domaines ({len(subs)})", st["H2x"]))
        story.append(Paragraph(", ".join(subs), st["Mono"]))

    # ── Discovered resources ────────────────────────────────
    res = report.get("discovered_resources", [])
    if res:
        story.append(Paragraph(f"Ressources découvertes ({len(res)})", st["H2x"]))
        rows = [["Code", "URL"]]
        for r in res[:80]:
            rows.append([str(r.get("status_code", "")), Paragraph(_esc(r.get("url", "") or ""), cell)])
        story.append(_grid(rows, [16 * mm, 138 * mm]))

    # ── Vulnerabilities ─────────────────────────────────────
    vulns = report.get("vulnerabilities", [])
    story.append(Paragraph(f"Vulnérabilités ({len(vulns)})", st["H2x"]))
    if not vulns:
        story.append(Paragraph("Aucune vulnérabilité détectée.", st["Body"]))
    else:
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        vulns_sorted = sorted(vulns, key=lambda v: order.get((v.get("severity") or "info").lower(), 5))
        rows = [["Sévérité", "Titre", "Description"]]
        for v in vulns_sorted:
            rows.append([
                (v.get("severity") or "info").upper(),
                Paragraph(_esc(v.get("title") or ""), cell),
                Paragraph(_esc((v.get("description") or "")[:300]), cell),
            ])
        tbl = _grid(rows, [22 * mm, 62 * mm, 70 * mm], header_bg="#0f172a")
        # colour the severity cells
        style_cmds = []
        for i, v in enumerate(vulns_sorted, start=1):
            sev = (v.get("severity") or "info").lower()
            style_cmds.append(("TEXTCOLOR", (0, i), (0, i), SEVERITY_COLORS.get(sev, colors.grey)))
            style_cmds.append(("FONTNAME", (0, i), (0, i), "Helvetica-Bold"))
        tbl.setStyle(TableStyle(style_cmds))
        story.append(tbl)

    doc.build(story)
    return buf.getvalue()


def _grid(rows, col_widths, header_bg="#f1f5f9"):
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    header_color = colors.HexColor(header_bg)
    header_text = colors.white if header_bg.startswith("#0") else colors.HexColor("#475569")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), header_text),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    return t
