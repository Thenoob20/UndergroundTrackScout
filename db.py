from __future__ import annotations
import sqlite3, csv, json, requests
from pathlib import Path
from datetime import datetime
from config import DB_PATH, FEEDBACK_SETTINGS_PATH, FEEDBACK_EXPORT_DIR, DEFAULT_GOOGLE_FORM_URL
from models import TrackCandidate


def _conn():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        artist TEXT, title TEXT, genre TEXT, platform TEXT, url TEXT UNIQUE,
        artist_url TEXT, score REAL, confidence REAL, label TEXT, hidden_gem INTEGER,
        reason TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS ignored_artists (
        artist TEXT PRIMARY KEY, created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS taste_feedback (
        url TEXT PRIMARY KEY,
        artist TEXT, title TEXT, genre TEXT, track_type TEXT,
        feedback TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS track_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tester_name TEXT, dj_type TEXT, rating TEXT, comment TEXT,
        artist TEXT, title TEXT, genre TEXT, track_type TEXT, platform TEXT, url TEXT,
        score REAL, confidence REAL, plays INTEGER, likes INTEGER, reposts INTEGER,
        hidden_gem INTEGER, label TEXT, reason TEXT,
        sent_online INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS seen_tracks (
        url TEXT PRIMARY KEY,
        artist TEXT, title TEXT, genre TEXT,
        seen_count INTEGER DEFAULT 0,
        first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
        last_seen TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    return conn


def add_favorite(t: TrackCandidate) -> bool:
    with _conn() as conn:
        cur = conn.execute('''INSERT OR IGNORE INTO favorites
            (artist,title,genre,platform,url,artist_url,score,confidence,label,hidden_gem,reason)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (t.artist,t.title,t.genre,t.platform,t.url,t.artist_url,t.discovery_score,t.source_confidence,t.label,int(t.hidden_gem),t.reason))
        conn.execute('''INSERT OR REPLACE INTO taste_feedback(url,artist,title,genre,track_type,feedback)
            VALUES (?,?,?,?,?,?)''', (t.url,t.artist,t.title,t.genre,t.track_type,"favorite"))
        return cur.rowcount > 0


def add_feedback(t: TrackCandidate, feedback: str) -> None:
    with _conn() as conn:
        conn.execute('''INSERT OR REPLACE INTO taste_feedback(url,artist,title,genre,track_type,feedback)
            VALUES (?,?,?,?,?,?)''', (t.url,t.artist,t.title,t.genre,t.track_type,feedback))


def get_feedback_settings() -> dict:
    path = Path(FEEDBACK_SETTINGS_PATH)
    if not path.exists():
        return {"tester_name": "", "dj_type": "", "webhook_url": "", "google_form_url": DEFAULT_GOOGLE_FORM_URL, "send_online": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "tester_name": data.get("tester_name", ""),
            "dj_type": data.get("dj_type", ""),
            "webhook_url": data.get("webhook_url", ""),
            "google_form_url": data.get("google_form_url") or DEFAULT_GOOGLE_FORM_URL,
            "send_online": bool(data.get("send_online", False)),
        }
    except Exception:
        return {"tester_name": "", "dj_type": "", "webhook_url": "", "google_form_url": DEFAULT_GOOGLE_FORM_URL, "send_online": False}


def save_feedback_settings(settings: dict) -> None:
    path = Path(FEEDBACK_SETTINGS_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def _feedback_payload(t: TrackCandidate, rating: str, comment: str, tester_name: str, dj_type: str) -> dict:
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "tester_name": tester_name,
        "dj_type": dj_type,
        "rating": rating,
        "comment": comment,
        "artist": t.artist,
        "track": t.title,
        "genre": t.genre,
        "track_type": t.track_type,
        "platform": t.platform,
        "url": t.url,
        "artist_url": t.artist_url,
        "artwork_url": getattr(t, "artwork_url", ""),
        "score": t.discovery_score,
        "confidence": t.source_confidence,
        "plays": t.plays,
        "likes": t.likes,
        "reposts": t.reposts,
        "hidden_gem": bool(t.hidden_gem),
        "label": t.label or t.label_signal,
        "why_picked": t.reason,
    }


def add_track_feedback(t: TrackCandidate, rating: str, comment: str = "", tester_name: str = "", dj_type: str = "") -> tuple[bool, str]:
    settings = get_feedback_settings()
    tester_name = tester_name or settings.get("tester_name", "")
    dj_type = dj_type or settings.get("dj_type", "")
    sent_online = 0
    online_msg = "Saved locally."
    if settings.get("send_online") and settings.get("webhook_url"):
        try:
            payload = _feedback_payload(t, rating, comment, tester_name, dj_type)
            r = requests.post(settings["webhook_url"], json=payload, timeout=12)
            if 200 <= r.status_code < 300:
                sent_online = 1
                online_msg = "Saved locally and sent online."
            else:
                online_msg = f"Saved locally. Online send failed: HTTP {r.status_code}"
        except Exception as exc:
            online_msg = f"Saved locally. Online send failed: {exc}"
    with _conn() as conn:
        conn.execute('''INSERT INTO track_feedback
            (tester_name,dj_type,rating,comment,artist,title,genre,track_type,platform,url,score,confidence,plays,likes,reposts,hidden_gem,label,reason,sent_online)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (tester_name,dj_type,rating,comment,t.artist,t.title,t.genre,t.track_type,t.platform,t.url,t.discovery_score,t.source_confidence,t.plays,t.likes,t.reposts,int(t.hidden_gem),t.label or t.label_signal,t.reason,sent_online))
    # Also train taste engine from simple feedback.
    if rating in ("Great Find", "Playable", "Favorite"):
        add_feedback(t, "like")
    elif rating in ("Bad Result", "Wrong Genre", "DJ Set / Mix", "Too Mainstream"):
        add_feedback(t, "dislike")
    return bool(sent_online), online_msg


def export_feedback_csv() -> Path:
    out_dir = Path(FEEDBACK_EXPORT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with _conn() as conn:
        rows = list(conn.execute('''SELECT created_at,tester_name,dj_type,rating,comment,artist,title,genre,track_type,platform,url,score,confidence,plays,likes,reposts,hidden_gem,label,reason,sent_online
            FROM track_feedback ORDER BY created_at DESC'''))
    headers = ["created_at","tester_name","dj_type","rating","comment","artist","track","genre","track_type","platform","url","score","confidence","plays","likes","reposts","hidden_gem","label","why_picked","sent_online"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    return path


def feedback_summary() -> dict:
    with _conn() as conn:
        ratings = list(conn.execute('''SELECT rating, COUNT(*) FROM track_feedback GROUP BY rating ORDER BY COUNT(*) DESC'''))
        testers = list(conn.execute('''SELECT tester_name, COUNT(*) FROM track_feedback WHERE COALESCE(tester_name,'')<>'' GROUP BY tester_name ORDER BY COUNT(*) DESC'''))
        total = conn.execute('''SELECT COUNT(*) FROM track_feedback''').fetchone()[0]
    return {"total": total, "ratings": ratings, "testers": testers}


def taste_profile() -> dict:
    with _conn() as conn:
        rows = list(conn.execute("SELECT genre, track_type, feedback FROM taste_feedback"))
    profile = {"genres": {}, "types": {}, "likes": 0, "dislikes": 0, "favorites": 0}
    for genre, track_type, feedback in rows:
        weight = 2 if feedback == "favorite" else (1 if feedback == "like" else -1)
        if feedback in ("like", "favorite"):
            profile["likes"] += 1
        if feedback == "dislike":
            profile["dislikes"] += 1
        if feedback == "favorite":
            profile["favorites"] += 1
        if genre:
            profile["genres"][genre.lower()] = profile["genres"].get(genre.lower(), 0) + weight
        if track_type:
            profile["types"][track_type.lower()] = profile["types"].get(track_type.lower(), 0) + weight
    return profile


def taste_bonus(t: TrackCandidate) -> float:
    p = taste_profile()
    bonus = 0.0
    g = (t.genre or "").lower()
    tt = (t.track_type or "").lower()
    for known, weight in p["genres"].items():
        if known and (known in g or g in known):
            bonus += max(-8, min(8, weight * 1.5))
    if tt in p["types"]:
        bonus += max(-6, min(6, p["types"][tt] * 1.5))
    return round(max(-12, min(12, bonus)), 2)


def mark_seen(tracks: list[TrackCandidate]) -> None:
    with _conn() as conn:
        for t in tracks:
            if not t.url:
                continue
            conn.execute('''INSERT INTO seen_tracks(url,artist,title,genre,seen_count)
                VALUES (?,?,?,?,1)
                ON CONFLICT(url) DO UPDATE SET seen_count=seen_count+1,last_seen=CURRENT_TIMESTAMP''',
                (t.url,t.artist,t.title,t.genre))


def seen_counts(urls: list[str]) -> dict[str, int]:
    if not urls:
        return {}
    qmarks = ",".join("?" for _ in urls)
    with _conn() as conn:
        return {u: c for u, c in conn.execute(f"SELECT url,seen_count FROM seen_tracks WHERE url IN ({qmarks})", urls)}


def ignored_artists() -> set[str]:
    with _conn() as conn:
        return {r[0].lower() for r in conn.execute("SELECT artist FROM ignored_artists")}


def ignore_artist(artist: str) -> None:
    if artist:
        with _conn() as conn:
            conn.execute("INSERT OR IGNORE INTO ignored_artists(artist) VALUES (?)", (artist,))


def label_stats() -> list[tuple[str,int,float,int]]:
    with _conn() as conn:
        rows = list(conn.execute('''SELECT label, COUNT(*), AVG(score), SUM(hidden_gem)
            FROM favorites WHERE COALESCE(label,'') <> '' GROUP BY label ORDER BY AVG(score) DESC'''))
    return [(r[0], r[1], round(r[2] or 0, 1), r[3] or 0) for r in rows]


def rising_artist_stats() -> list[tuple[str,int,float,int]]:
    with _conn() as conn:
        favs = list(conn.execute('''SELECT artist, COUNT(*), AVG(score), SUM(hidden_gem)
            FROM favorites GROUP BY artist HAVING COUNT(*) >= 1 ORDER BY AVG(score) DESC LIMIT 50'''))
    return [(r[0], r[1], round(r[2] or 0, 1), r[3] or 0) for r in favs]
