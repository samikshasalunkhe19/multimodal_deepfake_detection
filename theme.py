"""Look and feel: CSS plus small HTML builders (risk meter, reason cards)."""
from __future__ import annotations

import html
import math
from typing import Dict, List

LEVEL = {
    "Low":    {"color": "#16a34a", "soft": "#dcfce7", "text": "Low risk",    "icon": "✓"},
    "Medium": {"color": "#d97706", "soft": "#fef3c7", "text": "Medium risk", "icon": "!"},
    "High":   {"color": "#dc2626", "soft": "#fee2e2", "text": "High risk",   "icon": "⚠"},
}
KIND = {
    "risk": {"color": "#dc2626", "soft": "#fef2f2", "icon": "▲", "tag": "Raises risk"},
    "ok":   {"color": "#16a34a", "soft": "#f0fdf4", "icon": "✓", "tag": "Reassuring"},
    "info": {"color": "#4f46e5", "soft": "#eef2ff", "icon": "i", "tag": "Context"},
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp { font-family: 'Inter', system-ui, sans-serif; }
.stApp { background: linear-gradient(180deg, #f5f7ff 0%, #ffffff 380px); }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 1.2rem; max-width: 1150px; }

.hero { background: linear-gradient(120deg, #312e81 0%, #4f46e5 45%, #0ea5e9 100%);
  border-radius: 22px; padding: 34px 38px; color: #fff; margin-bottom: 22px;
  box-shadow: 0 14px 40px rgba(79,70,229,.28); position: relative; overflow: hidden; }
.hero:after { content: ""; position: absolute; right: -60px; top: -60px; width: 280px; height: 280px;
  background: radial-gradient(circle, rgba(255,255,255,.22), transparent 65%); }
.hero .eyebrow { font-size: .78rem; letter-spacing: .14em; text-transform: uppercase; opacity: .85; font-weight: 600; }
.hero h1 { color: #fff; font-size: 2.1rem; line-height: 1.15; margin: 6px 0 8px; font-weight: 800; padding: 0; }
.hero p { margin: 0; font-size: 1.02rem; opacity: .92; max-width: 640px; }
.chips { margin-top: 18px; display: flex; gap: 10px; flex-wrap: wrap; }
.chip { background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.28); padding: 6px 14px;
  border-radius: 999px; font-size: .85rem; font-weight: 600; backdrop-filter: blur(4px); }

.step { display: flex; align-items: center; gap: 12px; margin: 6px 0 10px; }
.step .num { width: 30px; height: 30px; border-radius: 50%; background: #4f46e5; color: #fff; display: flex;
  align-items: center; justify-content: center; font-weight: 700; font-size: .9rem; flex: none; }
.step .t { font-weight: 700; font-size: 1.12rem; color: #1e1b4b; }
.step .s { color: #64748b; font-size: .9rem; }

.card { background: #fff; border: 1px solid #e5e7f3; border-radius: 18px; padding: 22px 24px;
  box-shadow: 0 4px 18px rgba(30,27,75,.06); }
.drop-title { font-weight: 700; color: #1e1b4b; font-size: 1.02rem; margin-bottom: 2px; }
.drop-sub { color: #64748b; font-size: .85rem; margin-bottom: 8px; }

[data-testid="stFileUploader"] section { border: 2px dashed #c7d2fe; background: #f8faff; border-radius: 16px; }
[data-testid="stFileUploader"] section:hover { border-color: #6366f1; background: #eef2ff; }
.stButton > button[kind="primary"], .stDownloadButton > button { border-radius: 12px; font-weight: 700;
  padding: .7rem 1.4rem; border: none; background: linear-gradient(120deg, #4f46e5, #0ea5e9); color: #fff; }
.stButton > button[kind="primary"]:hover { filter: brightness(1.07); transform: translateY(-1px); }
.stButton > button { border-radius: 12px; font-weight: 600; }
.stTabs [data-baseweb="tab-list"] { gap: 6px; background: #eef2ff; padding: 6px; border-radius: 14px; }
.stTabs [data-baseweb="tab"] { border-radius: 10px; padding: 8px 18px; font-weight: 600; height: auto; }
.stTabs [aria-selected="true"] { background: #fff; box-shadow: 0 2px 8px rgba(79,70,229,.18); }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

.result { display: grid; grid-template-columns: 260px 1fr; gap: 26px; align-items: center; }
@media (max-width: 760px) { .result { grid-template-columns: 1fr; } .hero h1 { font-size: 1.6rem; } }
.badge { display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 999px;
  font-weight: 700; font-size: .9rem; }
.verdict { font-size: 1.5rem; font-weight: 800; color: #1e1b4b; margin: 10px 0 6px; line-height: 1.25; }
.summary { color: #475569; font-size: .97rem; line-height: 1.55; }
.meter-label { display: flex; justify-content: space-between; font-size: .8rem; color: #64748b; margin: 14px 0 5px; }
.meter { height: 9px; border-radius: 99px; background: #e5e7eb; overflow: hidden; }
.meter > div { height: 100%; border-radius: 99px; background: linear-gradient(90deg, #6366f1, #0ea5e9); }

.section-title { font-size: 1.2rem; font-weight: 800; color: #1e1b4b; margin: 26px 0 4px; }
.section-sub { color: #64748b; font-size: .9rem; margin-bottom: 12px; }
.reason { display: flex; gap: 14px; padding: 14px 16px; border-radius: 14px; margin-bottom: 10px;
  border: 1px solid transparent; }
.reason .ic { width: 28px; height: 28px; border-radius: 50%; color: #fff; display: flex; align-items: center;
  justify-content: center; font-weight: 800; font-size: .8rem; flex: none; margin-top: 2px; }
.reason .rt { font-weight: 700; color: #1e1b4b; font-size: .98rem; }
.reason .rd { color: #475569; font-size: .89rem; margin-top: 2px; line-height: 1.5; }
.reason .tag { margin-left: 8px; font-size: .68rem; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; }

.legend { display: flex; gap: 16px; font-size: .8rem; color: #64748b; justify-content: center; margin-top: 4px; }
.legend span:before { content: ""; display: inline-block; width: 10px; height: 10px; border-radius: 50%;
  margin-right: 6px; background: var(--c); }
.note { background: #fffbeb; border: 1px solid #fde68a; color: #78350f; border-radius: 12px; padding: 10px 14px;
  font-size: .86rem; margin: 10px 0; }
.empty { text-align: center; padding: 40px 10px; color: #64748b; }
.empty .big { font-size: 2.4rem; }
[data-testid="stSidebar"] { background: #f8faff; border-right: 1px solid #e5e7f3; }
</style>
"""


def hero() -> str:
    return (
        '<div class="hero"><div class="eyebrow">AI-powered · Image + Video</div>'
        '<h1>Multimodal Deepfake Detection Platform</h1>'
        '<p>Upload an image, a video, or both. We analyse the content, give it a risk score from 0 to 100, '
        'and explain the reasons in plain language.</p>'
        '<div class="chips"><span class="chip">🖼️ Image forensics</span><span class="chip">🎬 Video frame analysis</span>'
        '<span class="chip">🎯 Risk score</span><span class="chip">💡 Clear reasons</span></div></div>'
    )


def step(num: int, title: str, sub: str = "") -> str:
    return (f'<div class="step"><div class="num">{num}</div><div><div class="t">{html.escape(title)}</div>'
            f'<div class="s">{html.escape(sub)}</div></div></div>')


def gauge_svg(score: float, level: str) -> str:
    """Semicircle risk meter drawn as inline SVG (no extra libraries)."""
    score = max(0.0, min(100.0, float(score)))
    cx, cy, r = 130, 130, 100

    def pt(v: float, radius: float = r):
        ang = math.pi * (1 - v / 100.0)
        return cx + radius * math.cos(ang), cy - radius * math.sin(ang)

    def arc(v0: float, v1: float, color: str, width: int = 18) -> str:
        x0, y0 = pt(v0)
        x1, y1 = pt(v1)
        return (f'<path d="M {x0:.1f} {y0:.1f} A {r} {r} 0 0 1 {x1:.1f} {y1:.1f}" stroke="{color}" '
                f'stroke-width="{width}" fill="none" stroke-linecap="round"/>')

    color = LEVEL.get(level, LEVEL["Medium"])["color"]
    nx, ny = pt(score, r - 30)
    return (
        '<svg viewBox="0 0 260 210" width="100%" style="max-width:270px">'
        + arc(0, 34, "#bbf7d0") + arc(36, 64, "#fde68a") + arc(66, 100, "#fecaca")
        + arc(0, max(score, 0.5), color, 18)
        + f'<line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="#1e1b4b" stroke-width="4" stroke-linecap="round"/>'
        + f'<circle cx="{cx}" cy="{cy}" r="9" fill="#1e1b4b"/>'
        + f'<text x="{cx}" y="{cy + 50}" text-anchor="middle" font-size="40" font-weight="800" fill="#1e1b4b">{score:.0f}</text>'
        + f'<text x="{cx}" y="{cy + 68}" text-anchor="middle" font-size="12" fill="#64748b">out of 100</text>'
        + '</svg>'
        + '<div class="legend"><span style="--c:#16a34a">Low</span><span style="--c:#d97706">Medium</span>'
          '<span style="--c:#dc2626">High</span></div>'
    )


def result_card(res: Dict, headline: str) -> str:
    level = res.get("risk_level", "Medium")
    lv = LEVEL.get(level, LEVEL["Medium"])
    conf = res.get("confidence")
    conf_html = ""
    if conf is not None:
        pct = round(min(max(conf, 0.0), 1.0) * 100)
        conf_html = (f'<div class="meter-label"><span>Evidence strength (not a probability)</span><b>{pct}%</b></div>'
                     f'<div class="meter"><div style="width:{pct}%"></div></div>')
    return (
        '<div class="card"><div class="result"><div>' + gauge_svg(res.get("risk_score", 0), level) + '</div><div>'
        f'<span class="badge" style="background:{lv["soft"]};color:{lv["color"]}">{lv["icon"]} {lv["text"]}</span>'
        f'<div class="verdict">{html.escape(str(res.get("result_label", "")))}</div>'
        f'<div class="summary">{html.escape(headline)}</div>{conf_html}</div></div></div>'
    )


def sort_reasons(reasons: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Risk-raising reasons first, then context, then reassuring ones (stable within each group)."""
    order = {"risk": 0, "info": 1, "ok": 2}
    return sorted(reasons, key=lambda r: order.get(r["kind"], 1))


def reasons_html(reasons: List[Dict[str, str]]) -> str:
    if not reasons:
        return '<div class="note">No detailed reasons are available for this result.</div>'
    rows = []
    for r in sort_reasons(reasons):
        k = KIND.get(r["kind"], KIND["info"])
        rows.append(
            f'<div class="reason" style="background:{k["soft"]}"><div class="ic" style="background:{k["color"]}">{k["icon"]}</div>'
            f'<div><div class="rt">{html.escape(r["title"])}<span class="tag" style="color:{k["color"]}">{k["tag"]}</span></div>'
            f'<div class="rd">{html.escape(r["detail"])}</div></div></div>')
    return "".join(rows)
