"""Streamlit user interface - Multimodal Deepfake Detection Platform (image + video).

    streamlit run frontend/app.py

The backend must be running first (uvicorn backend.main:app --port 8000).
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # so `frontend.*` imports work

from frontend import api_client as api   # noqa: E402
from frontend import theme               # noqa: E402
from frontend.reasons import build_reasons   # noqa: E402

IMAGE_TYPES = ["jpg", "jpeg", "png"]
VIDEO_TYPES = ["mp4", "avi", "mov"]

st.set_page_config(page_title="Multimodal Deepfake Detection Platform", page_icon="🛡️", layout="wide")
st.markdown(theme.CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------- helpers

def b64_image(data: str) -> bytes:
    return base64.b64decode(data)


def timeline_chart(timeline: list) -> None:
    pts = [(p["t"], p["p_fake"] * 100) for p in timeline if p.get("p_fake") is not None]
    if not pts:
        return
    t, p = zip(*pts)
    fig = go.Figure()
    fig.add_hrect(y0=65, y1=100, fillcolor="#fee2e2", opacity=0.55, line_width=0)
    fig.add_hrect(y0=35, y1=65, fillcolor="#fef3c7", opacity=0.55, line_width=0)
    fig.add_hrect(y0=0, y1=35, fillcolor="#dcfce7", opacity=0.55, line_width=0)
    fig.add_trace(go.Scatter(x=t, y=p, mode="lines+markers", line=dict(color="#4f46e5", width=3),
                             marker=dict(size=7), hovertemplate="%{x:.1f}s: %{y:.0f}% fake<extra></extra>"))
    fig.update_layout(xaxis_title="Time (seconds)", yaxis_title="Fake likelihood (%)", yaxis_range=[0, 100],
                      height=300, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)


def run(label: str, fn, *args):
    """Call the API with a spinner; show errors nicely. Returns the result or None."""
    try:
        with st.spinner(label):
            return fn(*args)
    except api.ApiError as exc:
        st.error(str(exc))
        return None


def headline_for(res: dict) -> str:
    """One-sentence plain-language takeaway shown under the verdict."""
    level = res.get("risk_level")
    if res.get("usable") is False:
        return "This content could not be scored reliably, so treat the result as inconclusive."
    return {
        "High": "Several signals suggest this content may be AI-generated or manipulated. Verify it before trusting or sharing it.",
        "Medium": "The signals are mixed. This is not a clear verdict - a human should review the content.",
        "Low": "No strong signs of manipulation were found. That does not prove the content is genuine.",
    }.get(level, res.get("explanation", ""))


def visual_evidence(res: dict) -> None:
    """Heat-maps, timeline and suspicious frames for one module result."""
    modality = res.get("modality")
    if modality == "image" and res.get("images"):
        imgs = res["images"]
        c1, c2 = st.columns(2)
        if imgs.get("heatmap_png_b64"):
            c1.image(b64_image(imgs["heatmap_png_b64"]), caption="Grad-CAM heat-map: where the model looked")
        if imgs.get("ela_map_png_b64"):
            c2.image(b64_image(imgs["ela_map_png_b64"]), caption="Error Level Analysis (weak hint)")
    if modality == "video":
        if res.get("timeline"):
            st.markdown("**Fake likelihood over time**")
            timeline_chart(res["timeline"])
        if res.get("suspicious_frames"):
            st.markdown("**Most suspicious frames**")
            cols = st.columns(min(5, len(res["suspicious_frames"])))
            for col, f in zip(cols, res["suspicious_frames"]):
                if f.get("thumbnail_png_b64"):
                    col.image(b64_image(f["thumbnail_png_b64"]), caption=f"{f['timestamp']} · {f['p_fake'] * 100:.0f}%")


def show_result(res: dict, key: str) -> None:
    """Render one analysis result (single modality or fused): score, reasons, evidence, report."""
    st.markdown(theme.result_card(res, headline_for(res)), unsafe_allow_html=True)
    if res.get("usable") is False:
        st.markdown('<div class="note">⚠️ This result is inconclusive and was not counted as evidence.</div>',
                    unsafe_allow_html=True)

    st.markdown('<div class="section-title">Why this score?</div>'
                '<div class="section-sub">What the detectors found, most important first.</div>', unsafe_allow_html=True)
    reasons = theme.sort_reasons(build_reasons(res))
    st.markdown(theme.reasons_html(reasons[:6]), unsafe_allow_html=True)
    if len(reasons) > 6:
        with st.expander(f"Show {len(reasons) - 6} more detail{'s' if len(reasons) - 6 != 1 else ''}"):
            st.markdown(theme.reasons_html(reasons[6:]), unsafe_allow_html=True)

    modality = res.get("modality")
    if modality == "overall":
        ev = res["evidence"]
        rows = [{"Content": m["modality"].capitalize(), "Risk score": round(m["risk_score"]),
                 "Level": m["risk_level"], "Weight": m["weight"]} for m in ev.get("modules_used", [])]
        rows += [{"Content": s["modality"].capitalize(), "Risk score": None, "Level": "not used", "Weight": None}
                 for s in ev.get("modules_skipped", [])]
        if rows:
            st.markdown('<div class="section-title">Image vs video</div>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        for kind, comp in (res.get("components") or {}).items():
            with st.expander(f"{'🖼️' if kind == 'image' else '🎬'} {kind.capitalize()} evidence", expanded=False):
                visual_evidence({**comp, "modality": kind})
    else:
        has_visual = bool((modality == "image" and res.get("images")) or
                          (modality == "video" and (res.get("timeline") or res.get("suspicious_frames"))))
        if has_visual:
            st.markdown('<div class="section-title">Visual evidence</div>', unsafe_allow_html=True)
            visual_evidence(res)

    if res.get("limitations"):
        with st.expander("⚖️ Limitations - please read"):
            for lim in res["limitations"]:
                st.write(f"- {lim}")
    with st.expander("🔧 Technical details (JSON)"):
        st.json(res.get("evidence", {}), expanded=False)

    if res.get("id"):
        pdf_key = f"pdf_{res['id']}"
        c1, c2, _ = st.columns([1, 1, 3])
        if c1.button("📄 Prepare PDF report", key=f"btn_{key}"):
            try:
                st.session_state[pdf_key] = api.report_pdf(res["id"])
            except api.ApiError as exc:
                st.error(str(exc))
        if pdf_key in st.session_state:
            c2.download_button("⬇️ Download PDF", st.session_state[pdf_key],
                               file_name=f"report_{res['id'][:8]}.pdf", mime="application/pdf", key=f"dl_{key}")


# ---------------------------------------------------------------- sidebar

with st.sidebar:
    st.markdown("### 🛡️ DeepFake Shield")
    st.caption("Risk estimates for images and videos. Results are never proof.")
    try:
        h = api.health()
        st.success("Backend connected")
        st.write(f"Face detection: {'✅ on' if h['face_detection'] else '⚠️ off (whole frames are scored)'}")
    except api.ApiError as exc:
        st.error(str(exc))
    st.divider()
    st.markdown("**How to read the score**")
    st.markdown("🟢 **0-35** Low risk  \n🟠 **35-65** Needs review  \n🔴 **65-100** High risk")
    st.divider()
    st.caption("🔒 Uploaded files are deleted right after analysis. Only the result is saved in History.")

# ---------------------------------------------------------------- page

st.markdown(theme.hero(), unsafe_allow_html=True)
tab_analyze, tab_hist, tab_about = st.tabs(["🔍 Analyze", "🕘 History", "ℹ️ How it works"])

with tab_analyze:
    st.markdown(theme.step(1, "Add your content", "Choose an image, a video, or both"), unsafe_allow_html=True)
    c_img, c_vid = st.columns(2, gap="large")
    with c_img:
        st.markdown('<div class="drop-title">🖼️ Image</div><div class="drop-sub">JPG or PNG</div>', unsafe_allow_html=True)
        up_img = st.file_uploader("Image", type=IMAGE_TYPES, key="up_image", label_visibility="collapsed")
        if up_img is not None:
            st.image(up_img, width=380)
    with c_vid:
        st.markdown('<div class="drop-title">🎬 Video</div><div class="drop-sub">MP4, AVI or MOV</div>', unsafe_allow_html=True)
        up_vid = st.file_uploader("Video", type=VIDEO_TYPES, key="up_video", label_visibility="collapsed")
        if up_vid is not None:
            st.video(up_vid)

    st.markdown(theme.step(2, "Analyze", "We score the content and explain the result"), unsafe_allow_html=True)
    go_btn = st.button("🔍 Analyze content", type="primary", disabled=not (up_img or up_vid), key="go")
    if not (up_img or up_vid):
        st.caption("Upload at least one file to enable analysis.")

    if go_btn:
        if up_img and up_vid:
            files = {"image": (up_img.name, up_img.getvalue(), up_img.type),
                     "video": (up_vid.name, up_vid.getvalue(), up_vid.type)}
            st.session_state["result"] = run("Analysing image and video, then combining the results...",
                                             api.analyze_multimodal, files)
        else:
            kind, up = ("image", up_img) if up_img else ("video", up_vid)
            st.session_state["result"] = run(
                f"Analysing {kind} (the first run may download a model)...",
                api.analyze_file, kind, up.name, up.getvalue(), up.type)

    if st.session_state.get("result"):
        st.markdown(theme.step(3, "Your result", "Risk score, reasons and evidence"), unsafe_allow_html=True)
        show_result(st.session_state["result"], "main")

with tab_hist:
    f_type = st.selectbox("Show", ["all", "image", "video", "overall"],
                          format_func=lambda x: {"all": "All analyses", "image": "Images", "video": "Videos",
                                                 "overall": "Image + video together"}[x])
    try:
        data = api.list_history(limit=100, file_type=None if f_type == "all" else f_type)
    except api.ApiError as exc:
        st.error(str(exc))
        data = {"items": [], "total": 0}
    if not data["items"]:
        st.markdown('<div class="empty"><div class="big">🗂️</div><b>No saved analyses yet</b><br>'
                    'Results appear here after you analyze something.</div>', unsafe_allow_html=True)
    else:
        st.caption(f"{data['total']} saved analyses")
        df = pd.DataFrame([{
            "id": i["id"], "When (UTC)": i["created_at"][:19].replace("T", " "), "Type": i["file_type"],
            "File": i["file_name"], "Risk": round(i["risk_score"]), "Level": i["risk_level"], "Result": i["result_label"],
        } for i in data["items"]])
        st.dataframe(
            df.drop(columns=["id"]), hide_index=True, use_container_width=True,
            column_config={"Risk": st.column_config.ProgressColumn("Risk", min_value=0, max_value=100, format="%d")})
        chosen = st.selectbox("Open an analysis", [None] + list(df["id"]),
                              format_func=lambda x: "Choose one..." if x is None else f"{x[:8]} - {df.set_index('id').loc[x, 'File']}")
        if chosen:
            item = next(i for i in data["items"] if i["id"] == chosen)
            res = item["details"].get("fusion", item["details"]) if item["file_type"] == "overall" else item["details"]
            if item["file_type"] == "overall":
                res = {**res, "components": {k: {**v, "modality": k} for k, v in item["details"].get("components", {}).items()}}
            show_result({**res, "id": item["id"]}, f"h_{chosen}")
            if st.button("🗑️ Delete this analysis", key="del"):
                try:
                    api.delete_history(chosen)
                    st.rerun()
                except api.ApiError as exc:
                    st.error(str(exc))

with tab_about:
    st.markdown('<div class="section-title">How it works</div>', unsafe_allow_html=True)
    a, b, c = st.columns(3, gap="medium")
    cards = [
        (a, "🖼️ Image module", "A trained classifier looks at the face (or whole image). A heat-map shows where it looked. "
                              "Compression (ELA) and metadata checks add weaker hints."),
        (b, "🎬 Video module", "About one frame per second is scored. Suspicious moments and unstable scores across "
                              "frames are tracked, so short fake sections are not hidden."),
        (c, "🎯 Risk score", "Signals are blended into one 0-100 score. If image and video agree, confidence rises; "
                            "if they conflict, it drops and the result asks for human review."),
    ]
    for col, title, body in cards:
        col.markdown(f'<div class="card"><div class="drop-title">{title}</div><div class="summary">{body}</div></div>',
                     unsafe_allow_html=True)
    st.markdown('<div class="note">⚖️ <b>Results are risk estimates, not proof.</b> Detectors can be wrong, especially on '
                'content from newer generators or heavily compressed files. Use the score to decide what to check next.</div>',
                unsafe_allow_html=True)
