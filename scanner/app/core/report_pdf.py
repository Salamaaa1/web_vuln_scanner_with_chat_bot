"""Build the PDF pentest report from the structured report dict (see
scans._build_report).

Layout: executive summary → scope → vulnerabilities (overview + details) →
open ports → live hosts → crawled endpoints → discovered resources →
subdomains. Uses reportlab (pure Python, no system dependencies).
"""
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether,
)

PAGE_W, PAGE_H = A4
MARGIN = 16 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

INK = colors.HexColor("#0f172a")
TEXT = colors.HexColor("#334155")
MUTED = colors.HexColor("#64748b")
LINE = colors.HexColor("#e2e8f0")
SOFT = colors.HexColor("#f8fafc")
HEAD = colors.HexColor("#f1f5f9")
ACCENT = colors.HexColor("#2563eb")

SEVERITY = {
    "critical": ("Critique", colors.HexColor("#b91c1c")),
    "high":     ("Haute",    colors.HexColor("#c2410c")),
    "medium":   ("Moyenne",  colors.HexColor("#a16207")),
    "low":      ("Basse",    colors.HexColor("#15803d")),
    "info":     ("Info",     colors.HexColor("#2563eb")),
}
SEV_ORDER = ["critical", "high", "medium", "low", "info"]

# Long lists are cut in the PDF (the JSON export has everything).
MAX_ENDPOINTS = 200
MAX_RESOURCES = 150
MAX_HOSTS = 60


def _styles():
    ss = getSampleStyleSheet()

    def add(name, **kw):
        ss.add(ParagraphStyle(name=name, **kw))

    add("Title1", fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=colors.white)
    add("TitleSub", fontName="Helvetica", fontSize=9.5, leading=13, textColor=colors.HexColor("#cbd5e1"))
    add("H2", fontName="Helvetica-Bold", fontSize=13.5, leading=17, textColor=INK, spaceBefore=12, spaceAfter=6)
    add("H3", fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=INK)
    add("Body", fontName="Helvetica", fontSize=9, leading=13, textColor=TEXT)
    add("Small", fontName="Helvetica", fontSize=7.8, leading=10.5, textColor=MUTED)
    add("Label", fontName="Helvetica-Bold", fontSize=7.5, leading=10, textColor=MUTED)
    # wordWrap CJK lets very long URLs break anywhere instead of overflowing.
    add("Cell", fontName="Helvetica", fontSize=7.6, leading=9.8, textColor=TEXT, wordWrap="CJK")
    add("CellMono", fontName="Courier", fontSize=7.2, leading=9.4, textColor=TEXT, wordWrap="CJK")
    add("MetricNum", fontName="Helvetica-Bold", fontSize=20, leading=23, textColor=INK, alignment=1)
    add("MetricLbl", fontName="Helvetica", fontSize=7.5, leading=9, textColor=MUTED, alignment=1)
    return ss


def _esc(text) -> str:
    """Escape reportlab markup characters; keep line breaks."""
    s = str(text if text is not None else "")
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return s.replace("\r\n", "\n").replace("\n", "<br/>")


def _table(rows, widths, header=True, zebra=True):
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    cmds = [
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.6),
        ("TEXTCOLOR", (0, 0), (-1, -1), TEXT),
    ]
    if header:
        cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), HEAD),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
        ]
    if zebra and len(rows) > 1:
        cmds.append(("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, SOFT]))
    t.setStyle(TableStyle(cmds))
    return t


def _sev_label(sev, st):
    name, col = SEVERITY.get(sev, SEVERITY["info"])
    return Paragraph(f'<font color="{col.hexval()}"><b>{name.upper()}</b></font>', st["Cell"])


def _risk_level(breakdown: dict):
    for sev in ("critical", "high", "medium", "low"):
        if breakdown.get(sev):
            return SEVERITY[sev]
    return ("Aucun risque identifié", colors.HexColor("#15803d"))


def _footer(target_value):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, 11 * mm, PAGE_W - MARGIN, 11 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, 7 * mm, f"Auto-Pentest — rapport de sécurité — {target_value}"[:110])
        canvas.drawRightString(PAGE_W - MARGIN, 7 * mm, f"Page {doc.page}")
        canvas.restoreState()
    return draw


def _fmt_dt(value) -> str:
    """'2026-11-07T22:21:28Z' -> '07/11/2026 à 22:21 UTC'."""
    if not value:
        return "—"
    import datetime as _dt
    try:
        d = _dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return d.strftime("%d/%m/%Y à %H:%M UTC")
    except ValueError:
        return str(value)


def _header_band(report, st):
    target = report.get("target", {})
    sub = (f"Cible : <b>{_esc(target.get('value', '?'))}</b> &nbsp;·&nbsp; Type : {_esc(target.get('type', '?'))}"
           f"<br/>Scan du {_esc(_fmt_dt(report.get('scanned_at')))} &nbsp;·&nbsp; "
           f"Rapport généré le {_esc(_fmt_dt(report.get('generated_at')))}")
    band = Table([[Paragraph("Rapport de sécurité", st["Title1"])], [Paragraph(sub, st["TitleSub"])]],
                 colWidths=[CONTENT_W])
    band.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), INK),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, 0), 14),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 14),
    ]))
    return band


def _summary(report, st):
    s = report.get("summary", {})
    sb = s.get("severity_breakdown", {}) or {}
    out = [Paragraph("Synthèse", st["H2"])]

    level, col = _risk_level(sb)
    out.append(Paragraph(
        f'Niveau de risque global : <font color="{col.hexval()}"><b>{_esc(level)}</b></font>', st["Body"]))
    out.append(Spacer(1, 6))

    def box(num, lbl):
        return [Paragraph(str(num), st["MetricNum"]), Paragraph(lbl, st["MetricLbl"])]

    cells = [box(s.get("vulnerabilities", 0), "VULNÉRABILITÉS"), box(s.get("endpoints", 0), "URLS UNIQUES"),
             box(s.get("ports", 0), "PORTS OUVERTS"), box(s.get("subdomains", 0), "SOUS-DOMAINES")]
    w = CONTENT_W / 4
    t = Table([[c[0] for c in cells], [c[1] for c in cells]], colWidths=[w] * 4)
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0, colors.white),
        ("LINEAFTER", (0, 0), (-2, -1), 0.5, LINE),
        ("BACKGROUND", (0, 0), (-1, -1), SOFT),
        ("TOPPADDING", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 9),
    ]))
    out.append(t)
    out.append(Spacer(1, 6))

    # Severity breakdown row
    row = []
    for sev in SEV_ORDER:
        name, c = SEVERITY[sev]
        row.append(Paragraph(f'<font color="{c.hexval()}"><b>{sb.get(sev, 0)}</b></font> {name}', st["Body"]))
    sev_t = Table([row], colWidths=[CONTENT_W / 5] * 5)
    sev_t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                               ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    out.append(sev_t)
    return out


def _scope(report, st):
    sc = report.get("scope", {}) or {}
    tools = ", ".join(sc.get("tools") or []) or "—"
    lines = [f"<b>Outils exécutés :</b> {_esc(tools)}"]
    if sc.get("nuclei_targets") is not None:
        lines.append(f"<b>Analyse de vulnérabilités (nuclei) :</b> {sc.get('nuclei_targets')} cible(s) de base, "
                     f"{sc.get('nuclei_dast_targets') or 0} URL(s) à paramètres testée(s) en fuzzing (XSS, SQLi, LFI…)")
    if sc.get("nuclei_timed_out"):
        lines.append("<b>Note :</b> l'analyse nuclei a atteint sa limite de temps ; les résultats peuvent être partiels.")
    lines.append(f"<b>Scan de ports :</b> {'effectué' if sc.get('port_scan_done') else 'non effectué pour ce type de cible'}")
    return [Paragraph("Périmètre de l'analyse", st["H2"])] + [Paragraph(l, st["Body"]) for l in lines]


def _vulnerabilities(report, st):
    vulns = report.get("vulnerabilities", []) or []
    out = [Paragraph(f"Vulnérabilités ({len(vulns)})", st["H2"])]
    if not vulns:
        out.append(Paragraph(
            "Aucune vulnérabilité de sévérité basse ou supérieure n'a été détectée par les modèles exécutés. "
            "Cela ne garantit pas l'absence de failles : un test manuel reste recommandé.", st["Body"]))
        return out

    # Overview
    rows = [["#", "Sévérité", "Vulnérabilité", "Emplacement"]]
    for i, v in enumerate(vulns, 1):
        rows.append([str(i), _sev_label(v.get("severity"), st),
                     Paragraph(_esc(v.get("title")), st["Cell"]),
                     Paragraph(_esc(v.get("target") or "—"), st["CellMono"])])
    out.append(_table(rows, [8 * mm, 20 * mm, 62 * mm, CONTENT_W - 90 * mm]))

    # Details
    out.append(Paragraph("Détail des vulnérabilités", st["H2"]))
    for i, v in enumerate(vulns, 1):
        name, col = SEVERITY.get(v.get("severity"), SEVERITY["info"])
        block = []
        title = Table([[Paragraph(f'<font color="white"><b>{name.upper()}</b></font>', st["Cell"]),
                        Paragraph(f"{i}. {_esc(v.get('title'))}", st["H3"])]],
                      colWidths=[22 * mm, CONTENT_W - 22 * mm])
        title.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), col),
            ("BACKGROUND", (1, 0), (1, 0), SOFT),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, 0), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ]))
        block.append(title)

        fields = [("Emplacement", v.get("target"), "CellMono"),
                  ("Modèle", " · ".join(x for x in [v.get("template_id"), v.get("type")] if x), "CellMono"),
                  ("Description", v.get("description"), "Cell"),
                  ("Remédiation", v.get("remediation"), "Cell"),
                  ("Analyse IA", v.get("ai_analysis"), "Cell"),
                  ("Correctifs IA", v.get("ai_remediation"), "Cell"),
                  ("Références", "\n".join(v.get("references") or []), "CellMono")]
        rows = [[Paragraph(lbl.upper(), st["Label"]), Paragraph(_esc(val), st[style])]
                for lbl, val, style in fields if val]
        if rows:
            ft = Table(rows, colWidths=[28 * mm, CONTENT_W - 28 * mm])
            ft.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("LINEBELOW", (0, 0), (-1, -2), 0.3, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            block.append(ft)
        block.append(Spacer(1, 8))
        out.append(KeepTogether(block))
    return out


def _ports(report, st):
    ports = report.get("open_ports", []) or []
    scope = report.get("scope", {}) or {}
    out = [Paragraph(f"Ports ouverts ({len(ports)})", st["H2"])]
    if not ports:
        msg = ("Aucun port ouvert détecté sur les ports analysés." if scope.get("port_scan_done")
               else "Le scan de ports n'a pas été exécuté pour cette cible.")
        out.append(Paragraph(msg, st["Body"]))
        return out
    rows = [["Port", "Proto", "Service", "Produit / Version"]]
    for p in ports:
        rows.append([str(p.get("port", "")), p.get("protocol", ""), Paragraph(_esc(p.get("service")), st["Cell"]),
                     Paragraph(_esc(f"{p.get('product', '')} {p.get('version', '')}".strip() or "—"), st["Cell"])])
    out.append(_table(rows, [16 * mm, 16 * mm, 40 * mm, CONTENT_W - 72 * mm]))
    osi = report.get("os_info") or {}
    if osi.get("name"):
        out.append(Spacer(1, 4))
        out.append(Paragraph(f"Système détecté : {_esc(osi.get('name'))} ({osi.get('accuracy', '?')} %)", st["Small"]))
    return out


def _hosts(report, st):
    hosts = report.get("live_endpoints", []) or []
    out = [Paragraph(f"Hôtes web actifs ({len(hosts)})", st["H2"])]
    if not hosts:
        out.append(Paragraph("Aucun hôte web actif détecté.", st["Body"]))
        return out
    rows = [["Code", "URL", "Titre", "Serveur / Technologies"]]
    for h in hosts[:MAX_HOSTS]:
        tech = ", ".join(h.get("tech") or [])
        server = " · ".join(x for x in [h.get("webserver"), tech] if x)
        rows.append([str(h.get("status_code") or ""), Paragraph(_esc(h.get("url")), st["CellMono"]),
                     Paragraph(_esc(h.get("title") or "—"), st["Cell"]), Paragraph(_esc(server or "—"), st["Cell"])])
    out.append(_table(rows, [12 * mm, 62 * mm, 45 * mm, CONTENT_W - 119 * mm]))
    return out


def _endpoints(report, st):
    eps = report.get("crawled_endpoints", []) or []
    out = [Paragraph(f"Endpoints découverts par exploration ({len(eps)})", st["H2"])]
    if not eps:
        out.append(Paragraph("Aucun endpoint découvert par l'exploration (katana).", st["Body"]))
        return out
    with_params = sum(1 for e in eps if e.get("has_params"))
    out.append(Paragraph(f"{with_params} endpoint(s) avec paramètres (cibles du fuzzing).", st["Small"]))
    out.append(Spacer(1, 4))
    rows = [["Méthode", "URL"]]
    for e in eps[:MAX_ENDPOINTS]:
        rows.append([e.get("method", "GET"), Paragraph(_esc(e.get("url")), st["CellMono"])])
    out.append(_table(rows, [16 * mm, CONTENT_W - 16 * mm]))
    if len(eps) > MAX_ENDPOINTS:
        out.append(Paragraph(f"… et {len(eps) - MAX_ENDPOINTS} autre(s) (liste complète dans l'export JSON).", st["Small"]))
    return out


def _resources(report, st):
    res = report.get("discovered_resources", []) or []
    out = [Paragraph(f"Ressources découvertes par force brute ({len(res)})", st["H2"])]
    if not res:
        out.append(Paragraph("Aucune ressource cachée découverte (feroxbuster).", st["Body"]))
        return out
    rows = [["Code", "URL"]]
    for r in res[:MAX_RESOURCES]:
        rows.append([str(r.get("status_code") or ""), Paragraph(_esc(r.get("url")), st["CellMono"])])
    out.append(_table(rows, [14 * mm, CONTENT_W - 14 * mm]))
    if len(res) > MAX_RESOURCES:
        out.append(Paragraph(f"… et {len(res) - MAX_RESOURCES} autre(s) (liste complète dans l'export JSON).", st["Small"]))
    return out


def _subdomains(report, st):
    subs = report.get("subdomains", []) or []
    if not subs:
        return []
    out = [Paragraph(f"Sous-domaines ({len(subs)})", st["H2"])]
    rows = [[Paragraph(_esc(s), st["CellMono"]) for s in subs[i:i + 3]] for i in range(0, len(subs), 3)]
    rows[-1] += [""] * (3 - len(rows[-1]))
    out.append(_table(rows, [CONTENT_W / 3] * 3, header=False))
    return out


def build_report_pdf(report: dict) -> bytes:
    buf = io.BytesIO()
    target_value = (report.get("target") or {}).get("value", "")
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=16 * mm,
        title=f"Rapport de sécurité — {target_value}", author="Auto-Pentest",
    )
    st = _styles()
    story = [_header_band(report, st)]
    story += _summary(report, st)
    story += _scope(report, st)
    story += _vulnerabilities(report, st)
    story += _ports(report, st)
    story += _hosts(report, st)
    story += _endpoints(report, st)
    story += _resources(report, st)
    story += _subdomains(report, st)
    footer = _footer(target_value)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
