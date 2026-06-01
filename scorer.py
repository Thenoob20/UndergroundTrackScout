from __future__ import annotations
from datetime import datetime, timezone
from typing import Iterable
from config import DJ_FRIENDLY_KEYWORDS, MAX_PLAYS, NEGATIVE_KEYWORDS, TRACKED_LABELS, NON_TRACK_KEYWORDS
from models import TrackCandidate
try:
    from db import taste_bonus
except Exception:
    taste_bonus = None


def _lower(text: str | None) -> str:
    return (text or "").lower().strip()

def detect_track_type(c: TrackCandidate) -> str:
    text = _lower(" ".join([c.artist, c.title, c.genre]))
    if any(w in text for w in ["dj set", "live set", "podcast", "radio", "guest mix", "hour mix", "mix 202", "mixtape", "episode", "session"]):
        return "DJ Set"
    if "bootleg" in text:
        return "Bootleg"
    if "mashup" in text or "vs " in text:
        return "Mashup"
    if "remix" in text or "rmx" in text:
        return "Remix"
    if "edit" in text or "club edit" in text or "dj edit" in text:
        return "Edit"
    if "dub" in text or "tool" in text:
        return "DJ Tool"
    return "Original/Unknown"

def is_non_track(c: TrackCandidate) -> bool:
    text = _lower(" ".join([c.artist, c.title, c.genre]))
    return any(w in text for w in NON_TRACK_KEYWORDS) or detect_track_type(c) == "DJ Set"

def _parse_date(date_text: str | None):
    if not date_text:
        return None
    try:
        return datetime.fromisoformat(date_text.replace("Z", "+00:00"))
    except Exception:
        return None

def freshness_score(upload_date: str | None) -> tuple[float, str]:
    dt = _parse_date(upload_date)
    if not dt:
        return 0.0, "⚠ Metadata Missing: upload date"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    age_days = max(0, (datetime.now(timezone.utc) - dt).days)
    if age_days <= 7: return 18.0, "very fresh"
    if age_days <= 30: return 15.0, "fresh"
    if age_days <= 90: return 10.0, "recent"
    if age_days <= 180: return 4.0, "not too old"
    return -10.0, "older upload"

def engagement_score(plays, likes, reposts, comments) -> tuple[float, str]:
    plays, likes, reposts, comments = plays or 0, likes or 0, reposts or 0, comments or 0
    if plays <= 0:
        if likes or reposts or comments:
            raw = likes * 0.8 + reposts * 1.8 + comments * 1.0
            return min(10.0, raw), "partial engagement data"
        return 0.0, "⚠ Metadata Missing: plays/likes/reposts"
    engagement = likes + reposts * 2.5 + comments * 1.0
    ratio = engagement / max(plays, 1)
    if ratio >= 0.10: return 32.0, "elite engagement ratio"
    if ratio >= 0.06: return 26.0, "strong engagement ratio"
    if ratio >= 0.03: return 18.0, "good engagement ratio"
    if ratio >= 0.012: return 8.0, "some engagement"
    if plays > 20_000 and engagement < 100: return -15.0, "possible inflated plays"
    return 1.0, "low engagement"

def underground_score(plays) -> tuple[float, str]:
    if plays is None: return 0.0, "⚠ Metadata Missing: play count"
    if plays < 250: return 8.0, "very low plays"
    if plays < 1_000: return 14.0, "very low plays"
    if plays < 10_000: return 20.0, "underground play range"
    if plays < MAX_PLAYS: return 10.0, "below mainstream threshold"
    return -25.0, "above underground threshold"

def hidden_gem_score(c: TrackCandidate) -> tuple[float, str]:
    plays, likes, reposts, comments = c.plays or 0, c.likes or 0, c.reposts or 0, c.comments or 0
    engagement = likes + reposts * 2.5 + comments
    if plays and plays < 5000 and engagement >= 75:
        c.hidden_gem = True
        return 15.0, "hidden gem bonus"
    if plays and plays < 15000 and engagement >= 250:
        c.hidden_gem = True
        return 10.0, "possible hidden gem"
    c.hidden_gem = False
    return 0.0, ""

def label_score(c: TrackCandidate) -> tuple[float, str]:
    haystack = _lower(" ".join([c.artist, c.title, c.genre, c.reason, c.label, c.url, c.artist_url]))
    for label in TRACKED_LABELS:
        if _lower(label) in haystack:
            c.label = c.label or label
            c.label_signal = f"tracked label: {label}"
            return 8.0, c.label_signal
    c.label_signal = ""
    return 0.0, ""

def keyword_score(c: TrackCandidate, query_genres: Iterable[str]) -> tuple[float, str]:
    haystack = _lower(" ".join([c.artist, c.title, c.genre, c.reason, c.label]))
    score, reasons = 0.0, []
    for genre in query_genres:
        genre = _lower(genre)
        if genre and genre in haystack:
            score += 10; reasons.append(f"matches {genre}")
    for word in DJ_FRIENDLY_KEYWORDS:
        if word in haystack:
            score += 3; reasons.append(f"DJ tag: {word}")
    for word in NEGATIVE_KEYWORDS:
        if word in haystack:
            score -= 12; reasons.append(f"negative: {word}")
    return min(score, 25.0), "; ".join(reasons) if reasons else "no keyword boost"

def source_confidence(c: TrackCandidate) -> tuple[float, str]:
    base = {"Bandcamp": 72, "SoundCloud": 62, "Reddit": 38, "Demo": 50}.get(c.platform, 45)
    if c.url: base += 8
    if c.artist_url: base += 5
    if c.upload_date: base += 5
    if c.plays is not None or c.likes is not None: base += 5
    if c.label_signal: base += 5
    c.source_confidence = round(max(0, min(100, base)), 1)
    return c.source_confidence / 10.0, f"source confidence {c.source_confidence:.0f}/100"

def track_type_score(c: TrackCandidate) -> tuple[float, str]:
    c.track_type = detect_track_type(c)
    if c.track_type == "DJ Set":
        return -35.0, "non-track: DJ set/mix"
    if c.track_type in ("Edit", "Bootleg", "Remix", "Mashup", "DJ Tool"):
        return 8.0, f"DJ-friendly type: {c.track_type}"
    return 0.0, f"type: {c.track_type}"

def apply_taste_score(c: TrackCandidate) -> tuple[float, str]:
    if not taste_bonus:
        return 0.0, ""
    try:
        b = float(taste_bonus(c))
    except Exception:
        b = 0.0
    c.taste_score = b
    if b > 0:
        return b, f"taste match +{b:.1f}"
    if b < 0:
        return b, f"taste penalty {b:.1f}"
    return 0.0, ""

def score_candidate(c: TrackCandidate, query_genres: Iterable[str]) -> TrackCandidate:
    total = 0.0; parts = []
    components = [
        track_type_score(c),
        freshness_score(c.upload_date),
        engagement_score(c.plays, c.likes, c.reposts, c.comments),
        underground_score(c.plays),
        hidden_gem_score(c),
        label_score(c),
        keyword_score(c, query_genres),
        source_confidence(c),
        apply_taste_score(c),
    ]
    for value, reason in components:
        total += value
        if reason: parts.append(reason)
    total += c.source_reputation
    if c.source_reputation: parts.append(f"source reputation +{c.source_reputation:.1f}")

    spotify_penalty = float(getattr(c, "spotify_mainstream_penalty", 0.0) or 0.0)
    if spotify_penalty:
        total -= spotify_penalty
        parts.append(f"Spotify mainstream penalty -{spotify_penalty:.1f}")
    elif "not found" in getattr(c, "spotify_note", "").lower():
        total += 5.0
        parts.append("Spotify underground bonus: not found")

    spotify_note = getattr(c, "spotify_note", "")
    if spotify_note and "failed" not in spotify_note.lower():
        parts.append(f"Spotify: {spotify_note}")

    missing_core = (c.plays is None and c.likes is None and c.reposts is None)
    if missing_core:
        total = min(total, 45.0)
        if not any("Metadata Missing" in p for p in parts):
            parts.insert(0, "⚠ Metadata Missing")
        c.source_confidence = min(c.source_confidence or 0, 55)
    c.discovery_score = round(max(0, min(100, total)), 2)
    c.reason = " | ".join(p for p in parts if p)
    return c

def score_candidates(candidates: list[TrackCandidate], query_genres: Iterable[str]) -> list[TrackCandidate]:
    good = [c for c in candidates if c.artist != "ERROR"]
    scored = [score_candidate(c, query_genres) for c in good]
    return sorted(scored, key=lambda x: x.discovery_score, reverse=True)
