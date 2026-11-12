"""Professional PDF export (Feature 7) built with ReportLab."""
import io
from datetime import date, datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from app.utils.helpers import is_http_url

INDIGO = colors.HexColor("#4338CA")
SLATE = colors.HexColor("#475569")
LIGHT = colors.HexColor("#F1F5F9")

LABELS = {
    "verified": ("Verified", "#15803D"),
    "partially_supported": ("Partially supported", "#B45309"),
    "needs_verification": ("Needs verification", "#B91C1C"),
    "potentially_outdated": ("Potentially outdated", "#C2410C"),
}
FRESH = {"recent": "Recent", "potentially_outdated": "Potentially outdated", "unknown": "Date unknown"}


def _safe(s) -> str:
    """Standard PDF fonts cover Latin-1/cp1252 only; replace anything else instead of crashing."""
    return str(s if s is not None else "").encode("cp1252", "replace").decode("cp1252")


def esc(s) -> str:
    return escape(_safe(s))


def _fmt_date(d) -> str:
    if not d:
        return "unknown"
    if isinstance(d, str):
        try:
            d = date.fromisoformat(d[:10])
        except ValueError:
            return esc(d)
    return d.strftime("%d %b %Y")


def _styles():
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=ss["Title"], fontSize=22, textColor=INDIGO, alignment=TA_LEFT, spaceAfter=2),
        "sub": ParagraphStyle("s", parent=ss["Normal"], fontSize=11, textColor=SLATE, spaceAfter=8),
        "h1": ParagraphStyle("h1", parent=ss["Heading2"], fontSize=14, textColor=INDIGO, spaceBefore=14, spaceAfter=4),
        "h2": ParagraphStyle("h2", parent=ss["Heading3"], fontSize=11, textColor=colors.HexColor("#1E293B"), spaceBefore=8, spaceAfter=2),
        "body": ParagraphStyle("b", parent=ss["Normal"], fontSize=9.5, leading=13),
        "bullet": ParagraphStyle("bl", parent=ss["Normal"], fontSize=9.5, leading=13, leftIndent=12, bulletIndent=2, spaceAfter=3),
        "small": ParagraphStyle("sm", parent=ss["Normal"], fontSize=8, leading=10.5, textColor=SLATE),
        "banner": ParagraphStyle("bn", parent=ss["Normal"], fontSize=10, textColor=colors.white, backColor=colors.HexColor("#B91C1C"), borderPadding=6, leading=14),
    }


def _tag(item: dict) -> str:
    label, color = LABELS.get(item.get("evidence_label", ""), LABELS["needs_verification"])
    refs = item.get("refs") or []
    ref_txt = f" <font size=7 color='#475569'>[{', '.join(str(r) for r in refs)}]</font>" if refs else ""
    ai = " <font size=7 color='#64748B'>(AI interpretation)</font>" if item.get("is_inference") else ""
    return f" <font size=7 color='{color}'><b>[{label}]</b></font>{ref_txt}{ai}"


def _statements(items: list, st) -> list:
    return [Paragraph(f"{esc(i['text'])}{_tag(i)}", st["bullet"], bulletText="•") for i in items]


def _section(title: str, items: list, st) -> list:
    if not items:
        return []
    return [Paragraph(esc(title), st["h2"]), *_statements(items, st)]


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(SLATE)
    canvas.drawString(18 * mm, 10 * mm, "MeetWise AI - AI-assisted briefing. Verify important facts against the cited sources.")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf(meeting, briefing, sources: list) -> bytes:
    """meeting/briefing/sources are ORM objects; briefing.content is the validated JSON dict."""
    st = _styles()
    c = briefing.content
    ref_map = {s.id: i for i, s in enumerate(sorted(sources, key=lambda s: s.id), start=1)}

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
        title=f"MeetWise AI Briefing - {_safe(meeting.organization_or_person)}", author="MeetWise AI",
    )
    story: list = [Paragraph("MeetWise AI", st["sub"]), Paragraph("Pre-Meeting Briefing", st["title"]),
                   Paragraph(esc(meeting.organization_or_person), st["sub"])]

    if briefing.is_mock:
        story += [Paragraph("DEMO DATA: this briefing was generated in mock mode. It is NOT real research.", st["banner"]), Spacer(1, 6)]

    details = [
        ["Organisation / person", esc(meeting.organization_or_person)],
        ["Attendee", esc(meeting.attendee_name or "Not specified")],
        ["Date and time", f"{_fmt_date(meeting.meeting_date)}, {meeting.meeting_time.strftime('%H:%M')}"],
        ["Purpose", esc(meeting.purpose)],
        ["Briefing generated", briefing.generated_at.strftime("%d %b %Y %H:%M UTC")],
    ]
    t = Table([[Paragraph(f"<b>{k}</b>", st["body"]), Paragraph(v, st["body"])] for k, v in details], colWidths=[42 * mm, 130 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), LIGHT), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")), ("TOPPADDING", (0, 0), (-1, -1), 4),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story += [t, Spacer(1, 8)]

    ev = c.get("evidence_summary", {})
    story += [Paragraph("Evidence summary", st["h1"]),
              Paragraph(
                  f"{ev.get('total_sources', 0)} sources reviewed ({ev.get('recent_sources', 0)} recent, "
                  f"{ev.get('outdated_sources', 0)} potentially outdated, {ev.get('undated_sources', 0)} undated). "
                  f"Findings: {ev.get('verified', 0)} verified, {ev.get('partially_supported', 0)} partially supported, "
                  f"{ev.get('needs_verification', 0)} need verification, {ev.get('potentially_outdated', 0)} potentially outdated. "
                  "Statements marked 'AI interpretation' are analysis, not quoted facts. Numbers in [brackets] refer to the source list at the end.",
                  st["body"])]

    story += [Paragraph("Meeting overview", st["h1"]), *_statements(c.get("meeting_overview", []), st)]

    co = c.get("company", {})
    story.append(Paragraph("Company background", st["h1"]))
    for key, title in [("overview", "Overview"), ("business_model", "Business model"), ("products_services", "Products and services"),
                       ("competitors", "Competitors"), ("strategic_initiatives", "Strategic initiatives"), ("challenges", "Potential challenges")]:
        story += _section(title, co.get(key, []), st)

    at = c.get("attendee")
    if at:
        story.append(Paragraph("Attendee background", st["h1"]))
        if at.get("identity_note"):
            story.append(Paragraph(f"<i>Note: {esc(at['identity_note'])}</i>", st["small"]))
        for key, title in [("role", "Current role"), ("experience", "Previous experience"), ("achievements", "Public achievements"),
                           ("expertise", "Areas of expertise"), ("public_content", "Interviews and articles")]:
            story += _section(title, at.get(key, []), st)

    story.append(Paragraph("Recent developments (last 30 days prioritised)", st["h1"]))
    news = c.get("recent_developments", [])
    if not news:
        story.append(Paragraph("No recent news was found.", st["body"]))
    for n in news:
        url = n["url"]
        link = f"<link href=\"{escape(url, {chr(34): '&quot;'})}\" color=\"#2563EB\">{esc(url)}</link>" if is_http_url(url) else esc(url)
        story.append(KeepTogether([
            Paragraph(f"<b>{esc(n['headline'])}</b> <font size=7 color='#475569'>[{n['ref']}]</font>", st["body"]),
            Paragraph(f"{_fmt_date(n.get('published_date'))} · {FRESH.get(n.get('freshness'), 'Date unknown')}", st["small"]),
            Paragraph(esc(n["summary"]), st["body"]), Paragraph(link, st["small"]), Spacer(1, 5)]))

    story += [Paragraph("Key insights", st["h1"]), *_statements(c.get("insights", []), st)]

    story.append(Paragraph("Potential opportunities", st["h1"]))
    for o in c.get("opportunities", []):
        story.append(KeepTogether([
            Paragraph(f"<b>{esc(o['title'])}</b> <font size=7 color='#64748B'>({esc(o['type'])})</font>{_tag(o)}", st["body"]),
            Paragraph(esc(o.get("description", "")), st["bullet"]),
            Paragraph(f"<b>Why relevant:</b> {esc(o.get('why_relevant', ''))}", st["bullet"]), Spacer(1, 3)]))
    if not c.get("opportunities"):
        story.append(Paragraph("No opportunities could be identified from the evidence.", st["body"]))

    story += [Paragraph("Potential risks", st["h1"]), *_statements(c.get("risks", []), st)]
    story += [Paragraph("Suggested discussion points", st["h1"]), *_statements(c.get("discussion_points", []), st)]
    story += [Paragraph("Recommended meeting strategy", st["h1"]), *_statements(c.get("strategy", []), st)]

    story.append(Paragraph("Suggested questions", st["h1"]))
    qs = c.get("questions", {})
    for key, title in [("strategic", "Strategic"), ("technical", "Technical"), ("business", "Business"),
                       ("collaboration", "Collaboration"), ("follow_up", "Follow-up")]:
        items = qs.get(key, [])
        if not items:
            continue
        story.append(Paragraph(title, st["h2"]))
        for q in items:
            refs = f" <font size=7 color='#475569'>[{', '.join(str(r) for r in q.get('refs', []))}]</font>" if q.get("refs") else ""
            extra = f"<br/><font size=8 color='#475569'>Why ask: {esc(q['rationale'])}</font>" if q.get("rationale") else ""
            extra += f"<br/><font size=8 color='#475569'>Could reveal: {esc(q['reveals'])}</font>" if q.get("reveals") else ""
            story.append(Paragraph(f"{esc(q['question'])}{refs}{extra}", st["bullet"], bulletText="•"))

    if c.get("limitations"):
        story.append(Paragraph("Limitations and gaps", st["h1"]))
        story += [Paragraph(esc(x), st["bullet"], bulletText="•") for x in c["limitations"]]

    story += [Paragraph("Source references", st["h1"]), HRFlowable(width="100%", color=colors.HexColor("#CBD5E1"))]
    for s in sorted(sources, key=lambda s: s.id):
        link = f"<link href=\"{escape(s.url, {chr(34): '&quot;'})}\" color=\"#2563EB\">{esc(s.url)}</link>" if is_http_url(s.url) else esc(s.url)
        story.append(KeepTogether([
            Paragraph(f"<b>[{ref_map[s.id]}]</b> {esc(s.title)}", st["body"]),
            Paragraph(f"{esc(s.category.title())} · Published: {_fmt_date(s.published_date)} · Retrieved: "
                      f"{_fmt_date(s.retrieved_at.date() if isinstance(s.retrieved_at, datetime) else s.retrieved_at)} · "
                      f"{FRESH.get(s.freshness, 'Date unknown')}", st["small"]),
            Paragraph(link, st["small"]), Spacer(1, 4)]))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
