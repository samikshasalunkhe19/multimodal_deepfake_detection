"""Turn the raw evidence of an analysis result into short, plain-language reasons.

Pure Python (no Streamlit) so it is easy to test.

    build_reasons(result) -> list of {"kind": "risk" | "ok" | "info", "title": str, "detail": str}

kind:  risk = pushes the score up,  ok = reassuring,  info = neutral / context.
Nothing is invented here: every reason is read from fields the detectors already return.
"""
from __future__ import annotations

from typing import Any, Dict, List

Reason = Dict[str, str]


def _r(kind: str, title: str, detail: str) -> Reason:
    return {"kind": kind, "title": title, "detail": detail}


def _pct(x: float) -> str:
    return f"{round(x * 100)}%"


def _tier(p: float) -> str:
    return "high" if p >= 0.65 else "moderate" if p >= 0.35 else "low"


def image_reasons(res: Dict[str, Any]) -> List[Reason]:
    ev = res.get("evidence") or {}
    out: List[Reason] = []

    clf = ev.get("classifier") or {}
    if clf.get("available"):
        p = clf.get("p_fake")
        region = clf.get("region_scored", "image")
        if p is not None:
            kind = "risk" if p >= 0.65 else "ok" if p < 0.35 else "info"
            out.append(_r(kind, f"AI classifier: {_tier(p)} fake likelihood ({_pct(p)})",
                          f"A trained model scored the {region}. Higher means it looks more like AI-generated or "
                          f"manipulated content."))
        whole = clf.get("p_fake_whole_image")
        if p is not None and whole is not None and region != "whole image" and abs(p - whole) >= 0.25:
            out.append(_r("info", "Face and full image disagree",
                          f"The face crop scored {_pct(p)} but the whole image scored {_pct(whole)}. "
                          "Large gaps can mean only part of the picture was edited."))
    else:
        out.append(_r("info", "No trained model was used",
                      "Only weak checks (compression and metadata) contributed, so the score is capped at Medium."))

    ela = ev.get("ela") or {}
    if ela.get("applicable") and ela.get("score") is not None:
        s = ela["score"]
        if s >= 0.6:
            out.append(_r("risk", "Uneven compression pattern", f"Error Level Analysis score {s:.2f}/1. "
                          "Parts of the image were compressed differently, which can happen when regions are pasted in. "
                          "This is a weak hint on its own."))
        elif s <= 0.3:
            out.append(_r("ok", "Consistent compression", f"Error Level Analysis score {s:.2f}/1 - no obvious "
                          "patchwork of different compression levels."))

    meta = ev.get("metadata") or {}
    if meta.get("ai_indicators"):
        out.append(_r("risk", "Metadata names an AI image tool",
                      "Found: " + ", ".join(meta["ai_indicators"]) + ". This shows how the file was produced."))
    if meta.get("editing_software"):
        out.append(_r("info", "Edited with image software",
                      "Found: " + ", ".join(meta["editing_software"]) + ". Editing is common and not wrongdoing by itself."))
    if meta.get("camera"):
        out.append(_r("ok", "Camera information present", f"{meta['camera']}. Cameras write this; anyone can also fake it."))
    elif meta.get("format") == "JPEG" and not meta.get("has_exif"):
        out.append(_r("info", "No camera metadata", "Many apps and websites strip it, so this alone proves nothing."))

    n_faces = ev.get("faces_detected")
    if n_faces == 0:
        out.append(_r("info", "No face detected", "The whole image was scored. Face-trained models can be less reliable here."))
    elif n_faces:
        out.append(_r("info", f"{n_faces} face{'s' if n_faces != 1 else ''} detected", "The largest face was analysed."))

    size = ev.get("image_size")
    if size and min(size) < 256:
        out.append(_r("info", "Small image", f"{size[0]}x{size[1]} px gives detectors less detail to work with."))
    return out


def video_reasons(res: Dict[str, Any]) -> List[Reason]:
    ev = res.get("evidence") or {}
    agg = ev.get("aggregate") or {}
    out: List[Reason] = []

    if not agg:
        out.append(_r("info", "Not enough usable frames",
                      f"{ev.get('frames_scored', 0)} frame(s) could be scored, which is too few for a reliable result."))
        return out

    mean_p, vid_p = agg.get("mean_p_fake"), agg.get("video_p_fake")
    if vid_p is not None:
        kind = "risk" if vid_p >= 0.65 else "ok" if vid_p < 0.35 else "info"
        out.append(_r(kind, f"Video-level fake likelihood: {_tier(vid_p)} ({_pct(vid_p)})",
                      f"Average across frames is {_pct(mean_p or 0)}; the most suspicious frames weigh in more, "
                      "so a short fake section is not hidden by many normal frames."))

    frac = agg.get("fraction_suspicious")
    if frac is not None:
        if frac >= 0.3:
            out.append(_r("risk", f"{_pct(frac)} of frames look suspicious", "A large share of the video is flagged, "
                          "not just a single odd frame."))
        elif frac == 0:
            out.append(_r("ok", "No suspicious frames", "No sampled frame crossed the suspicion threshold."))

    segs = agg.get("segments") or []
    if segs:
        def ts(s: float) -> str:
            return f"{int(s // 60)}:{int(s % 60):02d}"
        shown = ", ".join(f"{ts(s['start_s'])}-{ts(s['end_s'])}" for s in segs[:3])
        out.append(_r("risk", f"{len(segs)} suspicious segment{'s' if len(segs) != 1 else ''}",
                      f"Consecutive suspicious frames at {shown}. Review these moments first."))

    if (agg.get("jitter") or 0) >= 0.15:
        out.append(_r("risk", "Unstable frame-to-frame scores", f"Jitter {agg['jitter']:.2f}. Scores that jump around "
                      "between neighbouring frames can come from flickering face edits."))

    mode = ev.get("scoring_mode")
    scored, sampled = ev.get("frames_scored"), ev.get("frames_sampled")
    if scored is not None and sampled:
        out.append(_r("info", f"{scored} of {sampled} sampled frames scored",
                      f"Method: {mode or 'frames'}. Frames without a clear face are skipped when scoring face crops."))
    return out


def overall_reasons(res: Dict[str, Any]) -> List[Reason]:
    ev = res.get("evidence") or {}
    out: List[Reason] = []
    used = ev.get("modules_used") or []
    if ev.get("conflict"):
        out.append(_r("info", "Image and video disagree",
                      "One shows high risk and the other low risk. Confidence is reduced - please review the originals."))
    if ev.get("corroboration_bonus_applied"):
        out.append(_r("risk", "Image and video agree on high risk", "Independent agreement is stronger evidence."))
    if len(used) == 1:
        out.append(_r("info", "Only one module was usable", "The result could not be cross-checked."))
    for s in ev.get("modules_skipped") or []:
        out.append(_r("info", f"{s['modality'].capitalize()} not counted", s.get("reason", "")))
    for m in sorted(used, key=lambda m: m["risk_score"], reverse=True):
        kind = "risk" if m["risk_level"] == "High" else "ok" if m["risk_level"] == "Low" else "info"
        out.append(_r(kind, f"{m['modality'].capitalize()} risk {round(m['risk_score'])}/100", f"Level: {m['risk_level']}."))
    return out


def build_reasons(res: Dict[str, Any]) -> List[Reason]:
    """Reasons for one result. For a fused result, module-level reasons are listed after the overall ones."""
    modality = res.get("modality")
    if modality == "image":
        return image_reasons(res)
    if modality == "video":
        return video_reasons(res)
    if modality == "overall":
        out = overall_reasons(res)
        for kind, comp in (res.get("components") or {}).items():
            sub = build_reasons({**comp, "modality": kind})
            for r in sub:
                title = r["title"] if r["title"].lower().startswith(kind) else f"{kind.capitalize()}: {r['title']}"
                out.append({**r, "title": title})
        return out
    return []
